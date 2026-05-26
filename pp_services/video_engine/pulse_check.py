"""
PULSE CHECK - Daily Video Briefing Engine
==========================================
Automated daily video that curates best moments from partner channels
with ElevenLabs narrator voiceover between segments.

DAILY FLOW:
1. Monitor partner channels for new videos
2. Download and transcribe new content
3. AI identifies best moments (highlight detection)
4. Extract clips from peak moments
5. Generate narrator script for transitions
6. ElevenLabs creates voiceover audio
7. Assemble medley video with clips + voiceover
8. Auto-publish to platforms

WEEKLY FLOW (separate):
- Curates best clips from the week
- Adds cinematic intro hook
- Higher production value
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseCheck")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PartnerChannel:
    """A YouTube channel we monitor for content."""
    name: str
    channel_id: str
    youtube_handle: str
    priority: int = 1  # 1 = high, 2 = medium, 3 = low
    enabled: bool = True


@dataclass
class VideoClip:
    """An extracted clip from a partner video."""
    source_video_id: str
    source_channel: str
    title: str
    start_time: float  # seconds
    end_time: float
    transcript: str
    hook_score: float  # 0-100, how compelling is this moment
    sentiment: str  # "bullish", "bearish", "educational", "breaking"
    local_path: Optional[str] = None
    

@dataclass
class NarratorSegment:
    """A voiceover segment for the narrator."""
    segment_type: str  # "intro", "transition", "context", "outro"
    script: str
    position: int  # order in the video
    audio_path: Optional[str] = None
    duration: Optional[float] = None


@dataclass
class PulseCheckVideo:
    """A complete daily Pulse Check video."""
    date: str
    clips: List[VideoClip]
    narrator_segments: List[NarratorSegment]
    total_duration: float
    render_path: Optional[str] = None
    status: str = "pending"  # pending, rendering, complete, published


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_PARTNER_CHANNELS = [
    PartnerChannel("Bitcoin Magazine", "UCni7PAlyNS0_12H-26DJJ3w", "@BitcoinMagazine", 1),
    PartnerChannel("Simply Bitcoin", "UCgYMrhLf9joZLfTx4WNUAUQ", "@SimplyBitcoin", 1),
    PartnerChannel("Swan Bitcoin", "UCsXs2jVSqEWp3tI3GQBV7Wg", "@SwanBitcoin", 1),
    PartnerChannel("What Bitcoin Did", "UCfl59StGFVCkJQgWmgYrKlA", "@WhatBitcoinDid", 2),
    PartnerChannel("The Bitcoin Layer", "UCNsBjT9qsHk7w1K-5ZEMmXA", "@TheBitcoinLayer", 2),
    PartnerChannel("Coin Bureau", "UCqK_GSMbpiV8spgD3ZGloSw", "@CoinBureau", 2),
    PartnerChannel("Anthony Pompliano", "UCCl3sIl__eyPsQ52sCWZVYw", "@AnthonyPompliano", 2),
]


class PulseCheckConfig:
    """Configuration for Pulse Check engine."""
    
    def __init__(self):
        self.config_path = Path("config/pulse_check.json")
        self.data_dir = Path("data/video_engine")
        self.clips_dir = self.data_dir / "clips"
        self.voiceover_dir = self.data_dir / "voiceovers"
        self.renders_dir = self.data_dir / "renders"
        self.output_dir = Path("static/video/daily")
        
        # Ensure directories exist
        for d in [self.clips_dir, self.voiceover_dir, self.renders_dir, self.output_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load or create config."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        
        # Default config
        config = {
            "partner_channels": [asdict(c) for c in DEFAULT_PARTNER_CHANNELS],
            "daily_clip_count": 5,  # How many clips per daily video
            "clip_min_duration": 30,  # Minimum clip length in seconds
            "clip_max_duration": 90,  # Maximum clip length
            "target_video_duration": 300,  # 5 minute target for daily
            "narrator_voice_id": "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs voice
            "narrator_style": "professional_journalist",
            "check_interval_hours": 4,
            "last_check": None
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        return config
    
    def save(self):
        """Save config."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def get_channels(self) -> List[PartnerChannel]:
        """Get list of partner channels."""
        return [PartnerChannel(**c) for c in self.config["partner_channels"]]


# ============================================================================
# CHANNEL MONITOR
# ============================================================================

class ChannelMonitor:
    """
    Monitors partner YouTube channels for new videos.
    """
    
    def __init__(self, config: PulseCheckConfig):
        self.config = config
        self.youtube_api_key = os.environ.get("YOUTUBE_API_KEY")
        self.processed_videos_file = self.config.data_dir / "processed_videos.json"
        self.processed_videos = self._load_processed()
    
    def _load_processed(self) -> set:
        """Load set of already processed video IDs."""
        if self.processed_videos_file.exists():
            with open(self.processed_videos_file) as f:
                return set(json.load(f))
        return set()
    
    def _save_processed(self):
        """Save processed video IDs."""
        with open(self.processed_videos_file, "w") as f:
            json.dump(list(self.processed_videos), f)
    
    def mark_processed(self, video_id: str):
        """Mark a video as processed."""
        self.processed_videos.add(video_id)
        self._save_processed()
    
    def get_recent_videos(self, channel: PartnerChannel, max_results: int = 5) -> List[Dict]:
        """
        Get recent videos from a channel.
        Uses YouTube API if available, falls back to yt-dlp.
        """
        videos = []
        
        if self.youtube_api_key:
            videos = self._get_videos_api(channel, max_results)
        
        if not videos:
            videos = self._get_videos_ytdlp(channel, max_results)
        
        # Filter out already processed
        new_videos = [v for v in videos if v["id"] not in self.processed_videos]
        
        logger.info(f"[{channel.name}] Found {len(new_videos)} new videos")
        return new_videos
    
    def _get_videos_api(self, channel: PartnerChannel, max_results: int) -> List[Dict]:
        """Get videos using YouTube Data API."""
        try:
            # First get upload playlist ID
            url = "https://www.googleapis.com/youtube/v3/channels"
            params = {
                "key": self.youtube_api_key,
                "id": channel.channel_id,
                "part": "contentDetails"
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if not data.get("items"):
                return []
            
            uploads_playlist = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get recent videos from uploads playlist
            url = "https://www.googleapis.com/youtube/v3/playlistItems"
            params = {
                "key": self.youtube_api_key,
                "playlistId": uploads_playlist,
                "part": "snippet",
                "maxResults": max_results
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            videos = []
            for item in data.get("items", []):
                snippet = item["snippet"]
                videos.append({
                    "id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "published_at": snippet["publishedAt"],
                    "channel_name": channel.name,
                    "channel_id": channel.channel_id,
                    "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url")
                })
            
            return videos
            
        except Exception as e:
            logger.warning(f"YouTube API error for {channel.name}: {e}")
            return []
    
    def _get_videos_ytdlp(self, channel: PartnerChannel, max_results: int) -> List[Dict]:
        """Get videos using yt-dlp (fallback)."""
        try:
            import yt_dlp
            
            ydl_opts = {
                "quiet": True,
                "extract_flat": True,
                "playlistend": max_results
            }
            
            url = f"https://www.youtube.com/{channel.youtube_handle}/videos"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=False)
                
                videos = []
                for entry in result.get("entries", [])[:max_results]:
                    videos.append({
                        "id": entry["id"],
                        "title": entry.get("title", "Unknown"),
                        "published_at": None,
                        "channel_name": channel.name,
                        "channel_id": channel.channel_id,
                        "thumbnail": entry.get("thumbnail")
                    })
                
                return videos
                
        except Exception as e:
            logger.warning(f"yt-dlp error for {channel.name}: {e}")
            return []
    
    def check_all_channels(self) -> List[Dict]:
        """Check all partner channels for new videos."""
        all_new_videos = []
        
        for channel in self.config.get_channels():
            if not channel.enabled:
                continue
            
            videos = self.get_recent_videos(channel)
            all_new_videos.extend(videos)
        
        # Sort by priority (channel priority) and recency
        all_new_videos.sort(key=lambda v: (
            next((c.priority for c in self.config.get_channels() 
                  if c.channel_id == v["channel_id"]), 99)
        ))
        
        return all_new_videos


# ============================================================================
# VIDEO PROCESSOR (Download + Transcribe)
# ============================================================================

class VideoProcessor:
    """
    Downloads videos and generates transcripts.
    """
    
    def __init__(self, config: PulseCheckConfig):
        self.config = config
        self.temp_dir = self.config.data_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def download_video(self, video_id: str) -> Optional[Path]:
        """Download a YouTube video."""
        try:
            import yt_dlp
            
            output_path = self.temp_dir / f"{video_id}.mp4"
            
            if output_path.exists():
                return output_path
            
            ydl_opts = {
                "format": "best[height<=720]",  # 720p max to save space/time
                "outtmpl": str(output_path),
                "quiet": True
            }
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if output_path.exists():
                logger.info(f"Downloaded: {video_id}")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"Download error for {video_id}: {e}")
            return None
    
    def download_audio_only(self, video_id: str) -> Optional[Path]:
        """Download just the audio (faster for transcription)."""
        try:
            import yt_dlp
            
            output_path = self.temp_dir / f"{video_id}.mp3"
            
            if output_path.exists():
                return output_path
            
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128"
                }],
                "outtmpl": str(self.temp_dir / f"{video_id}.%(ext)s"),
                "quiet": True
            }
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if output_path.exists():
                logger.info(f"Downloaded audio: {video_id}")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"Audio download error for {video_id}: {e}")
            return None
    
    def transcribe(self, audio_path: Path) -> Optional[Dict]:
        """
        Transcribe audio using OpenAI Whisper API.
        Returns transcript with timestamps.
        """
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("No OpenAI API key for transcription")
            return None
        
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            
            with open(audio_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            return {
                "text": transcript.text,
                "segments": [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text
                    }
                    for seg in transcript.segments
                ]
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None


# ============================================================================
# HIGHLIGHT DETECTOR
# ============================================================================

class HighlightDetector:
    """
    AI-powered detection of the best moments in a video.
    Uses transcript analysis to find compelling clips.
    """
    
    def __init__(self):
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.grok_key = os.environ.get("XAI_API_KEY")
    
    def detect_highlights(
        self,
        transcript: Dict,
        video_info: Dict,
        max_clips: int = 3
    ) -> List[Dict]:
        """
        Analyze transcript and identify the best moments.
        
        Returns list of highlight segments with:
        - start_time, end_time
        - hook_score (0-100)
        - reason (why this is compelling)
        - suggested_intro (narrator context)
        """
        if not transcript or not transcript.get("segments"):
            return []
        
        # Prepare transcript for analysis
        segments_text = "\n".join([
            f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}"
            for seg in transcript["segments"]
        ])
        
        prompt = f"""You are an expert video editor for a Bitcoin/crypto news channel called Protocol Pulse.

Analyze this transcript from "{video_info.get('title', 'Unknown')}" by {video_info.get('channel_name', 'Unknown')}.

Find the {max_clips} MOST COMPELLING moments that would make viewers stop scrolling. Look for:
- Surprising statistics or predictions
- Controversial takes or bold claims
- Emotional peaks (excitement, concern, revelation)
- Breaking news or insider information
- Clear explanations of complex topics
- Quotable soundbites

TRANSCRIPT:
{segments_text[:15000]}

Return a JSON array with exactly {max_clips} highlights:
[
  {{
    "start_time": 125.5,
    "end_time": 185.0,
    "hook_score": 87,
    "sentiment": "bullish",
    "key_quote": "The exact quote that makes this compelling",
    "reason": "Why this moment is compelling",
    "narrator_intro": "A 1-2 sentence intro the narrator would say before this clip"
  }}
]

Return ONLY valid JSON, no other text."""

        try:
            # Try Grok first (faster), fall back to OpenAI
            if self.grok_key:
                highlights = self._analyze_with_grok(prompt)
            elif self.openai_key:
                highlights = self._analyze_with_openai(prompt)
            else:
                logger.warning("No AI API key for highlight detection")
                return []
            
            return highlights
            
        except Exception as e:
            logger.error(f"Highlight detection error: {e}")
            return []
    
    def _analyze_with_grok(self, prompt: str) -> List[Dict]:
        """Use Grok for highlight analysis."""
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.grok_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-beta",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            timeout=60
        )
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return []
    
    def _analyze_with_openai(self, prompt: str) -> List[Dict]:
        """Use OpenAI for highlight analysis."""
        import openai
        client = openai.OpenAI(api_key=self.openai_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return []


# ============================================================================
# CLIP EXTRACTOR
# ============================================================================

class ClipExtractor:
    """
    Extracts video clips using ffmpeg.
    """
    
    def __init__(self, config: PulseCheckConfig):
        self.config = config
    
    def extract_clip(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        output_name: str
    ) -> Optional[Path]:
        """
        Extract a clip from a video.
        """
        output_path = self.config.clips_dir / f"{output_name}.mp4"
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", str(video_path),
                "-t", str(end_time - start_time),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                str(output_path)
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            if output_path.exists():
                logger.info(f"Extracted clip: {output_name}")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"Clip extraction error: {e}")
            return None


# ============================================================================
# NARRATOR ENGINE (ElevenLabs)
# ============================================================================

class NarratorEngine:
    """
    Generates voiceover narration using ElevenLabs.
    """
    
    def __init__(self, config: PulseCheckConfig):
        self.config = config
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.voice_id = config.config.get("narrator_voice_id", "21m00Tcm4TlvDq8ikWAM")
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def generate_intro_script(self, clips: List[Dict], date: str) -> str:
        """Generate the intro narration script."""
        channel_names = list(set(c.get("channel_name", "Bitcoin experts") for c in clips))
        channels_text = ", ".join(channel_names[:-1]) + f" and {channel_names[-1]}" if len(channel_names) > 1 else channel_names[0]
        
        return f"Welcome to today's Pulse Check for {date}. Here's what's making waves in Bitcoin. Today we're featuring insights from {channels_text}. Let's dive in."
    
    def generate_transition_script(self, prev_clip: Dict, next_clip: Dict) -> str:
        """Generate transition narration between clips."""
        next_channel = next_clip.get("channel_name", "our next guest")
        intro = next_clip.get("narrator_intro", "")
        
        if intro:
            return intro
        
        return f"And now, here's what {next_channel} had to say."
    
    def generate_outro_script(self) -> str:
        """Generate the outro narration."""
        return "That's your daily Pulse Check. Stay sovereign, stack sats, and we'll see you tomorrow."
    
    def synthesize_speech(self, script: str, output_name: str) -> Optional[Path]:
        """
        Generate audio from script using ElevenLabs.
        """
        if not self.api_key:
            logger.warning("ElevenLabs not configured")
            return None
        
        output_path = self.config.voiceover_dir / f"{output_name}.mp3"
        
        try:
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": script,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.6,
                        "similarity_boost": 0.8,
                        "style": 0.4,
                        "use_speaker_boost": True
                    }
                },
                timeout=60
            )
            
            if response.ok:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Generated voiceover: {output_name}")
                return output_path
            else:
                logger.error(f"ElevenLabs error: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Speech synthesis error: {e}")
            return None


# ============================================================================
# VIDEO ASSEMBLER
# ============================================================================

class VideoAssembler:
    """
    Assembles final video from clips and voiceover.
    Uses ffmpeg for local rendering or Ultron GPUs for heavy lifting.
    """
    
    def __init__(self, config: PulseCheckConfig):
        self.config = config
    
    def assemble_video(
        self,
        clips: List[Path],
        voiceovers: List[Path],
        output_name: str,
        use_ultron: bool = False
    ) -> Optional[Path]:
        """
        Assemble final video.
        
        For daily Pulse Check:
        - Intro voiceover
        - Clip 1
        - Transition voiceover
        - Clip 2
        - ...
        - Outro voiceover
        """
        output_path = self.config.output_dir / f"{output_name}.mp4"
        
        if use_ultron:
            return self._assemble_on_ultron(clips, voiceovers, output_path)
        else:
            return self._assemble_local(clips, voiceovers, output_path)
    
    def _assemble_local(
        self,
        clips: List[Path],
        voiceovers: List[Path],
        output_path: Path
    ) -> Optional[Path]:
        """
        Assemble video locally using ffmpeg concat.
        """
        try:
            # Create concat file
            concat_file = self.config.data_dir / "concat_list.txt"
            
            with open(concat_file, "w") as f:
                # Interleave voiceovers and clips
                for i, (vo, clip) in enumerate(zip(voiceovers, clips)):
                    if vo and vo.exists():
                        # Convert voiceover to video with black background
                        vo_video = self._voiceover_to_video(vo, f"vo_{i}")
                        if vo_video:
                            f.write(f"file '{vo_video}'\n")
                    
                    if clip and clip.exists():
                        f.write(f"file '{clip}'\n")
                
                # Add outro voiceover if exists
                if len(voiceovers) > len(clips):
                    outro_vo = voiceovers[-1]
                    if outro_vo and outro_vo.exists():
                        vo_video = self._voiceover_to_video(outro_vo, "vo_outro")
                        if vo_video:
                            f.write(f"file '{vo_video}'\n")
            
            # Concat all segments
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "medium",
                str(output_path)
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            if output_path.exists():
                logger.info(f"Assembled video: {output_path}")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"Video assembly error: {e}")
            return None
    
    def _voiceover_to_video(self, audio_path: Path, name: str) -> Optional[Path]:
        """
        Convert voiceover audio to video with Protocol Pulse branding.
        """
        output_path = self.config.data_dir / f"{name}_video.mp4"
        
        try:
            # Get audio duration
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", 
                        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                        str(audio_path)]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())
            
            # Create video with black background and audio
            # In production, you'd add Protocol Pulse logo/branding here
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s=1920x1080:d={duration}",
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                str(output_path)
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            return output_path if output_path.exists() else None
            
        except Exception as e:
            logger.error(f"Voiceover to video error: {e}")
            return None
    
    def _assemble_on_ultron(
        self,
        clips: List[Path],
        voiceovers: List[Path],
        output_path: Path
    ) -> Optional[Path]:
        """
        Assemble video on Ultron 4090 GPUs (for heavier processing).
        """
        # TODO: Implement SSH to Ultron for GPU-accelerated rendering
        logger.info("Ultron rendering not yet implemented, falling back to local")
        return self._assemble_local(clips, voiceovers, output_path)


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class PulseCheckEngine:
    """
    Main orchestrator for daily Pulse Check video generation.
    """
    
    def __init__(self):
        self.config = PulseCheckConfig()
        self.monitor = ChannelMonitor(self.config)
        self.processor = VideoProcessor(self.config)
        self.detector = HighlightDetector()
        self.extractor = ClipExtractor(self.config)
        self.narrator = NarratorEngine(self.config)
        self.assembler = VideoAssembler(self.config)
    
    def run_daily(self) -> Dict:
        """
        Run the full daily Pulse Check pipeline.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"=== PULSE CHECK DAILY RUN: {today} ===")
        
        result = {
            "date": today,
            "status": "started",
            "videos_checked": 0,
            "clips_extracted": 0,
            "final_video": None,
            "errors": []
        }
        
        try:
            # 1. Check for new videos
            logger.info("Step 1: Checking partner channels...")
            new_videos = self.monitor.check_all_channels()
            result["videos_checked"] = len(new_videos)
            
            if not new_videos:
                logger.info("No new videos to process")
                result["status"] = "no_new_content"
                return result
            
            # 2. Process videos and find highlights
            logger.info("Step 2: Processing videos and finding highlights...")
            all_highlights = []
            
            for video in new_videos[:5]:  # Process up to 5 videos
                video_id = video["id"]
                
                # Download audio
                audio_path = self.processor.download_audio_only(video_id)
                if not audio_path:
                    continue
                
                # Transcribe
                transcript = self.processor.transcribe(audio_path)
                if not transcript:
                    continue
                
                # Find highlights
                highlights = self.detector.detect_highlights(transcript, video)
                
                for h in highlights:
                    h["video_id"] = video_id
                    h["video_info"] = video
                    all_highlights.append(h)
                
                self.monitor.mark_processed(video_id)
            
            if not all_highlights:
                logger.warning("No highlights found in new videos")
                result["status"] = "no_highlights"
                return result
            
            # 3. Select top highlights for today's video
            logger.info("Step 3: Selecting top highlights...")
            daily_clip_count = self.config.config.get("daily_clip_count", 5)
            all_highlights.sort(key=lambda x: x.get("hook_score", 0), reverse=True)
            selected = all_highlights[:daily_clip_count]
            
            # 4. Download full videos and extract clips
            logger.info("Step 4: Extracting clips...")
            clips = []
            
            for i, highlight in enumerate(selected):
                video_id = highlight["video_id"]
                video_path = self.processor.download_video(video_id)
                
                if not video_path:
                    continue
                
                clip_path = self.extractor.extract_clip(
                    video_path,
                    highlight["start_time"],
                    highlight["end_time"],
                    f"pulse_{today}_{i}"
                )
                
                if clip_path:
                    clips.append({
                        "path": clip_path,
                        "highlight": highlight
                    })
            
            result["clips_extracted"] = len(clips)
            
            if not clips:
                logger.warning("No clips extracted")
                result["status"] = "no_clips"
                return result
            
            # 5. Generate narrator voiceovers
            logger.info("Step 5: Generating voiceovers...")
            voiceovers = []
            
            # Intro
            intro_script = self.narrator.generate_intro_script(
                [c["highlight"]["video_info"] for c in clips],
                datetime.now().strftime("%B %d, %Y")
            )
            intro_path = self.narrator.synthesize_speech(intro_script, f"pulse_{today}_intro")
            voiceovers.append(intro_path)
            
            # Transitions between clips
            for i in range(len(clips) - 1):
                trans_script = self.narrator.generate_transition_script(
                    clips[i]["highlight"],
                    clips[i + 1]["highlight"]
                )
                trans_path = self.narrator.synthesize_speech(trans_script, f"pulse_{today}_trans_{i}")
                voiceovers.append(trans_path)
            
            # Outro
            outro_script = self.narrator.generate_outro_script()
            outro_path = self.narrator.synthesize_speech(outro_script, f"pulse_{today}_outro")
            voiceovers.append(outro_path)
            
            # 6. Assemble final video
            logger.info("Step 6: Assembling final video...")
            clip_paths = [c["path"] for c in clips]
            
            final_video = self.assembler.assemble_video(
                clip_paths,
                voiceovers,
                f"pulse_check_{today}"
            )
            
            if final_video:
                result["final_video"] = str(final_video)
                result["status"] = "complete"
                logger.info(f"=== PULSE CHECK COMPLETE: {final_video} ===")
            else:
                result["status"] = "assembly_failed"
            
            return result
            
        except Exception as e:
            logger.error(f"Pulse Check error: {e}")
            result["status"] = "error"
            result["errors"].append(str(e))
            return result
    
    def get_status(self) -> Dict:
        """Get current engine status."""
        return {
            "configured": True,
            "elevenlabs": self.narrator.is_configured,
            "channels": len(self.config.get_channels()),
            "last_run": self.config.config.get("last_check"),
            "clips_dir": str(self.config.clips_dir),
            "output_dir": str(self.config.output_dir)
        }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    engine = PulseCheckEngine()
    
    if len(sys.argv) < 2:
        print("""
======================================================================
              PULSE CHECK - Daily Video Briefing Engine               
======================================================================

COMMANDS:
  status    - Show engine status
  run       - Run daily Pulse Check (full pipeline)
  channels  - List partner channels
  test      - Test individual components

WHAT IT DOES:
  1. Monitors partner YouTube channels for new videos
  2. AI detects the best/most compelling moments
  3. Extracts clips from those moments
  4. ElevenLabs narrator provides transitions
  5. Assembles into a daily briefing video

======================================================================
""")
        status = engine.get_status()
        print(f"Status:")
        print(f"  ElevenLabs: {'CONFIGURED' if status['elevenlabs'] else 'NOT SET'}")
        print(f"  Partner Channels: {status['channels']}")
        print(f"  Last Run: {status['last_run'] or 'Never'}")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        status = engine.get_status()
        print(json.dumps(status, indent=2))
    
    elif cmd == "run":
        result = engine.run_daily()
        print(json.dumps(result, indent=2, default=str))
    
    elif cmd == "channels":
        for ch in engine.config.get_channels():
            status = "ENABLED" if ch.enabled else "DISABLED"
            print(f"  [{ch.priority}] {ch.name} ({ch.youtube_handle}) - {status}")
    
    elif cmd == "test":
        print("Testing components...")
        
        # Test channel monitor
        print("\n1. Testing Channel Monitor...")
        videos = engine.monitor.check_all_channels()
        print(f"   Found {len(videos)} new videos")
        
        # Test narrator
        print("\n2. Testing Narrator...")
        if engine.narrator.is_configured:
            test_audio = engine.narrator.synthesize_speech(
                "This is a test of the Pulse Check narrator system.",
                "test_narrator"
            )
            print(f"   Generated: {test_audio}")
        else:
            print("   ElevenLabs not configured")
        
        print("\nTest complete!")
    
    else:
        print(f"Unknown command: {cmd}")
