#!/usr/bin/env python3
"""
episode_memory.py — Sovereign Episode Memory for Protocol Pulse

Records what was covered in each episode. SCRIBE queries this before
writing scripts to avoid repeating topics, reusing channels, or
recycling the same narrative angles.

This is how we structurally prevent stale context bleed.
"""
import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("episode_memory")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "agent_state.db")


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def record_episode(episode_date, script, clips, intel_data=None, quality_score=None, grade=None):
    """Record a completed episode to memory. Called after successful render."""
    dialogue = script.get("dialogue", [])
    full_text = " ".join(d.get("text", "") for d in dialogue).lower()

    # Extract topics from script text
    topic_keywords = [
        "mining", "hashrate", "etf", "regulation", "sec", "tariff", "trade war",
        "adoption", "institutional", "sovereignty", "lightning", "privacy", "nostr",
        "quantum", "cbdc", "stablecoin", "defi", "self-custody", "accumulation",
        "halving", "difficulty", "mempool", "fees", "dominance", "macro",
        "inflation", "federal reserve", "interest rate", "treasury", "china",
        "russia", "el salvador", "microstrategy", "saylor", "blackrock",
    ]
    topics = [t for t in topic_keywords if t in full_text]

    # Extract channels featured
    channels = []
    for c in clips:
        ch = c.get("channel", "")
        if ch and ch not in channels:
            channels.append(ch)

    # Extract cold open topic
    cold_open = ""
    for d in dialogue:
        if d.get("type") == "cold_open":
            cold_open = d.get("text", "")[:200]
            break

    conn = _connect()
    try:
        conn.execute("""
            INSERT INTO episode_memory 
            (episode_date, episode_title, topics_covered, channels_featured,
             clips_used, btc_price, dominance, fear_greed, hashrate,
             cold_open_topic, narrative_theme, quality_score, grade)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode_date,
            script.get("episode_title", ""),
            json.dumps(topics),
            json.dumps(channels),
            json.dumps([c.get("video_id", "") for c in clips]),
            str(intel_data.get("btc_price", "")) if intel_data else "",
            str(intel_data.get("btc_dominance", "")) if intel_data else "",
            str(intel_data.get("fear_greed_value", "")) if intel_data else "",
            str(intel_data.get("hashrate_current", "")) if intel_data else "",
            cold_open,
            script.get("theme", ""),
            quality_score,
            grade,
        ))
        conn.commit()
        logger.info(f"EPISODE MEMORY: Recorded {episode_date} — topics: {topics[:5]}, channels: {channels}")
    finally:
        conn.close()


def get_recent_topics(days=3, limit=5):
    """Get topics covered in the last N days. SCRIBE uses this to avoid repeats."""
    conn = _connect()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT episode_date, topics_covered, cold_open_topic, narrative_theme "
            "FROM episode_memory WHERE episode_date >= ? ORDER BY id DESC LIMIT ?",
            (cutoff, limit)
        ).fetchall()

        all_topics = []
        for row in rows:
            topics = json.loads(row["topics_covered"]) if row["topics_covered"] else []
            all_topics.extend(topics)

        # Count frequency
        from collections import Counter
        freq = Counter(all_topics)
        return {
            "recent_topics": dict(freq.most_common(15)),
            "cold_opens": [row["cold_open_topic"] for row in rows if row["cold_open_topic"]],
            "themes": [row["narrative_theme"] for row in rows if row["narrative_theme"]],
            "episode_count": len(rows),
        }
    finally:
        conn.close()


def get_recent_channels(days=3, limit=5):
    """Get channels featured in the last N days. Clip selector uses this for diversity."""
    conn = _connect()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT channels_featured FROM episode_memory "
            "WHERE episode_date >= ? ORDER BY id DESC LIMIT ?",
            (cutoff, limit)
        ).fetchall()

        all_channels = []
        for row in rows:
            channels = json.loads(row["channels_featured"]) if row["channels_featured"] else []
            all_channels.extend(channels)

        from collections import Counter
        return dict(Counter(all_channels).most_common(20))
    finally:
        conn.close()


def get_editorial_context():
    """Build a context string for SCRIBE's prompt. The key integration point."""
    memory = get_recent_topics(days=3, limit=5)
    channels = get_recent_channels(days=3, limit=5)

    if memory["episode_count"] == 0:
        return ""

    lines = []
    lines.append("EPISODE MEMORY (last 3 days):")

    if memory["recent_topics"]:
        overused = [t for t, c in memory["recent_topics"].items() if c >= 2]
        if overused:
            lines.append(f"  OVERUSED TOPICS (appeared 2+ times recently — avoid leading with these): {', '.join(overused)}")

    if memory["cold_opens"]:
        lines.append(f"  RECENT COLD OPENS (do NOT repeat similar hooks):")
        for co in memory["cold_opens"][:3]:
            lines.append(f"    - {co[:100]}")

    if memory["themes"]:
        lines.append(f"  RECENT THEMES (find a DIFFERENT angle today): {', '.join(memory['themes'][:3])}")

    if channels:
        heavy = [ch for ch, c in channels.items() if c >= 2]
        if heavy:
            lines.append(f"  OVERUSED CHANNELS (featured 2+ times in 3 days — deprioritize): {', '.join(heavy)}")

    lines.append("  RULE: If a topic appeared in the last 2 episodes, do NOT lead with it unless there is a >10% data change.")
    lines.append("  RULE: Find a FRESH angle. Surprise the audience. Do not recycle narratives.")

    return "\n".join(lines)


def get_memory_stats():
    """Dashboard stats for fleet monitoring."""
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) FROM episode_memory").fetchone()[0]
        avg_score = conn.execute(
            "SELECT AVG(quality_score) FROM episode_memory WHERE quality_score IS NOT NULL"
        ).fetchone()[0]
        latest = conn.execute(
            "SELECT episode_date, episode_title, quality_score, grade "
            "FROM episode_memory ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return {
            "total_episodes": total,
            "avg_quality": round(avg_score, 1) if avg_score else 0,
            "latest": dict(latest) if latest else None,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    # Self-test
    print("=== Episode Memory Self-Test ===")

    # Record a test episode
    record_episode(
        episode_date="2026-04-09",
        script={
            "episode_title": "Tariff Shock Meets Bitcoin Resilience",
            "theme": "macro instability drives bitcoin accumulation",
            "dialogue": [
                {"type": "cold_open", "text": "Bitcoin just shrugged off the largest tariff shock in decades."},
                {"type": "setup", "text": "The hashrate continues climbing past 950 exahash."},
                {"type": "react", "text": "Quantum computing threats remain theoretical at best."},
            ]
        },
        clips=[
            {"channel": "Bitcoin_Magazine", "video_id": "abc123"},
            {"channel": "Simply_Bitcoin", "video_id": "def456"},
            {"channel": "TFTC", "video_id": "ghi789"},
        ],
        intel_data={"btc_price": "$83,000", "btc_dominance": 57.0, "fear_greed_value": 17, "hashrate_current": 955},
        quality_score=96,
        grade="A"
    )
    print("  record_episode: PASS")

    # Query recent topics
    topics = get_recent_topics(days=3)
    assert topics["episode_count"] >= 1
    assert "quantum" in topics["recent_topics"]
    print(f"  get_recent_topics: PASS (found {topics['episode_count']} episodes, topics: {list(topics['recent_topics'].keys())[:5]})")

    # Query recent channels
    channels = get_recent_channels(days=3)
    assert "Bitcoin_Magazine" in channels
    print(f"  get_recent_channels: PASS ({channels})")

    # Get editorial context
    ctx = get_editorial_context()
    assert "OVERUSED TOPICS" in ctx or "EPISODE MEMORY" in ctx
    print(f"  get_editorial_context: PASS")
    print(f"\n  Context preview:\n{ctx[:300]}")

    # Stats
    stats = get_memory_stats()
    print(f"\n  Stats: {stats}")

    print("\n=== ALL TESTS PASSED ===")
