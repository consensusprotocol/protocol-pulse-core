"""
Transcript service: YouTube captions, X Spaces (XSPACESTREAM), and future local 4090/490 pipeline.
Single interface for all transcription so avatar and post-Space tweet pipelines stay consistent.
"""
import logging
import os

from services.ai_service import AIService  # LLM for post-Space summaries

# Optional: youtube_transcript_api for partner YouTube videos
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _YTA_AVAILABLE = True
except ImportError:
    YouTubeTranscriptApi = None
    _YTA_AVAILABLE = False


def get_youtube_transcript(video_id: str, prefer_manual=True):
    """
    Fetch transcript for a YouTube video. Uses youtube_transcript_api when available.
    Returns list of dicts with 'text', 'start', 'duration' or None if unavailable.
    """
    if not _YTA_AVAILABLE:
        logging.warning("youtube_transcript_api not installed; transcript unavailable for %s", video_id)
        return None
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        # Optional: filter by manual captions if prefer_manual and list has metadata
        return transcript_list
    except Exception as e:
        logging.warning("YouTube transcript failed for %s: %s", video_id, e)
        return None


def get_youtube_transcript_plain(video_id: str) -> str:
    """Return full transcript as a single string, or empty string."""
    segments = get_youtube_transcript(video_id)
    if not segments:
        return ""
    return " ".join(s.get("text", "") for s in segments)


def get_space_transcript(space_id: str, provider: str = "xspacestream") -> dict:
    """
    Stub: fetch transcript for an ended X Space.
    When implemented: integrate XSPACESTREAM (or similar) or local 4090/490 pipeline.
    Returns dict with keys: transcript_text, segments (list of {speaker?, text, start}), speakers (list of {handle, name}).
    """
    logging.info("Transcript service: get_space_transcript stub called for space_id=%s provider=%s", space_id, provider)
    # TODO: XSPACESTREAM API or webhook; or local capture + Whisper on 4090/490
    return {
        "transcript_text": "",
        "segments": [],
        "speakers": [],
        "space_id": space_id,
        "provider": provider,
    }


def summarize_for_tweet(transcript_text: str, max_quotes: int = 2, max_chars: int = 250) -> dict:
    """
    Given full transcript text, return suggested tweet content with key quotes and speaker tags.
    Uses AIService (OpenAI / Anthropic / Grok / Gemini) under the hood.
    Returns dict with: tweet_text, quotes (list of {text, speaker_handle}), tags (list of @handles).
    """
    text = (transcript_text or "").strip()
    if not text:
        logging.warning("summarize_for_tweet called with empty transcript")
        return {"tweet_text": "", "quotes": [], "tags": []}

    logging.info("Transcript service: summarize_for_tweet called (len=%s)", len(text))

    ai = AIService()
    system_prompt = (
        "You are the Protocol Pulse social editor. "
        "You write post-Space recap tweets that are:\n"
        "- Grounded ONLY in the provided transcript (no hallucinations)\n"
        "- World-class, organic, and high-signal\n"
        "- Focused on Bitcoin, macro, and sovereignty\n"
        "- Respectful of the speakers' actual words and tone.\n\n"
        "Rules:\n"
        "- Do NOT invent facts, numbers, or quotes.\n"
        "- Prefer direct quotes from the Space with attribution.\n"
        "- No hashtags. No emojis. No clickbait.\n"
        "- One main tweet under 260 characters, plus up to "
        f"{max_quotes} short quoted lines with speaker handles.\n"
    )

    user_prompt = (
        "Transcript of a completed X Space follows. "
        "Write a concise recap tweet and extract the best direct quotes.\n\n"
        "Return STRICT JSON ONLY with this shape:\n"
        "{\n"
        '  \"tweet_text\": \"...\",\n'
        '  \"quotes\": [\n'
        '    {\"text\": \"...\", \"speaker_handle\": \"@handle\"}\n'
        "  ],\n"
        '  \"tags\": [\"@handle1\", \"@handle2\"]\n'
        "}\n\n"
        "Transcript:\n"
        f"{text[:8000]}\n"  # hard cap for safety
    )

    try:
        result = ai.generate_structured_content(
            prompt=user_prompt,
            system_prompt=system_prompt,
            provider="openai",
        )
        if not isinstance(result, dict):
            logging.warning("summarize_for_tweet: non-dict response, falling back")
            raise ValueError("Non-dict response")

        tweet_text = (result.get("tweet_text") or "").strip()
        if len(tweet_text) > max_chars:
            tweet_text = tweet_text[: max_chars - 3].rstrip() + "..."

        quotes = result.get("quotes") or []
        tags = result.get("tags") or []
        return {
            "tweet_text": tweet_text,
            "quotes": quotes[:max_quotes],
            "tags": tags,
        }
    except Exception as e:
        logging.error("summarize_for_tweet LLM error: %s", e)
        # Safe fallback: simple truncation
        fallback = text[: max_chars - 3].rstrip() + "..." if len(text) > max_chars else text
        return {
            "tweet_text": fallback,
            "quotes": [],
            "tags": [],
        }
