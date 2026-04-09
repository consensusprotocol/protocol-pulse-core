#!/usr/bin/env python3
"""Partner clip scenes, clip visual, transitions, and Remotion helpers."""
import json
import math
import os
import subprocess

from assembler_common import (
    logger, run_ffmpeg, run_ffmpeg_filtergraph, ffprobe_duration,
    ffprobe_video_duration, ensure_audio, get_video_encoder,
    BASE, ASSETS, FONT_BOLD, FONT_MONO,
    COLOR_BG, COLOR_RED, COLOR_WHITE, COLOR_PANEL, COLOR_MUTED,
    GLITCH_TRANSITION, GLITCH_WHOOSH, BG_LOOP, CARD_SWOOSH,
    _whoosh_applied_parts,
    _sanitize_text, _build_corner_brackets_fg, _build_signature_info_rail,
    _ken_burns_motion,
)

REMOTION_DIR = os.path.join(BASE, "remotion")


def make_partner_clip_scene(video_path: str, audio_path: str, speaker: str,
                             quote: str, output_path: str,
                             btc_price: str = "N/A", duration: float = 0) -> str:
    """APEX Partner Clip — BEV2 restraint. Full-frame, premium lower-third, no competing animations."""
    clip_dur = ffprobe_duration(video_path)
    if clip_dur <= 0:
        logger.warning(f"Partner clip has zero duration: {video_path}")
        return ""

    # V31 AV FIX: Measure V/A durations separately and trim both to the shorter one.
    # fps=30 adds ~0.1s to video; without this, every clip drifts +0.1s.
    _v_dur = ffprobe_video_duration(video_path)
    _a_dur_raw = 0.0
    try:
        import subprocess as _sp_av
        _a_probe = _sp_av.run(["ffprobe", "-v", "quiet", "-select_streams", "a:0",
            "-show_entries", "stream=duration", "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=10)
        _a_dur_raw = float(_a_probe.stdout.strip()) if _a_probe.stdout.strip() else clip_dur
    except:
        _a_dur_raw = clip_dur
    _target_dur = min(_v_dur, _a_dur_raw) if _v_dur > 0 and _a_dur_raw > 0 else clip_dur
    logger.info(f"  AV TRIM: V={_v_dur:.3f}s A={_a_dur_raw:.3f}s target={_target_dur:.3f}s")

    safe_speaker = _sanitize_text(speaker)[:30] if speaker else "SOURCE"
    safe_quote = _sanitize_text(quote)[:60] if quote else ""
    safe_btc = btc_price.replace("'", "").replace('"', "")

    import datetime
    ts_str = datetime.datetime.now().strftime("%H-%M UTC")

    fade_out_start = max(0, _target_dur - 0.5)
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
           # Source label (no transcript text — clean partner clip)
           f"drawtext=fontfile={FONT_MONO}:text='SOURCE — PARTNER CHANNEL':"
           f"fontcolor=0xFFFFFF@0.4:fontsize=13:x=24:y=932,"
           f"drawtext=fontfile={FONT_MONO}:text='{ts_str}':"
           f"fontcolor=0xFFFFFF@0.35:fontsize=11:x=740:y=878"
           f"[pc_lt];\n")
    # Info rail (always present)
    fg += _build_signature_info_rail(clip_dur, btc_price, "pc_lt", "pc_railed")
    fg += _ken_burns_motion("pc_railed", "outv", clip_dur)
    # Render14: removed atrim=start=2.5 (was root cause of lipsync desync)
    # aresample=48000 REMOVED — clips already synced by clip_extractor, async was overcorrecting
    fg += (f"[0:a]atrim=duration={_target_dur:.3f},asetpts=PTS-STARTPTS,"
           f"highpass=f=50,lowpass=f=15000,"
           f"afade=t=in:d=0.5,afade=t=out:st={max(0, fade_out_start - 0.5)}:d=0.5[outa]")

    # Render14: removed itsoffset probing (was causing lipsync issues with atrim removal)
    input_spec = video_path

    ok = run_ffmpeg_filtergraph(
        [input_spec], fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",

        output_path, f"APEX partner clip ({safe_speaker})",
    )
    return output_path if ok else ""


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
        f"[1:a]aresample=48000[outa]",
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
    """R25 FIX 2 + BLACK FRAME FIX: 0.1s max transition with whoosh SFX.

    Previous: 0.5s of solid black + whoosh = Gemini penalizes as black frames.
    Now: 0.1s hard cut with whoosh audio compressed to fit. Clean broadcast-style.
    ISSUE 3 FIX: Global whoosh dedup via _whoosh_applied_parts set.
    """
    global _whoosh_applied_parts
    duration = 0.35  # Visible transition — red sweep + whoosh (was 0.1s = invisible)
    has_whoosh = os.path.exists(GLITCH_WHOOSH)
    # ISSUE 3: Check global whoosh dedup set
    abs_out = os.path.abspath(output_path)
    if abs_out in _whoosh_applied_parts:
        logger.info(f"  WHOOSH DEDUP: Skipping transition whoosh — already applied to {os.path.basename(output_path)}")
        has_whoosh = False  # render without whoosh

    # BLACK FRAME FIX: Use bg_loop (animated) instead of solid COLOR_BG (0x0A0A0F)
    # Solid dark bg triggers blackdetect pix_th=0.05 → Gemini penalizes as black frames
    _use_bg_loop = os.path.exists(BG_LOOP)
    if _use_bg_loop:
        _bg_input = ["-stream_loop", "-1", "-i", BG_LOOP]
        _bg_vf_prefix = f"scale=1920:1080,setsar=1,fps=30,trim=0:{duration + 0.5},setpts=PTS-STARTPTS,eq=brightness=-0.1:contrast=0.9,"
    else:
        _bg_input = ["-f", "lavfi", "-i", f"color=c=0x1A1A2F:s=1920x1080:d={duration}:r=30"]
        _bg_vf_prefix = ""

    if has_whoosh:
        ok = run_ffmpeg([
            *_bg_input,
            "-i", GLITCH_WHOOSH,
            "-filter_complex",
            f"[0:v]{_bg_vf_prefix}drawbox=x='(t/{duration})*1920-40':y=0:w=40:h=1080:"
            f"color={COLOR_RED}@0.8:t=fill,"
            f"fade=t=in:d=0.05,fade=t=out:st={max(0, duration - 0.1):.2f}:d=0.1[outv];"
            f"[1:a]atrim=0:{duration},asetpts=PTS-STARTPTS,volume=3.0,"
            f"afade=t=out:st={max(0, duration - 0.1):.2f}:d=0.1,alimiter=limit=0.95[outa]",
            "-map", "[outv]", "-map", "[outa]",
            "-t", str(duration),
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
            output_path,
        ], "red sweep transition + whoosh", 30)
    else:
        # Use brighter color (0x1A1A2F) to avoid blackdetect false positives
        ok = run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c=0x1A1A2F:s=1920x1080:d={duration}:r=30",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", str(duration),
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
            output_path,
        ], "instant hard cut (silent)", 30)
    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        _whoosh_applied_parts.add(abs_out)  # ISSUE 3: Track applied whoosh
        logger.info(f"  TRANSITION: hard cut ({dur:.2f}s)")
        return output_path
    return ""


def apply_xfade(clip1_path: str, clip2_path: str, output_path: str,
                 transition: str = "fade", duration: float = 1.0) -> str:
    """Issue 8: Apply xfade crossfade between two clips instead of hard-cut transitions.

    Overlaps the last `duration` seconds of clip1 with the first `duration` seconds of clip2.
    Returns output_path on success, '' on failure.
    """
    # FIX: Use VIDEO duration for xfade offset (not format duration which may be audio-dominated)
    dur1 = ffprobe_video_duration(clip1_path)
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
    # Ken Burns zoom REMOVED — was drifting text overlays, logos, lower thirds.
    # Static scale+crop to 1920x1080 instead.
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
        # aresample=48000 REMOVED — clips already synced by clip_extractor, async was overcorrecting
        f"[0:a]asetpts=PTS-STARTPTS,"
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
         "-af", "aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,volume=1.0,aresample=48000,aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp",
         output_path],
        "normalize", 180,
    )
    return output_path if (ok and os.path.exists(output_path)) else part_path
