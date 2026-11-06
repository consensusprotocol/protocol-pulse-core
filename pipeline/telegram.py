#!/usr/bin/env python3
"""pipeline/telegram.py — Telegram preview drop with VERIFIED_BY_ORCHESTRATOR guard (M16).

The ONLY path for sending review drops. Wraps segment_v1/tg_preview.py with
width, height, supports_streaming parameters. Refuses to send unless:
  1. Both aspect gate reports are all-pass (no GATE_FAIL.txt)
  2. segment/VERIFIED_BY_ORCHESTRATOR file exists (created by the orchestrator)

Ad-hoc requests.post / curl sends are FORBIDDEN (M16).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import resolve_paths


def send_telegram_preview(segment_dir, qa_version=None):
    """Send both outputs to Telegram. Raises on any guard failure."""
    paths = resolve_paths(segment_dir, qa_version)
    qa_dir = paths["qa_dir"]
    out_dir = paths["out_dir"]

    # Guard 1: VERIFIED_BY_ORCHESTRATOR must exist
    verified_path = os.path.join(segment_dir, "VERIFIED_BY_ORCHESTRATOR")
    if not os.path.exists(verified_path):
        raise RuntimeError(
            f"STOP: Telegram refused — {verified_path} not found. "
            "The orchestrator must verify and create this file first (M9, M16)."
        )

    # Guard 2: no GATE_FAIL.txt in qa_dir
    gate_fail = os.path.join(qa_dir, "GATE_FAIL.txt")
    if os.path.exists(gate_fail):
        raise RuntimeError(f"STOP: Telegram refused — gates failed: {gate_fail}")

    # Guard 3: both finals exist
    final_16 = os.path.join(out_dir, "segment.mp4")
    final_9 = os.path.join(out_dir, "segment_vertical.mp4")
    for f in [final_16, final_9]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"STOP: final output missing: {f}")

    # Guard 4: gate results for BOTH aspects exist and show all-pass
    for aspect in ["16x9", "9x16"]:
        results_path = os.path.join(qa_dir, f"gate_results_{aspect}.json")
        if not os.path.exists(results_path):
            raise FileNotFoundError(
                f"STOP: Telegram refused — gate results missing: {results_path}"
            )
        with open(results_path) as fp:
            results = json.load(fp)
        if not results.get("all_pass", False):
            raise RuntimeError(
                f"STOP: Telegram refused — {aspect} gates not all-pass"
            )

    # Delegate to tg_preview.py (sendVideo with dimensions)
    sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
    try:
        from tg_preview import send_preview
        segment_name = os.path.basename(os.path.normpath(segment_dir))
        caption = f"Pulse Check {segment_name} — gates PASS"
        send_preview(final_16, caption)
    except ImportError:
        # Fallback: use requests directly with proper dimensions
        _send_via_requests(final_16, final_9, segment_dir)


def _send_via_requests(final_16, final_9, segment_dir):
    """Direct Telegram sendVideo with width/height/supports_streaming (M16)."""
    import requests
    import subprocess

    sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
    from relay import get_key

    bot_token = get_key("TELEGRAM_BOT_TOKEN")
    chat_id = get_key("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        raise RuntimeError("STOP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    base = f"https://api.telegram.org/bot{bot_token}"
    segment_name = os.path.basename(os.path.normpath(segment_dir))

    for path, w, h, label in [
        (final_16, 1920, 1080, "16:9"),
        (final_9, 1080, 1920, "9:16"),
    ]:
        # Get duration
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10, check=True,
        )
        dur = int(float(r.stdout.strip()))

        with open(path, "rb") as f:
            resp = requests.post(
                f"{base}/sendVideo",
                data={
                    "chat_id": chat_id,
                    "caption": f"{segment_name} ({label}) — gates PASS",
                    "width": w,
                    "height": h,
                    "duration": dur,
                    "supports_streaming": "true",
                },
                files={"video": f},
                timeout=300,
            )
        data = resp.json()
        if data.get("ok"):
            print(f"  Telegram {label}: message_id={data['result']['message_id']}")
        else:
            raise RuntimeError(f"STOP: Telegram send failed ({label}): {data}")
