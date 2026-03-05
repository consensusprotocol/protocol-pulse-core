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

INTRO_VIDEO = os.path.join(ASSETS, "intro.mp4")
OUTRO_VIDEO = os.path.join(ASSETS, "outro.mp4")
GLITCH_TRANSITION = os.path.join(ASSETS, "transitions", "glitch_transition_waud.mp4")
WATERMARK = os.path.join(ASSETS, "logo", "watermark.png")
BG_MUSIC = os.path.join(ASSETS, "music", "pp_background.mp3")
TAG_VIDEO = os.path.join(ASSETS, "tag_vertical.mp4")
OUTRO_BRANDED = os.path.join(ASSETS, "outro_branded.mp4")
LOGO_IMAGE = os.path.join(ASSETS, "logo_protocol_pulse.png")


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

    fade_out_v = max(0, outro_dur - 0.5)
    fade_out_a = max(0, outro_dur - 1.0)
    vf = (f"scale=1920:1080,setsar=1,format=yuv420p,"
          f"fade=t=out:st={fade_out_v}:d=0.5")

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

def make_intro_coldopen(tts_path: str, output_path: str, btc_price: str = "N/A") -> str:
    """Intro segment: cold open TTS narration with pp_intro.mp3 jingle underneath.

    Deep space background + waveform + Protocol Pulse branding.
    The jingle plays at 35% volume under TTS.
    """
    import glob as _glob

    jingle = os.path.join(ASSETS, "music", "pp_intro.mp3")
    if not os.path.exists(jingle):
        tracks = _glob.glob(os.path.join(ASSETS, "music", "intro_*.mp3"))
        jingle = tracks[0] if tracks else ""

    tts_dur = ffprobe_duration(tts_path)
    total_dur = max(tts_dur + 1.0, 4.0)

    has_jingle = bool(jingle and os.path.exists(jingle))
    has_wm = os.path.exists(WATERMARK)
    has_logo = os.path.exists(LOGO_IMAGE)

    # Background: deep space + vignette + logo
    fg = f"color=c=0x0A0A0A:s=1920x1080:d={total_dur}:r=30[base];\n"
    fg += f"color=c=0x0F0000:s=1920x540:d={total_dur}:r=30[tophalf];\n"
    fg += f"[base][tophalf]overlay=0:0[bgbase];\n"
    # Vignette
    fg += (f"[bgbase]drawbox=x=0:y=0:w=250:h=1080:color=0x000000@0.12:t=fill"
           f",drawbox=x=1670:y=0:w=250:h=1080:color=0x000000@0.12:t=fill[bgvig];\n")
    fg += (f"[bgvig]drawbox=x=0:y=536:w=1920:h=3:color=0xCC0000@0.5:t=fill"
           f",drawbox=x=0:y=541:w=1920:h=1:color=0x880000@0.3:t=fill[bglines];\n")
    fg += f"color=c=0xCC0000@0.8:s=4x1080:d={total_dur}:r=30[leftbar];\n"
    fg += f"[bglines][leftbar]overlay=0:0[bgv0];\n"

    # Waveform — compact, centered, red with mirror reflection
    fg += (f"[0:a]showwaves=s=960x80:mode=cline:"
           f"colors=0xCC0000|0xFF4444:scale=sqrt:draw=full:rate=30[wave_raw];\n")
    fg += f"[wave_raw]split[wA][wB];\n"
    fg += f"[wB]vflip,colorchannelmixer=aa=0.35[wflip];\n"
    fg += f"[wA][wflip]vstack[wavepair];\n"
    fg += f"[bgv0][wavepair]overlay=480:460[withwave];\n"

    # Logo overlay (centered, 200px, black bg removed) or text fallback
    inp_args = [tts_path]
    idx = 1
    if has_logo:
        inp_args.append(LOGO_IMAGE)
        logo_idx = idx
        idx += 1
        fg += (f"[{logo_idx}:v]scale=-1:200,"
               f"colorkey=color=0x000000:similarity=0.25:blend=0.1[logo];\n")
        fg += f"[withwave][logo]overlay=(W-w)/2:60[title];\n"
    else:
        fg += (f"[withwave]drawtext=fontfile={FONT_BOLD}:"
               f"text='PROTOCOL PULSE':fontcolor=0xCC0000:fontsize=72:"
               f"x=(w-text_w)/2:y=80[title];\n")

    fg += (f"[title]drawtext=fontfile={FONT_MONO}:"
           f"text='PULSE CHECK':fontcolor=0xFFFFFF@0.7:fontsize=32:"
           f"x=(w-text_w)/2:y=280[v_final];\n")

    if has_wm:
        inp_args.append(WATERMARK)
        wm_idx = idx
        idx += 1
        fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
        fg += f"[v_final][wm]overlay=W-170:16[outv_wm];\n"
        last_v = "outv_wm"
    else:
        last_v = "v_final"
    fg += f"[{last_v}]format=yuv420p[outv];\n"

    if has_jingle:
        inp_args.append(jingle)
        jingle_idx = idx
        fg += f"[0:a]volume=1.0[tts_a];\n"
        fg += f"[{jingle_idx}:a]volume=0.35[jingle_a];\n"
        fg += f"[tts_a][jingle_a]amix=inputs=2:duration=first:weights=1 0.35[outa]"
    else:
        fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"

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
    fade_start = max(dur - 0.8, dur * 0.8)
    vf = (f"scale=1920:1080:force_original_aspect_ratio=increase,"
          f"crop=1920:1080,setsar=1,fps=30,format=yuv420p,"
          f"fade=t=out:st={fade_start:.2f}:d=0.8")

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

    host_names = {1: "JESSICA", 2: "CHRIS"}
    host_colors = {1: "0xCC0000@0.95", 2: "0x880000@0.95"}
    speaker = host_names.get(host, "HOST")
    color = host_colors.get(host, "0xFF3333@0.95")

    safe_btc = btc_price.replace("'", "").replace('"', "")
    ticker_text = f"  PROTOCOL PULSE  |  PULSE CHECK  |  BTC {safe_btc}  |  PROTOCOLPULSE.IO  "
    ticker_text = ticker_text.replace("'", "").replace('"', "")

    has_wm = os.path.exists(WATERMARK)
    has_bgm = os.path.exists(BG_MUSIC)
    has_thumb = bool(thumbnail_path and os.path.exists(thumbnail_path))
    has_logo = os.path.exists(LOGO_IMAGE)
    is_social = segment_type == "social_segment"

    # Get episode title for subtitle text
    ep_title = label.replace("host visual", "").replace("(JESSICA)", "").replace("(CHRIS)", "").strip()

    # Build inputs list
    # 0: TTS audio, [1: logo], [N: watermark], [N: bg music], [N: thumbnail]
    inputs = [audio_path]  # 0: tts audio
    inp_idx = 1

    if has_logo:
        inputs.append(LOGO_IMAGE)
        logo_idx = inp_idx
        inp_idx += 1
    else:
        logo_idx = -1

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

    # Filter graph — procedural background with logo + audio waveform
    # 1. Dark base (#0A0A0A) with subtle vignette
    fg = f"color=c=0x0A0A0A:s=1920x1080:d={total_dur}:r=30[base];\n"

    # 2. Subtle gradient overlay — slightly lighter top half for depth
    fg += f"color=c=0x0F0000:s=1920x540:d={total_dur}:r=30[tophalf];\n"
    fg += f"[base][tophalf]overlay=0:0[bgbase];\n"

    # 3. Vignette — darker corners for cinematic feel
    fg += (f"[bgbase]drawbox=x=0:y=0:w=250:h=1080:color=0x000000@0.12:t=fill"
           f",drawbox=x=1670:y=0:w=250:h=1080:color=0x000000@0.12:t=fill"
           f",drawbox=x=0:y=0:w=1920:h=120:color=0x000000@0.08:t=fill"
           f",drawbox=x=0:y=960:w=1920:h=120:color=0x000000@0.08:t=fill[bgvig];\n")

    # 4. Thin horizontal accent lines — red palette
    fg += (f"[bgvig]drawbox=x=0:y=538:w=1920:h=2:color=0xCC0000@0.35:t=fill"
           f",drawbox=x=0:y=542:w=1920:h=1:color=0x880000@0.2:t=fill[bglines];\n")

    # 5. LEFT SIDE vertical accent bar — red
    fg += f"color=c=0xCC0000@0.8:s=4x1080:d={total_dur}:r=30[leftbar];\n"
    fg += f"[bglines][leftbar]overlay=0:0[bgv0];\n"

    # 6. Logo overlay — centered, 200px height, black bg removed via colorkey
    if has_logo:
        fg += (f"[{logo_idx}:v]scale=-1:200,"
               f"colorkey=color=0x000000:similarity=0.25:blend=0.1[logo];\n")
        # Center logo: x=(1920-logo_w)/2, y=80
        fg += f"[bgv0][logo]overlay=(W-w)/2:80[bglogo];\n"
        last_bg = "bglogo"
    else:
        # Fallback: text title if no logo
        fg += (f"[bgv0]drawtext=fontfile={FONT_BOLD}:"
               f"text='PROTOCOL PULSE':fontcolor=0xCC0000:fontsize=72:"
               f"x=(w-text_w)/2:y=80[bglogo];\n")
        last_bg = "bglogo"

    # 7. "PULSE CHECK" subtitle below logo
    fg += (f"[{last_bg}]drawtext=fontfile={FONT_MONO}:"
           f"text='PULSE CHECK':fontcolor=0xFFFFFF@0.7:fontsize=28:"
           f"x=(w-text_w)/2:y=300[bgtitle];\n")

    # 8. Corner elements — date top-left, "PROTOCOL PULSE" top-right
    fg += (f"[bgtitle]drawtext=fontfile={FONT_MONO}:"
           f"text='PROTOCOL PULSE':fontcolor=0x444444:fontsize=16:"
           f"x=W-200:y=16[bgcorner];\n")
    last_bg = "bgcorner"

    # 9. Audio waveform — compact, centered, red (960x80)
    fg += (f"[0:a]showwaves=s=960x80:mode=cline:"
           f"colors=0xCC0000|0xFF4444:scale=sqrt:draw=full:rate=30[wave_raw];\n")

    # 10. Mirror reflection (vflip + 35% opacity fade)
    fg += f"[wave_raw]split[wA][wB];\n"
    fg += f"[wB]vflip,colorchannelmixer=aa=0.35[wflip];\n"
    fg += f"[wA][wflip]vstack[wavepair];\n"   # 960x160 total

    # 11. Overlay waveform centered: x=480, y=460
    fg += f"[{last_bg}][wavepair]overlay=480:460[withwave];\n"

    # 12. Speaker label bar (bottom left)
    fg += f"color=c={color}:s=280x52:d={total_dur}:r=30[spkbg];\n"
    fg += (f"[spkbg]drawtext=fontfile={FONT_BOLD}:text='{speaker}':"
           f"fontcolor=white:fontsize=26:x=16:y=12[spklabel];\n")

    # 13. Ticker bar (bottom) — gold text on near-black
    fg += f"color=c=0x0A0000@0.92:s=1920x44:d={total_dur}:r=30[tickbg];\n"
    fg += (f"[tickbg]drawtext=fontfile={FONT_MONO}:text='{ticker_text}':"
           f"fontcolor=0xFFD700:fontsize=18:x=w-mod(t*80\\,w+tw):y=12[ticker];\n")

    # 14. Compose base layers
    fg += f"[withwave][spklabel]overlay=40:H-90[v1];\n"
    fg += f"[v1][ticker]overlay=0:H-44[v2];\n"
    last_v = "v2"

    # 15. Watermark top-right
    if has_wm:
        fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
        fg += f"[v2][wm]overlay=W-170:16[v3];\n"
        last_v = "v3"

    # 12. Thumbnail PIP — MANDATORY for setup/react — right side
    if has_thumb:
        fg += f"[{thumb_idx}:v]scale=720:405,pad=722:407:1:1:color=0xCC0000@0.9[thumb];\n"
        fg += f"[{last_v}][thumb]overlay=1160:120[vthumb];\n"
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
        fg += f"[vscan]drawbox=x=0:y=0:w=1920:h=6:color=0xCC0000:t=fill[vsoc_bar];\n"
        # Section header — cyberpunk style
        fg += (f"[vsoc_bar]drawtext=fontfile={FONT_BOLD}:"
               f"text='WHAT THE BITCOIN INTERNET IS SAYING':"
               f"fontcolor=0xCC0000:fontsize=28:x=(w-text_w)/2:y=24[vsoc_title];\n")

        # Card glow background (slightly larger, transparent red)
        fg += f"color=c=0xCC0000@0.08:s=1420x320:d={total_dur}:r=30[cardglow];\n"
        fg += f"[vsoc_title][cardglow]overlay=250:168[vglow];\n"

        # Card body (dark surface with sharp red border)
        fg += f"color=c=0x141414@0.95:s=1400x300:d={total_dur}:r=30[tcard];\n"
        fg += f"[tcard]drawbox=x=0:y=0:w=1400:h=300:color=0xCC0000@0.6:t=2[tcardborder];\n"
        # Top edge accent line on card
        fg += f"[tcardborder]drawbox=x=0:y=0:w=1400:h=2:color=0xCC0000:t=fill[tcardtop];\n"

        # Pulse dot (animated blink via alpha modulation)
        fg += (f"[tcardtop]drawbox=x=20:y=20:w=8:h=8:color=0xCC0000:t=fill[tdot];\n")
        # Handle text
        fg += (f"[tdot]drawtext=fontfile={FONT_BOLD}:"
               f"text='@ProtocolPulse':"
               f"fontcolor=0xCC0000:fontsize=20:x=38:y=16[thandle];\n")

        # Tweet text (larger, better spacing, #EDEDED color)
        fg += (f"[thandle]drawtext=fontfile={FONT_MONO}:"
               f"text='{wrapped_text}':"
               f"fontcolor=0xEDEDED:fontsize=26:x=24:y=56:line_spacing=16:"
               f"box=0[tcardtext];\n")

        # Bottom-right engagement indicator
        fg += (f"[tcardtext]drawtext=fontfile={FONT_MONO}:"
               f"text='PROTOCOL PULSE':fontcolor=0x888888:fontsize=14:"
               f"x=w-180:y=h-24[tcardfoot];\n")

        # Overlay card centered on base (with fade-in)
        fg += f"[vglow][tcardfoot]overlay=260:178:format=auto,fade=t=in:st=0:d=0.3[vsoc2];\n"
        last_v = "vsoc2"

    fg += f"[{last_v}]format=yuv420p[outv];\n"

    # Audio: TTS + optional background music
    if has_bgm:
        fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[tts];\n"
        fg += f"[{bgm_idx}:a]volume=-18dB[bgm];\n"
        fg += f"[tts][bgm]amix=inputs=2:duration=first:weights=1 0.12[outa]"
    else:
        fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"

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
    ticker_text = f"  PROTOCOL PULSE  |  PULSE CHECK  |  BTC {safe_btc}  |  PROTOCOLPULSE.IO  "
    ticker_text = ticker_text.replace("'", "").replace('"', "")
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

    # Filtergraph — gradient background (dark to slightly lighter)
    fg = f"color=c=0x0C0C0C:s=1920x1080:d={total_dur}:r=30[bgdark];\n"
    fg += f"color=c=0x161616:s=1920x540:d={total_dur}:r=30[bglite];\n"
    fg += f"[bgdark][bglite]overlay=0:0[base];\n"

    # Scanline effect via geq (1px dark line every 4px at ~5% opacity)
    fg += (f"[base]geq=lum='if(eq(mod(Y,4),0),lum(X,Y)*0.92,lum(X,Y))':"
           f"cr='cr(X,Y)':cb='cb(X,Y)'[bgscan];\n")

    # Vignette corners (darker edges)
    fg += (f"[bgscan]drawbox=x=0:y=0:w=200:h=1080:color=0x000000@0.15:t=fill"
           f",drawbox=x=1720:y=0:w=200:h=1080:color=0x000000@0.15:t=fill"
           f",drawbox=x=0:y=0:w=1920:h=100:color=0x000000@0.10:t=fill"
           f",drawbox=x=0:y=980:w=1920:h=100:color=0x000000@0.10:t=fill[bgvig];\n")

    # Top red accent bar
    fg += f"[bgvig]drawbox=x=0:y=0:w=1920:h=4:color=0xCC0000:t=fill[bgbar];\n"

    # Pulse dot top-left (static red circle indicator)
    fg += f"[bgbar]drawbox=x=20:y=16:w=10:h=10:color=0xCC0000:t=fill[bgdot];\n"

    # Section header — "WHAT THE BITCOIN INTERNET IS SAYING"
    fg += (f"[bgdot]drawtext=fontfile={FONT_BOLD}:"
           f"text='WHAT THE BITCOIN INTERNET IS SAYING':"
           f"fontcolor=0xCC0000:fontsize=28:x=(w-text_w)/2:y=28[bgtitle];\n")
    last_v = "bgtitle"

    # Render up to 2 tweet cards — stacked vertically with spacing
    card_y_start = 90
    card_height = 260
    card_spacing = 30
    card_width = 1360
    card_x = 280

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
        fg += f"color=c=0xCC0000@0.08:s={card_width + 24}x{card_height + 24}:d={total_dur}:r=30[{tag}glow];\n"
        fg += f"[{last_v}][{tag}glow]overlay={card_x - 12}:{cy - 12}[{tag}g];\n"

        # Card body
        fg += f"color=c=0x141414@0.95:s={card_width}x{card_height}:d={total_dur}:r=30[{tag}body];\n"
        # Outer red border (2px)
        fg += f"[{tag}body]drawbox=x=0:y=0:w={card_width}:h={card_height}:color=0xCC0000@0.7:t=2[{tag}brd];\n"
        # Inner glow border (dark red, 2px inside the outer border)
        fg += f"[{tag}brd]drawbox=x=4:y=4:w={card_width - 8}:h={card_height - 8}:color=0x440000@0.5:t=2[{tag}inner];\n"
        # Left accent bar
        fg += f"[{tag}inner]drawbox=x=0:y=0:w=6:h={card_height}:color=0xCC0000:t=fill[{tag}lbar];\n"
        # Top edge accent
        fg += f"[{tag}lbar]drawbox=x=0:y=0:w={card_width}:h=2:color=0xCC0000:t=fill[{tag}top];\n"

        # Pulse dot
        fg += f"[{tag}top]drawbox=x=20:y=18:w=8:h=8:color=0xCC0000:t=fill[{tag}dot];\n"

        # Handle — monospace font
        fg += (f"[{tag}dot]drawtext=fontfile={FONT_MONO}:"
               f"text='{handle}':"
               f"fontcolor=0xCC0000:fontsize=22:x=38:y=14[{tag}hdl];\n")

        # Tweet text — bold for readability
        fg += (f"[{tag}hdl]drawtext=fontfile={FONT_BOLD}:"
               f"text='{tweet_text}':"
               f"fontcolor=0xEDEDED:fontsize=24:x=24:y=52:line_spacing=16:"
               f"box=0[{tag}txt];\n")

        # Engagement stats bottom
        fg += (f"[{tag}txt]drawtext=fontfile={FONT_MONO}:"
               f"text='{likes_str} likes  |  {rt_str} RTs':"
               f"fontcolor=0xFF4444:fontsize=16:x=24:y=h-32[{tag}stats];\n")

        # Source label bottom-right
        fg += (f"[{tag}stats]drawtext=fontfile={FONT_MONO}:"
               f"text='via X':fontcolor=0x888888:fontsize=14:"
               f"x=w-80:y=h-30[{tag}src];\n")

        # Overlay card on base with fade-in
        fade_start = ci * 0.4
        fg += f"[{tag}g][{tag}src]overlay={card_x}:{cy}:format=auto,fade=t=in:st={fade_start}:d=0.3[{tag}out];\n"
        last_v = f"{tag}out"

    # "WHAT THE BITCOIN INTERNET IS SAYING" repeated at bottom of cards area
    bottom_header_y = card_y_start + len(posts[:2]) * (card_height + card_spacing) + 10
    fg += (f"[{last_v}]drawtext=fontfile={FONT_BOLD}:"
           f"text='WHAT THE BITCOIN INTERNET IS SAYING':"
           f"fontcolor=0xCC0000@0.3:fontsize=18:x=(w-text_w)/2:y={bottom_header_y}[vbhdr];\n")
    last_v = "vbhdr"

    # Bottom info bar — gold/amber text
    fg += f"color=c=0x0A0000@0.92:s=1920x44:d={total_dur}:r=30[tickbg];\n"
    fg += (f"[tickbg]drawtext=fontfile={FONT_MONO}:text='{ticker_text}':"
           f"fontcolor=0xFFD700:fontsize=18:x=w-mod(t*80\\,w+tw):y=12[ticker];\n")
    fg += f"[{last_v}][ticker]overlay=0:H-44[vtick];\n"
    last_v = "vtick"

    # Watermark
    if has_wm:
        fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
        fg += f"[{last_v}][wm]overlay=W-170:16[vwm];\n"
        last_v = "vwm"

    fg += f"[{last_v}]format=yuv420p[outv];\n"

    # Audio: TTS + optional background music
    if has_bgm:
        fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[tts];\n"
        fg += f"[{bgm_idx}:a]volume=-18dB[bgm];\n"
        fg += f"[tts][bgm]amix=inputs=2:duration=first:weights=1 0.12[outa]"
    else:
        fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"

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

            # Try to extract whoosh audio from branded asset
            if os.path.exists(GLITCH_TRANSITION):
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
            f"[0:v]trim=0:{total_dur},setpts=PTS-STARTPTS,loop=loop=-1:size={int(total_dur*30)}:start=0,trim=0:{total_dur},setpts=PTS-STARTPTS[v];"
            f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[tts];"
            f"[2:a]volume=-18dB[bgm];"
            f"[tts][bgm]amix=inputs=2:duration=first:weights=1 0.12[outa]",
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
            f"[0:v]trim=0:{total_dur},setpts=PTS-STARTPTS,loop=loop=-1:size={int(total_dur*30)}:start=0,trim=0:{total_dur},setpts=PTS-STARTPTS[v];"
            f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]",
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
    frames = max(int((dur + 0.3) * 30), 90)

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


def make_remotion_social_card(audio_path: str, posts: list, output_path: str,
                              btc_price: str = "N/A") -> str:
    """Render SocialCard via Remotion + mux with TTS audio.

    Falls back to '' on failure (caller should use FFmpeg make_social_card_visual).
    """
    if not _remotion_enabled():
        return ""

    post = posts[0] if posts else {}
    dur = ffprobe_duration(audio_path)
    frames = max(int((dur + 0.3) * 30), 90)

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
    frames = max(int((dur + 1.0) * 30), 120)

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
            f"[0:v]trim=0:{total_dur},setpts=PTS-STARTPTS,loop=loop=-1:size={int(total_dur*30)}:start=0,trim=0:{total_dur},setpts=PTS-STARTPTS[v];"
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
    frames = int(overlay_dur * 30)

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
        "-f", "lavfi", "-i", f"color=c=0x0A0A0A:s=1920x1080:d={duration}:r=30",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
        output_path,
    ], "transition fallback", 30)
    return output_path if ok else ""


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

    fg = (
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30[clip];\n"
        # Source attribution (top-right, semi-transparent)
        f"color=c=0x0A0A0A@0.75:s=320x36:d={clip_dur}[srcbg];\n"
        f"[srcbg]drawtext=fontfile={FONT_MONO}:text='Source  {safe_source}':fontcolor=white:fontsize=15:x=10:y=10[srclabel];\n"
        # Compose — source overlay top-right
        f"[clip][srclabel]overlay=W-340:18,format=yuv420p[outv];\n"
        f"[0:a]asetpts=PTS-STARTPTS,volume=1.0[outa]"
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
         "-af", "aresample=async=1",
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
         "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
         "-movflags", "+faststart",
         output_path],
        "concat final encode", 600,
    )

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

    # Override default BG_MUSIC with mood-matched music bed if provided
    global BG_MUSIC
    if music_bed and os.path.exists(music_bed):
        BG_MUSIC = music_bed
        logger.info(f"  Music bed: {os.path.basename(music_bed)}")

    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "work")
    os.makedirs(work_dir, exist_ok=True)

    dialogue = script.get("dialogue", [])
    lines = audio_data.get("lines", [])
    parts = []
    part_idx = 0

    # Load real tweet data for social segment cards (V15)
    tweet_card_posts = []
    try:
        from utils.feature_flags import is_enabled
        if is_enabled("tweet_cards"):
            from utils.social_fetcher import get_todays_social_posts
            tweet_card_posts = get_todays_social_posts(max_posts=4)
    except Exception as e:
        logger.warning(f"Tweet card data load failed: {e}")
    social_card_idx = 0  # Track which posts have been shown

    # --- 1. INTRO: COLD OPEN TTS + JINGLE (no tag video) ---
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
        intro_out = os.path.join(work_dir, f"part_{part_idx:03d}_intro_cold_open.mp4")
        # Try Remotion TitleCard first, fall back to FFmpeg
        intro_result = ""
        try:
            ep_title = script.get("title", "Pulse Check Daily")
            intro_result = make_remotion_title_card(
                cold_open_audio["path"], intro_out,
                title=ep_title, btc_price=btc_price,
            )
        except Exception as e:
            logger.warning(f"Remotion TitleCard failed: {e}")
        if not intro_result:
            intro_result = make_intro_coldopen(cold_open_audio["path"], intro_out, btc_price=btc_price)
        if intro_result:
            parts.append(intro_result)
            dur = ffprobe_duration(intro_result)
            logger.info(f"[{part_idx:03d}] INTRO (cold open + jingle): {dur:.1f}s")
            part_idx += 1
            cold_open_consumed = True
        else:
            logger.warning("[---] Cold open intro failed, falling back to tag video")
            intro_out2 = os.path.join(work_dir, f"part_{part_idx:03d}_intro_tag.mp4")
            tag_result = make_tag_video(intro_out2)
            if tag_result:
                parts.append(tag_result)
                part_idx += 1
    else:
        logger.warning("[---] No cold open audio available, using tag intro")
        intro_out = os.path.join(work_dir, f"part_{part_idx:03d}_intro_tag.mp4")
        tag_result = make_tag_video(intro_out)
        if tag_result:
            parts.append(tag_result)
            part_idx += 1

    # --- 2. DIALOGUE + CLIPS ---

    # Build thumbnail map: rank → thumbnail_path
    clip_thumbnails = {}
    for rank, cinfo in extracted_clips.items():
        tp = fetch_youtube_thumbnail(cinfo)
        if tp:
            clip_thumbnails[rank] = tp
            logger.info(f"  Thumbnail for clip #{rank}: {os.path.basename(tp)}")

    # Track which audio line index we're on (host lines only, not CLIPs)
    # If we consumed the cold_open, skip the first host audio line
    audio_idx = 1 if cold_open_consumed else 0

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
                # Glitch transition BEFORE clip
                trans_out = os.path.join(work_dir, f"part_{part_idx:03d}_glitch.mp4")
                trans = make_transition_visual(trans_out)
                if trans:
                    parts.append(trans)
                    dur = ffprobe_duration(trans)
                    logger.info(f"[{part_idx:03d}] GLITCH TRANSITION: {dur:.2f}s")
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
                    parts.append(result)
                    dur = ffprobe_duration(result)
                    logger.info(f"[{part_idx:03d}] CLIP #{rank} [{channel}]: {dur:.1f}s")
                    part_idx += 1
                else:
                    logger.warning(f"[---] Clip #{rank}: visual failed, skipping")
            else:
                logger.warning(f"[---] Clip #{rank}: file not found ({clip_path}), skipping")
            continue

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

        # V15: Tweet card visual for social segments when real data available
        if entry_type == "social_segment" and tweet_card_posts and social_card_idx < len(tweet_card_posts):
            # Show 2 posts per card visual (or remaining)
            card_posts = tweet_card_posts[social_card_idx:social_card_idx + 2]
            social_card_idx += 2
            # Try Remotion SocialCard first
            result = ""
            try:
                result = make_remotion_social_card(
                    audio_path, card_posts, line_out, btc_price=btc_price,
                )
            except Exception as e:
                logger.warning(f"Remotion SocialCard failed: {e}")
            if not result:
                result = make_social_card_visual(
                    audio_path, card_posts, line_out, btc_price=btc_price,
                )
            if not result:
                # Fall back to standard host visual
                result = make_host_visual(
                    audio_path, host_num, text, line_out,
                    btc_price=btc_price, label=f"{entry_type} #{part_idx}",
                    segment_type=entry_type,
                )
        else:
            # Try Remotion WaveformVisualizer for host segments
            result = ""
            try:
                result = make_remotion_waveform(
                    audio_path, line_out,
                    title=text[:80] if text else "Pulse Check Daily",
                    btc_price=btc_price,
                )
            except Exception as e:
                logger.warning(f"Remotion WaveformVisualizer failed: {e}")
            if not result:
                result = make_host_visual(
                    audio_path, host_num, text, line_out,
                    btc_price=btc_price,
                    label=f"{entry_type} #{part_idx}",
                    thumbnail_path=thumb,
                    segment_type=entry_type,
                )
        if result:
            parts.append(result)
            dur = ffprobe_duration(result)
            speaker = "JESSICA" if host_num == 1 else "CHRIS"
            logger.info(f"[{part_idx:03d}] {entry_type.upper()} [{speaker}]: {dur:.1f}s")
            part_idx += 1
        else:
            logger.warning(f"[---] Host visual failed for {entry_type}")

    # --- 3. BRANDED OUTRO ---
    # RULE (Section 17): Outro plays ONLY after ALL dialogue parts including wrap.
    # Wrap already rendered above as part of dialogue loop — do NOT mix wrap audio
    # into outro again (that causes overlap/black screen gap).
    narration_end = sum(ffprobe_duration(p) for p in parts if p and os.path.exists(p))
    logger.info(f"Narration ends at {narration_end:.1f}s — outro starts here")

    outro_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro_branded.mp4")
    outro_result = make_branded_outro(outro_out)
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
