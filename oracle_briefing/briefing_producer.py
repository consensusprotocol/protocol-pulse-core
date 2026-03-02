#!/usr/bin/env python3
"""Oracle Briefing Producer — orchestrates the full daily briefing pipeline.

Pipeline:
1. Fetch live data (BTC, mempool, hashrate, FNG, articles)
2. Generate script via Claude (briefing_writer)
3. Generate overlays (overlay_engine)
4. TTS via ElevenLabs Jessica
5. Avatar generation via Oracle server (localhost:8200)
6. Composite: avatar (40%) + data overlay (60%) with FFmpeg
7. Generate thumbnail (Pillow)
8. Generate vertical short (1080x1920)
9. Output to output/oracle_YYYYMMDD/

Flags:
  --test       Use sample data, shorter briefing, skip avatar
  --no-avatar  Skip avatar, produce audio + overlays only
"""
import argparse, base64, json, os, subprocess, sys, time, tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from briefing_writer import generate_script, fetch_all_data, SAMPLE_DATA
from overlay_engine import generate_all_overlays
from relay import get_key

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_cfg = None
def cfg():
    global _cfg
    if _cfg is None:
        p = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(p) as f:
            _cfg = yaml.safe_load(f)
    return _cfg


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

_KEY_CACHE = {}

def _get_cached_key(name: str) -> str:
    if name not in _KEY_CACHE:
        k = get_key(name)
        if k:
            _KEY_CACHE[name] = k.strip()
    return _KEY_CACHE.get(name, "")


def tts_generate(text: str, output_path: str) -> bool:
    """Generate TTS audio via ElevenLabs Jessica voice."""
    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        print("[tts] ERROR: No ELEVENLABS_API_KEY")
        return False

    c = cfg()["tts"]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{c['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    body = {
        "text": text,
        "model_id": c["model_id"],
        "voice_settings": {
            "stability": c["stability"],
            "similarity_boost": c["similarity_boost"],
            "style": c["style"],
            "use_speaker_boost": c["use_speaker_boost"],
        },
    }

    for attempt in range(3):
        try:
            r = requests.post(url, json=body, headers=headers, timeout=90)
            if r.status_code == 200:
                mp3_tmp = output_path + ".tmp.mp3"
                with open(mp3_tmp, "wb") as f:
                    f.write(r.content)
                # Convert to m4a
                res = subprocess.run(
                    ["ffmpeg", "-y", "-i", mp3_tmp, "-c:a", "aac",
                     "-ar", "44100", "-ac", "1", "-b:a", "192k", output_path],
                    capture_output=True, text=True, timeout=60,
                )
                if os.path.exists(mp3_tmp):
                    os.remove(mp3_tmp)
                if res.returncode == 0 and os.path.exists(output_path):
                    print(f"[tts] Generated: {output_path}")
                    return True
                print(f"[tts] FFmpeg conversion failed")
                return False
            elif r.status_code == 429:
                wait = 2 ** attempt
                print(f"[tts] Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"[tts] HTTP {r.status_code}: {r.text[:200]}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
        except Exception as e:
            print(f"[tts] Error attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    return False


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Avatar
# ---------------------------------------------------------------------------

def generate_avatar_video(audio_path: str, output_path: str) -> bool:
    """Generate avatar video via Oracle server at localhost:8200."""
    c = cfg()["avatar"]
    url = f"{c['url']}/generate"

    print("[avatar] Reading audio for avatar generation...")
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    # Determine content type
    ext = os.path.splitext(audio_path)[1].lower()
    ct_map = {".m4a": "audio/mp4", ".mp3": "audio/mpeg", ".wav": "audio/wav"}
    content_type = ct_map.get(ext, "audio/mp4")

    payload = {
        "audio_base64": audio_b64,
        "content_type": content_type,
        "enable_blinks": c["enable_blinks"],
        "enable_head_movement": c["enable_head_movement"],
        "fps": c["fps"],
    }

    print(f"[avatar] Sending {len(audio_b64) // 1024}KB to Oracle server...")
    try:
        r = requests.post(url, json=payload, timeout=300)
        if r.status_code == 200:
            data = r.json()
            video_b64 = data.get("video_base64", "")
            if video_b64:
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(video_b64))
                print(f"[avatar] Generated: {output_path}")
                return True
            else:
                print("[avatar] No video_base64 in response")
        else:
            print(f"[avatar] HTTP {r.status_code}: {r.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("[avatar] Cannot connect to Oracle server at localhost:8200")
    except Exception as e:
        print(f"[avatar] Error: {e}")

    return False


def static_avatar_video(audio_path: str, output_path: str) -> bool:
    """Create a video from static avatar image + audio (fallback / test mode)."""
    c = cfg()["avatar"]
    img = os.path.join(os.path.dirname(__file__), c["static_image"])
    if not os.path.exists(img):
        print(f"[avatar] Static image not found: {img}")
        return False

    duration = ffprobe_duration(audio_path)
    if duration <= 0:
        print("[avatar] Cannot determine audio duration")
        return False

    r = subprocess.run(
        ["ffmpeg", "-y",
         "-loop", "1", "-i", img,
         "-i", audio_path,
         "-c:v", "libx264", "-tune", "stillimage",
         "-c:a", "aac", "-b:a", "192k",
         "-pix_fmt", "yuv420p",
         "-t", str(duration),
         "-vf", f"scale=512:512",
         output_path],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode == 0 and os.path.exists(output_path):
        print(f"[avatar] Static video: {output_path}")
        return True
    print(f"[avatar] FFmpeg error: {r.stderr[:300]}")
    return False


# ---------------------------------------------------------------------------
# Compositing
# ---------------------------------------------------------------------------

def composite_segment(avatar_video: str, overlay_png: str, audio_path: str,
                      output_path: str, duration: float) -> bool:
    """Composite avatar (left 40%) + overlay (right 60%) into segment video."""
    # Layout: 1920x1080, avatar on left (768px), overlay on right (1152px)
    filter_complex = (
        "[0:v]scale=768:1080:force_original_aspect_ratio=decrease,"
        "pad=768:1080:(ow-iw)/2:(oh-ih)/2:color=0x0A0A0A[avatar];"
        "[1:v]scale=1152:1080[overlay];"
        "[avatar][overlay]hstack=inputs=2[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", avatar_video,
        "-i", overlay_png,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "2:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode == 0 and os.path.exists(output_path):
        print(f"[composite] Segment: {output_path}")
        return True
    print(f"[composite] Error: {r.stderr[:300]}")
    return False


def composite_full_briefing(avatar_video: str, overlay_paths: dict,
                             script: dict, audio_path: str,
                             output_dir: str) -> str:
    """Composite full briefing: avatar + rotating overlays synced to segments."""
    # For simplicity, use a single overlay that matches the_number suggestion
    # and keep the avatar for the full duration
    suggestions = script.get("overlay_suggestions", {})

    # Pick the primary overlay
    primary = suggestions.get("the_number", "price_chart")
    overlay = overlay_paths.get(primary, "")
    if not overlay or not os.path.exists(overlay):
        # Fallback to first available
        for v in overlay_paths.values():
            if os.path.exists(v):
                overlay = v
                break

    audio_dur = ffprobe_duration(audio_path)
    out_path = os.path.join(output_dir, "oracle_briefing_raw.mp4")

    if avatar_video and os.path.exists(avatar_video):
        # Full composite: avatar left + overlay right
        filter_complex = (
            "[0:v]scale=768:1080:force_original_aspect_ratio=decrease,"
            "pad=768:1080:(ow-iw)/2:(oh-ih)/2:color=0x0A0A0A[avatar];"
            "[1:v]scale=1152:1080[overlay];"
            "[avatar][overlay]hstack=inputs=2[out]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", avatar_video,
            "-loop", "1", "-i", overlay,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "2:a",
            "-c:v", "libx264", "-crf", "20", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(audio_dur),
            "-pix_fmt", "yuv420p",
            "-shortest",
            out_path,
        ]
    else:
        # No avatar — overlay only with audio
        filter_complex = "[0:v]scale=1920:1080[out]"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", overlay,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "1:a",
            "-c:v", "libx264", "-crf", "20", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(audio_dur),
            "-pix_fmt", "yuv420p",
            "-shortest",
            out_path,
        ]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode == 0 and os.path.exists(out_path):
        print(f"[composite] Raw briefing: {out_path}")
        return out_path
    print(f"[composite] Error: {r.stderr[:400]}")
    return ""


def add_intro_outro(video_path: str, output_path: str) -> str:
    """Add simple intro/outro cards generated with FFmpeg."""
    duration = ffprobe_duration(video_path)
    if duration <= 0:
        return video_path

    intro_path = video_path.replace("_raw.mp4", "_intro.mp4")
    outro_path = video_path.replace("_raw.mp4", "_outro.mp4")
    out_dir = os.path.dirname(video_path)

    # Generate intro card (3s)
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0A0A0A:s=1920x1080:d=3:r=30",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-vf", (
            "drawtext=text='ORACLE BRIEFING':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ":fontsize=72:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-40,"
            "drawtext=text='Protocol Pulse Intelligence':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ":fontsize=28:fontcolor=0x666666:x=(w-text_w)/2:y=(h-text_h)/2+50"
        ),
        "-c:v", "libx264", "-crf", "20", "-c:a", "aac",
        "-t", "3", "-pix_fmt", "yuv420p", "-shortest",
        intro_path,
    ], capture_output=True, text=True, timeout=30)

    # Generate outro card (4s)
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0A0A0A:s=1920x1080:d=4:r=30",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-vf", (
            "drawtext=text='PROTOCOL PULSE':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ":fontsize=56:fontcolor=0xCC0000:x=(w-text_w)/2:y=(h-text_h)/2-30,"
            "drawtext=text='Stay sovereign. Stay informed.':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ":fontsize=24:fontcolor=0x666666:x=(w-text_w)/2:y=(h-text_h)/2+40"
        ),
        "-c:v", "libx264", "-crf", "20", "-c:a", "aac",
        "-t", "4", "-pix_fmt", "yuv420p", "-shortest",
        outro_path,
    ], capture_output=True, text=True, timeout=30)

    # Concatenate: intro + main + outro
    concat_file = os.path.join(out_dir, "concat.txt")
    parts = []
    if os.path.exists(intro_path):
        parts.append(intro_path)
    parts.append(video_path)
    if os.path.exists(outro_path):
        parts.append(outro_path)

    with open(concat_file, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")

    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
         "-c", "copy", output_path],
        capture_output=True, text=True, timeout=120,
    )

    # Cleanup temp files
    for p in [intro_path, outro_path, concat_file]:
        if os.path.exists(p):
            os.remove(p)

    if r.returncode == 0 and os.path.exists(output_path):
        print(f"[composite] Final with intro/outro: {output_path}")
        return output_path

    print(f"[composite] Concat error, using raw: {r.stderr[:200]}")
    return video_path


# ---------------------------------------------------------------------------
# Thumbnail
# ---------------------------------------------------------------------------

def generate_thumbnail(script: dict, output_path: str) -> bool:
    """Generate 1280x720 thumbnail with avatar face + headline + BTC price."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1280, 720

    # Create dark background
    img = Image.new("RGB", (W, H), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 28)
    except Exception:
        font_big = ImageFont.load_default()
        font_med = font_big
        font_sm = font_big

    # Try to load avatar
    avatar_path = os.path.join(os.path.dirname(__file__), "..", "oracle", "Proto_P_Avatar_512.png")
    if os.path.exists(avatar_path):
        try:
            avatar = Image.open(avatar_path).convert("RGBA")
            avatar = avatar.resize((360, 360), Image.LANCZOS)
            # Place avatar on left
            img.paste(avatar, (40, (H - 360) // 2), avatar)
        except Exception as e:
            print(f"[thumb] Avatar load error: {e}")

    # Red accent bar
    draw.rectangle([(430, 140), (436, 580)], fill=(204, 0, 0))

    # Headline text
    headline = script.get("thumbnail_headline", "ORACLE BRIEFING")
    # Word-wrap headline
    words = headline.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_big)
        if bbox[2] - bbox[0] > 760:
            if current:
                lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)

    y = 160
    for line in lines[:3]:
        draw.text((460, y), line.upper(), fill=(255, 255, 255), font=font_big)
        y += 70

    # BTC price
    btc_data = script.get("data", {}).get("btc", {})
    price = btc_data.get("price", 0)
    change = btc_data.get("change_24h", 0)
    if price > 0:
        price_str = f"BTC ${price:,.0f}"
        change_color = (0, 204, 102) if change >= 0 else (255, 51, 51)
        change_str = f"{change:+.1f}%"
        draw.text((460, y + 30), price_str, fill=(255, 255, 255), font=font_med)
        draw.text((460 + draw.textlength(price_str, font=font_med) + 20, y + 35),
                  change_str, fill=change_color, font=font_sm)

    # "ORACLE BRIEFING" badge
    draw.rectangle([(460, y + 100), (730, y + 140)], fill=(204, 0, 0))
    draw.text((470, y + 105), "ORACLE BRIEFING", fill=(255, 255, 255), font=font_sm)

    # Bottom branding
    draw.text((W - 300, H - 40), "PROTOCOL PULSE", fill=(102, 102, 102), font=font_sm)

    img.save(output_path, "JPEG", quality=92)
    print(f"[thumb] Thumbnail: {output_path}")
    return True


# ---------------------------------------------------------------------------
# Vertical Short
# ---------------------------------------------------------------------------

def generate_short(input_video: str, output_path: str) -> bool:
    """Create 1080x1920 vertical short by center-cropping."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", input_video,
         "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920",
         "-c:v", "libx264", "-crf", "22", "-preset", "fast",
         "-c:a", "aac", "-b:a", "192k",
         "-pix_fmt", "yuv420p",
         output_path],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode == 0 and os.path.exists(output_path):
        print(f"[short] Vertical: {output_path}")
        return True
    print(f"[short] Error: {r.stderr[:300]}")
    return False


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(test: bool = False, no_avatar: bool = False):
    """Run the full Oracle Briefing pipeline."""
    t0 = time.time()
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")

    mode = "TEST" if test else "LIVE"
    print(f"\n{'='*60}")
    print(f"  ORACLE BRIEFING PRODUCER — {mode} MODE")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    # Output directory
    if test:
        out_dir = os.path.join(os.path.dirname(__file__), "output", f"test_{date_str}_{now.strftime('%H%M%S')}")
    else:
        out_dir = os.path.join(os.path.dirname(__file__), "output", f"oracle_{date_str}")
    os.makedirs(out_dir, exist_ok=True)
    overlays_dir = os.path.join(out_dir, "overlays")
    os.makedirs(overlays_dir, exist_ok=True)

    # ---------------------------------------------------------------
    # Step 1: Fetch data
    # ---------------------------------------------------------------
    print("\n[1/8] FETCHING DATA...")
    if test:
        data = SAMPLE_DATA
        print("  Using sample data (test mode)")
    else:
        data = fetch_all_data()

    # ---------------------------------------------------------------
    # Step 2: Generate script
    # ---------------------------------------------------------------
    print("\n[2/8] GENERATING SCRIPT...")
    script = generate_script(data=data, test=test)

    # Assemble full_script if not provided
    if not script.get("full_script"):
        script["full_script"] = " ".join([
            script.get("hook", ""),
            script.get("the_number", ""),
            script.get("the_signal", ""),
            script.get("the_take", ""),
            script.get("signoff", ""),
        ]).strip()

    # Save script JSON
    script_path = os.path.join(out_dir, "script.json")
    with open(script_path, "w") as f:
        json.dump({k: v for k, v in script.items() if k != "data"}, f, indent=2)
    print(f"  Script saved: {script_path}")
    print(f"  Words: {len(script['full_script'].split())}")

    # ---------------------------------------------------------------
    # Step 3: Generate overlays
    # ---------------------------------------------------------------
    print("\n[3/8] GENERATING OVERLAYS...")
    overlay_paths = generate_all_overlays(data, overlays_dir)

    # ---------------------------------------------------------------
    # Step 4: TTS
    # ---------------------------------------------------------------
    print("\n[4/8] GENERATING TTS...")
    audio_path = os.path.join(out_dir, "briefing_audio.m4a")
    tts_ok = tts_generate(script["full_script"], audio_path)
    if not tts_ok:
        print("  TTS FAILED — generating silence placeholder")
        word_count = len(script["full_script"].split())
        est_duration = word_count / 2.5  # ~150 wpm
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i",
             f"anullsrc=r=44100:cl=mono", "-t", str(est_duration),
             "-c:a", "aac", "-b:a", "192k", audio_path],
            capture_output=True, text=True, timeout=30,
        )

    audio_dur = ffprobe_duration(audio_path)
    print(f"  Audio duration: {audio_dur:.1f}s")

    # ---------------------------------------------------------------
    # Step 5: Avatar video
    # ---------------------------------------------------------------
    print("\n[5/8] GENERATING AVATAR...")
    avatar_path = os.path.join(out_dir, "avatar_video.mp4")
    avatar_ok = False

    if no_avatar or test:
        print("  Skipping live avatar (--no-avatar / --test), using static image")
        avatar_ok = static_avatar_video(audio_path, avatar_path)
    else:
        # Try live avatar first, fall back to static
        avatar_ok = generate_avatar_video(audio_path, avatar_path)
        if not avatar_ok:
            print("  Live avatar failed, falling back to static")
            avatar_ok = static_avatar_video(audio_path, avatar_path)

    if not avatar_ok:
        print("  WARNING: No avatar video generated")
        avatar_path = None

    # ---------------------------------------------------------------
    # Step 6: Composite
    # ---------------------------------------------------------------
    print("\n[6/8] COMPOSITING...")
    raw_path = composite_full_briefing(
        avatar_path, overlay_paths, script, audio_path, out_dir
    )

    final_path = ""
    if raw_path:
        final_path = os.path.join(out_dir, f"oracle_briefing_{date_str}.mp4")
        final_path = add_intro_outro(raw_path, final_path)
        # Clean up raw
        if os.path.exists(raw_path) and raw_path != final_path:
            os.remove(raw_path)
    else:
        print("  Composite failed — outputting audio-only")
        # Copy audio as the deliverable
        import shutil
        final_path = os.path.join(out_dir, f"oracle_briefing_{date_str}.mp3")
        shutil.copy2(audio_path, final_path)

    # ---------------------------------------------------------------
    # Step 7: Thumbnail
    # ---------------------------------------------------------------
    print("\n[7/8] GENERATING THUMBNAIL...")
    thumb_path = os.path.join(out_dir, "thumbnail.jpg")
    generate_thumbnail(script, thumb_path)

    # ---------------------------------------------------------------
    # Step 8: Vertical short
    # ---------------------------------------------------------------
    print("\n[8/8] GENERATING SHORT...")
    short_path = os.path.join(out_dir, "oracle_short.mp4")
    if final_path.endswith(".mp4") and os.path.exists(final_path):
        generate_short(final_path, short_path)
    else:
        print("  Skipping short (no video source)")

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  ORACLE BRIEFING COMPLETE — {elapsed:.1f}s")
    print(f"{'='*60}")
    print(f"\n  Output: {out_dir}/")

    deliverables = [
        ("Script", script_path),
        ("Audio", audio_path),
        ("Video", final_path),
        ("Thumbnail", thumb_path),
        ("Short", short_path),
    ]
    for name, path in deliverables:
        if path and os.path.exists(path):
            sz = os.path.getsize(path)
            if sz > 1_000_000:
                print(f"  {name}: {os.path.basename(path)} ({sz / 1_000_000:.1f} MB)")
            else:
                print(f"  {name}: {os.path.basename(path)} ({sz / 1024:.0f} KB)")
        else:
            print(f"  {name}: MISSING")

    print(f"\n  Overlays: {len(overlay_paths)} generated in {overlays_dir}/")
    for name, path in overlay_paths.items():
        if os.path.exists(path):
            print(f"    {name}: {os.path.basename(path)}")

    return {
        "output_dir": out_dir,
        "script": script_path,
        "audio": audio_path,
        "video": final_path,
        "thumbnail": thumb_path,
        "short": short_path,
        "overlays": overlay_paths,
        "duration": audio_dur,
        "elapsed": elapsed,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle Briefing Producer")
    parser.add_argument("--test", action="store_true", help="Use sample data, skip live avatar")
    parser.add_argument("--no-avatar", action="store_true", help="Skip avatar generation")
    args = parser.parse_args()

    result = run_pipeline(test=args.test, no_avatar=args.no_avatar)
    sys.exit(0 if result.get("video") or result.get("audio") else 1)
