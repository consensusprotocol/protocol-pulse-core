"""
AI Clips Service: powers /clips page and Generate Daily Clips.
Uses ClipJob + ViralMomentsReelEngine + clip_service; reads partner_channels.json.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CLIPS = PROJECT_ROOT / "data" / "clips"
STATIC_CLIPS_REELS = PROJECT_ROOT / "static" / "clips" / "reels"


def _get_models():
    """Use project-root models so ClipJob is always available (avoids core.models missing ClipJob)."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    import models as root_models
    return root_models


def _load_partner_channels() -> List[Dict[str, str]]:
    """Load from config/partner_channels.json."""
    channels: List[Dict[str, str]] = []
    cfg = PROJECT_ROOT / "config" / "partner_channels.json"
    if not cfg.exists():
        return channels
    try:
        raw = json.loads(cfg.read_text(encoding="utf-8"))
        for item in raw.get("youtube_channels") or []:
            if isinstance(item, dict):
                cid = (item.get("channel_id") or "").strip()
                name = (item.get("name") or "").strip()
                if cid:
                    channels.append({"id": cid, "name": name, "channel_id": cid})
    except Exception as e:
        logger.warning("partner_channels.json unreadable: %s", e)
    return channels


class AIClipsService:
    """Single instance used by routes."""
    CLIPS_CHANNELS = _load_partner_channels()

    def reload_channels(self) -> None:
        """Reload partner list from config (e.g. after config change)."""
        AIClipsService.CLIPS_CHANNELS = _load_partner_channels()

    def get_status(self) -> Dict[str, Any]:
        """Status for /clips page: ffmpeg, yt-dlp, AI, clips_count."""
        status: Dict[str, Any] = {
            "status": "ok",
            "ffmpeg_available": bool(shutil.which("ffmpeg")),
            "ytdlp_available": bool(shutil.which("yt-dlp")) or bool((Path(os.environ.get("VIRTUAL_ENV", "")) / "bin" / "yt-dlp").exists()),
            "openai_configured": bool((os.environ.get("OPENAI_API_KEY") or "").strip()),
            "clips_count": 0,
        }
        try:
            from app import app
            models = _get_models()
            with app.app_context():
                completed = models.ClipJob.query.filter_by(status="Completed").filter(models.ClipJob.output_path.isnot(None)).count()
                status["clips_count"] = completed
                # Also count files in data/clips for legacy
                if DATA_CLIPS.exists():
                    mp4s = list(DATA_CLIPS.glob("*.mp4"))
                    status["clips_count"] = max(status["clips_count"], len(mp4s))
        except Exception as e:
            logger.debug("get_status ClipJob count: %s", e)
        return status

    def get_all_clips(self) -> List[Dict[str, Any]]:
        """Clips for gallery: ClipJob completed with output_path + data/clips/*.mp4."""
        out: List[Dict[str, Any]] = []
        try:
            from app import app
            models = _get_models()
            with app.app_context():
                jobs = (
                    models.ClipJob.query.filter_by(status="Completed")
                    .filter(models.ClipJob.output_path.isnot(None))
                    .order_by(models.ClipJob.created_at.desc())
                    .limit(50)
                    .all()
                )
                for j in jobs:
                    path = (j.output_path or "").strip()
                    if not path:
                        continue
                    if path.startswith("static/"):
                        url = f"/static/{path[7:]}"
                    elif path.startswith("/"):
                        url = path
                    else:
                        url = f"/static/{path}"
                    full_path = PROJECT_ROOT / path.lstrip("/") if not path.startswith("http") else None
                    if full_path and not full_path.exists():
                        # Try static/clips/reels/job_X_reel.mp4
                        alt = STATIC_CLIPS_REELS / Path(path).name
                        if alt.exists():
                            url = f"/static/clips/reels/{Path(path).name}"
                        else:
                            continue
                    out.append({
                        "id": f"job_{j.id}",
                        "url": url,
                        "filename": Path(path).name,
                        "filepath": path,
                        "title": f"{j.channel_name or 'Partner'} – {j.video_id}",
                        "created": (j.created_at.isoformat() if j.created_at else ""),
                        "is_final": True,
                    })
        except Exception as e:
            logger.warning("get_all_clips ClipJob: %s", e)

        # Add files from data/clips/
        try:
            if DATA_CLIPS.exists():
                for mp4 in sorted(DATA_CLIPS.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
                    name = mp4.name
                    if any(c["id"] == name for c in out):
                        continue
                    out.append({
                        "id": name,
                        "url": f"/api/clips/file/{name}",
                        "filename": name,
                        "filepath": str(mp4),
                        "title": name.replace("_", " ").replace(".mp4", ""),
                        "created": datetime.fromtimestamp(mp4.stat().st_mtime, tz=timezone.utc).isoformat(),
                        "is_final": "medley" in name or "fallback" in name or "job_" in name,
                    })
        except Exception as e:
            logger.warning("get_all_clips data/clips: %s", e)

        return out

    def _get_daily_count(self, channel_id: str) -> int:
        """ClipJobs created today for this channel (for daily limit)."""
        try:
            from app import app
            models = _get_models()
            from datetime import date
            today = date.today()
            with app.app_context():
                return models.ClipJob.query.filter(
                    models.ClipJob.channel_name.isnot(None),
                    models.ClipJob.created_at >= datetime.combine(today, datetime.min.time()),
                ).count()
        except Exception:
            return 0

    def run_daily_clips_job(self) -> Dict[str, Any]:
        """
        Trigger: monitor partners -> pick one Planned ClipJob -> render reel.
        Returns { clips_created, message, errors } for the Generate button.
        """
        result: Dict[str, Any] = {"clips_created": 0, "message": "", "errors": []}
        try:
            from app import app, db
            models = _get_models()
            from services.viralmoments import ViralMomentsReelEngine

            with app.app_context():
                engine = ViralMomentsReelEngine()
                # 1) Monitor: create ClipJobs for new videos from partner channels
                mon = engine.monitor_partners()
                planned_before = mon.get("planned", 0)
                job_ids = mon.get("job_ids") or []

                # 2) Pick first Planned job and render
                job = (
                    models.ClipJob.query.filter(models.ClipJob.status == "Planned")
                    .order_by(models.ClipJob.id.asc())
                    .first()
                )
                if not job:
                    result["message"] = "No new videos to process. Try again later or add a video manually."
                    if not job_ids and planned_before == 0:
                        result["errors"].append("No Planned jobs; monitor found no new videos.")
                    return result

                # 3) Render reel (5–10 min Intel Briefing)
                render = engine.render_reel(job)
                if not render.get("ok"):
                    result["errors"].append(render.get("error") or "Render failed")
                    result["message"] = "Reel render failed: " + (render.get("error") or "unknown")
                    return result

                result["clips_created"] = 1
                result["message"] = f"Generated 1 reel: {job.video_id} ({job.channel_name or 'Partner'})"
                result["output_path"] = render.get("output_path")
                return result

        except Exception as e:
            logger.exception("run_daily_clips_job failed")
            result["errors"].append(str(e))
            result["message"] = f"Job failed: {e}"
            return result

    def process_video(
        self,
        video_id: str,
        video_title: str = "",
        channel_name: str = "Manual",
        max_clips: int = 2,
    ) -> List[Dict[str, Any]]:
        """Process one YouTube video: build_medley_reel. Returns list of clip info."""
        try:
            from services.viralmoments import ViralMomentsReelEngine
            engine = ViralMomentsReelEngine()
            r = engine.build_medley_reel(video_id, channel_name=channel_name)
            if not r.get("ok"):
                return []
            medley_path = r.get("medley_path") or ""
            filename = Path(medley_path).name if medley_path else ""
            url = f"/api/clips/file/{filename}" if filename else ""
            return [{"video_id": video_id, "path": medley_path, "url": url, "filename": filename, "ok": True}]
        except Exception as e:
            logger.exception("process_video failed: %s", e)
            return []

    def process_partner_channels(self) -> Dict[str, Any]:
        """
        Process all partner channels: monitor for new videos, then run one daily clips job.
        Returns { clips_created, channels_processed } for the Content Command Center button.
        """
        channels_processed = len(self.CLIPS_CHANNELS) if self.CLIPS_CHANNELS else 0
        job_result = self.run_daily_clips_job()
        clips_created = job_result.get("clips_created", 0)
        return {
            "clips_created": clips_created,
            "channels_processed": channels_processed,
            "message": job_result.get("message", "Partner channels processed"),
        }


# Singleton used by routes
ai_clips_service = AIClipsService()
