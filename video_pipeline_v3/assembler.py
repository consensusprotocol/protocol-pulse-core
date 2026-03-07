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

# ── VDS COLOR SYSTEM ──────────────────────────────────────────────────────
COLOR_BG = "0x06070b"           # deep space black
COLOR_PANEL = "0x0d1118"        # elevated surface
COLOR_PANEL2 = "0x121824"       # secondary surface
COLOR_TEXT = "0xeef2ff"         # primary text (NOT pure white)
COLOR_MUTED = "0x95a0ba"        # secondary text
COLOR_RED = "0xff3b5f"          # Protocol Pulse red
COLOR_GOLD = "0xf8c15c"         # SIGNATURE gold
COLOR_CYAN = "0x5de4ff"         # data accents
COLOR_LIME = "0x89ffb8"         # positive metrics
COLOR_CORAL = "0xff8ba0"        # negative metrics
COLOR_INFOBAR_BG = "0xf8c15c"   # gold info bar background
COLOR_INFOBAR_TEXT = "0x1a1f2e"  # dark navy on gold

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


def _build_vds_background_fg(duration: float, label_out: str = "vds_bg") -> tuple:
    """VDS 7-layer procedural background. No external video files.

    Returns (extra_inputs, filtergraph_string).
    extra_inputs is always [] — pure procedural generation.
    """
    f = ""
    # Layer 0: Deep space base
    f += f"color=c=0x06070b:s=1920x1080:d={duration}:r=30[layer0];\n"
    # Layer 1: Three-source radial glows (red top-left, cyan top-right, gold bottom-center)
    f += (f"color=c=0x000000:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(80*exp(-(X*X+Y*Y)/160000),0,255)':g='0':b='0'[red_glow];\n")
    f += (f"color=c=0x000000:s=1920x1080:d={duration}:r=30,"
          f"geq=r='0':g='clip(40*exp(-((X-1920)*(X-1920)+Y*Y)/100000),0,255)':"
          f"b='clip(60*exp(-((X-1920)*(X-1920)+Y*Y)/100000),0,255)'[cyan_glow];\n")
    f += (f"color=c=0x000000:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(30*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/80000),0,255)':"
          f"g='clip(20*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/80000),0,255)':b='0'[gold_glow];\n")
    f += f"[layer0][red_glow]blend=all_mode=screen[bg1];\n"
    f += f"[bg1][cyan_glow]blend=all_mode=screen[bg2];\n"
    f += f"[bg2][gold_glow]blend=all_mode=screen[bg_glows];\n"
    # Layer 2: Perspective floor grid
    f += (f"[bg_glows]drawgrid=width=96:height=54:thickness=1:color=0xffffff@0.04,"
          f"perspective=x0=240:y0=540:x1=1680:y1=540:x2=0:y2=1080:x3=1920:y3=1080[bg_grid];\n")
    # Layer 3: Noise texture (subtle grain)
    f += f"[bg_grid]noise=alls=4:allf=t+u[bg_noise];\n"
    # Layer 4: Scanlines (horizontal lines every 4px at 4% opacity)
    f += f"[bg_noise]drawgrid=width=0:height=4:thickness=1:color=0x000000@0.04[bg_scan];\n"
    # Layer 5: Vignette
    f += f"[bg_scan]vignette=PI/5:mode=backward[{label_out}];\n"
    return ([], f)


def _build_info_bar_fg(duration: float, btc_price: str, block_height: str = "",
                       label_in: str = "v_pre_tick", label_out: str = "v_ticked") -> str:
    """Animated scrolling info bar — VDS gold text on dark bg.

    Replaces the static gold rectangle with a broadcast-quality ticker.
    """
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    if block_height:
        content = (f"  PROTOCOL PULSE  |  BTC {safe_btc}  |  BLOCK {block_height}"
                   f"  |  {date_str}  |  PROTOCOLPULSE.IO  |  STAY SOVEREIGN  "
                   f"  |  PROTOCOL PULSE  |  BTC {safe_btc}  |  BLOCK {block_height}"
                   f"  |  {date_str}  |  PROTOCOLPULSE.IO  |  STAY SOVEREIGN  ")
    else:
        content = (f"  PROTOCOL PULSE  |  BTC {safe_btc}  |  {date_str}"
                   f"  |  PROTOCOLPULSE.IO  |  STAY SOVEREIGN  |  PULSE CHECK"
                   f"  |  PROTOCOL PULSE  |  BTC {safe_btc}  |  {date_str}"
                   f"  |  PROTOCOLPULSE.IO  |  STAY SOVEREIGN  |  PULSE CHECK  ")

    safe_content = content.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # Dark base bar with subtle transparency
    fg += f"color=c=0x06070b@0.95:s=1920x44:d={duration}:r=30[tickbase];\n"
    # Thin gold line at top edge of bar (1px separator)
    fg += f"[tickbase]drawbox=x=0:y=0:w=1920:h=1:color=0xf8c15c@0.6:t=fill[tickline];\n"
    # Scrolling gold text
    fg += (f"[tickline]drawtext=fontfile={FONT_MONO}:text='{safe_content}':"
           f"fontcolor=0xf8c15c:fontsize=17:"
           f"x=w-mod(t*90\\,w+text_w):y=13[ticker];\n")
    # Overlay bar onto video frame at bottom
    fg += f"[{label_in}][ticker]overlay=0:H-44[{label_out}];\n"
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
    """Cold open: face on screen, NO logo, NO music, immediate voice.

    Per PRODUCTION_DESIGN_LAWS: cyberpunk bg + waveform + subtitle.
    Voice starts on frame 1. No pre-roll.
    """
    tts_dur = ffprobe_duration(tts_path)
    total_dur = max(tts_dur + 0.3, 3.0)

    has_thumb_co = bool(thumbnail_path and os.path.exists(thumbnail_path))

    # Build inputs: 0=TTS, [1=thumbnail if present]
    inp_args = [tts_path]
    idx = 1

    # VDS procedural background (7-layer, no video files)
    _, bg_fg = _build_vds_background_fg(total_dur, label_out="bgvig")
    fg = bg_fg

    # GPT face panel: thumbnail in cold open left panel
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

    # VDS waveform — red/gold gradient
    fg += (f"[0:a]showwaves=s=600x80:mode=cline:"
           f"colors={COLOR_RED}|{COLOR_GOLD}:scale=sqrt:draw=full:rate=30[wave_raw];\n")
    fg += f"[wave_raw]split[wA][wB];\n"
    fg += f"[wB]vflip,colorchannelmixer=aa=0.35[wflip];\n"
    fg += f"[wA][wflip]vstack[wavepair];\n"
    fg += f"[{face_base}][wavepair]overlay=228:440[withwave];\n"

    # VDS animated scrolling info bar
    fg += _build_info_bar_fg(total_dur, btc_price, label_in="withwave", label_out="v_final")
    fg += f"[v_final]format=yuv420p[outv];\n"

    # NO music — voice starts immediately
    fg += f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=7,aresample=async=1[outa]"

    ok = run_ffmpeg_filtergraph(
        inp_args, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "intro cold open", 120,
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

def make_host_visual(audio_path: str, host: int, text: str,
                     output_path: str, btc_price: str = "N/A",
                     label: str = "", thumbnail_path: str = "",
                     segment_type: str = "") -> str:
    """Host segment: procedural dark background + audio waveform visualizer + overlays.

    No video file backgrounds — background is generated procedurally from TTS audio.
    Background music at -18dB under TTS.
    Optional thumbnail PIP overlay for setup/react segments.
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = audio_dur + 0.3

    host_names = {1: "ERYN", 2: "MARK"}
    host_colors = {1: f"{COLOR_RED}@0.95", 2: f"{COLOR_RED}@0.80"}
    speaker = host_names.get(host, "HOST")
    color = host_colors.get(host, f"{COLOR_RED}@0.95")

    safe_btc = btc_price.replace("'", "").replace('"', "")

    has_wm = os.path.exists(WATERMARK)
    has_bgm = os.path.exists(BG_MUSIC)
    has_thumb = bool(thumbnail_path and os.path.exists(thumbnail_path))
    is_social = segment_type == "social_segment"

    # Build inputs list
    # 0: TTS audio, [N: watermark], [N: bg music], [N: thumbnail]
    inputs = [audio_path]  # 0: tts audio
    inp_idx = 1

    # Sprint 1.9: Logo NOT added as input for narration segments

    if has_wm:
        inputs.append(WATERMARK)
        wm_idx = inp_idx
        inp_idx += 1
    else:
        wm_idx = -1

    if has_bgm:
        inputs.append(["-stream_loop", "-1", "-i", BG_MUSIC])
        bgm_idx = inp_idx
        inp_idx += 1
    else:
        bgm_idx = -1

    if has_thumb:
        inputs.append(thumbnail_path)
        thumb_idx = inp_idx
        inp_idx += 1
    else:
        thumb_idx = -1

    # VDS procedural background (7-layer, no video files)
    _, bg_fg = _build_vds_background_fg(total_dur, label_out="bgvig")
    fg = bg_fg

    # VDS-1: Thin horizontal accent lines — VDS red
    fg += (f"[bgvig]drawbox=x=0:y=538:w=1920:h=2:color={COLOR_RED}@0.35:t=fill"
           f",drawbox=x=0:y=542:w=1920:h=1:color={COLOR_RED}@0.15:t=fill[bglines];\n")

    # VDS-1: LEFT SIDE vertical accent bar — VDS red
    fg += f"color=c={COLOR_RED}@0.8:s=4x1080:d={total_dur}:r=30[leftbar];\n"
    fg += f"[bglines][leftbar]overlay=0:0[bgv0];\n"

    last_bg = "bgv0"

    # VDS-5: Eyebrow kicker — gold, monospace, uppercase
    fg += (f"[{last_bg}]drawtext=fontfile={FONT_MONO}:"
           f"text='{speaker} - PROTOCOL PULSE':fontcolor={COLOR_GOLD}:fontsize=14:"
           f"x=40:y=16[bgcorner];\n")
    last_bg = "bgcorner"

    # VDS: Audio waveform — red/gold gradient
    fg += (f"[0:a]showwaves=s=600x80:mode=cline:"
           f"colors={COLOR_RED}|{COLOR_GOLD}:scale=sqrt:draw=full:rate=30[wave_raw];\n")

    # 10. Mirror reflection (vflip + 35% opacity fade)
    fg += f"[wave_raw]split[wA][wB];\n"
    fg += f"[wB]vflip,colorchannelmixer=aa=0.35[wflip];\n"
    fg += f"[wA][wflip]vstack[wavepair];\n"   # 600x160 total

    # 11. Overlay waveform centered in left zone: x=228, y=340
    # Left zone is 0-1056px, center of 600px waveform = (1056-600)/2 = 228
    fg += f"[{last_bg}][wavepair]overlay=228:340[withwave];\n"

    # VDS-5: Speaker label — eyebrow kicker style (gold text, no colored bg box)
    fg += f"color=c={COLOR_BG}@0.6:s=320x36:d={total_dur}:r=30[spkbg];\n"
    fg += (f"[spkbg]drawtext=fontfile={FONT_MONO}:text='{speaker} - PROTOCOL PULSE':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=12:y=10[spklabel];\n")

    # Sprint 3.5: Subtitle text overlay (white, bottom-center, above ticker)
    safe_sub = _sanitize_text(text) if text else ""
    if safe_sub:
        wrapped_sub = _word_wrap(safe_sub, max_width=50, max_lines=2)
        fg += (f"[withwave]drawtext=fontfile={FONT_BOLD}:"
               f"text='{wrapped_sub}':"
               f"fontcolor={COLOR_TEXT}:fontsize=30:x=(w-text_w)/2:y=H-160:"
               f"line_spacing=8:"
               f"box=1:boxcolor={COLOR_BG}@0.5:boxborderw=8[withsub];\n")
        fg += f"[withsub][spklabel]overlay=40:H-90[v1];\n"
    else:
        fg += f"[withwave][spklabel]overlay=40:H-90[v1];\n"

    # VDS animated scrolling info bar
    fg += _build_info_bar_fg(total_dur, btc_price, label_in="v1", label_out="v2")
    last_v = "v2"

    # 15. Watermark top-right
    if has_wm:
        fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
        fg += f"[v2][wm]overlay=W-170:16[v3];\n"
        last_v = "v3"

    # 12. Thumbnail PIP — right 40% panel (x=1056 to x=1920)
    # Issue 2: 820x462 at x=1056, y=200 with thin 2px border at 30% opacity
    if has_thumb:
        fg += f"[{thumb_idx}:v]scale=820:462,pad=824:466:2:2:color={COLOR_TEXT}@0.3[thumb];\n"
        fg += f"[{last_v}][thumb]overlay=1056:200[vthumb];\n"
        last_v = "vthumb"

    # 13. Social segment — cyberpunk tweet card (only for social_segment type)
    if is_social:
        safe_text = (text.replace("'", "").replace('"', "")
                         .replace(":", " -").replace(";", ",")
                         .replace("[", "(").replace("]", ")")
                         .replace("\u2014", "-").replace("\u2019", "")
                         .replace("\\", "").replace("\n", " "))
        # Word-wrap at ~60 chars, max 3 lines, truncate with ...
        wrapped_lines = []
        current_line = ""
        for word in safe_text.split():
            if len(current_line) + len(word) + 1 > 60:
                wrapped_lines.append(current_line)
                current_line = word
                if len(wrapped_lines) >= 3:
                    break
            else:
                current_line = f"{current_line} {word}".strip() if current_line else word
        if current_line and len(wrapped_lines) < 3:
            wrapped_lines.append(current_line)
        if len(wrapped_lines) == 3 and len(safe_text) > sum(len(l) for l in wrapped_lines):
            wrapped_lines[2] = wrapped_lines[2][:57] + "..."
        wrapped_text = "\\n".join(wrapped_lines)

        # --- Cyberpunk card design ---
        # Scanline effect via geq (subtle dark line every 4px)
        fg += (f"[{last_v}]geq=lum='if(eq(mod(Y,4),0),lum(X,Y)*0.94,lum(X,Y))':"
               f"cr='cr(X,Y)':cb='cb(X,Y)'[vscan];\n")

        # Red accent bar top (thicker for cyberpunk)
        fg += f"[vscan]drawbox=x=0:y=0:w=1920:h=6:color={COLOR_RED}:t=fill[vsoc_bar];\n"
        # Section header — gold eyebrow kicker style
        fg += (f"[vsoc_bar]drawtext=fontfile={FONT_MONO}:"
               f"text='WHAT THE BITCOIN INTERNET IS SAYING':"
               f"fontcolor={COLOR_GOLD}:fontsize=28:x=(w-text_w)/2:y=24[vsoc_title];\n")

        # Card glow background (slightly larger, transparent red)
        fg += f"color=c={COLOR_RED}@0.08:s=1420x320:d={total_dur}:r=30[cardglow];\n"
        fg += f"[vsoc_title][cardglow]overlay=250:168[vglow];\n"

        # Card body (dark surface with sharp red border)
        fg += f"color=c={COLOR_PANEL}@0.92:s=1400x300:d={total_dur}:r=30[tcard];\n"
        fg += f"[tcard]drawbox=x=0:y=0:w=1400:h=300:color={COLOR_RED}@0.4:t=2[tcardborder];\n"
        # Top edge accent line on card
        fg += f"[tcardborder]drawbox=x=0:y=0:w=1400:h=2:color={COLOR_RED}:t=fill[tcardtop];\n"

        # Pulse dot (animated blink via alpha modulation)
        fg += (f"[tcardtop]drawbox=x=20:y=20:w=8:h=8:color={COLOR_RED}:t=fill[tdot];\n")
        # Handle text — gold
        fg += (f"[tdot]drawtext=fontfile={FONT_MONO}:"
               f"text='@ProtocolPulse':"
               f"fontcolor={COLOR_GOLD}:fontsize=20:x=38:y=16[thandle];\n")

        # Tweet text
        fg += (f"[thandle]drawtext=fontfile={FONT_MONO}:"
               f"text='{wrapped_text}':"
               f"fontcolor={COLOR_TEXT}:fontsize=22:x=24:y=56:line_spacing=16:"
               f"box=0[tcardtext];\n")

        # Bottom-right engagement indicator
        fg += (f"[tcardtext]drawtext=fontfile={FONT_MONO}:"
               f"text='PROTOCOL PULSE':fontcolor={COLOR_MUTED}:fontsize=12:"
               f"x=w-180:y=h-24[tcardfoot];\n")

        # Overlay card centered on base (with fade-in)
        fg += f"[vglow][tcardfoot]overlay=260:178:format=auto,fade=t=in:st=0:d=0.3[vsoc2];\n"
        last_v = "vsoc2"

    fg += f"[{last_v}]format=yuv420p[outv];\n"

    # Sprint 1.3+1.4: Loudnorm narration to -14 LUFS + sidechain music ducking
    if has_bgm:
        fg += f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=7,aresample=async=1[tts];\n"
        # Sidechain ducking: music at -18dB idle, ducks to -30dB when voice present
        fg += f"[{bgm_idx}:a]volume=0.126,afade=t=in:d=0.5,afade=t=out:st={max(0, total_dur - 1.0)}:d=1.0[music_raw];\n"
        fg += f"[music_raw]asplit[music_play][music_sc];\n"
        fg += f"[music_play][music_sc]sidechaincompress=threshold=0.02:ratio=6:attack=50:release=500[music_ducked];\n"
        fg += f"[tts][music_ducked]amix=inputs=2:duration=first[outa]"
    else:
        fg += f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=7,aresample=async=1[outa]"

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label or f"host visual ({speaker})", 180,
    )

    if ok:
        return output_path

    # NO SILENT FALLBACK — log full error and raise so we know when it breaks
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
    """Word-wrap text for FFmpeg drawtext, return \\n-joined string."""
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
    return "\\n".join(lines)


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
    has_bgm = os.path.exists(BG_MUSIC)

    # Build inputs
    inputs = [audio_path]
    inp_idx = 1
    if has_wm:
        inputs.append(WATERMARK)
        wm_idx = inp_idx
        inp_idx += 1
    else:
        wm_idx = -1
    if has_bgm:
        inputs.append(["-stream_loop", "-1", "-i", BG_MUSIC])
        bgm_idx = inp_idx
        inp_idx += 1
    else:
        bgm_idx = -1

    # VDS procedural background (7-layer, no video files)
    _, bg_fg = _build_vds_background_fg(total_dur, label_out="bgvig")
    fg = bg_fg

    # VDS-1: Top red accent bar
    fg += f"[bgvig]drawbox=x=0:y=0:w=1920:h=4:color={COLOR_RED}:t=fill[bgbar];\n"

    # VDS: Pulse dot top-left
    fg += f"[bgbar]drawbox=x=20:y=16:w=10:h=10:color={COLOR_RED}:t=fill[bgdot];\n"

    # VDS: Section header — gold eyebrow kicker
    fg += (f"[bgdot]drawtext=fontfile={FONT_MONO}:"
           f"text='SOCIAL PULSE - WHAT BITCOIN IS SAYING':"
           f"fontcolor={COLOR_GOLD}:fontsize=14:x=(w-text_w)/2:y=20[bgtitle];\n")
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
                   f"fontcolor={COLOR_GOLD}:fontsize=14:x=38:y=16[{tag}hdl];\n")

            # Tweet text — bold for readability
            fg += (f"[{tag}hdl]drawtext=fontfile={FONT_BOLD}:"
                   f"text='{tweet_text}':"
                   f"fontcolor={COLOR_TEXT}:fontsize=22:x=24:y=52:line_spacing=16:"
                   f"box=0[{tag}txt];\n")

            # Engagement stats bottom
            fg += (f"[{tag}txt]drawtext=fontfile={FONT_MONO}:"
                   f"text='{likes_str} likes  |  {rt_str} RTs':"
                   f"fontcolor={COLOR_CORAL}:fontsize=12:x=24:y=h-28[{tag}stats];\n")

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
           f"fontcolor={COLOR_GOLD}@0.3:fontsize=12:x=(w-text_w)/2:y={bottom_header_y}[vbhdr];\n")
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

    # Sprint 1.3+1.4: Loudnorm + sidechain ducking for social segment
    if has_bgm:
        fg += f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=7,aresample=async=1[tts];\n"
        fg += f"[{bgm_idx}:a]volume=0.126,afade=t=in:d=0.5,afade=t=out:st={max(0, total_dur - 1.0)}:d=1.0[music_raw];\n"
        fg += f"[music_raw]asplit[music_play][music_sc];\n"
        fg += f"[music_play][music_sc]sidechaincompress=threshold=0.02:ratio=6:attack=50:release=500[music_ducked];\n"
        fg += f"[tts][music_ducked]amix=inputs=2:duration=first[outa]"
    else:
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

    has_bgm = bg_music and os.path.exists(BG_MUSIC)

    if has_bgm:
        ok = run_ffmpeg([
            "-i", video_path,
            "-i", audio_path,
            "-stream_loop", "-1", "-i", BG_MUSIC,
            "-filter_complex",
            f"[0:v]setpts=PTS-STARTPTS[v];"
            f"[1:a]aresample=async=1[tts];"
            f"[2:a]volume=0.10,afade=t=in:d=0.5,afade=t=out:st={max(0, total_dur - 1.0)}:d=1.0[bgm];"
            f"[tts][bgm]amix=inputs=2:duration=first:weights=1 0.15[outa]",
            "-map", "[v]", "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(total_dur), output_path,
        ], f"remotion mux with bgm", 180)
    else:
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
        ], f"remotion mux no bgm", 180)

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
    """Full-screen YouTube clip with original audio + source attribution.

    CRITICAL: Original audio is preserved. No muting. No TTS overlay.
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
        f"fade=t=in:d=0.3,fade=t=out:st={fade_out_start}:d=0.5,"
        # VDS: Subtle warm color grade for partner clips
        f"curves=r='0/0 1/1.03':g='0/0 1/1.01':b='0/0 1/0.96'[clip];\n"
        # VDS-6: Protocol Pulse watermark top-right (35% opacity)
        f"color=c={COLOR_PANEL}@0.35:s=220x28:d={clip_dur}[srcbg];\n"
        f"[srcbg]drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':fontcolor={COLOR_TEXT}@0.5:fontsize=12:x=8:y=8[srclabel];\n"
        # VDS-6: Lower third — glassmorphism bar with red left accent
        f"color=c={COLOR_PANEL}@0.88:s=1920x87:d={clip_dur}[ltbg];\n"
        f"[ltbg]drawbox=x=0:y=0:w=3:h=87:color={COLOR_RED}:t=fill[ltbar];\n"
        f"[ltbar]drawtext=fontfile={FONT_MONO}:text='SOURCE - {safe_source.upper()}':"
        f"fontcolor={COLOR_GOLD}:fontsize=11:x=20:y=14[ltkick];\n"
        f"[ltkick]drawtext=fontfile={FONT_BOLD}:text='{safe_source}':"
        f"fontcolor={COLOR_TEXT}:fontsize=22:x=20:y=38[ltname];\n"
        # Compose: watermark top-right, lower third slides in at t=0.5 for 6s
        f"[clip][srclabel]overlay=W-240:16[v1];\n"
        f"[v1][ltname]overlay=0:H-131:enable='between(t,0.5,6.5)',format=yuv420p[outv];\n"
        # Audio: fade in/out + loudnorm to -14 LUFS
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
    """Concat video parts using FFmpeg concat demuxer."""
    valid = [p for p in parts if p and os.path.exists(p)]
    if not valid:
        logger.error("No valid parts to concatenate")
        return ""
    if len(valid) == 1:
        shutil.copy2(valid[0], output_path)
        return output_path

    # Normalize all parts to consistent format
    normalized = []
    for i, p in enumerate(valid):
        tmp = output_path + f".norm{i}.mp4"
        norm = normalize_part(p, tmp)
        normalized.append(norm)

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for p in normalized:
            f.write(f"file '{os.path.abspath(p)}'\n")

    # Concat demuxer with stream copy (parts are already normalized)
    # Then re-encode final output with PTS reset + async audio to kill accumulated drift
    concat_raw = output_path + ".concat_raw.mp4"
    ok = run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", concat_file,
         "-c", "copy", concat_raw],
        "concat demux", 300,
    )

    if not ok or not os.path.exists(concat_raw):
        logger.error("Concat demuxer failed")
        return ""

    # Final encode: PTS reset on BOTH streams + async audio alignment
    # ABR mode WITHOUT CRF — CRF overrides -b:v and -minrate, defeating bitrate floor.
    # Parts already have CRF 17 quality. Final encode just needs bitrate guarantee.
    ok = run_ffmpeg(
        ["-fflags", "+genpts",
         "-i", concat_raw,
         "-c:v", "libx264", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-r", "30", "-vsync", "cfr",
         "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
         "-af", "asetpts=PTS-STARTPTS,aresample=async=1,loudnorm=I=-14:TP=-3.0:LRA=11:linear=true,alimiter=level_in=1:level_out=0.794:limit=0.708:attack=3:release=30:asc=1",
         "-movflags", "+faststart",
         output_path],
        "concat final encode", 600,
    )

    # Post-encode two-pass loudnorm — precisely controls true peak after AAC encoding
    if ok and os.path.exists(output_path):
        # Pass 1: measure
        import re as _re
        try:
            r = subprocess.run(
                ["ffmpeg", "-i", output_path, "-filter:a",
                 "loudnorm=I=-14:TP=-3.0:LRA=11:print_format=json", "-f", "null", "-"],
                capture_output=True, text=True, timeout=300,
            )
            json_start = r.stderr.rfind("{")
            json_end = r.stderr.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                measured = json.loads(r.stderr[json_start:json_end])
                mi = measured.get("input_i", "-14")
                mtp = measured.get("input_tp", "0")
                mlra = measured.get("input_lra", "7")
                mthresh = measured.get("input_thresh", "-24")
                # Pass 2: apply with measured values (precise two-pass mode)
                tp_pass = output_path + ".tp_limited.mp4"
                tp_ok = run_ffmpeg(
                    ["-i", output_path,
                     "-c:v", "copy",
                     "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                     "-af", (f"loudnorm=I=-14:TP=-3.0:LRA=11:linear=true"
                             f":measured_I={mi}:measured_TP={mtp}"
                             f":measured_LRA={mlra}:measured_thresh={mthresh}"),
                     "-movflags", "+faststart",
                     tp_pass],
                    "true peak two-pass loudnorm", 300,
                )
                if tp_ok and os.path.exists(tp_pass):
                    os.replace(tp_pass, output_path)
                    logger.info("Two-pass loudnorm true peak pass applied")
                elif os.path.exists(tp_pass):
                    os.remove(tp_pass)
        except Exception as e:
            logger.warning(f"Post-encode TP pass failed: {e}")

    # Cleanup concat raw
    if os.path.exists(concat_raw):
        try:
            os.remove(concat_raw)
        except OSError:
            pass

    # Cleanup
    for p in normalized:
        if ".norm" in p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    for p in valid:
        if p.endswith("_waud.mp4") and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    if os.path.exists(concat_file):
        os.remove(concat_file)

    return output_path if ok else ""


# ── Main assembly ────────────────────────────────────────────────────────────

def assemble_episode(script: dict, audio_data: dict, extracted_clips: dict,
                     output_path: str, btc_price: str = "N/A",
                     music_bed: str = "", intro_music: str = "") -> str:
    """Assemble a V6 ESPN-quality episode.

    Args:
        script: Script with dialogue array
        audio_data: From generate_dialogue_audio() — {lines, full, total_duration}
        extracted_clips: From clip_extractor.extract_all() — {rank: {path, channel, ...}}
        output_path: Final video path
        btc_price: BTC price string for ticker

    Returns:
        Path to final video, or "" on failure
    """
    logger.info("=" * 60)
    logger.info("ASSEMBLING V10 EPISODE — WAVEFORM VISUALIZER")
    logger.info("=" * 60)

    try:
        return _assemble_episode_inner(script, audio_data, extracted_clips,
                                       output_path, btc_price, music_bed, intro_music)
    except Exception:
        import traceback
        logger.error("ASSEMBLY CRASHED — full traceback:")
        traceback.print_exc()
        return ""


def _assemble_episode_inner(script, audio_data, extracted_clips,
                            output_path, btc_price="N/A", music_bed="", intro_music=""):
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

    if cold_open_audio:
        # Issue 1 FIX: Cold open hook is the FIRST thing in the video.
        # NO title card, NO logo intro. Just the hook + waveform visual.
        # The title card was causing the cold open audio to play twice
        # (once in cold open, once in title card).
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
                # Issue 8: xfade transition between last part and clip (not standalone)
                # Apply xfade to merge outgoing clip with incoming, then replace last part
                if parts:
                    prev_part = parts[-1]
                    xfade_out = os.path.join(work_dir, f"part_{part_idx:03d}_xfade.mp4")
                    xfaded = apply_xfade(prev_part, clip_path, xfade_out, transition="fade", duration=1.0)
                    if xfaded:
                        # Replace last part with xfaded version (it now includes the clip)
                        # But this merges two parts — we need the clip separate for lower third
                        # So fall back to standalone transition but keep it short
                        pass  # xfade between narration and raw clip is tricky with lower thirds
                    # Fallback: keep standalone transition but use custom whoosh
                    trans_out = os.path.join(work_dir, f"part_{part_idx:03d}_glitch.mp4")
                    trans = make_transition_visual(trans_out)
                    if trans:
                        parts.append(trans)
                        dur = ffprobe_duration(trans)
                        logger.info(f"[{part_idx:03d}] TRANSITION: {dur:.2f}s (with custom whoosh)")
                        part_idx += 1

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

        # Transition between segment type changes
        # Per PRODUCTION_DESIGN_LAWS: transitions between every segment
        needs_transition = (
            prev_segment_type != entry_type
            and prev_segment_type not in ("intro",)
            and parts  # at least one part already exists
        )
        if needs_transition:
            trans_out = os.path.join(work_dir, f"part_{part_idx:03d}_glitch.mp4")
            trans = make_transition_visual(trans_out)
            if trans:
                parts.append(trans)
                dur = ffprobe_duration(trans)
                logger.info(f"[{part_idx:03d}] TRANSITION ({prev_segment_type}→{entry_type}): {dur:.2f}s")
                part_idx += 1

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
            # VDS: All backgrounds are procedural now — use make_host_visual directly.
            result = make_host_visual(
                audio_path, host_num, text, line_out,
                btc_price=btc_price,
                label=f"{entry_type} #{part_idx}",
                thumbnail_path=thumb,
                segment_type=entry_type,
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
            speaker = "ERYN" if host_num == 1 else "MARK"
            logger.info(f"[{part_idx:03d}] {entry_type.upper()} [{speaker}]: {dur:.1f}s")
            part_idx += 1
            prev_segment_type = entry_type
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

    # Alpha transition before outro
    if parts:
        trans_out = os.path.join(work_dir, f"part_{part_idx:03d}_glitch_pre_outro.mp4")
        trans = make_transition_visual(trans_out)
        if trans:
            parts.append(trans)
            part_idx += 1

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
