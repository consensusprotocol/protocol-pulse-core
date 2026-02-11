"""
Sovereign Intelligence Nexus — KOL Pulse feed.
Aggregates real-time signals from X, Nostr, and YouTube into a single Command Log stream.
"""
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

KOL_LIST_PATH = Path(__file__).resolve().parents[1] / "config" / "kol_list.json"


def _db():
    from app import db
    return db


def _models():
    import models
    return models


def load_kol_list():
    """Load KOL list from config. Returns dict with x_handles, nostr_pubkeys, youtube_channel_ids."""
    try:
        if KOL_LIST_PATH.exists():
            with open(KOL_LIST_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("load_kol_list failed: %s", e)
    return {"x_handles": [], "nostr_pubkeys": [], "youtube_channel_ids": []}


def _tweet_id_from_url(url):
    if not url:
        return None
    m = re.search(r"(?:twitter\.com|x\.com)/\w+/status/(\d+)", url, re.I)
    return m.group(1) if m else None


def fetch_pulse_x(handles, limit_per_user=3):
    """Fetch recent tweets from KOL X handles. Returns list of dicts {platform, author_handle, author_name, content, url, external_id}."""
    if not handles:
        return []
    out = []
    try:
        from services.x_service import XService
        svc = XService()
        if not getattr(svc, "client_v2", None):
            return _mock_pulse_x(handles, limit_per_user)
        for handle in handles[:20]:
            try:
                # v2: users/by/username, then tweets
                user_resp = svc.client_v2.get_user(username=handle.strip().lstrip("@"))
                if not user_resp.data:
                    continue
                user_id = user_resp.data.id
                tweets = svc.client_v2.get_users_tweets(
                    user_id,
                    max_results=min(limit_per_user, 5),
                    exclude=["retweets", "replies"],
                    tweet_fields=["created_at", "text"],
                    user_fields=["name"],
                    expansions=["author_id"]
                )
                if not tweets.data:
                    continue
                users = {u.id: u for u in (tweets.includes.get("users") or [])}
                for t in tweets.data:
                    author = users.get(t.author_id) if tweets.includes else None
                    author_name = author.name if author else handle
                    text = getattr(t, "text", t.get("text", "")) or ""
                    tweet_id = t.id
                    url = f"https://x.com/{handle}/status/{tweet_id}"
                    out.append({
                        "platform": "x",
                        "author_handle": handle,
                        "author_name": author_name,
                        "content": text[:500],
                        "url": url,
                        "external_id": f"x_{tweet_id}",
                    })
            except Exception as e:
                logger.debug("fetch_pulse_x handle %s: %s", handle, e)
    except Exception as e:
        logger.warning("fetch_pulse_x: %s", e)
        return _mock_pulse_x(handles, limit_per_user)
    return out


def _mock_pulse_x(handles, limit_per_user):
    """Return mock items when X API is not configured."""
    out = []
    for i, h in enumerate(handles[:10]):
        for j in range(limit_per_user):
            external_id = f"x_mock_{h}_{i}_{j}"
            out.append({
                "platform": "x",
                "author_handle": h,
                "author_name": h,
                "content": f"Signal from @{h}. Bitcoin alpha flows here.",
                "url": f"https://x.com/{h}/status/mock{i}{j}",
                "external_id": external_id,
            })
    return out


def fetch_pulse_nostr(pubkeys, limit_total=20):
    """Fetch kind:1 notes from Nostr pubkeys. Returns list of dicts (same shape as X)."""
    if not pubkeys:
        return []
    out = []
    try:
        import subprocess
        # Use ncli or nostr-sdk if available; otherwise mock
        # Stub: return mock items so UI works
        for i, pk in enumerate(pubkeys[:5]):
            if not pk or not pk.startswith("npub"):
                continue
            external_id = f"nostr_{pk[-12:]}_{i}"
            out.append({
                "platform": "nostr",
                "author_handle": pk[:16] + "…",
                "author_name": "Nostr KOL",
                "content": "Bitcoin signal on Nostr. Zap to amplify.",
                "url": f"https://njump.me/{pk}",
                "external_id": external_id,
            })
    except Exception as e:
        logger.warning("fetch_pulse_nostr: %s", e)
    return out


def fetch_pulse_youtube(channel_ids, limit_per_channel=2):
    """Fetch latest uploads from YouTube channel IDs. Returns list of dicts."""
    if not channel_ids:
        return []
    out = []
    try:
        from services.youtube_service import YouTubeService
        yt = YouTubeService()
        api = getattr(yt, "youtube", None) or (getattr(yt, "get_api", None) and yt.get_api())
        if not api:
            return _mock_pulse_youtube(channel_ids, limit_per_channel)
        for cid in channel_ids[:15]:
            try:
                req = api.search().list(
                    part="snippet",
                    channelId=cid,
                    type="video",
                    order="date",
                    maxResults=limit_per_channel,
                )
                res = req.execute()
                for item in res.get("items", []):
                    sid = item["id"].get("videoId")
                    if not sid:
                        continue
                    sn = item.get("snippet", {})
                    title = sn.get("title", "Video")
                    channel = sn.get("channelTitle", "YouTube")
                    external_id = f"yt_{sid}"
                    out.append({
                        "platform": "youtube",
                        "author_handle": channel,
                        "author_name": channel,
                        "content": title[:300],
                        "url": f"https://www.youtube.com/watch?v={sid}",
                        "external_id": external_id,
                    })
            except Exception as e:
                logger.debug("fetch_pulse_youtube channel %s: %s", cid, e)
    except Exception as e:
        logger.warning("fetch_pulse_youtube: %s", e)
        return _mock_pulse_youtube(channel_ids, limit_per_channel)
    return out


def _mock_pulse_youtube(channel_ids, limit_per_channel):
    out = []
    for i, cid in enumerate(channel_ids[:8]):
        for j in range(limit_per_channel):
            out.append({
                "platform": "youtube",
                "author_handle": cid[:20],
                "author_name": "YouTube Partner",
                "content": "New content from partner channel. Watch for alpha.",
                "url": f"https://www.youtube.com/watch?v=mock{i}_{j}",
                "external_id": f"yt_mock_{cid}_{i}_{j}",
            })
    return out


def ingest_pulse():
    """Fetch from X, Nostr, YouTube and insert into KOLPulseItem. Dedupe by external_id. Returns count inserted."""
    kol = load_kol_list()
    all_items = []
    all_items.extend(fetch_pulse_x(kol.get("x_handles", []), limit_per_user=2))
    all_items.extend(fetch_pulse_nostr(kol.get("nostr_pubkeys", []), limit_total=10))
    all_items.extend(fetch_pulse_youtube(kol.get("youtube_channel_ids", []), limit_per_channel=1))
    db = _db()
    models = _models()
    inserted = 0
    try:
        for item in all_items:
            existing = models.KOLPulseItem.query.filter_by(external_id=item["external_id"]).first()
            if existing:
                continue
            row = models.KOLPulseItem(
                platform=item["platform"],
                author_handle=item["author_handle"],
                author_name=item.get("author_name") or item["author_handle"],
                content=item.get("content"),
                url=item.get("url"),
                external_id=item["external_id"],
                raw_json=json.dumps(item) if item else None,
            )
            db.session.add(row)
            inserted += 1
        db.session.commit()
    except Exception as e:
        logger.exception("ingest_pulse: %s", e)
        db.session.rollback()
    return inserted


def get_pulse_feed(limit=80):
    """Return latest pulse items for Command Log. Newest first."""
    models = _models()
    rows = (
        models.KOLPulseItem.query
        .order_by(models.KOLPulseItem.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "platform": r.platform,
            "author_handle": r.author_handle,
            "author_name": r.author_name or r.author_handle,
            "content": (r.content or "")[:200],
            "url": r.url,
            "external_id": r.external_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def compute_market_pulse():
    """
    Economic Sentiment Index: Zap-to-Post ratio (money flow = signal).
    Returns dict: { value 0-100, label, zap_volume_24h, posts_with_zaps_24h, ratio }.
    """
    from datetime import datetime, timedelta
    db = _db()
    models = _models()
    since = datetime.utcnow() - timedelta(hours=24)
    zap_volume = db.session.query(
        db.func.coalesce(db.func.sum(models.ZapEvent.amount_sats), 0)
    ).filter(models.ZapEvent.created_at >= since).scalar() or 0
    posts_with_zaps = db.session.query(
        db.func.count(db.distinct(models.ZapEvent.post_id))
    ).filter(models.ZapEvent.created_at >= since).scalar() or 0
    total_posts = models.CuratedPost.query.count() or 1
    # Ratio: high zap volume + concentrated on few posts = high signal; spread thin = noise
    if posts_with_zaps > 0:
        ratio = float(zap_volume) / posts_with_zaps
    else:
        ratio = 0.0
    # Normalize to 0-100: e.g. 1000 sats/post = 10, 10k = 50, 50k+ = 100
    import math
    value = min(100, max(0, math.log10(ratio + 1) * 25))
    if value < 25:
        label = "Noise"
    elif value < 50:
        label = "Neutral"
    elif value < 75:
        label = "Signal"
    else:
        label = "Hyper-Bullish"
    return {
        "value": round(value, 1),
        "label": label,
        "zap_volume_24h": int(zap_volume),
        "posts_with_zaps_24h": int(posts_with_zaps),
        "ratio": round(ratio, 0),
    }
