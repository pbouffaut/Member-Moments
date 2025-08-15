import requests
import json
import re
from typing import Dict, List, Optional, Tuple
import time
from urllib.parse import quote_plus

class GoogleKnowledgeGraphDisambiguator:
    """
    Uses Google Knowledge Graph API to disambiguate company names and verify entities
    Much broader coverage than Wikidata, especially for smaller companies
    """
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://kgsearch.googleapis.com/v1/entities:search"
        
    def disambiguate_company(self, company_name: str, article_context: str = "") -> Dict:
        """
        Disambiguate a company name using Google Knowledge Graph API
        Returns disambiguation results with confidence scores
        """
        if not self.api_key:
            return self._no_api_key_fallback(company_name)
        
        try:
            # Search for the company name with context
            search_results = self._search_entities(company_name, article_context)
            
            if not search_results:
                return self._no_results_fallback(company_name)
            
            # Filter and rank results
            company_results = self._filter_company_results(search_results, company_name)
            
            if not company_results:
                # Fallback to basic disambiguation logic
                return self._fallback_disambiguation(company_name, article_context)
            
            # Find best match
            best_match = self._find_best_match(company_results, company_name, article_context)
            
            return {
                'is_verified': best_match['confidence'] > 0.7,
                'confidence': best_match['confidence'],
                'entity_name': best_match['name'],
                'entity_type': best_match['types'],
                'description': best_match['description'],
                'url': best_match['url'],
                'wikidata_id': best_match['id'],  # Google's entity ID
                'disambiguation_results': company_results,
                'source': 'google_knowledge_graph'
            }
            
        except Exception as e:
            print(f"[GOOGLE_KG] Error during disambiguation: {e}")
            return self._fallback_disambiguation(company_name, article_context)
    
    def _fallback_disambiguation(self, company_name: str, article_context: str = "") -> Dict:
        """Fallback disambiguation using basic logic when Google KG fails"""
        # Check if this is a generic word that commonly causes false positives
        if self._is_generic_word(company_name):
            return {
                'is_verified': False,
                'confidence': 0.0,
                'entity_name': company_name,
                'entity_type': [],
                'description': 'Generic word - likely false positive',
                'url': '',
                'wikidata_id': '',
                'disambiguation_results': [],
                'source': 'fallback_logic'
            }
        
        # Basic company verification logic
        is_verified = False
        confidence = 0.3
        description = "Basic verification completed"
        
        # Check if company name looks like a person's name
        if self._is_likely_person_name(company_name):
            confidence = 0.1
            description = "Company name resembles person name - low confidence"
        else:
            # Check for business context in article
            if self._has_business_context(article_context):
                confidence = 0.5
                description = "Business context detected - medium confidence"
            else:
                confidence = 0.2
                description = "No business context - low confidence"
        
        return {
            'is_verified': confidence >= 0.6,
            'confidence': confidence,
            'entity_name': company_name,
            'entity_type': [],
            'description': description,
            'url': '',
            'wikidata_id': '',
            'disambiguation_results': [],
            'source': 'fallback_logic'
        }
    
    def _search_entities(self, query: str, context: str = "") -> List[Dict]:
        """Search Google Knowledge Graph for entities matching the query"""
        try:
            # Build search query with context if available
            search_query = query
            if context:
                # Add context words to improve search
                context_words = context.split()[:5]  # First 5 words
                search_query = f"{query} {' '.join(context_words)}"
            
            # For company searches, add business context
            if not context or len(context) < 20:
                search_query = f"{query} company business organization"
            
            params = {
                'query': search_query,
                'key': self.api_key,
                'limit': 20,  # Increase limit to get more results
                'types': 'Organization|Corporation|Company|EducationalOrganization',
                'indent': True
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'itemListElement' in data:
                return data['itemListElement']
            
            # If no results with types filter, try without it
            params.pop('types')
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'itemListElement' in data:
                return data['itemListElement']
            
            return []
            
        except Exception as e:
            print(f"[GOOGLE_KG] Search error: {e}")
            return []
    
    def _filter_company_results(self, search_results: List[Dict], company_name: str) -> List[Dict]:
        """Filter results to focus on company/organization entities"""
        company_results = []
        
        for item in search_results:
            if 'result' in item:
                result = item['result']
                # Check if it's likely a company/organization
                if self._is_likely_company(result, company_name):
                    # Add the result score for ranking
                    result['score'] = item.get('resultScore', 0)
                    company_results.append(result)
        
        return company_results
    
    def _is_likely_company(self, result: Dict, company_name: str) -> bool:
        """Check if the result is likely a company/organization"""
        description = result.get('description', '').lower()
        name = result.get('name', '').lower()
        
        # Company/organization indicators
        company_indicators = [
            'company', 'corporation', 'inc', 'llc', 'ltd', 'startup', 'tech',
            'software', 'platform', 'service', 'organization', 'business',
            'academy', 'institute', 'university', 'college', 'school',
            'agency', 'foundation', 'association', 'group', 'team'
        ]
        
        # Check description for company indicators
        for indicator in company_indicators:
            if indicator in description:
                return True
        
        # Check if name matches company name well
        if self._name_similarity(company_name, name) > 0.6:
            return True
        
        # If we have a good name match and any description, consider it
        if self._name_similarity(company_name, name) > 0.8 and description:
            return True
        
        return False
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        name1_lower = name1.lower().strip()
        name2_lower = name2.lower().strip()
        
        if name1_lower == name2_lower:
            return 1.0
        
        # Check if one contains the other
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return 0.8
        
        # Check word overlap
        words1 = set(name1_lower.split())
        words2 = set(name2_lower.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _get_entity_details(self, entity_id: str) -> Optional[Dict]:
        """Get detailed information about a Wikidata entity"""
        try:
            url = f"{self.entity_url}{entity_id}.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            entities = data.get('entities', {})
            entity = entities.get(entity_id, {})
            
            if not entity:
                return None
            
            # Extract entity information
            labels = entity.get('labels', {})
            descriptions = entity.get('descriptions', {})
            claims = entity.get('claims', {})
            
            # Get English label and description
            label = labels.get('en', {}).get('value', '') if 'en' in labels else ''
            description = descriptions.get('en', {}).get('value', '') if 'en' in descriptions else ''
            
            # Get entity types
            types = self._extract_entity_types(claims)
            
            # Get website URL if available
            website = self._extract_website(claims)
            
            return {
                'wikidata_id': entity_id,
                'name': label,
                'description': description,
                'types': types,
                'website': website,
                'url': f"{self.entity_url}{entity_id}",
                'claims': claims
            }
            
        except Exception as e:
            print(f"[WIKIDATA] Error getting entity details: {e}")
            return None
    
    def _extract_entity_types(self, claims: Dict) -> List[str]:
        """Extract entity types from Wikidata claims"""
        types = []
        
        # Check for instance of (P31) claims
        if 'P31' in claims:
            for claim in claims['P31']:
                if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                    value = claim['mainsnak']['datavalue'].get('value', {})
                    if isinstance(value, dict) and 'id' in value:
                        entity_id = value['id']
                        # Map common entity types
                        type_mapping = {
                            'Q43229': 'Organization',
                            'Q783794': 'Company',
                            'Q15636249': 'Startup',
                            'Q4671277': 'Corporation',
                            'Q159364': 'Educational Institution',
                            'Q16917': 'University',
                            'Q4671277': 'Corporation',
                            'Q163740': 'Non-profit Organization'
                        }
                        if entity_id in type_mapping:
                            types.append(type_mapping[entity_id])
        
        return types
    
    def _extract_website(self, claims: Dict) -> str:
        """Extract website URL from Wikidata claims"""
        if 'P856' in claims:  # Official website property
            for claim in claims['P856']:
                if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                    value = claim['mainsnak']['datavalue'].get('value', '')
                    if value:
                        return value
        return ""
    
    def _find_best_match(self, results: List[Dict], company_name: str, context: str = "") -> Dict:
        """Find the best matching entity from the results"""
        if not results:
            return self._default_result(company_name)
        
        # Score each result
        scored_results = []
        for result in results:
            score = self._calculate_match_score(result, company_name, context)
            scored_results.append((result, score))
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        best_result, best_score = scored_results[0]
        
        return {
            'id': best_result.get('id', ''),
            'name': best_result.get('name', ''),
            'description': best_result.get('description', ''),
            'types': best_result.get('@type', []),
            'url': best_result.get('url', ''),
            'confidence': best_score
        }
    
    def _calculate_match_score(self, result: Dict, company_name: str, context: str = "") -> float:
        """Calculate a match score for the entity"""
        score = 0.0
        
        # Name similarity (40% of score)
        name_sim = self._name_similarity(company_name, result.get('name', ''))
        score += name_sim * 0.4
        
        # Type relevance (30% of score)
        type_score = 0.0
        company_types = ['Organization', 'Corporation', 'Company', 'EducationalOrganization']
        for entity_type in result.get('@type', []):
            if entity_type in company_types:
                type_score = 1.0
                break
        score += type_score * 0.3
        
        # Description relevance (20% of score)
        desc_score = 0.0
        if result.get('description'):
            desc_lower = result['description'].lower()
            company_indicators = ['company', 'business', 'organization', 'startup', 'tech']
            for indicator in company_indicators:
                if indicator in desc_lower:
                    desc_score += 0.2
            desc_score = min(desc_score, 1.0)
        score += desc_score * 0.2
        
        # Google's result score (10% of score)
        google_score = 0.0
        if 'score' in result:
            # Normalize Google's score (usually 0-1000)
            google_score = min(result['score'] / 1000.0, 1.0)
        score += google_score * 0.1
        
        return min(score, 1.0)
    
    def _is_likely_person_name(self, text: str) -> bool:
        """Check if text looks like a person's name"""
        text = text.strip()
        
        # Check for titles that indicate a person
        person_titles = ['mr', 'mrs', 'ms', 'dr', 'professor', 'prof', 'sir', 'madam']
        words = text.lower().split()
        if words and words[0] in person_titles:
            return True
        
        # Check if it follows "First Last" pattern with proper capitalization
        parts = text.split()
        if len(parts) == 2:
            if (parts[0][0].isupper() and parts[0][1:].islower() and 
                parts[1][0].isupper() and parts[1][1:].islower()):
                return True
        
        return False
    
    def _has_business_context(self, text: str) -> bool:
        """Check if text contains business-related context"""
        if not text:
            return False
            
        text_lower = text.lower()
        
        # Business context indicators
        business_indicators = [
            'company', 'corporation', 'inc', 'llc', 'ltd', 'startup', 'tech',
            'software', 'platform', 'service', 'announces', 'launches', 'raises',
            'funding', 'partnership', 'merger', 'acquisition', 'appoints', 'ceo',
            'cto', 'headquarters', 'office', 'location', 'expansion'
        ]
        
        # Count business indicators
        business_score = 0
        for indicator in business_indicators:
            if indicator in text_lower:
                business_score += 1
        
        return business_score >= 2
    
    def _is_generic_word(self, text: str) -> bool:
        """Check if text is a generic word that could cause false positives"""
        text_lower = text.lower().strip()
        
        # Static list of definitely generic words (fast fallback)
        definitely_generic = [
            'yes', 'no', 'maybe', 'sure', 'ok', 'fine', 'good', 'bad',
            'up', 'down', 'in', 'out', 'left', 'right', 'high', 'low'
        ]
        
        if text_lower in definitely_generic:
            return True
        
        # For other words, use dynamic analysis if we have API access
        if self.api_key:
            return self._is_generic_word_dynamic(text)
        
        # Fallback to static list for common business false positives
        business_generic = [
            'advance', 'agency', 'new', 'old', 'big', 'small',
            'company', 'business', 'organization', 'team', 'group'
        ]
        
        return text_lower in business_generic
    
    def _is_generic_word_dynamic(self, text: str) -> bool:
        """Dynamically determine if a word is generic using Google Knowledge Graph analysis"""
        try:
            # Search for the word without business context
            search_results = self._search_entities_raw(text)
            
            if not search_results:
                return False  # No results, not necessarily generic
            
            # Analyze the diversity and relevance of results
            return self._analyze_result_diversity(search_results, text)
            
        except Exception as e:
            print(f"[GOOGLE_KG] Dynamic generic word analysis failed: {e}")
            return False  # Fallback to static analysis
    
    def _search_entities_raw(self, query: str) -> List[Dict]:
        """Search Google Knowledge Graph without business context modifiers"""
        try:
            params = {
                'query': query,
                'key': self.api_key,
                'limit': 15,
                'indent': True
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'itemListElement' in data:
                return data['itemListElement']
            
            return []
            
        except Exception as e:
            print(f"[GOOGLE_KG] Raw search error: {e}")
            return []
    
    def _analyze_result_diversity(self, search_results: List[Dict], query: str) -> bool:
        """Analyze search results to determine if the query is generic/ambiguous"""
        if len(search_results) < 3:
            return False  # Few results, likely specific
        
        # Extract entity types and categories
        entity_types = []
        descriptions = []
        names = []
        
        for item in search_results[:10]:  # Analyze first 10 results
            if 'result' in item:
                result = item['result']
                
                # Get entity types
                if 'type' in result:
                    entity_types.extend(result['type'])
                
                # Get descriptions
                if 'description' in result:
                    descriptions.append(result['description'].lower())
                
                # Get names
                if 'name' in result:
                    names.append(result['name'].lower())
        
        # Calculate diversity metrics
        type_diversity = len(set(entity_types))
        name_diversity = len(set(names))
        
        # Check if results are from completely different domains
        domain_keywords = {
            'sports': ['game', 'team', 'player', 'tournament', 'league', 'championship'],
            'business': ['company', 'corporation', 'business', 'office', 'ceo', 'startup'],
            'geography': ['city', 'town', 'country', 'region', 'state', 'province'],
            'entertainment': ['movie', 'show', 'actor', 'director', 'film', 'series'],
            'technology': ['software', 'app', 'platform', 'tech', 'digital', 'online']
        }
        
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for desc in descriptions if any(kw in desc for kw in keywords))
            domain_scores[domain] = score
        
        # If we have high diversity across multiple domains, it's likely generic
        active_domains = sum(1 for score in domain_scores.values() if score > 0)
        
        # Generic word indicators:
        # 1. High type diversity (many different types of entities)
        # 2. High name diversity (names don't relate to each other)
        # 3. Multiple active domains (results from different fields)
        # 4. Low relevance scores (Google KG isn't confident about matches)
        
        is_generic = (
            type_diversity > 5 or  # Many different entity types
            name_diversity > 8 or  # Very diverse names
            active_domains > 3 or  # Results from many different domains
            (type_diversity > 3 and active_domains > 2)  # Combination of factors
        )
        
        return is_generic

    def _no_api_key_fallback(self, company_name: str) -> Dict:
        """Fallback when no API key is provided"""
        return {
            'is_verified': False,
            'confidence': 0.3,
            'entity_name': company_name,
            'entity_type': [],
            'description': 'Google Knowledge Graph API key not provided',
            'url': '',
            'wikidata_id': '',
            'disambiguation_results': [],
            'source': 'google_knowledge_graph'
        }
    
    def _no_results_fallback(self, company_name: str) -> Dict:
        """Fallback when no search results found"""
        # Check if this looks like a generic word that could cause false positives
        if self._is_generic_word(company_name):
            return {
                'is_verified': False,
                'confidence': 0.0,
                'entity_name': company_name,
                'entity_type': [],
                'description': 'Generic word - likely false positive',
                'url': '',
                'wikidata_id': '',
                'disambiguation_results': [],
                'source': 'google_knowledge_graph'
            }
        else:
            return {
                'is_verified': False,
                'confidence': 0.0,
                'entity_name': company_name,
                'entity_type': [],
                'description': 'No Google Knowledge Graph results found',
                'url': '',
                'wikidata_id': '',
                'disambiguation_results': [],
                'source': 'google_knowledge_graph'
            }
    
    def _no_company_results_fallback(self, company_name: str) -> Dict:
        """Fallback when no company results found"""
        return {
            'is_verified': False,
            'confidence': 0.2,
            'entity_name': company_name,
            'entity_type': [],
            'description': 'No company entities found in Google Knowledge Graph',
            'url': '',
            'wikidata_id': '',
            'disambiguation_results': [],
            'source': 'google_knowledge_graph'
        }
    
    def _error_fallback(self, company_name: str, error: str) -> Dict:
        """Fallback when errors occur"""
        return {
            'is_verified': False,
            'confidence': 0.1,
            'entity_name': company_name,
            'entity_type': [],
            'description': f'Error: {error}',
            'url': '',
            'wikidata_id': '',
            'disambiguation_results': [],
            'source': 'google_knowledge_graph'
        }
    
    def _default_result(self, company_name: str) -> Dict:
        """Default result when no matches found"""
        return {
            'wikidata_id': '',
            'name': company_name,
            'description': '',
            'types': [],
            'url': '',
            'confidence': 0.0
        }

def test_google_knowledge_graph_disambiguation():
    """Test the Google Knowledge Graph disambiguation system"""
    # You'll need to set your API key
    api_key = "AIzaSyBDXQJdBMTcRoqY_qMDZZbK5eT8-rLYOHQ"
    
    if api_key == "YOUR_GOOGLE_KNOWLEDGE_GRAPH_API_KEY":
        print("Please set your Google Knowledge Graph API key to test")
        return
    
    disambiguator = GoogleKnowledgeGraphDisambiguator(api_key)
    
    # Test cases
    test_cases = [
        ("Advance Academy", "Advance Academy launches new online courses"),
        ("Apple", "Apple announces new iPhone"),
        ("advance", "Team advances to finals"),  # Should NOT match company
        ("Agency House", "Agency House expands operations"),
        ("Microsoft", "Microsoft reports earnings"),
        ("Tesla", "Tesla launches new model")
    ]
    
    for company_name, context in test_cases:
        print(f"\n--- Testing: {company_name} ---")
        result = disambiguator.disambiguate_company(company_name, context)
        print(f"Verified: {result['is_verified']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Entity: {result['entity_name']}")
        print(f"Type: {result['entity_type']}")
        print(f"Description: {result['description']}")
        print(f"Wikidata ID: {result['wikidata_id']}")
        print(f"URL: {result['url']}")

if __name__ == "__main__":
    test_google_knowledge_graph_disambiguation()
