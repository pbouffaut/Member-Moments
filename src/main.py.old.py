import argparse, csv, os, re, time, yaml, hashlib
from urllib.parse import urlparse, quote_plus
from datetime import datetime, timedelta, timezone
import requests, feedparser

from .utils import parse_date, utc_now, clamp01, normalize
from .storage import get_conn, seen_url, save_event
from .matcher import best_company_match
from .event_extract import classify_event, score_severity
from .slack_delivery import post_slack

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


def load_companies(csv_path, locations_csv=None):
    """
    Flexible loader that understands either the original companies.csv
    or the enriched_companies.csv (domain, enriched_company_name, wikidata_official_site, homepage_url ...).
    Optionally merges location fields from a separate CSV by domain.
    """
    import csv
    companies = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=',' if ',' in f.read(4096) else '	')
        f.seek(0); reader = csv.DictReader(f)
        rows = list(reader)

    # Build fast lookup for locations by domain if provided
    loc_map = {}
    if locations_csv:
        with open(locations_csv, newline='', encoding='utf-8') as lf:
            lreader = csv.DictReader(lf, delimiter=',' if ',' in lf.read(4096) else '	')
            lf.seek(0); lreader = csv.DictReader(lf)
            for r in lreader:
                dom = normalize(r.get("domains") or r.get("domain"))
                if not dom:
                    continue
                locs = normalize(r.get("locations") or "")
                locs_wc = normalize(r.get("locations_with_counts") or "")
                loc_map[dom] = {"locations": locs, "locations_with_counts": locs_wc}

    for row in rows:
        # Columns mapping
        name = normalize(row.get("company_name") or row.get("enriched_company_name"))
        website = normalize(row.get("website") or row.get("wikidata_official_site") or row.get("homepage_url"))
        # domains/domains: if 'domains' present, split by ';'
        raw_domains = normalize(row.get("domains") or row.get("domain"))
        domains = []
        if raw_domains:
            if ';' in raw_domains:
                domains = [d.strip() for d in raw_domains.split(';') if d.strip()]
            else:
                # in case it's a URL, strip scheme and www.
                dom = raw_domains.replace("https://","").replace("http://","").replace("www.","").strip('/').strip()
                domains = [dom] if dom else []
        if not name and domains:
            # fallback to domain base
            base = domains[0].split('.')[0].replace('-', ' ').replace('_',' ').title()
            name = base

        company = {
            "company_name": name,
            "website": website,
            "domains": domains,
            "notes": normalize(row.get("notes"))
        }
        # Attach location fields if present in the same row (or from loc_map)
        company["locations"] = normalize(row.get("locations"))
        company["locations_with_counts"] = normalize(row.get("locations_with_counts"))
        if (not company["locations"] and not company["locations_with_counts"]) and domains:
            # try merge from separate file
            lm = loc_map.get(domains[0])
            if lm:
                company["locations"] = lm.get("locations") or ""
                company["locations_with_counts"] = lm.get("locations_with_counts") or ""

        # Keep only rows that have at least one domain
        if company["domains"]:
            companies.append(company)
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
        from urllib.parse import urlparse
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

    companies = load_companies(csv_path, locations_csv=locations_csv)
    if verbose:
        print(f"[INFO] Loaded {len(companies)} companies from {csv_path}")
    names = [c["company_name"] for c in companies]
    # Build company -> primary location map (optional)
    name_to_location = {c['company_name']: choose_primary_location_from_fields(c.get('locations_with_counts'), c.get('locations')) for c in companies}

    conn = get_conn(cfg.get("db_path", "events.db"))
    since = utc_now() - timedelta(days=since_days or int(cfg.get("since_days", 14)))
    since_iso = since.isoformat()

    total_hits=0
    kept=0
    for c in companies:
        if verbose:
            print(f"[INFO] Querying for {c['company_name']} (domains={len(c['domains'])})")
        name = c["company_name"]
        queries = [f'"{name}"']
        for d in c["domains"]:
            queries.append(d)

        for q in queries:
            for item in google_news_rss(q, lang=lang):
                total_hits += 1
                if verbose and total_hits % 50 == 0:
                    print(f"[INFO] Seen {total_hits} items so far...")
                published = parse_date(item["published_at"])
                if published and published.replace(tzinfo=timezone.utc) < since:
                    continue
                process_item(item, name, names, min_conf, min_sev, slack_url, conn, name_to_location)

            try:
                for item in newsapi_everything(q, newsapi_key, since_iso):
                    published = parse_date(item["published_at"])
                    if published and published.replace(tzinfo=timezone.utc) < since:
                        continue
                    before=kept
                    process_item(item, name, names, min_conf, min_sev, slack_url, conn, name_to_location)
                    if verbose and before!=kept:
                        print("[INFO] Kept an item from NewsAPI")
            except Exception as e:
                print("[NewsAPI] Skipping due to error:", e)

def process_item(item, target_company, all_names, min_conf, min_sev, slack_url, conn, name_to_location):
    title = item.get("title") or ""
    url = item.get("url") or ""
    if not url or seen_url(conn, url):
        return

    best_name, conf = best_company_match(title, all_names)
    if conf < min_conf or best_name != target_company:
        return

    ev_type, cls_conf = classify_event(title, "")
    severity = score_severity(ev_type, domain_from_url(url))
    if severity < min_sev:
        return

    published_at = item.get("published_at")
    evidence = url
    company_location = name_to_location.get(best_name)

    row = {
        "created_at": datetime.utcnow().isoformat(),
        "published_at": published_at,
        "company_name": best_name,
        "company_location": company_location,
        "title": title,
        "url": url,
        "source": item.get("source"),
        "event_type": ev_type,
        "severity": severity,
        "confidence": conf,
        "evidence": evidence
    }
    save_event(conn, row)
    # count kept
    try:
        globals()['kept'] += 1
    except Exception:
        pass

    if slack_url:
        try:
            post_slack(slack_url, title=title, company=best_name, url=url,
                       event_type=ev_type, published_at=published_at or "", severity=severity, location=company_location)
        except Exception as e:
            print("[Slack] Failed to post:", e)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--test-slack", action="store_true", help="Post a test message and exit")
    ap.add_argument("--locations-csv", default=None, help="Optional CSV (from Wi‑Fi logs) to merge locations by domain")
    ap.add_argument("--csv", required=True, help="Path to companies.csv")
    ap.add_argument("--config", required=True, help="Path to config.yaml")
    ap.add_argument("--since_days", type=int, default=None, help="Lookback window")
    args = ap.parse_args()
    if args.test_slack:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        slack_url = cfg.get("slack_webhook_url")
        if not slack_url:
            print("[TEST] Missing slack_webhook_url in config.yaml")
            raise SystemExit(1)
        from .slack_delivery import post_slack
        from datetime import datetime
        post_slack(slack_url,
                   title="Synthetic test: Company XYZ raises $10M Series B",
                   company="Company XYZ",
                   url="https://example.com/test",
                   event_type="FUNDING",
                   published_at=datetime.utcnow().isoformat(),
                   severity=0.9,
                   location="Test Location")
        print("[TEST] Sent a test Slack message. Check your channel.")
        raise SystemExit(0)

    if args.test_slack:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        slack_url = cfg.get("slack_webhook_url")
        if not slack_url:
            print("[TEST] Missing slack_webhook_url in config.yaml")
        # Post a synthetic funding event to verify formatting
        from .slack_delivery import post_slack
        post_slack(slack_url,
                   title="Synthetic test: Company XYZ raises $10M Series B",
                   company="Company XYZ",
                   url="https://example.com/test",
                   event_type="FUNDING",
                   published_at=datetime.utcnow().isoformat(),
                   severity=0.9,
                   location="Test Location")
        print("[TEST] Sent a test Slack message. Check your channel.")

    run(args.csv, args.config, args.since_days, verbose=args.verbose, locations_csv=args.locations_csv)
