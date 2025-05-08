import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
import os
import json
import time
from datetime import datetime

# Import utility functions
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import clean_url, get_cache_path

class WebsiteScraper:
    """Class to handle website scraping operations"""
    
    def __init__(self, use_cache=True, cache_expiry=86400):
        """Initialize the scraper with caching options"""
        self.use_cache = use_cache
        self.cache_expiry = cache_expiry  # Default: 24 hours
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def scrape_website(self, url):
        """Main method to scrape a website and extract relevant content"""
        # Clean and validate URL
        url = clean_url(url)
        domain = urlparse(url).netloc
        
        # Check cache first if enabled
        if self.use_cache:
            cached_data = self._check_cache(url)
            if cached_data:
                print(f"Using cached data for {url}")
                return cached_data
        
        # Fetch main page
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch website: {str(e)}")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Extract basic company info
        company_data = {
            'url': url,
            'domain': domain,
            'name': self._extract_company_name(soup, domain),
            'title': self._extract_title(soup),
            'description': self._extract_meta_description(soup),
            'main_content': self._extract_main_content(soup),
            'timestamp': datetime.now().isoformat(),
            'important_pages': {}
        }
        
        # Get important pages to scrape
        important_pages = self._get_important_pages(soup, url, domain)
        
        # Scrape important pages
        for page_type, page_url in important_pages.items():
            try:
                page_data = self._scrape_page(page_url)
                company_data['important_pages'][page_type] = page_data
            except Exception as e:
                print(f"Error scraping {page_type} page: {str(e)}")
                company_data['important_pages'][page_type] = {'error': str(e)}
        
        # Cache the results if enabled
        if self.use_cache:
            self._cache_results(url, company_data)
        
        return company_data
    
    def _check_cache(self, url):
        """Check if we have a valid cache for this URL"""
        cache_path = get_cache_path(url)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache is expired
            timestamp = datetime.fromisoformat(cached_data.get('timestamp', '2000-01-01'))
            now = datetime.now()
            
            if (now - timestamp).total_seconds() > self.cache_expiry:
                print(f"Cache expired for {url}")
                return None
                
            return cached_data
        except Exception as e:
            print(f"Error reading cache: {str(e)}")
            return None
    
    def _cache_results(self, url, data):
        """Save results to cache"""
        cache_path = get_cache_path(url)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing to cache: {str(e)}")
    
    def _extract_company_name(self, soup, domain):
        """Extract company name from the website"""
        # Try several methods to find the company name
        
        # Method 1: Look for logo alt text
        logo = soup.find('img', {'alt': re.compile(r'logo', re.I)})
        if logo and logo.get('alt') and len(logo.get('alt').split()) <= 5:
            return logo.get('alt').strip()
        
        # Method 2: Look for the title tag
        if soup.title:
            title = soup.title.text.strip()
            # Remove common suffixes like "Home | Company" or "Company - Home"
            title = re.sub(r'\s*[|:–—-]\s*.*$', '', title)
            title = re.sub(r'^.*\s*[|:–—-]\s*', '', title)
            
            if len(title.split()) <= 5:  # Likely a company name if short
                return title
        
        # Method 3: Use the domain name as fallback
        domain_parts = domain.split('.')
        if len(domain_parts) > 1:
            return domain_parts[0].capitalize()
        
        return domain
    
    def _extract_title(self, soup):
        """Extract page title"""
        if soup.title:
            return soup.title.text.strip()
        return ""
    
    def _extract_meta_description(self, soup):
        """Extract meta description"""
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content').strip()
        
        # Try Open Graph description as fallback
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc.get('content').strip()
            
        return ""
    
    def _extract_main_content(self, soup):
        """Extract the main content from the page"""
        # Remove script, style, and nav elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'form']):
            element.decompose()
        
        # Try to find main content area
        main_content = ""
        
        # Method 1: Look for main tag
        main_tag = soup.find('main')
        if main_tag:
            main_content = main_tag.get_text(separator=' ', strip=True)
        
        # Method 2: Look for common content div IDs
        if not main_content:
            for content_id in ['content', 'main', 'main-content', 'mainContent']:
                content_div = soup.find('div', {'id': content_id})
                if content_div:
                    main_content = content_div.get_text(separator=' ', strip=True)
                    break
        
        # Method 3: Use the body as fallback
        if not main_content and soup.body:
            main_content = soup.body.get_text(separator=' ', strip=True)
        
        # Clean up the text
        main_content = re.sub(r'\s+', ' ', main_content).strip()
        return main_content
    
    def _get_important_pages(self, soup, base_url, domain):
        """Identify important pages to scrape"""
        important_pages = {}
        
        # Common page patterns to look for
        page_patterns = {
            'about': [r'/about', r'about-us', r'company', r'who-we-are'],
            'team': [r'/team', r'our-team', r'leadership', r'management', r'people'],
            'services': [r'/services', r'solutions', r'products', r'what-we-do'],
            'contact': [r'/contact', r'contact-us', r'get-in-touch'],
            'clients': [r'/clients', r'customers', r'case-studies', r'success-stories']
        }
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href')
            
            # Make sure it's an absolute URL
            if not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
            
            # Skip external links
            if domain not in urlparse(href).netloc:
                continue
            
            # Check if it matches any important page pattern
            for page_type, patterns in page_patterns.items():
                if page_type not in important_pages:  # Only keep the first match
                    for pattern in patterns:
                        if re.search(pattern, href, re.I):
                            important_pages[page_type] = href
                            break
        
        return important_pages
    
    def _scrape_page(self, url):
        """Scrape a specific page and extract its content"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract content
            page_data = {
                'url': url,
                'title': self._extract_title(soup),
                'content': self._extract_main_content(soup)
            }
            
            return page_data
        except Exception as e:
            raise Exception(f"Failed to scrape page {url}: {str(e)}")

# Function to be imported by other modules
def scrape_website(url, use_cache=True):
    """Scrape a website and return structured data"""
    scraper = WebsiteScraper(use_cache=use_cache)
    return scraper.scrape_website(url)

# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = "https://www.example.com"
    
    result = scrape_website(test_url)
    print(json.dumps(result, indent=2))
