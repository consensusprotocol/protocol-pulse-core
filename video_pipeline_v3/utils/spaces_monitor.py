#!/usr/bin/env python3
"""
spaces_monitor.py — X Spaces Discovery Engine V2

STRATEGY (in priority order):
1. Batch API poll: GET /2/spaces/by/creator_ids for ALL monitored handles (one call, 100 user IDs)
2. Participant cross-check: any Space with a legendary handle as host/speaker qualifies regardless of title
3. Tweet link intercept: scan recent tweets of monitored handles for /i/spaces/ links (catches announced spaces)
4. Keyword search fallback: Guest Token GraphQL search for bitcoin/btc/lightning spaces
5. Replay harvest: yt-dlp sweep for ended spaces with replays (daily job)

Runs every 5 minutes via cron.
Per PIPELINE_LAWS.md — no keyword title dependency. Handle-first detection.
"""

import json, logging, os, re, statistics, subprocess, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from utils.spaces_pulse import process_spaces_chunk

logger = logging.getLogger("SpacesMonitor")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [spaces] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

LIVE_SIGNALS = os.path.join(BASE, "data", "intelligence", "live_signals.json")
SPACES_CACHE_DIR = os.path.join(BASE, "cache", "spaces")
COOKIE_FILE = os.path.join(BASE, "cache", "x_cookies.txt")

# ─────────────────────────────────────────────────────────────────────────────
# MASTER HANDLE LIST — unified, deduplicated, corrected
# Any Space hosted or participated in by these handles is captured.
# ─────────────────────────────────────────────────────────────────────────────
MONITORED_HANDLES = [
    # Core Bitcoin thought leaders
    "saylor",           # Michael Saylor
    "jack",             # Jack Dorsey
    "lopp",             # Jameson Lopp
    "ODELL",            # Matt Odell
    "matt_odell",       # Matt Odell alt
    "MartyBent",        # Marty Bent
    "PrestonPysh",      # Preston Pysh
    "stephanlivera",    # Stephan Livera
    "natbrunell",       # Natalie Brunell
    "LynAldenContact",  # Lyn Alden
    "gladstein",        # Alex Gladstein
    "saifedean",        # Saifedean Ammous
    "adam3us",          # Adam Back
    "nvk",              # NVK
    "giacomozucco",     # Giacomo Zucco
    "dergigi",          # Gigi
    "pierre_rochard",   # Pierre Rochard — alias BitcoinPierre
    "BitcoinPierre",    # Pierre Rochard
    "coryklippsten",    # Cory Klippsten
    "Breedlove22",      # Robert Breedlove
    "JeffBooth",        # Jeff Booth
    "jimmysong",        # Jimmy Song
    "ToneVays",         # Tone Vays
    "Excellion",        # Samson Mow
    "nic__carter",      # Nic Carter
    "woonomic",         # Willy Woo
    "100trillionUSD",   # PlanB
    "aantonop",         # Andreas Antonopoulos
    "PeterMcCormack",   # Peter McCormack
    "APompliano",       # Anthony Pompliano
    "maxkeiser",        # Max Keiser
    "real_vijay",       # Vijay Boyapati
    "knutsvanholm",     # Knut Svanholm
    "TheGuySwann",      # Guy Swann
    "pete_rizzo_",      # Pete Rizzo
    "TuurDemeester",    # Tuur Demeester
    "MustStopMurad",    # Murad Mahmudov
    "bitstein",         # Michael Goldstein
    "pwuille",          # Pieter Wuille
    "TheBlueMatt",      # Matt Corallo
    "FossGregf",        # Greg Foss
    "parman_the",       # BTC Sessions / Par Man
    "level39",          # Level39
    "bitkite",          # Bitkite
    "BTCization",       # BTCization

    # Media / shows
    "DocumentingBTC",   # Documenting Bitcoin
    "BitcoinMagazine",  # Bitcoin Magazine
    "WhatBitcoinDid",   # Peter McCormack show
    "SimplyBitcoinTV",  # Simply Bitcoin
    "TheBitcoinConf",   # Bitcoin Conference
    "thebitcoinlayer",  # The Bitcoin Layer
    "stacker_news",     # Stacker News

    # Political / macro / institutional
    "nayibbukele",      # President Bukele
    "GaryCardone",      # Gary Cardone
    "LukeDashjr",       # Luke Dashjr

    # Community / traders / analysts
    "dotkrueger",       # Derek Ross
    "TonySeverinoCMT",  # Tony Severino
    "RealCryptoCrank",  # Crypto Crank
    "LadyTraderRa",     # Lady Trader Ra
    "ts_hodl",          # TS Hodl
    "isaiahdaustin",    # Isaiah D Austin
    "BritishHodl",      # British Hodl
    "LorenHodl",        # Loren Hodl
    "Rlad1776",         # Rlad1776
    "TheBTCTherapist",  # BTC Therapist
    "MMCrypto",         # MMCrypto
]

# Subset used for priority weighting in sentiment (top tier)
LEGENDARY_HANDLES = {h.lower() for h in [
    "saylor", "jack", "lopp", "ODELL", "MartyBent", "PrestonPysh",
    "stephanlivera", "natbrunell", "LynAldenContact", "gladstein",
    "saifedean", "adam3us", "nvk", "giacomozucco", "dergigi",
    "pierre_rochard", "BitcoinPierre", "coryklippsten", "Breedlove22",
    "JeffBooth", "jimmysong", "Excellion", "nic__carter", "woonomic",
    "100trillionUSD", "aantonop", "PeterMcCormack", "APompliano",
    "real_vijay", "knutsvanholm", "TuurDemeester", "MustStopMurad",
    "LukeDashjr", "nayibbukele", "GaryCardone", "maxkeiser",
    "ToneVays", "TheGuySwann", "pete_rizzo_", "FossGregf",
]}

# ─────────────────────────────────────────────────────────────────────────────
# Loop detection (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
LOOP_KEYWORDS = ['24/7','live price','live chart','radio','ambient','lofi','non-stop','continuous','price ticker']
REAL_STREAM_KEYWORDS = ['discussion','debate','interview','ama','recap','reaction','breaking','analysis','panel','live with']

def is_looped_stream(stream_info: dict) -> bool:
    red, green = 0, 0
    title_lower = stream_info.get('title','').lower()
    if stream_info.get('duration_seconds',0) > 21600: red += 1
    if any(kw in title_lower for kw in LOOP_KEYWORDS): red += 1
    words = stream_info.get('transcript_sample','').lower().split()
    if len(words) > 100:
        blocks = [' '.join(words[i:i+50]) for i in range(0,len(words)-50,25)]
        if blocks and len(set(blocks))/len(blocks) < 0.5: red += 1
    if stream_info.get('consecutive_live_days',0) >= 2: red += 1
    samples = stream_info.get('viewer_count_samples',[])
    if len(samples) >= 3 and statistics.mean(samples) > 0:
        if (statistics.stdev(samples)/statistics.mean(samples)) < 0.05: red += 1
    if any(kw in title_lower for kw in REAL_STREAM_KEYWORDS): green += 1
    if 1800 <= stream_info.get('duration_seconds',0) <= 18000: green += 1
    is_loop = (red >= 2) and (green == 0)
    if is_loop: logger.warning(f"[LOOP_DETECT] Discarding: {stream_info.get('title')}")
    return is_loop

# ─────────────────────────────────────────────────────────────────────────────
# Topic / sentiment classification (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
TOPIC_KEYWORDS = {
    "mining": ["mining","hashrate","hash rate","difficulty","miner","asic","exahash"],
    "ETF": ["etf","blackrock","fidelity","grayscale","inflows","outflows","ibit","fbtc"],
    "price": ["price","rally","dump","bull","bear","ath","all-time high","crash","pump"],
    "regulation": ["regulation","sec","congress","ban","legislation","gensler","warren"],
    "self-custody": ["custody","keys","wallet","cold storage","not your keys","self custody"],
    "lightning": ["lightning","layer 2","l2","payments","nostr","zap"],
    "macro": ["fed","inflation","interest rate","dollar","treasury","powell","monetary"],
    "institutional": ["saylor","microstrategy","corporate","treasury","institutional"],
    "privacy": ["privacy","coinjoin","mixer","surveillance","kyc"],
    "sovereignty": ["sovereignty","self-sovereign","cypherpunk","decentralize","censorship"],
}
BULLISH_WORDS = ["bullish","moon","pump","rally","accumulate","buy","stack","up","surge","breakout","green","higher","ath"]
BEARISH_WORDS = ["bearish","crash","dump","sell","fear","down","collapse","red","lower","capitulation","panic"]

def classify_text(text):
    text_lower = text.lower()
    topics = [t for t,kws in TOPIC_KEYWORDS.items() if any(kw in text_lower for kw in kws)]
    bull = sum(1 for w in BULLISH_WORDS if w in text_lower)
    bear = sum(1 for w in BEARISH_WORDS if w in text_lower)
    if bull > bear: sentiment = min(90, 50 + bull * 10)
    elif bear > bull: sentiment = max(10, 50 - bear * 10)
    else: sentiment = 50
    return topics, sentiment

# ─────────────────────────────────────────────────────────────────────────────
# Twitter API v2 — STRATEGY 1: Batch handle poll (primary, handle-first)
# ─────────────────────────────────────────────────────────────────────────────
import requests as _requests

X_PUBLIC_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

def _get_bearer():
    """Use project bearer token if available, else public."""
    return os.environ.get("TWITTER_BEARER_TOKEN", X_PUBLIC_BEARER)

def _api_headers():
    return {"Authorization": f"Bearer {_get_bearer()}", "User-Agent": "ProtocolPulse/2.0"}

def _resolve_user_ids(handles: list) -> dict:
    """
    Batch resolve handles → user IDs via GET /2/users/by.
    Returns {handle_lower: user_id}.
    Max 100 per call — we chunk automatically.
    """
    handle_to_id = {}
    for chunk_start in range(0, len(handles), 100):
        chunk = handles[chunk_start:chunk_start+100]
        try:
            r = _requests.get(
                "https://api.twitter.com/2/users/by",
                params={"usernames": ",".join(chunk), "user.fields": "id,username"},
                headers=_api_headers(), timeout=15,
            )
            if r.status_code == 200:
                for u in r.json().get("data", []):
                    handle_to_id[u["username"].lower()] = u["id"]
            else:
                logger.warning(f"[API] users/by HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.warning(f"[API] _resolve_user_ids failed: {e}")
    return handle_to_id

def batch_poll_spaces(handles: list) -> list:
    """
    STRATEGY 1: GET /2/spaces/by/creator_ids — one call per 100 user IDs.
    Returns all live/scheduled Spaces for our handle list.
    No title filtering — handle presence alone qualifies.
    """
    handle_to_id = _resolve_user_ids(handles)
    if not handle_to_id:
        logger.warning("[API] Could not resolve any user IDs — bearer token may be invalid")
        return []

    user_ids = list(handle_to_id.values())
    spaces = []
    id_to_handle = {v: k for k,v in handle_to_id.items()}

    for chunk_start in range(0, len(user_ids), 100):
        chunk = user_ids[chunk_start:chunk_start+100]
        try:
            r = _requests.get(
                "https://api.twitter.com/2/spaces/by/creator_ids",
                params={
                    "user_ids": ",".join(chunk),
                    "space.fields": "id,title,host_ids,speaker_ids,participant_count,started_at,state,ended_at,is_ticketed",
                    "expansions": "host_ids,speaker_ids",
                    "user.fields": "username",
                },
                headers=_api_headers(), timeout=20,
            )
            if r.status_code == 200:
                data = r.json()
                users = {u["id"]: u["username"] for u in data.get("includes",{}).get("users",[])}
                for s in data.get("data", []):
                    host_id = (s.get("host_ids") or [""])[0]
                    host_handle = users.get(host_id, id_to_handle.get(host_id, "unknown"))
                    spaces.append({
                        "video_id": s["id"],
                        "title": s.get("title","") or f"Space by @{host_handle}",
                        "channel": f"@{host_handle}",
                        "source": "x_spaces",
                        "url": f"https://twitter.com/i/spaces/{s['id']}",
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                        "state": s.get("state","live"),
                        "participant_count": s.get("participant_count",0),
                        "detected_via": "batch_api_v2",
                    })
                    logger.info(f"[BATCH] LIVE SPACE: @{host_handle} — {s.get('title','(no title)')}")
            elif r.status_code == 403:
                logger.warning("[API] 403 on spaces/by/creator_ids — token may not have Spaces access")
            else:
                logger.debug(f"[API] spaces/by/creator_ids HTTP {r.status_code}")
        except Exception as e:
            logger.warning(f"[API] batch_poll_spaces error: {e}")

    return spaces

# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY 2: Participant cross-check
# For any Space found, verify if legendary handles are participants/speakers
# ─────────────────────────────────────────────────────────────────────────────
def participant_cross_check(space_id: str) -> list:
    """
    GET /2/spaces/{id} with speaker/listener expansions.
    Returns list of legendary handles found as participants.
    """
    try:
        r = _requests.get(
            f"https://api.twitter.com/2/spaces/{space_id}",
            params={
                "space.fields": "host_ids,speaker_ids,participant_count",
                "expansions": "host_ids,speaker_ids",
                "user.fields": "username",
            },
            headers=_api_headers(), timeout=15,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        users = {u["id"]: u["username"].lower() for u in data.get("includes",{}).get("users",[])}
        return [uname for uname in users.values() if uname in LEGENDARY_HANDLES]
    except Exception:
        return []

# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY 3: Tweet link intercept — scan recent tweets for /i/spaces/ links
# ─────────────────────────────────────────────────────────────────────────────
def tweet_link_intercept(handles: list, handle_to_id: dict) -> list:
    """
    Scan last 30 mins of tweets from monitored handles for Space URLs.
    Catches spaces announced via tweet before showing up in Spaces API.
    """
    since = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    spaces_found = []
    seen_ids = set()

    # Sample up to 20 high-priority handles to keep API calls reasonable
    priority = [h for h in handles if h.lower() in LEGENDARY_HANDLES][:20]

    for handle in priority:
        uid = handle_to_id.get(handle.lower())
        if not uid:
            continue
        try:
            r = _requests.get(
                f"https://api.twitter.com/2/users/{uid}/tweets",
                params={
                    "start_time": since,
                    "max_results": 10,
                    "tweet.fields": "text,created_at",
                    "expansions": "attachments.media_keys",
                },
                headers=_api_headers(), timeout=10,
            )
            if r.status_code != 200:
                continue
            for tweet in r.json().get("data", []):
                text = tweet.get("text","")
                for match in re.finditer(r'twitter\.com/i/spaces/(\w+)|x\.com/i/spaces/(\w+)', text):
                    sid = match.group(1) or match.group(2)
                    if sid and sid not in seen_ids:
                        seen_ids.add(sid)
                        spaces_found.append({
                            "video_id": sid,
                            "title": f"Space announced by @{handle}",
                            "channel": f"@{handle}",
                            "source": "x_spaces",
                            "url": f"https://twitter.com/i/spaces/{sid}",
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                            "state": "live",
                            "detected_via": "tweet_link_intercept",
                        })
                        logger.info(f"[TWEET_INTERCEPT] @{handle} tweeted Space link: {sid}")
        except Exception as e:
            logger.debug(f"[TWEET_INTERCEPT] {handle}: {e}")

    return spaces_found

# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY 4: Guest Token keyword search fallback
# ─────────────────────────────────────────────────────────────────────────────
def guest_token_search() -> list:
    """Fallback keyword search via Guest Token GraphQL when API returns nothing."""
    try:
        r = _requests.post("https://api.twitter.com/1.1/guest/activate.json",
                           headers={"Authorization": f"Bearer {X_PUBLIC_BEARER}"}, timeout=10)
        r.raise_for_status()
        guest_token = r.json()["guest_token"]
    except Exception as e:
        logger.debug(f"[GUEST] Token refresh failed: {e}")
        return []

    headers = {
        "Authorization": f"Bearer {X_PUBLIC_BEARER}",
        "X-Guest-Token": guest_token,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/122.0.0.0 Safari/537.36",
        "X-Twitter-Active-User": "yes",
        "X-Twitter-Client-Language": "en",
    }

    spaces, seen = [], set()
    for kw in ["bitcoin", "btc", "lightning"]:
        try:
            variables = json.dumps({"query": f"{kw} space", "count": 20, "product": "Top"})
            features = json.dumps({
                "responsive_web_graphql_exclude_directive_enabled": True,
                "spaces_2022_h2_spaces_communities_enabled": True,
                "spaces_2022_h2_clipping_enabled": True,
            })
            r = _requests.get(
                "https://twitter.com/i/api/graphql/nK1dw4oV3k4w5TdtcAdSww/SearchTimeline",
                params={"variables": variables, "features": features},
                headers=headers, timeout=15,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            instructions = (data.get("data",{}).get("search_by_raw_query",{})
                              .get("search_timeline",{}).get("timeline",{}).get("instructions",[]))
            for inst in instructions:
                for entry in inst.get("entries",[]):
                    space_result = entry.get("content",{}).get("itemContent",{}).get("audioSpace",{})
                    if not space_result:
                        continue
                    meta = space_result.get("metadata",{})
                    sid = meta.get("rest_id","")
                    if not sid or sid in seen:
                        continue
                    seen.add(sid)
                    creator = (meta.get("creator_results",{}).get("result",{})
                                  .get("legacy",{}).get("screen_name","unknown"))
                    # Only include if creator is in our monitored list
                    if creator.lower() not in {h.lower() for h in MONITORED_HANDLES}:
                        continue
                    state = meta.get("state","").lower()
                    spaces.append({
                        "video_id": sid,
                        "title": meta.get("title","") or f"Space by @{creator}",
                        "channel": f"@{creator}",
                        "source": "x_spaces",
                        "url": f"https://twitter.com/i/spaces/{sid}",
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                        "state": "ended" if state in ("ended","timedout") else state,
                        "detected_via": "guest_token_keyword",
                    })
        except Exception as e:
            logger.debug(f"[GUEST] search {kw}: {e}")

    return spaces

# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY 5: twspace-dl / yt-dlp per-handle (last resort)
# ─────────────────────────────────────────────────────────────────────────────
def _find_twspace_dl():
    for name in ["twspace_dl","twspace-dl"]:
        for p in [os.path.expanduser(f"~/.local/bin/{name}"), f"/usr/local/bin/{name}"]:
            if os.path.exists(p): return p
    return None

TWSPACE_BIN = _find_twspace_dl()

def twspace_handle_check(handles: list) -> list:
    """Last-resort: poll individual handles via twspace-dl. Slow — limit to top 20."""
    if not TWSPACE_BIN:
        return []
    os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
    if not os.path.exists(COOKIE_FILE):
        open(COOKIE_FILE,"w").write("# Netscape HTTP Cookie File\n")

    spaces = []
    priority = [h for h in handles if h.lower() in LEGENDARY_HANDLES][:20]
    for handle in priority:
        try:
            res = subprocess.run(
                [TWSPACE_BIN, "-U", f"https://twitter.com/{handle}", "-c", COOKIE_FILE, "-p"],
                capture_output=True, text=True, timeout=15,
            )
            out = res.stdout.strip() + res.stderr.strip()
            if res.returncode == 0 and out and "no live" not in out.lower() and "error" not in out.lower():
                sid_match = re.search(r'spaces?/([a-zA-Z0-9]+)', out)
                sid = sid_match.group(1) if sid_match else f"twspace_{handle}_{int(time.time())}"
                title_match = re.search(r'title[\"\s:]+(.+?)[\n\"]', out, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else f"Live Space by @{handle}"
                spaces.append({
                    "video_id": sid, "title": title, "channel": f"@{handle}",
                    "source": "x_spaces", "url": f"https://twitter.com/i/spaces/{sid}",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "state": "live", "detected_via": "twspace_dl",
                })
                logger.info(f"[TWSPACE] LIVE: @{handle} — {title}")
        except subprocess.TimeoutExpired:
            logger.debug(f"[TWSPACE] Timeout: @{handle}")
        except Exception as e:
            logger.debug(f"[TWSPACE] {handle}: {e}")
    return spaces

# ─────────────────────────────────────────────────────────────────────────────
# Cookie validity check
# ─────────────────────────────────────────────────────────────────────────────
def check_cookie_validity(path):
    if not os.path.exists(path):
        logger.warning(f"[COOKIE] Missing: {path}")
        return False
    if os.path.getsize(path) < 50:
        logger.info("[COOKIE] Empty placeholder — unauthenticated mode")
        return True
    age = (time.time() - os.path.getmtime(path)) / 86400
    if age > 6:
        logger.warning(f"[COOKIE] {age:.1f} days old — may be stale. Refresh via browser export.")
    return True

# ─────────────────────────────────────────────────────────────────────────────
# Live Signals JSON
# ─────────────────────────────────────────────────────────────────────────────
def load_live_signals():
    if os.path.exists(LIVE_SIGNALS):
        try:
            with open(LIVE_SIGNALS) as f: return json.load(f)
        except (json.JSONDecodeError, OSError): pass
    return {"live_streams":[],"updated_at":None,"monitoring":True,"channels_watched":0}

def save_live_signals(signals):
    os.makedirs(os.path.dirname(LIVE_SIGNALS), exist_ok=True)
    signals["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = LIVE_SIGNALS + ".tmp"
    with open(tmp,"w") as f: json.dump(signals, f, indent=2)
    os.replace(tmp, LIVE_SIGNALS)

def update_live_signals(space_info, topics, sentiment, transcript_chunk=""):
    signals = load_live_signals()
    stream_entry = next((s for s in signals.get("live_streams",[])
                        if s.get("video_id") == space_info.get("video_id")), None)
    if stream_entry is None:
        stream_entry = {
            "video_id": space_info["video_id"],
            "title": space_info["title"],
            "channel": space_info["channel"],
            "source": "x_spaces",
            "url": space_info.get("url",""),
            "started_at": space_info.get("detected_at", datetime.now(timezone.utc).isoformat()),
            "topics":[], "current_sentiment":50, "sentiment_history":[],
            "transcript_chunks":[], "status":"live",
            "detected_via": space_info.get("detected_via","unknown"),
            "participant_count": space_info.get("participant_count",0),
        }
        signals.setdefault("live_streams",[]).append(stream_entry)

    stream_entry["topics"] = list(set(stream_entry.get("topics",[]) + topics))
    if sentiment != 50 or not stream_entry["sentiment_history"]:
        stream_entry["sentiment_history"].append(
            {"time": datetime.now(timezone.utc).isoformat(), "score": sentiment})
        stream_entry["sentiment_history"] = stream_entry["sentiment_history"][-100:]
    recent = stream_entry["sentiment_history"][-5:]
    stream_entry["current_sentiment"] = round(sum(r["score"] for r in recent) / len(recent))
    if transcript_chunk:
        stream_entry["transcript_chunks"].append(transcript_chunk[:200])
        stream_entry["transcript_chunks"] = stream_entry["transcript_chunks"][-50:]
    stream_entry["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_live_signals(signals)
    return stream_entry

# ─────────────────────────────────────────────────────────────────────────────
# Main — unified discovery with strategy cascade
# ─────────────────────────────────────────────────────────────────────────────
def detect_all_spaces() -> list:
    """
    Run all detection strategies in priority order.
    Deduplicate by video_id. Legendary-handle spaces always win.
    """
    check_cookie_validity(COOKIE_FILE)
    all_spaces = []
    seen_ids = set()

    def add_spaces(new_spaces, label):
        added = 0
        for s in new_spaces:
            if s["video_id"] not in seen_ids:
                seen_ids.add(s["video_id"])
                all_spaces.append(s)
                added += 1
        if added: logger.info(f"[{label}] +{added} space(s)")

    # Strategy 1: Batch API (best — no title dependency)
    handle_to_id = {}
    batch_spaces = batch_poll_spaces(MONITORED_HANDLES)
    add_spaces(batch_spaces, "BATCH_API")

    # Resolve IDs for strategy 3 (tweet intercept) — reuse if already done
    if not handle_to_id:
        handle_to_id = _resolve_user_ids(MONITORED_HANDLES)

    # Strategy 2: Participant cross-check for any spaces found
    for s in list(all_spaces):
        legendary = participant_cross_check(s["video_id"])
        if legendary:
            s["legendary_participants"] = legendary
            logger.info(f"[PARTICIPANT] {s['video_id']}: legendary participants — {legendary}")

    # Strategy 3: Tweet link intercept (catches pre-live announcements)
    tweet_spaces = tweet_link_intercept(MONITORED_HANDLES, handle_to_id)
    add_spaces(tweet_spaces, "TWEET_INTERCEPT")

    # Strategy 4: Keyword fallback (only if strategies 1+3 found nothing)
    if not all_spaces:
        guest_spaces = guest_token_search()
        add_spaces(guest_spaces, "GUEST_TOKEN")

    # Strategy 5: twspace-dl last resort
    if not all_spaces:
        twspace_spaces = twspace_handle_check(MONITORED_HANDLES)
        add_spaces(twspace_spaces, "TWSPACE_DL")

    return all_spaces

def run_daemon():
    logger.info(f"[V2] Scanning {len(MONITORED_HANDLES)} handles via 5-strategy cascade...")
    spaces = detect_all_spaces()

    if not spaces:
        logger.info("No active X Spaces detected across all strategies")
    else:
        for space in spaces:
            if is_looped_stream(space):
                continue
            logger.info(f"SPACE: {space['channel']} [{space.get('detected_via','?')}] — {space['title']}")
            topics, sentiment = classify_text(space["title"])
            update_live_signals(space, topics, sentiment, f"X Space detected: {space['title']}")
            process_spaces_chunk(
                space_id=space["video_id"],
                chunk_text=space["title"],
                speaker_handle=space["channel"].lstrip("@"),
                space_url=space.get("url",""),
                chunk_index=0,
            )

    signals = load_live_signals()
    space_count = sum(1 for s in signals.get("live_streams",[])
                     if s.get("source") == "x_spaces" and s.get("status") == "live")
    logger.info(f"[V2] Summary: {space_count} X Spaces in live_signals.json")

if __name__ == "__main__":
    run_daemon()
