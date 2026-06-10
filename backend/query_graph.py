import json
import re

from neo4j import GraphDatabase

from backend.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from backend.ollama_client import query_ollama
from backend.prompts import ANSWER_GENERATOR_PROMPT, ENTITY_EXTRACT_PROMPT, GENERAL_FALLBACK_PROMPT

# Patterns that indicate leaked reasoning/thinking garbage from the model
_GARBAGE_PATTERNS = re.compile(
    r'^(We |Ok |analysis|Okay|The query|Let\'s|I think|Wait|Hmm|Actually|So |But |If |In |By |With )',
    re.IGNORECASE
)
_CONTROL_TOKEN = re.compile(r'<\|[^|]+\|>')

def clean_answer(raw: str) -> str:
    """Strip reasoning-model leakage and return the first clean answer sentence."""
    if not raw:
        return raw

    # Remove control tokens like <|message|>, <|channel|>
    raw = _CONTROL_TOKEN.sub('', raw)

    lines = [l.strip() for l in raw.split('\n') if l.strip()]

    # Find the first line that looks like a real answer (not reasoning garbage)
    good_lines = []
    for line in lines:
        if _GARBAGE_PATTERNS.match(line):
            # If we already have some good lines, stop — rest is rambling
            if good_lines:
                break
            continue  # Skip garbage prefix lines
        if len(line) < 5:
            continue
        good_lines.append(line)
        # Stop after 2 good sentences to keep it concise
        if len(good_lines) >= 2:
            break

    result = ' '.join(good_lines).strip()

    # Last resort: if still empty, take raw first line
    if not result and lines:
        result = lines[0]

    return result

def _fallback_extract(question: str) -> list:
    """Extract capitalized word groups, or any key terms as a last resort."""
    # Grab sequences of capitalized words (e.g. 'Sam Altman', 'Apple', 'OpenAI')
    matches = re.findall(r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b', question)
    # Filter out common question words
    stopwords = {"who", "what", "where", "when", "why", "how", "which", "is", "are",
                 "did", "does", "do", "was", "were", "has", "have", "can", "the", "a", 
                 "an", "in", "on", "at", "for", "to", "of", "and", "or", "but", "with",
                 "by", "about", "from", "created", "founded", "founded by", "creator"}
    results = [m for m in matches if m.lower() not in stopwords]
    
    # If no capitalized words, extract any word that is not a stopword and is longer than 2 chars
    if not results:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question)
        results = [w for w in words if w.lower() not in stopwords]
        
    print(f"Fallback entity extraction from question: {results}")
    return results

def extract_entities(question: str) -> list:
    prompt = ENTITY_EXTRACT_PROMPT.format(question=question)
    response_text = query_ollama(prompt, json_mode=True)

    cleaned_response = response_text.strip()
    if cleaned_response.startswith("```"):
        cleaned_response = re.sub(r'^```(?:json)?\n|```$', '', cleaned_response, flags=re.MULTILINE).strip()

    try:
        entities = json.loads(cleaned_response)
        if isinstance(entities, list) and entities:
            return [str(e).strip() for e in entities if e]
    except Exception as e:
        print(f"Failed to parse entities list: {e}")
        print(f"Raw entity response: {response_text}")

    # LLM returned empty or unparseable — fall back to rule-based extraction
    print(f"LLM returned no entities, using fallback extractor.")
    return _fallback_extract(question)

def get_graph_context(entities: list) -> str:
    if not entities:
        return ""

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    seen = set()
    facts = []

    def add_fact(source, relation, target):
        key = (source, relation, target)
        if key not in seen:
            seen.add(key)
            # Human-readable arrow format for the LLM
            facts.append(f"{source} -[{relation}]-> {target}")

    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            for entity in entities:
                # ── FIX 1: Bidirectional search ──────────────────────────────
                # Finds the entity whether it appears as source OR target.
                # This is why "Sam Altman" (a leaf/target node) was returning nothing.
                result = session.run("""
                    MATCH (a:Entity)-[r]->(b:Entity)
                    WHERE toLower(a.name) CONTAINS toLower($entity)
                       OR toLower($entity) CONTAINS toLower(a.name)
                       OR toLower(b.name) CONTAINS toLower($entity)
                       OR toLower($entity) CONTAINS toLower(b.name)
                    RETURN a.name AS source, type(r) AS relation, b.name AS target
                """, entity=entity)

                direct_neighbors = set()
                for record in result:
                    add_fact(record["source"], record["relation"], record["target"])
                    # Collect both ends for 2-hop expansion
                    direct_neighbors.add(record["source"])
                    direct_neighbors.add(record["target"])

                # ── FIX 2: 2-hop expansion ───────────────────────────────────
                # For each neighbor found, also fetch their relationships so the
                # LLM has enough context to answer follow-up facts.
                for neighbor in direct_neighbors:
                    if neighbor.lower() == entity.lower():
                        continue  # skip the entity itself (already covered)
                    hop_result = session.run("""
                        MATCH (a:Entity)-[r]->(b:Entity)
                        WHERE toLower(a.name) = toLower($neighbor)
                        RETURN a.name AS source, type(r) AS relation, b.name AS target
                    """, neighbor=neighbor)
                    for record in hop_result:
                        add_fact(record["source"], record["relation"], record["target"])

    except Exception as e:
        print(f"Neo4j Read error: {e}")
    finally:
        driver.close()

    return "\n".join(facts)

def answer_question(question: str) -> dict:
    """Main Graph RAG pipeline execution. Returns both the answer and the retrieved context."""
    entities = extract_entities(question)
    print(f"Extracted entities: {entities}")

    context = get_graph_context(entities)
    print(f"Graph context ({len(context.splitlines())} facts):\n{context}")

    has_context = bool(context and context.strip())

    if has_context:
        # Answer grounded in graph facts
        prompt = ANSWER_GENERATOR_PROMPT.format(context=context, question=question)
        answer = ""
        for attempt in range(2):
            try:
                raw = query_ollama(prompt, json_mode=False).strip()
                answer = clean_answer(raw)
                if answer:
                    break
                print(f"Answer attempt {attempt + 1} returned empty after cleaning, retrying...")
            except Exception as e:
                print(f"Answer generation error (attempt {attempt + 1}): {e}")
                if attempt == 1:
                    answer = "I encountered an error generating a response. Please try again."
        return {
            "answer": answer or "I was unable to generate a response. Please try again.",
            "context": context,
            "has_context": True
        }
    else:
        # No graph facts — fall back to general conversational answer
        print("No graph context found. Using general fallback LLM response.")
        fallback_prompt = GENERAL_FALLBACK_PROMPT.format(question=question)
        fallback_answer = ""
        for attempt in range(2):
            try:
                raw = query_ollama(fallback_prompt, json_mode=False).strip()
                fallback_answer = clean_answer(raw)
                if fallback_answer:
                    break
                print(f"Fallback answer attempt {attempt + 1} returned empty, retrying...")
            except Exception as e:
                print(f"Fallback answer generation error (attempt {attempt + 1}): {e}")
                if attempt == 1:
                    fallback_answer = "I'm not sure about that one."

        combined = f"I don't know from the graph. {fallback_answer}" if fallback_answer else "I don't know from the graph."
        return {
            "answer": combined,
            "context": "",
            "has_context": False
        }

