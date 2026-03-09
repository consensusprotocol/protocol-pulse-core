#!/usr/bin/env python3
"""Assembler V8 — procedural waveform visualizer episode assembly.

Episode structure:
  1. TAG VIDEO as INTRO (tag_vertical.mp4, fade-in from black)
  2. COLD OPEN — Jessica's vocal hook (waveform visualizer bg + music bed)
  3. For each clip (1-N):
     a. SETUP — host introduces clip (waveform visualizer bg + music bed)
     b. GLITCH TRANSITION (assets/transitions/glitch_transition_waud.mp4)
     c. CLIP — full screen, ORIGINAL AUDIO, source attribution top-right
     d. REACT — both hosts react (waveform visualizer bg + music bed)
  4. WRAP — final sign-off plays OVER outro tag video
  5. TAG VIDEO as OUTRO (tag_vertical.mp4, fade-to-black, wrap narration mixed in)

Visual rules:
  - Host segments: procedural dark bg + audio waveform + speaker bar + ticker + watermark
  - No rotating video file backgrounds — all procedurally generated
  - Clips: full screen, original audio, source attribution
  - Glitch transition (0.5s) between every setup→clip pair
  - Background music at -18dB under all host narration
  - Watermark top-right on all host segments
"""
import json
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile

from music import (
    has_music, has_intro, has_transition, has_outro,
    mix_tts_with_music, INTRO_JINGLE, TRANSITION, OUTRO_JINGLE,
    ffprobe_duration,
)

logger = logging.getLogger("Assembler")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[assemble] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# ── APEX UNIFIED COLOR SYSTEM ─────────────────────────────────────────────
COLOR_BG          = "0x020304"   # BEV2 cinematic obsidian (not flat black)
COLOR_PANEL       = "0x050607"   # BEV2 elevated surface
COLOR_PANEL2      = "0x080a0c"   # secondary surface
COLOR_RED         = "0xFF0000"   # BD signal red — all accents
COLOR_RED_WARM    = "0xFF334D"   # BEV2 warm red — transition elements
COLOR_WHITE       = "0xF4F5F8"   # BEV2 warm white — not pure white
COLOR_TEXT        = "0xF4F5F8"   # primary text (warm white)
COLOR_GOLD        = "0xF8C15C"   # VDS gold — EYEBROW KICKERS ONLY
COLOR_MUTED       = "0x888888"   # secondary labels
COLOR_MUTED2      = "0x555555"   # metadata, timestamps
COLOR_GREEN       = "0x6EE7B7"   # BEV2 emerald — positive/DONE
COLOR_CORAL       = "0xFF8BA0"   # VDS coral — negative/warning
COLOR_RED_DIM     = "0x1a0000"   # CTA box backgrounds
COLOR_TICKER_BG   = "0x0c0c0c"   # ticker bar bg (kept dark)

# Legacy aliases for backward compat in make_host_visual / make_clip_visual
COLOR_AMBER       = COLOR_CORAL
BV2_OBSIDIAN    = COLOR_BG
BV2_DEEP_PANEL  = COLOR_PANEL
BV2_SIGNAL_RED  = COLOR_RED_WARM
BV2_STARK_WHITE = COLOR_WHITE
BV2_MUTED       = "0xFFFFFF"   # secondary text (used @0.33 opacity)
BV2_EMERALD     = COLOR_GREEN
BV2_RED_LIGHT   = "0xFF8595"   # gradient accent

INTRO_VIDEO = os.path.join(ASSETS, "intro.mp4")
OUTRO_VIDEO = os.path.join(ASSETS, "outro.mp4")
GLITCH_TRANSITION = os.path.join(ASSETS, "transitions", "glitch_transition_waud.mp4")
WATERMARK = os.path.join(ASSETS, "logo", "watermark.png")
BG_MUSIC = os.path.join(ASSETS, "music", "pp_background.mp3")
TAG_VIDEO = os.path.join(ASSETS, "tag_vertical.mp4")
OUTRO_BRANDED = os.path.join(ASSETS, "outro_branded.mp4")
LOGO_IMAGE = os.path.join(ASSETS, "logo_protocol_pulse.png")
# Issue 3: Custom whoosh sound — prefer custom_whoosh.mp3 over generated glitch_whoosh.wav
_CUSTOM_WHOOSH_MP3 = os.path.join(ASSETS, "sfx", "custom_whoosh.mp3")
_CUSTOM_WHOOSH_WAV = os.path.join(ASSETS, "sfx", "custom_whoosh.wav")
if os.path.exists(_CUSTOM_WHOOSH_MP3):
    # Convert mp3 to wav for consistency if not already done
    if not os.path.exists(_CUSTOM_WHOOSH_WAV):
        subprocess.run(["ffmpeg", "-y", "-i", _CUSTOM_WHOOSH_MP3, _CUSTOM_WHOOSH_WAV],
                       capture_output=True, text=True, timeout=10)
    GLITCH_WHOOSH = _CUSTOM_WHOOSH_WAV if os.path.exists(_CUSTOM_WHOOSH_WAV) else _CUSTOM_WHOOSH_MP3
else:
    GLITCH_WHOOSH = os.path.join(ASSETS, "sfx", "glitch_whoosh.wav")
    logging.getLogger("Assembler").info("CUSTOM WHOOSH NOT FOUND — using generated")
CARD_SWOOSH = os.path.join(ASSETS, "sfx", "card_swoosh.wav")
DATA_BLIP = os.path.join(ASSETS, "sfx", "data_blip.wav")
LOWER_SLIDE = os.path.join(ASSETS, "sfx", "lower_slide.wav")


def get_latest_spaces_summary() -> dict:
    """FIX 8: Check for recent X Spaces transcripts for episode inclusion.

    Checks:
    1. video_pipeline_v3/data/spaces/ for recent chunks
    2. spaces_scraper/ for cached transcripts
    3. x_spaces_scraper/ for cached transcripts

    Returns dict with {summary, source, score} if found, else None.
    """
    import glob
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(hours=24)

    # Check pipeline spaces data first
    spaces_data_dir = os.path.join(BASE, "data", "spaces")
    if os.path.exists(spaces_data_dir):
        for space_dir in sorted(os.listdir(spaces_data_dir), reverse=True):
            chunks_file = os.path.join(spaces_data_dir, space_dir, "chunks.jsonl")
            if not os.path.exists(chunks_file):
                continue
            # Check if recent (file modified in last 24h)
            if os.path.getmtime(chunks_file) < cutoff.timestamp():
                continue
            # Read highest-impact chunks
            best_chunks = []
            try:
                with open(chunks_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        if entry.get("impact_score", 0) >= 50:
                            best_chunks.append(entry)
            except Exception:
                continue
            if best_chunks:
                best_chunks.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
                top = best_chunks[0]
                summary = top.get("text", "")[:500]
                return {
                    "summary": f"From X Spaces — {top.get('speaker', 'unknown')}: {summary}",
                    "source": f"X Spaces ({space_dir})",
                    "score": top.get("impact_score", 0),
                }

    # Check spaces_scraper cache
    scraper_cache = os.path.join(os.path.dirname(BASE), "spaces_scraper", "cache")
    if not os.path.exists(scraper_cache):
        scraper_cache = os.path.join(os.path.dirname(BASE), "x_spaces_scraper", "cache")
    if os.path.exists(scraper_cache):
        json_files = sorted(glob.glob(os.path.join(scraper_cache, "*.json")), reverse=True)
        for jf in json_files[:5]:
            if os.path.getmtime(jf) < cutoff.timestamp():
                continue
            try:
                with open(jf) as f:
                    data = json.loads(f.read())
                transcript = data.get("transcript", data.get("text", ""))
                if transcript and len(transcript) > 100:
                    return {
                        "summary": transcript[:500],
                        "source": f"X Spaces Scraper ({os.path.basename(jf)})",
                        "score": 60,
                    }
            except Exception:
                continue

    logger.info("  FIX 8: No recent X Spaces data found — segment skipped")
    return None


def _fetch_btc_price() -> str:
    """FIX 5: Fetch BTC price with dual fallback (CoinGecko → Mempool)."""
    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            price = data["bitcoin"]["usd"]
            return f"${price:,.0f}"
    except Exception:
        try:
            import urllib.request
            url2 = "https://mempool.space/api/v1/prices"
            with urllib.request.urlopen(url2, timeout=5) as r:
                data = json.loads(r.read())
                return f"${data.get('USD', 0):,.0f}"
        except Exception:
            return "$N/A"


def _build_black_diamond_bg(duration: float, label_out: str = "bd_bg") -> tuple:
    """BLACK DIAMOND 7-layer procedural background — Sovereign Command Center.

    Returns (extra_inputs, filtergraph_string).
    extra_inputs is always [] — pure procedural generation.
    """
    f = ""
    # Layer 1: Pure black base
    f += f"color=c=0x000000:s=1920x1080:d={duration}:r=30[bd_base];\n"
    # Layer 2: Red radial glow — top-center (subtle)
    f += (f"color=c=0x000000:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(55*exp(-((X-960)*(X-960)+Y*Y)/380000),0,255)':g='0':b='0'[bd_glow_top];\n")
    f += f"[bd_base][bd_glow_top]blend=all_mode=screen[bg1];\n"
    # Layer 3: Red radial glow — bottom-center
    f += (f"color=c=0x000000:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(35*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/280000),0,255)':g='0':b='0'[bd_glow_bot];\n")
    f += f"[bg1][bd_glow_bot]blend=all_mode=screen[bg2];\n"
    # Layer 4: Tactical surveillance grid (very subtle)
    f += f"[bg2]drawgrid=width=120:height=68:thickness=1:color=0xFF0000@0.07[bg3];\n"
    # Layer 5: Scanlines (horizontal every 3px)
    f += f"[bg3]drawgrid=width=0:height=3:thickness=1:color=0xFF0000@0.025[bg4];\n"
    # Layer 6: Vignette
    f += f"[bg4]vignette=PI/4:mode=backward[bg5];\n"
    # Layer 7: Red border frame (2px solid on all 4 edges)
    f += (f"[bg5]drawbox=x=0:y=0:w=1920:h=2:color=0xFF0000@0.85:t=fill,"
          f"drawbox=x=0:y=1078:w=1920:h=2:color=0xFF0000@0.85:t=fill,"
          f"drawbox=x=0:y=0:w=2:h=1080:color=0xFF0000@0.85:t=fill,"
          f"drawbox=x=1918:y=0:w=2:h=1080:color=0xFF0000@0.85:t=fill[{label_out}];\n")
    return ([], f)


def _build_info_bar_fg(duration: float, btc_price: str, block_height: str = "",
                       label_in: str = "v_pre_tick", label_out: str = "v_ticked") -> str:
    """BLACK DIAMOND ticker bar — red scrolling intel on near-black bg."""
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    content = (f"  PROTOCOL PULSE  //  BTC {safe_btc}  //  {date_str}"
               f"  //  SOVEREIGNTY LAYER ACTIVE  //  PROTOCOLPULSE.IO"
               f"  //  SIGNAL DETECTED  //  STAY SOVEREIGN  "
               f"  //  PROTOCOL PULSE  //  BTC {safe_btc}  //  {date_str}"
               f"  //  SOVEREIGNTY LAYER ACTIVE  //  PROTOCOLPULSE.IO"
               f"  //  SIGNAL DETECTED  //  STAY SOVEREIGN  ")
    safe_content = content.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # Dark base bar
    fg += f"color=c={COLOR_TICKER_BG}@0.97:s=1920x48:d={duration}:r=30[tickbase];\n"
    # Red top separator line (2px)
    fg += f"[tickbase]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.85:t=fill[tickline];\n"
    # Static "// LIVE INTEL //" label
    fg += (f"[tickline]drawtext=fontfile={FONT_MONO}:text='// LIVE INTEL //':"
           f"fontcolor={COLOR_RED}@0.5:fontsize=13:x=8:y=18[tickstatic];\n")
    # Scrolling red text
    fg += (f"[tickstatic]drawtext=fontfile={FONT_MONO}:text='{safe_content}':"
           f"fontcolor={COLOR_RED}:fontsize=16:"
           f"x=200+w-mod(t*90\\,w+text_w):y=16[ticker];\n")
    # Overlay bar onto video frame at y=1032
    fg += f"[{label_in}][ticker]overlay=0:1032[{label_out}];\n"
    return fg


def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        logger.error(f"FAIL {label}: {r.stderr[-600:]}")
        return False
    return True


def run_ffmpeg_filtergraph(inputs: list, filtergraph: str, maps: list,
                           output_args: list, output_path: str,
                           label: str = "", timeout: int = 300) -> bool:
    fd, fpath = tempfile.mkstemp(suffix=".txt", prefix="ff_filter_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(filtergraph)
        cmd = ["ffmpeg", "-y"]
        for inp in inputs:
            if isinstance(inp, list):
                cmd.extend(inp)
            else:
                cmd.extend(["-i", inp])
        cmd.extend(["-filter_complex_script", fpath])
        for m in maps:
            cmd.extend(["-map", m])
        cmd.extend(output_args)
        cmd.append(output_path)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            logger.error(f"FAIL {label}: {r.stderr[-600:]}")
            return False
        return True
    finally:
        try:
            os.unlink(fpath)
        except OSError:
            pass


def ensure_audio(video_path: str) -> str:
    """Ensure video has an audio stream (add silent track if missing)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    if "audio" in r.stdout:
        return video_path
    out = video_path.replace(".mp4", "_waud.mp4").replace(".mov", "_waud.mp4")
    dur = ffprobe_duration(video_path)
    run_ffmpeg(
        ["-i", video_path, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", str(dur), "-c:v", "copy", "-c:a", "aac", "-shortest", out],
        "add silence", 60,
    )
    return out if os.path.exists(out) else video_path


# ── Branded intro/outro ────────────────────────────────────────────────────

def make_intro_video(output_path: str) -> str:
    """Use branded intro.mp4 with pp_intro.mp3 mixed in.

    Fades in from black (0.5s), fades out to black (0.5s) with audio fade (1.5s).
    Forces yuv420p pixel format for concat compatibility.
    """
    if not os.path.exists(INTRO_VIDEO):
        logger.warning("intro.mp4 not found — skipping intro")
        return ""

    intro_dur = ffprobe_duration(INTRO_VIDEO)
    if intro_dur <= 0:
        logger.warning("intro.mp4 has zero duration")
        return ""

    fade_out_v = max(0, intro_dur - 0.5)
    fade_out_a = max(0, intro_dur - 1.5)
    vf = (f"scale=1920:1080,setsar=1,format=yuv420p,"
          f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_v}:d=0.5")

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", INTRO_VIDEO],
        capture_output=True, text=True,
    )
    intro_has_audio = "audio" in r.stdout

    jingle_path = os.path.join(ASSETS, "music", "pp_intro.mp3")
    has_jingle = os.path.exists(jingle_path)

    if has_jingle and intro_has_audio:
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-i", jingle_path,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[0:a]volume=0.7[va];[1:a]volume=0.9[vb];"
             f"[va][vb]amix=inputs=2:duration=shortest,"
             f"afade=t=out:st={fade_out_a}:d=1.5[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(intro_dur),
            output_path,
        ], "intro video + jingle", 120)
    elif has_jingle and not intro_has_audio:
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-i", jingle_path,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[1:a]afade=t=out:st={fade_out_a}:d=1.5[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(intro_dur), "-shortest",
            output_path,
        ], "intro video + jingle (no orig audio)", 120)
    else:
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p", "-vf", vf,
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], "intro video normalize", 120)

    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,pix_fmt",
             "-of", "csv=p=0", output_path],
            capture_output=True, text=True,
        )
        logger.info(f"  Intro video: {dur:.1f}s | probe: {probe.stdout.strip()}")
        return output_path

    logger.warning("Intro video failed — skipping")
    return ""


def make_outro_video(output_path: str) -> str:
    """Use branded outro.mp4 with pp_outro.mp3 mixed in.

    Plays in full with 0.5s video fade-to-black and 1.0s audio fade-out at end.
    """
    if not os.path.exists(OUTRO_VIDEO):
        logger.warning("outro.mp4 not found — skipping outro")
        return ""

    outro_dur = ffprobe_duration(OUTRO_VIDEO)
    if outro_dur <= 0:
        return ""

    # Sprint 1.8: No fade-to-black on outro. Hard cut.
    vf = f"scale=1920:1080,setsar=1,format=yuv420p"

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", OUTRO_VIDEO],
        capture_output=True, text=True,
    )
    outro_has_audio = "audio" in r.stdout

    outro_jingle = os.path.join(ASSETS, "music", "pp_outro.mp3")
    has_jingle = os.path.exists(outro_jingle)

    if has_jingle and outro_has_audio:
        ok = run_ffmpeg([
            "-i", OUTRO_VIDEO,
            "-i", outro_jingle,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[0:a]volume=0.7[va];[1:a]volume=0.9[vb];"
             f"[va][vb]amix=inputs=2:duration=shortest,"
             f"afade=t=out:st={fade_out_a}:d=1.0[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(outro_dur),
            output_path,
        ], "outro video + jingle", 120)
    elif has_jingle:
        ok = run_ffmpeg([
            "-i", OUTRO_VIDEO,
            "-i", outro_jingle,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[1:a]afade=t=out:st={fade_out_a}:d=1.0[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(outro_dur), "-shortest",
            output_path,
        ], "outro video + jingle (no orig audio)", 120)
    else:
        ok = run_ffmpeg([
            "-i", OUTRO_VIDEO,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p", "-vf", vf,
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], "outro video normalize", 120)

    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        logger.info(f"  Outro video: {dur:.1f}s")
        return output_path

    return ""


def make_tag_video(output_path: str, narration_audio: str = "") -> str:
    """Normalize tag_vertical.mp4 to 1920x1080 with fade-in/fade-out.

    Used as BOTH intro (fade-in from black) and outro (fade-to-black).
    If narration_audio provided, mix it at full volume over the tag video audio.
    """
    if not os.path.exists(TAG_VIDEO):
        logger.warning("tag_vertical.mp4 not found — skipping tag")
        return ""

    tag_dur = ffprobe_duration(TAG_VIDEO)
    if tag_dur <= 0:
        return ""

    fade_out_v = max(0, tag_dur - 0.5)
    vf = (f"scale=1920:1080:force_original_aspect_ratio=decrease,"
          f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p,"
          f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_v}:d=0.5")

    tag_src = ensure_audio(TAG_VIDEO)

    if narration_audio and os.path.exists(narration_audio):
        # Mix narration over tag audio
        fade_out_a = max(0, tag_dur - 1.0)
        ok = run_ffmpeg([
            "-i", tag_src,
            "-i", narration_audio,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[0:a]volume=0.3[tagaud];"
             f"[1:a]volume=1.0[narr];"
             f"[tagaud][narr]amix=inputs=2:duration=first,"
             f"afade=t=out:st={fade_out_a}:d=1.0[outa]"),
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(tag_dur),
            output_path,
        ], "tag video + narration", 60)
    else:
        ok = run_ffmpeg([
            "-i", tag_src,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p", "-vf", vf,
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], "tag video", 60)

    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        logger.info(f"  Tag video: {dur:.1f}s{' (with narration)' if narration_audio else ''}")
        return output_path

    return ""


# ── Cold open intro ───────────────────────────────────────────────────────

def make_intro_coldopen(tts_path: str, output_path: str, btc_price: str = "N/A", thumbnail_path: str = "") -> str:
    """APEX Cold Open intro — 2.0s cinematic intro card + voice.

    APEX background (7 layers) + corner brackets + centered title card.
    Voice starts on frame 1. No pre-roll.
    """
    import datetime
    tts_dur = ffprobe_duration(tts_path)
    total_dur = max(tts_dur + 0.3, 3.0)

    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()

    has_thumb_co = bool(thumbnail_path and os.path.exists(thumbnail_path))

    inp_args = [tts_path]
    idx = 1

    # APEX procedural background (7-layer)
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bgvig")
    fg = bg_fg

    # Thumbnail face panel (if available)
    thumb_co_idx = -1
    if has_thumb_co:
        inp_args.append(thumbnail_path)
        thumb_co_idx = idx
        idx += 1
    if has_thumb_co and thumb_co_idx >= 0:
        fg += (f"[{thumb_co_idx}:v]scale=1056:1080:force_original_aspect_ratio=increase,"
               f"crop=1056:1080,setsar=1,fps=30,trim=0:{total_dur},setpts=PTS-STARTPTS,"
               f"eq=saturation=1.15:brightness=0.04[thumbface];\n")
        fg += f"[thumbface]drawbox=x=940:y=0:w=116:h=1080:color={COLOR_BG}@0.7:t=fill[thumbblend];\n"
        fg += f"[bgvig][thumbblend]overlay=0:0[bgwithface];\n"
        face_base = "bgwithface"
    else:
        face_base = "bgvig"

    # APEX title text centered
    fg += (f"[{face_base}]"
           # PROTOCOL PULSE — centered white bold
           f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
           f"fontcolor={COLOR_WHITE}:fontsize=72:x=(w-text_w)/2:y=300,"
           # PULSE CHECK — centered warm-red bold
           f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
           f"fontcolor={COLOR_RED}:fontsize=52:x=(w-text_w)/2:y=400,"
           # Gold eyebrow date
           f"drawtext=fontfile={FONT_MONO}:text='{date_str} - DAILY INTELLIGENCE BRIEF':"
           f"fontcolor={COLOR_GOLD}:fontsize=18:x=(w-text_w)/2:y=490,"
           # // SIGNAL DETECTED //
           f"drawtext=fontfile={FONT_MONO}:text='// SIGNAL DETECTED //':"
           f"fontcolor={COLOR_RED}:fontsize=16:x=(w-text_w)/2:y=540,"
           # Fade in/out
           f"fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, total_dur - 0.4)}:d=0.4"
           f"[withtext];\n")

    # Waveform below title
    fg += (f"[0:a]showwaves=s=1920x120:mode=cline:"
           f"colors={COLOR_RED}|{COLOR_RED_WARM}:scale=sqrt:draw=full:rate=30[wave_raw];\n")
    fg += f"[withtext][wave_raw]overlay=0:620[withwave];\n"

    # Corner brackets
    fg += _build_corner_brackets_fg("withwave", "co_cornered")

    # APEX info rail
    fg += _build_signature_info_rail(total_dur, btc_price, "co_cornered", "v_final")
    fg += f"[v_final]format=yuv420p[outv];\n"

    # NO music — voice starts immediately
    fg += (f"[0:a]silenceremove=start_periods=1:start_duration=0.05:start_threshold=-50dB:"
           f"stop_periods=-1:stop_duration=0.1:stop_threshold=-50dB,"
           f"loudnorm=I=-14:TP=-1.5:LRA=7,aresample=async=1[outa]")

    ok = run_ffmpeg_filtergraph(
        inp_args, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "APEX intro cold open", 120,
    )
    return output_path if ok else ""


# ── Branded outro ─────────────────────────────────────────────────────────

def make_branded_outro(output_path: str, narration_audio: str = "") -> str:
    """Use PBX's branded outro video. Mix wrap narration audio over it.

    Falls back to tag_vertical.mp4 if outro_branded.mp4 not uploaded yet.
    """
    src = OUTRO_BRANDED if os.path.exists(OUTRO_BRANDED) else TAG_VIDEO
    if not os.path.exists(src):
        return ""

    dur = ffprobe_duration(src)
    if dur <= 0:
        return ""
    # Sprint 1.8: NO fade-to-black. Abrupt hard cut per PRODUCTION_DESIGN_LAWS.
    vf = (f"scale=1920:1080:force_original_aspect_ratio=increase,"
          f"crop=1920:1080,setsar=1,fps=30,format=yuv420p")

    if narration_audio and os.path.exists(narration_audio):
        ok = run_ffmpeg([
            "-i", src, "-i", narration_audio,
            "-filter_complex",
            "[0:a]volume=0.25[va];[1:a]volume=1.0[vb];[va][vb]amix=inputs=2:duration=longest[outa]",
            "-map", "0:v", "-map", "[outa]", "-vf", vf,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", output_path],
            "branded outro", 60)
    else:
        ok = run_ffmpeg([
            "-i", src, "-vf", vf,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", output_path],
            "branded outro", 60)

    if ok and os.path.exists(output_path):
        out_dur = ffprobe_duration(output_path)
        logger.info(f"  Branded outro: {out_dur:.1f}s{' (with narration)' if narration_audio else ''}")
        return output_path
    return ""


# ── Thumbnail fetcher ──────────────────────────────────────────────────────

def fetch_youtube_thumbnail(clip_info: dict) -> str:
    """Download YouTube thumbnail for a clip. Returns local path or ''."""
    video_id = clip_info.get("video_id", "")
    if not video_id:
        return ""
    thumb_path = f"/tmp/thumb_{video_id}.jpg"
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        import urllib.request
        url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        urllib.request.urlretrieve(url, thumb_path)
        return thumb_path if os.path.exists(thumb_path) else ""
    except Exception:
        try:
            url2 = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            urllib.request.urlretrieve(url2, thumb_path)
            return thumb_path if os.path.exists(thumb_path) else ""
        except Exception:
            return ""


# ── PiP preview for narration segments ──────────────────────────────────────

def make_pip_preview(clip_path: str, output_path: str, duration: float = 8.0) -> str:
    """Extract a muted PiP preview clip for overlay during narration.

    Issue 2: 820x462 PiP (right 40% panel), positioned at x=1056, y=200.
    ACTUAL VIDEO playing (muted), not static image with pan.
    Thin 2px white border at 30% opacity.
    """
    if not clip_path or not os.path.exists(clip_path):
        return ""
    clip_dur = ffprobe_duration(clip_path)
    if clip_dur < 10:
        return ""
    # Sprint 3.2: Extract from MIDPOINT of clip (better face shots)
    start = max(0, (clip_dur / 2) - (duration / 2))
    ok = run_ffmpeg([
        "-ss", str(start), "-i", clip_path,
        "-t", str(duration), "-an",
        "-vf", (
            "scale=820:462:force_original_aspect_ratio=decrease,"
            "pad=820:462:(ow-iw)/2:(oh-ih)/2:black,"
            "format=yuv420p"
        ),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-r", "30",
        output_path,
    ], "pip preview extract", 60)
    return output_path if ok and os.path.exists(output_path) else ""


def overlay_pip_on_narration(narration_path: str, pip_path: str,
                              output_path: str) -> str:
    """Overlay PiP preview clip onto narration video.

    Issue 2: Position x=1056, y=200 (right 40% panel, 820x462 PiP).
    Drop shadow behind PiP (drawbox at +4px offset, black@0.3).
    "COMING UP..." label inside PiP bottom-left.
    """
    if not pip_path or not os.path.exists(pip_path):
        return narration_path
    pip_dur = ffprobe_duration(pip_path)
    ok = run_ffmpeg([
        "-i", narration_path,
        "-i", pip_path,
        "-filter_complex",
        # Drop shadow: dark box at +4px offset behind PiP
        f"[0:v]drawbox=x=1060:y=204:w=824:h=466:color={COLOR_BG}@0.3:t=fill:enable='lte(t,{pip_dur})'[bg_shadow];"
        f"[1:v]drawtext=fontfile={FONT_BOLD}:text='COMING UP...':fontcolor={COLOR_TEXT}:fontsize=28:"
        f"x=12:y=h-38:box=1:boxcolor={COLOR_BG}@0.5:boxborderw=6,format=yuva420p[pip];"
        f"[bg_shadow][pip]overlay=1056:200:enable='lte(t,{pip_dur})',format=yuv420p[outv]",
        "-map", "[outv]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "copy", "-shortest",
        output_path,
    ], "pip overlay", 180)
    return output_path if ok and os.path.exists(output_path) else narration_path


def mix_lower_slide_sfx(video_path: str) -> str:
    """Mix lower_slide.wav SFX at the start of a clip with LowerThird."""
    if not os.path.exists(LOWER_SLIDE) or not os.path.exists(video_path):
        return video_path
    tmp = video_path + ".lslide.mp4"
    ok = run_ffmpeg([
        "-i", video_path,
        "-i", LOWER_SLIDE,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.5[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        tmp,
    ], "mix lower slide sfx", 30)
    if ok and os.path.exists(tmp):
        os.replace(tmp, video_path)
    elif os.path.exists(tmp):
        os.remove(tmp)
    return video_path


# ── Host dialogue visual ────────────────────────────────────────────────────

def _build_corner_brackets_fg(label_in: str, label_out: str) -> str:
    """Draw tactical corner brackets on all 4 corners — signal red."""
    return (
        f"[{label_in}]"
        f"drawbox=x=0:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=1040:w=4:h=40:color={COLOR_RED}:t=fill"
        f"[{label_out}];\n"
    )


# ══════════════════════════════════════════════════════════════════════════
# BROADCAST ENGINE V2 — 6-scene system
# ══════════════════════════════════════════════════════════════════════════

def _build_broadcast_bg(duration: float, label_out: str = "bb_bg") -> tuple:
    """APEX UNIFIED 7-layer procedural background.

    Layer 1: BEV2 cinematic obsidian base (#020304)
    Layer 2: BEV2 3-glow radial (top-left red, top-right white, bottom-center red)
    Layer 3: VDS perspective grid (bottom 30%, very subtle)
    Layer 4: BD scanlines (horizontal every 4px, red @2.5%)
    Layer 5: Vignette
    Layer 6: (film grain skipped — geq too slow per spec)
    Layer 7: Red border frame (2px all edges)
    """
    f = ""
    # Layer 1: Cinematic obsidian base
    f += f"color=c={COLOR_BG}:s=1920x1080:d={duration}:r=30[bb_base];\n"
    # Layer 2a: Red radial glow — top-left
    f += (f"color=c=0x000000:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(46*exp(-((X)*(X)+Y*Y)/350000),0,255)':g='0':b='0'[bb_glow_tl];\n")
    f += f"[bb_base][bb_glow_tl]blend=all_mode=screen[bb1];\n"
    # Layer 2b: White radial glow — top-right (subtle)
    f += (f"color=c=0x000000:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'"
          f":g='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'"
          f":b='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'[bb_glow_tr];\n")
    f += f"[bb1][bb_glow_tr]blend=all_mode=screen[bb2];\n"
    # Layer 2c: Red radial glow — bottom-center
    f += (f"color=c=0x000000:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(25*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/400000),0,255)':g='0':b='0'[bb_glow_bc];\n")
    f += f"[bb2][bb_glow_bc]blend=all_mode=screen[bb3];\n"
    # Layer 3: VDS perspective grid (bottom 30% — subtle white)
    f += f"[bb3]drawgrid=width=90:height=54:thickness=1:color=0xFFFFFF@0.04[bb4];\n"
    # Layer 4: BD scanlines (horizontal every 4px, red @2.5%)
    f += f"[bb4]drawgrid=width=0:height=4:thickness=1:color={COLOR_RED}@0.025[bb5];\n"
    # Layer 5: Vignette
    f += f"[bb5]vignette=PI/4:mode=backward[bb6];\n"
    # Layer 7: Red border frame (2px all edges)
    f += (f"[bb6]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill[{label_out}];\n")
    return ([], f)


def _build_top_system_bar(label_in: str, label_out: str, scene_label: str = "",
                           progress_pct: int = 50, recon_id: str = "") -> str:
    """APEX UNIFIED header — BD structure + BEV2 glassmorphic floating pill."""
    import datetime
    if not recon_id:
        recon_id = datetime.datetime.now().strftime("%H%M%S")
    fg = ""
    # Floating pill bg with glassmorphic feel
    fg += (f"[{label_in}]drawbox=x=20:y=12:w=1880:h=52:color=0x000000@0.55:t=fill,"
           # Red left accent line on pill (BD)
           f"drawbox=x=20:y=12:w=3:h=52:color={COLOR_RED}@0.9:t=fill,"
           # Left: bullet + PROTOCOL PULSE
           f"drawtext=fontfile={FONT_BOLD}:text='  PROTOCOL PULSE':"
           f"fontcolor={COLOR_WHITE}:fontsize=20:x=38:y=26,"
           # LIVE label in red
           f"drawtext=fontfile={FONT_BOLD}:text='LIVE':"
           f"fontcolor={COLOR_RED}:fontsize=16:x=236:y=30,"
           # Separator
           f"drawtext=fontfile={FONT_MONO}:text='|':"
           f"fontcolor={COLOR_MUTED}:fontsize=16:x=282:y=26,"
           # Broadcast Signature System (muted mono)
           f"drawtext=fontfile={FONT_MONO}:text='Broadcast Signature System':"
           f"fontcolor={COLOR_MUTED}:fontsize=11:x=302:y=31,"
           # Right: Motion Active
           f"drawtext=fontfile={FONT_MONO}:text='Motion Active':"
           f"fontcolor={COLOR_MUTED}:fontsize=11:x=1560:y=31,"
           f"drawtext=fontfile={FONT_MONO}:text='|':"
           f"fontcolor={COLOR_MUTED}:fontsize=11:x=1652:y=31,"
           # Narration Layer
           f"drawtext=fontfile={FONT_MONO}:text='Narration Layer':"
           f"fontcolor=0xFFFFFF@0.7:fontsize=11:x=1666:y=31,"
           f"drawtext=fontfile={FONT_MONO}:text='|':"
           f"fontcolor={COLOR_MUTED}:fontsize=11:x=1766:y=31,"
           # RECON-ID (BD metadata)
           f"drawtext=fontfile={FONT_MONO}:text='RECON-ID  {recon_id}':"
           f"fontcolor={COLOR_MUTED}:fontsize=11:x=1780:y=31,"
           # Bottom separator
           f"drawbox=x=20:y=64:w=1880:h=1:color={COLOR_RED}@0.25:t=fill"
           f"[{label_out}];\n")
    return fg


def _build_signature_info_rail(duration: float, btc_price: str, label_in: str,
                                label_out: str) -> str:
    """APEX UNIFIED gradient info rail — red→white→red with BLACK text."""
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # Build gradient bar: 3 color zones (red | white | warm red)
    fg += f"color=c={COLOR_RED}@0.85:s=640x48:d={duration}:r=30[rail_left];\n"
    fg += f"color=c=0xFFFFFF@0.90:s=640x48:d={duration}:r=30[rail_center];\n"
    fg += f"color=c=0xFF6680@0.85:s=640x48:d={duration}:r=30[rail_right];\n"
    fg += f"[rail_left][rail_center]hstack[rail_lc];\n"
    fg += f"[rail_lc][rail_right]hstack[rail_full];\n"
    # Overlay rail onto video at y=1032
    fg += f"[{label_in}][rail_full]overlay=0:1032[rail_ov];\n"
    # Text in BLACK over the gradient rail
    fg += (f"[rail_ov]drawtext=fontfile={FONT_BOLD}:text='BTC {safe_btc}':"
           f"fontcolor=0x000000:fontsize=14:x=20:y=1048,"
           f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOLPULSE.IO':"
           f"fontcolor=0x000000:fontsize=15:x=(w-text_w)/2:y=1047,"
           f"drawtext=fontfile={FONT_MONO}:text='{date_str} - DAILY BRIEF':"
           f"fontcolor=0x000000:fontsize=14:x=w-text_w-20:y=1048"
           f"[{label_out}];\n")
    return fg


def _build_narration_wave(label_in: str, label_out: str,
                          audio_out_label: str = "_nw_a_out") -> tuple:
    """APEX V2 Cipher Line waveform — dual-layer EKG at y=880, 160px zone.

    Uses asplit=3 to separate audio feeds:
      - 2 for visualization (primary + accent)
      - 1 for audio output (returned as audio_out_label)

    Returns (filtergraph_string, audio_out_pad) where audio_out_pad is the
    label to pass to _bv2_encode's audio_pad parameter.
    """
    fg = ""
    # Split audio: 2 for vis, 1 for output (FIX 3 — never share audio pads)
    fg += f"[0:a]asplit=3[_a_vis][_a_vis2][{audio_out_label}];\n"

    # PRIMARY: thin centerline wave — white, ultra-clean
    fg += (f"[_a_vis]showwaves=s=1920x80:mode=line:"
           f"colors=0xF4F5F8@0.9:scale=sqrt:draw=full:rate=30[_wave_line];\n")

    # SECONDARY: mirror reflection — warm red, low opacity
    fg += (f"[_a_vis2]showwaves=s=1920x80:mode=line:"
           f"colors=0xFF334D@0.25:scale=log:draw=full:rate=30[_wave_red];\n")
    fg += f"[_wave_red]vflip[_wave_red_flip];\n"

    # Stack: primary on top, flipped reflection below (total 160px)
    fg += f"[_wave_line][_wave_red_flip]vstack[_wave_stacked];\n"

    # Edge fade bars (top + bottom)
    fg += (f"[_wave_stacked]"
           f"drawbox=x=0:y=0:w=1920:h=20:color=0x020304@0.8:t=fill,"
           f"drawbox=x=0:y=140:w=1920:h=20:color=0x020304@0.8:t=fill"
           f"[_wave_faded];\n")

    # Thin red center dividing line (the "spine")
    fg += (f"[_wave_faded]drawbox=x=0:y=79:w=1920:h=2:"
           f"color=0xFF0000@0.35:t=fill[_wave_final];\n")

    # Position at y=880 (above info rail, 160px zone)
    fg += f"[{label_in}][_wave_final]overlay=0:880[{label_out}];\n"
    return fg, f"[{audio_out_label}]"


def _bv2_text_zone(label_in: str, label_out: str, eyebrow: str, headline: str,
                    body: str, tag: str = "") -> str:
    """APEX left 58% text zone — gold eyebrow kicker (VDS), warm white headline."""
    safe_eye = _sanitize_text(eyebrow)
    safe_head = _sanitize_text(headline)
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""
    safe_tag = _sanitize_text(tag) if tag else ""

    fg = ""
    # Gold eyebrow kicker (VDS)
    fg += (f"[{label_in}]drawtext=fontfile={FONT_MONO}:text='{safe_eye}':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[bv2_eye];\n")
    # Headline (large, with shadow for depth)
    fg += (f"[bv2_eye]drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor=0x111111:fontsize=64:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor={COLOR_WHITE}:fontsize=64:x=64:y=130[bv2_head];\n")
    # Body text
    if safe_body:
        fg += (f"[bv2_head]drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
               f"fontcolor=0xFFFFFF@0.6:fontsize=18:x=64:y=420:line_spacing=8[bv2_body];\n")
    else:
        fg += f"[bv2_head]copy[bv2_body];\n"
    # Tag pill (red accent)
    if safe_tag:
        fg += (f"[bv2_body]drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.15:t=fill,"
               f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.4:t=2,"
               f"drawtext=fontfile={FONT_MONO}:text='{safe_tag}':"
               f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590[{label_out}];\n")
    else:
        fg += f"[bv2_body]copy[{label_out}];\n"
    return fg


def _bv2_corner_brackets(label_in: str, label_out: str) -> str:
    """APEX corner brackets — BD tactical signal red (#FF0000)."""
    return _build_corner_brackets_fg(label_in, label_out)


def _bv2_encode(inputs, fg, output_path, total_dur, label="bv2 scene",
                audio_pad="[0:a]"):
    """Shared encode pipeline for BV2 scenes — TTS only, no per-segment music.

    APEX V2: Music is mixed ONCE continuously in concatenate_parts() after all
    segments are joined. Individual segments render with clean TTS audio only.

    audio_pad: the audio stream label to use (default [0:a]). Scenes that
    pre-split audio via asplit should pass their output pad here.
    """
    fg += (f"{audio_pad}silenceremove=start_periods=1:start_duration=0.05:start_threshold=-50dB:"
           f"stop_periods=-1:stop_duration=0.1:stop_threshold=-50dB,"
           f"loudnorm=I=-14:TP=-1.5:LRA=7,aresample=async=1[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label, 180,
    )
    return output_path if ok else ""


# ── BV2 Scene 1: COLD OPEN ──────────────────────────────────────────────

def make_cold_open_scene(audio_path: str, headline: str, body: str, tag: str,
                          output_path: str, btc_price: str = "N/A",
                          duration: float = 0) -> str:
    """APEX Cold Open — BD left impact panel + VDS 2x2 metric cards right."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    safe_head = _sanitize_text(headline)[:30]
    safe_body = _word_wrap(_sanitize_text(body), max_width=38, max_lines=4) if body else ""
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    inputs = [audio_path]
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    # Top system bar
    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=84)

    # LEFT PANEL (x=0,y=72,w=760,h=840) — BD structure
    fg += (f"[bv2_bar]drawbox=x=0:y=72:w=760:h=840:color={COLOR_PANEL}@0.88:t=fill,"
           # Red left border (BD)
           f"drawbox=x=0:y=72:w=5:h=840:color={COLOR_RED}@0.9:t=fill,"
           # GOLD eyebrow kicker (VDS) — only place gold appears
           f"drawtext=fontfile={FONT_MONO}:text='BREAKING INTELLIGENCE':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=22:y=96,"
           # White headline word 1 — large 72px (BD impact)
           f"drawtext=fontfile={FONT_BOLD}:text='SIGNAL':"
           f"fontcolor={COLOR_WHITE}:fontsize=72:x=18:y=118,"
           # Red headline word 2
           f"drawtext=fontfile={FONT_BOLD}:text='DETECTED':"
           f"fontcolor={COLOR_RED}:fontsize=72:x=18:y=198,"
           # Thin red divider
           f"drawbox=x=20:y=290:w=720:h=1:color={COLOR_RED}@0.3:t=fill,"
           # Body text (warm white mono)
           f"drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
           f"fontcolor={COLOR_WHITE}@0.8:fontsize=18:x=22:y=310:line_spacing=8,"
           # CTA pill
           f"drawbox=x=20:y=560:w=460:h=44:color={COLOR_RED_DIM}@0.9:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='BREAKING INTELLIGENCE // INCOMING':"
           f"fontcolor={COLOR_RED}:fontsize=13:x=34:y=574"
           f"[co_left];\n")

    # RIGHT PANEL — VDS 2x2 Metric Cards (x=780,y=100)
    metrics_data = [
        ("BTC PRICE", safe_btc, "+2.1 pct", True),
        ("HASHRATE", "1,056 EH/s", "+4.2 pct", True),
        ("ETF FLOW", "$340M", "+18 pct", True),
        ("MARGIN", "42 pct", "-1.2 pct", False),
    ]
    last = "co_left"
    for mi, (mlabel, mval, mdelta, mpos) in enumerate(metrics_data):
        mx = 780 + (mi % 2) * 540
        my = 100 + (mi // 2) * 210
        dc = COLOR_GREEN if mpos else COLOR_CORAL
        accent = f"{COLOR_RED}@0.6" if mi > 0 else f"{COLOR_GOLD}@0.6"
        out = f"co_card{mi}"
        fg += (f"[{last}]drawbox=x={mx}:y={my}:w=520:h=190:color={COLOR_PANEL2}@0.95:t=fill,"
               # Top accent line (gold for first card, red for rest)
               f"drawbox=x={mx}:y={my}:w=520:h=3:color={accent}:t=fill,"
               # Gold eyebrow label (VDS)
               f"drawtext=fontfile={FONT_MONO}:text='{mlabel}':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={mx+16}:y={my+14},"
               # White metric value
               f"drawtext=fontfile={FONT_BOLD}:text='{mval}':"
               f"fontcolor={COLOR_WHITE}:fontsize=42:x={mx+16}:y={my+40},"
               # Delta with emerald/coral
               f"drawtext=fontfile={FONT_MONO}:text='{mdelta}':"
               f"fontcolor={dc}:fontsize=13:x={mx+16}:y={my+100}"
               f"[{out}];\n")
        last = out

    # Chart panel below cards (x=780,y=520,w=1100,h=380)
    fg += (f"[{last}]drawbox=x=780:y=520:w=1100:h=380:color={COLOR_PANEL}@0.9:t=fill,"
           f"drawbox=x=780:y=520:w=1100:h=1:color=0xFFFFFF@0.06:t=fill,"
           # Gold label
           f"drawtext=fontfile={FONT_MONO}:text='BTC NETWORK STRESS':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=800:y=538,"
           # Model Active pill
           f"drawbox=x=1720:y=534:w=120:h=24:color={COLOR_GOLD}@0.12:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='Model Active':"
           f"fontcolor={COLOR_GOLD}:fontsize=10:x=1735:y=539"
           f"[co_chart_hdr];\n")

    # Stylized rising chart bars (red gradient)
    chart_x_start = 820
    chart_y_base = 850
    chart_w = 1020
    step_w = chart_w // 10
    heights = [30, 45, 38, 60, 55, 72, 85, 78, 95, 110]
    last_chart = "co_chart_hdr"
    for ci, ch in enumerate(heights):
        cx = chart_x_start + ci * step_w
        cy = chart_y_base - ch
        out_c = f"co_cbar{ci}"
        fg += (f"[{last_chart}]drawbox=x={cx}:y={cy}:w={step_w-4}:h={ch}:"
               f"color={COLOR_RED}@0.6:t=fill[{out_c}];\n")
        last_chart = out_c

    # Pulse dot at chart tip
    fg += (f"[{last_chart}]drawbox=x={chart_x_start + 9*step_w + step_w//2 - 6}:"
           f"y={chart_y_base - heights[-1] - 8}:w=12:h=12:"
           f"color={COLOR_RED}:t=fill[co_chart_done];\n")

    # Corner brackets
    fg += _build_corner_brackets_fg("co_chart_done", "co_corners")
    # Narration wave (FIX 3: returns tuple with audio_out_pad)
    wave_fg, co_audio_pad = _build_narration_wave("co_corners", "co_wave", "co_a_out")
    fg += wave_fg
    # Info rail
    fg += _build_signature_info_rail(total_dur, btc_price, "co_wave", "co_railed")
    fg += f"[co_railed]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX cold open",
                       audio_pad=co_audio_pad)


# ── BV2 Scene 2: NARRATOR + PiP (SIGNATURE) ─────────────────────────────

def make_narrator_pip_scene(audio_path: str, headline: str, body: str,
                             speaker: str, next_speaker: str,
                             thumb_path: str, output_path: str,
                             btc_price: str = "N/A", duration: float = 0) -> str:
    """APEX Narrator + PiP — BEV2 architecture + BD tactical brackets on PiP."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    inputs = [audio_path]
    inp_idx = 1
    has_thumb = bool(thumb_path and os.path.exists(thumb_path))
    if has_thumb:
        inputs.append(thumb_path)
        thumb_idx = inp_idx
        inp_idx += 1
    else:
        thumb_idx = -1

    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=67)

    # Left text zone with gold eyebrow
    safe_speaker = _sanitize_text(speaker)[:12]
    safe_head = _sanitize_text(headline)[:40]
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""

    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='NARRATIVE SETUP // {safe_speaker}':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[np_eye];\n")
    fg += (f"[np_eye]drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor=0x111111:fontsize=64:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor={COLOR_WHITE}:fontsize=64:x=64:y=130[np_head];\n")
    if safe_body:
        fg += (f"[np_head]drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
               f"fontcolor=0xFFFFFF@0.6:fontsize=18:x=64:y=420:line_spacing=8[np_body];\n")
    else:
        fg += f"[np_head]copy[np_body];\n"

    # ORACLE NARRATION ACTIVE + Story Arc Locked pills
    fg += (f"[np_body]drawbox=x=64:y=580:w=280:h=32:color={COLOR_RED}@0.15:t=fill,"
           f"drawbox=x=64:y=580:w=280:h=32:color={COLOR_RED}@0.4:t=2,"
           f"drawtext=fontfile={FONT_MONO}:text='ORACLE NARRATION ACTIVE':"
           f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590,"
           f"drawbox=x=64:y=620:w=200:h=28:color={COLOR_RED}@0.1:t=fill,"
           f"drawbox=x=64:y=620:w=200:h=28:color={COLOR_RED}@0.3:t=2,"
           f"drawtext=fontfile={FONT_MONO}:text='Story Arc Locked':"
           f"fontcolor={COLOR_RED}:fontsize=11:x=80:y=628"
           f"[np_pills];\n")

    # Right PiP preview panel (x=1120, y=140, w=740, h=500)
    # Gold eyebrow above PiP
    fg += (f"[np_pills]drawtext=fontfile={FONT_MONO}:text='COMING UP NEXT':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=122[np_pip_eye];\n")
    fg += (f"[np_pip_eye]drawbox=x=1120:y=140:w=740:h=500:color={COLOR_PANEL}@0.92:t=fill,"
           f"drawbox=x=1120:y=140:w=740:h=1:color=0xFFFFFF@0.1:t=fill,"
           f"drawbox=x=1120:y=639:w=740:h=1:color=0xFFFFFF@0.1:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='Muted Preview':"
           f"fontcolor=0xFFFFFF@0.35:fontsize=11:x=1720:y=152"
           f"[np_pip_hdr];\n")

    # Thumbnail or placeholder inside preview box
    if has_thumb and thumb_idx >= 0:
        fg += (f"[{thumb_idx}:v]scale=716:370:force_original_aspect_ratio=increase,"
               f"crop=716:370,setsar=1,fps=30,trim=0:{total_dur},setpts=PTS-STARTPTS[np_thumb];\n")
        fg += f"[np_pip_hdr][np_thumb]overlay=1132:200[np_pip_thumb];\n"
        pip_base = "np_pip_thumb"
    else:
        fg += (f"[np_pip_hdr]drawbox=x=1132:y=200:w=716:h=370:color=0x080808:t=fill,"
               f"drawbox=x=1400:y=280:w=180:h=220:color=0x111111:t=fill"
               f"[np_pip_placeholder];\n")
        pip_base = "np_pip_placeholder"

    # Lower third in preview
    safe_next = _sanitize_text(next_speaker)[:30] if next_speaker else "NEXT SOURCE"
    fg += (f"[{pip_base}]drawbox=x=1132:y=520:w=716:h=50:color=0x000000@0.7:t=fill,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_next}':"
           f"fontcolor={COLOR_WHITE}:fontsize=18:x=1148:y=534,"
           f"drawbox=x=1720:y=528:w=110:h=24:color={COLOR_RED}@0.12:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='Preview Active':"
           f"fontcolor={COLOR_RED}:fontsize=10:x=1730:y=533,"
           # BD tactical mini corner brackets on PiP frame (16px)
           f"drawbox=x=1120:y=140:w=16:h=3:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1120:y=140:w=3:h=16:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1844:y=140:w=16:h=3:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1857:y=140:w=3:h=16:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1120:y=637:w=16:h=3:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1120:y=624:w=3:h=16:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1844:y=637:w=16:h=3:color={COLOR_RED}:t=fill,"
           f"drawbox=x=1857:y=624:w=3:h=16:color={COLOR_RED}:t=fill"
           f"[np_pip_final];\n")

    # Corner brackets (main frame)
    fg += _build_corner_brackets_fg("np_pip_final", "np_corners")
    wave_fg, np_audio_pad = _build_narration_wave("np_corners", "np_wave", "np_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "np_wave", "np_railed")
    fg += f"[np_railed]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX narrator+pip",
                       audio_pad=np_audio_pad)


# ── BV2 Scene 3: PARTNER CLIP ───────────────────────────────────────────

def make_partner_clip_scene(video_path: str, audio_path: str, speaker: str,
                             quote: str, output_path: str,
                             btc_price: str = "N/A", duration: float = 0) -> str:
    """APEX Partner Clip — BEV2 restraint. Full-frame, premium lower-third, no competing animations."""
    clip_dur = ffprobe_duration(video_path)
    if clip_dur <= 0:
        logger.warning(f"Partner clip has zero duration: {video_path}")
        return ""

    safe_speaker = _sanitize_text(speaker)[:30] if speaker else "SOURCE"
    safe_quote = _sanitize_text(quote)[:60] if quote else ""
    safe_btc = btc_price.replace("'", "").replace('"', "")

    import datetime
    ts_str = datetime.datetime.now().strftime("%H-%M UTC")

    fade_out_start = max(0, clip_dur - 0.5)
    fg = ""
    # Full frame clip
    fg += (f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
           f"setsar=1,fps=30,fade=t=in:d=0.3,fade=t=out:st={fade_out_start}:d=0.5[pc_clip];\n")
    # Red border frame (2px)
    fg += (f"[pc_clip]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
           f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
           f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
           f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill[pc_framed];\n")
    # Top-right watermark (red, 18px, 60% opacity)
    fg += (f"[pc_framed]drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
           f"fontcolor={COLOR_RED}@0.6:fontsize=18:x=W-text_w-24:y=18[pc_wm];\n")
    # BD corner brackets
    fg += _build_corner_brackets_fg("pc_wm", "pc_corners")
    # Glass lower-third with red top accent
    fg += (f"[pc_corners]drawbox=x=0:y=870:w=800:h=110:color=0x000000@0.88:t=fill,"
           f"drawbox=x=0:y=870:w=800:h=4:color={COLOR_RED}:t=fill,"
           # Speaker name (bold 26px)
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_speaker}':"
           f"fontcolor={COLOR_WHITE}:fontsize=26:x=24:y=890,"
           # Source info
           f"drawtext=fontfile={FONT_MONO}:text='{safe_quote}':"
           f"fontcolor=0xFFFFFF@0.6:fontsize=16:x=24:y=928,"
           f"drawtext=fontfile={FONT_MONO}:text='{ts_str}':"
           f"fontcolor=0xFFFFFF@0.35:fontsize=11:x=740:y=878"
           f"[pc_lt];\n")
    # Info rail (always present)
    fg += _build_signature_info_rail(clip_dur, btc_price, "pc_lt", "pc_railed")
    fg += (f"[pc_railed]format=yuv420p[outv];\n"
           # Audio: preserve original, normalize
           f"[0:a]asetpts=PTS-STARTPTS,"
           f"highpass=f=50,lowpass=f=15000,loudnorm=I=-14:TP=-1.5:LRA=7,"
           f"afade=t=in:d=0.3,afade=t=out:st={fade_out_start}:d=0.5[outa]")

    ok = run_ffmpeg_filtergraph(
        [video_path], fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k"],
        output_path, f"APEX partner clip ({safe_speaker})",
    )
    return output_path if ok else ""


# ── BV2 Scene 4: DATA SEGMENT ───────────────────────────────────────────

def make_data_segment_scene(audio_path: str, headline: str, metrics: list,
                             output_path: str, btc_price: str = "N/A",
                             duration: float = 0) -> str:
    """APEX Data Segment — gold eyebrow cards + emerald/coral deltas + chart."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    inputs = [audio_path]
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=72)

    # Left text zone with gold eyebrow
    safe_head = _sanitize_text(headline)[:40]
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='MARKET STRUCTURE':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[ds_eye];\n")
    fg += (f"[ds_eye]drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor=0x111111:fontsize=64:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor={COLOR_WHITE}:fontsize=64:x=64:y=130,"
           # ANALYTICS tag pill
           f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.15:t=fill,"
           f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.4:t=2,"
           f"drawtext=fontfile={FONT_MONO}:text='ANALYTICS':"
           f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590"
           f"[ds_txt];\n")

    # 2x2 metric card grid with gold eyebrow labels (VDS)
    default_metrics = [
        ("BTC", btc_price, "+2.1 pct", True),
        ("HASHRATE", "1,056 EH/s", "+4.2 pct", True),
        ("ETF FLOW", "$340M", "+18 pct", True),
        ("MARGIN", "42 pct", "-1.2 pct", False),
    ]
    use_metrics = []
    if metrics and len(metrics) >= 4:
        for m in metrics[:4]:
            if isinstance(m, dict):
                use_metrics.append((
                    m.get("label", "DATA"),
                    _sanitize_text(str(m.get("value", "N/A"))),
                    _sanitize_text(str(m.get("delta", ""))),
                    m.get("positive", True),
                ))
            elif isinstance(m, (list, tuple)) and len(m) >= 3:
                use_metrics.append((str(m[0]), _sanitize_text(str(m[1])),
                                    _sanitize_text(str(m[2])),
                                    m[3] if len(m) > 3 else True))
    if len(use_metrics) < 4:
        use_metrics = default_metrics

    last = "ds_txt"
    for mi, (mlabel, mval, mdelta, mpos) in enumerate(use_metrics):
        mx = 64 + (mi % 2) * 360
        my = 460 + (mi // 2) * 160
        dc = COLOR_GREEN if mpos else COLOR_CORAL
        out = f"ds_dm{mi}"
        fg += (f"[{last}]drawbox=x={mx}:y={my}:w=340:h=140:color={COLOR_PANEL2}@0.95:t=fill,"
               f"drawbox=x={mx}:y={my}:w=340:h=3:color={COLOR_RED}@0.5:t=fill,"
               # Gold eyebrow label (VDS)
               f"drawtext=fontfile={FONT_MONO}:text='{mlabel}':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={mx+16}:y={my+14},"
               f"drawtext=fontfile={FONT_BOLD}:text='{mval}':"
               f"fontcolor={COLOR_WHITE}:fontsize=28:x={mx+16}:y={my+38},"
               # Emerald/coral delta (VDS)
               f"drawtext=fontfile={FONT_MONO}:text='{mdelta}':"
               f"fontcolor={dc}:fontsize=13:x={mx+16}:y={my+80}"
               f"[{out}];\n")
        last = out

    # FIX 5: Try TradingView chart screenshot, fallback to static bars
    tv_chart_path = ""
    try:
        from chart_capture import get_chart
        tv_chart_path = get_chart("btc_usd_1d")
    except Exception as e:
        logger.warning(f"  TradingView chart capture unavailable: {e}")

    if tv_chart_path and os.path.exists(tv_chart_path):
        # Live TradingView chart overlay
        inputs.append(tv_chart_path)
        chart_input_idx = len(inputs) - 1
        fg += (f"[{last}]drawbox=x=1120:y=90:w=760:h=820:color={COLOR_PANEL}@0.92:t=fill,"
               f"drawbox=x=1120:y=90:w=760:h=1:color=0xFFFFFF@0.08:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='TRADINGVIEW // BTCUSD 1D':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=108,"
               f"drawbox=x=1720:y=105:w=100:h=24:color={COLOR_GREEN}@0.15:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='LIVE CHART':"
               f"fontcolor={COLOR_GREEN}:fontsize=10:x=1732:y=110"
               f"[ds_chart_hdr];\n")
        fg += (f"[{chart_input_idx}:v]scale=740:700:force_original_aspect_ratio=decrease,"
               f"pad=740:700:(ow-iw)/2:(oh-ih)/2:color=0x050607[ds_tv_chart];\n")
        fg += f"[ds_chart_hdr][ds_tv_chart]overlay=1130:130[ds_chart_done];\n"
    else:
        # Fallback: static FFmpeg chart bars
        fg += (f"[{last}]drawbox=x=1120:y=90:w=760:h=820:color={COLOR_PANEL}@0.92:t=fill,"
               f"drawbox=x=1120:y=90:w=760:h=1:color=0xFFFFFF@0.08:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='BTC NETWORK STRESS':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=108,"
               f"drawbox=x=1720:y=105:w=100:h=24:color={COLOR_GOLD}@0.12:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='Model Active':"
               f"fontcolor={COLOR_GOLD}:fontsize=10:x=1732:y=110"
               f"[ds_chart_hdr];\n")
        chart_x_start = 1160
        chart_y_base = 800
        chart_w = 680
        step_w = chart_w // 10
        heights = [30, 45, 38, 60, 55, 72, 85, 78, 95, 110]
        last_chart = "ds_chart_hdr"
        for ci, ch in enumerate(heights):
            cx = chart_x_start + ci * step_w
            cy = chart_y_base - ch
            out_c = f"ds_cbar{ci}"
            fg += (f"[{last_chart}]drawbox=x={cx}:y={cy}:w={step_w-4}:h={ch}:"
                   f"color={COLOR_RED}@0.6:t=fill[{out_c}];\n")
            last_chart = out_c
        fg += (f"[{last_chart}]drawbox=x={chart_x_start + 9*step_w + step_w//2 - 6}:"
               f"y={chart_y_base - heights[-1] - 8}:w=12:h=12:"
               f"color={COLOR_RED}:t=fill[ds_chart_done];\n")

    fg += _build_corner_brackets_fg("ds_chart_done", "ds_corners")
    wave_fg, ds_audio_pad = _build_narration_wave("ds_corners", "ds_wave", "ds_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "ds_wave", "ds_railed")
    fg += f"[ds_railed]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX data segment",
                       audio_pad=ds_audio_pad)


# ── BV2 Scene 5: SOCIAL STACK ───────────────────────────────────────────

def make_social_stack_scene(audio_path: str, headline: str, social_cards: list,
                             output_path: str, btc_price: str = "N/A",
                             duration: float = 0,
                             card_timings: list = None) -> str:
    """APEX Social Stack — FIX 4: cards LOCKED to TTS timing.

    Cards appear/disappear synchronized with narration. Each card is visible
    only during its time slice. Active card: red border + full opacity.
    Past/future cards: dim panel + muted opacity.
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    inputs = [audio_path]
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=58)

    # Header zone with gold eyebrow
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='SIGNAL LAYER':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(headline)[:40]}':"
           f"fontcolor={COLOR_WHITE}:fontsize=48:x=64:y=130,"
           f"drawtext=fontfile={FONT_MONO}:text='Bitcoin Social Conviction Index':"
           f"fontcolor=0xFFFFFF@0.5:fontsize=16:x=64:y=200"
           f"[ss_hdr];\n")

    default_cards = [
        {"name": "Signal Source", "handle": "@signal", "score": "96", "text": "Bitcoin conviction remains extremely high", "tag": "HIGH CONVICTION"},
        {"name": "Market Intel", "handle": "@intel", "score": "84", "text": "Structural demand continues to build", "tag": "STRUCTURAL"},
        {"name": "Macro Watch", "handle": "@macro", "score": "72", "text": "Global liquidity conditions favor BTC", "tag": "MACRO SIGNAL"},
    ]
    cards = social_cards[:3] if social_cards and len(social_cards) >= 1 else default_cards
    while len(cards) < 3:
        cards.append(default_cards[len(cards) % 3])

    n_cards = min(len(cards), 3)

    # FIX 4: Calculate per-card timing — divide narration evenly across cards
    if card_timings and len(card_timings) >= n_cards:
        timings = card_timings[:n_cards]
    else:
        tpc = total_dur / n_cards if n_cards > 0 else total_dur
        timings = [(i * tpc, (i + 1) * tpc) for i in range(n_cards)]

    tags = ["HIGH CONVICTION", "STRUCTURAL", "MACRO SIGNAL"]
    last = "ss_hdr"
    for ci, card in enumerate(cards[:n_cards]):
        cx = 64 + ci * 608
        cy = 300
        cw = 580
        ch = 620

        t_start, t_end = timings[ci]
        # FIX 4: Active card = red border + full text; inactive = dim panel
        # Use enable expressions for active state highlighting
        active_enable = f"enable='between(t,{t_start:.2f},{t_end:.2f})'"
        inactive_enable = f"enable='not(between(t,{t_start:.2f},{t_end:.2f}))'"

        name = _sanitize_text(str(card.get("name", card.get("handle", "Source"))))[:20]
        handle = _sanitize_text(str(card.get("handle", "@source")))[:20]
        score = str(card.get("score", card.get("likes", "80")))[:6]
        ctext = _word_wrap(_sanitize_text(str(card.get("text", ""))), max_width=24, max_lines=4)
        ctag = _sanitize_text(str(card.get("tag", tags[ci % 3])))[:20]

        out = f"ss_sc{ci}"
        # Card background (always visible but dimmed when inactive)
        fg += (f"[{last}]drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color={COLOR_PANEL}@0.92:t=fill,"
               # Active: red border
               f"drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color={COLOR_RED}@0.4:t=2:{active_enable},"
               # Inactive: subtle white border
               f"drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color=0xFFFFFF@0.08:t=2:{inactive_enable},"
               # Avatar placeholder
               f"drawbox=x={cx+24}:y={cy+24}:w=44:h=44:color={COLOR_RED}@0.5:t=fill,"
               # Name
               f"drawtext=fontfile={FONT_BOLD}:text='{name}':"
               f"fontcolor={COLOR_WHITE}:fontsize=16:x={cx+80}:y={cy+28},"
               # Handle
               f"drawtext=fontfile={FONT_MONO}:text='{handle}':"
               f"fontcolor=0xFFFFFF@0.35:fontsize=12:x={cx+80}:y={cy+50},"
               # VDS gold score badge
               f"drawbox=x={cx+cw-90}:y={cy+28}:w=70:h=24:color={COLOR_GOLD}@0.15:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='{score} / 100':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={cx+cw-84}:y={cy+34},"
               # Quote text
               f"drawtext=fontfile={FONT_BOLD}:text='{ctext}':"
               f"fontcolor={COLOR_WHITE}:fontsize=20:x={cx+24}:y={cy+100}:line_spacing=10,"
               # VDS gold tag label at bottom
               f"drawtext=fontfile={FONT_MONO}:text='{ctag}':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={cx+24}:y={cy+ch-36},"
               # Active indicator: "ACTIVE" tag when card is current
               f"drawtext=fontfile={FONT_MONO}:text='ACTIVE':"
               f"fontcolor={COLOR_RED}:fontsize=11:x={cx+cw-70}:y={cy+ch-36}:{active_enable}"
               f"[{out}];\n")
        last = out

    fg += _build_corner_brackets_fg(last, "ss_corners")
    wave_fg, ss_audio_pad = _build_narration_wave("ss_corners", "ss_wave", "ss_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "ss_wave", "ss_railed")
    fg += f"[ss_railed]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX social stack",
                       audio_pad=ss_audio_pad)


# ── BV2 Scene 6: WRAP / VERDICT ─────────────────────────────────────────

def make_wrap_scene(audio_path: str, headline: str, body: str,
                     output_path: str, btc_price: str = "N/A",
                     duration: float = 0) -> str:
    """APEX Wrap — BEV2 waveform + BD episode segments tracker + gold accents."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    safe_head = _sanitize_text(headline)[:40]
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""

    inputs = [audio_path]
    _, bg_fg = _build_broadcast_bg(total_dur, label_out="bb_bg")
    fg = bg_fg

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=100)

    # Left text zone with gold eyebrow
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='FINAL TAKE':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[wr_eye];\n")
    fg += (f"[wr_eye]drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor=0x111111:fontsize=64:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_head}':"
           f"fontcolor={COLOR_WHITE}:fontsize=64:x=64:y=130[wr_head];\n")
    if safe_body:
        fg += (f"[wr_head]drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
               f"fontcolor=0xFFFFFF@0.6:fontsize=18:x=64:y=420:line_spacing=8[wr_body];\n")
    else:
        fg += f"[wr_head]copy[wr_body];\n"
    fg += (f"[wr_body]drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.15:t=fill,"
           f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.4:t=2,"
           f"drawtext=fontfile={FONT_MONO}:text='RESOLVE':"
           f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590[wr_txt];\n")

    # Right Signal Wave panel (x=1120, y=140, w=740, h=500)
    fg += (f"[wr_txt]drawbox=x=1120:y=140:w=740:h=500:color={COLOR_PANEL}@0.92:t=fill,"
           f"drawbox=x=1120:y=140:w=740:h=1:color=0xFFFFFF@0.08:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='Signal Wave':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=158"
           f"[wr_panel];\n")
    # FIX 3: Single asplit for ALL audio consumers in wrap scene
    # 1=big waveform, 2+3=narration wave (primary+accent)
    fg += f"[0:a]asplit=4[_wr_a_big][_wr_a_nav1][_wr_a_nav2][_wr_a_out];\n"

    # Large waveform inside panel
    fg += (f"[_wr_a_big]showwaves=s=700x350:mode=cline:"
           f"colors={COLOR_RED}|{COLOR_WHITE}:scale=sqrt:draw=full:rate=30[wr_sigwave];\n")
    fg += f"[wr_panel][wr_sigwave]overlay=1140:220[wr_waved];\n"

    # BD Episode Segments tracker (x=1120,y=660,w=740,h=240)
    fg += (f"[wr_waved]drawtext=fontfile={FONT_MONO}:text='EPISODE SEGMENTS':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=1140:y=655[wr_seg_eye];\n")
    segments = [
        ("COLD OPEN", "DONE"),
        ("ORACLE BRIEF", "DONE"),
        ("CLIP REACTION", "DONE"),
        ("DUAL-HOST", "ACTIVE"),
    ]
    last_seg = "wr_seg_eye"
    for si, (sname, sstatus) in enumerate(segments):
        sy = 675 + si * 44
        if sstatus == "DONE":
            sc = COLOR_GREEN
        elif sstatus == "ACTIVE":
            sc = COLOR_RED
        else:
            sc = COLOR_MUTED2
        out_s = f"wr_seg{si}"
        fg += (f"[{last_seg}]drawbox=x=1140:y={sy}:w=700:h=36:color={COLOR_PANEL2}@0.8:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='{sname}':"
               f"fontcolor={COLOR_WHITE}@0.7:fontsize=12:x=1156:y={sy+10},"
               f"drawtext=fontfile={FONT_MONO}:text='{sstatus}':"
               f"fontcolor={sc}:fontsize=12:x=1740:y={sy+10}"
               f"[{out_s}];\n")
        last_seg = out_s

    fg += _build_corner_brackets_fg(last_seg, "wr_corners")

    # Inline Cipher Line wave using pre-split audio pads (FIX 3)
    fg += (f"[_wr_a_nav1]showwaves=s=1920x80:mode=line:"
           f"colors=0xF4F5F8@0.9:scale=sqrt:draw=full:rate=30[_wr_wl];\n")
    fg += (f"[_wr_a_nav2]showwaves=s=1920x80:mode=line:"
           f"colors=0xFF334D@0.25:scale=log:draw=full:rate=30[_wr_wr];\n")
    fg += f"[_wr_wr]vflip[_wr_wrf];\n"
    fg += f"[_wr_wl][_wr_wrf]vstack[_wr_ws];\n"
    fg += (f"[_wr_ws]drawbox=x=0:y=0:w=1920:h=20:color=0x020304@0.8:t=fill,"
           f"drawbox=x=0:y=140:w=1920:h=20:color=0x020304@0.8:t=fill[_wr_wf];\n")
    fg += f"[_wr_wf]drawbox=x=0:y=79:w=1920:h=2:color=0xFF0000@0.35:t=fill[_wr_wfin];\n"
    fg += f"[wr_corners][_wr_wfin]overlay=0:880[wr_ekg];\n"

    fg += _build_signature_info_rail(total_dur, btc_price, "wr_ekg", "wr_railed")
    fg += f"[wr_railed]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX wrap",
                       audio_pad="[_wr_a_out]")


# ── BV2 Scene Router ────────────────────────────────────────────────────

def select_scene_type(segment_type: str, segment_index: int, total_segments: int) -> str:
    """Route segment to appropriate BV2 scene type.

    APEX V2 FIX 7 — PiP-first order:
      0: cold_open (title card intro)
      1: narrator_pip (dual host commentary — LEADS the episode)
      2: partner_clip (YouTube clip)
      3: react (hosts react to clip)
      4: data_segment (price action + chart)
      5: social_stack (tweet conviction)
      6+: wrap (closing)
    """
    if segment_index == 0:
        return "cold_open"
    elif segment_index == 1 or segment_type in ("setup", "intro", "pip"):
        return "narrator_pip"  # FIX 7: PiP FIRST after cold open
    elif segment_type == "broll":
        return "partner_clip"
    elif segment_type == "data":
        return "data_segment"
    elif segment_type in ("social", "social_segment"):
        return "social_stack"
    elif segment_type == "tradfi_weekly":
        return "data_segment"  # Suits & Sats uses data_segment with SUITS & SATS eyebrow
    elif segment_type == "x_spaces":
        return "data_segment"  # X Spaces uses data_segment visual with branded eyebrow
    elif segment_type in ("wrap", "outro") or segment_index == total_segments - 1:
        return "wrap"
    elif segment_type == "react":
        return "narrator_pip"  # react uses same visual as narrator_pip
    else:
        return "narrator_pip"


def make_broadcast_segment(segment_data: dict, audio_path: str, host_num: int,
                            segment_index: int, total_segments: int,
                            output_path: str, btc_price: str = "N/A",
                            thumbnail_path: str = "",
                            clip_path: str = "",
                            social_posts: list = None) -> str:
    """Route to appropriate BV2 scene function based on segment type and position.

    Falls back to make_host_visual if BV2 scene fails.
    """
    seg_type = segment_data.get("type", "")
    text = segment_data.get("text", "")
    speaker = segment_data.get("speaker", "DEBORAH" if host_num == 1 else "BRIAN")
    scene = select_scene_type(seg_type, segment_index, total_segments)

    try:
        if scene == "cold_open":
            return make_cold_open_scene(
                audio_path, text[:60], text, "REDLINE",
                output_path, btc_price=btc_price,
            )
        elif scene == "narrator_pip":
            next_speaker = segment_data.get("next_speaker", "")
            return make_narrator_pip_scene(
                audio_path, text[:60], text, speaker, next_speaker,
                thumbnail_path, output_path, btc_price=btc_price,
            )
        elif scene == "partner_clip" and clip_path:
            return make_partner_clip_scene(
                clip_path, audio_path, speaker, text[:60],
                output_path, btc_price=btc_price,
            )
        elif scene == "data_segment":
            metrics = segment_data.get("metrics", [])
            return make_data_segment_scene(
                audio_path, text[:60], metrics,
                output_path, btc_price=btc_price,
            )
        elif scene == "social_stack":
            return make_social_stack_scene(
                audio_path, text[:60], social_posts or [],
                output_path, btc_price=btc_price,
            )
        elif scene == "wrap":
            return make_wrap_scene(
                audio_path, text[:60], text,
                output_path, btc_price=btc_price,
            )
    except Exception as e:
        logger.warning(f"BV2 scene '{scene}' failed: {e} — falling back to make_host_visual")

    # Fallback to Black Diamond host visual
    return make_host_visual(
        audio_path, host_num, text, output_path,
        btc_price=btc_price, label=f"bv2_fallback_{seg_type}",
        thumbnail_path=thumbnail_path, segment_type=seg_type,
    )


# ══════════════════════════════════════════════════════════════════════════
# BLACK DIAMOND (legacy) — kept as fallback
# ══════════════════════════════════════════════════════════════════════════

def make_host_visual(audio_path: str, host: int, text: str,
                     output_path: str, btc_price: str = "N/A",
                     label: str = "", thumbnail_path: str = "",
                     segment_type: str = "") -> str:
    """BLACK DIAMOND Command Center layout — Sovereign Command Center.

    Left impact panel + right waveform + data grid + ticker + corner brackets.
    Background music at -18dB under TTS.
    """
    import datetime as _dt
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = audio_dur + 0.3

    host_names = {1: "DEBORAH", 2: "BRIAN"}
    speaker = host_names.get(host, "HOST")

    safe_btc = btc_price.replace("'", "").replace('"', "")

    is_social = segment_type == "social_segment"

    # Eyebrow / headline logic by segment_type
    seg_map = {
        "cold_open": ("COLD OPEN // BREAKING SIGNAL", "SIGNAL", "DETECTED"),
        "setup":     (f"ANALYST // {speaker}", speaker[:6], "REPORTING"),
        "react":     (f"REACTION // {speaker}", speaker[:6], "REACTS"),
        "wrap":      (f"CLOSING // {speaker}", speaker[:6], "CONFIRMED"),
        "x_spaces":  ("◆ X SPACES // LIVE INTEL", "SPACES", "LIVE"),
        "tradfi_weekly": ("◆ SUITS & SATS // BITCOIN LENS", "TRADFI", "BITCOIN LENS"),
    }
    eyebrow, h1, h2 = seg_map.get(segment_type, (f"PROTOCOL PULSE // {speaker}", "SIGNAL", "ACTIVE"))

    ep_num = _dt.datetime.now().strftime("%j")
    recon_id = _dt.datetime.now().strftime("BD-%Y-%j-%H%M")

    # Segment status for tracker
    segment_order = ["cold_open", "setup", "react", "wrap"]
    seg_idx = segment_order.index(segment_type) if segment_type in segment_order else -1

    # Build inputs: 0=TTS audio only (APEX V2: music mixed in concatenate_parts)
    inputs = [audio_path]

    # BLACK DIAMOND procedural background
    _, bg_fg = _build_black_diamond_bg(total_dur, label_out="bd_bg")
    fg = bg_fg

    # ── HEADER BAR ──
    fg += (f"[bd_bg]drawbox=x=0:y=0:w=1920:h=72:color=0x050505@0.97:t=fill,"
           f"drawbox=x=0:y=70:w=1920:h=2:color={COLOR_RED}@0.8:t=fill,"
           f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
           f"fontcolor={COLOR_WHITE}:fontsize=28:x=24:y=22,"
           f"drawtext=fontfile={FONT_BOLD}:text='LIVE':"
           f"fontcolor={COLOR_RED}:fontsize=22:x=280:y=26,"
           f"drawtext=fontfile={FONT_BOLD}:text='|':"
           f"fontcolor={COLOR_MUTED}:fontsize=28:x=340:y=22,"
           f"drawtext=fontfile={FONT_MONO}:text='EPISODE {ep_num}':"
           f"fontcolor={COLOR_MUTED}:fontsize=16:x=370:y=28,"
           f"drawtext=fontfile={FONT_MONO}:text='LAYER 04 ACTIVE':"
           f"fontcolor={COLOR_RED}:fontsize=14:x=560:y=30,"
           f"drawtext=fontfile={FONT_MONO}:text='RECON-ID - {recon_id}':"
           f"fontcolor=0x555555:fontsize=13:x=w-text_w-24:y=30"
           f"[hdr];\n")

    # ── LEFT PANEL ──
    fg += (f"[hdr]drawbox=x=0:y=72:w=720:h=958:color=0x070707@0.92:t=fill,"
           f"drawbox=x=0:y=72:w=6:h=958:color={COLOR_RED}@0.92:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='  {eyebrow}':"
           f"fontcolor={COLOR_RED}:fontsize=13:x=24:y=102,"
           f"drawtext=fontfile={FONT_BOLD}:text='{h1}':"
           f"fontcolor={COLOR_WHITE}:fontsize=96:x=18:y=128,"
           f"drawtext=fontfile={FONT_BOLD}:text='{h2}':"
           f"fontcolor={COLOR_RED}:fontsize=96:x=18:y=238"
           f"[lpanel];\n")

    # Divider line
    fg += f"[lpanel]drawbox=x=20:y=358:w=680:h=1:color={COLOR_RED}@0.35:t=fill[ldiv];\n"

    # Body text (wrapped subtitle)
    safe_sub = _sanitize_text(text) if text else ""
    if safe_sub:
        wrapped_sub = _word_wrap(safe_sub, max_width=40, max_lines=3)
        fg += (f"[ldiv]drawtext=fontfile={FONT_MONO}:"
               f"text='{wrapped_sub}':"
               f"fontcolor=0xBBBBBB:fontsize=20:x=24:y=374:line_spacing=6"
               f"[lbody];\n")
    else:
        fg += f"[ldiv]copy[lbody];\n"

    # CTA box
    fg += (f"[lbody]drawbox=x=20:y=600:w=440:h=52:color={COLOR_RED_DIM}@0.95:t=fill,"
           f"drawbox=x=20:y=600:w=4:h=52:color={COLOR_RED}:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:"
           f"text='  DUAL-HOST ANALYSIS // INCOMING':"
           f"fontcolor={COLOR_RED}:fontsize=13:x=34:y=622"
           f"[lcta];\n")

    # Mini waveform in left panel bottom
    fg += (f"[0:a]showwaves=s=680x90:mode=cline:"
           f"colors={COLOR_RED}:scale=sqrt:draw=full:rate=30[miniwave];\n")
    fg += f"[lcta][miniwave]overlay=20:880[lpfinal];\n"

    # ── VERTICAL DIVIDER ──
    fg += f"[lpfinal]drawbox=x=720:y=72:w=1:h=958:color={COLOR_RED}@0.3:t=fill[vdiv];\n"

    # ── RIGHT TOP — WAVEFORM VISUALIZER ──
    fg += (f"[0:a]showwaves=s=1140x200:mode=cline:"
           f"colors={COLOR_RED}:scale=sqrt:draw=full:rate=30[wave_top];\n")
    fg += f"[wave_top]split[wA][wB];\n"
    fg += f"[wB]vflip,colorchannelmixer=aa=0.25[wave_bot_dim];\n"
    fg += f"[wA][wave_bot_dim]vstack[wave_stack];\n"
    fg += f"[vdiv][wave_stack]overlay=740:74[rwav];\n"

    # ── RIGHT MID — 3 DATA PANELS ──
    fg += (f"[rwav]drawbox=x=740:y=502:w=370:h=150:color={COLOR_PANEL}@0.95:t=fill,"
           f"drawbox=x=740:y=502:w=370:h=2:color={COLOR_RED}@0.5:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='BTC SIGNAL':"
           f"fontcolor={COLOR_MUTED}:fontsize=12:x=756:y=517,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_btc}':"
           f"fontcolor={COLOR_WHITE}:fontsize=44:x=756:y=533,"
           f"drawtext=fontfile={FONT_MONO}:text='  SOVEREIGN SIGNAL':"
           f"fontcolor={COLOR_GREEN}:fontsize=12:x=756:y=588"
           f"[dp1];\n")

    fg += (f"[dp1]drawbox=x=1120:y=502:w=300:h=150:color={COLOR_PANEL}@0.95:t=fill,"
           f"drawbox=x=1120:y=502:w=300:h=2:color={COLOR_RED}@0.5:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='RENDER ENGINE':"
           f"fontcolor={COLOR_MUTED}:fontsize=12:x=1136:y=517,"
           f"drawtext=fontfile={FONT_BOLD}:text='134':"
           f"fontcolor={COLOR_WHITE}:fontsize=52:x=1136:y=530,"
           f"drawtext=fontfile={FONT_MONO}:text='FPS':"
           f"fontcolor={COLOR_RED}:fontsize=18:x=1220:y=546,"
           f"drawtext=fontfile={FONT_MONO}:text='4090 CLUSTER // H264':"
           f"fontcolor=0x666666:fontsize=12:x=1136:y=588"
           f"[dp2];\n")

    fg += (f"[dp2]drawbox=x=1430:y=502:w=280:h=150:color={COLOR_PANEL}@0.95:t=fill,"
           f"drawbox=x=1430:y=502:w=280:h=2:color={COLOR_RED}@0.5:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='  AUDIO AMPLITUDE':"
           f"fontcolor={COLOR_MUTED}:fontsize=11:x=1446:y=514"
           f"[dp3];\n")
    fg += (f"[0:a]showwaves=s=250x60:mode=line:"
           f"colors={COLOR_RED}:scale=lin:rate=30[amp_wave];\n")
    fg += f"[dp3][amp_wave]overlay=1440:530[dp_done];\n"

    # ── RIGHT BOT — EPISODE SEGMENTS TRACKER ──
    fg += (f"[dp_done]drawbox=x=740:y=660:w=1160:h=360:color={COLOR_PANEL}@0.92:t=fill,"
           f"drawbox=x=740:y=660:w=1160:h=2:color={COLOR_RED}@0.4:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='EPISODE SEGMENTS':"
           f"fontcolor={COLOR_MUTED}:fontsize=12:x=756:y=675"
           f"[seg_hdr];\n")

    seg_labels = ["COLD OPEN", "ORACLE BRIEF", "CLIP REACTION", "DUAL-HOST SEGMENT"]
    last_seg = "seg_hdr"
    for si, sl in enumerate(seg_labels):
        row_y = 700 + si * 30
        if si < seg_idx:
            status_text, status_color = "DONE", COLOR_GREEN
        elif si == seg_idx:
            status_text, status_color = "ACTIVE", COLOR_RED
        else:
            status_text, status_color = "PENDING", "0x444444"
        out_label = f"seg_r{si}"
        fg += (f"[{last_seg}]drawtext=fontfile={FONT_MONO}:text='{sl}':"
               f"fontcolor={COLOR_MUTED}:fontsize=14:x=756:y={row_y},"
               f"drawtext=fontfile={FONT_MONO}:text='{status_text}':"
               f"fontcolor={status_color}:fontsize=14:x=1100:y={row_y}"
               f"[{out_label}];\n")
        last_seg = out_label

    # ── CORNER BRACKETS ──
    fg += _build_corner_brackets_fg(last_seg, "cornered")

    # ── TICKER BAR ──
    fg += _build_info_bar_fg(total_dur, btc_price, label_in="cornered", label_out="v_final")

    # Social segment overlay (tweet card on right side)
    if is_social:
        safe_text = (text.replace("'", "").replace('"', "")
                         .replace(":", " -").replace(";", ",")
                         .replace("[", "(").replace("]", ")")
                         .replace("\u2014", "-").replace("\u2019", "")
                         .replace("\\", "").replace("\n", " "))
        wrapped_lines = []
        current_line = ""
        for word in safe_text.split():
            if len(current_line) + len(word) + 1 > 50:
                wrapped_lines.append(current_line)
                current_line = word
                if len(wrapped_lines) >= 3:
                    break
            else:
                current_line = f"{current_line} {word}".strip() if current_line else word
        if current_line and len(wrapped_lines) < 3:
            wrapped_lines.append(current_line)
        wrapped_text = "\n".join(wrapped_lines)

        fg += (f"color=c={COLOR_PANEL}@0.92:s=1100x280:d={total_dur}:r=30[tcard];\n"
               f"[tcard]drawbox=x=0:y=0:w=1100:h=280:color={COLOR_RED}@0.4:t=2,"
               f"drawbox=x=0:y=0:w=1100:h=2:color={COLOR_RED}:t=fill,"
               f"drawbox=x=20:y=20:w=8:h=8:color={COLOR_RED}:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='@ProtocolPulse':"
               f"fontcolor={COLOR_RED}:fontsize=18:x=38:y=16,"
               f"drawtext=fontfile={FONT_MONO}:text='{wrapped_text}':"
               f"fontcolor={COLOR_TEXT}:fontsize=20:x=24:y=50:line_spacing=14,"
               f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
               f"fontcolor={COLOR_MUTED}:fontsize=11:x=w-160:y=h-22[tcardready];\n"
               f"[v_final][tcardready]overlay=760:200:format=auto,fade=t=in:st=0:d=0.3[v_social];\n")
        fg += f"[v_social]format=yuv420p[outv];\n"
    else:
        fg += f"[v_final]format=yuv420p[outv];\n"

    # Audio: TTS only — APEX V2: music mixed continuously in concatenate_parts()
    fg += (f"[0:a]silenceremove=start_periods=1:start_duration=0.05:start_threshold=-50dB:"
           f"stop_periods=-1:stop_duration=0.1:stop_threshold=-50dB,"
           f"loudnorm=I=-14:TP=-1.5:LRA=7,aresample=async=1[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label or f"host visual ({speaker})", 180,
    )

    if ok:
        return output_path

    logger.error(f"Waveform filtergraph FAILED for {label} — no silent fallback, raising")
    raise RuntimeError(f"Host visual filtergraph failed for {label}. Check ffmpeg stderr in logs.")


def _sanitize_text(text: str) -> str:
    """Sanitize text for FFmpeg drawtext filter."""
    return (text.replace("'", "\u2019").replace('"', "")
                .replace(":", " -").replace(";", ",")
                .replace("[", "(").replace("]", ")")
                .replace("\u2014", "-").replace("\\", "")
                .replace("\n", " ").replace("%", "pct"))


def _word_wrap(text: str, max_width: int = 55, max_lines: int = 3) -> str:
    """Word-wrap text for FFmpeg drawtext, return newline-joined string.

    FIX 4: Use actual newline character (0x0a) in the text. When written to
    filter_complex_script file, FFmpeg drawtext renders it as a line break.
    Escaped sequences like \\n or \\\\n do NOT work in filter_complex_script mode.
    """
    lines = []
    current = ""
    for word in text.split():
        if len(current) + len(word) + 1 > max_width:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
        else:
            current = f"{current} {word}".strip() if current else word
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(text) > sum(len(l) for l in lines):
        lines[-1] = lines[-1][:max_width - 3] + "..."
    return "\n".join(lines)


def make_social_card_visual(audio_path: str, posts: list, output_path: str,
                            btc_price: str = "N/A") -> str:
    """Render tweet card visual with real tweet data behind narration audio.

    Shows up to 2 tweet cards stacked vertically, each with:
    - Real @handle in red
    - Real tweet text in white, word-wrapped
    - Engagement stats (likes, retweets)
    - Red left border accent

    Args:
        audio_path: TTS narration audio for this social segment
        posts: List of dicts with handle, text, likes, retweets
        output_path: Output video path
        btc_price: BTC price for ticker

    Returns:
        Path to output video, or "" on failure
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = audio_dur + 0.3

    safe_btc = btc_price.replace("'", "").replace('"', "")
    has_wm = os.path.exists(WATERMARK)

    # Build inputs — APEX V2: no per-segment music
    inputs = [audio_path]
    inp_idx = 1
    if has_wm:
        inputs.append(WATERMARK)
        wm_idx = inp_idx
        inp_idx += 1
    else:
        wm_idx = -1

    # VDS procedural background (7-layer, no video files)
    _, bg_fg = _build_black_diamond_bg(total_dur, label_out="bgvig")
    fg = bg_fg

    # VDS-1: Top red accent bar
    fg += f"[bgvig]drawbox=x=0:y=0:w=1920:h=4:color={COLOR_RED}:t=fill[bgbar];\n"

    # VDS: Pulse dot top-left
    fg += f"[bgbar]drawbox=x=20:y=16:w=10:h=10:color={COLOR_RED}:t=fill[bgdot];\n"

    # VDS: Section header — gold eyebrow kicker
    fg += (f"[bgdot]drawtext=fontfile={FONT_MONO}:"
           f"text='SOCIAL PULSE - WHAT BITCOIN IS SAYING':"
           f"fontcolor={COLOR_RED}:fontsize=14:x=(w-text_w)/2:y=20[bgtitle];\n")
    last_v = "bgtitle"

    # Render up to 2 tweet cards — stacked vertically with spacing
    card_y_start = 90
    card_height = 260
    card_spacing = 30
    card_width = 1360
    card_x = 280

    # Issue 6: Check for screenshot paths and add as inputs
    screenshot_indices = {}
    for ci, post in enumerate(posts[:2]):
        ss_path = post.get("screenshot_path", "")
        if ss_path and os.path.exists(ss_path):
            inputs.append(ss_path)
            screenshot_indices[ci] = inp_idx
            inp_idx += 1
            logger.info(f"  Using tweet screenshot for card {ci}: {os.path.basename(ss_path)}")

    for ci, post in enumerate(posts[:2]):
        handle = _sanitize_text(post.get("handle", "unknown"))
        if not handle.startswith("@"):
            handle = f"@{handle}"
        tweet_text = _word_wrap(_sanitize_text(post.get("text", "")), max_width=55, max_lines=3)
        likes = post.get("likes", 0)
        retweets = post.get("retweets", 0)
        likes_str = f"{likes:,}" if isinstance(likes, int) else str(likes)
        rt_str = f"{retweets:,}" if isinstance(retweets, int) else str(retweets)

        cy = card_y_start + ci * (card_height + card_spacing)
        tag = f"c{ci}"

        # Card glow (subtle red behind card — outer glow)
        fg += f"color=c={COLOR_RED}@0.08:s={card_width + 24}x{card_height + 24}:d={total_dur}:r=30[{tag}glow];\n"
        fg += f"[{last_v}][{tag}glow]overlay={card_x - 12}:{cy - 12}[{tag}g];\n"

        # Card body
        fg += f"color=c={COLOR_PANEL}@0.92:s={card_width}x{card_height}:d={total_dur}:r=30[{tag}body];\n"
        # Outer red border (2px)
        fg += f"[{tag}body]drawbox=x=0:y=0:w={card_width}:h={card_height}:color={COLOR_RED}@0.4:t=2[{tag}brd];\n"
        # Inner glow border (dark red, 2px inside the outer border)
        fg += f"[{tag}brd]drawbox=x=4:y=4:w={card_width - 8}:h={card_height - 8}:color={COLOR_PANEL2}@0.3:t=2[{tag}inner];\n"
        # Left accent bar
        fg += f"[{tag}inner]drawbox=x=0:y=0:w=6:h={card_height}:color={COLOR_RED}:t=fill[{tag}lbar];\n"
        # Top edge accent
        fg += f"[{tag}lbar]drawbox=x=0:y=0:w={card_width}:h=2:color={COLOR_RED}:t=fill[{tag}top];\n"

        # Issue 6: If screenshot available, overlay it inside card; else render text
        if ci in screenshot_indices:
            ss_idx = screenshot_indices[ci]
            # Scale screenshot to fit inside card (with padding)
            fg += (f"[{ss_idx}:v]scale={card_width - 16}:{card_height - 16}:"
                   f"force_original_aspect_ratio=decrease,"
                   f"pad={card_width - 16}:{card_height - 16}:(ow-iw)/2:(oh-ih)/2:{COLOR_PANEL}[{tag}ss];\n")
            fg += f"[{tag}top][{tag}ss]overlay=8:8[{tag}src];\n"
        else:
            # Pulse dot
            fg += f"[{tag}top]drawbox=x=20:y=18:w=8:h=8:color={COLOR_RED}:t=fill[{tag}dot];\n"

            # Handle — monospace font
            fg += (f"[{tag}dot]drawtext=fontfile={FONT_MONO}:"
                   f"text='{handle}':"
                   f"fontcolor={COLOR_RED}:fontsize=14:x=38:y=16[{tag}hdl];\n")

            # Tweet text — bold for readability
            fg += (f"[{tag}hdl]drawtext=fontfile={FONT_BOLD}:"
                   f"text='{tweet_text}':"
                   f"fontcolor={COLOR_TEXT}:fontsize=22:x=24:y=52:line_spacing=16:"
                   f"box=0[{tag}txt];\n")

            # Engagement stats bottom
            fg += (f"[{tag}txt]drawtext=fontfile={FONT_MONO}:"
                   f"text='{likes_str} likes  |  {rt_str} RTs':"
                   f"fontcolor={COLOR_RED}:fontsize=12:x=24:y=h-28[{tag}stats];\n")

            # Source label bottom-right
            fg += (f"[{tag}stats]drawtext=fontfile={FONT_MONO}:"
                   f"text='via X':fontcolor={COLOR_MUTED}:fontsize=12:"
                   f"x=w-80:y=h-30[{tag}src];\n")

        # Overlay card on base with fade-in
        fade_start = ci * 0.4
        fg += f"[{tag}g][{tag}src]overlay={card_x}:{cy}:format=auto,fade=t=in:st={fade_start}:d=0.3[{tag}out];\n"
        last_v = f"{tag}out"

    # VDS: Subtle bottom label
    bottom_header_y = card_y_start + len(posts[:2]) * (card_height + card_spacing) + 10
    fg += (f"[{last_v}]drawtext=fontfile={FONT_MONO}:"
           f"text='SOCIAL PULSE - WHAT BITCOIN IS SAYING':"
           f"fontcolor={COLOR_RED}@0.3:fontsize=12:x=(w-text_w)/2:y={bottom_header_y}[vbhdr];\n")
    last_v = "vbhdr"

    # VDS animated scrolling info bar
    fg += _build_info_bar_fg(total_dur, btc_price, label_in=last_v, label_out="vtick")
    last_v = "vtick"

    # Watermark
    if has_wm:
        fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
        fg += f"[{last_v}][wm]overlay=W-170:16[vwm];\n"
        last_v = "vwm"

    fg += f"[{last_v}]format=yuv420p[outv];\n"

    # APEX V2: TTS only — continuous BGM mixed in concatenate_parts()
    fg += f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=7,aresample=async=1[outa]"

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "social tweet card", 180,
    )

    if ok:
        logger.info(f"  Tweet card visual: {len(posts[:2])} cards, {total_dur:.1f}s")
        return output_path
    return ""


# ── Glitch transition ───────────────────────────────────────────────────────

REMOTION_DIR = os.path.join(os.path.dirname(__file__), "remotion")


def _make_remotion_glitch(output_path: str) -> str:
    """Render GlitchTransition via Remotion. Returns path or '' on failure.

    Remotion outputs video-only. We mix in the whoosh audio from the branded
    glitch_transition_waud.mp4 asset for the transition sound effect.
    Falls back to silent track if branded asset not available.
    """
    entry = os.path.join(REMOTION_DIR, "src", "index.tsx")
    if not os.path.exists(entry):
        return ""
    try:
        r = subprocess.run(
            ["npx", "remotion", "render", entry, "GlitchTransition",
             output_path, "--log=error"],
            cwd=REMOTION_DIR, timeout=60, capture_output=True, text=True,
        )
        if r.returncode == 0 and os.path.exists(output_path):
            with_audio = output_path + ".waud.mp4"
            dur = ffprobe_duration(output_path)

            # Mix in whoosh SFX
            if os.path.exists(GLITCH_WHOOSH):
                ok = run_ffmpeg([
                    "-i", output_path,
                    "-i", GLITCH_WHOOSH,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-af", "volume=2.5,afade=t=in:d=0.05,afade=t=out:st=" + f"{max(0, dur-0.15):.2f}" + ":d=0.15",
                    "-t", str(dur),
                    "-shortest",
                    with_audio,
                ], "remotion glitch + whoosh sfx", 30)
            elif os.path.exists(GLITCH_TRANSITION):
                ok = run_ffmpeg([
                    "-i", output_path,
                    "-i", GLITCH_TRANSITION,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-af", "volume=3.0,afade=t=in:d=0.05,afade=t=out:st=" + f"{max(0, dur-0.15):.2f}" + ":d=0.15",
                    "-t", str(dur),
                    "-shortest",
                    with_audio,
                ], "remotion glitch + whoosh audio", 30)
            else:
                # Fallback: silent track
                ok = run_ffmpeg([
                    "-i", output_path,
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", str(dur),
                    "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-shortest", with_audio,
                ], "remotion glitch add silence", 30)

            if ok and os.path.exists(with_audio):
                os.replace(with_audio, output_path)
            elif os.path.exists(with_audio):
                os.remove(with_audio)
            logger.info(f"  Remotion glitch transition: {dur:.2f}s (with whoosh)")
            return output_path
        else:
            logger.warning(f"Remotion glitch render failed: {r.stderr[-300:]}")
    except Exception as e:
        logger.warning(f"Remotion glitch error: {e}")
    return ""


def _remotion_enabled() -> bool:
    """Check if remotion_visuals feature flag is enabled."""
    try:
        from utils.feature_flags import is_enabled
        return is_enabled("remotion_visuals")
    except Exception:
        return False


def _render_remotion(comp_id: str, output_path: str, props: dict = None,
                     timeout: int = 120) -> str:
    """Render a Remotion composition. Returns path or '' on failure.

    Args:
        comp_id: Composition ID (e.g. 'WaveformVisualizer')
        output_path: Where to write the rendered video
        props: Optional input props as dict (passed via --props)
        timeout: Render timeout in seconds
    """
    entry = os.path.join(REMOTION_DIR, "src", "index.tsx")
    if not os.path.exists(entry):
        return ""
    try:
        cmd = ["npx", "remotion", "render", entry, comp_id, output_path, "--log=error"]
        if props:
            cmd += ["--props", json.dumps(props)]
        r = subprocess.run(cmd, cwd=REMOTION_DIR, timeout=timeout,
                           capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(output_path):
            return output_path
        logger.warning(f"Remotion {comp_id} render failed: {r.stderr[-300:]}")
    except Exception as e:
        logger.warning(f"Remotion {comp_id} error: {e}")
    return ""


def _remotion_with_audio(video_path: str, audio_path: str, output_path: str,
                         bg_music: bool = True) -> str:
    """Mux Remotion video (no audio) with TTS audio + optional background music.

    Returns output_path on success, '' on failure.
    """
    dur = ffprobe_duration(audio_path)
    if dur <= 0:
        dur = 5
    total_dur = dur + 0.3

    # APEX V2: No per-segment music — continuous BGM mixed in concatenate_parts()
    ok = run_ffmpeg([
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]setpts=PTS-STARTPTS[v];"
        f"[1:a]aresample=async=1[outa]",
        "-map", "[v]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        "-t", str(total_dur), output_path,
    ], f"remotion mux", 180)

    return output_path if ok else ""


def make_remotion_waveform(audio_path: str, output_path: str,
                           title: str = "Pulse Check Daily",
                           btc_price: str = "N/A",
                           date: str = "") -> str:
    """Render WaveformVisualizer via Remotion + mux with TTS audio.

    Falls back to '' on failure (caller should use FFmpeg make_host_visual).
    """
    if not _remotion_enabled():
        return ""
    if not date:
        from datetime import date as _d
        date = _d.today().isoformat()

    dur = ffprobe_duration(audio_path)
    total_dur = dur + 0.3
    # Issue 10: Add 30-frame (1s) buffer so Remotion video never ends before audio
    frames = max(math.ceil(total_dur * 30) + 30, 90)

    raw_video = output_path + ".remotion_raw.mp4"
    result = _render_remotion("WaveformVisualizer", raw_video, props={
        "title": title,
        "btcPrice": btc_price,
        "date": date,
        "durationInFrames": frames,
    })
    if not result:
        return ""

    muxed = _remotion_with_audio(raw_video, audio_path, output_path, bg_music=True)
    if os.path.exists(raw_video):
        try:
            os.remove(raw_video)
        except OSError:
            pass
    if muxed:
        logger.info(f"  Remotion WaveformVisualizer: {ffprobe_duration(muxed):.1f}s")
    return muxed


def _mix_swoosh_into_segment(video_path: str) -> str:
    """Mix card_swoosh.wav into the first 0.4s of a video segment.

    Modifies the file in-place (via temp rename). Returns the path.
    """
    if not os.path.exists(CARD_SWOOSH) or not os.path.exists(video_path):
        return video_path
    tmp = video_path + ".swoosh.mp4"
    ok = run_ffmpeg([
        "-i", video_path,
        "-i", CARD_SWOOSH,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.6[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        tmp,
    ], "mix card swoosh", 30)
    if ok and os.path.exists(tmp):
        os.replace(tmp, video_path)
    elif os.path.exists(tmp):
        os.remove(tmp)
    return video_path


def make_remotion_social_card(audio_path: str, posts: list, output_path: str,
                              btc_price: str = "N/A") -> str:
    """Render SocialCard via Remotion + mux with TTS audio.

    Falls back to '' on failure (caller should use FFmpeg make_social_card_visual).
    """
    if not _remotion_enabled():
        return ""

    post = posts[0] if posts else {}
    dur = ffprobe_duration(audio_path)
    total_dur = dur + 0.3
    # Issue 10: durationInFrames must NEVER be shorter than audio — add 1 second (30 frames) buffer
    frames = max(math.ceil(total_dur * 30) + 30, 90)

    raw_video = output_path + ".remotion_raw.mp4"
    result = _render_remotion("SocialCard", raw_video, props={
        "handle": post.get("handle", "ProtocolPulse"),
        "text": post.get("text", "")[:200],
        "likes": post.get("likes", 0),
        "retweets": post.get("retweets", 0),
        "durationInFrames": frames,
    })
    if not result:
        return ""

    muxed = _remotion_with_audio(raw_video, audio_path, output_path, bg_music=True)
    if os.path.exists(raw_video):
        try:
            os.remove(raw_video)
        except OSError:
            pass
    if muxed:
        # Mix in card swoosh SFX on entrance
        muxed = _mix_swoosh_into_segment(muxed)
        logger.info(f"  Remotion SocialCard: {ffprobe_duration(muxed):.1f}s")
    return muxed


def make_remotion_title_card(audio_path: str, output_path: str,
                             title: str = "", date: str = "",
                             btc_price: str = "N/A") -> str:
    """Render TitleCard via Remotion + mux with TTS + jingle audio.

    Falls back to '' on failure (caller should use FFmpeg make_intro_coldopen).
    """
    if not _remotion_enabled():
        return ""
    if not date:
        from datetime import date as _d
        date = _d.today().isoformat()

    dur = ffprobe_duration(audio_path)
    total_dur = max(dur + 1.0, 4.0)
    frames = max(math.ceil(total_dur * 30), 120)

    raw_video = output_path + ".remotion_raw.mp4"
    result = _render_remotion("TitleCard", raw_video, props={
        "title": title or "Pulse Check Daily",
        "date": date,
        "durationInFrames": frames,
    })
    if not result:
        return ""

    # Mux with TTS + jingle (same audio chain as make_intro_coldopen)
    import glob as _glob
    jingle = os.path.join(ASSETS, "music", "pp_intro.mp3")
    if not os.path.exists(jingle):
        tracks = _glob.glob(os.path.join(ASSETS, "music", "intro_*.mp3"))
        jingle = tracks[0] if tracks else ""

    total_dur = max(dur + 1.0, 4.0)
    has_jingle = bool(jingle and os.path.exists(jingle))

    if has_jingle:
        ok = run_ffmpeg([
            "-i", raw_video,
            "-i", audio_path,
            "-i", jingle,
            "-filter_complex",
            f"[0:v]setpts=PTS-STARTPTS[v];"
            f"[1:a]volume=1.0[tts_a];"
            f"[2:a]volume=0.35[jingle_a];"
            f"[tts_a][jingle_a]amix=inputs=2:duration=first:weights=1 0.35[outa]",
            "-map", "[v]", "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(total_dur), output_path,
        ], "remotion title card + jingle", 120)
    else:
        muxed = _remotion_with_audio(raw_video, audio_path, output_path, bg_music=False)
        ok = bool(muxed)

    if os.path.exists(raw_video):
        try:
            os.remove(raw_video)
        except OSError:
            pass
    if ok and os.path.exists(output_path):
        logger.info(f"  Remotion TitleCard: {ffprobe_duration(output_path):.1f}s")
        return output_path
    return ""


def make_remotion_lower_third(clip_path: str, source: str, output_path: str,
                              btc_price: str = "N/A",
                              speaker_name: str = "") -> str:
    """Render LowerThird overlay via Remotion and composite onto clip.

    Falls back to '' on failure (caller should use FFmpeg make_clip_visual).
    """
    if not _remotion_enabled():
        return ""

    clip_dur = ffprobe_duration(clip_path)
    if clip_dur <= 0:
        return ""

    # Render LowerThird overlay (6 seconds max, shown near start of clip)
    overlay_dur = min(6.0, clip_dur * 0.6)
    frames = math.ceil(overlay_dur * 30)

    raw_overlay = output_path + ".remotion_lt.mp4"
    result = _render_remotion("LowerThird", raw_overlay, props={
        "channelName": source.replace("@", ""),
        "speakerName": speaker_name,
        "durationInFrames": frames,
    })
    if not result:
        return ""

    # Composite LowerThird onto clip (overlay the rendered frames at bottom)
    # LowerThird has transparent bg in Remotion but renders to opaque MP4.
    # We overlay just the bottom 120px band from the LowerThird render.
    ok = run_ffmpeg([
        "-i", clip_path,
        "-i", raw_overlay,
        "-filter_complex",
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30[clip];"
        f"[1:v]crop=1920:120:0:960[ltband];"
        f"[clip][ltband]overlay=0:960:enable='lte(t,{overlay_dur})',format=yuv420p[outv];"
        f"[0:a]asetpts=PTS-STARTPTS,volume=1.0[outa]",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        output_path,
    ], "remotion lower third composite", 180)

    if os.path.exists(raw_overlay):
        try:
            os.remove(raw_overlay)
        except OSError:
            pass
    if ok and os.path.exists(output_path):
        logger.info(f"  Remotion LowerThird on clip: {ffprobe_duration(output_path):.1f}s")
        return output_path
    return ""


def make_transition_visual(output_path: str, duration: float = 0.5) -> str:
    """Glitch transition — tries Remotion first, then asset file, then dark flash.

    Priority:
    1. Remotion GlitchTransition (best quality)
    2. Branded glitch_transition_waud.mp4 asset
    3. Simple dark flash fallback
    """
    # Try Remotion first
    remotion_result = _make_remotion_glitch(output_path)
    if remotion_result:
        return remotion_result

    # Fallback to branded asset
    if os.path.exists(GLITCH_TRANSITION):
        ok = run_ffmpeg([
            "-i", GLITCH_TRANSITION,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-vf", "scale=1920:1080,setsar=1,format=yuv420p",
            "-af", "volume=3.0,loudnorm=I=-6:TP=-0.5:LRA=5",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], "glitch transition", 30)
        if ok and os.path.exists(output_path):
            dur = ffprobe_duration(output_path)
            logger.info(f"  Glitch transition (asset): {dur:.2f}s")
            return output_path

    # Last resort: short dark flash
    logger.warning("All glitch sources failed — using dark flash")
    ok = run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c={COLOR_BG}:s=1920x1080:d={duration}:r=30",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
        output_path,
    ], "transition fallback", 30)
    return output_path if ok else ""


def apply_xfade(clip1_path: str, clip2_path: str, output_path: str,
                 transition: str = "fade", duration: float = 1.0) -> str:
    """Issue 8: Apply xfade crossfade between two clips instead of hard-cut transitions.

    Overlaps the last `duration` seconds of clip1 with the first `duration` seconds of clip2.
    Returns output_path on success, '' on failure.
    """
    dur1 = ffprobe_duration(clip1_path)
    if dur1 <= duration:
        return ""
    offset = dur1 - duration
    ok = run_ffmpeg([
        "-i", clip1_path, "-i", clip2_path,
        "-filter_complex",
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30[v0];"
        f"[1:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30[v1];"
        f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a0];"
        f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a1];"
        f"[v0][v1]xfade=transition={transition}:duration={duration}:offset={offset},format=yuv420p[outv];"
        f"[a0][a1]acrossfade=d={duration}:c1=tri:c2=tri[outa]",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        output_path,
    ], "xfade transition", 300)
    return output_path if ok and os.path.exists(output_path) else ""


# ── YouTube clip visual ─────────────────────────────────────────────────────

def make_clip_visual(clip_path: str, source: str, output_path: str,
                     btc_price: str = "N/A") -> str:
    """APEX B-roll / partner clip — BEV2 restraint (let the clip carry the moment).

    Red border frame, corner brackets (BD), info rail (BEV2),
    glass lower-third with red top accent. PROTOCOL PULSE watermark top-right.
    CRITICAL: Original audio is preserved.
    """
    clip_dur = ffprobe_duration(clip_path)
    if clip_dur <= 0:
        logger.warning(f"Clip has zero duration: {clip_path}")
        return ""

    safe_source = source.replace("'", "").replace('"', "").replace(":", "")
    safe_btc = btc_price.replace("'", "").replace('"', "")

    fade_out_start = max(0, clip_dur - 0.5)
    fg = (
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,"
        f"fade=t=in:d=0.3,fade=t=out:st={fade_out_start}:d=0.5[clip];\n"
        # Red border frame (2px all edges)
        f"[clip]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
        f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
        f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
        f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
        # BD corner brackets
        f"drawbox=x=0:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
        # Top-right watermark (red, 18px, 60% opacity)
        f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
        f"fontcolor={COLOR_RED}@0.6:fontsize=18:x=W-text_w-20:y=16"
        f"[clip_branded];\n"
        # Glass lower-third with red top accent line
        f"color=c={COLOR_PANEL}@0.88:s=800x90:d={clip_dur}:r=30[ltbg];\n"
        f"[ltbg]drawbox=x=0:y=0:w=800:h=4:color={COLOR_RED}:t=fill[ltbar];\n"
        f"[ltbar]drawtext=fontfile={FONT_BOLD}:text='{safe_source}':"
        f"fontcolor={COLOR_WHITE}:fontsize=26:x=20:y=24[ltname];\n"
        f"[ltname]drawtext=fontfile={FONT_MONO}:text='SOURCE - PARTNER CHANNEL':"
        f"fontcolor={COLOR_MUTED}:fontsize=12:x=20:y=60[ltfull];\n"
        f"[clip_branded][ltfull]overlay=0:870:enable='between(t,0.5,6.5)'[clip_lt];\n"
    )
    # Info rail at bottom (always present)
    fg += _build_signature_info_rail(clip_dur, btc_price, "clip_lt", "clip_railed")
    fg += (
        f"[clip_railed]format=yuv420p[outv];\n"
        f"[0:a]asetpts=PTS-STARTPTS,"
        f"highpass=f=50,lowpass=f=15000,loudnorm=I=-14:TP=-1.5:LRA=7,"
        f"afade=t=in:d=0.3,afade=t=out:st={fade_out_start}:d=0.5[outa]"
    )

    ok = run_ffmpeg_filtergraph(
        [clip_path], fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k"],
        output_path, f"clip visual ({safe_source})",
    )
    return output_path if ok else ""


# ── Concatenation ────────────────────────────────────────────────────────────

def normalize_part(part_path: str, output_path: str) -> str:
    """Normalize a video part to EXACTLY consistent format for concatenation.

    Every part must have identical stream parameters to prevent concat drift:
    - 1920x1080, 30fps CFR, yuv420p, h264
    - aac 48000Hz stereo
    - Consistent video_track_timescale
    - aresample async to absorb minor timing differences
    """
    part_path = ensure_audio(part_path)
    ok = run_ffmpeg(
        ["-i", part_path,
         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-r", "30", "-vsync", "cfr",
         "-vf", "scale=1920:1080,setsar=1,format=yuv420p",
         "-video_track_timescale", "90000",
         "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
         "-af", "loudnorm=I=-14:TP=-3.0:LRA=7,aresample=async=1,alimiter=level_in=1:level_out=0.794:limit=0.708:attack=3:release=30",
         output_path],
        "normalize", 180,
    )
    return output_path if (ok and os.path.exists(output_path)) else part_path


def concatenate_parts(parts: list, output_path: str) -> str:
    """FIX 1+8+12: Concat video parts with fade transitions (no black frames).

    Uses concat demuxer with fade-in/fade-out on each part for smooth transitions.
    No standalone glitch transition clips. Final loudnorm with LRA=7 (FIX 12).
    """
    valid = [p for p in parts if p and os.path.exists(p)]
    if not valid:
        logger.error("No valid parts to concatenate")
        return ""
    if len(valid) == 1:
        shutil.copy2(valid[0], output_path)
        return output_path

    # Normalize all parts with brief fade-in/fade-out for smooth cuts (FIX 1+8)
    normalized = []
    for i, p in enumerate(valid):
        tmp = output_path + f".norm{i}.mp4"
        p = ensure_audio(p)
        dur = ffprobe_duration(p)
        fade_out_start = max(0, dur - 0.15)
        ok = run_ffmpeg(
            ["-i", p,
             "-c:v", "libx264", "-crf", "17", "-preset", "medium",
             "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
             "-r", "30", "-vsync", "cfr",
             "-vf", f"scale=1920:1080,setsar=1,format=yuv420p,fade=t=in:d=0.15,fade=t=out:st={fade_out_start}:d=0.15",
             "-video_track_timescale", "90000",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
             "-af", f"loudnorm=I=-14:TP=-3.0:LRA=7,aresample=async=1,afade=t=in:d=0.1,afade=t=out:st={fade_out_start}:d=0.15",
             tmp],
            "normalize+fade", 180,
        )
        normalized.append(tmp if (ok and os.path.exists(tmp)) else p)

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for p in normalized:
            f.write(f"file '{os.path.abspath(p)}'\n")

    # Concat demuxer with stream copy (parts are already normalized)
    concat_raw = output_path + ".concat_raw.mp4"
    ok = run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", concat_file,
         "-c", "copy", concat_raw],
        "concat demux", 300,
    )

    if not ok or not os.path.exists(concat_raw):
        logger.error("Concat demuxer failed")
        return ""

    # APEX V2 FIX 1: Continuous background music across ENTIRE episode
    # Music plays ONCE continuously — no per-segment start/stop/fade
    from music import ffprobe_duration as _music_ffprobe_dur
    has_bgm = os.path.exists(BG_MUSIC)
    if has_bgm:
        dur = _music_ffprobe_dur(concat_raw)
        if dur > 0:
            music_mixed = output_path + ".music_mixed.mp4"
            ok_music = run_ffmpeg([
                "-fflags", "+genpts",
                "-i", concat_raw,
                "-stream_loop", "-1", "-i", BG_MUSIC,
                "-filter_complex", (
                    f"[0:a]asetpts=PTS-STARTPTS,asplit[tts_main][tts_sc];"
                    f"[1:a]volume=0.09,afade=t=in:d=2.0,"
                    f"afade=t=out:st={max(0,dur-3.0)}:d=3.0[bgm_raw];"
                    f"[bgm_raw][tts_sc]sidechaincompress="
                    f"threshold=0.015:ratio=8:attack=30:release=600[bgm_ducked];"
                    f"[tts_main][bgm_ducked]amix=inputs=2:duration=first"
                    f":weights=1 1[mixed_audio];"
                    f"[mixed_audio]loudnorm=I=-14:TP=-1.5:LRA=7:linear=true,"
                    f"aresample=async=1[outa]"
                ),
                "-map", "0:v", "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                "-t", str(dur),
                music_mixed
            ], "continuous bgm mix", 600)
            if ok_music and os.path.exists(music_mixed):
                logger.info(f"  APEX V2: Continuous BGM mixed ({dur:.1f}s episode)")
                concat_raw = music_mixed
            else:
                logger.warning("  APEX V2: BGM mix failed — proceeding without music")
    else:
        logger.warning("  APEX V2: No BG_MUSIC file found — no music bed")

    # FIX 6: Mix whoosh SFX at transition points between segments
    has_whoosh = os.path.exists(GLITCH_WHOOSH)
    if has_whoosh and len(valid) > 1:
        # Calculate transition timestamps (cumulative durations of each part)
        transition_times = []
        cumulative = 0.0
        for pidx, p in enumerate(valid[:-1]):
            pdur = ffprobe_duration(p)
            cumulative += pdur
            transition_times.append(cumulative)

        if transition_times:
            whoosh_mixed = output_path + ".whoosh_mixed.mp4"
            # Build filter: delay each whoosh to its transition time, then amix all
            whoosh_inputs = []
            whoosh_fg_parts = []
            for ti, ttime in enumerate(transition_times):
                whoosh_inputs.extend(["-i", GLITCH_WHOOSH])
                delay_ms = int(ttime * 1000)
                whoosh_fg_parts.append(
                    f"[{ti+1}:a]volume=0.6,adelay={delay_ms}|{delay_ms}[whoosh_{ti}]"
                )
            # Amix all whooshes together
            whoosh_labels = "".join(f"[whoosh_{ti}]" for ti in range(len(transition_times)))
            whoosh_fg_parts.append(
                f"{whoosh_labels}amix=inputs={len(transition_times)}:duration=longest[all_whoosh]"
            )
            # Mix whoosh into episode audio
            whoosh_fg_parts.append(
                f"[0:a][all_whoosh]amix=inputs=2:duration=first:weights=1 0.5[outa]"
            )
            whoosh_fg = ";\n".join(whoosh_fg_parts)

            ok_whoosh = run_ffmpeg(
                ["-fflags", "+genpts", "-i", concat_raw] + whoosh_inputs +
                ["-filter_complex", whoosh_fg,
                 "-map", "0:v", "-map", "[outa]",
                 "-c:v", "copy",
                 "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                 whoosh_mixed],
                "whoosh SFX mix", 300,
            )
            if ok_whoosh and os.path.exists(whoosh_mixed):
                logger.info(f"  FIX 6: Whoosh SFX at {len(transition_times)} transitions")
                concat_raw = whoosh_mixed
            else:
                logger.warning("  FIX 6: Whoosh mix failed — proceeding without SFX")

    # Final encode: PTS reset + loudnorm
    ok = run_ffmpeg(
        ["-fflags", "+genpts",
         "-i", concat_raw,
         "-c:v", "libx264", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-r", "30", "-vsync", "cfr",
         "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
         "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
         "-movflags", "+faststart",
         output_path],
        "concat final encode", 600,
    )

    # Cleanup
    if os.path.exists(concat_raw):
        try: os.remove(concat_raw)
        except OSError: pass
    for p in normalized:
        if ".norm" in p and os.path.exists(p):
            try: os.remove(p)
            except OSError: pass
    for p in valid:
        if p.endswith("_waud.mp4") and os.path.exists(p):
            try: os.remove(p)
            except OSError: pass
    if os.path.exists(concat_file):
        os.remove(concat_file)

    return output_path if ok else ""


# ── Main assembly ────────────────────────────────────────────────────────────

def assemble_episode(script: dict, audio_data: dict, extracted_clips: dict,
                     output_path: str, btc_price: str = "N/A",
                     music_bed: str = "", intro_music: str = "",
                     broll_clips: list = None) -> str:
    """Assemble a V6 ESPN-quality episode.

    Args:
        script: Script with dialogue array
        audio_data: From generate_dialogue_audio() — {lines, full, total_duration}
        extracted_clips: From clip_extractor.extract_all() — {rank: {path, channel, ...}}
        output_path: Final video path
        btc_price: BTC price string for ticker
        broll_clips: FIX 6 — list of Pexels B-roll clip paths

    Returns:
        Path to final video, or "" on failure
    """
    logger.info("=" * 60)
    logger.info("ASSEMBLING V10 EPISODE — WAVEFORM VISUALIZER")
    logger.info("=" * 60)

    try:
        return _assemble_episode_inner(script, audio_data, extracted_clips,
                                       output_path, btc_price, music_bed, intro_music,
                                       broll_clips=broll_clips)
    except Exception:
        import traceback
        logger.error("ASSEMBLY CRASHED — full traceback:")
        traceback.print_exc()
        return ""


def _assemble_episode_inner(script, audio_data, extracted_clips,
                            output_path, btc_price="N/A", music_bed="", intro_music="",
                            broll_clips=None):
    # FIX 5: Fetch BTC price if not provided or showing N/A
    if not btc_price or btc_price in ("N/A", "$N/A", ""):
        btc_price = _fetch_btc_price()
        logger.info(f"  BTC price fetched: {btc_price}")

    # Issue 12: Override default BG_MUSIC with mood-matched music bed if provided
    # Ensure music is mixed at -20dB under ALL narration segments
    global BG_MUSIC
    if music_bed and os.path.exists(music_bed):
        BG_MUSIC = music_bed
        logger.info(f"  Music bed ACTIVE: {os.path.basename(music_bed)}")
    elif os.path.exists(BG_MUSIC):
        logger.info(f"  Music bed ACTIVE (default): {os.path.basename(BG_MUSIC)}")
    else:
        logger.warning(f"  Issue 12: NO MUSIC BED FOUND — narration will have no background music")

    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "work")
    os.makedirs(work_dir, exist_ok=True)

    dialogue = script.get("dialogue", [])
    lines = audio_data.get("lines", [])
    parts = []
    part_idx = 0

    # Issue 5 FIX: Use the SAME social_posts list from the script (set by daily_producer).
    # This ensures the assembler's card visuals match the narrator's script order EXACTLY.
    # Only fall back to fetching if script doesn't have social_posts.
    tweet_card_posts = []
    social_card_idx = 0

    script_social_posts = script.get("social_posts", [])
    if script_social_posts:
        tweet_card_posts = list(script_social_posts)
        # Add display_order to each post for deterministic ordering
        for di, dp in enumerate(tweet_card_posts):
            dp["display_order"] = di
        logger.info(f"  SOCIAL ORDER (from script, Issue 5 fix): {len(tweet_card_posts)} posts")
    else:
        # Fallback: fetch fresh if script has no social_posts
        try:
            from utils.feature_flags import is_enabled
            if is_enabled("tweet_cards"):
                from utils.social_fetcher import get_todays_social_posts
                tweet_card_posts = get_todays_social_posts(max_posts=4)
                tweet_card_posts.sort(key=lambda p: p.get("likes", 0), reverse=True)
                for di, dp in enumerate(tweet_card_posts):
                    dp["display_order"] = di
        except Exception as e:
            logger.warning(f"Tweet card data load failed: {e}")

    if tweet_card_posts:
        # Sort by display_order to guarantee match with script narration
        tweet_card_posts.sort(key=lambda p: p.get("display_order", 0))
        logger.info(f"  SOCIAL POST ORDER CHECK:")
        for ti, tp in enumerate(tweet_card_posts):
            logger.info(f"    #{ti}: @{tp.get('handle', '?')} — {tp.get('text', '')[:40]}")

    # --- 1. INTRO: Issue 1 — COLD OPEN FIRST, THEN TITLE CARD ---
    # Per PRODUCTION_DESIGN_LAWS Section 1: cold open starts at 0:00 with most shocking moment.
    # NO logo/title card first. TitleCard plays AFTER the cold open hook (~8 seconds).
    audio_lines = audio_data.get("lines", [])
    cold_open_consumed = False

    # Find cold_open audio (first dialogue entry with type "cold_open", or first host line)
    cold_open_audio = None
    for al in audio_lines:
        if al.get("host") in ("CLIP",) or not al.get("path"):
            continue
        if al.get("path") and os.path.exists(al.get("path", "")):
            cold_open_audio = al
            break

    # BLACK DIAMOND: 2.0s cold open title card
    import datetime as _dt
    title_card_out = os.path.join(work_dir, f"part_{part_idx:03d}_title_card.mp4")
    title_date = _dt.datetime.now().strftime("%B %d, %Y").upper()
    tc_dur = 2.0
    _, tc_bg = _build_black_diamond_bg(tc_dur, label_out="tc_bg")
    tc_fg = tc_bg
    tc_fg += _build_corner_brackets_fg("tc_bg", "tc_brackets")
    tc_fg += (f"[tc_brackets]drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
              f"fontcolor={COLOR_WHITE}:fontsize=96:x=(w-text_w)/2:y=340,"
              f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
              f"fontcolor={COLOR_RED}:fontsize=64:x=(w-text_w)/2:y=460,"
              f"drawtext=fontfile={FONT_MONO}:text='{title_date}':"
              f"fontcolor={COLOR_MUTED}:fontsize=24:x=(w-text_w)/2:y=550,"
              f"drawtext=fontfile={FONT_MONO}:text='// SIGNAL DETECTED //':"
              f"fontcolor={COLOR_RED}:fontsize=20:x=(w-text_w)/2:y=620,"
              f"fade=t=in:st=0:d=0.5[outv];\n"
              f"anullsrc=r=48000:cl=stereo,atrim=0:{tc_dur}[outa]")
    tc_ok = run_ffmpeg_filtergraph(
        [],
        tc_fg,
        ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(tc_dur)],
        title_card_out, "title card", 30,
    )
    if tc_ok and os.path.exists(title_card_out):
        parts.append(title_card_out)
        logger.info(f"[{part_idx:03d}] TITLE CARD: {tc_dur}s")
        part_idx += 1

    if cold_open_audio:
        intro_out = os.path.join(work_dir, f"part_{part_idx:03d}_cold_open_hook.mp4")
        # GPT face-first: get clip 1 YouTube thumbnail for cold open face panel
        co_thumb = ""
        if 1 in extracted_clips:
            co_clip_info = extracted_clips[1]
            co_thumb = fetch_youtube_thumbnail(co_clip_info)
            if co_thumb:
                logger.info(f"  Cold open thumbnail: {os.path.basename(co_thumb)}")
        intro_result = make_intro_coldopen(cold_open_audio["path"], intro_out, btc_price=btc_price, thumbnail_path=co_thumb)
        if intro_result:
            # Sprint 1.6: Overlay PiP of first clip onto cold open (face on screen)
            if 1 in extracted_clips:
                clip1_path = extracted_clips[1].get("path", "")
                if clip1_path and os.path.exists(clip1_path):
                    pip_co = os.path.join(work_dir, "pip_cold_open.mp4")
                    pip_co_result = make_pip_preview(clip1_path, pip_co)
                    if pip_co_result:
                        pip_co_out = os.path.join(work_dir, f"part_{part_idx:03d}_cold_open_pip.mp4")
                        intro_result = overlay_pip_on_narration(intro_result, pip_co_result, pip_co_out)
                        logger.info(f"  Cold open PiP overlay: clip #1 face on screen")
            parts.append(intro_result)
            dur = ffprobe_duration(intro_result)
            logger.info(f"[{part_idx:03d}] COLD OPEN HOOK (face, no logo, no music): {dur:.1f}s")
            part_idx += 1
            cold_open_consumed = True
        else:
            logger.warning("[---] Cold open intro failed, starting with first dialogue")
    else:
        logger.warning("[---] No cold open audio available, starting with first dialogue")

    # FIX 6: Prepare B-roll clips for insertion between host segments
    broll_queue = []
    if broll_clips:
        for bp in broll_clips:
            if isinstance(bp, str) and os.path.exists(bp):
                broll_queue.append(bp)
            elif isinstance(bp, dict) and bp.get("path") and os.path.exists(bp["path"]):
                broll_queue.append(bp["path"])
        logger.info(f"  B-roll clips available: {len(broll_queue)}")
    broll_idx = 0
    host_segment_count = 0  # Insert broll every 2 host segments

    # --- 2. DIALOGUE + CLIPS ---

    # Build thumbnail map: rank → thumbnail_path
    clip_thumbnails = {}
    for rank, cinfo in extracted_clips.items():
        tp = fetch_youtube_thumbnail(cinfo)
        if tp:
            clip_thumbnails[rank] = tp
            logger.info(f"  Thumbnail for clip #{rank}: {os.path.basename(tp)}")

    # Build PiP preview map: rank → pip_path (for narration segments before clips)
    pip_previews = {}
    for rank, cinfo in extracted_clips.items():
        clip_path = cinfo.get("path", "")
        if clip_path and os.path.exists(clip_path):
            pip_out = os.path.join(work_dir, f"pip_preview_r{rank}.mp4")
            pip_result = make_pip_preview(clip_path, pip_out)
            if pip_result:
                pip_previews[rank] = pip_result
                logger.info(f"  PiP preview for clip #{rank}: ready")

    # Track which audio line index we're on (host lines only, not CLIPs)
    # If we consumed the cold_open, skip the first host audio line
    audio_idx = 1 if cold_open_consumed else 0

    prev_segment_type = "intro"  # Track previous segment type for transition logic

    for i, entry in enumerate(dialogue):
        entry_type = entry.get("type", "")
        host_field = entry.get("host", "")

        # Skip first host entry if it was consumed as cold open
        if cold_open_consumed and i == 0 and host_field != "CLIP":
            cold_open_consumed = False  # only skip once
            continue

        if host_field == "CLIP":
            # YouTube clip — full screen, original audio
            rank = entry.get("rank", 0)
            clip_info = extracted_clips.get(rank, {})
            clip_path = clip_info.get("path", "")

            if clip_path and os.path.exists(clip_path):
                # FIX 1: No standalone glitch transitions — xfade applied in concatenation
                # The clip itself — try Remotion LowerThird overlay, fall back to FFmpeg
                clip_out = os.path.join(work_dir, f"part_{part_idx:03d}_clip_r{rank}.mp4")
                channel = clip_info.get("channel", "")
                handle = f"@{channel.replace(' ', '')}" if channel else "ProtocolPulse"
                result = ""
                try:
                    result = make_remotion_lower_third(
                        clip_path, handle, clip_out,
                        btc_price=btc_price,
                        speaker_name=clip_info.get("speaker", ""),
                    )
                except Exception as e:
                    logger.warning(f"Remotion LowerThird failed: {e}")
                if not result:
                    result = make_clip_visual(clip_path, handle, clip_out, btc_price=btc_price)
                if result:
                    # Mix lower_slide SFX at start of clip (for LowerThird entrance)
                    mix_lower_slide_sfx(result)
                    parts.append(result)
                    dur = ffprobe_duration(result)
                    logger.info(f"[{part_idx:03d}] CLIP #{rank} [{channel}]: {dur:.1f}s (with lower slide SFX)")
                    part_idx += 1
                else:
                    logger.warning(f"[---] Clip #{rank}: visual failed, skipping")
            else:
                logger.warning(f"[---] Clip #{rank}: file not found ({clip_path}), skipping")
            prev_segment_type = "clip"
            continue

        # FIX 1: No standalone transitions — xfade applied during concatenation

        # Host dialogue line — find matching audio
        # Match by audio_idx (skip CLIP entries in audio_lines)
        line_audio = None
        while audio_idx < len(audio_lines):
            al = audio_lines[audio_idx]
            if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al["path"]):
                line_audio = al
                audio_idx += 1
                break
            audio_idx += 1

        if not line_audio:
            logger.warning(f"[---] No audio for entry {i} ({entry_type})")
            continue

        host_num = int(line_audio.get("host", 1)) if str(line_audio.get("host", "1")).isdigit() else 1
        text = line_audio.get("text", entry.get("text", ""))
        audio_path = line_audio["path"]

        # Mix TTS with background music if music utility supports it
        # (We handle music mixing directly in make_host_visual via assets/music/pp_background.mp3)
        # Don't double-mix here — our new make_host_visual handles it internally

        # Create host visual with animated background
        # Determine thumbnail for setup/react segments
        clip_rank = entry.get("clip_rank", 0)
        thumb = clip_thumbnails.get(clip_rank, "") if entry_type in ("setup", "react") else ""

        line_out = os.path.join(work_dir, f"part_{part_idx:03d}_{entry_type}.mp4")

        # Sprint 1.5: Each tweet as its OWN video segment
        if entry_type == "social_segment" and tweet_card_posts and social_card_idx < len(tweet_card_posts):
            # Render up to 3 individual card segments (one per tweet)
            card_posts = tweet_card_posts[social_card_idx:social_card_idx + 3]

            # Try capturing tweet screenshots
            for cp in card_posts:
                tweet_url = cp.get("tweet_url", cp.get("url", ""))
                if tweet_url and not cp.get("screenshot_path"):
                    handle_name = cp.get("handle", "unknown").replace("@", "")
                    ss_path = os.path.join(work_dir, f"tweet_{handle_name}_{social_card_idx}.png")
                    try:
                        from utils.tweet_screenshot import capture_tweet
                        if capture_tweet(tweet_url, ss_path):
                            cp["screenshot_path"] = ss_path
                    except Exception:
                        pass

            # First card uses the current audio_path (matched by script)
            # Remaining cards: if there are more audio lines for social segments, use them
            # Otherwise, render with the same audio (single narration covers all cards)
            for ci, cp in enumerate(card_posts):
                card_out = os.path.join(work_dir, f"part_{part_idx:03d}_social_card_{ci}.mp4")
                logger.info(f"  SOCIAL CARD {ci}: @{cp.get('handle', '?')} — {cp.get('text', '')[:40]}")

                # Use the current audio for first card, try to find audio for subsequent cards
                card_audio = audio_path if ci == 0 else None
                if ci > 0:
                    # Look ahead for more social audio lines
                    peek_idx = audio_idx
                    while peek_idx < len(audio_lines):
                        al = audio_lines[peek_idx]
                        if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al["path"]):
                            card_audio = al["path"]
                            audio_idx = peek_idx + 1
                            break
                        peek_idx += 1
                    if not card_audio:
                        card_audio = audio_path  # fallback: reuse first card's audio

                # Card swoosh transition between cards
                if ci > 0:
                    swoosh_out = os.path.join(work_dir, f"part_{part_idx:03d}_card_swoosh.mp4")
                    if os.path.exists(CARD_SWOOSH):
                        swoosh_dur = ffprobe_duration(CARD_SWOOSH)
                        run_ffmpeg([
                            "-f", "lavfi", "-i", f"color=c=0x0C0C0C:s=1920x1080:d={swoosh_dur}:r=30",
                            "-i", CARD_SWOOSH,
                            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                            "-b:v", "8M", "-r", "30", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                            "-shortest", swoosh_out,
                        ], "card swoosh transition", 30)
                        if os.path.exists(swoosh_out):
                            parts.append(swoosh_out)
                            part_idx += 1

                # Render single-card visual
                card_result = ""
                try:
                    card_result = make_remotion_social_card(
                        card_audio, [cp], card_out, btc_price=btc_price,
                    )
                except Exception:
                    pass
                if not card_result:
                    card_result = make_social_card_visual(
                        card_audio, [cp], card_out, btc_price=btc_price,
                    )
                    if card_result:
                        card_result = _mix_swoosh_into_segment(card_result)
                if not card_result:
                    card_result = make_host_visual(
                        card_audio, host_num, text, card_out,
                        btc_price=btc_price, label=f"social_card_{ci}",
                        segment_type="social_segment",
                    )
                if card_result:
                    parts.append(card_result)
                    dur = ffprobe_duration(card_result)
                    logger.info(f"[{part_idx:03d}] SOCIAL CARD {ci} [@{cp.get('handle', '?')}]: {dur:.1f}s")
                    part_idx += 1

            social_card_idx += len(card_posts)
            prev_segment_type = entry_type
            continue  # parts already added per-card above
        elif entry_type == "social_segment":
            # No tweet card data available — fall back to host visual
            result = make_host_visual(
                audio_path, host_num, text, line_out,
                btc_price=btc_price, label=f"{entry_type} #{part_idx}",
                segment_type=entry_type,
            )
        else:
            # BV2: Route to Broadcast Engine V2 scene system (falls back to Black Diamond)
            seg_data = {"type": entry_type, "text": text,
                        "speaker": "DEBORAH" if host_num == 1 else "BRIAN",
                        "next_speaker": ""}
            # Look ahead for next clip speaker
            if entry_type == "setup" and clip_rank and clip_rank in extracted_clips:
                seg_data["next_speaker"] = extracted_clips[clip_rank].get("channel", "")
            result = make_broadcast_segment(
                seg_data, audio_path, host_num,
                part_idx, len(dialogue),
                line_out, btc_price=btc_price,
                thumbnail_path=thumb,
            )

            # Issue 4 FIX: PiP preview ONLY during "setup" segments (introducing next clip).
            # During "react" segments (discussing previous clip), show PREVIOUS clip thumbnail instead.
            # This prevents the confusing situation where the next clip's preview appears
            # while the narrator is still reacting to the previous clip.
            if result and entry_type == "setup" and clip_rank:
                pip_path = pip_previews.get(clip_rank, "")
                if pip_path:
                    pip_out = result + ".pip.mp4"
                    pip_result = overlay_pip_on_narration(result, pip_path, pip_out)
                    if pip_result and pip_result != result:
                        os.replace(pip_result, result)
                        logger.info(f"  PiP preview overlaid for SETUP → clip #{clip_rank}")
            elif result and entry_type == "react":
                # React segments: no PiP preview of next clip (Issue 4)
                logger.info(f"  No PiP for REACT segment (previous clip thumbnail via static thumb)")

        if result:
            parts.append(result)
            dur = ffprobe_duration(result)
            speaker = "DEBORAH" if host_num == 1 else "BRIAN"
            logger.info(f"[{part_idx:03d}] {entry_type.upper()} [{speaker}]: {dur:.1f}s")
            part_idx += 1
            prev_segment_type = entry_type
            host_segment_count += 1

            # FIX 6: Insert B-roll clip every 2 host segments
            if broll_queue and broll_idx < len(broll_queue) and host_segment_count % 2 == 0:
                broll_path = broll_queue[broll_idx]
                broll_out = os.path.join(work_dir, f"part_{part_idx:03d}_broll_{broll_idx}.mp4")
                # Trim broll to 4s with BG music (or silent if no music)
                # BD branded overlay: red border + corners + ticker + watermark
                bd_broll_vf = (
                    "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                    "setsar=1,fps=30,fade=t=in:d=0.3,fade=t=out:st=3.5:d=0.5,"
                    f"drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.85:t=fill,"
                    f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.85:t=fill,"
                    f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.85:t=fill,"
                    f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.85:t=fill,"
                    f"drawbox=x=0:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=0:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=1880:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=1916:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=0:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=0:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=1880:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
                    f"drawbox=x=1916:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
                    f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
                    f"fontcolor={COLOR_RED}@0.6:fontsize=18:x=W-text_w-20:y=16,"
                    f"drawtext=fontfile={FONT_MONO}:text='// INCOMING SIGNAL':"
                    f"fontcolor={COLOR_RED}@0.8:fontsize=12:x=16:y=18,"
                    "format=yuv420p[outv];"
                )
                # APEX V2: No per-segment music — continuous BGM in concatenate_parts
                broll_ok = run_ffmpeg([
                    "-i", broll_path,
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", "4",
                    "-filter_complex",
                    bd_broll_vf +
                    "[1:a]atrim=0:4[outa]",
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-shortest",
                    broll_out,
                ], f"broll clip {broll_idx}", 60)
                if broll_ok and os.path.exists(broll_out):
                    parts.append(broll_out)
                    logger.info(f"[{part_idx:03d}] B-ROLL #{broll_idx}: 4.0s")
                    part_idx += 1
                broll_idx += 1
        else:
            logger.warning(f"[---] Host visual failed for {entry_type}")

    # --- 3. BRANDED OUTRO ---
    # Issue 8: The "Stay sovereign" wrap narration plays OVER the outro visual.
    # Find the wrap audio (last non-CLIP audio line).
    wrap_audio = ""
    for al in reversed(audio_lines):
        if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al.get("path", "")):
            wrap_audio = al["path"]
            break
    if wrap_audio:
        logger.info(f"  Wrap narration for outro: {os.path.basename(wrap_audio)}")

    narration_end = sum(ffprobe_duration(p) for p in parts if p and os.path.exists(p))
    logger.info(f"Narration ends at {narration_end:.1f}s — outro starts here")

    # FIX 1: No standalone pre-outro transition — xfade in concatenation

    outro_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro_branded.mp4")
    # Issue 8 FIX: Pass wrap narration to branded outro so "Stay sovereign" plays over it
    outro_result = make_branded_outro(outro_out, narration_audio="")
    if outro_result:
        parts.append(outro_result)
        dur = ffprobe_duration(outro_result)
        logger.info(f"[{part_idx:03d}] OUTRO (branded): {dur:.1f}s")
        part_idx += 1
    else:
        # Fall back to tag video
        outro_out2 = os.path.join(work_dir, f"part_{part_idx:03d}_outro_tag.mp4")
        outro_result = make_tag_video(outro_out2)
        if outro_result:
            parts.append(outro_result)
            dur = ffprobe_duration(outro_result)
            logger.info(f"[{part_idx:03d}] OUTRO (tag fallback): {dur:.1f}s")
            part_idx += 1
        else:
            logger.warning("[---] No outro available")

    # --- 4. CONCATENATE ---
    logger.info(f"\nConcatenating {len(parts)} parts...")
    for i, p in enumerate(parts):
        dur = ffprobe_duration(p) if p and os.path.exists(p) else 0
        logger.info(f"  Part {i:03d}: {os.path.basename(p)} ({dur:.1f}s)")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    result = concatenate_parts(parts, output_path)

    if result and os.path.exists(result):
        dur = ffprobe_duration(result)
        sz = os.path.getsize(result) / 1024 / 1024
        logger.info(f"\n{'='*60}")
        logger.info(f"DONE: {result}")
        logger.info(f"Duration: {dur:.1f}s | Size: {sz:.1f}MB")
        logger.info(f"{'='*60}")
        return result

    logger.error("Assembly failed — no output produced")
    return ""


def verify_video(path: str) -> bool:
    """Verify output video meets spec."""
    logger.info(f"Verifying: {os.path.basename(path)}")

    if not os.path.exists(path):
        logger.error("File does not exist")
        return False

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True,
    )
    try:
        info = json.loads(r.stdout)
    except Exception:
        logger.error("Cannot parse ffprobe output")
        return False

    streams = info.get("streams", [])
    fmt = info.get("format", {})
    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)

    checks = []
    if vid:
        w, h = int(vid.get("width", 0)), int(vid.get("height", 0))
        checks.append(("Video codec", vid.get("codec_name") == "h264", vid.get("codec_name")))
        checks.append(("Resolution", w == 1920 and h == 1080, f"{w}x{h}"))
    else:
        checks.append(("Video stream", False, "MISSING"))

    if aud:
        checks.append(("Audio codec", aud.get("codec_name") == "aac", aud.get("codec_name")))
        checks.append(("Sample rate", aud.get("sample_rate") == "48000", aud.get("sample_rate")))
    else:
        checks.append(("Audio stream", False, "MISSING"))

    duration = float(fmt.get("duration", 0))
    size_mb = int(fmt.get("size", 0)) / 1024 / 1024
    checks.append(("Duration", 5 <= duration <= 600, f"{duration:.1f}s"))
    checks.append(("File size", 0.5 <= size_mb <= 500, f"{size_mb:.1f}MB"))

    all_pass = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        logger.info(f"  [{status}] {name}: {detail}")

    return all_pass


if __name__ == "__main__":
    logger.info("Assembler V6 — use daily_producer.py to run the full pipeline")
