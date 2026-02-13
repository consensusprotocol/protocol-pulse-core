from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from services import ollama_runtime
from services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)

POWER_WORDS = [
    "sovereignty", "breakout", "collapse", "liquidation", "conviction",
    "invalidation", "signal", "alpha", "treasury", "runway",
]


def _topic_from_text(text: str) -> str:
    t = (text or "").lower()
    if "etf" in t or "flows" in t:
        return "etf"
    if "regulation" in t or "sec" in t or "policy" in t:
        return "regulation"
    if "mining" in t or "hashrate" in t or "difficulty" in t:
        return "mining"
    if "custody" in t or "cold storage" in t or "private key" in t:
        return "self-custody"
    return "macro"


def _score_segment(text: str) -> float:
    t = (text or "").lower()
    score = 0.0
    if any(p in t for p in POWER_WORDS):
        score += 0.35
    if re.search(r"\$?\d{2,3}(,\d{3})*(\.\d+)?", t):
        score += 0.2
    if "!" in text or any(c.isupper() for c in text[:12]):
        score += 0.1
    if "because" in t or "here's why" in t or "here is why" in t:
        score += 0.15
    n = len(re.findall(r"\w+", t))
    if 8 <= n <= 65:
        score += 0.2
    return max(0.0, min(1.0, score))


class VideoAnalystService:
    def __init__(self) -> None:
        self.project_root = Path("/home/ultron/protocol_pulse")
        self.ingest_manifest = self.project_root / "data" / "raw_footage_manifest.json"
        self.edit_metadata = self.project_root / "data" / "edit_metadata.json"

    def _transcribe_with_whisper(self, video_path: str) -> List[Dict]:
        try:
            from faster_whisper import WhisperModel
        except Exception:
            return []
        try:
            gpu_idx = int(os.environ.get("MEDLEY_ANALYST_GPU", "0"))
            model = WhisperModel("large-v3", device="cuda", device_index=gpu_idx, compute_type="float16")
            segs, _ = model.transcribe(video_path, beam_size=4, vad_filter=True)
            rows = []
            for seg in segs:
                rows.append({"start": float(seg.start), "end": float(seg.end), "text": str(seg.text or "").strip()})
            return rows
        except Exception:
            logger.exception("whisper transcription failed")
            return []

    def _fallback_transcript(self, video_id: str) -> List[Dict]:
        yt = YouTubeService()
        raw = yt.get_transcript_segments(video_id)
        rows = []
        for r in raw:
            start = float(r.get("start", 0.0) or 0.0)
            duration = float(r.get("duration", 0.0) or 0.0)
            rows.append({"start": start, "end": start + duration, "text": str(r.get("text") or "")})
        return rows

    def _top_moments(self, segments: List[Dict], k: int = 3) -> List[Dict]:
        scored = []
        for s in segments:
            txt = str(s.get("text") or "")
            if not txt.strip():
                continue
            sc = _score_segment(txt)
            scored.append({**s, "score": sc, "topic": _topic_from_text(txt)})
        scored.sort(key=lambda x: x.get("score", 0), reverse=True)
        out = []
        for row in scored:
            start = float(row.get("start", 0.0))
            end = float(row.get("end", start + 18.0))
            # Expand clip for context to increase retention.
            clip_start = max(0.0, start - 3.0)
            clip_end = max(clip_start + 16.0, end + 4.0)
            overlap = False
            for o in out:
                if not (clip_end <= o["start"] or clip_start >= o["end"]):
                    overlap = True
                    break
            if overlap:
                continue
            out.append(
                {
                    "start": round(clip_start, 2),
                    "end": round(min(clip_end, clip_start + 60.0), 2),
                    "score": round(float(row.get("score", 0)), 3),
                    "topic": row.get("topic", "macro"),
                    "text": row.get("text", "")[:260],
                }
            )
            if len(out) >= k:
                break
        # Assign story roles.
        for idx, row in enumerate(out):
            row["role"] = "hook" if idx == 0 else ("outro" if idx == len(out) - 1 else "meat")
        return out

    def _llm_refine(self, title: str, clips: List[Dict]) -> List[Dict]:
        if not clips:
            return clips
        prompt = (
            "you are a retention editor. keep best 3 moments ordered as hook, meat, outro.\n"
            "respond in json array with objects {index:int, role:string}.\n"
            f"title={title}\nclips={json.dumps(clips, ensure_ascii=True)}"
        )
        raw = ollama_runtime.generate(prompt, preferred_model="llama3.1", options={"temperature": 0.2, "num_predict": 140}, timeout=8)
        if not raw:
            return clips
        try:
            plan = json.loads(raw)
            if isinstance(plan, list):
                reordered = []
                for item in plan:
                    idx = int(item.get("index", -1))
                    if 0 <= idx < len(clips):
                        row = dict(clips[idx])
                        role = str(item.get("role") or row.get("role") or "meat")
                        row["role"] = role
                        reordered.append(row)
                if reordered:
                    return reordered[:3]
        except Exception:
            pass
        return clips

    def run(self) -> Dict:
        if not self.ingest_manifest.exists():
            return {"ok": False, "error": "ingest manifest missing"}
        payload = json.loads(self.ingest_manifest.read_text(encoding="utf-8"))
        videos = payload.get("videos") or []
        analyzed = []
        by_topic = defaultdict(int)

        for v in videos:
            vid = str(v.get("video_id") or "").strip()
            path = str(v.get("local_video_path") or "").strip()
            title = str(v.get("title") or "untitled")
            if not vid or not path:
                continue
            segs = self._transcribe_with_whisper(path)
            if not segs:
                segs = self._fallback_transcript(vid)
            moments = self._top_moments(segs, k=3)
            if not moments:
                moments = [
                    {"start": 8.0, "end": 42.0, "score": 0.55, "topic": _topic_from_text(title), "text": title, "role": "hook"},
                    {"start": 44.0, "end": 78.0, "score": 0.52, "topic": _topic_from_text(title), "text": title, "role": "meat"},
                    {"start": 80.0, "end": 110.0, "score": 0.5, "topic": _topic_from_text(title), "text": title, "role": "outro"},
                ]
            moments = self._llm_refine(title, moments)
            for m in moments:
                by_topic[m.get("topic", "macro")] += 1
            analyzed.append(
                {
                    "video_id": vid,
                    "channel": v.get("channel_name"),
                    "title": title,
                    "local_video_path": path,
                    "moments": moments,
                }
            )

        edit = {
            "ts": datetime.utcnow().isoformat(),
            "videos_analyzed": len(analyzed),
            "topic_histogram": dict(by_topic),
            "clips": [
                {
                    "video_id": row["video_id"],
                    "channel": row["channel"],
                    "video_title": row["title"],
                    "source_video": row["local_video_path"],
                    "start": m["start"],
                    "end": m["end"],
                    "role": m.get("role", "meat"),
                    "topic": m.get("topic", "macro"),
                    "score": m.get("score", 0),
                    "transcript": m.get("text", ""),
                }
                for row in analyzed
                for m in (row.get("moments") or [])
            ],
        }
        self.edit_metadata.write_text(json.dumps(edit, ensure_ascii=True, indent=2), encoding="utf-8")
        return {"ok": True, **edit}


video_analyst_service = VideoAnalystService()

