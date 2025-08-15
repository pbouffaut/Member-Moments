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
        # Financial growth
        r'\braise[sd]?\b', r'\brise[sd]?\b', r'\bgain[sd]?\b', r'\bclimb[sd]?\b',
        r'\bsurge[sd]?\b', r'\bsoar[sd]?\b', r'\bjump[sd]?\b', r'\bleap[sd]?\b',
        r'\bgrowth\b', r'\bexpand[sd]?\b', r'\bexpansion\b', r'\bprofit[s]?\b',
        r'\brevenue\b', r'\bearnings\b', r'\bup\b', r'\bhigher\b', r'\bstrong\b',
        
        # Business success
        r'\bfund(?:ed|ing)\b', r'\bacquire[d]?\b', r'\bpartnership\b', r'\bcollaboration\b',
        r'\bsuccess\b', r'\bsuccessful\b', r'\bwin[s]?\b', r'\bwon\b', r'\baward[s]?\b',
        r'\bachievement\b', r'\bmilestone\b', r'\bbreakthrough\b', r'\binnovation\b',
        
        # Product launches
        r'\blaunch[esd]?\b', r'\brelease[sd]?\b', r'\bunveil[sd]?\b', r'\bintroduce[sd]?\b',
        r'\bnew\b', r'\binnovative\b', r'\bexciting\b', r'\bamazing\b', r'\boutstanding\b',
        r'\bexcellent\b', r'\bbrilliant\b', r'\bfantastic\b', r'\bwonderful\b',
        
        # General positive
        r'\bpositive\b', r'\bgood\b', r'\bgreat\b', r'\bawesome\b', r'\bterrific\b',
        r'\bperfect\b', r'\bideal\b', r'\boptimal\b', r'\bbest\b', r'\btop\b'
    ]
    
    # Negative tone indicators
    negative_patterns = [
        # Financial decline
        r'\bfall[s]?\b', r'\bdecline[sd]?\b', r'\bdrop[sd]?\b', r'\bplunge[sd]?\b',
        r'\bcrash[esd]?\b', r'\bslump[sd]?\b', r'\btumble[sd]?\b', r'\bslide[sd]?\b',
        r'\bloss\b', r'\blosses\b', r'\blosing\b', r'\blost\b',
        r'\bdecrease[sd]?\b', r'\breduce[sd]?\b', r'\breduction\b',
        r'\bdown\b', r'\blower\b', r'\bweak\b', r'\bweaken[ed]?\b',
        
        # Stock market specific
        r'\bshare[s]?\s+fall[sd]?\b', r'\bstock\s+fall[sd]?\b', r'\bprice\s+fall[sd]?\b',
        r'\bafter\s*[-]?hours?\b', r'\binsider\s+sell[ing]?\b', r'\bsell[ing]?\s+stock\b',
        r'\bmarket\s+decline\b', r'\bbear\s+market\b', r'\bcorrection\b',
        
        # Business problems
        r'\blayoff[s]?\b', r'\bbreach\b', r'\battack\b', r'\bhack[ed]?\b',
        r'\bsecurity\s+incident\b', r'\bdata\s+breach\b', r'\bcyber\s+attack\b',
        r'\bfraud\b', r'\bscandal\b', r'\bcontroversy\b', r'\blawsuit\b',
        r'\bshutdown\b', r'\bbankruptcy\b', r'\bfailure\b', r'\bfailed\b',
        r'\bstruggl[esd]?\b', r'\btrouble[sd]?\b', r'\bproblem[s]?\b',
        r'\bissue[s]?\b', r'\bconcern[s]?\b', r'\brisk[s]?\b', r'\bdanger\b',
        
        # General negative
        r'\bnegative\b', r'\bbad\b', r'\bterrible\b', r'\bawful\b', r'\bhorrible\b',
        r'\bdisaster\b', r'\bcrisis\b', r'\bemergency\b', r'\bpanic\b', r'\bfear\b'
    ]
    
    # Neutral/balanced indicators
    neutral_patterns = [
        # Administrative changes
        r'\bappoint[sd]?\b', r'\bjoin[sd]?\b', r'\bannounce[sd]?\b', r'\bannouncement\b',
        r'\bhire[sd]?\b', r'\bhire[d]?\b', r'\bpromote[sd]?\b', r'\bpromotion\b',
        r'\bresign[sd]?\b', r'\bresignation\b', r'\bleave[sd]?\b', r'\bdeparture\b',
        
        # Business transactions
        r'\bpartnership\b', r'\bcollaboration\b', r'\bmerger\b', r'\bacquisition\b',
        r'\binvestment\b', r'\bdeal\b', r'\bagreement\b', r'\bcontract\b',
        r'\btransaction\b', r'\bexchange\b', r'\btrade\b', r'\bpurchase\b',
        
        # General business
        r'\bquarterly\b', r'\bannual\b', r'\bmonthly\b', r'\bupdate\b',
        r'\breport[sd]?\b', r'\bstatement\b', r'\bresults\b', r'\bperformance\b'
    ]
    
    def count_matches(patterns):
        return sum(len(re.findall(p, text, re.IGNORECASE)) for p in patterns)
    
    positive_count = count_matches(positive_patterns)
    negative_count = count_matches(negative_patterns)
    neutral_count = count_matches(neutral_patterns)
    
    # Determine tone based on pattern counts with weighted scoring
    # Give more weight to negative patterns as they're often more significant
    weighted_positive = positive_count * 1.0
    weighted_negative = negative_count * 1.2  # Negative patterns get 20% more weight
    weighted_neutral = neutral_count * 0.8    # Neutral patterns get 20% less weight
    
    # Calculate confidence based on pattern strength
    if weighted_positive > weighted_negative and weighted_positive > weighted_neutral:
        confidence = min(0.95, 0.6 + (positive_count * 0.08))
        return "POSITIVE", confidence
    elif weighted_negative > weighted_positive and weighted_negative > weighted_neutral:
        confidence = min(0.95, 0.6 + (negative_count * 0.08))
        return "NEGATIVE", confidence
    elif weighted_neutral > 0 and abs(weighted_positive - weighted_negative) < 2:
        # Only neutral if positive and negative are close
        confidence = min(0.8, 0.4 + (neutral_count * 0.1))
        return "NEUTRAL", confidence
    else:
        # Default to neutral with low confidence if unclear
        return "NEUTRAL", 0.3

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
