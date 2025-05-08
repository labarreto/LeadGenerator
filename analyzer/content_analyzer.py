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
        # Get max content length from environment or use default
        max_length = int(os.environ.get('MAX_CONTENT_LENGTH', 2000))
        
        # Start with basic information (most important)
        content = f"Website: {website_data['url']}\n"
        content += f"Company Name: {website_data['name']}\n"
        content += f"Page Title: {website_data['title']}\n"
        content += f"Description: {website_data['description']}\n\n"
        
        # Extract the most important content first - the description and about page
        about_content = ""
        if 'about' in website_data.get('important_pages', {}):
            about_page = website_data['important_pages']['about']
            if 'content' in about_page and 'error' not in about_page:
                about_content = about_page['content']
                # Only use first 1000 chars of about page
                if len(about_content) > 1000:
                    about_content = about_content[:1000]
        
        # Add main content (heavily truncated to save tokens)
        main_content = website_data['main_content']
        # Only use first part of main content if we have about content
        main_length = max_length - len(about_content)
        if main_length > 0:
            if len(main_content) > main_length:
                content += f"Main Content (truncated): {main_content[:main_length]}...\n\n"
            else:
                content += f"Main Content: {main_content}\n\n"
        
        # Add about page content if available
        if about_content:
            content += f"About Page Content: {about_content}\n\n"
            
        # Skip other pages if SCRAPE_IMPORTANT_PAGES_ONLY is True
        if os.environ.get('SCRAPE_IMPORTANT_PAGES_ONLY', 'True').lower() != 'true':
            # Add other important pages content (limited)
            for page_type, page_data in website_data.get('important_pages', {}).items():
                # Skip about page as we've already added it
                if page_type == 'about' or 'error' in page_data:
                    continue
                    
                page_content = page_data.get('content', '')
                if page_content:
                    # Very short snippet
                    snippet = page_content[:300] + "..."
                    content += f"{page_type.capitalize()} Page: {snippet}\n\n"
        
        return content
    
    def _analyze_with_llm(self, content):
        """Use LLM to analyze the content"""
        if self.use_local_llm and ollama is not None:
            return self._analyze_with_ollama(content)
        else:
            # Fallback to a simple rule-based analysis if no LLM is available
            return self._analyze_without_llm(content)
    
    def _analyze_with_ollama(self, content):
        """Use Ollama for local LLM analysis - optimized for lightweight models"""
        try:
            # First, perform a focused analysis on key business attributes
            business_prompt = f"""
            Analyze this website content and extract detailed business information.
            
            {content}
            
            Focus on these THREE specific areas with detailed analysis:
            
            1. COMPANY SIZE: Analyze employee count, office locations, revenue indicators, client size, etc.
               Classify as Small (1-50 employees), Medium (51-500), or Large (500+).
               Provide specific evidence from the content.
            
            2. TARGET MARKET: Who exactly are their ideal customers? Be specific about:
               - Industries they target
               - Company sizes they serve
               - Geographic regions they focus on
               - Specific roles or departments they sell to
            
            3. OFFERINGS: What specific products/services do they provide?
               - List main product/service categories
               - Identify their flagship or primary offerings
               - Note any specialized or unique offerings
            
            Format your response as JSON with these keys: company_size, target_market, offerings
            For target_market and offerings, provide arrays with specific items, not just general descriptions.
            """
            
            # Call Ollama for the focused business analysis
            business_response = ollama.generate(
                model=self.model_name, 
                prompt=business_prompt,
                options={"num_predict": 1000}
            )
            
            # Now get the general company information with a separate prompt
            general_prompt = f"""
            Analyze this website content and extract basic company information.
            
            {content}
            
            Extract and return ONLY these fields in JSON format:
            - company_type: B2B, B2C, Government, or Non-profit
            - industry: Main industry
            - decision_maker_roles: List of 2-3 job titles who would make purchasing decisions
            - pain_points: Main challenges they might face
            
            Return ONLY valid JSON with these exact keys.
            """
            
            # Call Ollama for the general company information
            general_response = ollama.generate(
                model=self.model_name, 
                prompt=general_prompt,
                options={"num_predict": 800}
            )
            
            # Combine the responses
            business_data = self._extract_json_from_response(business_response['response'])
            general_data = self._extract_json_from_response(general_response['response'])
            
            # Create a combined response
            response = {'response': json.dumps({**general_data, **business_data})}
            
            # Process the combined response
            return self._process_llm_response(response)
        except Exception as e:
            print(f"Error in Ollama analysis: {str(e)}")
            return self._analyze_without_llm(content)
                
    def _extract_json_from_response(self, text):
        """Extract JSON from LLM response"""
        # Try to find JSON with markdown formatting
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without markdown formatting
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = text
        
        # Remove any non-JSON text before or after the JSON object
        json_str = re.sub(r'^[^{]*', '', json_str)
        json_str = re.sub(r'[^}]*$', '', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}
    
    def _process_llm_response(self, response):
        """Process the LLM response and ensure all required fields are present"""
        try:
            # Extract JSON from response
            if isinstance(response, dict) and 'response' in response:
                result = json.loads(response['response'])
            else:
                result = self._extract_json_from_response(response)
            
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
            'target_market': self._guess_target_market(content),
            'offerings': self._extract_offerings(content),
            'decision_maker_roles': self._guess_decision_makers(content),
            'company_size': self._guess_company_size(content),
            'pain_points': self._guess_pain_points(content)
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
    
    def _guess_company_size(self, content):
        """Guess the company size from content"""
        # Look for employee count indicators
        small_indicators = ['small', 'startup', 'founder', 'small business']
        medium_indicators = ['growing', 'mid-size', 'medium']
        large_indicators = ['enterprise', 'corporation', 'global', 'nationwide', 'international']
        
        # Check for size indicators
        for indicator in large_indicators:
            if re.search(r'\b' + indicator + r'\b', content, re.I):
                return "Large"
                
        for indicator in medium_indicators:
            if re.search(r'\b' + indicator + r'\b', content, re.I):
                return "Medium"
                
        for indicator in small_indicators:
            if re.search(r'\b' + indicator + r'\b', content, re.I):
                return "Small"
        
        # Look for team/employee mentions
        team_match = re.search(r'team of (\d+)', content, re.I)
        if team_match:
            count = int(team_match.group(1))
            if count < 50:
                return "Small"
            elif count < 500:
                return "Medium"
            else:
                return "Large"
        
        return "Unknown - LLM analysis required"
        
    def _guess_target_market(self, content):
        """Guess the target market from content"""
        target_markets = []
        
        # Look for common target market indicators
        b2b_indicators = ['enterprise', 'business', 'companies', 'organizations', 'firms']
        b2c_indicators = ['consumer', 'individual', 'personal', 'people', 'family']
        industry_indicators = ['healthcare', 'finance', 'retail', 'education', 'manufacturing', 'technology']
        
        # Check for B2B/B2C indicators
        for indicator in b2b_indicators:
            if re.search(r'\b' + indicator + r'\b', content, re.I):
                target_markets.append('B2B Companies')
                break
                
        for indicator in b2c_indicators:
            if re.search(r'\b' + indicator + r'\b', content, re.I):
                target_markets.append('Individual Consumers')
                break
                
        # Check for industry-specific indicators
        for indicator in industry_indicators:
            if re.search(r'\b' + indicator + r'\b', content, re.I):
                target_markets.append(f'{indicator.title()} Industry')
        
        # Return results or default
        return target_markets if target_markets else ["Unknown - LLM analysis required"]
        
    def _guess_pain_points(self, content):
        """Guess potential pain points from content"""
        pain_points = []
        
        # Look for common pain point indicators
        pain_indicators = [
            'challenge', 'problem', 'struggle', 'difficulty', 'obstacle',
            'improve', 'optimize', 'streamline', 'enhance', 'simplify',
            'reduce costs', 'save time', 'increase efficiency'
        ]
        
        for indicator in pain_indicators:
            pattern = r'(?:' + indicator + r')\s+([^.!?;]+)'
            matches = re.findall(pattern, content, re.I)
            for match in matches:
                if 10 < len(match) < 100:  # Filter out very short or long matches
                    pain_points.append(match.strip())
        
        # Return results or default
        return pain_points if pain_points else ["Unknown - LLM analysis required"]
        
        # Look for list items that might be services
        list_items = re.findall(r'[•*\-]\s+([^•*\-\n]+)', content)
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
