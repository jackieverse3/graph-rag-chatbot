import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleaware
from pydantic import BaseModel
from neo4j import GraphDatabase
from backend.graph_builder import build_graph_from_file, build_graph_from_text
from backend.query_graph import answer_question, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import io 
from pypdf import PdfReader

def extract_text_from_pdf(pdf_bytes:bytes) -> str:
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    text= ""
    for page in reader.pages:
        page_text=page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


app = FastAPI(title = "GraphMind")

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

class TextInput(BaseModel):
    text: str

@app.post("/build-graph")
def build_graph():
    file_path = os.path.join("data", "sample.txt")
    if not os.path.exists(file_path)
        raise HTTPException(status_code = 404, detail = f"Data file not found at {file_path}") 

    with open(file_path,"r",encoding ="utf-8") as f:
        text= f.read()

    success = build_graph_from_file(file_path)   
    if success:
        return {
            "message":"Graph successfully built from default sample",
            "text":text
            }
    else:
        raise HTTPException(status_code=500, detail="Graph build failed from sample text.")     


@app.post("/build-graph/text")
def build_graph_text(payload: TextInput):
    if not payload.text.strip():
        raise HTTPException(status_code=400,detail="Text content cannot be empty")

    if len(payload.text) > 100000:
        raise HTTPException(status_code=400,detail="Text length exceeds the 100,000 characters limit.")

    success = build_graph_from_text(payload.text)
    if success:
        return {
            "message":"Graph successfully built from custom text",
            "text": payload.text
        }
    else:
        raise HTTPException(status_code:500,detail="Graph build from pasted text.")

@app.post("/build-graph/pdf")
async def build_graph_from_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read content to verify size (1 MB limit)
    content = await file.read()
    if len(content) > 1024*1024:
        raise HTTPException(status_code=400,detail = "File size exceeds the 1MB limit.")

    try:
        text = extract_text_from_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to parse PDF: {str(e)}")
    
    if not text.strip():
        raise HTTPException(status_code=400,detail="No readable text could be extracted from the PDF.")

    success = build_graph_from_text(text)
    if success:
        return {
            "message": "Graph successfully built from PDF content",
            "text":text
        }
    else:
        raise HTTPException(status_code=500,detail = "Graph build failed from PDF content.")

        

@app.post("/chat")
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty. ")

    # Calls our updated pipeline that returns answer & context.
    answer= answer_question(request.question)    
    return result 