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
COLOR_BG          = "0x0A0A0F"   # VDS dark navy — #0A0A0F per PIPELINE_LAWS
COLOR_PANEL       = "0x050607"   # BEV2 elevated surface
COLOR_PANEL2      = "0x080a0c"   # secondary surface
COLOR_RED         = "0xFF3333"   # BD signal red — all accents
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
COLOR_CYAN        = "0x5DE4FF"   # VDS cyan — data accents, chart signal line
COLOR_AMBER       = COLOR_CORAL
BV2_OBSIDIAN    = COLOR_BG
BV2_DEEP_PANEL  = COLOR_PANEL
BV2_SIGNAL_RED  = COLOR_RED_WARM
BV2_STARK_WHITE = COLOR_WHITE
BV2_MUTED       = COLOR_WHITE  # secondary text (used @0.33 opacity, warm white)
BV2_EMERALD     = COLOR_GREEN
BV2_RED_LIGHT   = "0xFF8595"   # gradient accent

INTRO_VIDEO = os.path.join(ASSETS, "intro.mp4")
OUTRO_VIDEO = os.path.join(ASSETS, "outro.mp4")
GLITCH_TRANSITION = os.path.join(ASSETS, "transitions", "glitch_transition_waud.mp4")
DIGITAL_TRANSITION = os.path.join(ASSETS, "transitions", "digital_transition_1080p.mov")
WATERMARK = os.path.join(ASSETS, "logo", "watermark.png")
BG_MUSIC = os.path.join(ASSETS, "music", "pp_background.mp3")
TAG_VIDEO = os.path.join(ASSETS, "tag_vertical.mp4")
OUTRO_BRANDED = os.path.join(ASSETS, "outro_branded.mp4")
INTRO_TAG = os.path.join(ASSETS, "intro_tag.mp4")
INTRO_MUSIC_FILE = os.path.join(ASSETS, "intro_music.mp3")
BG_LOOP = os.path.join(ASSETS, "bg_loop.mp4")
PIP_PLACEHOLDER = os.path.join(ASSETS, "pip_placeholder.mp4")
OUTRO_BRANDED_NEW = os.path.join(ASSETS, "outro_branded_new.mp4")
LOGO_IMAGE = os.path.join(ASSETS, "logo_protocol_pulse.png")
SCANLINE_OVERLAY = os.path.join(ASSETS, "scanline_overlay.png")
# Issue 3: Custom whoosh sound — prefer custom_whoosh.wav/.mp3 over generated glitch_whoosh.wav
_CUSTOM_WHOOSH_MP3 = os.path.join(ASSETS, "sfx", "custom_whoosh.mp3")
_CUSTOM_WHOOSH_WAV = os.path.join(ASSETS, "sfx", "custom_whoosh.wav")
if os.path.exists(_CUSTOM_WHOOSH_WAV):
    GLITCH_WHOOSH = _CUSTOM_WHOOSH_WAV
elif os.path.exists(_CUSTOM_WHOOSH_MP3):
    # Convert mp3 to wav for consistency if not already done
    subprocess.run(["ffmpeg", "-y", "-i", _CUSTOM_WHOOSH_MP3, _CUSTOM_WHOOSH_WAV],
                   capture_output=True, text=True, timeout=10)
    GLITCH_WHOOSH = _CUSTOM_WHOOSH_WAV if os.path.exists(_CUSTOM_WHOOSH_WAV) else _CUSTOM_WHOOSH_MP3
else:
    GLITCH_WHOOSH = os.path.join(ASSETS, "sfx", "glitch_whoosh.wav")
    logging.getLogger("Assembler").info("CUSTOM WHOOSH NOT FOUND — using generated")
CARD_SWOOSH = os.path.join(ASSETS, "sfx", "card_swoosh.wav")
DATA_BLIP = os.path.join(ASSETS, "sfx", "data_blip.wav")
LOWER_SLIDE = os.path.join(ASSETS, "sfx", "lower_slide.wav")


def _get_bg_layer(inputs: list, duration: float, label_out: str = "bb_bg") -> str:
    """Get background layer filtergraph. Uses bg_loop.mp4 if available, else procedural.

    Appends bg_loop to inputs list and returns filtergraph that outputs [label_out].
    bg_loop replaces the procedural background for narration/host segments.
    """
    if os.path.exists(BG_LOOP):
        inputs.append(["-stream_loop", "-1", "-i", BG_LOOP])
        bg_idx = len(inputs) - 1
        # Round 2 Fix 7: Glassmorphic darkening overlay on bg_loop for PiP segments
        # Applies 45% black overlay so bg_loop is visible but not distracting
        fg = (f"[{bg_idx}:v]scale=1920:1080,setsar=1,fps=30,"
              f"trim=0:{duration},setpts=PTS-STARTPTS,"
              # Keep vignette for cinematic depth
              f"vignette=PI/4:mode=backward,"
              # Glassmorphic darken: multiply brightness by 0.55 (45% darker)
              f"eq=brightness=-0.15:contrast=0.9,"
              # Red border frame (2px all edges — PIPELINE_LAWS)
              f"drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
              f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
              f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
              f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill[{label_out}];\n")
        return fg
    _, fg = _build_broadcast_bg(duration, label_out=label_out)
    return fg


def apply_scanline(inputs: list, fg: str, label_in: str, label_out: str,
                   duration: float) -> str:
    """R26 UPGRADE 1: CRT scanline overlay — adds scanline_overlay.png on top of scene.

    Appends the PNG to inputs and returns updated filtergraph that overlays it.
    """
    if not os.path.exists(SCANLINE_OVERLAY):
        fg += f"[{label_in}]copy[{label_out}];\n"
        return fg
    inputs.append(SCANLINE_OVERLAY)
    sl_idx = len(inputs) - 1
    fg += (f"[{sl_idx}:v]scale=1920:1080,loop=loop=-1:size=2:start=0,"
           f"setpts=PTS-STARTPTS,trim=0:{duration},setpts=PTS-STARTPTS,"
           f"format=rgba[_scanline];\n")
    fg += f"[{label_in}][_scanline]overlay=0:0:format=auto[{label_out}];\n"
    return fg


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


_PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_live_metric(key: str, fallback: str) -> str:
    """Fetch a live metric from intelligence signals JSON files, with API fallback for hashrate."""
    for path in ['data/intelligence/live_signals.json', 'data/intelligence/daily_signals.json']:
        try:
            with open(os.path.join(_PIPELINE_DIR, path)) as f:
                d = json.load(f)
                if key in d:
                    return str(d[key])
        except Exception:
            pass
    # API fallback for hashrate
    if key == "hashrate":
        try:
            import urllib.request as _ur
            with _ur.urlopen("https://mempool.space/api/v1/mining/hashrate/3d", timeout=5) as r:
                data = json.load(r)
                if data.get("currentHashrate"):
                    eh = data["currentHashrate"] / 1e18
                    return f"{eh:,.0f} EH/s"
        except Exception:
            pass
    # API fallback for mempool fee
    if key == "mempool_fee":
        try:
            import urllib.request as _ur
            with _ur.urlopen("https://mempool.space/api/v1/fees/recommended", timeout=5) as r:
                data = json.load(r)
                return f"{data.get('halfHourFee', 'N/A')} sat/vB"
        except Exception:
            pass
    return fallback


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
    # Layer 1: VDS dark navy base (#0A0A0F per PIPELINE_LAWS)
    f += f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30[bd_base];\n"
    # Layer 2: Red radial glow — top-center (subtle)
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(55*exp(-((X-960)*(X-960)+Y*Y)/380000),0,255)':g='0':b='0'[bd_glow_top];\n")
    f += f"[bd_base][bd_glow_top]blend=all_mode=screen[bg1];\n"
    # Layer 3: Red radial glow — bottom-center
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(35*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/280000),0,255)':g='0':b='0'[bd_glow_bot];\n")
    f += f"[bg1][bd_glow_bot]blend=all_mode=screen[bg2];\n"
    # Layer 4: Tactical surveillance grid (very subtle)
    f += f"[bg2]drawgrid=width=120:height=68:thickness=1:color=0xFF0000@0.07[bg3];\n"
    # Layer 5: Scanlines (horizontal every 3px)
    f += f"[bg3]drawgrid=width=0:height=3:thickness=1:color=0xFF0000@0.025[bg4];\n"
    # Layer 6: Vignette
    f += f"[bg4]vignette=PI/4:mode=backward[bg5];\n"
    # Layer 7: Red border frame (2px solid on all 4 edges)
    f += (f"[bg5]drawbox=x=0:y=0:w=1920:h=2:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=0:y=1078:w=1920:h=2:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=0:y=0:w=2:h=1080:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=1918:y=0:w=2:h=1080:color=0xFF3333@0.85:t=fill[{label_out}];\n")
    return ([], f)


def _build_info_bar_fg(duration: float, btc_price: str, block_height: str = "",
                       label_in: str = "v_pre_tick", label_out: str = "v_ticked") -> str:
    """BLACK DIAMOND ticker bar — red scrolling intel on near-black bg."""
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    content = (f"  PROTOCOL PULSE  //  BITCOIN {safe_btc}  //  {date_str}"
               f"  //  PROTOCOLPULSE.IO  //  STAY SOVEREIGN  "
               f"  //  PROTOCOL PULSE DAILY BRIEF  //  {date_str}"
               f"  //  FEAR/GREED  //  STAY SOVEREIGN"
               f"  //  BITCOIN {safe_btc}  //  PROTOCOLPULSE.IO  ")
    safe_content = content.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # FIX 5: Glassmorphic black base bar
    fg += f"color=c=0x000000@0.75:s=1920x48:d={duration}:r=30[tickbase];\n"
    # Red top separator line (2px)
    fg += f"[tickbase]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.85:t=fill[tickline];\n"
    # Static 'PULSE CHECK' label left
    fg += (f"[tickline]drawtext=fontfile={FONT_MONO}:text='PULSE CHECK':"
           f"fontcolor=0xF4F5F8:fontsize=14:x=8:y=18[tickstatic];\n")
    # Scrolling red text
    fg += (f"[tickstatic]drawtext=fontfile={FONT_MONO}:text='{safe_content}':"
           f"fontcolor={COLOR_RED}:fontsize=14:"
           f"x=W-mod(n*2\\,W+text_w):y=18[ticker];\n")
    # Overlay bar onto video frame at y=1032
    fg += f"[{label_in}][ticker]overlay=0:1032[{label_out}];\n"
    return fg


def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
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
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
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


def _generate_fallback_silent_audio(work_dir: str, idx: int, text: str = "") -> str:
    """BUG1 FIX: Generate silence audio as TTS fallback when ElevenLabs quota is exhausted.

    Estimates duration from text length (~150 words/min, ~5 chars/word).
    Returns path to silent .m4a file, or "" on failure.
    """
    # Estimate duration: ~150 wpm, ~5 chars/word → ~750 chars/min → ~12.5 chars/s
    # Minimum 2s, maximum 30s
    dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
    out = os.path.join(work_dir, f"fallback_silence_{idx:03d}.m4a")
    ok = run_ffmpeg([
        "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
        "-t", str(dur),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        out,
    ], "fallback silence", 15)
    if ok and os.path.exists(out):
        logger.warning(f"  [fallback] Generated {dur:.1f}s silence for idx={idx} (TTS quota exhausted)")
        return out
    return ""


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
             f"[0:a]volume=0.15[va];[1:a]volume=0.25[vb];"
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


# ── Branded intro tag ─────────────────────────────────────────────────────

def make_intro_tag_sequence(output_path: str) -> str:
    """Render intro_tag.mp4 (8s branded intro) as the episode opener.

    Plays intro_tag.mp4 at full quality with its embedded audio.
    intro_music.mp3 is NOT mixed here — it's mixed in concatenate_parts()
    so it can continue seamlessly into the first narration segment.
    """
    if not os.path.exists(INTRO_TAG):
        logger.warning("intro_tag.mp4 not found — skipping intro tag")
        return ""

    tag_dur = ffprobe_duration(INTRO_TAG)
    if tag_dur <= 0:
        logger.warning("intro_tag.mp4 has zero duration")
        return ""

    vf = "scale=1920:1080,setsar=1,format=yuv420p"

    # Check if intro_tag has audio
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", INTRO_TAG],
        capture_output=True, text=True,
    )
    has_audio = "audio" in r.stdout

    if has_audio:
        ok = run_ffmpeg([
            "-i", INTRO_TAG,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            # R25 FIX 3: Intro music atrim 8s, fade from 6s
            "-af", "atrim=start=0:end=8,asetpts=PTS-STARTPTS,afade=t=out:st=6.0:d=2.0",
            output_path,
        ], "intro tag sequence", 120)
    else:
        # Add silent audio track for concat compatibility
        ok = run_ffmpeg([
            "-i", INTRO_TAG,
            "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
            "-vf", vf,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(tag_dur), "-shortest",
            output_path,
        ], "intro tag sequence (no audio)", 120)

    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        logger.info(f"  Intro tag: {dur:.1f}s")
        return output_path

    logger.warning("Intro tag failed — skipping")
    return ""


# ── Cold open intro ───────────────────────────────────────────────────────

def make_intro_coldopen(tts_path: str, output_path: str, btc_price: str = "N/A", thumbnail_path: str = "") -> str:
    """PBX voice-over intro: overlay cold_open TTS on intro_tag.mp4 video.

    Broadcast hook technique — PBX starts speaking at t=0.5s while the
    Protocol Pulse logo animates.  Intro music ducks to 30% under TTS.
    If TTS is longer than 8s the intro video freezes its last frame and
    PBX keeps talking.  Falls back to cyberpunk bg if intro_tag is missing.
    """
    import datetime
    tts_dur = ffprobe_duration(tts_path)
    # Render22 FIX 4: Full cold open — 1.5s PBX start delay + full TTS + 0.3s tail
    total_dur = max(tts_dur + 1.8, 3.0)  # 1.5s delay + tts + 0.3s tail

    # ── Try intro_tag.mp4 as video source ──
    use_intro_tag = os.path.exists(INTRO_TAG)
    if use_intro_tag:
        tag_dur = ffprobe_duration(INTRO_TAG)
        if tag_dur <= 0:
            use_intro_tag = False

    if use_intro_tag:
        # Check if intro_tag has embedded audio
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", INTRO_TAG],
            capture_output=True, text=True,
        )
        tag_has_audio = "audio" in r.stdout

        # Video: use intro_tag, freeze last frame if TTS outlasts it
        vid_dur = max(total_dur, tag_dur)
        vf = (f"scale=1920:1080,setsar=1,format=yuv420p,"
              f"tpad=stop_mode=clone:stop_duration={max(0, vid_dur - tag_dur + 1)}")

        if tag_has_audio:
            # FIX 1 (render11): Hard cut intro music at exactly 3.0s — strip tag's baked audio,
            # use only intro_music.mp3 trimmed to 3s + TTS delayed by 0.5s.
            # The -an on intro_tag input is handled by ignoring [0:a] — we read intro_music separately.
            _has_intro_mus = os.path.exists(INTRO_MUSIC_FILE)
            if _has_intro_mus:
                ok = run_ffmpeg([
                    "-i", INTRO_TAG,                    # [0] intro tag (video+audio — audio ignored)
                    "-i", tts_path,                     # [1] PBX cold open TTS
                    "-i", INTRO_MUSIC_FILE,             # [2] intro music (clean source)
                    "-filter_complex", (
                        # Video: intro tag with last-frame freeze
                        f"[0:v]{vf},"
                        f"fade=t=out:st={max(0, vid_dur - 0.5)}:d=0.5[outv];"
                        # Audio: intro music hard-cut at 3.0s (atrim), then silence via apad
                        f"[2:a]atrim=0:8.0,asetpts=PTS-STARTPTS,afade=t=out:st=6.0:d=2.0,volume=0.20,"
                        f"asetpts=PTS-STARTPTS[intro_mus];"
                        f"[1:a]aformat=channel_layouts=stereo,adelay=1500|1500[tts_delayed];"
                        f"[intro_mus][tts_delayed]amix=inputs=2:duration=longest:weights=1 1,"
                        f"alimiter=limit=0.85:level=disabled:attack=5:release=50,"
                        f"aresample=async=1[outa]"
                    ),
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                    "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                    "-r", "30",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-t", str(vid_dur),
                    output_path,
                ], "intro tag + PBX voice-over (hard cut intro music)", 300)
            else:
                # No separate intro music file — strip tag audio entirely, TTS only
                ok = run_ffmpeg([
                    "-i", INTRO_TAG,                    # [0] intro tag (video+audio — audio ignored)
                    "-i", tts_path,                     # [1] PBX cold open TTS
                    "-filter_complex", (
                        f"[0:v]{vf},"
                        f"fade=t=out:st={max(0, vid_dur - 0.5)}:d=0.5[outv];"
                        f"[1:a]aformat=channel_layouts=stereo,adelay=1500|1500,"
                        f"alimiter=limit=0.85:level=disabled:attack=5:release=50,"
                        f"aresample=async=1[outa]"
                    ),
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                    "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                    "-r", "30",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    "-t", str(vid_dur),
                    output_path,
                ], "intro tag + PBX voice-over (no intro music file)", 300)
        else:
            # No intro audio — just overlay TTS on silent intro video
            ok = run_ffmpeg([
                "-i", INTRO_TAG,
                "-i", tts_path,
                "-filter_complex", (
                    f"[0:v]{vf},"
                    f"fade=t=out:st={max(0, vid_dur - 0.5)}:d=0.5[outv];"
                    f"[1:a]aformat=channel_layouts=stereo,"
                    f"alimiter=limit=0.85:level=disabled:attack=5:release=50,"
                    f"aresample=async=1[outa]"
                ),
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                "-r", "30",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                "-t", str(vid_dur),
                output_path,
            ], "intro tag + PBX voice-over (no tag audio)", 300)

        if ok and os.path.exists(output_path):
            dur = ffprobe_duration(output_path)
            logger.info(f"  Intro+PBX voice-over: {dur:.1f}s (tag={tag_dur:.1f}s, tts={tts_dur:.1f}s)")
            return output_path
        logger.warning("Intro tag + PBX voice-over failed — falling back to bg-only cold open")

    # ── Fallback: cyberpunk background + date text ──
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    inputs = [tts_path]
    fg = _get_bg_layer(inputs, total_dur, "co_bg")
    fg += (f"[co_bg]"
           f"drawtext=fontfile={FONT_MONO}:text='{date_str}':"
           f"fontcolor={COLOR_WHITE}:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2,"
           f"fade=t=in:st=0:d=0.5,fade=t=out:st={max(0, total_dur - 0.5)}:d=0.5"
           f"[outv];\n")
    fg += (f"[0:a]aformat=channel_layouts=stereo,"
           f"alimiter=limit=0.85:level=disabled:attack=5:release=50,aresample=async=1[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "clean cold open (fallback)", 120,
    )
    return output_path if ok else ""


# ── Clip unavailable placeholder ──────────────────────────────────────────

def _make_clip_unavailable_card(rank: int, output_path: str, btc_price: str = "$N/A") -> str:
    """BUG4 FIX: 8-second branded 'INTELLIGENCE INCOMING' card — professional, not debug.

    Uses 0x0D1117 background (above blackdetect threshold 0x020304).
    Cyberpunk grid overlay, gold info rail, 'INTELLIGENCE INCOMING' branding.
    No 'error'/'unavailable'/'interrupted' language.
    """
    import datetime
    dur = 8.0
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = (btc_price or "$N/A").replace("'", "").replace('"', "").replace("\\", "")

    ok = run_ffmpeg([
        "-f", "lavfi", "-i",
        f"color=c=0x1A1A2E:s=1920x1080:r=30:d={dur}",  # FIX 4: brighter bg above blackdetect threshold
        "-f", "lavfi", "-i",
        f"anullsrc=r=48000:cl=stereo",
        "-filter_complex",
        # Cyberpunk grid overlay at low opacity (intentional look)
        f"[0:v]"
        f"drawgrid=width=60:height=60:thickness=1:color=0xFF0000@0.06,"
        f"drawgrid=width=120:height=120:thickness=1:color=0xFF0000@0.04,"
        # Horizontal scan lines (cyberpunk aesthetic)
        f"drawbox=x=0:y=270:w=1920:h=1:color=0xFF0000@0.12:t=fill,"
        f"drawbox=x=0:y=540:w=1920:h=1:color=0xFF0000@0.12:t=fill,"
        f"drawbox=x=0:y=810:w=1920:h=1:color=0xFF0000@0.12:t=fill,"
        # Center card container
        f"drawbox=x=360:y=280:w=1200:h=380:color=0x0A0E14@0.92:t=fill,"
        f"drawbox=x=360:y=280:w=1200:h=4:color=0xFF3333@0.9:t=fill,"
        f"drawbox=x=360:y=656:w=1200:h=4:color={COLOR_GOLD}@0.9:t=fill,"
        f"drawbox=x=360:y=280:w=4:h=380:color=0xFF3333@0.9:t=fill,"
        f"drawbox=x=1556:y=280:w=4:h=380:color=0xFF3333@0.9:t=fill,"
        # Main headline
        f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK'"
        f":fontcolor={COLOR_GOLD}:fontsize=52:x=(w-text_w)/2:y=360,"
        # Subtext
        f"drawtext=fontfile={FONT_MONO}:text='INTELLIGENCE INCOMING'"
        f":fontcolor=0x888888:fontsize=26:x=(w-text_w)/2:y=450,"
        f"drawtext=fontfile={FONT_MONO}:text='STAY SOVEREIGN'"
        f":fontcolor={COLOR_RED}@0.7:fontsize=18:x=(w-text_w)/2:y=500,"
        # Gold info rail at bottom
        f"drawbox=x=0:y=1032:w=1920:h=48:color={COLOR_GOLD}@0.95:t=fill,"
        f"drawtext=fontfile={FONT_BOLD}:text='BITCOIN {safe_btc}':fontcolor=0x000000:fontsize=14:x=20:y=1048,"
        f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOLPULSE.IO':fontcolor=0x000000:fontsize=15:x=(w-text_w)/2:y=1047,"
        f"drawtext=fontfile={FONT_MONO}:text='{date_str} - DAILY BRIEF':fontcolor=0x000000:fontsize=14:x=w-text_w-20:y=1048,"
        # Watermark top-right
        f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':fontcolor={COLOR_RED}@0.4:fontsize=18:x=w-230:y=20"
        f"[outv]",
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-maxrate", "10M", "-bufsize", "15M",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-t", str(dur),
        output_path,
    ], "clip_unavailable_card", 30)
    return output_path if ok and os.path.exists(output_path) else ""


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


# ── Branded outro (new) ───────────────────────────────────────────────────

def make_outro_branded_new(output_path: str) -> str:
    """Render outro_branded_new.mp4 as the final episode segment.

    Has its own embedded music — NO additional music, NO wrap narration.
    Hard cut at end — NO fade-to-black, NO silence padding.
    """
    if not os.path.exists(OUTRO_BRANDED_NEW):
        logger.warning("outro_branded_new.mp4 not found — falling back to old outro")
        return ""

    dur = ffprobe_duration(OUTRO_BRANDED_NEW)
    if dur <= 0:
        return ""

    # Scale to 1920x1080, hard cut at end (no fades)
    vf = ("scale=1920:1080:force_original_aspect_ratio=increase,"
          "crop=1920:1080,setsar=1,fps=30,format=yuv420p")

    ok = run_ffmpeg([
        "-i", OUTRO_BRANDED_NEW,
        "-vf", vf,
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        output_path,
    ], "branded outro new", 60)

    if ok and os.path.exists(output_path):
        out_dur = ffprobe_duration(output_path)
        logger.info(f"  Branded outro (new): {out_dur:.1f}s — hard cut, own music")
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
        logger.warning(f"PiP: clip path missing: {clip_path}")
        logger.warning(f"PiP SKIP — will show narration without PiP overlay")
        return ""
    try:
        file_size = os.path.getsize(clip_path)
        if file_size < 50_000:  # < 50KB = stub/corrupt
            logger.warning(f"PiP: clip too small ({file_size}b), skipping: {clip_path}")
            return ""
    except OSError as e:
        logger.warning(f"PiP: cannot stat clip: {e}")
        return ""
    clip_dur = ffprobe_duration(clip_path)
    if clip_dur < 2:  # FIX 1: lowered min from 10s to 2s
        return ""
    actual_dur = min(duration, clip_dur - 0.5)
    if actual_dur <= 0:
        actual_dur = min(duration, clip_dur)
    # Extract from MIDPOINT of clip (better face shots)
    start = max(0, (clip_dur / 2) - (actual_dur / 2))
    ok = run_ffmpeg([
        "-ss", str(start), "-i", clip_path,
        "-t", str(actual_dur), "-an",
        "-vf", (
            # FIX 1: scale UP to fill the frame, then crop — NOT decrease+pad which leaves black borders
            "scale=716:370:force_original_aspect_ratio=increase,"
            "crop=716:370,setsar=1,"
            # Issue 3: grayscale + slow Ken Burns zoom for preview aesthetic
            "hue=s=0,eq=brightness=-0.1:contrast=1.1,"
            "zoompan=z='min(zoom+0.0005,1.15)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=716x370:fps=30,"
            "format=yuv420p"
        ),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-r", "30",
        output_path,
    ], "pip preview extract", 120)  # FIX 1: increased timeout
    if ok and os.path.exists(output_path):
        # Render21 FIX 2: Verify PiP output is real video (not still image)
        pip_out_dur = ffprobe_duration(output_path)
        try:
            fc_result = subprocess.run(
                ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                 "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", output_path],
                capture_output=True, text=True, timeout=30)
            frame_count = int(fc_result.stdout.strip() or "0")
        except Exception:
            frame_count = 0
        if pip_out_dur < 2.0 or frame_count < 15:
            logger.error(f"PiP STILL IMAGE detected: dur={pip_out_dur:.1f}s frames={frame_count} src={clip_path}")
            try:
                os.remove(output_path)
            except OSError:
                pass
            return ""
        logger.info(f"PiP verified: {pip_out_dur:.1f}s, {frame_count} frames from {clip_path}")
        return output_path
    return ""


def _ensure_pip_placeholder() -> str:
    """Render18 FIX 1: Generate branded PiP placeholder from bg_loop if it doesn't exist."""
    if os.path.exists(PIP_PLACEHOLDER) and os.path.getsize(PIP_PLACEHOLDER) > 10000:
        return PIP_PLACEHOLDER
    if not os.path.exists(BG_LOOP):
        logger.warning("PiP placeholder: bg_loop.mp4 not found, cannot generate")
        return ""
    ok = run_ffmpeg([
        "-i", BG_LOOP,
        "-t", "8",
        "-vf", "scale=716:370:force_original_aspect_ratio=increase,crop=716:370",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-an",
        PIP_PLACEHOLDER,
    ], "generate pip placeholder", 60)
    if ok and os.path.exists(PIP_PLACEHOLDER):
        logger.info(f"PiP placeholder generated: {PIP_PLACEHOLDER}")
        return PIP_PLACEHOLDER
    return ""


def overlay_pip_on_narration(narration_path: str, pip_path: str,
                              output_path: str) -> str:
    """Overlay PiP preview clip onto narration video.

    Issue 2: Position x=1056, y=200 (right 40% panel, 820x462 PiP).
    Drop shadow behind PiP (drawbox at +4px offset, black@0.3).
    "COMING UP..." label inside PiP bottom-left.
    """
    # Render22 FIX 2: NEVER use intro_tag as PiP source
    if pip_path and os.path.abspath(pip_path) == os.path.abspath(INTRO_TAG):
        logger.error(f"FIX 2: BLOCKED intro_tag.mp4 as PiP source in overlay_pip_on_narration! Returning narration unchanged.")
        return narration_path

    if not pip_path or not os.path.exists(pip_path):
        # Render18 FIX 1: Use branded placeholder instead of returning narration-only
        pip_path = _ensure_pip_placeholder()
        if not pip_path:
            logger.info(f"PiP: no preview available, using narration-only for this segment")
            return narration_path
        logger.info(f"PiP: using branded placeholder for this segment")
    pip_dur = ffprobe_duration(pip_path)
    ok = run_ffmpeg([
        "-i", narration_path,
        "-i", pip_path,
        "-filter_complex",
        # Drop shadow: dark box at +4px offset behind PiP
        f"[0:v]drawbox=x=1060:y=144:w=824:h=466:color={COLOR_BG}@0.3:t=fill:enable='lte(t,{pip_dur})',"
        # Red border outline around PiP box
        f"drawbox=x=1054:y=138:w=824:h=466:color=0xff3b5f@0.8:t=2:enable='lte(t,{pip_dur})',"
        # Channel name above PiP
        f"drawtext=fontfile={FONT_BOLD}:text='COMING UP':fontcolor={COLOR_GOLD}:fontsize=22:x=1056:y=120:enable='lte(t,{pip_dur})'[bg_shadow];"
        f"[1:v]drawtext=fontfile={FONT_BOLD}:text='COMING UP...':fontcolor={COLOR_TEXT}:fontsize=28:"
        f"x=12:y=h-38:box=1:boxcolor={COLOR_BG}@0.5:boxborderw=6,format=yuva420p[pip];"
        f"[bg_shadow][pip]overlay=1056:140:enable='lte(t,{pip_dur})',format=yuv420p[outv]",
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
    # Layer 1: VDS dark navy base (#0A0A0F per PIPELINE_LAWS)
    f += f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30[bb_base];\n"
    # Layer 2a: Red radial glow — top-left
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(46*exp(-((X)*(X)+Y*Y)/350000),0,255)':g='0':b='0'[bb_glow_tl];\n")
    f += f"[bb_base][bb_glow_tl]blend=all_mode=screen[bb1];\n"
    # Layer 2b: White radial glow — top-right (subtle)
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'"
          f":g='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'"
          f":b='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'[bb_glow_tr];\n")
    f += f"[bb1][bb_glow_tr]blend=all_mode=screen[bb2];\n"
    # Layer 2c: Red radial glow — bottom-center
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
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
           # LIVE label in red (render11 FIX 4: +16px gap from PROTOCOL PULSE text end)
           f"drawtext=fontfile={FONT_BOLD}:text='LIVE':"
           f"fontcolor={COLOR_RED}:fontsize=16:x=252:y=30,"
           # Bottom separator
           f"drawbox=x=20:y=64:w=1880:h=1:color={COLOR_RED}@0.25:t=fill"
           f"[{label_out}];\n")
    return fg


def _build_signature_info_rail(duration: float, btc_price: str, label_in: str,
                                label_out: str) -> str:
    """FIX 5 — Glassmorphic black bottom bar: rgba(0,0,0,0.75) with red top separator.
    Left: 'PULSE CHECK' white monospace. Right: scrolling red ticker.
    """
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = (btc_price or "N/A").replace("'", "").replace('"', "").replace("\\", "")
    ticker_content = (
        f"  BITCOIN {safe_btc}  //  PROTOCOL PULSE DAILY BRIEF  //  "
        f"{date_str}  //  FEAR/GREED  //  STAY SOVEREIGN  //  "
        f"BITCOIN {safe_btc}  //  PROTOCOLPULSE.IO  //  STAY SOVEREIGN  "
    )
    safe_ticker = ticker_content.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # Glassmorphic black bar (0,0,0 @0.75 opacity)
    fg += (f"[{label_in}]"
           f"drawbox=x=0:y=1032:w=1920:h=48:color=0x000000@0.75:t=fill,"
           # Red top separator line (2px)
           f"drawbox=x=0:y=1032:w=1920:h=2:color={COLOR_RED}@0.85:t=fill,"
           # Left: static 'PULSE CHECK' in white monospace
           f"drawtext=fontfile={FONT_MONO}:text='PULSE CHECK':"
           f"fontcolor=0xF4F5F8:fontsize=14:x=16:y=1048,"
           # Vertical separator after label
           f"drawbox=x=140:y=1036:w=1:h=38:color={COLOR_RED}@0.5:t=fill,"
           # Right: scrolling red ticker
           f"drawtext=fontfile={FONT_MONO}:text='{safe_ticker}':"
           f"fontcolor={COLOR_RED}:fontsize=14:"
           f"x=W-mod(n*2\\,W+text_w):y=1048"
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
    """APEX left 58% text zone — gold eyebrow kicker (VDS), warm white headline.
    Render11 FIX 3: Glassmorphic dark panel behind headline for readability.
    """
    safe_eye = _sanitize_text(eyebrow)
    safe_head = _sanitize_text(headline)
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""
    safe_tag = _sanitize_text(tag) if tag else ""

    # FIX 3: Calculate headline panel height (1 line = ~72px, 2 lines = ~144px)
    _head_nlines = max(1, (len(safe_head) // 18) + 1)
    _head_ph = _head_nlines * 72 + 20

    fg = ""
    # Gold eyebrow kicker (VDS)
    fg += (f"[{label_in}]drawtext=fontfile={FONT_MONO}:text='{safe_eye}':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[bv2_eye];\n")
    # FIX 3: Glassmorphic panel behind headline (dark 60% fill + white border)
    fg += (f"[bv2_eye]"
           f"drawbox=x=56:y=120:w=860:h={_head_ph}:color=0x000000@0.60:t=fill,"
           f"drawbox=x=56:y=120:w=860:h={_head_ph}:color=0xFFFFFF@0.12:t=2"
           f"[bv2_glass];\n")
    # Render21 FIX 6: 2-line headline if >45 chars — never truncate
    _h_line1, _h_line2 = _split_headline_for_render(safe_head)
    _h_fs = 34 if _h_line2 else 64
    _h_y2 = 130 + 65  # Render24 FIX 7: y+65 offset for line 2
    fg += (f"[bv2_glass]drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_h_line1)}':"
           f"fontcolor=0x111111:fontsize={_h_fs}:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_h_line1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_h_fs}:x=64:y=130")
    if _h_line2:
        fg += (f",drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_h_line2)}':"
               f"fontcolor=0x111111:fontsize={_h_fs}:x=66:y={_h_y2 + 2},"
               f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_h_line2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_h_fs}:x=64:y={_h_y2}")
    fg += f"[bv2_head];\n"
    # Body text
    if safe_body:
        fg += (f"[bv2_head]drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
               f"fontcolor=0xFFFFFF@0.6:fontsize=18:x=64:y=420:line_spacing=8[bv2_body];\n")
    else:
        fg += f"[bv2_head]copy[bv2_body];\n"
    # Render24 FIX 5: Live metrics strip below body text
    _m_hashrate = _sanitize_text(_get_live_metric("hashrate", "850 EH/s"))
    _m_mempool = _sanitize_text(_get_live_metric("mempool_fee", "12 sat/vB"))
    _m_etf = _sanitize_text(_get_live_metric("etf_flow", "$340M"))
    _m_halving = _sanitize_text(_get_live_metric("halving_pct", "78 pct"))
    _m_dominance = _sanitize_text(_get_live_metric("dominance", "61.4 pct"))
    fg += (f"[bv2_body]"
           # Metric strip background
           f"drawbox=x=64:y=480:w=860:h=80:color=0x000000@0.45:t=fill,"
           f"drawbox=x=64:y=480:w=860:h=1:color=0xFFFFFF@0.08:t=fill,"
           # HASHRATE
           f"drawtext=fontfile={FONT_MONO}:text='HASHRATE':fontcolor={COLOR_MUTED}:fontsize=9:x=76:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_hashrate}':fontcolor={COLOR_WHITE}:fontsize=13:x=76:y=500,"
           # MEMPOOL
           f"drawtext=fontfile={FONT_MONO}:text='MEMPOOL':fontcolor={COLOR_MUTED}:fontsize=9:x=250:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_mempool}':fontcolor={COLOR_WHITE}:fontsize=13:x=250:y=500,"
           # ETF FLOW
           f"drawtext=fontfile={FONT_MONO}:text='ETF FLOW':fontcolor={COLOR_MUTED}:fontsize=9:x=424:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_etf}':fontcolor={COLOR_WHITE}:fontsize=13:x=424:y=500,"
           # HALVING
           f"drawtext=fontfile={FONT_MONO}:text='HALVING':fontcolor={COLOR_MUTED}:fontsize=9:x=598:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_halving}':fontcolor={COLOR_WHITE}:fontsize=13:x=598:y=500,"
           # DOMINANCE
           f"drawtext=fontfile={FONT_MONO}:text='DOMINANCE':fontcolor={COLOR_MUTED}:fontsize=9:x=750:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_dominance}':fontcolor={COLOR_WHITE}:fontsize=13:x=750:y=500"
           f"[bv2_metrics];\n")

    # Tag pill (red accent)
    if safe_tag:
        fg += (f"[bv2_metrics]drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.15:t=fill,"
               f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.4:t=2,"
               f"drawtext=fontfile={FONT_MONO}:text='{safe_tag}':"
               f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590[{label_out}];\n")
    else:
        fg += f"[bv2_metrics]copy[{label_out}];\n"
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
    fg += (f"{audio_pad}aformat=channel_layouts=stereo,"
           f"alimiter=limit=0.85:level=disabled:attack=5:release=50,aresample=async=1[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label, 300,
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

    safe_head = _sanitize_text(headline)[:60]
    safe_body = _word_wrap(_sanitize_text(body), max_width=38, max_lines=4) if body else ""
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    inputs = [audio_path]
    fg = _get_bg_layer(inputs, total_dur, "bb_bg")

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
        ("BITCOIN PRICE", safe_btc, "+2.1 pct", True),
        ("HASHRATE", _get_live_metric("hashrate", "850 EH/s"), "+4.2 pct", True),
        ("ETF FLOW", _get_live_metric("etf_flow", "$340M"), "+18 pct", True),
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
                             btc_price: str = "N/A", duration: float = 0,
                             pip_video_path: str = "") -> str:
    """FIX 1 — APEX Narrator + PiP: uses actual video clip in PiP (not static thumbnail).
    pip_video_path: path to muted PiP preview video from make_pip_preview().
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    inputs = [audio_path]
    inp_idx = 1
    # FIX 1: prefer video PiP over static thumbnail
    has_pip_video = bool(pip_video_path and os.path.exists(pip_video_path)
                         and os.path.getsize(pip_video_path) > 10000)  # >10KB = real video
    has_thumb = bool(thumb_path and os.path.exists(thumb_path)) and not has_pip_video

    if has_pip_video:
        inputs.append(pip_video_path)
        pip_vid_idx = inp_idx
        inp_idx += 1
    else:
        pip_vid_idx = -1

    if has_thumb:
        inputs.append(thumb_path)
        thumb_idx = inp_idx
        inp_idx += 1
    else:
        thumb_idx = -1

    # ── Load intelligence data at render time ──────────────────────────────
    import json as _json, datetime as _dt
    _BASE_INTEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data", "intelligence")
    _nc_path = os.path.join(_BASE_INTEL, "narrative_context.json")
    _ds_path = os.path.join(_BASE_INTEL, "daily_signals.json")

    # Defaults
    _btc_price_val = btc_price if btc_price and btc_price not in ("N/A", "$0", "") else None
    _dominant_narrative = "Bitcoin Sound Money"
    _market_mood = "NEUTRAL"
    _top_quote = ""
    _quote_handle = ""
    _top_topics = []

    # Narrative context
    try:
        with open(_nc_path) as _f:
            _nc = _json.load(_f)
        _computed = _nc.get("computed_at", "")
        if _computed:
            _age = (_dt.datetime.now(_dt.timezone.utc) -
                    _dt.datetime.fromisoformat(_computed)).total_seconds() / 3600
            if _age < 12:
                _dominant_narrative = _nc.get("dominant_narrative", _dominant_narrative)[:42]
                _market_mood = _nc.get("market_mood", "neutral").upper().replace("_", " ")[:16]
                _hint = _nc.get("eryn_intro_hook", "")
                if "'" in _hint:
                    _qs = _hint.find("'") + 1
                    _qe = _hint.find("'", _qs)
                    if _qe > _qs:
                        _top_quote = _hint[_qs:_qe][:70]
                _tl = _nc.get("thought_leaders_mentioned", [])
                _quote_handle = ("@" + _tl[0][:18]) if _tl else ""
    except Exception:
        pass

    # Daily signals — top topics
    try:
        with open(_ds_path) as _f:
            _ds = _json.load(_f)
        _top_topics = [t.get("topic", "")[:28] for t in _ds.get("topic_velocity", [])[:3]
                       if t.get("velocity_score", 0) > 10]
    except Exception:
        pass

    # BTC price — fetch fresh if not passed in
    if not _btc_price_val:
        try:
            import urllib.request as _ur
            with _ur.urlopen("https://mempool.space/api/v1/prices", timeout=3) as _r:
                _btc_price_val = f"${_json.loads(_r.read()).get('USD', 0):,.0f}"
        except Exception:
            _btc_price_val = "LOADING"

    # Sanitize all strings for FFmpeg
    _btc_safe = _sanitize_text(_btc_price_val)
    _narr_safe = _sanitize_text(_dominant_narrative)
    _mood_safe = _sanitize_text(_market_mood)
    _quote_safe = _sanitize_text(_top_quote[:60]) if _top_quote else ""
    _handle_safe = _sanitize_text(_quote_handle)
    _ts_safe = _dt.datetime.now(tz=_dt.timezone.utc).strftime("%H:%M UTC")

    fg = _get_bg_layer(inputs, total_dur, "bb_bg")

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=67)

    # Left text zone with gold eyebrow
    safe_speaker = _sanitize_text(speaker)[:12]
    safe_head = _sanitize_text(headline)  # Render21 FIX 6: no truncation
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""

    # FIX 4 (render10): Glassmorphic panel behind headline for readability
    # Estimate headline height: single line = 72px, multi-line = 72*lines + 20
    _head_lines = max(1, (len(safe_head) // 20) + 1)
    _head_panel_h = _head_lines * 72 + 20
    fg += (f"[bv2_bar]"
           f"drawbox=x=56:y=122:w=860:h={_head_panel_h}:color=0x000000@0.55:t=fill,"
           f"drawbox=x=56:y=122:w=860:h={_head_panel_h}:color=0xFFFFFF@0.15:t=2"
           f"[np_eye];\n")
    # Render21 FIX 6: 2-line headline support
    _np_l1, _np_l2 = _split_headline_for_render(safe_head)
    _np_fs = 34 if _np_l2 else 64
    fg += (f"[np_eye]drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_np_l1)}':"
           f"fontcolor=0x111111:fontsize={_np_fs}:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_np_l1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_np_fs}:x=64:y=130")
    if _np_l2:
        fg += (f",drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_np_l2)}':"
               f"fontcolor=0x111111:fontsize={_np_fs}:x=66:y={130 + 65 + 2},"
               f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_np_l2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_np_fs}:x=64:y={130 + 65}")
    fg += f"[np_head];\n"
    # No duplicate body text — left zone is clean headline only
    fg += f"[np_head]copy[np_body];\n"

    # ═══════════════════════════════════════════════════════
    # R26 UPGRADE 5: NARRATOR LEFT PANEL — 4-ZONE LAYOUT
    # x=40, w=300, replaces BTC price panel
    # Zone A y=80-230: HASHRATE hero metric
    # Zone B y=240-420: 300x160 sparkline PNG
    # Zone C y=430-590: TODAY SIGNAL (fear/greed)
    # Zone D y=600-800: Five stacked metrics
    # ═══════════════════════════════════════════════════════

    # Fetch intelligence data for zones
    _z_intel = {}
    try:
        from fetch_intelligence_data import load_or_refresh as _z_intel_load
        _z_intel = _z_intel_load()
    except Exception:
        pass

    _z_hashrate = _sanitize_text(_get_live_metric("hashrate", "850 EH/s"))
    _z_hashrate_delta = _sanitize_text(_get_live_metric("hashrate_delta", "+4.2 pct"))
    _z_fg_value = _z_intel.get("fear_greed_value", 50)
    _z_block_height = _z_intel.get("block_height", 0)
    _z_dominance = _sanitize_text(_get_live_metric("dominance", "61.4 pct"))
    _z_mempool = _sanitize_text(_get_live_metric("mempool_fee", "12 sat/vB"))
    _z_etf = _sanitize_text(_get_live_metric("etf_flow", "$340M"))
    _z_halving = _sanitize_text(_get_live_metric("halving_pct", "78 pct"))

    # Panel background
    fg += (
        f"[np_body]"
        f"drawbox=x=40:y=220:w=300:h=590:color=0x05060A@0.88:t=fill,"
        f"drawbox=x=40:y=220:w=300:h=2:color={COLOR_RED}:t=fill,"
        f"drawbox=x=40:y=220:w=2:h=590:color={COLOR_RED}@0.6:t=fill"
        f"[np_z_base];\n"
    )

    # ── Zone A: HASHRATE hero metric (y=230-380) ──
    fg += (
        f"[np_z_base]"
        f"drawtext=fontfile={FONT_MONO}:text='HASHRATE':"
        f"fontcolor={COLOR_GOLD}:fontsize=13:x=54:y=232,"
        f"drawtext=fontfile={FONT_BOLD}:text='{_z_hashrate}':"
        f"fontcolor={COLOR_WHITE}:fontsize=32:x=54:y=252,"
        f"drawtext=fontfile={FONT_MONO}:text='{_z_hashrate_delta}':"
        f"fontcolor={COLOR_GREEN}:fontsize=13:x=54:y=292,"
        f"drawbox=x=54:y=316:w=270:h=1:color=0xFFFFFF@0.08:t=fill"
        f"[np_zone_a];\n"
    )

    # ── Zone B: Sparkline PNG overlay (y=330-490, 300x160) ──
    _sparkline_path = os.path.join(_PIPELINE_DIR, "cache", "charts", "sparkline_24h.png")
    if os.path.exists(_sparkline_path) and os.path.getsize(_sparkline_path) > 500:
        inputs.append(_sparkline_path)
        _spark_idx = len(inputs) - 1
        fg += (f"[{_spark_idx}:v]scale=280:140[_np_spark];\n"
               f"[np_zone_a][_np_spark]overlay=50:330[np_zone_b];\n")
    else:
        fg += f"[np_zone_a]copy[np_zone_b];\n"

    # ── Zone C: TODAY SIGNAL — fear/greed conviction (y=490-590) ──
    if _z_fg_value > 60:
        _z_conviction = "HIGH CONVICTION"
        _z_conv_color = COLOR_GREEN
    elif _z_fg_value >= 40:
        _z_conviction = "NEUTRAL"
        _z_conv_color = COLOR_WHITE
    else:
        _z_conviction = "CAUTION"
        _z_conv_color = COLOR_CORAL
    fg += (
        f"[np_zone_b]"
        f"drawtext=fontfile={FONT_MONO}:text='TODAY SIGNAL':"
        f"fontcolor={COLOR_GOLD}:fontsize=11:x=54:y=492,"
        f"drawtext=fontfile={FONT_BOLD}:text='{_z_fg_value}':"
        f"fontcolor={COLOR_WHITE}:fontsize=28:x=54:y=510,"
        f"drawtext=fontfile={FONT_BOLD}:text='{_z_conviction}':"
        f"fontcolor={_z_conv_color}:fontsize=14:x=54:y=544,"
        f"drawbox=x=54:y=570:w=270:h=1:color=0xFFFFFF@0.08:t=fill"
        f"[np_zone_c];\n"
    )

    # ── Zone D: Five stacked metrics (y=580-800) ──
    _z_bh_str = f"{_z_block_height:,}" if _z_block_height else "N/A"
    _zone_d_metrics = [
        ("MEMPOOL", _z_mempool),
        ("ETF FLOW", _z_etf),
        ("HALVING", _z_halving),
        ("DOMINANCE", _z_dominance),
        ("BLOCK HEIGHT", _sanitize_text(_z_bh_str)),
    ]
    _zd_last = "np_zone_c"
    for _zdi, (_zdl, _zdv) in enumerate(_zone_d_metrics):
        _zd_y = 582 + _zdi * 38
        _zd_out = f"np_zd{_zdi}"
        fg += (f"[{_zd_last}]"
               f"drawtext=fontfile={FONT_MONO}:text='{_zdl}':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x=54:y={_zd_y},"
               f"drawtext=fontfile={FONT_BOLD}:text='{_zdv}':"
               f"fontcolor={COLOR_WHITE}:fontsize=18:x=54:y={_zd_y + 14}"
               f"[{_zd_out}];\n")
        _zd_last = _zd_out
    intel_out = _zd_last

    # Corner bracket accents (cyberpunk tactical)
    fg += (
        f"[{intel_out}]"
        f"drawbox=x=1012:y=222:w=12:h=2:color={COLOR_RED}@0.5:t=fill,"
        f"drawbox=x=1022:y=222:w=2:h=12:color={COLOR_RED}@0.5:t=fill,"
        f"drawbox=x=64:y=650:w=12:h=2:color={COLOR_RED}@0.3:t=fill,"
        f"drawbox=x=64:y=640:w=2:h=12:color={COLOR_RED}@0.3:t=fill"
        f"[np_pills];\n"
    )

    # ═══════════════════════════════════════════════════════════════════════
    # R27 FIX 3: FULL-SCREEN ZOOMPAN PiP — cinematic preview background
    # Replaces small contained PiP box with full-screen desaturated preview
    # ═══════════════════════════════════════════════════════════════════════
    if has_pip_video and pip_vid_idx >= 0:
        pip_dur_src = ffprobe_duration(pip_video_path)
        src_frames = max(30, int(pip_dur_src * 30) + 5) if pip_dur_src > 0 else 300
        total_frames = max(30, int(total_dur * 30))
        loop_flag = f"loop=loop=-1:size={src_frames}:start=0," if pip_dur_src < total_dur else ""
        # Scale to full 1920x1080, crop to fill, desaturate, slow zoompan
        fg += (f"[{pip_vid_idx}:v]{loop_flag}"
               f"scale=1920:1080:force_original_aspect_ratio=increase,"
               f"crop=1920:1080,setsar=1,fps=30,"
               f"hue=s=0.4,"
               f"zoompan=z='min(zoom+0.0004,1.08)':d={total_frames}:"
               f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30,"
               f"trim=0:{total_dur},setpts=PTS-STARTPTS[np_fs_pip];\n")
        # Overlay full-screen PiP behind narrator panels (replaces bg)
        fg += f"[np_pills][np_fs_pip]overlay=0:0:shortest=1[np_fs_bg];\n"
    else:
        # No PiP video: keep current bg as-is (bg_loop, never intro_tag)
        fg += f"[np_pills]copy[np_fs_bg];\n"

    # Corner brackets overlay (red L-shapes, 60px each, 3px width)
    _cb_path = os.path.join(_PIPELINE_DIR, "assets", "corner_brackets.png")
    if os.path.exists(_cb_path) and os.path.getsize(_cb_path) > 500:
        inputs.append(_cb_path)
        _cb_idx = len(inputs) - 1
        fg += (f"[{_cb_idx}:v]scale=1920:1080[_cb_img];\n"
               f"[np_fs_bg][_cb_img]overlay=0:0[np_cb_over];\n")
    else:
        # Draw corner brackets with drawbox: 4 L-shapes, red #ff3b5f, 3px, 60px
        fg += (f"[np_fs_bg]"
               # Top-left L
               f"drawbox=x=40:y=40:w=60:h=3:color=0xFF3B5F:t=fill,"
               f"drawbox=x=40:y=40:w=3:h=60:color=0xFF3B5F:t=fill,"
               # Top-right L
               f"drawbox=x=1820:y=40:w=60:h=3:color=0xFF3B5F:t=fill,"
               f"drawbox=x=1877:y=40:w=3:h=60:color=0xFF3B5F:t=fill,"
               # Bottom-left L
               f"drawbox=x=40:y=1037:w=60:h=3:color=0xFF3B5F:t=fill,"
               f"drawbox=x=40:y=980:w=3:h=60:color=0xFF3B5F:t=fill,"
               # Bottom-right L
               f"drawbox=x=1820:y=1037:w=60:h=3:color=0xFF3B5F:t=fill,"
               f"drawbox=x=1877:y=980:w=3:h=60:color=0xFF3B5F:t=fill"
               f"[np_cb_over];\n")

    # Waveform strip at bottom y=920 h=80 from audio
    fg += (f"[np_cb_over]"
           f"drawbox=x=0:y=920:w=1920:h=80:color=0x000000@0.5:t=fill"
           f"[np_wave_bg];\n")
    # Audio waveform visualization in the strip
    fg += (f"[0:a]showwavespic=s=1920x80:colors={COLOR_RED}@0.7|{COLOR_RED}@0.3,"
           f"format=rgba[np_wave_pic];\n")
    fg += f"[np_wave_bg][np_wave_pic]overlay=0:920:shortest=1[np_wave_done];\n"

    # Channel name and clip title text overlay
    safe_next = _sanitize_text(next_speaker)[:30] if next_speaker else "NEXT SOURCE"
    fg += (f"[np_wave_done]"
           f"drawbox=x=0:y=860:w=800:h=50:color=0x000000@0.7:t=fill,"
           f"drawtext=fontfile={FONT_BOLD}:text='{safe_next}':"
           f"fontcolor={COLOR_WHITE}:fontsize=20:x=24:y=870,"
           f"drawbox=x=1600:y=860:w=200:h=24:color={COLOR_RED}@0.15:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='PREVIEW':"
           f"fontcolor={COLOR_RED}:fontsize=12:x=1660:y=864"
           f"[np_pip_final];\n")

    # Render11 FIX 7: Mini-dashboard panel below PiP (x=1060, y=700, w=820, h=160)
    # BTC price ticker + episode date + PULSE CHECK branding
    import datetime as _dt7
    _ep_date = _dt7.datetime.now().strftime("%b %d, %Y").upper()
    _ep_num = _dt7.datetime.now().strftime("EP-%j")
    fg += (f"[np_pip_final]"
           # Glassmorphic mini-dashboard panel
           f"drawbox=x=1060:y=700:w=820:h=160:color=0x05060A@0.85:t=fill,"
           f"drawbox=x=1060:y=700:w=820:h=2:color={COLOR_RED}@0.4:t=fill,"
           f"drawbox=x=1060:y=700:w=2:h=160:color={COLOR_RED}@0.3:t=fill,"
           # BTC LIVE label
           f"drawtext=fontfile={FONT_MONO}:text='BTC LIVE':"
           f"fontcolor={COLOR_GOLD}@0.6:fontsize=11:x=1078:y=714,"
           # BTC price in gold (large)
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(btc_price)}':"
           f"fontcolor={COLOR_GOLD}:fontsize=42:x=1078:y=730,"
           # Vertical separator
           f"drawbox=x=1400:y=714:w=1:h=130:color=0xFFFFFF@0.08:t=fill,"
           # Episode number + date
           f"drawtext=fontfile={FONT_MONO}:text='{_ep_num}':"
           f"fontcolor={COLOR_RED}:fontsize=12:x=1420:y=718,"
           f"drawtext=fontfile={FONT_MONO}:text='{_ep_date}':"
           f"fontcolor=0xFFFFFF@0.5:fontsize=11:x=1420:y=738,"
           # PULSE CHECK branding
           f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
           f"fontcolor={COLOR_WHITE}@0.3:fontsize=24:x=1420:y=780,"
           # Bottom edge
           f"drawbox=x=1060:y=858:w=820:h=1:color=0xFFFFFF@0.06:t=fill"
           f"[np_dash];\n")

    # Corner brackets (main frame)
    fg += _build_corner_brackets_fg("np_dash", "np_corners")
    wave_fg, np_audio_pad = _build_narration_wave("np_corners", "np_wave", "np_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "np_wave", "np_railed")
    # R26 UPGRADE 1: CRT SCANLINE
    fg = apply_scanline(inputs, fg, "np_railed", "np_scanned", total_dur)
    fg += f"[np_scanned]format=yuv420p[outv];\n"

    result = _bv2_encode(inputs, fg, output_path, total_dur, "APEX narrator+pip",
                         audio_pad=np_audio_pad)

    # Session 4 Fix 6: Try Remotion IntelPanel overlay (upgrade from drawtext)
    if result and os.path.exists(result):
        try:
            frames = max(int(total_dur * 30), 120)
            remotion_panel = _make_remotion_intel_panel(frames, btc_price)
            if remotion_panel and os.path.exists(remotion_panel):
                upgraded = output_path + ".intel_upgrade.mp4"
                ok = run_ffmpeg([
                    "-i", result,
                    "-i", remotion_panel,
                    "-filter_complex",
                    "[0:v][1:v]overlay=0:0:shortest=1[outv]",
                    "-map", "[outv]", "-map", "0:a",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                    "-b:v", "8M", "-c:a", "copy",
                    "-t", str(total_dur), upgraded,
                ], "Remotion IntelPanel overlay", 120)
                if ok and os.path.exists(upgraded):
                    shutil.move(upgraded, output_path)
                    logger.info("  Fix 6: Remotion IntelPanel overlay applied")
                else:
                    logger.info("  Fix 6: Remotion overlay failed — keeping drawtext panel")
        except Exception as e:
            logger.info(f"  Fix 6: Remotion IntelPanel skipped: {e}")

    return result


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
           f"setsar=1,fps=30,fade=t=in:d=0.3,fade=t=out:st={fade_out_start}:d=0.5[pc_raw];\n")
    # Cyberpunk aesthetic: darken clip slightly + tactical grid + radial vignette
    fg += (f"[pc_raw]"
           f"eq=brightness=-0.05:saturation=0.9:contrast=1.05,"
           f"drawgrid=width=120:height=68:thickness=1:color=0xFF0000@0.05,"
           f"vignette=PI/5:mode=backward"
           f"[pc_clip];\n")
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
           # Render14: removed atrim=start=2.5 (was root cause of lipsync desync)
           f"[0:a]aresample=async=1,asetpts=PTS-STARTPTS,"
           f"highpass=f=50,lowpass=f=15000,"
           f"afade=t=in:d=0.5,afade=t=out:st={max(0, fade_out_start - 0.5)}:d=0.5[outa]")

    # Render14: removed itsoffset probing (was causing lipsync issues with atrim removal)
    input_spec = video_path

    ok = run_ffmpeg_filtergraph(
        [input_spec], fg, ["[outv]", "[outa]"],
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
    """APEX Data Segment — full-canvas intelligence dashboard with 6 metric cards,
    rotating chart overlays, and sponsor strip (Meanwhile/Curated Mining/Protocol Pulse)."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    # ── Fetch intelligence data and render chart PNGs ──
    _intel_data = {}
    try:
        from fetch_intelligence_data import load_or_refresh as _intel_load
        _intel_data = _intel_load()
        from render_chart_assets import render_all as _render_charts
        _render_charts(_intel_data)
    except Exception as _intel_err:
        logger.warning("Intelligence data/chart render failed: %s", _intel_err)

    _chart_dir = os.path.join(_PIPELINE_DIR, "cache", "charts")
    _chart_files = ["price_chart.png", "hashrate_chart.png", "dominance_chart.png"]
    _chart_full = [os.path.join(_chart_dir, f) for f in _chart_files]
    charts_available = all(os.path.exists(p) and os.path.getsize(p) > 1000 for p in _chart_full)

    _fg_value = _intel_data.get("fear_greed_value", 0)
    _fg_label = _intel_data.get("fear_greed_label", "N/A")

    inputs = [audio_path]
    fg = _get_bg_layer(inputs, total_dur, "bb_bg")

    # ── Top eyebrow: "TODAY'S INTELLIGENCE" left, date right ──
    import datetime
    date_str = datetime.date.today().strftime("%B %d, %Y").upper()
    fg += (f"[bb_bg]drawtext=fontfile={FONT_MONO}:text='TODAYS INTELLIGENCE':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=40:y=40,"
           f"drawtext=fontfile={FONT_MONO}:text='{date_str}':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=w-tw-40:y=40"
           f"[ds_eyebrow];\n")

    # ── HEADLINE (Render24 FIX 7: universal 2-line wrap at char45) ──
    safe_head = _sanitize_text(headline)
    _ds_l1, _ds_l2 = _split_headline_for_render(safe_head)
    _ds_fs = 34 if _ds_l2 else 42
    fg += (f"[ds_eyebrow]drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ds_l1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_ds_fs}:x=40:y=72")
    if _ds_l2:
        fg += (f",drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ds_l2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_ds_fs}:x=40:y={72 + 65}")
    fg += f"[ds_headline];\n"

    # 6 metrics: FEAR GREED | HASHRATE | ETF FLOW | MEMPOOL FEE | HALVING % | DOMINANCE
    default_metrics = [
        ("FEAR GREED", str(_fg_value), _sanitize_text(_fg_label), _fg_value > 50),
        ("HASHRATE", _get_live_metric("hashrate", "850 EH/s"), "+4.2 pct", True),
        ("ETF FLOW", _get_live_metric("etf_flow", "$340M"), "+18 pct", True),
        ("MEMPOOL FEE", _get_live_metric("mempool_fee", "12 sat/vB"), "-8 pct", False),
        ("HALVING PCT", "78 pct", "+0.3 pct", True),
        ("DOMINANCE", "61.4 pct", "+1.1 pct", True),
    ]
    use_metrics = []
    if metrics:
        for m in metrics[:6]:
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
    while len(use_metrics) < 6:
        use_metrics.append(default_metrics[len(use_metrics)])

    # Render12 FIX C: Horizontal metric strip (6 cards in a row above hero chart)
    card_w, card_h, gap = 280, 80, 12
    grid_x, grid_y = 40, 140
    last = "ds_headline"
    for mi, (mlabel, mval, mdelta, mpos) in enumerate(use_metrics):
        mx = grid_x + mi * (card_w + gap)
        my = grid_y
        dc = COLOR_GREEN if mpos else COLOR_CORAL
        out = f"ds_m{mi}"
        fg += (f"[{last}]"
               # Card background
               f"drawbox=x={mx}:y={my}:w={card_w}:h={card_h}:color={COLOR_PANEL2}@0.95:t=fill,"
               # 3px red top accent
               f"drawbox=x={mx}:y={my}:w={card_w}:h=3:color={COLOR_RED}@0.6:t=fill,"
               # Gold label 10px
               f"drawtext=fontfile={FONT_MONO}:text='{mlabel}':"
               f"fontcolor={COLOR_GOLD}:fontsize=10:x={mx+10}:y={my+10},"
               # White value 22px bold
               f"drawtext=fontfile={FONT_BOLD}:text='{mval}':"
               f"fontcolor={COLOR_WHITE}:fontsize=22:x={mx+10}:y={my+28},"
               # Emerald/coral delta 11px mono
               f"drawtext=fontfile={FONT_MONO}:text='{mdelta}':"
               f"fontcolor={dc}:fontsize=11:x={mx+10}:y={my+58}"
               f"[{out}];\n")
        last = out

    # ── HERO CHART — ROTATING CHART OVERLAYS (price → hashrate → dominance) ──
    chart_panel_x, chart_panel_y = 200, 250
    chart_panel_w, chart_panel_h = 1520, 460

    if charts_available:
        # Add 3 chart PNGs as FFmpeg inputs
        _chart_input_start = len(inputs)
        for cp in _chart_full:
            inputs.append(cp)

        t1 = total_dur / 3.0
        t2 = 2 * total_dur / 3.0

        # Scale each chart PNG to panel size
        for ci in range(3):
            inp_idx = _chart_input_start + ci
            fg += (f"[{inp_idx}:v]scale={chart_panel_w}:{chart_panel_h},"
                   f"format=yuva420p[ds_chts{ci}];\n")

        # Overlay chart 0 (price): 0 → t1
        fg += (f"[{last}][ds_chts0]overlay=x={chart_panel_x}:y={chart_panel_y}:"
               f"enable='between(t,0,{t1:.3f})'[ds_chto0];\n")
        # Overlay chart 1 (hashrate): t1 → t2
        fg += (f"[ds_chto0][ds_chts1]overlay=x={chart_panel_x}:y={chart_panel_y}:"
               f"enable='between(t,{t1:.3f},{t2:.3f})'[ds_chto1];\n")
        # Overlay chart 2 (dominance): t2 → end
        fg += (f"[ds_chto1][ds_chts2]overlay=x={chart_panel_x}:y={chart_panel_y}:"
               f"enable='between(t,{t2:.3f},{total_dur:.3f})'[ds_chart_done];\n")
    else:
        # Fallback: static bars when charts unavailable
        chart_x_start = chart_panel_x + 40
        chart_y_base = chart_panel_y + chart_panel_h - 50
        chart_area_w = chart_panel_w - 80
        step_w = chart_area_w // 10
        bar_w = 120
        heights_raw = [30, 45, 38, 60, 55, 72, 85, 78, 95, 110]
        scale_factor = 3.0
        heights = [min(int(h * scale_factor), chart_panel_h - 100) for h in heights_raw]
        day_labels = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN", "MON", "TUE", "WED"]
        signal_line_y = chart_y_base - int(72 * scale_factor)

        fg += (f"[{last}]"
               f"drawbox=x={chart_panel_x}:y={chart_panel_y}:w={chart_panel_w}:h={chart_panel_h}:"
               f"color={COLOR_PANEL2}@0.85:t=fill,"
               f"drawbox=x={chart_panel_x}:y={chart_panel_y}:w={chart_panel_w}:h=1:"
               f"color=0xFFFFFF@0.08:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='BTC NETWORK STRESS INDEX':"
               f"fontcolor={COLOR_GOLD}:fontsize=24:x={chart_panel_x+24}:y={chart_panel_y+16},"
               f"drawbox=x={chart_panel_x+chart_panel_w-140}:y={chart_panel_y+12}:w=120:h=28:"
               f"color={COLOR_GOLD}@0.12:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='LIVE MODEL':"
               f"fontcolor={COLOR_GOLD}:fontsize=12:x={chart_panel_x+chart_panel_w-128}:y={chart_panel_y+18}"
               f"[ds_chart_bg];\n")

        last_chart = "ds_chart_bg"
        for ci, ch in enumerate(heights):
            cx = chart_x_start + ci * step_w + (step_w - bar_w) // 2
            cy = chart_y_base - ch
            out_c = f"ds_bar{ci}"
            gold_h = ch // 2
            fg += (f"[{last_chart}]"
                   f"drawbox=x={cx}:y={cy}:w={bar_w}:h={ch}:color={COLOR_RED}@0.6:t=fill,"
                   f"drawbox=x={cx}:y={cy}:w={bar_w}:h={gold_h}:color={COLOR_GOLD}@0.45:t=fill,"
                   f"drawtext=fontfile={FONT_MONO}:text='{day_labels[ci]}':"
                   f"fontcolor={COLOR_GOLD}:fontsize=11:"
                   f"x={cx + bar_w//2 - 11}:y={chart_y_base + 10}"
                   f"[{out_c}];\n")
            last_chart = out_c

        fg += (f"[{last_chart}]"
               f"drawbox=x={chart_x_start}:y={signal_line_y}:w={chart_area_w}:h=3:"
               f"color={COLOR_CYAN}@0.7:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='SIGNAL LINE':"
               f"fontcolor={COLOR_CYAN}:fontsize=11:x={chart_x_start + chart_area_w - 100}:"
               f"y={signal_line_y - 16}"
               f"[ds_chart_done];\n")

    # ── SPONSOR ROTATION STRIP ──
    sponsors = [
        {"name": "Meanwhile", "tagline": "Bitcoin Life Insurance",
         "cta": "Get covered in Bitcoin  protocolpulse.io/meanwhile", "color": COLOR_GOLD},
        {"name": "Curated Mining", "tagline": "White-Glove Bitcoin Mining",
         "cta": "Start mining  curatedmining.com", "color": COLOR_CYAN},
        {"name": "Protocol Pulse", "tagline": "Bitcoin Intelligence Daily",
         "cta": "Subscribe  protocolpulse.io", "color": COLOR_RED},
    ]
    slot_dur = total_dur / 3.0
    strip_x, strip_y, strip_w, strip_h = 40, 730, 1840, 120

    last_sp = "ds_chart_done"
    for si, sp in enumerate(sponsors):
        t_start = si * slot_dur
        t_end = (si + 1) * slot_dur
        enable = f"enable='between(t,{t_start:.3f},{t_end:.3f})'"
        sp_name = _sanitize_text(sp["name"])
        sp_tagline = _sanitize_text(sp["tagline"])
        sp_cta = _sanitize_text(sp["cta"])
        sp_color = sp["color"]
        out_sp = f"ds_sp{si}"
        fg += (f"[{last_sp}]"
               # Strip background
               f"drawbox=x={strip_x}:y={strip_y}:w={strip_w}:h={strip_h}:"
               f"color={COLOR_PANEL2}@0.95:t=fill:{enable},"
               # Left accent bar
               f"drawbox=x={strip_x}:y={strip_y}:w=6:h={strip_h}:"
               f"color={sp_color}@1.0:t=fill:{enable},"
               # "SPONSORED BY" micro label
               f"drawtext=fontfile={FONT_MONO}:text='SPONSORED BY':"
               f"fontcolor={COLOR_GOLD}:fontsize=10:x={strip_x+20}:y={strip_y+18}:{enable},"
               # Sponsor NAME 34px bold
               f"drawtext=fontfile={FONT_BOLD}:text='{sp_name}':"
               f"fontcolor={COLOR_WHITE}:fontsize=34:x={strip_x+20}:y={strip_y+38}:{enable},"
               # Tagline gray mono 15px
               f"drawtext=fontfile={FONT_MONO}:text='{sp_tagline}':"
               f"fontcolor={COLOR_MUTED}:fontsize=15:x={strip_x+20}:y={strip_y+80}:{enable},"
               # CTA right-aligned in sponsor color
               f"drawtext=fontfile={FONT_MONO}:text='{sp_cta}':"
               f"fontcolor={sp_color}:fontsize=14:"
               f"x={strip_x+strip_w}-tw-20:y={strip_y+80}:{enable},"
               # PARTNER badge top-right
               f"drawbox=x={strip_x+strip_w-100}:y={strip_y+8}:w=90:h=22:"
               f"color={sp_color}@0.15:t=fill:{enable},"
               f"drawtext=fontfile={FONT_MONO}:text='PARTNER':"
               f"fontcolor={sp_color}:fontsize=10:"
               f"x={strip_x+strip_w-90}:y={strip_y+13}:{enable}"
               f"[{out_sp}];\n")
        last_sp = out_sp

    fg += _build_corner_brackets_fg(last_sp, "ds_corners")
    wave_fg, ds_audio_pad = _build_narration_wave("ds_corners", "ds_wave", "ds_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "ds_wave", "ds_railed")
    # R26 UPGRADE 1: CRT SCANLINE
    fg = apply_scanline(inputs, fg, "ds_railed", "ds_scanned", total_dur)
    fg += f"[ds_scanned]format=yuv420p[outv];\n"

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX data segment",
                       audio_pad=ds_audio_pad)


# ── BV2 Scene 5: SOCIAL STACK ───────────────────────────────────────────

def _rank_cards_for_segment(cards: list, segment_text: str) -> list:
    """Session 4 Fix 4: Rank tweet cards by relevance to narrator text."""
    if not cards or not segment_text:
        return cards
    words = set(segment_text.lower().split())
    def score(card):
        card_words = set((card.get('text', '') + ' ' + card.get('handle', '')).lower().split())
        return len(words & card_words)
    return sorted(cards, key=score, reverse=True)


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
    fg = _get_bg_layer(inputs, total_dur, "bb_bg")

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=58)

    # Header zone with gold eyebrow — Render24 FIX 7: universal 2-line wrap
    _ss_head = _sanitize_text(headline)
    _ss_l1, _ss_l2 = _split_headline_for_render(_ss_head)
    _ss_fs = 34 if _ss_l2 else 48
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='SIGNAL LAYER':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ss_l1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_ss_fs}:x=64:y=130,")
    if _ss_l2:
        fg += (f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ss_l2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_ss_fs}:x=64:y={130 + 65},")
    fg += (f"drawtext=fontfile={FONT_MONO}:text='Bitcoin Social Conviction Index':"
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

    safe_head = _sanitize_text(headline)
    # Render24 FIX 7: universal 2-line wrap at char45
    _wr_l1, _wr_l2 = _split_headline_for_render(safe_head)
    _wrap_fontsize = 34 if _wr_l2 else 52
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""

    inputs = [audio_path]
    fg = _get_bg_layer(inputs, total_dur, "bb_bg")

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=100)

    # Left text zone with gold eyebrow
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='FINAL TAKE':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[wr_eye];\n")
    fg += (f"[wr_eye]drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_wr_l1)}':"
           f"fontcolor=0x111111:fontsize={_wrap_fontsize}:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_wr_l1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_wrap_fontsize}:x=64:y=130")
    if _wr_l2:
        fg += (f",drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_wr_l2)}':"
               f"fontcolor=0x111111:fontsize={_wrap_fontsize}:x=66:y={130 + 65 + 2},"
               f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_wr_l2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_wrap_fontsize}:x=64:y={130 + 65}")
    fg += f"[wr_head];\n"
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
    # Session 4 Fix 7: Extended fade-to-black (1.5s) and audio fade (2.5s) for clean ending
    fade_v_start = max(0, total_dur - 1.5)
    fade_a_start = max(0, total_dur - 2.5)
    fg += (f"[wr_railed]fade=t=out:st={fade_v_start:.2f}:d=1.5:color=0x0A0A0F,"
           f"format=yuv420p[outv];\n")
    fg += (f"[_wr_a_out]afade=t=out:st={fade_a_start:.2f}:d=2.5[_wr_a_faded];\n")

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX wrap",
                       audio_pad="[_wr_a_faded]")


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
                            social_posts: list = None,
                            pip_video_path: str = "") -> str:
    """Route to appropriate BV2 scene function based on segment type and position.

    Falls back to make_host_visual if BV2 scene fails.
    """
    seg_type = segment_data.get("type", "")
    text = segment_data.get("text", "")
    headline = segment_data.get("headline") or segment_data.get("title") or _smart_headline(text)
    speaker = segment_data.get("speaker", "DEBORAH")  # dual host — Deborah (HOST_1) + Mark (HOST_2)
    scene = select_scene_type(seg_type, segment_index, total_segments)

    try:
        if scene == "cold_open":
            return make_cold_open_scene(
                audio_path, headline, text, "REDLINE",
                output_path, btc_price=btc_price,
            )
        elif scene == "narrator_pip":
            next_speaker = segment_data.get("next_speaker", "")
            return make_narrator_pip_scene(
                audio_path, headline, text, speaker, next_speaker,
                thumbnail_path, output_path, btc_price=btc_price,
                pip_video_path=pip_video_path,  # FIX 1: pass actual video
            )
        elif scene == "partner_clip" and clip_path:
            return make_partner_clip_scene(
                clip_path, audio_path, speaker, headline,
                output_path, btc_price=btc_price,
            )
        elif scene == "data_segment":
            metrics = segment_data.get("metrics", [])
            return make_data_segment_scene(
                audio_path, headline, metrics,
                output_path, btc_price=btc_price,
            )
        elif scene == "social_stack":
            return make_social_stack_scene(
                audio_path, headline, social_posts or [],
                output_path, btc_price=btc_price,
            )
        elif scene == "wrap":
            return make_wrap_scene(
                audio_path, headline, text,
                output_path, btc_price=btc_price,
            )

        # Signal Active 60/40 layout — triggered when signal_content injected
        signal_data = segment_data.get("signal_content")
        if signal_data and headline.upper().startswith("SIGNAL"):
            return make_signal_active_scene(
                audio_path, signal_data, output_path, btc_price=btc_price,
            )
    except Exception as e:
        logger.warning(f"BV2 scene '{scene}' failed: {e} — falling back to make_host_visual")

    # Fallback to Black Diamond host visual
    result = make_host_visual(
        audio_path, host_num, text, output_path,
        btc_price=btc_price, label="bv2_fallback_{}".format(seg_type),
        thumbnail_path=thumbnail_path, segment_type=seg_type,
    )
    # HARD SAFETY NET: if output still missing/empty, generate solid bg+audio
    if not result or not os.path.exists(result):
        logger.error("make_host_visual also failed -- generating emergency bg clip")
        try:
            dur = ffprobe_duration(audio_path) or 10.0
            run_ffmpeg([
                "-f", "lavfi", "-i",
                "color=c=0x0A0A0F:s=1920x1080:d={:.3f}:r=30".format(dur),
                "-i", audio_path,
                "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                "-t", "{:.3f}".format(dur), output_path
            ], "emergency bg clip", 60)
            result = output_path if os.path.exists(output_path) else ""
        except Exception as _e:
            logger.error("Emergency clip also failed: %s", _e)
    return result


# ══════════════════════════════════════════════════════════════════════════
# SIGNAL ACTIVE — 60/40 split layout (X Spaces left, Nostr right)
# ══════════════════════════════════════════════════════════════════════════

COLOR_GOLD    = "0xf8c15c"
COLOR_NOSTR   = "0x00ff9d"
COLOR_SIG_RED = "0xff3b5f"

def make_signal_active_scene(audio_path: str, signal_content: dict,
                              output_path: str, btc_price: str = "N/A") -> str:
    """Render Signal Active segment with 60/40 split: X Spaces left, Nostr right.

    Left 60% (x=60-1140): X SPACES LIVE header in gold
    Right 40% (x=1160-1860): NOSTR SIGNAL header in green
    Cards stagger in at 0s/6s/12s per column.
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 15
    total_dur = audio_dur + 0.3

    spaces = signal_content.get("spaces_quotes", [])[:3]
    nostr = signal_content.get("nostr_posts", [])[:3]

    # Issue 13: If both sources empty, show clean placeholder instead of debug text
    if not spaces and not nostr:
        logger.info("Signal Active: no spaces/nostr data — showing SIGNAL COLLECTING placeholder")

    safe_btc = btc_price.replace("'", "").replace('"', "")

    inputs = [audio_path]

    # Procedural dark background
    _, bg_fg = _build_black_diamond_bg(total_dur, label_out="sig_bg")
    fg = bg_fg

    # ── R26 UPGRADE 2: HEADER BAR — left-aligned terminal header ──
    import datetime as _dt_sig
    _utc_ts = _dt_sig.datetime.utcnow().strftime("%H\\:%M UTC")
    fg += (f"[sig_bg]drawbox=x=0:y=0:w=1920:h=72:color=0x050505@0.97:t=fill,"
           f"drawbox=x=0:y=70:w=1920:h=2:color={COLOR_SIG_RED}@0.8:t=fill,"
           # Red dot
           f"drawbox=x=60:y=22:w=14:h=14:color={COLOR_SIG_RED}:t=fill,"
           # LIVE text
           f"drawtext=fontfile={FONT_MONO}:text='LIVE':"
           f"fontcolor={COLOR_SIG_RED}:fontsize=18:x=84:y=14,"
           # SIGNAL ACTIVE
           f"drawtext=fontfile={FONT_BOLD}:text='SIGNAL ACTIVE':"
           f"fontcolor={COLOR_WHITE}:fontsize=38:x=150:y=8,"
           # UTC timestamp top-right
           f"drawtext=fontfile={FONT_MONO}:text='{_utc_ts}':"
           f"fontcolor={COLOR_GOLD}:fontsize=16:x=w-tw-40:y=14"
           f"[sig_hdr];\n")

    # ── R26 UPGRADE 4: COLUMN HEADERS with sub-labels ──
    fg += (f"[sig_hdr]"
           f"drawtext=fontfile={FONT_BOLD}:text='X SPACES LIVE':"
           f"fontcolor={COLOR_GOLD}:fontsize=28:x=60:y=84,"
           # Sub-label: TRANSCRIBING... in gold 13px
           f"drawtext=fontfile={FONT_MONO}:text='TRANSCRIBING...':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=60:y=116,"
           f"drawtext=fontfile={FONT_BOLD}:text='NOSTR SIGNAL':"
           f"fontcolor={COLOR_NOSTR}:fontsize=28:x=1160:y=84,"
           # Sub-label: RELAY CONNECTED in green 13px
           f"drawtext=fontfile={FONT_MONO}:text='RELAY CONNECTED':"
           f"fontcolor={COLOR_NOSTR}:fontsize=13:x=1160:y=116"
           f"[sig_cols];\n")

    last_label = "sig_cols"

    # ── LEFT COLUMN: X SPACES (x=60..1140, width=1080) ──
    for idx, quote in enumerate(spaces):
        card_y = 150 + idx * 280
        card_h = 260
        card_w = 1080
        card_x = 60

        text_raw = quote.get("text", "")
        title = quote.get("space_title", "X Spaces")
        text_safe = _sanitize_text(text_raw)
        title_safe = _sanitize_text(title)
        wrapped = _word_wrap(text_safe, max_width=60, max_lines=4)

        enable_t = idx * 6  # stagger: 0s, 6s, 12s
        enable = f"enable='between(t,{enable_t},{total_dur:.1f})'"

        # R26: FETCHED source at card bottom
        space_source = _sanitize_text(quote.get("source", "X Spaces"))
        fetched_spaces = f"FETCHED {space_source}"

        out_label = f"sc{idx}"
        fg += (f"[{last_label}]"
               # Card background
               f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
               f"color=0x0a0a0a@0.85:t=fill:{enable},"
               # 1px gold border
               f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
               f"color={COLOR_GOLD}@0.6:t=1:{enable},"
               # Space title
               f"drawtext=fontfile={FONT_BOLD}:"
               f"text='{title_safe}':"
               f"fontcolor={COLOR_GOLD}:fontsize=20:x={card_x + 16}:y={card_y + 14}:{enable},"
               # Quote text
               f"drawtext=fontfile={FONT_MONO}:"
               f"text='{wrapped}':"
               f"fontcolor=0xe8e8e8:fontsize=26:x={card_x + 16}:y={card_y + 50}:"
               f"line_spacing=8:{enable},"
               # R26: FETCHED source at card bottom
               f"drawtext=fontfile={FONT_MONO}:"
               f"text='{fetched_spaces}':"
               f"fontcolor={COLOR_MUTED2}:fontsize=10:x={card_x + 16}:y={card_y + card_h - 20}:{enable}"
               f"[{out_label}];\n")
        last_label = out_label

    # ── R26 UPGRADE 4: RIGHT COLUMN: NOSTR (x=1160..1860, width=700) ──
    for idx, post in enumerate(nostr):
        card_y = 150 + idx * 280
        card_h = 260
        card_w = 700
        card_x = 1160

        text_raw = post.get("text", "")
        # R26: Primary identity = nip05 if available, else truncated pubkey
        nip05 = post.get("nip05", "")
        display_name = nip05 if nip05 else (post.get("display_name") or post.get("pubkey", "")[:16])
        text_safe = _sanitize_text(text_raw)
        name_safe = _sanitize_text(display_name)
        wrapped = _word_wrap(text_safe, max_width=38, max_lines=4)

        enable_t = idx * 6
        enable = f"enable='between(t,{enable_t},{total_dur:.1f})'"

        # R26: ZAP+amount+sats in gold if zap_amount present
        zap_indicator = ""
        zap_amount = post.get("zap_amount", 0)
        if zap_amount:
            zap_indicator = (
                f"drawtext=fontfile={FONT_BOLD}:text='ZAP {zap_amount} sats':"
                f"fontcolor={COLOR_GOLD}:fontsize=14:x={card_x + card_w - 160}:y={card_y + 14}:{enable},"
            )
        elif post.get("has_zap"):
            zap_indicator = (
                f"drawtext=fontfile={FONT_BOLD}:text='ZAP':"
                f"fontcolor={COLOR_GOLD}:fontsize=14:x={card_x + card_w - 60}:y={card_y + 14}:{enable},"
            )

        # R26: FETCHED source at card bottom
        fetch_source = _sanitize_text(post.get("source", "relay"))
        fetched_text = f"FETCHED {fetch_source}"

        out_label = f"nc{idx}"
        fg += (f"[{last_label}]"
               # Card background
               f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
               f"color=0x0a0a0a@0.85:t=fill:{enable},"
               # 1px green border
               f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
               f"color={COLOR_NOSTR}@0.6:t=1:{enable},"
               # Display name (nip05 or pubkey)
               f"drawtext=fontfile={FONT_MONO}:"
               f"text='{name_safe}':"
               f"fontcolor={COLOR_NOSTR}:fontsize=18:x={card_x + 16}:y={card_y + 14}:{enable},"
               # Zap indicator
               f"{zap_indicator}"
               # Post text
               f"drawtext=fontfile={FONT_MONO}:"
               f"text='{wrapped}':"
               f"fontcolor=0xe8e8e8:fontsize=26:x={card_x + 16}:y={card_y + 50}:"
               f"line_spacing=8:{enable},"
               # R26: FETCHED source at card bottom
               f"drawtext=fontfile={FONT_MONO}:"
               f"text='{fetched_text}':"
               f"fontcolor={COLOR_MUTED2}:fontsize=10:x={card_x + 16}:y={card_y + card_h - 20}:{enable}"
               f"[{out_label}];\n")
        last_label = out_label

    # ── R25 FIX 4: SPONSOR STRIP (replaces leaked EPISODE SEGMENTS) ──
    sponsors = ["MEANWHILE", "CURATED MINING", "PROTOCOL PULSE"]
    sponsor_w = 1800 // len(sponsors)
    fg += (f"[{last_label}]drawbox=x=60:y=990:w=1800:h=50:color=0x050505@0.85:t=fill,"
           f"drawbox=x=60:y=990:w=1800:h=1:color={COLOR_RED}@0.4:t=fill")
    for si, sp in enumerate(sponsors):
        sx = 60 + si * sponsor_w + sponsor_w // 2
        sep = f",drawbox=x={60 + (si+1)*sponsor_w}:y=995:w=1:h=40:color={COLOR_MUTED2}@0.5:t=fill" if si < len(sponsors) - 1 else ""
        fg += (f",drawtext=fontfile={FONT_MONO}:text='{sp}':"
               f"fontcolor={COLOR_MUTED}:fontsize=12:x={sx}-(text_w/2):y=1008{sep}")
    fg += f"[sig_sponsored];\n"

    # ── R26 UPGRADE 3: WAVEFORM BOTTOM BAND at y=880 ──
    fg += (f"[0:a]showwavespic=s=1800x120:colors=ff3b5f[_sig_wave_pic];\n"
           f"[_sig_wave_pic]format=rgba,colorchannelmixer=aa=0.4[_sig_wave_alpha];\n"
           f"[sig_sponsored][_sig_wave_alpha]overlay=60:880[sig_waved];\n")

    # ── CORNER BRACKETS ──
    fg += _build_corner_brackets_fg("sig_waved", "sig_cornered")

    # ── TICKER BAR ──
    fg += _build_info_bar_fg(total_dur, btc_price, label_in="sig_cornered", label_out="sig_final")

    # ── R26 UPGRADE 1: CRT SCANLINE ──
    fg = apply_scanline(inputs, fg, "sig_final", "sig_scanned", total_dur)

    fg += f"[sig_scanned]format=yuv420p[outv];\n"

    # Audio
    fg += (f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,"
           f"alimiter=limit=0.85:level=disabled:attack=5:release=50[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "signal_active_60_40", 600,
    )

    if ok:
        logger.info("R25 FIX 4: Signal Active 60/40 rendered (no EPISODE SEGMENTS, sponsor strip added): %s", output_path)
        return output_path

    logger.error("Signal Active 60/40 render failed — falling back to host visual")
    return ""


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

    speaker = "PBX"  # Render22: PBX solo mode — single host

    safe_btc = btc_price.replace("'", "").replace('"', "")

    is_social = segment_type == "social_segment"

    # Eyebrow / headline logic by segment_type
    seg_map = {
        "cold_open": ("COLD OPEN // BREAKING SIGNAL", "SIGNAL", "DETECTED"),
        "setup":     (f"ANALYST // {speaker}", speaker[:6], "REPORTING"),
        "react":     (f"REACTION // {speaker}", speaker[:6], "REACTS"),
        "wrap":      (f"CLOSING // {speaker}", speaker[:6], "CONFIRMED"),
        "x_spaces":  ("◆ X SPACES // LIVE INTEL", "SPACES", "LIVE"),
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
           # render11 FIX 4: +16px gap from PROTOCOL PULSE text end
           f"drawtext=fontfile={FONT_BOLD}:text='LIVE':"
           f"fontcolor={COLOR_RED}:fontsize=22:x=296:y=26,"
           f"drawtext=fontfile={FONT_BOLD}:text='|':"
           f"fontcolor={COLOR_MUTED}:fontsize=28:x=340:y=22,"
           f"drawbox=x=0:y=0:w=0:h=0:color=0x000000@0:t=fill"
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

    # Body text (wrapped subtitle) — Issue 13: filter out debug/internal text
    _debug_patterns = {"COLD OPEN", "COLD_OPEN", "SETUP", "REACT", "BRIDGE", "WRAP", "DATA", "SOCIAL"}
    safe_sub = _sanitize_text(text) if text else ""
    if safe_sub and safe_sub.strip().upper() in _debug_patterns:
        safe_sub = ""  # suppress internal segment type labels
    if safe_sub:
        wrapped_sub = _word_wrap(safe_sub, max_width=40, max_lines=3)
        fg += (f"[ldiv]drawtext=fontfile={FONT_MONO}:"
               f"text='{wrapped_sub}':"
               f"fontcolor=0xBBBBBB:fontsize=20:x=24:y=374:line_spacing=6"
               f"[lbody];\n")
    else:
        fg += f"[ldiv]copy[lbody];\n"

    # R25 FIX 5: All 5 live metrics in left panel for narrator segments
    _lm_btc = _sanitize_text(safe_btc)
    _lm_hashrate = _sanitize_text(_get_live_metric("hashrate", "850 EH/s"))
    _lm_mempool = _sanitize_text(_get_live_metric("mempool_fee", "12 sat/vB"))
    _lm_etf = _sanitize_text(_get_live_metric("etf_flow", "$340M"))
    _lm_dominance = _sanitize_text(_get_live_metric("dominance", "61.4 pct"))
    _metrics_5 = [
        ("BTC", _lm_btc, COLOR_WHITE),
        ("HASHRATE", _lm_hashrate, COLOR_GREEN),
        ("MEMPOOL", _lm_mempool, COLOR_CORAL),
        ("ETF FLOW", _lm_etf, COLOR_GREEN),
        ("DOMINANCE", _lm_dominance, COLOR_WHITE),
    ]
    _m5_y = 480
    _m5_last = "lbody"
    for _mi, (_ml, _mv, _mc) in enumerate(_metrics_5):
        _m5_row_y = _m5_y + _mi * 28
        _m5_out = f"lm5_{_mi}"
        fg += (f"[{_m5_last}]drawtext=fontfile={FONT_MONO}:text='{_ml}':"
               f"fontcolor={COLOR_MUTED}:fontsize=11:x=24:y={_m5_row_y},"
               f"drawtext=fontfile={FONT_BOLD}:text='{_mv}':"
               f"fontcolor={_mc}:fontsize=14:x=140:y={_m5_row_y}"
               f"[{_m5_out}];\n")
        _m5_last = _m5_out

    # CTA box
    fg += (f"[{_m5_last}]drawbox=x=20:y=640:w=440:h=52:color={COLOR_RED_DIM}@0.95:t=fill,"
           f"drawbox=x=20:y=640:w=4:h=52:color={COLOR_RED}:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:"
           f"text='  DUAL-HOST ANALYSIS // INCOMING':"
           f"fontcolor={COLOR_RED}:fontsize=13:x=34:y=660"
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

    # Render22 FIX 6: Live metrics panels (HASHRATE, MEMPOOL, DOMINANCE)
    _live_hashrate = _get_live_metric("hashrate", "N/A").replace("'", "")
    _live_mempool = _get_live_metric("mempool_fee", "N/A").replace("'", "")
    _live_dominance = _get_live_metric("btc_dominance", "N/A").replace("'", "")
    fg += (f"[dp1]drawbox=x=1120:y=502:w=300:h=150:color={COLOR_PANEL}@0.95:t=fill,"
           f"drawbox=x=1120:y=502:w=300:h=2:color={COLOR_RED}@0.5:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='HASHRATE':"
           f"fontcolor={COLOR_MUTED}:fontsize=12:x=1136:y=517,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_live_hashrate}':"
           f"fontcolor={COLOR_WHITE}:fontsize=36:x=1136:y=535,"
           f"drawtext=fontfile={FONT_MONO}:text='MEMPOOL FEE':"
           f"fontcolor={COLOR_MUTED}:fontsize=12:x=1136:y=576,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_live_mempool}':"
           f"fontcolor={COLOR_GREEN}:fontsize=18:x=1136:y=592"
           f"[dp2];\n")

    fg += (f"[dp2]drawbox=x=1430:y=502:w=280:h=150:color={COLOR_PANEL}@0.95:t=fill,"
           f"drawbox=x=1430:y=502:w=280:h=2:color={COLOR_RED}@0.5:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='BTC DOMINANCE':"
           f"fontcolor={COLOR_MUTED}:fontsize=11:x=1446:y=514,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_live_dominance}':"
           f"fontcolor={COLOR_WHITE}:fontsize=36:x=1446:y=535"
           f"[dp3];\n")
    fg += (f"[0:a]showwaves=s=250x60:mode=line:"
           f"colors={COLOR_RED}:scale=lin:rate=30[amp_wave];\n")
    fg += f"[dp3][amp_wave]overlay=1440:570[dp_done];\n"

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
    fg += (f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,alimiter=limit=0.85:level=disabled:attack=5:release=50[outa]")

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


def trim_to_sentence(text: str, max_chars: int = 400) -> str:
    """Trim text at the last sentence boundary before max_chars."""
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    matches = list(re.finditer(r'[.!?](?:\s|$)', chunk))
    if matches:
        last = matches[-1]
        return text[:last.end()].strip()
    # No sentence boundary — trim at last word boundary
    last_space = chunk.rfind(' ')
    return (text[:last_space] if last_space > 0 else chunk).strip()


def _smart_headline(text: str, max_len: int = 90) -> str:
    """Render21 FIX 6: Never truncate headlines. Return full text up to max_len."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > max_len // 2:
        return truncated[:last_space]
    return truncated


def _split_headline_for_render(headline: str, max_line_chars: int = 45):
    """Render21 FIX 6: Split headline into 2 lines if >45 chars. Returns (line1, line2)."""
    if len(headline) <= max_line_chars:
        return (headline, "")
    # Split at last space before char 45
    split_at = headline[:max_line_chars].rfind(" ")
    if split_at < max_line_chars // 2:
        split_at = max_line_chars
    return (headline[:split_at].strip(), headline[split_at:].strip())


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

    # FIX 4: explicit stereo format before loudnorm/aresample to prevent channel layout error
    fg += f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,alimiter=limit=0.85:level=disabled:attack=5:release=50[outa]"

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
    Render24 FIX 3: Skip if filename contains xfade or transition (already has swoosh).
    """
    if not os.path.exists(CARD_SWOOSH) or not os.path.exists(video_path):
        return video_path
    # FIX 3: Prevent double whoosh on xfade/transition segments
    basename = os.path.basename(video_path).lower()
    if "xfade" in basename or "transition" in basename:
        logger.info(f"  FIX 3: Skipping swoosh — filename has xfade/transition: {basename}")
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
    # Session 4 Fix 1: Title card suppressed — kills momentum with 8s dead air
    logger.info("Title card suppressed — per PIPELINE_LAWS session 4")
    return ""
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


def _make_remotion_intel_panel(duration_frames: int = 300,
                               btc_price: str = "N/A") -> str:
    """Session 4 Fix 6: Render IntelPanel overlay via Remotion.

    Reads narrative_context.json for live data. Returns path to rendered
    transparent overlay video, or '' on failure.
    """
    if not _remotion_enabled():
        return ""

    # Read narrative context
    import json as _json, datetime as _dt
    _intel_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "intelligence")
    _nc_path = os.path.join(_intel_dir, "narrative_context.json")

    narrative = "Bitcoin Sound Money"
    market_mood = "NEUTRAL"
    quote_text = ""
    quote_handle = ""

    try:
        with open(_nc_path) as f:
            nc = _json.load(f)
        computed = nc.get("computed_at", "")
        if computed:
            age = (_dt.datetime.now(_dt.timezone.utc) -
                   _dt.datetime.fromisoformat(computed)).total_seconds() / 3600
            if age < 12:
                narrative = nc.get("dominant_narrative", narrative)[:42]
                market_mood = nc.get("market_mood", "neutral").upper().replace("_", " ")[:16]
                hint = nc.get("eryn_intro_hook", "")
                if "'" in hint:
                    qs = hint.find("'") + 1
                    qe = hint.find("'", qs)
                    if qe > qs:
                        quote_text = hint[qs:qe][:70]
                tl = nc.get("thought_leaders_mentioned", [])
                quote_handle = ("@" + tl[0][:18]) if tl else ""
    except Exception:
        pass

    import hashlib
    props_hash = hashlib.md5(f"{btc_price}{narrative}{market_mood}".encode()).hexdigest()[:8]
    out_path = os.path.join(tempfile.gettempdir(), f"intel_panel_{props_hash}.mp4")

    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        return out_path  # cached

    result = _render_remotion("IntelPanel", out_path, props={
        "btcPrice": btc_price,
        "narrative": narrative,
        "marketMood": market_mood,
        "quoteText": quote_text,
        "quoteHandle": quote_handle,
        "durationInFrames": duration_frames,
    }, timeout=120)

    if result:
        logger.info(f"  Remotion IntelPanel rendered: {narrative} / {market_mood}")
    return result or ""


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


def make_transition_visual(output_path: str, duration: float = 2.2) -> str:
    """R25 FIX 2: Instant 0.06s black frame + whoosh SFX only.

    No visual overlay — just a flash-cut black frame with whoosh sound.
    This creates snappy broadcast-style transitions without visual clutter.
    """
    duration = 0.06  # R25: instant black flash
    has_whoosh = os.path.exists(GLITCH_WHOOSH)

    if has_whoosh:
        # 0.06s black + whoosh (whoosh extends slightly for audibility)
        whoosh_dur = 0.5  # whoosh needs ~0.5s to be heard
        ok = run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c={COLOR_BG}:s=1920x1080:d={whoosh_dur}:r=30",
            "-i", GLITCH_WHOOSH,
            "-filter_complex",
            f"[1:a]atrim=0:{whoosh_dur},asetpts=PTS-STARTPTS,volume=2.5,"
            f"afade=t=out:st=0.3:d=0.2,alimiter=limit=0.95[outa]",
            "-map", "0:v", "-map", "[outa]",
            "-t", str(whoosh_dur),
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
            output_path,
        ], "R25 instant black + whoosh", 30)
    else:
        ok = run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c={COLOR_BG}:s=1920x1080:d={duration}:r=30",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", str(duration),
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
            output_path,
        ], "R25 instant black (silent)", 30)
    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        logger.info(f"  R25 TRANSITION: instant black + whoosh ({dur:.2f}s)")
        return output_path
    return ""


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
        # Render14: removed atrim=start=2.5 (was root cause of lipsync desync)
        f"[0:a]aresample=async=1,asetpts=PTS-STARTPTS,"
        f"highpass=f=50,lowpass=f=15000,"
        f"afade=t=in:d=0.5,afade=t=out:st={max(0, fade_out_start - 0.5)}:d=0.5[outa]"
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
         "-af", "aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,loudnorm=I=-14:TP=-3.0:LRA=7,aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,alimiter=level_in=1:level_out=0.794:limit=0.708:attack=3:release=30",
         output_path],
        "normalize", 180,
    )
    return output_path if (ok and os.path.exists(output_path)) else part_path


def concatenate_parts(parts: list, output_path: str,
                       intro_music_duration: float = 0,
                       skip_outro_fade: bool = False) -> str:
    """FIX 1+8+12: Concat video parts with fade transitions (no black frames).

    Uses concat demuxer with fade-in/fade-out on each part for smooth transitions.
    No standalone glitch transition clips. Final loudnorm with LRA=7 (FIX 12).

    Args:
        intro_music_duration: Total play time of intro_music.mp3 including 3s fade.
            Mixed from t=0 at -18dB. 0 = no intro music.
        skip_outro_fade: If True, last part is branded outro — no extended fade,
            BGM fades out before it, no additional music on outro.
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
        fade_out_start = max(0, dur - 0.05)
        # Render11 FIX 2: Reduce fades on narration parts to eliminate audible pauses
        # Render18 FIX 2: Further tightened narrator fades 0.05→0.03s to kill dead air gaps
        pbase_norm = os.path.basename(p).lower()
        is_clip_part = "clip_r" in pbase_norm or ("clip_" in pbase_norm and "partner" not in pbase_norm)
        v_fade = 0.15 if is_clip_part else 0.03
        a_fade_in = 0.15 if is_clip_part else 0.03
        a_fade_out = 0.3 if is_clip_part else 0.03
        fade_out_start_v = max(0, dur - v_fade)
        ok = run_ffmpeg(
            ["-i", p,
             "-c:v", "libx264", "-crf", "17", "-preset", "medium",
             "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
             "-r", "30", "-vsync", "cfr",
             "-vf", f"scale=1920:1080,setsar=1,format=yuv420p,fade=t=in:d={v_fade},fade=t=out:st={fade_out_start_v}:d={v_fade}",
             "-video_track_timescale", "90000",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
             "-af", f"aresample=async=1,afade=t=in:d={a_fade_in},afade=t=out:st={max(0, dur - a_fade_out - 0.05)}:d={a_fade_out}",
             tmp],
            "normalize+fade", 180,
        )
        chosen = tmp if (ok and os.path.exists(tmp)) else p
        # BLACK HOLE GUARD (FIX 3): scan for >0.5s of black mid-part, re-render or replace
        # Lowered from d=1 to d=0.5 to catch 1.9s black frames from failed PiP composites
        try:
            bd = subprocess.run(
                ["ffmpeg", "-i", chosen,
                 "-vf", "blackdetect=d=0.5:pix_th=0.02",
                 "-an", "-f", "null", "-"],
                capture_output=True, text=True, timeout=60
            )
            import re as _re_bd
            black_segments = _re_bd.findall(
                r"black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)",
                bd.stderr
            )
            part_dur = ffprobe_duration(chosen)
            # Filter: only count black segments that are mid-part (not at start/end edges)
            mid_black = [
                (float(bs), float(be), float(bd_val))
                for bs, be, bd_val in black_segments
                if float(bs) > 0.2 and float(be) < part_dur - 0.2 and float(bd_val) > 0.5
            ]
            if mid_black:
                total_mid_black = sum(d for _, _, d in mid_black)
                logger.warning("BLACK HOLE part %d: %.1fs mid-part black (%d segments) -- replacing with bg-only",
                               i, total_mid_black, len(mid_black))
                bg_only = chosen + ".bgonly.mp4"
                # Use bg_loop as fallback video (not pure black) + preserve original audio
                _bg_loop = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "bg_loop.mp4")
                if os.path.exists(_bg_loop):
                    _fc = "[0:v]scale=1920:1080,setsar=1,setpts=PTS-STARTPTS,eq=brightness=-0.15:contrast=0.9[outv]"
                    run_ffmpeg([
                        "-stream_loop", "-1",
                        "-t", "{:.3f}".format(part_dur),
                        "-i", _bg_loop,
                        "-i", chosen,
                        "-filter_complex", _fc,
                        "-map", "[outv]", "-map", "1:a?",
                        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                        "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                        "-t", "{:.3f}".format(part_dur), bg_only
                    ], "bg-loop fallback {}".format(i), 60)
                else:
                    run_ffmpeg([
                        "-f", "lavfi", "-i",
                        "color=c=0x06070b:s=1920x1080:d={:.3f}:r=30".format(part_dur),
                        "-i", chosen,
                        "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                        "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                        "-t", "{:.3f}".format(part_dur), bg_only
                    ], "bg-only fallback {}".format(i), 60)
                if os.path.exists(bg_only):
                    chosen = bg_only
        except Exception as _bh_err:
            logger.warning("Black hole check failed: %s", _bh_err)
        normalized.append(chosen)

    # Session 4 Fix 7B: Re-apply longer fade to last part (outro) for clean ending
    # Skip if branded outro (skip_outro_fade) — it has its own audio and hard-cuts
    if len(normalized) >= 2 and not skip_outro_fade:
        last_part = normalized[-1]
        last_dur = ffprobe_duration(last_part)
        if last_dur > 2.0:
            last_refaded = last_part + ".refaded.mp4"
            fade_v_start = max(0, last_dur - 1.5)
            fade_a_start = max(0, last_dur - 2.5)
            ok_refade = run_ffmpeg(
                ["-i", last_part,
                 "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                 "-b:v", "8M", "-r", "30", "-vsync", "cfr",
                 "-vf", f"scale=1920:1080,setsar=1,format=yuv420p,fade=t=in:d=0.15,fade=t=out:st={fade_v_start:.2f}:d=1.5:color=0x0A0A0F",
                 "-video_track_timescale", "90000",
                 "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                 "-af", f"aresample=async=1,afade=t=in:d=0.1,afade=t=out:st={fade_a_start:.2f}:d=2.5",
                 last_refaded],
                "outro extended fade", 180,
            )
            if ok_refade and os.path.exists(last_refaded):
                normalized[-1] = last_refaded
                logger.info(f"  Fix 7B: Extended outro fade applied (1.5s video, 2.5s audio)")

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

    # APEX V2 FIX 2: Continuous BGM — infinite loop, duration=longest, no gaps
    # BGM loops infinitely via -stream_loop -1, trimmed to episode+5s safety buffer.
    # amix duration=longest ensures BGM never cuts short at clip boundaries.
    # FIX 1+4: Volume envelope ducks BGM to -28dB during partner clips, -24dB during PiP narration
    from music import ffprobe_duration as _music_ffprobe_dur
    has_bgm = os.path.exists(BG_MUSIC)
    if has_bgm:
        dur = _music_ffprobe_dur(concat_raw)
        if dur > 0:
            # If branded outro, fade BGM out before outro starts
            if skip_outro_fade and valid:
                outro_dur_est = ffprobe_duration(valid[-1])
                bgm_fade_st = max(0, dur - outro_dur_est - 3.0)
            else:
                bgm_fade_st = max(0, dur - 3.0)

            # FIX 5 (render10): Build volume envelope — duck during clip segments
            # clip_r parts → 0.02 (-34dB), default → 0.10 (-20dB)
            cumulative_t = 0.0
            vol_clauses = []
            for p in valid:
                pdur = ffprobe_duration(p)
                pbase = os.path.basename(p).lower()
                t_start = cumulative_t
                t_end = cumulative_t + pdur
                cumulative_t = t_end
                if "clip_r" in pbase or "clip_" in pbase and "partner" not in pbase:
                    # Partner clips: duck to 0.02 (-34dB) — let clip audio breathe
                    vol_clauses.append(f"between(t,{t_start:.3f},{t_end:.3f})*0.02")
            if vol_clauses:
                # R25 FIX 8: BGM at -14dB (0.2) for narrator segments, ducked during clips
                vol_expr = "volume='if(" + "+".join(f"({vc})" for vc in vol_clauses) + ",1,0.2)':eval=frame"
                bgm_vol_filter = f"{vol_expr},afade=t=in:d=2.0,afade=t=out:st={bgm_fade_st}:d=3.0"
            else:
                bgm_vol_filter = f"volume=0.2,afade=t=in:d=2.0,afade=t=out:st={bgm_fade_st}:d=3.0"

            music_mixed = output_path + ".music_mixed.mp4"
            ok_music = run_ffmpeg([
                "-fflags", "+genpts",
                "-i", concat_raw,
                "-stream_loop", "-1", "-i", BG_MUSIC,
                "-filter_complex", (
                    # BGM infinite loop: stream_loop=-1 loops the file forever.
                    # atrim cuts it to episode duration + 5s safety buffer.
                    # amix duration=longest so BGM NEVER drops at segment boundaries.
                    # Sidechain compress ducks BGM under TTS (narration segments).
                    # FIX 1: Volume envelope ducks to -28dB during partner clips.
                    f"[0:a]asetpts=PTS-STARTPTS,asplit[tts_main][tts_sc];"
                    f"[1:a]atrim=0:{dur + 5.0},asetpts=PTS-STARTPTS,"
                    f"{bgm_vol_filter}[bgm_raw];"
                    f"[bgm_raw][tts_sc]sidechaincompress="
                    f"threshold=0.02:ratio=8:attack=3:release=150[bgm_ducked];"
                    f"[tts_main][bgm_ducked]amix=inputs=2:duration=longest"
                    f":weights=1 0.04[mixed_audio];"
                    f"[mixed_audio]aresample=async=1[outa]"
                ),
                "-map", "0:v", "-map", "[outa]",
                # BUG2 FIX: Full libx264 re-encode (not -c:v copy) to reset PTS for AV sync
                "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                "-r", "30", "-vsync", "cfr",
                "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                "-t", str(dur),
                music_mixed
            ], "continuous bgm mix (infinite loop)", 600)
            if ok_music and os.path.exists(music_mixed):
                logger.info(f"  APEX V2: Continuous BGM mixed — infinite loop ({dur:.1f}s episode)")
                concat_raw = music_mixed
            else:
                logger.warning("  APEX V2: BGM mix failed — proceeding without music")
    else:
        logger.warning("  APEX V2: No BG_MUSIC file found — no music bed")

    # Round 3 FIX 4: Skip intro_music.mp3 if intro_tag.mp4 was used (it has baked-in audio)
    skip_intro_music = os.path.exists(INTRO_TAG) and any(
        "intro_tag" in os.path.basename(p).lower() for p in valid
    )
    if skip_intro_music:
        logger.info("  FIX 4: Skipping intro_music.mp3 — intro_tag.mp4 has baked-in audio")

    # Intro music underlay: plays from t=0 for intro_music_duration, fades out over 3s
    if intro_music_duration > 0 and os.path.exists(INTRO_MUSIC_FILE) and not skip_intro_music:
        ep_dur = ffprobe_duration(concat_raw)
        if ep_dur > 0:
            intro_mus_mixed = output_path + ".intro_mus.mp4"
            im_fade_start = max(0, intro_music_duration - 3.0)
            ok_im = run_ffmpeg([
                "-i", concat_raw,
                "-stream_loop", "-1", "-i", INTRO_MUSIC_FILE,
                "-filter_complex",
                (f"[1:a]volume=0.40,atrim=0:8.0,"
                 f"asetpts=PTS-STARTPTS,"
                 f"afade=t=out:st=6.0:d=2.0,aresample=48000[im];"
                 f"[0:a][im]amix=inputs=2:duration=first:weights=1 1[outa]"),
                "-map", "0:v", "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                intro_mus_mixed,
            ], "intro music underlay", 300)
            if ok_im and os.path.exists(intro_mus_mixed):
                logger.info(f"  Intro music mixed: {intro_music_duration:.1f}s play, fade at {im_fade_start:.1f}s")
                concat_raw = intro_mus_mixed
            else:
                logger.warning("  Intro music mix failed — continuing without")

    # Round 3 FIX 7: bg_loop ambient audio — RAISED to -18dB during transitions (was -25dB)
    if os.path.exists(BG_LOOP):
        ep_dur = ffprobe_duration(concat_raw)
        if ep_dur > 0:
            bgl_mixed = output_path + ".bgl_audio.mp4"
            # Build volume envelope: boost bg_loop at clip transitions
            # R25 FIX 8: volume=0.10 (-20dB floor), transitions: volume=0.2 (-14dB), clip boundaries: volume=0.16 (-16dB)
            vol_expr_parts = []
            cumulative = 0.0
            for pidx, p in enumerate(valid):
                pdur = ffprobe_duration(p)
                t_start = cumulative
                cumulative += pdur
                pbase = os.path.basename(p).lower()
                if "transition" in pbase or "glitch" in pbase:
                    # FIX 7: Raise to -18dB for entire transition segment (was -25dB)
                    vol_expr_parts.append(f"between(t,{t_start:.3f},{cumulative:.3f})*0.2")
                elif pidx > 0:
                    # FIX 7: Raise to -16dB for 1.0s around each part boundary (was -20dB/0.5s)
                    vol_expr_parts.append(f"between(t,{max(0,t_start-0.5):.3f},{t_start+0.5:.3f})*0.16")
            if vol_expr_parts:
                # Use volume expr: boosted at transitions, floor 0.10 (-20dB) elsewhere
                vol_filter = "volume='if(" + "+".join(f"({vp})" for vp in vol_expr_parts) + f",1,0.10)':eval=frame"
            else:
                vol_filter = "volume=0.10"
            ok_bgl = run_ffmpeg([
                "-i", concat_raw,
                "-stream_loop", "-1", "-i", BG_LOOP,
                "-filter_complex",
                (f"[1:a]{vol_filter},aresample=48000[bgl];"
                 f"[0:a][bgl]amix=inputs=2:duration=first:weights=1 1[outa]"),
                "-map", "0:v", "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                bgl_mixed,
            ], "bg loop ambience mix (boosted transitions)", 300)
            if ok_bgl and os.path.exists(bgl_mixed):
                logger.info("  BG loop ambient audio mixed (boosted at transitions)")
                concat_raw = bgl_mixed

    # FIX 6: Mix whoosh SFX at transition points between segments
    # FIX 6B: Single input + asplit (was N inputs → ffmpeg filter graph explosion at 30+ parts)
    has_whoosh = os.path.exists(GLITCH_WHOOSH)
    if has_whoosh and len(valid) > 1:
        # Calculate transition timestamps (cumulative durations of each part)
        transition_times = []
        cumulative = 0.0
        for pidx, p in enumerate(valid[:-1]):
            pdur = ffprobe_duration(p)
            cumulative += pdur
            transition_times.append(cumulative)

        # Cap at 20 whooshes — thin out evenly if too many
        MAX_WHOOSH = 20
        if len(transition_times) > MAX_WHOOSH:
            step = len(transition_times) / MAX_WHOOSH
            transition_times = [transition_times[int(i * step)] for i in range(MAX_WHOOSH)]

        if transition_times:
            whoosh_mixed = output_path + ".whoosh_mixed.mp4"
            n = len(transition_times)
            # Single whoosh input → asplit into N copies, delay each, amix together
            split_labels = "".join(f"[ws{i}]" for i in range(n))
            whoosh_fg_parts = [f"[1:a]asplit={n}{split_labels}"]
            for ti, ttime in enumerate(transition_times):
                delay_ms = int(ttime * 1000)
                # Render11 FIX 6: Normalize whoosh to consistent perceived loudness
                # loudnorm ensures every whoosh hits at same level regardless of surrounding audio
                whoosh_fg_parts.append(
                    f"[ws{ti}]volume=2.5,loudnorm=I=-12:TP=-1.0:LRA=3,alimiter=limit=0.9,adelay={delay_ms}|{delay_ms}[whoosh_{ti}]"
                )
            # Amix all whooshes together
            whoosh_labels = "".join(f"[whoosh_{ti}]" for ti in range(n))
            whoosh_fg_parts.append(
                f"{whoosh_labels}amix=inputs={n}:duration=longest[all_whoosh]"
            )
            # Mix whoosh into episode audio
            whoosh_fg_parts.append(
                # FIX 3: Whoosh mix weight raised 0.5→1.0 so whooshes cut through
                f"[0:a][all_whoosh]amix=inputs=2:duration=first:weights=1 1.0[outa]"
            )
            whoosh_fg = ";\n".join(whoosh_fg_parts)

            ok_whoosh = run_ffmpeg(
                ["-fflags", "+genpts", "-i", concat_raw, "-i", GLITCH_WHOOSH,
                 "-filter_complex", whoosh_fg,
                 "-map", "0:v", "-map", "[outa]",
                 "-c:v", "copy",
                 "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                 whoosh_mixed],
                "whoosh SFX mix", 300,
            )
            if ok_whoosh and os.path.exists(whoosh_mixed):
                logger.info(f"  FIX 6B: Whoosh SFX at {n} transitions (single-input asplit)")
                concat_raw = whoosh_mixed
            else:
                logger.warning("  FIX 6B: Whoosh mix failed — proceeding without SFX")

    # Final encode: nuclear PTS reset + AV sync lock + BUG5 single authoritative loudnorm
    # CRF 15 + minrate 3.5M floor to guarantee ≥3.5Mbps output (was CRF 17 → 2.8Mbps on dark content)
    ok = run_ffmpeg(
        ["-fflags", "+genpts+igndts+discardcorrupt",
         "-i", concat_raw,
         "-c:v", "libx264", "-crf", "15", "-preset", "medium",
         "-b:v", "8M", "-minrate", "3.5M", "-maxrate", "10M", "-bufsize", "15M",
         "-r", "30", "-vsync", "cfr",
         "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
         # BUG5 FIX: Single authoritative loudnorm at end (removed from all intermediate steps)
         # FIX 4: adelay=65ms to compensate video PTS 0.066 vs DTS -0.000651 offset (audio leads video)
         "-af", "asetpts=PTS-STARTPTS,aresample=async=1:min_hard_comp=0.1:first_pts=0,loudnorm=I=-14:TP=-3.0:LRA=7:linear=false,alimiter=level_in=1:level_out=0.794:limit=0.794:attack=5:release=50",
         "-avoid_negative_ts", "make_zero",
         "-max_interleave_delta", "0",
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


def should_insert_transition(prev_part: str, next_part: str) -> bool:
    """Render22 FIX 5: Transition logic — returns True ONLY when clip_rank changes
    or transitioning to/from a clip part. Returns False for all narrator-to-narrator
    switches on same topic/screen.

    Args:
        prev_part: previous segment type (e.g. "clip", "setup", "react", "cold_open", "intro", "wrap", "social_segment", "data")
        next_part: next segment type
    Returns:
        True if a transition animation should be inserted between these segments.
    """
    # Always transition into or out of a clip
    if prev_part == "clip" or next_part == "clip":
        return True
    # Transition when moving from react to setup (next clip block)
    if prev_part == "react" and next_part == "setup":
        return True
    # Transition into social or data segments from clip-related segments
    if prev_part in ("react", "clip") and next_part in ("social_segment", "data"):
        return True
    # NO transition for narrator-to-narrator within same flow
    # e.g., setup→setup, react→react, cold_open→setup, data→social_segment
    return False


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

    # Render21 FIX 4: Sync hashrate mentions in dialogue with live data
    live_hr = _get_live_metric("hashrate", "")
    if live_hr:
        _hr_pattern = re.compile(r'\d[\d,]*\s*EH.{0,3}s|\d[\d,]*\s*exahash', re.IGNORECASE)
        for entry in script.get("dialogue", []):
            if "text" in entry and _hr_pattern.search(entry["text"]):
                old_text = entry["text"]
                entry["text"] = _hr_pattern.sub(live_hr, entry["text"])
                if old_text != entry["text"]:
                    logger.info(f"  FIX 4: Hashrate synced in dialogue: {live_hr}")

    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "work")
    os.makedirs(work_dir, exist_ok=True)

    dialogue = script.get("dialogue", [])
    lines = audio_data.get("lines", [])
    parts = []
    part_idx = 0

    # Issue 5 FIX: Use the SAME social_posts list from the script (set by daily_producer).
    tweet_card_posts = []
    social_card_idx = 0

    # R25 FIX 6: Use script social_posts ONLY — no fetcher fallback
    script_social_posts = script.get("social_posts", [])
    if script_social_posts:
        tweet_card_posts = list(script_social_posts)
        for di, dp in enumerate(tweet_card_posts):
            dp["display_order"] = di
        logger.info(f"  R25 FIX 6: SOCIAL ORDER (from script only): {len(tweet_card_posts)} posts")
    else:
        logger.info("  R25 FIX 6: No social_posts in script — skipping tweet cards (no fetcher fallback)")

    if tweet_card_posts:
        tweet_card_posts.sort(key=lambda p: p.get("display_order", 0))
        logger.info(f"  SOCIAL POST ORDER (final):")
        for ti, tp in enumerate(tweet_card_posts):
            logger.info(f"    CARD #{ti}: @{tp.get('handle', '?')} — {tp.get('text', '')[:40]}")

        # Cross-check narrator handles vs card handles
        _social_dialogue = [d for d in dialogue if d.get("type") == "social_segment"
                            and d.get("host") in (1, 2, "1", "2")]
        _narrator_handles = []
        for sd in _social_dialogue:
            for h in re.findall(r'@(\w+)', sd.get("text", "")):
                h_lower = h.lower()
                if h_lower not in _narrator_handles:
                    _narrator_handles.append(h_lower)
        _card_handles = [tp.get("handle", "").lower().lstrip("@") for tp in tweet_card_posts]
        if _narrator_handles and _card_handles:
            if _narrator_handles[:len(_card_handles)] == _card_handles[:len(_narrator_handles)]:
                logger.info(f"  FIX A VERIFIED: narrator handles {_narrator_handles} match card order {_card_handles}")
            else:
                logger.warning(f"  FIX A MISMATCH: narrator={_narrator_handles} vs cards={_card_handles} — reordering")
                handle_to_post = {tp.get("handle", "").lower().lstrip("@"): tp for tp in tweet_card_posts}
                reordered = []
                for nh in _narrator_handles:
                    if nh in handle_to_post:
                        reordered.append(handle_to_post.pop(nh))
                reordered.extend(handle_to_post.values())
                tweet_card_posts = reordered
                for ri, rp in enumerate(tweet_card_posts):
                    rp["display_order"] = ri

    # --- 0+1. INTRO TAG + COLD OPEN (merged: PBX narrates over intro) ---
    intro_tag_dur = 0.0
    audio_lines = audio_data.get("lines", [])
    cold_open_consumed = False

    _est_narration = sum(al.get("duration", 0) for al in audio_lines if al.get("host") not in ("CLIP",))
    _est_clips = sum(al.get("duration", 0) for al in audio_lines if al.get("host") == "CLIP")
    _est_clips += sum(c.get("duration", 0) for c in extracted_clips.values())
    _est_total = _est_narration + _est_clips + 20
    logger.info(f"  EPISODE ESTIMATE: narration={_est_narration:.0f}s + clips={_est_clips:.0f}s + overhead=20s = {_est_total:.0f}s")

    cold_open_audio = None
    for al in audio_lines:
        if al.get("host") in ("CLIP",) or not al.get("path"):
            continue
        if al.get("path") and os.path.exists(al.get("path", "")):
            cold_open_audio = al
            break

    logger.info("  Session 4: Title card SUPPRESSED — cold open leads directly into content")

    if cold_open_audio:
        intro_out = os.path.join(work_dir, f"part_{part_idx:03d}_intro_pbx_hook.mp4")
        intro_result = make_intro_coldopen(cold_open_audio["path"], intro_out, btc_price=btc_price)
        if intro_result:
            parts.append(intro_result)
            dur = ffprobe_duration(intro_result)
            intro_tag_dur = dur
            logger.info(f"[{part_idx:03d}] INTRO+PBX HOOK: {dur:.1f}s")
            part_idx += 1
            cold_open_consumed = True
        else:
            logger.warning("[---] Intro+PBX hook failed, starting with first dialogue")
    else:
        if os.path.exists(INTRO_TAG):
            intro_tag_out = os.path.join(work_dir, f"part_{part_idx:03d}_intro_tag.mp4")
            intro_tag_result = make_intro_tag_sequence(intro_tag_out)
            if intro_tag_result:
                parts.append(intro_tag_result)
                intro_tag_dur = ffprobe_duration(intro_tag_result)
                logger.info(f"[{part_idx:03d}] INTRO TAG (no TTS): {intro_tag_dur:.1f}s")
                part_idx += 1
        else:
            logger.info("  No intro_tag.mp4 — skipping branded intro")
        logger.warning("[---] No cold open audio available, starting with first dialogue")

    # FIX 6: Prepare B-roll clips
    broll_queue = []
    if broll_clips:
        for bp in broll_clips:
            if isinstance(bp, str) and os.path.exists(bp):
                broll_queue.append(bp)
            elif isinstance(bp, dict) and bp.get("path") and os.path.exists(bp["path"]):
                broll_queue.append(bp["path"])
        logger.info(f"  B-roll clips available: {len(broll_queue)}")
    broll_idx = 0
    host_segment_count = 0

    # --- 2. DIALOGUE + CLIPS ---

    clip_thumbnails = {}
    for rank, cinfo in extracted_clips.items():
        tp = fetch_youtube_thumbnail(cinfo)
        if tp:
            clip_thumbnails[rank] = tp
            logger.info(f"  Thumbnail for clip #{rank}: {os.path.basename(tp)}")

    # Build PiP preview map: rank → pip_path
    # R25 FIX 1: Also search output/clips/ as fallback for PiP source
    pip_previews = {}
    for rank, cinfo in extracted_clips.items():
        clip_path = cinfo.get("path", "")
        if clip_path and os.path.exists(clip_path):
            pip_out = os.path.join(work_dir, f"pip_preview_r{rank}.mp4")
            clips_dir = os.path.join(os.path.dirname(work_dir), "clips")
            output_clips_dir = os.path.join(BASE, "output", "clips")
            reencoded = None
            expected_channel = cinfo.get("channel", "").lower().replace(" ", "_")
            for _search_dir in [clips_dir, output_clips_dir]:
                if os.path.isdir(_search_dir):
                    import glob
                    pattern = os.path.join(_search_dir, f"clip_{rank}_*.mp4")
                    matches = sorted(glob.glob(pattern))
                    for _m in matches:
                        _mbase = os.path.basename(_m).lower()
                        if expected_channel and expected_channel in _mbase:
                            reencoded = _m
                            logger.info(f"  PiP source for rank {rank} matched channel '{expected_channel}' in {_search_dir}")
                            break
                    if not reencoded and matches:
                        logger.warning(f"  PiP rank {rank}: glob found {len(matches)} files but none match channel '{expected_channel}' — using cinfo path directly")
                    if reencoded:
                        break
            pip_source = reencoded if reencoded and os.path.getsize(reencoded) > 50000 else clip_path
            logger.info(f"  R25 FIX 1: PiP rank {rank} source={os.path.basename(pip_source)} (reencoded={reencoded is not None})")
            pip_result = make_pip_preview(pip_source, pip_out)
            if pip_result:
                pip_previews[rank] = pip_result
                logger.info(f"  PiP preview for clip #{rank}: ready")
            else:
                logger.warning(f"  R25 FIX 1: PiP preview for clip #{rank} FAILED — will use fallback")

    audio_idx = 1 if cold_open_consumed else 0
    prev_segment_type = "intro"

    # Render22 FIX 7: Signal Active segment — load real content
    signal_content = None
    try:
        from signal_intelligence import get_signal_content, generate_signal_summary
        signal_content = get_signal_content()
        if signal_content and (signal_content.get("spaces_quotes") or signal_content.get("nostr_posts")):
            logger.info(f"  FIX 7: Signal intelligence loaded — {len(signal_content.get('spaces_quotes', []))} spaces, {len(signal_content.get('nostr_posts', []))} nostr")
        else:
            signal_content = None
            logger.info("  FIX 7: No signal intelligence available")
    except Exception as _sig_err:
        logger.warning(f"  FIX 7: Signal intelligence import failed: {_sig_err}")

    for i, entry in enumerate(dialogue):
        entry_type = entry.get("type", "")
        host_field = entry.get("host", "")

        if cold_open_consumed and i == 0 and host_field != "CLIP":
            cold_open_consumed = False
            continue

        if host_field == "CLIP":
            # Render22 FIX 5: Use should_insert_transition()
            if should_insert_transition(prev_segment_type, "clip"):
                trans_out = os.path.join(work_dir, f"part_{part_idx:03d}_transition_to_clip.mp4")
                trans_result = make_transition_visual(trans_out, duration=2.2)
                if trans_result:
                    parts.append(trans_result)
                    logger.info(f"DIGITAL TRANSITION: [{prev_segment_type}] → [CLIP]")
                    part_idx += 1

            rank = entry.get("rank", 0)
            clip_info = extracted_clips.get(rank, {})
            clip_path = clip_info.get("path", "")

            if clip_path and os.path.exists(clip_path):
                codec_check = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=codec_name", "-of", "default", clip_path],
                    capture_output=True, text=True, timeout=10
                )
                clip_codec = codec_check.stdout.strip().replace("codec_name=", "").strip()
                if clip_codec in ("av1", "hevc", "vp9", "vp8"):
                    h264_path = clip_path + ".h264.mp4"
                    ok_conv = run_ffmpeg([
                        "-i", clip_path,
                        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                        "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", h264_path,
                    ], f"AV1→H264 pre-convert clip #{rank}", 120)
                    if ok_conv and os.path.exists(h264_path):
                        clip_path = h264_path
                        logger.info(f"  FIX4: Pre-converted {clip_codec.upper()} clip #{rank} to H264")

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
                # Render24 FIX 2: If partner clip ffmpeg fails, retry stream copy then bg_loop fallback
                if not result:
                    stream_copy_out = clip_out + ".streamcopy.mp4"
                    sc_ok = run_ffmpeg([
                        "-i", clip_path, "-c:v", "copy", "-c:a", "copy",
                        "-t", str(ffprobe_duration(clip_path)),
                        stream_copy_out,
                    ], f"FIX2 stream copy clip #{rank}", 60)
                    if sc_ok and os.path.exists(stream_copy_out):
                        result = stream_copy_out
                        logger.info(f"  FIX 2: Stream copy fallback for clip #{rank}")
                    else:
                        if os.path.exists(stream_copy_out):
                            os.remove(stream_copy_out)
                        # Last resort: bg_loop video + clip audio
                        if os.path.exists(BG_LOOP):
                            clip_audio_dur = ffprobe_duration(clip_path)
                            bg_fallback_out = clip_out + ".bgfallback.mp4"
                            bg_ok = run_ffmpeg([
                                "-stream_loop", "-1", "-i", BG_LOOP,
                                "-i", clip_path,
                                "-map", "0:v", "-map", "1:a",
                                "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                                "-vf", "scale=1920:1080,setsar=1,fps=30",
                                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                                "-t", str(clip_audio_dur),
                                "-shortest",
                                bg_fallback_out,
                            ], f"FIX2 bg_loop+audio clip #{rank}", 120)
                            if bg_ok and os.path.exists(bg_fallback_out):
                                result = bg_fallback_out
                                logger.info(f"  FIX 2: bg_loop+audio fallback for clip #{rank}")
                            elif os.path.exists(bg_fallback_out):
                                os.remove(bg_fallback_out)
                if result:
                    mix_lower_slide_sfx(result)
                    parts.append(result)
                    dur = ffprobe_duration(result)
                    logger.info(f"[{part_idx:03d}] CLIP #{rank} [{channel}]: {dur:.1f}s (with lower slide SFX)")
                    part_idx += 1
                else:
                    logger.warning(f"[---] Clip #{rank}: visual failed, skipping")
            else:
                logger.warning(f"[assembler] Clip #{rank} not found ({clip_path}) — SKIPPING slot")
            prev_segment_type = "clip"
            continue

        # Render22 FIX 5: Use should_insert_transition() for all segments
        if should_insert_transition(prev_segment_type, entry_type):
            trans_out = os.path.join(work_dir, f"part_{part_idx:03d}_transition.mp4")
            trans_result = make_transition_visual(trans_out, duration=2.2)
            if trans_result:
                parts.append(trans_result)
                logger.info(f"DIGITAL TRANSITION: [{prev_segment_type}] → [{entry_type}]")
                part_idx += 1

        # Host dialogue line — find matching audio
        line_audio = None
        while audio_idx < len(audio_lines):
            al = audio_lines[audio_idx]
            audio_idx += 1
            if al.get("host") in ("CLIP",):
                continue
            line_audio = al
            break

        if not line_audio:
            logger.warning(f"[---] No audio entry for dialogue {i} ({entry_type}) — skipping")
            continue

        if not line_audio.get("path") or not os.path.exists(line_audio.get("path", "")):
            fallback_text = line_audio.get("text", entry.get("text", ""))
            fallback_path = _generate_fallback_silent_audio(work_dir, part_idx, fallback_text)
            if fallback_path:
                line_audio = dict(line_audio)
                line_audio["path"] = fallback_path
                logger.warning(f"  [BUG1] Segment {i} ({entry_type}): TTS fallback silence generated")
            else:
                logger.warning(f"  [BUG1] Segment {i} ({entry_type}): silence generation failed, skipping")
                continue

        host_num = int(line_audio.get("host", 1)) if str(line_audio.get("host", "1")).isdigit() else 1
        text = line_audio.get("text", entry.get("text", ""))
        audio_path = line_audio["path"]

        try:
            tts_size = os.path.getsize(audio_path)
            if tts_size < 5000:
                logger.warning(f"  [GAP GUARD] Segment {i} ({entry_type}): TTS file {os.path.basename(audio_path)} is {tts_size}B (<5KB)")
                silence_pad = os.path.join(work_dir, f"silence_pad_{part_idx:03d}.m4a")
                run_ffmpeg([
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", "0.5", "-c:a", "aac", "-b:a", "192k", silence_pad,
                ], "silence pad", 10)
                if os.path.exists(silence_pad):
                    audio_path = silence_pad
        except OSError:
            pass

        clip_rank = entry.get("clip_rank", 0)
        thumb = clip_thumbnails.get(clip_rank, "") if entry_type in ("setup", "react") else ""

        line_out = os.path.join(work_dir, f"part_{part_idx:03d}_{entry_type}.mp4")

        # Sprint 1.5: Each tweet as its OWN video segment
        if entry_type == "social_segment" and tweet_card_posts and social_card_idx < len(tweet_card_posts):
            card_posts = tweet_card_posts[social_card_idx:]
            card_posts = _rank_cards_for_segment(card_posts, text)

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

            card_rendered_paths = []
            for ci, cp in enumerate(card_posts):
                card_out = os.path.join(work_dir, f"part_{part_idx:03d}_social_card_{ci}.mp4")
                logger.info(f"  SOCIAL CARD {ci}: @{cp.get('handle', '?')} — {cp.get('text', '')[:40]}")

                card_audio = audio_path if ci == 0 else None
                if ci > 0:
                    peek_idx = audio_idx
                    while peek_idx < len(audio_lines):
                        al = audio_lines[peek_idx]
                        if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al["path"]):
                            card_audio = al["path"]
                            audio_idx = peek_idx + 1
                            break
                        peek_idx += 1
                    if not card_audio:
                        card_audio = audio_path

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
                    card_rendered_paths.append(card_result)
                    dur = ffprobe_duration(card_result)
                    logger.info(f"  SOCIAL CARD {ci} rendered: @{cp.get('handle', '?')} ({dur:.1f}s)")

            if len(card_rendered_paths) >= 2:
                current_stitched = card_rendered_paths[0]
                for xfi in range(1, len(card_rendered_paths)):
                    xfade_out = os.path.join(work_dir, f"part_{part_idx:03d}_social_xfade_{xfi}.mp4")
                    xfade_result = apply_xfade(
                        current_stitched, card_rendered_paths[xfi],
                        xfade_out, transition="slideleft", duration=0.4,
                    )
                    if xfade_result:
                        current_stitched = xfade_result
                    else:
                        parts.append(current_stitched)
                        current_stitched = card_rendered_paths[xfi]
                        part_idx += 1
                if os.path.exists(CARD_SWOOSH) and len(card_rendered_paths) > 1:
                    swoosh_mixed = current_stitched + ".swoosh.mp4"
                    card_durs = [ffprobe_duration(p) for p in card_rendered_paths]
                    swoosh_inputs = []
                    swoosh_fg_parts = []
                    cumul = 0.0
                    for si in range(len(card_durs) - 1):
                        cumul += card_durs[si] - 0.4
                        swoosh_inputs.extend(["-i", CARD_SWOOSH])
                        delay_ms = int(cumul * 1000)
                        swoosh_fg_parts.append(f"[{si+1}:a]volume=0.5,adelay={delay_ms}|{delay_ms}[sw_{si}]")
                    sw_labels = "".join(f"[sw_{si}]" for si in range(len(card_durs) - 1))
                    swoosh_fg_parts.append(f"{sw_labels}amix=inputs={len(card_durs)-1}:duration=longest[all_sw]")
                    swoosh_fg_parts.append(f"[0:a][all_sw]amix=inputs=2:duration=first:weights=1 0.5[outa]")
                    swoosh_fg = ";\n".join(swoosh_fg_parts)
                    ok_sw = run_ffmpeg(
                        ["-i", current_stitched] + swoosh_inputs +
                        ["-filter_complex", swoosh_fg,
                         "-map", "0:v", "-map", "[outa]",
                         "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                         swoosh_mixed],
                        "card swoosh mix", 120,
                    )
                    if ok_sw and os.path.exists(swoosh_mixed):
                        current_stitched = swoosh_mixed
                parts.append(current_stitched)
                dur = ffprobe_duration(current_stitched)
                logger.info(f"[{part_idx:03d}] SOCIAL CARDS (xfaded): {dur:.1f}s")
                part_idx += 1
            elif len(card_rendered_paths) == 1:
                parts.append(card_rendered_paths[0])
                dur = ffprobe_duration(card_rendered_paths[0])
                logger.info(f"[{part_idx:03d}] SOCIAL CARD (single): {dur:.1f}s")
                part_idx += 1

            social_card_idx += len(card_posts)
            prev_segment_type = entry_type

            # Render24 FIX 4: Signal Active as its own segment after tweet cards
            if signal_content and (signal_content.get("spaces_quotes") or signal_content.get("nostr_posts")):
                try:
                    from signal_intelligence import generate_signal_summary
                    from tts_engine import tts_elevenlabs
                    sig_summary = generate_signal_summary(signal_content)
                    if sig_summary:
                        sig_tts_path = os.path.join(work_dir, f"part_{part_idx:03d}_signal_active_tts.m4a")
                        tts_ok = tts_elevenlabs(sig_summary, sig_tts_path, host=2, segment_type="signal_active")
                        if tts_ok and os.path.exists(sig_tts_path):
                            sig_out = os.path.join(work_dir, f"part_{part_idx:03d}_signal_active.mp4")
                            sig_result = make_signal_active_scene(
                                sig_tts_path, signal_content, sig_out, btc_price=btc_price,
                            )
                            if sig_result:
                                parts.append(sig_result)
                                sig_dur = ffprobe_duration(sig_result)
                                logger.info(f"[{part_idx:03d}] SIGNAL ACTIVE [PBX]: {sig_dur:.1f}s")
                                part_idx += 1
                                prev_segment_type = "signal_active"
                                signal_content = None  # consumed — don't re-inject
                            else:
                                logger.warning("  FIX 4: Signal Active scene render failed")
                        else:
                            logger.warning("  FIX 4: Signal Active TTS generation failed")
                except Exception as _sig4_err:
                    logger.warning(f"  FIX 4: Signal Active segment failed: {_sig4_err}")

            continue
        elif entry_type == "social_segment":
            result = make_host_visual(
                audio_path, host_num, text, line_out,
                btc_price=btc_price, label=f"{entry_type} #{part_idx}",
                segment_type=entry_type,
            )
        else:
            # Render22: PBX solo — speaker always PBX
            seg_speaker = "PBX"
            seg_data = {"type": entry_type, "text": text,
                        "speaker": seg_speaker,
                        "headline": entry.get("headline", ""),
                        "next_speaker": ""}
            if entry_type == "setup" and clip_rank and clip_rank in extracted_clips:
                seg_data["next_speaker"] = extracted_clips[clip_rank].get("channel", "")

            # Render22 FIX 2+3: PiP guard — NEVER use INTRO_TAG as PiP source
            pip_vid = ""
            if entry_type == "cold_open":
                pip_vid = ""
            elif entry_type in ("setup", "react") and clip_rank:
                # FIX 3: SETUP for clip N → pip_previews[N]. REACT for clip N → pip_previews[N].
                pip_vid = pip_previews.get(clip_rank, "")
                logger.info(f"  PiP clip #{clip_rank} path: {pip_vid or 'NONE'}")
                # FIX 2: NEVER use intro_tag as PiP source
                if pip_vid and os.path.abspath(pip_vid) == os.path.abspath(INTRO_TAG):
                    logger.error(f"  FIX 2: BLOCKED intro_tag.mp4 as PiP source! Using fallback.")
                    pip_vid = ""
                if not pip_vid and entry_type in ("setup", "react"):
                    # Render24 FIX 1: PiP fallback — use bg_loop or skip. NEVER use rank1's PiP for another rank.
                    if os.path.exists(BG_LOOP):
                        pip_vid = BG_LOOP
                        logger.info(f"  FIX 1: Using bg_loop as PiP placeholder for {entry_type.upper()} → clip #{clip_rank}")
                    elif entry_type == "setup":
                        pip_vid = _ensure_pip_placeholder()
                        if pip_vid:
                            logger.info(f"  FIX 1: Using branded placeholder PiP for SETUP → clip #{clip_rank}")
            if pip_vid and pip_vid != PIP_PLACEHOLDER:
                logger.info(f"  FIX 3: PiP video embedded for {entry_type.upper()} → clip #{clip_rank}")

            # Render22 FIX 7: Signal Active segment — replace debug data with real content
            if seg_data.get("headline", "").startswith("SIGNAL") and signal_content:
                seg_data["signal_content"] = signal_content

            result = make_broadcast_segment(
                seg_data, audio_path, host_num,
                part_idx, len(dialogue),
                line_out, btc_price=btc_price,
                thumbnail_path=thumb,
                pip_video_path=pip_vid,
            )

        if result:
            parts.append(result)
            dur = ffprobe_duration(result)
            logger.info(f"[{part_idx:03d}] {entry_type.upper()} [PBX]: {dur:.1f}s")
            part_idx += 1
            prev_segment_type = entry_type
            host_segment_count += 1

            if broll_queue and broll_idx < len(broll_queue) and host_segment_count % 2 == 0:
                broll_path = broll_queue[broll_idx]
                broll_out = os.path.join(work_dir, f"part_{part_idx:03d}_broll_{broll_idx}.mp4")
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
    skip_outro_fade = False

    if os.path.exists(OUTRO_BRANDED_NEW):
        narration_end = sum(ffprobe_duration(p) for p in parts if p and os.path.exists(p))
        logger.info(f"Narration ends at {narration_end:.1f}s — outro starts here")

        outro_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro_branded_new.mp4")
        outro_result = make_outro_branded_new(outro_out)
        if outro_result:
            parts.append(outro_result)
            dur = ffprobe_duration(outro_result)
            logger.info(f"[{part_idx:03d}] OUTRO (branded new): {dur:.1f}s — hard cut, own music")
            part_idx += 1
            skip_outro_fade = True
        else:
            logger.warning("  outro_branded_new.mp4 render failed — falling back to old outro")

    if not skip_outro_fade:
        wrap_audio = ""
        for al in reversed(audio_lines):
            if al.get("host") not in ("CLIP",) and al.get("path") and os.path.exists(al.get("path", "")):
                wrap_audio = al["path"]
                break
        if parts and wrap_audio:
            last_part_name = os.path.basename(parts[-1]) if parts[-1] else ""
            if "wrap" in last_part_name.lower():
                removed = parts.pop()
                part_idx -= 1
                logger.info(f"  Removed duplicate wrap segment ({os.path.basename(removed)})")
        narration_end = sum(ffprobe_duration(p) for p in parts if p and os.path.exists(p))
        logger.info(f"Narration ends at {narration_end:.1f}s — outro starts here")
        outro_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro_branded.mp4")
        outro_result = make_branded_outro(outro_out, narration_audio=wrap_audio)
        if outro_result:
            parts.append(outro_result)
            dur = ffprobe_duration(outro_result)
            logger.info(f"[{part_idx:03d}] OUTRO (branded): {dur:.1f}s")
            part_idx += 1
        else:
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
    # Option A FIX: Zero-byte / missing audio detection before concat
    # Abort if any part is missing, zero-byte, or has no detectable duration
    logger.info(f"\nValidating {len(parts)} parts before concat...")
    for i, p in enumerate(parts):
        if not p or not os.path.exists(p):
            raise RuntimeError(
                f"ASSEMBLY ABORT: Part {i:03d} missing or null path: {p}. "
                f"Cannot concatenate with missing segments."
            )
        fsize = os.path.getsize(p)
        if fsize < 1000:
            raise RuntimeError(
                f"ASSEMBLY ABORT: Part {i:03d} is {fsize} bytes (zero-byte/corrupt): "
                f"{os.path.basename(p)}. Refusing to render around missing audio."
            )
        dur = ffprobe_duration(p)
        if dur < 0.1:
            raise RuntimeError(
                f"ASSEMBLY ABORT: Part {i:03d} has {dur:.3f}s duration (effectively empty): "
                f"{os.path.basename(p)}. Refusing to render around missing audio."
            )
        logger.info(f"  Part {i:03d}: {os.path.basename(p)} ({dur:.1f}s, {fsize//1024}KB) OK")

    intro_music_total = (intro_tag_dur + 10.0 + 3.0) if intro_tag_dur > 0 else 0

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    result = concatenate_parts(parts, output_path,
                               intro_music_duration=intro_music_total,
                               skip_outro_fade=skip_outro_fade)

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
    checks.append(("Duration", 5 <= duration <= 900, f"{duration:.1f}s"))
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
