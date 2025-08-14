import re
import requests
from typing import Tuple, List, Optional
from urllib.parse import urlparse
import time

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

def verify_domain_in_article(url: str, company_domains: List[str], verbose: bool = False, test_mode: bool = False) -> Tuple[bool, str]:
    """
    Check if any of the company domains appear in the article content.
    Returns (is_verified, verification_note)
    """
    if not company_domains:
        return False, "No company domains to verify"
    
    # In test mode, simulate verification
    if test_mode:
        return True, "Test mode - verification simulated"
    
    try:
        # Add a small delay to be respectful to news sites
        time.sleep(0.5)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; MemberMoments/1.0; +https://github.com/pbouffaut/Member-Moments)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        content = response.text.lower()
        
        # Check if any company domain appears in the article
        for domain in company_domains:
            if domain.lower() in content:
                if verbose:
                    print(f"[VERIFY] Domain '{domain}' found in article")
                return True, f"Domain '{domain}' verified in article"
        
        if verbose:
            print(f"[VERIFY] No company domains found in article content")
        return False, "Company domain not found in article content"
        
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"[VERIFY] Error fetching article: {e}")
        return False, f"Could not verify: {str(e)}"
    except Exception as e:
        if verbose:
            print(f"[VERIFY] Unexpected error: {e}")
        return False, f"Verification error: {str(e)}"

def analyze_article_tone(title: str, content: str = "") -> Tuple[str, float]:
    """
    Analyze the tone of an article based on title and content.
    Returns (tone, confidence_score)
    """
    text = f"{title or ''} {content or ''}".lower()
    
    # Positive tone indicators
    positive_patterns = [
        r'\braise[sd]?\b', r'\bfund(?:ed|ing)\b', r'\bacquire[d]?\b', r'\bpartnership\b',
        r'\bexpansion\b', r'\bgrowth\b', r'\bsuccess\b', r'\bwin[s]?\b', r'\baward[s]?\b',
        r'\blaunch[esd]?\b', r'\brelease[sd]?\b', r'\bunveil[sd]?\b', r'\bnew\b',
        r'\binnovative\b', r'\bbreakthrough\b', r'\bexciting\b', r'\bpositive\b'
    ]
    
    # Negative tone indicators
    negative_patterns = [
        r'\blayoff[s]?\b', r'\bbreach\b', r'\battack\b', r'\bhack[ed]?\b',
        r'\bsecurity\s+incident\b', r'\bdata\s+breach\b', r'\bcyber\s+attack\b',
        r'\bfraud\b', r'\bscandal\b', r'\bcontroversy\b', r'\blawsuit\b',
        r'\bshutdown\b', r'\bbankruptcy\b', r'\bfailure\b', r'\bdecline\b',
        r'\bloss\b', r'\bdecrease\b', r'\bdown\b', r'\bnegative\b'
    ]
    
    # Neutral/balanced indicators
    neutral_patterns = [
        r'\bappoint[sd]?\b', r'\bjoin[sd]?\b', r'\bannounce[sd]?\b',
        r'\bpartnership\b', r'\bcollaboration\b', r'\bmerger\b', r'\bacquisition\b'
    ]
    
    def count_matches(patterns):
        return sum(len(re.findall(p, text, re.IGNORECASE)) for p in patterns)
    
    positive_count = count_matches(positive_patterns)
    negative_count = count_matches(negative_patterns)
    neutral_count = count_matches(neutral_patterns)
    
    # Determine tone based on pattern counts
    if positive_count > negative_count and positive_count > neutral_count:
        confidence = min(0.9, 0.5 + (positive_count * 0.1))
        return "POSITIVE", confidence
    elif negative_count > positive_count and negative_count > neutral_count:
        confidence = min(0.9, 0.5 + (negative_count * 0.1))
        return "NEGATIVE", confidence
    elif neutral_count > 0:
        confidence = min(0.8, 0.4 + (neutral_count * 0.1))
        return "NEUTRAL", confidence
    else:
        return "NEUTRAL", 0.5

def get_tone_emoji(tone: str) -> str:
    """Get appropriate emoji for tone"""
    return {
        "POSITIVE": "✅",
        "NEGATIVE": "⚠️",
        "NEUTRAL": "ℹ️"
    }.get(tone, "ℹ️")

def get_verification_emoji(is_verified: bool) -> str:
    """Get emoji for verification status"""
    return "✅" if is_verified else "⚠️"
