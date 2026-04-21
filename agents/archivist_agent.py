#!/usr/bin/env python3
"""archivist_agent.py — The Episode Intelligence Recorder.

Consumes: grade_complete (all grades)

On each grade_complete:
  1. Pull the episode_memory row matching payload.episode_date (channels, topics, narrative,
     btc_price, etc.) — this is the SCRIBE-facing record written by daily_producer.py
  2. Build a structured archive summary {date, score, grade, channels_featured,
     topics_covered, script_sentiment, btc_price_at_render, consecutive_a, output_path}
  3. Append as one JSONL line to agents/state/episode_archive.jsonl
  4. Recompute rolling insights: avg_score_7d, top_performing_topics, channels_overused
  5. Emit archive_updated → broadcast, so other agents get the latest trend deck
  6. Save state {total_episodes, avg_score, best_grade_date, best_score}

Budget: zero LLM calls.
"""
import json
import logging
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from base_agent import BaseAgent
from event_bus import save_state, load_state, log_metric, emit


ARCHIVE_PATH = os.path.join(_AGENT_DIR, "state", "episode_archive.jsonl")
DB_PATH = os.path.join(_AGENT_DIR, "state", "agent_state.db")


def _fetch_episode_memory(episode_date):
    """Fetch the episode_memory row SCRIBE/daily_producer just wrote. May be None."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM episode_memory WHERE episode_date = ? "
            "ORDER BY id DESC LIMIT 1",
            (episode_date,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    return dict(row) if row else None


def _simple_sentiment(text):
    """Cheap lexical sentiment. Positive/negative/neutral tone on a -1..1 axis."""
    if not text:
        return 0.0
    lowered = text.lower()
    bullish = ["bullish", "rally", "breakout", "resilient", "accumulation", "surge",
               "strength", "inflow", "dominance", "record high", "buyer"]
    bearish = ["bearish", "crash", "collapse", "capitulation", "drawdown", "sell-off",
               "weakness", "outflow", "tariff", "recession", "contagion"]
    pos = sum(lowered.count(w) for w in bullish)
    neg = sum(lowered.count(w) for w in bearish)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


def _load_archive_window(days=7):
    """Return list of archive entries from the last N days."""
    if not os.path.exists(ARCHIVE_PATH):
        return []
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    entries = []
    try:
        with open(ARCHIVE_PATH) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("date", "") >= cutoff:
                    entries.append(rec)
    except Exception:
        return []
    return entries


class ArchivistAgent(BaseAgent):
    name = "archivist"
    consumes = ["grade_complete"]

    def handle(self, event):
        payload = event.get("payload", {}) or {}
        episode_date = payload.get("episode_date") or datetime.utcnow().strftime("%Y-%m-%d")
        score = int(payload.get("score", 0) or 0)
        grade = payload.get("grade", "?")
        consecutive_a = int(payload.get("consecutive_a", 0) or 0)
        output_path = payload.get("output_path", "")

        mem = _fetch_episode_memory(episode_date) or {}

        try:
            channels = json.loads(mem.get("channels_featured") or "[]")
        except Exception:
            channels = []
        try:
            topics = json.loads(mem.get("topics_covered") or "[]")
        except Exception:
            topics = []

        cold_open = mem.get("cold_open_topic", "") or ""
        narrative = mem.get("narrative_theme", "") or ""
        script_sentiment = _simple_sentiment(f"{cold_open} {narrative}")

        summary = {
            "date": episode_date,
            "score": score,
            "grade": grade,
            "channels_featured": channels,
            "topics_covered": topics,
            "script_sentiment": script_sentiment,
            "btc_price_at_render": mem.get("btc_price", ""),
            "btc_dominance": mem.get("dominance", ""),
            "fear_greed": mem.get("fear_greed", ""),
            "hashrate": mem.get("hashrate", ""),
            "narrative_theme": narrative,
            "consecutive_a": consecutive_a,
            "output_path": output_path,
            "archived_at": datetime.utcnow().isoformat(timespec="seconds"),
        }

        # 3) Append to JSONL
        try:
            os.makedirs(os.path.dirname(ARCHIVE_PATH), exist_ok=True)
            with open(ARCHIVE_PATH, "a") as fh:
                fh.write(json.dumps(summary, default=str) + "\n")
            self.logger.info(f"archived episode {episode_date} ({grade}, {score}) → {ARCHIVE_PATH}")
        except Exception as exc:
            self.logger.error(f"archive write failed: {exc}")

        # 4) Rolling insights (7-day window)
        window = _load_archive_window(days=7)
        window.append(summary)
        scores = [int(e.get("score", 0) or 0) for e in window]
        avg_score_7d = round(sum(scores) / len(scores), 1) if scores else 0.0

        topic_counter = Counter()
        score_by_topic = {}
        for e in window:
            s = int(e.get("score", 0) or 0)
            for t in e.get("topics_covered", []) or []:
                topic_counter[t] += 1
                score_by_topic.setdefault(t, []).append(s)
        top_performing_topics = sorted(
            (
                (t, round(sum(v) / len(v), 1), len(v))
                for t, v in score_by_topic.items() if len(v) >= 1
            ),
            key=lambda row: (-row[1], -row[2]),
        )[:5]

        channel_counter = Counter()
        for e in window:
            for c in e.get("channels_featured", []) or []:
                channel_counter[c] += 1
        channels_overused = [c for c, n in channel_counter.items() if n >= 3]

        insights = {
            "avg_score_7d": avg_score_7d,
            "episodes_7d": len(window),
            "top_performing_topics": top_performing_topics,
            "channels_overused": channels_overused,
            "latest_grade": grade,
            "latest_score": score,
            "latest_date": episode_date,
        }

        # 5) Broadcast
        emit(self.name, "archive_updated", insights)

        # 6) State + metrics
        prev = load_state(self.name) or {}
        total_episodes = int(prev.get("total_episodes", 0)) + 1
        best_score = max(int(prev.get("best_score", 0)), score)
        best_grade_date = episode_date if score >= int(prev.get("best_score", 0)) \
            else prev.get("best_grade_date", episode_date)

        log_metric(self.name, "avg_score_7d", float(avg_score_7d))
        log_metric(self.name, "episodes_archived", 1, episode_date)

        save_state(
            self.name,
            {
                "total_episodes": total_episodes,
                "avg_score": avg_score_7d,
                "best_grade_date": best_grade_date,
                "best_score": best_score,
                "channels_overused": channels_overused,
                "latest": {"date": episode_date, "grade": grade, "score": score},
            },
            last_action=f"archive_{grade}_{score}",
            self_eval=avg_score_7d / 100.0,
            notes=f"episodes={total_episodes} avg7d={avg_score_7d} overused={channels_overused[:3]}",
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s %(message)s")
    handled = ArchivistAgent().cycle()
    print(f"archivist: {handled} event(s) handled; archive={ARCHIVE_PATH}")
