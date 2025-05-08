import os
import json
import re
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import get_cache_path

class LeadGenerator:
    """Class to identify potential leads and their contact information"""
    
    def __init__(self, use_cache=True, cache_expiry=86400):
        """Initialize the lead generator with caching options"""
        self.use_cache = use_cache
        self.cache_expiry = cache_expiry
        
        # Common email patterns for different companies
        self.email_patterns = [
            "{first}.{last}@{domain}",
            "{first_initial}{last}@{domain}",
            "{first}@{domain}",
            "{last}@{domain}",
            "{first_initial}.{last}@{domain}",
            "{first}{last_initial}@{domain}"
        ]
    
    def generate_leads(self, company_analysis, domain):
        """Generate potential leads based on company analysis"""
        # Check cache first if enabled
        if self.use_cache:
            cache_key = f"leads_{domain}"
            cached_data = self._check_cache(cache_key)
            if cached_data:
                print(f"Using cached leads for {domain}")
                return cached_data
        
        # Generate leads based on decision maker roles
        leads = []
        
        # Get decision maker roles from company analysis
        roles = company_analysis.get('decision_maker_roles', [])
        if not isinstance(roles, list):
            # Handle case where roles might be a string
            roles = [roles]
        
        # If no roles identified, use default roles based on company type
        if not roles or roles == ["Not identified"]:
            company_type = company_analysis.get('company_type', 'Unknown')
            roles = self._get_default_roles(company_type)
        
        # Generate leads for each role
        for role in roles:
            lead = self._create_lead_for_role(role, domain, company_analysis)
            leads.append(lead)
        
        # Add timestamp for cache management
        result = {
            'leads': leads,
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache the results if enabled
        if self.use_cache:
            cache_key = f"leads_{domain}"
            self._cache_results(cache_key, result)
        
        return result['leads']
    
    def _create_lead_for_role(self, role, domain, company_analysis):
        """Create a lead profile for a specific role"""
        # Generate a realistic name for the role
        first_name, last_name = self._generate_name_for_role(role)
        
        # Create the lead profile
        lead = {
            'name': f"{first_name} {last_name}",
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'company_domain': domain,
            'email': self._generate_email(first_name, last_name, domain),
            'confidence_score': self._calculate_confidence_score(role, company_analysis),
            'outreach_suggestions': self._generate_outreach_suggestions(role, company_analysis)
        }
        
        return lead
    
    def _generate_name_for_role(self, role):
        """Generate a realistic name for a role"""
        # This is a simplified version - in a real application, 
        # you might use a database of common names or an API
        
        # Common first names
        first_names = [
            "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
            "Thomas", "Charles", "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", 
            "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Margaret"
        ]
        
        # Common last names
        last_names = [
            "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
            "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
            "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis"
        ]
        
        # Use role to influence name selection (just for demonstration)
        # In a real application, you might use demographic data
        role_lower = role.lower()
        
        if "cto" in role_lower or "technical" in role_lower:
            tech_first_names = ["Alex", "Sam", "Jordan", "Taylor", "Casey"]
            first_names.extend(tech_first_names)
        
        if "ceo" in role_lower or "president" in role_lower:
            exec_last_names = ["Blackwell", "Montgomery", "Wellington", "Rothschild"]
            last_names.extend(exec_last_names)
        
        # Select a name
        import random
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        return first_name, last_name
    
    def _generate_email(self, first_name, last_name, domain):
        """Generate potential email addresses based on common patterns"""
        # Format the name components
        first = first_name.lower()
        last = last_name.lower()
        first_initial = first[0] if first else ""
        last_initial = last[0] if last else ""
        
        # Choose a pattern based on the domain
        # In a real application, you might use an email verification API
        import random
        pattern = random.choice(self.email_patterns)
        
        # Format the email
        email = pattern.format(
            first=first,
            last=last,
            first_initial=first_initial,
            last_initial=last_initial,
            domain=domain
        )
        
        return email
    
    def _calculate_confidence_score(self, role, company_analysis):
        """Calculate a confidence score for the lead"""
        # Base score
        score = 50
        
        # Adjust based on company analysis
        company_type = company_analysis.get('company_type', 'Unknown')
        if company_type != 'Unknown':
            score += 10
        
        # Adjust based on role relevance
        role_lower = role.lower()
        if "c" in role_lower and "o" in role_lower:  # C-level executive
            score += 20
        elif "director" in role_lower or "vp" in role_lower or "vice president" in role_lower:
            score += 15
        elif "manager" in role_lower:
            score += 10
        
        # Cap the score at 95 (never 100% certain)
        return min(score, 95)
    
    def _generate_outreach_suggestions(self, role, company_analysis):
        """Generate outreach suggestions based on role and company analysis"""
        suggestions = []
        
        # Get company information
        company_type = company_analysis.get('company_type', 'Unknown')
        industry = company_analysis.get('industry', 'Unknown')
        pain_points = company_analysis.get('pain_points', 'Unknown')
        
        # Generate role-specific suggestions
        role_lower = role.lower()
        
        if "cto" in role_lower or "technical" in role_lower or "engineering" in role_lower:
            suggestions.append("Focus on technical capabilities and integration ease")
            suggestions.append("Highlight case studies with technical ROI metrics")
        
        elif "cmo" in role_lower or "marketing" in role_lower:
            suggestions.append("Emphasize marketing analytics and customer insights")
            suggestions.append("Share content about improving customer engagement")
        
        elif "cfo" in role_lower or "finance" in role_lower:
            suggestions.append("Focus on cost savings and ROI calculations")
            suggestions.append("Provide clear pricing and implementation timelines")
        
        elif "ceo" in role_lower or "president" in role_lower or "founder" in role_lower:
            suggestions.append("Address strategic business outcomes and competitive advantage")
            suggestions.append("Reference similar companies where your solution made an impact")
        
        # Add industry-specific suggestions
        if industry != 'Unknown':
            suggestions.append(f"Mention your experience in the {industry} industry")
        
        # Add pain point suggestions
        if pain_points != 'Unknown' and pain_points != "Unknown - LLM analysis required":
            if isinstance(pain_points, list):
                for point in pain_points[:1]:  # Just use the first pain point
                    suggestions.append(f"Address their challenge: {point}")
            else:
                suggestions.append(f"Address their challenge: {pain_points}")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _get_default_roles(self, company_type):
        """Get default decision maker roles based on company type"""
        default_roles = {
            'B2B': ['CTO', 'VP of Engineering', 'Director of IT'],
            'B2C': ['CMO', 'Digital Marketing Director', 'Customer Experience Manager'],
            'Government': ['IT Director', 'Program Manager', 'Procurement Officer'],
            'Non-profit': ['Executive Director', 'Program Director', 'Operations Manager'],
            'Unknown': ['CEO', 'CTO', 'Operations Director']
        }
        
        return default_roles.get(company_type, default_roles['Unknown'])
    
    def _check_cache(self, cache_key):
        """Check if we have a valid cache for this analysis"""
        cache_path = get_cache_path(cache_key, subdir='leads')
        
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
                
            return cached_data.get('leads', [])
        except Exception as e:
            print(f"Error reading cache: {str(e)}")
            return None
    
    def _cache_results(self, cache_key, data):
        """Save results to cache"""
        cache_path = get_cache_path(cache_key, subdir='leads')
        
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing to cache: {str(e)}")

# Function to be imported by other modules
def generate_leads(company_analysis, domain):
    """Generate leads based on company analysis"""
    generator = LeadGenerator()
    return generator.generate_leads(company_analysis, domain)

# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Load company analysis from file
        with open(sys.argv[1], 'r') as f:
            company_analysis = json.load(f)
        domain = sys.argv[2] if len(sys.argv) > 2 else "example.com"
    else:
        # Use sample data
        company_analysis = {
            'company_type': 'B2B',
            'industry': 'Technology',
            'target_market': 'Enterprise companies',
            'offerings': ['Cloud solutions', 'Data analytics'],
            'decision_maker_roles': ['CTO', 'VP of Engineering'],
            'company_size': 'Medium',
            'pain_points': 'Legacy system integration'
        }
        domain = "example.com"
    
    result = generate_leads(company_analysis, domain)
    print(json.dumps(result, indent=2))
