from flask import Flask, render_template, request, jsonify, session
import os
from datetime import datetime
import json

# Import project modules
from scraper.website_scraper import scrape_website
from analyzer.content_analyzer import analyze_company
from lead_finder.lead_generator import generate_leads
from utils.helpers import clean_url, format_results

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['SESSION_TYPE'] = 'filesystem'

# Create necessary directories if they don't exist
os.makedirs('data/results', exist_ok=True)
os.makedirs('data/cache', exist_ok=True)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process a website URL and generate leads"""
    url = request.form.get('url', '')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # Clean and validate the URL
    url = clean_url(url)
    
    try:
        # Step 1: Scrape the website
        website_data = scrape_website(url)
        
        # Step 2: Analyze the company
        company_analysis = analyze_company(website_data)
        
        # Step 3: Generate leads
        leads = generate_leads(company_analysis, url)
        
        # Format the results
        results = format_results(url, company_analysis, leads)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/results/{url.replace('https://', '').replace('http://', '').split('/')[0]}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Store in session for retrieval
        session['last_result'] = filename
        
        return jsonify({
            'success': True,
            'company': company_analysis,
            'leads': leads,
            'result_file': filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def results():
    """View the last analysis results"""
    result_file = session.get('last_result')
    
    if not result_file or not os.path.exists(result_file):
        return render_template('results.html', error="No results found")
    
    with open(result_file, 'r') as f:
        results = json.load(f)
    
    return render_template('results.html', results=results)

@app.route('/export/<format>')
def export_results(format):
    """Export results in various formats"""
    result_file = session.get('last_result')
    
    if not result_file or not os.path.exists(result_file):
        return jsonify({'error': 'No results found'}), 404
    
    with open(result_file, 'r') as f:
        results = json.load(f)
    
    if format == 'json':
        return jsonify(results)
    elif format == 'csv':
        # Implementation for CSV export
        # This would be implemented in a real application
        return jsonify({'error': 'CSV export not implemented yet'}), 501
    else:
        return jsonify({'error': 'Unsupported export format'}), 400

if __name__ == '__main__':
    app.run(debug=True)
