from __future__ import annotations
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text
from ..constants import (
    VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT,
    VIDEO_CODEC, VIDEO_CRF,
    AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
    INTRO_TAG, INTRO_MUSIC, COLOR_BG, FONT_BOLD, FONT_MONO,
    COLOR_RED, COLOR_WHITE, COLOR_CYAN,
    FFMPEG_TIMEOUT_FILTER
)
logger = logging.getLogger(__name__)
FREEZE_FRAME_BUFFER_S = 1.0  # Extra frames after tag ends so fade-out has video to work on


class ColdOpenSegment(Segment):
    """
    Cold open: intro_tag.mp4 plays with intro_music.mp3 fading under PBX narration.
    Audio law (confirmed working from old pipeline):
      - intro_music: volume=0.05, fades out at 6s
      - PBX TTS: delayed 300ms, amix weight=3.0 vs music weight=0.5
      - amix duration=first — TTS anchors the output length
    """
    criticality = "required"

    def render(self, spec: SegmentSpec, ctx: EpisodeContext,
               output_path: Path, idx: int) -> RenderedSegment:
        try:
            return self._render(spec, ctx, output_path)
        except Exception as e:
            logger.error(f"[cold_open] exception: {e}")
            return self.filler_result(spec, ctx, output_path, str(e))

    def _render(self, spec: SegmentSpec, ctx: EpisodeContext,
                output_path: Path) -> RenderedSegment:
        tts = spec.tts()
        if not tts or not tts.exists() or tts.stat().st_size < 1000:
            return self.filler_result(spec, ctx, output_path, "TTS missing")

        tts_dur = ffprobe_duration(tts)
        if tts_dur < 0.5:
            return self.filler_result(spec, ctx, output_path, "TTS silent")

        # intro_tag provides the visual; its duration caps the segment
        tag_dur = ffprobe_duration(INTRO_TAG) if INTRO_TAG.exists() else 0.0
        total_dur = max(tts_dur, tag_dur if tag_dur > 0 else tts_dur)

        tmp = output_path.with_suffix(".tmp.mp4")

        if INTRO_TAG.exists() and INTRO_MUSIC.exists():
            ok = self._render_full(tts, tmp, tts_dur, tag_dur, total_dur)
        elif INTRO_TAG.exists():
            ok = self._render_tag_only(tts, tmp, tts_dur, tag_dur, total_dur)
        else:
            ok = self._render_tts_only(tts, tmp, tts_dur, spec)

        if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
            return self.filler_result(spec, ctx, output_path, "cold_open encode failed")

        passed, summary = ffprobe_contract(tmp)
        atomic_rename(tmp, output_path)
        dur = summary.get("duration", total_dur)
        logger.info(f"[cold_open] OK ({dur:.1f}s)")
        return RenderedSegment(
            spec=spec, path=str(output_path),
            duration=dur, contract_passed=passed,
            degraded=not passed, ffprobe_summary=summary
        )

    def _render_full(self, tts, tmp, tts_dur, tag_dur, total_dur):
        """Full cold open: intro tag video + music + PBX TTS."""
        # video: scale intro_tag, freeze last frame to fill TTS duration
        freeze_extra = max(0.0, tts_dur - tag_dur + FREEZE_FRAME_BUFFER_S)
        vf = (
            f"scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},"
            f"tpad=stop_mode=clone:stop_duration={freeze_extra:.3f}"
        )
        fg = (
            f"[0:v]{vf},fade=t=out:st={max(0,total_dur-0.4):.3f}:d=0.4[v_out];"
            # Music: trim to 8s, fade out at 6s, very quiet under voice
            f"[2:a]atrim=0:8.0,asetpts=PTS-STARTPTS,"
            f"afade=t=out:st=6.0:d=2.0,volume=0.05[mus];"
            # TTS: 300ms delay so music hits first, then PBX voice dominates
            f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
            f"adelay=300|300[tts];"
            # Mix: duration=first = TTS anchors length (confirmed working)
            f"[mus][tts]amix=inputs=2:duration=first:weights=0.5 3.0,"
            f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
            f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50,"
            f"aresample=async=1[a_out]"
        )
        return run_ffmpeg([
            "-i", str(INTRO_TAG),
            "-i", str(tts),
            "-i", str(INTRO_MUSIC),
            "-filter_complex", fg,
            "-map", "[v_out]", "-map", "[a_out]",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
            "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
            "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
            "-t", str(round(total_dur, 3)),
            "-movflags", "+faststart", str(tmp)
        ], "cold_open full", FFMPEG_TIMEOUT_FILTER)

    def _render_tag_only(self, tts, tmp, tts_dur, tag_dur, total_dur):
        """Intro tag video + TTS only (no music file)."""
        freeze_extra = max(0.0, tts_dur - tag_dur + FREEZE_FRAME_BUFFER_S)
        vf = (
            f"scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},"
            f"tpad=stop_mode=clone:stop_duration={freeze_extra:.3f}"
        )
        fg = (
            f"[0:v]{vf},fade=t=out:st={max(0,total_dur-0.4):.3f}:d=0.4[v_out];"
            f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
            f"adelay=300|300,"
            f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
            f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50,"
            f"aresample=async=1[a_out]"
        )
        return run_ffmpeg([
            "-i", str(INTRO_TAG), "-i", str(tts),
            "-filter_complex", fg,
            "-map", "[v_out]", "-map", "[a_out]",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
            "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
            "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
            "-t", str(round(total_dur, 3)),
            "-movflags", "+faststart", str(tmp)
        ], "cold_open tag-only", FFMPEG_TIMEOUT_FILTER)

    def _render_tts_only(self, tts, tmp, tts_dur, spec):
        """Fallback: dark background + TTS narration only."""
        safe_hl = safe_text(spec.headline or "PULSE CHECK", 60)
        fg = (
            f"[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg];"
            f"[bg]drawtext=fontfile={FONT_BOLD}:text='{safe_hl}':"
            f"fontcolor={COLOR_RED}:fontsize=72:"
            f"x=(w-text_w)/2:y=(h-text_h)/2[v_out];"
            f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
            f"adelay=300|300,"
            f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
            f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]"
        )
        return run_ffmpeg([
            "-f", "lavfi", "-i",
            f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
            "-i", str(tts),
            "-filter_complex", fg,
            "-map", "[v_out]", "-map", "[a_out]",
            "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
            "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
            "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
            "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
            "-t", str(round(tts_dur + 0.5, 3)),
            "-movflags", "+faststart", str(tmp)
        ], "cold_open tts-only fallback", FFMPEG_TIMEOUT_FILTER)
