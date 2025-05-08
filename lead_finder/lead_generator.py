import os
import json
import re
import random
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import get_cache_path

class LeadGenerator:
    """Class to identify potential leads and their contact information"""
    
    def __init__(self, use_cache=True, cache_expiry=86400, find_external_leads=True):
        """Initialize the lead generator with caching options"""
        self.use_cache = use_cache
        self.cache_expiry = cache_expiry
        self.find_external_leads = find_external_leads
        
        # Common email patterns for different companies
        self.email_patterns = [
            "{first}.{last}@{domain}",
            "{first_initial}{last}@{domain}",
            "{first}@{domain}",
            "{last}@{domain}",
            "{first_initial}.{last}@{domain}",
            "{first}{last_initial}@{domain}"
        ]
        
        # External company domains by industry
        self.industry_domains = {
            'Technology': ['techcorp.com', 'innovatetech.io', 'nextsoftware.com', 'cloudservices.net', 'datatech.ai'],
            'Healthcare': ['healthsolutions.org', 'medicalgroup.com', 'careproviders.net', 'healthtech.io', 'medicalservices.com'],
            'Finance': ['financialgroup.com', 'investmentfirm.com', 'bankingsolutions.net', 'wealthmanagement.com', 'fintech.io'],
            'Education': ['learningsolutions.org', 'educationgroup.com', 'academicservices.net', 'trainingpro.com', 'edtech.io'],
            'Manufacturing': ['industrialsolutions.com', 'manufacturinggroup.net', 'productionservices.com', 'factorytech.io', 'industrialequipment.com'],
            'Retail': ['retailgroup.com', 'shoppingsolutions.net', 'consumerproducts.com', 'retailtech.io', 'marketingsolutions.com'],
            'Consulting': ['consultinggroup.com', 'advisoryservices.net', 'businessconsultants.com', 'strategyadvisors.io', 'consultingfirm.com']
        }
        
        # External company names by industry
        self.industry_companies = {
            'Technology': ['TechCorp', 'InnovateTech', 'NextSoftware', 'CloudServices', 'DataTech'],
            'Healthcare': ['HealthSolutions', 'MedicalGroup', 'CareProviders', 'HealthTech', 'MedicalServices'],
            'Finance': ['FinancialGroup', 'InvestmentFirm', 'BankingSolutions', 'WealthManagement', 'FinTech'],
            'Education': ['LearningSolutions', 'EducationGroup', 'AcademicServices', 'TrainingPro', 'EdTech'],
            'Manufacturing': ['IndustrialSolutions', 'ManufacturingGroup', 'ProductionServices', 'FactoryTech', 'IndustrialEquipment'],
            'Retail': ['RetailGroup', 'ShoppingSolutions', 'ConsumerProducts', 'RetailTech', 'MarketingSolutions'],
            'Consulting': ['ConsultingGroup', 'AdvisoryServices', 'BusinessConsultants', 'StrategyAdvisors', 'ConsultingFirm']
        }
    
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
        
        # Generate internal leads (from the analyzed company)
        internal_leads = self._generate_internal_leads(company_analysis, domain)
        leads.extend(internal_leads)
        
        # Generate external leads (potential customers or partners)
        if self.find_external_leads:
            external_leads = self._generate_external_leads(company_analysis, domain)
            leads.extend(external_leads)
        
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
        
    def _generate_internal_leads(self, company_analysis, domain):
        """Generate leads from within the analyzed company"""
        internal_leads = []
        
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
            lead['lead_type'] = 'internal'
            internal_leads.append(lead)
            
        return internal_leads
    
    def _generate_external_leads(self, company_analysis, domain):
        """Generate external leads that would be potential customers or partners"""
        external_leads = []
        
        # Extract key information from company analysis
        industry = company_analysis.get('industry', 'Unknown')
        company_type = company_analysis.get('company_type', 'B2B')
        target_market = company_analysis.get('target_market', [])
        offerings = company_analysis.get('offerings', [])
        company_size = company_analysis.get('company_size', 'Medium')
        
        # Determine potential customer industries based on offerings and target market
        potential_industries = self._determine_potential_customer_industries(industry, offerings, target_market)
        
        # Generate 2-3 external leads
        num_leads = random.randint(2, 3)
        for _ in range(num_leads):
            # Select a random industry for this lead
            target_industry = random.choice(potential_industries)
            
            # Get appropriate roles for this industry
            roles = self._get_target_roles_for_industry(target_industry, offerings)
            role = random.choice(roles)
            
            # Get a company domain for this industry
            if target_industry in self.industry_domains:
                company_domain = random.choice(self.industry_domains[target_industry])
                company_name = random.choice(self.industry_companies[target_industry])
            else:
                # Fallback to generic domains
                company_domain = f"{target_industry.lower().replace(' ', '')}company.com"
                company_name = f"{target_industry} Company"
            
            # Create the lead
            lead = self._create_lead_for_role(role, company_domain, company_analysis)
            lead['lead_type'] = 'external'
            lead['company_name'] = company_name
            lead['target_reason'] = self._generate_target_reason(company_analysis, target_industry, role)
            external_leads.append(lead)
            
        return external_leads
    
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
    
    def _determine_potential_customer_industries(self, industry, offerings, target_market):
        """Determine potential customer industries based on company analysis"""
        potential_industries = []
        
        # Convert offerings and target_market to lists if they're not already
        if isinstance(offerings, str):
            offerings = [offerings]
        if isinstance(target_market, str):
            target_market = [target_market]
            
        # Default industries to consider
        all_industries = [
            'Technology', 'Healthcare', 'Finance', 'Education', 
            'Manufacturing', 'Retail', 'Consulting'
        ]
        
        # If we have specific target markets, use them to determine industries
        if target_market and target_market != ["Unknown - LLM analysis required"]:
            for market in target_market:
                market_lower = market.lower()
                
                # Check for industry mentions in target market
                for ind in all_industries:
                    if ind.lower() in market_lower:
                        potential_industries.append(ind)
                
                # Check for B2B/B2C indicators
                if 'b2b' in market_lower or 'business' in market_lower or 'companies' in market_lower:
                    # For B2B, add industries that commonly need business services
                    potential_industries.extend(['Technology', 'Finance', 'Consulting'])
                    
                if 'b2c' in market_lower or 'consumer' in market_lower or 'individual' in market_lower:
                    # For B2C, add industries that commonly serve consumers
                    potential_industries.extend(['Retail', 'Healthcare', 'Education'])
        
        # Use offerings to further refine potential industries
        if offerings and offerings != ["Unknown - LLM analysis required"]:
            for offering in offerings:
                offering_lower = offering.lower()
                
                # Technology-related offerings
                if any(term in offering_lower for term in ['software', 'app', 'platform', 'tech', 'digital', 'ai', 'data']):
                    potential_industries.extend(['Technology', 'Finance', 'Healthcare'])
                    
                # Healthcare-related offerings
                if any(term in offering_lower for term in ['health', 'medical', 'care', 'patient', 'wellness']):
                    potential_industries.extend(['Healthcare', 'Education'])
                    
                # Financial-related offerings
                if any(term in offering_lower for term in ['finance', 'payment', 'banking', 'investment', 'insurance']):
                    potential_industries.extend(['Finance', 'Retail', 'Technology'])
                    
                # Education-related offerings
                if any(term in offering_lower for term in ['education', 'learning', 'training', 'course', 'teach']):
                    potential_industries.extend(['Education', 'Technology', 'Healthcare'])
                    
                # Manufacturing-related offerings
                if any(term in offering_lower for term in ['manufacturing', 'production', 'factory', 'industrial']):
                    potential_industries.extend(['Manufacturing', 'Technology'])
                    
                # Retail-related offerings
                if any(term in offering_lower for term in ['retail', 'shop', 'store', 'product', 'consumer']):
                    potential_industries.extend(['Retail', 'Technology'])
                    
                # Consulting-related offerings
                if any(term in offering_lower for term in ['consulting', 'advisory', 'strategy', 'service']):
                    potential_industries.extend(['Consulting', 'Finance', 'Technology'])
        
        # If we still don't have any potential industries, use the company's own industry
        # and add some complementary industries
        if not potential_industries and industry != 'Unknown':
            potential_industries.append(industry)
            
            # Add complementary industries
            industry_complements = {
                'Technology': ['Finance', 'Healthcare', 'Retail'],
                'Healthcare': ['Technology', 'Education', 'Finance'],
                'Finance': ['Technology', 'Consulting', 'Retail'],
                'Education': ['Technology', 'Healthcare', 'Consulting'],
                'Manufacturing': ['Technology', 'Consulting', 'Retail'],
                'Retail': ['Technology', 'Finance', 'Consulting'],
                'Consulting': ['Finance', 'Technology', 'Manufacturing']
            }
            
            if industry in industry_complements:
                potential_industries.extend(industry_complements[industry])
        
        # If we still don't have any industries, use all of them
        if not potential_industries:
            potential_industries = all_industries
        
        # Remove duplicates and the company's own industry
        potential_industries = list(set(potential_industries))
        if industry in potential_industries:
            potential_industries.remove(industry)
            
        # Ensure we have at least 3 industries
        while len(potential_industries) < 3 and len(all_industries) > 0:
            random_industry = random.choice(all_industries)
            if random_industry != industry and random_industry not in potential_industries:
                potential_industries.append(random_industry)
                
        return potential_industries
    
    def _get_target_roles_for_industry(self, industry, offerings):
        """Get appropriate decision maker roles for the target industry based on offerings"""
        # Default roles by industry
        industry_roles = {
            'Technology': ['CTO', 'CIO', 'VP of Engineering', 'IT Director', 'Head of Digital'],
            'Healthcare': ['Medical Director', 'Chief of Operations', 'Head of Patient Services', 'IT Director', 'Clinical Director'],
            'Finance': ['CFO', 'Head of Risk', 'Investment Director', 'VP of Operations', 'Technology Director'],
            'Education': ['Dean', 'Principal', 'Director of IT', 'Head of Operations', 'Chief Academic Officer'],
            'Manufacturing': ['COO', 'Production Director', 'VP of Operations', 'Supply Chain Manager', 'Plant Manager'],
            'Retail': ['CMO', 'Head of Merchandising', 'Operations Director', 'Digital Director', 'Customer Experience Manager'],
            'Consulting': ['Managing Partner', 'Practice Lead', 'Director of Operations', 'Business Development Manager', 'Senior Consultant']
        }
        
        # Get the default roles for this industry
        roles = industry_roles.get(industry, ['CEO', 'COO', 'CTO'])
        
        # Refine based on offerings if available
        if offerings and offerings != ["Unknown - LLM analysis required"]:
            for offering in offerings:
                offering_lower = offering.lower()
                
                # Technology-focused offerings
                if any(term in offering_lower for term in ['software', 'app', 'platform', 'tech', 'digital', 'ai', 'data']):
                    roles.extend(['CTO', 'CIO', 'IT Director', 'Digital Transformation Lead'])
                    
                # Marketing-focused offerings
                if any(term in offering_lower for term in ['marketing', 'brand', 'advertising', 'social media', 'content']):
                    roles.extend(['CMO', 'Marketing Director', 'Brand Manager', 'Digital Marketing Lead'])
                    
                # Operations-focused offerings
                if any(term in offering_lower for term in ['operations', 'process', 'efficiency', 'workflow', 'management']):
                    roles.extend(['COO', 'Operations Director', 'Process Improvement Manager'])
                    
                # Finance-focused offerings
                if any(term in offering_lower for term in ['finance', 'payment', 'banking', 'investment', 'accounting']):
                    roles.extend(['CFO', 'Finance Director', 'Controller', 'Treasurer'])
        
        # Remove duplicates
        roles = list(set(roles))
        
        return roles
    
    def _generate_target_reason(self, company_analysis, target_industry, role):
        """Generate a reason why this lead would be interested in the company's offerings"""
        # Extract key information
        offerings = company_analysis.get('offerings', [])
        if isinstance(offerings, str):
            offerings = [offerings]
            
        industry = company_analysis.get('industry', 'Unknown')
        company_type = company_analysis.get('company_type', 'B2B')
        
        # Generate a reason based on the role and industry
        reasons = [
            f"As a {role} in the {target_industry} industry, they could benefit from your {industry} expertise",
            f"Their {target_industry} business faces challenges that your offerings could address",
            f"Your solutions are well-suited for {target_industry} companies with {role}s looking to improve operations"
        ]
        
        # Add offering-specific reasons if available
        if offerings and offerings != ["Unknown - LLM analysis required"]:
            for offering in offerings[:2]:  # Use up to 2 offerings
                reasons.append(f"Your {offering} offering would be valuable to a {role} in {target_industry}")
        
        # Return a random reason
        return random.choice(reasons)
    
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
    # Check if we should find external leads
    find_external_leads = os.environ.get('FIND_EXTERNAL_LEADS', 'True').lower() == 'true'
    
    generator = LeadGenerator(find_external_leads=find_external_leads)
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
