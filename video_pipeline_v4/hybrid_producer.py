#!/usr/bin/env python3
"""
Hybrid Producer — V3 content + V4 Remotion design.

Reads the latest v3 episode_manifest.json (or WINNER_RECIPE.json for path),
extracts real content (TTS audio, partner clips, social cards, charts, timing),
maps them into a v4 episode_spec.json, and renders with Remotion.

Output: video_pipeline_v4/output/YYYY-MM-DD/pulse_check_v4_hybrid_YYYYMMDD.mp4
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

V3_BASE = Path(__file__).parent.parent / "video_pipeline_v3"
V4_BASE = Path(__file__).parent
REMOTION_DIR = V4_BASE / "remotion"
OUTPUT_DIR = V4_BASE / "output"
PUBLIC_DIR = REMOTION_DIR / "public"
# v3 assets are already symlinked at public/assets
DATA_DIR = PUBLIC_DIR / "data"

FPS = 30


def _find_latest_v3_output() -> Path:
    """Find the most recent v3 output directory with an episode_manifest.json."""
    output_dir = V3_BASE / "output"
    if not output_dir.exists():
        raise FileNotFoundError(f"v3 output dir not found: {output_dir}")

    # Sort date dirs descending
    date_dirs = sorted(
        [d for d in output_dir.iterdir()
         if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", d.name)],
        key=lambda d: d.name,
        reverse=True,
    )
    for d in date_dirs:
        manifest = d / "episode_manifest.json"
        if manifest.exists():
            return d
    raise FileNotFoundError("No v3 output directory with episode_manifest.json found")


def _copy_to_public(src_path: str, subdir: str) -> str:
    """Copy a v3 file into Remotion public/data/ and return the public-relative path."""
    src = Path(src_path)
    if not src.exists():
        return ""
    dest_dir = DATA_DIR / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
        shutil.copy2(src, dest)
    return f"/data/{subdir}/{src.name}"


def _parse_btc_price(price_str: str) -> int:
    """Parse '$66,295' → 66295."""
    cleaned = re.sub(r"[^\d]", "", price_str)
    return int(cleaned) if cleaned else 0


def build_hybrid_spec(v3_dir: Path = None) -> dict:
    """Build a v4 episode_spec from v3 manifest content."""
    if v3_dir is None:
        v3_dir = _find_latest_v3_output()

    manifest_path = v3_dir / "episode_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    date_str = manifest.get("episode_id", datetime.now().strftime("%Y-%m-%d"))
    btc_price = _parse_btc_price(manifest.get("btc_price", "$0"))

    # Try to load signals for fear_greed / hashrate
    signals_path = V4_BASE.parent / "data" / "signals.json"
    signals = {}
    if signals_path.exists():
        signals = json.loads(signals_path.read_text())

    fear_greed_raw = signals.get("fear_greed", {})
    hashrate_raw = signals.get("hashrate", {})

    spec = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hybrid": True,
        "v3_source": str(manifest_path),
        "btc_price": btc_price,
        "fear_greed": {
            "value": fear_greed_raw.get("value", 50),
            "label": fear_greed_raw.get("label", "Neutral"),
        },
        "hashrate": hashrate_raw.get("value", 0) if isinstance(hashrate_raw, dict) else 0,
        "segments": [],
    }

    v3_segments = manifest.get("segments", [])

    for seg in v3_segments:
        seg_type = seg["type"]
        duration = seg.get("duration_sec", 0)

        # Copy audio to public dir
        audio_pub = ""
        if seg.get("audio_path") and os.path.exists(seg["audio_path"]):
            audio_pub = _copy_to_public(seg["audio_path"], "audio")

        # Map v3 segment types → v4 segment types
        if seg_type == "cold_open":
            pip_pub = ""
            if seg.get("pip_source") and os.path.exists(seg["pip_source"]):
                pip_pub = _copy_to_public(seg["pip_source"], "clips")
            spec["segments"].append({
                "type": "cold_open",
                "duration_seconds": duration,
                "narration_audio": audio_pub,
            })

        elif seg_type == "title_sequence":
            # Map to a short narration intro
            spec["segments"].append({
                "type": "narration",
                "duration_seconds": duration,
                "topic": "intro",
            })

        elif seg_type == "narration_setup":
            pip_pub = ""
            if seg.get("pip_source") and os.path.exists(seg["pip_source"]):
                pip_pub = _copy_to_public(seg["pip_source"], "clips")

            if pip_pub:
                # Has a clip → PIP scene
                channel = ""
                if seg.get("lower_third"):
                    channel = seg["lower_third"].get("channel", "")
                spec["segments"].append({
                    "type": "pip",
                    "duration_seconds": duration,
                    "narration_audio": audio_pub,
                    "clip_path": pip_pub,
                    "channel_name": channel,
                })
            else:
                # No clip → narration scene
                spec["segments"].append({
                    "type": "narration",
                    "duration_seconds": duration,
                    "narration_audio": audio_pub,
                    "topic": "analysis",
                })

        elif seg_type == "partner_clip":
            clip_pub = ""
            clip_src = seg.get("video_path") or seg.get("audio_path", "")
            if clip_src and os.path.exists(clip_src):
                clip_pub = _copy_to_public(clip_src, "clips")
            channel = ""
            if seg.get("lower_third"):
                channel = seg["lower_third"].get("channel", "")
            spec["segments"].append({
                "type": "pip",
                "duration_seconds": duration,
                "clip_path": clip_pub,
                "channel_name": channel,
            })

        elif seg_type == "social_card":
            card_data = seg.get("social_card_data", {}) or {}
            spec["segments"].append({
                "type": "social",
                "duration_seconds": duration,
                "narration_audio": audio_pub,
                "post_handle": card_data.get("handle", ""),
                "post_content": card_data.get("text", ""),
                "post_likes": card_data.get("likes", 0),
            })

        elif seg_type == "data":
            # Data segments → intelligence scene
            spec["segments"].append({
                "type": "intelligence",
                "duration_seconds": duration,
                "narration_audio": audio_pub,
                "chart_type": "price",
            })

        elif seg_type == "wrap":
            spec["segments"].append({
                "type": "narration",
                "duration_seconds": duration,
                "narration_audio": audio_pub,
                "topic": "wrap",
                "is_recap": True,
            })

        elif seg_type == "outro":
            spec["segments"].append({
                "type": "outro",
                "duration_seconds": max(duration, 8),
            })

        elif seg_type == "transition":
            # Skip — v4 adds its own GlitchCut transitions
            continue

        else:
            # Unknown type → narration fallback
            if duration > 0:
                spec["segments"].append({
                    "type": "narration",
                    "duration_seconds": duration,
                    "narration_audio": audio_pub,
                })

    # Ensure there's an outro
    if not spec["segments"] or spec["segments"][-1]["type"] != "outro":
        spec["segments"].append({"type": "outro", "duration_seconds": 10})

    total_dur = sum(s["duration_seconds"] for s in spec["segments"])
    spec["total_duration_sec"] = total_dur
    spec["total_frames"] = int(total_dur * FPS)
    spec["total_segments"] = len(spec["segments"])

    return spec


def hybrid_render(spec: dict = None, test: bool = False) -> str:
    """Render the hybrid spec via Remotion."""
    if spec is None:
        spec = build_hybrid_spec()

    date_str = spec["date"]
    out_dir = OUTPUT_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(out_dir / f"pulse_check_v4_hybrid_{date_str.replace('-', '')}.mp4")

    # Write spec for Remotion
    spec_dest = PUBLIC_DIR / "episode_spec.json"
    spec_dest.write_text(json.dumps(spec, indent=2))

    props_file = PUBLIC_DIR / "render_props.json"
    props_file.write_text(json.dumps({"spec": spec}))

    cmd = [
        "npx", "remotion", "render",
        "PulseCheck", output_path,
        "--props", str(props_file.resolve()),
        "--codec", "h264",
        "--crf", "17",
        "--fps", "30",
        "--width", "1920",
        "--height", "1080",
        "--concurrency", "8",
        "--timeout", "120000",
    ]

    if test:
        cmd += ["--frames", "0-89"]
        print("[hybrid] TEST MODE: 90 frames only")

    print(f"[hybrid] Rendering {len(spec['segments'])} segments, ~{spec['total_duration_sec']:.0f}s...")
    print(f"[hybrid] Output: {output_path}")

    result = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print("HYBRID RENDER FAILED:")
        print(result.stderr[-3000:] if len(result.stderr) > 3000 else result.stderr)
        sys.exit(1)

    size_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0
    print(f"[hybrid] Complete: {output_path} ({size_mb:.1f} MB)")
    return output_path


def hybrid_generate():
    """Entry point for generate_spec.py --hybrid flag."""
    spec = build_hybrid_spec()
    spec_path = V4_BASE / "episode_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2))
    print(f"[hybrid] Spec written: {spec_path}")
    print(f"[hybrid] {spec['total_segments']} segments, ~{spec['total_duration_sec']:.0f}s")
    print(f"[hybrid] Source: {spec['v3_source']}")
    return str(spec_path)


if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    spec_only = "--spec-only" in sys.argv

    spec = build_hybrid_spec()

    if spec_only:
        hybrid_generate()
    else:
        hybrid_render(spec, test=test_mode)
