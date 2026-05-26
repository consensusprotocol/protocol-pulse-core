"""
Grok Triage — Stage 1
======================
Fast-scan content filter using xAI Grok API.
Reads all transcripts + tweets, identifies candidates,
flags rejections (ads, sponsor reads) and risk claims.

Output: candidates/triage_output.json (validates against TriageOutput schema)
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from pp_services.video_engine.editorial.schemas import (
    TriageOutput, CandidateMoment, RejectedSegment, RiskFlag
)

logger = logging.getLogger("GrokTriage")

GROK_SYSTEM_PROMPT = """You are a fast-scan content filter for Protocol Pulse, a Bitcoin-first news platform.

YOUR JOB: Read this transcript and identify sections that contain newsworthy,
insightful, or compelling Bitcoin-related content.

Return JSON with THREE sections:

1. candidates[] — potentially newsworthy moments:
   { "source_type": "youtube", "source_name": "{channel}", "source_id": "{video_id}",
     "approx_start": "MM:SS", "approx_end": "MM:SS",
     "topic": "2-5 words", "why_interesting": "1 sentence max 200 chars",
     "speaker": "name or null", "content_type": "insight|news|opinion|data|drama|technical",
     "relevance_score": 1-10, "sentiment": "bullish|bearish|neutral" }

2. rejected[] — segments to NEVER clip:
   { "source_id": "{video_id}", "approx_start": "MM:SS", "approx_end": "MM:SS",
     "reason": "sponsor_read|off_topic|repeat|altcoin_shill|needs_visual_context|ad_read|low_quality" }

3. risk_flags[] — claims that need evidence before broadcast:
   { "source_id": "{video_id}", "claim": "the specific text",
     "risk_type": "unverified_number|regulatory_claim|allegation|ath_claim|prediction|attribution",
     "approx_timestamp": "MM:SS" }

FILTER OUT: Altcoin content (unless directly relevant to BTC ecosystem), pure price
speculation without thesis, ads/sponsors, content requiring visual context,
repetitive content (flag BEST version only).

KEEP: Genuine Bitcoin insight, hot takes that generate discussion, breaking news,
feuds/debates between notable figures, data points with context, developer updates,
mining/hashrate developments, regulatory moves.

Respond with JSON ONLY. No prose, no markdown fences, no explanation."""


class GrokTriage:
    """Stage 1: Fast triage of all source content via Grok."""

    def __init__(self):
        self.api_key = os.environ.get("XAI_API_KEY", "")
        self.model = os.environ.get("GROK_MODEL", "grok-3-fast")
        self.base_url = "https://api.x.ai/v1"
        self.all_candidates = []
        self.all_rejected = []
        self.all_risk_flags = []
        self.tokens_in = 0
        self.tokens_out = 0

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def triage_all(self, source_bundle: Dict,
                    bundle_path: Path = None) -> Optional[TriageOutput]:
        """
        Run triage on all sources in the bundle.
        Returns validated TriageOutput or None on failure.
        """
        if not self.configured:
            logger.error("XAI_API_KEY not set — cannot run Grok triage")
            return None

        logger.info(f"\n{'='*60}")
        logger.info(f"GROK TRIAGE — Stage 1")
        logger.info(f"{'='*60}\n")

        youtube = source_bundle.get("sources", {}).get("youtube", {})
        transcripts = youtube.get("transcripts", [])
        tweets = source_bundle.get("sources", {}).get("tweets", {}).get("tweets", [])

        # Triage each transcript
        for tx in transcripts:
            self._triage_transcript(tx)
            time.sleep(0.5)  # Rate limit courtesy

        # Triage tweets as a batch
        if tweets:
            self._triage_tweets(tweets)

        # Sort candidates by relevance
        self.all_candidates.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)

        logger.info(f"\n  Triage results:")
        logger.info(f"    Candidates: {len(self.all_candidates)}")
        logger.info(f"    Rejected: {len(self.all_rejected)}")
        logger.info(f"    Risk flags: {len(self.all_risk_flags)}")
        logger.info(f"    Tokens: {self.tokens_in} in, {self.tokens_out} out")

        # Validate against schema
        try:
            output = TriageOutput(
                candidates=[CandidateMoment(**c) for c in self.all_candidates],
                rejected=[RejectedSegment(**r) for r in self.all_rejected],
                risk_flags=[RiskFlag(**rf) for rf in self.all_risk_flags]
            )
        except Exception as e:
            logger.error(f"  Schema validation failed: {e}")
            # Attempt partial recovery — keep what validates
            valid_candidates = []
            for c in self.all_candidates:
                try:
                    valid_candidates.append(CandidateMoment(**c))
                except Exception:
                    pass
            output = TriageOutput(candidates=valid_candidates)
            logger.info(f"  Recovered {len(valid_candidates)} valid candidates")

        # Save output
        if bundle_path:
            out_path = bundle_path / "candidates" / "triage_output.json"
            out_path.write_text(json.dumps(output.dict(), indent=2, default=str))
            logger.info(f"  Saved: {out_path}")

        return output

    def _triage_transcript(self, transcript: dict):
        """Triage a single YouTube transcript via Grok."""
        channel = transcript.get("source_name", "Unknown")
        video_id = transcript.get("source_id", "")
        title = transcript.get("title", "")
        text = transcript.get("timestamped_text", "") or transcript.get("text", "")

        # Truncate to ~12,000 chars for API limits
        if len(text) > 12000:
            text = text[:12000] + "\n[TRUNCATED — video continues]"

        prompt = f"""Analyze this YouTube video transcript.

Channel: {channel}
Video Title: {title}
Video ID: {video_id}

TRANSCRIPT:
{text}

Return JSON with candidates[], rejected[], and risk_flags[] arrays."""

        response = self._call_grok(prompt)
        if response:
            self._merge_response(response, video_id)

    def _triage_tweets(self, tweets: List[dict]):
        """Triage notable tweets as a batch via Grok."""
        if not tweets:
            return

        tweet_text = "\n\n".join([
            f"@{t.get('author_handle', '?')} ({t.get('likes', 0)} likes):\n{t.get('text', '')}"
            for t in tweets[:30]
        ])

        prompt = f"""Analyze these notable Bitcoin tweets from the last 24 hours.
For tweet candidates, use source_type "tweet" and the author's handle as source_name.
Use the tweet URL or author handle as source_id.
Set approx_start and approx_end to "00:00" for tweets.

TWEETS:
{tweet_text}

Return JSON with candidates[], rejected[], and risk_flags[] arrays."""

        response = self._call_grok(prompt)
        if response:
            self._merge_response(response)

    def _call_grok(self, prompt: str) -> Optional[dict]:
        """Call Grok API and parse JSON response."""
        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": GROK_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 4000,
                "temperature": 0.3
            }

            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if resp.status_code != 200:
                logger.warning(f"  Grok API returned {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()

            # Track tokens
            usage = data.get("usage", {})
            self.tokens_in += usage.get("prompt_tokens", 0)
            self.tokens_out += usage.get("completion_tokens", 0)

            # Parse response content
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Strip markdown fences if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.warning(f"  Grok response not valid JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"  Grok API call failed: {e}")
            return None

    def _merge_response(self, response: dict, default_source_id: str = ""):
        """Merge triage response into accumulated results."""
        for c in response.get("candidates", []):
            if not c.get("source_id") and default_source_id:
                c["source_id"] = default_source_id
            # Ensure required fields have defaults
            c.setdefault("source_type", "youtube")
            c.setdefault("sentiment", "neutral")
            c.setdefault("content_type", "insight")
            c.setdefault("relevance_score", 5)
            self.all_candidates.append(c)

        for r in response.get("rejected", []):
            if not r.get("source_id") and default_source_id:
                r["source_id"] = default_source_id
            self.all_rejected.append(r)

        for rf in response.get("risk_flags", []):
            if not rf.get("source_id") and default_source_id:
                rf["source_id"] = default_source_id
            self.all_risk_flags.append(rf)
