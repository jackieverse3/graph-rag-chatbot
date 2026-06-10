import json
import os
import re

from neo4j import GraphDatabase

from backend.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from backend.ollama_client import query_ollama
from backend.prompts import GRAPH_BUILD_PROMPT

def sanitize_relation(relation: str) -> str:
    """Formats relationship strings to be valid Cypher relationship types."""
    # Remove non-alphanumeric characters, spaces to underscores, uppercase
    cleaned = re.sub(r'[^a-zA-Z0-9\s_]', '', relation)
    cleaned = cleaned.strip().replace(' ', '_').upper()
    return cleaned if cleaned else "RELATED_TO"

def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 500) -> list:
    """Splits text into chunks of chunk_size with overlap."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
        # Stop if the next chunk would start beyond the end of the text
        if start >= len(text):
            break
    return chunks

def build_graph_from_text(text: str) -> bool:
    """Extracts relationships from a text string via LLM chunk by chunk, and inserts them into Neo4j."""
    if not text or not text.strip():
        print("Error: Empty text provided.")
        return False

    chunks = chunk_text(text)
    print(f"Split text into {len(chunks)} chunks for graph building.")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            # Clear previous nodes once before building a new graph
            session.run("MATCH (n) DETACH DELETE n")
            print("Database cleared. Extracting and writing relationships...")

            for i, chunk in enumerate(chunks):
                print(f"Processing chunk {i+1}/{len(chunks)}...")
                prompt = GRAPH_BUILD_PROMPT.format(text=chunk)
                try:
                    response_text = query_ollama(prompt, json_mode=True)
                except Exception as e:
                    print(f"LLM call failed for chunk {i+1}: {e}")
                    continue

                # Clean LLM response if it accidentally wrapped JSON in markdown formatting
                cleaned_response = response_text.strip()
                if cleaned_response.startswith("```"):
                    cleaned_response = re.sub(r'^```(?:json)?\n|```$', '', cleaned_response, flags=re.MULTILINE).strip()

                try:
                    triples = json.loads(cleaned_response)
                except Exception as e:
                    print(f"JSON Parsing failed for chunk {i+1}: {e}")
                    print(f"Raw Output was: {response_text}")
                    continue

                if not isinstance(triples, list):
                    print(f"Expected a list of triples for chunk {i+1}, got {type(triples)}")
                    continue

                for item in triples:
                    source = item.get("source")
                    relation = item.get("relation")
                    target = item.get("target")

                    if source and relation and target:
                        rel_type = sanitize_relation(relation)
                        query = f"""
                        MERGE (s:Entity {{name: $source}})
                        MERGE (t:Entity {{name: $target}})
                        MERGE (s)-[r:{rel_type}]->(t)
                        """
                        session.run(query, source=source, target=target)
        return True
    except Exception as e:
        print(f"Neo4j Write error: {e}")
        return False
    finally:
        driver.close()

def build_graph_from_file(file_path: str) -> bool:
    """Reads a file, extracts relationships via LLM, and inserts them into Neo4j."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    return build_graph_from_text(text)