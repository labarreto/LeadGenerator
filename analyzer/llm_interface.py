"""
Interface for querying LLMs using OpenAI API
"""
import os
import json
import requests
import time
from openai import OpenAI

# Simple function to load environment variables from .env file
def load_env_from_file():
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")

# Try to load environment variables from .env file if not already set
if 'OPENAI_API_KEY' not in os.environ:
    load_env_from_file()

# Get LLM configuration from environment variables
USE_LOCAL_LLM = os.getenv('USE_LOCAL_LLM', 'False').lower() == 'true'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-nano')

# Initialize OpenAI client
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize OpenAI client: {e}")

def query_llm(prompt, model=None, temperature=0.7, max_retries=3, retry_delay=2):
    """
    Query LLM with the given prompt
    
    Args:
        prompt (str): The prompt to send to the LLM
        model (str, optional): The model to use. Defaults to the OPENAI_MODEL env var.
        temperature (float, optional): Sampling temperature. Defaults to 0.7.
        max_retries (int, optional): Maximum number of retries. Defaults to 3.
        retry_delay (int, optional): Delay between retries in seconds. Defaults to 2.
        
    Returns:
        str: The LLM response text
    """
    # Use the specified model or fall back to the default
    model_name = model or OPENAI_MODEL
    
    print(f"\n[DEBUG] Querying OpenAI with model: {model_name}")
    print(f"[DEBUG] Prompt length: {len(prompt)} characters")
    
    if not OPENAI_API_KEY:
        print("OpenAI API key is not set. Using fallback methods.")
        return "OpenAI API key is not set"
    
    if client is None:
        print("OpenAI client is not initialized. Using fallback methods.")
        return "OpenAI client is not initialized"
    
    # Try to query the LLM with retries
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Attempt {attempt+1}/{max_retries} to query OpenAI")
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides concise, accurate information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=1000
            )
            
            print(f"[DEBUG] Successfully received response from OpenAI")
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[DEBUG] Exception querying OpenAI (Attempt {attempt+1}/{max_retries}): {str(e)}")
            print(f"[DEBUG] Exception type: {type(e).__name__}")
            time.sleep(retry_delay)
    
    # If all retries failed, return a fallback response
    print("[DEBUG] All attempts to query OpenAI failed. Using fallback response.")
    return "Failed to get response from LLM"


# Legacy function name for backward compatibility
def query_ollama(prompt, model=None, temperature=0.7, max_retries=3, retry_delay=2):
    """
    Legacy function that now redirects to query_llm
    """
    return query_llm(prompt, model, temperature, max_retries, retry_delay)

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
