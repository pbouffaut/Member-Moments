import re
from datetime import datetime, timezone
from dateutil import parser

def parse_date(dt_str):
    if not dt_str:
        return None
    try:
        return parser.parse(dt_str)
    except Exception:
        return None

def utc_now():
    return datetime.now(timezone.utc)

def clamp01(x):
    try:
        f = float(x)
    except:
        return 0.0
    return max(0.0, min(1.0, f))

def normalize(s: str) -> str:
    return (s or "").strip()
