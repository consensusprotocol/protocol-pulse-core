#!/usr/bin/env python3
"""
FIRST REAL RUN — Pulse Check Episode Producer
===============================================
Streamlined pipeline that uses all the components we've built.
Runs the complete pipeline: scan → triage → direct → clip → narrate → assemble.

Usage:
    python3 -m services.video_engine.first_run
    python3 -m services.video_engine.first_run --test  # 2 channels, 1 story
"""
import json
import logging
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# Setup
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("FirstRun")

# Load .env
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def run(test_mode: bool = False):
    """Execute the full pipeline."""
    start_time = time.time()
    date_str = datetime.now().strftime("%Y-%m-%d")
    bundle = Path(f"data/episodes/{date_str}")
    bundle.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    for sub in ["audio", "clips", "voiceovers", "work", "final",
                "shorts", "manifest", "logs", "costs", "candidates",
                "show_plan", "sources"]:
        (bundle / sub).mkdir(exist_ok=True)

    costs = {
        "episode_date": date_str,
        "whisper_minutes": 0,
        "grok_tokens_in": 0, "grok_tokens_out": 0,
        "claude_tokens_in": 0, "claude_tokens_out": 0,
        "elevenlabs_characters": 0,
    }

    logger.info(f"\n{'#'*70}")
    logger.info(f"  PULSE CHECK — FIRST RUN")
    logger.info(f"  Date: {date_str}")
    logger.info(f"  Mode: {'TEST' if test_mode else 'PRODUCTION'}")
    logger.info(f"{'#'*70}\n")

    # ──────────────────────────────────────────────
    # STEP 0: GROK TREND SCOUT — discover what we might miss
    # ──────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 0: Grok Trend Scout")
    logger.info("=" * 60)

    grok_clips = []
    try:
        from services.video_engine.editorial.trend_scout import scout_trends, search_discovery_clips
        trends = scout_trends(date_str)
        grok_clips = search_discovery_clips(trends.get("discoveries", []))
        logger.info(f"  Discoveries: {len(trends.get('discoveries', []))}")
        logger.info(f"  Searchable clips: {len(grok_clips)}")
        if trends.get("top_story"):
            logger.info(f"  Top story: {trends['top_story']}")
    except Exception as e:
        logger.info(f"  Trend scout skipped: {e}")

    # ──────────────────────────────────────────────
    # STEP 1: YouTube Scan
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: YouTube Scan + Transcription")
    logger.info("=" * 60)

    from services.video_engine.local_whisper import download_audio, transcribe_audio

    # Bitcoin YouTube channels to scan
    channels = [
        {"channel_id": "UCBBQgZTG5cG9OqOXx-mIIEg", "name": "Simply Bitcoin"},
        {"channel_id": "UCXWkNJOgLaq5WtPhan5JQag", "name": "Bitcoin Magazine"},
        {"channel_id": "UCgo7FCCPuylVk4luP3JAgVw", "name": "The Bitcoin Layer"},
        {"channel_id": "UCs-JCH6LiUlVPAmsj8z6F8w", "name": "SimplyBitcoinTV"},
        {"channel_id": "UCJgHxpqfhWEEjYH7cLVGnBA", "name": "Natalie Brunell"},
    ]

    if test_mode:
        channels = channels[:2]

    import subprocess
    transcripts = {}
    video_meta = []

    # Try channel-based scanning first
    for ch in channels:
        logger.info(f"\n  Scanning: {ch['name']}...")
        try:
            cmd = [
                "yt-dlp", "--flat-playlist", "--no-download",
                "--print", "%(id)s|||%(title)s|||%(duration)s",
                "--playlist-items", "1:3",
                f"https://www.youtube.com/channel/{ch['channel_id']}/videos"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            for line in result.stdout.strip().split("\n"):
                if not line or "|||" not in line:
                    continue
                parts = line.split("|||")
                if len(parts) < 2:
                    continue
                vid_id = parts[0]
                title = parts[1]
                dur = int(float(parts[2])) if len(parts) > 2 and parts[2] not in ("NA", "") else 0

                if dur < 120 or dur > 7200:
                    continue

                video_meta.append({
                    "video_id": vid_id,
                    "title": title,
                    "duration": dur,
                    "channel": ch["name"],
                })
                logger.info(f"    Found: {title[:60]} ({dur//60}m)")

        except Exception as e:
            logger.warning(f"    Scan failed: {e}")

    # Fallback: YouTube search if no channel results
    if not video_meta:
        logger.info("\n  Channel scan empty — using YouTube search fallback...")
        search_queries = [
            "ytsearch3:bitcoin news today",
            "ytsearch3:bitcoin market analysis",
        ]
        if test_mode:
            search_queries = search_queries[:1]

        for query in search_queries:
            try:
                cmd = [
                    "yt-dlp", "--flat-playlist", "--no-download",
                    "--print", "%(id)s|||%(title)s|||%(duration)s",
                    query
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                for line in result.stdout.strip().split("\n"):
                    if not line or "|||" not in line:
                        continue
                    parts = line.split("|||")
                    if len(parts) < 2:
                        continue
                    vid_id = parts[0]
                    title = parts[1]
                    dur = int(float(parts[2])) if len(parts) > 2 and parts[2] not in ("NA", "") else 0
                    if dur < 120 or dur > 7200:
                        continue
                    video_meta.append({
                        "video_id": vid_id,
                        "title": title,
                        "duration": dur,
                        "channel": "YouTube Search",
                    })
                    logger.info(f"    Search result: {title[:60]} ({dur//60}m)")
            except Exception as e:
                logger.warning(f"    Search failed: {e}")

    # ── STEP 1B: Mainstream Channel Scan (keyword-filtered) ──
    logger.info("\n  Scanning mainstream channels (keyword-filtered)...")
    try:
        import yaml
        channels_yaml = Path(__file__).resolve().parents[2] / "video_pipeline_v3" / "channels.yaml"
        if channels_yaml.exists():
            with open(channels_yaml) as f:
                ch_config = yaml.safe_load(f)
            mainstream_channels = ch_config.get("mainstream", [])
            if test_mode:
                mainstream_channels = mainstream_channels[:2]

            mainstream_found = []
            for mch in mainstream_channels:
                url = mch.get("url", "")
                keywords = mch.get("filter_keywords", [])
                name = mch.get("name", "Unknown")
                if not url:
                    continue
                logger.info(f"    Scanning mainstream: {name}...")
                try:
                    cmd = [
                        "yt-dlp", "--flat-playlist", "--no-download",
                        "--print", "%(id)s|||%(title)s|||%(duration)s",
                        "--playlist-items", "1:3",
                        f"{url}/videos"
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                    for line in result.stdout.strip().split("\n"):
                        if not line or "|||" not in line:
                            continue
                        parts = line.split("|||")
                        if len(parts) < 2:
                            continue
                        vid_id = parts[0]
                        title = parts[1]
                        dur = int(float(parts[2])) if len(parts) > 2 and parts[2] not in ("NA", "") else 0

                        if dur < 120 or dur > 7200:
                            continue

                        # Keyword filter: only include if title matches
                        title_lower = title.lower()
                        if any(kw.lower() in title_lower for kw in keywords):
                            video_meta.append({
                                "video_id": vid_id,
                                "title": title,
                                "duration": dur,
                                "channel": name,
                                "mainstream_match": True,
                            })
                            mainstream_found.append(title[:50])
                            logger.info(f"      MATCH: {title[:60]} ({dur//60}m)")

                except Exception as e:
                    logger.warning(f"      Scan failed: {e}")

            logger.info(f"  Mainstream matches: {len(mainstream_found)}")
    except ImportError:
        logger.info("  PyYAML not installed, skipping mainstream scan")
    except Exception as e:
        logger.info(f"  Mainstream scan skipped: {e}")

    # ── STEP 1C: Add Grok discovery clips ──
    for gc in grok_clips:
        # Avoid duplicates
        existing_ids = {vm["video_id"] for vm in video_meta}
        if gc["video_id"] not in existing_ids:
            video_meta.append(gc)

    logger.info(f"\n  Total videos found: {len(video_meta)} "
                f"(partner + mainstream + grok)")

    # Transcribe (first 5 minutes of each)
    max_vids = 3 if test_mode else 6
    for vm in video_meta[:max_vids]:
        vid_id = vm["video_id"]
        logger.info(f"\n  Transcribing: {vm['title'][:50]}...")
        try:
            audio_path = download_audio(vid_id, str(bundle / "audio"))
            if audio_path:
                transcript = transcribe_audio(audio_path, model_size="base")
                if transcript:
                    transcripts[vid_id] = transcript
                    transcripts[vid_id]["channel"] = vm["channel"]
                    transcripts[vid_id]["title"] = vm["title"]
                    dur_mins = len(transcript.get("text", "").split()) / 150
                    costs["whisper_minutes"] += dur_mins
                    logger.info(f"    Transcribed: {len(transcript.get('words', []))} words")
        except Exception as e:
            logger.warning(f"    Transcription failed: {e}")

    logger.info(f"\n  Transcripts: {len(transcripts)}")

    if not transcripts:
        logger.error("  No transcripts — cannot continue")
        return {"status": "failed", "error": "No transcripts"}

    # ──────────────────────────────────────────────
    # STEP 2: Nostr + Spaces (soft deps)
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Nostr + Spaces (soft dependencies)")
    logger.info("=" * 60)

    nostr_posts = []
    try:
        from services.video_engine.sources.nostr_capture import fetch_notable_nostr
        nostr_posts = fetch_notable_nostr(hours=48, max_posts=3)
        logger.info(f"  Nostr posts: {len(nostr_posts)}")
    except Exception as e:
        logger.info(f"  Nostr: {e}")

    spaces_data = []
    try:
        from services.video_engine.sources.spaces_listener import find_recent_spaces
        spaces_data = find_recent_spaces()
        logger.info(f"  Spaces found: {len(spaces_data)}")
    except Exception as e:
        logger.info(f"  Spaces: {e}")

    # ──────────────────────────────────────────────
    # STEP 3: Grok Triage
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Grok Triage")
    logger.info("=" * 60)

    from services.video_engine.editorial.grok_triage import GrokTriage

    triage = GrokTriage()
    if triage.configured:
        # Build source bundle in the format triage_all expects
        transcript_list = []
        for vid_id, t in transcripts.items():
            transcript_list.append({
                "source_id": vid_id,
                "source_name": t.get("channel", ""),
                "title": t.get("title", ""),
                "text": t.get("text", "")[:4000],
                "timestamped_text": t.get("timestamped_text", "")[:8000],
            })

        source_bundle = {
            "sources": {
                "youtube": {
                    "transcripts": transcript_list,
                },
                "tweets": {"tweets": []},
            }
        }

        triage_result = triage.triage_all(source_bundle, bundle)
        costs["grok_tokens_in"] = triage.tokens_in
        costs["grok_tokens_out"] = triage.tokens_out
        logger.info(f"  Candidates: {len(triage_result.candidates)}")
        logger.info(f"  Rejected: {len(triage_result.rejected)}")
    else:
        logger.warning("  Grok not configured — creating minimal triage")
        from services.video_engine.editorial.schemas import TriageOutput, CandidateMoment
        # Create basic candidates from transcripts
        candidates = []
        for vid_id, t in list(transcripts.items())[:3]:
            candidates.append(CandidateMoment(
                source_type="youtube",
                source_name=t.get("channel", "Unknown"),
                source_id=vid_id,
                approx_start="01:00",
                approx_end="03:00",
                topic=t.get("title", "Bitcoin News")[:50],
                why_interesting="Recent Bitcoin content",
                content_type="news",
                relevance_score=7,
            ))
        triage_result = TriageOutput(candidates=candidates)

    # ──────────────────────────────────────────────
    # STEP 4: Claude Director
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Claude Director")
    logger.info("=" * 60)

    from services.video_engine.editorial.claude_director import ClaudeDirector

    director = ClaudeDirector()
    if not director.configured:
        logger.error("  Claude not configured — cannot continue")
        return {"status": "failed", "error": "ANTHROPIC_API_KEY not set"}

    # Build source bundle for Claude
    cluster_bundle = {
        "transcripts": {
            vid_id: {
                "text": t.get("text", "")[:3000],
                "source_name": t.get("channel", ""),
                "title": t.get("title", ""),
            }
            for vid_id, t in transcripts.items()
        }
    }

    # Create a mock cluster output from triage
    from services.video_engine.editorial.schemas import ClusterOutput, StoryCluster
    clusters = ClusterOutput(clusters=[
        StoryCluster(
            cluster_id=f"cluster_{i}",
            topic=c.topic,
            hero_candidates=[str(i)],
            all_candidates=[str(i)],
            novelty_score=0.8,
            sources_represented=[c.source_name],
        )
        for i, c in enumerate(triage_result.candidates[:4])
    ])

    show_plan = director.create_show_plan(
        clusters, cluster_bundle, {}, bundle, date_str)

    costs["claude_tokens_in"] = director.tokens_in
    costs["claude_tokens_out"] = director.tokens_out

    if not show_plan:
        logger.error("  Claude Director failed")
        return {"status": "failed", "error": "No show plan"}

    logger.info(f"  Headline: {show_plan.episode_headline}")
    logger.info(f"  Stories: {len(show_plan.stories)}")
    logger.info(f"  Shorts: {len(show_plan.shorts_plan)}")

    # Save show plan
    plan_path = bundle / "manifest" / "show_plan.json"
    plan_path.write_text(json.dumps(show_plan.dict(), indent=2, default=str))

    # ──────────────────────────────────────────────
    # STEP 5: Clip Extraction
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 5: Clip Extraction")
    logger.info("=" * 60)

    from services.video_engine.editorial.clip_extractor import ClipExtractor

    extractor = ClipExtractor(
        transcripts,
        audio_dir=str(bundle / "audio"),
        clips_dir=str(bundle / "clips")
    )
    clip_map = extractor.extract_all_clips(show_plan.dict(), bundle)
    logger.info(f"  Clips extracted: {len(clip_map)}")

    # ──────────────────────────────────────────────
    # STEP 6: Narration
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 6: Narration (ElevenLabs)")
    logger.info("=" * 60)

    from services.video_engine.editorial.narration_generator import NarrationGenerator

    narrator = NarrationGenerator()
    if narrator.configured:
        audio_map = narrator.generate_all(show_plan.dict(), bundle / "voiceovers")
        costs["elevenlabs_characters"] = narrator.total_characters
        logger.info(f"  Voiceovers: {len(audio_map)}, chars: {narrator.total_characters}")
    else:
        logger.warning("  ElevenLabs not configured — no narration")
        audio_map = {}

    # ──────────────────────────────────────────────
    # STEP 7: Tweet + Nostr Screenshots
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 7: Screenshots")
    logger.info("=" * 60)

    tweet_images = {}

    # Nostr cards
    if nostr_posts:
        from services.video_engine.sources.nostr_capture import render_nostr_card
        for i, post in enumerate(nostr_posts[:3]):
            img_path = str(bundle / "work" / f"nostr_{i}.png")
            result = render_nostr_card(post, img_path)
            if result:
                tweet_images[f"nostr_{i}"] = result
                logger.info(f"  Nostr card: {post['author']}")

    # Tweet cards from show plan
    from services.video_engine.sources.tweet_screenshot import capture_tweet
    for story in show_plan.stories:
        sn = story.story_number
        for ti, tweet in enumerate(story.tweet_overlays):
            if tweet.tweet_text:
                img_path = str(bundle / "work" / f"tweet_s{sn}_t{ti}.png")
                capture_tweet({
                    "author_name": tweet.author_name,
                    "author_handle": tweet.author_handle,
                    "text": tweet.tweet_text,
                    "tweet_id": "",
                }, img_path)
                tweet_images[f"story{sn}_tweet{ti}"] = img_path
                logger.info(f"  Tweet card: {tweet.author_name}")

    logger.info(f"  Total screenshots: {len(tweet_images)}")

    # ──────────────────────────────────────────────
    # STEP 8: Full Assembly
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 8: Episode Assembly")
    logger.info("=" * 60)

    from services.video_engine.assembly.episode_builder import EpisodeBuilder

    builder = EpisodeBuilder(
        str(bundle), show_plan.dict(),
        audio_map, clip_map,
        tweet_images=tweet_images,
    )
    build_result = builder.build()

    # ──────────────────────────────────────────────
    # STEP 9: Shorts
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 9: Shorts")
    logger.info("=" * 60)

    shorts_results = []
    if show_plan.shorts_plan:
        from services.video_engine.assembly.shorts_builder import ShortsBuilder
        shorts_builder = ShortsBuilder(str(bundle / "work" / "shorts"))
        shorts_results = shorts_builder.build_all_shorts(
            show_plan.dict(), audio_map, clip_map,
            str(bundle / "shorts")
        )
        logger.info(f"  Shorts: {len(shorts_results)}")

    # ──────────────────────────────────────────────
    # STEP 10: Teaser
    # ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("STEP 10: Teaser")
    logger.info("=" * 60)

    teaser_path = None
    try:
        from services.video_engine.assembly.teaser_builder import build_teaser
        teaser_file = str(bundle / "final" / f"pulse_check_{date_str}_teaser.mp4")
        teaser_path = build_teaser(show_plan.dict(), clip_map, audio_map, teaser_file)
        if teaser_path:
            logger.info(f"  Teaser: {teaser_path}")
    except Exception as e:
        logger.warning(f"  Teaser failed: {e}")

    # ──────────────────────────────────────────────
    # STEP 11: Save Results
    # ──────────────────────────────────────────────
    elapsed = time.time() - start_time
    costs["total_runtime_seconds"] = round(elapsed, 1)

    # Estimate cost
    grok_cost = (costs["grok_tokens_in"] * 0.005 +
                 costs["grok_tokens_out"] * 0.015) / 1000
    claude_cost = (costs["claude_tokens_in"] * 0.003 +
                   costs["claude_tokens_out"] * 0.015) / 1000
    el_cost = costs["elevenlabs_characters"] * 0.00003
    costs["estimated_cost_usd"] = round(grok_cost + claude_cost + el_cost, 2)

    (bundle / "costs" / "run_costs.json").write_text(
        json.dumps(costs, indent=2, default=str))

    # Latest status
    from services.video_engine.assembly import ffmpeg_ops
    video_path = build_result.get("video_path", "")
    video_info = ffmpeg_ops.probe(video_path) if video_path and Path(video_path).exists() else {}

    status = {
        "date": date_str,
        "status": "complete" if build_result.get("video_path") else "failed",
        "duration_sec": round(video_info.get("duration", 0)),
        "clips": len(clip_map),
        "shorts": len(shorts_results),
        "voiceovers": len(audio_map),
        "cost_usd": costs["estimated_cost_usd"],
        "runtime_sec": round(elapsed),
        "headline": show_plan.episode_headline,
        "video_path": build_result.get("video_path", ""),
        "audio_path": build_result.get("audio_path", ""),
        "thumbnail_path": build_result.get("thumbnail_path", ""),
        "teaser_path": teaser_path,
    }

    status_path = Path("data/episodes/latest_status.json")
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2, default=str))

    # Summary
    logger.info(f"\n{'#'*70}")
    logger.info(f"  PIPELINE COMPLETE")
    logger.info(f"{'#'*70}")
    logger.info(f"  Date: {date_str}")
    logger.info(f"  Headline: {show_plan.episode_headline}")
    logger.info(f"  Duration: {video_info.get('duration', 0):.0f}s")
    logger.info(f"  Clips: {len(clip_map)}")
    logger.info(f"  Voiceovers: {len(audio_map)}")
    logger.info(f"  Shorts: {len(shorts_results)}")
    logger.info(f"  Cost: ~${costs['estimated_cost_usd']:.2f}")
    logger.info(f"  Runtime: {elapsed:.0f}s")
    logger.info(f"  Video: {build_result.get('video_path', 'NONE')}")
    logger.info(f"{'#'*70}\n")

    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Test mode (fewer sources)")
    args = parser.parse_args()

    result = run(test_mode=args.test)
    print(json.dumps(result, indent=2, default=str))
