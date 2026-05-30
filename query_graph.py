import json
import re
from neo4j import GraphDatabase
from backend.ollama_client import query_ollama
from backend.prompts import ENTITY_EXTRACT_PROMPT, ANSWER_GENERATOR_PROMPT

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

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
        if isinstance(entities, list):
            return entities
    except Exception as e:
        print (f"Failed to parse entities list: {e}")
    return []    

def get_graph_context(entities: list) -> str:
    """Queries Neo4j for matching facts regarding specific entities."""
    if not entities:
        return ""

    driver = GraphDatabase.driver(NEO4J_URI,NEO4J_PASSWORD)   
    facts = [] 

    try:
        with driver.session() as session:
            for entity in entities:
                # Perform a case-insensitive check to retrieve adjacent entities

                query = """
                MATCH (e:Entity)-[r]->(n:Entity)
                WHERE toLower(e.name) = toLower($entity)
                RETURN e.name AS source, type(r) AS relation, n.name AS target """

                result = session.run(query, entity=entity)
                for record in result:
                    facts.append(f"{record['source']} {record['relation']}
                    {record['target']}")
    except Exception as e:
        print(f"Neo4j Read error: {e}")
    finally:
        driver.close()    

    return "\n".join(facts)    

def answer_questions(question: str)-> str:   
    """Main Graph RAG pipeline execution."""

    # Step 1 : Find entities in user query
    entities = extract_entities(question) 
    print(f"Extracted Entities: {entities}")

    # Step 2 : Grab context path from Neo4j
    context = get_graph_context(entities)
    print(f"Retrieved Graph Context:\n{context}\n")

    # Step 3 : Run generated facts through generator LLM
    prompt = ANSWER_GENERATOR_PROMPT.format(context=context, question= question)
    answer= query_ollama(prompt,json_mode=False)
    return answer.strip()





