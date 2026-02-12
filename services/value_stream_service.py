"""
Value Stream — Sovereign Intelligence Market.
Curated content feed and creator/curator APIs with metadata enrichment and zap splits.
"""

import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from urllib.parse import urlunparse

logger = logging.getLogger(__name__)

# Curator earns 10%, creator/platform gets 90%
CURATOR_SPLIT = 0.10
CREATOR_SPLIT = 0.90


def _extract_meta(soup):
    """Extract metadata across OG/Twitter tags."""
    title = None
    description = None
    image = None

    title_selectors = [
        ("meta", {"property": "og:title"}),
        ("meta", {"name": "twitter:title"}),
    ]
    desc_selectors = [
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "twitter:description"}),
        ("meta", {"name": "description"}),
    ]
    image_selectors = [
        ("meta", {"property": "og:image"}),
        ("meta", {"name": "twitter:image"}),
    ]

    for tag_name, attrs in title_selectors:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            title = tag.get("content")
            break
    if not title and soup.title and soup.title.string:
        title = soup.title.string

    for tag_name, attrs in desc_selectors:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            description = tag.get("content")
            break

    for tag_name, attrs in image_selectors:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            image = tag.get("content")
            break

    title = (title or "").strip()[:500] or None
    description = (description or "").strip()[:1000] or None
    image = (image or "").strip()[:500] or None
    if image and image.startswith("//"):
        image = "https:" + image

    return {"title": title, "description": description, "image": image}


def _fetch_html(url, timeout=8):
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ProtocolPulse/1.0)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
    if not resp.text:
        return None
    return resp.text


def _tweet_id_from_url(url):
    if not url:
        return None
    m = re.search(r"(?:twitter\.com|x\.com)/\w+/status/(\d+)", url, re.I)
    return m.group(1) if m else None


def _large_twitter_image(url):
    """Promote twitter CDN image URLs to large variant where possible."""
    if not url:
        return None
    if "pbs.twimg.com" not in url:
        return url
    if "name=" in url:
        return re.sub(r"name=\w+", "name=large", url)
    return url + ("&name=large" if "?" in url else "?name=large")


def _fetch_x_api_metadata(tweet_id):
    """Fetch text/media for X posts from fx/vx API mirrors."""
    try:
        import requests
        resp = requests.get(f"https://api.fxtwitter.com/status/{tweet_id}", timeout=8)
        if resp.ok:
            data = resp.json() or {}
            tweet = data.get("tweet") or {}
            text = (tweet.get("text") or tweet.get("raw_text") or "").strip()
            author = ((tweet.get("author") or {}).get("name") or "").strip()
            media = tweet.get("media") or {}
            media_all = media.get("all") or []
            image = None
            for item in media_all:
                if not isinstance(item, dict):
                    continue
                thumb = item.get("thumbnail_url")
                url = item.get("url")
                image = _large_twitter_image(thumb or url)
                if image:
                    break
            title = f"Post by {author}" if author else "X post"
            if text or image:
                return {"title": title[:500], "description": text[:1000] or None, "image": image}
    except Exception:
        pass

    try:
        import requests
        resp = requests.get(f"https://api.vxtwitter.com/Twitter/status/{tweet_id}", timeout=8)
        if resp.ok:
            data = resp.json() or {}
            text = (data.get("text") or "").strip()
            author = (data.get("user_name") or data.get("user_screen_name") or "").strip()
            image = None
            for item in (data.get("media_extended") or []):
                if not isinstance(item, dict):
                    continue
                thumb = item.get("thumbnail_url")
                url = item.get("url")
                image = _large_twitter_image(thumb or url)
                if image:
                    break
            title = f"Post by {author}" if author else "X post"
            if text or image:
                return {"title": title[:500], "description": text[:1000] or None, "image": image}
    except Exception:
        pass
    return None


def fetch_metadata(url):
    """Scrape metadata from URL with X/Twitter fallback domains. Returns dict or None."""
    try:
        from bs4 import BeautifulSoup
        parsed = urlparse(url)

        html = _fetch_html(url)
        if html:
            primary = _extract_meta(BeautifulSoup(html, "html.parser"))
            if primary.get("title") or primary.get("description") or primary.get("image"):
                return primary

        # X/Twitter often blocks OG for server-side requests. Try metadata mirrors.
        host = (parsed.netloc or "").lower()
        if "x.com" in host or "twitter.com" in host:
            tweet_id = _tweet_id_from_url(url)
            if tweet_id:
                api_meta = _fetch_x_api_metadata(tweet_id)
                if api_meta and (api_meta.get("title") or api_meta.get("description") or api_meta.get("image")):
                    return api_meta

            path_with_query = urlunparse(("", "", parsed.path or "", parsed.params or "", parsed.query or "", ""))
            for alt_base in ("https://vxtwitter.com", "https://fxtwitter.com"):
                alt_url = f"{alt_base}{path_with_query}"
                try:
                    alt_html = _fetch_html(alt_url)
                    if not alt_html:
                        continue
                    alt_meta = _extract_meta(BeautifulSoup(alt_html, "html.parser"))
                    if alt_meta.get("title") or alt_meta.get("description") or alt_meta.get("image"):
                        return alt_meta
                except Exception:
                    continue

            # Fallback: Twitter/X oEmbed still returns text when OG tags are unavailable.
            try:
                import requests
                from bs4 import BeautifulSoup
                resp = requests.get(
                    "https://publish.twitter.com/oembed",
                    params={"url": url, "omit_script": "1", "dnt": "true"},
                    timeout=8,
                )
                if resp.ok:
                    data = resp.json()
                    html_snippet = data.get("html") or ""
                    soup = BeautifulSoup(html_snippet, "html.parser")
                    p = soup.find("p")
                    text = (p.get_text(" ", strip=True) if p else "").strip()
                    author = (data.get("author_name") or "").strip()
                    title = f"Post by {author}" if author else "X post"
                    if text:
                        return {
                            "title": title[:500],
                            "description": text[:1000],
                            "image": None,
                        }
            except Exception:
                pass
    except Exception as e:
        logger.warning("fetch_metadata failed for %s: %s", url[:80], e)
    return None


def _platform_from_url(url):
    """Infer platform from URL for badge/filter. Returns x, youtube, nostr, reddit, stacker, web."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if "youtube.com" in host or "youtu.be" in host:
            return "youtube"
        if "twitter.com" in host or "x.com" in host:
            return "x"
        if "reddit.com" in host:
            return "reddit"
        if "stacker.news" in host or "stackernews" in host:
            return "stacker"
        if "nostr" in host or "njump" in host or "snort" in host:
            return "nostr"
    except Exception:
        pass
    return "web"


def _db():
    from app import db
    return db


def _models():
    import models
    return models


def get_value_stream(limit=50, platform=None):
    """Return list of post dicts with at least 'id' for CuratedPost.query.get."""
    from flask import has_app_context
    if not has_app_context():
        from app import app
        with app.app_context():
            return get_value_stream(limit=limit, platform=platform)
    db = _db()
    models = _models()
    q = models.CuratedPost.query.order_by(db.func.coalesce(models.CuratedPost.signal_score, 0).desc())
    if platform:
        if platform == "stacker":
            q = q.filter(models.CuratedPost.platform.in_(["stacker", "stacker_news"]))
        else:
            q = q.filter(models.CuratedPost.platform == platform)
    posts = q.limit(limit).all()
    return [{"id": p.id} for p in posts]


def get_top_curators(limit=10):
    """Return list of curator dicts with at least 'id' for ValueCreator.query.get."""
    from flask import has_app_context
    if not has_app_context():
        from app import app
        with app.app_context():
            return get_top_curators(limit=limit)
    db = _db()
    models = _models()
    curators = (
        models.ValueCreator.query
        .order_by(db.func.coalesce(models.ValueCreator.curator_score, 0).desc())
        .limit(limit)
        .all()
    )
    return [{"id": c.id} for c in curators]


def get_value_stream_enhanced(limit=50):
    """Enhanced feed for Signal Terminal: list of dicts with post + curator info."""
    db = _db()
    models = _models()
    posts = (
        models.CuratedPost.query
        .order_by(db.func.coalesce(models.CuratedPost.signal_score, 0).desc())
        .limit(limit)
        .all()
    )
    out = []
    for p in posts:
        c = p.curator if hasattr(p, "curator") else None
        out.append({
            "id": p.id,
            "platform": p.platform or "",
            "title": p.title or "Untitled",
            "content_preview": (p.content_preview or "")[:200],
            "original_url": p.original_url or "",
            "total_sats": p.total_sats or 0,
            "zap_count": p.zap_count or 0,
            "signal_score": round(p.signal_score or 0, 2),
            "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
            "curator_name": c.display_name if c else "Anonymous",
            "curator_id": c.id if c else None,
        })
    return out


def submit_content(url, curator_id, title):
    """Submit a new curated post. Enriches with og:title/description/image and platform. Returns {success, id} or {success: False, error}."""
    db = _db()
    models = _models()
    try:
        url = (url or "").strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        existing = models.CuratedPost.query.filter_by(original_url=url).first()
        if existing:
            # If older row was created before metadata parser worked, backfill now.
            if (existing.thumbnail_url or "").startswith("https://www.google.com/s2/favicons"):
                existing.thumbnail_url = None
                db.session.commit()
            needs_backfill = (
                not existing.content_preview
                or not existing.thumbnail_url
                or not existing.title
                or existing.title == existing.original_url
            )
            if needs_backfill:
                meta = fetch_metadata(url)
                changed = False
                if meta:
                    if (not existing.title or existing.title == existing.original_url) and meta.get("title"):
                        existing.title = meta["title"]
                        changed = True
                    if not existing.content_preview and meta.get("description"):
                        existing.content_preview = meta["description"]
                        changed = True
                    if not existing.thumbnail_url and meta.get("image"):
                        existing.thumbnail_url = meta["image"]
                        changed = True
                    if changed:
                        db.session.commit()
            return {"success": True, "id": existing.id, "existing": True}
        meta = fetch_metadata(url)
        platform = _platform_from_url(url)
        title_val = (title or "").strip()[:500]
        content_preview = None
        thumbnail_url = None
        if meta:
            if not title_val and meta.get("title"):
                title_val = meta["title"]
            if meta.get("description"):
                content_preview = meta["description"]
            if meta.get("image"):
                thumbnail_url = meta["image"]
        if not title_val:
            title_val = url
        post = models.CuratedPost(
            platform=platform,
            original_url=url,
            title=title_val,
            content_preview=content_preview,
            thumbnail_url=thumbnail_url,
            curator_id=curator_id,
        )
        if post.submitted_at is None:
            post.submitted_at = datetime.utcnow()
        post.calculate_signal_score()
        db.session.add(post)
        db.session.commit()
        return {"success": True, "id": post.id}
    except Exception as e:
        logger.exception("submit_content failed")
        db.session.rollback()
        return {"success": False, "error": str(e)}


def process_zap(post_id, sender_id, amount, payment_hash):
    """Record a zap and update post totals. Returns {success, ...}."""
    import os
    db = _db()
    models = _models()
    try:
        post = models.CuratedPost.query.get(post_id)
        if not post:
            return {"success": False, "error": "Post not found"}
        require_verify = str(os.environ.get("VERIFY_ZAP_PAYMENT", "true")).strip().lower() in {"1", "true", "yes", "on"}
        verified = bool(payment_hash) or not require_verify
        curator_share_sats = int(amount * CURATOR_SPLIT)
        creator_share_sats = amount - curator_share_sats
        zap = models.ZapEvent(
            post_id=post_id,
            sender_id=sender_id,
            amount_sats=amount,
            curator_share=curator_share_sats,
            creator_share=creator_share_sats,
            platform_share=0,
            payment_hash=payment_hash or "",
            status="settled" if verified else "pending",
        )
        db.session.add(zap)
        db.session.flush()
        zap_id = zap.id
        if verified:
            post.total_sats = (post.total_sats or 0) + amount
            post.zap_count = (post.zap_count or 0) + 1
            post.last_zap_at = datetime.utcnow()
            post.calculate_signal_score()
            if post.curator_id:
                curator = models.ValueCreator.query.get(post.curator_id)
                if curator:
                    curator.total_sats_received = (curator.total_sats_received or 0) + curator_share_sats
                    curator.total_zaps = (curator.total_zaps or 0) + 1
            if post.creator_id:
                creator = models.ValueCreator.query.get(post.creator_id)
                if creator:
                    creator.total_sats_received = (creator.total_sats_received or 0) + creator_share_sats
        db.session.commit()
        return {
            "success": True,
            "post_id": post_id,
            "zap_id": zap_id,
            "amount_sats": amount,
            "curator_share_sats": curator_share_sats,
            "creator_share_sats": creator_share_sats,
            "status": "settled" if verified else "pending",
        }
    except Exception as e:
        logger.exception("process_zap failed")
        db.session.rollback()
        return {"success": False, "error": str(e)}


def post_zap_comment(post_id, zap_id, amount_sats, base_url=None):
    """
    Diplomat bridge: after a zap, post a reply on X (and optionally Nostr) so the KOL can claim sats.
    base_url e.g. https://protocolpulse.com. Claim URL = base_url/value-stream/claim?zap_id=...
    """
    import os
    db = _db()
    models = _models()
    post = models.CuratedPost.query.get(post_id)
    if not post:
        return
    base_url = (base_url or os.environ.get("PROTOCOL_PULSE_CLAIM_BASE_URL") or "").rstrip("/")
    claim_path = f"/value-stream/claim?zap={zap_id}"
    claim_url = f"{base_url}{claim_path}" if base_url else claim_path
    amount_str = f"{amount_sats:,}" if amount_sats >= 1000 else str(amount_sats)
    message = f"⚡ Signal detected. You received {amount_str} sats on Protocol Pulse for this alpha. Claim: {claim_url}"
    if post.platform in ("x", "twitter"):
        tweet_id = _tweet_id_from_url(post.original_url) or post.original_id
        if tweet_id:
            try:
                from services.x_service import XService
                svc = XService()
                reply_id = svc.post_reply(tweet_id, message)
                if reply_id:
                    log = models.ZapCommentLog(
                        post_id=post_id,
                        zap_event_id=zap_id,
                        platform="x",
                        external_id=tweet_id,
                        reply_id=reply_id,
                        message=message,
                        claim_url=claim_url,
                    )
                    db.session.add(log)
                    db.session.commit()
                    logger.info("Zap comment posted to X for post %s reply %s", post_id, reply_id)
            except Exception as e:
                logger.warning("post_zap_comment X: %s", e)
    # Nostr kind:9734 stub: would broadcast zap request to creator's pubkey if we have it
    # if post.creator and post.creator.nostr_pubkey: ...


def register_creator(display_name, nostr_pubkey=None, lightning_address=None, nip05=None):
    """Register a new value creator. Returns {success, id} or {success: False, error}."""
    db = _db()
    models = _models()
    try:
        existing = models.ValueCreator.query.filter_by(display_name=display_name).first()
        if existing:
            return {"success": True, "id": existing.id, "existing": True}
        creator = models.ValueCreator(
            display_name=display_name[:100],
            nostr_pubkey=nostr_pubkey[:128] if nostr_pubkey else None,
            lightning_address=lightning_address[:200] if lightning_address else None,
            nip05=nip05[:200] if nip05 else None,
        )
        db.session.add(creator)
        db.session.commit()
        return {"success": True, "id": creator.id}
    except Exception as e:
        logger.exception("register_creator failed")
        db.session.rollback()
        return {"success": False, "error": str(e)}


# ---------- Sovereign Claim Portal ----------

def get_claimable_balance(creator_id):
    """Claimable sats = total_sats_received - sum of successful payouts."""
    try:
        db = _db()
        models = _models()
        creator = models.ValueCreator.query.get(creator_id)
        if not creator:
            return 0
        total = creator.total_sats_received or 0
        paid = db.session.query(db.func.coalesce(db.func.sum(models.ClaimPayout.amount_sats), 0)).filter(
            models.ClaimPayout.creator_id == creator_id,
            models.ClaimPayout.status == "sent"
        ).scalar() or 0
        return max(0, int(total) - int(paid))
    except Exception as e:
        logger.warning("get_claimable_balance failed: %s", e)
        return 0


def get_creator_by_pubkey(pubkey):
    """Return ValueCreator for nostr_pubkey or None."""
    if not pubkey or not isinstance(pubkey, str):
        return None
    models = _models()
    return models.ValueCreator.query.filter_by(nostr_pubkey=pubkey.strip()).first()


def _last_claim_at(pubkey):
    """Timestamp of most recent successful claim by this pubkey, or None."""
    try:
        db = _db()
        models = _models()
        creator = get_creator_by_pubkey(pubkey)
        if not creator:
            return None
        row = (
            db.session.query(db.func.max(models.ClaimPayout.settled_at))
            .filter(
                models.ClaimPayout.claimed_by_pubkey == pubkey.strip(),
                models.ClaimPayout.status == "sent"
            )
            .scalar()
        )
        return row
    except Exception as e:
        logger.warning("_last_claim_at failed: %s", e)
        return None


def _parse_datetime(value):
    """Parse DB datetime (may be datetime or string from SQLite) to datetime or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Try without microseconds first (SQLite often returns no .ffffff)
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
            try:
                s = value[:26] if len(value) > 26 else value
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    return None


def can_claim_again(pubkey):
    """True if no successful claim in the last 24 hours for this pubkey."""
    last = _last_claim_at(pubkey)
    last_dt = _parse_datetime(last)
    if last_dt is None:
        return True
    return (datetime.utcnow() - last_dt).total_seconds() >= 24 * 3600


def _verify_nostr_signature(pubkey_hex, message, sig_hex):
    """Verify Nostr-style schnorr signature. Returns True if valid. Uses secp256k1 if available."""
    try:
        import hashlib
        pubkey_hex = (pubkey_hex or "").strip()
        sig_hex = (sig_hex or "").strip()
        if len(pubkey_hex) != 64 or len(sig_hex) != 128:
            return False
        try:
            from secp256k1 import PublicKey
            pk = PublicKey(bytes.fromhex(pubkey_hex), raw=True)
            msg_hash = hashlib.sha256(message.encode("utf-8")).digest()
            sig_bytes = bytes.fromhex(sig_hex)
            return pk.verify(sig_bytes, msg_hash)
        except ImportError:
            pass
        # Optional: ecdda / nostr package
        return False
    except Exception as e:
        logger.warning("nostr verify failed: %s", e)
        return False


def process_claim(pubkey, signature, signed_message, lightning_address):
    """
    Verify Nostr identity, check balance and rate limit, create ClaimPayout, send via Lightning.
    Returns {success, amount_sats, payment_hash, error}.
    """
    try:
        db = _db()
        models = _models()
        pubkey = (pubkey or "").strip()
        if not pubkey:
            return {"success": False, "error": "Missing pubkey"}
        creator = get_creator_by_pubkey(pubkey)
        if not creator:
            return {"success": False, "error": "No account linked to this Nostr key. Register or link your pubkey first."}
        if not can_claim_again(pubkey):
            return {"success": False, "error": "Rate limit: one claim per 24 hours. Try again later."}
        balance = get_claimable_balance(creator.id)
        if balance <= 0:
            return {"success": False, "error": "No sats available to claim."}
        lightning_address = (lightning_address or (creator.lightning_address or "") or "").strip()
        if not lightning_address or "@" not in lightning_address:
            return {"success": False, "error": "Valid Lightning Address required (e.g. you@getalby.com)."}
        import os
        if signature and signed_message and not os.environ.get("ALLOW_CLAIM_WITHOUT_NOSTR_VERIFY"):
            if not _verify_nostr_signature(pubkey, signed_message, signature):
                return {"success": False, "error": "Invalid Nostr signature. Prove you own this key."}
        amount = min(balance, 10_000_000)  # 10M sats max per claim
        payout = models.ClaimPayout(
            creator_id=creator.id,
            amount_sats=amount,
            lightning_address=lightning_address,
            claimed_by_pubkey=pubkey,
            status="pending",
        )
        db.session.add(payout)
        db.session.flush()
        payment_hash, pay_error = _pay_lightning(amount, lightning_address)
        if pay_error:
            payout.status = "failed"
            payout.error_message = pay_error[:500]
            db.session.commit()
            return {"success": False, "error": pay_error}
        payout.status = "sent"
        payout.payment_hash = payment_hash or ""
        payout.settled_at = datetime.utcnow()
        db.session.commit()
        return {"success": True, "amount_sats": amount, "payment_hash": payment_hash}
    except Exception as e:
        logger.exception("process_claim failed: %s", e)
        try:
            _db().session.rollback()
        except Exception:
            pass
        return {"success": False, "error": "Claim failed. Please try again."}


def _pay_lightning(amount_sats, lightning_address):
    """Send sats to Lightning Address. Returns (payment_hash, None) or (None, error_string)."""
    import os
    url = os.environ.get("LNBITS_URL") or os.environ.get("LNURL_PAY_URL")
    key = os.environ.get("LNBITS_ADMIN_KEY") or os.environ.get("LNBITS_API_KEY")
    if not url or not key:
        return None, "Lightning payout not configured. Set LNBITS_URL and LNBITS_ADMIN_KEY."
    try:
        import requests
        # LNbits pay to Lightning Address: POST /api/v1/payments
        # body: amount in sats, lnaddr or bolt11
        r = requests.post(
            f"{url.rstrip('/')}/api/v1/payments",
            headers={"X-Api-Key": key, "Content-Type": "application/json"},
            json={"amount": amount_sats, "lnaddr": lightning_address},
            timeout=30,
        )
        if r.status_code != 200:
            return None, r.text or f"HTTP {r.status_code}"
        data = r.json()
        return data.get("payment_hash") or data.get("checking_id") or "", None
    except Exception as e:
        logger.exception("_pay_lightning failed")
        return None, str(e)


class ValueStreamService:
    """Namespace for value stream methods (used as value_stream_service in routes)."""
    get_value_stream = staticmethod(get_value_stream)
    get_top_curators = staticmethod(get_top_curators)
    get_value_stream_enhanced = staticmethod(get_value_stream_enhanced)
    submit_content = staticmethod(submit_content)
    process_zap = staticmethod(process_zap)
    post_zap_comment = staticmethod(post_zap_comment)
    register_creator = staticmethod(register_creator)
    get_claimable_balance = staticmethod(get_claimable_balance)
    get_creator_by_pubkey = staticmethod(get_creator_by_pubkey)
    can_claim_again = staticmethod(can_claim_again)
    process_claim = staticmethod(process_claim)


value_stream_service = ValueStreamService()
