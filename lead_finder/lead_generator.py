import os
import json
import re
import random
from datetime import datetime
import sys
import requests
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import get_cache_path
from analyzer.llm_interface import query_llm

class LeadGenerator:
    """Class to identify potential external leads based on company analysis"""
    
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
        
        # Generate external leads (potential customers or partners)
        leads = self._generate_external_leads(company_analysis, domain)
        
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
    
    def _generate_external_leads(self, company_analysis, domain):
        """Generate high-quality external leads that would be potential customers or partners using LLM"""
        external_leads = []
        
        # Extract key information from company analysis
        industry = company_analysis.get('industry', 'Unknown')
        company_type = company_analysis.get('company_type', 'B2B')
        target_market = company_analysis.get('target_market', [])
        offerings = company_analysis.get('offerings', [])
        company_size = company_analysis.get('company_size', 'Medium')
        company_description = company_analysis.get('description', '')
        
        # If offerings are unknown, try to infer them from industry and company type
        if not offerings or offerings == ["Unknown - LLM analysis required"]:
            offerings = self._infer_offerings_from_industry(industry, company_type)
        
        # Use LLM to generate potential customer companies based on offerings
        potential_matches = self._generate_potential_matches_with_llm(industry, offerings, target_market, company_size, company_description)
        
        # If LLM fails, fall back to the rule-based approach
        if not potential_matches:
            potential_matches = self._determine_potential_matches(industry, offerings, target_market, company_size)
        
        # Generate 4-6 high-quality external leads
        num_leads = min(len(potential_matches), random.randint(4, 6))
        
        # Sort potential matches by match score (highest first)
        potential_matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        for i in range(min(num_leads, len(potential_matches))):
            match = potential_matches[i]
            
            # Get appropriate roles for this company based on the specific match reason
            roles = self._get_target_roles_for_match(match)
            role = roles[0] if roles else "Director of Operations"
            
            # Create the lead
            lead = self._create_lead_for_role(role, match['domain'], company_analysis)
            lead['lead_type'] = 'external'
            lead['company_name'] = match['company_name']
            lead['match_score'] = match['match_score']
            lead['match_percentage'] = f"{match['match_score']}%"  # Add percentage format
            lead['target_reason'] = match['match_reason']
            lead['potential_value'] = self._calculate_potential_value(match, company_analysis)
            lead['industry'] = match['industry']
            # Use size if available, otherwise infer from potential value
            if 'size' in match:
                lead['company_size'] = match['size']
            else:
                # Default to medium if size not available
                lead['company_size'] = 'Medium'
            external_leads.append(lead)
            
        return external_leads
        
    def _infer_offerings_from_industry(self, industry, company_type):
        """Infer potential offerings based on industry and company type"""
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
    def _generate_potential_matches_with_llm(self, industry, offerings, target_market, company_size, company_description):
        """Generate potential customer matches using LLM for more accurate and specific results"""
        try:
            # Ensure we have valid offerings and target market
            if not offerings or offerings == ["Unknown - LLM analysis required"]:
                offerings = self._infer_offerings_from_industry(industry, 'B2B')
                
            if not target_market or target_market == "Unknown - LLM analysis required":
                # Default to B2B if unknown
                target_market = "B2B"
            
            # Create a detailed prompt for the LLM
            offerings_str = ", ".join(offerings) if isinstance(offerings, list) else offerings
            target_market_str = ", ".join(target_market) if isinstance(target_market, list) else target_market
            
            prompt = f"""
            You are a lead generation expert. Based on the following company profile, generate 5-7 SPECIFIC potential customer companies that would be interested in their offerings.
            
            Company Profile:
            - Industry: {industry}
            - Offerings: {offerings_str}
            - Target Market: {target_market_str}
            - Company Size: {company_size}
            - Description: {company_description}
            
            For each potential customer, provide:
            1. Company Name (use REAL company names, not generic ones like 'Tech Solutions Inc')
            2. Industry they operate in (be specific)
            3. Why they would be interested in the offerings (be VERY specific about which offerings and how they would use them)
            4. Match Score (a percentage between 60-95% indicating how good of a match they are)
            5. Potential Value (estimated annual contract value, e.g. $10K-$50K, $50K-$100K, etc.)
            
            Return the results in this JSON format:
            {{"potential_matches": [
                {{"company_name": "Company Name", 
                  "industry": "Industry", 
                  "match_reason": "Detailed reason for match", 
                  "match_score": 85, 
                  "potential_value": "$10K-$50K"}},
                ...
            ]}}
            
            IMPORTANT GUIDELINES:
            - Focus on companies that would genuinely benefit from the specific offerings
            - Be very specific about WHY each company would benefit from the offerings
            - Ensure match scores accurately reflect how well the company aligns with the offerings
            - Provide realistic potential value estimates based on company size and industry
            - Use real company names that make sense for the industry
            
            Return ONLY the JSON with no additional text.
            """
            
            # Query the LLM
            response = query_llm(prompt)
            
            # Parse the response as JSON
            try:
                # Try to extract JSON from the response
                json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', response)
                if json_match:
                    response = json_match.group(1)
                
                data = json.loads(response)
                valid_matches = []
                
                # Validate and process each match
                if 'potential_matches' in data and isinstance(data['potential_matches'], list):
                    for match in data['potential_matches']:
                        # Validate required fields
                        if not all(k in match for k in ['company_name', 'industry', 'match_reason']):
                            continue
                            
                        # Ensure match_score is an integer
                        if 'match_score' not in match or not isinstance(match['match_score'], (int, float)):
                            try:
                                if isinstance(match.get('match_score'), str):
                                    match['match_score'] = int(match['match_score'].rstrip('%'))
                                else:
                                    match['match_score'] = random.randint(70, 90)
                            except:
                                match['match_score'] = random.randint(70, 90)
                        
                        # Ensure potential_value is present
                        if 'potential_value' not in match or not match['potential_value']:
                            if company_size == 'Large':
                                match['potential_value'] = '$100K-$500K'
                            elif company_size == 'Medium':
                                match['potential_value'] = '$50K-$100K'
                            else:
                                match['potential_value'] = '$10K-$50K'
                        
                        # Add offering category for compatibility with existing code
                        match['offering_category'] = 'llm_generated'
                        
                        # Add domain field if not present
                        if 'domain' not in match:
                            # Generate a domain from the company name
                            company_name = match['company_name'].lower()
                            # Remove non-alphanumeric characters and spaces
                            domain_base = ''.join(e for e in company_name if e.isalnum() or e.isspace())
                            domain_base = domain_base.replace(' ', '')
                            match['domain'] = f"{domain_base}.com"
                            
                        # Add size field if not present
                        if 'size' not in match:
                            # Use a size based on the potential value or a default
                            potential_value = match.get('potential_value', '')
                            if '$100K' in potential_value or '$500K' in potential_value:
                                match['size'] = 'Large'
                            elif '$50K' in potential_value:
                                match['size'] = 'Medium'
                            else:
                                match['size'] = 'Small'
                        
                        valid_matches.append(match)
                
                return valid_matches
            except json.JSONDecodeError as e:
                print(f"Failed to parse LLM response as JSON: {str(e)}")
                print(f"Response: {response[:200]}...")
                return self._generate_fallback_matches(industry, offerings, target_market, company_size)
                
        except Exception as e:
            print(f"Error generating matches with LLM: {str(e)}")
            return self._generate_fallback_matches(industry, offerings, target_market, company_size)
            
    def _generate_fallback_matches(self, industry, offerings, target_market, company_size):
        """Generate fallback matches when LLM fails"""
        print("Using fallback match generation")
        matches = []
        
        # Define some realistic company names based on industry
        industry_companies = {
            'Technology': ['Microsoft', 'Salesforce', 'Adobe', 'Oracle', 'IBM', 'ServiceNow'],
            'Healthcare': ['Mayo Clinic', 'Cleveland Clinic', 'Kaiser Permanente', 'UnitedHealth Group', 'CVS Health'],
            'Finance': ['JPMorgan Chase', 'Bank of America', 'Wells Fargo', 'Goldman Sachs', 'Morgan Stanley'],
            'Manufacturing': ['General Electric', 'Siemens', 'Boeing', 'Caterpillar', '3M Company'],
            'Retail': ['Walmart', 'Target', 'Amazon', 'Costco', 'Home Depot'],
            'Consulting': ['Deloitte', 'McKinsey', 'Boston Consulting Group', 'Accenture', 'KPMG']
        }
        
        # Get companies for this industry or use generic ones
        companies = industry_companies.get(industry, ['Company A', 'Company B', 'Company C', 'Company D', 'Company E'])
        
        # Generate 5 matches
        for i in range(5):
            if i < len(companies):
                company_name = companies[i]
            else:
                company_name = f"Company {chr(65+i)}"
                
            # Generate a match reason based on offerings
            if isinstance(offerings, list) and offerings:
                offering = offerings[i % len(offerings)]
                match_reason = f"Would benefit from {offering} to improve their operations and efficiency."
            else:
                match_reason = f"Would benefit from products/services in the {industry} sector."
            
            # Generate match score and potential value
            match_score = random.randint(70, 90)
            
            if company_size == 'Large':
                potential_value = '$100K-$500K'
            elif company_size == 'Medium':
                potential_value = '$50K-$100K'
            else:
                potential_value = '$10K-$50K'
            
            # Generate a domain from the company name
            company_name_lower = company_name.lower()
            # Remove non-alphanumeric characters and spaces
            domain_base = ''.join(e for e in company_name_lower if e.isalnum() or e.isspace())
            domain_base = domain_base.replace(' ', '')
            domain = f"{domain_base}.com"
            
            # Determine size based on potential value
            if '$100K' in potential_value or '$500K' in potential_value:
                size = 'Large'
            elif '$50K' in potential_value:
                size = 'Medium'
            else:
                size = 'Small'
                
            matches.append({
                'company_name': company_name,
                'industry': industry,
                'match_reason': match_reason,
                'match_score': match_score,
                'potential_value': potential_value,
                'offering_category': 'fallback_generated',
                'domain': domain,
                'size': size
            })
        
        return matches
    
    def _determine_potential_matches(self, industry, offerings, target_market, company_size):
        """Determine potential customer matches based on detailed analysis of offerings"""
        potential_matches = []
        
        # Convert offerings and target_market to lists if they're not already
        if isinstance(offerings, str):
            offerings = [offerings]
        if isinstance(target_market, str):
            target_market = [target_market]
            
        # Ensure we have valid offerings
        if not offerings or offerings == ["Unknown - LLM analysis required"]:
            # Provide industry-specific default offerings
            offerings = self._infer_offerings_from_industry(industry, 'B2B')
            
        # Analyze each offering to determine potential matches
        for offering in offerings:
            offering_lower = offering.lower()
            
            # Identify offering category and potential customer types
            offering_categories = self._categorize_offering(offering_lower)
            
            # For each category, identify potential companies that would need this offering
            for category in offering_categories:
                # Get companies that match this category
                matches = self._find_companies_for_category(category, industry, company_size)
                
                for match in matches:
                    # Calculate match score based on relevance
                    match_score = self._calculate_match_score(match, offering, target_market, company_size)
                    
                    # Generate specific reason why this company would need the offering
                    match_reason = self._generate_specific_match_reason(match, offering, category)
                    
                    potential_matches.append({
                        'company_name': match['name'],
                        'domain': match['domain'],
                        'industry': match['industry'],
                        'size': match['size'],
                        'match_score': match_score,
                        'match_reason': match_reason,
                        'offering_category': category
                    })
        
        # Remove duplicates (same company might match multiple offerings)
        unique_matches = []
        seen_domains = set()
        
        for match in potential_matches:
            if match['domain'] not in seen_domains:
                seen_domains.add(match['domain'])
                unique_matches.append(match)
        
        # Ensure we have at least some matches
        if not unique_matches:
            # Add some generic matches based on industry
            for i in range(3):
                if industry in self.industry_companies and i < len(self.industry_companies[industry]):
                    company_name = self.industry_companies[industry][i]
                    domain = self.industry_domains[industry][i]
                    
                    unique_matches.append({
                        'company_name': company_name,
                        'domain': domain,
                        'industry': industry,
                        'size': self._get_random_company_size(),
                        'match_score': 65,  # Medium match score
                        'match_reason': f"Companies in the {industry} industry often need {offerings[0] if offerings else 'professional services'}",
                        'offering_category': 'industry_match'
                    })
        
        return unique_matches
        
    def _categorize_offering(self, offering):
        """Categorize an offering to determine potential customer types"""
        categories = []
        
        # Technology-related offerings
        if any(term in offering for term in ['software', 'app', 'platform', 'tech', 'digital', 'ai', 'data', 'cloud', 'automation']):
            categories.extend(['tech_solution', 'digital_transformation'])
            
        # Service-related offerings
        if any(term in offering for term in ['service', 'consulting', 'support', 'management', 'strategy', 'advisory']):
            categories.extend(['professional_service', 'business_advisory'])
            
        # Product-related offerings
        if any(term in offering for term in ['product', 'equipment', 'device', 'hardware', 'tool', 'system']):
            categories.extend(['product_solution', 'equipment_provider'])
            
        # Marketing-related offerings
        if any(term in offering for term in ['marketing', 'brand', 'advertising', 'promotion', 'content', 'media']):
            categories.extend(['marketing_solution', 'brand_development'])
            
        # Financial-related offerings
        if any(term in offering for term in ['finance', 'payment', 'banking', 'investment', 'accounting', 'tax']):
            categories.extend(['financial_service', 'payment_solution'])
            
        # If no specific categories identified, use generic ones
        if not categories:
            categories = ['business_solution', 'industry_service']
            
        return categories
    def _find_companies_for_category(self, category, source_industry, company_size):
        """Find companies that would be interested in a specific offering category"""
        companies = []
        
        # Define which industries would be interested in each category
        category_to_industries = {
            'tech_solution': ['Technology', 'Finance', 'Healthcare', 'Retail', 'Education'],
            'digital_transformation': ['Manufacturing', 'Finance', 'Healthcare', 'Retail'],
            'professional_service': ['Consulting', 'Finance', 'Technology', 'Healthcare'],
            'business_advisory': ['Finance', 'Technology', 'Manufacturing', 'Retail'],
            'product_solution': ['Manufacturing', 'Retail', 'Healthcare', 'Technology'],
            'equipment_provider': ['Manufacturing', 'Healthcare', 'Education'],
            'marketing_solution': ['Retail', 'Technology', 'Finance', 'Healthcare'],
            'brand_development': ['Retail', 'Technology', 'Finance'],
            'financial_service': ['Finance', 'Technology', 'Retail', 'Healthcare'],
            'payment_solution': ['Retail', 'Finance', 'Technology'],
            'business_solution': ['Technology', 'Finance', 'Consulting', 'Manufacturing'],
            'industry_service': ['Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail']
        }
        
        # Get target industries for this category
        target_industries = category_to_industries.get(category, ['Technology', 'Finance', 'Retail'])
        
        # Remove the source industry to avoid suggesting competitors
        if source_industry in target_industries:
            target_industries.remove(source_industry)
            
        # If we have no industries left, add some generic ones
        if not target_industries:
            target_industries = ['Technology', 'Finance', 'Retail']
            
        # For each target industry, add companies
        for industry in target_industries:
            if industry in self.industry_companies:
                # Get all companies for this industry
                for i in range(len(self.industry_companies[industry])):
                    company_name = self.industry_companies[industry][i]
                    domain = self.industry_domains[industry][i]
                    
                    # Determine company size - try to match with source company size
                    size = self._get_complementary_size(company_size)
                    
                    companies.append({
                        'name': company_name,
                        'domain': domain,
                        'industry': industry,
                        'size': size
                    })
        
        # Shuffle to get different results each time
        random.shuffle(companies)
        
        return companies[:5]  # Return up to 5 companies
        
    def _calculate_match_score(self, match, offering, target_market, company_size):
        """Calculate a match score (0-100) based on relevance"""
        score = 70  # Start with a base score
        
        # Adjust based on industry relevance
        industry_relevance = {
            'tech_solution': {'Technology': 20, 'Finance': 15, 'Healthcare': 10, 'Retail': 10, 'Education': 5},
            'digital_transformation': {'Manufacturing': 20, 'Finance': 15, 'Healthcare': 15, 'Retail': 10},
            'professional_service': {'Consulting': 20, 'Finance': 15, 'Technology': 10, 'Healthcare': 5},
            'business_advisory': {'Finance': 20, 'Technology': 15, 'Manufacturing': 10, 'Retail': 5},
            'product_solution': {'Manufacturing': 20, 'Retail': 15, 'Healthcare': 10, 'Technology': 5},
            'equipment_provider': {'Manufacturing': 20, 'Healthcare': 15, 'Education': 10},
            'marketing_solution': {'Retail': 20, 'Technology': 15, 'Finance': 10, 'Healthcare': 5},
            'brand_development': {'Retail': 20, 'Technology': 15, 'Finance': 10},
            'financial_service': {'Finance': 20, 'Technology': 15, 'Retail': 10, 'Healthcare': 5},
            'payment_solution': {'Retail': 20, 'Finance': 15, 'Technology': 10},
            'business_solution': {'Technology': 15, 'Finance': 15, 'Consulting': 15, 'Manufacturing': 10},
            'industry_service': {'Technology': 15, 'Healthcare': 15, 'Finance': 15, 'Manufacturing': 10, 'Retail': 10}
        }
        
        # Get the offering category
        offering_categories = self._categorize_offering(offering.lower())
        offering_category = offering_categories[0] if offering_categories else 'business_solution'
        
        # Add industry relevance score
        if offering_category in industry_relevance:
            score += industry_relevance[offering_category].get(match['industry'], 0)
            
        # Adjust based on size compatibility
        if match['size'] == company_size:
            score += 10  # Perfect size match
        elif (match['size'] == 'Large' and company_size == 'Medium') or \
             (match['size'] == 'Medium' and company_size == 'Small'):
            score += 5  # Good size match (larger customer for smaller provider)
            
        # Cap the score at 95 to leave room for randomness
        score = min(score, 95)
        
        # Add some randomness (±5 points)
        score += random.randint(-5, 5)
        
        # Ensure score is within 0-100 range
        return max(0, min(100, score))
    def _generate_specific_match_reason(self, match, offering, category):
        """Generate a specific reason why this company would need the offering"""
        industry = match['industry']
        size = match['size']
        
        # Industry-specific reasons
        industry_reasons = {
            'Technology': [
                f"As a {size.lower()} technology company, {match['name']} could leverage your {offering} to enhance their product development",
                f"{match['name']} is likely seeking solutions like your {offering} to stay competitive in the fast-moving tech industry",
                f"Technology firms like {match['name']} often need specialized {offering} to improve their operational efficiency"
            ],
            'Finance': [
                f"Financial institutions like {match['name']} require robust {offering} to ensure regulatory compliance and security",
                f"{match['name']} could benefit from your {offering} to streamline their customer service operations",
                f"In the finance sector, {match['name']} faces challenges that your {offering} is specifically designed to address"
            ],
            'Healthcare': [
                f"Healthcare providers like {match['name']} need reliable {offering} to improve patient outcomes",
                f"{match['name']} could use your {offering} to enhance their healthcare delivery while reducing costs",
                f"The healthcare industry faces unique challenges that your {offering} can help {match['name']} overcome"
            ],
            'Retail': [
                f"Retailers like {match['name']} can use your {offering} to enhance customer experience and drive sales",
                f"{match['name']} needs solutions like your {offering} to compete effectively in today's digital retail landscape",
                f"Your {offering} could help {match['name']} optimize their inventory management and supply chain"
            ],
            'Manufacturing': [
                f"Manufacturing companies like {match['name']} can improve production efficiency with your {offering}",
                f"{match['name']} could leverage your {offering} to reduce waste and optimize their manufacturing processes",
                f"Your {offering} addresses key challenges that {match['name']} faces in the manufacturing industry"
            ],
            'Education': [
                f"Educational institutions like {match['name']} can enhance learning outcomes with your {offering}",
                f"{match['name']} could use your {offering} to improve administrative efficiency and focus on their core mission",
                f"Your {offering} provides solutions to the unique challenges {match['name']} faces in the education sector"
            ],
            'Consulting': [
                f"Consulting firms like {match['name']} can deliver more value to their clients using your {offering}",
                f"{match['name']} could integrate your {offering} into their service offerings to clients",
                f"Your {offering} addresses operational challenges that consulting firms like {match['name']} commonly face"
            ]
        }
        
        # Category-specific reasons
        category_reasons = {
            'tech_solution': [
                f"Your technology solution could help {match['name']} modernize their operations",
                f"{match['name']} is likely looking for innovative solutions like yours to stay competitive"
            ],
            'digital_transformation': [
                f"As companies like {match['name']} undergo digital transformation, your offering provides essential capabilities",
                f"{match['name']} needs partners with expertise in digital transformation to evolve their business model"
            ],
            'professional_service': [
                f"Your professional services align with {match['name']}'s need for specialized expertise",
                f"{match['name']} could benefit from your industry knowledge and professional guidance"
            ],
            'business_advisory': [
                f"Your strategic advisory services could help {match['name']} navigate industry challenges",
                f"{match['name']} would benefit from your business insights to optimize their operations"
            ],
            'product_solution': [
                f"Your product offering addresses specific needs in {match['name']}'s operational workflow",
                f"{match['name']} is likely seeking products like yours to enhance their capabilities"
            ]
        }
        
        # Select reasons based on industry and category
        reasons = []
        
        if industry in industry_reasons:
            reasons.extend(industry_reasons[industry])
            
        if category in category_reasons:
            reasons.extend(category_reasons[category])
            
        # If we don't have specific reasons, use generic ones
        if not reasons:
            reasons = [
                f"{match['name']} could benefit from your {offering} to improve their business operations",
                f"Your {offering} addresses challenges that companies like {match['name']} commonly face",
                f"As a {size.lower()} company in the {industry.lower()} industry, {match['name']} needs solutions like your {offering}"
            ]
            
        # Return a random reason
        return random.choice(reasons)
        
    def _get_complementary_size(self, company_size):
        """Get a complementary company size that would be a good match"""
        if company_size == 'Small':
            return random.choice(['Small', 'Medium', 'Medium'])
        elif company_size == 'Medium':
            return random.choice(['Medium', 'Large', 'Small'])
        elif company_size == 'Large':
            return random.choice(['Large', 'Medium', 'Medium'])
        else:
            return random.choice(['Small', 'Medium', 'Large'])
            
    def _get_random_company_size(self):
        """Get a random company size with weighted distribution"""
        return random.choice(['Small', 'Medium', 'Medium', 'Large'])
        
    def _calculate_potential_value(self, match, company_analysis):
        """Calculate the potential value of this lead (Low, Medium, High)"""
        # Base value on match score
        if match['match_score'] >= 85:
            return "High"
        elif match['match_score'] >= 70:
            return "Medium"
        else:
            return "Low"
    def _get_target_roles_for_match(self, match):
        """Get appropriate decision maker roles based on the specific match"""
        industry = match['industry']
        category = match.get('offering_category', 'business_solution')
        
        # Industry-specific roles
        industry_roles = {
            'Technology': ['CTO', 'CIO', 'VP of Engineering', 'IT Director', 'Head of Digital'],
            'Healthcare': ['Medical Director', 'Chief of Operations', 'Head of Patient Services', 'IT Director', 'Clinical Director'],
            'Finance': ['CFO', 'Head of Risk', 'Investment Director', 'VP of Operations', 'Technology Director'],
            'Education': ['Dean', 'Principal', 'Director of IT', 'Head of Operations', 'Chief Academic Officer'],
            'Manufacturing': ['COO', 'Production Director', 'VP of Operations', 'Supply Chain Manager', 'Plant Manager'],
            'Retail': ['CMO', 'Head of Merchandising', 'Operations Director', 'Digital Director', 'Customer Experience Manager'],
            'Consulting': ['Managing Partner', 'Practice Lead', 'Director of Operations', 'Business Development Manager', 'Senior Consultant']
        }
        
        # Category-specific roles
        category_roles = {
            'tech_solution': ['CTO', 'CIO', 'IT Director', 'Digital Transformation Lead'],
            'digital_transformation': ['CIO', 'Digital Director', 'Head of Innovation', 'Technology Transformation Lead'],
            'professional_service': ['COO', 'VP of Operations', 'Director of Professional Services'],
            'business_advisory': ['CEO', 'COO', 'Strategy Director', 'Business Development Lead'],
            'product_solution': ['Product Director', 'Operations Manager', 'Supply Chain Director'],
            'equipment_provider': ['Operations Director', 'Facilities Manager', 'Production Manager'],
            'marketing_solution': ['CMO', 'Marketing Director', 'Brand Manager', 'Digital Marketing Lead'],
            'brand_development': ['CMO', 'Brand Director', 'Marketing Manager'],
            'financial_service': ['CFO', 'Finance Director', 'Controller', 'Treasurer'],
            'payment_solution': ['CFO', 'Finance Director', 'Payments Manager'],
            'business_solution': ['COO', 'Operations Director', 'Business Process Manager'],
            'industry_service': ['COO', 'Operations Director', 'Service Director']
        }
        
        # Combine industry and category roles
        roles = []
        
        if industry in industry_roles:
            roles.extend(industry_roles[industry][:2])  # Take top 2 roles from industry
            
        if category in category_roles:
            roles.extend(category_roles[category][:2])  # Take top 2 roles from category
            
        # If we don't have specific roles, use generic ones
        if not roles:
            roles = ['COO', 'Operations Director', 'Business Development Manager']
            
        # Remove duplicates and return
        return list(dict.fromkeys(roles))
    
    def _create_lead_for_role(self, role, domain, company_analysis):
        """Create a lead profile for a specific role"""
        # Generate a name for this role
        name = self._generate_name_for_role(role)
        first_name, last_name = name.split(' ', 1)
        
        # Generate email
        email = self._generate_email(first_name, last_name, domain)
        
        # Generate outreach suggestions
        outreach_suggestions = self._generate_outreach_suggestions(role, company_analysis)
        
        # Create the lead profile
        lead = {
            'name': name,
            'role': role,
            'email': email,
            'outreach_suggestions': outreach_suggestions
        }
        
        return lead
    
    def _generate_name_for_role(self, role):
        """Generate a realistic name for a role"""
        # Common first names
        first_names = [
            'James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph', 'Thomas', 'Charles',
            'Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen',
            'Christopher', 'Daniel', 'Matthew', 'Anthony', 'Mark', 'Donald', 'Steven', 'Paul', 'Andrew', 'Joshua',
            'Michelle', 'Amanda', 'Kimberly', 'Melissa', 'Stephanie', 'Rebecca', 'Laura', 'Emily', 'Megan', 'Hannah'
        ]
        
        # Common last names
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor',
            'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin', 'Thompson', 'Garcia', 'Martinez', 'Robinson',
            'Clark', 'Rodriguez', 'Lewis', 'Lee', 'Walker', 'Hall', 'Allen', 'Young', 'Hernandez', 'King',
            'Wright', 'Lopez', 'Hill', 'Scott', 'Green', 'Adams', 'Baker', 'Gonzalez', 'Nelson', 'Carter'
        ]
        
        # Randomly select a first and last name
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        return f"{first_name} {last_name}"
    
    def _generate_email(self, first_name, last_name, domain):
        """Generate potential email addresses based on common patterns"""
        # Select a random email pattern
        pattern = random.choice(self.email_patterns)
        
        # Apply the pattern
        email = pattern.format(
            first=first_name.lower(),
            last=last_name.lower(),
            first_initial=first_name[0].lower(),
            last_initial=last_name[0].lower(),
            domain=domain
        )
        
        return email
    
    def _generate_outreach_suggestions(self, role, company_analysis):
        """Generate outreach suggestions based on role and company analysis"""
        # Extract key information
        industry = company_analysis.get('industry', 'Unknown')
        offerings = company_analysis.get('offerings', [])
        if isinstance(offerings, str):
            offerings = [offerings]
        
        # Role-specific suggestions
        role_suggestions = {
            'CTO': [
                "Focus on technical benefits and integration capabilities",
                "Highlight how your solution addresses technical challenges",
                "Discuss scalability and future-proofing aspects"
            ],
            'CIO': [
                "Emphasize ROI and business value of your technical solution",
                "Address security and compliance considerations",
                "Discuss how your solution fits into their overall IT strategy"
            ],
            'COO': [
                "Focus on operational efficiency improvements",
                "Highlight cost-saving aspects of your solution",
                "Discuss implementation timeline and minimal disruption"
            ],
            'CMO': [
                "Emphasize customer experience benefits",
                "Highlight marketing and brand enhancement capabilities",
                "Discuss analytics and measurement aspects"
            ],
            'CFO': [
                "Focus on financial benefits and ROI",
                "Highlight cost reduction and revenue growth potential",
                "Discuss pricing model and payment flexibility"
            ]
        }
        
        # Generic suggestions based on role type
        if 'CTO' in role or 'IT' in role or 'Technical' in role or 'Technology' in role or 'Digital' in role:
            suggestions = role_suggestions.get('CTO', [])
        elif 'CIO' in role:
            suggestions = role_suggestions.get('CIO', [])
        elif 'COO' in role or 'Operations' in role:
            suggestions = role_suggestions.get('COO', [])
        elif 'CMO' in role or 'Marketing' in role:
            suggestions = role_suggestions.get('CMO', [])
        elif 'CFO' in role or 'Finance' in role:
            suggestions = role_suggestions.get('CFO', [])
        else:
            suggestions = [
                "Highlight how your solution addresses their specific industry challenges",
                "Focus on the business value and ROI of your offering",
                "Personalize your approach based on their role and responsibilities"
            ]
        
        # Add offering-specific suggestions
        if offerings and offerings != ["Unknown - LLM analysis required"]:
            offering = offerings[0] if offerings else "solution"
            suggestions.append(f"Mention specific benefits of your {offering} for their role")
        
        return suggestions
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
def generate_leads(company_analysis, domain, use_cache=True):
    """Generate leads based on company analysis"""
    generator = LeadGenerator(use_cache=use_cache)
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
            'company_size': 'Medium',
            'pain_points': 'Legacy system integration'
        }
        domain = "example.com"
    
    result = generate_leads(company_analysis, domain)
    print(json.dumps(result, indent=2))
