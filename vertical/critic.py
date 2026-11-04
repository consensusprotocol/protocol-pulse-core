"""
vertical/critic.py -- Grok vision critic for composed vertical frames.

For each rendered shot, sends 2 frames to Grok vision (model grok-4, xAI API)
with fixed diagnostic questions. Cost-logs every call to critic_costs.jsonl.

Model fallback chain: grok-4 -> grok-4-0709 -> grok-3. Skip on 402/429.
"""

import os
import json
import time
import base64
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone

logger = logging.getLogger("vertical.critic")

_VERT_DIR = os.path.dirname(os.path.abspath(__file__))
_COST_LOG = os.path.join(_VERT_DIR, "critic_costs.jsonl")
_API_URL  = "https://api.x.ai/v1/chat/completions"
_MODELS   = ["grok-4", "grok-4-0709", "grok-3"]
_TIMEOUT  = 90

# HTTP status codes that trigger model fallback
_SKIP_CODES = {402, 429}

# ── Prompt ───────────────────────────────────────────────────────────────────

_CRITIC_PROMPT = """\
You are a QA vision critic for a vertical (9:16) video reframing pipeline.
Examine the provided frame and answer EVERY question in the JSON format below.
Only state what you can verify from the image. If uncertain, say so.

Questions (from Grok design review v1):
1. tiles_visible: Which exact source tiles (speaker boxes) are visible? List them as top-to-bottom or left-to-right labels. (list of strings, e.g. ["tile_0", "tile_1"])
2. tile_missing: Is any tile completely missing that you would expect from a multi-person layout? (true/false)
3. debug_artifacts: Are there any debug rectangles, colored bounding boxes, or text artifacts (like "LAYOUT: 2up" or coordinate labels) that don't belong in a final render? (true/false)
4. face_cut_off: Is any face cut off at the 9:16 frame edges (top/bottom/left/right)? (true/false)
5. layout_id: Which layout does this frame show?
   (a) single face-centered crop
   (b) two stacked bands
   (c) three stacked bands
   (d) full 16:9 top + guest column below
   (e) none / unrecognizable

Respond with ONLY valid JSON:
{
  "tiles_visible": ["tile_0", "tile_1"],
  "tile_missing": false,
  "debug_artifacts": false,
  "face_cut_off": false,
  "layout_id": "b"
}"""


# ── Key loader ───────────────────────────────────────────────────────────────

def _load_key() -> str:
    env_path = os.path.expanduser("~/protocol_pulse/.env")
    for line in open(env_path):
        if "=" in line and not line.startswith("#"):
            k, v = line.rstrip("\n").split("=", 1)
            if k.strip() == "XAI_API_KEY_MEDLEY":
                return v.strip().strip('"').strip("'")
    raise RuntimeError("XAI_API_KEY_MEDLEY not found in ~/protocol_pulse/.env")


# ── Image encoding ───────────────────────────────────────────────────────────

def _encode_image(path: str) -> str:
    """Read an image file, return base64 JPEG string."""
    import cv2
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf.tobytes()).decode("ascii")


# ── API call with fallback ───────────────────────────────────────────────────

def _call_grok_vision(b64_img1: str, b64_img2: str, key: str) -> dict:
    """Call Grok vision with two frames. Returns (parsed_json, model_used,
    input_tokens, output_tokens). Falls back through model chain."""

    content_blocks = [
        {"type": "image_url",
         "image_url": {"url": f"data:image/jpeg;base64,{b64_img1}"}},
        {"type": "image_url",
         "image_url": {"url": f"data:image/jpeg;base64,{b64_img2}"}},
        {"type": "text", "text": _CRITIC_PROMPT},
    ]

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for model in _MODELS:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": content_blocks}],
            "response_format": {"type": "json_object"},
        }
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(_API_URL, payload, headers)

        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            usage = raw.get("usage", {})
            text = raw["choices"][0]["message"]["content"]
            parsed = json.loads(text)
            return {
                "result": parsed,
                "model": model,
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            }
        except urllib.error.HTTPError as e:
            code = e.code
            logger.warning(f"[CRITIC] {model} returned HTTP {code}")
            if code in _SKIP_CODES:
                continue  # try next model
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.warning(f"[CRITIC] {model} network error: {e}")
            continue

    raise RuntimeError("All Grok models exhausted (402/429 or network error)")


# ── Cost logger ──────────────────────────────────────────────────────────────

def _log_cost(shot_id: str, model: str, input_tokens: int,
              output_tokens: int, passed: bool):
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model,
        "shot_id": shot_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "pass": passed,
    }
    with open(_COST_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Validation logic ────────────────────────────────────────────────────────

_LAYOUT_MAP = {
    "solo":     "a",
    "2-up":     "b",
    "3-up":     "c",
    "full+col": "d",
}


def _validate_response(resp: dict, shot: dict) -> dict:
    """Compare Grok response against shot_map data.
    Returns {pass, tiles_ok, crop_ok, artifacts_ok, composition_ok, issues}."""
    issues = []

    # --- tiles_ok: all expected tiles visible, none missing ---
    expected_tiles = len(shot.get("tiles", []))
    visible_tiles = resp.get("tiles_visible", [])
    tile_missing = resp.get("tile_missing", True)
    tiles_ok = len(visible_tiles) >= expected_tiles and not tile_missing
    if not tiles_ok:
        issues.append(f"tiles: expected {expected_tiles}, visible={visible_tiles}, missing={tile_missing}")

    # --- crop_ok: no face cut off at 9:16 edges ---
    face_cut = resp.get("face_cut_off", True)
    crop_ok = not face_cut
    if not crop_ok:
        issues.append("face cut off at 9:16 edge")

    # --- artifacts_ok: no debug boxes/text ---
    artifacts = resp.get("debug_artifacts", True)
    artifacts_ok = not artifacts
    if not artifacts_ok:
        issues.append("debug artifacts visible in frame")

    # --- composition_ok: layout_id matches expected ---
    expected_layout = shot.get("layout", "")
    expected_comp = _LAYOUT_MAP.get(expected_layout, "")
    actual_comp = resp.get("layout_id", "e")
    composition_ok = (actual_comp == expected_comp) if expected_comp else True
    if not composition_ok:
        issues.append(f"layout: expected '{expected_comp}' "
                      f"({expected_layout}), got '{actual_comp}'")

    passed = tiles_ok and crop_ok and artifacts_ok and composition_ok
    return {
        "pass": passed,
        "tiles_ok": tiles_ok,
        "crop_ok": crop_ok,
        "artifacts_ok": artifacts_ok,
        "composition_ok": composition_ok,
        "issues": issues,
    }


# ── Public API ───────────────────────────────────────────────────────────────

def critique_shot(shot: dict, frame1_path: str, frame2_path: str,
                  work_dir: str) -> dict:
    """Critique one shot by sending two frames to Grok vision.

    Args:
        shot:        shot dict with shot_id, layout, tiles, faces, etc.
        frame1_path: path to first sample frame (JPEG/PNG).
        frame2_path: path to second sample frame (JPEG/PNG).
        work_dir:    working directory (unused currently, reserved).

    Returns:
        {shot_id, pass, faces_ok, crop_ok, artifacts_ok, composition_ok,
         issues, model, raw_response}
    """
    shot_id = shot.get("shot_id", "unknown")

    try:
        key = _load_key()
        b64_1 = _encode_image(frame1_path)
        b64_2 = _encode_image(frame2_path)
        api_resp = _call_grok_vision(b64_1, b64_2, key)

        validation = _validate_response(api_resp["result"], shot)
        _log_cost(shot_id, api_resp["model"],
                  api_resp["input_tokens"], api_resp["output_tokens"],
                  validation["pass"])

        return {
            "shot_id": shot_id,
            "pass": validation["pass"],
            "tiles_ok": validation["tiles_ok"],
            "crop_ok": validation["crop_ok"],
            "artifacts_ok": validation["artifacts_ok"],
            "composition_ok": validation["composition_ok"],
            "issues": validation["issues"],
            "model": api_resp["model"],
            "raw_response": api_resp["result"],
        }

    except Exception as e:
        logger.error(f"[CRITIC] Shot {shot_id} critique failed: {e}")
        return {
            "shot_id": shot_id,
            "pass": False,
            "tiles_ok": False,
            "crop_ok": False,
            "artifacts_ok": False,
            "composition_ok": False,
            "issues": [f"critique error: {e}"],
            "model": None,
            "raw_response": None,
        }


def critique_all(shots: list, composed_dir: str, work_dir: str) -> dict:
    """Critique all shots. For each shot, picks frame at 25% and 75% of the
    composed frame sequence in composed_dir.

    Expects composed_dir to contain per-shot subdirectories or frame files
    named: {shot_id}_frame_{N:06d}.jpg

    Args:
        shots:        list of shot dicts.
        composed_dir: directory containing composed frame images.
        work_dir:     working directory for temp files.

    Returns:
        {overall_pass, shots: [critique_results...], summary}
    """
    results = []
    pass_count = 0
    fail_count = 0

    for shot in shots:
        shot_id = shot.get("shot_id", "unknown")

        # Find frames for this shot
        frames = _find_shot_frames(shot_id, composed_dir)
        if len(frames) < 2:
            logger.warning(f"[CRITIC] Shot {shot_id}: fewer than 2 frames "
                           f"found in {composed_dir}, skipping")
            results.append({
                "shot_id": shot_id,
                "pass": False,
                "issues": [f"insufficient frames ({len(frames)})"],
            })
            fail_count += 1
            continue

        # Pick frames at 25% and 75%
        idx_25 = len(frames) // 4
        idx_75 = (3 * len(frames)) // 4
        f1 = frames[idx_25]
        f2 = frames[idx_75]

        result = critique_shot(shot, f1, f2, work_dir)
        results.append(result)

        if result["pass"]:
            pass_count += 1
        else:
            fail_count += 1

    overall = fail_count == 0 and pass_count > 0
    total = pass_count + fail_count
    summary = (f"{pass_count}/{total} shots passed"
               if total > 0 else "no shots evaluated")

    logger.info(f"[CRITIC] Critique complete: {summary} "
                f"(overall={'PASS' if overall else 'FAIL'})")

    return {
        "overall_pass": overall,
        "shots": results,
        "summary": summary,
    }


# ── Frame discovery ──────────────────────────────────────────────────────────

def _find_shot_frames(shot_id: str, composed_dir: str) -> list:
    """Find composed frame files for a given shot_id.
    Looks for files matching {shot_id}_frame_*.jpg or {shot_id}_*.png."""
    if not os.path.isdir(composed_dir):
        return []

    # Check for a shot-specific subdirectory first
    shot_subdir = os.path.join(composed_dir, shot_id)
    if os.path.isdir(shot_subdir):
        search_dir = shot_subdir
        prefix = ""
    else:
        search_dir = composed_dir
        prefix = f"{shot_id}_"

    frames = []
    for fname in sorted(os.listdir(search_dir)):
        if not fname.startswith(prefix) and prefix:
            continue
        lower = fname.lower()
        if lower.endswith((".jpg", ".jpeg", ".png")):
            frames.append(os.path.join(search_dir, fname))

    return frames
