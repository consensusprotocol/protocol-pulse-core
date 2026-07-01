#!/usr/bin/env python3
"""
comedy_machine.py — Bitcoin Bugle-style deadpan satirist for Protocol Pulse (6.4)

DECISION (PBX 2026-07-01, resolved — do not re-litigate):
  - Posts from the main @ProtocolPulseHQ account. No separate handle.
  - Tasteful and SPARSE: every 3-5 days, never daily. Skip rather than force.
  - Text-first. Image generation is optional phase 2, not built here.

HARD RULE: satire must read as OBVIOUSLY ABSURD, never as a believable false
claim. (The opposite failure of the killed "Congress passed the CLARITY Act"
backlog tweet.) The quality gate enforces this with a believability check:
if a reasonable reader could mistake the joke for real news, it is KILLED.

Fed by live material:
  - emerging_narratives (data/sovereign_intel.db)
  - perception_layer.json composite mood
  - x_reader top thought-leader posts (Grok x_search, cached, ~$0.018/call)
  - recent partner-channel video titles (channel_archive index)

Cadence enforcement: cron runs daily at 13:00 ET; this script self-gates.
It exits silently unless >= min_days_between_posts (3) since the last post.
The quality gate makes real spacing naturally land in the 3-5+ day band.

Config:  config/comedy_config.json   (posting_enabled flips after live proof)
State:   data/intelligence/comedy_state.json
Log:     logs/comedy_machine.log
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
CONFIG_PATH = BASE / "config" / "comedy_config.json"
STATE_PATH = BASE / "data" / "intelligence" / "comedy_state.json"
PERCEPTION_PATH = BASE / "data" / "perception_layer.json"
INTEL_DB = BASE / "data" / "sovereign_intel.db"
ARCHIVE_DIR = BASE / "video_pipeline_v3" / "data" / "channel_archive"
LOG_PATH = BASE / "logs" / "comedy_machine.log"

STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_env():
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

logging.basicConfig(
    level=logging.INFO,
    format="[comedy] %(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
logger = logging.getLogger("comedy")

DEFAULT_CONFIG = {
    "enabled": True,
    "posting_enabled": False,      # flip to True only after live proof
    "min_days_between_posts": 3,
    "quality_floor": 88,           # gate overall score; below = skip, not ship
    "candidates_per_run": 5,
    "dedup_history": 8,            # never reuse a theme from the last N posts
    "model": "claude-sonnet-4-6",
    "max_chars": 240,
}

# Aligned with tweet_machine voice laws (services/tweet_machine.py)
BANNED_PHRASES = [
    "game-changer", "paradigm shift", "bullish af", "to the moon",
    "now more than ever", "in a world where", "at the end of the day",
    "deep dive", "unpack", "leverage", "synergy", "amazing", "incredible",
    "exciting", "massive", "stay free", "stay sovereign", "no chain but",
    "blood oath", "defiant hodler",
]

# Never satirize into these lanes (identity laws + brand safety)
BANNED_TOPICS = [
    "altcoin", "ethereum", "solana", "stablecoin", "nft", "defi", "web3",
]

SATIRE_PROMPT = """You write deadpan fake-news satire for @ProtocolPulseHQ, a
Bitcoin intelligence account. Think The Onion meets a Bitcoin desk: a fake
headline or fake report delivered completely straight.

PERSONA: Theo Von absurdism, delivered with Lyn Alden's dry "already did the
homework" calm. The joke lands because the premise is insane and the delivery
is boring. No winking, no "lol", no exclamation marks.

THE ONE INVIOLABLE RULE: the satire must be OBVIOUSLY ABSURD on its face.
A reasonable stranger scrolling past must instantly know it is a joke.
NEVER write something a reader could mistake for a real news event
(no plausible bills passing, no plausible ETF/exchange/company announcements,
no plausible price events, no real person plausibly saying a thing they could
plausibly say). Impossible premises only: physics-breaking, bureaucracy taken
to insane extremes, absurd institutional behavior no institution could do.

TODAY'S REAL MATERIAL (mine it for the premise, then exaggerate past the
point of believability):

MARKET MOOD: {mood}

LIVE NARRATIVES:
{narratives}

WHAT THOUGHT LEADERS POSTED TODAY:
{posts}

RECENT PARTNER CHANNEL COVERAGE:
{channel_titles}

RECENTLY USED SATIRE THEMES (do NOT reuse any of these):
{used_themes}

FORM: the strongest shape is a single deadpan fake headline. One absurd beat,
no setup, no second sentence unless it is a killer tag. Target under 160
characters. These are the SHAPE to match (do not reuse their content):
- "Fed unveils new inflation target of whatever happens"
- "Man who called the top in 2013 schedules 14th consecutive farewell tour"
- "Treasury to back dollar with full faith, credit, and a strongly worded memo"
- "Central bank hires 4,000th economist to explain why the first 3,999 were wrong"
Notice: zero filler, the absurdity IS the punchline, reads in one breath.

FORMAT RULES (hard):
- Under {max_chars} characters, but under 160 is stronger
- No emoji, no hashtags, no exclamation marks
- No em dashes, no double dashes, no dashes as pauses
- No trailing period
- Never use: {banned}
- Bitcoin lens only: fiat absurdity, central banks, treasury companies,
  mining, self-custody culture, Bitcoin Twitter itself. Never altcoins,
  stablecoins, ETH, or broad crypto
- Punch up (institutions, central banks, grifters), never at protected
  groups, never at named private individuals

Write {count} DIFFERENT satire candidates, each mining a different premise
from the material above. Respond with a JSON array only, no markdown:
[{{"text": "<the satire>", "theme": "<3-6 word theme label>",
   "premise": "<one line: why this is obviously impossible>"}}, ...]"""

GATE_PROMPT = """You are the quality gate for Bitcoin satire posted by a
professional intelligence brand (@ProtocolPulseHQ) that is courting Bitcoin
sponsors. A weak or risky joke gets KILLED, not softened.

CANDIDATE:
"{text}"
Theme: {theme}
Claimed absurdity: {premise}

Score it honestly and strictly:

1. believable_as_real_news: could ANY reasonable reader scrolling fast
   mistake this for a real event, real quote, or real announcement?
   This is the kill criterion. When in doubt, answer true (= kill).
2. absurdity_clear: is the impossibility obvious within the first read?
3. funny (0-100): deadpan-absurdist funny, not pun-funny, not cringe.
4. on_voice (0-100): dry, terse, sounds like a smart person's phone, not AI.
   Penalize hedging, corporate words, emoji-adjacent energy, tribal maxi
   copy, and anything that reads like a caption.
5. brand_safe: no protected-group targets, no named private individuals,
   no altcoin/stablecoin/ETH subject matter, nothing a professional Bitcoin
   sponsor would flinch at beyond healthy edginess.
6. overall (0-100): would this make a sharp Bitcoin audience exhale through
   their nose and respect the account more? Reserve 88+ for genuinely sharp.

Respond with JSON only, no markdown:
{{"believable_as_real_news": false, "absurdity_clear": true, "funny": 0,
  "on_voice": 0, "brand_safe": true, "overall": 0,
  "verdict": "ship" or "kill", "reason": "<one line>"}}"""


# ── config / state ────────────────────────────────────────────────────────────

def _config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def _state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {"last_posted_at": None, "history": [], "skips": []}


def _save_state(st):
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=2))
    tmp.replace(STATE_PATH)


def days_since_last_post(st, now=None):
    if not st.get("last_posted_at"):
        return 10_000.0
    now = now or datetime.now(timezone.utc)
    last = datetime.fromisoformat(st["last_posted_at"])
    return (now - last).total_seconds() / 86400.0


# ── material gathering ────────────────────────────────────────────────────────

def _mood():
    try:
        p = json.load(open(PERCEPTION_PATH))
        c = p.get("composite", {})
        return f"{c.get('label', 'Neutral')} (score {c.get('perception_score', '?')}/100)"
    except Exception:
        return "Neutral"


def _narratives(limit=10):
    try:
        con = sqlite3.connect(str(INTEL_DB))
        cur = con.cursor()
        cur.execute(
            "SELECT theme FROM emerging_narratives ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = [r[0] for r in cur.fetchall()]
        con.close()
        return "\n".join(f"- {t}" for t in rows) or "- (none)"
    except Exception as e:
        logger.warning("narratives unavailable: %s", e)
        return "- (none)"


def _leader_posts(limit=6):
    try:
        import sys as _s
        _s.path.insert(0, str(BASE))
        try:
            from services import x_reader
        except ImportError:
            import x_reader
        try:
            from services.tweet_machine import THOUGHT_LEADERS
        except Exception:
            THOUGHT_LEADERS = ["PrestonPysh", "LynAldenContact", "Breedlove22",
                               "MartyBent", "TFTC21", "American_HODL",
                               "daborado", "nic__carter"]
        posts = x_reader.get_top_posts(THOUGHT_LEADERS, hours=24, limit=limit) or []
        lines = []
        for p in posts[:limit]:
            lines.append(f"- @{p.get('author', '?')}: {str(p.get('text', ''))[:160]}")
        return "\n".join(lines) or "- (none)"
    except Exception as e:
        logger.warning("x_reader unavailable: %s", e)
        return "- (none)"


def _channel_titles(limit=8):
    try:
        candidates = sorted(
            ARCHIVE_DIR.glob("known_videos*.json"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        if not candidates:
            return "- (none)"
        idx = json.load(open(candidates[0]))
        items = idx if isinstance(idx, list) else list(idx.values())
        def up(v):
            return str(v.get("upload_date", "")) if isinstance(v, dict) else ""
        items = [v for v in items if isinstance(v, dict)]
        items.sort(key=up, reverse=True)
        lines = []
        for v in items[:limit]:
            lines.append(f"- {v.get('channel', '?')}: {str(v.get('title', ''))[:110]}")
        return "\n".join(lines) or "- (none)"
    except Exception as e:
        logger.warning("channel archive unavailable: %s", e)
        return "- (none)"


# ── LLM cascade (Anthropic Sonnet -> Gemini -> Grok) ─────────────────────────

def _post_json(url, body, headers, timeout=60):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _llm(prompt, model):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            r = _post_json(
                "https://api.anthropic.com/v1/messages",
                {"model": model, "max_tokens": 1200,
                 "messages": [{"role": "user", "content": prompt}]},
                {"x-api-key": key, "anthropic-version": "2023-06-01"},
            )
            return "".join(b.get("text", "") for b in r.get("content", []))
        except Exception as e:
            logger.warning("anthropic failed: %s", e)
    gkey = os.environ.get("GEMINI_API_KEY")
    if gkey:
        try:
            r = _post_json(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.5-flash:generateContent?key={gkey}",
                {"contents": [{"parts": [{"text": prompt}]}]},
                {},
            )
            return r["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning("gemini failed: %s", e)
    xkey = os.environ.get("XAI_API_KEY")
    if xkey:
        try:
            r = _post_json(
                "https://api.x.ai/v1/chat/completions",
                {"model": "grok-3",
                 "messages": [{"role": "user", "content": prompt}]},
                {"Authorization": f"Bearer {xkey}"},
            )
            return r["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("grok failed: %s", e)
    raise RuntimeError("all LLM backends failed")


def _extract_json(text):
    """Pull the first complete JSON object/array from an LLM response."""
    text = re.sub(r"```(?:json)?", "", text).strip().strip("`")
    # Try openers in order of FIRST APPEARANCE in the text, so an object
    # containing an inner array is parsed as the object, not the array.
    # (Same root cause as the x_reader parse_json_block bug, 2026-07-01.)
    pairs = [(op, cl) for op, cl in (("{", "}"), ("[", "]")) if text.find(op) != -1]
    pairs.sort(key=lambda p: text.find(p[0]))
    for opener, closer in pairs:
        start = text.find(opener)
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
    raise ValueError("no valid JSON in response")


# ── filters / gate ────────────────────────────────────────────────────────────

def hard_filter(text, max_chars=240):
    """Deterministic voice-law filter. Returns (ok, reason)."""
    t = text.strip()
    if not t or len(t) > max_chars:
        return False, f"length {len(t)} > {max_chars}"
    low = t.lower()
    for b in BANNED_PHRASES:
        if b in low:
            return False, f"banned phrase: {b}"
    for b in BANNED_TOPICS:
        if re.search(r"\b" + re.escape(b), low):
            return False, f"banned topic: {b}"
    if re.search(r"[!#\u2014\u2013]|--|\.\.\.", t):
        return False, "punctuation law (dash/exclaim/hashtag/ellipsis)"
    if re.search(r"[\U0001F000-\U0001FAFF\u2600-\u27BF]", t):
        return False, "emoji"
    if t.endswith("."):
        return False, "trailing period"
    return True, "ok"


def gate(candidate, cfg):
    """LLM quality gate. Returns (ship, result_dict)."""
    prompt = GATE_PROMPT.format(
        text=candidate["text"],
        theme=candidate.get("theme", "?"),
        premise=candidate.get("premise", "?"),
    )
    result = _extract_json(_llm(prompt, cfg["model"]))
    ship = (
        result.get("verdict") == "ship"
        and not result.get("believable_as_real_news", True)
        and result.get("absurdity_clear", False)
        and result.get("brand_safe", False)
        and int(result.get("overall", 0)) >= cfg["quality_floor"]
    )
    return ship, result


# ── main run ──────────────────────────────────────────────────────────────────

def run(dry_run=False):
    cfg = _config()
    if not cfg.get("enabled"):
        logger.info("disabled via config; exit")
        return {"status": "disabled"}

    st = _state()
    gap = days_since_last_post(st)
    if gap < cfg["min_days_between_posts"]:
        logger.info("cadence gate: %.1f days since last post (< %d); exit",
                    gap, cfg["min_days_between_posts"])
        return {"status": "cadence_gated", "days": round(gap, 1)}

    used = [h.get("theme", "") for h in st.get("history", [])][-cfg["dedup_history"]:]
    material = {
        "mood": _mood(),
        "narratives": _narratives(),
        "posts": _leader_posts(),
        "channel_titles": _channel_titles(),
        "used_themes": "\n".join(f"- {u}" for u in used) or "- (none yet)",
        "banned": ", ".join(BANNED_PHRASES[:12]),
        "max_chars": cfg["max_chars"],
        "count": cfg["candidates_per_run"],
    }
    logger.info("generating %d candidates (mood: %s)", cfg["candidates_per_run"],
                material["mood"])
    raw = _llm(SATIRE_PROMPT.format(**material), cfg["model"])
    candidates = _extract_json(raw)
    if not isinstance(candidates, list):
        candidates = [candidates]

    survivors = []
    for c in candidates:
        text = str(c.get("text", "")).strip()
        # Normalize: a single trailing period is a fixable style slip, not a
        # kill offense. Strip it (voice law: no trailing period), keep the
        # hard filter as backstop for anything weirder.
        if text.endswith(".") and not text.endswith(".."):
            text = text[:-1].rstrip()
            c["text"] = text
        ok, why = hard_filter(text, cfg["max_chars"])
        if not ok:
            logger.info("hard filter kill (%s): %s", why, text[:70])
            continue
        theme = str(c.get("theme", "")).strip().lower()
        if any(theme and theme == u.lower() for u in used):
            logger.info("dedup kill (theme reused): %s", theme)
            continue
        survivors.append(c)

    best, best_result = None, None
    for c in survivors:
        try:
            ship, result = gate(c, cfg)
        except Exception as e:
            logger.warning("gate error, treating as kill: %s", e)
            continue
        logger.info("gate %s (%s): overall=%s funny=%s believable=%s | %s",
                    result.get("verdict"), c.get("theme"),
                    result.get("overall"), result.get("funny"),
                    result.get("believable_as_real_news"),
                    str(c.get("text", ""))[:70])
        if ship and (best is None or
                     int(result.get("overall", 0)) > int(best_result.get("overall", 0))):
            best, best_result = c, result

    now = datetime.now(timezone.utc).isoformat()
    if best is None:
        st.setdefault("skips", []).append({"at": now, "reason": "no candidate cleared gate",
                                           "candidates": len(candidates)})
        st["skips"] = st["skips"][-20:]
        _save_state(st)
        logger.info("SKIP: nothing cleared the %d floor. Skipping beats forcing.",
                    cfg["quality_floor"])
        return {"status": "skipped_quality", "candidates": len(candidates)}

    text = best["text"].strip()
    logger.info("WINNER (overall=%s): %s", best_result.get("overall"), text)

    if dry_run or not cfg.get("posting_enabled"):
        logger.info("dry_run/posting_disabled: not posting")
        return {"status": "dry_run", "text": text, "gate": best_result}

    import sys as _s
    _s.path.insert(0, str(BASE))
    try:
        from services.buffer_poster import post_to_buffer
    except ImportError:
        from buffer_poster import post_to_buffer
    resp = post_to_buffer(text, channel="x", mode="shareNow")
    if not (resp and (resp.get("success") or resp.get("post_id"))):
        logger.error("buffer post failed: %s", resp)
        return {"status": "post_failed", "text": text, "resp": resp}

    st["last_posted_at"] = now
    st.setdefault("history", []).append({
        "at": now, "text": text, "theme": best.get("theme", ""),
        "overall": best_result.get("overall"),
        "hash": hashlib.sha256(text.encode()).hexdigest()[:12],
        "buffer_post_id": resp.get("post_id"),
    })
    st["history"] = st["history"][-50:]
    _save_state(st)
    logger.info("POSTED via Buffer: post_id=%s", resp.get("post_id"))
    return {"status": "posted", "text": text, "post_id": resp.get("post_id"),
            "gate": best_result}


if __name__ == "__main__":
    import sys
    print(json.dumps(run(dry_run="--dry-run" in sys.argv), indent=2))
