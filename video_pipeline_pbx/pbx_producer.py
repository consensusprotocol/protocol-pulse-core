#!/usr/bin/env python3
"""PBX Producer — Daily video pipeline with PBX avatar format.

Orchestrates: transcript scan → clip selection → script generation →
PBX TTS → avatar assembly → final video.

Single narrator (PBX voice), avatar left + clip right layout.

Usage:
    python3 pbx_producer.py              # Full production run
    python3 pbx_producer.py --test       # Test mode (fewer clips)
    python3 pbx_producer.py --fast-test  # Fast test (hardcoded script, no API)
    python3 pbx_producer.py --skip-scan  # Use cached transcripts
"""
import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure imports resolve
BASE = str(Path(__file__).resolve().parent)
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
V3_DIR = str(Path(PROJECT_ROOT) / "video_pipeline_v3")

sys.path.insert(0, BASE)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, V3_DIR)

from relay import get_key
from pbx_tts import generate_pbx_audio
from pbx_assembler import assemble_episode

logger = logging.getLogger("pbx_producer")

# ── Shared from V3 pipeline ─────────────────────────────────────────────────
# These are symlinked / imported from video_pipeline_v3
try:
    from channel_scanner import scan_channels
except ImportError:
    scan_channels = None

try:
    from clip_selector import select_clips
except ImportError:
    select_clips = None

try:
    from clip_extractor import extract_all
except ImportError:
    extract_all = None


def get_btc_price() -> str:
    """Fetch current BTC price."""
    import requests
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=10
        )
        price = r.json()["bitcoin"]["usd"]
        return f"${price:,.0f}"
    except Exception:
        try:
            r = requests.get("https://mempool.space/api/v1/prices", timeout=10)
            return f"${r.json()['USD']:,.0f}"
        except Exception:
            return "$0"


def generate_script(clips: list, btc_price: str, test_mode: bool = False) -> dict:
    """Generate PBX single-narrator script from selected clips.

    Uses Claude to write a solo-anchor dialogue where PBX introduces each clip,
    plays it, then reacts — ending with a wrap.
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=get_key("ANTHROPIC_API_KEY"))
    except Exception as e:
        logger.warning(f"Claude unavailable ({e}) — using fallback script")
        return _build_fallback_script(clips, btc_price)

    clips_context = "\n".join(
        f"CLIP {c.get('rank', i+1)}: [{c.get('channel', 'Unknown')}] \"{c.get('title', '')}\"\n"
        f"  Quote: {c.get('quote', 'N/A')}\n"
        f"  Why: {c.get('why', 'Relevant Bitcoin insight')}"
        for i, c in enumerate(clips[:5])
    )

    max_clips = 3 if test_mode else 5

    prompt = f"""You are PBX, the solo anchor of Protocol Pulse — a Bitcoin intelligence broadcast.
Write a video script for today's Pulse Check episode.

BTC Price: {btc_price}
Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}

CLIPS TO DISCUSS:
{clips_context}

FORMAT RULES:
- Single narrator (PBX) — no co-host, no "we"
- Cold open: 2-3 punchy sentences setting the tone
- For each clip (max {max_clips}): setup (2-3 sentences), then CLIP marker, then react (2-3 sentences)
- Wrap: 2-3 sentences sign-off ending with "Stay free. Stay sovereign. This is PBX, Protocol Pulse."
- Total spoken text: 600-900 words
- Tone: confident broadcaster, data-driven, no hype

OUTPUT JSON:
{{
  "title": "episode title",
  "dialogue": [
    {{"host": 2, "type": "cold_open", "text": "..."}},
    {{"host": 2, "type": "setup", "text": "...", "topic": "clip topic"}},
    {{"host": "CLIP", "type": "clip", "rank": 1, "duration": 60, "channel": "...", "video_id": "..."}},
    {{"host": 2, "type": "react", "text": "..."}},
    ... more clips ...
    {{"host": 2, "type": "wrap", "text": "... Stay free. Stay sovereign. This is PBX, Protocol Pulse."}}
  ]
}}

Return ONLY the JSON object, no markdown fences."""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
        script = json.loads(text)
        logger.info(f"Script generated: {len(script.get('dialogue', []))} entries")
        return script
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        return _build_fallback_script(clips, btc_price)


def _build_fallback_script(clips: list, btc_price: str) -> dict:
    """Hardcoded fallback script when Claude is unavailable."""
    dialogue = [
        {"host": 2, "type": "cold_open",
         "text": f"Bitcoin at {btc_price}. This is your Pulse Check. Let's get into what the smartest minds in Bitcoin are saying today."},
    ]

    for i, clip in enumerate(clips[:3]):
        channel = clip.get("channel", "Unknown")
        title = clip.get("title", "")
        dialogue.append({
            "host": 2, "type": "setup",
            "text": f"{channel} dropped an important segment. Here's what they had to say.",
            "topic": title[:60],
        })
        dialogue.append({
            "host": "CLIP", "type": "clip",
            "rank": clip.get("rank", i + 1),
            "duration": clip.get("duration", 60),
            "channel": channel,
            "video_id": clip.get("video_id", ""),
        })
        dialogue.append({
            "host": 2, "type": "react",
            "text": "Interesting perspective. Let's keep moving.",
        })

    dialogue.append({
        "host": 2, "type": "wrap",
        "text": "That's your Pulse Check for today. Stay free. Stay sovereign. This is PBX, Protocol Pulse.",
    })

    return {"title": f"Pulse Check — {btc_price}", "dialogue": dialogue}


def _build_fast_test_script() -> dict:
    """Hardcoded script for --fast-test mode (no API calls)."""
    return {
        "title": "PBX Fast Test",
        "dialogue": [
            {"host": 2, "type": "cold_open",
             "text": "Bitcoin just printed a new local high. This is PBX with a quick pulse check."},
            {"host": 2, "type": "setup",
             "text": "Simply Bitcoin had a key segment on the mining difficulty adjustment.",
             "topic": "Mining Difficulty"},
            {"host": 2, "type": "react",
             "text": "The hashrate is telling us something the price hasn't priced in yet."},
            {"host": 2, "type": "wrap",
             "text": "That's the pulse. Stay free. Stay sovereign. This is PBX, Protocol Pulse."},
        ],
    }


# ── Main Pipeline ────────────────────────────────────────────────────────────

def run_pipeline(test_mode: bool = False, skip_scan: bool = False,
                 fast_test: bool = False) -> bool:
    """Run the full PBX video production pipeline."""
    if fast_test:
        test_mode = True
        skip_scan = True

    ts = datetime.now(timezone.utc)
    date_str = ts.strftime("%Y%m%d")
    time_str = ts.strftime("%Y%m%d_%H%M%S")

    if test_mode:
        run_dir = os.path.join(BASE, "output", f"test_{time_str}")
    else:
        run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))

    os.makedirs(run_dir, exist_ok=True)
    audio_dir = os.path.join(run_dir, "audio")
    clips_dir = os.path.join(run_dir, "clips")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    final_video = os.path.join(run_dir, f"pbx_pulse_{date_str}.mp4")
    t_start = time.time()

    mode_label = "FAST TEST" if fast_test else ("TEST" if test_mode else "PRODUCTION")
    print("\n" + "=" * 60)
    print(f"  PBX PULSE CHECK — {mode_label}")
    print(f"  Output: {run_dir}")
    print("=" * 60)

    # ── Step 1: BTC Price ────────────────────────────────────────────────────
    print("\n[1/7] Fetching BTC price...")
    btc_price = get_btc_price()
    print(f"  BTC: {btc_price}")

    # ── Step 2: Scan channels (reuse V3 transcripts) ─────────────────────────
    clips = []
    if not fast_test:
        if not skip_scan and scan_channels:
            print("\n[2/7] Scanning partner channels...")
            try:
                scan_channels()
                print("  Channel scan complete")
            except Exception as e:
                logger.warning(f"Channel scan failed: {e}")
                print(f"  Scan failed: {e} — using cached transcripts")
        else:
            print("\n[2/7] Skipping channel scan (using cached transcripts)")

        # ── Step 3: Select clips ─────────────────────────────────────────────
        print("\n[3/7] Selecting clips...")
        if select_clips:
            try:
                # Load transcripts from V3
                transcript_dir = os.path.join(V3_DIR, "transcripts")
                videos = []
                for tf in sorted(Path(transcript_dir).glob("*.json"), key=os.path.getmtime, reverse=True)[:50]:
                    try:
                        with open(tf) as f:
                            data = json.load(f)
                        videos.append(data)
                    except Exception:
                        continue

                if videos:
                    sel = select_clips(videos)
                    clips = sel.get("clips", []) if isinstance(sel, dict) else sel
                    print(f"  Selected {len(clips)} clips")

                    # Save selections
                    with open(os.path.join(run_dir, "selections.json"), "w") as f:
                        json.dump(clips, f, indent=2)
                else:
                    print("  No transcripts available")
            except Exception as e:
                logger.error(f"Clip selection failed: {e}")
                print(f"  Selection failed: {e}")
        else:
            print("  clip_selector not available")

        # ── Step 4: Extract clips ────────────────────────────────────────────
        if clips and extract_all:
            print(f"\n[4/7] Extracting {len(clips)} clips...")
            try:
                extract_all(clips, clips_dir)
                print(f"  Clips extracted to {clips_dir}")
            except Exception as e:
                logger.error(f"Clip extraction failed: {e}")
                print(f"  Extraction failed: {e}")
        else:
            print("\n[4/7] Skipping clip extraction")

    # ── Step 5: Generate script ──────────────────────────────────────────────
    if fast_test:
        print("\n[5/7] Using fast-test script...")
        script = _build_fast_test_script()
    else:
        print("\n[5/7] Generating PBX script...")
        script = generate_script(clips, btc_price, test_mode)

    script_path = os.path.join(run_dir, "script.json")
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)
    print(f"  Script: {len(script.get('dialogue', []))} entries")

    # ── Step 6: TTS Audio ────────────────────────────────────────────────────
    print("\n[6/7] Generating PBX voice audio...")
    tts_result = generate_pbx_audio(script.get("dialogue", []), audio_dir)
    print(f"  TTS: {tts_result['ok_count']} lines OK, {tts_result['fail_count']} failed")

    if tts_result["ok_count"] == 0:
        print("  [FAIL] No TTS audio generated!")
        return False

    # ── Step 7: Assemble video ───────────────────────────────────────────────
    print("\n[7/7] Assembling PBX video...")
    result = assemble_episode(script, audio_dir, clips_dir, final_video, btc_price)

    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    if result["ok"]:
        print(f"  PBX PULSE CHECK COMPLETE")
        print(f"  Output: {result['output_path']}")
        print(f"  Duration: {result['duration']:.1f}s")
        print(f"  Parts: {result['parts_count']}")
        print(f"  Elapsed: {elapsed:.0f}s")
    else:
        print(f"  ASSEMBLY FAILED: {result.get('error', 'unknown')}")
    print("=" * 60)

    return result["ok"]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="PBX Pulse Check Producer")
    parser.add_argument("--test", action="store_true", help="Test mode (fewer clips)")
    parser.add_argument("--fast-test", action="store_true", help="Fast test (no API calls)")
    parser.add_argument("--skip-scan", action="store_true", help="Skip channel scan")
    args = parser.parse_args()

    ok = run_pipeline(
        test_mode=args.test,
        skip_scan=args.skip_scan,
        fast_test=args.fast_test,
    )
    sys.exit(0 if ok else 1)
