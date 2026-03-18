from __future__ import annotations
import os
import logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text
from ..constants import (
    VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
    AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
    COLOR_BG, FONT_BOLD, FONT_MONO,
    FFMPEG_TIMEOUT_FILTER,
)

logger = logging.getLogger(__name__)

BRAND_RED = "0xE8272B"
CARD_BG = "0x141419"
META_GRAY = "0x888888"


class XSpacesSegment(Segment):
    """X Spaces intelligence segment — branded visual with TTS narration."""
    criticality = 'optional'

    def render(self, spec: SegmentSpec, ctx: EpisodeContext,
               output_path: Path, idx: int) -> RenderedSegment:
        try:
            return self._render(spec, ctx, output_path)
        except Exception as e:
            logger.error(f'[x_spaces] exception: {e}')
            return self.filler_result(spec, ctx, output_path, str(e))

    def _render(self, spec: SegmentSpec, ctx: EpisodeContext,
                output_path: Path) -> RenderedSegment:
        # Law 1: no content → filler
        if not spec.body:
            return self.filler_result(spec, ctx, output_path, 'no_x_spaces_content')

        # Get TTS audio
        tts = self._get_tts(spec, ctx)
        if not tts or not tts.exists() or tts.stat().st_size < 1000:
            return self.filler_result(spec, ctx, output_path, 'no_tts_for_x_spaces')

        dur = ffprobe_duration(tts)
        if dur < 0.5:
            dur = 10.0

        tmp = output_path.with_suffix('.tmp.mp4')
        fg = self._build_filter_graph(spec)

        ok = run_ffmpeg([
            '-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}',
            '-i', str(tts),
            '-filter_complex', fg,
            '-map', '[v_out]', '-map', '[a_out]',
            '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
            '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
            '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
            '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
            '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp),
        ], 'x_spaces', FFMPEG_TIMEOUT_FILTER)

        if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
            return self.filler_result(spec, ctx, output_path, 'x_spaces encode failed')

        passed, summary = ffprobe_contract(tmp)
        if not passed:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec, ctx, output_path, 'contract_failed')

        atomic_rename(tmp, output_path)
        actual = summary.get('duration', dur)
        logger.info(f'[x_spaces] OK ({actual:.1f}s)')
        return RenderedSegment(
            spec=spec, path=str(output_path), duration=actual,
            contract_passed=True, degraded=False, ffprobe_summary=summary,
        )

    def _get_tts(self, spec: SegmentSpec, ctx: EpisodeContext):
        """Get TTS audio: spec.tts_path first, then inline ElevenLabs."""
        tts = spec.tts()
        if tts and tts.exists() and tts.stat().st_size >= 1000:
            return tts

        # Inline ElevenLabs — follow cold_open.py pattern
        try:
            import requests
            key = os.environ.get('ELEVENLABS_API_KEY', '')
            if not key:
                return None
            voice_id = '1SM7GgM6IMuvQlz2BwM3'
            text = spec.body[:500]
            out_path = ctx.segment_dir() / 'x_spaces_tts.mp3'
            resp = requests.post(
                f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
                headers={'xi-api-key': key, 'Content-Type': 'application/json'},
                json={
                    'text': text,
                    'model_id': 'eleven_turbo_v2_5',
                    'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5},
                },
                timeout=30,
            )
            if resp.status_code != 200 or len(resp.content) < 1000:
                return None
            out_path.write_bytes(resp.content)
            return out_path
        except Exception as e:
            logger.warning(f'[x_spaces] inline TTS failed: {e}')
            return None

    def _build_filter_graph(self, spec: SegmentSpec) -> str:
        """Build branded X Spaces visual filter graph."""
        parts = [f'[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg]']

        # Top red eyebrow strip
        eyebrow = safe_text(spec.headline or 'X SPACES', 40)
        parts.append(
            f'[bg]drawbox=x=0:y=0:w={VIDEO_W}:h=80:color={BRAND_RED}:t=fill[bar]'
        )
        parts.append(
            f"[bar]drawtext=fontfile={FONT_BOLD}:text='{eyebrow}':"
            f"fontcolor=white:fontsize=32:x=40:y=24[top]"
        )

        # Main content: transcript excerpt
        body_text = safe_text(spec.body or '', 200)
        parts.append(
            f"[top]drawtext=fontfile={FONT_MONO}:text='{body_text}':"
            f"fontcolor=white:fontsize=22:x=60:y=140:line_spacing=8[mid]"
        )

        # Bottom attribution strip
        btc_str = safe_text(f'BTC {spec.btc_price}', 30) if spec.btc_price and spec.btc_price != 'N/A' else ''
        source_attr = safe_text('via X Spaces // Protocol Pulse', 60)
        parts.append(
            f"[mid]drawbox=x=0:y={VIDEO_H - 80}:w={VIDEO_W}:h=80:"
            f"color={CARD_BG}:t=fill[bot]"
        )
        parts.append(
            f"[bot]drawtext=fontfile={FONT_MONO}:text='{source_attr}':"
            f"fontcolor={META_GRAY}:fontsize=18:x=40:y={VIDEO_H - 52}[v_out]"
        )

        # Audio processing
        parts.append(
            f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
            f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
            f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
        )

        return ';'.join(parts)
