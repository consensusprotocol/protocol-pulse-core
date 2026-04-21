#!/usr/bin/env python3
"""sentinel_agent.py — The Quality Watchdog.

Consumes: grade_complete (handles only grade != 'A')

On each non-A grade:
  1. Identify failing dimensions (from payload.failing_dims, or inferred from score)
  2. Write /tmp/sentinel_alert_{episode_date}.json with {failing_dims, score, recommended_fix}
  3. Post Telegram alert
  4. Emit fix_requested → target: render_loop with the failing dims
  5. Save state {consecutive_fails, last_fail_date, known_failing_dims}

Budget: zero LLM calls by default. One optional local Qwen call when score < 70
and OLLAMA_HOST is set (never fails the cycle if Ollama is unreachable).
"""
import json
import logging
import os
import sys
import time

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from base_agent import BaseAgent
from event_bus import save_state, load_state, log_metric, emit
import telegram


# Map score ranges → likeliest failing dimensions (from quality_gate.py penalty model)
SCORE_INFERENCE = [
    (0, 30,  ["silence_check", "black_frames_check", "host_authenticity"]),
    (30, 50, ["true_peak_check", "loudness_check", "silence_check"]),
    (50, 75, ["visual_polish", "music_mix", "pacing"]),
    (75, 88, ["cold_open_hook", "script_quality", "narrative_arc"]),
]


def _infer_failing_dims(score):
    """Return a shortlist of failing dimensions based on score band."""
    for lo, hi, dims in SCORE_INFERENCE:
        if lo <= score < hi:
            return list(dims)
    return []


def _maybe_qwen_diagnose(score, failing_dims, output_path):
    """Optional local Qwen call. Returns recommended_fix string, or '' on failure.

    Only runs when score < 70 AND OLLAMA_HOST env is set. Never raises.
    """
    if score >= 70:
        return ""
    ollama_host = os.environ.get("OLLAMA_HOST", "").strip()
    if not ollama_host:
        return ""
    try:
        import requests  # noqa: F401
        import requests as _req
    except ImportError:
        return ""
    prompt = (
        "You are a Protocol Pulse video QC engineer. Episode scored "
        f"{score}/100. Failing dimensions: {', '.join(failing_dims) or 'unknown'}. "
        f"Output file: {os.path.basename(output_path) if output_path else 'n/a'}. "
        "Name the single most likely root cause in 15 words or less."
    )
    try:
        resp = _req.post(
            f"{ollama_host.rstrip('/')}/api/generate",
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False},
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = (data.get("response", "") or "").strip()
            return text[:240]
    except Exception:
        return ""
    return ""


class SentinelAgent(BaseAgent):
    name = "sentinel"
    consumes = ["grade_complete"]

    def handle(self, event):
        payload = event.get("payload", {}) or {}
        grade = payload.get("grade", "?")
        if grade == "A":
            self.logger.debug(f"A grade — sentinel ignoring event {event['id']}")
            return

        score = int(payload.get("score", 0) or 0)
        episode_date = payload.get("episode_date") or time.strftime("%Y-%m-%d")
        output_path = payload.get("output_path", "")

        failing_dims = payload.get("failing_dims") or _infer_failing_dims(score)
        failing_dims = [d for d in failing_dims if d]

        recommended = _maybe_qwen_diagnose(score, failing_dims, output_path)

        alert = {
            "episode_date": episode_date,
            "grade": grade,
            "score": score,
            "failing_dims": failing_dims,
            "recommended_fix": recommended,
            "output_path": output_path,
            "timestamp": time.time(),
        }
        alert_path = f"/tmp/sentinel_alert_{episode_date}.json"
        try:
            with open(alert_path, "w") as fh:
                json.dump(alert, fh, indent=2, default=str)
            self.logger.info(f"wrote sentinel alert {alert_path}")
        except Exception as exc:
            self.logger.error(f"alert write failed: {exc}")

        dims_str = ", ".join(failing_dims[:4]) if failing_dims else "unknown"
        msg = (
            f"⚠️ *Grade {grade}* ({score}/100) — {dims_str}. Auto-fix queued.\n"
            f"Episode: `{episode_date}`"
        )
        if recommended:
            msg += f"\n_Qwen_: {recommended}"
        telegram.send(msg)

        emit(self.name, "fix_requested", {
            "episode_date": episode_date,
            "score": score,
            "grade": grade,
            "failing_dims": failing_dims,
            "output_path": output_path,
            "recommended_fix": recommended,
            "sentinel_alert_path": alert_path,
        }, target="render_loop")

        prev = load_state(self.name) or {}
        consecutive_fails = int(prev.get("consecutive_fails", 0)) + 1
        known = prev.get("known_failing_dims", {}) or {}
        for dim in failing_dims:
            known[dim] = int(known.get(dim, 0)) + 1

        log_metric(self.name, "fail_score", float(score), f"grade={grade}")
        log_metric(self.name, "consecutive_fails", consecutive_fails)

        save_state(
            self.name,
            {
                "last_fail_date": episode_date,
                "last_score": score,
                "last_grade": grade,
                "consecutive_fails": consecutive_fails,
                "known_failing_dims": known,
                "last_alert_path": alert_path,
                "last_recommended_fix": recommended,
            },
            last_action=f"alert_{grade}_{score}",
            self_eval=score / 100.0,
            notes=f"dims={failing_dims} streak_fails={consecutive_fails}",
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s %(message)s")
    handled = SentinelAgent().cycle()
    print(f"sentinel: {handled} event(s) handled")
