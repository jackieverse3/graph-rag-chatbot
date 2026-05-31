```markdown
# Graph RAG Chatbot (Prototype)

This is a minimal Graph Retrieval-Augmented Generation (Graph RAG) prototype that extracts structured entity relationships from a text document using a local LLM, stores them in Neo4j, and queries them to answer user questions.

---

## 1. Prerequisites

Before running the application, make sure the following local engines are installed and running:

1. **Ollama**:
   * Install from [ollama.com](https://ollama.com).
   * Ensure it is running in your taskbar/menu bar.
   * Pull the default model from your terminal:
     ```bash
     ollama pull llama3
     ```

2. **Neo4j**:
   * Install [Neo4j Desktop](https://neo4j.com/download/) or run Neo4j via Docker.
   * Create a local DBMS instance.
   * Set the password to `password` (or match the configuration password inside the Python files).
   * Start the database and ensure the connection matches standard Bolt port: `bolt://localhost:7687`.

---

## 2. Python Backend Setup

Configure a virtual environment, install the library packages, and launch your API:

1. **Create and Activate Virtual Environment**:
   * **On Windows**:
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   * **On macOS/Linux**:
     ```bash
     python -m venv venv
     source venv/bin/activate
     ```

2. **Install Package Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the FastAPI Server**:
   ```bash
   uvicorn backend.main:app --reload
   ```
   *The server is active when your terminal logs point to `http://127.0.0.1:8000`.*

---

## 3. Frontend Setup

1. Open your system's file manager and navigate to the `graph-rag-chatbot/frontend/` folder.
2. Double-click `index.html` to open it in your web browser. 
3. *Alternatively*, if using Visual Studio Code, right-click `index.html` and choose **Open with Live Server**.

---

## 4. How to Use

1. **Build Graph**: Click the **Build Knowledge Graph** button in the sidebar. This reads `data/sample.txt`, runs LLM extraction, wipes old database records, and populates your Neo4j instance.
2. **Review Metrics**: Verify that the sidebar metrics update to reflect your node and relationship counts.
3. **Query Terminal**: Type a question (e.g., *"What operating system competes with iOS?"*) into the text box and press **Ask Terminal** to view the response, query latency, and visual path trace.
```
