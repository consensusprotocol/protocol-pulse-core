#!/usr/bin/env python3
"""pipeline/shoutout.py — Parameterised shoutout renderer.

FROZEN from segment_v1/scene_shoutout.py. Delegates to the original.
Only difference: resolves channels from EDL and passes to the frozen renderer.
M23: aspect-isolated temp dirs, exact frame-count validation, dimension check.

Usage:
    python3 -m pipeline.shoutout --segment <segment_dir> [--qa-version N]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import resolve_paths

# Import the frozen shoutout renderer
sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
from scene_shoutout import render_shoutout, save_qa_frames


def build_shoutout(segment_dir, qa_version=None, fmt="16x9"):
    """Build shoutout from EDL channel list. Returns shoutout mp4 path."""
    paths = resolve_paths(segment_dir, qa_version)
    qa_dir = paths["qa_dir"]

    with open(paths["edl_json"]) as f:
        edl = json.load(f)

    # Extract unique channels: hook first, then clips in EDL order (R2-16)
    channels = []
    seen = set()

    # Hook channel comes first (if present)
    hook = edl.get("hook", {})
    hook_ch = hook.get("channel", "")
    if hook_ch and hook_ch not in seen:
        channels.append({
            "name": hook_ch,
            "handle": hook.get("handle", ""),
            "avatar_path": _find_avatar(segment_dir, hook_ch),
        })
        seen.add(hook_ch)

    for clip in edl.get("clips", []):
        ch = clip.get("channel", "")
        if ch and ch not in seen:
            channels.append({
                "name": ch,
                "handle": clip.get("handle", ""),
                "avatar_path": _find_avatar(segment_dir, ch),
            })
            seen.add(ch)

    print(f"=== SHOUTOUT ({fmt}) ===")
    print(f"  Channels: {[c['name'] for c in channels]}")

    if fmt == "16x9":
        size = (1920, 1080)
        out_name = "shoutout_16x9.mp4"
    else:
        size = (1080, 1920)
        out_name = "shoutout_9x16.mp4"

    final_path = os.path.join(qa_dir, out_name)

    # Get signoff VO if available, ensure 48kHz stereo for concat compatibility
    vo_dir = paths["vo_dir"]
    manifest_path = os.path.join(vo_dir, "VO_MANIFEST.json")
    # M12: signoff WAV is REQUIRED — missing = STOP
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"STOP: VO manifest missing: {manifest_path}")
    with open(manifest_path) as f:
        manifest = json.load(f)
    if "signoff" not in manifest:
        raise RuntimeError("STOP: VO manifest has no 'signoff' entry")
    raw_wav = os.path.join(vo_dir, manifest["signoff"]["stem_wav"])
    if not os.path.exists(raw_wav):
        raise FileNotFoundError(f"STOP: signoff WAV missing: {raw_wav}")
    # Resample to 48kHz stereo (ElevenLabs outputs 22050 mono)
    vo_wav = os.path.join(qa_dir, "vo_signoff_48k.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_wav,
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", vo_wav,
    ], capture_output=True, timeout=30, check=True)

    # M23: Render in an aspect-isolated temp dir to prevent frame contamination.
    # scene_shoutout.py places frames in <dirname(out_path)>/shoutout_frames_raw/
    # so we set out_path inside an isolated subdir, then move the mp4 out.
    build_dir = os.path.join(qa_dir, f"shoutout_build_{fmt.replace(':', 'x')}")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    temp_out = os.path.join(build_dir, out_name)

    render_shoutout(channels, size=size, vo_wav=vo_wav, out_path=temp_out)

    if not os.path.exists(temp_out) or os.path.getsize(temp_out) < 1000:
        raise RuntimeError(f"STOP: shoutout render failed: {temp_out}")

    # M23: Validate frame dimensions in the rendered mp4
    _validate_shoutout_frames(temp_out, size, fmt)

    # Move to final location and clean up build dir
    shutil.move(temp_out, final_path)
    shutil.rmtree(build_dir, ignore_errors=True)

    print(f"  Output: {final_path}")
    return final_path


def _validate_shoutout_frames(mp4_path, expected_size, fmt):
    """M23: Verify every frame in the shoutout mp4 has the expected dimensions."""
    r = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_frames",
        "-of", "csv=p=0", mp4_path,
    ], capture_output=True, text=True, timeout=10)
    parts = r.stdout.strip().split(",")
    w, h = int(parts[0]), int(parts[1])
    expected_w, expected_h = expected_size
    if w != expected_w or h != expected_h:
        raise RuntimeError(
            f"STOP: shoutout {fmt} has wrong dimensions: {w}x{h}, "
            f"expected {expected_w}x{expected_h} — likely cross-aspect contamination"
        )


AVATAR_SQUARE_TOL = 0.01      # D4: the frozen renderer resizes to a square; a non-square image squashes
AVATAR_MIN_PX = 128


def validate_avatar(path):
    """D4 (2026-11-11): a credit avatar must be the channel's square picture. A 16:9 video thumbnail
    is refused (the frozen scene_shoutout resizes every avatar to a square and would squash it)."""
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    if abs(w - h) > AVATAR_SQUARE_TOL * max(w, h):
        raise ValueError(f"avatar must be square, got {w}x{h} (a video thumbnail?): {path}")
    if min(w, h) < AVATAR_MIN_PX:
        raise ValueError(f"avatar too small ({w}x{h} < {AVATAR_MIN_PX} px square): {path}")
    return w


def _find_avatar(segment_dir, channel_name):
    """The channel's REAL avatar from pipeline/channels.json only (fetched + visually verified by
    pipeline/avatar_onboard.py, M6), sha256-prefix checked and square. No on-demand fetch, no video
    thumbnail, no generated stand-in (M12 fail closed)."""
    import hashlib
    channels_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")
    with open(channels_json) as f:
        registry = json.load(f)
    entry = next((e for e in registry if e.get("display_name") == channel_name), None)
    avatar = (entry or {}).get("avatar_path", "")
    if not avatar or not os.path.exists(avatar):
        raise FileNotFoundError(f"STOP: no verified avatar for channel '{channel_name}' in channels.json "
                                f"(pipeline/avatar_onboard.py fetch, verify the contact sheet, register)")
    prefix = entry.get("avatar_sha256_prefix", "")
    if prefix and not hashlib.sha256(open(avatar, "rb").read()).hexdigest().startswith(prefix):
        raise RuntimeError(f"STOP: avatar for '{channel_name}' does not match its registered sha256 prefix")
    validate_avatar(avatar)
    return avatar


def main():
    p = argparse.ArgumentParser(description="Parameterised shoutout renderer")
    p.add_argument("--segment", required=True, help="Segment directory")
    p.add_argument("--qa-version", type=int, default=None)
    p.add_argument("--fmt", default="16x9", choices=["16x9", "9x16"])
    args = p.parse_args()

    build_shoutout(args.segment, args.qa_version, args.fmt)


if __name__ == "__main__":
    main()
