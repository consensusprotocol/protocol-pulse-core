from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app, db
import models
from services.youtube_service import YouTubeService
from services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


@dataclass
class ViralMoment:
    start: float
    end: float
    context: str
    narrative: str = ""


class TranscriptAPI:
    """Transcript fetcher with local GPU fallback (faster-whisper)."""

    def __init__(self) -> None:
        self.project_root = Path("/home/ultron/protocol_pulse")

    def _video_id_from_url(self, url: str) -> Optional[str]:
        u = (url or "").strip()
        if not u:
            return None
        m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", u)
        return m.group(1) if m else None

    def _local_fallback_path(self, url: str) -> Optional[Path]:
        """Map known partner URLs to local cached/fallback MP4 when available."""
        u = (url or "").lower()
        # This repo already stores fallback partner MP4s under data/raw_footage/YYYY-MM-DD.
        if "natalie" in u or "brunell" in u:
            candidates = sorted((self.project_root / "data" / "raw_footage").glob("**/natalie_brunell_fallback_*.mp4"))
            return candidates[-1] if candidates else None
        # If a fallback video_id is provided via a YouTube-style URL, resolve via manifest.
        m = re.search(r"(fallback_\d{4}-\d{2}-\d{2}_\d+)", u)
        if m:
            vid = m.group(1)
            manifest = self.project_root / "data" / "raw_footage_manifest.json"
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
                for row in (payload.get("videos") or []):
                    if str(row.get("video_id")) == vid:
                        p = Path(str(row.get("local_video_path") or ""))
                        return p if p.exists() else None
            except Exception:
                return None
        return None

    def get_transcript_segments(self, url_or_video_id: str) -> List[Dict]:
        """Return [{start,end,text}] segments. Never raises."""
        # Prefer YouTube transcript API via YouTubeService if available.
        try:
            yt = YouTubeService()
            vid = url_or_video_id
            if "http" in (url_or_video_id or ""):
                vid = self._video_id_from_url(url_or_video_id) or url_or_video_id
            rows = yt.get_transcript_segments(str(vid))
            if rows:
                out = []
                for r in rows:
                    start = float(r.get("start", 0.0) or 0.0)
                    duration = float(r.get("duration", 0.0) or 0.0)
                    out.append({"start": start, "end": start + duration, "text": str(r.get("text") or "").strip()})
                if out:
                    return out
        except Exception:
            pass

        # GPU local transcription fallback (faster-whisper) against a local MP4 if we have one.
        local_path = None
        if isinstance(url_or_video_id, str) and url_or_video_id.strip().startswith("/"):
            local_path = Path(url_or_video_id.strip())
        else:
            local_path = self._local_fallback_path(url_or_video_id)
        if not local_path or not local_path.exists():
            logger.warning("TranscriptAPI: no transcript and no local fallback asset for %s", url_or_video_id)
            return []

        try:
            from faster_whisper import WhisperModel
        except Exception as e:
            logger.error("TranscriptAPI: faster-whisper unavailable: %s", e)
            return []

        try:
            gpu_idx = int(os.environ.get("VIRAL_AGENT_GPU", "0"))
            model_size = os.environ.get("VIRAL_AGENT_WHISPER_MODEL", "large-v3")
            try:
                model = WhisperModel(model_size, device="cuda", device_index=gpu_idx, compute_type="float16")
                segs, _ = model.transcribe(str(local_path), beam_size=4, vad_filter=True)
            except Exception as gpu_exc:
                # CUDA libs may not be present even on GPU boxes; fall back to CPU to avoid hard failure.
                logger.warning("TranscriptAPI: GPU whisper failed, falling back to CPU: %s", gpu_exc)
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                segs, _ = model.transcribe(str(local_path), beam_size=2, vad_filter=True)
            out = []
            for seg in segs:
                out.append({"start": float(seg.start), "end": float(seg.end), "text": str(seg.text or "").strip()})
            return out
        except Exception as e:
            logger.exception("TranscriptAPI: whisper transcription failed: %s", e)
            return []


def _score_segment(text: str) -> float:
    t = (text or "").lower()
    score = 0.0
    if any(k in t for k in ("sovereignty", "hashrate", "mempool", "liquidity", "treasury", "etf", "flows", "macro")):
        score += 0.35
    if re.search(r"\$?\d{2,3}(,\d{3})*(\.\d+)?", t):
        score += 0.2
    n = len(re.findall(r"\w+", t))
    if 8 <= n <= 70:
        score += 0.25
    if "here's why" in t or "here is why" in t or "because" in t:
        score += 0.2
    return max(0.0, min(1.0, score))


class PartnerWatcher:
    """PartnerWatcher skill: scan RSS and create ClipJob plans."""

    def __init__(self) -> None:
        self.transcript_api = TranscriptAPI()
        self.youtube = YouTubeService()

    def _gemini_viral_moments(self, transcript: str) -> Tuple[List[ViralMoment], str]:
        if not getattr(gemini_service, "client", None):
            return [], ""
        prompt = (
            "You are Protocol Pulse's viral clip editor.\n"
            "From the transcript, identify 3 to 5 viral moments suitable for vertical shorts.\n"
            "Return STRICT JSON with keys:\n"
            "moments: [{start: number, end: number, context: string, narrative: string}],\n"
            "intro: string (two sentences, Bloomberg-style).\n\n"
            f"TRANSCRIPT:\n{transcript[:12000]}\n"
        )
        try:
            # Prefer pro model if available.
            model_id = getattr(gemini_service, "pro_model", None) or getattr(gemini_service, "text_model", None)
            if not model_id:
                return [], ""
            from google.genai import types  # type: ignore
            resp = gemini_service.client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.25,
                    max_output_tokens=900,
                    response_mime_type="application/json",
                ),
            )
            raw = resp.text or ""
            payload = json.loads(raw)
            moments = []
            for m in (payload.get("moments") or [])[:5]:
                moments.append(
                    ViralMoment(
                        start=float(m.get("start", 0.0) or 0.0),
                        end=float(m.get("end", 0.0) or 0.0),
                        context=str(m.get("context") or "").strip(),
                        narrative=str(m.get("narrative") or "").strip(),
                    )
                )
            intro = str(payload.get("intro") or "").strip()
            return moments, intro
        except Exception as e:
            logger.warning("Gemini viral moments failed: %s", e)
            return [], ""

    def _heuristic_viral_moments(self, segments: List[Dict]) -> Tuple[List[ViralMoment], str]:
        scored = []
        for s in segments:
            txt = str(s.get("text") or "").strip()
            if not txt:
                continue
            scored.append(
                {
                    "start": float(s.get("start", 0.0) or 0.0),
                    "end": float(s.get("end", 0.0) or 0.0),
                    "text": txt,
                    "score": _score_segment(txt),
                }
            )
        scored.sort(key=lambda r: r.get("score", 0), reverse=True)
        moments: List[ViralMoment] = []
        for row in scored:
            start = max(0.0, float(row["start"]) - 2.5)
            end = max(start + 18.0, float(row["end"]) + 3.5)
            # avoid overlap
            if any(not (end <= m.start or start >= m.end) for m in moments):
                continue
            moments.append(ViralMoment(start=round(start, 2), end=round(min(end, start + 55.0), 2), context=row["text"][:240]))
            if len(moments) >= 3:
                break
        intro = (
            "Bitcoin narratives are shifting as macro headlines collide with on-chain reality, tightening the window for clean reads. "
            "Protocol Pulse isolates the segments where the signal compresses into actionable context for allocators."
        )
        return moments, intro

    def plan_clip_job(self, *, video_url: str, video_id: Optional[str] = None) -> Dict:
        vid = video_id or self.transcript_api._video_id_from_url(video_url) or video_url
        segs = self.transcript_api.get_transcript_segments(video_url)
        transcript = " ".join([str(s.get("text") or "") for s in segs]) if segs else ""

        def _probe_duration_seconds(path: Path) -> float:
            import subprocess
            try:
                proc = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                if proc.returncode != 0:
                    return 0.0
                return float((proc.stdout or "").strip() or 0.0)
            except Exception:
                return 0.0

        moments, intro = self._gemini_viral_moments(transcript) if transcript else ([], "")
        if not moments:
            moments, intro = self._heuristic_viral_moments(segs)

        # If we still have nothing (silent/corrupt transcript), create deterministic windows from duration.
        if not moments:
            local_path = self.transcript_api._local_fallback_path(video_url)
            dur = _probe_duration_seconds(local_path) if local_path and local_path.exists() else 0.0
            if dur > 0:
                base = [0.0, max(5.0, dur * 0.25), max(10.0, dur * 0.55)]
                windows: List[ViralMoment] = []
                for start in base:
                    end = min(dur, start + 22.0)
                    if end - start < 8:
                        continue
                    windows.append(ViralMoment(start=round(start, 2), end=round(end, 2), context="(transcript unavailable)"))
                if windows:
                    moments = windows[:5]
                    intro = (
                        "Protocol Pulse flagged timing windows after a transcript-degraded capture, keeping the cut list moving without stalling the bureau. "
                        "These segments are structured for a fast re-rank once clean speech is available, preserving a Bloomberg-style pacing for Bitcoin coverage."
                    )

        if not moments:
            return {"ok": False, "error": "no transcript/moments", "video_id": vid}

        timestamps_payload = [asdict(m) for m in moments]
        narrative_context = (intro.strip() + "\n\n" + "\n".join([f"- {m.start:.2f}-{m.end:.2f}s: {m.context}" for m in moments])).strip()

        with app.app_context():
            row = models.ClipJob(
                video_id=str(vid),
                timestamps_json=json.dumps(timestamps_payload, ensure_ascii=True),
                narrative_context=narrative_context,
                status="Planned",
            )
            db.session.add(row)
            db.session.commit()
            return {"ok": True, "job_id": row.id, "video_id": row.video_id, "moment_count": len(moments)}

    def scan_partner_feeds_once(self) -> Dict:
        channel_ids = [c.strip() for c in (os.environ.get("PARTNER_YOUTUBE_CHANNEL_IDS") or "").split(",") if c.strip()]
        if not channel_ids:
            # Safe default: no-op unless configured.
            return {"ok": True, "scanned": 0, "planned": 0, "detail": "PARTNER_YOUTUBE_CHANNEL_IDS not set"}
        planned = 0
        scanned = 0
        for cid in channel_ids:
            videos = self.youtube.get_channel_uploads(cid, max_results=2)
            for v in videos:
                scanned += 1
                vid = v.get("id")
                if not vid:
                    continue
                url = f"https://www.youtube.com/watch?v={vid}"
                out = self.plan_clip_job(video_url=url, video_id=str(vid))
                if out.get("ok"):
                    planned += 1
        return {"ok": True, "scanned": scanned, "planned": planned}

    def run_daemon(self, interval_seconds: int = 1800) -> None:
        logger.info("PartnerWatcher daemon online interval=%ss", interval_seconds)
        while True:
            try:
                out = self.scan_partner_feeds_once()
                logger.info("PartnerWatcher scan: %s", out)
            except Exception as e:
                logger.exception("PartnerWatcher scan failed: %s", e)
            time.sleep(max(60, int(interval_seconds)))


partner_watcher = PartnerWatcher()


def openclaw_skill_manifest() -> Dict:
    """Minimal manifest OpenClaw can reference (tooling expects a skill definition)."""
    return {
        "name": "PartnerWatcher",
        "version": "1.0",
        "schedule": "*/30 * * * *",
        "entrypoint": "services.viral_agent:partner_watcher.scan_partner_feeds_once",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PartnerWatcher manual trigger")
    parser.add_argument("--url", required=True, help="YouTube URL (or local fallback key)")
    args = parser.parse_args()
    result = partner_watcher.plan_clip_job(video_url=args.url)
    print(json.dumps(result, ensure_ascii=True, indent=2))

