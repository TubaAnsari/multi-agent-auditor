import requests
import json
import time

def query_ollama(prompt, model="qwen2.5-coder:7b", max_retries=2):
    """Query Ollama with better timeout handling and retries"""
    
    # Truncate extremely long prompts (over 15,000 chars)
    if len(prompt) > 15000:
        prompt = prompt[:15000] + "\n... [truncated due to length]"
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 2048,  # Limit response length
                        "temperature": 0.7
                    }
                },
                timeout=180  # Increase to 180 seconds
            )
            
            if response.status_code == 200:
                return response.json()["response"]
            else:
                return f"Error: Ollama returned status {response.status_code}"
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"Timeout, retrying... (attempt {attempt + 2}/{max_retries})")
                time.sleep(2)
                continue
            return "Error: Ollama timeout - the file might be too large. Try a smaller file."
        except Exception as e:
            return f"Error: {str(e)}"
    
    return "Error: Max retries exceeded"

if __name__ == "__main__":
    test = query_ollama("Say 'Ollama is working!'")
    print(test)