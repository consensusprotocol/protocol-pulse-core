"""
x_reader.py — Shared X read layer on xAI Agent Tools API (x_search).

WHY THIS EXISTS
The @ProtocolPulseHQ X developer account is credit-depleted (402) for both
reads and writes. Writes are solved via Buffer (buffer_poster.py). This module
solves READS for every consumer (comment_radar, quote_rt_engine, reply engine,
spaces/nitter replacements) using xAI's server-side x_search tool, which reads
X for ~fractions of a cent per call and returns cited, current posts.

Validated live 2026-07-01: POST https://api.x.ai/v1/responses, model grok-4.3,
tools=[{"type":"x_search"}] returned real current posts with url_citation
annotations. The old Live Search (search_parameters) is deprecated (410) — do
not use it.

PUBLIC API
  get_top_posts(handles, hours=24, limit=10)  -> [ {author, url, text,
        engagement, reply_sentiment, post_id, fetched_at} ]
  get_reactions(post_url)                     -> { sentiment,
        top_reply_themes: [...],
        representative_replies: [{author, likes, text}] }

The representative_replies shape intentionally matches what
comment_radar.GrokRadar.synthesize() expects for top_comments, so radar can be
repointed at this module with no synth changes.

DEGRADED HANDLING
xAI may return unsourced training-data answers when filters match nothing.
We reject a response as unsourced when the API marks it degraded OR when there
are zero url_citation annotations backing the text. Callers get [] / None
rather than hallucinated posts.

CACHING & COST
Responses cached to data/x_reader_cache/ (JSON, sha256 key of the request).
Default TTL: 30 min posts, 60 min reactions. Every real API call appends a
line to data/x_reader_cache/cost_log.jsonl with usage + cost_in_usd_ticks.

FEATURE FLAG
config/x_reader_config.json {"enabled": bool, ...}. When disabled, calls
return empty results and log a warning (never raise), so consumers degrade
gracefully.
"""

import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

log = logging.getLogger("x_reader")
if not log.handlers:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data", "x_reader_cache")
COST_LOG = os.path.join(CACHE_DIR, "cost_log.jsonl")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "x_reader_config.json")
ENV_PATH = os.path.join(BASE_DIR, ".env")

XAI_URL = "https://api.x.ai/v1/responses"
XAI_MODEL = "grok-4.3"

DEFAULT_CONFIG = {
    "enabled": False,          # law: new features start FALSE
    "posts_ttl_seconds": 1800,
    "reactions_ttl_seconds": 3600,
    "timeout_seconds": 75,
    "max_handles_per_call": 10,
}

_STATUS_URL_RE = re.compile(r"x\.com/[^/]+/status/(\d+)")


# ---------------------------------------------------------------- config/env

def _load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    except Exception as e:
        log.warning("bad x_reader_config.json (%s); using defaults", e)
    return cfg


def _get_xai_key():
    key = os.environ.get("XAI_API_KEY")
    if key:
        return key
    try:
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith("XAI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


# ------------------------------------------------------------------- cache

def _cache_key(kind, payload):
    raw = kind + "|" + json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _cache_get(key, ttl):
    path = os.path.join(CACHE_DIR, key + ".json")
    try:
        st = os.stat(path)
        if time.time() - st.st_mtime > ttl:
            return None
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _cache_put(key, value):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, key + ".json"), "w") as f:
            json.dump(value, f)
    except Exception as e:
        log.warning("cache write failed: %s", e)


def _log_cost(kind, usage):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        ticks = usage.get("cost_in_usd_ticks")
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "server_side_tools": usage.get("num_server_side_tools_used"),
            "cost_in_usd_ticks": ticks,
            "est_usd": (ticks / 1e10) if isinstance(ticks, (int, float)) else None,
        }
        with open(COST_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning("cost log failed: %s", e)


# ------------------------------------------------------------- xAI plumbing

def _call_xsearch(prompt, handles=None, from_date=None, to_date=None,
                  timeout=75):
    """Raw call. Returns (text, citations, usage) or (None, [], {}) on
    failure/degraded/unsourced."""
    key = _get_xai_key()
    if not key:
        log.error("XAI_API_KEY not found (env or .env)")
        return None, [], {}

    tool = {"type": "x_search"}
    if handles:
        tool["allowed_x_handles"] = list(handles)
    if from_date:
        tool["from_date"] = from_date
    if to_date:
        tool["to_date"] = to_date

    body = {
        "model": XAI_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [tool],
    }
    req = urllib.request.Request(
        XAI_URL, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        log.error("xAI HTTP %s: %s", e.code, e.read().decode()[:300])
        return None, [], {}
    except Exception as e:
        log.error("xAI call failed: %s", e)
        return None, [], {}

    usage = data.get("usage", {}) or {}
    _log_cost("x_search", usage)

    if data.get("degraded"):
        log.warning("x_search DEGRADED response — rejecting as unsourced")
        return None, [], usage

    text, citations = "", []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text += c.get("text", "")
                    for ann in c.get("annotations", []) or []:
                        if ann.get("type") == "url_citation":
                            citations.append(ann.get("url", ""))

    if not text.strip():
        log.warning("x_search returned empty text")
        return None, [], usage
    if not citations:
        log.warning("x_search returned text with ZERO citations — rejecting "
                    "as unsourced (anti-hallucination gate)")
        return None, [], usage
    return text, citations, usage


def parse_json_block(text):
    """Extract the first JSON array/object from model text (handles ``` fences
    and prose preamble). Returns parsed value or None."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.rstrip().endswith("```"):
            t = t.rstrip().rsplit("```", 1)[0]
    t = t.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    # find first [...] or {...} region — try whichever opener occurs FIRST
    pairs = [(t.find(o), o, c) for o, c in (("[", "]"), ("{", "}"))]
    pairs = sorted([p for p in pairs if p[0] != -1])
    for start, opener, closer in pairs:
        depth = 0
        for i in range(start, len(t)):
            if t[i] == opener:
                depth += 1
            elif t[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(t[start:i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def extract_post_id(url):
    """x.com status URL -> post id string, or ''."""
    m = _STATUS_URL_RE.search(url or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------- public api

def get_top_posts(handles, hours=24, limit=10):
    """Top recent posts from the given handles via x_search.

    Returns a list of dicts:
      {author, url, text, engagement, reply_sentiment, post_id, fetched_at}
    Empty list on failure/disabled/unsourced. Never raises.
    """
    cfg = _load_config()
    if not cfg.get("enabled"):
        log.warning("x_reader disabled via config/x_reader_config.json")
        return []
    handles = list(handles)[: cfg["max_handles_per_call"]]

    payload = {"handles": sorted(handles), "hours": hours, "limit": limit}
    key = _cache_key("posts", payload)
    cached = _cache_get(key, cfg["posts_ttl_seconds"])
    if cached is not None:
        return cached

    since = (datetime.now(timezone.utc) - timedelta(hours=hours))
    prompt = (
        "Find the {n} highest-engagement Bitcoin-related X posts from these "
        "accounts since {since} UTC: {handles}. Only include posts you can "
        "actually see on X right now. For each post return: the author handle "
        "(without @), the full x.com status URL, the complete post text, the "
        "like count as an integer, the retweet count as an integer, the reply "
        "count as an integer, and a one-word sentiment of the replies to it "
        "(bullish/bearish/mixed/neutral). Respond with ONLY a JSON array of "
        "objects with keys: author, url, text, likes, retweets, replies, "
        "reply_sentiment. No prose, no markdown fences."
    ).format(n=limit, since=since.strftime("%Y-%m-%d %H:%M"),
             handles=", ".join("@" + h for h in handles))

    text, citations, _ = _call_xsearch(
        prompt, handles=handles,
        from_date=since.strftime("%Y-%m-%d"),
        timeout=cfg["timeout_seconds"])
    if text is None:
        return []

    parsed = parse_json_block(text)
    if not isinstance(parsed, list):
        log.warning("get_top_posts: could not parse JSON array from response")
        return []

    now_iso = datetime.now(timezone.utc).isoformat()
    posts = []
    for p in parsed:
        if not isinstance(p, dict):
            continue
        url = str(p.get("url", ""))
        pid = extract_post_id(url)
        if not pid:
            continue  # no verifiable status URL -> drop
        author = str(p.get("author", "")).lstrip("@")
        if handles and author.lower() not in {h.lower() for h in handles}:
            continue  # hard filter: only requested handles
        try:
            likes = int(p.get("likes", 0))
        except (TypeError, ValueError):
            likes = 0
        def _i(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0
        posts.append({
            "author": author,
            "url": url,
            "text": str(p.get("text", "")).strip(),
            "engagement": likes,
            "retweets": _i(p.get("retweets", 0)),
            "replies": _i(p.get("replies", 0)),
            "reply_sentiment": str(p.get("reply_sentiment", "unknown")),
            "post_id": pid,
            "fetched_at": now_iso,
        })
    posts.sort(key=lambda x: x["engagement"], reverse=True)
    posts = posts[:limit]
    if posts:
        _cache_put(key, posts)
    return posts


def get_reactions(post_url):
    """Reply sentiment + themes + representative replies for one post.

    Returns:
      {sentiment: str, top_reply_themes: [str],
       representative_replies: [{author, likes, text}]}   (radar-compatible)
    or None on failure/disabled/unsourced. Never raises.
    """
    cfg = _load_config()
    if not cfg.get("enabled"):
        log.warning("x_reader disabled via config/x_reader_config.json")
        return None
    pid = extract_post_id(post_url)
    if not pid:
        log.warning("get_reactions: not a status URL: %s", post_url)
        return None

    key = _cache_key("reactions", {"post_id": pid})
    cached = _cache_get(key, cfg["reactions_ttl_seconds"])
    if cached is not None:
        return cached

    prompt = (
        "Look at the replies to this X post: {url} . Summarize the overall "
        "reply sentiment in one word (bullish/bearish/mixed/neutral), list up "
        "to 5 short reply themes, and quote up to 8 representative real "
        "replies with their author handle (without @) and approximate like "
        "count. Only include replies you can actually see. Respond with ONLY "
        "a JSON object with keys: sentiment (string), top_reply_themes "
        "(array of strings), representative_replies (array of objects with "
        "keys author, likes, text). No prose, no markdown fences."
    ).format(url=post_url)

    text, citations, _ = _call_xsearch(prompt, timeout=cfg["timeout_seconds"])
    if text is None:
        return None

    parsed = parse_json_block(text)
    if not isinstance(parsed, dict):
        log.warning("get_reactions: could not parse JSON object")
        return None

    replies = []
    for r in parsed.get("representative_replies", []) or []:
        if not isinstance(r, dict):
            continue
        try:
            likes = int(r.get("likes", 0))
        except (TypeError, ValueError):
            likes = 0
        replies.append({
            "author": str(r.get("author", "?")).lstrip("@"),
            "likes": likes,
            "text": str(r.get("text", "")).strip(),
        })

    result = {
        "sentiment": str(parsed.get("sentiment", "unknown")),
        "top_reply_themes": [str(t) for t in
                             (parsed.get("top_reply_themes") or [])][:5],
        "representative_replies": replies,
    }
    _cache_put(key, result)
    return result


# ----------------------------------------------------------------- CLI smoke

if __name__ == "__main__":
    import sys
    handles = sys.argv[1:] or ["PrestonPysh", "LynAldenContact", "saylor"]
    posts = get_top_posts(handles, hours=24, limit=5)
    print(json.dumps(posts, indent=2)[:2000])
    if posts:
        rx = get_reactions(posts[0]["url"])
        print(json.dumps(rx, indent=2)[:1500])
