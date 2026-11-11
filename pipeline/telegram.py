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


# ==============================================================
# run_fresh drops (mission 4a / DEC-8, 2026-11-11): both aspects, the verdict in the caption
# ==============================================================

HOLD_OK = "HOLD FOR APPROVAL - all gates passed, no waivers"
REVIEW = "REVIEW ONLY"
CAPTION_MAX = 1024                       # Telegram caption limit
DIMS = {"16x9": (1920, 1080), "9x16": (1080, 1920)}


def gate_status(run_dir):
    """(all_pass, failing) from GATE_REPORT.json: every row of both formats must read PASS. Placeholder rows
    '<gate>(run_gates)' point to the real row (G11 parity in 9x16) and are not results themselves."""
    with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
        rows = json.load(f)["rows"]
    failing = [f"{k} ({fmt}): {v[:60]}" for fmt in ("16x9", "9x16") for k, v in rows.get(fmt, {}).items()
               if not k.endswith("(run_gates)") and not str(v).startswith("PASS")]
    if not rows.get("16x9") or not rows.get("9x16"):
        failing.append("gate rows missing for a format")
    return not failing, failing


def build_caption(run_dir, fmt, option=None):
    """Verdict line first: HOLD FOR APPROVAL only when every gate passed with no waiver AND the
    automated verification pack is complete; otherwise REVIEW ONLY with the failing list."""
    import vertical_layout
    ok, failing = gate_status(run_dir)
    vpath = os.path.join(run_dir, "VERIFY", "VERIFICATION.json")
    pack_ok = os.path.exists(vpath) and json.load(open(vpath)).get("complete") is True
    if not pack_ok:
        failing.append("verification pack missing or incomplete")
    with open(os.path.join(run_dir, "edl.json")) as f:
        edl = json.load(f)
    head = HOLD_OK if (ok and pack_ok) else f"{REVIEW} - {len(failing)} failing"
    if option:
        head = f"OPTION {option} (transition choice, not a release candidate) | {head}"
    lines = [head, f"{os.path.basename(os.path.normpath(run_dir))} | {fmt} {DIMS[fmt][0]}x{DIMS[fmt][1]}",
             f"Story: {edl.get('topic', '')}",
             "Clips: " + ", ".join([edl["hook"].get("channel", "?")] + [c.get("channel", "?") for c in edl.get("clips", [])])]
    note = vertical_layout.layout_note(edl) if fmt == "9x16" else ""
    if note:
        lines.append(note)
    if failing:
        lines.append("Failing: " + "; ".join(failing))
    cap = "\n".join(lines)
    return cap if len(cap) <= CAPTION_MAX else cap[:CAPTION_MAX - 20] + " ...(see GATE_REPORT)"


def _dims(path):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True, check=True, timeout=30)
    j = json.loads(r.stdout)
    return int(j["streams"][0]["width"]), int(j["streams"][0]["height"]), float(j["format"]["duration"])


def deliver_run(run_dir, option=None, send=None, sheets=True):
    """Send a run_fresh run's two finals to the approval chat (never publishing), each with its caption,
    plus (sheets=True) the verification pack's contact sheets; transition options send the two finals only.
    send(kind, path, fields) -> message_id (tests inject it).
    Writes TELEGRAM_DELIVERY.json. Raises on a missing/misdimensioned final (fail closed)."""
    import hashlib
    send = send or _send_bot_api
    finals = {"16x9": os.path.join(run_dir, "out", "segment.mp4"),
              "9x16": os.path.join(run_dir, "out", "segment_vertical.mp4")}
    record = {"option": option, "messages": []}
    for fmt, path in finals.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"STOP: final output missing: {path}")
        w, h, dur = _dims(path)
        if (w, h) != DIMS[fmt]:
            raise RuntimeError(f"STOP: {fmt} final is {w}x{h}, expected {DIMS[fmt][0]}x{DIMS[fmt][1]}")
        cap = build_caption(run_dir, fmt, option)
        mid = send("video", path, {"caption": cap, "width": w, "height": h, "duration": int(round(dur)),
                                   "supports_streaming": "true"})
        record["messages"].append({"format": fmt, "message_id": mid, "caption": cap,
                                   "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()})
    for fmt in (("16x9", "9x16") if sheets else ()):        # one contact sheet of the finished video per format
        p = os.path.join(run_dir, "qa", f"contact_sheet_{fmt}.jpg")
        if os.path.exists(p):
            kind = "photo" if _photo_ok(p) else "document"
            mid = send(kind, p, {"caption": f"contact sheet {fmt}: 2 s stills, +-3 frames at every boundary, "
                                            f"full-resolution credits" + (" and segment first frames" if fmt == "9x16" else "")})
            record["messages"].append({"sheet": os.path.basename(p), "message_id": mid, "as": kind})
    with open(os.path.join(run_dir, f"TELEGRAM_DELIVERY{'_' + option if option else ''}.json"), "w") as f:
        json.dump(record, f, indent=2)
    return record


PHOTO_MAX_BYTES = 9_500_000     # Telegram sendPhoto takes <= 10 MB; the margin keeps a near-limit sheet from a
                                # rejected send. Above it the sheet goes as a document: it still arrives, full size.


def _photo_ok(path):
    """Telegram sendPhoto limits: <= 10 MB (PHOTO_MAX_BYTES, with margin), width + height <= 10000,
    aspect ratio <= 20."""
    from PIL import Image
    try:
        w, h = Image.open(path).size
    except Exception:                       # unreadable image: send it as a document (never lose the delivery record)
        return False
    return os.path.getsize(path) <= PHOTO_MAX_BYTES and w + h <= 10000 and max(w, h) / max(1, min(w, h)) <= 20


def _send_bot_api(kind, path, fields):
    """One sendVideo / sendPhoto to the approval chat (M16 path; credentials never printed)."""
    import requests
    sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
    from relay import get_key
    tok, chat = get_key("TELEGRAM_BOT_TOKEN"), get_key("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        raise RuntimeError("STOP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
    method, field = {"video": ("sendVideo", "video"), "photo": ("sendPhoto", "photo"),
                     "document": ("sendDocument", "document")}[kind]
    with open(path, "rb") as fh:
        resp = requests.post(f"https://api.telegram.org/bot{tok}/{method}", data={"chat_id": chat, **fields},
                             files={field: fh}, timeout=600)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"STOP: Telegram {method} failed: {data.get('description')}")
    return data["result"]["message_id"]
