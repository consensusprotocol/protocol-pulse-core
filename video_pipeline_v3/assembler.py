#!/usr/bin/env python3
"""Assembler V10 — Episode orchestrator with modular render pipeline.

Episode structure:
  1. INTRO: intro_tag.mp4 + PBX cold open voice-over
  2. SEGMENTS: setup/clip/react/data/social/signal cycles
  3. OUTRO: branded outro (own music) or tag video fallback
  4. MASTERING: continuous BGM, LUFS normalization, whoosh SFX

Modular architecture (V4 session 2):
  - assembler_common.py → Shared constants, FFmpeg utilities, visual building blocks
  - render_intro_outro.py → Intro/outro/cold-open/wrap scene rendering
  - render_narrator.py  → Narrator PiP scenes, host visual
  - render_clip.py      → Partner clip scenes, Remotion helpers, transitions
  - render_social.py    → Social stack, signal active, space tap scenes
  - render_data.py      → Data dashboard scene rendering
  - audio_master.py     → LUFS normalization, sidechain ducking
  - transitions.py      → Crossfade transitions between segments
  - lower_thirds.py     → Branded lower third overlays
"""
import json
import os
import re
import shutil
import subprocess

import assembler_common
from assembler_common import (
    logger, run_ffmpeg, run_ffmpeg_filtergraph, ffprobe_duration,
    ffprobe_video_duration, ensure_audio, get_video_encoder,
    _enforce_av_sync, _generate_fallback_silent_audio,
    _fetch_btc_price, _get_live_metric, _is_nostr_spam_assembler,
    _smart_headline, _sanitize_text,
    BASE, ASSETS, FONT_BOLD, FONT_MONO,
    COLOR_RED, COLOR_WHITE, COLOR_GOLD,
    BG_LOOP, INTRO_TAG, INTRO_MUSIC_FILE,
    GLITCH_WHOOSH, CARD_SWOOSH, PIP_PLACEHOLDER, OUTRO_BRANDED_NEW,
    _whoosh_applied_parts,
)
from render_intro_outro import (
    make_intro_video, make_outro_video, make_tag_video,
    make_intro_tag_sequence, make_intro_coldopen,
    _make_clip_unavailable_card, make_branded_outro, make_outro_branded_new,
    make_wrap_scene,
)
from render_narrator import (
    make_cold_open_scene, make_narrator_pip_scene, make_host_visual,
    fetch_youtube_thumbnail, make_pip_preview, _ensure_pip_placeholder,
    overlay_pip_on_narration, mix_lower_slide_sfx,
)
from render_clip import (
    make_partner_clip_scene, make_clip_visual,
    make_transition_visual, apply_xfade, normalize_part,
    make_remotion_lower_third,
)
from render_social import (
    make_social_stack_scene, make_social_card_visual,
    make_signal_active_scene, make_space_tap_scene,
    _mix_swoosh_into_segment, make_remotion_social_card,
)
from render_data import make_data_segment_scene


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
    elif segment_type == "space_tap":
        return "space_tap"
    elif segment_type == "x_spaces":
        return "data_segment"  # X Spaces uses data_segment visual with branded eyebrow
    elif segment_type in ("wrap", "outro", "signoff") or segment_index == total_segments - 1:
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
    speaker = segment_data.get("speaker", "PBX")  # PBX solo mode — single host
    episode_title = segment_data.get("episode_title", "PULSE CHECK")
    scene = select_scene_type(seg_type, segment_index, total_segments)

    try:
        if scene == "cold_open":
            return make_cold_open_scene(
                audio_path, headline, text, "REDLINE",
                output_path, btc_price=btc_price,
                episode_title=episode_title,
            )
        elif scene == "narrator_pip":
            next_speaker = segment_data.get("next_speaker", "")
            return make_narrator_pip_scene(
                audio_path, headline, text, speaker, next_speaker,
                thumbnail_path, output_path, btc_price=btc_price,
                pip_video_path=pip_video_path,  # FIX 1: pass actual video
                episode_title=episode_title,
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
                script_text=text,
                episode_title=episode_title,
            )
        elif scene == "social_stack":
            return make_social_stack_scene(
                audio_path, headline, social_posts or [],
                output_path, btc_price=btc_price,
                episode_title=episode_title,
            )
        elif scene == "wrap":
            return make_wrap_scene(
                audio_path, headline, text,
                output_path, btc_price=btc_price,
                episode_title=episode_title,
            )

        elif scene == "space_tap":
            space_clips = segment_data.get("space_clips", [])
            return make_space_tap_scene(
                audio_path, space_clips,
                output_path, btc_price=btc_price,
                episode_title=episode_title,
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
        is_wrap_part = "wrap" in pbase_norm
        v_fade = 0.15 if is_clip_part else 0.03
        a_fade_in = 0.15 if is_clip_part else 0.03
        a_fade_out = 0.3 if is_clip_part else (0.0 if is_wrap_part else 0.03)  # V16: no fade on signoff
        fade_out_start_v = max(0, dur - v_fade)
        _enc = get_video_encoder(crf=17)
        ok = run_ffmpeg(
            ["-i", p] + _enc + [
             "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
             "-r", "30", "-vsync", "cfr",
             "-vf", f"fps=30,setpts=PTS-STARTPTS,scale=1920:1080,setsar=1,format=yuv420p,fade=t=in:d={v_fade},fade=t=out:st={fade_out_start_v}:d={v_fade}",
             "-video_track_timescale", "15360",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
             "-af", f"aresample=48000,{'volume=8dB,' if is_wrap_part else ''}afade=t=in:d={a_fade_in}{(',afade=t=out:st=' + str(max(0, dur - a_fade_out - 0.05)) + ':d=' + str(a_fade_out)) if a_fade_out > 0 else ''}",
             tmp],
            "normalize+fade", 180,
        )
        chosen = tmp if (ok and os.path.exists(tmp)) else p
        # BLACK HOLE GUARD (FIX 3): scan for >0.5s of black mid-part, re-render or replace
        # pix_th=0.05 catches #0A0A0F bg color (Y≈10/255≈0.039) which pix_th=0.02 missed
        try:
            bd = subprocess.run(
                ["ffmpeg", "-i", chosen,
                 "-vf", "blackdetect=d=0.5:pix_th=0.05",
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
                    _fc = f"[0:v]trim=0:{part_dur + 0.5},setpts=PTS-STARTPTS,scale=1920:1080,setsar=1,eq=brightness=-0.15:contrast=0.9[outv]"
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
        # AV SYNC FIX: Enforce matching V/A durations per-part before concat
        # Prevents accumulated drift from parts where audio ≠ video duration
        chosen = _enforce_av_sync(chosen)
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
                 "-af", f"aresample=48000,afade=t=in:d=0.1,afade=t=out:st={fade_a_start:.2f}:d=2.5",
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

    # TS-based concatenation: convert parts → MPEG-TS → concat protocol → re-encode
    # Fixes timestamp inflation caused by mixed timebases in MP4 concat demuxer
    concat_raw = output_path + ".concat_raw.mp4"
    ts_files = []
    for ci, cp in enumerate(normalized):
        ts_path = cp + ".ts"
        ts_ok = run_ffmpeg(
            ["-i", cp,
             "-c", "copy", "-bsf:v", "h264_mp4toannexb",
             "-f", "mpegts", ts_path],
            f"ts convert part {ci}", 30,
        )
        if ts_ok and os.path.exists(ts_path):
            ts_files.append(ts_path)
        else:
            logger.warning(f"TS convert failed for part {ci} — using MP4 fallback")
            ts_files.append(cp)
    ts_concat_str = "|".join(ts_files)
    ok = run_ffmpeg(
        ["-fflags", "+genpts",
         "-i", f"concat:{ts_concat_str}",
         "-c:v", "libx264", "-crf", "17", "-preset", "fast",
         "-r", "30", "-vsync", "cfr",
         "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
         "-af", "asetpts=PTS-STARTPTS",
         "-avoid_negative_ts", "make_zero",
         "-movflags", "+faststart",
         concat_raw],
        "TS concat re-encode", 600,
    )
    # Clean up TS files
    for ts_path in ts_files:
        if ts_path.endswith(".ts") and os.path.exists(ts_path):
            try:
                os.remove(ts_path)
            except OSError:
                pass

    if not ok or not os.path.exists(concat_raw):
        logger.error("Concat demuxer failed")
        return ""

    # APEX V2 FIX 2: Continuous BGM — infinite loop, duration=longest, no gaps
    # BGM loops infinitely via -stream_loop -1, trimmed to episode+5s safety buffer.
    # amix duration=longest ensures BGM never cuts short at clip boundaries.
    # FIX 1+4: Volume envelope ducks BGM to -28dB during partner clips, -24dB during PiP narration
    from music import ffprobe_duration as _music_ffprobe_dur
    has_bgm = os.path.exists(assembler_common.BG_MUSIC)
    if has_bgm:
        _ac = __import__("subprocess").run(["ffprobe","-v","error","-select_streams","a","-show_entries","stream=codec_type","-of","csv=p=0",concat_raw],capture_output=True,text=True,timeout=15)
        if "audio" not in _ac.stdout:
            raise RuntimeError("[ABORT] concat_raw has no audio stream - TTS was not embedded")
        dur = _music_ffprobe_dur(concat_raw)
        if dur > 0:
            # If branded outro, fade BGM out before outro starts
            if skip_outro_fade and valid:
                outro_dur_est = ffprobe_duration(valid[-1])
                bgm_fade_st = max(0, dur - outro_dur_est - 0.5)  # V15 FIX: was -3.0, fading signoff
            else:
                bgm_fade_st = max(0, dur - 3.0)

            # V12 FIX: Segment-aware music ducking
            # Narration: 0.22 (prominent), Clips: 0.04 (near silent), Social: 0.15
            cumulative_t = 0.0
            clip_ranges = []
            social_ranges = []
            for p in valid:
                pdur = ffprobe_duration(p)
                pbase = os.path.basename(p).lower()
                t_start = cumulative_t
                t_end = cumulative_t + pdur
                cumulative_t = t_end
                if "clip_r" in pbase or ("clip_" in pbase and "partner" not in pbase):
                    clip_ranges.append((t_start, t_end))
                elif "social" in pbase or "signal" in pbase:
                    social_ranges.append((t_start, t_end))
            if clip_ranges or social_ranges:
                # Build volume expression: 0.04 during clips, 0.15 during social, 0.22 otherwise
                clip_conds = [f"between(t,{s:.3f},{e:.3f})" for s, e in clip_ranges]
                social_conds = [f"between(t,{s:.3f},{e:.3f})" for s, e in social_ranges]
                # Nested if: check clips first (lowest), then social, then default
                vol_inner = "0.22"
                if social_conds:
                    social_test = "+".join(social_conds)
                    vol_inner = f"if({social_test},0.15,0.22)"
                if clip_conds:
                    clip_test = "+".join(clip_conds)
                    vol_inner = f"if({clip_test},0.04,{vol_inner})"
                vol_expr = f"volume='{vol_inner}':eval=frame"
                bgm_vol_filter = f"{vol_expr},afade=t=in:d=4.0,afade=t=out:st={bgm_fade_st}:d=3.0"
            else:
                bgm_vol_filter = f"volume=0.22,afade=t=in:d=4.0,afade=t=out:st={bgm_fade_st}:d=3.0"

            music_mixed = output_path + ".music_mixed.mp4"
            ok_music = run_ffmpeg([
                "-fflags", "+genpts",
                "-i", concat_raw,
                "-stream_loop", "-1", "-i", assembler_common.BG_MUSIC,
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
                    f"threshold=0.04:ratio=4:attack=5:release=200[bgm_ducked];"
                    # V11 FIX 1: amix weight 1:1 — volume envelope controls BGM level directly
                    f"[tts_main][bgm_ducked]amix=inputs=2:duration=first"
                    f":weights=1 1[mixed_audio];"
                    f"[mixed_audio]aresample=48000[outa]"
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
            ], "continuous bgm mix (infinite loop)", max(600, int(dur * 0.25)))
            if ok_music and os.path.exists(music_mixed):
                logger.info(f"  APEX V2: Continuous BGM mixed — infinite loop ({dur:.1f}s episode)")
                concat_raw = music_mixed
            else:
                logger.warning("  APEX V2: BGM mix failed — proceeding without music")
    else:
        logger.warning("  APEX V2: No BG_MUSIC file found — no music bed")

    # Round 3 FIX 4: Skip intro_music.mp3 if ANY intro part already has music baked in.
    # make_intro_coldopen() already mixes intro_music.mp3 with TTS — adding it again
    # in concatenate_parts() causes double intro music.
    # make_intro_tag_sequence() uses intro_tag.mp4 which has baked-in audio.
    # make_intro_video() uses intro.mp4 which has baked-in jingle.
    skip_intro_music = any(
        ("intro_tag" in os.path.basename(p).lower() or
         "intro_pbx" in os.path.basename(p).lower() or
         "intro_hook" in os.path.basename(p).lower() or
         "intro_video" in os.path.basename(p).lower())
        for p in valid
    )
    if skip_intro_music:
        logger.info("  FIX 4: Skipping intro_music.mp3 — intro part already has audio baked in")

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
                (f"[1:a]volume=0.08,atrim=0:8.0,"
                 f"asetpts=PTS-STARTPTS,"
                 f"afade=t=out:st=6.0:d=2.0,aresample=48000[im];"
                 f"[0:a][im]amix=inputs=2:duration=first:weights=1 0.3[outa]"),
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
            # V4.2 FIX 1: bg_loop raised — floor -16dB (0.16), transitions -12dB (0.25), boundaries -14dB (0.20)
            vol_expr_parts = []
            cumulative = 0.0
            for pidx, p in enumerate(valid):
                pdur = ffprobe_duration(p)
                t_start = cumulative
                cumulative += pdur
                pbase = os.path.basename(p).lower()
                if "transition" in pbase or "glitch" in pbase:
                    # V4.2: -12dB for transitions (clearly audible ambient)
                    vol_expr_parts.append(f"between(t,{t_start:.3f},{cumulative:.3f})*0.25")
                elif pidx > 0:
                    # V4.2: -14dB for 1.0s around each part boundary
                    vol_expr_parts.append(f"between(t,{max(0,t_start-0.5):.3f},{t_start+0.5:.3f})*0.20")
            if vol_expr_parts:
                # V4.2: floor 0.16 (-16dB) elsewhere — present atmospheric bed
                vol_filter = "volume='if(" + "+".join(f"({vp})" for vp in vol_expr_parts) + f",1,0.16)':eval=frame"
            else:
                vol_filter = "volume=0.12"
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

    # FIX 6 DISABLED: Episode-level whoosh mastering caused DOUBLE WHOOSH at transitions.
    # Root cause: make_transition_visual() already bakes whoosh into each transition segment,
    # and _mix_swoosh_into_segment() adds swoosh to social cards. This episode-level pass
    # then added ANOTHER whoosh at every boundary — producing 2-3 overlapping whooshes.
    # Per-segment whoosh is sufficient. Do NOT re-enable without removing per-segment whoosh first.
    has_whoosh = False  # was: os.path.exists(GLITCH_WHOOSH)
    if has_whoosh and len(valid) > 1:
        # Calculate transition timestamps (cumulative durations of each part)
        # SFX fires AT the boundary (offset=0 relative to cut point)
        transition_times = []
        cumulative = 0.0
        for pidx, p in enumerate(valid[:-1]):
            pdur = ffprobe_duration(p)
            cumulative += pdur
            # Place whoosh exactly at the cut point (subtract 0.05s so SFX starts
            # just before the visual cut for perceived synchronization)
            t_whoosh = max(0, cumulative - 0.05)
            transition_times.append(t_whoosh)

        # 2-second dedup: remove any whoosh within 2s of a previous one
        deduped_times = []
        for t in transition_times:
            if not deduped_times or (t - deduped_times[-1]) >= 2.0:
                deduped_times.append(t)
            else:
                logger.info(f"  WHOOSH DEDUP: Skipping whoosh at {t:.2f}s (within 2s of {deduped_times[-1]:.2f}s)")
        transition_times = deduped_times

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
                    f"[ws{ti}]volume=2.5,loudnorm=I=-12:TP=-1.5:LRA=3,alimiter=limit=0.9,adelay={delay_ms}|{delay_ms}[whoosh_{ti}]"
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

    # V17 FIX: Dynamic AV sync — measure PTS offset BEFORE final encode
    _av_compensation = 0.043  # safe default
    try:
        _avr = __import__("subprocess").run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_packets", "-read_intervals", "%+#5", concat_raw],
            capture_output=True, text=True, timeout=15)
        _avd = __import__("json").loads(_avr.stdout)
        _avpkts = _avd.get("packets", [])
        _v_pts = next((float(p.get("pts_time", 0)) for p in _avpkts if p.get("codec_type") == "video"), 0)
        _a_pts = next((float(p.get("pts_time", 0)) for p in _avpkts if p.get("codec_type") == "audio"), 0)
        _pts_offset = _a_pts - _v_pts
        if _pts_offset < -0.005:
            _av_compensation = abs(_pts_offset) + 0.043  # V19 FIX: doubled to cover itsoffset priming
        else:
            _av_compensation = 0.043
        logger.info(f"  AV SYNC: Input offset {_pts_offset:+.4f}s -> compensation +{_av_compensation:.4f}s")
    except Exception as _e:
        logger.warning(f"  AV SYNC: measurement failed ({_e}) — fallback +0.043s")

    # Final encode: nuclear PTS reset + AV sync lock + BUG5 single authoritative loudnorm
    # CRF 15 + minrate 3.5M floor to guarantee ≥3.5Mbps output (was CRF 17 → 2.8Mbps on dark content)
    # V4.3 FIX 5: NVENC for final encode (10-50x faster on RTX 4090)
    _final_enc = get_video_encoder(crf=15)
    ok = run_ffmpeg(
        ["-fflags", "+genpts+igndts+discardcorrupt",
         "-i", concat_raw,
         "-itsoffset", f"{abs(_av_compensation):.6f}",
         "-i", concat_raw,
         "-map", "0:v:0", "-map", "1:a:0"] + _final_enc + [
         "-b:v", "8M", "-minrate", "3.5M", "-maxrate", "10M", "-bufsize", "15M",
         "-r", "30", "-vsync", "cfr",
         "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
         # BUG5 FIX: Single authoritative loudnorm at end (removed from all intermediate steps)
         # V4.2 FIX 8: loudnorm I=-14 TP=-1.0 LRA=11 — broadcast standard (MUST be LAST audio filter)
         # V9 FIX 9: True peak brick wall — alimiter AFTER loudnorm with attack=0.1 (near-zero lookahead)
         "-af", "aresample=48000:min_hard_comp=0.1:first_pts=0,loudnorm=I=-14:TP=-2.0:LRA=11:linear=true,alimiter=limit=0.75:level=disabled:attack=5:release=50",
         "-avoid_negative_ts", "make_zero",
         "-max_interleave_delta", "0",
         "-movflags", "+faststart",
         output_path],
        "concat final encode", max(600, int(dur * 0.25)),
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

    # Validate inputs before assembly
    from validators import validate_clip_response
    if not isinstance(script, dict) or not script.get("dialogue"):
        logger.error("ASSEMBLY ABORT: script missing or has no dialogue")
        return ""
    if not isinstance(audio_data, dict) or not audio_data.get("lines"):
        logger.error("ASSEMBLY ABORT: audio_data missing or has no lines")
        return ""
    if not extracted_clips:
        logger.error("ASSEMBLY ABORT: no extracted clips provided")
        return ""

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
    # FIX 1: Transition out of partner/clip/space_tap into data/intelligence
    if prev_part in ("partner", "space_tap") and next_part in ("data", "social_segment"):
        return True
    # FIX 1: Transition out of data/intelligence into social/signal_active
    if prev_part == "data" and next_part in ("social_segment", "signal_active"):
        return True
    # FIX 1: Transition out of social into signal_active
    if prev_part == "social_segment" and next_part == "signal_active":
        return True
    # NO transition for narrator-to-narrator within same flow
    # e.g., setup→setup, react→react, cold_open→setup
    return False




def _make_filler_segment(work_dir: str, idx: int, audio_path: str) -> str:
    """Generate a dark filler segment with narration audio still playing.
    FIX iter1: Use bg_loop instead of static color to prevent freeze-frame detection.
    """
    out = os.path.join(work_dir, f"part_{idx:03d}_filler.mp4")
    dur = ffprobe_duration(audio_path) if audio_path and os.path.exists(audio_path) else 15.0
    has_audio = bool(audio_path and os.path.exists(audio_path))
    # FIX iter1: Use bg_loop (animated) instead of static color=0x0A0A0F
    # Static color frames are detected as freeze frames by freezedetect
    if os.path.exists(BG_LOOP):
        args = ["-stream_loop", "-1", "-i", BG_LOOP]
        vf = (f"scale=1920:1080,setsar=1,fps=30,"
              f"trim=0:{dur + 2.0},setpts=PTS-STARTPTS,"
              f"eq=brightness=-0.15:contrast=0.9")
    else:
        args = ["-f", "lavfi", "-i", f"color=c=0x0A0A0F:s=1920x1080:d={dur}:r=30"]
        vf = None
    if has_audio:
        args.extend(["-i", audio_path])
    else:
        args.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
    if vf:
        args.extend([
            "-vf", vf,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(dur), out
        ])
    else:
        args.extend([
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(dur), out
        ])
    run_ffmpeg(args, "filler segment", 30)
    return out if os.path.exists(out) else ""


def _assemble_episode_inner(script, audio_data, extracted_clips,
                            output_path, btc_price="N/A", music_bed="", intro_music="",
                            broll_clips=None):
    # V8 FIX 3: Clear whoosh dedup set at episode start — prevents stale dedup from prior render
    global _whoosh_applied_parts
    _whoosh_applied_parts.clear()
    logger.info(f"  WHOOSH: dedup set cleared, GLITCH_WHOOSH={'EXISTS' if os.path.exists(GLITCH_WHOOSH) else 'MISSING'} ({GLITCH_WHOOSH})")

    # FIX 5: Fetch BTC price if not provided or showing N/A
    if not btc_price or btc_price in ("N/A", "$N/A", ""):
        btc_price = _fetch_btc_price()
        logger.info(f"  BTC price fetched: {btc_price}")

    # Issue 12: Override default BG_MUSIC with mood-matched music bed if provided
    # Ensure music is mixed at -20dB under ALL narration segments
    if music_bed and os.path.exists(music_bed):
        assembler_common.BG_MUSIC = music_bed
        logger.info(f"  Music bed ACTIVE: {os.path.basename(music_bed)}")
    elif os.path.exists(assembler_common.BG_MUSIC):
        logger.info(f"  Music bed ACTIVE (default): {os.path.basename(assembler_common.BG_MUSIC)}")
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
        # FIX 9: Log source file and tweet details for debugging
        _src = script_social_posts[0].get("source", "unknown") if script_social_posts else "none"
        logger.info(f"  R25 FIX 6: SOCIAL ORDER (from script only): {len(tweet_card_posts)} posts (source: {_src})")
        for ti, tp in enumerate(tweet_card_posts):
            logger.info(f"    POST #{ti}: @{tp.get('handle', '?')} — {tp.get('text', '')[:50]}... (ss: {tp.get('screenshot_path', 'none')})")
    else:
        logger.info("  R25 FIX 6: No social_posts in script — skipping tweet cards (no fetcher fallback)")

    if tweet_card_posts:
        tweet_card_posts.sort(key=lambda p: p.get("display_order", 0))
        logger.info(f"  SOCIAL POST ORDER (final):")
        for ti, tp in enumerate(tweet_card_posts):
            logger.info(f"    CARD #{ti}: @{tp.get('handle', '?')} — {tp.get('text', '')[:40]}")

        # NEW: ID-based binding — extract [ID:tweet_XXXXXXXX_N] from narration
        _social_dialogue = [d for d in dialogue if d.get("type") == "social_segment"
                            and d.get("host") in (1, 2, "1", "2")]

        # Extract seg_ids from narration in order
        _narrator_seg_ids = []
        for sd in _social_dialogue:
            id_match = re.search(r'\[ID:(tweet_[a-f0-9]+_\d+)\]', sd.get("text", ""))
            if id_match:
                _narrator_seg_ids.append(id_match.group(1))

        # Build seg_id → post map
        _seg_id_to_post = {tp.get("seg_id", ""): tp for tp in tweet_card_posts if tp.get("seg_id")}

        if _narrator_seg_ids and _seg_id_to_post:
            # Reorder tweet_card_posts to EXACTLY match narration order by seg_id
            reordered = []
            for sid in _narrator_seg_ids:
                if sid in _seg_id_to_post:
                    reordered.append(_seg_id_to_post.pop(sid))
            # Append any remaining posts not mentioned (shouldn't happen but safe fallback)
            reordered.extend(_seg_id_to_post.values())
            if reordered:
                tweet_card_posts = reordered
                for ri, rp in enumerate(tweet_card_posts):
                    rp["display_order"] = ri
                logger.info(f"  ID-BIND: Reordered {len(reordered)} tweet cards by seg_id — GUARANTEED MATCH")
                for ri, rp in enumerate(tweet_card_posts):
                    logger.info(f"    BOUND #{ri}: seg_id={rp.get('seg_id')} @{rp.get('handle')} → narration seg {ri}")
        else:
            logger.warning("  ID-BIND: No seg_ids found in narration — falling back to handle matching")
            # Fallback: old @handle matching for backwards compat
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
        # ISSUE 1 FIX: Log exact cold open TTS path and file size for debugging
        _co_path = cold_open_audio["path"]
        try:
            _co_size = os.path.getsize(_co_path)
        except OSError:
            _co_size = -1
        logger.info(f"  COLD OPEN TTS: path={_co_path} size={_co_size}B exists={os.path.exists(_co_path)}")
        if _co_size <= 0:
            # Fallback: find first valid audio file in audio/ directory
            _audio_dir = os.path.dirname(_co_path) if _co_path else ""
            if _audio_dir and os.path.isdir(_audio_dir):
                _sorted_audio = sorted(f for f in os.listdir(_audio_dir) if f.endswith(('.m4a', '.mp3', '.wav')))
                for _af in _sorted_audio:
                    _af_path = os.path.join(_audio_dir, _af)
                    if os.path.getsize(_af_path) > 1000:
                        cold_open_audio = dict(cold_open_audio)
                        cold_open_audio["path"] = _af_path
                        logger.warning(f"  COLD OPEN FIX: Original TTS empty/missing, using fallback: {_af_path}")
                        break
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

    # Build PiP preview map: rank → pip_path (A/B rotation)
    # Session fix 3b: Extract TWO clips per topic — clip_a at 15%, clip_b at 60%
    # R25 FIX 1: Also search output/clips/ as fallback for PiP source
    pip_previews = {}    # rank → pip_path (clip_a for setup, used as default)
    pip_previews_b = {}  # rank → pip_path (clip_b for react/recap)
    for rank, cinfo in extracted_clips.items():
        clip_path = cinfo.get("path", "")
        if clip_path and os.path.exists(clip_path):
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

            def _verify_pip(pip_result, rank_val, label):
                """Verify PiP is real video, not dark placeholder."""
                if not pip_result:
                    return None
                try:
                    _pip_br = subprocess.run(
                        ["ffmpeg", "-v", "error", "-ss", "1",
                         "-i", pip_result, "-vframes", "3",
                         "-vf", "signalstats", "-f", "null", "-"],
                        capture_output=True, text=True, timeout=15)
                    _yavg_vals = re.findall(r"YAVG:\s*([\d.]+)", _pip_br.stderr)
                    _mean_y = sum(float(v) for v in _yavg_vals) / len(_yavg_vals) if _yavg_vals else 999
                except Exception:
                    _mean_y = 999
                if _mean_y < 12:
                    logger.info(f"  FIX 6: PiP {label} for clip #{rank_val} is dark (YAVG={_mean_y:.1f}) — skipping")
                    return None
                logger.info(f"  PiP {label} for clip #{rank_val}: ready (YAVG={_mean_y:.1f})")
                return pip_result

            # Clip A: 15% into content (for setup/intro narration)
            pip_out_a = os.path.join(work_dir, f"pip_preview_r{rank}_a.mp4")
            pip_a = make_pip_preview(pip_source, pip_out_a, position_pct=0.15)
            pip_a = _verify_pip(pip_a, rank, "clip_a")
            if not pip_a:
                # FIX: Retry at 40% — channels with dark intros (Simply Bitcoin etc.)
                # fail at 15% because trimmed clip starts with logo/overlay frames
                pip_out_a2 = os.path.join(work_dir, f"pip_preview_r{rank}_a_retry.mp4")
                pip_a = make_pip_preview(pip_source, pip_out_a2, position_pct=0.40)
                pip_a = _verify_pip(pip_a, rank, "clip_a@40%")
            if pip_a:
                pip_previews[rank] = pip_a

            # Clip B: 60% into content (for react/recap narration)
            pip_out_b = os.path.join(work_dir, f"pip_preview_r{rank}_b.mp4")
            pip_b = make_pip_preview(pip_source, pip_out_b, position_pct=0.60)
            pip_b = _verify_pip(pip_b, rank, "clip_b")
            if not pip_b:
                # FIX: Retry at 80% for channels with dark midpoints
                pip_out_b2 = os.path.join(work_dir, f"pip_preview_r{rank}_b_retry.mp4")
                pip_b = make_pip_preview(pip_source, pip_out_b2, position_pct=0.80)
                pip_b = _verify_pip(pip_b, rank, "clip_b@80%")
            if pip_b:
                pip_previews_b[rank] = pip_b
            elif pip_a:
                # If clip_b failed, fallback to clip_a for react segments too
                pip_previews_b[rank] = pip_a

    audio_idx = 1 if cold_open_consumed else 0
    prev_segment_type = "intro"

    # Render22 FIX 7: Signal Active segment — load real content
    signal_content = None
    try:
        from signal_intelligence import get_signal_content, generate_signal_summary
        signal_content = get_signal_content()
        # FIX 4: Filter nostr spam at source before any rendering
        if signal_content and "nostr_posts" in signal_content:
            _pre_filter = len(signal_content["nostr_posts"])
            signal_content["nostr_posts"] = [
                p for p in signal_content["nostr_posts"]
                if not _is_nostr_spam_assembler(p)
            ]
            _post_filter = len(signal_content["nostr_posts"])
            if _pre_filter != _post_filter:
                logger.info(f"  FIX 4: Filtered {_pre_filter - _post_filter} nostr spam posts")
        if signal_content and (signal_content.get("spaces_quotes") or signal_content.get("nostr_posts") or signal_content.get("x_posts")):
            logger.info(f"  FIX 7: Signal intelligence loaded — {len(signal_content.get('spaces_quotes', []))} spaces, {len(signal_content.get('nostr_posts', []))} nostr, {len(signal_content.get('x_posts', []))} x_posts")
        elif signal_content and signal_content.get("nostr_posts"):
            # FIX 7: Even with empty spaces, nostr-only is valid signal content
            logger.info(f"  FIX 7: Signal intelligence (nostr only) — {len(signal_content.get('nostr_posts', []))} nostr posts, 0 spaces")
        else:
            signal_content = None
            logger.info("  FIX 7: No signal intelligence available")
    except Exception as _sig_err:
        logger.warning(f"  FIX 7: Signal intelligence import failed: {_sig_err}")

    # V10 FIX: Dedup signal x_posts against tweet card posts BEFORE main loop.
    # Ensures narration AND visuals both exclude posts already shown as tweet cards.
    if signal_content and signal_content.get("x_posts") and tweet_card_posts:
        _used_handles = {tp.get("handle", "").lower().lstrip("@") for tp in tweet_card_posts}
        _used_texts = {tp.get("text", "")[:80].lower() for tp in tweet_card_posts if tp.get("text")}
        _before = len(signal_content["x_posts"])
        signal_content["x_posts"] = [
            p for p in signal_content["x_posts"]
            if (p.get("handle", "").lower().lstrip("@") not in _used_handles
                and p.get("text", "")[:80].lower() not in _used_texts)
        ]
        _after = len(signal_content["x_posts"])
        if _before != _after:
            logger.info(f"  V10 POST DEDUP: Removed {_before - _after} x_posts that overlap with tweet cards")

    # V11 FIX 2: Minimum 3 posts in Signal Active (x_posts + nostr combined).
    # If after dedup + spam filter we have fewer than 3, pad from x_posts cache.
    if signal_content:
        _total = len(signal_content.get("x_posts", [])) + len(signal_content.get("nostr_posts", []))
        if _total < 3:
            _need = 3 - _total
            try:
                from signal_intelligence import _read_x_posts
                _extra = _read_x_posts(max_posts=_need + 5)
                _existing_handles = {p.get("handle", "").lower() for p in signal_content.get("x_posts", [])}
                _existing_handles |= {tp.get("handle", "").lower().lstrip("@") for tp in tweet_card_posts} if tweet_card_posts else set()
                _padded = 0
                for xp in _extra:
                    if xp.get("handle", "").lower() not in _existing_handles:
                        signal_content.setdefault("x_posts", []).append(xp)
                        _existing_handles.add(xp.get("handle", "").lower())
                        _padded += 1
                        if _padded >= _need:
                            break
                if _padded:
                    logger.info(f"  V11 FIX 2: Padded Signal Active with {_padded} extra x_posts (was {_total}, now {_total + _padded})")
            except Exception as _pad_err:
                logger.warning(f"  V11 FIX 2: Could not pad Signal Active: {_pad_err}")

    past_wrap = False  # BUG 8 FIX: Guard flag to skip clips after wrap/outro
    for i, entry in enumerate(dialogue):
        entry_type = entry.get("type", "")
        host_field = entry.get("host", "")

        if cold_open_consumed and i == 0 and host_field != "CLIP":
            cold_open_consumed = False
            continue

        # BUG 8 FIX: Skip clip segments after wrap — prevents random clip after "stay sovereign" outro
        if past_wrap and host_field == "CLIP":
            logger.info(f"  BUG 8 FIX: Skipping clip segment after wrap (dialogue {i})")
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

                # FIX CFR: Normalize clip to CFR 30fps h264 before visual render.
                # VFR/b-frame clips cause ffmpeg filtergraphs to silently produce black frames.
                cfr_clip = clip_path + ".cfr_clip.mp4"
                cfr_ok = run_ffmpeg([
                    "-i", clip_path,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-vsync", "cfr", "-r", "30", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                    cfr_clip,
                ], f"CFR pre-process clip #{rank}", 120)
                if cfr_ok and os.path.exists(cfr_clip) and os.path.getsize(cfr_clip) > 50_000:
                    clip_path = cfr_clip
                    logger.info(f"  FIX CFR: Clip #{rank} normalized to CFR 30fps")
                else:
                    if os.path.exists(cfr_clip):
                        try:
                            os.remove(cfr_clip)
                        except OSError:
                            pass
                    logger.warning(f"  FIX CFR: Clip #{rank} CFR pre-process failed, using original")

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
                        # V9 FIX 1: Waveform visualization from audio (better than bare bg_loop)
                        waveform_out = clip_out + ".waveform.mp4"
                        clip_audio_dur_wf = ffprobe_duration(clip_path)
                        wf_ok = run_ffmpeg([
                            "-i", clip_path,
                            "-filter_complex",
                            f"[0:a]showwaves=s=1920x1080:mode=cline:rate=30:colors={COLOR_RED}|0xFFFFFF@0.3,"
                            f"drawbox=x=0:y=0:w=1920:h=1080:color=0x0A0A0F@0.6:t=fill,"
                            f"drawtext=fontfile={FONT_BOLD}:text='{channel}':fontcolor=white:fontsize=36:x=60:y=50,"
                            f"drawtext=fontfile={FONT_MONO}:text='AUDIO ONLY':fontcolor={COLOR_RED}:fontsize=20:x=60:y=100[outv]",
                            "-map", "[outv]", "-map", "0:a",
                            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                            "-t", str(clip_audio_dur_wf), "-shortest",
                            waveform_out,
                        ], f"V9 waveform fallback clip #{rank}", 120)
                        if wf_ok and os.path.exists(waveform_out):
                            result = waveform_out
                            logger.info(f"  V9 FIX 1: Waveform fallback for clip #{rank}")
                        else:
                            if os.path.exists(waveform_out):
                                os.remove(waveform_out)
                        # Last resort: bg_loop video + clip audio
                        if not result and os.path.exists(BG_LOOP):
                            clip_audio_dur = ffprobe_duration(clip_path)
                            bg_fallback_out = clip_out + ".bgfallback.mp4"
                            bg_ok = run_ffmpeg([
                                "-stream_loop", "-1", "-i", BG_LOOP,
                                "-i", clip_path,
                                "-map", "0:v", "-map", "1:a",
                                "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                                "-vf", f"trim=0:{clip_audio_dur + 0.5},setpts=PTS-STARTPTS,scale=1920:1080,setsar=1,fps=30",
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
                    # FIX 8: Ensure 0.5s audio fade-out on clip end to prevent abrupt cutoff
                    _clip_dur = ffprobe_duration(result)
                    if _clip_dur > 1.0:
                        _fade_tmp = result + ".fadeout.mp4"
                        _fade_st = max(0, _clip_dur - 0.5)
                        _fade_ok = run_ffmpeg([
                            "-i", result,
                            "-c:v", "copy",
                            "-af", f"afade=t=out:st={_fade_st:.3f}:d=0.5",
                            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                            _fade_tmp,
                        ], f"FIX8 clip fade-out #{rank}", 60)
                        if _fade_ok and os.path.exists(_fade_tmp):
                            os.replace(_fade_tmp, result)
                        elif os.path.exists(_fade_tmp):
                            os.remove(_fade_tmp)
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

        host_num = int(line_audio.get("host", 2)) if str(line_audio.get("host", "2")).isdigit() else 2
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
        # V8 FIX 1: Process ONE card per social_segment entry (was: all remaining).
        # Each social_segment dialogue entry has its own TTS audio line. Processing
        # all cards in the first entry consumed audio lines for entries 14/15, causing
        # "No audio entry for dialogue N (social_segment) — skipping".
        if entry_type == "social_segment" and tweet_card_posts and social_card_idx < len(tweet_card_posts):
            card_posts = [tweet_card_posts[social_card_idx]]
            # FIX 4: CARD ORDER LOCK — never re-sort, script_writer order is gospel
            logger.info(f"[SOCIAL] passing {len(card_posts)} cards to segment {part_idx}")

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
                # FIX 9: Log card-screenshot match for debugging
                _ss = cp.get("screenshot_path", "")
                _ss_handle = os.path.basename(_ss).split("_")[1] if _ss and "_" in os.path.basename(_ss) else "none"
                _card_handle = cp.get("handle", "?").lstrip("@").lower()
                if _ss and _ss_handle.lower() != _card_handle:
                    logger.warning(f"  FIX 9: SCREENSHOT MISMATCH! Card @{_card_handle} has screenshot for {_ss_handle}")
                    cp.pop("screenshot_path", None)  # remove mismatched screenshot
                logger.info(f"  SOCIAL CARD {ci}: @{cp.get('handle', '?')} — {cp.get('text', '')[:40]} (ss: {os.path.basename(_ss) if _ss else 'none'})")

                # V8 FIX 1: One card per social_segment entry — always use this entry's audio
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
                    # AV SYNC FIX: Enforce per-card sync before xfade stitching
                    _enforce_av_sync(card_result)
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
                    # AV SYNC FIX: Enforce sync after each xfade to prevent cascading drift
                    if xfade_result:
                        _enforce_av_sync(xfade_result)
                        current_stitched = xfade_result
                    else:
                        parts.append(current_stitched)
                        current_stitched = card_rendered_paths[xfi]
                        part_idx += 1
                if os.path.exists(CARD_SWOOSH) and len(card_rendered_paths) > 1:
                    swoosh_mixed = current_stitched + ".swoosh.mp4"
                    card_durs = [ffprobe_duration(p) for p in card_rendered_paths]
                    # Skip swoosh if any card < 2s — adelay filter fails on very short clips
                    _min_card_dur = min(card_durs) if card_durs else 0
                    if _min_card_dur < 2.0:
                        logger.info(f"  SWOOSH SKIP: card too short ({_min_card_dur:.1f}s < 2.0s min)")
                    else:
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
                            _whoosh_applied_parts.add(os.path.abspath(swoosh_mixed))
                # FIX 3: Audio fade-out on social segment to prevent narrator cutoff at boundary
                _social_dur = ffprobe_duration(current_stitched)
                if _social_dur > 1.0:
                    _sfade_tmp = current_stitched + ".audiofade.mp4"
                    _sfade_st = max(0, _social_dur - 0.5)
                    _sfade_ok = run_ffmpeg([
                        "-i", current_stitched,
                        "-c:v", "copy",
                        "-af", f"afade=t=out:st={_sfade_st:.3f}:d=0.5",
                        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                        _sfade_tmp,
                    ], "Fix3 social audio fade-out", 60)
                    if _sfade_ok and os.path.exists(_sfade_tmp):
                        os.replace(_sfade_tmp, current_stitched)
                        logger.info(f"  FIX 3: Audio fade-out applied to social segment ({_sfade_st:.1f}s)")
                    elif os.path.exists(_sfade_tmp):
                        os.remove(_sfade_tmp)
                # AV SYNC FIX: Enforce matching video/audio durations after xfade stitching
                # Social xfade can accumulate drift (audio longer than video) which breaks concat
                _enforce_av_sync(current_stitched)
                parts.append(current_stitched)
                dur = ffprobe_duration(current_stitched)
                logger.info(f"[{part_idx:03d}] SOCIAL CARDS (xfaded): {dur:.1f}s")
                part_idx += 1
            elif len(card_rendered_paths) == 1:
                # FIX 3: Audio fade-out on single social card too
                _single_card = card_rendered_paths[0]
                _sc_dur = ffprobe_duration(_single_card)
                if _sc_dur > 1.0:
                    _sc_fade_tmp = _single_card + ".audiofade.mp4"
                    _sc_fade_st = max(0, _sc_dur - 0.5)
                    _sc_fade_ok = run_ffmpeg([
                        "-i", _single_card,
                        "-c:v", "copy",
                        "-af", f"afade=t=out:st={_sc_fade_st:.3f}:d=0.5",
                        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                        _sc_fade_tmp,
                    ], "Fix3 single social card audio fade-out", 60)
                    if _sc_fade_ok and os.path.exists(_sc_fade_tmp):
                        os.replace(_sc_fade_tmp, _single_card)
                        logger.info(f"  FIX 3: Audio fade-out applied to single social card ({_sc_fade_st:.1f}s)")
                    elif os.path.exists(_sc_fade_tmp):
                        os.remove(_sc_fade_tmp)
                parts.append(_single_card)
                dur = ffprobe_duration(_single_card)
                logger.info(f"[{part_idx:03d}] SOCIAL CARD (single): {dur:.1f}s")
                part_idx += 1

            social_card_idx += len(card_posts)
            prev_segment_type = entry_type

            # V9 FIX 5 moved to early dedup (before main loop) — see V10 POST DEDUP above

            # Render24 FIX 4: Signal Active as its own segment after tweet cards
            if signal_content and (signal_content.get("spaces_quotes") or signal_content.get("nostr_posts") or signal_content.get("x_posts")):
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
            try:
                result = make_host_visual(
                    audio_path, host_num, text, line_out,
                    btc_price=btc_price, label=f"{entry_type} #{part_idx}",
                    segment_type=entry_type,
                )
                if result and not os.path.exists(result):
                    result = ""
            except Exception as _seg_err:
                logger.error(f"SEGMENT FAILED: {entry_type} — {_seg_err}")
                result = ""
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
            # V4.2 FIX 4: EVERY narration segment gets PiP — no bare bg for >5s
            pip_vid = ""
            # V4.3 FIX: Any non-cold_open segment without PiP gets nearest clip preview
            _any_pip = next((v for v in list(pip_previews.values()) + list(pip_previews_b.values()) if v and os.path.exists(v)), "")
            if entry_type == "cold_open":
                pip_vid = ""
            elif entry_type in ("setup", "react") and clip_rank:
                # Session fix 3b: A/B rotation — SETUP uses clip_a, REACT uses clip_b
                if entry_type == "react":
                    pip_vid = pip_previews_b.get(clip_rank, pip_previews.get(clip_rank, ""))
                else:
                    pip_vid = pip_previews.get(clip_rank, "")
                logger.info(f"  PiP clip #{clip_rank} path: {pip_vid or 'NONE'}")
                # FIX 2: NEVER use intro_tag as PiP source
                if pip_vid and os.path.abspath(pip_vid) == os.path.abspath(INTRO_TAG):
                    logger.error(f"  FIX 2: BLOCKED intro_tag.mp4 as PiP source! Using fallback.")
                    pip_vid = ""
                if not pip_vid:
                    # V4.2 FIX 4: Try NEXT available clip as PiP preview
                    for _fallback_rank in sorted(pip_previews.keys()):
                        if _fallback_rank != clip_rank and pip_previews.get(_fallback_rank):
                            pip_vid = pip_previews[_fallback_rank]
                            logger.info(f"  V4.2 FIX 4: Using clip #{_fallback_rank} PiP as fallback for #{clip_rank}")
                            break
                if not pip_vid:
                    if os.path.exists(BG_LOOP):
                        pip_vid = BG_LOOP
                        logger.info(f"  FIX 1: Using bg_loop as PiP placeholder for {entry_type.upper()} → clip #{clip_rank}")
                    elif entry_type == "setup":
                        pip_vid = _ensure_pip_placeholder()
                        if pip_vid:
                            logger.info(f"  FIX 1: Using branded placeholder PiP for SETUP → clip #{clip_rank}")
            elif entry_type in ("data", "bridge", "wrap") and not pip_vid:
                # V4.2 FIX 4: Non-clip segments also get PiP — use any available preview
                for _fallback_rank in sorted(pip_previews.keys()):
                    if pip_previews.get(_fallback_rank):
                        pip_vid = pip_previews[_fallback_rank]
                        logger.info(f"  V4.2 FIX 4: Using clip #{_fallback_rank} PiP for {entry_type.upper()} segment")
                        break
                if not pip_vid and os.path.exists(BG_LOOP):
                    pip_vid = BG_LOOP
                    logger.info(f"  V4.2 FIX 4: bg_loop PiP for {entry_type.upper()} segment")
            if pip_vid and pip_vid != PIP_PLACEHOLDER:
                logger.info(f"  FIX 3: PiP video embedded for {entry_type.upper()} → clip #{clip_rank}")

            # Render22 FIX 7: Signal Active segment — replace debug data with real content
            if seg_data.get("headline", "").startswith("SIGNAL") and signal_content:
                    seg_data["signal_content"] = signal_content

            # V4.3: FINAL PiP FALLBACK — no segment should have empty PiP for >5s
            if not pip_vid and entry_type not in ("cold_open",) and _any_pip:
                pip_vid = _any_pip
                logger.info(f"  PiP FALLBACK: {entry_type} using nearest available clip")

            try:
                # FIX 5: Pass social_posts at every handoff
                result = make_broadcast_segment(
                    seg_data, audio_path, host_num,
                    part_idx, len(dialogue),
                    line_out, btc_price=btc_price,
                    thumbnail_path=thumb,
                    social_posts=tweet_card_posts,
                    pip_video_path=pip_vid,
                )
                if result and not os.path.exists(result):
                    result = ""
            except Exception as _seg_err:
                logger.error(f"SEGMENT FAILED: {entry_type} — {_seg_err}")
                result = ""

        if result:
            parts.append(result)
            dur = ffprobe_duration(result)
            logger.info(f"[{part_idx:03d}] {entry_type.upper()} [PBX]: {dur:.1f}s")
            part_idx += 1
            prev_segment_type = entry_type
            host_segment_count += 1
            # BUG 8 FIX: Set past_wrap flag after wrap segment to prevent trailing clips
            if entry_type == "wrap":
                past_wrap = True
                # FIX: Warn if wrap segment is too short (< 4s = abrupt ending)
                wrap_dur = ffprobe_duration(result)
                if wrap_dur < 4.0:
                    logger.warning(f"WRAP TOO SHORT: {wrap_dur:.1f}s — episode may end abruptly (target >= 4s)")

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
            logger.error(f"SEGMENT FAILED: {entry_type} — inserting filler")
            filler_out = _make_filler_segment(work_dir, part_idx, audio_path)
            if filler_out:
                parts.append(filler_out)
                _filler_dur = ffprobe_duration(filler_out)
                logger.info(f"[{part_idx:03d}] FILLER ({entry_type.upper()}): {_filler_dur:.1f}s")
                part_idx += 1
                prev_segment_type = entry_type

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
    logger.info("Assembler V10 — Modular render pipeline")
    logger.info("Modules: audio_master, transitions, lower_thirds, render_segment, render_intro, render_outro")
    logger.info("Use daily_producer.py to run the full pipeline")
