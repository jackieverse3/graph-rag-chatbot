import json
import re

from neo4j import GraphDatabase
from backend.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from backend.ollama_client import query_ollama
from backend.prompts import ANSWER_GENERATOR_PROMPT, ENTITY_EXTRACT_PROMPT, GENERAL_FALLBACK_PROMPT


# Patterns that indicate leaked reasoning/thinking garbage from the model
_GARBAGE_PATTERNS = re.compile (
    r'^(We |Ok |analysis|Okay|The query|Let\'s|I think|Wait|Hmm|Actually|So |But |If |In |By |With )',
    re.IGNORECASE
)

_CONTROL_TOKEN = re.compile(r'<\|[^|]+\|>')

def clean_answer(raw: str) -> str:
    """Strip reasoning-model leakage and return the first clean answer sentence."""
    if not raw:
        return raw

    raw=_CONTROL_TOKEN.sub('',raw)

    lines = [l.strip() for l in raw.split('\n') if l.strip()]

    good_lines = []
    for line in lines:
        if _GARBAGE_PATTERNS.match(line):
            if good_lines:
                break
            continue
        if len(line)<5:
            continue
        good_lines.append(line)

        if len(good_lines)>=2:
            break

    result = ' '.join(good_lines).strip()

    if not result and lines:
        result=lines[0]
    return result

def _fallback_extract(question: str) -> list:
    matches = re.findall(r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b', question)

    stopwords = {"Who","What","Where","When","Why","How","Which","Is","Are".
    "Did","Does","Do","Was","Were","Has","Have","Can"}

    results=[m for m in matches if m not in stopwords]
    print(f"Fallback entity extraction from question: {results}")
    return results


def extract_entities(question: str) -> list:
    """Uses LLM to extract entity name mentioned in the user's question."""
    prompt = ENTITY_EXTRACT_PROMPT.format(question=question)
    response_text= query_ollama(prompt,json_mode= True)

    cleaned_response= response_text.strip()
    if cleaned_response.startswith("```"):
        cleaned_response= re.sub(r'^```(?:json)?\n|```$','',
        cleaned_response, flags=re.MULTILINE).strip()

    try:
        entities = json.loads(cleaned_response)    
        if isinstance(entities, list) and entities:
            return [str(e).strip() for e in entities if e]
    except Exception as e:
        print (f"Failed to parse entities list: {e}")
        print (f"Raw entity response: {response_text}")

        print(f"LLM returned no entities, using fallback extractor.")
        return _fallback_extract(question)


def get_graph_context(entities: list) -> str:
    """Queries Neo4j for matching facts regarding specific entities."""
    if not entities:
        return ""

    driver = GraphDatabase.driver(NEO4J_URI,auth = (NEO4J_USER,NEO4J_PASSWORD))   
    seen = set()
    facts = [] 

    def add_fact(source, relation , target):
        key = (source, relation, target)
        if key not in seen:
            seen.add(key)
            facts.append(f"{source} -[{relation}]-> {target}")

    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            for entity in entities:
                
                result = session.run (""" 
                MATCH (a:Entity)-[r]->(b:Entity)
                WHERE toLower(a.name) = toLower($entity)
                 OR toLower(b.name) = toLower($entity)
                RETURN a.name AS source, type(r) AS relation, b.name AS target """,
                entity=entity)

                direct_neighbors = set()
                for record in result:
                    add_fact(record["source"],record["relation"],record["target"])

                    direct_neighbors.add(record["source"])
                    direct_neighbors.add(record["target"])

                for neighbor in direct_neighbors:
                    if neighbor.lower() == entity.lower():
                        continue
                    hop_result = session.run ("""
                       MATCH (a:Entity)-[r]->(b:Entity)
                       WHERE toLower(a.name) = toLower($entity)
                       RETURN a.name AS source, type(r) AS relation, b.name AS target 
                       """, neighbor=neighbor)
                    for record in hop_result:
                        add_fact(record["source"],record["relation"],record["target"])
    except Exception as e:
        print(f"Neo4j Read error: {e}")
    finally:
        driver.close()    

    return "\n".join(facts)    

def answer_questions(question: str)->dict:
    """Main Graph RAG pipeline execution. Returns both the answer and the 
    retrieved context. """

    entities = extract_entities (question)
    print(f"Extracted entities: {entities}")

    context = get_graph_context(entities)
    print(f"Graph context ({len(context.splitlines())} facts:\n{context}")

    has_context = bool(context and context.strip()
    
    if has_context:
        
    prompt = ANSWER_GENERATOR_PROMPT.format(context=context,question=question)
    answer = ""

    for attempt in range(2):
        try:
            raw = query_ollama(prompt, json_mode=False).strip()
            answer= clean_answer(raw)
            if answer:
                break
            print(f"Answer attempt {attempt + 1} returned empty after cleaning, returning ...")
        except Exception as e:
            print(f"Answer generation error (attempt {attempt + 1}): {e}")
            if attempt == 1:
                answer= "I encountered an error generating a response.Please try again."
    return {
        "answer": answer or "I was unable to generate a response. Please try again.",
        "context" : context,
        "has_context": True
    }
    
else:
    print("no graph context found.Using general fallback LLM response.")
    fallback_prompt = GENERAL_FALLBACK_PROMPT.format(question=question)
    fallback_answer = ""
    for attemmpt in range(2):
        try:
            raw = query_ollama(fallback_prompt, json_mode=False).strip()
            fallback_answer=clean_answer(raw)
            if fallback_answer:
                break
            print(f"Fallback answer attempt {attempt + 1} returned empty, retrying ...")
        except Exception as e:
            print(f"Fallback answer generation error (attempt {attempt +1}): {e}")
            if attemmpt == 1:
                fallback_answer = "I'm not sure about that one."
        combined = f"I don't know from the graph. {fallback_answer}" if fallback_answer else "I don't know from the graph."
        return {
            "answer":combined,
            "context":"",
            "has_context":False
        }