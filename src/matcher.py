from rapidfuzz import fuzz, process

def best_company_match(text: str, companies: list[str]) -> tuple[str, float]:
    if not text or not companies:
        return ("", 0.0)
    match, score, _ = process.extractOne(text, companies, scorer=fuzz.token_set_ratio)
    return (match, score/100.0 if score else 0.0)
