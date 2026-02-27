"""
Shorts Creator v2 - Vertical Video Generator
Creates 9:16 vertical clips (1-2 min each) from Pulse Check segments.

Each of the 5 partner channel clips becomes a standalone vertical short
with branding overlays. Vertical outro tag is appended when available.

Sends FFmpeg commands to Ultron for GPU-accelerated processing.
"""

import os
import json
import logging
import requests
from datetime import datetime
from services.video_engine.ultron_client import UltronClient

logger = logging.getLogger(__name__)

# ── Shorts Config ─────────────────────────────────────────────────
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920

# Branding
BRAND_TEXT = "PULSE CHECK"
BRAND_FONT_SIZE = 42
BRAND_COLOR = "white"
BRAND_BG_COLOR = "black@0.6"
HEADLINE_FONT_SIZE = 36
HEADLINE_COLOR = "white"
HEADLINE_BG_COLOR = "black@0.5"

# Vertical outro tag (set to None until created)
# Upload to Ultron: ~/video_engine/assets/tag_vertical.mp4
# Dimensions: 1080x1920, 2-3 seconds
VERTICAL_TAG_FILE = os.environ.get("VERTICAL_TAG_FILE", "assets/tag_vertical.mp4")
VERTICAL_TAG_ENABLED = os.environ.get("VERTICAL_TAG_ENABLED", "false").lower() == "true"


class ShortsCreator:
    """Creates vertical short-form clips from Pulse Check segments."""

    def __init__(self):
        self.ultron = UltronClient()

    def create_short_from_clip(
        self,
        clip_filename: str,
        headline: str,
        channel_name: str,
        date_str: str,
        output_filename: str = None,
    ) -> dict | None:
        """
        Convert a landscape clip (90-120s) to a branded vertical short.

        Process:
        1. Center-crop 16:9 to 9:16
        2. Add branded header with "PULSE CHECK"
        3. Add headline text overlay
        4. Add channel attribution at bottom
        5. Append vertical outro tag (when available)
        """
        if output_filename is None:
            safe_channel = channel_name.lower().replace(" ", "_")
            output_filename = f"short_{date_str}_{safe_channel}.mp4"

        headline_escaped = self._escape_ffmpeg_text(headline)
        channel_escaped = self._escape_ffmpeg_text(channel_name)

        filters = self._build_vertical_filter(
            headline=headline_escaped,
            channel_name=channel_escaped,
        )

        # Send to Ultron for processing
        try:
            result = self.ultron.process_ffmpeg(
                input_file=f"clips/{clip_filename}",
                output_file=f"shorts/{output_filename}",
                filters=filters,
                extra_args=[
                    "-c:v", "h264_nvenc",
                    "-preset", "p4",
                    "-b:v", "8M",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-ar", "44100",
                ],
            )

            if result and result.get("success"):
                # Append vertical tag if enabled
                if VERTICAL_TAG_ENABLED:
                    self._append_vertical_tag(output_filename)

                logger.info(f"✓ Short created: {output_filename}")
                return {
                    "success": True,
                    "filename": output_filename,
                    "size_mb": result.get("size_mb"),
                    "headline": headline,
                    "channel": channel_name,
                }
            else:
                return self._create_short_via_bash(
                    clip_filename, output_filename,
                    headline_escaped, channel_escaped,
                )

        except Exception as e:
            logger.error(f"Short creation error: {e}")
            return self._create_short_via_bash(
                clip_filename, output_filename,
                headline_escaped, channel_escaped,
            )

    def _append_vertical_tag(self, short_filename: str) -> bool:
        """Concatenate vertical tag.mp4 to end of short."""
        try:
            temp_name = f"temp_{short_filename}"
            # Create concat file
            concat_cmd = (
                f"echo \"file '/home/ultron/video_engine/shorts/{short_filename}'\" > /tmp/concat.txt && "
                f"echo \"file '/home/ultron/video_engine/{VERTICAL_TAG_FILE}'\" >> /tmp/concat.txt && "
                f"ffmpeg -y -f concat -safe 0 -i /tmp/concat.txt "
                f"-c:v h264_nvenc -preset p4 -b:v 8M -c:a aac "
                f"~/video_engine/shorts/{temp_name} && "
                f"mv ~/video_engine/shorts/{temp_name} ~/video_engine/shorts/{short_filename}"
            )
            result = self.ultron.run_command(concat_cmd)
            return result and result.get("returncode") == 0
        except Exception as e:
            logger.warning(f"Vertical tag append failed (non-fatal): {e}")
            return False

    def _build_vertical_filter(self, headline: str, channel_name: str) -> str:
        """Build FFmpeg filtergraph for vertical conversion with overlays."""
        filter_parts = [
            f"scale=-2:{SHORTS_HEIGHT}",
            f"crop={SHORTS_WIDTH}:{SHORTS_HEIGHT}",

            # Top branding bar
            f"drawbox=x=0:y=0:w={SHORTS_WIDTH}:h=90:color={BRAND_BG_COLOR}:t=fill",

            # "PULSE CHECK" title
            (
                f"drawtext=text='{BRAND_TEXT}'"
                f":fontsize={BRAND_FONT_SIZE}"
                f":fontcolor={BRAND_COLOR}"
                f":x=(w-text_w)/2"
                f":y=25"
                f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ),

            # Headline
            (
                f"drawtext=text='{headline}'"
                f":fontsize={HEADLINE_FONT_SIZE}"
                f":fontcolor={HEADLINE_COLOR}"
                f":x=(w-text_w)/2"
                f":y=130"
                f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                f":box=1:boxcolor={HEADLINE_BG_COLOR}:boxborderw=12"
            ),

            # Channel attribution
            (
                f"drawtext=text='{channel_name}'"
                f":fontsize=28"
                f":fontcolor=white@0.9"
                f":x=(w-text_w)/2"
                f":y=h-80"
                f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                f":box=1:boxcolor=black@0.5:boxborderw=8"
            ),
        ]

        return ",".join(filter_parts)

    def _create_short_via_bash(
        self,
        clip_filename: str,
        output_filename: str,
        headline: str,
        channel_name: str,
    ) -> dict | None:
        """Fallback: create short via bash command to Ultron."""
        try:
            filters = self._build_vertical_filter(headline, channel_name)

            cmd = (
                f"ffmpeg -y "
                f"-i ~/video_engine/clips/{clip_filename} "
                f'-vf "{filters}" '
                f"-c:v h264_nvenc -preset p4 -b:v 8M "
                f"-c:a aac -b:a 192k -ar 44100 "
                f"~/video_engine/shorts/{output_filename}"
            )

            result = self.ultron.run_command(cmd)

            if result and result.get("returncode") == 0:
                return {
                    "success": True,
                    "filename": output_filename,
                    "method": "bash_fallback",
                }
            return None

        except Exception as e:
            logger.error(f"Bash fallback failed: {e}")
            return None

    def create_all_shorts(self, pipeline_result: dict) -> list[dict]:
        """Create vertical shorts from all clips in a Pulse Check result."""
        date_str = pipeline_result.get("date", datetime.now().strftime("%Y-%m-%d"))
        clips = pipeline_result.get("clips", [])
        shorts = []

        self.ultron.run_command("mkdir -p ~/video_engine/shorts")

        for clip in clips:
            logger.info(f"Creating short: {clip['channel']} - {clip['headline']}")

            result = self.create_short_from_clip(
                clip_filename=clip["filename"],
                headline=clip["headline"],
                channel_name=clip["channel"],
                date_str=date_str,
            )

            if result:
                shorts.append(result)
                logger.info(f"  ✓ {result['filename']}")
            else:
                logger.warning(f"  ✗ Failed for {clip['channel']}")

        logger.info(f"Created {len(shorts)}/{len(clips)} shorts")
        return shorts

    def download_shorts(
        self, shorts: list[dict], local_dir: str = "data/video_engine/shorts/"
    ) -> list[str]:
        """Download created shorts from Ultron to local filesystem."""
        os.makedirs(local_dir, exist_ok=True)
        local_files = []

        for short in shorts:
            if not short.get("success"):
                continue

            filename = short["filename"]
            local_path = os.path.join(local_dir, filename)

            try:
                data = self.ultron.download_file(f"shorts/{filename}")
                if data:
                    with open(local_path, "wb") as f:
                        f.write(data)
                    local_files.append(local_path)
                    logger.info(f"  ✓ Downloaded: {local_path}")
            except Exception as e:
                logger.warning(f"  Download failed for {filename}: {e}")

        return local_files

    @staticmethod
    def _escape_ffmpeg_text(text: str) -> str:
        """Escape special characters for FFmpeg drawtext."""
        replacements = {
            "'": "\\'",
            ":": "\\:",
            "\\": "\\\\",
            "%": "%%",
            "\n": " ",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        if len(text) > 60:
            text = text[:57] + "..."

        return text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Shorts Creator v2")
    print("  Creates 1-2 min vertical shorts from each clip")
    print("  Vertical tag: set VERTICAL_TAG_ENABLED=true when ready")
