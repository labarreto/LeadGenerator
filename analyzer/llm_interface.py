"""
Interface for querying local LLMs using Ollama
"""
import os
import json
import requests
import time

# Simple function to load environment variables from .env file
def load_env_from_file():
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"\'')
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")

# Load environment variables
load_env_from_file()

# Get LLM configuration from environment variables
USE_LOCAL_LLM = os.getenv('USE_LOCAL_LLM', 'True').lower() == 'true'
LLM_MODEL = os.getenv('LLM_MODEL', 'phi3')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

def query_ollama(prompt, model=None, temperature=0.7, max_retries=3, retry_delay=2):
    """
    Query Ollama LLM with the given prompt
    
    Args:
        prompt (str): The prompt to send to the LLM
        model (str, optional): The model to use. Defaults to the LLM_MODEL env var.
        temperature (float, optional): Sampling temperature. Defaults to 0.7.
        max_retries (int, optional): Maximum number of retries. Defaults to 3.
        retry_delay (int, optional): Delay between retries in seconds. Defaults to 2.
        
    Returns:
        str: The LLM response text
    """
    if not USE_LOCAL_LLM:
        print("Local LLM is disabled. Using fallback methods.")
        return "Local LLM is disabled"
    
    # Use the specified model or fall back to the default
    model_name = model or LLM_MODEL
    
    # Prepare the request payload
    payload = {
        "model": model_name,
        "prompt": prompt,
        "temperature": temperature,
        "stream": False
    }
    
    # Endpoint for Ollama API
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    # Try to query the LLM with retries
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                print(f"Error querying Ollama (Attempt {attempt+1}/{max_retries}): Status {response.status_code}")
                time.sleep(retry_delay)
        except Exception as e:
            print(f"Exception querying Ollama (Attempt {attempt+1}/{max_retries}): {str(e)}")
            time.sleep(retry_delay)
    
    # If all retries failed, return a fallback response
    return "Failed to get response from LLM"

def extract_json_from_response(response_text):
    """
    Extract JSON from an LLM response that might contain additional text
    
    Args:
        response_text (str): The raw response from the LLM
        
    Returns:
        dict: The extracted JSON object or None if extraction failed
    """
    try:
        # Try to parse the entire response as JSON first
        return json.loads(response_text)
    except json.JSONDecodeError:
        # If that fails, try to extract JSON from the response
        try:
            # Look for JSON object in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            
            # Look for JSON array in the response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            
        except (json.JSONDecodeError, ValueError):
            pass
    
    # If all extraction attempts fail, return None
    return None
