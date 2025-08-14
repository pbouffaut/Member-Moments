import requests
import json
from typing import Dict, List, Optional, Tuple
import time

class EntityDisambiguator:
    """
    Uses Google Knowledge Graph API to disambiguate company names and verify entities
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://kgsearch.googleapis.com/v1/entities:search"
    
    def disambiguate_company(self, company_name: str, article_context: str = "") -> Dict:
        """
        Disambiguate a company name using Google Knowledge Graph API
        Returns disambiguation results with confidence scores
        """
        if not self.api_key:
            return self._fallback_disambiguation(company_name, article_context)
        
        try:
            # Build query with context
            query = company_name
            if article_context:
                # Add context to help disambiguation
                context_words = article_context.split()[:10]  # First 10 words for context
                query = f"{company_name} {' '.join(context_words)}"
            
            params = {
                'query': query,
                'key': self.api_key,
                'limit': 5,  # Get top 5 results
                'types': 'Organization|Corporation|Company',  # Focus on business entities
                'indent': True
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'itemListElement' in data and data['itemListElement']:
                # Process results
                results = []
                for item in data['itemListElement']:
                    if 'result' in item:
                        result = item['result']
                        score = item.get('resultScore', 0)
                        
                        entity_info = {
                            'name': result.get('name', ''),
                            'type': result.get('@type', []),
                            'description': result.get('description', ''),
                            'url': result.get('url', ''),
                            'score': score,
                            'is_company': self._is_company_entity(result),
                            'confidence': self._calculate_confidence(result, company_name, score)
                        }
                        results.append(entity_info)
                
                # Return best match
                if results:
                    best_match = max(results, key=lambda x: x['confidence'])
                    return {
                        'is_verified': best_match['confidence'] > 0.7,
                        'confidence': best_match['confidence'],
                        'entity_name': best_match['name'],
                        'entity_type': best_match['type'],
                        'description': best_match['description'],
                        'url': best_match['url'],
                        'disambiguation_results': results
                    }
            
            # No good matches found
            return {
                'is_verified': False,
                'confidence': 0.0,
                'entity_name': company_name,
                'entity_type': [],
                'description': '',
                'url': '',
                'disambiguation_results': []
            }
            
        except Exception as e:
            print(f"[DISAMBIGUATION] Error with Google Knowledge Graph API: {e}")
            return self._fallback_disambiguation(company_name, article_context)
    
    def _is_company_entity(self, entity: Dict) -> bool:
        """Check if the entity is a company/organization"""
        entity_types = entity.get('@type', [])
        company_types = ['Organization', 'Corporation', 'Company', 'Business', 'EducationalOrganization']
        return any(t in entity_types for t in company_types)
    
    def _calculate_confidence(self, entity: Dict, company_name: str, score: float) -> float:
        """Calculate confidence score for the entity match"""
        # Normalize Google's score (usually 0-1000)
        normalized_score = min(score / 1000.0, 1.0)
        
        # Boost confidence if names are very similar
        entity_name = entity.get('name', '').lower()
        company_name_lower = company_name.lower()
        
        if entity_name == company_name_lower:
            name_boost = 0.3
        elif entity_name in company_name_lower or company_name_lower in entity_name:
            name_boost = 0.2
        else:
            name_boost = 0.0
        
        # Boost if it's clearly a company
        company_boost = 0.2 if self._is_company_entity(entity) else 0.0
        
        final_confidence = normalized_score + name_boost + company_boost
        return min(final_confidence, 1.0)
    
    def _fallback_disambiguation(self, company_name: str, article_context: str = "") -> Dict:
        """Fallback disambiguation when API is not available"""
        return {
            'is_verified': False,
            'confidence': 0.3,
            'entity_name': company_name,
            'entity_type': [],
            'description': 'API not available',
            'url': '',
            'disambiguation_results': []
        }

def test_disambiguation():
    """Test the disambiguation system"""
    # You'll need to set your API key
    api_key = "YOUR_GOOGLE_KNOWLEDGE_GRAPH_API_KEY"
    
    if api_key == "YOUR_GOOGLE_KNOWLEDGE_GRAPH_API_KEY":
        print("Please set your Google Knowledge Graph API key to test")
        return
    
    disambiguator = EntityDisambiguator(api_key)
    
    # Test cases
    test_cases = [
        ("Advance Academy", "Advance Academy launches new online courses"),
        ("Apple", "Apple announces new iPhone"),
        ("advance", "Team advances to finals"),  # Should NOT match company
        ("Agency House", "Agency House expands operations")
    ]
    
    for company_name, context in test_cases:
        print(f"\n--- Testing: {company_name} ---")
        result = disambiguator.disambiguate_company(company_name, context)
        print(f"Verified: {result['is_verified']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Entity: {result['entity_name']}")
        print(f"Type: {result['entity_type']}")
        print(f"Description: {result['description']}")

if __name__ == "__main__":
    test_disambiguation()
