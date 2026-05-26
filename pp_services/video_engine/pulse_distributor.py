"""
PULSE DISTRIBUTOR
==================
Multi-platform distribution for Pulse Check videos and shorts.

Platforms:
  - Twitter/X: Horizontal video + thread with quotes
  - YouTube: Horizontal upload + Shorts
  - TikTok: Vertical shorts (via manual upload link)
  - Rumble: Horizontal upload
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from pp_services.video_engine.pipeline_state import (
    add_distribution, update_distribution
)

logger = logging.getLogger("PulseDistributor")

OUTPUT_DIR = Path("data/video_engine/output")
SHORTS_DIR = Path("data/video_engine/shorts")
INTEL_DIR = Path("data/video_engine/intel")


class PulseDistributor:
    """Distribute Pulse Check content across platforms."""

    def __init__(self, run_id: str, today: str):
        self.run_id = run_id
        self.today = today
        self.results = {}

    def distribute_all(self, video_result: Dict, intel_result: Dict) -> Dict:
        """Run all enabled distribution channels."""
        logger.info(f"\n{'='*60}")
        logger.info(f"DISTRIBUTION: Pulse Check {self.today}")
        logger.info(f"{'='*60}\n")

        horizontal = OUTPUT_DIR / video_result.get("horizontal", "")
        shorts = [SHORTS_DIR / s for s in video_result.get("shorts", [])]

        # Load daily intel for metadata
        intel_path = Path(intel_result.get("daily_intel", ""))
        daily_intel = {}
        if intel_path.exists():
            daily_intel = json.loads(intel_path.read_text())

        # Twitter/X
        if os.environ.get("ENABLE_TWEETS", "").lower() in ("true", "1"):
            self.results["twitter"] = self._distribute_twitter(
                horizontal, daily_intel)
        else:
            logger.info("  Twitter: disabled (ENABLE_TWEETS != true)")

        # YouTube Horizontal
        if os.environ.get("ENABLE_YT_PULSE", "").lower() in ("true", "1"):
            self.results["youtube_horizontal"] = self._distribute_youtube_horizontal(
                horizontal, daily_intel)
        else:
            logger.info("  YouTube Horizontal: disabled (ENABLE_YT_PULSE != true)")

        # YouTube Shorts
        if os.environ.get("ENABLE_YT_SHORTS", "").lower() in ("true", "1"):
            self.results["youtube_shorts"] = self._distribute_youtube_shorts(
                shorts, daily_intel)
        else:
            logger.info("  YouTube Shorts: disabled (ENABLE_YT_SHORTS != true)")

        # Summary
        logger.info(f"\n  Distribution complete:")
        for platform, result in self.results.items():
            status = "OK" if result.get("success") else "FAIL"
            logger.info(f"    {platform}: {status}")

        return self.results

    def _distribute_twitter(self, video_path: Path, daily_intel: Dict) -> Dict:
        """Post horizontal video to Twitter/X with quote thread."""
        logger.info("  Twitter: posting horizontal video...")
        dist_id = add_distribution(self.run_id, "twitter", "horizontal",
                                    video_path.name if video_path.exists() else None)

        try:
            import tweepy

            auth = tweepy.OAuth1UserHandler(
                os.environ["TWITTER_API_KEY"],
                os.environ["TWITTER_API_SECRET"],
                os.environ["TWITTER_ACCESS_TOKEN"],
                os.environ["TWITTER_ACCESS_TOKEN_SECRET"]
            )
            api = tweepy.API(auth)
            client = tweepy.Client(
                consumer_key=os.environ["TWITTER_API_KEY"],
                consumer_secret=os.environ["TWITTER_API_SECRET"],
                access_token=os.environ["TWITTER_ACCESS_TOKEN"],
                access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"]
            )

            # Upload video
            if video_path.exists():
                media = api.media_upload(
                    str(video_path),
                    media_category="tweet_video",
                    chunked=True
                )

                # Compose main tweet
                top_quote = daily_intel.get("top_quote", "")

                tweet_text = (
                    f"Pulse Check — {self.today}\n\n"
                    f'"{top_quote[:150]}"'
                )
                # Strip hashtags (Protocol Pulse never uses hashtags)
                import re
                tweet_text = re.sub(r'#\w+\s*', '', tweet_text).strip()

                # Global gate check
                try:
                    from pp_services.x_service import can_post_tweet
                    allowed, reason = can_post_tweet(tweet_text[:280], source="pulse_distributor")
                    if not allowed:
                        logger.warning("    Gate blocked: %s", reason)
                        update_distribution(dist_id, "failed", error=reason)
                        return {"success": False, "error": reason, "gate_blocked": True}
                except Exception as gate_err:
                    logger.warning("    Gate check failed (allowing): %s", gate_err)

                response = client.create_tweet(
                    text=tweet_text,
                    media_ids=[media.media_id]
                )

                tweet_url = f"https://x.com/i/status/{response.data['id']}"
                update_distribution(dist_id, "complete", url=tweet_url)
                logger.info(f"    + Tweet posted: {tweet_url}")

                # Post reply thread with highlights
                highlights = daily_intel.get("highlights", [])[:5]
                parent_id = response.data["id"]

                for h in highlights:
                    if h.get("tweet_text"):
                        reply = client.create_tweet(
                            text=h["tweet_text"][:280],
                            in_reply_to_tweet_id=parent_id
                        )
                        parent_id = reply.data["id"]

                return {"success": True, "url": tweet_url}
            else:
                update_distribution(dist_id, "failed", error="Video file not found")
                return {"success": False, "error": "Video file not found"}

        except Exception as e:
            logger.error(f"    Twitter distribution failed: {e}")
            update_distribution(dist_id, "failed", error=str(e))
            return {"success": False, "error": str(e)}

    def _distribute_youtube_horizontal(self, video_path: Path, daily_intel: Dict) -> Dict:
        """Upload horizontal highlight reel to YouTube."""
        logger.info("  YouTube: uploading horizontal video...")
        dist_id = add_distribution(self.run_id, "youtube", "horizontal",
                                    video_path.name if video_path.exists() else None)

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            creds = Credentials(
                token=None,
                refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
                client_id=os.environ["YOUTUBE_CLIENT_ID"],
                client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
                token_uri="https://oauth2.googleapis.com/token"
            )

            youtube = build("youtube", "v3", credentials=creds)

            # Build description
            highlights = daily_intel.get("highlights", [])
            desc_lines = [
                f"Pulse Check — {self.today}",
                "",
                "Today's top Bitcoin moments from across the network.",
                "",
                "Featured channels:"
            ]
            for h in highlights:
                if h.get("used_in_video"):
                    desc_lines.append(f"  {h['channel']} ({h.get('channel_handle', '')})")

            desc_lines.extend([
                "",
                "Timestamps:",
                "0:00 Intro"
            ])

            themes = daily_intel.get("themes_today", [])
            tags = ["Bitcoin", "Pulse Check", "BTC", "crypto news"] + themes[:5]

            body = {
                "snippet": {
                    "title": f"Pulse Check — {self.today} | Bitcoin Daily Highlights",
                    "description": "\n".join(desc_lines),
                    "tags": tags,
                    "categoryId": "25"  # News & Politics
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            }

            media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
            request_obj = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

            response = None
            while response is None:
                _, response = request_obj.next_chunk()

            video_id = response["id"]
            video_url = f"https://youtube.com/watch?v={video_id}"
            update_distribution(dist_id, "complete", url=video_url)
            logger.info(f"    + YouTube horizontal: {video_url}")

            return {"success": True, "url": video_url, "video_id": video_id}

        except Exception as e:
            logger.error(f"    YouTube horizontal failed: {e}")
            update_distribution(dist_id, "failed", error=str(e))
            return {"success": False, "error": str(e)}

    def _distribute_youtube_shorts(self, short_paths: List[Path], daily_intel: Dict) -> Dict:
        """Upload vertical shorts to YouTube Shorts."""
        logger.info(f"  YouTube Shorts: uploading {len(short_paths)} shorts...")
        results = []

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            creds = Credentials(
                token=None,
                refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
                client_id=os.environ["YOUTUBE_CLIENT_ID"],
                client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
                token_uri="https://oauth2.googleapis.com/token"
            )

            youtube = build("youtube", "v3", credentials=creds)

            highlights = daily_intel.get("highlights", [])
            highlight_map = {h.get("channel", ""): h for h in highlights}

            for short_path in short_paths:
                if not short_path.exists():
                    continue

                dist_id = add_distribution(self.run_id, "youtube_shorts", "short",
                                            short_path.name)

                # Extract channel name from filename
                parts = short_path.stem.split("_", 2)
                channel_guess = parts[2].replace("_", " ") if len(parts) > 2 else ""
                highlight = highlight_map.get(channel_guess, {})

                title = highlight.get("key_quote", f"Bitcoin Pulse Check — {self.today}")[:100]
                if not title.startswith('"'):
                    title = f'"{title}"'

                body = {
                    "snippet": {
                        "title": title + " #shorts #bitcoin",
                        "description": f"Pulse Check — {self.today}\n\n#Bitcoin #BTC #shorts",
                        "tags": ["Bitcoin", "BTC", "shorts", "crypto"],
                        "categoryId": "25"
                    },
                    "status": {
                        "privacyStatus": "public",
                        "selfDeclaredMadeForKids": False
                    }
                }

                media = MediaFileUpload(str(short_path), mimetype="video/mp4", resumable=True)
                req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

                response = None
                while response is None:
                    _, response = req.next_chunk()

                video_id = response["id"]
                url = f"https://youtube.com/shorts/{video_id}"
                update_distribution(dist_id, "complete", url=url)
                results.append({"success": True, "url": url, "filename": short_path.name})
                logger.info(f"    + Short uploaded: {url}")

        except Exception as e:
            logger.error(f"    YouTube Shorts failed: {e}")
            return {"success": False, "error": str(e), "uploaded": results}

        return {"success": True, "uploaded": results, "count": len(results)}


def distribute_pulse(run_id: str, today: str, video_result: Dict, intel_result: Dict) -> Dict:
    """Convenience function to distribute a completed pipeline run."""
    distributor = PulseDistributor(run_id, today)
    return distributor.distribute_all(video_result, intel_result)
