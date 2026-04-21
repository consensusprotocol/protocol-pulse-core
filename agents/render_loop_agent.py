#!/usr/bin/env python3
"""render_loop_agent.py — The Orchestrator.

Consumes:
  - fix_requested  (from SENTINEL)
  - archive_updated (from ARCHIVIST, held as rolling context)

On fix_requested:
  1. Read failing_dims → map each to (target_file, function_name) tuples via DIMENSION_MAP
  2. Track fix history so the same dim isn't retried forever
  3. Emit fix_approved → target: render_loop (the external fix loop daemon) describing
     the proposed change. This is the hand-off to render_improvement_loop.py.
  4. On 3 consecutive same-dim fix requests: escalate via Telegram "human review needed"

On archive_updated:
  Just cache the latest 7-day insights in state so future fix decisions can factor them.

Budget: one optional Qwen validation call per fix_requested. Never fatal if Ollama is down.
"""
import json
import logging
import os
import sys

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from base_agent import BaseAgent
from event_bus import save_state, load_state, log_metric, emit
import telegram


# ── DIMENSION_MAP ──────────────────────────────────────────────────────────
# Authoritative copy lives in render_improvement_loop.py. We import if available
# so the two stay in lockstep; fall back to a verified snapshot otherwise.
try:
    _repo_root = os.path.dirname(_AGENT_DIR)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from render_improvement_loop import DIMENSION_MAP as _IMPORTED_MAP  # type: ignore
    DIMENSION_MAP = _IMPORTED_MAP
except Exception:
    DIMENSION_MAP = {
        "freeze_check": [("video_pipeline_v3/clip_extractor.py", "generate_clip"),
                         ("video_pipeline_v3/assembler.py", "build_scene")],
        "true_peak_check": [("video_pipeline_v3/assembler.py", "apply_loudnorm"),
                            ("video_pipeline_v3/assembler.py", "final_mix")],
        "loudness_check": [("video_pipeline_v3/assembler.py", "apply_loudnorm")],
        "silence_check": [("video_pipeline_v3/tts_engine.py", "generate_audio"),
                          ("video_pipeline_v3/assembler.py", "concat_audio")],
        "host_authenticity": [("video_pipeline_v3/assembler.py", "generate_host_segment"),
                              ("oracle/avatar_server.py", "generate_video")],
        "visual_polish": [("video_pipeline_v3/assembler.py", "build_scene"),
                          ("video_pipeline_v3/clip_extractor.py", "generate_clip")],
        "no_artifacts": [("video_pipeline_v3/assembler.py", "preflight_check")],
        "audio_quality": [("video_pipeline_v3/assembler.py", "final_mix")],
        "black_frames_check": [("video_pipeline_v3/assembler.py", "concat_segments")],
        "script_quality": [("video_pipeline_v3/script_writer.py", "write_script")],
        "cold_open_hook": [("video_pipeline_v3/script_writer.py", "write_cold_open")],
        "episode_title": [("video_pipeline_v3/daily_producer.py", "generate_title")],
        "narrative_arc": [("video_pipeline_v3/script_writer.py", "write_script")],
        "music_mix": [("video_pipeline_v3/assembler.py", "mix_music")],
        "transitions": [("video_pipeline_v3/assembler.py", "apply_transitions")],
        "clip_relevance": [("video_pipeline_v3/clip_extractor.py", "score_clips")],
        "pacing": [("video_pipeline_v3/script_writer.py", "write_script"),
                   ("video_pipeline_v3/assembler.py", "build_scene")],
        "subtitle_accuracy": [("video_pipeline_v3/assembler.py", "generate_subtitles")],
        "color_grading": [("video_pipeline_v3/assembler.py", "apply_color_grade")],
        "thumbnail_quality": [("video_pipeline_v3/daily_producer.py", "generate_thumbnail")],
    }


ESCALATE_AFTER = 3  # identical consecutive fix_requested on same dim → human


def _qwen_validate(dim, targets):
    """Optional Qwen sanity check. Returns validation note string or ''."""
    ollama_host = os.environ.get("OLLAMA_HOST", "").strip()
    if not ollama_host:
        return ""
    try:
        import requests
        prompt = (
            f"Failing dimension: {dim}. Candidate fix targets: {targets}. "
            "In one sentence, state whether this is the right file to patch "
            "or name a likelier target."
        )
        resp = requests.post(
            f"{ollama_host.rstrip('/')}/api/generate",
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False},
            timeout=15,
        )
        if resp.status_code == 200:
            return (resp.json().get("response") or "").strip()[:240]
    except Exception:
        return ""
    return ""


class RenderLoopAgent(BaseAgent):
    name = "render_loop"
    consumes = ["fix_requested", "archive_updated"]

    def handle(self, event):
        if event["type"] == "archive_updated":
            self._handle_archive(event)
        elif event["type"] == "fix_requested":
            self._handle_fix(event)
        else:
            self.logger.warning(f"unexpected event type {event['type']}")

    def _handle_archive(self, event):
        payload = event.get("payload", {}) or {}
        prev = load_state(self.name) or {}
        prev["last_archive_insights"] = {
            "avg_score_7d": payload.get("avg_score_7d"),
            "episodes_7d": payload.get("episodes_7d"),
            "channels_overused": payload.get("channels_overused", []),
            "top_performing_topics": payload.get("top_performing_topics", []),
        }
        save_state(
            self.name,
            prev,
            last_action="archive_cached",
            self_eval=1.0,
            notes=f"avg7d={payload.get('avg_score_7d')}",
        )

    def _handle_fix(self, event):
        payload = event.get("payload", {}) or {}
        failing_dims = payload.get("failing_dims") or []
        failing_dims = [d for d in failing_dims if d]
        episode_date = payload.get("episode_date", "")
        score = int(payload.get("score", 0) or 0)

        prev = load_state(self.name) or {}
        history = prev.get("fix_history", []) or []
        escalations = prev.get("escalations", {}) or {}

        approved = []
        for dim in failing_dims:
            targets = DIMENSION_MAP.get(dim, [])
            if not targets:
                self.logger.warning(f"unknown dim {dim} — no DIMENSION_MAP entry")
                continue

            # 3 consecutive same-dim fix_requested → escalate instead of re-approving
            recent_dims = [h.get("dim") for h in history[-ESCALATE_AFTER:]]
            if recent_dims.count(dim) >= ESCALATE_AFTER - 1:
                telegram.send(
                    f"🚨 *Human review needed* — dim `{dim}` has failed "
                    f"{ESCALATE_AFTER}+ times in a row (episode {episode_date}, score {score}).\n"
                    f"Targets: {targets}"
                )
                escalations[dim] = int(escalations.get(dim, 0)) + 1
                self.logger.error(f"escalated dim={dim} to human review")
                history.append({
                    "dim": dim, "episode": episode_date, "score": score,
                    "action": "escalated", "targets": targets,
                })
                continue

            qwen_note = _qwen_validate(dim, targets)
            target_file, target_func = targets[0]
            description = (
                f"Patch {target_func}() in {target_file} to fix dim '{dim}' "
                f"(score {score} on episode {episode_date})."
            )
            if qwen_note:
                description += f" Qwen: {qwen_note}"

            fix_payload = {
                "episode_date": episode_date,
                "dim": dim,
                "fix_type": dim,
                "target_file": target_file,
                "target_function": target_func,
                "all_targets": targets,
                "description": description,
                "score": score,
                "qwen_note": qwen_note,
            }

            # Broadcast — external render_improvement_loop.py or future dispatcher picks up.
            emit(self.name, "fix_approved", fix_payload)
            approved.append(fix_payload)
            history.append({
                "dim": dim, "episode": episode_date, "score": score,
                "action": "approved", "targets": targets,
            })
            self.logger.info(f"approved fix for dim={dim} → {target_file}:{target_func}")

        # Keep history bounded
        history = history[-50:]

        log_metric(self.name, "fixes_approved", float(len(approved)), f"dims={len(failing_dims)}")

        save_state(
            self.name,
            {
                "last_fix_request": episode_date,
                "last_failing_dims": failing_dims,
                "last_approved_count": len(approved),
                "fix_history": history,
                "escalations": escalations,
                "last_archive_insights": prev.get("last_archive_insights"),
            },
            last_action=f"approved_{len(approved)}_of_{len(failing_dims)}",
            self_eval=1.0 if approved else 0.5,
            notes=f"approved={[a['dim'] for a in approved]} escalations={escalations}",
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s %(message)s")
    handled = RenderLoopAgent().cycle()
    print(f"render_loop: {handled} event(s) handled; dims={len(DIMENSION_MAP)}")
