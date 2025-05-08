import os
import json
import re
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import get_cache_path

# Import LLM modules
try:
    import ollama
except ImportError:
    ollama = None

class ContentAnalyzer:
    """Class to analyze website content and extract company information using LLMs"""
    
    def __init__(self, use_local_llm=True, model_name="phi3", use_cache=True, cache_expiry=86400):
        """Initialize the content analyzer with LLM options"""
        self.use_local_llm = use_local_llm
        self.model_name = model_name
        self.use_cache = use_cache
        self.cache_expiry = cache_expiry
        
        # Check if we can use the local LLM
        if self.use_local_llm and ollama is None:
            print("Warning: Ollama not installed. Falling back to API-based LLMs if configured.")
            self.use_local_llm = False
    
    def analyze_company(self, website_data):
        """Analyze website content to extract company information"""
        # Check cache first if enabled
        if self.use_cache:
            cache_key = f"analysis_{website_data['domain']}"
            cached_data = self._check_cache(cache_key)
            if cached_data:
                print(f"Using cached analysis for {website_data['domain']}")
                return cached_data
        
        # Prepare content for analysis
        content_to_analyze = self._prepare_content(website_data)
        
        # Use LLM to analyze content
        analysis_result = self._analyze_with_llm(content_to_analyze)
        
        # Add timestamp for cache management
        analysis_result['timestamp'] = datetime.now().isoformat()
        
        # Cache the results if enabled
        if self.use_cache:
            cache_key = f"analysis_{website_data['domain']}"
            self._cache_results(cache_key, analysis_result)
        
        return analysis_result
    
    def _prepare_content(self, website_data):
        """Prepare website content for LLM analysis"""
        # Start with basic information
        content = f"Website: {website_data['url']}\n"
        content += f"Company Name: {website_data['name']}\n"
        content += f"Page Title: {website_data['title']}\n"
        content += f"Description: {website_data['description']}\n\n"
        
        # Add main content (truncated if too long)
        main_content = website_data['main_content']
        if len(main_content) > 3000:
            content += f"Main Content (truncated): {main_content[:3000]}...\n\n"
        else:
            content += f"Main Content: {main_content}\n\n"
        
        # Add important pages content
        for page_type, page_data in website_data.get('important_pages', {}).items():
            if 'error' in page_data:
                continue
                
            page_content = page_data.get('content', '')
            if page_content:
                # Truncate if too long
                if len(page_content) > 2000:
                    content += f"{page_type.capitalize()} Page Content (truncated): {page_content[:2000]}...\n\n"
                else:
                    content += f"{page_type.capitalize()} Page Content: {page_content}\n\n"
        
        return content
    
    def _analyze_with_llm(self, content):
        """Use LLM to analyze the content"""
        if self.use_local_llm and ollama is not None:
            return self._analyze_with_ollama(content)
        else:
            # Fallback to a simple rule-based analysis if no LLM is available
            return self._analyze_without_llm(content)
    
    def _analyze_with_ollama(self, content):
        """Use Ollama for local LLM analysis"""
        try:
            # Prepare the prompt for company analysis
            prompt = f"""
            Analyze the following website content and extract key information about the company.
            
            {content}
            
            Please provide the following information in a structured format:
            1. Company Type: (B2B, B2C, Government, Non-profit, etc.)
            2. Industry: (Technology, Healthcare, Finance, Education, etc.)
            3. Target Market: (Who are their customers/clients?)
            4. Products/Services: (What do they offer?)
            5. Key Decision Maker Roles: (What job titles would likely make purchasing decisions?)
            6. Company Size Estimate: (Small, Medium, Large)
            7. Potential Pain Points: (What problems might they be trying to solve?)
            
            Format your response as JSON with these exact keys: company_type, industry, target_market, offerings, decision_maker_roles, company_size, pain_points
            """
            
            # Call Ollama
            response = ollama.generate(model=self.model_name, prompt=prompt)
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response['response'], re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without markdown formatting
                json_match = re.search(r'(\{.*\})', response['response'], re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response['response']
            
            # Clean up and parse JSON
            try:
                # Remove any non-JSON text before or after the JSON object
                json_str = re.sub(r'^[^{]*', '', json_str)
                json_str = re.sub(r'[^}]*$', '', json_str)
                
                result = json.loads(json_str)
                
                # Ensure all expected keys are present
                expected_keys = ['company_type', 'industry', 'target_market', 'offerings', 
                                'decision_maker_roles', 'company_size', 'pain_points']
                
                for key in expected_keys:
                    if key not in result:
                        result[key] = "Not identified"
                
                return result
            except json.JSONDecodeError:
                print("Failed to parse JSON from LLM response. Falling back to rule-based analysis.")
                return self._analyze_without_llm(content)
                
        except Exception as e:
            print(f"Error using Ollama: {str(e)}")
            return self._analyze_without_llm(content)
    
    def _analyze_without_llm(self, content):
        """Simple rule-based analysis as fallback"""
        # This is a very basic fallback if LLM is not available
        result = {
            'company_type': self._guess_company_type(content),
            'industry': self._guess_industry(content),
            'target_market': "Unknown - LLM analysis required",
            'offerings': self._extract_offerings(content),
            'decision_maker_roles': self._guess_decision_makers(content),
            'company_size': "Unknown - LLM analysis required",
            'pain_points': "Unknown - LLM analysis required"
        }
        
        return result
    
    def _guess_company_type(self, content):
        """Simple rule-based company type detection"""
        content = content.lower()
        
        if re.search(r'\b(b2b|business.{1,10}business|enterprise.{1,10}solution)\b', content):
            return "B2B"
        elif re.search(r'\b(b2c|consumer|retail|shop|store)\b', content):
            return "B2C"
        elif re.search(r'\b(government|federal|agency|public sector)\b', content):
            return "Government"
        elif re.search(r'\b(non.?profit|ngo|charity|foundation)\b', content):
            return "Non-profit"
        else:
            return "Unknown"
    
    def _guess_industry(self, content):
        """Simple rule-based industry detection"""
        content = content.lower()
        
        industry_patterns = {
            'Technology': [r'\b(tech|software|it|computing|digital|ai|artificial intelligence)\b'],
            'Healthcare': [r'\b(health|medical|hospital|pharma|doctor|patient|clinic)\b'],
            'Finance': [r'\b(finance|bank|investment|insurance|loan|mortgage|financial)\b'],
            'Education': [r'\b(education|school|university|college|learning|student|teacher)\b'],
            'Manufacturing': [r'\b(manufacturing|factory|production|industrial|machinery)\b'],
            'Retail': [r'\b(retail|shop|store|ecommerce|product|consumer)\b'],
            'Consulting': [r'\b(consulting|consultant|advisor|professional service)\b']
        }
        
        for industry, patterns in industry_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    return industry
        
        return "Unknown"
    
    def _extract_offerings(self, content):
        """Extract potential offerings from content"""
        # This is a very basic extraction and would be much better with LLM
        offerings = []
        
        # Look for common offering patterns
        service_matches = re.findall(r'(?:offer|provide|deliver)s?\s+([^.!?;]+)', content, re.I)
        for match in service_matches:
            if 10 < len(match) < 100:  # Filter out very short or long matches
                offerings.append(match.strip())
        
        # Look for list items that might be services
        list_items = re.findall(r'[•*-]\s+([^•*-\n]+)', content)
        for item in list_items:
            if 10 < len(item) < 100:
                offerings.append(item.strip())
        
        # Deduplicate and limit
        unique_offerings = list(set(offerings))
        return unique_offerings[:5] if unique_offerings else ["Unknown - LLM analysis required"]
    
    def _guess_decision_makers(self, content):
        """Guess potential decision maker roles"""
        content = content.lower()
        
        common_roles = {
            'Technology': ['CTO', 'CIO', 'IT Director', 'VP of Engineering', 'Technical Director'],
            'Marketing': ['CMO', 'Marketing Director', 'Brand Manager', 'Digital Marketing Manager'],
            'Finance': ['CFO', 'Finance Director', 'Controller', 'Accounting Manager'],
            'Operations': ['COO', 'Operations Director', 'VP of Operations', 'Facility Manager'],
            'Human Resources': ['CHRO', 'HR Director', 'Talent Acquisition Manager', 'People Operations'],
            'Executive': ['CEO', 'President', 'Owner', 'Founder', 'Managing Director']
        }
        
        # Determine which department the content most relates to
        department_scores = {}
        for dept in common_roles.keys():
            department_scores[dept] = content.count(dept.lower())
        
        # Add the executive department as it's always relevant
        department_scores['Executive'] = 1
        
        # Get top 2 departments
        top_departments = sorted(department_scores.items(), key=lambda x: x[1], reverse=True)[:2]
        
        # Get roles from top departments
        roles = []
        for dept, _ in top_departments:
            roles.extend(common_roles[dept][:3])  # Take top 3 roles from each department
        
        return roles
    
    def _check_cache(self, cache_key):
        """Check if we have a valid cache for this analysis"""
        cache_path = get_cache_path(cache_key, subdir='analysis')
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache is expired
            timestamp = datetime.fromisoformat(cached_data.get('timestamp', '2000-01-01'))
            now = datetime.now()
            
            if (now - timestamp).total_seconds() > self.cache_expiry:
                print(f"Cache expired for {cache_key}")
                return None
                
            return cached_data
        except Exception as e:
            print(f"Error reading cache: {str(e)}")
            return None
    
    def _cache_results(self, cache_key, data):
        """Save results to cache"""
        cache_path = get_cache_path(cache_key, subdir='analysis')
        
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing to cache: {str(e)}")

# Function to be imported by other modules
def analyze_company(website_data):
    """Analyze website data and extract company information"""
    # Get settings from environment variables or use defaults
    use_local_llm = os.environ.get('USE_LOCAL_LLM', 'True').lower() == 'true'
    model_name = os.environ.get('LLM_MODEL', 'phi3')
    
    analyzer = ContentAnalyzer(use_local_llm=use_local_llm, model_name=model_name)
    return analyzer.analyze_company(website_data)

# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Load website data from file
        with open(sys.argv[1], 'r') as f:
            website_data = json.load(f)
    else:
        # Use sample data
        website_data = {
            'url': 'https://www.example.com',
            'domain': 'example.com',
            'name': 'Example Company',
            'title': 'Example Company - Home',
            'description': 'Example Company provides enterprise solutions',
            'main_content': 'Example Company is a leading provider of enterprise solutions...',
            'important_pages': {}
        }
    
    result = analyze_company(website_data)
    print(json.dumps(result, indent=2))
