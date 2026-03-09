#!/usr/bin/env python3
"""Clip Fetcher V4 — Pexels B-roll + YouTube clip download via yt-dlp.
Fetches real YouTube clips for CLIP markers in dialogue scripts."""
import os, json, subprocess, hashlib, glob as globmod, time
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

BASE = os.path.dirname(os.path.abspath(__file__))
PEXELS_CACHE_DIR = os.path.join(BASE, "downloads", "pexels_cache")
YT_CACHE_DIR = os.path.join(BASE, "downloads", "yt_cache")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

_KEY_CACHE: dict = {}


def _get_cached_key(name: str) -> str:
    if name not in _KEY_CACHE:
        try:
            k = get_key(name, required=False)
            if k:
                _KEY_CACHE[name] = k.strip()
        except (KeyError, Exception):
            pass
    return _KEY_CACHE.get(name, "")


def _cache_path(query: str, index: int) -> str:
    os.makedirs(PEXELS_CACHE_DIR, exist_ok=True)
    key = f"{query.lower().strip()}_{index}"
    digest = hashlib.md5(key.encode()).hexdigest()[:16]
    return os.path.join(PEXELS_CACHE_DIR, f"px_{digest}.mp4")


def _yt_cache_path(query: str) -> str:
    os.makedirs(YT_CACHE_DIR, exist_ok=True)
    digest = hashlib.md5(query.lower().strip().encode()).hexdigest()[:16]
    return os.path.join(YT_CACHE_DIR, f"yt_{digest}.mp4")


def _process_clip(raw_path: str, out_path: str, duration: float) -> bool:
    """Trim, scale, Ken Burns pan + color-grade a raw clip."""
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
        capture_output=True, text=True, timeout=180,
    )
    return r.returncode == 0 and os.path.exists(out_path)


# ── YouTube clip fetching via yt-dlp ─────────────────────────────────────────

def fetch_youtube_clip(query: str, output_dir: str, max_duration: int = 60,
                       source: str = "") -> str:
    """Search YouTube and download a short clip via yt-dlp.

    Args:
        query: Search terms (e.g., "bitcoin mining facility 2024")
        output_dir: Directory to save the clip
        max_duration: Max clip duration in seconds
        source: Optional channel hint (e.g., "@BitcoinMagazine")

    Returns:
        Path to downloaded clip, or "" on failure.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Check cache
    cache = _yt_cache_path(query)
    if os.path.exists(cache) and os.path.getsize(cache) > 10_000:
        dest = os.path.join(output_dir, os.path.basename(cache))
        subprocess.run(["cp", cache, dest], capture_output=True)
        if os.path.exists(dest):
            print(f"  [yt] Cache hit: {query[:40]}")
            return dest

    search_query = query
    if source and source.startswith("@"):
        search_query = f"{source} {query}"

    raw_path = cache + ".raw.mp4"

    try:
        # Search + download best quality up to 1080p, limit duration
        cmd = [
            "yt-dlp",
            f"ytsearch1:{search_query}",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--max-filesize", "100M",
            "--match-filter", f"duration<={max_duration * 3}",
            "--no-playlist",
            "--no-check-certificates",
            "-o", raw_path,
            "--quiet",
            "--no-warnings",
        ]

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if r.returncode != 0 or not os.path.exists(raw_path):
            # Try simpler format selection
            cmd2 = [
                "yt-dlp",
                f"ytsearch1:{search_query}",
                "-f", "best[height<=1080]",
                "--no-playlist",
                "--no-check-certificates",
                "-o", raw_path,
                "--quiet",
                "--no-warnings",
            ]
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
            if r2.returncode != 0 or not os.path.exists(raw_path):
                print(f"  [yt] Download failed for: {query[:50]}")
                return ""

    except subprocess.TimeoutExpired:
        print(f"  [yt] Timeout downloading: {query[:50]}")
        return ""
    except Exception as e:
        print(f"  [yt] Error: {e}")
        return ""

    if not os.path.exists(raw_path) or os.path.getsize(raw_path) < 10_000:
        print(f"  [yt] Bad download for: {query[:50]}")
        return ""

    # Process: trim to max_duration, scale to 1920x1080
    if _process_clip(raw_path, cache, max_duration):
        try:
            os.remove(raw_path)
        except Exception:
            pass
        dest = os.path.join(output_dir, os.path.basename(cache))
        subprocess.run(["cp", cache, dest], capture_output=True)
        if os.path.exists(dest):
            print(f"  [yt] Downloaded + cached: {query[:40]}")
            return dest
    else:
        # If processing fails, use raw file directly with simple trim
        simple = os.path.join(output_dir, os.path.basename(cache))
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path, "-t", str(max_duration),
             "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
             "-c:v", "libx264", "-crf", "22", "-an", simple],
            capture_output=True, text=True, timeout=120,
        )
        try:
            os.remove(raw_path)
        except Exception:
            pass
        if r.returncode == 0 and os.path.exists(simple):
            print(f"  [yt] Downloaded (simple): {query[:40]}")
            return simple

    return ""


def fetch_dialogue_clips(dialogue: list, output_dir: str) -> dict:
    """Fetch YouTube clips for all CLIP markers in the dialogue.

    Returns:
        {"clips": {line_index: clip_path, ...}, "count": int}
    """
    os.makedirs(output_dir, exist_ok=True)
    clips = {}
    clip_dir = os.path.join(output_dir, "yt_clips")

    for i, entry in enumerate(dialogue):
        if entry.get("host") != "CLIP":
            continue

        query = entry.get("query", "")
        source = entry.get("source", "")

        if not query:
            continue

        clip_path = fetch_youtube_clip(query, clip_dir, max_duration=30, source=source)
        if clip_path:
            clips[i] = clip_path
        else:
            print(f"  [clip] No YT clip for line {i}, will use fallback visual")

    return {"clips": clips, "count": len(clips)}


# ── Pexels B-roll ────────────────────────────────────────────────────────────

def fetch_pexels_clips(keywords: list, output_dir: str, duration: float = 15,
                       count: int = 2) -> list:
    """Fetch B-roll from Pexels API with disk cache."""
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
            timeout=20,
        )
        if r.status_code != 200:
            return []

        videos = r.json().get("videos", [])
        if not videos:
            return []

        fetched = 0
        for vi, video in enumerate(videos):
            if fetched >= count:
                break
            files = video.get("video_files", [])
            hd = (
                next((f for f in files if f.get("height", 0) >= 1080), None)
                or next((f for f in files if f.get("height", 0) >= 720), None)
                or (files[0] if files else None)
            )
            if not hd:
                continue

            cache = _cache_path(query, vi)
            clip_dest = os.path.join(output_dir, f"pexels_{fetched}.mp4")

            if os.path.exists(cache) and os.path.getsize(cache) > 10_000:
                subprocess.run(["cp", cache, clip_dest], capture_output=True)
                if os.path.exists(clip_dest):
                    clips.append(clip_dest)
                    fetched += 1
                    continue

            raw = cache + ".raw.mp4"
            try:
                vid_r = requests.get(hd["link"], timeout=90, stream=True)
                with open(raw, "wb") as fh:
                    for chunk in vid_r.iter_content(chunk_size=65536):
                        fh.write(chunk)
            except Exception as e:
                print(f"  [pexels] Download error {vi}: {e}")
                continue

            if not os.path.exists(raw) or os.path.getsize(raw) < 10_000:
                continue

            if _process_clip(raw, cache, duration):
                os.remove(raw)
                subprocess.run(["cp", cache, clip_dest], capture_output=True)
                if os.path.exists(clip_dest):
                    clips.append(clip_dest)
                    fetched += 1
            else:
                if os.path.exists(raw):
                    os.remove(raw)

    except Exception as e:
        print(f"  [pexels] error: {e}")

    return clips


def fetch_broll_for_dialogue(dialogue: list, output_dir: str) -> list:
    """Fetch Pexels B-roll clips to use as background during host dialogue.
    Returns list of clip paths."""
    os.makedirs(output_dir, exist_ok=True)
    # Use general Bitcoin/finance B-roll queries
    queries = [
        ["bitcoin", "cryptocurrency", "trading"],
        ["stock market", "finance", "data"],
        ["technology", "digital", "network"],
        ["city", "skyline", "night"],
    ]
    all_clips = []
    for qi, q in enumerate(queries):
        seg_dir = os.path.join(output_dir, f"broll_{qi}")
        clips = fetch_pexels_clips(q, seg_dir, duration=20, count=1)
        all_clips.extend(clips)
        if len(all_clips) >= 4:
            break
    return all_clips


def fetch_all_clips(script: dict, output_dir: str) -> dict:
    """V4: Fetch both YouTube clips (for CLIP markers) and Pexels B-roll."""
    os.makedirs(output_dir, exist_ok=True)
    result = {"yt_clips": {}, "broll": [], "count": 0}

    dialogue = script.get("dialogue", [])

    # 1. YouTube clips for CLIP markers
    yt_data = fetch_dialogue_clips(dialogue, output_dir)
    result["yt_clips"] = yt_data.get("clips", {})
    result["count"] += yt_data.get("count", 0)
    print(f"  [clip] YouTube clips: {yt_data.get('count', 0)}")

    # 2. Pexels B-roll for dialogue background
    broll = fetch_broll_for_dialogue(dialogue, output_dir)
    result["broll"] = broll
    result["count"] += len(broll)
    print(f"  [clip] Pexels B-roll: {len(broll)}")

    return result


if __name__ == "__main__":
    from script_writer import generate_script
    import sys
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    clip_dir = os.path.join(base_dir, "output", "clips_test")
    result = fetch_all_clips(script, clip_dir)
    print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))
