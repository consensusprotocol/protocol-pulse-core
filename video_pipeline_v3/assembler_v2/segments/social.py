from __future__ import annotations
import os, logging
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text
from ..constants import (
    VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
    AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
    COLOR_BG, FONT_BOLD, FONT_MONO
)
logger = logging.getLogger(__name__)

BRAND_RED = "0xE8272B"
CARD_BG = "0x141419"
META_GRAY = "0x888888"


class SocialSegment(Segment):
    """Renders up to 3 X posts as styled cards on branded background."""
    criticality = 'optional'

    def render(self, spec: SegmentSpec, ctx: EpisodeContext,
               output_path: Path, idx: int) -> RenderedSegment:
        try:
            return self._render(spec, ctx, output_path)
        except Exception as e:
            logger.error(f'[social] exception: {e}')
            return self.filler_result(spec, ctx, output_path, str(e))

    def _render(self, spec, ctx, output_path):
        posts = spec.social_posts
        if not posts:
            return self.filler_result(spec, ctx, output_path, 'no_social_posts')

        posts = posts[:3]

        # Audio: spec TTS → inline ElevenLabs → fallback silence
        tts = spec.tts()
        if not tts or not tts.exists() or tts.stat().st_size < 1000:
            tts = self._try_inline_tts(posts, ctx)
        if not tts or not tts.exists() or tts.stat().st_size < 1000:
            tts = ctx.segment_dir() / 'social_fallback.m4a'
            self._make_fallback_audio(tts, 10.0)

        dur = ffprobe_duration(tts)
        if dur < 0.5:
            dur = 10.0

        tmp = output_path.with_suffix('.tmp.mp4')
        ok = self._render_cards(posts, tts, tmp, dur)

        if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
            return self.filler_result(spec, ctx, output_path, 'social encode failed')

        passed, summary = ffprobe_contract(tmp)
        atomic_rename(tmp, output_path)
        actual = summary.get('duration', dur)
        logger.info(f'[social] OK ({actual:.1f}s, {len(posts)} posts)')
        return RenderedSegment(
            spec=spec, path=str(output_path), duration=actual,
            contract_passed=passed, degraded=not passed,
            ffprobe_summary=summary
        )

    def _try_inline_tts(self, posts, ctx):
        """Inline ElevenLabs TTS following cold_open pattern. Returns Path or None."""
        try:
            import requests
            key = os.environ.get('ELEVENLABS_API_KEY', '')
            if not key:
                return None
            text = '. '.join(
                f"{p.get('account', 'unknown')} posted: {p.get('text', '')}"
                for p in posts
            )[:500]
            voice_id = '1SM7GgM6IMuvQlz2BwM3'
            out = ctx.segment_dir() / 'social_tts.mp3'
            resp = requests.post(
                f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
                headers={'xi-api-key': key, 'Content-Type': 'application/json'},
                json={'text': text, 'model_id': 'eleven_turbo_v2_5',
                      'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5}},
                timeout=30
            )
            if resp.status_code == 200 and len(resp.content) > 1000:
                out.write_bytes(resp.content)
                return out
        except Exception as e:
            logger.warning(f'[social] inline TTS failed: {e}')
        return None

    def _make_fallback_audio(self, path, duration):
        run_ffmpeg([
            '-f', 'lavfi', '-i', f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo',
            '-t', str(duration),
            '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
            '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
            str(path)
        ], 'social fallback audio', 30)

    def _render_cards(self, posts, tts, tmp, dur):
        n = len(posts)
        card_h = min(300, (VIDEO_H - 40) // n - 20)
        card_w = VIDEO_W - 80

        fg_parts = [f'[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg0]']

        for i, post in enumerate(posts):
            y = 20 + i * (card_h + 20)
            x = 40
            prev = f'bg{i}'
            final = 'v_out' if i == n - 1 else f'bg{i + 1}'

            account = safe_text(post.get('account', 'unknown'), 40)
            text = safe_text(post.get('text', ''), 80)
            likes = post.get('likes', 0)
            retweets = post.get('retweets', 0)
            ts = safe_text(post.get('timestamp', ''), 30)
            meta = safe_text(f'{post.get("timestamp", "")} | {likes} likes | {retweets} retweets', 60)

            fg_parts.append(
                f'[{prev}]drawbox=x={x}:y={y}:w={card_w}:h={card_h}:'
                f'color={CARD_BG}:t=fill[cb{i}]'
            )
            fg_parts.append(
                f'[cb{i}]drawbox=x={x}:y={y}:w=4:h={card_h}:'
                f'color={BRAND_RED}:t=fill[ca{i}]'
            )
            fg_parts.append(
                f"[ca{i}]drawtext=fontfile={FONT_BOLD}:text='{account}':"
                f"fontcolor={BRAND_RED}:fontsize=26:x={x + 20}:y={y + 15}[an{i}]"
            )
            fg_parts.append(
                f"[an{i}]drawtext=fontfile={FONT_MONO}:text='{text}':"
                f"fontcolor=white:fontsize=20:x={x + 20}:y={y + 55}:line_spacing=6[bt{i}]"
            )
            fg_parts.append(
                f"[bt{i}]drawtext=fontfile={FONT_MONO}:text='{meta}':"
                f"fontcolor={META_GRAY}:fontsize=16:x={x + 20}:y={y + card_h - 30}[{final}]"
            )

        fg_parts.append(
            f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
            f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
            f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
        )

        fg = ';'.join(fg_parts)

        return run_ffmpeg([
            '-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}',
            '-i', str(tts),
            '-filter_complex', fg,
            '-map', '[v_out]', '-map', '[a_out]',
            '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
            '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
            '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
            '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
            '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp)
        ], f'social {len(posts)} cards', 120)
