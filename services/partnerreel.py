from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from app import db
import models
from services.youtube_service import YouTubeService
from services import highlightcurator
from services.podcast_generator import podcast_generator

logger = logging.getLogger(__name__)


class PartnerReelService:
    def __init__(self) -> None:
        self.project_root = Path("/home/ultron/protocol_pulse")

    def _dominant_theme(self, story: List[Dict]) -> str:
        topics = [str(s.get("topic") or "macro") for s in story]
        if not topics:
            return "sovereign signal highlights"
        topic, _ = Counter(topics).most_common(1)[0]
        mapping = {
            "etf": "ETF flows & sovereign adoption",
            "regulation": "regulation pressure & sovereign response",
            "mining": "mining dynamics & network resilience",
            "macro": "macro stress & bitcoin signal",
            "self-custody": "self-custody & sovereignty playbook",
        }
        return mapping.get(topic, "sovereign signal highlights")

    def _source_summary(self, videos: List[Dict]) -> str:
        lines = []
        for v in videos:
            lines.append(f"{v.get('channel_name', 'unknown')}: {v.get('title', 'untitled')}")
        return "; ".join(lines)[:1900]

    def build_daily_partner_reel(self, max_videos_per_channel: int = 2) -> Optional[models.PartnerHighlightReel]:
        yt = YouTubeService()
        videos = yt.check_partner_channels_for_new_videos(hours_back=24)
        if not videos:
            logger.info("[PARTNER REEL] no new partner videos found in 24h window; using local fallback montage sources")
            channels = [c.get("name") for c in yt.PODCAST_CHANNELS[:4] if c.get("name")]
            videos = []
            for idx, ch in enumerate(channels):
                videos.append(
                    {
                        "video_id": f"fallback_{date.today().isoformat()}_{idx}",
                        "title": f"{ch} daily signal window",
                        "channel_name": ch,
                        "thumbnail": "",
                        "published_at": datetime.utcnow().isoformat(),
                    }
                )

        # Cap videos per channel.
        channel_counts = Counter()
        filtered = []
        for v in videos:
            ch = str(v.get("channel_name") or "unknown")
            if channel_counts[ch] >= max_videos_per_channel:
                continue
            filtered.append(v)
            channel_counts[ch] += 1

        candidates: List[Dict] = []
        for video in filtered:
            candidates.extend(highlightcurator.propose_clips_for_video(video))
        if not candidates:
            logger.info("[PARTNER REEL] no clip candidates produced")
            return None

        story = highlightcurator.build_story_from_candidates(candidates)
        if len(story) < 3:
            logger.info("[PARTNER REEL] story under minimum segment threshold")
            return None

        # Normalize story keys expected downstream.
        normalized_story = []
        for seg in story:
            normalized_story.append(
                {
                    "channel": seg.get("channel"),
                    "video_id": seg.get("video_id"),
                    "video_title": seg.get("title"),
                    "start": float(seg.get("start", 0)),
                    "end": float(seg.get("end", 0)),
                    "topic": seg.get("topic"),
                    "role": seg.get("role"),
                }
            )

        assembled = podcast_generator.assemble_highlight_reel(
            normalized_story,
            outro_path="static/video/tag.mp4",
        )
        reel_video = assembled.get("reel_video")
        if not reel_video or not Path(reel_video).exists():
            logger.warning("[PARTNER REEL] assembly did not create final reel artifact")
            return None

        final_segments = assembled.get("segments") or normalized_story
        clip_paths = [s.get("clip_video") for s in final_segments if s.get("clip_video")]
        row = models.PartnerHighlightReel(
            date=date.today(),
            theme=self._dominant_theme(final_segments),
            story_json=json.dumps(final_segments, ensure_ascii=True),
            video_path=str(reel_video),
            audio_path=None,
            clips_json=json.dumps(clip_paths, ensure_ascii=True),
            source_summary=self._source_summary(filtered),
            status="draft",
            created_at=datetime.utcnow(),
        )
        db.session.add(row)
        db.session.commit()
        logger.info("[PARTNER REEL] draft reel created id=%s video=%s", row.id, row.video_path)
        return row


partner_reel_service = PartnerReelService()

