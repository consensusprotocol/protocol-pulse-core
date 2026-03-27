from __future__ import annotations
import glob as _glob
import html
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
            return self._render(spec, ctx, output_path, idx)
        except Exception as e:
            logger.exception(f'[social] exception: {e}')
            return self.filler_result(spec, ctx, output_path, str(e))

    def _render(self, spec, ctx, output_path, idx=0):
        posts = spec.social_posts
        if not posts:
            return self.filler_result(spec, ctx, output_path, 'no_social_posts')

        posts = posts[:3]

        # Audio: spec TTS → inline ElevenLabs → fallback silence
        tts = spec.tts()
        if not tts or not tts.exists() or tts.stat().st_size < 1000:
            tts = self._try_inline_tts(posts, ctx, idx)
        if not tts or not tts.exists() or tts.stat().st_size < 1000:
            tts = ctx.segment_dir() / f'social_{idx}_fallback.m4a'
            self._make_fallback_audio(tts, 10.0)

        dur = ffprobe_duration(tts)
        if dur < 0.5:
            dur = 10.0

        tmp = output_path.with_suffix('.tmp.mp4')

        # Playwright first → drawtext fallback (Law 1)
        ok = False
        try:
            ok = self._render_cards_playwright(posts, tts, tmp, dur, ctx)
        except Exception as e:
            logger.warning(f'[social] playwright failed: {e}, falling back to drawtext')
            ok = False

        if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
            tmp.unlink(missing_ok=True)
            ok = self._render_cards(posts, tts, tmp, dur)

        if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
            return self.filler_result(spec, ctx, output_path, 'social encode failed')

        passed, summary = ffprobe_contract(tmp)
        if not passed:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec, ctx, output_path, 'contract_failed')
        rename_ok = atomic_rename(tmp, output_path)
        if not rename_ok:
            tmp.unlink(missing_ok=True)
            return self.filler_result(spec, ctx, output_path, 'atomic_rename failed')
        actual = summary.get('duration', dur)
        logger.info(f'[social] OK ({actual:.1f}s, {len(posts)} posts)')
        return RenderedSegment(
            spec=spec, path=str(output_path), duration=actual,
            contract_passed=True, degraded=False,
            ffprobe_summary=summary
        )

    def _try_inline_tts(self, posts, ctx, idx=0):
        """Inline ElevenLabs TTS following cold_open pattern. Returns Path or None."""
        try:
            from ..network import http_post
            key = os.environ.get('ELEVENLABS_API_KEY', '')
            if not key:
                return None
            text = '. '.join(
                f"{p.get('account', 'unknown')} posted: {p.get('text', '')}"
                for p in posts
            )[:500]
            voice_id = '1SM7GgM6IMuvQlz2BwM3'
            out = ctx.segment_dir() / f'social_{idx}_tts.mp3'
            resp = http_post(
                f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
                headers={'xi-api-key': key, 'Content-Type': 'application/json'},
                json_body={'text': text, 'model_id': 'eleven_turbo_v2_5',
                      'voice_settings': {'stability': 0.35, 'similarity_boost': 0.90, 'style': 0.30, 'use_speaker_boost': True}},
                timeout=30
            )
            if resp is not None and len(resp.content) > 1000:
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

    @staticmethod
    def _find_chromium():
        """Find chromium executable: env var → system binary → Playwright cache."""
        import shutil
        # 1. Explicit env var
        env_path = os.environ.get('PLAYWRIGHT_CHROMIUM_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        # 2. System chromium
        for name in ('chromium-browser', 'chromium', 'google-chrome', 'chrome'):
            found = shutil.which(name)
            if found:
                return found
        # 3. Playwright cache (last resort)
        patterns = [
            os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-linux/chrome'),
            os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium'),
        ]
        for pat in patterns:
            matches = sorted(_glob.glob(pat))
            if matches:
                return matches[-1]  # most recent version
        return None

    def _render_cards_playwright(self, posts, tts, tmp, dur, ctx):
        """Render tweet cards as Playwright PNG screenshots, composite via ffmpeg.
        Returns True on success, False on failure."""
        from playwright.sync_api import sync_playwright  # lazy import — Law: no module-level import

        chrome_path = self._find_chromium()
        if not chrome_path:
            raise FileNotFoundError('chromium executable not found — falling back to drawtext')

        n = len(posts)
        card_pngs = []
        pw = sync_playwright().start()
        browser = None
        try:
            browser = pw.chromium.launch(headless=True, executable_path=chrome_path)
            for i, post in enumerate(posts):
                account_escaped = html.escape(str(post.get('account', 'unknown')))
                text_escaped = html.escape(str(post.get('text', '')))
                likes = html.escape(str(post.get('likes', 0)))
                retweets = html.escape(str(post.get('retweets', 0)))
                timestamp_escaped = html.escape(str(post.get('timestamp', '')))

                card_html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 800px; height: 280px; overflow: hidden;
    background: #0d1118;
    font-family: 'Courier New', Courier, monospace;
    display: flex; align-items: stretch;
  }}
  .card {{
    width: 100%; background: #0d1118;
    border: 1px solid #1e2a3a;
    border-left: 4px solid #ff3b5f;
    padding: 24px 28px;
    display: flex; flex-direction: column; gap: 12px;
  }}
  .header {{ display: flex; align-items: center; gap: 10px; }}
  .x-logo {{ color: #eef2ff; font-size: 18px; font-weight: bold; }}
  .account {{
    color: #ff3b5f; font-size: 18px; font-weight: bold;
    letter-spacing: 0.5px;
  }}
  .badge {{
    background: #f8c15c22; color: #f8c15c;
    font-size: 11px; padding: 2px 8px; border-radius: 3px;
    border: 1px solid #f8c15c44; letter-spacing: 1px;
    text-transform: uppercase;
  }}
  .text {{
    color: #eef2ff; font-size: 17px; line-height: 1.5;
    flex: 1;
    display: -webkit-box; -webkit-line-clamp: 3;
    -webkit-box-orient: vertical; overflow: hidden;
  }}
  .meta {{
    display: flex; gap: 20px; align-items: center;
    color: #95a0ba; font-size: 13px;
  }}
  .meta-item {{ display: flex; gap: 5px; align-items: center; }}
  .meta-value {{ color: #f8c15c; font-weight: bold; }}
  .divider {{
    position: absolute; bottom: 0; left: 0; right: 0;
    height: 1px; background: linear-gradient(90deg, #ff3b5f44, transparent);
  }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <span class="x-logo">\U0001d54f</span>
    <span class="account">@{account_escaped}</span>
    <span class="badge">Bitcoin Signal</span>
  </div>
  <div class="text">{text_escaped}</div>
  <div class="meta">
    <div class="meta-item">\u2764 <span class="meta-value">{likes}</span></div>
    <div class="meta-item">\U0001f501 <span class="meta-value">{retweets}</span></div>
    <div class="meta-item">{timestamp_escaped}</div>
  </div>
</div>
</body></html>'''

                page = browser.new_page(viewport={'width': 800, 'height': 280})
                page.set_content(card_html, wait_until='load')
                png_path = ctx.segment_dir() / f'tweet_card_{i}.png'
                page.screenshot(path=str(png_path), timeout=10000, full_page=False)
                page.close()
                if not png_path.exists() or png_path.stat().st_size < 100:
                    raise RuntimeError(f'tweet_card_{i}.png empty or missing')
                card_pngs.append(png_path)
        finally:
            if browser:
                browser.close()
            pw.stop()

        # Composite PNGs onto 1920x1080 branded background via ffmpeg
        # Scale each card proportionally: 800x280 source → maintain aspect ratio
        # Fit n cards into VIDEO_H with 80px top/bottom padding and gaps between cards
        padding = 160  # 80px top + 80px bottom
        gap = 20 * (n - 1) if n > 1 else 0  # 20px gap between cards
        max_card_h = min(616, (VIDEO_H - padding - gap) // n)
        card_h = max_card_h
        card_w = int(card_h * 800 / 280)  # maintain aspect ratio
        total_h = n * card_h + gap
        y_start = (VIDEO_H - total_h) // 2

        inputs = ['-f', 'lavfi', '-i', f'color=c=0x06070B:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}']
        inputs += ['-i', str(tts)]
        for png in card_pngs:
            inputs += ['-i', str(png)]

        # Build filter_complex
        fc_parts = []
        prev_label = '0:v'
        for i in range(n):
            card_gap = 20 if n > 1 else 0
            y = y_start + i * (card_h + card_gap)
            inp_idx = i + 2  # 0=bg, 1=audio, 2+=pngs
            scale_label = f'sc{i}'
            out_label = f'ov{i}' if i < n - 1 else 'v_pre'
            x_center = (VIDEO_W - card_w) // 2
            fc_parts.append(f'[{inp_idx}:v]scale={card_w}:{card_h}:flags=lanczos,format={VIDEO_PIX_FMT}[{scale_label}]')
            fc_parts.append(f'[{prev_label}][{scale_label}]overlay=x={x_center}:y={y}[{out_label}]')
            prev_label = out_label

        # Add kicker text
        kicker_text = safe_text('TOP X SIGNALS', 30)
        fc_parts.append(
            f"[v_pre]drawtext=fontfile={FONT_BOLD}:text='{kicker_text}':"
            f"fontcolor=0xF8C15C:fontsize=24:x=80:y=40[v_out]"
        )

        # Audio normalization
        fc_parts.append(
            f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
            f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
            f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
        )

        fc = ';'.join(fc_parts)

        return run_ffmpeg(
            inputs + [
                '-filter_complex', fc,
                '-map', '[v_out]', '-map', '[a_out]',
                '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
                '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
                '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
                '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
                '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp)
            ], f'social playwright {n} cards', 120
        )

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
