from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from services import ollama_runtime

logger = logging.getLogger(__name__)


class PodcastGenerator:
    """Video/commentary assembler used by partner highlight reel pipeline (draft-only)."""

    def __init__(self) -> None:
        self.project_root = Path("/home/ultron/protocol_pulse")
        self.work_root = self.project_root / "logs" / "partner_reel_work"
        self.video_root = self.project_root / "static" / "video" / "highlights"
        self.video_root.mkdir(parents=True, exist_ok=True)
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.elevenlabs_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
        self.elevenlabs_voice = (os.environ.get("ELEVENLABS_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL").strip()

    def _run(self, cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def _has_bin(self, name: str) -> bool:
        return shutil.which(name) is not None

    def _safe_name(self, s: str) -> str:
        return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (s or ""))[:80]

    def _segment_summary(self, segment: Dict) -> str:
        return (
            f"{segment.get('channel', 'partner')} on {segment.get('topic', 'macro')} "
            f"({segment.get('role', 'deep_dive')})"
        )

    def _topic_to_voice_hint(self, mood: str = "professional") -> str:
        return "professional_male" if mood == "professional" else "professional_female"

    def _draft_commentary_text(self, segment: Dict, pre: bool = True) -> str:
        channel = segment.get("channel", "partner channel")
        topic = segment.get("topic", "bitcoin")
        role = segment.get("role", "deep_dive")
        if pre:
            prompt = (
                "write a short pre-clip intro under 45 words.\n"
                "tone: chill, world-class, tactical, lowercase.\n"
                f"upcoming clip from {channel}. topic={topic}, role={role}. "
                "tell listeners what to watch and why it matters for transactors."
            )
        else:
            prompt = (
                "write a short post-clip reaction under 45 words.\n"
                "tone: chill, world-class, tactical, lowercase.\n"
                f"clip source={channel}, topic={topic}, role={role}. "
                "add one sovereign insight and close cleanly."
            )
        text = ollama_runtime.generate(
            prompt=prompt,
            preferred_model="llama3.1",
            options={"temperature": 0.45, "num_predict": 110},
            timeout=8,
        )
        if text:
            return " ".join(text.split())[:260]
        if pre:
            return f"up next: {channel} breaks down {topic}. listen for the signal and what it changes for active transactors."
        return f"solid clip from {channel}. key takeaway: {topic} is a sovereignty lever when timing, custody, and conviction align."

    def _synthesize_audio(self, text: str, out_path: Path) -> str:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if self.elevenlabs_key:
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice}"
                payload = {
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
                }
                resp = requests.post(
                    url,
                    headers={"xi-api-key": self.elevenlabs_key, "Content-Type": "application/json"},
                    json=payload,
                    timeout=45,
                )
                if resp.ok and resp.content:
                    out_path.write_bytes(resp.content)
                    return str(out_path)
            except Exception:
                logger.exception("elevenlabs synthesis failed")

        # Fallback: silence block so pipeline can still render.
        duration = max(4, min(16, len(text.split()) // 2))
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(duration), "-c:a", "aac", str(out_path),
        ]
        self._run(cmd, timeout=60)
        return str(out_path)

    def generate_commentary_for_segment(self, segment: Dict, mood: str = "chill") -> Dict:
        """
        Given a segment (channel/topic/role), generate pre and post commentary audio blocks.
        """
        day = date.today().isoformat()
        base = self.work_root / day / f"{self._safe_name(segment.get('video_id', 'vid'))}_{int(float(segment.get('start',0)))}"
        pre_txt = self._draft_commentary_text(segment, pre=True)
        post_txt = self._draft_commentary_text(segment, pre=False)
        _ = self._topic_to_voice_hint("professional" if mood == "chill" else mood)
        pre_audio = self._synthesize_audio(pre_txt, base.with_name(base.name + "_pre.m4a"))
        post_audio = self._synthesize_audio(post_txt, base.with_name(base.name + "_post.m4a"))
        return {
            "pre_commentary_audio": pre_audio,
            "post_commentary_audio": post_audio,
            "pre_text": pre_txt,
            "post_text": post_txt,
        }

    def download_source_video(self, video_id: str) -> str:
        """
        Download YouTube source clip to local cache using yt-dlp/youtube-dl.
        """
        day = date.today().isoformat()
        cache_dir = self.work_root / day / "sources"
        cache_dir.mkdir(parents=True, exist_ok=True)
        target = cache_dir / f"{video_id}.mp4"
        if target.exists() and target.stat().st_size > 0:
            return str(target)

        if str(video_id).startswith("fallback_"):
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=700:sample_rate=44100",
                "-t", "120",
                "-c:v", "libx264", "-c:a", "aac",
                str(target),
            ]
            self._run(cmd, timeout=120)
            return str(target)

        url = f"https://www.youtube.com/watch?v={video_id}"
        if self._has_bin("yt-dlp"):
            cmd = ["yt-dlp", "-f", "mp4", "-o", str(target), url]
            proc = self._run(cmd, timeout=240)
            if proc.returncode == 0 and target.exists():
                return str(target)
        elif self._has_bin("youtube-dl"):
            cmd = ["youtube-dl", "-f", "mp4", "-o", str(target), url]
            proc = self._run(cmd, timeout=240)
            if proc.returncode == 0 and target.exists():
                return str(target)

        # Offline fallback placeholder.
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100",
            "-t", "120",
            "-c:v", "libx264", "-c:a", "aac",
            str(target),
        ]
        self._run(cmd, timeout=180)
        return str(target)

    def extract_video_clip(self, source_video: str, start: float, end: float) -> str:
        day = date.today().isoformat()
        clips_dir = self.work_root / day / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        out = clips_dir / f"clip_{int(start)}_{int(end)}_{self._safe_name(Path(source_video).stem)}.mp4"
        duration = max(1.0, float(end) - float(start))
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(max(0.0, float(start))),
            "-i", str(source_video),
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac",
            str(out),
        ]
        self._run(cmd, timeout=180)
        return str(out)

    def make_transition_slide(self, title: str, channel: str, topic: str) -> str:
        day = date.today().isoformat()
        trans_dir = self.work_root / day / "transitions"
        trans_dir.mkdir(parents=True, exist_ok=True)
        out = trans_dir / f"transition_{self._safe_name(channel)}_{self._safe_name(topic)}.mp4"
        base_png = self.project_root / "static" / "video" / "transition-base.png"
        if not base_png.exists():
            base_png.parent.mkdir(parents=True, exist_ok=True)
            cmd_png = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=1",
                "-frames:v", "1", str(base_png),
            ]
            self._run(cmd_png, timeout=30)
        text = f"{channel} • {topic}"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(base_png),
            "-vf",
            (
                "drawtext=fontcolor=white:fontsize=46:x=(w-text_w)/2:y=(h-text_h)/2:"
                f"text='{text}',"
                "drawtext=fontcolor=white:fontsize=30:x=(w-text_w)/2:y=(h/2)+60:"
                f"text='{self._safe_name(title)[:42]}'"
            ),
            "-t", "4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(out),
        ]
        self._run(cmd, timeout=60)
        return str(out)

    def _audio_to_block_video(self, audio_path: str, label: str, channel: str, topic: str) -> str:
        day = date.today().isoformat()
        blocks = self.work_root / day / "commentary_blocks"
        blocks.mkdir(parents=True, exist_ok=True)
        out = blocks / f"{self._safe_name(channel)}_{self._safe_name(topic)}_{label}.mp4"
        bg = self.project_root / "static" / "video" / "commentary-bg.png"
        if not bg.exists():
            bg.parent.mkdir(parents=True, exist_ok=True)
            self._run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#0a0a0a:s=1280x720:d=1", "-frames:v", "1", str(bg)],
                timeout=30,
            )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(bg),
            "-i", str(audio_path),
            "-vf",
            (
                "drawtext=fontcolor=white:fontsize=44:x=(w-text_w)/2:y=(h/2)-20:"
                f"text='protocol pulse {label}',"
                "drawtext=fontcolor=white:fontsize=30:x=(w-text_w)/2:y=(h/2)+40:"
                f"text='{self._safe_name(channel)} | {self._safe_name(topic)}'"
            ),
            "-shortest",
            "-c:v", "libx264",
            "-c:a", "aac",
            str(out),
        ]
        self._run(cmd, timeout=120)
        return str(out)

    def assemble_highlight_reel(self, segments: List[Dict], outro_path: str | None = None) -> Dict:
        """
        Build final timeline:
        [segment_pre][segment_clip][segment_post][transition]...
        and append optional Protocol Pulse outro.
        """
        day = date.today().isoformat()
        out_dir = self.video_root / day
        out_dir.mkdir(parents=True, exist_ok=True)
        timeline_parts: List[str] = []
        updated_segments: List[Dict] = []

        for idx, seg in enumerate(segments):
            source_video = self.download_source_video(seg["video_id"])
            clip_path = self.extract_video_clip(source_video, float(seg["start"]), float(seg["end"]))
            comm = self.generate_commentary_for_segment(seg, mood="chill")
            pre_block = self._audio_to_block_video(
                comm["pre_commentary_audio"],
                label="prelude",
                channel=str(seg.get("channel", "partner")),
                topic=str(seg.get("topic", "macro")),
            )
            post_block = self._audio_to_block_video(
                comm["post_commentary_audio"],
                label="debrief",
                channel=str(seg.get("channel", "partner")),
                topic=str(seg.get("topic", "macro")),
            )
            seg["pre_commentary_audio"] = comm["pre_commentary_audio"]
            seg["post_commentary_audio"] = comm["post_commentary_audio"]
            seg["clip_video"] = clip_path
            seg["pre_commentary_video"] = pre_block
            seg["post_commentary_video"] = post_block
            updated_segments.append(seg)

            timeline_parts.extend([pre_block, clip_path, post_block])
            if idx < len(segments) - 1:
                trans = self.make_transition_slide(
                    title=str(seg.get("video_title") or seg.get("title") or "next"),
                    channel=str(seg.get("channel") or "partner"),
                    topic=str(seg.get("topic") or "macro"),
                )
                timeline_parts.append(trans)

        if outro_path:
            maybe_outro = Path(outro_path)
            if not maybe_outro.is_absolute():
                maybe_outro = self.project_root / outro_path
            if maybe_outro.exists():
                timeline_parts.append(str(maybe_outro))

        concat_list = out_dir / "concat.txt"
        concat_list.write_text("".join([f"file '{p}'\n" for p in timeline_parts]), encoding="utf-8")
        final_path = out_dir / "highlight.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264", "-c:a", "aac",
            str(final_path),
        ]
        proc = self._run(cmd, timeout=900)
        if proc.returncode != 0:
            logger.warning("highlight concat failed: %s", (proc.stderr or "")[-300:])
        return {
            "reel_video": str(final_path),
            "segments": updated_segments,
            "timeline_parts": timeline_parts,
            "draft_only": True,
        }

    def generate_podcast_from_video(
        self,
        video_id: str,
        thumbnail_url: Optional[str] = None,
        channel_name: str = "YouTube Channel",
    ) -> Dict:
        """
        Transform a YouTube video into a podcast-style audio (or audio+static) asset.
        Returns dict with audio_file, video_file (optional) for Content Command Center.
        """
        day = date.today().isoformat()
        out_dir = self.work_root / day / "podcast"
        out_dir.mkdir(parents=True, exist_ok=True)
        audio_path = out_dir / f"podcast_{self._safe_name(video_id)}.m4a"
        try:
            source = self.download_source_video(video_id)
            if source and Path(source).exists():
                cmd = [
                    "ffmpeg", "-y", "-i", source,
                    "-vn", "-acodec", "aac", "-b:a", "128k",
                    str(audio_path),
                ]
                self._run(cmd, timeout=600)
            if not audio_path.exists() or audio_path.stat().st_size == 0:
                self._run([
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", "60", "-c:a", "aac", str(audio_path),
                ], timeout=60)
        except Exception as e:
            logger.warning("generate_podcast_from_video: %s", e)
            if not audio_path.exists():
                self._run([
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", "60", "-c:a", "aac", str(audio_path),
                ], timeout=60)
        rel = os.path.relpath(audio_path, self.project_root)
        return {
            "audio_file": rel.replace("\\", "/"),
            "video_file": None,
            "channel_name": channel_name,
            "video_id": video_id,
        }

    def create_full_social_package(
        self,
        video_id: str,
        channel_name: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Dict:
        """
        Generate podcast + placeholder article + clips list for Full Social Package.
        Returns dict with podcast, article, clips, social_videos, generated_at.
        """
        channel_name = channel_name or "Partner Channel"
        podcast_result = self.generate_podcast_from_video(
            video_id, thumbnail_url=thumbnail_url, channel_name=channel_name
        )
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        return {
            "podcast": podcast_result,
            "article": {
                "title": f"Bitcoin Lens: {channel_name} – {video_id}",
                "content_preview": f"Full package generated from {channel_name}.",
            },
            "clips": [],
            "social_videos": [],
            "generated_at": now,
        }

    def generate_bitcoin_lens_review(self, video_id: str, channel_name: str = "Partner Channel") -> Optional[Dict]:
        """
        Generate a reactionary Bitcoin Lens article (title + content). Does not save to DB.
        Returns dict with title, content, source_channel, generated_at.
        """
        from datetime import datetime, timezone
        prompt = (
            f"Write a short Protocol Pulse 'Bitcoin Lens' reaction paragraph (under 200 words) "
            f"about a YouTube video from {channel_name} (video id {video_id}). "
            "Tone: sovereign, tactical, lowercase. Focus on one key takeaway for transactors."
        )
        try:
            text = ollama_runtime.generate(prompt=prompt, preferred_model="llama3.1", timeout=15)
            content = (text or "").strip() or f"Bitcoin Lens analysis of {channel_name} coming soon."
            return {
                "title": f"Bitcoin Lens: {channel_name}",
                "content": content,
                "source_channel": channel_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.warning("generate_bitcoin_lens_review: %s", e)
            return {
                "title": f"Bitcoin Lens: {channel_name}",
                "content": f"Analysis of {channel_name} (video {video_id}) will be available after review.",
                "source_channel": channel_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    def generate_bitcoin_lens_article(
        self, video_id: str, channel_name: str = "Content Creator"
    ) -> Dict:
        """
        Generate Bitcoin Lens article and return article_id/title (for admin route that saves to DB).
        Caller in routes.py may create Article and commit; we just return content for that.
        """
        review = self.generate_bitcoin_lens_review(video_id, channel_name)
        if not review:
            return {"article_id": None, "title": None}
        return {
            "article_id": None,
            "title": review.get("title"),
            "content": review.get("content"),
            "source_channel": review.get("source_channel"),
        }


podcast_generator = PodcastGenerator()

