#!/usr/bin/env python3
"""
Trend Scout — Grok Intelligence Layer
=======================================
Uses Grok/X API to discover Bitcoin mentions from influential mainstream figures.
Runs BEFORE channel scanning to discover what's happening today that we might miss.

Returns discoveries that can be searched on YouTube for actual video clips.
"""
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("TrendScout")

GROK_API_KEY = None  # resolved at runtime
GROK_URL = "https://api.x.ai/v1/chat/completions"

SCOUT_PROMPT = """You are a Bitcoin media intelligence scout. Your job is to identify:

1. Any MAINSTREAM public figure (politician, celebrity, billionaire, tech CEO, athlete) who mentioned Bitcoin, cryptocurrency, digital currency, or related topics in the last 24 hours
2. Any viral moment, debate, or controversy involving Bitcoin today
3. Any government/regulatory announcement about crypto today
4. Any major podcast episode (Joe Rogan, Lex Fridman, All-In, PBD, Tucker) that touched Bitcoin

For each discovery, provide:
- WHO said it
- WHAT they said (brief quote or summary)
- WHERE (podcast name, TV show, tweet, press conference)
- YouTube/video URL if available (search your knowledge for the most likely link)
- IMPACT SCORE (1-10, how important this is for Bitcoin community)

Today's date: {date}

Return ONLY valid JSON:
{{
  "discoveries": [
    {{
      "who": "Person name",
      "what": "Brief summary of what they said",
      "where": "Source (podcast, show, tweet)",
      "url": "YouTube or video URL if known",
      "impact_score": 8,
      "search_query": "YouTube search query to find this content"
    }}
  ],
  "top_story": "One sentence summary of the biggest Bitcoin story today"
}}

If nothing notable happened, return empty discoveries array. Don't fabricate — only report real events."""


def _get_api_key() -> Optional[str]:
    """Resolve Grok API key from environment."""
    return os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")


def scout_trends(date_str: str = None) -> dict:
    """Run Grok trend scout to discover Bitcoin mentions from mainstream figures.

    Returns dict with 'discoveries' list and 'top_story' string.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.info("  [scout] No Grok API key, skipping trend scout")
        return {"discoveries": [], "top_story": ""}

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    prompt = SCOUT_PROMPT.format(date=date_str)

    try:
        import requests
        resp = requests.post(
            GROK_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=30
        )

        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"]
            # Clean and parse JSON
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "", 1).strip()
            result = json.loads(text)
            n_disc = len(result.get("discoveries", []))
            logger.info(f"  [scout] Grok found {n_disc} notable mentions")
            if result.get("top_story"):
                logger.info(f"  [scout] Top story: {result['top_story']}")
            return result
        else:
            logger.warning(f"  [scout] Grok API returned {resp.status_code}: {resp.text[:200]}")

    except json.JSONDecodeError as e:
        logger.warning(f"  [scout] Failed to parse Grok response as JSON: {e}")
    except Exception as e:
        logger.warning(f"  [scout] Grok trend scout failed: {e}")

    return {"discoveries": [], "top_story": ""}


def search_discovery_clips(discoveries: list) -> list:
    """For each high-impact Grok discovery, search YouTube for the actual video.

    Returns list of video metadata dicts compatible with the pipeline.
    """
    clips_found = []

    for disc in discoveries:
        if disc.get("impact_score", 0) < 6:
            continue  # Only chase high-impact stories

        query = disc.get("search_query", f"{disc.get('who', 'bitcoin')} bitcoin")
        logger.info(f"  [scout] Searching YouTube for: {query}")

        cmd = [
            "yt-dlp", f"ytsearch3:{query}",
            "--flat-playlist",
            "--print", "%(id)s|%(title)s|%(duration)s|%(upload_date)s|%(channel)s",
            "--no-warnings",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            for line in result.stdout.strip().split("\n"):
                if "|" not in line:
                    continue
                parts = line.split("|")
                if len(parts) < 4:
                    continue

                vid_id = parts[0]
                title = parts[1]
                dur_raw = parts[2]
                upload_date = parts[3]
                channel = parts[4] if len(parts) > 4 else "Unknown"

                # Parse duration
                try:
                    dur = int(float(dur_raw)) if dur_raw not in ("NA", "") else 0
                except (ValueError, TypeError):
                    dur = 0

                # Skip shorts and very long videos
                if dur < 120 or dur > 7200:
                    continue

                clips_found.append({
                    "video_id": vid_id,
                    "title": title,
                    "duration": dur,
                    "upload_date": upload_date,
                    "channel": channel,
                    "discovery": disc,
                    "source": "grok_scout",
                    "mainstream_match": True,
                })
                logger.info(f"    Found: {title[:60]} ({dur // 60}m)")

        except subprocess.TimeoutExpired:
            logger.warning(f"  [scout] YouTube search timed out for '{query}'")
        except Exception as e:
            logger.warning(f"  [scout] YouTube search failed for '{query}': {e}")

    logger.info(f"  [scout] {len(clips_found)} searchable video clips from discoveries")
    return clips_found
