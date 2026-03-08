#!/usr/bin/env python3
"""
spaces_pipeline.py — X Spaces -> Video Pipeline bridge.
Reads recent high-impact Space chunks from data/spaces/
and returns formatted segment data for injection into episode.

V2: Enforces transcript source truth, quality gates, speaker attribution.
"""
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPACES_DATA = os.path.join(BASE, "data", "spaces")
X_SCRAPER_CACHE = os.path.join(BASE, "..", "x_spaces_scraper", "cache")


def get_latest_spaces_segment(max_age_hours=4):
    """
    Return the most recent high-impact X Space as a video segment dict.
    Returns None if no fresh spaces available.

    V2 rules:
    - Only audio_replay/live_capture sources produce narration-grade text
    - context_only requires impact_score >= 75 to inject
    - Speaker attribution included when segments available
    """
    best_chunk = None
    best_score = 0
    best_source = None

    for cache_dir in [X_SCRAPER_CACHE, SPACES_DATA]:
        if not os.path.exists(cache_dir):
            continue

        # Check JSON files
        for item in Path(cache_dir).rglob("*.json"):
            try:
                age = time.time() - item.stat().st_mtime
                if age > max_age_hours * 3600:
                    continue
                with open(item) as f:
                    data = json.load(f)
                score = data.get("impact_score", 0) or data.get("score", 0)
                source = data.get("source", data.get("transcript_source", ""))

                # context_only needs higher bar
                if source == "context_only" and score < 75:
                    continue
                # Check usable flag if present
                if "usable" in data and not data["usable"] and source != "context_only":
                    continue

                if score > best_score:
                    best_score = score
                    best_chunk = data
                    best_source = source
            except (json.JSONDecodeError, OSError):
                continue

        # Check chunks.jsonl files
        for chunks_file in Path(cache_dir).rglob("chunks.jsonl"):
            try:
                if time.time() - chunks_file.stat().st_mtime > max_age_hours * 3600:
                    continue
                with open(chunks_file) as f:
                    for line in f:
                        try:
                            chunk = json.loads(line.strip())
                            score = chunk.get("impact_score", 0)
                            source = chunk.get("source", "")
                            if source == "context_only" and score < 75:
                                continue
                            if score > best_score:
                                best_score = score
                                best_chunk = chunk
                                best_source = source
                        except json.JSONDecodeError:
                            continue
            except OSError:
                continue

    if not best_chunk or best_score < 40:
        return None

    # Build narrator script from chunk text
    space_title = best_chunk.get("title", best_chunk.get("space_title", "X Space"))
    host = best_chunk.get("speaker", best_chunk.get("host", "Bitcoin Community"))
    text = best_chunk.get("text", best_chunk.get("transcript", ""))
    segments = best_chunk.get("segments", [])
    impact_score = best_score
    is_context_only = best_source == "context_only"

    # Speaker-attributed narration for audio-derived transcripts
    if not is_context_only and segments and any(s.get("speaker") for s in segments):
        host_lines = [s["text"] for s in segments if s.get("speaker") == "HOST"]
        if host_lines:
            top_quote = max(host_lines, key=len)[:200]
            narrator_script = (
                f"On X Spaces, {host} is hosting: {space_title}. "
                f"The host stated: {top_quote}. "
                f"Protocol Pulse classified this as {impact_score} impact intelligence."
            )
        else:
            narrator_script = (
                f"On X Spaces, {host} is hosting a discussion: {space_title}. "
                f"Here are the key takeaways: {text[:300]}. "
                f"This is a live intelligence signal from Protocol Pulse."
            )
    elif is_context_only:
        narrator_script = (
            f"X Spaces context alert: {host} hosted {space_title}. "
            f"This is context-level intelligence — full transcript unavailable. "
            f"Protocol Pulse rates this {impact_score} impact."
        )
    else:
        narrator_script = (
            f"On X Spaces, {host} is hosting a discussion: {space_title}. "
            f"Here are the key takeaways: {text[:300]}. "
            f"This is a live intelligence signal from Protocol Pulse."
        )

    result = {
        "type": "x_spaces",
        "headline": "X SPACES // LIVE INTEL",
        "kicker": "LIVE X SPACES SIGNAL",
        "tag": "INTEL",
        "text": narrator_script,
        "source": "x_spaces",
        "transcript_source": best_source or "unknown",
        "space_title": space_title,
        "space_host": host,
        "impact_score": impact_score,
    }

    if is_context_only:
        result["context_only_segment"] = True
        result["tag"] = "CONTEXT INTEL"
        result["kicker"] = "LIVE INTEL — CONTEXT ONLY"

    return result


if __name__ == "__main__":
    seg = get_latest_spaces_segment()
    print("SPACES SEGMENT:", json.dumps(seg, indent=2) if seg else "None")
