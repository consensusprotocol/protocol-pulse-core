#!/usr/bin/env python3
"""Step 8: Shorts Cutter — generate vertical 9:16 shorts from horizontal master."""
import os, subprocess, json, tempfile

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 0.0


def cut_short(segment_video: str, headline: str, output_path: str,
              max_duration: float = 59) -> str:
    """Create a vertical short from a segment video."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    dur = min(ffprobe_duration(segment_video), max_duration)
    if dur <= 0:
        dur = 30

    safe_headline = headline.replace("'", "").replace(":", " -").replace('"', '').replace('%', ' pct')
    words = safe_headline.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > 25:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    lines = lines[:3]

    headline_filters = ""
    for i, line in enumerate(lines):
        y = 1500 + i * 55
        headline_filters += (
            f"drawtext=fontfile={FONT_BOLD}:text='{line}':"
            f"fontcolor=white:fontsize=42:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y={y},"
        )

    fg = (
        f"[0:v]scale=1920:1080,crop=608:1080:656:0,scale=1080:1920,"
        # Simple branded overlay at top
        f"drawbox=x=0:y=0:w=1080:h=80:c=0x0A0A0A@0.7:t=fill,"
        f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
        f"fontcolor=white:fontsize=32:x=(w-text_w)/2:y=25,"
        # Headline captions
        f"{headline_filters}"
        # Bottom branding bar
        f"drawbox=x=0:y=1820:w=1080:h=100:c=0x0A0A0A@0.8:t=fill,"
        f"drawtext=fontfile={FONT_MONO}:text='@ProtocolPulse':"
        f"fontcolor=0xCC0000:fontsize=28:x=(w-text_w)/2:y=1845,"
        f"format=yuv420p[v];\n"
        f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    fd, fpath = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(fg)
        cmd = ["ffmpeg", "-y", "-i", segment_video,
               "-filter_complex_script", fpath,
               "-map", "[v]", "-map", "[a]",
               "-c:v", "libx264", "-crf", "22", "-preset", "fast",
               "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
               "-t", str(dur), output_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"  [shorts] FAILED: {r.stderr[-300:]}")
            return ""
    finally:
        os.unlink(fpath)

    dur_out = ffprobe_duration(output_path)
    sz = os.path.getsize(output_path) // 1024
    print(f"  [shorts] {os.path.basename(output_path)}: {dur_out:.1f}s, {sz}KB")
    return output_path


def generate_shorts(work_dir: str, script: dict, output_dir: str) -> list:
    """Generate vertical shorts from assembled segment files."""
    os.makedirs(output_dir, exist_ok=True)
    shorts = []
    segments = script.get("segments", [])

    for i, seg in enumerate(segments[:5]):
        seg_file = os.path.join(work_dir, f"seg_{i:02d}.mp4")
        if not os.path.exists(seg_file):
            print(f"  [shorts] skipping short {i}: no segment file")
            continue
        short_path = os.path.join(output_dir, f"short_{i:02d}.mp4")
        result = cut_short(seg_file, seg["headline"], short_path)
        if result:
            shorts.append(result)

    return shorts
