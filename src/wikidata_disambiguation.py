import requests
import json
import re
from typing import Dict, List, Optional, Tuple
import time
from urllib.parse import quote_plus

class WikidataDisambiguator:
    """
    Uses Wikidata API to disambiguate company names and verify entities
    Completely free, no API key required
    """
    
    def __init__(self):
        self.base_url = "https://www.wikidata.org/w/api.php"
        self.search_url = "https://www.wikidata.org/w/api.php"
        self.entity_url = "https://www.wikidata.org/entity/"
        
    def disambiguate_company(self, company_name: str, article_context: str = "") -> Dict:
        """
        Disambiguate a company name using Wikidata API
        Returns disambiguation results with confidence scores
        """
        try:
            # Search for the company name
            search_results = self._search_entities(company_name, article_context)
            
            if not search_results:
                return self._no_results_fallback(company_name)
            
            # Filter and rank results
            company_results = self._filter_company_results(search_results, company_name)
            
            if not company_results:
                return self._no_company_results_fallback(company_name)
            
            # Get detailed entity information for top results
            detailed_results = []
            for result in company_results[:3]:  # Top 3 results
                entity_info = self._get_entity_details(result['id'])
                if entity_info:
                    detailed_results.append(entity_info)
            
            # Find best match
            best_match = self._find_best_match(detailed_results, company_name, article_context)
            
            return {
                'is_verified': best_match['confidence'] > 0.7,
                'confidence': best_match['confidence'],
                'entity_name': best_match['name'],
                'entity_type': best_match['types'],
                'description': best_match['description'],
                'url': best_match['url'],
                'wikidata_id': best_match['wikidata_id'],
                'disambiguation_results': detailed_results,
                'source': 'wikidata'
            }
            
        except Exception as e:
            print(f"[WIKIDATA] Error during disambiguation: {e}")
            return self._error_fallback(company_name, str(e))
    
    def _search_entities(self, query: str, context: str = "") -> List[Dict]:
        """Search Wikidata for entities matching the query"""
        try:
            # Build search query with context if available
            search_query = query
            if context:
                # Add context words to improve search
                context_words = context.split()[:5]  # First 5 words
                search_query = f"{query} {' '.join(context_words)}"
            
            params = {
                'action': 'wbsearchentities',
                'search': search_query,
                'language': 'en',
                'type': 'item',
                'limit': 10,
                'format': 'json'
            }
            
            response = requests.get(self.search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'search' in data:
                return data['search']
            return []
            
        except Exception as e:
            print(f"[WIKIDATA] Search error: {e}")
            return []
    
    def _filter_company_results(self, search_results: List[Dict], company_name: str) -> List[Dict]:
        """Filter results to focus on company/organization entities"""
        company_results = []
        
        for result in search_results:
            # Check if it's likely a company/organization
            if self._is_likely_company(result, company_name):
                company_results.append(result)
        
        return company_results
    
    def _is_likely_company(self, result: Dict, company_name: str) -> bool:
        """Check if the result is likely a company/organization"""
        description = result.get('description', '').lower()
        label = result.get('label', '').lower()
        
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
        
        # Check if label matches company name well
        if self._name_similarity(company_name, label) > 0.7:
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
            'wikidata_id': best_result['wikidata_id'],
            'name': best_result['name'],
            'description': best_result['description'],
            'types': best_result['types'],
            'url': best_result['url'],
            'confidence': best_score
        }
    
    def _calculate_match_score(self, result: Dict, company_name: str, context: str = "") -> float:
        """Calculate a match score for the entity"""
        score = 0.0
        
        # Name similarity (40% of score)
        name_sim = self._name_similarity(company_name, result['name'])
        score += name_sim * 0.4
        
        # Type relevance (30% of score)
        type_score = 0.0
        company_types = ['Company', 'Organization', 'Corporation', 'Startup']
        for entity_type in result['types']:
            if entity_type in company_types:
                type_score = 1.0
                break
        score += type_score * 0.3
        
        # Description relevance (20% of score)
        desc_score = 0.0
        if result['description']:
            desc_lower = result['description'].lower()
            company_indicators = ['company', 'business', 'organization', 'startup', 'tech']
            for indicator in company_indicators:
                if indicator in desc_lower:
                    desc_score += 0.2
            desc_score = min(desc_score, 1.0)
        score += desc_score * 0.2
        
        # Context relevance (10% of score)
        if context and result['description']:
            context_words = set(context.lower().split()[:10])
            desc_words = set(result['description'].lower().split())
            overlap = len(context_words.intersection(desc_words))
            context_score = min(overlap / 5.0, 1.0)  # Normalize
            score += context_score * 0.1
        
        return min(score, 1.0)
    
    def _no_results_fallback(self, company_name: str) -> Dict:
        """Fallback when no search results found"""
        return {
            'is_verified': False,
            'confidence': 0.0,
            'entity_name': company_name,
            'entity_type': [],
            'description': 'No Wikidata results found',
            'url': '',
            'wikidata_id': '',
            'disambiguation_results': [],
            'source': 'wikidata'
        }
    
    def _no_company_results_fallback(self, company_name: str) -> Dict:
        """Fallback when no company results found"""
        return {
            'is_verified': False,
            'confidence': 0.2,
            'entity_name': company_name,
            'entity_type': [],
            'description': 'No company entities found in Wikidata',
            'url': '',
            'wikidata_id': '',
            'disambiguation_results': [],
            'source': 'wikidata'
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
            'source': 'wikidata'
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

def test_wikidata_disambiguation():
    """Test the Wikidata disambiguation system"""
    disambiguator = WikidataDisambiguator()
    
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
    test_wikidata_disambiguation()
