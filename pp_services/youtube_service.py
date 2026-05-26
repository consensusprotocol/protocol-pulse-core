"""
YouTube Upload Service for Pulse Check
Uses YouTube Data API v3 with resumable uploads.

Setup Requirements:
1. Create OAuth2 credentials at console.cloud.google.com
2. Download client_secrets.json to project root
3. Run `python services/youtube_service.py --auth` to generate token
4. Set YOUTUBE_CLIENT_SECRETS_FILE and YOUTUBE_TOKEN_FILE env vars

First-time auth requires browser access (run from Mac, not Replit).
After that, the refresh token works headlessly.
"""

import os
import json
import logging
import time
import httplib2
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE = "youtube"
YOUTUBE_API_VERSION = "v3"

CLIENT_SECRETS_FILE = os.environ.get(
    "YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"
)
TOKEN_FILE = os.environ.get("YOUTUBE_TOKEN_FILE", "youtube_token.json")

# Retry config for resumable uploads
MAX_RETRIES = 5
RETRY_STATUSES = [500, 502, 503, 504]

# Default video settings
DEFAULT_CATEGORY = "28"  # Science & Technology
DEFAULT_PRIVACY = "public"
DEFAULT_LANGUAGE = "en"


class YouTubeService:
    """Handles YouTube video uploads via Data API v3."""

    def __init__(self):
        self._service = None
        self._credentials = None

    def _get_credentials(self):
        """Load or refresh OAuth2 credentials."""
        if self._credentials and not self._credentials.invalid:
            return self._credentials

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            # Try loading existing token
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, "r") as f:
                    token_data = json.load(f)

                self._credentials = Credentials(
                    token=token_data.get("token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    scopes=YOUTUBE_SCOPES,
                )

                # Refresh if expired
                if self._credentials.expired:
                    self._credentials.refresh(Request())
                    self._save_token()

                return self._credentials

            logger.error(
                f"No token file found at {TOKEN_FILE}. "
                f"Run: python services/youtube_service.py --auth"
            )
            return None

        except Exception as e:
            logger.error(f"Credential error: {e}")
            return None

    def _save_token(self):
        """Save credentials to token file."""
        if self._credentials:
            token_data = {
                "token": self._credentials.token,
                "refresh_token": self._credentials.refresh_token,
                "token_uri": self._credentials.token_uri,
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
            }
            with open(TOKEN_FILE, "w") as f:
                json.dump(token_data, f)

    def _get_service(self):
        """Build the YouTube API service."""
        if self._service:
            return self._service

        credentials = self._get_credentials()
        if not credentials:
            return None

        try:
            from googleapiclient.discovery import build

            self._service = build(
                YOUTUBE_API_SERVICE,
                YOUTUBE_API_VERSION,
                credentials=credentials,
            )
            return self._service
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")
            return None

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str] = None,
        category: str = DEFAULT_CATEGORY,
        privacy: str = DEFAULT_PRIVACY,
        thumbnail_path: str = None,
        made_for_kids: bool = False,
    ) -> dict | None:
        """
        Upload a video to YouTube with resumable upload.

        Args:
            file_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            tags: List of tags
            category: YouTube category ID
            privacy: public, private, or unlisted
            thumbnail_path: Optional custom thumbnail image
            made_for_kids: COPPA compliance flag

        Returns:
            dict with video_id, url, etc. or None on failure
        """
        service = self._get_service()
        if not service:
            logger.error("YouTube service not initialized")
            return None

        if not os.path.exists(file_path):
            logger.error(f"Video file not found: {file_path}")
            return None

        try:
            from googleapiclient.http import MediaFileUpload

            # Prepare metadata
            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "tags": tags or ["Bitcoin", "Crypto", "News", "PulseCheck"],
                    "categoryId": category,
                    "defaultLanguage": DEFAULT_LANGUAGE,
                    "defaultAudioLanguage": DEFAULT_LANGUAGE,
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": made_for_kids,
                },
            }

            # Create resumable upload
            media = MediaFileUpload(
                file_path,
                mimetype="video/mp4",
                resumable=True,
                chunksize=10 * 1024 * 1024,  # 10MB chunks
            )

            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            # Execute with retry
            response = None
            retry_count = 0

            logger.info(f"Uploading to YouTube: {title}")
            logger.info(f"  File: {file_path} ({os.path.getsize(file_path) / 1024 / 1024:.1f} MB)")

            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"  Upload progress: {progress}%")
                except Exception as e:
                    error_str = str(e)
                    if retry_count < MAX_RETRIES:
                        retry_count += 1
                        sleep_time = 2 ** retry_count
                        logger.warning(
                            f"  Upload error (retry {retry_count}/{MAX_RETRIES}): "
                            f"{error_str}, sleeping {sleep_time}s"
                        )
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"  Upload failed after {MAX_RETRIES} retries: {error_str}")
                        return None

            video_id = response["id"]
            video_url = f"https://youtu.be/{video_id}"
            logger.info(f"  ✓ Uploaded: {video_url}")

            # Set thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    thumb_media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                    service.thumbnails().set(
                        videoId=video_id,
                        media_body=thumb_media,
                    ).execute()
                    logger.info(f"  ✓ Thumbnail set")
                except Exception as e:
                    logger.warning(f"  Thumbnail upload failed (non-fatal): {e}")

            return {
                "success": True,
                "video_id": video_id,
                "url": video_url,
                "title": title,
            }

        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            return None

    def upload_pulse_check(self, pipeline_result: dict, video_path: str) -> dict | None:
        """
        Upload a Pulse Check video with auto-generated metadata.

        Args:
            pipeline_result: Result dict from run_pulse_check()
            video_path: Local path to the video file

        Returns:
            Upload result dict or None
        """
        date_str = pipeline_result.get("date", datetime.now().strftime("%Y-%m-%d"))
        clips = pipeline_result.get("clips", [])

        # Build title
        title = f"Pulse Check - Bitcoin News Highlights | {date_str}"

        # Build description
        desc_parts = [
            f"🔴 Pulse Check - Daily Bitcoin News Highlights for {date_str}",
            "",
            "Today's highlights:",
        ]

        for i, clip in enumerate(clips, 1):
            desc_parts.append(
                f"{i}. {clip['headline']} ({clip['channel']})"
            )

        desc_parts.extend([
            "",
            "Sources:",
        ])

        for clip in clips:
            desc_parts.append(f"• {clip['channel']} ({clip['handle']}): {clip.get('video_url', '')}")

        desc_parts.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "🎙️ Follow Protocol Pulse for daily Bitcoin intelligence",
            "🐦 Twitter: @ProtocolPulse",
            "📧 Newsletter: protocolpulse.io",
            "",
            "#Bitcoin #BTC #Crypto #News #PulseCheck",
        ])

        description = "\n".join(desc_parts)

        tags = [
            "Bitcoin", "BTC", "Crypto", "Cryptocurrency",
            "Bitcoin News", "Pulse Check", "Protocol Pulse",
            "Daily Bitcoin", "Bitcoin Today",
        ]

        # Add channel names as tags
        for clip in clips:
            tags.append(clip["channel"])

        return self.upload_video(
            file_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy="public",
        )


def run_auth_flow():
    """Interactive OAuth2 flow for first-time setup. Run from Mac/desktop."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"ERROR: {CLIENT_SECRETS_FILE} not found!")
        print("Download it from Google Cloud Console > APIs > Credentials")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=YOUTUBE_SCOPES
    )
    credentials = flow.run_local_server(port=8090)

    # Save token
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)

    print(f"✓ Token saved to {TOKEN_FILE}")
    print("You can now upload videos from Replit!")


if __name__ == "__main__":
    import sys

    if "--auth" in sys.argv:
        run_auth_flow()
    else:
        print("Usage:")
        print("  python services/youtube_service.py --auth   # First-time OAuth setup")
        print("")
        print("In code:")
        print("  from pp_services.youtube_service import YouTubeService")
        print("  yt = YouTubeService()")
        print("  yt.upload_pulse_check(result, '/path/to/video.mp4')")
