#!/usr/bin/env python3
"""Intelligent Clip Scoring Engine — data-driven clip selection.

Scores each potential clip moment 0-100 based on 5 dimensions:
1. Topic velocity (from daily_signals.json) — 0-25 points
2. Engagement potential (topic trending on X) — 0-20 points
3. Novelty (not covered in recent episodes) — 0-20 points
4. Speaker authority (channel priority) — 0-15 points
5. Emotional impact (keyword analysis) — 0-20 points

Per PRODUCTION_DESIGN_LAWS.md and PIPELINE_LAWS Section 9.
"""

import json
import logging
import os

logger = logging.getLogger("ClipScorer")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_SIGNALS_PATH = os.path.join(BASE, "data", "intelligence", "daily_signals.json")
LIVE_SIGNALS_PATH = os.path.join(BASE, "data", "intelligence", "live_signals.json")
USED_CLIPS_PATH = os.path.join(BASE, "data", "used_clips.json")
NARRATIVE_CONTEXT_PATH = os.path.join(BASE, "data", "intelligence", "narrative_context.json")
CHANNELS_FILE = os.path.join(BASE, "channels.yaml")

# High-impact words that indicate emotional/breaking content
IMPACT_WORDS = [
    "breaking", "shocking", "unprecedented", "historic", "billion", "million",
    "crashed", "surged", "banned", "approved", "emergency", "revolutionary",
    "first time", "never before", "record", "all-time", "critical", "massive",
    "collapse", "exploded", "plummeted", "skyrocketed", "halving", "strategic reserve",
]

# Engagement-boosting topics (from tweet study data and X algorithm preferences)
HIGH_ENGAGEMENT_TOPICS = {
    "ETF": 18, "price": 16, "mining": 14, "regulation": 15,
    "self-custody": 12, "macro": 13, "institutional": 14,
    "lightning": 10, "privacy": 11,
}


def _load_json(path):
    """Load JSON file safely."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_channel_priorities():
    """Load channel priority map from channels.yaml."""
    try:
        import yaml
        with open(CHANNELS_FILE) as f:
            config = yaml.safe_load(f)
        priorities = {}
        for ch in config.get("channels", []) + config.get("mainstream", []):
            name = ch.get("name", ch.get("handle", ""))
            if name:
                priorities[name] = ch.get("priority", ch.get("tier", 3))
        return priorities
    except Exception:
        return {}


def _get_recent_topics(max_episodes=3):
    """Get topics covered in last N episodes (for novelty scoring)."""
    data = _load_json(USED_CLIPS_PATH)
    if not data:
        return set()

    recent = data.get("episodes", [])[-max_episodes:]
    topics = set()
    for ep in recent:
        # Extract channel names as proxy for topics (full topic tracking would need
        # the actual clip quotes stored in episode memory)
        topics.update(ep.get("channels", []))
    return topics


def _get_live_boost_topics():
    """Get topics from active live streams for velocity boost (1.5x per LIVE_INTELLIGENCE_LAWS)."""
    data = _load_json(LIVE_SIGNALS_PATH)
    if not data:
        return set()
    live_topics = set()
    for s in data.get("live_streams", []):
        if s.get("status") == "live":
            live_topics.update(s.get("topics", []))
    return live_topics


def _load_narrative_context():
    """Load narrative_context.json for narrative match scoring."""
    return _load_json(NARRATIVE_CONTEXT_PATH) or {}


def _score_narrative_match(clip: dict, narrative_context: dict) -> int:
    """Score how well a clip matches today's dominant thought leader narrative.

    0-25 points:
    - 25: clip topic exactly matches #1 narrative AND channel is thought leader's YT channel
    - 20: clip topic matches #1 narrative
    - 15: clip topic matches #2 or #3 narrative
    - 10: clip topic adjacent to a narrative
    - 5:  clip mentions any trending thought leader by name
    - 0:  no narrative connection
    """
    priority_topics = narrative_context.get("clip_selection_priority", [])
    if not priority_topics:
        return 0

    clip_text = " ".join([
        clip.get("quote", ""),
        clip.get("key_quote", ""),
        clip.get("video_title", ""),
        clip.get("why", ""),
        clip.get("host_setup", ""),
        clip.get("narrator_intro", ""),
    ]).lower()

    if not clip_text.strip():
        return 0

    # Check exact match with top narrative
    top_narrative = priority_topics[0].lower() if priority_topics else ""
    if top_narrative:
        top_words = [w for w in top_narrative.split() if len(w) > 2]
        if top_words and all(w in clip_text for w in top_words):
            return 25  # Full match with #1 narrative
        if top_words and any(w in clip_text for w in top_words):
            return 20  # Partial match with #1 narrative

    # Check secondary narratives (#2 and #3)
    for topic in priority_topics[1:3]:
        topic_words = [w for w in topic.lower().split() if len(w) > 2]
        if topic_words and any(w in clip_text for w in topic_words):
            return 15

    # Check thought leader name mentions
    thought_leaders = narrative_context.get("thought_leaders_mentioned", [])
    if any(tl.lower() in clip_text for tl in thought_leaders if tl):
        return 5

    return 0


def score_clip(clip, daily_signals=None, channel_priorities=None, recent_channels=None,
               live_topics=None, narrative_context=None):
    """Score a single clip moment 0-100 across 6 dimensions.

    Dimensions:
    1. Topic velocity (daily_signals.json) — 0-25 pts
    2. Engagement potential (X trending) — 0-20 pts
    3. Novelty (not in recent episodes) — 0-20 pts
    4. Speaker authority (channel tier) — 0-15 pts
    5. Emotional impact (keyword) — 0-20 pts
    6. Narrative match (thought leader discourse) — 0-25 pts

    Raw total 0-125, normalized to 0-100.

    Args:
        clip: Dict with at minimum 'channel' and 'quote'/'transcript' keys.
        daily_signals: Loaded daily_signals.json dict (or None to load from disk).
        channel_priorities: Dict of channel_name -> priority int (or None to load).
        recent_channels: Set of channel names from recent episodes (or None to compute).
        live_topics: Set of topics from active live streams (or None to load).
        narrative_context: Loaded narrative_context.json dict (or None to load from disk).

    Returns:
        int: Score 0-100.
    """
    if daily_signals is None:
        daily_signals = _load_json(DAILY_SIGNALS_PATH) or {}
    if channel_priorities is None:
        channel_priorities = _load_channel_priorities()
    if recent_channels is None:
        recent_channels = _get_recent_topics(max_episodes=3)
    if live_topics is None:
        live_topics = _get_live_boost_topics()
    if narrative_context is None:
        narrative_context = _load_narrative_context()

    # Combine all text for analysis
    text = " ".join([
        clip.get("quote", ""),
        clip.get("why", ""),
        clip.get("host_setup", ""),
        clip.get("video_title", ""),
    ]).lower()

    raw_score = 0

    # ── 1. Topic Velocity (0-25 points) ──
    topic_velocity = daily_signals.get("topic_velocity", [])
    best_velocity = 0
    for topic_entry in topic_velocity:
        topic_name = topic_entry.get("topic", "").lower()
        velocity = topic_entry.get("velocity_score", 0)

        if topic_name in text or any(w in text for w in topic_name.split()):
            topic_score = min(velocity / 4, 25)
            if topic_name in live_topics:
                topic_score = min(topic_score * 1.5, 25)
            best_velocity = max(best_velocity, topic_score)

    raw_score += round(best_velocity)

    # ── 2. Engagement Potential (0-20 points) ──
    engagement_score = 0
    for topic, base_engagement in HIGH_ENGAGEMENT_TOPICS.items():
        if topic.lower() in text:
            engagement_score = max(engagement_score, base_engagement)
    raw_score += min(engagement_score, 20)

    # ── 3. Novelty (0-20 points) ──
    channel = clip.get("channel", "")
    if channel in recent_channels:
        raw_score += 5
    else:
        raw_score += 20

    # ── 4. Speaker Authority (0-15 points) ──
    priority = channel_priorities.get(channel, 3)
    authority_map = {1: 15, 2: 10, 3: 5}
    raw_score += authority_map.get(priority, 3)

    # ── 5. Emotional Impact (0-20 points) ──
    impact_count = sum(1 for w in IMPACT_WORDS if w in text)
    raw_score += min(impact_count * 5, 20)

    # ── 6. Narrative Match (0-25 points) ──
    raw_score += _score_narrative_match(clip, narrative_context)

    # Normalize: raw 0-125 → 0-100
    final_score = min(100, round(raw_score * 100 / 125))
    return final_score


def rank_clips(clips, daily_signals=None, narrative_context=None):
    """Score and rank a list of clips. Returns clips sorted by score (highest first).

    Each clip gets a 'score' field added.

    Args:
        clips: List of clip dicts (from Claude's selection).
        daily_signals: Optional pre-loaded daily_signals.json.
        narrative_context: Optional pre-loaded narrative_context.json.

    Returns:
        List of clips sorted by score descending, each with 'score' added.
    """
    if daily_signals is None:
        daily_signals = _load_json(DAILY_SIGNALS_PATH) or {}
    if narrative_context is None:
        narrative_context = _load_narrative_context()

    channel_priorities = _load_channel_priorities()
    recent_channels = _get_recent_topics(max_episodes=3)
    live_topics = _get_live_boost_topics()

    # Log narrative context
    dominant = narrative_context.get("dominant_narrative", "none")
    priorities = narrative_context.get("clip_selection_priority", [])
    if dominant and dominant != "none":
        logger.info(f"Episode narrative: {dominant} | Priority topics: {priorities}")

    for clip in clips:
        clip["score"] = score_clip(
            clip,
            daily_signals=daily_signals,
            channel_priorities=channel_priorities,
            recent_channels=recent_channels,
            live_topics=live_topics,
            narrative_context=narrative_context,
        )

    ranked = sorted(clips, key=lambda c: c.get("score", 0), reverse=True)

    for i, clip in enumerate(ranked):
        logger.info(f"  SCORE #{i+1}: [{clip.get('channel', '')}] "
                    f"score={clip['score']} — {clip.get('video_title', '')[:40]}")

    return ranked


def select_top_clips(clips, count=5, daily_signals=None, narrative_context=None):
    """Score all clips, then pick the top N from N unique channels.

    Enforces channel diversity: one clip per channel, highest-scored wins.

    Args:
        clips: List of clip dicts.
        count: Number of clips to select (default 5).
        daily_signals: Optional pre-loaded daily_signals.json.
        narrative_context: Optional pre-loaded narrative_context.json.

    Returns:
        List of top N clips from N unique channels, sorted by score.
    """
    ranked = rank_clips(clips, daily_signals=daily_signals, narrative_context=narrative_context)

    selected = []
    seen_channels = set()
    for clip in ranked:
        channel = clip.get("channel", "")
        if channel in seen_channels:
            continue
        seen_channels.add(channel)
        selected.append(clip)
        if len(selected) >= count:
            break

    logger.info(f"Selected top {len(selected)} clips from {len(seen_channels)} unique channels")
    return selected


if __name__ == "__main__":
    # Demo with mock clips
    test_clips = [
        {"channel": "Simply Bitcoin", "quote": "Bitcoin ETF inflows just hit a record billion dollars",
         "video_title": "BREAKING: ETF Record Inflows", "why": "Record breaking ETF data"},
        {"channel": "TFTC", "quote": "Hash rate surged to unprecedented levels",
         "video_title": "Mining Update: Hash Rate ATH", "why": "Historic hash rate data"},
        {"channel": "What Bitcoin Did", "quote": "The fed is going to have to cut rates",
         "video_title": "Macro Analysis with Luke Gromen", "why": "Macro insight"},
        {"channel": "Preston Pysh", "quote": "Self custody is more important than ever",
         "video_title": "Why Self-Custody Matters in 2026", "why": "Sovereignty angle"},
        {"channel": "Blockworks", "quote": "Lightning network capacity just exploded",
         "video_title": "Lightning Network Growth", "why": "Layer 2 data"},
    ]

    results = select_top_clips(test_clips, count=5)
    print("\nTop clips by score:")
    for c in results:
        print(f"  {c['score']:3d} | {c['channel']:20s} | {c['video_title']}")
