"""Montage blueprint — serves daily highlights montage videos."""

import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, send_file

montage_bp = Blueprint("montage", __name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
PIPELINE_OUTPUT = PROJECT_ROOT / "video_pipeline_v3" / "output"


@montage_bp.route("/montage")
def serve_montage():
    """Serve the latest montage video."""
    path = STATIC_DIR / "montage_latest.mp4"
    if not path.exists():
        return jsonify({"error": "No montage available yet"}), 404
    return send_file(str(path.resolve()), mimetype="video/mp4")


@montage_bp.route("/montage/shorts")
def serve_shorts():
    """Serve the latest Shorts version."""
    path = STATIC_DIR / "montage_latest_shorts.mp4"
    if not path.exists():
        return jsonify({"error": "No shorts montage available yet"}), 404
    return send_file(str(path.resolve()), mimetype="video/mp4")


@montage_bp.route("/montage/latest")
def montage_metadata():
    """Return JSON metadata for today's montage."""
    today = datetime.now().strftime("%Y-%m-%d")
    meta_path = PIPELINE_OUTPUT / today / f"montage_{today}_meta.json"

    if not meta_path.exists():
        # Try finding any recent montage metadata
        for i in range(7):
            from datetime import timedelta
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            p = PIPELINE_OUTPUT / d / f"montage_{d}_meta.json"
            if p.exists():
                meta_path = p
                break
        else:
            return jsonify({"error": "No montage metadata found"}), 404

    with open(meta_path) as f:
        data = json.load(f)

    return jsonify(data)
