import os 
import json
import re 
from neo4j import GraphDatabase
from backend.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from backend.ollama_client import query_ollama
from backend.prompts import GRAPH_BUILD_PROMPT

def sanitize_relation(relation: str)-> str:
    """ Formats relationship strings to be valid Cypher relationship types."""
    cleaned = re.sub(r'[^a-zA-Z0-9\s_]','',relation) 
    cleaned = cleaned.strip().replace(' ','_').upper()
    return cleaned if cleaned else "RELATED_TO"

def build_graph_from_text(text: str)-> bool:
    """ Extracts relationships from a text string via LLM, and inserts them into Neo4j."""
    if not text or not text.strip():
        print("Error: Empty text provided.")
        return False


    # Get data from LLM
    prompt = GRAPH_BUILD_PROMPT.format(text=text)
        response_text = query_ollama(prompt, json_mode= True )

    try:
        response_text = query_ollama(prompt, json_mode=True)
    except Exception as e:
        print(f"LLm call failed during graph build: {e}")
        return False

    # Clean LLM response if it accidentally wrapped JSON in markdown formatting
    cleaned_response = response_text.strip()
        if cleaned_response.startswith("```"):
            cleaned_response = re.sub(r'^```(?:json)?\n|```$', '',
    cleaned_response, flags=re.MULTILINE).strip()  


    try:
        tripled = json.loads(cleaned_response)
    except Exception as e :
        print(f"JSON Parsing failed: {e}")  
        print(f"Raw Ouput was: {response_text}")
        return False

        # Insert into database
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER,NEO4J_PASSWORD))    

    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            # For this MVP, we clear previous nodes before writing a new graph
            session.run("MATCH (n) DETACH DELETE n")
            print("Database cleared. Writing new relationships...")

            for item in triples:
                source = item.get("source")   
                relation = item.get("relation") 
                target = item.get ("target")

                if source and relation and target:
                    rel_type = sanitize_relation(relation)    
                    query = f"""
                    MERGE (s:Entity {{name: $source}})
                    MERGE (t:Entity {{name: $target}})
                    MERGE (s)-[r:{rel_type}]->(t)
                    """
                    session.run(query, source=source,target=target)

        return True
    except Exception as e:
        print(f"Neo4j Write error: {e}") 
        return False
    finally:
        driver.close()       


def build_graph_from_file(file_path: str) -> bool;
    """ Reads a file, extracts relationships via LLM, and inserts them into Neo4j."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        text=f.read()

    return build_graph_from_text(text)


