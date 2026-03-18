from __future__ import annotations
import os, logging, json, time as _time
from pathlib import Path
from .base import Segment
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text
from ..constants import (
    VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
    AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
    COLOR_BG, COLOR_GOLD, FONT_BOLD, FONT_MONO, PIPELINE_DIR
)
logger = logging.getLogger(__name__)

BRAND_RED = "0xE8272B"
CARD_BG = "0x141419"
META_GRAY = "0x888888"
# Read-only config path — acceptable as module constant (Law 3: no MUTABLE module-level state)
SIGNAL_CACHE = PIPELINE_DIR / "cache" / "active_signal.json"


class SignalActiveSegment(Segment):
    """Top half: Nostr signal display. Bottom half: Curated Mining sponsor (always)."""
    criticality = 'optional'

    SPONSOR_L1 = "CURATED MINING"
    SPONSOR_L2 = "White-glove Bitcoin mining. Section 179 LLC structure."
    SPONSOR_L3 = "curatedmining.com"

    def render(self, spec: SegmentSpec, ctx: EpisodeContext,
               output_path: Path, idx: int) -> RenderedSegment:
        try:
            return self._render(spec, ctx, output_path, idx)
        except Exception as e:
            logger.error(f'[signal_active] exception: {e}')
            return self.filler_result(spec, ctx, output_path, str(e))

    def _read_signal(self, spec):
        """Read top Nostr signal. Returns dict or None."""
        if spec.signal_content and spec.signal_content.get('nostr_posts'):
            posts = spec.signal_content['nostr_posts']
            return posts[0] if posts else None
        try:
            data = json.loads(SIGNAL_CACHE.read_text())
            posts = data.get('nostr_posts', [])
            return posts[0] if posts else None
        except Exception as e:
            logger.warning(f'[signal_active] cache read failed: {e}')
            return None

    def _render(self, spec, ctx, output_path, idx=0):
        signal = self._read_signal(spec)

        # Audio: spec TTS → inline ElevenLabs → fallback silence
        tts = spec.tts()
        if not tts or not tts.exists() or tts.stat().st_size < 1000:
            tts = self._generate_audio(signal, ctx, idx)
        if not tts or not tts.exists() or tts.stat().st_size < 1000:
            tts = ctx.segment_dir() / f'signal_{idx}_fallback.m4a'
            self._make_fallback_audio(tts, 8.0)

        dur = ffprobe_duration(tts)
        if dur < 0.5:
            dur = 8.0

        tmp = output_path.with_suffix('.tmp.mp4')
        fg = self._build_fg(signal)
        ok = run_ffmpeg([
            '-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}',
            '-i', str(tts),
            '-filter_complex', fg,
            '-map', '[v_out]', '-map', '[a_out]',
            '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
            '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
            '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
            '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
            '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp)
        ], 'signal_active', 120)

        if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
            return self.filler_result(spec, ctx, output_path, 'signal_active encode failed')

        passed, summary = ffprobe_contract(tmp)
        if not passed:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec, ctx, output_path, 'contract_failed')
        rename_ok = atomic_rename(tmp, output_path)
        if not rename_ok:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec, ctx, output_path, 'atomic_rename failed')
        actual = summary.get('duration', dur)
        logger.info(f'[signal_active] OK ({actual:.1f}s signal={"yes" if signal else "no"})')
        return RenderedSegment(
            spec=spec, path=str(output_path), duration=actual,
            contract_passed=True, degraded=False,
            ffprobe_summary=summary
        )

    def _build_fg(self, signal):
        """Build filter graph for split-screen: signal top, sponsor bottom."""
        parts = [f'[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg]']

        # Top half: Nostr signal card
        parts.append(f'[bg]drawbox=x=40:y=20:w=1840:h=500:color={CARD_BG}:t=fill[top]')

        if signal:
            name = safe_text(signal.get('display_name', 'Unknown'), 40)
            text = safe_text(signal.get('text', ''), 80)
            score_str = safe_text(f"Signal Score: {signal.get('score', 0)}", 40)
            try:
                ts_raw = _time.strftime('%Y-%m-%d %H:%M UTC',
                                        _time.gmtime(signal.get('created_at', 0)))
            except Exception:
                ts_raw = str(signal.get('created_at', ''))
            meta = safe_text(f'{ts_raw} | {signal.get("relay", "")}', 60)

            parts.append(
                f"[top]drawtext=fontfile={FONT_BOLD}:"
                f"text='{safe_text('NOSTR SIGNAL', 20)}':"
                f"fontcolor={BRAND_RED}:fontsize=32:x=60:y=40[th]"
            )
            parts.append(
                f"[th]drawtext=fontfile={FONT_BOLD}:text='{name}':"
                f"fontcolor=white:fontsize=26:x=60:y=90[tn]"
            )
            parts.append(
                f"[tn]drawtext=fontfile={FONT_MONO}:text='{text}':"
                f"fontcolor=white:fontsize=20:x=60:y=140:line_spacing=6[tt]"
            )
            parts.append(
                f"[tt]drawtext=fontfile={FONT_BOLD}:text='{score_str}':"
                f"fontcolor={COLOR_GOLD}:fontsize=24:x=60:y=400[ts]"
            )
            parts.append(
                f"[ts]drawtext=fontfile={FONT_MONO}:text='{meta}':"
                f"fontcolor={META_GRAY}:fontsize=16:x=60:y=440[mid]"
            )
        else:
            parts.append(
                f"[top]drawtext=fontfile={FONT_BOLD}:"
                f"text='{safe_text('NO SIGNAL', 20)}':"
                f"fontcolor={BRAND_RED}:fontsize=48:x=(w-text_w)/2:y=220[mid]"
            )

        # Bottom half: Curated Mining sponsor — ALWAYS present, NEVER conditional
        s1 = safe_text(self.SPONSOR_L1, 40)
        s2 = safe_text(self.SPONSOR_L2, 80)
        s3 = safe_text(self.SPONSOR_L3, 40)
        parts.append(
            f'[mid]drawbox=x=40:y=560:w=1840:h=460:'
            f'color={COLOR_BG}:t=fill[bot]'
        )
        parts.append(
            f"[bot]drawtext=fontfile={FONT_BOLD}:text='{s1}':"
            f"fontcolor={BRAND_RED}:fontsize=36:x=(w-text_w)/2:y=660[sp1]"
        )
        parts.append(
            f"[sp1]drawtext=fontfile={FONT_MONO}:text='{s2}':"
            f"fontcolor=white:fontsize=22:x=(w-text_w)/2:y=740[sp2]"
        )
        parts.append(
            f"[sp2]drawtext=fontfile={FONT_BOLD}:text='{s3}':"
            f"fontcolor={BRAND_RED}:fontsize=28:x=(w-text_w)/2:y=820[v_out]"
        )

        # Audio
        parts.append(
            f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
            f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
            f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
        )

        return ';'.join(parts)

    def _generate_audio(self, signal, ctx, idx=0):
        """Inline ElevenLabs TTS for both halves, concat with 0.5s gap."""
        try:
            from ..network import http_post
            key = os.environ.get('ELEVENLABS_API_KEY', '')
            if not key:
                return None
            voice_id = '1SM7GgM6IMuvQlz2BwM3'
            top_text = signal.get('text', '')[:500] if signal else 'No active signal'
            bottom_text = f'{self.SPONSOR_L1}. {self.SPONSOR_L2}. {self.SPONSOR_L3}'

            top_path = ctx.segment_dir() / f'sig_{idx}_top.mp3'
            bot_path = ctx.segment_dir() / f'sig_{idx}_bot.mp3'

            for text, path in [(top_text, top_path), (bottom_text, bot_path)]:
                resp = http_post(
                    f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
                    headers={'xi-api-key': key, 'Content-Type': 'application/json'},
                    json_body={'text': text, 'model_id': 'eleven_turbo_v2_5',
                          'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5}},
                    timeout=30
                )
                if resp is None or len(resp.content) < 1000:
                    return None
                path.write_bytes(resp.content)

            # 0.5s silence gap
            gap = ctx.segment_dir() / f'sig_{idx}_gap.m4a'
            run_ffmpeg([
                '-f', 'lavfi', '-i', f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo',
                '-t', '0.5', '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
                '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS), str(gap)
            ], 'signal gap', 15)

            # Concat with ffmpeg concat demuxer
            concat_file = ctx.segment_dir() / f'sig_{idx}_concat.txt'
            concat_tmp = concat_file.with_suffix('.tmp')
            concat_tmp.write_text(f"file '{top_path}'\nfile '{gap}'\nfile '{bot_path}'\n")
            import os as _os
            _os.replace(str(concat_tmp), str(concat_file))
            out = ctx.segment_dir() / f'sig_{idx}_concat_out.m4a'
            ok = run_ffmpeg([
                '-f', 'concat', '-safe', '0', '-i', str(concat_file),
                '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
                '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS), str(out)
            ], 'signal concat audio', 30)

            if ok and out.exists() and out.stat().st_size > 1000:
                return out
        except Exception as e:
            logger.warning(f'[signal_active] inline TTS failed: {e}')
        return None

    def _make_fallback_audio(self, path, duration):
        run_ffmpeg([
            '-f', 'lavfi', '-i', f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo',
            '-t', str(duration),
            '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
            '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
            str(path)
        ], 'signal fallback audio', 30)
