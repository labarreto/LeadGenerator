import os
import json
import re
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import get_cache_path

# Import LLM interface
from .llm_interface import query_llm, extract_json_from_response

class ContentAnalyzer:
    """Class to analyze website content and extract company information using LLMs"""
    
    def __init__(self, use_local_llm=False, model_name="gpt-4.1-nano", use_cache=True, cache_expiry=86400):
        """Initialize the content analyzer with LLM options"""
        self.use_local_llm = use_local_llm
        self.model_name = model_name
        self.use_cache = use_cache
        self.cache_expiry = cache_expiry
        self.company_analysis = {}
        
        # Local LLM is disabled, using OpenAI instead
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
        
        # Store the analysis for other methods to use
        self.company_analysis = analysis_result
        
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
                if page_type == 'about' or 'error' in page_data or 'content' not in page_data:
                    continue
                
                page_content = page_data['content']
                if len(page_content) > 500:  # Limit to 500 chars per page
                    page_content = page_content[:500] + "..."
                
                content += f"{page_type.title()} Page Content: {page_content}\n\n"
        
        return content
    
    def _analyze_with_llm(self, content):
        """Use LLM to analyze website content"""
        return self._analyze_with_openai(content)
    
    def _analyze_with_openai(self, content):
        """Use OpenAI for content analysis"""
        try:
            # Prepare the prompt for company analysis
            prompt = f"""
            You are a business analyst expert. Analyze the following website content and extract key information about the company.
            
            IMPORTANT: Focus especially on identifying SPECIFIC offerings/products/services and the target market.
            
            Return the results in JSON format with the following fields:
            - company_name: The name of the company
            - industry: The specific industry or sector the company operates in (be detailed, not general)
            - company_size: Estimated company size (small, medium, large)
            - target_market: Who the company sells to (B2B, B2C, or both) - BE SPECIFIC about the types of customers
            - offerings: List of SPECIFIC products or services the company offers (at least 3-5 items if possible)
            - company_description: A brief description of what the company does
            - location: Company headquarters location if mentioned
            - founded_year: When the company was founded if mentioned
            - key_people: Key executives or team members if mentioned
            - contact_info: Contact information if available
            - social_media: Social media links if available
            
            IMPORTANT GUIDELINES:
            1. For offerings: List SPECIFIC named products/services, not general categories
            2. For target_market: Be specific about the types of customers (e.g., "Enterprise healthcare providers" not just "B2B")
            3. NEVER use "Unknown - LLM analysis required" - make your best inference based on the content
            4. If information isn't explicitly stated, make reasonable inferences based on the content
            
            Website Content:
            {content[:2000]}  # Limit content to avoid token limits
            
            Return ONLY valid JSON without any additional text or explanation.
            """
            
            # Call OpenAI with the prompt
            response_text = query_llm(prompt, model=self.model_name)
            
            # Parse the JSON response
            try:
                result = extract_json_from_response(response_text)
                return self._process_llm_response(result)
            except json.JSONDecodeError:
                print("Failed to parse LLM response as JSON")
                return self._analyze_without_llm(content)
                
        except Exception as e:
            print(f"Error using OpenAI: {str(e)}")
            # Fall back to rule-based analysis
            return self._analyze_without_llm(content)
    
    def _process_llm_response(self, response):
        """Process the LLM response and ensure all required fields are present"""
        # Define required fields with default values
        required_fields = {
            'company_type': 'Unknown',
            'industry': 'Unknown',
            'company_size': 'Unknown',
            'target_market': 'Unknown',
            'offerings': [],
            'pain_points': []
        }
        
        # Ensure all required fields are present
        for field, default_value in required_fields.items():
            if field not in response or not response[field]:
                response[field] = default_value
            
            # Ensure lists are actually lists
            if field in ['offerings', 'pain_points', 'target_market'] and isinstance(response[field], str):
                response[field] = [response[field]]
        
        return response
    
    def _analyze_without_llm(self, content):
        """Simple rule-based analysis as fallback"""
        # Create a basic analysis using rule-based methods
        analysis = {
            'company_type': self._guess_company_type(content),
            'industry': self._guess_industry(content),
            'company_size': self._guess_company_size(content),
            'target_market': self._guess_target_market(content),
            'offerings': self._extract_offerings(content),
            'pain_points': self._guess_pain_points(content)
        }
        
        return analysis
    
    def _guess_company_type(self, content):
        """Simple rule-based company type detection"""
        content = content.lower()
        
        # Look for B2B indicators
        b2b_indicators = ['business', 'enterprise', 'organization', 'company', 'client', 'solution']
        b2b_count = sum(content.count(indicator) for indicator in b2b_indicators)
        
        # Look for B2C indicators
        b2c_indicators = ['consumer', 'customer', 'individual', 'personal', 'user', 'people']
        b2c_count = sum(content.count(indicator) for indicator in b2c_indicators)
        
        # Look for government indicators
        gov_indicators = ['government', 'public sector', 'agency', 'federal', 'state', 'municipal']
        gov_count = sum(content.count(indicator) for indicator in gov_indicators)
        
        # Look for non-profit indicators
        npo_indicators = ['non-profit', 'nonprofit', 'charity', 'foundation', 'community', 'donation']
        npo_count = sum(content.count(indicator) for indicator in npo_indicators)
        
        # Determine the most likely type
        counts = {
            'B2B': b2b_count,
            'B2C': b2c_count,
            'Government': gov_count,
            'Non-profit': npo_count
        }
        
        # Return the type with the highest count, or Unknown if all are 0
        max_type = max(counts.items(), key=lambda x: x[1])
        return max_type[0] if max_type[1] > 0 else "Unknown"
    
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
        """Extract the company's offerings (products/services) with improved detection"""
        if not content:
            return ["Unknown - LLM analysis required"]
        
        # Enhanced prompt for better offerings detection
        offerings_prompt = (
            "Analyze the following website content and identify the specific products or services offered by this company. "
            "Focus on finding concrete offerings rather than general capabilities. "
            "Look for sections like 'Products', 'Services', 'Solutions', or 'What We Offer'. "
            "Return a comma-separated list of 3-6 specific offerings (e.g., 'Cloud Storage, AI Consulting, Data Analytics'). "
            "Be as specific as possible with each offering. "
            "If you can't determine the offerings with confidence, respond with 'Unknown':\n\n"
            f"{content[:4000]}"
        )
        
        try:
            if self.use_local_llm:
                offerings_text = query_llm(offerings_prompt, model=self.model_name)
                if isinstance(offerings_text, dict) and 'offerings' in offerings_text:
                    offerings = offerings_text['offerings']
                    if isinstance(offerings, list):
                        return offerings
                    elif isinstance(offerings, str):
                        return [item.strip() for item in offerings.split(',') if item.strip()]
                    
                # Fallback to pattern matching
                offerings_text = self._extract_offerings_with_patterns(content)
            else:
                # Fallback to pattern matching if LLM is not available
                offerings_text = self._extract_offerings_with_patterns(content)
            
            if offerings_text and offerings_text.lower() != "unknown":
                # Split by commas and clean up
                offerings = [item.strip() for item in offerings_text.split(',') if item.strip()]
                
                # Filter out generic or vague offerings
                filtered_offerings = []
                for offering in offerings:
                    # Skip very short or generic offerings
                    if len(offering) < 4 or offering.lower() in ['services', 'products', 'solutions']:
                        continue
                    filtered_offerings.append(offering)
                
                return filtered_offerings if filtered_offerings else self._infer_offerings_from_industry()
            else:
                return self._infer_offerings_from_industry()
        except Exception as e:
            print(f"Error extracting offerings: {e}")
            return self._infer_offerings_from_industry()
    
    def _extract_offerings_with_patterns(self, content):
        """Extract offerings using pattern matching as a fallback method"""
        # Look for common patterns that indicate offerings
        offerings = []
        
        # Pattern 1: Look for bullet points after headings like "Our Services"
        service_sections = re.findall(r'(?:Our|Key|Main)\s+(?:Services|Products|Solutions|Offerings)(?:[:\s]*)([^#]+?)(?:\n\n|$)', content, re.IGNORECASE)
        for section in service_sections:
            # Look for bullet points or numbered lists
            items = re.findall(r'(?:•|\*|\-|\d+\.)\s*([^\n•\*\-\d]+)', section)
            if items:
                offerings.extend([item.strip() for item in items if len(item.strip()) > 3][:6])  # Limit to 6 items
        
        # Pattern 2: Look for "We provide" or "We offer" statements
        offer_statements = re.findall(r'(?:We|Our company)\s+(?:provide|offer|deliver|specialize in)\s+([^.]+)', content, re.IGNORECASE)
        for statement in offer_statements:
            # Split by "and" or commas
            parts = re.split(r'\s+and\s+|,\s*', statement)
            offerings.extend([part.strip() for part in parts if len(part.strip()) > 3][:6])  # Limit to 6 items
        
        # Deduplicate and limit
        unique_offerings = list(dict.fromkeys([o for o in offerings if o]))
        
        if unique_offerings:
            return ", ".join(unique_offerings[:6])  # Return top 6 offerings
        else:
            return "Unknown"
    
    def _infer_offerings_from_industry(self):
        """Infer potential offerings based on detected industry and company type"""
        industry = self.company_analysis.get('industry', 'Unknown')
        company_type = self.company_analysis.get('company_type', 'B2B')
        
        industry_offerings = {
            'Technology': ['Software Development', 'IT Consulting', 'Cloud Services', 'Data Analytics', 'Cybersecurity'],
            'Healthcare': ['Medical Services', 'Healthcare IT', 'Patient Management', 'Medical Equipment', 'Telehealth'],
            'Finance': ['Financial Services', 'Investment Management', 'Banking Solutions', 'Insurance', 'Payment Processing'],
            'Education': ['Educational Content', 'Learning Management', 'Student Services', 'Educational Technology', 'Training Programs'],
            'Manufacturing': ['Production Services', 'Supply Chain Management', 'Quality Control', 'Equipment Manufacturing', 'Industrial Design'],
            'Retail': ['E-commerce Solutions', 'Inventory Management', 'Customer Experience', 'Point of Sale Systems', 'Retail Analytics'],
            'Consulting': ['Business Strategy', 'Management Consulting', 'Process Improvement', 'Change Management', 'Industry Expertise']
        }
        
        if industry in industry_offerings:
            # Return the top 3 most relevant offerings for this industry
            return industry_offerings[industry][:3]
        else:
            # Generic offerings based on company type
            if company_type == 'B2B':
                return ['Business Services', 'Professional Solutions', 'Enterprise Software']
            elif company_type == 'B2C':
                return ['Consumer Products', 'Customer Services', 'Retail Solutions']
            else:
                return ['Professional Services', 'Industry Solutions', 'Specialized Expertise']
    
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
        
        return "Medium"  # Default to Medium if unknown
    
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
        
        # Deduplicate and limit
        unique_pain_points = list(dict.fromkeys([p for p in pain_points if p]))
        return unique_pain_points[:5] if unique_pain_points else ["Unknown - LLM analysis required"]
    
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
def analyze_company(website_data, use_cache=True):
    """Analyze website data and extract company information"""
    # Get settings from environment variables or use defaults
    use_local_llm = os.environ.get('USE_LOCAL_LLM', 'True').lower() == 'true'
    model_name = os.environ.get('OPENAI_MODEL', 'gpt-4.1-nano')
    
    analyzer = ContentAnalyzer(use_local_llm=use_local_llm, model_name=model_name, use_cache=use_cache)
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
