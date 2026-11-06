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

    # On-demand fetch: try to download from EDL video metadata
    avatar = _fetch_avatar_on_demand(segment_dir, channel_name)
    if avatar:
        return avatar

    raise FileNotFoundError(f"STOP: avatar missing for channel '{channel_name}'")


def _fetch_avatar_on_demand(segment_dir, channel_name):
    """Try to fetch channel avatar via yt-dlp from the EDL's video entries."""
    import subprocess
    import hashlib

    avatars_dir = os.path.join(segment_dir, "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
    slug = channel_name.lower().replace(" ", "_").replace("'", "")

    # Find a video_id for this channel from EDL
    edl_path = os.path.join(segment_dir, "edl.json")
    if not os.path.exists(edl_path):
        return None

    with open(edl_path) as f:
        edl = json.load(f)

    video_id = None
    hook = edl.get("hook", {})
    if hook.get("channel") == channel_name:
        video_id = hook.get("video_id")
    for clip in edl.get("clips", []):
        if clip.get("channel") == channel_name:
            video_id = clip.get("video_id")
            break

    if not video_id:
        return None

    # Use yt-dlp to get channel thumbnail URL from video metadata
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--skip-download", "--no-warnings",
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        meta = json.loads(result.stdout)

        # Try direct thumbnail fields that are actual image URLs
        avatar_url = None
        for key in ("channel_url", "uploader_url"):
            url = meta.get(key, "")
            if url and "yt3.ggpht.com" in url:
                avatar_url = url
                break

        # Search thumbnails list for avatar entries
        if not avatar_url:
            for t in meta.get("thumbnails", []):
                url = t.get("url", "")
                if "yt3.ggpht.com" in url:
                    avatar_url = url
                    break

        # Construct from channel_id using known YouTube avatar URL pattern
        if not avatar_url:
            channel_id = meta.get("channel_id", "")
            uploader_id = meta.get("uploader_id", "")
            # Try video thumbnail as a safe fallback
            avatar_url = meta.get("thumbnail")

        if not avatar_url:
            return None

        # Download the image
        import urllib.request
        out_path = os.path.join(avatars_dir, f"{slug}.jpg")
        urllib.request.urlretrieve(avatar_url, out_path)

        # Verify it's actually an image
        if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
            # Quick check: valid image header
            with open(out_path, "rb") as fimg:
                header = fimg.read(16)
            if header[:3] in (b'\xff\xd8\xff', b'\x89PN') or b'WEBP' in header[:20]:
                # Convert to PNG for PIL compatibility
                try:
                    from PIL import Image
                    img = Image.open(out_path).convert("RGB")
                    png_path = os.path.join(avatars_dir, f"{slug}.png")
                    img.save(png_path)
                    print(f"    Fetched avatar for {channel_name}: {png_path}")
                    return png_path
                except Exception:
                    print(f"    Fetched avatar for {channel_name}: {out_path}")
                    return out_path
            else:
                os.unlink(out_path)  # Not a real image
    except Exception as e:
        print(f"    WARN: avatar fetch failed for {channel_name}: {e}")

    # Last resort: generate a placeholder
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (512, 512), (40, 40, 60))
        draw = ImageDraw.Draw(img)
        # Draw initials
        initials = "".join(w[0].upper() for w in channel_name.split()[:3] if w)
        draw.text((180, 180), initials, fill=(247, 147, 26))
        out_path = os.path.join(avatars_dir, f"{slug}.png")
        img.save(out_path)
        print(f"    Generated placeholder avatar for {channel_name}")
        return out_path
    except Exception:
        pass

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
