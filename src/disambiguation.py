import re
from typing import Tuple, List, Dict, Optional
from urllib.parse import urlparse
import requests
import time

# Common false positive patterns that indicate personal names or unrelated content
PERSON_NAME_PATTERNS = [
    r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last names
    r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Middle Last
    r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Four part names
]

# Business context indicators that suggest the article is about a company
BUSINESS_CONTEXT_PATTERNS = [
    r'\bcompany\b', r'\bcorporation\b', r'\binc\b', r'\bllc\b', r'\bltd\b',
    r'\bstartup\b', r'\btech\b', r'\bsoftware\b', r'\bplatform\b', r'\bservice\b',
    r'\bannounces\b', r'\blaunches\b', r'\braises\b', r'\bfunding\b', r'\bpartnership\b',
    r'\bmerger\b', r'\bacquisition\b', r'\bappoints\b', r'\bceo\b', r'\bcto\b',
    r'\bheadquarters\b', r'\boffice\b', r'\blocation\b', r'\bexpansion\b'
]

# Non-business context indicators that suggest the article is NOT about a company
NON_BUSINESS_CONTEXT_PATTERNS = [
    r'\bsports\b', r'\bgame\b', r'\bplay\b', r'\bteam\b', r'\bplayer\b', r'\bcoach\b',
    r'\bweather\b', r'\bclimate\b', r'\btemperature\b', r'\brain\b', r'\bstorm\b',
    r'\bpolitics\b', r'\belection\b', r'\bvote\b', r'\bgovernment\b', r'\bofficial\b',
    r'\bcrime\b', r'\barrest\b', r'\bpolice\b', r'\bincident\b', r'\baccident\b',
    r'\bdisaster\b', r'\bflood\b', r'\bfire\b', r'\bearthquake\b', r'\btsunami\b',
    r'\bhealth\b', r'\bmedical\b', r'\bhospital\b', r'\bdoctor\b', r'\bpatient\b',
    r'\bentertainment\b', r'\bmovie\b', r'\bshow\b', r'\bconcert\b', r'\bartist\b',
    r'\beducation\b', r'\bschool\b', r'\buniversity\b', r'\bstudent\b', r'\bteacher\b'
]

# Generic terms that often cause false positives
GENERIC_TERMS = [
    'the', 'and', 'or', 'for', 'with', 'from', 'about', 'new', 'old', 'big', 'small',
    'good', 'bad', 'high', 'low', 'fast', 'slow', 'hot', 'cold', 'open', 'close',
    'start', 'stop', 'begin', 'end', 'first', 'last', 'next', 'previous'
]

# High-risk single-word company names that require extra verification
HIGH_RISK_SINGLE_WORDS = [
    'advance', 'agency', 'house', 'home', 'work', 'play', 'go', 'get', 'make', 'take',
    'see', 'look', 'find', 'help', 'care', 'love', 'life', 'time', 'day', 'way',
    'world', 'city', 'town', 'place', 'space', 'room', 'door', 'window', 'light',
    'water', 'fire', 'earth', 'air', 'sun', 'moon', 'star', 'tree', 'flower', 'bird',
    'fish', 'dog', 'cat', 'man', 'woman', 'boy', 'girl', 'child', 'people', 'family',
    'friend', 'team', 'group', 'club', 'band', 'show', 'game', 'play', 'book', 'film',
    'music', 'art', 'food', 'drink', 'shop', 'store', 'bank', 'school', 'church',
    'hospital', 'hotel', 'restaurant', 'cafe', 'bar', 'park', 'road', 'street', 'avenue'
]

def extract_domain_from_url(url: str) -> str:
    """Extract clean domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return ""

def is_likely_person_name(text: str) -> bool:
    """Check if text looks like a person's name"""
    text = text.strip()
    
    # Check against person name patterns
    for pattern in PERSON_NAME_PATTERNS:
        if re.search(pattern, text):
            return True
    
    # Check for titles that indicate a person
    person_titles = ['mr', 'mrs', 'ms', 'dr', 'professor', 'prof', 'sir', 'madam']
    words = text.lower().split()
    if words and words[0] in person_titles:
        return True
    
    # Check if it's just initials or very short
    if len(text) <= 3 or text.count(' ') == 0:
        return False
    
    # Check if it follows "First Last" pattern with proper capitalization
    parts = text.split()
    if len(parts) == 2:
        if (parts[0][0].isupper() and parts[0][1:].islower() and 
            parts[1][0].isupper() and parts[1][1:].islower()):
            return True
    
    return False

def has_business_context(text: str) -> bool:
    """Check if text contains business-related context"""
    text_lower = text.lower()
    
    # Count business context indicators
    business_score = 0
    for pattern in BUSINESS_CONTEXT_PATTERNS:
        if re.search(pattern, text_lower):
            business_score += 1
    
    # Count non-business context indicators (negative score)
    non_business_score = 0
    for pattern in NON_BUSINESS_CONTEXT_PATTERNS:
        if re.search(pattern, text_lower):
            non_business_score += 1
    
    # Calculate net business score
    net_business_score = business_score - non_business_score
    
    # Return True only if we have a strong positive business context
    return net_business_score >= 2

def calculate_name_similarity(company_name: str, article_text: str) -> Tuple[float, str]:
    """
    Calculate similarity between company name and article text.
    Returns (similarity_score, match_type)
    """
    company_name = company_name.lower().strip()
    article_text = article_text.lower()
    
    # Exact match (highest confidence)
    if company_name in article_text:
        return 1.0, "exact_match"
    
    # Check for company name with slight variations (spaces, punctuation)
    company_words = re.findall(r'\b\w+\b', company_name)
    if len(company_words) > 1:
        # Multi-word company name
        all_words_present = all(word in article_text for word in company_words)
        if all_words_present:
            return 0.95, "all_words_present"
    
    # Check for partial matches (but be more strict)
    company_parts = company_name.split()
    if len(company_parts) > 1:
        # For multi-word names, require at least 2/3 of words to match
        matching_parts = sum(1 for part in company_parts if part in article_text)
        if matching_parts >= len(company_parts) * 0.67:
            return 0.8, "majority_words_match"
    
    # Single word company name - be extremely strict
    if len(company_parts) == 1:
        word = company_parts[0].lower()
        
        # High-risk single words require domain verification AND business context
        if word in HIGH_RISK_SINGLE_WORDS:
            # For high-risk words, require both domain verification AND strong business context
            if has_business_context(article_text):
                return 0.4, "high_risk_single_word_with_context"
            else:
                return 0.1, "high_risk_single_word_no_context"
        
        # Regular single words - still strict but not as harsh
        if word not in GENERIC_TERMS and word in article_text:
            if has_business_context(article_text):
                return 0.6, "single_word_business_context"
            else:
                return 0.2, "single_word_no_context"
        
        return 0.0, "single_word_generic_or_not_found"
    
    return 0.0, "no_match"

def is_company_specific_mention(company_name: str, article_text: str, company_domains: List[str]) -> bool:
    """
    Check if the article is specifically about the company vs. just using the word in a different context.
    This helps distinguish between "Apple launches new iPhone" vs "She ate an apple"
    """
    company_name_lower = company_name.lower()
    article_text_lower = article_text.lower()
    
    # Check for company-specific indicators
    company_indicators = [
        f"{company_name_lower} announces",
        f"{company_name_lower} launches", 
        f"{company_name_lower} raises",
        f"{company_name_lower} appoints",
        f"{company_name_lower} expands",
        f"{company_name_lower} reports",
        f"{company_name_lower} earnings",
        f"{company_name_lower} revenue",
        f"{company_name_lower} stock",
        f"{company_name_lower} shares",
        f"{company_name_lower} ceo",
        f"{company_name_lower} cto",
        f"{company_name_lower} headquarters",
        f"{company_name_lower} office",
        f"{company_name_lower} location"
    ]
    
    # Check if any company-specific indicators are present
    for indicator in company_indicators:
        if indicator in article_text_lower:
            return True
    
    # Check if company name appears in proper noun context (capitalized)
    # This helps distinguish "Apple" (company) from "apple" (fruit)
    company_words = company_name.split()
    for word in company_words:
        if word.lower() in article_text_lower:
            # Look for capitalized version in context
            capitalized_word = word.capitalize()
            if capitalized_word in article_text:
                # Check if it's in a business context
                context_before = article_text_lower.find(word.lower())
                context_after = context_before + len(word)
                
                # Look for business context around the mention
                start = max(0, context_before - 50)
                end = min(len(article_text_lower), context_after + 50)
                context_window = article_text_lower[start:end]
                
                if has_business_context(context_window):
                    return True
    
    return False

def verify_company_mention(company_name: str, company_domains: List[str], 
                          article_url: str, article_title: str, 
                          verbose: bool = False, test_mode: bool = False) -> Tuple[bool, str, float]:
    """
    Comprehensive verification that a company is actually mentioned in the article.
    Returns (is_verified, verification_note, confidence_score)
    """
    if not company_domains:
        return False, "No company domains to verify", 0.0
    
    # First, check if any company domain appears in the article
    domain_verified = False
    domain_note = ""
    
    if not test_mode:
        try:
            # Add a small delay to be respectful to news sites
            time.sleep(0.5)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; MemberMoments/1.0; +https://github.com/pbouffaut/Member-Moments)'
            }
            
            response = requests.get(article_url, headers=headers, timeout=10)
            response.raise_for_status()
            article_content = response.text
        except Exception as e:
            if verbose:
                print(f"[VERIFY] Error fetching article: {e}")
            article_content = article_title  # Fall back to title only
    else:
        article_content = article_title  # Test mode
        domain_verified = True
        domain_note = "Test mode - domain verification simulated"
    
    # Check domain presence
    if not test_mode:
        for domain in company_domains:
            if domain.lower() in article_content.lower():
                domain_verified = True
                domain_note = f"Domain '{domain}' found in article"
                break
        
        if not domain_verified:
            domain_note = "No company domains found in article content"
    
    # Check name similarity and context
    name_similarity, match_type = calculate_name_similarity(company_name, article_content)
    
    # Check if company name looks like a person's name
    is_person_name = is_likely_person_name(company_name)
    
    # Calculate overall confidence with stricter rules for high-risk companies
    confidence = 0.0
    verification_note = ""
    
    # Check if this is a high-risk single-word company
    company_words = company_name.lower().split()
    is_high_risk_single_word = len(company_words) == 1 and company_words[0] in HIGH_RISK_SINGLE_WORDS
    
    if domain_verified:
        if name_similarity > 0.8:
            confidence = 0.9
            verification_note = f"High confidence: {domain_note}, {match_type}"
        elif name_similarity > 0.6:
            confidence = 0.7
            verification_note = f"Medium confidence: {domain_note}, {match_type}"
        else:
            confidence = 0.5
            verification_note = f"Low confidence: {domain_note}, {match_type}"
    else:
        # No domain verification - much lower confidence
        if name_similarity > 0.9 and has_business_context(article_content):
            confidence = 0.6
            verification_note = f"Domain not verified, but strong name match with business context: {match_type}"
        else:
            confidence = 0.2
            verification_note = f"Domain not verified, weak name match: {match_type}"
    
    # CRITICAL: High-risk single-word companies MUST have domain verification
    if is_high_risk_single_word and not domain_verified:
        confidence = 0.1
        verification_note += " (REJECTED: high-risk single-word company without domain verification)"
    
    # Penalize if company name looks like a person's name
    if is_person_name:
        confidence *= 0.5
        verification_note += " (penalized: company name resembles person name)"
    
    # Final verification decision - higher threshold for high-risk companies
    if is_high_risk_single_word:
        is_verified = confidence >= 0.7  # Higher threshold for risky companies
    else:
        is_verified = confidence >= 0.6  # Standard threshold
    
    if verbose:
        print(f"[VERIFY] Company: {company_name}")
        print(f"[VERIFY] Domain verified: {domain_verified}")
        print(f"[VERIFY] Name similarity: {name_similarity:.2f} ({match_type})")
        print(f"[VERIFY] Is person name: {is_person_name}")
        print(f"[VERIFY] Final confidence: {confidence:.2f}")
        print(f"[VERIFY] Verification note: {verification_note}")
    
    return is_verified, verification_note, confidence

def get_verification_emoji(is_verified: bool, confidence: float) -> str:
    """Get appropriate emoji for verification status and confidence"""
    if is_verified:
        if confidence >= 0.8:
            return "✅"
        elif confidence >= 0.6:
            return "⚠️"
        else:
            return "❓"
    else:
        return "❌"
