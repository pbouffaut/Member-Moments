
import argparse, csv, os, re, yaml
from urllib.parse import urlparse, quote_plus
from datetime import datetime, timedelta, timezone
import requests, feedparser

from .utils import parse_date, utc_now, normalize
from .storage import get_conn, seen_url, save_event
from .matcher import best_company_match
from .event_extract import classify_event, score_severity
from .slack_delivery import post_slack
from .verification import analyze_article_tone, get_tone_emoji
from .disambiguation import verify_company_mention, get_verification_emoji

def parse_locations_with_counts(s: str):
    # Expect "Location A (12); Location B (7)"
    result = []
    if not s:
        return result
    for part in [p.strip() for p in s.split(";")]:
        if not part:
            continue
        m = re.match(r"^(.*)\s+\((\d+)\)$", part)
        if m:
            loc = m.group(1).strip()
            cnt = int(m.group(2))
            result.append((loc, cnt))
        else:
            result.append((part, 1))
    return result

def choose_primary_location_from_fields(locs_with_counts: str, locs_simple: str):
    lwc = (locs_with_counts or "").strip()
    if lwc:
        pairs = parse_locations_with_counts(lwc)
        if pairs:
            pairs.sort(key=lambda x: x[1], reverse=True)
            return pairs[0][0]
    locs = (locs_simple or "").strip()
    if locs:
        first = [p.strip() for p in locs.split(";") if p.strip()]
        if first:
            return first[0]
    return None

def infer_delimiter(sample_text: str) -> str:
    # naive: prefer comma, then tab, then semicolon
    if sample_text.count(",") >= sample_text.count("\t") and sample_text.count(",") >= sample_text.count(";"):
        return ","
    if sample_text.count("\t") >= sample_text.count(";"):
        return "\t"
    return ";"

def load_companies(csv_path, locations_csv=None, verbose=False):
    """
    Flexible loader that understands either the original companies.csv
    or the enriched_companies.csv (domain, enriched_company_name, wikidata_official_site, homepage_url ...).
    Optionally merges location fields from a separate CSV by domain.
    """
    companies = []
    # Read input with delimiter inference
    with open(csv_path, "r", encoding="utf-8") as f:
        sample = f.read(4096)
        delim = infer_delimiter(sample)
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        rows = list(reader)
    if verbose:
        print(f"[INFO] Input delimiter guessed as '{delim}' with {len(rows)} rows")

    # Build fast lookup for locations by domain if provided
    loc_map = {}
    if locations_csv:
        with open(locations_csv, "r", encoding="utf-8") as lf:
            sample2 = lf.read(4096); d2 = infer_delimiter(sample2); lf.seek(0)
            lreader = csv.DictReader(lf, delimiter=d2)
            for r in lreader:
                dom = normalize(r.get("domains") or r.get("domain"))
                if not dom:
                    continue
                locs = normalize(r.get("locations") or "")
                locs_wc = normalize(r.get("locations_with_counts") or "")
                loc_map[dom] = {"locations": locs, "locations_with_counts": locs_wc}

    for row in rows:
        # Map columns from either format
        name = normalize(row.get("company_name") or row.get("enriched_company_name"))
        website = normalize(row.get("website") or row.get("wikidata_official_site") or row.get("homepage_url"))
        raw_domains = normalize(row.get("domains") or row.get("domain"))
        domains = []
        if raw_domains:
            # split by ';' or ','
            parts = []
            if ";" in raw_domains:
                parts = [p.strip() for p in raw_domains.split(";")]
            elif "," in raw_domains:
                parts = [p.strip() for p in raw_domains.split(",")]
            else:
                parts = [raw_domains]
            for p in parts:
                p = p.replace("https://","").replace("http://","").replace("www.","").strip("/").strip()
                if p:
                    domains.append(p)
        if not name and domains:
            base = domains[0].split(".")[0].replace("-", " ").replace("_"," ").title()
            name = base

        locations = normalize(row.get("locations"))
        locations_with_counts = normalize(row.get("locations_with_counts"))
        if (not locations and not locations_with_counts) and domains:
            lm = loc_map.get(domains[0])
            if lm:
                locations = lm.get("locations") or ""
                locations_with_counts = lm.get("locations_with_counts") or ""

        company = {
            "company_name": name,
            "website": website,
            "domains": domains,
            "notes": normalize(row.get("notes")),
            "locations": locations,
            "locations_with_counts": locations_with_counts
        }
        if company["domains"]:
            # Enhanced filtering to reduce false positives
            if name:
                # Filter out companies whose names are only numbers
                if re.match(r'^[\d\s\-\.]+$', name):
                    if verbose:
                        print(f"[INFO] Skipping company with numeric name: {name}")
                    continue
                
                # Filter out very short names that could be ambiguous
                if len(name.strip()) <= 2:
                    if verbose:
                        print(f"[INFO] Skipping company with very short name: {name}")
                    continue
                
                # Filter out names that look like initials only
                if re.match(r'^[A-Z]\s*[A-Z]\s*[A-Z]?$', name.strip()):
                    if verbose:
                        print(f"[INFO] Skipping company with initials-only name: {name}")
                    continue
                
                # Filter out names that are just common words
                common_words = ['the', 'and', 'or', 'for', 'new', 'old', 'big', 'small']
                if name.lower().strip() in common_words:
                    if verbose:
                        print(f"[INFO] Skipping company with generic name: {name}")
                    continue
                
                companies.append(company)
            else:
                if verbose:
                    print(f"[INFO] Skipping company with no name")
    return companies

def google_news_rss(query, lang="en"):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={lang}"
    feed = feedparser.parse(url)
    for e in feed.entries:
        yield {
            "title": e.get("title"),
            "url": e.get("link"),
            "published_at": e.get("published") or e.get("updated"),
            "source": "google_news_rss"
        }

def newsapi_everything(query, api_key, from_iso):
    if not api_key:
        return []
    endpoint = "https://newsapi.org/v2/everything"
    params = {"q": query, "from": from_iso, "sortBy": "publishedAt", "language": "en", "pageSize": 50}
    headers = {"X-Api-Key": api_key}
    r = requests.get(endpoint, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    results = []
    for a in data.get("articles", []):
        results.append({
            "title": a.get("title"),
            "url": a.get("url"),
            "published_at": a.get("publishedAt"),
            "source": "newsapi"
        })
    return results

def domain_from_url(url):
    try:
        return urlparse(url).netloc.lower()
    except:
        return ""

def run(csv_path, config_path, since_days, verbose=False, locations_csv=None):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    slack_url = cfg.get("slack_webhook_url")
    newsapi_key = cfg.get("newsapi_key", "")
    lang = cfg.get("google_news_lang", "en")
    min_conf = float(cfg.get("min_confidence", 0.8))
    min_sev = float(cfg.get("min_severity", 0.6))

    companies = load_companies(csv_path, locations_csv=locations_csv, verbose=verbose)
    names = [c["company_name"] for c in companies]
    # Build maps for locations
    name_to_primary_location = {
        c["company_name"]: choose_primary_location_from_fields(c.get("locations_with_counts"), c.get("locations"))
        for c in companies
    }
    name_to_all_locations = {
        c["company_name"]: c.get("locations") or "" for c in companies
    }

    if verbose:
        print(f"[INFO] Loaded {len(companies)} companies from {csv_path}")

    conn = get_conn(cfg.get("db_path", "events.db"))
    since = utc_now() - timedelta(days=since_days or int(cfg.get("since_days", 14)))
    since_iso = since.isoformat()

    for c in companies:
        name = c["company_name"]
        if verbose:
            print(f"[INFO] Querying for {name} (domains={len(c['domains'])})")
        queries = [f'"{name}"']
        for d in c["domains"]:
            queries.append(d)

        for q in queries:
            # Google News RSS
            for item in google_news_rss(q, lang=lang):
                published = parse_date(item["published_at"])
                if published and published.replace(tzinfo=timezone.utc) < since:
                    continue
                process_item(item, name, names, min_conf, min_sev, slack_url, conn,
                             name_to_primary_location, name_to_all_locations, companies, verbose=verbose)

            # NewsAPI (optional)
            try:
                for item in newsapi_everything(q, newsapi_key, since_iso):
                    published = parse_date(item["published_at"])
                    if published and published.replace(tzinfo=timezone.utc) < since:
                        continue
                    process_item(item, name, names, min_conf, min_sev, slack_url, conn,
                                 name_to_primary_location, name_to_all_locations, companies, verbose=verbose)
            except Exception as e:
                if verbose:
                    print("[NewsAPI] Skipping due to error:", e)

def process_item(item, target_company, all_names, min_conf, min_sev, slack_url, conn,
                 name_to_primary_location, name_to_all_locations, companies_data, verbose=False):
    title = item.get("title") or ""
    url = item.get("url") or ""
    if not url or seen_url(conn, url):
        return

    # Fuzzy match best company referenced by the headline
    best_name, conf = best_company_match(title, all_names)
    if conf < min_conf or best_name != target_company:
        return

    ev_type, _ = classify_event(title, "")
    severity = score_severity(ev_type, domain_from_url(url))
    if severity < min_sev:
        return

    published_at = item.get("published_at")
    evidence = url

    # Get company domains for comprehensive verification
    company_domains = []
    for company_data in companies_data:
        if company_data["company_name"] == best_name:
            company_domains = company_data["domains"]
            break

    # Comprehensive company verification using new disambiguation system
    test_mode = os.environ.get('GITHUB_ACTIONS') == 'true'
    is_verified, verification_note, confidence_score = verify_company_mention(
        best_name, company_domains, url, title, verbose, test_mode
    )
    
    # Tone analysis
    tone, tone_confidence = analyze_article_tone(title)
    
    # Location handling
    primary_location = name_to_primary_location.get(best_name)
    all_locations = (name_to_all_locations.get(best_name) or "").strip()
    
    # Create enhanced title with verification status and tone
    verification_prefix = ""
    if not is_verified:
        verification_prefix = f"{get_verification_emoji(is_verified, confidence_score)} *UNVERIFIED* - {verification_note}\n"
    else:
        verification_prefix = f"{get_verification_emoji(is_verified, confidence_score)} *VERIFIED* ({confidence_score:.2f}) - {verification_note}\n"
    
    tone_info = f"Tone: {get_tone_emoji(tone)} {tone} ({tone_confidence:.2f})"
    
    title_augmented = title
    if all_locations:
        title_augmented = f"{title}\nLocations: {all_locations}"
    
    # Add verification and tone info
    title_augmented = f"{verification_prefix}{title_augmented}\n{tone_info}"

    row = {
        "created_at": datetime.utcnow().isoformat(),
        "published_at": published_at,
        "company_name": best_name,
        "company_location": primary_location,
        "title": title_augmented,
        "url": url,
        "source": item.get("source"),
        "event_type": ev_type,
        "severity": severity,
        "confidence": conf,
        "evidence": evidence,
        "is_verified": is_verified,
        "verification_note": verification_note,
        "verification_confidence": confidence_score,
        "tone": tone,
        "tone_confidence": tone_confidence
    }
    save_event(conn, row)

    if slack_url:
        try:
            post_slack(slack_url, title=title_augmented, company=best_name, url=url,
                       event_type=ev_type, published_at=published_at or "", severity=severity,
                       location=primary_location, is_verified=is_verified, tone=tone, confidence=confidence_score)
        except Exception as e:
            if verbose:
                print("[Slack] Failed to post:", e)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to companies.csv (or enriched_companies.csv)")
    ap.add_argument("--config", required=True, help="Path to config.yaml")
    ap.add_argument("--since_days", type=int, default=None, help="Lookback window")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--test-slack", action="store_true", help="Post a test message and exit")
    ap.add_argument("--locations-csv", default=None, help="Optional CSV to merge locations by domain")
    args = ap.parse_args()

    if args.test_slack:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        slack_url = cfg.get("slack_webhook_url")
        if not slack_url:
            print("[TEST] Missing slack_webhook_url in config.yaml")
            raise SystemExit(1)
        post_slack(slack_url,
                   title="Synthetic test: Company XYZ raises $10M Series B\nLocations: Midtown on 50th; Bryant Park",
                   company="Company XYZ",
                   url="https://example.com/test",
                   event_type="FUNDING",
                   published_at=datetime.utcnow().isoformat(),
                   severity=0.9,
                   location="Midtown on 50th")
        print("[TEST] Sent a test Slack message. Check your channel.")
        raise SystemExit(0)

    run(args.csv, args.config, args.since_days, verbose=args.verbose, locations_csv=args.locations_csv)
