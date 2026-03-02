#!/usr/bin/env python3
"""Podcast feed — extract audio to MP3 + generate RSS XML."""
import os, subprocess, json
from datetime import datetime


def extract_podcast_audio(video_path: str, output_path: str) -> str:
    """Extract audio from video as high-quality MP3 podcast file.

    Args:
        video_path: Source video file
        output_path: Destination MP3 path

    Returns:
        Path to MP3 file, or "" on failure.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    r = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vn", "-c:a", "libmp3lame", "-q:a", "2",
         "-ar", "44100", "-ac", "1",
         "-metadata", "title=Pulse Check - Protocol Pulse",
         "-metadata", "artist=Protocol Pulse",
         "-metadata", "album=Pulse Check Daily",
         "-metadata", "genre=Podcast",
         output_path],
        capture_output=True, text=True, timeout=120,
    )

    if r.returncode == 0 and os.path.exists(output_path):
        # Get duration
        dur_r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", output_path],
            capture_output=True, text=True,
        )
        try:
            dur = float(dur_r.stdout.strip())
        except Exception:
            dur = 0
        sz = os.path.getsize(output_path)
        print(f"  [podcast] Extracted: {dur:.1f}s, {sz // 1024}KB → {output_path}")
        return output_path

    print(f"  [podcast] Audio extraction failed: {r.stderr[-200:]}")
    return ""


def generate_rss_item(episode_title: str, mp3_path: str,
                      description: str = "",
                      base_url: str = "https://protocolpulse.replit.app") -> str:
    """Generate an RSS XML item for a podcast episode.

    Returns:
        RSS item XML string.
    """
    now = datetime.utcnow()
    pub_date = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
    date_slug = now.strftime("%Y-%m-%d")

    # Get file size
    try:
        file_size = os.path.getsize(mp3_path)
    except Exception:
        file_size = 0

    # Get duration
    try:
        dur_r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", mp3_path],
            capture_output=True, text=True,
        )
        dur_secs = int(float(dur_r.stdout.strip()))
        duration_str = f"{dur_secs // 3600}:{(dur_secs % 3600) // 60:02d}:{dur_secs % 60:02d}"
    except Exception:
        duration_str = "0:02:00"

    mp3_filename = os.path.basename(mp3_path)
    enclosure_url = f"{base_url}/podcast/{date_slug}/{mp3_filename}"

    if not description:
        description = f"Pulse Check daily Bitcoin intelligence briefing for {date_slug}."

    return f"""  <item>
    <title>{_xml_escape(episode_title)}</title>
    <description>{_xml_escape(description)}</description>
    <pubDate>{pub_date}</pubDate>
    <enclosure url="{enclosure_url}" length="{file_size}" type="audio/mpeg"/>
    <itunes:duration>{duration_str}</itunes:duration>
    <itunes:episode>{date_slug.replace('-', '')}</itunes:episode>
    <guid isPermaLink="false">pulse-check-{date_slug}</guid>
  </item>"""


def generate_rss_feed(items: list, output_path: str) -> str:
    """Generate a complete RSS podcast feed XML file.

    Args:
        items: List of RSS item XML strings
        output_path: Where to write the feed

    Returns:
        Path to RSS file.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Pulse Check — Protocol Pulse</title>
    <link>https://protocolpulse.replit.app</link>
    <description>Daily Bitcoin intelligence briefing. Two hosts break down the most important stories in Bitcoin. Stay sovereign.</description>
    <language>en-us</language>
    <itunes:author>Protocol Pulse</itunes:author>
    <itunes:category text="Technology"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:image href="https://protocolpulse.replit.app/static/podcast_cover.png"/>
{"".join(items)}
  </channel>
</rss>"""

    with open(output_path, "w") as f:
        f.write(feed)

    print(f"  [podcast] RSS feed: {output_path}")
    return output_path


def _xml_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


if __name__ == "__main__":
    print("podcast_feed.py — use daily_producer.py for full pipeline")
