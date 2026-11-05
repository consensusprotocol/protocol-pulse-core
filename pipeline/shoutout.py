#!/usr/bin/env python3
"""pipeline/shoutout.py — Parameterised shoutout renderer.

FROZEN from segment_v1/scene_shoutout.py. Delegates to the original.
Only difference: resolves channels from EDL and passes to the frozen renderer.

Usage:
    python3 -m pipeline.shoutout --segment <segment_dir> [--qa-version N]
"""
import argparse
import json
import os
import sys

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

    # Extract unique channels in EDL order
    channels = []
    seen = set()
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

    out_path = os.path.join(qa_dir, out_name)

    # Get signoff VO if available
    vo_dir = paths["vo_dir"]
    manifest_path = os.path.join(vo_dir, "VO_MANIFEST.json")
    vo_wav = None
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        if "signoff" in manifest:
            vo_wav = os.path.join(vo_dir, manifest["signoff"]["stem_wav"])
            if not os.path.exists(vo_wav):
                vo_wav = None

    render_shoutout(channels, size=size, vo_wav=vo_wav, out_path=out_path)

    if os.path.exists(out_path):
        print(f"  Output: {out_path}")
        return out_path
    print("  ERROR: shoutout render failed")
    return None


def _find_avatar(segment_dir, channel_name):
    """Find avatar for a channel. Looks in channels.json registry, then local avatars/."""
    # Try channels.json registry
    channels_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")
    if os.path.exists(channels_json):
        with open(channels_json) as f:
            registry = json.load(f)
        for entry in registry:
            if entry.get("display_name") == channel_name:
                avatar = entry.get("avatar_path", "")
                if avatar and os.path.exists(avatar):
                    return avatar

    # Try local avatars dir
    avatars_dir = os.path.join(segment_dir, "avatars")
    if os.path.exists(avatars_dir):
        slug = channel_name.lower().replace(" ", "_")
        for ext in [".jpg", ".png", ".webp"]:
            candidate = os.path.join(avatars_dir, f"{slug}{ext}")
            if os.path.exists(candidate):
                return candidate

    return None


def main():
    p = argparse.ArgumentParser(description="Parameterised shoutout renderer")
    p.add_argument("--segment", required=True, help="Segment directory")
    p.add_argument("--qa-version", type=int, default=None)
    p.add_argument("--fmt", default="16x9", choices=["16x9", "9x16"])
    args = p.parse_args()

    build_shoutout(args.segment, args.qa_version, args.fmt)


if __name__ == "__main__":
    main()
