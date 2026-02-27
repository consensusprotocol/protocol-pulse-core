#!/usr/bin/env python3
"""
PROTOCOL PULSE INTELLIGENCE SERVICE
====================================
Monitors partner YouTube channels + Substacks
Generates NotebookLM-style conversational breakdowns
Posts to X with urgency-style hooks
Sends Telegram briefings
Powers weekly newsletter digest
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseIntelligence")


import json
import os
from datetime import datetime

POSTED_URLS_FILE = "data/posted_urls.json"

def _load_posted_urls():
    """Load previously posted URLs"""
    os.makedirs("data", exist_ok=True)
    if os.path.exists(POSTED_URLS_FILE):
        try:
            with open(POSTED_URLS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"urls": [], "last_cleanup": None}
    return {"urls": [], "last_cleanup": None}

def _save_posted_url(url):
    """Save a URL as posted"""
    data = _load_posted_urls()
    if url not in data["urls"]:
        data["urls"].append(url)
        # Keep only last 500 URLs
        if len(data["urls"]) > 500:
            data["urls"] = data["urls"][-500:]
        with open(POSTED_URLS_FILE, 'w') as f:
            json.dump(data, f)

def _is_already_posted(url):
    """Check if URL was already posted"""
    data = _load_posted_urls()
    return url in data["urls"]


class PulseIntelligenceService:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.grok_key = os.getenv("GROK_API_KEY")
        
        # Load partner channels
        try:
            with open("config/partner_channels.json", "r") as f:
                self.channels = json.load(f)
        except:
            self.channels = {"youtube_channels": [], "substack_channels": []}
        
        # Cache for channel IDs
        self.channel_id_cache = {}
        
        logger.info(f"Pulse Intelligence initialized with {len(self.channels['youtube_channels'])} YouTube channels")
    
    def _get_channel_id(self, handle: str) -> Optional[str]:
        """Get YouTube channel ID from handle"""
        if handle in self.channel_id_cache:
            return self.channel_id_cache[handle]
        
        clean_handle = handle.replace("@", "")
        
        # Try channels endpoint first (for handles)
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            "key": self.youtube_api_key,
            "forHandle": clean_handle,
            "part": "id"
        }
        
        r = requests.get(url, params=params)
        if r.status_code == 200:
            data = r.json()
            if data.get("items"):
                channel_id = data["items"][0]["id"]
                self.channel_id_cache[handle] = channel_id
                return channel_id
        
        # Fallback: search for channel
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": self.youtube_api_key,
            "q": clean_handle,
            "type": "channel",
            "maxResults": 1
        }
        
        r = requests.get(url, params=params)
        if r.status_code == 200:
            data = r.json()
            if data.get("items"):
                channel_id = data["items"][0]["id"]["channelId"]
                self.channel_id_cache[handle] = channel_id
                return channel_id
        
        return None
    
    def get_recent_videos(self, hours_back: int = 24) -> List[Dict]:
        """Fetch recent videos from all partner channels"""
        if not self.youtube_api_key:
            logger.error("YOUTUBE_API_KEY not set")
            return []
        
        all_videos = []
        published_after = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat() + "Z"
        
        for channel in self.channels["youtube_channels"]:
            try:
                handle = channel["handle"]
                channel_id = self._get_channel_id(handle)
                
                if not channel_id:
                    logger.warning(f"Could not find channel ID for {handle}")
                    continue
                
                # Get recent videos from this channel
                url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "key": self.youtube_api_key,
                    "channelId": channel_id,
                    "type": "video",
                    "order": "date",
                    "maxResults": 3,
                    "publishedAfter": published_after,
                    "part": "snippet"
                }
                
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", []):
                        snippet = item.get("snippet", {})
                        video_id = item.get("id", {}).get("videoId")
                        
                        if video_id and snippet:
                            all_videos.append({
                                "channel_name": channel["name"],
                                "channel_twitter": channel.get("twitter", ""),
                                "video_id": video_id,
                                "title": snippet.get("title", ""),
                                "description": snippet.get("description", "")[:500],
                                "published_at": snippet.get("publishedAt", ""),
                                "url": f"https://www.youtube.com/watch?v={video_id}"
                            })
                else:
                    logger.warning(f"API error for {channel['name']}: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error fetching {channel['name']}: {e}")
        
        # Sort by published date
        all_videos.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        
        logger.info(f"Found {len(all_videos)} recent videos")
        return all_videos
    
    def generate_conversational_breakdown(self, video: Dict) -> Dict:
        """Generate NotebookLM-style conversational breakdown"""
        
        prompt = f"""You are creating a Protocol Pulse intelligence briefing - a NotebookLM-style conversational breakdown of a Bitcoin/crypto video.

VIDEO INFO:
Title: {video['title']}
Channel: {video['channel_name']}
Description: {video['description']}

Write a conversational breakdown as if two sharp analysts are discussing the key takeaways. Style:
- Casual but highly informed
- Extract the ALPHA - what's the actionable insight?
- Highlight any bold predictions or contrarian takes
- Note the sentiment (bullish/bearish/neutral) with reasoning
- Keep it punchy - this is cliff notes for busy people

Format:
**🎯 THE ALPHA:**
[One sentence summary of the most important takeaway]

**💬 THE BREAKDOWN:**
[2-3 paragraph conversational analysis, as if two analysts chatting]

**📊 SENTIMENT:** [Bullish/Bearish/Neutral] - [brief reason]

Keep it under 300 words total. Be direct, no fluff."""

        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.8
        )
        
        breakdown = response.choices[0].message.content.strip()
        
        return {
            "video": video,
            "breakdown": breakdown,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def generate_urgency_hook(self, video: Dict, breakdown: str) -> str:
        """Generate urgency-style X post hook"""
        
        prompt = f"""Create an attention-grabbing X/Twitter post for this Bitcoin content.

VIDEO: {video['title']} by {video['channel_name']}
BREAKDOWN SUMMARY: {breakdown[:300]}

Style guidelines:
- Urgency/intrigue hook (like viral YouTube thumbnails but text)
- Professional institutional crypto-anarchy tone
- Make people NEED to click
- Tag the creator: {video.get('channel_twitter', '')}
- End with link placeholder [LINK]

Examples of good hooks:
- "Breedlove just dropped something that changes everything about how we think about [X]..."
- "This might be the most important 20 minutes you watch this month. @creator breaks down..."
- "The smart money is paying attention to this. Here's why..."
- "I've watched hundreds of Bitcoin videos. This one hit different."

Keep under 250 chars (before link). No hashtags. Just the hook, nothing else."""

        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.9
        )
        
        hook = response.choices[0].message.content.strip().strip('"')
        return hook
    
    def generate_telegram_briefing(self, videos_with_breakdowns: List[Dict]) -> str:
        """Generate casual Telegram briefing"""
        
        if not videos_with_breakdowns:
            return None
        
        briefing_parts = ["🔴 <b>PROTOCOL PULSE INTEL DROP</b>\n"]
        briefing_parts.append("Here's what the smart money is talking about today:\n")
        
        for item in videos_with_breakdowns[:5]:
            video = item["video"]
            breakdown = item["breakdown"]
            
            # Extract just the alpha line
            alpha_line = ""
            for line in breakdown.split("\n"):
                if "ALPHA" in line.upper():
                    alpha_line = line.replace("**", "").replace("🎯", "").replace("THE ALPHA:", "").strip()
                    break
            
            if not alpha_line:
                alpha_line = video["title"][:80]
            
            briefing_parts.append(f"\n• <b>{video['channel_name']}</b>: {alpha_line[:100]}")
        
        briefing_parts.append("\n\n📰 Full breakdowns on Protocol Pulse →")
        
        return "".join(briefing_parts)
    
    def run_daily_pulse(self) -> Dict:
        """Run the daily intelligence pulse"""
        logger.info("Running daily pulse intelligence...")
        
        # 1. Get recent videos
        videos = self.get_recent_videos(hours_back=48)
        
        if not videos:
            logger.info("No new videos found")
            return {"status": "no_content", "videos": 0}
        
        # 2. Generate breakdowns for top videos
        breakdowns = []
        for video in videos[:5]:
            try:
                breakdown = self.generate_conversational_breakdown(video)
                breakdowns.append(breakdown)
                logger.info(f"Generated breakdown for: {video['title'][:50]}")
            except Exception as e:
                logger.error(f"Error generating breakdown: {e}")
        
        # 3. Generate urgency hooks for X posts
        x_posts = []
        for item in breakdowns[:3]:
            try:
                hook = self.generate_urgency_hook(item["video"], item["breakdown"])
                x_posts.append({
                    "hook": hook,
                    "video": item["video"],
                    "breakdown": item["breakdown"]
                })
            except Exception as e:
                logger.error(f"Error generating X hook: {e}")
        
        # 4. Generate Telegram briefing
        telegram_msg = self.generate_telegram_briefing(breakdowns)
        
        # 5. Send Telegram briefing
        if telegram_msg:
            try:
                from services.telegram_service import send_telegram_message
                send_telegram_message(telegram_msg, parse_mode='HTML')
                logger.info("Sent Telegram briefing")
            except Exception as e:
                logger.error(f"Failed to send Telegram: {e}")
        
        return {
            "status": "success",
            "videos_processed": len(breakdowns),
            "breakdowns": breakdowns,
            "x_posts": x_posts,
            "telegram_briefing": telegram_msg
        }

# Singleton
pulse_intelligence = PulseIntelligenceService()

if __name__ == "__main__":
    result = pulse_intelligence.run_daily_pulse()
    print(json.dumps(result, indent=2, default=str))
