"""
BRIEFINGS BLUEPRINT — Protocol Pulse
======================================
GET /briefings — Public page showing last 7 days of HeyGen Sarah briefings.
Pulls from market_briefings table + oracle_briefing/output/ filesystem.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, render_template, jsonify

briefings_bp = Blueprint("briefings", __name__)


def _get_fs_briefings(days: int = 7) -> list[dict]:
    """Scan oracle_briefing/output/ for briefing videos."""
    base = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "oracle_briefing" / "output"
    briefings = []
    cutoff = datetime.now() - timedelta(days=days)

    if not base.exists():
        return briefings

    for date_dir in sorted(base.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        try:
            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
            if dir_date < cutoff:
                break
        except ValueError:
            continue

        for mp4 in sorted(date_dir.glob("briefing_*.mp4"), reverse=True):
            parts = mp4.stem.split("_")
            btype = parts[1] if len(parts) > 1 else "unknown"
            btime = parts[2] if len(parts) > 2 else "0000"
            size_mb = round(mp4.stat().st_size / 1024 / 1024, 1)

            # Check for matching script
            script_path = mp4.with_suffix(".txt")
            script_text = ""
            if script_path.exists():
                script_text = script_path.read_text()[:500]

            briefings.append({
                "date": date_dir.name,
                "type": btype,
                "time": f"{btime[:2]}:{btime[2:]}" if len(btime) == 4 else btime,
                "file": str(mp4),
                "filename": mp4.name,
                "size_mb": size_mb,
                "script_preview": script_text,
                "video_url": f"/briefings/video/{date_dir.name}/{mp4.name}",
            })

    return briefings


def _get_db_briefings(days: int = 7) -> list[dict]:
    """Pull briefings from MarketBriefing DB table."""
    try:
        from models import MarketBriefing
        cutoff = datetime.now() - timedelta(days=days)
        rows = MarketBriefing.query.filter(
            MarketBriefing.generated_at >= cutoff,
            MarketBriefing.status == "completed",
        ).order_by(MarketBriefing.generated_at.desc()).all()

        return [{
            "date": r.scheduled_date or r.generated_at.strftime("%Y-%m-%d"),
            "type": r.briefing_type,
            "time": r.generated_at.strftime("%H:%M") if r.generated_at else "",
            "title": r.title,
            "script_preview": (r.script_text or "")[:500],
            "video_url": r.video_url or "",
            "duration": r.duration_seconds,
            "btc_price": r.btc_price_at_generation,
            "source": "db",
        } for r in rows]
    except Exception:
        return []


@briefings_bp.route("/briefings")
def briefings_page():
    """Public page: last 7 days of Oracle Briefings."""
    fs_briefings = _get_fs_briefings(days=7)
    db_briefings = _get_db_briefings(days=7)

    # Merge: prefer DB entries, supplement with filesystem
    all_briefings = db_briefings + fs_briefings

    # Group by date
    by_date = {}
    for b in all_briefings:
        date = b["date"]
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(b)

    return render_template("briefings.html", briefings_by_date=by_date)


@briefings_bp.route("/api/briefings")
def briefings_api():
    """JSON API: last 7 days of briefings."""
    fs_briefings = _get_fs_briefings(days=7)
    db_briefings = _get_db_briefings(days=7)
    return jsonify({"briefings": db_briefings + fs_briefings})


@briefings_bp.route("/briefings/video/<date>/<filename>")
def briefing_video(date, filename):
    """Serve briefing video files."""
    from flask import send_from_directory
    video_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "oracle_briefing" / "output" / date
    return send_from_directory(str(video_dir), filename)
