#!/usr/bin/env python3
"""Narrator PiP scenes, host visual, and PiP preview rendering."""
import os
import subprocess

from assembler_common import (
    logger, run_ffmpeg, run_ffmpeg_filtergraph, ffprobe_duration,
    BASE, ASSETS, FONT_BOLD, FONT_MONO,
    COLOR_BG, COLOR_RED, COLOR_RED_WARM, COLOR_WHITE, COLOR_TEXT, COLOR_GOLD,
    COLOR_MUTED, COLOR_MUTED2, COLOR_GREEN, COLOR_CORAL,
    COLOR_PANEL, COLOR_PANEL2, COLOR_RED_DIM,
    INTRO_TAG, BG_LOOP, PIP_PLACEHOLDER, LOWER_SLIDE,
    _sanitize_text, _word_wrap, _split_headline_for_render, _get_live_metric,
    _get_bg_layer, _build_top_system_bar, _build_corner_brackets_fg,
    _build_broadcast_bg, _build_black_diamond_bg, _build_info_bar_fg,
    _build_narration_wave, _build_signature_info_rail,
    _add_episode_title_pill, _ken_burns_motion, _bv2_encode,
)


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

def make_pip_preview(clip_path: str, output_path: str, duration: float = 8.0,
                     position_pct: float = 0.5) -> str:
    """Extract a muted PiP preview clip for overlay during narration.

    Issue 2: 820x462 PiP (right 40% panel), positioned at x=1056, y=200.
    ACTUAL VIDEO playing (muted), not static image with pan.
    Thin 2px white border at 30% opacity.

    Args:
        position_pct: Where in the clip to extract from (0.0=start, 0.5=mid, 1.0=end).
                      Default 0.5 (midpoint). Use 0.15 for clip_a, 0.60 for clip_b.
    """
    if not clip_path or not os.path.exists(clip_path):
        logger.warning(f"PiP: clip path missing: {clip_path} — generating dark placeholder")
        # FIX 1: Generate solid dark placeholder instead of returning empty/NONE
        try:
            ok = run_ffmpeg([
                "-f", "lavfi", "-i", f"color=c=0x0A0A0F:s=716x370:d={duration}:r=30",
                "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
                "-t", str(duration), "-an",
                "-c:v", "libx264", "-crf", "17", "-preset", "ultrafast",
                "-r", "30", "-pix_fmt", "yuv420p",
                output_path,
            ], "pip dark placeholder", 30)
            if ok and os.path.exists(output_path):
                logger.info(f"PiP: dark placeholder generated ({duration}s)")
                return output_path
        except Exception as e:
            logger.warning(f"PiP: dark placeholder generation failed: {e}")
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

    # FIX CFR: Pre-process source clip to normalize framerate/encoding before PiP render.
    # Eliminates b-frame/VFR issues that cause ffmpeg to silently output black frames.
    cfr_path = clip_path + ".cfr_prep.mp4"
    cfr_ok = run_ffmpeg([
        "-i", clip_path,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-vsync", "cfr", "-r", "30",
        "-c:a", "aac", "-ar", "48000",
        cfr_path,
    ], "pip cfr pre-process", 600)
    if cfr_ok and os.path.exists(cfr_path) and os.path.getsize(cfr_path) > 50_000:
        pip_source = cfr_path
        logger.info(f"PiP: CFR pre-processed {os.path.basename(clip_path)}")
    else:
        if os.path.exists(cfr_path):
            try:
                os.remove(cfr_path)
            except OSError:
                pass
        logger.warning(f"PiP: CFR pre-process failed — generating dark placeholder instead of VFR original")
        # FIX: VFR/bad-codec originals cause black frames in PiP filtergraph — use placeholder
        try:
            placeholder_ok = run_ffmpeg([
                "-f", "lavfi", "-i", f"color=c=0x0A0A0F:s=716x370:d={duration}:r=30",
                "-t", str(duration), "-an",
                "-c:v", "libx264", "-crf", "17", "-preset", "ultrafast",
                "-r", "30", "-pix_fmt", "yuv420p",
                output_path,
            ], "pip cfr-fail placeholder", 30)
            if placeholder_ok and os.path.exists(output_path):
                logger.info(f"PiP: dark placeholder generated after CFR failure ({duration}s)")
                return output_path
        except Exception as e:
            logger.warning(f"PiP: placeholder generation failed after CFR failure: {e}")
        return ""

    actual_dur = min(duration, clip_dur - 0.5)
    if actual_dur <= 0:
        actual_dur = min(duration, clip_dur)
    # Extract from position_pct of clip (default midpoint for backward compat)
    start = max(0, (clip_dur * position_pct) - (actual_dur / 2))
    # Clamp so we don't exceed clip bounds
    if start + actual_dur > clip_dur:
        start = max(0, clip_dur - actual_dur)
    ok = run_ffmpeg([
        "-ss", str(start), "-i", pip_source,
        "-t", str(actual_dur), "-an",
        "-vf", (
            # FIX 1: scale UP to fill the frame, then crop — NOT decrease+pad which leaves black borders
            "scale=716:370:force_original_aspect_ratio=increase,"
            "crop=716:370,setsar=1,"
            # Issue 3: grayscale + slow Ken Burns zoom for preview aesthetic
            "hue=s=0,eq=brightness=-0.1:contrast=1.1,"
            "format=yuv420p"
        ),
        "-c:v", "libx264", "-crf", "17", "-preset", "ultrafast",
        "-r", "30",
        output_path,
    ], "pip preview extract", 120)  # FIX 1: increased timeout

    # Clean up CFR temp
    if os.path.exists(cfr_path):
        try:
            os.remove(cfr_path)
        except OSError:
            pass

    if ok and os.path.exists(output_path):
        # Render21 FIX 2: Verify PiP output is real video (not still image)
        pip_out_dur = ffprobe_duration(output_path)
        try:
            fc_result = subprocess.run(
                ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                 "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", output_path],
                capture_output=True, text=True, timeout=300)
            frame_count = int(fc_result.stdout.strip() or "0")
        except Exception:
            frame_count = 0
        if pip_out_dur < 2.0 or frame_count < 15:
            logger.warning(f"PiP STILL IMAGE detected: dur={pip_out_dur:.1f}s frames={frame_count} — applying Ken Burns")
            # Session fix 3e: Static frame banned — create Ken Burns pan/zoom from thumbnail
            ken_burns_path = output_path + ".kenburns.mp4"
            kb_ok = run_ffmpeg([
                "-loop", "1", "-t", str(duration),
                "-i", output_path,
                "-vf", (
                    "scale=800:420:flags=lanczos,"
                    "zoompan=z='min(zoom+0.001,1.08)':d=1:s=716x370:fps=30,"
                    "setsar=1,format=yuv420p"
                ),
                "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                "-r", "30", "-an",
                ken_burns_path,
            ], "pip ken burns from thumbnail", 60)
            if kb_ok and os.path.exists(ken_burns_path) and os.path.getsize(ken_burns_path) > 10000:
                os.replace(ken_burns_path, output_path)
                logger.info(f"PiP Ken Burns effect applied: {duration:.1f}s from static thumbnail")
                return output_path
            # Ken Burns failed — fall through to black check or return empty
            try:
                os.remove(output_path)
            except OSError:
                pass
            if os.path.exists(ken_burns_path):
                try:
                    os.remove(ken_burns_path)
                except OSError:
                    pass
            return ""

        # FIX BLACK: Sample mid-frame brightness to detect silent black output.
        # ffmpeg can produce valid frame counts but all-black video from bad sources.
        try:
            brightness_result = subprocess.run(
                ["ffmpeg", "-v", "error", "-ss", str(min(actual_dur / 2, pip_out_dur / 2)),
                 "-i", output_path, "-vframes", "3",
                 "-vf", "signalstats", "-f", "null", "-"],
                capture_output=True, text=True, timeout=15)
            import re as _re_pip
            yavg_vals = _re_pip.findall(r"YAVG:\s*([\d.]+)", brightness_result.stderr)
            mean_brightness = sum(float(v) for v in yavg_vals) / len(yavg_vals) if yavg_vals else 999
        except Exception:
            mean_brightness = 999  # can't check — assume ok
        if mean_brightness < 12:
            logger.error(f"PiP BLACK OUTPUT detected: YAVG={mean_brightness:.1f} src={clip_path} — falling back to letterbox")
            try:
                os.remove(output_path)
            except OSError:
                pass
            # Fallback: simple centered letterbox clip (plain video > black frames)
            letterbox_ok = run_ffmpeg([
                "-ss", str(start), "-i", clip_path,
                "-t", str(actual_dur), "-an",
                "-vf", (
                    "scale=716:370:force_original_aspect_ratio=decrease,"
                    "pad=716:370:(ow-iw)/2:(oh-ih)/2:color=0x0A0A0F,"
                    "format=yuv420p"
                ),
                "-c:v", "libx264", "-crf", "17", "-preset", "ultrafast",
                "-r", "30",
                output_path,
            ], "pip letterbox fallback", 120)
            if letterbox_ok and os.path.exists(output_path):
                logger.info(f"PiP: letterbox fallback rendered for {os.path.basename(clip_path)}")
                return output_path
            return ""

        # FIX: blackdetect validation — catch continuous black frames in first 3s
        try:
            import re as _re_bd
            bd_result = subprocess.run(
                ["ffmpeg", "-i", output_path, "-vf", "blackdetect=d=0.1:pix_th=0.10",
                 "-an", "-t", "3", "-f", "null", "-"],
                capture_output=True, text=True, timeout=15)
            black_durations = _re_bd.findall(r"black_duration:\s*([\d.]+)", bd_result.stderr)
            total_black = sum(float(d) for d in black_durations)
            check_dur = min(3.0, pip_out_dur)
            if check_dur > 0 and total_black / check_dur > 0.5:
                logger.error(f"PiP BLACKDETECT: {total_black:.1f}s/{check_dur:.1f}s black in first 3s — discarding")
                try:
                    os.remove(output_path)
                except OSError:
                    pass
                # Generate dark placeholder instead
                run_ffmpeg([
                    "-f", "lavfi", "-i", f"color=c=0x0A0A0F:s=716x370:d={actual_dur}:r=30",
                    "-t", str(actual_dur), "-an",
                    "-c:v", "libx264", "-crf", "17", "-preset", "ultrafast",
                    "-r", "30", "-pix_fmt", "yuv420p",
                    output_path,
                ], "pip blackdetect placeholder", 30)
                if os.path.exists(output_path):
                    logger.info(f"PiP: dark placeholder after blackdetect failure ({actual_dur:.1f}s)")
                    return output_path
                return ""
        except Exception:
            pass  # blackdetect check failed — continue with existing output

        logger.info(f"PiP verified: {pip_out_dur:.1f}s, {frame_count} frames, YAVG={mean_brightness:.1f} from {clip_path}")
        return output_path
    return ""


def _ensure_pip_placeholder(channel_name: str = "", topic_title: str = "") -> str:
    """Generate branded PiP placeholder with channel name + topic text overlay.

    Session fix 3c: Never show black frame — show dark card with text instead.
    """
    # Use channel-specific placeholder if names provided
    if channel_name or topic_title:
        safe_channel = _sanitize_text(channel_name or "PARTNER CHANNEL")[:30]
        safe_topic = _sanitize_text(topic_title or "COMING UP")[:40]
        placeholder_path = PIP_PLACEHOLDER + f".{hash(channel_name + topic_title) & 0xFFFF:04x}.mp4"
        ok = run_ffmpeg([
            "-f", "lavfi", "-i",
            f"color=c=0x111111:s=716x370:d=8:r=30",
            "-vf",
            (f"drawbox=x=0:y=0:w=716:h=3:color={COLOR_RED}:t=fill,"
             f"drawtext=fontfile={FONT_BOLD}:text='{safe_channel}':"
             f"fontcolor={COLOR_WHITE}:fontsize=28:x=(w-text_w)/2:y=140,"
             f"drawtext=fontfile={FONT_MONO}:text='{safe_topic}':"
             f"fontcolor={COLOR_MUTED}:fontsize=20:x=(w-text_w)/2:y=185"),
            "-c:v", "libx264", "-crf", "20", "-preset", "ultrafast",
            "-an",
            placeholder_path,
        ], "generate branded pip placeholder", 30)
        if ok and os.path.exists(placeholder_path):
            logger.info(f"PiP branded placeholder: {safe_channel} / {safe_topic}")
            return placeholder_path

    # Fallback: generic dark placeholder
    if os.path.exists(PIP_PLACEHOLDER) and os.path.getsize(PIP_PLACEHOLDER) > 10000:
        return PIP_PLACEHOLDER
    ok = run_ffmpeg([
        "-f", "lavfi", "-i",
        "color=c=0x111111:s=716x370:d=8:r=30",
        "-vf",
        (f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
         f"fontcolor={COLOR_RED}@0.5:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2"),
        "-c:v", "libx264", "-crf", "20", "-preset", "ultrafast",
        "-an",
        PIP_PLACEHOLDER,
    ], "generate dark pip placeholder", 60)
    if ok and os.path.exists(PIP_PLACEHOLDER):
        logger.info(f"PiP placeholder generated (branded fallback): {PIP_PLACEHOLDER}")
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
        # FIX 4: Dark fallback instead of bg_loop mosaic
        logger.warning("PiP preview missing for clip — using dark fallback")
        pip_path = _ensure_pip_placeholder()
        if not pip_path:
            logger.info(f"PiP: no preview available, using narration-only for this segment")
            return narration_path
        logger.info(f"PiP: using dark placeholder for this segment")
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
        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
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


def make_cold_open_scene(audio_path: str, headline: str, body: str, tag: str,
                          output_path: str, btc_price: str = "N/A",
                          duration: float = 0,
                          episode_title: str = "PULSE CHECK") -> str:
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
    # FIX 3: Episode title pill
    fg += _add_episode_title_pill("co_railed", "_co_pilled", episode_title, total_dur)
    fg += _ken_burns_motion("_co_pilled", "outv", total_dur)

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX cold open",
                       audio_pad=co_audio_pad)


def make_narrator_pip_scene(audio_path: str, headline: str, body: str,
                             speaker: str, next_speaker: str,
                             thumb_path: str, output_path: str,
                             btc_price: str = "N/A", duration: float = 0,
                             pip_video_path: str = "",
                             episode_title: str = "PULSE CHECK") -> str:
    """Narrator + PiP split: left panel waveform/text, right panel looping video."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur
    total_frames = max(int(total_dur * 30), 30)

    safe_head = _sanitize_text(headline)
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""
    safe_btc = _sanitize_text(btc_price) if btc_price else "$N/A"

    inputs = [audio_path]
    # FIX 2: Use bg_loop via _get_bg_layer() instead of procedural color base
    fg = _get_bg_layer(inputs, total_dur, "base")

    # === LEFT PANEL (x=0..960): episode title + segment topic + sponsor carousel ===

    # ── TOP THIRD (y=40..340): PULSE CHECK kicker + episode title ──
    safe_ep_title = _sanitize_text(episode_title or "PULSE CHECK")[:40]
    _ep_l1, _ep_l2 = _split_headline_for_render(safe_ep_title, max_line_chars=22)
    _ep_fs = 36 if _ep_l2 else 48

    fg += (f"[base]"
           # Session fix 4a: Clean dark left panel overlay (masks bg_loop on left half)
           f"drawbox=x=0:y=0:w=960:h=1080:color=0x0d0d0d@0.92:t=fill,"
           f"drawbox=x=46:y=50:w=2:h=990:color={COLOR_RED}@0.12:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='LIVE INTELLIGENCE':"
           f"fontcolor={COLOR_RED}@0.25:fontsize=11:x=55:y=58,"
           # Red accent line at top of left panel
           f"drawbox=x=40:y=80:w=80:h=3:color={COLOR_RED}:t=fill,"
           # "PULSE CHECK" kicker — red monospace uppercase
           f"drawtext=fontfile={FONT_MONO}:text='PULSE CHECK':"
           f"fontcolor={COLOR_RED}:fontsize=22:x=40:y=100,"
           # Episode title line 1 — large white bold
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ep_l1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_ep_fs}:x=40:y=140")
    if _ep_l2:
        fg += (f",drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ep_l2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_ep_fs}:x=40:y={140 + _ep_fs + 8}")
    # BTC price in gold under title
    _btc_y = 140 + (_ep_fs + 8) * (2 if _ep_l2 else 1) + 16
    fg += (f",drawtext=fontfile={FONT_MONO}:text='BTC {safe_btc}':"
           f"fontcolor={COLOR_GOLD}:fontsize=20:x=40:y={_btc_y}"
           f"[lp_top];\n")

    # ── MIDDLE (y=360..580): segment topic + audio waveform ──
    _l1, _l2 = _split_headline_for_render(safe_head, max_line_chars=28)
    _seg_fs = 24 if _l2 else 32

    # Segment topic glass card background
    fg += (f"[lp_top]"
           f"drawbox=x=30:y=360:w=900:h=180:color=0x000000@0.45:t=fill,"
           # Red left accent on segment card
           f"drawbox=x=30:y=360:w=3:h=180:color={COLOR_RED}:t=fill,"
           # "NOW PLAYING" micro-label
           f"drawtext=fontfile={FONT_MONO}:text='NOW PLAYING':"
           f"fontcolor={COLOR_RED}@0.8:fontsize=13:x=50:y=375,"
           # Segment headline
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_l1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_seg_fs}:x=50:y=400")
    if _l2:
        fg += (f",drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_l2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_seg_fs}:x=50:y={400 + _seg_fs + 6}")
    # Body text (if present)
    if safe_body:
        _body_y = 400 + (_seg_fs + 6) * (2 if _l2 else 1) + 12
        fg += (f",drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
               f"fontcolor={COLOR_WHITE}@0.6:fontsize=16:x=50:y={_body_y}:line_spacing=6")
    fg += f"[lp_mid];\n"

    # Audio waveform — compact, below segment card
    fg += (f"[0:a]showwaves=s=900x80:mode=cline:colors={COLOR_RED}@0.7|{COLOR_RED}@0.3:"
           f"rate=30,format=rgba[waveform];\n")
    fg += f"[lp_mid][waveform]overlay=30:555:shortest=1[lp_wave];\n"

# ── BOTTOM THIRD (y=680..1040): daily sponsor card ──
    # Session fix 7a: Daily sponsor rotation (Curated Mining / Meanwhile / River)
    import datetime as _dt_sp_nar
    _NAR_SPONSORS = [
        {"name": "CURATED MINING", "tagline": "White-glove Bitcoin mining", "url": "curatedmining.io"},
        {"name": "MEANWHILE", "tagline": "Bitcoin Life Insurance", "url": "meanwhile.bm"},
        {"name": "RIVER", "tagline": "Buy Bitcoin. Earn Bitcoin.", "url": "river.com"},
    ]
    _nar_sp = _NAR_SPONSORS[_dt_sp_nar.date.today().timetuple().tm_yday % len(_NAR_SPONSORS)]
    _sp_name = _nar_sp["name"]
    _sp_tagline = _nar_sp["tagline"]
    _sp_url = _nar_sp["url"]

    # "PARTNERS" section label + daily sponsor card
    fg += (f"[lp_wave]"
           f"drawbox=x=40:y=670:w=60:h=2:color={COLOR_RED}@0.6:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='PARTNERS':"
           f"fontcolor={COLOR_RED}@0.7:fontsize=13:x=40:y=680,"
           # Daily sponsor card (single card, rotates daily)
           f"drawbox=x=40:y=710:w=880:h=120:color=0x111111@0.82:t=fill,"
           f"drawbox=x=40:y=710:w=3:h=120:color={COLOR_RED}:t=fill,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sp_name}':"
           f"fontcolor={COLOR_WHITE}:fontsize=24:x=60:y=730,"
           f"drawtext=fontfile={FONT_MONO}:text='{_sp_tagline}':"
           f"fontcolor={COLOR_WHITE}@0.65:fontsize=16:x=60:y=762,"
           f"drawtext=fontfile={FONT_MONO}:text='{_sp_url}':"
           f"fontcolor={COLOR_GOLD}:fontsize=14:x=60:y=795,"
           # Watermark at bottom-left
           f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
           f"fontcolor={COLOR_RED}@0.4:fontsize=12:x=40:y=1040"
           f"[left_done];\n")


    # === RIGHT PANEL (x=960..1920): looping PiP video or solid dark ===
    has_pip = bool(pip_video_path and os.path.exists(pip_video_path)
                   and os.path.getsize(pip_video_path) > 10000)

    if has_pip:
        inputs.append(["-stream_loop", "-1", "-i", pip_video_path])
        pip_idx = len(inputs) - 1
        # Trim stream_loop output to total_dur, reset PTS to prevent freeze frames
        fg += (f"[{pip_idx}:v]trim=0:{total_dur},setpts=PTS-STARTPTS,"
               f"scale=960:1080:force_original_aspect_ratio=increase,"
               # Session fix 3d: Face centering — crop biased to upper 30% where faces sit
               f"crop=960:1080:(iw-960)/2:'max(0,(ih-1080)*0.3)',setsar=1,fps=30,"
               # Session fix 3a: Neutral gray PIP — desaturate fully, no red tint
               f"hue=s=0.0,"
               f"eq=saturation=0.0:brightness=0.0,"
               f"setpts=PTS-STARTPTS[pip_panel];\n")
    else:
        # No PiP — solid dark right panel
        fg += f"color=c=0x0A0A0F:s=960x1080:d={total_dur}:r=30[pip_panel];\n"

    # Composite right panel onto base at x=960
    fg += f"[left_done][pip_panel]overlay=960:0:shortest=1[composited];\n"

    # 2px red border at x=958 separating left/right panels
    fg += (f"[composited]drawbox=x=958:y=0:w=2:h=1080:color={COLOR_RED}:t=fill"
           f"[_pip_bordered];\n")
    # FIX 3: Episode title pill
    fg += _add_episode_title_pill("_pip_bordered", "_pip_pilled", episode_title, total_dur)
    fg += _ken_burns_motion("_pip_pilled", "outv", total_dur)

    # Audio: PBX narration only, no music
    fg += f"[0:a]alimiter=limit=0.85,aresample=48000[outa]"

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "fast",
         "-b:v", "8M", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
         "-t", str(total_dur)],
        output_path, "narrator+pip split", 300,
    )
    return output_path if ok else ""


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

    # v3-phase1a: use bg_loop.mp4 when available (procedural fallback)
    fg = _get_bg_layer(inputs, total_dur, label_out="bd_bg")

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
           f"text='  SIGNAL ANALYSIS // ACTIVE':"
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

    # ── CORNER BRACKETS ── (EPISODE SEGMENTS debug overlay removed)
    fg += f"[dp_done]copy[seg_clean];\n"
    fg += _build_corner_brackets_fg("seg_clean", "cornered")

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
        fg += _ken_burns_motion("v_social", "outv", total_dur)
    else:
        fg += _ken_burns_motion("v_final", "outv", total_dur)

    # Audio: TTS only — APEX V2: music mixed continuously in concatenate_parts()
    fg += (f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,alimiter=limit=0.85:level=disabled:attack=5:release=50[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "fast",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label or f"host visual ({speaker})", 180,
    )

    if ok:
        return output_path

    logger.error(f"Waveform filtergraph FAILED for {label} — no silent fallback, raising")
    raise RuntimeError(f"Host visual filtergraph failed for {label}. Check ffmpeg stderr in logs.")
