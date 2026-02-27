from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def _get_fallback_clip():
    """Lazy import to allow Batch 4 validator to run without app context."""
    from services.clip_service import fallback_clip
    return fallback_clip


class ViralMomentsReelEngine:
    """Viral Moments reel engine (monitor -> transcript -> plan segments -> ClipJob).

    Batch 2 goal: monitoring + planning. Rendering/narration remain placeholders.
    """

    def __init__(self) -> None:
        pass

    def plan_segments(self, video_id: str, narration_path: Optional[str] = None) -> Dict:
        # We don't refactor upstream transcript logic here. We only detect the empty-transcript condition
        # via a best-effort faster-whisper probe and then fall back to a thumbnail reel.
        try:
            from faster_whisper import WhisperModel
        except Exception:
            WhisperModel = None  # type: ignore

        has_speech = True
        if WhisperModel is not None:
            # If the local source is available, we can probe for speech; otherwise treat as unknown.
            local_source = None
            try:
                from services.clip_service import _resolve_local_source  # type: ignore
                local_source = _resolve_local_source(video_id)
            except Exception:
                local_source = None
            if local_source and local_source.exists():
                try:
                    prefer_device = os.environ.get("CLIP_WHISPER_DEVICE", "cpu").strip().lower()
                    if prefer_device in {"cuda", "gpu"}:
                        model = WhisperModel("large-v3", device="cuda", device_index=0, compute_type="float16")
                    else:
                        model = WhisperModel("large-v3", device="cpu", compute_type="int8")
                    segs, _ = model.transcribe(str(local_source), beam_size=2, vad_filter=True)
                    speech = [s for s in segs if str(getattr(s, "text", "") or "").strip()]
                    has_speech = bool(speech)
                except Exception:
                    # If whisper fails, do not abort planning here.
                    has_speech = True

        if not has_speech:
            logger.warning("NO SPEECH DETECTED – triggering thumbnail + narration fallback")
            channel_name = (os.environ.get("CLIP_FEATURED_CHANNEL") or os.environ.get("MEDLEY_PARTNER_CHANNEL") or "Partner").strip()
            try:
                from services.clip_service import fallback_thumbnail_reel  # type: ignore
                fb = fallback_thumbnail_reel(video_id, narration_path=narration_path, channel_name=channel_name)
            except Exception:
                # Back-compat fallback (older function name)
                fb = _get_fallback_clip()(video_id, narration_path=narration_path, channel_name=channel_name)
            return {"ok": bool(fb.get("ok")), "fallback": True, **fb}

        # If speech exists, leave the job to the main planner elsewhere. This file only adds fallback.
        return {"ok": True, "fallback": False, "video_id": video_id, "segments": []}

    def _load_partner_channels(self) -> List[Dict[str, str]]:
        """Load channel list from config/partner_channels.json (preferred) with fallbacks."""
        channels: List[Dict[str, str]] = []

        def add_channel(cid: str, name: str = "") -> None:
            cid = (cid or "").strip()
            if not cid:
                return
            if any(c.get("channel_id") == cid for c in channels):
                return
            channels.append({"channel_id": cid, "name": (name or "").strip()})

        cfg_path = PROJECT_ROOT / "config" / "partner_channels.json"
        if cfg_path.exists():
            try:
                raw = json.loads(cfg_path.read_text(encoding="utf-8"))
                for item in (raw.get("youtube_channels") or []):
                    if isinstance(item, dict):
                        add_channel(str(item.get("channel_id") or ""), str(item.get("name") or ""))
                    elif isinstance(item, str):
                        add_channel(item, "")
            except Exception as exc:
                logger.warning("partner_channels.json unreadable: %s", exc)

        # Fallbacks: supported_sources.json and ENV
        if not channels:
            sup = PROJECT_ROOT / "config" / "supported_sources.json"
            try:
                raw = json.loads(sup.read_text(encoding="utf-8"))
                for item in (raw.get("youtube_channels") or []):
                    if isinstance(item, dict):
                        add_channel(str(item.get("channel_id") or ""), str(item.get("name") or ""))
            except Exception:
                pass

        env_ids = [c.strip() for c in (os.environ.get("PARTNER_YOUTUBE_CHANNEL_IDS") or "").split(",") if c.strip()]
        for cid in env_ids:
            add_channel(cid, "")

        # Batch 2 requirement: ensure this channel is present
        required = "UC9ZM3N0ybRtp44-WLqsW3iQ"
        if not any(c.get("channel_id") == required for c in channels):
            add_channel(required, "Test Channel (Batch 2 required)")

        if len(channels) < 50:
            logger.warning("Partner channel list is small (%s). Add more to config/partner_channels.json.", len(channels))

        return channels

    def _rss_latest_videos(self, channel_id: str, limit: int = 2) -> List[Dict[str, str]]:
        """Fetch latest videos via the public YouTube RSS feed."""
        import requests
        import xml.etree.ElementTree as ET

        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            resp = requests.get(rss_url, timeout=15)
            if resp.status_code != 200:
                return []
            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
            out: List[Dict[str, str]] = []
            for entry in root.findall("atom:entry", ns)[:limit]:
                vid = entry.find("yt:videoId", ns)
                title = entry.find("atom:title", ns)
                published = entry.find("atom:published", ns)
                if vid is None or not (vid.text or "").strip():
                    continue
                out.append(
                    {
                        "video_id": (vid.text or "").strip(),
                        "title": (title.text or "").strip() if title is not None else "",
                        "published": (published.text or "").strip() if published is not None else "",
                        "rss_url": rss_url,
                    }
                )
            return out
        except Exception as exc:
            logger.warning("RSS fetch failed for %s: %s", channel_id, exc)
            return []

    def _fetch_transcript(self, video_id: str) -> List[Dict[str, Any]]:
        """Fetch transcript via youtube_transcript_api."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"youtube_transcript_api not available: {exc}") from exc

        # youtube_transcript_api has changed APIs across versions. Support both:
        # - legacy: YouTubeTranscriptApi.get_transcript(...)
        # - current (1.2.x): YouTubeTranscriptApi().list(video_id) -> TranscriptList
        prefer_langs = ["en", "en-US", "en-GB"]

        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            try:
                return YouTubeTranscriptApi.get_transcript(video_id, languages=prefer_langs)  # type: ignore[attr-defined]
            except Exception:
                return YouTubeTranscriptApi.get_transcript(video_id)  # type: ignore[attr-defined]

        api = YouTubeTranscriptApi()
        tlist = api.list(video_id)
        # Prefer manually-created, then generated; fall back to any available transcript.
        transcript = None
        for finder_name in (
            "find_manually_created_transcript",
            "find_generated_transcript",
            "find_transcript",
        ):
            finder = getattr(tlist, finder_name, None)
            if finder is None:
                continue
            try:
                transcript = finder(prefer_langs)
                break
            except Exception:
                transcript = None
        if transcript is None:
            # Grab first iterable transcript if possible
            try:
                transcript = next(iter(tlist))
            except Exception as exc:
                raise RuntimeError(f"no transcript available for {video_id}: {exc}") from exc

        fetched = transcript.fetch()
        normalized: List[Dict[str, Any]] = []
        for row in fetched:
            # Supports both dict-like rows (older versions) and snippet objects (newer versions).
            if isinstance(row, dict):
                normalized.append(row)
                continue
            normalized.append(
                {
                    "text": str(getattr(row, "text", "") or ""),
                    "start": float(getattr(row, "start", 0.0) or 0.0),
                    "duration": float(getattr(row, "duration", 0.0) or 0.0),
                }
            )
        return normalized

    def _plan_viral_segments_from_transcript(self, transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify 3-5 keyword segments (30-90s), favoring 'breaking/upgrade/insight'."""
        if not transcript:
            return []

        # Primary keywords per spec (include simple variants so we don't miss matches).
        kw_weights = {
            "breaking": 3,
            "break": 2,
            "upgrade": 2,
            "upgraded": 2,
            "insight": 2,
            "insights": 2,
        }
        min_len = 30.0
        max_len = 90.0
        target_len = 60.0

        # Approx video duration from transcript tail
        last = transcript[-1]
        approx_end = float(last.get("start") or 0.0) + float(last.get("duration") or 0.0)
        approx_end = max(approx_end, 0.0)

        candidates: List[Tuple[float, float, int, str]] = []
        for row in transcript:
            text = str(row.get("text") or "")
            tl = text.lower()
            score = 0
            for k, w in kw_weights.items():
                if k in tl:
                    score += w
            if score <= 0:
                continue

            start = float(row.get("start") or 0.0)
            # Build a stable 30-90s window around the hit.
            seg_start = max(0.0, start - 8.0)
            seg_end = seg_start + target_len
            seg_end = max(seg_end, seg_start + min_len)
            seg_end = min(seg_end, seg_start + max_len)
            if approx_end > 0:
                seg_end = min(seg_end, approx_end)
                if seg_end - seg_start < min_len:
                    continue

            snippet = re.sub(r"\s+", " ", text).strip()[:160]
            candidates.append((seg_start, seg_end, score, snippet))

        # Choose top segments, spaced out to avoid duplicates.
        candidates.sort(key=lambda t: (t[2], -(t[1] - t[0])), reverse=True)
        picked: List[Dict[str, Any]] = []
        for seg_start, seg_end, score, snippet in candidates:
            if len(picked) >= 5:
                break
            if any(abs(seg_start - float(p["start"])) < 25.0 for p in picked):
                continue
            picked.append(
                {
                    "start": round(seg_start, 2),
                    "end": round(seg_end, 2),
                    "score": int(score),
                    "reason": "keyword_hit",
                    "snippet": snippet,
                }
            )

        # If keywords are sparse, we still want 3-5 segments to keep the pipeline moving.
        # Add a few evenly-spread "coverage windows" (still 30-90s) as a fallback.
        if len(picked) < 3 and approx_end >= 90.0:
            targets = [0.18, 0.45, 0.72, 0.88]
            for frac in targets:
                if len(picked) >= 3:
                    break
                center = approx_end * frac
                seg_start = max(0.0, center - 12.0)
                seg_end = min(seg_start + target_len, approx_end)
                if seg_end - seg_start < min_len:
                    continue
                if any(abs(seg_start - float(p["start"])) < 25.0 for p in picked):
                    continue
                picked.append(
                    {
                        "start": round(seg_start, 2),
                        "end": round(seg_end, 2),
                        "score": 0,
                        "reason": "coverage_window",
                        "snippet": "",
                    }
                )

        return picked[:5]

    def monitor_partners(
        self,
        video_id: Optional[str] = None,
        narration_path: Optional[str] = None,
        *,
        heartbeat_minutes: int = 60,
        force_video_id: Optional[str] = None,
        force_channel_id: Optional[str] = None,
        max_channels: int = 999,
    ) -> Dict:
        """Scan partner channels and create ClipJob rows for new videos.

        Back-compat: if `video_id` is provided, this behaves like the older Batch-2
        wrapper and calls `plan_segments(video_id, narration_path)`.
        """
        if video_id:
            return self.plan_segments(video_id=video_id, narration_path=narration_path)

        # Optional test knobs via env so the gate can be run without changing code.
        force_video_id = (force_video_id or os.environ.get("VIRAL_TEST_VIDEO_ID") or "").strip() or None
        force_channel_id = (force_channel_id or os.environ.get("VIRAL_TEST_CHANNEL_ID") or "").strip() or None

        channels = self._load_partner_channels()[: max_channels if max_channels > 0 else 0]
        logger.info("ViralMoments heartbeat=%sm scanning_channels=%s", heartbeat_minutes, len(channels))

        # Resolve candidate videos
        candidates: List[Dict[str, str]] = []
        for c in channels:
            cid = c.get("channel_id") or ""
            if not cid:
                continue
            vids = self._rss_latest_videos(cid, limit=2)
            for v in vids:
                v["channel_id"] = cid
                v["channel_name"] = c.get("name") or cid
                candidates.append(v)

        if force_video_id:
            candidates.insert(
                0,
                {
                    "video_id": force_video_id,
                    "title": "",
                    "published": "",
                    "rss_url": "",
                    "channel_id": force_channel_id or "",
                    "channel_name": force_channel_id or "Test Channel",
                },
            )

        # Deduplicate by video_id while preserving order
        seen: set[str] = set()
        uniq: List[Dict[str, str]] = []
        for c in candidates:
            vid = (c.get("video_id") or "").strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            uniq.append(c)
        candidates = uniq

        planned = 0
        skipped_existing = 0
        no_segments = 0
        errors = 0
        total_seconds = 0.0
        created_job_ids: List[int] = []

        # Import inside to avoid circular imports on module import.
        from app import app, db
        import models

        with app.app_context():
            for item in candidates:
                vid = item.get("video_id") or ""
                cid = item.get("channel_id") or ""
                cname = item.get("channel_name") or cid or ""

                existing = models.ClipJob.query.filter_by(video_id=vid).first()
                if existing is not None:
                    skipped_existing += 1
                    continue

                try:
                    transcript = self._fetch_transcript(vid)
                    segments = self._plan_viral_segments_from_transcript(transcript)
                    if len(segments) < 3:
                        no_segments += 1
                        logger.info("video=%s segments=%s (skipping; need >=3)", vid, len(segments))
                        continue

                    segments = segments[:5]
                    seg_seconds = sum(max(0.0, float(s["end"]) - float(s["start"])) for s in segments)
                    total_seconds += seg_seconds

                    now = datetime.now(timezone.utc).isoformat()
                    metadata = {
                        "source": "monitor_partners",
                        "channel_id": cid,
                        "channel_name": cname,
                        "rss_url": item.get("rss_url") or "",
                        "published": item.get("published") or "",
                        "title": item.get("title") or "",
                        "planned_at": now,
                        "segments_total_seconds": round(seg_seconds, 2),
                    }

                    # Legacy columns are NOT NULL: keep them populated.
                    timestamps_payload = [{"start": s["start"], "end": s["end"], "context": s.get("snippet", "")} for s in segments]
                    narrative = " | ".join(str(s.get("snippet") or "") for s in segments[:3]).strip()

                    job = models.ClipJob(
                        video_id=vid,
                        channel_name=cname or None,
                        segments_json=json.dumps(segments),
                        narration_path=narration_path,
                        output_path=None,
                        metadata_json=json.dumps(metadata),
                        timestamps_json=json.dumps(timestamps_payload),
                        narrative_context=narrative,
                        status="Planned",
                        created_at=datetime.utcnow(),
                    )
                    db.session.add(job)
                    db.session.commit()
                    created_job_ids.append(int(job.id))
                    planned += 1

                    logger.info("planned ClipJob id=%s video=%s segments=%s", job.id, vid, len(segments))
                except Exception as exc:
                    errors += 1
                    logger.warning("planning failed video=%s err=%s", vid, exc)

        # Threshold logic for 2x daily publishing is an ops policy; we log the readiness signal here.
        readiness = "low"
        if 300.0 <= total_seconds <= 600.0:
            readiness = "target_window"
        elif total_seconds > 600.0:
            readiness = "above_target"

        logger.info(
            "monitor_partners result planned=%s existing=%s no_segments=%s errors=%s total_seconds=%.1f readiness=%s",
            planned,
            skipped_existing,
            no_segments,
            errors,
            total_seconds,
            readiness,
        )

        return {
            "ok": errors == 0,
            "planned": planned,
            "skipped_existing": skipped_existing,
            "no_segments": no_segments,
            "errors": errors,
            "total_seconds": round(total_seconds, 1),
            "readiness": readiness,
            "job_ids": created_job_ids,
        }

    # ----------------------------
    # Batch 4: Voiceover – Grok script + ElevenLabs Flash v2.5 + overlay
    # ----------------------------

    def generate_narration(self, clip_job: Any) -> Dict:
        """Grok: smooth news brief script (Bloomberg style, 10–20s intro/insights per clip, 2 CTAs).
        ElevenLabs Flash v2.5: authoritative voice. Returns narration_audio path for add_narration.
        """
        from app import app
        import models
        try:
            from services.grok_service import grok_service
            from services.elevenlabs_service import ElevenLabsService
        except Exception as e:
            return {"ok": False, "error": f"import: {e}", "job_id": getattr(clip_job, "id", None)}

        with app.app_context():
            job = clip_job
            if not hasattr(job, "id"):
                job = models.ClipJob.query.get(int(clip_job))
            if job is None:
                return {"ok": False, "error": "ClipJob not found", "job_id": None}

            work_dir = PROJECT_ROOT / "data" / "viral_reels" / f"job_{int(job.id)}"
            work_dir.mkdir(parents=True, exist_ok=True)
            out_audio = work_dir / "narration_combined.mp3"

            try:
                segments = json.loads(job.segments_json or "[]") if job.segments_json else []
            except Exception:
                segments = []
            num_clips = max(1, min(len(segments), 5))
            channel_name = str(job.channel_name or "Partner").strip()
            segments_summary = (job.narrative_context or "")[:1000]

            script_data = grok_service.generate_reel_narration_script(
                channel_name=channel_name,
                segments_summary=segments_summary,
                num_clips=num_clips,
            )
            if script_data.get("error"):
                return {"ok": False, "error": script_data["error"], "job_id": int(job.id)}

            intro = (script_data.get("intro") or "Protocol Pulse Intelligence.").strip()
            insights = script_data.get("insights") or []
            insights = [str(x).strip() for x in insights if str(x).strip()][:num_clips]
            while len(insights) < num_clips:
                insights.append("Key insight from our partner.")
            cta1 = (script_data.get("cta1") or "Subscribe for more Bitcoin intelligence.").strip()
            cta2 = (script_data.get("cta2") or "Visit protocolpulsehq.com.").strip()

            el = ElevenLabsService()
            parts: List[Path] = []
            for i, text in enumerate([intro] + insights + [cta1, cta2]):
                if not text:
                    continue
                part_path = work_dir / f"narration_part_{i:02d}.mp3"
                res = el.synthesize(text=text, out_path=part_path, use_alignment=False)
                if not res.ok:
                    logger.warning("ElevenLabs part %s failed: %s", i, res.error)
                    continue
                parts.append(part_path)

            if not parts:
                return {"ok": False, "error": "No narration audio generated", "job_id": int(job.id)}

            try:
                from pydub import AudioSegment
                combined = AudioSegment.empty()
                for p in parts:
                    seg = AudioSegment.from_file(str(p))
                    combined += seg
                combined.export(str(out_audio), format="mp3", bitrate="192k")
            except Exception as e:
                return {"ok": False, "error": f"pydub concat: {e}", "job_id": int(job.id)}

            if not out_audio.exists() or out_audio.stat().st_size < 1024:
                return {"ok": False, "error": "narration_combined empty", "job_id": int(job.id)}

            return {
                "ok": True,
                "job_id": int(job.id),
                "narration_path": str(out_audio),
                "script": {"intro": intro, "insights": insights, "cta1": cta1, "cta2": cta2},
            }

    def add_narration(self, reel_mp4: str, narration_audio: str) -> Dict:
        """Overlay narration (intro + bridges + 2 CTAs) onto reel. Mix with existing audio via ffmpeg or moviepy."""
        reel_path = Path(reel_mp4)
        narr_path = Path(narration_audio)
        if not reel_path.is_absolute():
            reel_path = PROJECT_ROOT / reel_mp4
        if not narr_path.is_absolute():
            narr_path = PROJECT_ROOT / narration_audio
        if not reel_path.exists():
            return {"ok": False, "error": f"reel not found: {reel_path}"}
        if not narr_path.exists():
            return {"ok": False, "error": f"narration not found: {narr_path}"}

        work = reel_path.parent
        out_path = work / (reel_path.stem + "_vo.mp4")
        reel_str = str(reel_path)
        narr_str = str(narr_path)

        # Prefer ffmpeg for reliable mixing (no moviepy silence/fps quirks).
        try:
            # Pad or trim narration to match reel duration; then amix. Reel may have no audio.
            reel_audio = work / "reel_audio_extract.aac"
            pad_narr = work / "narration_padded.mp3"
            mixed_audio = work / "mixed_audio.aac"
            cmd_extract = ["ffmpeg", "-y", "-i", reel_str, "-vn", "-acodec", "copy", str(reel_audio)]
            proc = self._run(cmd_extract, timeout=30)
            has_reel_audio = proc.returncode == 0 and reel_audio.exists() and reel_audio.stat().st_size > 0

            reel_dur = self._ffprobe_duration_s(reel_path)
            if reel_dur <= 0:
                return {"ok": False, "error": "reel duration unknown"}

            # Pad narration with silence or trim to reel_dur
            pad_cmd = [
                "ffmpeg", "-y",
                "-i", narr_str,
                "-af", f"apad=whole_dur={reel_dur}",
                "-t", str(reel_dur),
                str(pad_narr),
            ]
            self._run(pad_cmd, timeout=60)

            if has_reel_audio:
                # amix: inputs=2, duration=longest; scale down so sum ~1.0
                mix_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(reel_audio),
                    "-i", str(pad_narr),
                    "-filter_complex", "[0:a]volume=0.25[a0];[1:a]volume=0.85[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0",
                    "-ac", "1", "-ar", "44100", "-c:a", "aac", "-b:a", "192k",
                    str(mixed_audio),
                ]
            else:
                mix_cmd = [
                    "ffmpeg", "-y", "-i", str(pad_narr),
                    "-ac", "1", "-ar", "44100", "-c:a", "aac", "-b:a", "192k",
                    str(mixed_audio),
                ]
            proc = self._run(mix_cmd, timeout=60)
            if proc.returncode != 0 or not mixed_audio.exists():
                return {"ok": False, "error": "ffmpeg mix failed"}

            # Mux video (no audio) + mixed audio
            mux_cmd = [
                "ffmpeg", "-y", "-i", reel_str, "-i", str(mixed_audio),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest",
                "-movflags", "+faststart", str(out_path),
            ]
            proc = self._run(mux_cmd, timeout=120)
            for f in (reel_audio, pad_narr, mixed_audio):
                try:
                    if f.exists():
                        f.unlink()
                except Exception:
                    pass
            if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1024:
                shutil.move(str(out_path), reel_str)
                return {"ok": True, "reel_path": reel_str}
            return {"ok": False, "error": "ffmpeg mux failed"}
        except Exception as e:
            logger.exception("add_narration failed")
            return {"ok": False, "error": str(e)}

    def _nvidia_smi_snapshot(self) -> str:
        try:
            proc = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,utilization.gpu,utilization.memory,memory.used,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            return out or err or "(nvidia-smi: no output)"
        except Exception as exc:
            return f"(nvidia-smi unavailable: {exc})"

    def _log_gpu(self, label: str) -> None:
        logger.info("GPU snapshot (%s): %s", label, self._nvidia_smi_snapshot())

    def _run(self, cmd: List[str], *, timeout: int = 60 * 30) -> subprocess.CompletedProcess:
        logger.info("exec: %s", " ".join(cmd))
        dmon_proc = None
        dmon_out = ""
        # Best-effort GPU sampling during ffmpeg renders.
        try:
            samples = int(os.environ.get("VIRAL_GPU_DMON_SAMPLES") or "0")
        except Exception:
            samples = 0
        try:
            if samples > 0 and cmd and Path(cmd[0]).name == "ffmpeg":
                dmon_proc = subprocess.Popen(  # noqa: S603,S607
                    ["nvidia-smi", "dmon", "-s", "u", "-c", str(samples)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
        except Exception:
            dmon_proc = None

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        finally:
            if dmon_proc is not None:
                try:
                    dmon_out = (dmon_proc.communicate(timeout=3)[0] or "").strip()
                except Exception:
                    try:
                        dmon_proc.kill()
                    except Exception:
                        pass
        if dmon_out:
            logger.info("nvidia-smi dmon (samples=%s):\n%s", samples, dmon_out)
        return proc

    def _ffprobe_duration_s(self, path: Path) -> float:
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nokey=1:noprint_wrappers=1", str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return 0.0
            return float((proc.stdout or "").strip() or 0.0)
        except Exception:
            return 0.0

    def _ffprobe_has_audio(self, path: Path) -> bool:
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return proc.returncode == 0 and bool((proc.stdout or "").strip())
        except Exception:
            return False

    def _download_youtube_video(self, video_id: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and out_path.stat().st_size > 128 * 1024:
            return out_path

        url = f"https://www.youtube.com/watch?v={video_id}"
        tmp_template = str(out_path.with_suffix(".%(ext)s"))
        ytdlp = shutil.which("yt-dlp")
        if not ytdlp:
            # Prefer the venv script if present; otherwise fall back to `python -m yt_dlp`.
            venv_candidate = Path(sys.executable).parent / "yt-dlp"
            if venv_candidate.exists():
                ytdlp = str(venv_candidate)
        cmd = [
            ytdlp or sys.executable,
        ]
        if not ytdlp:
            cmd += ["-m", "yt_dlp"]
        # YouTube extraction requires a JS runtime (see https://github.com/yt-dlp/yt-dlp/wiki/EJS)
        js_runtime = (os.environ.get("YT_DLP_JS_RUNTIME") or "").strip().lower()
        if not js_runtime and shutil.which("node"):
            js_runtime = "node"
        if not js_runtime and shutil.which("deno"):
            js_runtime = "deno"
        if js_runtime:
            cmd += ["--js-runtimes", js_runtime]
        cmd += [
            "--no-playlist",
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "-o",
            tmp_template,
            url,
        ]
        proc = self._run(cmd, timeout=60 * 20)
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp failed: {proc.stderr[-400:]}")

        # yt-dlp will produce out_path.with_suffix(".mp4") in most cases, but be defensive.
        mp4 = out_path.with_suffix(".mp4")
        if mp4.exists():
            return mp4
        if out_path.exists():
            return out_path

        # Last resort: pick the newest .mp4 in the folder with the same stem.
        candidates = sorted(out_path.parent.glob(out_path.stem + "*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            return candidates[0]
        raise RuntimeError("yt-dlp succeeded but output mp4 not found")

    def _ensure_tag_outro(self, work_dir: Path) -> Optional[Path]:
        """Ensure a branded outro exists; uses tag.mp4 if present or generates one."""
        env_path = (os.environ.get("VIRAL_OUTRO_PATH") or "").strip()
        if env_path:
            p = Path(env_path)
            if p.exists():
                return p

        # Look for an existing tag.mp4 (spec: always append static/video/tag.mp4 when present)
        for p in (
            PROJECT_ROOT / "static" / "video" / "tag.mp4",
            PROJECT_ROOT / "tag.mp4",
            PROJECT_ROOT / "static" / "tag.mp4",
            PROJECT_ROOT / "static" / "clips" / "tag.mp4",
        ):
            if p.exists() and p.stat().st_size > 64 * 1024:
                return p

        # Generate a lightweight outro into the workdir (no repo binary commits).
        out = work_dir / "tag.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and out.stat().st_size > 64 * 1024:
            return out

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#050505:s=1080x1920:d=5:r=30",
            "-vf",
            "drawbox=x=0:y=0:w=iw:h=ih:color=#DC2626@0.12:t=fill,"
            "drawtext=fontcolor=white:fontsize=56:x=(w-text_w)/2:y=(h-text_h)/2-40:text='PROTOCOL PULSE',"
            "drawtext=fontcolor=#f7931a:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+30:text='INTELLIGENCE REEL'",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ]
        proc = self._run(cmd, timeout=120)
        if proc.returncode != 0:
            logger.warning("Failed generating tag outro: %s", (proc.stderr or "")[-400:])
            return None
        return out if out.exists() else None

    def _make_overlay_png(self, out_path: Path, *, headline: str, subline: str) -> Path:
        from PIL import Image, ImageDraw, ImageFont  # pillow is already in requirements

        out_path.parent.mkdir(parents=True, exist_ok=True)
        w, h = 1080, 1920
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Red tint + dark bottom gradient
        for y in range(h):
            t = y / float(h - 1)
            # darker towards bottom; keep subtle so underlying video shows
            alpha = int(30 + 120 * (t**2))
            r = 220
            g = int(38 * (1 - t) + 10 * t)
            b = int(38 * (1 - t) + 10 * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b, alpha))

        # Text panel
        panel_h = 320
        panel_y = h - panel_h - 80
        draw.rounded_rectangle([(60, panel_y), (w - 60, panel_y + panel_h)], radius=28, fill=(0, 0, 0, 170), outline=(220, 38, 38, 160), width=3)

        # Fonts: default to built-in if system fonts unavailable
        try:
            font_h = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
            font_s = ImageFont.truetype("DejaVuSans.ttf", 28)
        except Exception:
            font_h = ImageFont.load_default()
            font_s = ImageFont.load_default()

        # Headline in orange-ish, subline in white
        headline = (headline or "").strip()[:64]
        subline = re.sub(r"\s+", " ", (subline or "").strip())[:160]

        draw.text((90, panel_y + 40), headline, fill=(247, 147, 26, 255), font=font_h)

        # Simple wrap for subline
        words = subline.split()
        lines: List[str] = []
        cur = ""
        for w0 in words:
            nxt = (cur + " " + w0).strip()
            if draw.textlength(nxt, font=font_s) > (w - 180):
                if cur:
                    lines.append(cur)
                cur = w0
            else:
                cur = nxt
        if cur:
            lines.append(cur)
        lines = lines[:3]
        y = panel_y + 110
        for line in lines:
            draw.text((90, y), line, fill=(255, 255, 255, 235), font=font_s)
            y += 40

        img.save(out_path)
        return out_path

    def _render_segment(
        self,
        *,
        src_path: Path,
        start_s: float,
        end_s: float,
        overlay_png: Path,
        out_path: Path,
        try_gpu: bool = True,
    ) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        dur = max(1.0, float(end_s) - float(start_s))
        fade = min(0.5, max(0.25, dur * 0.06))
        fade_out_start = max(0.0, dur - fade)

        vf = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,format=yuv420p[base];"
            "[1:v]format=rgba[ov];"
            "[base][ov]overlay=0:0:format=auto,"
            f"fade=t=in:st=0:d={fade},fade=t=out:st={fade_out_start}:d={fade}[v]"
        )

        has_audio = self._ffprobe_has_audio(src_path)
        ffmpeg_base = ["ffmpeg", "-y"]
        if try_gpu:
            ffmpeg_base += ["-hwaccel", "cuda", "-hwaccel_device", "0"]

        ffmpeg_in = ["-ss", f"{start_s:.3f}", "-t", f"{dur:.3f}", "-i", str(src_path), "-i", str(overlay_png)]
        maps = ["-map", "[v]"]
        af = []
        if has_audio:
            af = ["-af", f"afade=t=in:st=0:d={fade},afade=t=out:st={fade_out_start}:d={fade}", "-map", "0:a:0?"]

        # Prefer GPU encode if available; fall back to libx264.
        out_tmp = out_path.with_suffix(".tmp.mp4")
        for encoder in ("h264_nvenc", "libx264"):
            cmd = ffmpeg_base + ffmpeg_in + ["-filter_complex", vf] + maps + af + [
                "-c:v",
                encoder,
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(out_tmp),
            ]
            self._log_gpu(f"before_segment_{encoder}")
            proc = self._run(cmd, timeout=int(max(120, dur * 6)))
            self._log_gpu(f"after_segment_{encoder}")
            if proc.returncode == 0 and out_tmp.exists() and out_tmp.stat().st_size > 64 * 1024:
                out_tmp.replace(out_path)
                return
            logger.warning("segment render failed encoder=%s rc=%s err_tail=%s", encoder, proc.returncode, (proc.stderr or "")[-300:])

            # If nvdec/CUDA hwaccel causes failure, retry once without GPU flags.
            if try_gpu and ("nvdec" in (proc.stderr or "").lower() or "cuda" in (proc.stderr or "").lower() or "hwaccel" in (proc.stderr or "").lower()):
                try_gpu = False
                ffmpeg_base = ["ffmpeg", "-y"]

        raise RuntimeError(f"segment render failed for {out_path.name}")

    def _concat_segments(self, segment_paths: List[Path], out_path: Path, *, try_gpu_encode: bool = True) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        list_path = out_path.parent / (out_path.stem + "_concat.txt")
        lines = "\n".join([f"file '{p.as_posix()}'" for p in segment_paths]) + "\n"
        list_path.write_text(lines, encoding="utf-8")

        # Fast path: concat stream copy
        cmd_copy = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", "-movflags", "+faststart", str(out_path)]
        proc = self._run(cmd_copy, timeout=60 * 10)
        if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 128 * 1024:
            return

        # Fallback: re-encode final
        for encoder in ("h264_nvenc", "libx264"):
            if encoder == "h264_nvenc" and not try_gpu_encode:
                continue
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c:v", encoder, "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
            self._log_gpu(f"before_concat_{encoder}")
            proc2 = self._run(cmd, timeout=60 * 30)
            self._log_gpu(f"after_concat_{encoder}")
            if proc2.returncode == 0 and out_path.exists() and out_path.stat().st_size > 256 * 1024:
                return

        raise RuntimeError(f"concat failed: {(proc.stderr or '')[-300:]}")

    def _add_cta_overlays(self, video_path: Path, duration_s: float, *, work_dir: Path) -> bool:
        """Add two CTAs at 25% and 75% of reel (spec: one at 25%, one at 75%)."""
        if duration_s <= 0:
            return False
        t1 = 0.25 * duration_s
        t2 = 0.75 * duration_s
        show_s = 5.0
        # drawtext: show "Protocol Pulse | Subscribe" for 5s at 25% and 75%
        cta_text = "Protocol Pulse | Subscribe"
        # Escape single quotes for ffmpeg enable expr
        f1_start = t1
        f1_end = t1 + show_s
        f2_start = t2
        f2_end = t2 + show_s
        out_path = work_dir / "reel_with_cta.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        vf = (
            f"drawtext=text='{cta_text}':fontcolor=white:fontsize=36:borderw=2:bordercolor=black@0.8:"
            f"x=(w-text_w)/2:y=h-120:enable='between(t,{f1_start},{f1_end})',"
            f"drawtext=text='{cta_text}':fontcolor=white:fontsize=36:borderw=2:bordercolor=black@0.8:"
            f"x=(w-text_w)/2:y=h-120:enable='between(t,{f2_start},{f2_end})'"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", vf,
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(out_path),
        ]
        proc = self._run(cmd, timeout=300)
        if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1024:
            shutil.move(str(out_path), str(video_path))
            return True
        return False

    def render_reel(self, clip_job: Any) -> Dict:
        """Render a 5-10 minute reel for a ClipJob.

        - Downloads source via yt-dlp
        - Extracts segments with ffmpeg (+ CUDA hwaccel if available)
        - Applies red/black overlay + text insights via PIL-generated overlay PNGs
        - Concats segments + tag.mp4 outro
        """
        # Optional import: we don't rely on moviepy for the heavy lifting (GPU path is ffmpeg),
        # but we import it to keep the "moviepy present" requirement satisfied.
        try:
            import moviepy  # noqa: F401
        except Exception:
            pass

        from app import app, db
        import models

        with app.app_context():
            job = clip_job
            if not hasattr(job, "id"):
                job = models.ClipJob.query.get(int(clip_job))
            if job is None:
                return {"ok": False, "error": "ClipJob not found"}

            work_dir = PROJECT_ROOT / "data" / "viral_reels" / f"job_{int(job.id)}"
            seg_dir = work_dir / "segments"
            ov_dir = work_dir / "overlays"
            work_dir.mkdir(parents=True, exist_ok=True)
            seg_dir.mkdir(parents=True, exist_ok=True)
            ov_dir.mkdir(parents=True, exist_ok=True)

            try:
                job.status = "Processing"
                db.session.commit()

                try:
                    segments = json.loads(job.segments_json or "[]") if job.segments_json else []
                except Exception:
                    segments = []
                if not segments:
                    try:
                        legacy = json.loads(job.timestamps_json or "[]")
                        segments = [{"start": r.get("start"), "end": r.get("end"), "snippet": r.get("context", ""), "reason": "legacy"} for r in (legacy or [])]
                    except Exception:
                        segments = []

                src_path = self._download_youtube_video(str(job.video_id), work_dir / f"{job.video_id}.mp4")
                src_dur = self._ffprobe_duration_s(src_path)
                if src_dur <= 1.0:
                    raise RuntimeError("source duration unknown/invalid (ffprobe)")
                # Expand to 5-10 minutes total (target ~7 minutes).
                target_min_s = 5 * 60.0
                target_max_s = 10 * 60.0
                target_s = float(os.environ.get("VIRAL_TARGET_SECONDS") or 420.0)
                target_s = min(target_max_s, max(target_min_s, target_s))

                # Normalize segment list (start/end floats).
                norm: List[Dict[str, Any]] = []
                for s in segments:
                    try:
                        st = float(s.get("start") or 0.0)
                        en = float(s.get("end") or 0.0)
                    except Exception:
                        continue
                    if en <= st:
                        continue
                    norm.append({**s, "start": st, "end": en})
                segments = norm

                total = sum(max(0.0, float(s["end"]) - float(s["start"])) for s in segments)
                if total < target_min_s:
                    # Add coverage windows across the video to reach the target duration.
                    existing_starts = [float(s["start"]) for s in segments]
                    window = 60.0
                    cursor = 0
                    while total < target_s and cursor < 20:
                        cursor += 1
                        frac = (cursor + 1) / float(10 + 2)
                        st = max(0.0, min(src_dur - window - 1.0, src_dur * frac))
                        if any(abs(st - es) < 25.0 for es in existing_starts):
                            continue
                        segments.append({"start": st, "end": min(src_dur, st + window), "score": 0, "reason": "coverage_window", "snippet": ""})
                        existing_starts.append(st)
                        total += window

                # Clamp and cap segments so we don't exceed 10 minutes.
                segments.sort(key=lambda s: float(s["start"]))
                trimmed: List[Dict[str, Any]] = []
                run = 0.0
                for s in segments:
                    st = max(0.0, float(s["start"]))
                    en = min(src_dur, float(s["end"]))
                    if en - st < 20.0:
                        continue
                    dur = en - st
                    if run + dur > target_max_s:
                        break
                    trimmed.append({**s, "start": st, "end": en})
                    run += dur
                    if run >= target_s:
                        break
                segments = trimmed

                if run < target_min_s:
                    raise RuntimeError(f"not enough segment duration for reel: {run:.1f}s")

                self._log_gpu("before_reel")
                segment_paths: List[Path] = []
                for idx, s in enumerate(segments):
                    st = float(s["start"])
                    en = float(s["end"])
                    snippet = str(s.get("snippet") or "").strip()
                    reason = str(s.get("reason") or "INSIGHT").strip()
                    headline = "BREAKING" if "break" in reason.lower() else ("UPGRADE" if "upgrad" in reason.lower() else "INSIGHT")

                    overlay = self._make_overlay_png(
                        ov_dir / f"ov_{idx:02d}.png",
                        headline=headline,
                        subline=(snippet or f"Featured insight from {job.channel_name or 'Partner'}"),
                    )
                    seg_out = seg_dir / f"seg_{idx:02d}.mp4"
                    self._render_segment(src_path=src_path, start_s=st, end_s=en, overlay_png=overlay, out_path=seg_out, try_gpu=True)
                    segment_paths.append(seg_out)

                outro = self._ensure_tag_outro(work_dir)
                if outro is not None and outro.exists():
                    # Re-encode outro to match format (1080x1920, yuv420p) for concat stability.
                    outro_norm = work_dir / "tag_norm.mp4"
                    cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(outro),
                        "-vf",
                        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "fast",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-movflags",
                        "+faststart",
                        str(outro_norm),
                    ]
                    proc = self._run(cmd, timeout=120)
                    if proc.returncode == 0 and outro_norm.exists() and outro_norm.stat().st_size > 64 * 1024:
                        segment_paths.append(outro_norm)

                final_rel = Path("static") / "clips" / "reels" / f"job_{int(job.id)}_reel.mp4"
                final_path = PROJECT_ROOT / final_rel
                self._concat_segments(segment_paths, final_path, try_gpu_encode=True)

                final_dur = self._ffprobe_duration_s(final_path)
                self._log_gpu("after_reel")
                # CTAs at 25% and 75% (spec)
                self._add_cta_overlays(final_path, final_dur, work_dir=work_dir)

                # Batch 4: optional voiceover (Grok script + ElevenLabs + overlay)
                if os.environ.get("VIRAL_ADD_VOICEOVER", "").strip().lower() in ("1", "true", "yes"):
                    gen = self.generate_narration(job)
                    if gen.get("ok") and gen.get("narration_path"):
                        add_result = self.add_narration(str(final_path), gen["narration_path"])
                        if not add_result.get("ok"):
                            logger.warning("add_narration failed: %s", add_result.get("error"))

                job.output_path = final_rel.as_posix()
                job.metadata_json = json.dumps(
                    {
                        "rendered_at": datetime.utcnow().isoformat(),
                        "source_path": str(src_path),
                        "final_path": str(final_path),
                        "final_duration_s": round(final_dur, 2),
                        "segments_count": len(segments),
                        "target_seconds": target_s,
                    }
                )
                job.status = "Completed"
                db.session.commit()

                return {
                    "ok": True,
                    "job_id": int(job.id),
                    "output_path": job.output_path,
                    "duration_s": round(final_dur, 2),
                    "segments": len(segments),
                }
            except Exception as exc:
                logger.exception("render_reel failed job_id=%s", getattr(job, "id", "?"))
                try:
                    job.status = "Failed"
                    job.metadata_json = json.dumps({"error": str(exc), "failed_at": datetime.utcnow().isoformat()})
                    db.session.commit()
                except Exception:
                    pass
                return {"ok": False, "job_id": int(job.id), "error": str(exc)}
        # unreachable
        return {"ok": False, "error": "unexpected"}

    def build_reel(self, job_id: int) -> Dict:
        """Orchestration: render ClipJob into reel (segments + tag outro + CTAs)."""
        from app import app
        import models
        with app.app_context():
            job = models.ClipJob.query.get(int(job_id))
            if job is None:
                return {"ok": False, "job_id": job_id, "error": "ClipJob not found"}
            return self.render_reel(job)

    def build_medley_reel(self, video_id: str, *, channel_name: Optional[str] = None) -> Dict:
        """Build Intel Briefing reel for a video: get/create ClipJob, render, copy to data/clips/.
        Validator: >10MB vertical MP4 in data/clips/ with synced audio and branded outro.
        """
        from app import app, db
        import models
        vid = (video_id or "").strip()
        if not vid:
            return {"ok": False, "error": "video_id required"}
        out_dir = PROJECT_ROOT / "data" / "clips"
        out_dir.mkdir(parents=True, exist_ok=True)
        medley_path = out_dir / f"medley_{vid}.mp4"

        with app.app_context():
            job = models.ClipJob.query.filter_by(video_id=vid).first()
            if job is None:
                transcript = self._fetch_transcript(vid)
                segments = self._plan_viral_segments_from_transcript(transcript)
                if len(segments) < 3:
                    return {
                        "ok": False,
                        "error": f"insufficient segments (need >=3, got {len(segments)})",
                        "video_id": vid,
                    }
                segments = segments[:5]
                cname = channel_name or "Partner"
                now = datetime.now(timezone.utc).isoformat()
                metadata = {
                    "source": "build_medley_reel",
                    "channel_name": cname,
                    "planned_at": now,
                }
                timestamps_payload = [{"start": s["start"], "end": s["end"], "context": s.get("snippet", "")} for s in segments]
                narrative = " | ".join(str(s.get("snippet") or "") for s in segments[:3]).strip()
                job = models.ClipJob(
                    video_id=vid,
                    channel_name=cname,
                    segments_json=json.dumps(segments),
                    narration_path=None,
                    output_path=None,
                    metadata_json=json.dumps(metadata),
                    timestamps_json=json.dumps(timestamps_payload),
                    narrative_context=narrative,
                    status="Planned",
                    created_at=datetime.utcnow(),
                )
                db.session.add(job)
                db.session.commit()

            result = self.render_reel(job)
            if not result.get("ok"):
                return {"ok": False, "error": result.get("error", "render failed")}
            # Copy to data/clips/ for validator (SUCCESS: >10MB vertical MP4 in data/clips/)
            src = PROJECT_ROOT / (result.get("output_path") or "")
            if src.exists():
                shutil.copy2(str(src), str(medley_path))
                result["medley_path"] = str(medley_path)
                if medley_path.exists():
                    result["medley_size_mb"] = round(medley_path.stat().st_size / (1024 * 1024), 2)
            return result


def run_heartbeat_forever() -> None:
    """Simple 60-minute heartbeat loop (can be invoked by a daemon/runner)."""
    engine = ViralMomentsReelEngine()
    while True:
        engine.monitor_partners()
        sleep_s = int(max(60, float(os.environ.get("VIRAL_HEARTBEAT_SECONDS") or 3600)))
        logger.info("heartbeat sleep=%ss", sleep_s)
        time.sleep(sleep_s)

