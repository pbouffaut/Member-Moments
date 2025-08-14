import json, requests
from datetime import datetime

def flair_for_event(event_type: str) -> str:
    et = (event_type or "").upper()
    if et == "FUNDING":
        return "Congratulate them! 🎉"
    if et == "PRODUCT_LAUNCH":
        return "Give them a shoutout or offer demo space."
    if et == "AWARD":
        return "Congratulate them! 🏆"
    if et == "HIRING":
        return "Congratulate them and consider amplifying openings to the community."
    if et == "EXEC_CHANGE":
        return "Share a note; welcome them or support the transition."
    if et in ("LAYOFFS", "SECURITY_INCIDENT"):
        return "Reach out privately and offer support. Keep the tone compassionate."
    return "Consider a friendly shoutout."


def post_slack(webhook_url: str, *, title: str, company: str, url: str, event_type: str, published_at: str, severity: float, location: str | None = None, is_verified: bool = True, tone: str = "NEUTRAL", confidence: float = 1.0):
    ts = published_at or datetime.utcnow().isoformat()
    emoji = {
        "FUNDING": "🎉",
        "EXEC_CHANGE": "🧭",
        "HIRING": "📈",
        "PRODUCT_LAUNCH": "🚀",
        "AWARD": "🏆",
        "PRESS_MENTION": "📰",
    }.get(event_type, "📰")

    location_suffix = f" in {location}" if location else ""
    
    # Add verification status and tone to the message
    verification_emoji = "✅" if is_verified else "⚠️"
    verification_status = f"{verification_emoji} VERIFIED ({confidence:.2f})" if is_verified else f"{verification_emoji} UNVERIFIED ({confidence:.2f})"
    tone_emoji = {"POSITIVE": "✅", "NEGATIVE": "⚠️", "NEUTRAL": "ℹ️"}.get(tone, "ℹ️")
    
    text = f"{emoji} *{event_type}: {company}{location_suffix}*\n{verification_status} · Tone: {tone_emoji} {tone}\n{title}\n<{url}|Evidence> · {ts[:10]} · Sev {severity:.2f}\n_{flair_for_event(event_type)}_"
    payload = {"text": text}
    resp = requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    try:
        resp.raise_for_status()
    except Exception as e:
        print("[Slack] Error posting:", e, resp.text)
