"""
analyzer.py — Gemini Sentiment Extraction
Analyzes rolling transcripts every 30s using Gemini 2.0 Flash.
Produces Bitcoin sentiment scores, key topics, notable quotes.
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    space_id: str
    sentiment_score: int          # 0–100 (0=extreme fear, 100=extreme greed)
    sentiment_label: str          # EXTREME FEAR | FEAR | NEUTRAL | GREED | EXTREME GREED
    key_topics: list[str]
    notable_quotes: list[str]
    market_signals: list[str]
    confidence: float
    analyzed_at: float = field(default_factory=time.time)
    transcript_words: int = 0

    def to_dict(self):
        d = asdict(self)
        return d


SENTIMENT_PROMPT_TEMPLATE = """You are a Bitcoin market analyst. Analyze this transcript from a live Bitcoin discussion on X Spaces.

Transcript (last ~{window_minutes} minutes):
---
{transcript}
---

Respond in JSON ONLY (no markdown, no explanation):
{{
  "sentiment_score": <integer 0-100, where 0=extreme fear, 50=neutral, 100=extreme greed>,
  "sentiment_label": "<EXTREME FEAR|FEAR|NEUTRAL|GREED|EXTREME GREED>",
  "key_topics": ["<topic1>", "<topic2>", "<topic3>"],
  "notable_quotes": ["<direct quote or paraphrase>"],
  "market_signals": ["<specific signal mentioned, e.g. 'ETF inflows mentioned', 'halving discussed'>"],
  "confidence": <float 0.0-1.0 based on transcript clarity and relevance>
}}

Rules:
- sentiment_score: based purely on tone and content, not price
- key_topics: max 5, concise (2-4 words each)
- notable_quotes: max 3, most impactful statements
- market_signals: specific actionable signals only, max 5
- If transcript is too short or unclear, set confidence < 0.4"""


def score_to_label(score: int) -> str:
    if score <= 20:
        return "EXTREME FEAR"
    elif score <= 40:
        return "FEAR"
    elif score <= 60:
        return "NEUTRAL"
    elif score <= 80:
        return "GREED"
    else:
        return "EXTREME GREED"


class SentimentAnalyzer:
    """
    Periodically analyzes rolling transcripts using Gemini 2.0 Flash.
    """

    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self._latest: dict[str, SentimentResult] = {}  # space_id → latest result
        self._history: dict[str, list[SentimentResult]] = {}  # space_id → history
        self._running = False

        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set — sentiment analysis will be disabled")

    def analyze_transcript(self, space_id: str, transcript: str, window_minutes: float = 5.0) -> Optional[SentimentResult]:
        """
        Synchronously call Gemini to analyze a transcript chunk.
        Returns SentimentResult or None if analysis fails.
        """
        if not self.api_key:
            return self._mock_result(space_id, transcript)

        if not transcript or len(transcript.split()) < 10:
            logger.debug(f"[{space_id}] Transcript too short for analysis ({len(transcript.split())} words)")
            return None

        prompt = SENTIMENT_PROMPT_TEMPLATE.format(
            window_minutes=int(window_minutes),
            transcript=transcript[:4000],  # Limit to avoid token overflow
        )

        try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{config.GEMINI_MODEL}:generateContent"
                f"?key={self.api_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 512,
                    "responseMimeType": "application/json",
                },
            }
            r = requests.post(url, json=payload, timeout=15)
            r.raise_for_status()

            response_json = r.json()
            raw_text = (
                response_json.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            # Parse JSON from response
            parsed = self._parse_json_response(raw_text)
            if not parsed:
                logger.warning(f"[{space_id}] Could not parse Gemini response: {raw_text[:200]}")
                return None

            score = int(parsed.get("sentiment_score", 50))
            score = max(0, min(100, score))

            result = SentimentResult(
                space_id=space_id,
                sentiment_score=score,
                sentiment_label=parsed.get("sentiment_label", score_to_label(score)),
                key_topics=parsed.get("key_topics", [])[:5],
                notable_quotes=parsed.get("notable_quotes", [])[:3],
                market_signals=parsed.get("market_signals", [])[:5],
                confidence=float(parsed.get("confidence", 0.5)),
                transcript_words=len(transcript.split()),
            )

            logger.info(
                f"[{space_id}] Sentiment: {result.sentiment_label} ({result.sentiment_score}) "
                f"confidence={result.confidence:.2f} topics={result.key_topics[:2]}"
            )
            return result

        except requests.exceptions.Timeout:
            logger.warning(f"[{space_id}] Gemini API timeout")
            return None
        except Exception as e:
            logger.error(f"[{space_id}] Gemini API error: {e}")
            return None

    def _parse_json_response(self, text: str) -> Optional[dict]:
        """Extract and parse JSON from Gemini response text."""
        text = text.strip()
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Extract JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    def _mock_result(self, space_id: str, transcript: str) -> SentimentResult:
        """Return a neutral mock result when API key is not set."""
        return SentimentResult(
            space_id=space_id,
            sentiment_score=50,
            sentiment_label="NEUTRAL",
            key_topics=["bitcoin", "analysis"],
            notable_quotes=[],
            market_signals=[],
            confidence=0.0,
            transcript_words=len(transcript.split()),
        )

    def update_result(self, result: SentimentResult):
        """Store a new result."""
        self._latest[result.space_id] = result
        if result.space_id not in self._history:
            self._history[result.space_id] = []
        self._history[result.space_id].append(result)
        # Keep last 100 results per space
        if len(self._history[result.space_id]) > 100:
            self._history[result.space_id] = self._history[result.space_id][-100:]

    def get_latest(self, space_id: str) -> Optional[SentimentResult]:
        return self._latest.get(space_id)

    def get_aggregate_sentiment(self) -> dict:
        """
        Compute aggregate sentiment across all active spaces.
        Weighted by confidence.
        """
        if not self._latest:
            return {
                "overall_score": 50,
                "label": "NEUTRAL",
                "active_spaces_count": 0,
                "topics": [],
                "updated_at": time.time(),
            }

        total_weight = 0.0
        weighted_score = 0.0
        all_topics: dict[str, int] = {}

        for result in self._latest.values():
            w = max(result.confidence, 0.1)
            weighted_score += result.sentiment_score * w
            total_weight += w
            for topic in result.key_topics:
                all_topics[topic] = all_topics.get(topic, 0) + 1

        avg_score = int(weighted_score / total_weight) if total_weight > 0 else 50

        # Top topics by frequency
        top_topics = sorted(all_topics, key=lambda t: all_topics[t], reverse=True)[:6]

        return {
            "overall_score": avg_score,
            "label": score_to_label(avg_score),
            "active_spaces_count": len(self._latest),
            "topics": top_topics,
            "updated_at": time.time(),
        }

    async def run_analysis_loop(self, transcriber):
        """
        Periodic loop: every SENTIMENT_ANALYSIS_INTERVAL seconds,
        analyze the rolling transcript for each active space.
        """
        self._running = True
        logger.info(
            f"SentimentAnalyzer loop started "
            f"(interval={config.SENTIMENT_ANALYSIS_INTERVAL}s, "
            f"window={config.TRANSCRIPT_WINDOW_MINUTES}m)"
        )
        while self._running:
            await asyncio.sleep(config.SENTIMENT_ANALYSIS_INTERVAL)
            if not transcriber:
                continue
            for space_id, rolling in transcriber.get_all_transcripts().items():
                transcript = rolling.get_text(minutes=config.TRANSCRIPT_WINDOW_MINUTES)
                if not transcript:
                    continue
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self.analyze_transcript,
                    space_id,
                    transcript,
                    config.TRANSCRIPT_WINDOW_MINUTES,
                )
                if result:
                    self.update_result(result)

    def stop(self):
        self._running = False
