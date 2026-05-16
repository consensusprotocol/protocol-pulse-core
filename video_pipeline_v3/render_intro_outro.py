#!/usr/bin/env python3
"""Intro, outro, cold open, and wrap scene rendering for Protocol Pulse episodes."""
import os
import subprocess

from assembler_common import (
    logger, run_ffmpeg, run_ffmpeg_filtergraph, ffprobe_duration,
    BASE, ASSETS, FONT_BOLD, FONT_MONO,
    COLOR_BG, COLOR_RED, COLOR_WHITE, COLOR_GOLD, COLOR_MUTED, COLOR_PANEL,
    COLOR_GREEN, COLOR_CORAL, COLOR_RED_DIM, COLOR_PANEL2,
    INTRO_VIDEO, OUTRO_VIDEO, TAG_VIDEO, OUTRO_BRANDED, INTRO_TAG,
    INTRO_MUSIC_FILE, BG_LOOP, OUTRO_BRANDED_NEW,
    ensure_audio, _sanitize_text, _word_wrap, _split_headline_for_render,
    _get_bg_layer, _build_top_system_bar, _build_corner_brackets_fg,
    _build_signature_info_rail, _add_episode_title_pill,
    _ken_burns_motion, _bv2_encode,
)


def make_intro_video(output_path: str) -> str:
    """Use branded intro.mp4 — its audio track IS the intro jingle.

    intro.mp4 already has the jingle baked in. Do NOT mix pp_intro.mp3 on top
    or you get double intro sounds. Just normalize video+audio and apply fades.
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

    if intro_has_audio:
        # intro.mp4 already has jingle baked in — use its audio, do NOT add pp_intro.mp3
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-vf", vf,
            "-af", f"afade=t=out:st={fade_out_a}:d=1.5",
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(intro_dur),
            output_path,
        ], "intro video (baked audio)", 120)
    elif has_jingle and not intro_has_audio:
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-i", jingle_path,
            "-filter_complex",
            (f"[0:v]{vf}[outv];"
             f"[1:a]afade=t=out:st={fade_out_a}:d=1.5[outa]"),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(intro_dur), "-shortest",
            output_path,
        ], "intro video + jingle (no orig audio)", 120)
    else:
        ok = run_ffmpeg([
            "-i", INTRO_VIDEO,
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
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
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
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
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(outro_dur), "-shortest",
            output_path,
        ], "outro video + jingle (no orig audio)", 120)
    else:
        ok = run_ffmpeg([
            "-i", OUTRO_VIDEO,
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
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
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(tag_dur),
            output_path,
        ], "tag video + narration", 60)
    else:
        ok = run_ffmpeg([
            "-i", tag_src,
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-pix_fmt", "yuv420p", "-vf", vf,
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            output_path,
        ], "tag video", 60)

    if ok and os.path.exists(output_path):
        dur = ffprobe_duration(output_path)
        logger.info(f"  Tag video: {dur:.1f}s{' (with narration)' if narration_audio else ''}")
        return output_path

    return ""


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
            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
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
            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
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

        # FIX iter1: Replace tpad=stop_mode=clone with loop — cloning the last
        # frame creates literal freeze frames detected by freezedetect. Instead,
        # loop the intro tag so it stays animated beyond its natural duration.
        vid_dur = max(total_dur, tag_dur)
        # loop=-1 infinite loops all frames, then trim to exact duration needed
        tag_frames = max(1, int(tag_dur * 30))
        vf = (f"scale=1920:1080,setsar=1,format=yuv420p,"
              f"loop=-1:size={tag_frames}:start=0,"
              f"trim=0:{vid_dur + 0.5},setpts=PTS-STARTPTS")

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
                        # BUG 7 FIX: Reduced intro music volume (0.05→0.03), narrator starts sooner (300→100ms),
                        # boosted TTS weight (3.0→4.0) so narrator isn't drowned by music
                        f"[2:a]atrim=0:8.0,asetpts=PTS-STARTPTS,afade=t=out:st=6.0:d=2.0,volume=0.03,"
                        f"asetpts=PTS-STARTPTS[intro_mus];"
                        f"[1:a]aformat=channel_layouts=stereo,adelay=100|100[tts_delayed];"
                        f"[intro_mus][tts_delayed]amix=inputs=2:duration=longest:weights=0.3 4.0,"
                        f"alimiter=limit=0.85:level=disabled:attack=5:release=50,"
                        f"aresample=48000[outa]"
                    ),
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-crf", "17", "-preset", "fast",
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
                        f"[1:a]aformat=channel_layouts=stereo,adelay=300|300,"
                        f"alimiter=limit=0.85:level=disabled:attack=5:release=50,"
                        f"aresample=48000[outa]"
                    ),
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-crf", "17", "-preset", "fast",
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
                    f"aresample=48000[outa]"
                ),
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-crf", "17", "-preset", "fast",
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
           f"alimiter=limit=0.85:level=disabled:attack=5:release=50,aresample=48000[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "fast",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "clean cold open (fallback)", 120,
    )
    return output_path if ok else ""


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
        f"[_uc_pre];"
        f"[_uc_pre]scale=1960:1102:flags=lanczos,"
        f"crop=1920:1080:'20*t/{dur}':'11*t/{dur}',setsar=1[outv]",
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
        "-b:v", "8M", "-maxrate", "10M", "-bufsize", "15M",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-t", str(dur),
        output_path,
    ], "clip_unavailable_card", 30)
    return output_path if ok and os.path.exists(output_path) else ""


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
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", output_path],
            "branded outro", 60)
    else:
        ok = run_ffmpeg([
            "-i", src, "-vf", vf,
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k", output_path],
            "branded outro", 60)

    if ok and os.path.exists(output_path):
        out_dur = ffprobe_duration(output_path)
        logger.info(f"  Branded outro: {out_dur:.1f}s{' (with narration)' if narration_audio else ''}")
        return output_path
    return ""


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
        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
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


def make_wrap_scene(audio_path: str, headline: str, body: str,
                     output_path: str, btc_price: str = "N/A",
                     duration: float = 0,
                     episode_title: str = "PULSE CHECK") -> str:
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
           f"drawbox=x=1120:y=140:w=0:h=0:color=0x000000@0:t=fill"
           f"[wr_panel];\n")
    # FIX 3: Single asplit for ALL audio consumers in wrap scene
    # 1=big waveform, 2+3=narration wave (primary+accent)
    fg += f"[0:a]asplit=4[_wr_a_big][_wr_a_nav1][_wr_a_nav2][_wr_a_out];\n"

    # Large waveform inside panel
    fg += (f"[_wr_a_big]showwaves=s=700x350:mode=cline:"
           f"colors={COLOR_RED}|{COLOR_WHITE}:scale=sqrt:draw=full:rate=30[wr_sigwave];\n")
    fg += f"[wr_panel][wr_sigwave]overlay=1140:220[wr_waved];\n"

    # DUAL-HOST DISABLED — PBX SOLO MODE (segment tracker removed)
    fg += f"[wr_waved]copy[wr_clean];\n"

    fg += _build_corner_brackets_fg("wr_clean", "wr_corners")

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
    # FIX 3: Episode title pill
    fg += _add_episode_title_pill("wr_railed", "_wr_pilled", episode_title, total_dur)
    # Session 4 Fix 7: Extended fade-to-black (1.5s) and audio fade (2.5s) for clean ending
    fade_v_start = max(0, total_dur - 1.5)
    fade_a_start = max(0, total_dur - 2.5)
    dur_kb = max(0.1, total_dur)
    fg += (f"[_wr_pilled]scale=1960:1102:flags=lanczos,"
           f"crop=1920:1080:'20*t/{dur_kb:.2f}':'11*t/{dur_kb:.2f}',setsar=1,"
           f"fade=t=out:st={fade_v_start:.2f}:d=1.5:color=0x0A0A0F,"
           f"format=yuv420p[outv];\n")
    fg += (f"[_wr_a_out]afade=t=out:st={fade_a_start:.2f}:d=2.5[_wr_a_faded];\n")

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX wrap",
                       audio_pad="[_wr_a_faded]")
