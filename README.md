# Member Moments MVP (Public Signals → Slack Alerts)

This prototype watches **public news** for company mentions and flags likely events (e.g., funding, exec change, product launch, awards). It then posts concise alerts into Slack.

## What's new
- **Location-aware alerts**: If your CSV includes `locations_with_counts` (preferred) or `locations`, Slack alerts will mention a **primary location** (e.g., “in Midtown on 50th”).

## Quick start

1) **Install**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2) **Prepare config and CSV**
```bash
cp config.example.yaml config.yaml
# Put your Slack webhook in config.yaml
# Provide your CSV (see format below)
```

3) **Run**
```bash
python -m src.main --csv companies.csv --config config.yaml --since_days 14
```

4) **Slack alerts**
Alerts will show up in your configured Slack channel.

---

## CSV format

Required columns:
- **company_name**
- **website**
- **domains** (semicolon-separated if multiple)

Optional columns:
- **locations_with_counts** (e.g., `Industrious - Midtown on 50th (12); Industrious - Bryant Park (7)`)
- **locations** (`; `-separated list, used if counts aren’t provided)
- **notes**

Example:
```csv
company_name,website,domains,locations_with_counts,locations,notes
Toma,https://toma.ai,toma.ai;get-toma.com,"Industrious - Midtown on 50th (12); Industrious - Bryant Park (7)",,Suite 402 - NYC
Industrious,https://www.industriousoffice.com,industriousoffice.com,,Industrious - Bryant Park,All locations
```

## Config

`config.yaml` keys:
- `slack_webhook_url`: Slack Incoming Webhook (required)
- `newsapi_key`: Optional NewsAPI.org key
- `google_news_lang`: Default `en`
- `min_confidence`: default `0.8`
- `min_severity`: default `0.6`
- `since_days`: default `14`

## Locations (optional)

If your CSV includes a `locations_with_counts` column (like `"Industrious - Midtown (12); Industrious - Bryant Park (7)"`) or a simpler `locations` column, the app will include a **primary location** in Slack alerts.

- Priority is given to `locations_with_counts` by picking the location with the **highest count**.
- If only `locations` is present, it uses the first in the list.
- If neither is present, alerts are posted without a location reference.


## Contextual flair in Slack alerts
Alerts now include a short, context-aware suggestion. Examples:
- FUNDING → “Congratulate them!”
- PRODUCT_LAUNCH → “Give them a shoutout or offer demo space.”
- AWARD → “Congratulate them!”
- EXEC_CHANGE → “Share a note; welcome or support the transition.”
- HIRING → “Congratulate them and consider amplifying openings to the community.”
- LAYOFFS / SECURITY_INCIDENT → “Reach out privately and offer support (compassionate tone).”


### Using `enriched_companies.csv` directly
The loader now auto-detects enriched CSV headers:
- `company_name` **or** `enriched_company_name`
- `website` **or** `wikidata_official_site` **or** `homepage_url`
- `domains` **or** `domain`

You can also provide a separate locations CSV (from the Wi‑Fi logs) and the app will merge by domain:
```
python -m src.main --csv enriched_companies.csv --locations-csv companies_with_locations.csv --config config.yaml --since_days 180
```
