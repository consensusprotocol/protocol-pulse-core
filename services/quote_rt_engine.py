#!/usr/bin/env python3
"""
quote_rt_engine.py — Quote-RT Amplification Engine for Protocol Pulse
The Kirill strategy: systematically quote-retweet top-performing tweets
with fresh hooks spaced over 3-5 days.

Cron:
  - identify_anchors + generate_quote_hooks: daily at 10am ET
  - post_next_scheduled: every 3 hours via social_daemon
Output: data/intelligence/quote_rt_schedule.json
"""

import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
POSTED_TWEETS_PATH = BASE / "data" / "posted_tweets.json"
RAW_TWEETS_PATH = BASE / "data" / "tweet_study" / "raw_tweets.json"
SCHEDULE_PATH = BASE / "data" / "intelligence" / "quote_rt_schedule.json"
LOG_PATH = BASE / "logs" / "quote_rt_engine.log"

SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_env():
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

# NVIDIA NIM free tier model
NIM_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"

logging.basicConfig(
    level=logging.INFO,
    format="[quote_rt] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("quote_rt")

# Banned phrases for hooks (aligned with tweet_machine voice laws)
BANNED_PHRASES = [
    "game-changer", "paradigm shift", "bullish af", "to the moon",
    "now more than ever", "in a world where", "at the end of the day",
    "deep dive", "unpack", "leverage", "synergy",
    "amazing", "incredible", "exciting", "massive",
]

HOOK_GENERATION_PROMPT = """You are Protocol Pulse's tweet writer. Generate {count} different quote-tweet hooks for this anchor tweet.

ANCHOR TWEET by @{handle}:
"{text}"

Each hook is a standalone 1-2 line comment that adds insight, reframes the data, or draws a cypherpunk conclusion. Each should hit a different emotional angle:
1. Conviction (firm stance, no hedging)
2. Irony (dry wit about the situation)
3. Data insight (specific implication of the data)
4. Philosophical (deeper meaning about money/sovereignty)
5. Contrarian (the angle everyone missed)

RULES:
- Under 150 characters each
- No emoji. No exclamation marks. No hashtags
- No em dashes or double dashes
- Never use: {banned}
- Protocol Pulse voice: dry, understated, cypherpunk

Respond with a JSON array of strings only, no markdown:
["hook 1", "hook 2", ...]"""


QRT_CONFIG_PATH = BASE / "config" / "quote_rt_config.json"

QUOTED_LEDGER_PATH = BASE / "data" / "intelligence" / "quoted_anchors.json"


def _quoted_ledger() -> set:
    """Permanent set of anchor_ids ever quoted by quote_rt OR comment_radar.
    2026-07-06 (PBX): never quote the same post twice, even across restarts."""
    try:
        import json as _j
        d = _j.load(open(QUOTED_LEDGER_PATH))
        return set(str(x) for x in d.get("quoted_anchor_ids", []))
    except Exception:
        return set()


def _mark_quoted(anchor_id: str):
    import json as _j
    ids = _quoted_ledger()
    ids.add(str(anchor_id))
    QUOTED_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    _j.dump({"quoted_anchor_ids": sorted(ids),
             "note": "Anchors ever quote-tweeted by quote_rt OR comment_radar. Never re-quote."},
            open(QUOTED_LEDGER_PATH, "w"), indent=2)


def _qrt_config():
    cfg = {"posting_enabled": False, "max_posts_per_day": 2,
           "min_anchor_engagement": 500, "hooks_per_anchor": 3}
    try:
        with open(QRT_CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


class QuoteRTEngine:

    def _get_xreader_anchors(self, hours_back: int = 24) -> list:
        """2026-07 (Fable5 6.3): primary anchor discovery via x_reader
        (Grok x_search). The raw_tweets.json KOL scrape is stale and the
        X API is 402 for reads."""
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
                THOUGHT_LEADERS = ["PrestonPysh", "LynAldenContact",
                                   "Breedlove22", "MartyBent", "TFTC21",
                                   "American_HODL", "daborado", "nic__carter"]
            min_eng = _qrt_config()["min_anchor_engagement"]

            def _collect(handles):
                posts = x_reader.get_top_posts(handles,
                                               hours=hours_back, limit=8)
                res = []
                for p in posts:
                    if p.get("engagement", 0) < min_eng:
                        continue
                    res.append({
                        "tweet_id": p["post_id"],
                        "text": p["text"],
                        "engagement": p["engagement"],
                        "source": "x_search",
                        "handle": p["author"],
                        "posted_at": p.get("fetched_at", ""),
                    })
                return res

            out = _collect(THOUGHT_LEADERS)
            if len(out) < 2:
                # quiet day on the core list — widen to curated quality KOLs
                WIDE_KOLS = ["saylor", "BitcoinMagazine", "ODELL",
                             "DocumentingBTC", "gladstein", "River",
                             "CaitlinLong_", "jack"]
                logger.info("Core list quiet; widening to curated KOLs")
                out += _collect(WIDE_KOLS)
            logger.info(f"x_reader anchors: {len(out)} above {min_eng} engagement")
            return out
        except Exception as e:
            logger.warning(f"x_reader anchor discovery failed: {e}")
            return []

    def _get_own_tweet_engagement(self, hours_back: int = 48) -> list:
        """Check Protocol Pulse posted tweets from the DB for recent high performers."""
        import sqlite3
        results = []
        ledger_db = BASE / "data" / "x_post_ledger.db"
        if not ledger_db.exists():
            return results
        try:
            conn = sqlite3.connect(str(ledger_db))
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
            rows = conn.execute(
                "SELECT id, tweet_text, posted_at FROM x_post_ledger "
                "WHERE posted_at >= ? AND allowed = 1 "
                "ORDER BY posted_at DESC LIMIT 20",
                (cutoff,)
            ).fetchall()
            conn.close()
            for row_id, text, posted_at in rows:
                if text:
                    results.append({
                        "tweet_id": str(row_id),
                        "text": text,
                        "engagement": 0,  # No live metrics without API call
                        "source": "own",
                        "handle": "ProtocolPulse",
                        "posted_at": posted_at,
                    })
        except Exception as e:
            logger.warning(f"Failed to load own tweets: {e}")
        return results

    def _get_kol_high_performers(self, hours_back: int = 48) -> list:
        """Get top KOL tweets with engagement > 500 from raw_tweets.json."""
        if not RAW_TWEETS_PATH.exists():
            return []
        try:
            with open(RAW_TWEETS_PATH) as f:
                raw = f.read()
            try:
                all_tweets = json.loads(raw)
            except json.JSONDecodeError:
                decoder = json.JSONDecoder()
                all_tweets, _ = decoder.raw_decode(raw)
        except Exception as e:
            logger.error(f"Failed to load raw_tweets.json: {e}")
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        results = []

        for t in all_tweets:
            try:
                ts_str = t.get("created_at", "").replace("Z", "+00:00")
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue
            except Exception:
                continue

            likes = t.get("likes", 0) or 0
            retweets = t.get("retweets", 0) or 0
            engagement = likes + retweets * 2

            if engagement >= 500:
                results.append({
                    "tweet_id": t.get("id", ""),
                    "text": t.get("text", ""),
                    "engagement": engagement,
                    "source": "kol",
                    "handle": t.get("handle", ""),
                    "posted_at": t.get("created_at", ""),
                })

        return results

    def identify_anchors(self, hours_back: int = 48) -> list:
        """Identify top 3 anchor candidates from own tweets + KOL tweets."""
        xr = self._get_xreader_anchors(min(hours_back, 24))
        own = self._get_own_tweet_engagement(hours_back)
        kol = self._get_kol_high_performers(hours_back)

        # Combine and sort by engagement (x_search anchors carry live metrics)
        candidates = xr + own + kol
        candidates.sort(key=lambda x: x["engagement"], reverse=True)

        # Deduplicate by tweet_id; require a REAL X status id (own-ledger
        # rows carry DB row ids like "486" which would produce broken quote
        # URLs) and nonzero engagement
        seen = set()
        unique = []
        for c in candidates:
            tid = str(c.get("tweet_id", ""))
            if not (tid.isdigit() and len(tid) >= 15):
                continue
            if c.get("engagement", 0) < 1:
                continue
            if tid not in seen:
                seen.add(tid)
                unique.append(c)

        # Check against existing schedule to avoid re-quoting
        schedule = self._load_schedule()
        scheduled_ids = {entry["anchor_id"] for entry in schedule}
        ledgered = _quoted_ledger()
        # 2026-07-06 (PBX): never re-quote an anchor already scheduled OR ever quoted
        unique = [c for c in unique
                  if c["tweet_id"] not in scheduled_ids
                  and str(c["tweet_id"]) not in ledgered]

        top = unique[:3]
        logger.info(f"Identified {len(top)} anchor candidates from {len(own)} own + {len(kol)} KOL tweets")
        return top

    def _call_llm(self, prompt: str) -> str:
        """LLM fallback chain: Anthropic -> Gemini -> Grok."""
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key:
            try:
                payload = {
                    "model": "claude-sonnet-4-6",  # voice law: Haiku flat, Sonnet on-persona
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}],
                }
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=json.dumps(payload).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "User-Agent": "ProtocolPulse/1.0",
                    },
                )
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read())
                content = data.get("content", [{}])[0].get("text", "").strip()
                if content:
                    logger.info("Hooks generated via Anthropic Sonnet")
                    return content
            except Exception as e:
                logger.warning(f"Anthropic failed: {e}")

        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if gemini_key:
            try:
                gpayload = json.dumps({
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.7},
                }).encode()
                req = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                    data=gpayload,
                    headers={"Content-Type": "application/json"},
                )
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read())
                parts = data["candidates"][0]["content"]["parts"]
                for p in reversed(parts):
                    if not p.get("thought") and p.get("text"):
                        content = p["text"].strip()
                        if content:
                            logger.info("Hooks generated via Gemini")
                            return content
            except Exception as e:
                logger.warning(f"Gemini failed: {e}")

        xai_key = os.environ.get("XAI_API_KEY", "")
        if xai_key:
            try:
                gpayload = json.dumps({
                    "model": "grok-3-mini-fast",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                    "temperature": 0.7,
                }).encode()
                req = urllib.request.Request(
                    "https://api.x.ai/v1/chat/completions",
                    data=gpayload,
                    headers={
                        "Authorization": f"Bearer {xai_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read())
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    logger.info("Hooks generated via Grok")
                    return content
            except Exception as e:
                logger.warning(f"Grok failed: {e}")

        # 4. NVIDIA NIM (free tier fallback)
        nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
        if nvidia_key:
            try:
                from openai import OpenAI as _NIMClient
                nim = _NIMClient(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key)
                nim_resp = nim.chat.completions.create(
                    model=NIM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=600,
                    temperature=0.7,
                )
                content = nim_resp.choices[0].message.content or ""
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                if content:
                    logger.info("Hooks generated via NVIDIA NIM")
                    return content
            except Exception as e:
                logger.warning(f"NVIDIA NIM failed: {e}")

        return ""

    def generate_quote_hooks(self, anchor: dict, count: int = 5) -> list:
        """Generate fresh hooks for quoting the anchor tweet."""
        if not anchor or not anchor.get("text"):
            return []

        prompt = HOOK_GENERATION_PROMPT.format(
            count=count,
            handle=anchor.get("handle", "unknown"),
            text=anchor["text"][:280],
            banned=", ".join(BANNED_PHRASES),
        )

        content = self._call_llm(prompt)
        if not content:
            logger.error("All LLM providers failed for hook generation")
            return []

        # Parse JSON array from response
        content = content.strip()
        if content.startswith("```"):
            inner = content.split("```", 2)[1]
            if inner.startswith("json"):
                inner = inner[4:]
            content = inner.rsplit("```", 1)[0].strip()

        hooks = []
        try:
            hooks = json.loads(content)
        except json.JSONDecodeError:
            # Regex fallback for complete array
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                try:
                    hooks = json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            # If still no hooks, try extracting individual quoted strings
            if not hooks:
                hooks = re.findall(r'"([^"]{10,150})"', content)
                if hooks:
                    logger.info(f"Extracted {len(hooks)} hooks via regex fallback")

        if not isinstance(hooks, list):
            hooks = []

        # Filter: enforce banned phrases, truncate to 150 chars
        valid = []
        for h in hooks:
            if not isinstance(h, str):
                continue
            h = h.strip()
            if not h:
                continue
            if any(bp.lower() in h.lower() for bp in BANNED_PHRASES):
                continue
            if "!" in h:
                h = h.replace("!", "")
            if len(h) > 150:
                h = h[:147] + "..."
            valid.append(h)

        logger.info(f"Generated {len(valid)} valid hooks (from {len(hooks)} raw)")
        return valid[:count]

    def _load_schedule(self) -> list:
        """Load existing quote-RT schedule."""
        if SCHEDULE_PATH.exists():
            try:
                with open(SCHEDULE_PATH) as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                return []
        return []

    def _save_schedule(self, schedule: list):
        """Save quote-RT schedule atomically."""
        tmp = SCHEDULE_PATH.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)
        tmp.replace(SCHEDULE_PATH)

    def schedule_quotes(self, anchor_id: str, anchor_text: str, anchor_handle: str, hooks: list):
        """Schedule hooks for posting: 1 every 8 hours over 3 days."""
        schedule = self._load_schedule()

        now = datetime.now(timezone.utc)
        hooks = hooks[:_qrt_config()["hooks_per_anchor"]]
        for i, hook in enumerate(hooks):
            post_at = now + timedelta(hours=24 * i)  # first due now, then daily
            entry = {
                "anchor_id": anchor_id,
                "anchor_text": anchor_text[:280],
                "anchor_handle": anchor_handle,
                "hook": hook,
                "scheduled_at": post_at.isoformat(),
                "status": "pending",
                "posted_at": None,
                "created_at": now.isoformat(),
            }
            schedule.append(entry)

        self._save_schedule(schedule)
        logger.info(f"Scheduled {len(hooks)} quote-RTs for anchor {anchor_id}")

    def post_next_scheduled(self) -> dict:
        """Check schedule for next pending quote-RT due now. Post if ready."""
        schedule = self._load_schedule()
        now = datetime.now(timezone.utc)

        # 2026-07 (Fable5 6.3): hard daily cap — PBX gate is 1-2 QRTs/day max
        cfg = _qrt_config()
        today = now.strftime("%Y-%m-%d")
        posted_today = sum(1 for e in schedule
                           if e.get("status") == "posted"
                           and (e.get("posted_at") or "").startswith(today))
        if posted_today >= cfg["max_posts_per_day"]:
            logger.info(f"Daily QRT cap reached ({posted_today}/{cfg['max_posts_per_day']})")
            return None

        # Find the first pending entry that is due
        for entry in schedule:
            if entry["status"] != "pending":
                continue
            _aid = str(entry.get("anchor_id", ""))
            if not (_aid.isdigit() and len(_aid) >= 15):
                entry["status"] = "invalid_anchor"
                self._save_schedule(schedule)
                logger.warning(f"Marked invalid anchor entry: {_aid}")
                continue
            scheduled_at = datetime.fromisoformat(entry["scheduled_at"])
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            if scheduled_at > now:
                continue

            # This entry is due — attempt to post
            anchor_id = entry["anchor_id"]
            hook = entry["hook"]

            # Build quote tweet text (hook + URL to anchor)
            tweet_url = f"https://x.com/i/status/{anchor_id}"
            quote_text = f"{hook}\n\n{tweet_url}"

            if len(quote_text) > 280:
                # Truncate hook to fit
                max_hook = 280 - len(tweet_url) - 3  # 2 newlines + safety
                quote_text = f"{hook[:max_hook]}\n\n{tweet_url}"

            logger.info(f"Posting quote-RT: {hook[:60]}... for anchor {anchor_id}")

            # Check if posting is enabled (config/quote_rt_config.json)
            if not cfg.get("posting_enabled"):
                logger.info(f"[DRY RUN] Would post: {quote_text[:100]}")
                entry["status"] = "dry_run"
                entry["posted_at"] = now.isoformat()
                self._save_schedule(schedule)
                return {"posted": False, "dry_run": True, "text": quote_text, "anchor_id": anchor_id}

            # Post via x_service global gate
            try:
                import sys
                sys.path.insert(0, str(BASE))
                from services.x_service import can_post_tweet
                allowed, reason = can_post_tweet(quote_text, source="quote_rt_engine", angle_category="community_response")
                if not allowed:
                    logger.warning(f"GATE BLOCKED quote-RT: {reason}")
                    return {"posted": False, "reason": reason}
            except Exception as e:
                logger.warning(f"Gate check failed (allowing): {e}")

            # 2026-07 (Fable5 6.3): post via Buffer GraphQL (X API is 402).
            # A quote-tweet is the hook plus the quoted status URL appended;
            # X renders the quote card automatically.
            try:
                import sys as _s
                _s.path.insert(0, str(BASE))
                try:
                    from services.buffer_poster import post_to_buffer
                except ImportError:
                    from buffer_poster import post_to_buffer
                result = post_to_buffer(quote_text, channel="x", mode="shareNow")
                _bid = (result or {}).get("post_id") or (result or {}).get("id")
                if result and (result.get("success") or _bid):
                    entry["status"] = "posted"
                    _mark_quoted(anchor_id)
                    entry["posted_at"] = now.isoformat()
                    entry["posted_tweet_id"] = str(_bid)
                    entry["posted_via"] = "buffer"
                    self._save_schedule(schedule)
                    logger.info(f"Posted quote-RT via Buffer: {_bid}")
                    return {"posted": True, "tweet_id": str(_bid),
                            "text": quote_text, "anchor_id": anchor_id}
                logger.error(f"Buffer post returned no id: {result}")
                entry["status"] = "post_failed"
                self._save_schedule(schedule)
                return {"posted": False, "error": "buffer_no_id"}
            except Exception as e:
                logger.error(f"Quote-RT Buffer post failed: {e}")
                entry["status"] = "post_failed"
                self._save_schedule(schedule)
                return {"posted": False, "error": str(e)}

        logger.info("No pending quote-RTs due")
        return None

    def run_daily_cycle(self):
        """Daily entry: identify anchors, generate hooks, schedule them."""
        logger.info("=" * 60)
        logger.info("Quote-RT daily cycle starting")
        logger.info("=" * 60)

        anchors = self.identify_anchors()
        if not anchors:
            logger.info("No anchor candidates found")
            return

        # Generate and schedule for top anchor only (avoid spam)
        anchor = anchors[0]
        hooks = self.generate_quote_hooks(anchor)
        if hooks:
            self.schedule_quotes(
                anchor_id=anchor["tweet_id"],
                anchor_text=anchor["text"],
                anchor_handle=anchor["handle"],
                hooks=hooks,
            )
            logger.info(f"Scheduled {len(hooks)} hooks for @{anchor['handle']}")
        else:
            logger.warning("No hooks generated for top anchor")


def main():
    engine = QuoteRTEngine()
    engine.run_daily_cycle()


if __name__ == "__main__":
    main()
