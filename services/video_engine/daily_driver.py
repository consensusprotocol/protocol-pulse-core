"""
DAILY DRIVER — Master Orchestrator
=====================================
The single entry point for the Pulse Check Content OS pipeline.
Runs the full editorial pipeline from source ingestion to distribution.

Usage:
    python -m services.video_engine.daily_driver --now       # Run immediately
    python -m services.video_engine.daily_driver --dry-run   # Show plan only, no assembly
    python -m services.video_engine.daily_driver --force     # Override one-run-per-day lock
    python -m services.video_engine.daily_driver --date 2026-02-25  # Build for specific date

Steps:
    1. Acquire run lock
    2. Create episode bundle
    3. Source ingestion (YouTube + Tweets + Market + Spaces)
    4. Grok triage (Stage 1)
    5. Clustering + novelty gate (Stage 1.5)
    6. Claude Director (Stage 2)
    7. QA Editor (Stage 3)
    8. Extract clips
    9. Generate narration
    10. Build assembly manifest
    11. Upload assets + assemble on Ultron
    12. Post-assembly validation
    13. Generate distribution pack
    14. Export audio-only podcast
    15. Update editorial memory
    16. Log costs
    17. Send alerts
    18. Release run lock
"""
import os
import sys
import json
import time
import fcntl
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

import pytz

logger = logging.getLogger("DailyDriver")

LOCK_FILE = Path("state/run.lock")
STATE_DIR = Path("state")
EPISODES_DIR = Path("data/episodes")


class DailyDriver:
    """Master orchestrator for the Pulse Check Content OS pipeline."""

    def __init__(self, date_str: str = None, dry_run: bool = False,
                 force: bool = False):
        tz = pytz.timezone(os.environ.get("PULSE_RUN_TZ", "America/New_York"))
        self.date_str = date_str or datetime.now(tz).strftime("%Y-%m-%d")
        self.dry_run = dry_run
        self.force = force
        self.start_time = time.time()
        self.bundle_path = None
        self.costs = {
            "episode_date": self.date_str,
            "grok_tokens_in": 0,
            "grok_tokens_out": 0,
            "claude_tokens_in": 0,
            "claude_tokens_out": 0,
            "elevenlabs_characters": 0,
            "whisper_minutes": 0,
            "total_runtime_seconds": 0,
            "estimated_cost_usd": 0
        }
        self.lock_fd = None

    def run(self) -> Dict:
        """Execute the full pipeline. Returns result summary."""
        logger.info(f"\n{'#'*70}")
        logger.info(f"  PULSE CHECK CONTENT OS — DAILY DRIVER")
        logger.info(f"  Date: {self.date_str}")
        logger.info(f"  Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info(f"{'#'*70}\n")

        result = {
            "date": self.date_str,
            "status": "running",
            "dry_run": self.dry_run,
            "stages": {}
        }

        try:
            # Step 1: Acquire lock
            if not self._acquire_lock():
                result["status"] = "locked"
                result["error"] = "Another run is in progress or already ran today"
                return result

            # Step 2: Create episode bundle
            from services.video_engine.editorial.episode_bundle import create_episode_bundle
            self.bundle_path = create_episode_bundle(self.date_str)

            # Setup episode-specific logging
            self._setup_episode_log()

            # Step 3: Source ingestion
            source_bundle, transcripts = self._stage_source_ingestion()
            result["stages"]["source_ingestion"] = {
                "transcripts": len(transcripts),
                "status": "complete" if transcripts else "empty"
            }

            if not transcripts:
                logger.warning("  No transcripts obtained — continuing with available data")

            # Step 4: Grok triage
            triage = self._stage_grok_triage(source_bundle)
            result["stages"]["grok_triage"] = {
                "candidates": len(triage.candidates) if triage else 0,
                "status": "complete" if triage else "failed"
            }

            if not triage or not triage.candidates:
                logger.warning("  No triage candidates — falling back to Quick Hits")

            # Step 5: Clustering
            clusters = self._stage_clustering(triage)
            result["stages"]["clustering"] = {
                "clusters": len(clusters.clusters) if clusters else 0,
                "status": "complete" if clusters else "skipped"
            }

            # Step 6: Claude Director
            show_plan = self._stage_claude_director(clusters, source_bundle)
            result["stages"]["claude_director"] = {
                "stories": len(show_plan.stories) if show_plan else 0,
                "headline": show_plan.episode_headline if show_plan else "none",
                "status": "complete" if show_plan else "failed"
            }

            if not show_plan:
                result["status"] = "failed"
                result["error"] = "Claude Director failed to produce show plan"
                self._send_alerts(result)
                return result

            # Step 7: QA Review
            qa_report = self._stage_qa_review(show_plan, triage)
            result["stages"]["qa_review"] = {
                "approved": qa_report.approved if qa_report else False,
                "issues": len(qa_report.issues) if qa_report else 0,
                "status": "complete"
            }

            # Dry run stops here
            if self.dry_run:
                logger.info("\n  DRY RUN complete — stopping before assembly")
                result["status"] = "dry_run_complete"
                self._log_costs()
                return result

            # Step 8: Extract clips
            clip_map = self._stage_clip_extraction(show_plan, transcripts)
            result["stages"]["clip_extraction"] = {
                "clips": len(clip_map),
                "status": "complete" if clip_map else "empty"
            }

            # Step 9: Generate narration
            audio_map = self._stage_narration(show_plan)
            result["stages"]["narration"] = {
                "voiceovers": len(audio_map),
                "status": "complete" if audio_map else "failed"
            }

            # Step 9.5: Avatar generation (optional)
            avatar_map = self._stage_avatar(audio_map)
            result["stages"]["avatar"] = {
                "segments": len(avatar_map),
                "status": "complete" if avatar_map else "skipped"
            }

            # Step 10: Build manifest
            manifest, shorts_manifests = self._stage_manifest(
                show_plan, audio_map, clip_map)
            result["stages"]["manifest"] = {
                "timeline_entries": len(manifest.timeline) if manifest else 0,
                "status": "complete" if manifest else "failed"
            }

            # Step 11: Ultron assembly
            assembly_result = self._stage_assembly(manifest, shorts_manifests)
            result["stages"]["assembly"] = assembly_result

            # Step 12: Post-assembly QA
            if assembly_result.get("horizontal", {}).get("status") == "complete":
                post_qa = self._stage_post_qa()
                result["stages"]["post_assembly_qa"] = post_qa

            # Step 13: Distribution pack
            dist = self._stage_distribution_pack(show_plan)
            result["stages"]["distribution_pack"] = {
                "platforms": len(dist) if dist else 0,
                "status": "complete" if dist else "failed"
            }

            # Step 14: Update editorial memory
            self._update_editorial_memory(show_plan)

            # Step 15: Log costs
            self._log_costs()
            result["costs"] = self.costs

            result["status"] = "complete"
            logger.info(f"\n{'#'*70}")
            logger.info(f"  PIPELINE COMPLETE — {self.date_str}")
            logger.info(f"  Runtime: {time.time() - self.start_time:.0f}s")
            logger.info(f"{'#'*70}\n")

        except Exception as e:
            logger.error(f"  Pipeline failed: {e}", exc_info=True)
            result["status"] = "error"
            result["error"] = str(e)

        finally:
            self._release_lock()
            self.costs["total_runtime_seconds"] = time.time() - self.start_time
            self._send_alerts(result)

        return result

    # ─── Stage Implementations ───

    def _stage_source_ingestion(self):
        """Stage 3: Ingest all sources."""
        logger.info(f"\n  STAGE: Source Ingestion")

        # Load config
        from services.config_loader import get_enabled_channels
        from services.video_engine.sources.youtube_scanner import YouTubeScanner
        from services.video_engine.sources.tweet_monitor import TweetMonitor
        from services.video_engine.sources.market_data import MarketDataProvider
        from services.video_engine.sources.spaces_monitor import fetch_recent_spaces
        from services.video_engine.sources.bundle_assembler import SourceBundleAssembler

        channels = get_enabled_channels()

        # YouTube
        scanner = YouTubeScanner(channels)
        videos = scanner.scan_all()
        transcripts = scanner.download_and_transcribe(videos, self.bundle_path)

        # Track whisper minutes
        total_duration = sum(
            v.get("duration_seconds", 0) for v in videos if v.get("video_id") in transcripts
        )
        self.costs["whisper_minutes"] = total_duration / 60

        # Tweets
        tweet_config = self._load_editorial_config()
        tweet_accounts = tweet_config.get("tweet_accounts", [])
        min_likes = tweet_config.get("tweet_min_likes", 1000)

        monitor = TweetMonitor(tweet_accounts, min_likes)
        tweets = monitor.fetch_notable_tweets(self.bundle_path)

        # Market data
        market = MarketDataProvider()
        market_data = market.fetch(self.bundle_path)

        # Spaces (skeleton)
        spaces = fetch_recent_spaces(bundle_path=self.bundle_path)

        # Assemble bundle
        assembler = SourceBundleAssembler(self.bundle_path, self.date_str)
        articles = assembler.load_existing_articles()
        source_bundle = assembler.assemble(
            transcripts, tweets, market_data, spaces, articles)

        return source_bundle, transcripts

    def _stage_grok_triage(self, source_bundle):
        """Stage 4: Grok triage."""
        logger.info(f"\n  STAGE: Grok Triage")

        from services.video_engine.editorial.grok_triage import GrokTriage

        triage = GrokTriage()
        if not triage.configured:
            logger.warning("  Grok not configured — skipping triage")
            from services.video_engine.editorial.schemas import TriageOutput
            return TriageOutput(candidates=[])

        result = triage.triage_all(source_bundle, self.bundle_path)
        self.costs["grok_tokens_in"] = triage.tokens_in
        self.costs["grok_tokens_out"] = triage.tokens_out

        return result

    def _stage_clustering(self, triage):
        """Stage 5: Clustering + novelty gate."""
        logger.info(f"\n  STAGE: Clustering")

        if not triage or not triage.candidates:
            from services.video_engine.editorial.schemas import ClusterOutput
            return ClusterOutput(clusters=[])

        from services.video_engine.editorial.clustering import StoryClustering

        memory = self._load_editorial_memory()
        clustering = StoryClustering(memory)
        return clustering.cluster(triage, self.bundle_path)

    def _stage_claude_director(self, clusters, source_bundle):
        """Stage 6: Claude Director."""
        logger.info(f"\n  STAGE: Claude Director")

        from services.video_engine.editorial.claude_director import ClaudeDirector

        director = ClaudeDirector()
        memory = self._load_editorial_memory()
        plan = director.create_show_plan(
            clusters, source_bundle, memory,
            self.bundle_path, self.date_str
        )

        self.costs["claude_tokens_in"] += director.tokens_in
        self.costs["claude_tokens_out"] += director.tokens_out

        return plan

    def _stage_qa_review(self, show_plan, triage):
        """Stage 7: QA Review."""
        logger.info(f"\n  STAGE: QA Review")

        from services.video_engine.editorial.qa_reviewer import QAReviewer

        reviewer = QAReviewer()
        return reviewer.review(show_plan, triage, self.bundle_path)

    def _stage_clip_extraction(self, show_plan, transcripts):
        """Stage 8: Clip extraction."""
        logger.info(f"\n  STAGE: Clip Extraction")

        from services.video_engine.editorial.clip_extractor import ClipExtractor

        extractor = ClipExtractor(transcripts)
        return extractor.extract_all_clips(show_plan.dict(), self.bundle_path)

    def _stage_narration(self, show_plan):
        """Stage 9: Narration generation."""
        logger.info(f"\n  STAGE: Narration Generation")

        from services.video_engine.editorial.narration_generator import NarrationGenerator

        generator = NarrationGenerator()
        if not generator.configured:
            logger.warning("  ElevenLabs not configured — skipping narration")
            return {}

        vo_dir = self.bundle_path / "voiceovers"
        audio_map = generator.generate_all(show_plan.dict(), vo_dir)
        self.costs["elevenlabs_characters"] = generator.total_characters

        return audio_map

    def _stage_manifest(self, show_plan, audio_map, clip_map):
        """Stage 10: Manifest building."""
        logger.info(f"\n  STAGE: Manifest Building")

        from services.video_engine.assembly.manifest_builder import (
            ManifestBuilder, build_shorts_manifests
        )

        builder = ManifestBuilder(show_plan.dict(), audio_map, clip_map)
        manifest = builder.build(self.bundle_path)
        shorts = build_shorts_manifests(show_plan.dict(), audio_map, clip_map)

        return manifest, shorts

    def _stage_assembly(self, manifest, shorts_manifests):
        """Stage 11: Ultron assembly."""
        logger.info(f"\n  STAGE: Ultron Assembly")

        from services.video_engine.assembly.ultron_assembler import UltronAssembler

        assembler = UltronAssembler()
        result = {"horizontal": {}, "shorts": []}

        # Horizontal
        h_result = assembler.assemble_horizontal(manifest, self.bundle_path)
        result["horizontal"] = h_result or {"status": "failed"}

        # Shorts
        if shorts_manifests:
            s_results = assembler.assemble_shorts(shorts_manifests, self.bundle_path)
            result["shorts"] = s_results

        # Audio-only export
        if h_result and h_result.get("status") == "complete":
            video_path = self.bundle_path / "final" / manifest.output_name
            if video_path.exists():
                audio_path = assembler.export_audio_only(
                    video_path, self.bundle_path / "final")
                result["podcast_audio"] = audio_path

        return result

    def _stage_post_qa(self):
        """Stage 12: Post-assembly validation."""
        logger.info(f"\n  STAGE: Post-Assembly QA")

        from services.video_engine.assembly.post_assembly_qa import PostAssemblyQA

        qa = PostAssemblyQA()
        # Find the assembled video
        final_dir = self.bundle_path / "final"
        videos = list(final_dir.glob("pulse_check_*.mp4"))
        if not videos:
            return {"passed": False, "error": "No assembled video found"}

        return qa.validate(videos[0], bundle_path=self.bundle_path)

    def _stage_distribution_pack(self, show_plan):
        """Stage 13: Distribution pack."""
        logger.info(f"\n  STAGE: Distribution Pack")

        from services.video_engine.assembly.distribution_pack import DistributionPackGenerator

        generator = DistributionPackGenerator(show_plan.dict(), self.date_str)
        return generator.generate_all(self.bundle_path)

    def _stage_avatar(self, audio_map):
        """Stage 9.5: Avatar generation (optional)."""
        if not os.environ.get("ENABLE_AVATAR", "").lower() == "true":
            logger.info(f"\n  STAGE: Avatar — disabled (set ENABLE_AVATAR=true)")
            return {}

        logger.info(f"\n  STAGE: Avatar Generation")

        try:
            from services.video_engine.editorial.avatar_generator import AvatarGenerator

            mode = os.environ.get("AVATAR_MODE", "intro_outro")
            generator = AvatarGenerator(mode=mode)

            if not generator.configured:
                logger.info("  MuseTalk not available — skipping")
                return {}

            return generator.generate_avatar_segments(audio_map, self.bundle_path)
        except Exception as e:
            logger.warning(f"  Avatar generation failed: {e}")
            return {}

    # ─── Helpers ───

    def _acquire_lock(self) -> bool:
        """Acquire file-based run lock."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        # Check if already ran today (unless --force)
        if not self.force:
            existing_bundle = EPISODES_DIR / self.date_str
            if existing_bundle.exists() and (existing_bundle / "costs" / "run_costs.json").exists():
                logger.warning(f"  Already ran today ({self.date_str}). Use --force to override.")
                return False

        try:
            self.lock_fd = open(LOCK_FILE, "w")
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(f"{os.getpid()}\n{self.date_str}\n{datetime.utcnow().isoformat()}")
            self.lock_fd.flush()
            logger.info("  Run lock acquired")
            return True
        except (IOError, OSError):
            logger.warning("  Could not acquire run lock — another run in progress?")
            return False

    def _release_lock(self):
        """Release run lock."""
        try:
            if self.lock_fd:
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
            LOCK_FILE.unlink(missing_ok=True)
            logger.info("  Run lock released")
        except Exception:
            pass

    def _setup_episode_log(self):
        """Setup file-based logging for this episode."""
        log_path = self.bundle_path / "logs" / "run.log"
        handler = logging.FileHandler(str(log_path))
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s'))
        logging.getLogger().addHandler(handler)

    def _load_editorial_config(self) -> dict:
        """Load editorial config."""
        config_path = Path("config/editorial_config.json")
        if config_path.exists():
            return json.loads(config_path.read_text())
        return {}

    def _load_editorial_memory(self) -> dict:
        """Load editorial memory."""
        memory_path = Path("state/editorial_memory.json")
        if memory_path.exists():
            try:
                return json.loads(memory_path.read_text())
            except Exception:
                pass
        return {}

    def _update_editorial_memory(self, show_plan):
        """Update rolling editorial memory after successful run."""
        memory = self._load_editorial_memory()

        # Add today's episode
        episode = {
            "date": self.date_str,
            "theme": show_plan.dominant_theme,
            "headline": show_plan.episode_headline,
            "story_count": len(show_plan.stories),
            "tone": show_plan.tone,
            "sources": list(set(
                c.source_name for s in show_plan.stories for c in s.clips
            ))
        }
        memory.setdefault("recent_episodes", []).insert(0, episode)
        memory["recent_episodes"] = memory["recent_episodes"][:14]

        # Update running stories
        for story in show_plan.stories:
            found = False
            for rs in memory.get("running_stories", []):
                if rs.get("topic", "").lower() == story.headline.lower():
                    rs["last_covered"] = self.date_str
                    rs["times_covered"] = rs.get("times_covered", 0) + 1
                    rs["angles_used"].append(story.story_mode)
                    found = True
                    break
            if not found:
                memory.setdefault("running_stories", []).append({
                    "topic": story.headline,
                    "first_covered": self.date_str,
                    "last_covered": self.date_str,
                    "angles_used": [story.story_mode],
                    "times_covered": 1,
                    "sources_used": [c.source_name for c in story.clips]
                })

        # Trim running stories to 14 days
        memory["running_stories"] = memory.get("running_stories", [])[:20]

        # Tomorrow's watchlist
        memory["tomorrows_watchlist"] = show_plan.tomorrows_watchlist

        # Overused sources
        source_counts = {}
        for ep in memory.get("recent_episodes", [])[:7]:
            for src in ep.get("sources", []):
                source_counts[src] = source_counts.get(src, 0) + 1
        memory["overused_sources"] = [
            s for s, c in source_counts.items() if c >= 5
        ]

        # Save
        memory_path = Path("state/editorial_memory.json")
        memory_path.write_text(json.dumps(memory, indent=2, default=str))
        logger.info(f"  Editorial memory updated")

    def _log_costs(self):
        """Save cost tracking data."""
        self.costs["total_runtime_seconds"] = time.time() - self.start_time

        # Estimate costs (rough)
        grok_cost = (self.costs["grok_tokens_in"] * 0.005 +
                     self.costs["grok_tokens_out"] * 0.015) / 1000
        claude_cost = (self.costs["claude_tokens_in"] * 0.003 +
                       self.costs["claude_tokens_out"] * 0.015) / 1000
        el_cost = self.costs["elevenlabs_characters"] * 0.00003  # ~$30/1M chars
        self.costs["estimated_cost_usd"] = round(grok_cost + claude_cost + el_cost, 2)

        if self.bundle_path:
            costs_path = self.bundle_path / "costs" / "run_costs.json"
            costs_path.write_text(json.dumps(self.costs, indent=2, default=str))
            logger.info(f"  Costs logged: ~${self.costs['estimated_cost_usd']:.2f}")

    def _send_alerts(self, result):
        """Send pipeline alerts."""
        try:
            from services.video_engine.pipeline_alerts import (
                send_pipeline_complete, send_pipeline_error
            )

            if result.get("status") == "complete":
                send_pipeline_complete(result, result)
            elif result.get("status") in ("error", "failed"):
                send_pipeline_error(
                    result.get("error", "Unknown"),
                    stage="daily_driver",
                    date=self.date_str
                )
        except Exception as e:
            logger.warning(f"  Alert sending failed: {e}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Pulse Check Content OS — Daily Driver")
    parser.add_argument("--now", action="store_true", help="Run immediately")
    parser.add_argument("--dry-run", action="store_true", help="Show plan only, no assembly")
    parser.add_argument("--force", action="store_true", help="Override one-run-per-day lock")
    parser.add_argument("--date", type=str, help="Build for specific date (YYYY-MM-DD)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )

    driver = DailyDriver(
        date_str=args.date,
        dry_run=args.dry_run,
        force=args.force
    )

    result = driver.run()

    # Print summary
    print(f"\n{'='*50}")
    print(f"Status: {result.get('status', 'unknown')}")
    if result.get("error"):
        print(f"Error: {result['error']}")
    if result.get("costs"):
        print(f"Cost: ~${result['costs'].get('estimated_cost_usd', 0):.2f}")
        print(f"Runtime: {result['costs'].get('total_runtime_seconds', 0):.0f}s")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
