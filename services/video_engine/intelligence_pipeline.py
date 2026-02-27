"""
INTELLIGENCE PIPELINE v3
=========================
Monitor ALL -> Analyze ALL -> Select TOP -> Produce + Feed

This is the daily driver that:
1. Scans all enabled channels
2. Transcribes everything
3. Analyzes with Grok to find best moments
4. Selects top 5-7 for video
5. Produces horizontal + vertical content
6. Outputs intelligence feeds for other systems
"""

import os
import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests

from services.config_loader import get_enabled_channels, get_settings
from services.video_engine.ultron_client import ultron
from services.video_engine.pipeline_state import (
    create_run, update_run, complete_run, get_run,
    add_channel_scan, update_channel, save_highlight, mark_selected,
    get_incomplete_channels, get_completed_channels,
    ChannelStage, RunStage
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger("IntelligencePipeline")

# Output directories
INTEL_DIR = Path("data/video_engine/intel")
OUTPUT_DIR = Path("data/video_engine/output")
SHORTS_DIR = Path("data/video_engine/shorts")
VOICEOVER_DIR = Path("data/video_engine/voiceovers")

for d in [INTEL_DIR, OUTPUT_DIR, SHORTS_DIR, VOICEOVER_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class IntelligencePipeline:
    """The daily intelligence and video production pipeline."""

    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.date_display = datetime.now().strftime("%B %d, %Y")
        self.run_id = f"intel_{self.today}_{datetime.now().strftime('%H%M%S')}"
        self.settings = get_settings()
        self.channels = get_enabled_channels()

        # Will be populated during run
        self.all_highlights = []
        self.selected_highlights = []

    def get_latest_video(self, channel: Dict) -> Optional[Dict]:
        """Get latest video from a YouTube channel.
        Uses handle (e.g. @SimplyBitcoin) for yt-dlp lookup since many channel_ids
        are not resolvable by yt-dlp. Falls back to channel_id if handle fails.
        """
        handle = channel.get("handle", "")
        channel_id = channel.get("channel_id", "")

        # Prefer handle-based URL (more reliable with yt-dlp)
        urls_to_try = []
        if handle:
            urls_to_try.append(f"https://www.youtube.com/{handle}/videos")
        if channel_id:
            urls_to_try.append(f"https://www.youtube.com/channel/{channel_id}/videos")

        for url in urls_to_try:
            try:
                cmd = [
                    "yt-dlp", "--flat-playlist", "--playlist-items", "1",
                    "--print", '{"id": "%(id)s", "title": "%(title)s", "duration": %(duration)s, "upload_date": "%(upload_date)s"}',
                    url
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                # Filter out warning lines, get last valid JSON line
                lines = [l for l in result.stdout.strip().split('\n') if l.startswith('{')]
                if lines:
                    video = json.loads(lines[-1])
                    upload_date_str = video.get("upload_date", "")
                    if upload_date_str and upload_date_str != "NA":
                        try:
                            upload_date = datetime.strptime(upload_date_str, "%Y%m%d")
                            if datetime.now() - upload_date > timedelta(days=2):
                                logger.info(f"  [{channel['name']}] Latest video is >48h old, skipping")
                                return None
                        except ValueError:
                            pass  # upload_date format unexpected, proceed anyway
                    return video
            except subprocess.TimeoutExpired:
                logger.warning(f"  [{channel['name']}] Timeout fetching from {url}")
            except Exception as e:
                logger.warning(f"  [{channel['name']}] Error fetching from {url}: {e}")

        logger.error(f"  [{channel['name']}] All URL formats failed")
        return None

    def analyze_with_grok(self, transcript: str, channel: Dict, video_title: str) -> Optional[Dict]:
        """Use Grok to analyze transcript and find best moment."""
        grok_key = os.environ.get("XAI_API_KEY")
        if not grok_key:
            logger.error("No XAI_API_KEY")
            return None

        settings = self.settings

        prompt = f"""You are a Bitcoin content curator for "Pulse Check," a daily highlight show.

Analyze this transcript from {channel['name']} and identify the SINGLE BEST {settings['clip_duration_min']}-{settings['clip_duration_max']} second moment.

VIDEO TITLE: {video_title}
CHANNEL TAGS: {', '.join(channel.get('tags', []))}

CRITERIA (ranked by importance):
1. Bold prediction or controversial take that will stop scrolling
2. Surprising statistic, data point, or revelation
3. Emotionally charged, passionate delivery
4. Clean, quotable statement (no mid-sentence cuts)
5. Bitcoin-specific insight (not generic crypto/altcoin content)

RULES:
- Clip MUST be {settings['clip_duration_min']}-{settings['clip_duration_max']} seconds
- Start/end on sentence boundaries
- Moment must be self-contained (understandable without context)
- Avoid price speculation, focus on fundamentals/adoption/macro

Transcript (with timestamps):
{transcript[:12000]}

Respond with ONLY valid JSON:
{{
    "start_time": <float>,
    "end_time": <float>,
    "key_quote": "<most quotable line, max 150 chars>",
    "hook_score": <int 1-100, viral potential>,
    "narrator_intro": "<1 sentence to set up this clip for AI host>",
    "vertical_caption": "<punchy text for vertical overlay, max 60 chars>",
    "tweet_text": "<standalone tweet version of this insight, include channel credit, max 250 chars>",
    "themes": [<list of 1-3 theme tags like "macro", "adoption", "mining", "regulation", "technical">],
    "summary": "<2-3 sentence summary of the key insight for newsletter>"
}}"""

        try:
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {grok_key}", "Content-Type": "application/json"},
                json={"model": "grok-3", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
                timeout=90
            )

            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]

                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                result = json.loads(content.strip())

                duration = result.get("end_time", 0) - result.get("start_time", 0)
                if duration < settings['clip_duration_min']:
                    result["end_time"] = result["start_time"] + settings['clip_duration_min'] + 5
                elif duration > settings['clip_duration_max'] + 10:
                    result["end_time"] = result["start_time"] + settings['clip_duration_max']

                return result
            else:
                logger.error(f"Grok API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Grok analysis error: {e}")
        return None

    def phase1_scan_all(self) -> List[Dict]:
        """PHASE 1: Scan all enabled channels. Download audio and transcribe."""
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 1: SCANNING {len(self.channels)} CHANNELS")
        logger.info(f"{'='*60}\n")

        update_run(self.run_id, stage=RunStage.SCANNING)

        videos_to_process = []
        for channel in self.channels:
            add_channel_scan(self.run_id, channel["name"], channel["channel_id"])
            video = self.get_latest_video(channel)
            if video:
                videos_to_process.append({"channel": channel, "video": video})
                update_channel(self.run_id, channel["name"],
                               stage=ChannelStage.DOWNLOADING,
                               video_id=video["id"],
                               video_title=video.get("title", ""))
                logger.info(f"  + [{channel['name']}] {video.get('title', 'Unknown')[:50]}...")
            else:
                update_channel(self.run_id, channel["name"], stage=ChannelStage.SKIPPED)
                logger.info(f"  - [{channel['name']}] No recent video")

        if not videos_to_process:
            logger.warning("No videos to process!")
            return []

        logger.info(f"\n  Found {len(videos_to_process)} videos to process")

        # Batch download audio on Ultron
        video_ids = [v["video"]["id"] for v in videos_to_process]

        logger.info(f"\n  Batch downloading {len(video_ids)} audio files...")
        dl_job_id = ultron.batch_download_audio(video_ids)
        if dl_job_id:
            download_result = ultron.poll_job(dl_job_id, max_wait=600, interval=10)
            logger.info(f"  Audio download: {download_result.get('successes', 0)}/{len(video_ids)} succeeded")

        # Batch transcribe on Ultron
        logger.info(f"\n  Batch transcribing {len(video_ids)} videos...")
        tx_job_id = ultron.batch_transcribe(video_ids)
        if tx_job_id:
            transcribe_result = ultron.poll_job(tx_job_id, max_wait=1800, interval=15)
            logger.info(f"  Transcription: {transcribe_result.get('successes', 0)}/{len(video_ids)} succeeded")

        # Fetch all transcripts
        transcripts = ultron.get_transcripts(video_ids)

        for item in videos_to_process:
            vid = item["video"]["id"]
            if vid in transcripts:
                item["transcript"] = transcripts[vid]
                update_channel(self.run_id, item["channel"]["name"],
                               stage=ChannelStage.COMPLETE,
                               transcript_chars=len(transcripts[vid].get("text", "")))
            else:
                update_channel(self.run_id, item["channel"]["name"],
                               stage=ChannelStage.FAILED, error="No transcript returned")

        update_run(self.run_id, channels_scanned=len(videos_to_process))
        return videos_to_process

    def phase2_analyze_all(self, videos: List[Dict]) -> List[Dict]:
        """PHASE 2: Analyze all transcripts with Grok. Score every video."""
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 2: ANALYZING {len(videos)} TRANSCRIPTS")
        logger.info(f"{'='*60}\n")

        update_run(self.run_id, stage=RunStage.ANALYZING)
        all_highlights = []

        for item in videos:
            channel = item["channel"]
            video = item["video"]
            transcript = item.get("transcript", {})

            if not transcript.get("text"):
                logger.warning(f"  [{channel['name']}] No transcript, skipping")
                continue

            segments = transcript.get("segments", [])
            timestamped = "\n".join([f"[{s['start']:.1f}s] {s['text']}" for s in segments])

            logger.info(f"  Analyzing: {channel['name']}...")
            update_channel(self.run_id, channel["name"], stage=ChannelStage.ANALYZING)

            highlight = self.analyze_with_grok(timestamped, channel, video.get("title", ""))

            if highlight:
                highlight["channel_name"] = channel["name"]
                highlight["channel_handle"] = channel.get("handle", "")
                highlight["video_id"] = video["id"]
                highlight["video_title"] = video.get("title", "")
                highlight["channel_tags"] = channel.get("tags", [])

                all_highlights.append(highlight)
                save_highlight(self.run_id, highlight)
                update_channel(self.run_id, channel["name"],
                               stage=ChannelStage.COMPLETE,
                               hook_score=highlight.get("hook_score", 0))

                logger.info(f"    -> Score: {highlight.get('hook_score', 0)} | "
                            f"Quote: {highlight.get('key_quote', '')[:50]}...")
            else:
                update_channel(self.run_id, channel["name"],
                               stage=ChannelStage.FAILED, error="Grok analysis failed")
                logger.warning(f"    -> Analysis failed")

        self.all_highlights = all_highlights
        update_run(self.run_id, highlights_found=len(all_highlights))
        return all_highlights

    def phase3_select_top(self, highlights: List[Dict]) -> List[Dict]:
        """PHASE 3: Select top N highlights for video. Ensure diversity."""
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 3: SELECTING TOP CLIPS")
        logger.info(f"{'='*60}\n")

        update_run(self.run_id, stage=RunStage.SELECTING)
        settings = self.settings
        min_score = settings.get("min_hook_score", 60)
        top_n = settings.get("top_clips_for_video", 5)

        qualified = [h for h in highlights if h.get("hook_score", 0) >= min_score]
        logger.info(f"  {len(qualified)}/{len(highlights)} meet minimum score ({min_score})")

        qualified.sort(key=lambda x: x.get("hook_score", 0), reverse=True)

        # Diversity constraint: max 2 per channel
        selected = []
        channel_counts = {}
        for h in qualified:
            channel = h["channel_name"]
            if channel_counts.get(channel, 0) >= 2:
                continue
            selected.append(h)
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
            if len(selected) >= top_n:
                break

        logger.info(f"\n  Selected {len(selected)} clips for video:")
        for i, h in enumerate(selected):
            logger.info(f"    {i+1}. [{h['channel_name']}] Score: {h['hook_score']} -- {h['key_quote'][:40]}...")

        self.selected_highlights = selected
        mark_selected(self.run_id, [h["video_id"] for h in selected])
        update_run(self.run_id, clips_selected=len(selected))
        return selected

    def phase4_produce_video(self, selected: List[Dict]) -> Dict:
        """PHASE 4: Produce horizontal highlight reel + vertical shorts."""
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 4: PRODUCING VIDEO CONTENT")
        logger.info(f"{'='*60}\n")

        update_run(self.run_id, stage=RunStage.PRODUCING)

        # Download full videos for selected clips
        logger.info("  Downloading full videos for clips...")
        for h in selected:
            result = ultron.download_video(h["video_id"])
            if result and result.get("success"):
                logger.info(f"    + {h['channel_name']}")
            else:
                logger.warning(f"    - {h['channel_name']} download failed")

        # Extract clips
        logger.info("\n  Extracting clips...")
        for i, h in enumerate(selected):
            clip_name = f"pulse_{self.today}_{h['channel_name'].replace(' ', '_')}"
            result = ultron.extract_clip(
                h["video_id"], h["start_time"], h["end_time"], clip_name
            )
            if result and result.get("success"):
                h["clip_path"] = result.get("path", "")
                h["clip_filename"] = f"{clip_name}.mp4"
                logger.info(f"    + Clip {i+1}: {h['channel_name']}")
            else:
                logger.warning(f"    - Clip {i+1}: {h['channel_name']} failed")

        # Generate voiceovers
        logger.info("\n  Generating voiceovers...")
        from services.video_engine.assemble_pulse import generate_voiceover

        top_theme = self._get_top_theme(selected)
        intro_text = f"Welcome to your Pulse Check for {self.date_display}. {top_theme}"
        intro_path = generate_voiceover(intro_text, f"pulse_{self.today}_intro")
        if intro_path:
            ultron.upload_voiceover(str(intro_path), f"pulse_{self.today}_intro.mp3")

        for i, h in enumerate(selected):
            trans_text = h.get("narrator_intro", f"Here's {h['channel_name']}.")
            trans_path = generate_voiceover(trans_text, f"pulse_{self.today}_trans_{i}")
            if trans_path:
                ultron.upload_voiceover(str(trans_path), f"pulse_{self.today}_trans_{i}.mp3")
                h["voiceover_file"] = f"pulse_{self.today}_trans_{i}.mp3"

        outro_text = "That's your Pulse Check for today. Stay sovereign, stack sats."
        outro_path = generate_voiceover(outro_text, f"pulse_{self.today}_outro")
        if outro_path:
            ultron.upload_voiceover(str(outro_path), f"pulse_{self.today}_outro.mp3")

        # Assemble horizontal video
        logger.info("\n  Assembling horizontal highlight reel...")
        manifest = {
            "output_name": f"pulse_check_{self.today}.mp4",
            "intro_voiceover": f"pulse_{self.today}_intro.mp3",
            "outro_voiceover": f"pulse_{self.today}_outro.mp3",
            "segments": [
                {
                    "clip": h.get("clip_filename", ""),
                    "voiceover": h.get("voiceover_file", ""),
                    "channel_name": h["channel_name"],
                    "lower_third_text": h["channel_name"]
                }
                for h in selected if h.get("clip_filename")
            ]
        }

        assembly_job = ultron.assemble_advanced(manifest)
        if assembly_job:
            horizontal_result = ultron.poll_job(assembly_job, max_wait=600, interval=10)
            if horizontal_result and horizontal_result.get("status") == "complete":
                ultron.download_output(f"pulse_check_{self.today}.mp4", str(OUTPUT_DIR))
                logger.info(f"    + Horizontal reel complete")
                update_run(self.run_id, videos_produced=1)

        # Generate vertical shorts
        logger.info("\n  Generating vertical shorts...")
        shorts = []
        for i, h in enumerate(selected):
            if not h.get("clip_filename"):
                continue
            params = {
                "clip": h["clip_filename"],
                "output_name": f"short_{self.today}_{h['channel_name'].replace(' ', '_')}.mp4",
                "channel_name": h["channel_name"],
                "caption_text": h.get("vertical_caption", h.get("key_quote", "")[:60])
            }
            job_id = ultron.generate_vertical(params)
            if job_id:
                result = ultron.poll_job(job_id, max_wait=180, interval=5)
                if result and result.get("status") == "complete":
                    ultron.download_short(params["output_name"], str(SHORTS_DIR))
                    shorts.append(params["output_name"])
                    logger.info(f"    + Short {i+1}: {h['channel_name']}")

        update_run(self.run_id, shorts_produced=len(shorts))
        return {
            "horizontal": f"pulse_check_{self.today}.mp4",
            "shorts": shorts,
            "clips_used": len([h for h in selected if h.get("clip_filename")])
        }

    def phase5_output_intel(self) -> Dict:
        """PHASE 5: Output intelligence feeds for other systems."""
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 5: GENERATING INTELLIGENCE FEEDS")
        logger.info(f"{'='*60}\n")

        update_run(self.run_id, stage=RunStage.DISTRIBUTING)

        # Daily intel (for articles/newsletter)
        daily_intel = {
            "date": self.today,
            "channels_scanned": len(self.channels),
            "videos_analyzed": len(self.all_highlights),
            "clips_produced": len(self.selected_highlights),
            "highlights": [
                {
                    "channel": h["channel_name"],
                    "channel_handle": h.get("channel_handle", ""),
                    "video_title": h.get("video_title", ""),
                    "video_id": h.get("video_id", ""),
                    "key_quote": h.get("key_quote", ""),
                    "hook_score": h.get("hook_score", 0),
                    "themes": h.get("themes", []),
                    "summary": h.get("summary", ""),
                    "tweet_text": h.get("tweet_text", ""),
                    "used_in_video": h in self.selected_highlights
                }
                for h in self.all_highlights
            ],
            "themes_today": self._aggregate_themes(),
            "top_quote": self.selected_highlights[0].get("key_quote", "") if self.selected_highlights else ""
        }

        intel_path = INTEL_DIR / f"daily_intel_{self.today}.json"
        intel_path.write_text(json.dumps(daily_intel, indent=2))
        logger.info(f"  + daily_intel.json ({len(self.all_highlights)} highlights)")

        # Tweet queue
        tweets = []
        for h in self.all_highlights:
            if h.get("tweet_text"):
                tweets.append({
                    "text": h["tweet_text"],
                    "source_channel": h["channel_name"],
                    "hook_score": h.get("hook_score", 0),
                    "themes": h.get("themes", [])
                })

        tweet_path = INTEL_DIR / f"tweet_queue_{self.today}.json"
        tweet_path.write_text(json.dumps({"date": self.today, "tweets": tweets}, indent=2))
        logger.info(f"  + tweet_queue.json ({len(tweets)} tweets)")

        # Newsletter digest
        newsletter = {
            "date": self.today,
            "date_display": self.date_display,
            "themes": self._aggregate_themes(),
            "top_highlights": [
                {
                    "channel": h["channel_name"],
                    "quote": h.get("key_quote", ""),
                    "summary": h.get("summary", "")
                }
                for h in sorted(self.all_highlights, key=lambda x: x.get("hook_score", 0), reverse=True)[:7]
            ],
            "video_link": f"https://youtube.com/watch?v=PLACEHOLDER_{self.today}"
        }

        newsletter_path = INTEL_DIR / f"newsletter_digest_{self.today}.json"
        newsletter_path.write_text(json.dumps(newsletter, indent=2))
        logger.info(f"  + newsletter_digest.json")

        return {
            "daily_intel": str(intel_path),
            "tweet_queue": str(tweet_path),
            "newsletter_digest": str(newsletter_path)
        }

    def _get_top_theme(self, highlights: List[Dict]) -> str:
        """Generate a theme summary for the intro."""
        themes = self._aggregate_themes()
        if themes:
            return f"Today's focus: {', '.join(themes[:2])}."
        return "Here's what's making waves in Bitcoin."

    def _aggregate_themes(self) -> List[str]:
        """Aggregate and count themes across all highlights."""
        theme_counts = {}
        for h in self.all_highlights:
            for theme in h.get("themes", []):
                theme_counts[theme] = theme_counts.get(theme, 0) + 1

        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_themes[:5]]

    def run(self) -> Dict:
        """Execute the full intelligence pipeline."""
        logger.info(f"\n{'='*70}")
        logger.info(f"  PULSE CHECK INTELLIGENCE PIPELINE")
        logger.info(f"  Date: {self.today}")
        logger.info(f"  Run ID: {self.run_id}")
        logger.info(f"  Channels: {len(self.channels)}")
        logger.info(f"{'='*70}\n")

        create_run(self.run_id, self.today, len(self.channels))

        try:
            # Check Ultron
            health = ultron.health_check()
            if health.get("status") != "ok":
                logger.error(f"Ultron offline: {health}")
                complete_run(self.run_id, error="Ultron offline")
                return {"error": "Ultron offline"}
            logger.info(f"Ultron: {health.get('gpu_count', 0)} GPUs online")

            # Phase 1: Scan all channels
            videos = self.phase1_scan_all()
            if not videos:
                complete_run(self.run_id, error="No videos to process")
                return {"error": "No videos to process"}

            # Phase 2: Analyze all transcripts
            highlights = self.phase2_analyze_all(videos)
            if not highlights:
                complete_run(self.run_id, error="No highlights found")
                return {"error": "No highlights found"}

            # Phase 3: Select top clips
            selected = self.phase3_select_top(highlights)
            if not selected:
                complete_run(self.run_id, error="No clips met quality threshold")
                return {"error": "No clips met quality threshold"}

            # Phase 4: Produce video content
            video_result = self.phase4_produce_video(selected)

            # Phase 5: Output intelligence feeds
            intel_result = self.phase5_output_intel()

            complete_run(self.run_id)

            result = {
                "status": "complete",
                "run_id": self.run_id,
                "date": self.today,
                "channels_scanned": len(self.channels),
                "videos_analyzed": len(self.all_highlights),
                "clips_selected": len(self.selected_highlights),
                "video": video_result,
                "intel": intel_result
            }

            logger.info(f"\n{'='*70}")
            logger.info(f"  PIPELINE COMPLETE")
            logger.info(f"  Scanned: {len(self.channels)} channels")
            logger.info(f"  Analyzed: {len(self.all_highlights)} videos")
            logger.info(f"  Produced: {video_result.get('clips_used', 0)} clips")
            logger.info(f"  Shorts: {len(video_result.get('shorts', []))}")
            logger.info(f"{'='*70}\n")

            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            complete_run(self.run_id, error=str(e))
            return {"error": str(e)}


if __name__ == "__main__":
    pipeline = IntelligencePipeline()
    result = pipeline.run()
    print(json.dumps(result, indent=2))
