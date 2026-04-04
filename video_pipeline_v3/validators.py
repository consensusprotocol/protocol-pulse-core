"""Pipeline Reliability Engine — Input validation, retry, and sanitization.

Every JSON file read, every API response parsed, every stage attempt
goes through these validators. Fail fast on bad input, retry on transient
errors, reset corrupt files to known-good defaults.
"""
import json
import logging
import os
import time
from functools import wraps

logger = logging.getLogger("validators")


# ═══════════════════════════════════════════════════════════════════════
# 1. JSON FILE VALIDATION
# ═══════════════════════════════════════════════════════════════════════

def validate_json_file(path, expected_type=dict, required_keys=None):
    """Validate JSON file format. Auto-resets corrupt files.

    Returns:
        (data, errors): Tuple of parsed data and list of error strings.
    """
    errors = []
    if not os.path.exists(path):
        return expected_type(), [f"File not found: {path}"]
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        default = expected_type()
        with open(path, "w") as f:
            json.dump(default, f, indent=2)
        return default, [f"Malformed JSON in {path}: {e} — reset to default"]
    if not isinstance(data, expected_type):
        default = expected_type()
        with open(path, "w") as f:
            json.dump(default, f, indent=2)
        return default, [f"Wrong type in {path}: expected {expected_type.__name__}, got {type(data).__name__} — reset"]
    if required_keys:
        missing = [k for k in required_keys if k not in data]
        if missing:
            for k in missing:
                data[k] = [] if k == "episodes" else None
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            errors.append(f"Missing keys in {path}: {missing} — added defaults")
    return data, errors


# ═══════════════════════════════════════════════════════════════════════
# 2. CLIP RESPONSE VALIDATION
# ═══════════════════════════════════════════════════════════════════════

def validate_clip_response(result):
    """Validate and sanitize Claude clip selection response.

    Handles: list responses, missing fields, wrong types, rank assignment.
    Returns: (sanitized_result, errors)
    """
    errors = []
    if isinstance(result, list):
        result = {"clips": result, "episode_title": "Pulse Check", "cold_open": ""}
        errors.append("Response was list, wrapped to dict")
    if not isinstance(result, dict):
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}, ["Result is not dict or list"]

    clips = result.get("clips", [])
    if not isinstance(clips, list):
        clips = []
        errors.append(f"clips field was {type(clips).__name__}, reset to []")

    valid_clips = []
    for i, c in enumerate(clips):
        if not isinstance(c, dict):
            errors.append(f"Clip {i} is {type(c).__name__}, skipped")
            continue
        if "video_id" not in c:
            errors.append(f"Clip {i} missing video_id, skipped")
            continue
        c.setdefault("rank", i + 1)
        c.setdefault("channel", "Unknown")
        c.setdefault("start_seconds", 0)
        c.setdefault("end_seconds", 30)
        c.setdefault("quote", "")
        c.setdefault("why", "")
        c.setdefault("host_setup", "")
        c.setdefault("host_react", "")
        valid_clips.append(c)

    result["clips"] = valid_clips
    result.setdefault("episode_title", "Pulse Check")
    result.setdefault("cold_open", "")
    return result, errors


# ═══════════════════════════════════════════════════════════════════════
# 3. API RESPONSE PARSING
# ═══════════════════════════════════════════════════════════════════════

def validate_api_response(text):
    """Strip markdown fences and parse JSON from LLM response.

    Returns: (parsed_data, errors)
    """
    import re
    if not text or not text.strip():
        return None, ["Empty response"]

    stripped = text.strip()
    # Strip markdown fences
    if "```json" in stripped:
        stripped = stripped.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in stripped:
        stripped = stripped.split("```", 1)[1].split("```", 1)[0].strip()

    # Try direct parse
    try:
        return json.loads(stripped), []
    except json.JSONDecodeError:
        pass

    # Try extracting the outermost JSON object
    # Find first { and last }
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        try:
            return json.loads(stripped[first_brace:last_brace + 1]), []
        except json.JSONDecodeError:
            pass

    # Try extracting outermost JSON array
    first_bracket = stripped.find("[")
    last_bracket = stripped.rfind("]")
    if first_bracket >= 0 and last_bracket > first_bracket:
        try:
            return json.loads(stripped[first_bracket:last_bracket + 1]), []
        except json.JSONDecodeError:
            pass

    return None, [f"Could not parse JSON (first 200 chars): {text[:200]}"]


# ═══════════════════════════════════════════════════════════════════════
# 4. RETRY WITH BACKOFF
# ═══════════════════════════════════════════════════════════════════════

def retry_stage(max_retries=3, backoff_seconds=5, stage_name=None):
    """Decorator that retries a stage function on failure with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = stage_name or func.__name__
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Stage {name} failed (attempt {attempt}/{max_retries}): {e}")
                    if attempt < max_retries:
                        wait = backoff_seconds * attempt
                        logger.info(f"Retrying {name} in {wait}s...")
                        time.sleep(wait)
                    else:
                        logger.error(f"Stage {name} FAILED after {max_retries} attempts")
                        raise
        return wrapper
    return decorator
