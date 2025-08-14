import re
from typing import Tuple

FUNDING_PATTERNS = [
    r"series\s+[A-E]", r"\bseed\b", r"\bpre-seed\b", r"\bround\b",
    r"\$\s?\d+(\.\d+)?\s?(m|b)\b", r"\d+\s?(million|billion)\b"
]
EXEC_PATTERNS = [
    r"\bCEO\b|\bCTO\b|\bCFO\b|\bChief\b|\bChief\s+\w+",
    r"\bappoints?\b|\bjoins?\b|\bsteps\s+down\b|\bresigns?\b|\bleaves?\b"
]
HIRING_PATTERNS = [
    r"\bhiring\b", r"\bopen roles\b", r"\bnow hiring\b", r"\bgrowing team\b", r"\bexpanding\b"
]
LAUNCH_PATTERNS = [
    r"\blaunch(es|ed|ing)?\b", r"\brelease(s|d|ing)?\b", r"\bunveil(s|ed|ing)?\b"
]
AWARD_PATTERNS = [

    r"\baward(s)?\b", r"\bwinner\b", r"\brecognition\b", r"\bhonor(?:ed)?\b"
]

def classify_event(title: str, snippet: str = "") -> Tuple[str, float]:
    text = f"{title or ''} {snippet or ''}".lower()

    def match_any(patterns):
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    if match_any(FUNDING_PATTERNS):
        return ("FUNDING", 0.9)
    if match_any(EXEC_PATTERNS):
        return ("EXEC_CHANGE", 0.75)
    if match_any(HIRING_PATTERNS):
        return ("HIRING", 0.6)
    if match_any(LAUNCH_PATTERNS):
        return ("PRODUCT_LAUNCH", 0.6)
    if match_any(AWARD_PATTERNS):
        return ("AWARD", 0.6)
    if match_any(LAYOFFS_PATTERNS):
        return ("LAYOFFS", 0.95)
    if match_any(SECURITY_PATTERNS):
        return ("SECURITY_INCIDENT", 0.9)
    return ("PRESS_MENTION", 0.5)

def score_severity(event_type: str, source_domain: str = "") -> float:
    base = {
        "FUNDING": 0.9,
        "EXEC_CHANGE": 0.75,
        "HIRING": 0.55,
        "PRODUCT_LAUNCH": 0.65,
        "AWARD": 0.6,
        "PRESS_MENTION": 0.5,
        "LAYOFFS": 0.85,
        "SECURITY_INCIDENT": 0.8,
    }.get(event_type, 0.5)

    high_auth = ["techcrunch.com", "theverge.com", "wsj.com", "ft.com", "reuters.com", "bloomberg.com"]
    if any(h in (source_domain or "") for h in high_auth):
        base += 0.1

    return min(1.0, base)

LAYOFFS_PATTERNS = [
    r"\blayoff(s)?\b", r"\bworkforce reduction\b", r"\bstaff cuts?\b",
    r"\bjob cuts?\b", r"\bredundanc(y|ies)\b", r"\bdownsizing\b",
    r"\bheadcount reduction\b"
]
SECURITY_PATTERNS = [
    r"\bdata breach\b", r"\bsecurity incident\b", r"\bcyber ?attack\b",
    r"\bransomware\b", r"\bhacked\b", r"\bcompromise(d)?\b"
]
