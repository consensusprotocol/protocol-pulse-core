"""
Intelligence Stream: posts intel tweet threads every 3 hours in Alex (Quant) or Sarah (Macro) voice.
Gets latest video from partner YouTube channels (Bitcoin Magazine, Natalie Brunell, Simply Bitcoin,
BTC Sessions, etc.), pulls transcript, feeds to GPT-4o to generate a human-sounding tweet thread
tagging the partner. Publishes to both X and Nostr.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Partner channels for intel stream (subset of supported_sources)
INTEL_STREAM_CHANNELS = [
    {"name": "Bitcoin Magazine", "channel_id": "UCwdB8sCl5w9fLOTxrpJoVtA"},
    {"name": "Natalie Brunell", "channel_id": "UCv-_bq3fB7y_wGmRqNGbCrw"},
    {"name": "Simply Bitcoin", "channel_id": "UCxu0RQ-f4R6FbLVzAjS-49Q"},
    {"name": "BTC Sessions", "channel_id": "UCQvhxHvJSQr-xPWKuqT2e7w"},
]


class IntelligenceStreamService:
    def __init__(self):
        self._ai = None
        self._youtube = None
        self._x = None
        self._nostr = None

    def _get_ai(self):
        if self._ai is None:
            from services.ai_service import AIService
            self._ai = AIService()
        return self._ai

    def _get_youtube(self):
        if self._youtube is None:
            from services.youtube_service import YouTubeService
            self._youtube = YouTubeService()
        return self._youtube

    def _get_x(self):
        if self._x is None:
            from services.x_service import XService
            self._x = XService()
        return self._x

    def get_latest_partner_video(self, channel_name=None, channel_id=None):
        """Return latest video info (video_id, title, channel_name) for one partner channel."""
        try:
            yt = self._get_youtube()
            # Use channel_id from INTEL_STREAM_CHANNELS or from supported_sources
            chan = channel_id or (channel_name and next(
                (c.get("channel_id") for c in INTEL_STREAM_CHANNELS if c.get("name") == channel_name), None
            ))
            if not chan:
                chan = INTEL_STREAM_CHANNELS[0].get("channel_id")
            # Fetch latest upload (implementation depends on youtube_service API)
            if hasattr(yt, "get_latest_video_for_channel"):
                out = yt.get_latest_video_for_channel(chan)
            else:
                import requests
                r = requests.get(
                    f"https://www.youtube.com/feeds/videos.xml?channel_id={chan}",
                    timeout=10,
                )
                if r.status_code != 200:
                    return None
                import xml.etree.ElementTree as ET
                root = ET.fromstring(r.text)
                ns = {"yt": "http://www.youtube.com/xml/schemas/2015"}
                entry = root.find(".//yt:entry", ns) or root.find(".//{http://www.w3.org/2005/Atom}entry")
                if entry is None:
                    entry = root.find("entry")
                if entry is None:
                    return None
                vid = entry.find("yt:videoId", ns)
                if vid is None:
                    vid = entry.get("videoId") or entry.find("videoId")
                video_id = vid.text if hasattr(vid, "text") else (vid or "")
                title_el = entry.find("title")
                title = title_el.text if title_el is not None else "Latest video"
                out = {"video_id": video_id, "title": title, "channel_name": channel_name or chan}
            return out
        except Exception as e:
            logger.warning("get_latest_partner_video failed: %s", e)
            return None

    def get_transcript_for_video(self, video_id):
        """Fetch transcript text for a YouTube video_id."""
        try:
            from services.transcript_service import get_youtube_transcript_plain
            return get_youtube_transcript_plain(video_id)
        except Exception as e:
            logger.warning("get_transcript_for_video failed: %s", e)
            return ""

    def generate_intel_thread(self, transcript_text, channel_name, voice="sarah"):
        """
        Generate a human-sounding tweet thread from transcript in Alex (Quant) or Sarah (Macro) voice.
        voice: 'alex' | 'sarah'. Returns list of tweet strings (thread order).
        """
        ai = self._get_ai()
        persona = (
            "Alex (Quant): data-driven, technical, block height and hashrate. Short punchy lines."
            if voice == "alex"
            else "Sarah (Macro): clinical, sovereignty-focused, macro and monetary policy. Lyn Alden meets cypherpunk."
        )
        prompt = f"""You are writing a tweet thread for Protocol Pulse intelligence stream.

PERSONA: {persona}

TRANSCRIPT EXCERPT (from {channel_name}):
{transcript_text[:8000]}

TASK: Write 3–5 tweet-length messages that summarize the key intel and tag the creator. No emojis, no hashtags. Each tweet max 280 chars. Number them 1/5, 2/5, etc. End the last tweet with a nod to @{channel_name.replace(' ', '')} or the channel name. Output only the tweets, one per line."""

        try:
            raw = ai.generate_content_openai(prompt)
        except Exception as e:
            logger.warning("generate_intel_thread OpenAI failed: %s", e)
            return []
        if not raw:
            return []
        lines = [line.strip() for line in raw.strip().split("\n") if line.strip() and len(line.strip()) <= 280]
        return lines[:5]

    def post_thread_to_x(self, thread_texts):
        """Post thread to X (reply chain). Returns first tweet id or None."""
        x = self._get_x()
        if not getattr(x, "client", None):
            logger.warning("X client not configured; skipping intel stream post")
            return None
        try:
            prev_id = None
            for i, text in enumerate(thread_texts):
                if prev_id:
                    status = x.client.update_status(status=text[:280], in_reply_to_status_id=prev_id)
                else:
                    status = x.client.update_status(status=text[:280])
                prev_id = status.id
            return prev_id
        except Exception as e:
            logger.warning("post_thread_to_x failed: %s", e)
            return None

    def post_thread_to_nostr(self, thread_texts):
        """Post thread to Nostr (e.g. via nostr_broadcaster). Returns event id or None."""
        try:
            from services.nostr_broadcaster import nostr_broadcaster
            full_text = "\n\n".join(thread_texts)
            return nostr_broadcaster.broadcast_note(full_text)
        except Exception as e:
            logger.debug("Nostr broadcast not available: %s", e)
            return None

    def run_intel_stream_cycle(self, voice=None):
        """
        One cycle: pick a partner channel, get latest video, transcript, generate thread, post to X + Nostr.
        voice: 'alex' | 'sarah' | None (alternate by hour: odd=sarah, even=alex).
        Returns dict with success, channel_name, video_id, thread_count, x_id, nostr_id.
        """
        voice = voice or ("sarah" if datetime.utcnow().hour % 2 == 1 else "alex")
        channel = INTEL_STREAM_CHANNELS[datetime.utcnow().hour % len(INTEL_STREAM_CHANNELS)]
        channel_name = channel.get("name", "Partner")
        video = self.get_latest_partner_video(channel_name=channel_name, channel_id=channel.get("channel_id"))
        if not video or not video.get("video_id"):
            return {"success": False, "error": "No latest video"}
        transcript = self.get_transcript_for_video(video["video_id"])
        if not transcript or len(transcript) < 200:
            return {"success": False, "error": "Transcript too short", "video_id": video["video_id"]}
        thread = self.generate_intel_thread(transcript, channel_name, voice=voice)
        if not thread:
            return {"success": False, "error": "Thread generation failed"}
        x_id = self.post_thread_to_x(thread)
        nostr_id = self.post_thread_to_nostr(thread)
        return {
            "success": True,
            "channel_name": channel_name,
            "video_id": video["video_id"],
            "thread_count": len(thread),
            "x_id": x_id,
            "nostr_id": nostr_id,
        }


# Singleton for cron/use
intelligence_stream_service = IntelligenceStreamService()
