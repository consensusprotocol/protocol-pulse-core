#!/usr/bin/env python3
"""
sentiment_brief_service.py — KOL Sentiment Brief for Protocol Pulse
Aggregates top Bitcoin KOL tweets, runs LLM analysis, produces a structured
sentiment brief with TTS-ready script.

Cron: 7am, 1pm, 7pm ET (after nitter scraper runs)
Output: data/intelligence/kol_sentiment_brief.json
"""

import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
RAW_TWEETS_PATH = BASE / "data" / "tweet_study" / "raw_tweets.json"
OUTPUT_PATH = BASE / "data" / "intelligence" / "kol_sentiment_brief.json"
LOG_PATH = BASE / "logs" / "sentiment_brief.log"

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    format="[sentiment_brief] %(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("sentiment_brief")

# Top Bitcoin KOL handles (lowercase for matching)
KOL_HANDLES = {
    "odell", "saylor", "martybent", "prestonpysh", "nataliebrunell",
    "stephanlivera", "saifedean", "lukedashjr", "petermccormack",
    "realvision", "lynaldencontact", "gladstein", "documentingbtc",
    "daborasat", "bitcoinmagazine", "tftc21", "american_hodl",
    "breedlove22", "nic__carter", "daborado",
}

ANALYSIS_PROMPT = """{persona}

You are the intelligence analyst for Protocol Pulse. Analyze these tweets from top Bitcoin voices and produce a structured sentiment brief.

TOP KOL TWEETS (sorted by engagement):
{tweets_block}

Produce a JSON object with EXACTLY this structure (respond with valid JSON only, no markdown, no preamble):
{{
  "sentiment": "<bullish|bearish|neutral|mixed>",
  "dominant_narrative": "<1 sentence describing what KOLs are collectively focused on>",
  "top_signal": "<the single most important insight with attribution to the KOL who said it>",
  "contrarian_view": "<any notable disagreement or minority position among these voices, or 'None detected' if consensus is strong>",
  "tts_script": "<under 90 words, written for voice narration by a cypherpunk intelligence analyst. No emoji, no exclamation marks. Conversational but data-dense. Summarize the KOL consensus and the key signal.>"
}}"""

PBX_PERSONA = """PERSONA: You are a ghost analyst inside Protocol Pulse. Austrian economics lens.
Dry wit. Zero fluff. You observe the decay of one monetary system and the emergence of another.
FORBIDDEN: corporate jargon, breathless hype, cliches, emoji, exclamation marks."""


class SentimentBriefService:

    def scrape_kol_tweets(self, hours_back: int = 12) -> list:
        """Load latest tweets from raw_tweets.json, filter to KOL handles,
        sort by engagement, return top 10."""
        if not RAW_TWEETS_PATH.exists():
            logger.warning("raw_tweets.json not found")
            return []

        try:
            with open(RAW_TWEETS_PATH) as f:
                raw = f.read()
            try:
                all_tweets = json.loads(raw)
            except json.JSONDecodeError:
                decoder = json.JSONDecoder()
                all_tweets, _ = decoder.raw_decode(raw)
                logger.warning(f"raw_tweets.json had extra data, recovered {len(all_tweets)} tweets")
        except Exception as e:
            logger.error(f"Failed to load raw_tweets.json: {e}")
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        kol_tweets = []

        for t in all_tweets:
            handle = (t.get("handle") or "").lower()
            if handle not in KOL_HANDLES:
                continue
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

            kol_tweets.append({
                "handle": t.get("handle", ""),
                "text": t.get("text", ""),
                "engagement_score": engagement,
                "likes": likes,
                "retweets": retweets,
                "created_at": t.get("created_at", ""),
            })

        kol_tweets.sort(key=lambda x: x["engagement_score"], reverse=True)
        top = kol_tweets[:10]
        logger.info(f"Found {len(kol_tweets)} KOL tweets, returning top {len(top)}")
        return top

    def _call_llm(self, prompt: str) -> str:
        """LLM fallback chain: Anthropic Haiku -> Gemini -> Grok. Returns raw text."""
        # 1. Anthropic Haiku
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key:
            try:
                payload = {
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 800,
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
                    logger.info("Brief generated via Anthropic Haiku")
                    return content
            except Exception as e:
                logger.warning(f"Anthropic Haiku failed: {e}")

        # 2. Gemini 2.5 Flash
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if gemini_key:
            try:
                gpayload = json.dumps({
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.4},
                }).encode()
                req = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                    data=gpayload,
                    headers={"Content-Type": "application/json"},
                )
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read())
                parts = data["candidates"][0]["content"]["parts"]
                content = ""
                for p in reversed(parts):
                    if not p.get("thought") and p.get("text"):
                        content = p["text"].strip()
                        break
                if content:
                    logger.info("Brief generated via Gemini fallback")
                    return content
            except Exception as e:
                logger.warning(f"Gemini fallback failed: {e}")

        # 3. Grok/xAI
        xai_key = os.environ.get("XAI_API_KEY", "")
        if xai_key:
            try:
                gpayload = json.dumps({
                    "model": "grok-3-mini-fast",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.4,
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
                    logger.info("Brief generated via Grok/xAI fallback")
                    return content
            except Exception as e:
                logger.warning(f"Grok fallback failed: {e}")

        return ""

    def _extract_json(self, raw: str) -> dict:
        """Robustly extract JSON from LLM response."""
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        if raw.startswith("```"):
            inner = raw.split("```", 2)[1]
            if inner.startswith("json"):
                inner = inner[4:]
            inner = inner.rsplit("```", 1)[0].strip()
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                pass
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.error(f"No valid JSON in LLM response: {raw[:200]}")
        return {}

    def build_sentiment_brief(self) -> dict:
        """Scrape KOL tweets, run LLM analysis, return structured brief."""
        tweets = self.scrape_kol_tweets()
        if not tweets:
            logger.warning("No KOL tweets found, returning empty brief")
            return {
                "sentiment": "neutral",
                "dominant_narrative": "No KOL signal available",
                "top_signal": "Insufficient data",
                "contrarian_view": "N/A",
                "tts_script": "No KOL signal detected in the last twelve hours. Standing by for the next cycle.",
                "voices_sampled": 0,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by": "fallback",
            }

        tweets_block = ""
        for i, t in enumerate(tweets, 1):
            tweets_block += (
                f"{i}. @{t['handle']} (engagement: {t['engagement_score']}): "
                f"{t['text'][:280]}\n"
            )

        prompt = ANALYSIS_PROMPT.format(
            persona=PBX_PERSONA,
            tweets_block=tweets_block,
        )

        content = self._call_llm(prompt)
        if not content:
            logger.error("All LLM providers failed for sentiment brief")
            return {
                "sentiment": "neutral",
                "dominant_narrative": "LLM analysis unavailable",
                "top_signal": "Service degraded",
                "contrarian_view": "N/A",
                "tts_script": "Intelligence brief generation failed. All LLM providers down. Manual review required.",
                "voices_sampled": len(tweets),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by": "error",
            }

        brief = self._extract_json(content)
        if not brief:
            logger.error("Failed to parse LLM response as JSON")
            return {}

        # Validate TTS script word count
        tts = brief.get("tts_script", "")
        word_count = len(tts.split())
        if word_count > 100:
            logger.warning(f"TTS script too long ({word_count} words), will truncate")
            words = tts.split()[:90]
            brief["tts_script"] = " ".join(words)

        # Add metadata
        unique_handles = set(t["handle"].lower() for t in tweets)
        brief["voices_sampled"] = len(unique_handles)
        brief["generated_at"] = datetime.now(timezone.utc).isoformat()
        brief["generated_by"] = "sentiment_brief_service"
        brief["kol_handles_seen"] = sorted(unique_handles)

        # Save to file
        tmp = OUTPUT_PATH.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(brief, f, indent=2, ensure_ascii=False)
        tmp.replace(OUTPUT_PATH)
        logger.info(f"Brief saved to {OUTPUT_PATH}")
        logger.info(f"Sentiment: {brief.get('sentiment')} | Voices: {brief.get('voices_sampled')}")

        return brief

    def get_cached_brief(self) -> dict:
        """Load cached brief. If older than 6 hours, regenerate."""
        if OUTPUT_PATH.exists():
            try:
                age_hours = (
                    datetime.now().timestamp() - OUTPUT_PATH.stat().st_mtime
                ) / 3600
                if age_hours < 6:
                    with open(OUTPUT_PATH) as f:
                        brief = json.load(f)
                    logger.info(f"Returning cached brief ({age_hours:.1f}h old)")
                    return brief
                else:
                    logger.info(f"Cached brief is {age_hours:.1f}h old, regenerating")
            except Exception as e:
                logger.warning(f"Failed to load cached brief: {e}")

        return self.build_sentiment_brief()


def main():
    logger.info("=" * 60)
    logger.info("KOL Sentiment Brief generating")
    logger.info("=" * 60)
    svc = SentimentBriefService()
    brief = svc.build_sentiment_brief()
    if brief:
        logger.info(f"Sentiment: {brief.get('sentiment')}")
        logger.info(f"Narrative: {brief.get('dominant_narrative')}")
        logger.info(f"TTS words: {len(brief.get('tts_script', '').split())}")
    else:
        logger.error("Brief generation failed")


if __name__ == "__main__":
    main()
