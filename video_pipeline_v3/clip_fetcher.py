#!/usr/bin/env python3
"""Step 6: Clip Fetcher — Pexels B-roll + FFmpeg-generated screenshot cards."""
import os, json, subprocess
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def fetch_pexels_clips(keywords: list, output_dir: str, duration: float = 15, count: int = 2) -> list:
    """Fetch video clips from Pexels API."""
    key = get_key("PEXELS_API_KEY")
    if not key or not HAS_REQUESTS:
        return []

    os.makedirs(output_dir, exist_ok=True)
    clips = []
    query = " ".join(keywords[:3])

    try:
        r = requests.get(
            f"https://api.pexels.com/videos/search?query={query}&per_page={count}&size=medium",
            headers={"Authorization": key}, timeout=15
        )
        if r.status_code != 200:
            return []
        data = r.json()
        for i, video in enumerate(data.get("videos", [])[:count]):
            # Get HD file
            files = video.get("video_files", [])
            hd = next((f for f in files if f.get("height", 0) >= 720), files[0] if files else None)
            if not hd:
                continue
            url = hd["link"]
            clip_path = os.path.join(output_dir, f"pexels_{i}.mp4")
            # Download
            vid_r = requests.get(url, timeout=60)
            with open(clip_path + ".raw", "wb") as f:
                f.write(vid_r.content)
            # Trim and scale to 1080p, apply Ken Burns + color grade
            subprocess.run(
                f"ffmpeg -y -i '{clip_path}.raw' -t {duration} "
                f"-vf 'scale=1920:1080:force_original_aspect_ratio=increase,"
                f"crop=1920:1080,"
                f"zoompan=z=min(zoom+0.0008\\,1.08):d=1:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1920x1080:fps=30,"
                f"eq=saturation=0.85:contrast=1.1,"
                f"colorbalance=rs=0.05:gs=-0.02:bs=-0.02' "
                f"-c:v libx264 -crf 20 -an '{clip_path}'",
                shell=True, capture_output=True, text=True, timeout=120
            )
            os.remove(clip_path + ".raw")
            if os.path.exists(clip_path):
                clips.append(clip_path)
                print(f"  [pexels] Downloaded: {clip_path}")
    except Exception as e:
        print(f"  [pexels] error: {e}")

    return clips


def generate_broll_ffmpeg(keywords: list, output_path: str, duration: float = 15) -> str:
    """Generate synthetic B-roll using FFmpeg when Pexels is unavailable."""
    import tempfile
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    keyword_text = " | ".join(keywords[:3]).upper().replace("'", "").replace('"', '')
    kw_main = (keywords[0].upper() if keywords else "BITCOIN").replace("'", "").replace('"', '')

    fg = (
        f"[0:v]drawgrid=w=60:h=60:t=1:c=0x1A1A1A@0.5,"
        f"drawgrid=w=300:h=300:t=2:c=0x2A0000@0.3,"
        f"colorbalance=rs=0.1:gs=0:bs=0,"
        f"drawtext=fontfile={FONT_MONO}:text='{keyword_text}':"
        f"fontcolor=0xCC0000@0.6:fontsize=28:x=100:y=100,"
        f"drawtext=fontfile={FONT_BOLD}:text='{kw_main}':"
        f"fontcolor=white@0.15:fontsize=160:"
        f"x=(w-text_w)/2:y=(h-text_h)/2,"
        f"drawbox=x=0:y=540:w=1920:h=2:c=0xCC0000@0.4:t=fill,"
        f"noise=alls=5:allf=t,format=yuv420p[out]"
    )
    fd, fpath = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(fg)
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i",
               f"color=c=0x0A0A0A:s=1920x1080:d={duration}:r=30",
               "-filter_complex_script", fpath, "-map", "[out]",
               "-c:v", "libx264", "-crf", "22", output_path]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(fpath)
    return output_path if os.path.exists(output_path) else ""


def generate_screenshot_card(headline: str, source: str, output_path: str, duration: float = 8) -> str:
    """Create a styled screenshot/article card."""
    import tempfile
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    safe_headline = headline.replace("'", "").replace(":", " -").replace('"', '')
    safe_source = source.replace("'", "").replace(":", "").replace('"', '')

    words = safe_headline.split()
    lines = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 > 38:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}".strip()
    if current:
        lines.append(current)
    lines = lines[:4]

    fg = (
        f"[0:v]drawgrid=w=60:h=60:t=1:c=0x1A1A1A@0.4,"
        f"colorbalance=rs=0.08:gs=0:bs=0,"
        f"drawbox=x=260:y=260:w=1400:h=560:c=0x111111@0.92:t=fill,"
        f"drawbox=x=260:y=260:w=8:h=560:c=0xCC0000:t=fill,"
    )
    for i, line in enumerate(lines):
        y_pos = 320 + i * 60
        fg += f"drawtext=fontfile={FONT_BOLD}:text='{line}':fontcolor=white:fontsize=44:x=300:y={y_pos},"
    fg += (
        f"drawtext=fontfile={FONT_MONO}:text='{safe_source}':"
        f"fontcolor=0xCC0000:fontsize=24:x=300:y={320 + len(lines)*60 + 30},"
        f"noise=alls=3:allf=t,format=yuv420p[out]"
    )
    fd, fpath = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(fg)
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i",
               f"color=c=0x0A0A0A:s=1920x1080:d={duration}:r=30",
               "-filter_complex_script", fpath, "-map", "[out]",
               "-c:v", "libx264", "-crf", "20", output_path]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(fpath)
    return output_path if os.path.exists(output_path) else ""


def fetch_all_clips(script: dict, output_dir: str) -> dict:
    """Fetch/generate all clips for the episode. Returns paths dict."""
    os.makedirs(output_dir, exist_ok=True)
    clips = {"segments": []}

    for i, seg in enumerate(script["segments"]):
        seg_dir = os.path.join(output_dir, f"seg_{i:02d}")
        os.makedirs(seg_dir, exist_ok=True)
        keywords = seg.get("keywords_for_visuals", ["bitcoin"])
        duration = seg.get("duration_seconds", 15)

        # Try Pexels first
        pexels = fetch_pexels_clips(keywords, seg_dir, duration)
        if pexels:
            clips["segments"].append({"type": "pexels", "clips": pexels})
            print(f"  [clip] seg_{i:02d}: {len(pexels)} Pexels clips")
        else:
            # Generate synthetic B-roll
            broll = os.path.join(seg_dir, "broll.mp4")
            generate_broll_ffmpeg(keywords, broll, duration)
            # Also generate a headline card
            card = os.path.join(seg_dir, "card.mp4")
            generate_screenshot_card(seg["headline"], "Protocol Pulse", card, duration)
            clips["segments"].append({"type": "generated", "clips": [broll, card]})
            print(f"  [clip] seg_{i:02d}: generated B-roll + card")

    return clips


if __name__ == "__main__":
    from script_writer import generate_script
    import sys
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base = os.path.dirname(os.path.abspath(__file__))
    clip_dir = os.path.join(base, "output", "clips_test")
    result = fetch_all_clips(script, clip_dir)
    print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))
