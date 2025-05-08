"""
Lead Generator - Google Colab Setup Script

This script contains the code needed to set up and run the Lead Generator project in Google Colab.
Copy and paste the sections below into Colab cells as needed.

INSTRUCTIONS:
1. Upload the entire LeadGenerator folder to your Google Drive
2. Create a new Google Colab notebook
3. Copy the sections below into separate cells in your notebook
4. Run the cells in order
"""

# Cell 1: Mount Google Drive
"""
# Mount Google Drive to access the project files
from google.colab import drive
drive.mount('/content/drive')

# Set the path to your project directory
import os
project_path = '/content/drive/MyDrive/LeadGenerator'  # Update this path as needed
os.chdir(project_path)
print(f"Working directory set to: {os.getcwd()}")
"""

# Cell 2: Install dependencies
"""
# Install required packages
!pip install -r requirements.txt

# Install Ollama (if you want to use it locally)
# Note: This won't work in Colab as it requires system-level installation
# Instead, we'll use API-based LLMs or the Colab GPU directly

# Install additional Colab-specific packages
!pip install flask-ngrok  # For exposing Flask to the internet
"""

# Cell 3: Set up environment variables
"""
# Set up environment variables
import os

# Configure to use API-based LLM instead of Ollama
os.environ['USE_LOCAL_LLM'] = 'False'

# If you have API keys for external LLM services, set them here
# os.environ['OPENAI_API_KEY'] = 'your_openai_key'  # Uncomment and add your key if using OpenAI
# os.environ['COHERE_API_KEY'] = 'your_cohere_key'  # Uncomment and add your key if using Cohere

# Or use Hugging Face's pipeline with Colab's GPU
os.environ['USE_HUGGINGFACE'] = 'True'
"""

# Cell 4: Create a direct interface to Hugging Face models (since Ollama won't work in Colab)
"""
# Add a Hugging Face integration for Colab
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

# Function to initialize the model (run this once)
def initialize_hf_model():
    print("Initializing Hugging Face model...")
    
    # Check if GPU is available
    device = 0 if torch.cuda.is_available() else -1
    print(f"Using device: {'GPU' if device == 0 else 'CPU'}")
    
    # Load a smaller model suitable for Colab's resources
    # Options: 'google/flan-t5-base', 'facebook/opt-1.3b', 'EleutherAI/pythia-1.4b'
    model_name = "google/flan-t5-base"  # This is a good balance of size and capability
    
    # Create the pipeline
    generator = pipeline(
        "text2text-generation",
        model=model_name,
        device=device
    )
    
    return generator

# Create a function that mimics the Ollama interface
class HuggingFaceInterface:
    def __init__(self):
        self.generator = initialize_hf_model()
    
    def generate(self, model=None, prompt=None, options=None):
        # Process the prompt
        max_length = 1024
        if options and 'num_predict' in options:
            max_length = options['num_predict']
        
        # Generate text
        response = self.generator(
            prompt,
            max_length=max_length,
            do_sample=True,
            temperature=0.7,
        )
        
        # Format response to match Ollama's format
        return {
            'response': response[0]['generated_text'],
            'model': model or 'huggingface'
        }

# Create the interface
hf_interface = HuggingFaceInterface()

# Monkey patch the import system to provide a fake 'ollama' module
import sys
class OllamaModule:
    @staticmethod
    def generate(**kwargs):
        return hf_interface.generate(**kwargs)

# Create a fake ollama module
sys.modules['ollama'] = OllamaModule
"""

# Cell 5: Run the Flask app with ngrok to expose it to the internet
"""
# Run the Flask app with ngrok
from flask_ngrok import run_with_ngrok
from app import app

# Enable ngrok
run_with_ngrok(app)

# Run the app
app.run()
"""

# Cell 6: Alternative - Run without a web interface (for testing)
"""
# Test the lead generation pipeline directly without the web interface
from scraper.website_scraper import scrape_website
from analyzer.content_analyzer import analyze_company
from lead_finder.lead_generator import generate_leads
from utils.helpers import format_results

# Test URL
test_url = "https://www.example.com"  # Replace with a real website

# Run the pipeline
print(f"Scraping website: {test_url}")
website_data = scrape_website(test_url)

print("Analyzing company...")
company_analysis = analyze_company(website_data)

print("Generating leads...")
domain = website_data['domain']
leads = generate_leads(company_analysis, domain)

# Format results
results = format_results(test_url, company_analysis, leads)

# Display results
import json
print(json.dumps(results, indent=2))
"""

# Additional notes for Colab users
"""
IMPORTANT NOTES FOR GOOGLE COLAB:

1. Runtime Limitations:
   - Colab sessions have time limits (usually disconnecting after 90 minutes of inactivity)
   - For larger websites, consider implementing checkpointing to save progress

2. Memory Management:
   - Monitor memory usage with: !nvidia-smi
   - If you encounter memory issues, reduce batch sizes or model size

3. Storage:
   - Results are stored in the Colab VM by default and will be lost when the session ends
   - Save important results to Google Drive:
     ```python
     # Save results to Google Drive
     results_path = '/content/drive/MyDrive/LeadGenerator/results/'
     os.makedirs(results_path, exist_ok=True)
     with open(f"{results_path}/results_{domain}.json", 'w') as f:
         json.dump(results, f, indent=2)
     ```

4. Security:
   - Never share your API keys in the notebook
   - Use environment variables or secrets management
   - Be careful when exposing your app with ngrok - it's publicly accessible
"""
