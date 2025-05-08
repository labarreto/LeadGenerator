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

# Clear cache for testing new features
def clear_cache():
    """Clear the cache directories to test new features"""
    try:
        cache_dirs = ['data/cache/analysis', 'data/cache/leads', 'data/cache/scrape']
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                for cache_file in os.listdir(cache_dir):
                    os.remove(os.path.join(cache_dir, cache_file))
                print(f"Cleared cache in {cache_dir}")
    except Exception as e:
        print(f"Error clearing cache: {e}")

# Clear cache when app starts in debug mode
if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1':
    clear_cache()

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process a website URL and generate leads"""
    url = request.form.get('url', '')
    force_refresh = request.form.get('force_refresh', 'false').lower() == 'true'
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # Clean and validate the URL
    url = clean_url(url)
    
    try:
        # Set environment variables for testing
        os.environ['USE_LOCAL_LLM'] = 'True'
        os.environ['FIND_EXTERNAL_LEADS'] = 'True'
        
        # Step 1: Scrape the website (force refresh if requested)
        website_data = scrape_website(url, use_cache=not force_refresh)
        
        # Step 2: Analyze the company (force refresh if requested)
        company_analysis = analyze_company(website_data, use_cache=not force_refresh)
        
        # Step 3: Generate leads (force refresh if requested)
        leads = generate_leads(company_analysis, url, use_cache=not force_refresh)
        
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
