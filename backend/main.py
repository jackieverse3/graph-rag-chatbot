import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleaware
from pydantic import BaseModel
from neo4j import GraphDatabase
from backend.graph_builder import build_graph_from_file
from backend.query_graph import answer_question, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

app = FastAPI(title = "Graph RAG Chatbot Prototype")

app.add_middleware(
    CORSMiddleaware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question:str

@app.get("/stats")
def get_stats():
    """ Queries Neo4j to count current nodes and relationship. """
    driver = GraphDatabase.driver (NEO4J_URI, auth=(NEO4J_USER,NEO4J_PASSWORD))

    try:
        with driver.session() as session:
            nodes_res = session.run("MATCH (n:Entity) RETURN count(n) as count")

            nodes_count = nodes_res.single()["count"]

            rels_res = session.run ("MATCH ()-[r]->() RETURN count(r) as count")
            rels_count= rels_res.single()["count"]

            return {"nodes": nodes_count, "relationships": rels_count}
    except Exception as e:
        return {"nodes":0, "relationships":0, "error":str(e)}   
    finally:
        driver.close()


@app.post("/build-graph")
def build_graph():
    file_path = os.path.join("data", "sample.txt")
    if not os.path.exists(file_path)
        raise HTTPException(status_code = 404, detail = f"Data file not found at {file_path}") 

    success = build_graph_from_file(file_path)   
    if success:
        return {"message":"Graph successfully built in Neo4j"}
    else:
        raise HTTPException(status_code=500, detail="Failed to parse text or write to Neo4j.")     

@app.post("/chat")
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty. ")

    # Calls our updated pipeline that returns answer & context.
    answer= answer_question(request.question)    
    return result 