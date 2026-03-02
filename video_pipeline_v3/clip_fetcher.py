#!/usr/bin/env python3
"""Step 6: Clip Fetcher — Pexels B-roll with disk cache.
Production mode: Pexels or fail with clear error (no FFmpeg-generated backgrounds)."""
import os, json, subprocess, hashlib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

BASE = os.path.dirname(os.path.abspath(__file__))
PEXELS_CACHE_DIR = os.path.join(BASE, "..", "downloads", "pexels_cache")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Module-level key cache
_KEY_CACHE: dict = {}


def _get_cached_key(name: str) -> str:
    if name not in _KEY_CACHE:
        k = get_key(name)
        if k:
            _KEY_CACHE[name] = k.strip()
    return _KEY_CACHE.get(name, "")


def _cache_path(query: str, index: int) -> str:
    """Stable cache file path for a given query + index."""
    os.makedirs(PEXELS_CACHE_DIR, exist_ok=True)
    key = f"{query.lower().strip()}_{index}"
    digest = hashlib.md5(key.encode()).hexdigest()[:16]
    return os.path.join(PEXELS_CACHE_DIR, f"px_{digest}.mp4")


def _process_clip(raw_path: str, out_path: str, duration: float) -> bool:
    """Trim, scale, Ken Burns pan + color-grade a raw Pexels clip."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", raw_path, "-t", str(duration),
         "-vf", (
             "scale=1920:1080:force_original_aspect_ratio=increase,"
             "crop=1920:1080,"
             "zoompan=z=min(zoom+0.0008\\,1.08):d=1:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1920x1080:fps=30,"
             "eq=saturation=0.85:contrast=1.1,"
             "colorbalance=rs=0.05:gs=-0.02:bs=-0.02"
         ),
         "-c:v", "libx264", "-crf", "20", "-an", out_path],
        capture_output=True, text=True, timeout=180
    )
    return r.returncode == 0 and os.path.exists(out_path)


def fetch_pexels_clips(keywords: list, output_dir: str, duration: float = 15,
                       count: int = 2) -> list:
    """Fetch video clips from Pexels API, using disk cache to avoid re-downloading."""
    key = _get_cached_key("PEXELS_API_KEY")
    if not key or not HAS_REQUESTS:
        return []

    os.makedirs(output_dir, exist_ok=True)
    query = " ".join(keywords[:3])
    clips = []

    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": count + 2, "size": "medium",
                    "orientation": "landscape"},
            headers={"Authorization": key},
            timeout=20
        )
        if r.status_code == 401:
            print(f"  [pexels] Auth failed — check PEXELS_API_KEY")
            return []
        if r.status_code != 200:
            print(f"  [pexels] HTTP {r.status_code} for query '{query}'")
            return []

        videos = r.json().get("videos", [])
        if not videos:
            print(f"  [pexels] No results for '{query}'")
            return []

        fetched = 0
        for vi, video in enumerate(videos):
            if fetched >= count:
                break
            files = video.get("video_files", [])
            # Prefer 1080p then 720p then any
            hd = (
                next((f for f in files if f.get("height", 0) >= 1080), None) or
                next((f for f in files if f.get("height", 0) >= 720), None) or
                (files[0] if files else None)
            )
            if not hd:
                continue

            cache = _cache_path(query, vi)
            clip_dest = os.path.join(output_dir, f"pexels_{fetched}.mp4")

            # Check cache
            if os.path.exists(cache) and os.path.getsize(cache) > 10_000:
                # Copy from cache to output_dir (so caller has a local reference)
                subprocess.run(["cp", cache, clip_dest], capture_output=True)
                if os.path.exists(clip_dest):
                    print(f"  [pexels] Cache hit: {os.path.basename(cache)}")
                    clips.append(clip_dest)
                    fetched += 1
                    continue

            # Download raw
            raw = cache + ".raw.mp4"
            try:
                vid_r = requests.get(hd["link"], timeout=90, stream=True)
                with open(raw, "wb") as fh:
                    for chunk in vid_r.iter_content(chunk_size=65536):
                        fh.write(chunk)
            except Exception as e:
                print(f"  [pexels] Download error for video {vi}: {e}")
                continue

            if not os.path.exists(raw) or os.path.getsize(raw) < 10_000:
                print(f"  [pexels] Bad download for video {vi}")
                continue

            # Process → cache
            if _process_clip(raw, cache, duration):
                os.remove(raw)
                subprocess.run(["cp", cache, clip_dest], capture_output=True)
                if os.path.exists(clip_dest):
                    print(f"  [pexels] Downloaded + cached: '{query}' [{vi}]")
                    clips.append(clip_dest)
                    fetched += 1
            else:
                print(f"  [pexels] Processing failed for video {vi}")
                if os.path.exists(raw):
                    os.remove(raw)

    except Exception as e:
        print(f"  [pexels] error: {e}")

    return clips


def generate_broll_ffmpeg(keywords: list, output_path: str, duration: float = 15) -> str:
    """Generate synthetic B-roll using FFmpeg (utility function — not used in production)."""
    import tempfile
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    keyword_text = " | ".join(keywords[:3]).upper().replace("'", "").replace('"', '')
    kw_main = (keywords[0].upper() if keywords else "BITCOIN").replace("'", "").replace('"', '')

    fg = (
        f"[0:v]drawgrid=w=60:h=60:t=1:c=0x1A1A1A@0.5,"
        f"drawgrid=w=300:h=300:t=2:c=0x2A0000@0.3,"
        f"colorbalance=rs=0.1:gs=0:bs=0,"
        f"drawtext=fontfile={FONT_MONO}:text='{keyword_text}':"
        f"fontcolor=0xCC0000@0.6:fontsize=28:x=100:y=100,"
        f"drawtext=fontfile={FONT_BOLD}:text='{kw_main}':"
        f"fontcolor=white@0.15:fontsize=160:x=(w-text_w)/2:y=(h-text_h)/2,"
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


def fetch_all_clips(script: dict, output_dir: str) -> dict:
    """Fetch all clips for the episode from Pexels.
    Production mode: raises RuntimeError if Pexels returns no clips for a segment."""
    os.makedirs(output_dir, exist_ok=True)
    clips = {"segments": []}

    key = _get_cached_key("PEXELS_API_KEY")
    if not key:
        raise RuntimeError(
            "PEXELS_API_KEY not available. Cannot fetch B-roll. "
            "No generated backgrounds in production mode."
        )

    for i, seg in enumerate(script["segments"]):
        seg_dir = os.path.join(output_dir, f"seg_{i:02d}")
        os.makedirs(seg_dir, exist_ok=True)

        keywords = seg.get("keywords_for_visuals", ["bitcoin finance"])
        duration = seg.get("duration_seconds", 20)

        pexels = fetch_pexels_clips(keywords, seg_dir, duration, count=2)

        if pexels:
            clips["segments"].append({"type": "pexels", "clips": pexels})
            print(f"  [clip] seg_{i:02d}: {len(pexels)} Pexels clips ({keywords[0]})")
        else:
            # Try a broader query fallback within Pexels
            fallback_keywords = ["finance technology", "bitcoin", "digital money"]
            print(f"  [clip] seg_{i:02d}: No results for {keywords}, trying fallback...")
            pexels_fb = fetch_pexels_clips(fallback_keywords, seg_dir, duration, count=1)
            if pexels_fb:
                clips["segments"].append({"type": "pexels_fallback", "clips": pexels_fb})
                print(f"  [clip] seg_{i:02d}: 1 Pexels fallback clip")
            else:
                raise RuntimeError(
                    f"Pexels returned no clips for segment {i} (keywords={keywords}). "
                    "Check PEXELS_API_KEY and network. "
                    "No generated backgrounds in production mode."
                )

    return clips


if __name__ == "__main__":
    from script_writer import generate_script
    import sys
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    clip_dir = os.path.join(base_dir, "output", "clips_test")
    result = fetch_all_clips(script, clip_dir)
    print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))
