import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Cloud or local endpoint
OLLAMA_URL = os.getenv("OLLAMA_URL","https://ollama.com/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME","gpt-oss:120b-cloud")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY","")

def query_ollama (prompt:str,json_mode: bool = False,think: bool = False) ->str:
""" 
Sends a request to the Ollama instance and returns the generated text.

Args:
     prompt: The prompt to send.
     json_mode: If True, instructs the model to return valid JSON.
     think: If False(default), suppresses chain-of-thought for reasoning models so 
     that the 'response' failed is never empty.
     """
    headers = {"Content-type": "application/json"}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer{OLLAMA_API_KEY}"

    payload = {
        "model:"MODEL_NAME,
        "prompt:"prompt,
        "stream": False
    }

    if json_mode:
        payload["format"]="json"

    if not think:
        payload["think"]=False

    try:
        response = requests.post(OLLAMA_URL,header=header,json=payload,timeout=300)
        if not response.ok:
            print(f"Ollama API error - HTTP {response.status_code}:{response.text[:500]}")
        response.raise_for_status()
        return response.json()

        text = result.get("response","").strip()
        
        if not text and result.get("thinking"):
            thinking = result["thinking"].strip()
            lines=[l.strip() for l in thinking.split("\n") if l.strip()]
            text = lines[-1] if lines else ""
            if text:
                print("Warning: used 'thinking' fallback to extract answer.")
            return text 
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Eror calling Ollama: {e}")
        raise
    except Exception as e:
        print(f"Error calling Ollama:{e}")
        raise
