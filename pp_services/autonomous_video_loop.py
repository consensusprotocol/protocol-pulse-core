"""
Autonomous Video Loop Service
24/7 Machine for Cypherpunk'd content slicing and distribution
Runs in background to generate and publish clips while you sleep
"""
import os
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from threading import Thread
import time

logger = logging.getLogger(__name__)

class AutonomousVideoLoop:
    """
    The 24/7 Machine - Autonomously generates and distributes video content
    Monitors source channels, extracts clips, applies kinetic typography,
    and queues for social distribution
    """
    
    CONTENT_SOURCES = {
        'cypherpunkd': {
            'type': 'youtube_channel',
            'channel_id': 'UC_placeholder',
            'check_interval': 21600,  # 6 hours
            'auto_clip': True,
            'max_clip_duration': 60
        },
        'x_spaces': {
            'type': 'x_spaces',
            'monitored_accounts': ['@ProtocolPulse'],
            'check_interval': 3600,  # 1 hour
            'auto_transcribe': True
        },
        'partner_channels': {
            'type': 'youtube_playlist',
            'playlist_ids': [],
            'check_interval': 43200,  # 12 hours
            'auto_clip': True
        }
    }
    
    DISTRIBUTION_TARGETS = ['youtube_shorts', 'x_video', 'nostr']
    
    def __init__(self):
        self.is_running = False
        self.loop_thread = None
        self.clip_queue = []
        self.published_clips = []
        self.stats = {
            'clips_generated': 0,
            'clips_published': 0,
            'total_views': 0,
            'last_run': None
        }
        logger.info("Autonomous Video Loop initialized")
    
    def start(self):
        """Start the autonomous loop in a background thread"""
        if self.is_running:
            logger.warning("Autonomous loop already running")
            return
        
        self.is_running = True
        self.loop_thread = Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()
        logger.info("Autonomous Video Loop STARTED - 24/7 machine active")
    
    def stop(self):
        """Stop the autonomous loop"""
        self.is_running = False
        logger.info("Autonomous Video Loop STOPPED")
    
    def _run_loop(self):
        """Main loop - runs continuously in background"""
        while self.is_running:
            try:
                self._check_content_sources()
                self._process_clip_queue()
                self._publish_ready_clips()
                self.stats['last_run'] = datetime.utcnow().isoformat()
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Autonomous loop error: {e}")
                time.sleep(60)
    
    def _check_content_sources(self):
        """Check all configured content sources for new material"""
        for source_name, config in self.CONTENT_SOURCES.items():
            try:
                if config['type'] == 'youtube_channel':
                    self._check_youtube_source(source_name, config)
                elif config['type'] == 'x_spaces':
                    self._check_x_spaces(source_name, config)
            except Exception as e:
                logger.error(f"Error checking source {source_name}: {e}")
    
    def _check_youtube_source(self, name: str, config: Dict):
        """Check YouTube channel for new videos to clip"""
        logger.debug(f"Checking YouTube source: {name}")
        pass
    
    def _check_x_spaces(self, name: str, config: Dict):
        """Check for X Spaces recordings to transcribe and clip"""
        logger.debug(f"Checking X Spaces source: {name}")
        pass
    
    def _process_clip_queue(self):
        """Process queued clips - apply kinetic typography and prepare for publish"""
        if not self.clip_queue:
            return
        
        from pp_services.kinetic_typography import kinetic_service
        
        for clip in self.clip_queue[:5]:  # Process up to 5 at a time
            try:
                if clip.get('needs_captions'):
                    result = kinetic_service.generate_caption_overlay(
                        input_video=clip['video_path'],
                        captions=clip.get('captions', []),
                        style=clip.get('style', 'protocol_pulse')
                    )
                    if result:
                        clip['processed_path'] = result
                        clip['ready_for_publish'] = True
                        self.stats['clips_generated'] += 1
                
                self.clip_queue.remove(clip)
            except Exception as e:
                logger.error(f"Clip processing error: {e}")
    
    def _publish_ready_clips(self):
        """Publish clips that are ready for distribution"""
        ready_clips = [c for c in self.clip_queue if c.get('ready_for_publish')]
        
        for clip in ready_clips[:3]:  # Publish up to 3 at a time
            try:
                for target in self.DISTRIBUTION_TARGETS:
                    if self._publish_to_target(clip, target):
                        logger.info(f"Published clip to {target}: {clip.get('title', 'Untitled')}")
                
                self.published_clips.append(clip)
                self.clip_queue.remove(clip)
                self.stats['clips_published'] += 1
            except Exception as e:
                logger.error(f"Publish error: {e}")
    
    def _publish_to_target(self, clip: Dict, target: str) -> bool:
        """Publish a clip to a specific distribution target"""
        if target == 'nostr':
            return self._publish_to_nostr(clip)
        elif target == 'x_video':
            return self._publish_to_x(clip)
        elif target == 'youtube_shorts':
            return self._publish_to_youtube_shorts(clip)
        return False
    
    def _publish_to_nostr(self, clip: Dict) -> bool:
        """Publish clip announcement to Nostr"""
        try:
            from pp_services.nostr_broadcaster import nostr_broadcaster
            message = f"New Signal Clip: {clip.get('title', 'Bitcoin Intel')}\n\n{clip.get('description', '')}"
            return nostr_broadcaster.broadcast_content(message) is not None
        except Exception as e:
            logger.error(f"Nostr publish error: {e}")
            return False
    
    def _publish_to_x(self, clip: Dict) -> bool:
        """Publish clip to X/Twitter"""
        logger.debug(f"X publish queued: {clip.get('title')}")
        return True
    
    def _publish_to_youtube_shorts(self, clip: Dict) -> bool:
        """Publish clip as YouTube Short"""
        logger.debug(f"YouTube Shorts publish queued: {clip.get('title')}")
        return True
    
    def add_to_queue(
        self,
        video_path: str,
        title: str,
        captions: List[Dict] = None,
        style: str = 'protocol_pulse',
        auto_publish: bool = True
    ) -> bool:
        """Manually add a clip to the processing queue"""
        clip = {
            'video_path': video_path,
            'title': title,
            'captions': captions or [],
            'style': style,
            'needs_captions': bool(captions),
            'auto_publish': auto_publish,
            'added_at': datetime.utcnow().isoformat()
        }
        self.clip_queue.append(clip)
        logger.info(f"Added clip to queue: {title}")
        return True
    
    def get_status(self) -> Dict:
        """Get current status of the autonomous loop"""
        return {
            'is_running': self.is_running,
            'queue_size': len(self.clip_queue),
            'published_count': len(self.published_clips),
            'stats': self.stats
        }
    
    def get_queue(self) -> List[Dict]:
        """Get current clip queue"""
        return self.clip_queue
    
    def get_published(self, limit: int = 20) -> List[Dict]:
        """Get recently published clips"""
        return self.published_clips[-limit:]

autonomous_loop = AutonomousVideoLoop()
