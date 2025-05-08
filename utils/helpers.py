import os
import re
import hashlib
from urllib.parse import urlparse

def clean_url(url):
    """Clean and normalize a URL"""
    # Add http:// if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    # Ensure domain is lowercase
    parsed = urlparse(url)
    url = url.replace(parsed.netloc, parsed.netloc.lower())
    
    return url

def get_domain_from_url(url):
    """Extract domain from URL"""
    parsed = urlparse(clean_url(url))
    return parsed.netloc

def get_cache_path(key, subdir=None):
    """Get the path to a cache file"""
    # Create a hash of the key to use as filename
    hash_obj = hashlib.md5(key.encode())
    filename = hash_obj.hexdigest() + '.json'
    
    # Determine the cache directory
    cache_dir = os.path.join('data', 'cache')
    if subdir:
        cache_dir = os.path.join(cache_dir, subdir)
    
    # Create the directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)
    
    # Return the full path
    return os.path.join(cache_dir, filename)

def format_results(url, company_analysis, leads):
    """Format the final results for display and export"""
    domain = get_domain_from_url(url)
    
    # Ensure offerings is always a list
    offerings = company_analysis.get('offerings', [])
    if offerings is None:
        offerings = []
    elif isinstance(offerings, str):
        offerings = [offerings]
        
    # Ensure target_market is always a string
    target_market = company_analysis.get('target_market', 'Unknown')
    if isinstance(target_market, list):
        target_market = ', '.join(target_market)
    elif target_market is None:
        target_market = 'Unknown'
    
    # Create a structured result object
    result = {
        'url': url,
        'domain': domain,
        'company': {
            'name': company_analysis.get('name', domain),
            'type': company_analysis.get('company_type', 'Unknown'),
            'industry': company_analysis.get('industry', 'Unknown'),
            'size': company_analysis.get('company_size', 'Unknown'),
            'target_market': target_market,
            'offerings': offerings
        },
        'leads': []
    }
    
    # Format each lead
    for lead in leads:
        formatted_lead = {
            'name': lead.get('name', ''),
            'role': lead.get('role', ''),
            'email': lead.get('email', ''),
            'confidence_score': lead.get('confidence_score', 0),
            'outreach_suggestions': lead.get('outreach_suggestions', []),
            'lead_type': lead.get('lead_type', 'internal')
        }
        
        # Add company_name and target_reason for external leads
        if lead.get('lead_type') == 'external':
            formatted_lead['company_name'] = lead.get('company_name', '')
            formatted_lead['target_reason'] = lead.get('target_reason', '')
            
        result['leads'].append(formatted_lead)
    
    return result

def truncate_text(text, max_length=100):
    """Truncate text to a maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'

def extract_emails_from_text(text):
    """Extract email addresses from text"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)

def extract_phone_numbers(text):
    """Extract phone numbers from text"""
    # This is a simplified pattern - real implementation would be more complex
    phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    return re.findall(phone_pattern, text)

def is_valid_email(email):
    """Check if an email address is valid"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def sanitize_filename(filename):
    """Sanitize a filename to be safe for file systems"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename
