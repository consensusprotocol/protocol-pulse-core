from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

from services.youtube_service import YouTubeService


KEYWORD_WEIGHTS = {
    "bitcoin": 0.16,
    "etf": 0.20,
    "difficulty": 0.18,
    "mining": 0.16,
    "regulation": 0.20,
    "sec": 0.18,
    "self-custody": 0.20,
    "custody": 0.16,
    "time preference": 0.20,
    "macro": 0.14,
    "liquidity": 0.12,
}

TOPIC_BUCKETS = {
    "etf": ["etf", "flows", "institutional"],
    "regulation": ["regulation", "sec", "ban", "policy", "compliance"],
    "mining": ["mining", "hashrate", "difficulty", "energy"],
    "macro": ["macro", "inflation", "rates", "liquidity", "recession"],
    "self-custody": ["self-custody", "custody", "cold storage", "private key", "seed phrase"],
}

EXPLANATION_CUES = ("because", "means", "here's why", "here is why", "therefore")


def score_segment(text: str, channel: str) -> float:
    text_l = (text or "").lower()
    score = 0.0
    for kw, w in KEYWORD_WEIGHTS.items():
        if kw in text_l:
            score += w

    n_words = len(re.findall(r"\w+", text_l))
    if 8 <= n_words <= 90:
        score += 0.20
    elif n_words < 4 or n_words > 200:
        score -= 0.15

    if any(cue in text_l for cue in EXPLANATION_CUES):
        score += 0.16

    if channel and ("bitcoin" in channel.lower() or "bureau" in channel.lower()):
        score += 0.04

    # Normalize to 0..1
    return max(0.0, min(1.0, score))


def _topic_guess(text: str) -> str:
    t = (text or "").lower()
    for topic, keywords in TOPIC_BUCKETS.items():
        if any(k in t for k in keywords):
            return topic
    return "macro"


def propose_clips_for_video(video: Dict) -> List[Dict]:
    yt = YouTubeService()
    video_id = str(video.get("video_id") or video.get("videoid") or "").strip()
    if not video_id:
        return []
    channel = str(video.get("channel_name") or video.get("channelname") or "unknown").strip()
    title = str(video.get("title") or "untitled").strip()
    segments = yt.get_transcript_segments(video_id)
    if not segments:
        # transcript unavailable fallback clip
        return [
            {
                "video_id": video_id,
                "channel": channel,
                "title": title,
                "start": 30.0,
                "end": 90.0,
                "score": 0.45,
                "topic_guess": _topic_guess(title),
            }
        ]

    candidates: List[Dict] = []
    n = len(segments)
    for i in range(n):
        start = float(segments[i].get("start") or 0.0)
        text_parts = []
        weighted = 0.0
        span_end = start
        for j in range(i, min(i + 45, n)):
            s = segments[j]
            s_start = float(s.get("start") or 0.0)
            s_dur = float(s.get("duration") or 0.0)
            span_end = max(span_end, s_start + s_dur)
            text = str(s.get("text") or "")
            text_parts.append(text)
            weighted += score_segment(text, channel)
            duration = span_end - start
            if duration >= 90:
                break
        duration = span_end - start
        if duration < 30:
            continue
        joined = " ".join(text_parts).strip()
        avg = weighted / max(1, len(text_parts))
        candidates.append(
            {
                "video_id": video_id,
                "channel": channel,
                "title": title,
                "start": round(start, 2),
                "end": round(span_end, 2),
                "score": round(max(0.0, min(1.0, avg)), 3),
                "topic_guess": _topic_guess(joined),
            }
        )

    # Keep top clips per video.
    candidates.sort(key=lambda x: x["score"], reverse=True)
    deduped = []
    for c in candidates:
        overlaps = False
        for d in deduped:
            if d["video_id"] != c["video_id"]:
                continue
            if not (c["end"] <= d["start"] or c["start"] >= d["end"]):
                overlaps = True
                break
        if not overlaps:
            deduped.append(c)
        if len(deduped) >= 6:
            break
    return deduped


def build_story_from_candidates(candidates: List[Dict]) -> List[Dict]:
    if not candidates:
        return []
    by_topic: Dict[str, List[Dict]] = defaultdict(list)
    for c in candidates:
        by_topic[str(c.get("topic_guess") or "macro")].append(c)
    for topic in by_topic:
        by_topic[topic].sort(key=lambda x: x.get("score", 0), reverse=True)

    ordered_topics = ["macro", "etf", "regulation", "mining", "self-custody"]
    chosen: List[Dict] = []
    for topic in ordered_topics:
        picks = by_topic.get(topic) or []
        for clip in picks[:2]:
            chosen.append(dict(clip))
    if not chosen:
        chosen = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)[:4]

    # Keep 3-6 clips
    chosen = chosen[:6]
    if len(chosen) < 3:
        for c in sorted(candidates, key=lambda x: x.get("score", 0), reverse=True):
            if c not in chosen:
                chosen.append(dict(c))
            if len(chosen) >= 3:
                break

    for idx, clip in enumerate(chosen):
        if idx == 0:
            role = "setup"
        elif idx == len(chosen) - 1:
            role = "resolution"
        else:
            role = "deep_dive"
        clip["role"] = role
        clip["topic"] = clip.get("topic_guess", "macro")
    return chosen

