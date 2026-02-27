import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import requests

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
CACHE_DURATION = 300


_channel_cache = {}
_cache_timestamps = {}


def load_youtube_channels():
    try:
        with open('data/supported_sources.json', 'r') as f:
            data = json.load(f)
            return data.get('youtube_channels', [])
    except Exception as e:
        logger.error(f"Failed to load youtube channels: {e}")
        return []


def get_channel_stats(channel_id: str) -> Optional[Dict]:
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY not configured")
        return None
    
    cache_key = f"stats_{channel_id}"
    if cache_key in _channel_cache:
        if datetime.now().timestamp() - _cache_timestamps.get(cache_key, 0) < CACHE_DURATION:
            return _channel_cache[cache_key]
    
    try:
        url = f"https://www.googleapis.com/youtube/v3/channels"
        params = {
            'part': 'snippet,statistics',
            'id': channel_id,
            'key': YOUTUBE_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('items'):
            item = data['items'][0]
            result = {
                'channel_id': channel_id,
                'title': item['snippet']['title'],
                'thumbnail': item['snippet']['thumbnails']['default']['url'],
                'subscriber_count': int(item['statistics'].get('subscriberCount', 0)),
                'video_count': int(item['statistics'].get('videoCount', 0)),
                'view_count': int(item['statistics'].get('viewCount', 0))
            }
            _channel_cache[cache_key] = result
            _cache_timestamps[cache_key] = datetime.now().timestamp()
            return result
    except Exception as e:
        logger.error(f"Failed to get channel stats for {channel_id}: {e}")
    
    return None


def get_latest_videos(channel_id: str, max_results: int = 3) -> List[Dict]:
    if not YOUTUBE_API_KEY:
        return []
    
    cache_key = f"videos_{channel_id}"
    if cache_key in _channel_cache:
        if datetime.now().timestamp() - _cache_timestamps.get(cache_key, 0) < CACHE_DURATION:
            return _channel_cache[cache_key]
    
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'order': 'date',
            'type': 'video',
            'maxResults': max_results,
            'key': YOUTUBE_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        videos = []
        for item in data.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            videos.append({
                'video_id': video_id,
                'title': snippet['title'],
                'thumbnail': snippet['thumbnails']['medium']['url'],
                'published_at': snippet['publishedAt'],
                'url': f"https://www.youtube.com/watch?v={video_id}"
            })
        
        _channel_cache[cache_key] = videos
        _cache_timestamps[cache_key] = datetime.now().timestamp()
        return videos
    except Exception as e:
        logger.error(f"Failed to get latest videos for {channel_id}: {e}")
    
    return []


def get_all_channel_cards() -> List[Dict]:
    channels = load_youtube_channels()
    cards = []
    
    for channel in channels:
        channel_id = channel.get('channel_id')
        if not channel_id:
            continue
        
        stats = get_channel_stats(channel_id)
        videos = get_latest_videos(channel_id, 3)
        
        card = {
            'name': channel['name'],
            'channel_id': channel_id,
            'tier': channel.get('tier', 'macro'),
            'featured': channel.get('featured', False),
            'stats': stats,
            'latest_videos': videos,
            'verified': True
        }
        cards.append(card)
    
    cards.sort(key=lambda x: (not x['featured'], -(x['stats']['subscriber_count'] if x['stats'] else 0)))
    return cards


def calculate_signal_strength(video: Dict) -> str:
    try:
        published = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
        age_hours = max(1, (datetime.now(published.tzinfo) - published).total_seconds() / 3600)
        
        if age_hours < 2:
            return "BREAKING"
        elif age_hours < 6:
            return "HOT"
        elif age_hours < 24:
            return "FRESH"
        elif age_hours < 72:
            return "RECENT"
        else:
            return "ARCHIVE"
    except:
        return "UNKNOWN"
