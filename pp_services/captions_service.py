"""
Captions.ai Service for Protocol Pulse
Generates AI avatar videos for Alex & Sarah style breakdowns
Uses the AI Creator API for talking-head video generation
"""

import os
import logging
import requests
from typing import Dict, Optional, List
from datetime import datetime

class CaptionsService:
    """Service for generating AI avatar videos via Captions.ai API"""
    
    BASE_URL = "https://api.captions.ai/v1"
    
    # Alex (Quant) and Sarah (Macro) avatar configurations
    AVATARS = {
        'alex': {
            'name': 'Alex',
            'role': 'Quantitative Analyst',
            'style': 'data-driven, technical, precise',
            'avatar_id': None  # Will use default or custom AI Twin
        },
        'sarah': {
            'name': 'Sarah',
            'role': 'Macro Strategist', 
            'style': 'contextual, geopolitical, institutional',
            'avatar_id': None
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.environ.get('CAPTIONS_API_KEY')
        self.initialized = False
        
        if self.api_key:
            self.initialized = True
            self.logger.info("Captions.ai service initialized")
        else:
            self.logger.warning("CAPTIONS_API_KEY not configured - video generation disabled")
    
    def _get_headers(self) -> Dict:
        """Get API headers"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def generate_script(self, topic: str, style: str = 'alex', 
                        max_chars: int = 750) -> str:
        """Generate a script for the AI avatar based on topic
        
        Args:
            topic: The news topic or data to cover
            style: 'alex' for quant or 'sarah' for macro
            max_chars: Maximum characters (Captions limit is 800)
        """
        avatar = self.AVATARS.get(style, self.AVATARS['alex'])
        
        if style == 'alex':
            intro = f"Breaking down the data on {topic}. "
            tone = "Focus on numbers, metrics, and technical analysis."
        else:
            intro = f"Here's the macro perspective on {topic}. "
            tone = "Focus on institutional implications and geopolitical context."
        
        script = f"{intro}Let me give you the key insights you need to know. {topic[:max_chars - 100]}"
        return script[:max_chars]
    
    def create_video(self, script: str, avatar_type: str = 'alex',
                     language: str = 'en') -> Optional[Dict]:
        """Create an AI avatar video from script
        
        Args:
            script: The text script (max 800 chars for 1 min video)
            avatar_type: 'alex' or 'sarah'
            language: Language code (default 'en')
            
        Returns:
            Dict with video_id and status, or None on failure
        """
        if not self.initialized:
            self.logger.error("Captions.ai not configured")
            return None
        
        if len(script) > 800:
            script = script[:800]
            self.logger.warning("Script truncated to 800 characters")
        
        avatar = self.AVATARS.get(avatar_type, self.AVATARS['alex'])
        
        try:
            payload = {
                'script': script,
                'language': language,
                'style': 'professional'
            }
            
            # Add avatar_id if configured
            if avatar.get('avatar_id'):
                payload['avatar'] = avatar['avatar_id']
            
            response = requests.post(
                f'{self.BASE_URL}/ai-creator/generate',
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Video generation started: {data.get('video_id')}")
                return {
                    'video_id': data.get('video_id'),
                    'status': data.get('status', 'processing'),
                    'estimated_time': data.get('estimated_time', 60)
                }
            else:
                self.logger.error(f"Captions API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating video: {e}")
            return None
    
    def check_video_status(self, video_id: str) -> Optional[Dict]:
        """Check the status of a video generation job
        
        Args:
            video_id: The video ID from create_video
            
        Returns:
            Dict with status and video_url if complete
        """
        if not self.initialized:
            return None
        
        try:
            response = requests.get(
                f'{self.BASE_URL}/ai-creator/status/{video_id}',
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'video_id': video_id,
                    'status': data.get('status'),
                    'video_url': data.get('video_url'),
                    'thumbnail_url': data.get('thumbnail_url'),
                    'duration': data.get('duration')
                }
            else:
                self.logger.error(f"Status check failed: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error checking video status: {e}")
            return None
    
    def download_video(self, video_url: str, output_path: str) -> bool:
        """Download a completed video to local storage
        
        Args:
            video_url: URL of the generated video
            output_path: Local path to save the video
            
        Returns:
            True if download successful
        """
        try:
            response = requests.get(video_url, stream=True, timeout=120)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.logger.info(f"Video downloaded to {output_path}")
                return True
            else:
                self.logger.error(f"Download failed: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Error downloading video: {e}")
            return False
    
    def generate_daily_brief(self, network_data: Dict, 
                             avatar_type: str = 'sarah') -> Optional[Dict]:
        """Generate a daily market brief video
        
        Args:
            network_data: Bitcoin network metrics
            avatar_type: Which avatar to use
            
        Returns:
            Video generation result
        """
        btc_price = network_data.get('price', 0)
        hashrate = network_data.get('hashrate', 0)
        difficulty = network_data.get('difficulty', 0)
        mempool_count = network_data.get('mempool_count', 0)
        
        if avatar_type == 'alex':
            script = f"""
            Good morning, transactors. Alex here with your daily network metrics.
            
            Bitcoin is trading at ${btc_price:,.0f}. Network hashrate stands at {hashrate:.1f} exahash.
            Current difficulty is {difficulty:.2f} trillion. The mempool shows {mempool_count:,} pending transactions.
            
            Key insight: These metrics indicate {"strong" if hashrate > 500 else "moderate"} miner confidence.
            Stay sovereign. Stay vigilant.
            """.strip()
        else:
            script = f"""
            Hello, this is Sarah with your macro brief.
            
            Bitcoin at ${btc_price:,.0f} reflects {"institutional accumulation" if btc_price > 80000 else "market consolidation"}.
            With {hashrate:.0f} exahash securing the network, Bitcoin remains the most secure monetary network in history.
            
            The macro takeaway: {"Bullish momentum continues" if btc_price > 80000 else "Building strength for the next move"}.
            This is Protocol Pulse. Intelligence for transactors.
            """.strip()
        
        return self.create_video(script, avatar_type)
    
    def generate_news_clip(self, headline: str, summary: str,
                           avatar_type: str = 'alex') -> Optional[Dict]:
        """Generate a short news clip video
        
        Args:
            headline: News headline
            summary: Brief summary of the news
            avatar_type: Which avatar to use
            
        Returns:
            Video generation result
        """
        script = f"""
        Breaking: {headline}
        
        {summary[:500]}
        
        This is Protocol Pulse, delivering intelligence for transactors.
        """.strip()
        
        return self.create_video(script[:800], avatar_type)


# Singleton instance
captions_service = CaptionsService()
