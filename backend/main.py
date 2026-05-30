import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleaware
from pydantic import BaseModel
from backend.graph_builder import build_graph_from_file
from backend.query_graph import answer_question

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

    answer= answer_question(request.question)    
    return {"answer": answer}