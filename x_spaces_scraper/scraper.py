"""
scraper.py — Real-time X Spaces interceptor for Protocol Pulse.

Finds LIVE Bitcoin spaces, grabs HLS audio streams via yt-dlp,
transcribes with faster-whisper, and extracts the best 15s signal-dense clips.
Also catches recently-ended spaces (within 6h) that are still streamable.

Called by daily_run.py via get_best_space_clips().
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"

# ── Search queries for live/ended space discovery ──────────────────────────
SEARCH_QUERIES = ["bitcoin", "btc", "sound money", "bitcoin mining", "market crash", "federal reserve", "macro bitcoin"]
TIER1_HANDLES = {
    "saylor","jack","lopp","ODELL","matt_odell","MartyBent","PrestonPysh",
    "stephanlivera","natbrunell","LynAldenContact","gladstein","saifedean",
    "adam3us","nvk","giacomozucco","dergigi","pierre_rochard","BitcoinPierre",
    "coryklippsten","Breedlove22","JeffBooth","jimmysong","ToneVays","Excellion",
    "nic__carter","woonomic","100trillionUSD","aantonop","PeterMcCormack",
    "APompliano","maxkeiser","real_vijay","knutsvanholm","TheGuySwann",
    "pete_rizzo_","TuurDemeester","MustStopMurad","FossGregf","LukeDashjr",
    "nayibbukele","GaryCardone","dotkrueger","CJKonstantinos","LawrenceLepard",
    "BobBurnett","DocumentingBTC","BitcoinMagazine","SimplyBitcoinTV",
    "thebitcoinlayer","WhatBitcoinDid","TheBitcoinConf",
    "TonySeverinoCMT","ts_hodl","BritishHodl","TheBTCTherapist",
    "bitstein","parman_the",
    "zerohedge","KobeissiLetter","RaoulGMI","TaviCosta",
}
TIER2_HANDLES = {
    "caitlinlong_","wclementeiii","sethforprivacy","parkerlewis",
    "tomerstrolight","moneyball","stacker_news","level39","isaiahdaustin",
    "LorenHodl","Rlad1776","RealCryptoCrank","LadyTraderRa",
}

# ── Signal scoring keywords ────────────────────────────────────────────────
HIGH_SIGNAL = {
    "bitcoin", "btc", "saylor", "etf", "lightning", "halving", "sovereignty",
    "inflation", "fed", "mining", "hashrate", "blackrock", "regulation",
    "institutional", "freedom", "fiat", "sound money",
}
OPINION_MARKERS = {
    "think", "believe", "actually", "wrong", "right", "truth",
    "critical", "massive", "huge", "nobody", "everyone",
}
DATA_MARKERS = {
    "percent", "million", "billion", "thousand", "price", "rate",
}

# ── Title keywords for space relevance scoring ─────────────────────────────
TITLE_KEYWORDS = {
    "bitcoin", "btc", "saylor", "lightning", "halving", "sovereignty",
    "mining", "etf", "blackrock", "hodl", "satoshi",
}

# Whisper model singleton — loaded once, reused
_whisper_model = None


def _get_whisper_model():
    """Lazy-load faster-whisper model (GPU)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
        logger.info("[SpaceTap] Whisper model loaded (base, cuda, float16)")
    return _whisper_model


def _get_bearer_token() -> str:
    """Get Twitter bearer token from env."""
    token = os.environ.get("TWITTER_BEARER_TOKEN", "")
    if not token:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
        token = os.environ.get("TWITTER_BEARER_TOKEN", "")
    return token


def _score_space(space: dict) -> float:
    """Score a space for signal quality based on participants, title, freshness."""
    score = 0.0
    pc = space.get("participant_count", 0) or 0

    if pc >= 10:
        score += 30
    if pc >= 50:
        score += 20

    title_lower = (space.get("title") or "").lower()
    for kw in TITLE_KEYWORDS:
        if kw in title_lower:
            score += 20
            break

    started = space.get("started_at", "")
    if started:
        try:
            dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            age_minutes = (datetime.now(timezone.utc) - dt).total_seconds() / 60
            if age_minutes <= 120:
                score += 15
            if age_minutes <= 30:
                score += 10
        except (ValueError, TypeError):
            pass

    # Live spaces get priority over ended
    if space.get("state") == "live":
        score += 25

    host_h = (space.get("host_handle") or "").lower().lstrip("@")
    if host_h in TIER1_HANDLES: score += 50
    elif host_h in TIER2_HANDLES: score += 25
    return score


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1 — Find live (and recently ended) Bitcoin spaces
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def find_live_bitcoin_spaces() -> list[dict]:
    """Search Twitter Spaces API for live + recently ended Bitcoin spaces.

    Runs multiple keyword queries, deduplicates, scores, and returns top 5.
    Results cached with 30-minute TTL.
    """
    try:
        return _find_live_bitcoin_spaces_inner()
    except Exception as e:
        logger.error(f"[SpaceTap] find_live_bitcoin_spaces failed: {e}")
        return []


def _find_live_bitcoin_spaces_inner() -> list[dict]:
    bearer = _get_bearer_token()
    if not bearer:
        logger.warning("[SpaceTap] TWITTER_BEARER_TOKEN not set — cannot search spaces")
        return []

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache (30-min TTL)
    now = datetime.now(timezone.utc)
    cache_key = now.strftime("%Y%m%d_%H")
    # Use half-hour buckets
    half = "00" if now.minute < 30 else "30"
    cache_file = CACHE_DIR / f"live_spaces_{cache_key}{half}.json"

    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            cache_age = time.time() - cached.get("fetched_at", 0)
            if cache_age < 1800:  # 30 min
                logger.info(f"[SpaceTap] Using cached spaces ({len(cached['spaces'])} spaces, {cache_age:.0f}s old)")
                return cached["spaces"]
        except (json.JSONDecodeError, KeyError):
            pass

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {bearer}"

    seen_ids: set[str] = set()
    all_spaces: list[dict] = []

    # Search both live and ended states
    for state in ("live", "ended"):
        for query in SEARCH_QUERIES:
            try:
                r = session.get(
                    "https://api.twitter.com/2/spaces/search",
                    params={
                        "query": query,
                        "state": state,
                        "space.fields": "creator_id,title,participant_count,started_at,state",
                    },
                    timeout=15,
                )
                if r.status_code == 429:
                    logger.warning("[SpaceTap] API rate limited — skipping live search")
                    # Return whatever we have so far
                    break
                if r.status_code != 200:
                    logger.warning(f"[SpaceTap] Spaces search {query}/{state}: HTTP {r.status_code}")
                    continue

                data = r.json()
                spaces = data.get("data", [])

                for s in spaces:
                    sid = s.get("id", "")
                    if not sid or sid in seen_ids:
                        continue
                    seen_ids.add(sid)

                    space_dict = {
                        "space_id": sid,
                        "title": s.get("title", ""),
                        "creator_id": s.get("creator_id", ""),
                        "participant_count": s.get("participant_count", 0),
                        "started_at": s.get("started_at", ""),
                        "state": s.get("state", "").lower(),
                    }
                    all_spaces.append(space_dict)

            except requests.exceptions.RequestException as e:
                logger.debug(f"[SpaceTap] Search {query}/{state} request error: {e}")
            except Exception as e:
                logger.debug(f"[SpaceTap] Search {query}/{state} error: {e}")

    if not all_spaces:
        logger.info("[SpaceTap] No live Bitcoin spaces found")
        return []

    # Filter ended spaces: must be within 6 hours
    cutoff = datetime.now(timezone.utc)
    filtered = []
    for s in all_spaces:
        if s["state"] == "ended":
            started = s.get("started_at", "")
            if started:
                try:
                    dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    age_hours = (cutoff - dt).total_seconds() / 3600
                    if age_hours > 6:
                        continue
                except (ValueError, TypeError):
                    continue
        # Filter: minimum 3 participants
        pc = s.get("participant_count", 0) or 0
        if pc < 3:
            continue
        filtered.append(s)

    # Score and sort
    for s in filtered:
        s["score"] = _score_space(s)
    filtered.sort(key=lambda x: x["score"], reverse=True)

    # Top 5
    result = filtered[:5]

    logger.info(f"[SpaceTap] Found {len(result)} live Bitcoin spaces")
    for s in result[:3]:
        logger.info(f"[SpaceTap]   '{s['title']}' — {s.get('participant_count', 0)} listeners (score={s['score']:.0f}, {s['state']})")

    # Cache
    cache_file.write_text(json.dumps({
        "spaces": result,
        "fetched_at": time.time(),
    }, indent=2))

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2 — Intercept a single space: stream → transcribe → extract clips
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def intercept_space(space_id: str, title: str, participant_count: int,
                    creator_id: str = "") -> Optional[dict]:
    """Intercept a live/recent space: grab HLS stream, transcribe, extract best clips.

    Returns clip dict or None on failure.
    """
    try:
        return _intercept_space_inner(space_id, title, participant_count, creator_id)
    except Exception as e:
        logger.error(f"[SpaceTap] intercept_space({space_id}) failed: {e}")
        return None


def _intercept_space_inner(space_id: str, title: str, participant_count: int,
                           creator_id: str = "") -> Optional[dict]:
    logger.info(f"[SpaceTap] Intercepting: '{title}' ({participant_count} participants)")

    clip_dir = CACHE_DIR / space_id
    clip_dir.mkdir(parents=True, exist_ok=True)

    # Check for cached clips (reuse if < 30 min old)
    clips_path = clip_dir / "clips.json"
    if clips_path.exists():
        try:
            cached = json.loads(clips_path.read_text())
            intercepted = cached.get("intercepted_at", "")
            if intercepted:
                dt = datetime.fromisoformat(intercepted)
                if (datetime.now(timezone.utc) - dt).total_seconds() < 1800:
                    logger.info(f"[SpaceTap] Using cached intercept for {space_id}")
                    return cached
        except (json.JSONDecodeError, ValueError):
            pass

    # ── Step A: Get HLS stream URL via yt-dlp ──────────────────────────────
    space_url = f"https://twitter.com/i/spaces/{space_id}"
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "--get-url", space_url],
            capture_output=True, text=True, timeout=20,
        )
        m3u8_url = result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"[SpaceTap] yt-dlp timeout for {space_id}")
        return None
    except Exception as e:
        logger.warning(f"[SpaceTap] yt-dlp error for {space_id}: {e}")
        return None

    if not m3u8_url or not m3u8_url.startswith("http"):
        # Fallback: try twspace_dl
        logger.debug(f"[SpaceTap] yt-dlp returned no URL, trying twspace_dl fallback")
        try:
            raw_path = clip_dir / "live_raw.m4a"
            result = subprocess.run(
                ["/home/ultron/.local/bin/twspace_dl",
                 "-i", space_url, "-o", str(raw_path)],
                capture_output=True, text=True, timeout=90,
            )
            if raw_path.exists() and raw_path.stat().st_size > 10000:
                logger.info(f"[SpaceTap] twspace_dl fallback succeeded for {space_id}")
                # Skip to transcription
                m3u8_url = None  # signal to skip ffmpeg grab
            else:
                logger.warning(f"[SpaceTap] twspace_dl also failed for {space_id}")
                return None
        except Exception as e:
            logger.warning(f"[SpaceTap] twspace_dl fallback error: {e}")
            return None

    # ── Step B: Grab 45 seconds of live audio via ffmpeg ───────────────────
    raw_path = clip_dir / "live_raw.m4a"
    if m3u8_url and (not raw_path.exists() or raw_path.stat().st_size < 10000):
        try:
            subprocess.run(
                ["ffmpeg", "-y",
                 "-i", m3u8_url,
                 "-t", "45",
                 "-c:a", "aac", "-ar", "16000", "-ac", "1",
                 str(raw_path)],
                capture_output=True, timeout=60,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"[SpaceTap] ffmpeg timeout grabbing {space_id}")
            return None
        except Exception as e:
            logger.warning(f"[SpaceTap] ffmpeg error for {space_id}: {e}")
            return None

    if not raw_path.exists() or raw_path.stat().st_size < 10000:
        logger.warning(f"[SpaceTap] Audio too small or missing for {space_id}")
        return None

    # ── Step C: Transcribe with faster-whisper ─────────────────────────────
    try:
        model = _get_whisper_model()
        segments_iter, _info = model.transcribe(str(raw_path), language="en")
        segments = []
        for seg in segments_iter:
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            })
    except Exception as e:
        logger.error(f"[SpaceTap] Whisper transcription failed for {space_id}: {e}")
        return None

    total_words = sum(len(s["text"].split()) for s in segments)
    if not segments or total_words < 30:
        logger.info(f"[SpaceTap] Insufficient speech in {space_id} ({total_words} words)")
        return None


    # ── Relevance gate: reject if transcript has zero Bitcoin signal ───────
    full_transcript = " ".join(s["text"] for s in segments).lower()
    RELEVANCE_REQUIRED = {"bitcoin", "btc", "saylor", "crypto", "satoshi",
                          "lightning", "halving", "mining", "hashrate", "etf",
                          "blockchain", "defi", "nft", "wallet", "hodl",
                          "inflation", "fed", "monetary", "fiat", "financial"}
    if not any(kw in full_transcript for kw in RELEVANCE_REQUIRED):
        logger.info(f"[SpaceTap] REJECTED {space_id} — no financial/crypto relevance in transcript")
        return None
    logger.info(f"[SpaceTap] Captured 45s, transcribed {total_words} words, extracting clips")

    # ── Step D: Score segments, find best 15s windows ──────────────────────
    scored_windows = []
    total_duration = segments[-1]["end"] if segments else 0

    t = 0.0
    while t + 15.0 <= total_duration:
        window_end = t + 15.0
        window_segs = [s for s in segments if s["end"] > t and s["start"] < window_end]
        window_text = " ".join(s["text"] for s in window_segs)
        words = window_text.lower().split()

        if len(words) < 8:
            t += 3.0
            continue

        score = 0.0
        word_set = set(words)
        for kw in HIGH_SIGNAL:
            if kw in window_text.lower():
                score += 3
        for kw in OPINION_MARKERS:
            if kw in word_set:
                score += 2
        for kw in DATA_MARKERS:
            if kw in word_set:
                score += 2

        # Bonus for word density (more speech = more signal)
        score += min(len(words) / 5, 10)

        scored_windows.append({
            "start_sec": round(t, 2),
            "duration": 15.0,
            "text": window_text,
            "score": round(score, 1),
        })
        t += 3.0  # 3s step for good overlap

    if not scored_windows:
        logger.info(f"[SpaceTap] No scoreable windows in {space_id}")
        return None

    # Top 2 non-overlapping windows
    scored_windows.sort(key=lambda x: x["score"], reverse=True)
    selected: list[dict] = []
    for w in scored_windows:
        if len(selected) >= 2:
            break
        overlaps = False
        for s in selected:
            if w["start_sec"] < s["start_sec"] + s["duration"] and \
               w["start_sec"] + w["duration"] > s["start_sec"]:
                overlaps = True
                break
        if not overlaps:
            selected.append(w)

    # ── Extract clip audio files ───────────────────────────────────────────
    for i, clip in enumerate(selected):
        clip_path = clip_dir / f"clip_{i}.m4a"
        try:
            subprocess.run(
                ["ffmpeg", "-y",
                 "-ss", str(clip["start_sec"]),
                 "-i", str(raw_path),
                 "-t", "15",
                 "-c:a", "aac", "-ar", "48000", "-ac", "2",
                 str(clip_path)],
                capture_output=True, timeout=30,
            )
            clip["clip_path"] = str(clip_path)
        except Exception as e:
            logger.warning(f"[SpaceTap] Clip extraction failed: {e}")
            clip["clip_path"] = ""

    logger.info(f"[SpaceTap] Extracted {len(selected)} clips, best score: {selected[0]['score']:.1f} — '{selected[0]['text'][:50]}'")

    # ── Step E: Get speaker profile ────────────────────────────────────────
    host_name = ""
    host_handle = ""
    host_profile_image = ""

    if creator_id:
        bearer = _get_bearer_token()
        if bearer:
            try:
                r = requests.get(
                    f"https://api.twitter.com/2/users/{creator_id}",
                    params={"user.fields": "name,username,profile_image_url"},
                    headers={"Authorization": f"Bearer {bearer}"},
                    timeout=10,
                )
                if r.status_code == 200:
                    user_data = r.json().get("data", {})
                    host_name = user_data.get("name", "")
                    host_handle = user_data.get("username", "")
                    profile_url = user_data.get("profile_image_url", "")
                    if profile_url:
                        # Get higher-res version
                        profile_url = profile_url.replace("_normal", "_400x400")
                        try:
                            img_resp = requests.get(profile_url, timeout=10)
                            if img_resp.status_code == 200:
                                profile_path = clip_dir / "profile.jpg"
                                profile_path.write_bytes(img_resp.content)
                                host_profile_image = str(profile_path)
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"[SpaceTap] User lookup failed for {creator_id}: {e}")

    # ── Step F: Save clips.json ────────────────────────────────────────────
    result = {
        "space_id": space_id,
        "title": title,
        "participant_count": participant_count,
        "host_name": host_name or "Unknown",
        "host_handle": host_handle or "unknown",
        "host_profile_image": host_profile_image,
        "source": "live_intercept",
        "intercepted_at": datetime.now(timezone.utc).isoformat(),
        "clips": selected,
    }
    clips_path.write_text(json.dumps(result, indent=2))

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3 — get_best_space_clips() — entry point for daily_run.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_best_space_clips(max_clips: int = 4) -> Optional[dict]:
    """Top-level function called by daily_run.py.

    Discovers live Bitcoin spaces, intercepts top 3, extracts best clips.
    Total time budget: ~3 minutes.

    Returns {clips: [...], spaces_count: N} or None.
    """
    try:
        return _get_best_space_clips_inner(max_clips)
    except Exception as e:
        logger.error(f"[SpaceTap] get_best_space_clips failed: {e}")
        return None


def _get_best_space_clips_inner(max_clips: int = 4) -> Optional[dict]:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    # Step 1: Find live spaces
    spaces = find_live_bitcoin_spaces()
    if not spaces:
        logger.info("[SpaceTap] No live Bitcoin spaces found")
        return None

    logger.info(f"[SpaceTap] Found {len(spaces)} live Bitcoin spaces")

    # Step 2: Intercept top 3 spaces
    all_clips: list[dict] = []
    spaces_intercepted = 0
    budget_start = time.time()

    for space in spaces[:3]:
        # Time budget: 3 minutes total
        elapsed = time.time() - budget_start
        if elapsed > 180:
            logger.info(f"[SpaceTap] Time budget exceeded ({elapsed:.0f}s), stopping")
            break

        space_id = space["space_id"]
        title = space.get("title", "")
        pc = space.get("participant_count", 0)
        creator_id = space.get("creator_id", "")

        result = intercept_space(space_id, title, pc, creator_id)
        if result and result.get("clips"):
            spaces_intercepted += 1
            for clip in result["clips"]:
                # Enrich clip with space metadata
                clip["space_id"] = space_id
                clip["space_title"] = title
                clip["host_name"] = result.get("host_name", "Unknown")
                clip["host_handle"] = result.get("host_handle", "unknown")
                clip["host_profile_image"] = result.get("host_profile_image", "")
                clip["participant_count"] = pc
                clip["source"] = "live_intercept"
                all_clips.append(clip)

    if not all_clips:
        logger.info("[SpaceTap] No clips extracted from any space")
        return None

    # Step 3: Sort by score, take best
    all_clips.sort(key=lambda x: x.get("score", 0), reverse=True)
    best = all_clips[:max_clips]

    total_from = len(all_clips)
    logger.info(f"[SpaceTap] Total: {total_from} clips from {spaces_intercepted} spaces, returning top {len(best)}")
    for c in best:
        logger.info(f"[SpaceTap]   score={c['score']:.1f} | {c['text'][:80]}")

    return {
        "clips": best,
        "spaces_count": spaces_intercepted,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    print("=== SpaceTap: Real-time X Spaces Interceptor ===\n")

    spaces = find_live_bitcoin_spaces()
    if spaces:
        print(f"Found {len(spaces)} live Bitcoin spaces:")
        for s in spaces:
            print(f"  [{s['state']}] '{s['title']}' — {s.get('participant_count', 0)} listeners (score={s.get('score', 0):.0f})")
    else:
        print("No live Bitcoin spaces found right now.")
        exit(0)

    print("\nIntercepting top spaces...")
    result = get_best_space_clips(max_clips=2)
    if result:
        print(f"\nSUCCESS: {len(result['clips'])} clips from {result['spaces_count']} spaces")
        for c in result["clips"]:
            print(f"  score={c['score']:.1f} | {c['text'][:80]}")
    else:
        print("\nNo clips this run (spaces may have ended or had no speech)")


# Compatibility shim
from dataclasses import dataclass

@dataclass
class SpaceInfo:
    space_id: str
    title: str = ""
    host: str = ""
    url: str = ""
    state: str = "ended"
    date: str = ""
    detected_via: str = "search"
    participant_count: int = 0

    def to_dict(self):
        return {"space_id":self.space_id,"title":self.title,"host":self.host,"url":self.url,"state":self.state,"started_at":self.date,"participant_count":self.participant_count}


class XSpacesScraper:
    def __init__(self): self.db=None; self._done=set()

    def find_spaces(self,skip_processed=True):
        raw=find_live_bitcoin_spaces()
        out=[]
        for s in raw:
            sid=s.get("space_id","")
            if skip_processed and sid in self._done: continue
            out.append(SpaceInfo(space_id=sid,title=s.get("title",""),host=s.get("host",s.get("creator_id","")),url=s.get("url",f"https://twitter.com/i/spaces/{sid}"),state=s.get("state","ended"),date=s.get("started_at",""),detected_via=s.get("detected_via","search"),participant_count=s.get("participant_count",0)))
        return out

    def mark_processed(self,sid):
        self._done.add(sid)
        if self.db:
            try:
                from datetime import datetime as _dt
                self.db.upsert(sid,published_at=_dt.utcnow().isoformat())
            except Exception as _e: logger.warning(f"mark_processed: {_e}")
