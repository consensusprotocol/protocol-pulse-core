"""assembler_common — Shared infrastructure for the modular render pipeline.

Constants, color system, asset paths, FFmpeg helpers, visual building blocks,
and text utilities used by all render modules (render_intro, render_segment,
render_clip, render_social, render_data, render_outro, and the orchestrator).

Usage:
    from assembler_common import *          # grab everything
    from assembler_common import run_ffmpeg  # or cherry-pick
"""
import json
import logging
import math
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


# V4.3 FIX 5: NVENC GPU encoder with libx264 fallback
_NVENC_AVAILABLE = None

def get_video_encoder(crf: int = 18):
    """Use NVENC if available (RTX 4090), fallback to libx264."""
    global _NVENC_AVAILABLE
    if _NVENC_AVAILABLE is None:
        try:
            result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'],
                                    capture_output=True, text=True, timeout=10)
            _NVENC_AVAILABLE = 'h264_nvenc' in result.stdout
        except Exception:
            _NVENC_AVAILABLE = False
        logging.getLogger("Assembler").info(f"NVENC available: {_NVENC_AVAILABLE}")
    if _NVENC_AVAILABLE:
        return ['-c:v', 'h264_nvenc', '-preset', 'p4', '-rc', 'vbr', '-cq', str(crf),
                '-b:v', '8M', '-maxrate', '12M', '-gpu', '0']
    return ['-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf)]

# V4 Session 2: Modular render pipeline imports
from audio_master import get_lufs, normalize_segment, master_audio
from transitions import apply_crossfade, apply_transitions
from lower_thirds import lower_third_filter, apply_lower_third

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

# ── APEX UNIFIED COLOR SYSTEM ─────────────────────────────────────────────
COLOR_BG          = "0x0A0A0F"   # VDS dark navy — #0A0A0F per PIPELINE_LAWS
COLOR_BLACK       = "0x000000"   # true black
COLOR_PANEL       = "0x050607"   # BEV2 elevated surface
COLOR_PANEL2      = "0x080a0c"   # secondary surface
COLOR_RED         = "0xCC2222"   # BD signal red — all accents (PIPELINE_LAWS gospel)
COLOR_RED_WARM    = "0xFF334D"   # BEV2 warm red — transition elements
COLOR_WHITE       = "0xF4F5F8"   # BEV2 warm white — not pure white
COLOR_TEXT        = "0xF4F5F8"   # primary text (warm white)
COLOR_GOLD        = "0xF5A623"   # VDS gold — EYEBROW KICKERS ONLY (PIPELINE_LAWS gospel)
COLOR_MUTED       = "0x888888"   # secondary labels
COLOR_MUTED2      = "0x555555"   # metadata, timestamps
COLOR_GREEN       = "0x6EE7B7"   # BEV2 emerald — positive/DONE
COLOR_CORAL       = "0xFF8BA0"   # VDS coral — negative/warning
COLOR_RED_DIM     = "0x1a0000"   # CTA box backgrounds
COLOR_TICKER_BG   = "0x0c0c0c"   # ticker bar bg (kept dark)

# Legacy aliases for backward compat in make_host_visual / make_clip_visual
COLOR_CYAN        = "0x5DE4FF"   # VDS cyan — data accents, chart signal line
COLOR_AMBER       = COLOR_CORAL
BV2_OBSIDIAN    = COLOR_BG
BV2_DEEP_PANEL  = COLOR_PANEL
BV2_SIGNAL_RED  = COLOR_RED_WARM
BV2_STARK_WHITE = COLOR_WHITE
BV2_MUTED       = COLOR_WHITE  # secondary text (used @0.33 opacity, warm white)
BV2_EMERALD     = COLOR_GREEN
BV2_RED_LIGHT   = "0xFF8595"   # gradient accent

INTRO_VIDEO = os.path.join(ASSETS, "intro.mp4")
OUTRO_VIDEO = os.path.join(ASSETS, "outro.mp4")
GLITCH_TRANSITION = os.path.join(ASSETS, "transitions", "glitch_transition_waud.mp4")
DIGITAL_TRANSITION = os.path.join(ASSETS, "transitions", "digital_transition_1080p.mov")
WATERMARK = os.path.join(ASSETS, "logo", "watermark.png")
BG_MUSIC = os.path.join(ASSETS, "music", "pp_background.mp3")
TAG_VIDEO = os.path.join(ASSETS, "tag_vertical.mp4")
OUTRO_BRANDED = os.path.join(ASSETS, "outro_branded.mp4")
INTRO_TAG = os.path.join(ASSETS, "intro_tag.mp4")
INTRO_MUSIC_FILE = os.path.join(ASSETS, "intro_music.mp3")
BG_LOOP = os.path.join(ASSETS, "bg_loop.mp4")
PIP_PLACEHOLDER = os.path.join(ASSETS, "pip_placeholder.mp4")
OUTRO_BRANDED_NEW = os.path.join(ASSETS, "outro_branded_new.mp4")
LOGO_IMAGE = os.path.join(ASSETS, "logo_protocol_pulse.png")
SCANLINE_OVERLAY = os.path.join(ASSETS, "scanline_overlay.png")
# Issue 3: Custom whoosh sound — prefer custom_whoosh.wav/.mp3 over generated glitch_whoosh.wav
_CUSTOM_WHOOSH_MP3 = os.path.join(ASSETS, "sfx", "custom_whoosh.mp3")
_CUSTOM_WHOOSH_WAV = os.path.join(ASSETS, "sfx", "custom_whoosh.wav")
if os.path.exists(_CUSTOM_WHOOSH_WAV):
    GLITCH_WHOOSH = _CUSTOM_WHOOSH_WAV
elif os.path.exists(_CUSTOM_WHOOSH_MP3):
    # Convert mp3 to wav for consistency if not already done
    subprocess.run(["ffmpeg", "-y", "-i", _CUSTOM_WHOOSH_MP3, _CUSTOM_WHOOSH_WAV],
                   capture_output=True, text=True, timeout=10)
    GLITCH_WHOOSH = _CUSTOM_WHOOSH_WAV if os.path.exists(_CUSTOM_WHOOSH_WAV) else _CUSTOM_WHOOSH_MP3
else:
    GLITCH_WHOOSH = os.path.join(ASSETS, "sfx", "glitch_whoosh.wav")
    logging.getLogger("Assembler").info("CUSTOM WHOOSH NOT FOUND — using generated")
CARD_SWOOSH = os.path.join(ASSETS, "sfx", "card_swoosh.wav")
DATA_BLIP = os.path.join(ASSETS, "sfx", "data_blip.wav")

# ISSUE 3 FIX: Global whoosh dedup — tracks output paths that already have whoosh/swoosh applied
_whoosh_applied_parts = set()

# ── FIX 4: NOSTR SPAM FILTER (ported from core/routes.py — can't import routes from assembler) ──
NOSTR_SPAM_TERMS = [
    'incest', 'onlyfans', 'nude', 'xxx', 'porn', 'naked', 'sex tape',
    'teenage', 'teenagegirls', '#nolimit', 'FolloFFFFvh', 'RssazZZZ',
    'altcoin', 'memecoin', '#solana', '#ethereum', '#eth ', '#nft',
    # V11 FIX 2: Lightning address spam + zap begging
    'lightning address', 'lnurl', 'zap me', 'feel free to zap',
    '@npubx.cash', 'lightning payments', 'can now receive',
    'airdrop', 'shitcoin', 'presale', 'pump it',
    # Session fix 8c: Filter Nick Szabo references (contested attribution, editorial risk)
    'nick szabo', 'szabo',
]
NOSTR_SPAM_NPUBS = ['npub1a1c6869a', '50514b']


def _is_nostr_spam_assembler(post: dict) -> bool:
    """Filter explicit content, altcoin spam, and known spam accounts from Nostr posts."""
    content = post.get('content', post.get('text', '')).lower()
    npub = post.get('npub', post.get('author', ''))
    if any(t in content for t in NOSTR_SPAM_TERMS):
        return True
    if any(n in npub for n in NOSTR_SPAM_NPUBS):
        return True
    # V4.3: Low-value content filter
    # Self-promotional posts ("New article", "Introducing", "Check out")
    promo_starts = ['new article', 'introducing', 'check out', 'just published', 'just launched', 'announcing']
    if any(content.startswith(p) for p in promo_starts):
        return True
    # V11 FIX 2: Self-promo ("my address", "my link", "my channel")
    if 'my ' in content and any(w in content for w in ['address', 'link', 'channel', 'wallet', 'node']):
        return True
    # Too short to be insightful (under 50 chars)
    if len(content.strip()) < 50:
        return True
    # Contains URLs (link drops, not original thought)
    if 'http://' in content or 'https://' in content or '.com/' in content:
        return True
    # Hashtag farm detection
    words = content.split()
    if words:
        hashtag_ratio = sum(1 for w in words if w.startswith('#')) / len(words)
        if hashtag_ratio > 0.6:
            return True
    return False
LOWER_SLIDE = os.path.join(ASSETS, "sfx", "lower_slide.wav")


def _get_bg_layer(inputs: list, duration: float, label_out: str = "bb_bg") -> str:
    """Get background layer filtergraph. Uses bg_loop.mp4 if available, else procedural.

    Appends bg_loop to inputs list and returns filtergraph that outputs [label_out].
    bg_loop replaces the procedural background for narration/host segments.
    """
    if os.path.exists(BG_LOOP):
        inputs.append(["-stream_loop", "-1", "-i", BG_LOOP])
        bg_idx = len(inputs) - 1
        # Round 2 Fix 7: Glassmorphic darkening overlay on bg_loop for PiP segments
        # Applies 45% black overlay so bg_loop is visible but not distracting
        fg = (f"[{bg_idx}:v]scale=1920:1080,setsar=1,fps=30,"
              f"trim=0:{duration + 2.0},setpts=PTS-STARTPTS,"
              # Keep vignette for cinematic depth
              f"vignette=PI/4:mode=backward,"
              # BUG 2 FIX: Removed hue=s=0.15 — bg_loop stays FULL COLOR
              # The 45% dark overlay already provides cinematic effect
              # Glassmorphic darken: multiply brightness by 0.55 (45% darker)
              f"eq=brightness=-0.15:contrast=0.9,"
              # Red border frame (2px all edges — PIPELINE_LAWS)
              f"drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
              f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
              f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
              f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill[{label_out}];\n")
        return fg
    _, fg = _build_broadcast_bg(duration, label_out=label_out)
    return fg


def _add_episode_title_pill(label_in: str, label_out: str,
                            episode_title: str, duration: float) -> str:
    """FIX 3: Glassmorphic episode title pill at bottom-left safe zone.

    Semi-transparent rounded rect with PULSE CHECK label + episode title.
    Visible from t=0.5 to end of segment.
    """
    safe_title = _sanitize_text(episode_title or "PULSE CHECK")[:32]  # overflow fix
    return (
        f"[{label_in}]"
        # Semi-transparent black background pill
        f"drawbox=x=40:y=980:w=500:h=56:color=0x000000@0.55:t=fill:"
        f"enable='between(t,0.5,{duration})',"
        # Subtle white border at 15% opacity
        f"drawbox=x=40:y=980:w=500:h=56:color=0xFFFFFF@0.15:t=1:"
        f"enable='between(t,0.5,{duration})',"
        # Red monospace label above title
        f"drawtext=fontfile={FONT_MONO}:text='PULSE CHECK':"
        f"fontcolor={COLOR_RED}:fontsize=11:x=52:y=982:"
        f"enable='between(t,0.5,{duration})',"
        # White episode title text
        f"drawtext=fontfile={FONT_BOLD}:text='{safe_title}':"
        f"fontcolor={COLOR_WHITE}:fontsize=18:x=52:y=1000:"
        f"enable='between(t,0.5,{duration})'"
        f"[{label_out}];\n"
    )


def apply_scanline(inputs: list, fg: str, label_in: str, label_out: str,
                   duration: float) -> str:
    """R26 UPGRADE 1: CRT scanline overlay — adds scanline_overlay.png on top of scene.

    Appends the PNG to inputs and returns updated filtergraph that overlays it.
    """
    if not os.path.exists(SCANLINE_OVERLAY):
        fg += f"[{label_in}]copy[{label_out}];\n"
        return fg
    inputs.append(SCANLINE_OVERLAY)
    sl_idx = len(inputs) - 1
    fg += (f"[{sl_idx}:v]scale=1920:1080,loop=loop=-1:size=2:start=0,"
           f"setpts=PTS-STARTPTS,trim=0:{duration},setpts=PTS-STARTPTS,"
           f"format=rgba[_scanline];\n")
    fg += f"[{label_in}][_scanline]overlay=0:0:format=auto[{label_out}];\n"
    return fg


def get_latest_spaces_summary() -> dict:
    """FIX 8: Check for recent X Spaces transcripts for episode inclusion.

    Checks:
    1. video_pipeline_v3/data/spaces/ for recent chunks
    2. spaces_scraper/ for cached transcripts
    3. x_spaces_scraper/ for cached transcripts

    Returns dict with {summary, source, score} if found, else None.
    """
    import glob
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(hours=24)

    # Check pipeline spaces data first
    spaces_data_dir = os.path.join(BASE, "data", "spaces")
    if os.path.exists(spaces_data_dir):
        for space_dir in sorted(os.listdir(spaces_data_dir), reverse=True):
            chunks_file = os.path.join(spaces_data_dir, space_dir, "chunks.jsonl")
            if not os.path.exists(chunks_file):
                continue
            # Check if recent (file modified in last 24h)
            if os.path.getmtime(chunks_file) < cutoff.timestamp():
                continue
            # Read highest-impact chunks
            best_chunks = []
            try:
                with open(chunks_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        if entry.get("impact_score", 0) >= 50:
                            best_chunks.append(entry)
            except Exception:
                continue
            if best_chunks:
                best_chunks.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
                top = best_chunks[0]
                summary = top.get("text", "")[:500]
                return {
                    "summary": f"From X Spaces — {top.get('speaker', 'unknown')}: {summary}",
                    "source": f"X Spaces ({space_dir})",
                    "score": top.get("impact_score", 0),
                }

    # Check spaces_scraper cache
    scraper_cache = os.path.join(os.path.dirname(BASE), "spaces_scraper", "cache")
    if not os.path.exists(scraper_cache):
        scraper_cache = os.path.join(os.path.dirname(BASE), "x_spaces_scraper", "cache")
    if os.path.exists(scraper_cache):
        json_files = sorted(glob.glob(os.path.join(scraper_cache, "*.json")), reverse=True)
        for jf in json_files[:5]:
            if os.path.getmtime(jf) < cutoff.timestamp():
                continue
            try:
                with open(jf) as f:
                    data = json.loads(f.read())
                transcript = data.get("transcript", data.get("text", ""))
                if transcript and len(transcript) > 100:
                    return {
                        "summary": transcript[:500],
                        "source": f"X Spaces Scraper ({os.path.basename(jf)})",
                        "score": 60,
                    }
            except Exception:
                continue

    logger.info("  FIX 8: No recent X Spaces data found — segment skipped")
    return None


_PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_live_metric(key: str, fallback: str) -> str:
    """Fetch a live metric from intelligence signals JSON files, with API fallback for hashrate."""
    for path in ['data/intelligence/live_signals.json', 'data/intelligence/daily_signals.json']:
        try:
            with open(os.path.join(_PIPELINE_DIR, path)) as f:
                d = json.load(f)
                if key in d:
                    return str(d[key])
        except Exception:
            pass
    # API fallback for hashrate
    if key == "hashrate":
        try:
            import urllib.request as _ur
            with _ur.urlopen("https://mempool.space/api/v1/mining/hashrate/3d", timeout=5) as r:
                data = json.load(r)
                if data.get("currentHashrate"):
                    eh = data["currentHashrate"] / 1e18
                    return f"{eh:,.0f} EH/s"
        except Exception:
            pass
    # V11 FIX 3: API fallback for BTC dominance
    if key == "dominance":
        try:
            import urllib.request as _ur
            with _ur.urlopen("https://api.coingecko.com/api/v3/global", timeout=5) as r:
                data = json.load(r)
                dom = data.get("data", {}).get("market_cap_percentage", {}).get("btc", 0)
                if dom and 10 < dom < 100:
                    return f"{dom:.1f} pct"
        except Exception:
            pass
        # Secondary: mempool.space doesn't have dominance, try sovereign context
        try:
            _ctx_path = os.path.join(_PIPELINE_DIR, "data", "sovereign_context", "latest.json")
            with open(_ctx_path) as _cf:
                _ctx = json.load(_cf)
                dom = _ctx.get("btc_dominance", _ctx.get("dominance", 0))
                if dom and 10 < dom < 100:
                    return f"{dom:.1f} pct"
        except Exception:
            pass
    # API fallback for mempool fee
    if key == "mempool_fee":
        try:
            import urllib.request as _ur
            with _ur.urlopen("https://mempool.space/api/v1/fees/recommended", timeout=5) as r:
                data = json.load(r)
                return f"{data.get('halfHourFee', 'N/A')} sat/vB"
        except Exception:
            pass
    return fallback


def _fetch_btc_price() -> str:
    """FIX 5: Fetch BTC price with dual fallback (CoinGecko → Mempool)."""
    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            price = data["bitcoin"]["usd"]
            return f"${price:,.0f}"
    except Exception:
        try:
            import urllib.request
            url2 = "https://mempool.space/api/v1/prices"
            with urllib.request.urlopen(url2, timeout=5) as r:
                data = json.loads(r.read())
                return f"${data.get('USD', 0):,.0f}"
        except Exception:
            return "$N/A"


def _ken_burns_motion(label_in: str, label_out: str, duration: float) -> str:
    """Static frame pass — ensures 1920x1080 output with correct format.

    Ken Burns pan/zoom REMOVED: it was applied to the full 1920x1080 output
    AFTER all compositing, causing the PP logo, lower thirds, info banners,
    and all text overlays to drift and become partially cut off.

    Now returns a static scale+format chain with no motion.
    Ken Burns is only used on PiP preview windows (see make_pip_preview).
    """
    return (f"[{label_in}]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"setsar=1,format=yuv420p[{label_out}];\n")


def _build_black_diamond_bg(duration: float, label_out: str = "bd_bg") -> tuple:
    """BLACK DIAMOND 7-layer procedural background — Sovereign Command Center.

    Returns (extra_inputs, filtergraph_string).
    extra_inputs is always [] — pure procedural generation.
    """
    f = ""
    # Layer 1: VDS dark navy base (#0A0A0F per PIPELINE_LAWS)
    f += f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30[bd_base];\n"
    # Layer 2: Red radial glow — top-center (subtle)
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(55*exp(-((X-960)*(X-960)+Y*Y)/380000),0,255)':g='0':b='0'[bd_glow_top];\n")
    f += f"[bd_base][bd_glow_top]blend=all_mode=screen[bg1];\n"
    # Layer 3: Red radial glow — bottom-center
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(35*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/280000),0,255)':g='0':b='0'[bd_glow_bot];\n")
    f += f"[bg1][bd_glow_bot]blend=all_mode=screen[bg2];\n"
    # Layer 4: Tactical surveillance grid (very subtle)
    f += f"[bg2]drawgrid=width=120:height=68:thickness=1:color=0xFF0000@0.07[bg3];\n"
    # Layer 5: Scanlines (horizontal every 3px)
    f += f"[bg3]drawgrid=width=0:height=3:thickness=1:color=0xFF0000@0.025[bg4];\n"
    # Layer 6: Vignette
    f += f"[bg4]vignette=PI/4:mode=backward[bg5];\n"
    # Layer 7: Red border frame (2px solid on all 4 edges)
    f += (f"[bg5]drawbox=x=0:y=0:w=1920:h=2:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=0:y=1078:w=1920:h=2:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=0:y=0:w=2:h=1080:color=0xFF3333@0.85:t=fill,"
          f"drawbox=x=1918:y=0:w=2:h=1080:color=0xFF3333@0.85:t=fill[{label_out}];\n")
    return ([], f)


def _build_info_bar_fg(duration: float, btc_price: str, block_height: str = "",
                       label_in: str = "v_pre_tick", label_out: str = "v_ticked") -> str:
    """BLACK DIAMOND ticker bar — red scrolling intel on near-black bg."""
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = btc_price.replace("'", "").replace('"', "").replace("\\", "")

    content = (f"  PROTOCOL PULSE  //  BITCOIN {safe_btc}  //  {date_str}"
               f"  //  PROTOCOLPULSE.IO  //  STAY SOVEREIGN  "
               f"  //  PROTOCOL PULSE DAILY BRIEF  //  {date_str}"
               f"  //  FEAR/GREED  //  STAY SOVEREIGN"
               f"  //  BITCOIN {safe_btc}  //  PROTOCOLPULSE.IO  ")
    safe_content = content.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # FIX 5: Glassmorphic black base bar
    fg += f"color=c=0x000000@0.75:s=1920x48:d={duration}:r=30[tickbase];\n"
    # Red top separator line (2px)
    fg += f"[tickbase]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.85:t=fill[tickline];\n"
    # Static 'PULSE CHECK' label left
    fg += (f"[tickline]drawtext=fontfile={FONT_MONO}:text='PULSE CHECK':"
           f"fontcolor=0xF4F5F8:fontsize=14:x=8:y=18[tickstatic];\n")
    # Scrolling red text
    fg += (f"[tickstatic]drawtext=fontfile={FONT_MONO}:text='{safe_content}':"
           f"fontcolor={COLOR_RED}:fontsize=14:"
           f"x=W-mod(n*2\\,W+text_w):y=18[ticker];\n")
    # Overlay bar onto video frame at y=1032
    fg += f"[{label_in}][ticker]overlay=0:1032[{label_out}];\n"
    return fg


def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
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
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
        if r.returncode != 0:
            logger.error(f"FAIL {label}: {r.stderr[-600:]}")
            return False
        return True
    finally:
        try:
            os.unlink(fpath)
        except OSError:
            pass


def ffprobe_video_duration(path: str) -> float:
    """Return video stream duration specifically (not format/container duration).

    Unlike ffprobe_duration() which returns format duration (max of all streams),
    this returns only the video stream duration. Critical for xfade offset calculation
    where audio may be longer than video after a failed crossfade.
    """
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=15,
    )
    try:
        return float(r.stdout.strip())
    except (ValueError, AttributeError):
        # Fallback: some containers don't report stream duration, try format
        return ffprobe_duration(path)


def _enforce_av_sync(path: str) -> str:
    """Ensure audio and video durations match by truncating the longer stream.

    Returns the path to a sync-corrected file, or the original if already in sync.
    Prevents accumulated AV drift when parts are concatenated via concat demuxer.
    """
    v_dur = ffprobe_video_duration(path)
    a_dur_r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=15,
    )
    try:
        a_dur = float(a_dur_r.stdout.strip())
    except (ValueError, AttributeError):
        return path

    drift = abs(a_dur - v_dur)
    if drift < 0.1:  # <100ms is acceptable
        return path

    logger.warning(f"AV SYNC FIX: {os.path.basename(path)} V={v_dur:.3f}s A={a_dur:.3f}s drift={drift:.3f}s")
    target_dur = min(v_dur, a_dur)
    fixed = path + ".avsync.mp4"
    ok = run_ffmpeg([
        "-i", path,
        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
        "-b:v", "8M", "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        "-t", f"{target_dur:.3f}",
        "-shortest",
        fixed,
    ], f"AV sync enforce ({drift:.3f}s drift)", 120)
    if ok and os.path.exists(fixed):
        os.replace(fixed, path)
        logger.info(f"AV SYNC FIX: Corrected to {target_dur:.3f}s")
    elif os.path.exists(fixed):
        os.remove(fixed)
    return path


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


def _generate_fallback_silent_audio(work_dir: str, idx: int, text: str = "") -> str:
    """BUG1 FIX: Generate silence audio as TTS fallback when ElevenLabs quota is exhausted.

    Estimates duration from text length (~150 words/min, ~5 chars/word).
    Returns path to silent .m4a file, or "" on failure.
    """
    raise RuntimeError("[ABORT] TTS failed - refusing silent audio fallback. Fix ElevenLabs voice/key.")

    # Estimate duration: ~150 wpm, ~5 chars/word → ~750 chars/min → ~12.5 chars/s
    # Minimum 2s, maximum 30s
    dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
    out = os.path.join(work_dir, f"fallback_silence_{idx:03d}.m4a")
    ok = run_ffmpeg([
        "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
        "-t", str(dur),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        out,
    ], "fallback silence", 15)
    if ok and os.path.exists(out):
        logger.warning(f"  [fallback] Generated {dur:.1f}s silence for idx={idx} (TTS quota exhausted)")
        return out
    return ""


def _build_corner_brackets_fg(label_in: str, label_out: str) -> str:
    """Draw tactical corner brackets on all 4 corners — signal red."""
    return (
        f"[{label_in}]"
        f"drawbox=x=0:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=0:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=0:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=0:y=1040:w=4:h=40:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1880:y=1076:w=40:h=4:color={COLOR_RED}:t=fill,"
        f"drawbox=x=1916:y=1040:w=4:h=40:color={COLOR_RED}:t=fill"
        f"[{label_out}];\n"
    )


def _build_broadcast_bg(duration: float, label_out: str = "bb_bg") -> tuple:
    """APEX UNIFIED 7-layer procedural background.

    Layer 1: BEV2 cinematic obsidian base (#020304)
    Layer 2: BEV2 3-glow radial (top-left red, top-right white, bottom-center red)
    Layer 3: VDS perspective grid (bottom 30%, very subtle)
    Layer 4: BD scanlines (horizontal every 4px, red @2.5%)
    Layer 5: Vignette
    Layer 6: (film grain skipped — geq too slow per spec)
    Layer 7: Red border frame (2px all edges)
    """
    f = ""
    # Layer 1: VDS dark navy base (#0A0A0F per PIPELINE_LAWS)
    f += f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30[bb_base];\n"
    # Layer 2a: Red radial glow — top-left
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(46*exp(-((X)*(X)+Y*Y)/350000),0,255)':g='0':b='0'[bb_glow_tl];\n")
    f += f"[bb_base][bb_glow_tl]blend=all_mode=screen[bb1];\n"
    # Layer 2b: White radial glow — top-right (subtle)
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'"
          f":g='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'"
          f":b='clip(15*exp(-((X-1920)*(X-1920)+Y*Y)/300000),0,255)'[bb_glow_tr];\n")
    f += f"[bb1][bb_glow_tr]blend=all_mode=screen[bb2];\n"
    # Layer 2c: Red radial glow — bottom-center
    f += (f"color=c=0x0A0A0F:s=1920x1080:d={duration}:r=30,"
          f"geq=r='clip(25*exp(-((X-960)*(X-960)+(Y-1080)*(Y-1080))/400000),0,255)':g='0':b='0'[bb_glow_bc];\n")
    f += f"[bb2][bb_glow_bc]blend=all_mode=screen[bb3];\n"
    # Layer 3: VDS perspective grid (bottom 30% — subtle white)
    f += f"[bb3]drawgrid=width=90:height=54:thickness=1:color=0xFFFFFF@0.04[bb4];\n"
    # Layer 4: BD scanlines (horizontal every 4px, red @2.5%)
    f += f"[bb4]drawgrid=width=0:height=4:thickness=1:color={COLOR_RED}@0.025[bb5];\n"
    # Layer 5: Vignette
    f += f"[bb5]vignette=PI/4:mode=backward[bb6];\n"
    # Layer 7: Red border frame (2px all edges)
    f += (f"[bb6]drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill[{label_out}];\n")
    return ([], f)


def _build_top_system_bar(label_in: str, label_out: str, scene_label: str = "",
                           progress_pct: int = 50, recon_id: str = "") -> str:
    """APEX UNIFIED header — BD structure + BEV2 glassmorphic floating pill."""
    import datetime
    if not recon_id:
        recon_id = datetime.datetime.now().strftime("%H%M%S")
    fg = ""
    # Floating pill bg with glassmorphic feel
    fg += (f"[{label_in}]drawbox=x=20:y=12:w=1880:h=52:color=0x000000@0.55:t=fill,"
           # Red left accent line on pill (BD)
           f"drawbox=x=20:y=12:w=3:h=52:color={COLOR_RED}@0.9:t=fill,"
           # Left: bullet + PROTOCOL PULSE
           f"drawtext=fontfile={FONT_BOLD}:text='  PROTOCOL PULSE':"
           f"fontcolor={COLOR_WHITE}:fontsize=20:x=38:y=26,"
           # LIVE label in red (render11 FIX 4: +16px gap from PROTOCOL PULSE text end)
           f"drawtext=fontfile={FONT_BOLD}:text='LIVE':"
           f"fontcolor={COLOR_RED}:fontsize=16:x=252:y=30,"
           # Bottom separator
           f"drawbox=x=20:y=64:w=1880:h=1:color={COLOR_RED}@0.25:t=fill"
           f"[{label_out}];\n")
    return fg


def _build_signature_info_rail(duration: float, btc_price: str, label_in: str,
                                label_out: str) -> str:
    """FIX 5 — Glassmorphic black bottom bar: rgba(0,0,0,0.75) with red top separator.
    Left: 'PULSE CHECK' white monospace. Right: scrolling red ticker.
    """
    import datetime
    date_str = datetime.datetime.now().strftime("%b %d, %Y").upper()
    safe_btc = (btc_price or "N/A").replace("'", "").replace('"', "").replace("\\", "")
    ticker_content = (
        f"  BITCOIN {safe_btc}  //  PROTOCOL PULSE DAILY BRIEF  //  "
        f"{date_str}  //  FEAR/GREED  //  STAY SOVEREIGN  //  "
        f"BITCOIN {safe_btc}  //  PROTOCOLPULSE.IO  //  STAY SOVEREIGN  "
    )
    safe_ticker = ticker_content.replace("'", "").replace('"', "").replace("\\", "")

    fg = ""
    # Glassmorphic black bar (0,0,0 @0.75 opacity)
    fg += (f"[{label_in}]"
           f"drawbox=x=0:y=1032:w=1920:h=48:color=0x000000@0.75:t=fill,"
           # Red top separator line (2px)
           f"drawbox=x=0:y=1032:w=1920:h=2:color={COLOR_RED}@0.85:t=fill,"
           # Left: static 'PULSE CHECK' in white monospace
           f"drawtext=fontfile={FONT_MONO}:text='PULSE CHECK':"
           f"fontcolor=0xF4F5F8:fontsize=14:x=16:y=1048,"
           # Vertical separator after label
           f"drawbox=x=140:y=1036:w=1:h=38:color={COLOR_RED}@0.5:t=fill,"
           # Right: scrolling red ticker
           f"drawtext=fontfile={FONT_MONO}:text='{safe_ticker}':"
           f"fontcolor={COLOR_RED}:fontsize=14:"
           f"x=W-mod(n*2\\,W+text_w):y=1048"
           f"[{label_out}];\n")
    return fg


def _build_narration_wave(label_in: str, label_out: str,
                          audio_out_label: str = "_nw_a_out") -> tuple:
    """APEX V2 Cipher Line waveform — dual-layer EKG at y=880, 160px zone.

    Uses asplit=3 to separate audio feeds:
      - 2 for visualization (primary + accent)
      - 1 for audio output (returned as audio_out_label)

    Returns (filtergraph_string, audio_out_pad) where audio_out_pad is the
    label to pass to _bv2_encode's audio_pad parameter.
    """
    fg = ""
    # Split audio: 2 for vis, 1 for output (FIX 3 — never share audio pads)
    fg += f"[0:a]asplit=3[_a_vis][_a_vis2][{audio_out_label}];\n"

    # PRIMARY: thin centerline wave — white, ultra-clean
    fg += (f"[_a_vis]showwaves=s=1920x80:mode=line:"
           f"colors=0xF4F5F8@0.9:scale=sqrt:draw=full:rate=30[_wave_line];\n")

    # SECONDARY: mirror reflection — warm red, low opacity
    fg += (f"[_a_vis2]showwaves=s=1920x80:mode=line:"
           f"colors=0xFF334D@0.25:scale=log:draw=full:rate=30[_wave_red];\n")
    fg += f"[_wave_red]vflip[_wave_red_flip];\n"

    # Stack: primary on top, flipped reflection below (total 160px)
    fg += f"[_wave_line][_wave_red_flip]vstack[_wave_stacked];\n"

    # Edge fade bars (top + bottom)
    fg += (f"[_wave_stacked]"
           f"drawbox=x=0:y=0:w=1920:h=20:color=0x020304@0.8:t=fill,"
           f"drawbox=x=0:y=140:w=1920:h=20:color=0x020304@0.8:t=fill"
           f"[_wave_faded];\n")

    # Thin red center dividing line (the "spine")
    fg += (f"[_wave_faded]drawbox=x=0:y=79:w=1920:h=2:"
           f"color=0xFF0000@0.35:t=fill[_wave_final];\n")

    # Position at y=880 (above info rail, 160px zone)
    fg += f"[{label_in}][_wave_final]overlay=0:880[{label_out}];\n"
    return fg, f"[{audio_out_label}]"


def _bv2_text_zone(label_in: str, label_out: str, eyebrow: str, headline: str,
                    body: str, tag: str = "") -> str:
    """APEX left 58% text zone — gold eyebrow kicker (VDS), warm white headline.
    Render11 FIX 3: Glassmorphic dark panel behind headline for readability.
    """
    safe_eye = _sanitize_text(eyebrow)
    safe_head = _sanitize_text(headline)
    safe_body = _word_wrap(_sanitize_text(body), max_width=30, max_lines=3) if body else ""
    safe_tag = _sanitize_text(tag) if tag else ""

    # FIX 3: Calculate headline panel height (1 line = ~72px, 2 lines = ~144px)
    _head_nlines = max(1, (len(safe_head) // 18) + 1)
    _head_ph = _head_nlines * 72 + 20

    fg = ""
    # Gold eyebrow kicker (VDS)
    fg += (f"[{label_in}]drawtext=fontfile={FONT_MONO}:text='{safe_eye}':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100[bv2_eye];\n")
    # FIX 3: Glassmorphic panel behind headline (dark 60% fill + white border)
    fg += (f"[bv2_eye]"
           f"drawbox=x=56:y=120:w=860:h={_head_ph}:color=0x000000@0.60:t=fill,"
           f"drawbox=x=56:y=120:w=860:h={_head_ph}:color=0xFFFFFF@0.12:t=2"
           f"[bv2_glass];\n")
    # Render21 FIX 6: 2-line headline if >45 chars — never truncate
    _h_line1, _h_line2 = _split_headline_for_render(safe_head)
    _h_fs = 34 if _h_line2 else 64
    _h_y2 = 130 + 65  # Render24 FIX 7: y+65 offset for line 2
    fg += (f"[bv2_glass]drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_h_line1)}':"
           f"fontcolor=0x111111:fontsize={_h_fs}:x=66:y=132,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_h_line1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_h_fs}:x=64:y=130")
    if _h_line2:
        fg += (f",drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_h_line2)}':"
               f"fontcolor=0x111111:fontsize={_h_fs}:x=66:y={_h_y2 + 2},"
               f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_h_line2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_h_fs}:x=64:y={_h_y2}")
    fg += f"[bv2_head];\n"
    # Body text
    if safe_body:
        fg += (f"[bv2_head]drawtext=fontfile={FONT_MONO}:text='{safe_body}':"
               f"fontcolor=0xFFFFFF@0.6:fontsize=18:x=64:y=420:line_spacing=8[bv2_body];\n")
    else:
        fg += f"[bv2_head]copy[bv2_body];\n"
    # Render24 FIX 5: Live metrics strip below body text
    _m_hashrate = _sanitize_text(_get_live_metric("hashrate", "850 EH/s"))
    _m_mempool = _sanitize_text(_get_live_metric("mempool_fee", "12 sat/vB"))
    _m_etf = _sanitize_text(_get_live_metric("etf_flow", "$340M"))
    _m_halving = _sanitize_text(_get_live_metric("halving_pct", "78 pct"))
    _m_dominance = _sanitize_text(_get_live_metric("dominance", "61.4 pct"))
    fg += (f"[bv2_body]"
           # Metric strip background
           f"drawbox=x=64:y=480:w=860:h=80:color=0x000000@0.45:t=fill,"
           f"drawbox=x=64:y=480:w=860:h=1:color=0xFFFFFF@0.08:t=fill,"
           # HASHRATE
           f"drawtext=fontfile={FONT_MONO}:text='HASHRATE':fontcolor={COLOR_MUTED}:fontsize=9:x=76:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_hashrate}':fontcolor={COLOR_WHITE}:fontsize=13:x=76:y=500,"
           # MEMPOOL
           f"drawtext=fontfile={FONT_MONO}:text='MEMPOOL':fontcolor={COLOR_MUTED}:fontsize=9:x=250:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_mempool}':fontcolor={COLOR_WHITE}:fontsize=13:x=250:y=500,"
           # ETF FLOW
           f"drawtext=fontfile={FONT_MONO}:text='ETF FLOW':fontcolor={COLOR_MUTED}:fontsize=9:x=424:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_etf}':fontcolor={COLOR_WHITE}:fontsize=13:x=424:y=500,"
           # HALVING
           f"drawtext=fontfile={FONT_MONO}:text='HALVING':fontcolor={COLOR_MUTED}:fontsize=9:x=598:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_halving}':fontcolor={COLOR_WHITE}:fontsize=13:x=598:y=500,"
           # DOMINANCE
           f"drawtext=fontfile={FONT_MONO}:text='DOMINANCE':fontcolor={COLOR_MUTED}:fontsize=9:x=750:y=486,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_m_dominance}':fontcolor={COLOR_WHITE}:fontsize=13:x=750:y=500"
           f"[bv2_metrics];\n")

    # Tag pill (red accent)
    if safe_tag:
        fg += (f"[bv2_metrics]drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.15:t=fill,"
               f"drawbox=x=64:y=580:w=220:h=32:color={COLOR_RED}@0.4:t=2,"
               f"drawtext=fontfile={FONT_MONO}:text='{safe_tag}':"
               f"fontcolor={COLOR_RED}:fontsize=12:x=76:y=590[{label_out}];\n")
    else:
        fg += f"[bv2_metrics]copy[{label_out}];\n"
    return fg


def _bv2_corner_brackets(label_in: str, label_out: str) -> str:
    """APEX corner brackets — BD tactical signal red (#FF0000)."""
    return _build_corner_brackets_fg(label_in, label_out)


def _bv2_encode(inputs, fg, output_path, total_dur, label="bv2 scene",
                audio_pad="[0:a]"):
    """Shared encode pipeline for BV2 scenes — TTS only, no per-segment music.

    APEX V2: Music is mixed ONCE continuously in concatenate_parts() after all
    segments are joined. Individual segments render with clean TTS audio only.

    audio_pad: the audio stream label to use (default [0:a]). Scenes that
    pre-split audio via asplit should pass their output pad here.
    """
    fg += (f"{audio_pad}aformat=channel_layouts=stereo,"
           f"alimiter=limit=0.85:level=disabled:attack=5:release=50,aresample=48000[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label, 300,
    )
    return output_path if ok else ""


def _sanitize_text(text: str) -> str:
    """Sanitize text for FFmpeg drawtext filter."""
    return (text.replace("'", "\u2019").replace('"', "")
                .replace(":", " -").replace(";", ",")
                .replace("[", "(").replace("]", ")")
                .replace("\u2014", "-").replace("\\", "")
                .replace("\n", " ").replace("%", "pct"))


def trim_to_sentence(text: str, max_chars: int = 400) -> str:
    """Trim text at the last sentence boundary before max_chars."""
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    matches = list(re.finditer(r'[.!?](?:\s|$)', chunk))
    if matches:
        last = matches[-1]
        return text[:last.end()].strip()
    # No sentence boundary — trim at last word boundary
    last_space = chunk.rfind(' ')
    return (text[:last_space] if last_space > 0 else chunk).strip()


def _smart_headline(text: str, max_len: int = 90) -> str:
    """Render21 FIX 6: Never truncate headlines. Return full text up to max_len."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > max_len // 2:
        return truncated[:last_space]
    return truncated


def _split_headline_for_render(headline: str, max_line_chars: int = 45):
    """Render21 FIX 6: Split headline into 2 lines if >45 chars. Returns (line1, line2)."""
    if len(headline) <= max_line_chars:
        return (headline, "")
    # Split at last space before char 45
    split_at = headline[:max_line_chars].rfind(" ")
    if split_at < max_line_chars // 2:
        split_at = max_line_chars
    return (headline[:split_at].strip(), headline[split_at:].strip())


def _word_wrap(text: str, max_width: int = 55, max_lines: int = 3) -> str:
    """Word-wrap text for FFmpeg drawtext, return newline-joined string.

    FIX 4: Use actual newline character (0x0a) in the text. When written to
    filter_complex_script file, FFmpeg drawtext renders it as a line break.
    Escaped sequences like \\n or \\\\n do NOT work in filter_complex_script mode.
    """
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
    return "\n".join(lines)
