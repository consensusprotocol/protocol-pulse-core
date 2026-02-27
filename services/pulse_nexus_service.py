"""
Sovereign Intelligence Nexus — KOL Pulse feed.
Aggregates real-time signals from X, Nostr, and YouTube into a single Command Log stream.
"""
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import websocket

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


def _valid_url(url):
    try:
        p = urlparse((url or "").strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def _is_placeholder_item(item):
    content = (item.get("content") or "").lower()
    url = (item.get("url") or "").lower()
    external_id = (item.get("external_id") or "").lower()
    if "mock" in external_id:
        return True
    if "/status/mock" in url or "watch?v=mock" in url:
        return True
    generic_markers = (
        "bitcoin alpha flows here",
        "bitcoin signal on nostr",
        "new content from partner channel",
    )
    return any(marker in content for marker in generic_markers)


def _load_collected_signal_feed(limit=80):
    """
    Pull recent verified X/Nostr signals from CollectedSignal.
    This is the same live signal well used by media intel pipelines.
    """
    models = _models()
    rows = (
        models.CollectedSignal.query
        .filter(
            models.CollectedSignal.is_verified == True,  # noqa: E712
            models.CollectedSignal.platform.in_(["x", "nostr"]),
            models.CollectedSignal.collected_at >= datetime.utcnow() - timedelta(hours=72),
        )
        .order_by(models.CollectedSignal.collected_at.desc())
        .limit(max(limit * 2, 120))
        .all()
    )
    out = []
    for r in rows:
        item = {
            "id": f"sig_{r.id}",
            "platform": r.platform,
            "author_handle": r.author_handle,
            "author_name": r.author_name or r.author_handle,
            "content": (r.content or "")[:260],
            "url": r.url,
            "external_id": f"signal_{r.platform}_{r.post_id}",
            "created_at": (r.posted_at or r.collected_at).isoformat() if (r.posted_at or r.collected_at) else None,
        }
        if _is_placeholder_item(item):
            continue
        if not _valid_url(item.get("url")):
            continue
        if not item.get("content"):
            continue
        out.append(item)
    return out[:limit]


def fetch_pulse_x(handles, limit_per_user=3):
    """Fetch recent tweets from KOL X handles. Returns list of dicts {platform, author_handle, author_name, content, url, external_id}."""
    if not handles:
        return []
    out = []
    try:
        from services.x_service import XService
        svc = XService()
        if not getattr(svc, "client_v2", None):
            return []
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
        return []
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
    out = []
    now_ts = int(time.time())
    seen_ids = set()
    # Pull from major relays directly so this still works when third-party APIs are flaky.
    relays = [
        "wss://relay.damus.io",
        "wss://relay.primal.net",
        "wss://nos.lol",
    ]
    if not pubkeys:
        pubkeys = []
    tracked_suffixes = {pk[-16:] for pk in pubkeys if isinstance(pk, str) and pk.startswith("npub")}
    btc_words = ("bitcoin", "btc", "sats", "lightning", "mempool", "hashrate", "mining")

    for relay in relays:
        ws = None
        sub_id = f"pp-{int(time.time() * 1000)}"
        try:
            ws = websocket.create_connection(relay, timeout=6)
            filt = {"kinds": [1], "limit": 35, "since": now_ts - 7200}
            ws.send(json.dumps(["REQ", sub_id, filt], separators=(",", ":")))
            ws.settimeout(1.2)
            # Read a short burst so route stays snappy.
            for _ in range(80):
                raw = ws.recv()
                if not raw:
                    continue
                msg = json.loads(raw)
                if not isinstance(msg, list) or len(msg) < 2:
                    continue
                mtype = msg[0]
                if mtype == "EOSE":
                    break
                if mtype != "EVENT" or len(msg) < 3:
                    continue
                event = msg[2] or {}
                event_id = str(event.get("id") or "").strip()
                content = (event.get("content") or "").strip()
                pubkey = str(event.get("pubkey") or "").strip()
                if not event_id or not content or event_id in seen_ids:
                    continue
                low = content.lower()
                if not any(w in low for w in btc_words):
                    continue
                # If configured npubs exist, lightly bias toward matching pubkey suffix when possible.
                if tracked_suffixes and pubkey and not any(pubkey.endswith(sfx) for sfx in tracked_suffixes):
                    if len(out) >= (limit_total // 2):
                        continue
                seen_ids.add(event_id)
                out.append({
                    "platform": "nostr",
                    "author_handle": pubkey[:16] + "…",
                    "author_name": "Nostr",
                    "content": content[:500],
                    "url": f"https://primal.net/e/{event_id}",
                    "external_id": f"nostr_{event_id}",
                })
                if len(out) >= limit_total:
                    break
        except Exception as e:
            logger.debug("fetch_pulse_nostr relay %s failed: %s", relay, e)
        finally:
            try:
                if ws:
                    ws.send(json.dumps(["CLOSE", sub_id]))
                    ws.close()
            except Exception:
                pass
        if len(out) >= limit_total:
            break
    return out[:limit_total]


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
            return []
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
        return []
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
            if _is_placeholder_item(item):
                continue
            if not _valid_url(item.get("url")):
                continue
            if not (item.get("content") or "").strip():
                continue
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
    """Return latest pulse items for Command Log. Newest first, no placeholders."""
    models = _models()
    rows = (
        models.KOLPulseItem.query
        .order_by(models.KOLPulseItem.created_at.desc())
        .limit(max(limit * 2, 120))
        .all()
    )

    feed = []
    seen_urls = set()
    for r in rows:
        item = {
            "id": r.id,
            "platform": r.platform,
            "author_handle": r.author_handle,
            "author_name": r.author_name or r.author_handle,
            "content": (r.content or "")[:200],
            "url": r.url,
            "external_id": r.external_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        if _is_placeholder_item(item):
            continue
        if not _valid_url(item.get("url")):
            continue
        if not item.get("content"):
            continue
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])
        feed.append(item)
        if len(feed) >= limit:
            return feed

    # Prefer real-time verified signal pipeline (X + Nostr) over synthetic/fallback content.
    try:
        signal_feed = _load_collected_signal_feed(limit=limit)
        for item in signal_feed:
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            feed.append(item)
            if len(feed) >= limit:
                return feed
    except Exception as e:
        logger.warning("get_pulse_feed collected_signal fallback: %s", e)

    # Fallback: if external APIs are unavailable, show real curated posts instead of fake placeholders.
    try:
        post_rows = (
            models.CuratedPost.query
            .order_by(models.CuratedPost.submitted_at.desc())
            .limit(max(limit * 2, 120))
            .all()
        )
        for p in post_rows:
            if not _valid_url(p.original_url):
                continue
            raw_title = (p.title or "").strip()
            raw_preview = (p.content_preview or "").strip()
            if not raw_preview and (not raw_title or raw_title == p.original_url):
                # Skip URL-only rows that were ingested without metadata.
                continue
            content = ((raw_preview or raw_title)[:220]).strip()
            if not content:
                continue
            if content.lower().startswith("http://") or content.lower().startswith("https://"):
                continue
            if p.original_url in seen_urls:
                continue
            seen_urls.add(p.original_url)
            curator_name = None
            try:
                curator_name = p.curator.display_name if p.curator else None
            except Exception:
                curator_name = None
            feed.append({
                "id": p.id,
                "platform": p.platform or "web",
                "author_handle": curator_name or (p.platform or "source"),
                "author_name": curator_name or (p.platform or "source"),
                "content": content,
                "url": p.original_url,
                "external_id": f"curated_{p.id}",
                "created_at": p.submitted_at.isoformat() if p.submitted_at else None,
            })
            if len(feed) >= limit:
                break
    except Exception as e:
        logger.warning("get_pulse_feed curated fallback: %s", e)
    return feed[:limit]


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
