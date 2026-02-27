#!/usr/bin/env python3
"""
Batch 6: End-to-end reel pipeline test.
Runs: monitor → segment → clip (render) → narrate → publish (if ENABLE_LIVE_POSTING).
Produces: full narrated reel MP4 + publish log.
Usage:
  python scripts/test_reel_pipeline.py [--video-id VIDEO_ID] [--channel-name NAME] [--no-narration] [--no-publish]
  TEST_VIDEO_ID=yD0b2PXuwNI python scripts/test_reel_pipeline.py
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Project root
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test_reel_pipeline")

# Default sample partner video (Natalie Brunell)
DEFAULT_VIDEO_ID = "yD0b2PXuwNI"
DEFAULT_CHANNEL = "Natalie Brunell"


def _send_alert_email(subject: str, body: str) -> bool:
    """Send alert email on failure (same as scheduler)."""
    to = os.environ.get("VIRAL_ALERT_EMAIL") or os.environ.get("CONTACT_EMAIL") or os.environ.get("SENDGRID_FROM_EMAIL")
    if not to:
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
    except ImportError:
        return False
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        return False
    from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@protocolpulse.io")
    message = Mail(
        from_email=Email(from_email, "Protocol Pulse"),
        to_emails=To(to),
        subject=subject[:200],
        plain_text_content=Content("text/plain", body[:10000]),
    )
    try:
        SendGridAPIClient(api_key).send(message)
        return True
    except Exception as e:
        logger.warning("Alert email failed: %s", e)
        return False


def run_pipeline(
    video_id: str,
    channel_name: str,
    skip_narration: bool = False,
    skip_publish: bool = False,
) -> dict:
    """Run full pipeline: build reel → narrate → publish. Returns report dict."""
    from app import app
    import models
    from services.viralmoments import ViralMomentsReelEngine
    from services.scheduler import ENABLE_LIVE_POSTING, _send_alert_email as scheduler_alert

    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "video_id": video_id,
        "channel_name": channel_name,
        "skip_narration": skip_narration,
        "skip_publish": skip_publish,
        "steps": {},
        "reel_path": None,
        "reel_url": None,
        "published_x": False,
        "published_tg": False,
        "success": False,
        "error": None,
    }

    with app.app_context():
        engine = ViralMomentsReelEngine()

        # 1) Build reel (get/create ClipJob, render segments + outro + CTAs)
        logger.info("Step 1: build reel for video_id=%s", video_id)
        try:
            result = engine.build_medley_reel(video_id, channel_name=channel_name)
        except Exception as e:
            logger.exception("build_medley_reel failed")
            report["error"] = str(e)
            report["steps"]["build_reel"] = {"ok": False, "error": str(e)}
            scheduler_alert("[Protocol Pulse] test_reel_pipeline build failed", f"video_id={video_id}\n{e}")
            return report

        if not result.get("ok"):
            report["error"] = result.get("error", "build failed")
            report["steps"]["build_reel"] = result
            scheduler_alert("[Protocol Pulse] test_reel_pipeline build failed", f"video_id={video_id}\n{report['error']}")
            return report

        report["steps"]["build_reel"] = {"ok": True, "job_id": result.get("job_id"), "output_path": result.get("output_path")}
        output_path = result.get("output_path")
        # Reel is written to static/clips/reels/job_N_reel.mp4; copy may exist in data/clips/medley_VID.mp4
        reel_path = REPO_ROOT / (output_path or "")
        if not reel_path.exists():
            alt = REPO_ROOT / "data" / "clips" / f"medley_{video_id}.mp4"
            reel_path = alt if alt.exists() else reel_path
        report["reel_path"] = str(reel_path)

        job = models.ClipJob.query.filter_by(video_id=video_id).first()
        if not job:
            report["error"] = "ClipJob not found after build"
            return report

        # 2) Narrate (Grok script + ElevenLabs + overlay)
        if not skip_narration and reel_path.exists():
            logger.info("Step 2: generate narration and overlay")
            try:
                gen = engine.generate_narration(job)
                if gen.get("ok") and gen.get("narration_path"):
                    add_result = engine.add_narration(str(reel_path), gen["narration_path"])
                    report["steps"]["narration"] = {"generate": gen, "add_narration": add_result}
                    if not add_result.get("ok"):
                        logger.warning("add_narration failed: %s", add_result.get("error"))
                else:
                    report["steps"]["narration"] = {"generate": gen, "add_narration": None}
            except Exception as e:
                logger.exception("Narration step failed")
                report["steps"]["narration"] = {"ok": False, "error": str(e)}
        else:
            report["steps"]["narration"] = {"skipped": True} if skip_narration else {"skipped": True, "reason": "reel_path missing"}

        base_url = os.environ.get("BASE_URL", "https://protocolpulse.io").rstrip("/")
        report["reel_url"] = f"{base_url}/static/clips/reels/{Path(output_path or '').name}" if output_path else None
        if not report["reel_url"] and reel_path.exists():
            report["reel_url"] = f"{base_url}/data/clips/medley_{video_id}.mp4"

        # 3) Publish (if ENABLE_LIVE_POSTING and not skip_publish)
        if skip_publish or not os.environ.get("ENABLE_LIVE_POSTING", "").strip().lower() in ("1", "true", "yes"):
            report["steps"]["publish"] = {"skipped": True, "reason": "skip_publish or ENABLE_LIVE_POSTING=false"}
            report["success"] = True
            return report

        if not report["reel_url"]:
            report["steps"]["publish"] = {"skipped": True, "reason": "no reel_url"}
            report["success"] = True
            return report

        # Publish to X
        try:
            from services.x_service import XService
            x = XService()
            text = f"Intel Briefing reel — {channel_name} | {report['reel_url']}"
            if len(text) > 280:
                text = f"Intel Briefing | {channel_name} {report['reel_url']}"
            if x.client:
                x.client.update_status(text[:280])
                report["published_x"] = True
            elif getattr(x, "client_v2", None) and x.client_v2:
                x.client_v2.create_tweet(text=text[:280])
                report["published_x"] = True
        except Exception as ex:
            logger.warning("X post failed: %s", ex)
            report["steps"]["publish_x"] = {"ok": False, "error": str(ex)}
            scheduler_alert("[Protocol Pulse] test_reel_pipeline X post failed", str(ex))

        # Publish to Telegram
        try:
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            if token and chat_id:
                import requests
                r = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": f"Intel Briefing reel — {channel_name}\n{report['reel_url']}"},
                    timeout=10,
                )
                report["published_tg"] = r.status_code == 200
        except Exception as ex:
            logger.warning("Telegram post failed: %s", ex)
            report["steps"]["publish_tg"] = {"ok": False, "error": str(ex)}

        report["steps"]["publish"] = {"published_x": report["published_x"], "published_tg": report["published_tg"]}
        report["success"] = True
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end reel pipeline test")
    parser.add_argument("--video-id", default=os.environ.get("TEST_VIDEO_ID", DEFAULT_VIDEO_ID), help="YouTube video ID")
    parser.add_argument("--channel-name", default=os.environ.get("TEST_CHANNEL_NAME", DEFAULT_CHANNEL), help="Channel display name")
    parser.add_argument("--no-narration", action="store_true", help="Skip Grok+ElevenLabs narration overlay")
    parser.add_argument("--no-publish", action="store_true", help="Do not post to X/Telegram even if ENABLE_LIVE_POSTING")
    parser.add_argument("--log-dir", default=None, help="Directory for publish log (default: REPO_ROOT/logs)")
    args = parser.parse_args()

    video_id = (args.video_id or DEFAULT_VIDEO_ID).strip()
    channel_name = (args.channel_name or DEFAULT_CHANNEL).strip()
    log_dir = Path(args.log_dir or REPO_ROOT / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"test_reel_pipeline_{ts}.json"
    log_path_txt = log_dir / f"test_reel_pipeline_{ts}.log"

    logger.info("Starting pipeline video_id=%s channel=%s", video_id, channel_name)
    try:
        report = run_pipeline(
            video_id=video_id,
            channel_name=channel_name,
            skip_narration=args.no_narration,
            skip_publish=args.no_publish,
        )
    except Exception as e:
        logger.exception("Pipeline failed")
        report = {
            "success": False,
            "error": str(e),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        _send_alert_email("[Protocol Pulse] test_reel_pipeline failed", f"video_id={video_id}\n{e}")

    report["finished_at"] = datetime.now(timezone.utc).isoformat()

    # Write publish log (JSON)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Publish log written: %s", log_path)

    # Human-readable log
    with open(log_path_txt, "w", encoding="utf-8") as f:
        f.write(f"Test reel pipeline {report.get('started_at', '')} -> {report.get('finished_at', '')}\n")
        f.write(f"video_id={video_id} channel={channel_name}\n")
        f.write(f"success={report.get('success')} error={report.get('error')}\n")
        f.write(f"reel_path={report.get('reel_path')}\n")
        f.write(f"reel_url={report.get('reel_url')}\n")
        f.write(f"published_x={report.get('published_x')} published_tg={report.get('published_tg')}\n")
        f.write("\nFull report:\n")
        f.write(json.dumps(report, indent=2, default=str))
    logger.info("Log (text) written: %s", log_path_txt)

    if report.get("reel_path"):
        p = Path(report["reel_path"])
        if p.exists():
            size_mb = p.stat().st_size / (1024 * 1024)
            logger.info("Reel MP4: %s (%.2f MB)", p, size_mb)
        else:
            logger.warning("Reel file not found at %s", report["reel_path"])

    print("Batch 6 pipeline report:")
    print(f"  success={report.get('success')}")
    print(f"  reel_path={report.get('reel_path')}")
    print(f"  reel_url={report.get('reel_url')}")
    print(f"  publish_log={log_path}")
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
