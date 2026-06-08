# GraphMind

GraphMind is a Graph RAG prototype that turns unstructured text into a knowledge graph and lets you ask questions against it. Text is processed with an LLM(via Ollama) to extract entities and relationships,stored in Neo4j, and queried through a simple Web UI.

## Features

- Build a graph from sample text, pasted content, or a PDF upload
- Chat with your knowledge graph and inspect retrieved context.
- Live Neo4j stats (node and relationship counts)

## Prerequisites

- **Python 3.10+**
- **Neo4j** running locally (default: `bolt://localhost:7687`)
- **Ollama** - local instance or Ollama Cloud with an API key
## Setup

1. Clone the repository and create a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate  
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

OLLAMA_URL=https://ollama.com/api/generate
MODEL_NAME=gpt-oss:120b-cloud
OLLAMA_API_KEY=your_api_key
```

## How to Run

1. Start Neo4j and confirm it is reachable.

2. Start the backend from the project root:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

3. Serve the frontend (in a second terminal):

```bash
cd frontend
python -m http.server 5500
```

4. Open [http://127.0.0.1:5500](http://127.0.0.1:5500) in your browser.


## Folder Structure

```
GraphMind/
├── backend/
│   ├── main.py         
│   ├── graph_build.py    
│   ├── query_graph.py    
│   ├── ollama_client.py  
│   └── prompts.py        
├── frontend/
│   ├── index.html     
│   ├── app.js            
│   └── style.css        
├── data/
│   └── sample.txt       
├── requirements.txt      
└── .env                 
```

## API Endpoints

| Method | Path               | Description                    |
|--------|--------------------|--------------------------------|
| GET    | `/health`          | Liveness check                 |
| GET    | `/health/ready`    | Neo4j connectivity check       |
| GET    | `/stats`           | Node and relationship counts   |
| POST   | `/build-graph`     | Build from `data/sample.txt`   |
| POST   | `/build-graph/text`| Build from pasted text         |
| POST   | `/build-graph/pdf` | Build from uploaded PDF        |
| POST   | `/chat`            | Ask a question                 |
