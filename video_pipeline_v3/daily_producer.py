#!/usr/bin/env python3
"""Daily Pulse Check Producer V5 — clip-first pipeline.

Real YouTube clips from partner channels, host dialogue around them,
music integration, cold open, avatar shorts.

Usage:
  python3 daily_producer.py               # Full daily episode
  python3 daily_producer.py --test        # Test mode (fewer clips, truncated)
  python3 daily_producer.py --skip-scan   # Use cached transcripts only
  python3 daily_producer.py --fast-test   # Fast test: no API calls, <3 min render
"""
import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from channel_scanner import scan_all_channels
from clip_selector import select_clips
from clip_extractor import extract_all, check_av_sync
from script_writer import generate_from_clips
from tts_engine import generate_dialogue_audio
from assembler import assemble_episode, verify_video
from shorts_cutter import generate_shorts
from thumbnail_gen import generate_thumbnail
from chapters import generate_chapters
from podcast_feed import extract_podcast_audio, generate_rss_item
from newsletter_embed import generate_email_html, save_newsletter_html
from music import ensure_music_dir, has_music, has_intro, has_outro
from utils.feature_flags import is_enabled, load_all as load_flags
from utils.quality_gate import compute_quality_score, should_upload, format_score_report
from utils.telegram_alerts import (
    alert_pipeline_start, alert_pipeline_success,
    alert_pipeline_failure, alert_quality_hold, alert_upload_success,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("Producer")


def get_btc_price() -> str:
    """Fetch current BTC price from mempool.space."""
    try:
        import requests
        r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
        if r.status_code == 200:
            usd = r.json().get("USD", 0)
            return f"${usd:,.0f}"
    except Exception:
        pass
    return "$97,000"  # Fallback


def _build_fast_test_script(clips_info: dict, btc_price: str) -> dict:
    """Build a minimal hardcoded script for fast-test mode (no Claude API call)."""
    dialogue = []
    # Cold open
    dialogue.append({
        "host": 1, "type": "cold_open",
        "text": f"Bitcoin at {btc_price}. Let's get into today's pulse check.",
    })
    # For each clip, add a setup + clip marker + react
    for rank, info in sorted(clips_info.items()):
        channel = info.get("channel", "Unknown")
        dialogue.append({
            "host": 1, "type": "setup",
            "text": f"Here's what {channel} had to say.",
        })
        dialogue.append({
            "host": "CLIP", "type": "clip",
            "rank": rank, "source_id": info.get("video_id", ""),
        })
        dialogue.append({
            "host": 2, "type": "react",
            "text": "Interesting take. Let's keep moving.",
        })
    # Wrap
    dialogue.append({
        "host": 1, "type": "wrap",
        "text": "That's the pulse check for today. Like, subscribe, and we'll see you next time.",
    })
    return {
        "episode_title": f"Fast Test — {btc_price}",
        "dialogue": dialogue,
        "thumbnail": {"headline": "FAST TEST", "subtext": btc_price},
    }


def run_pipeline(test_mode: bool = False, skip_scan: bool = False,
                 fast_test: bool = False) -> bool:
    # Fast test implies test + skip-scan
    if fast_test:
        test_mode = True
        skip_scan = True

    ts = datetime.now()
    date_str = ts.strftime("%Y%m%d")
    time_str = ts.strftime("%Y%m%d_%H%M%S")

    if test_mode:
        run_dir = os.path.join(BASE, "output", f"test_{time_str}")
    else:
        run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))

    os.makedirs(run_dir, exist_ok=True)
    final_video = os.path.join(run_dir, f"pulse_check_{date_str}.mp4")
    timing = {}
    t_pipeline_start = time.time()

    # Ensure music directory exists
    ensure_music_dir()

    # Log feature flags at startup
    flags = load_flags()
    logger.info(f"Feature flags: {json.dumps(flags)}")

    # Telegram alert at pipeline start
    if is_enabled("telegram_alerts"):
        alert_pipeline_start(date_str, test_mode)

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK V5 — CLIP-FIRST PIPELINE")
    mode_label = "FAST TEST " if fast_test else ("TEST " if test_mode else "")
    print(f"  {mode_label}Run {time_str}")
    print(f"  Output: {run_dir}")
    print(f"  Music: {'YES' if has_music() else 'no (skipped gracefully)'}")
    print("=" * 70)

    # ── Step 1: BTC PRICE ─────────────────────────────────────────────────
    print("\n[STEP 1/12] FETCHING BTC PRICE...")
    t0 = time.time()
    btc_price = get_btc_price()
    print(f"  BTC: {btc_price}")
    timing["1_price"] = round(time.time() - t0, 2)

    # ── Step 2: SCAN CHANNELS ─────────────────────────────────────────────
    print("\n[STEP 2/12] SCANNING PARTNER CHANNELS...")
    t0 = time.time()
    if skip_scan:
        # Load cached transcripts from transcript dir
        import glob
        transcript_dir = os.path.join(BASE, "transcripts")
        videos = []
        for tf in sorted(glob.glob(os.path.join(transcript_dir, "*.json")))[:20]:
            with open(tf) as f:
                data = json.load(f)
                videos.append({
                    "video_id": data.get("video_id", ""),
                    "title": data.get("title", ""),
                    "channel": data.get("channel", ""),
                    "duration": data.get("duration", 0),
                    "upload_date": "",
                    "url": f"https://www.youtube.com/watch?v={data.get('video_id', '')}",
                    "transcript_text": data.get("text", ""),
                    "timestamped_text": data.get("timestamped_text", ""),
                })
        print(f"  Loaded {len(videos)} cached transcripts")
    else:
        whisper_model = "tiny" if test_mode else "base"
        videos = scan_all_channels(model_size=whisper_model)
        print(f"  Scanned: {len(videos)} videos with transcripts")
    timing["2_scan"] = round(time.time() - t0, 2)

    if not videos:
        print("\n  [FAIL] No videos found — cannot produce episode")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "scan", "No videos found")
        return False

    # ── Step 3: SELECT BEST CLIPS ─────────────────────────────────────────
    if fast_test:
        print("\n[STEP 3/12] SELECTING CLIPS (fast-test: first 2, no Claude)...")
        t0 = time.time()
        # Build minimal selections from cached videos without calling Claude
        fast_clips = []
        for i, v in enumerate(videos[:2], 1):
            text = v.get("transcript_text", "")
            fast_clips.append({
                "rank": i,
                "video_id": v["video_id"],
                "channel": v.get("channel", ""),
                "title": v.get("title", ""),
                "quote": text[:100] if text else "No transcript",
                "why": "fast-test auto-select",
                "start_seconds": 60,
                "end_seconds": 90,
            })
        selections = {"clips": fast_clips}
        clips = fast_clips
        print(f"  Auto-selected: {len(clips)} clips (no API call)")
        timing["3_select"] = round(time.time() - t0, 2)
    else:
        print("\n[STEP 3/12] SELECTING BEST CLIPS (Claude)...")
        t0 = time.time()
        selections = select_clips(videos)
        clips = selections.get("clips", [])
        print(f"  Selected: {len(clips)} clips")
        for c in clips:
            print(f"    #{c['rank']}: [{c.get('channel','')}] {c.get('quote','')[:50]}...")
        timing["3_select"] = round(time.time() - t0, 2)

    if not clips:
        print("\n  [FAIL] No clips selected — cannot produce episode")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "select", "No clips selected")
        return False

    # In test mode, use only top 2 clips
    if not fast_test and test_mode and len(clips) > 2:
        selections["clips"] = clips[:2]
        clips = selections["clips"]
        print(f"  [test] Truncated to {len(clips)} clips")

    # Save selections
    sel_path = os.path.join(run_dir, "selections.json")
    with open(sel_path, "w") as f:
        json.dump(selections, f, indent=2)

    # ── Step 4: EXTRACT CLIPS ─────────────────────────────────────────────
    print("\n[STEP 4/12] EXTRACTING CLIPS (yt-dlp with original audio)...")
    t0 = time.time()
    clip_dir = os.path.join(run_dir, "clips")
    extracted_clips = extract_all(selections, clip_dir)
    print(f"  Extracted: {len(extracted_clips)}/{len(clips)} clips")
    for rank, info in sorted(extracted_clips.items()):
        print(f"    #{rank}: {info['channel']} — {info['duration']:.1f}s")
    timing["4_extract"] = round(time.time() - t0, 2)

    if not extracted_clips:
        print("\n  [FAIL] No clips extracted — cannot produce episode")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "extract", "No clips extracted")
        return False

    # ── Step 4b: MOOD CLASSIFICATION + MUSIC SELECTION ──────────────────
    import glob as _glob
    import random as _random

    def classify_episode_mood(script_text: str) -> str:
        """Classify episode mood from clip quotes."""
        moods = {"tense": 0, "confident": 0, "contemplative": 0, "upbeat": 0, "edge": 0}
        lower = script_text.lower()
        if any(w in lower for w in ["crash", "sell", "breaking", "emergency", "plunge", "war"]):
            moods["tense"] += 3
        if any(w in lower for w in ["bullish", "ath", "record", "buying", "accumul"]):
            moods["confident"] += 3
        if any(w in lower for w in ["philosoph", "long-term", "decade", "future", "think about"]):
            moods["contemplative"] += 2
        if any(w in lower for w in ["community", "fun", "meme", "laugh", "celebrate"]):
            moods["upbeat"] += 2
        if any(w in lower for w in ["controversial", "scam", "fraud", "attack", "fight"]):
            moods["edge"] += 2
        best = max(moods, key=moods.get)
        return best if moods[best] > 0 else "confident"

    def select_music_bed(mood: str, music_dir: str) -> str:
        tracks = _glob.glob(os.path.join(music_dir, f"{mood}_*.mp3"))
        if not tracks:
            tracks = _glob.glob(os.path.join(music_dir, "confident_*.mp3"))
        if not tracks:
            tracks = _glob.glob(os.path.join(music_dir, "*.mp3"))
        return _random.choice(tracks) if tracks else ""

    def select_intro_music(music_dir: str) -> str:
        tracks = _glob.glob(os.path.join(music_dir, "intro_*.mp3"))
        return _random.choice(tracks) if tracks else ""

    # Classify mood from clip quotes
    clip_quotes = " ".join(c.get("quote", "") + " " + c.get("why", "") for c in clips)
    episode_mood = classify_episode_mood(clip_quotes)
    music_dir = os.path.join(BASE, "assets", "music")
    music_bed = select_music_bed(episode_mood, music_dir)
    intro_music = select_intro_music(music_dir)
    print(f"  Mood: {episode_mood} | Music: {os.path.basename(music_bed) if music_bed else 'default'}")

    # ── Step 4c: LIVE SIGNALS ─────────────────────────────────────────────
    live_context = ""
    live_signals_path = os.path.join(BASE, "data", "intelligence", "live_signals.json")
    try:
        if os.path.exists(live_signals_path):
            with open(live_signals_path) as f:
                live_data = json.load(f)
            from datetime import timezone as _tz
            now = datetime.now(_tz.utc) if hasattr(datetime, 'now') else datetime.utcnow()
            active_streams = []
            for s in live_data.get("live_streams", []):
                # Only include streams from last 6 hours
                started = s.get("started_at", "")
                try:
                    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    age_hours = (now - started_dt).total_seconds() / 3600
                    if age_hours > 6:
                        continue
                except (ValueError, AttributeError):
                    continue
                source = s.get("source", "youtube_live")
                channel = s.get("channel", "unknown")
                title = s.get("title", "")
                topics = ", ".join(s.get("topics", []))
                sentiment = s.get("current_sentiment", 50)
                sentiment_label = "bullish" if sentiment > 60 else "bearish" if sentiment < 40 else "neutral"
                active_streams.append(
                    f"- {channel} ({source}): \"{title}\" — topics: {topics}, sentiment: {sentiment_label} ({sentiment})"
                )
            if active_streams:
                live_context = "\n".join(active_streams)
                print(f"  Live signals: {len(active_streams)} active streams in last 6 hours")
                for line in active_streams:
                    print(f"    {line}")
            else:
                print("  Live signals: no active streams in last 6 hours")
    except Exception as e:
        logger.warning(f"Live signals read failed: {e}")

    # ── Step 5: GENERATE SCRIPT ───────────────────────────────────────────
    if fast_test:
        print("\n[STEP 5/12] GENERATING SCRIPT (fast-test: hardcoded, no Claude)...")
        t0 = time.time()
        script = _build_fast_test_script(extracted_clips, btc_price)
        dialogue = script["dialogue"]
        speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
        clip_markers = [d for d in dialogue if d.get("host") == "CLIP"]
        print(f"  Title: {script.get('episode_title', 'Untitled')}")
        print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips (hardcoded)")
        timing["5_script"] = round(time.time() - t0, 2)
    else:
        print("\n[STEP 5/12] GENERATING HOST DIALOGUE (Claude)...")
        t0 = time.time()
        script = generate_from_clips(selections, btc_price=btc_price,
                                     live_context=live_context)
        dialogue = script.get("dialogue", [])
        speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
        clip_markers = [d for d in dialogue if d.get("host") == "CLIP"]
        print(f"  Title: {script.get('episode_title', 'Untitled')}")
        print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips")
        timing["5_script"] = round(time.time() - t0, 2)

    # Issue 9: Sort social posts ONCE by engagement (likes desc), store on script
    # This ensures assembler uses the EXACT SAME order as script_writer
    try:
        from utils.social_fetcher import get_todays_social_posts
        sorted_social = get_todays_social_posts(max_posts=5)
        if sorted_social:
            sorted_social.sort(key=lambda p: p.get("likes", 0), reverse=True)
            script["social_posts"] = sorted_social
            for si, sp in enumerate(sorted_social):
                logger.info(f"SOCIAL ORDER: #{si}: @{sp.get('handle', '?')} — {sp.get('text', '')[:40]}")
    except Exception as e:
        logger.warning(f"Social posts fetch for ordering failed: {e}")

    # Save script
    script_path = os.path.join(run_dir, "script.json")
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)

    # ── Step 6: TTS ───────────────────────────────────────────────────────
    print("\n[STEP 6/12] GENERATING DUAL-HOST AUDIO (ElevenLabs)...")
    t0 = time.time()
    audio_dir = os.path.join(run_dir, "audio")
    audio_data = generate_dialogue_audio(dialogue, audio_dir)
    successful = sum(1 for l in audio_data.get("lines", [])
                     if l.get("path") and os.path.exists(l.get("path", "")))
    print(f"  Audio: {successful}/{len(speech_lines)} lines")
    print(f"  Duration: {audio_data.get('total_duration', 0):.1f}s")
    timing["6_tts"] = round(time.time() - t0, 2)

    # ── Step 7: ASSEMBLE ──────────────────────────────────────────────────
    print("\n[STEP 7/12] ASSEMBLING VIDEO...")
    t0 = time.time()
    result = assemble_episode(script, audio_data, extracted_clips, final_video,
                              btc_price=btc_price, music_bed=music_bed,
                              intro_music=intro_music)
    timing["7_assemble"] = round(time.time() - t0, 2)

    if not result or not os.path.exists(final_video):
        print("\n  [FAIL] Assembly failed")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        if is_enabled("telegram_alerts"):
            alert_pipeline_failure(date_str, "assemble", "Video assembly failed")
        return False

    # ── Step 8: SHORTS ────────────────────────────────────────────────────
    print("\n[STEP 8/12] GENERATING SHORTS (avatar)...")
    t0 = time.time()
    shorts_dir = os.path.join(run_dir, "shorts")
    shorts = generate_shorts(script, shorts_dir, btc_price=btc_price,
                             max_shorts=3 if not test_mode else 1)
    print(f"  Shorts: {len(shorts)}")
    timing["8_shorts"] = round(time.time() - t0, 2)

    # ── Step 9: THUMBNAIL ─────────────────────────────────────────────────
    print("\n[STEP 9/12] GENERATING THUMBNAIL (MMA Central style)...")
    t0 = time.time()
    thumb_data = script.get("thumbnail", {})
    top_quote = ""
    if clips:
        top_quote = clips[0].get("quote", "")
    thumb_path = os.path.join(run_dir, "thumbnail.png")
    generate_thumbnail(
        thumb_data.get("headline", script.get("episode_title", "PULSE CHECK")),
        thumb_data.get("subtext", ""),
        thumb_path,
        btc_price=btc_price,
        top_quote=top_quote,
    )
    timing["9_thumbnail"] = round(time.time() - t0, 2)

    # ── Step 10: CHAPTERS ─────────────────────────────────────────────────
    print("\n[STEP 10/12] GENERATING CHAPTERS...")
    t0 = time.time()
    chapters_path = os.path.join(run_dir, "chapters.txt")
    generate_chapters(script, audio_data, chapters_path)
    timing["10_chapters"] = round(time.time() - t0, 2)

    # ── Step 11: PODCAST + NEWSLETTER ─────────────────────────────────────
    print("\n[STEP 11/12] PODCAST AUDIO + NEWSLETTER...")
    t0 = time.time()
    podcast_path = os.path.join(run_dir, "podcast.mp3")
    extract_podcast_audio(final_video, podcast_path)

    email_html = generate_email_html(
        script.get("episode_title", "Pulse Check"),
        segments_summary=script.get("segments_summary", []),
        btc_price=btc_price,
    )
    newsletter_path = os.path.join(run_dir, "newsletter.html")
    save_newsletter_html(email_html, newsletter_path)
    timing["11_podcast_newsletter"] = round(time.time() - t0, 2)

    # ── Step 12: VERIFY ───────────────────────────────────────────────────
    print("\n[STEP 12/12] VERIFYING OUTPUT...")
    t0 = time.time()
    passed = verify_video(final_video)

    # Final AV sync validation
    final_offset = check_av_sync(final_video)
    print(f"  Final AV sync offset: {final_offset:+.3f}s")
    if abs(final_offset) > 0.05:
        logger.error(f"FINAL OUTPUT SYNC FAILED: {final_offset:+.3f}s > 0.05s — nuclear re-encode")
        nuclear_tmp = final_video + ".nuclear.mp4"
        nuclear_cmd = subprocess.run([
            "ffmpeg", "-y",
            "-fflags", "+genpts+igndts",
            "-i", final_video,
            "-c:v", "libx264", "-preset", "medium",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-r", "30", "-vsync", "cfr",
            "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
            "-movflags", "+faststart",
            nuclear_tmp,
        ], capture_output=True, text=True, timeout=600)
        if nuclear_cmd.returncode == 0 and os.path.exists(nuclear_tmp):
            os.replace(nuclear_tmp, final_video)
            recheck = check_av_sync(final_video)
            print(f"  Nuclear re-encode done. New offset: {recheck:+.3f}s")
        elif os.path.exists(nuclear_tmp):
            os.remove(nuclear_tmp)

    # Final bitrate validation
    br_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
        capture_output=True, text=True,
    )
    try:
        br_info = json.loads(br_result.stdout)
        bitrate = int(br_info.get("format", {}).get("bit_rate", 0))
        print(f"  Final bitrate: {bitrate / 1_000_000:.1f} Mbps")
        if bitrate < 3_000_000:
            logger.error(f"FINAL OUTPUT QUALITY FAILED: {bitrate / 1_000_000:.1f}Mbps < 3Mbps")
    except Exception:
        pass

    timing["12_verify"] = round(time.time() - t0, 2)

    # ── Summary ──────────────────────────────────────────────────────────
    timing["total"] = round(time.time() - t_pipeline_start, 2)

    # Video stats
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", final_video],
        capture_output=True, text=True,
    )
    try:
        info = json.loads(r.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])
        vid = next((s for s in streams if s.get("codec_type") == "video"), {})
        aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
        dur = float(fmt.get("duration", 0))
        sz = int(fmt.get("size", 0)) / 1024 / 1024
        timing["video_duration"] = round(dur, 1)
        timing["video_size_mb"] = round(sz, 1)
    except Exception:
        vid, aud, dur, sz = {}, {}, 0, 0

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK V5 — {'SUCCESS' if passed else 'COMPLETE (warnings)'}")
    print(f"  Title:    {script.get('episode_title', 'Untitled')}")
    print(f"  Video:    {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
    print(f"  Audio:    {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
    print(f"  Size:     {sz:.1f}MB")
    print(f"  Clips:    {len(extracted_clips)} real YouTube clips with original audio")
    print(f"  Shorts:   {len(shorts)}")
    print(f"  Music:    {'layered' if has_music() else 'none (graceful skip)'}")

    outputs = {
        "video": final_video,
        "shorts": [s for s in shorts],
        "thumbnail": thumb_path,
        "chapters": chapters_path,
        "podcast": podcast_path,
        "newsletter": newsletter_path,
        "script": script_path,
        "selections": sel_path,
    }

    print(f"\n  OUTPUT FILES:")
    for name, path in outputs.items():
        if isinstance(path, list):
            for p in path:
                exists = "Y" if os.path.exists(p) else "N"
                print(f"    [{exists}] {os.path.basename(p)}")
        else:
            exists = "Y" if os.path.exists(path) else "N"
            print(f"    [{exists}] {os.path.basename(path)}")

    print(f"\n  TIMING:")
    for step, secs in timing.items():
        if step not in ("video_duration", "video_size_mb"):
            print(f"    {step:25s}: {secs:.1f}s")
    print(f"\n  Output: {run_dir}")
    print("=" * 70)

    _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)

    # Save manifest
    manifest = {
        "version": "v5",
        "episode_title": script.get("episode_title", ""),
        "btc_price": btc_price,
        "test_mode": test_mode,
        "timestamp": time_str,
        "clips_used": [
            {"rank": r, "channel": info.get("channel", ""), "video_id": info.get("video_id", "")}
            for r, info in sorted(extracted_clips.items())
        ],
        "outputs": {k: (v if isinstance(v, list) else [v]) for k, v in outputs.items()},
        "timing": timing,
        "success": passed,
    }
    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # ── Step 13: QUALITY GATE + AUTO-UPLOAD ────────────────────────────────
    print("\n[STEP 13] QUALITY GATE...")
    t0 = time.time()
    quality_score = compute_quality_score(manifest_path)
    print(f"  {format_score_report(quality_score)}")
    manifest["quality_score"] = quality_score

    if is_enabled("youtube_auto_upload") and should_upload(quality_score):
        from utils.youtube_upload import upload_episode as yt_upload, build_description, build_tags
        # Build YouTube metadata
        ep_title = script.get("episode_title", "Pulse Check")
        yt_title = f"Bitcoin Daily Brief — {ts.strftime('%b %d, %Y')} | Protocol Pulse"
        chapters_text = ""
        if os.path.exists(chapters_path):
            with open(chapters_path) as f:
                chapters_text = f.read()
        yt_description = build_description(
            summary=f"{ep_title}\n\nBTC Price: {btc_price}",
            chapters_text=chapters_text,
        )
        topics = [c.get("channel", "") for c in clips]
        yt_tags = build_tags(topics)

        print(f"  Uploading to YouTube (unlisted)...")
        upload_result = yt_upload(
            final_video, yt_title, yt_description,
            tags=yt_tags, thumbnail_path=thumb_path, privacy="unlisted",
        )
        print(f"  Upload result: {upload_result.get('status')}")
        if upload_result.get("url"):
            print(f"  URL: {upload_result['url']}")
        manifest["upload_result"] = upload_result
        if is_enabled("telegram_alerts") and upload_result.get("url"):
            alert_upload_success(date_str, upload_result["url"])
    elif quality_score < 85:
        logger.warning(f"QUALITY HOLD: Score {quality_score} < 85. Episode held for review.")
        hold_path = os.path.join(run_dir, "HOLD_FOR_REVIEW.txt")
        with open(hold_path, "w") as f:
            f.write(f"Quality score: {quality_score}/100\n")
            f.write(f"Threshold: 85\n")
            f.write(f"Reason: Below quality threshold\n")
            f.write(f"Episode: {script.get('episode_title', '')}\n")
            f.write(f"Video: {final_video}\n")
        manifest["held_for_review"] = True
        if is_enabled("telegram_alerts"):
            alert_quality_hold(date_str, quality_score)
    else:
        logger.info("YouTube auto-upload disabled in feature flags")

    # Write final manifest with quality score
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    timing["13_quality_gate"] = round(time.time() - t0, 2)

    # Save episode performance data (V17)
    try:
        from utils.analytics_store import save_episode_performance
        perf_data = {
            "date": ts.strftime("%Y-%m-%d"),
            "episode_title": script.get("episode_title", ""),
            "channels_used": [c.get("channel", "") for c in manifest.get("clips_used", [])],
            "quality_score": manifest.get("quality_score", 0),
            "clips_count": len(manifest.get("clips_used", [])),
            "duration_seconds": round(timing.get("video_duration", 0), 1),
            "bitrate_mbps": round(timing.get("video_size_mb", 0) * 8 / max(timing.get("video_duration", 1), 1), 1),
            "av_sync_offset": round(final_offset, 3),
            "music_mood": episode_mood,
            "test_mode": test_mode,
        }
        save_episode_performance(date_str, perf_data)
    except Exception as e:
        logger.warning(f"Performance data save failed: {e}")

    # Telegram success alert
    if is_enabled("telegram_alerts") and passed:
        alert_pipeline_success(date_str, quality_score,
                               timing.get("video_duration", 0), final_video)

    return passed


def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
    report_path = os.path.join(run_dir, "timing_report.txt")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "PULSE CHECK V5 — Timing Report",
        f"Generated: {ts}",
        f"Status: {'SUCCESS' if success else 'FAILED'}",
        "",
        "STEP TIMINGS:",
    ]
    for step, val in timing.items():
        if step in ("video_duration", "video_size_mb"):
            continue
        lines.append(f"  {step:<25}: {val:.1f}s")
    lines += [
        "",
        "OUTPUT STATS:",
        f"  video_duration_s     : {timing.get('video_duration', 'N/A')}",
        f"  video_size_mb        : {timing.get('video_size_mb', 'N/A')}",
        f"  total_wall_time_s    : {time.time() - t_start:.1f}",
    ]
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Pulse Check V5 — Clip-First Video Producer")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: fewer clips, truncated, test output dir")
    parser.add_argument("--skip-scan", action="store_true",
                        help="Skip channel scanning, use cached transcripts")
    parser.add_argument("--fast-test", action="store_true",
                        help="Fast test: no API calls (Claude/scan), hardcoded script, <3 min render")
    args = parser.parse_args()
    success = run_pipeline(test_mode=args.test, skip_scan=args.skip_scan,
                           fast_test=args.fast_test)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
