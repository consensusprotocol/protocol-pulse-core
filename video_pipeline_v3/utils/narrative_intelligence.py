#!/usr/bin/env python3
"""
Narrative Intelligence Engine — Protocol Pulse

Monitors 50 Bitcoin thought leaders on X, extracts narrative topics,
scores topic velocity, and produces a ranked narrative signal for
clip selection.

Data flow:
  social_targets.json (50 handles)
    → X API recent tweets (last 4hr, Priority-1 handles only for freshness)
    → Claude Haiku narrative extraction per tweet batch
    → Topic velocity scoring (mentions × authority weight)
    → daily_signals.json updated with real narrative data
    → narrative_context.json written for clip_selector consumption

Run: python3 -m utils.narrative_intelligence  (standalone from video_pipeline_v3/)
Also called from daily_run.py Step 0 before clip selection.

# TODO(P2): Add historical velocity decay from previous day's dominant narrative
# TODO(P2): Add rate-limit backoff for X API (currently relies on Tweepy's built-in)
"""

import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("NarrativeIntelligence")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[narrative] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Paths
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOCIAL_TARGETS_PATH = os.path.join(os.path.dirname(BASE), "config", "social_targets.json")
INTELLIGENCE_DIR = os.path.join(BASE, "data", "intelligence")
DAILY_SIGNALS_PATH = os.path.join(INTELLIGENCE_DIR, "daily_signals.json")
NARRATIVE_CONTEXT_PATH = os.path.join(INTELLIGENCE_DIR, "narrative_context.json")
HISTORY_PATH = os.path.join(INTELLIGENCE_DIR, "narrative_history.json")

# Handles to skip (competitor intel — different signal per build plan)
SKIP_HANDLES = {"VitalikButerin", "CZ_Binance"}

# Priority-1 handles (3x authority weight)
PRIORITY_1_HANDLES = {
    "saylor", "natbrunell", "jack", "gladstein", "PrestonPysh",
    "MartyBent", "CaitlinLong_", "LynAldenContact", "JeffBooth", "ODELL",
    "aantonop", "adam3us", "NickSzabo4", "Snowden", "pwuille",
}

NARRATIVE_PROMPT = """You are analyzing tweets from Bitcoin thought leaders to identify the dominant narrative
topics being discussed RIGHT NOW.

Tweets (last 4-12 hours from high-authority Bitcoin accounts):
{tweet_batch}

Extract the TOP 5 narrative topics being discussed. For each topic:
- Give it a clean label (e.g. "ETF inflows", "mining difficulty", "Fed policy",
  "self-custody", "halving cycle", "regulatory clarity", "institutional adoption",
  "Lightning adoption", "miner capitulation", "macro correlation", "stablecoin risk")
- Count how many unique handles mentioned it
- Assess sentiment: bullish / bearish / neutral / mixed
- Identify the most authoritative quote (shortest, most quotable statement)

RULES:
- Labels must be specific, not generic ("ETF inflows" not just "ETF")
- Ignore price speculation ("going to 100k") — focus on fundamentals/narrative
- One topic per concept (don't split "mining" and "hashrate" — they're the same)
- If a Priority-1 handle (Saylor, Lyn Alden, Jack Dorsey, etc.) mentions a topic,
  weight it 3x vs a Priority-2 handle

Return ONLY valid JSON:
{{
  "narratives": [
    {{
      "topic": "ETF inflows",
      "mention_count": 8,
      "authority_score": 45,
      "sentiment": "bullish",
      "top_quote": "BlackRock saw $400M inflow yesterday",
      "handles": ["saylor", "LynAldenContact"],
      "velocity": "rising"
    }}
  ],
  "dominant_narrative": "ETF inflows",
  "market_mood": "cautiously_bullish",
  "computed_at": "{timestamp}"
}}"""


class NarrativeIntelligenceEngine:
    def __init__(self):
        self.targets = self._load_targets()
        os.makedirs(INTELLIGENCE_DIR, exist_ok=True)

    def _load_targets(self) -> list:
        """Load and filter thought leader handles from social_targets.json."""
        try:
            with open(SOCIAL_TARGETS_PATH) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Cannot load social_targets.json: {e}")
            return []

        targets = []
        for t in data.get("targets", []):
            handle = t.get("handle", "")
            priority = t.get("priority", 3)
            if priority > 2:
                continue
            if handle in SKIP_HANDLES:
                continue
            targets.append({
                "handle": handle,
                "priority": priority,
                "category": t.get("category", ""),
            })
        logger.info(f"Loaded {len(targets)} thought leader handles "
                    f"({sum(1 for t in targets if t['priority'] == 1)} P1, "
                    f"{sum(1 for t in targets if t['priority'] == 2)} P2)")
        return targets

    def fetch_thought_leader_tweets(self, max_per_handle: int = 10) -> list:
        """Fetch recent tweets from thought leader handles via X API.

        Uses Tweepy v2 search_recent_tweets with handle batching.
        Falls back to empty list if API unavailable.
        """
        try:
            import tweepy
        except ImportError:
            logger.warning("Tweepy not installed — using fallback")
            return []

        # Get bearer token
        sys.path.insert(0, BASE)
        try:
            from relay import get_key
            bearer_token = get_key("X_BEARER_TOKEN", required=False)
            if not bearer_token:
                bearer_token = get_key("TWITTER_BEARER_TOKEN", required=False)
        except Exception:
            bearer_token = ""

        if not bearer_token:
            logger.warning("No X bearer token — using fallback data")
            return []

        client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)

        # Batch handles into groups of 15 (query length limit)
        p1_handles = [t["handle"] for t in self.targets if t["priority"] == 1]
        p2_handles = [t["handle"] for t in self.targets if t["priority"] == 2]

        all_tweets = []
        now = datetime.now(timezone.utc)

        for handle_group, max_age_hours in [(p1_handles, 4), (p2_handles, 12)]:
            cutoff = now - timedelta(hours=max_age_hours)

            # Batch into groups of 15 handles (512 char query limit)
            for i in range(0, len(handle_group), 15):
                batch = handle_group[i:i+15]
                query_parts = [f"from:{h}" for h in batch]
                query = "(" + " OR ".join(query_parts) + ") -is:retweet lang:en"

                if len(query) > 512:
                    # Split further if needed
                    mid = len(batch) // 2
                    batch = batch[:mid]
                    query_parts = [f"from:{h}" for h in batch]
                    query = "(" + " OR ".join(query_parts) + ") -is:retweet lang:en"

                try:
                    response = client.search_recent_tweets(
                        query=query,
                        max_results=min(max_per_handle * len(batch), 100),
                        tweet_fields=["created_at", "public_metrics", "author_id"],
                        user_fields=["username"],
                        expansions=["author_id"],
                        sort_order="recency",
                    )
                except Exception as e:
                    logger.warning(f"X API search failed for batch: {e}")
                    continue

                if not response.data:
                    continue

                # Build author_id → username map
                users_map = {}
                if response.includes and "users" in response.includes:
                    for u in response.includes["users"]:
                        users_map[u.id] = u.username

                for tweet in response.data:
                    created = tweet.created_at
                    if created and created < cutoff:
                        continue

                    text = tweet.text or ""
                    # Filter rules from build plan
                    if len(text) < 5:
                        continue
                    if text.startswith("RT @"):
                        continue
                    # Skip pure price speculation
                    text_lower = text.lower()
                    if any(phrase in text_lower for phrase in
                           ["going to 200k", "going to 100k", "buy now", "price target",
                            "going to 500k", "going to 1m"]):
                        continue

                    handle = users_map.get(tweet.author_id, "unknown")
                    priority = 1 if handle in PRIORITY_1_HANDLES else 2
                    metrics = tweet.public_metrics or {}

                    all_tweets.append({
                        "handle": handle,
                        "text": text,
                        "created_at": created.isoformat() if created else "",
                        "author_priority": priority,
                        "likes": metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                    })

        logger.info(f"Fetched {len(all_tweets)} tweets from thought leaders")
        return all_tweets

    def extract_narratives(self, tweets: list) -> dict:
        """Use Claude Haiku to extract narrative topics from tweet batch."""
        if not tweets:
            return self._fallback_narratives()

        sys.path.insert(0, BASE)
        from relay import get_key

        # Format tweets for prompt
        tweet_lines = []
        for t in tweets[:50]:  # Cap at 50 tweets for token budget
            p_label = "P1" if t["author_priority"] == 1 else "P2"
            tweet_lines.append(
                f"[@{t['handle']}] ({p_label}, {t['likes']}♥) {t['text'][:280]}"
            )
        tweet_batch = "\n".join(tweet_lines)
        timestamp = datetime.now(timezone.utc).isoformat()
        prompt = NARRATIVE_PROMPT.format(tweet_batch=tweet_batch, timestamp=timestamp)

        # Try Claude Haiku first
        anthropic_key = get_key("ANTHROPIC_API_KEY", required=False)
        if anthropic_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key)
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = resp.content[0].text.strip()
                # Strip markdown fences
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                return json.loads(text)
            except Exception as e:
                logger.warning(f"Claude narrative extraction failed: {e}")

        # Fallback to Grok
        xai_key = get_key("XAI_API_KEY", required=False)
        if xai_key:
            try:
                import requests
                resp = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {xai_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": "grok-3-mini-fast",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2000,
                        "temperature": 0.2,
                    },
                    timeout=60,
                )
                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"].strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]
                    return json.loads(text)
            except Exception as e:
                logger.warning(f"Grok narrative extraction failed: {e}")

        return self._fallback_narratives()

    def _fallback_narratives(self) -> dict:
        """Fallback narrative data when APIs are unavailable."""
        # Try to use existing daily_signals as baseline
        try:
            with open(DAILY_SIGNALS_PATH) as f:
                existing = json.load(f)
            topics = existing.get("topic_velocity", [])
            if topics:
                logger.info("Using existing daily_signals.json as fallback narrative data")
                return {
                    "narratives": [{
                        "topic": t.get("topic", "unknown"),
                        "mention_count": t.get("channels", 1),
                        "authority_score": t.get("velocity_score", 10),
                        "sentiment": t.get("sentiment", "neutral"),
                        "top_quote": "",
                        "handles": [],
                        "velocity": "stable",
                    } for t in topics[:5]],
                    "dominant_narrative": topics[0].get("topic", "unknown") if topics else "unknown",
                    "market_mood": "neutral",
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception:
            pass

        logger.warning("No fallback data available — returning empty narratives")
        return {
            "narratives": [],
            "dominant_narrative": "unknown",
            "market_mood": "neutral",
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    def compute_velocity_score(self, narrative: dict) -> float:
        """Score = (mention_count x authority_weight) x velocity_multiplier. Max 100."""
        mention_count = narrative.get("mention_count", 0)
        handles = narrative.get("handles", [])

        # Authority weight: 3.0 if any P1 handle, 1.5 otherwise
        has_p1 = any(h in PRIORITY_1_HANDLES for h in handles)
        authority_weight = 3.0 if has_p1 else 1.5

        # Velocity multiplier based on velocity field
        velocity_str = narrative.get("velocity", "stable")
        velocity_map = {"rising": 2.0, "stable": 1.0, "falling": 0.5}
        velocity_mult = velocity_map.get(velocity_str, 1.0)

        # Historical decay: if same topic dominated yesterday, reduce
        history = self._load_history()
        yesterday_dominant = history.get("yesterday_dominant", "")
        topic = narrative.get("topic", "")
        if topic.lower() == yesterday_dominant.lower() and yesterday_dominant:
            velocity_mult *= 0.5  # Decay stale dominant narratives

        raw = mention_count * authority_weight * velocity_mult
        return min(100.0, raw)

    def _load_history(self) -> dict:
        """Load yesterday's narrative history for decay calculation."""
        try:
            with open(HISTORY_PATH) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_history(self, dominant_narrative: str):
        """Save today's dominant narrative as history for tomorrow's decay."""
        history = {"yesterday_dominant": dominant_narrative,
                   "saved_at": datetime.now(timezone.utc).isoformat()}
        self._atomic_write(HISTORY_PATH, history)

    def _atomic_write(self, path: str, data: dict):
        """Write JSON atomically (tmp file → rename) to prevent corruption."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(path), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def build_daily_signals(self, narrative_result: dict, tweet_count: int,
                            active_leaders: int) -> dict:
        """Build daily_signals.json from narrative extraction result."""
        narratives = narrative_result.get("narratives", [])
        topic_velocity = []
        for n in narratives:
            score = self.compute_velocity_score(n)
            topic_velocity.append({
                "topic": n.get("topic", "unknown"),
                "channels": n.get("mention_count", 0),
                "sentiment": n.get("sentiment", "neutral"),
                "velocity_score": round(score),
                "authority_score": n.get("authority_score", 0),
                "top_quote": n.get("top_quote", ""),
                "thought_leaders": n.get("handles", []),
                "source": "thought_leader_tweets",
                "freshness_hours": 4.0,
            })

        # Sort by velocity_score descending
        topic_velocity.sort(key=lambda x: x["velocity_score"], reverse=True)

        signals = {
            "topic_velocity": topic_velocity,
            "breaking_threshold": any(t["velocity_score"] >= 80 for t in topic_velocity),
            "recommended_topics": [t["topic"] for t in topic_velocity[:3]],
            "dominant_narrative": narrative_result.get("dominant_narrative", "unknown"),
            "market_mood": narrative_result.get("market_mood", "neutral"),
            "total_tweets_analyzed": tweet_count,
            "thought_leaders_active": active_leaders,
            "scan_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return signals

    def build_narrative_context(self, narrative_result: dict,
                                signals: dict) -> dict:
        """Build narrative_context.json for clip selector + script writer."""
        narratives = narrative_result.get("narratives", [])
        dominant = narrative_result.get("dominant_narrative", "unknown")
        mood = narrative_result.get("market_mood", "neutral")

        # Count active P1 handles
        all_handles = set()
        for n in narratives:
            all_handles.update(n.get("handles", []))
        p1_active = sum(1 for h in all_handles if h in PRIORITY_1_HANDLES)

        # Build episode narrative description
        top_narrative = narratives[0] if narratives else {}
        top_quote = top_narrative.get("top_quote", "")
        top_handles = top_narrative.get("handles", [])

        episode_narrative = (
            f"{dominant} is dominating Bitcoin discourse — "
            f"{top_narrative.get('mention_count', 0)} of {p1_active} Priority-1 "
            f"thought leaders tweeted about it in the last 4 hours"
        ) if narratives else "No dominant narrative detected"

        eryn_hook = (
            f"Eryn should reference: '{top_quote}' from thought leaders "
            f"{', '.join(top_handles[:3])}"
        ) if top_quote else "Eryn should lead with the day's strongest Bitcoin signal"

        mark_context = ""
        if len(narratives) >= 2:
            second = narratives[1]
            mark_context = (
                f"Mark should add context: '{second.get('topic', '')}' is also trending "
                f"with {second.get('mention_count', 0)} thought leaders discussing it"
            )
        else:
            mark_context = "Mark should provide contrarian analysis on the dominant narrative"

        context = {
            "episode_narrative": episode_narrative,
            "eryn_intro_hook": eryn_hook,
            "mark_context": mark_context,
            "clip_selection_priority": [n.get("topic", "") for n in narratives[:3]],
            "avoid_topics": ["price speculation", "altcoins"],
            "thought_leaders_mentioned": list(all_handles),
            "narrative_bridge_lines": [
                "And this is exactly what Bitcoin thought leaders predicted — here's what they said:",
                "The discourse on X is clear — let's hear from the channels who called this first:",
            ],
            "dominant_narrative": dominant,
            "market_mood": mood,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        return context

    def run(self) -> dict:
        """Main entry: fetch tweets → extract narratives → write output files."""
        logger.info("Starting narrative intelligence scan...")
        t0 = time.time()

        # 1. Fetch tweets
        tweets = self.fetch_thought_leader_tweets()
        tweet_count = len(tweets)
        active_handles = len(set(t["handle"] for t in tweets)) if tweets else 0

        # 2. Extract narratives
        if tweets:
            narrative_result = self.extract_narratives(tweets)
            source = "live"
        else:
            logger.warning("No tweets fetched — using fallback narratives")
            narrative_result = self._fallback_narratives()
            source = "fallback_historical"

        # Tag source
        for n in narrative_result.get("narratives", []):
            n["source"] = source

        # 3. Compute velocity scores and build outputs
        signals = self.build_daily_signals(narrative_result, tweet_count, active_handles)
        context = self.build_narrative_context(narrative_result, signals)

        # 4. Write outputs atomically
        self._atomic_write(DAILY_SIGNALS_PATH, signals)
        self._atomic_write(NARRATIVE_CONTEXT_PATH, context)

        # 5. Save history for tomorrow's decay
        dominant = narrative_result.get("dominant_narrative", "unknown")
        self._save_history(dominant)

        elapsed = time.time() - t0
        logger.info(f"Narrative scan complete in {elapsed:.1f}s — "
                    f"dominant: {dominant}, mood: {signals.get('market_mood')}, "
                    f"tweets: {tweet_count}, leaders: {active_handles}, "
                    f"source: {source}")

        return signals


if __name__ == "__main__":
    engine = NarrativeIntelligenceEngine()
    result = engine.run()
    print(f"\nDominant narrative: {result['dominant_narrative']}")
    print(f"Market mood: {result['market_mood']}")
    print(f"Top topics: {[t['topic'] for t in result.get('topic_velocity', [])[:3]]}")
    print(f"Tweets analyzed: {result['total_tweets_analyzed']}")
    print(f"Thought leaders active: {result['thought_leaders_active']}")
