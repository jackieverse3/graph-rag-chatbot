import requests

# Default endpoint for local
OLLAMA_URL = "http://localhost:11434/api/generate"

#Adjust model name to match whatever you pulled locally
MODEL_NAME = "llama3"

def query_ollama (prompt:str,json_mode: bool = False) ->str:
    payload = {
        "model:"MODEL_NAME,
        "prompt:"prompt,
        "stream": False
    }

    if json_mode:
        payload["format"]="json"

    try:
        response = requests.post(OLLAMA_URL,json=payload,timeout=60)
        response.raise_for_status()
        return response.json().get("response", "")

    except Exception as e:
        print(f"Error calling Ollama:{e}")
        return ""    
