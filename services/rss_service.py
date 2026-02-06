import feedparser
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app import db
import models

class RSSService:
    """Service for managing RSS feed synchronization and generation"""
    
    # Global filter list for content to exclude from media feeds
    EXCLUDED_SHOWS = [
        'Orange Is The Nw Jill',
        'Orange Is The New Jill',
        'orange is the nw jill',
        'orange is the new jill'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Your podcast RSS feeds (curated list)
        self.podcast_feeds = [
            {
                'name': "Cypherpunk'd",
                'url': 'https://anchor.fm/s/fa724db8/podcast/rss',
                'category': 'Privacy & Freedom',
                'host': 'PBX',
                'color': '#f7931a'
            },
            {
                'name': 'Protocol Pulse', 
                'url': 'https://feed.podbean.com/protocolpulse/feed.xml',
                'category': 'Bitcoin & Markets',
                'host': 'Protocol Pulse',
                'color': '#dc2626'
            }
        ]
        
        # Episode cache for real-time display
        self._episode_cache = {}
        self._cache_expiry = None
    
    def sync_all_feeds(self) -> Dict[str, int]:
        """Synchronize all configured podcast RSS feeds"""
        results = {}
        
        for feed_config in self.podcast_feeds:
            try:
                count = self.sync_feed(feed_config['url'], feed_config['category'], feed_config['name'])
                results[feed_config['name']] = count
                self.logger.info(f"Synced {count} episodes from {feed_config['name']}")
            except Exception as e:
                self.logger.error(f"Failed to sync {feed_config['name']}: {e}")
                results[feed_config['name']] = 0
        
        return results
    
    def sync_feed(self, rss_url: str, category: str = "Web3", rss_source: str = "Protocol Pulse") -> int:
        """Sync individual RSS feed to database"""
        try:
            feed = feedparser.parse(rss_url)
            synced_count = 0
            
            for entry in feed.entries:
                # Skip excluded content - HARD BLOCK on "Jill" in any form
                if self._is_excluded_content(entry.title, rss_source):
                    continue
                if 'jill' in entry.title.lower():
                    continue
                
                # Check if episode already exists
                existing = models.Podcast.query.filter_by(
                    title=entry.title,
                    audio_url=self.extract_audio_url(entry)
                ).first()
                
                if existing:
                    continue
                
                # Create new podcast episode
                podcast = models.Podcast()
                podcast.title = entry.title
                podcast.description = self.clean_description(entry.get('description', ''))
                podcast.host = feed.feed.get('author', 'Protocol Pulse')
                podcast.duration = self.extract_duration(entry)
                podcast.audio_url = self.extract_audio_url(entry)
                podcast.cover_image_url = self.extract_cover_image(entry, feed)
                podcast.published_date = self.parse_date(entry.get('published_parsed'))
                podcast.category = category
                podcast.rss_source = rss_source
                podcast.featured = False
                
                db.session.add(podcast)
                synced_count += 1
            
            db.session.commit()
            return synced_count
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error syncing RSS feed {rss_url}: {e}")
            raise
    
    def extract_audio_url(self, entry) -> Optional[str]:
        """Extract audio URL from RSS entry"""
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.type.startswith('audio/'):
                    return enclosure.href
        
        # Fallback: look for links
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type', '').startswith('audio/'):
                    return link.href
        
        return None
    
    def extract_duration(self, entry) -> str:
        """Extract episode duration from RSS entry"""
        # Check iTunes duration
        if hasattr(entry, 'itunes_duration'):
            return entry.itunes_duration
        
        # Check other duration fields
        duration_fields = ['duration', 'podcast_duration']
        for field in duration_fields:
            if hasattr(entry, field):
                return str(getattr(entry, field))
        
        return "Unknown"
    
    def extract_cover_image(self, entry, feed) -> Optional[str]:
        """Extract cover image from RSS entry or feed"""
        # Episode-specific image
        if hasattr(entry, 'image') and entry.image.get('href'):
            return entry.image.href
        
        # iTunes image
        if hasattr(entry, 'itunes_image'):
            return entry.itunes_image
        
        # Feed-level image
        if hasattr(feed.feed, 'image') and feed.feed.image.get('href'):
            return feed.feed.image.href
        
        return None
    
    def clean_description(self, description: str) -> str:
        """Clean and truncate description"""
        import re
        # Remove HTML tags
        clean_desc = re.sub(r'<[^>]*>', '', description)
        # Limit length
        if len(clean_desc) > 500:
            clean_desc = clean_desc[:497] + "..."
        return clean_desc.strip()
    
    def _is_excluded_content(self, title: str, show_name: str = '') -> bool:
        """Check if content should be excluded based on title or show name"""
        check_text = f"{title} {show_name}".lower()
        for excluded in self.EXCLUDED_SHOWS:
            if excluded.lower() in check_text:
                self.logger.info(f"Filtering out excluded content: {title}")
                return True
        return False
    
    def parse_date(self, date_tuple) -> datetime:
        """Parse RSS date tuple to datetime"""
        if date_tuple:
            try:
                import time
                return datetime.fromtimestamp(time.mktime(date_tuple))
            except:
                pass
        return datetime.utcnow()
    
    def generate_rss_feed(self) -> str:
        """Generate RSS feed XML for published podcasts"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Get latest published podcasts
        podcasts = models.Podcast.query.order_by(models.Podcast.published_date.desc()).limit(50).all()
        
        # Create RSS XML
        rss = Element('rss', version='2.0')
        rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
        rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')
        
        channel = SubElement(rss, 'channel')
        
        # Channel info
        SubElement(channel, 'title').text = 'Protocol Pulse Podcast'
        SubElement(channel, 'description').text = 'The leading podcast for Web3, Bitcoin, and blockchain insights'
        SubElement(channel, 'link').text = 'https://your-domain.com/podcasts'
        SubElement(channel, 'language').text = 'en-us'
        SubElement(channel, 'copyright').text = f'© {datetime.now().year} Protocol Pulse'
        
        # Add episodes
        for podcast in podcasts:
            item = SubElement(channel, 'item')
            SubElement(item, 'title').text = podcast.title
            SubElement(item, 'description').text = podcast.description or ""
            SubElement(item, 'link').text = f'https://your-domain.com/podcasts/{podcast.id}'
            SubElement(item, 'guid').text = f'https://your-domain.com/podcasts/{podcast.id}'
            SubElement(item, 'pubDate').text = podcast.published_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            if podcast.audio_url:
                enclosure = SubElement(item, 'enclosure')
                enclosure.set('url', podcast.audio_url)
                enclosure.set('type', 'audio/mpeg')
                enclosure.set('length', '0')  # You may want to add actual file size
            
            if podcast.duration:
                SubElement(item, 'itunes:duration').text = podcast.duration
        
        # Pretty print XML
        rough_string = tostring(rss, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def get_latest_episodes(self, limit: int = 20) -> List[Dict]:
        """Get latest episodes from all feeds with caching"""
        import time
        
        # Check cache validity (15 minute cache)
        if self._cache_expiry and time.time() < self._cache_expiry and self._episode_cache:
            return list(self._episode_cache.values())[:limit]
        
        all_episodes = []
        
        for feed_config in self.podcast_feeds:
            try:
                feed = feedparser.parse(feed_config['url'])
                show_name = feed_config['name']
                
                for entry in feed.entries[:10]:  # Get latest 10 per show
                    # Skip excluded content
                    if self._is_excluded_content(entry.title, show_name):
                        continue
                    
                    episode = {
                        'id': hash(entry.get('link', entry.title))  % 100000,
                        'title': entry.title,
                        'description': self.clean_description(entry.get('description', '')),
                        'audio_url': self.extract_audio_url(entry),
                        'duration': self.extract_duration(entry),
                        'published_date': self.parse_date(entry.get('published_parsed')),
                        'cover_image': self.extract_cover_image(entry, feed),
                        'show_name': show_name,
                        'host': feed_config.get('host', 'Protocol Pulse'),
                        'category': feed_config.get('category', 'Main'),
                        'color': feed_config.get('color', '#dc2626')
                    }
                    all_episodes.append(episode)
                    
            except Exception as e:
                self.logger.error(f"Error fetching {feed_config['name']}: {e}")
        
        # Sort by date, newest first
        all_episodes.sort(key=lambda x: x['published_date'], reverse=True)
        
        # Update cache
        self._episode_cache = {ep['id']: ep for ep in all_episodes}
        self._cache_expiry = time.time() + (15 * 60)  # 15 minutes
        
        return all_episodes[:limit]
    
    def get_show_info(self) -> List[Dict]:
        """Get information about all podcast shows"""
        shows = []
        for feed_config in self.podcast_feeds:
            try:
                feed = feedparser.parse(feed_config['url'])
                show = {
                    'id': feed_config['name'].lower().replace(' ', '_').replace("'", ''),
                    'name': feed_config['name'],
                    'description': feed.feed.get('description', '')[:200] if hasattr(feed, 'feed') else '',
                    'host': feed_config.get('host', 'Protocol Pulse'),
                    'category': feed_config.get('category', 'Main'),
                    'color': feed_config.get('color', '#dc2626'),
                    'episode_count': len(feed.entries) if hasattr(feed, 'entries') else 0,
                    'cover_image': self._get_feed_cover(feed),
                    'rss_url': feed_config['url']
                }
                shows.append(show)
            except Exception as e:
                self.logger.error(f"Error getting show info for {feed_config['name']}: {e}")
        return shows
    
    def _get_feed_cover(self, feed) -> Optional[str]:
        """Extract cover image from feed"""
        try:
            if hasattr(feed.feed, 'image') and feed.feed.image:
                return feed.feed.image.get('href')
            if hasattr(feed.feed, 'itunes_image'):
                return feed.feed.itunes_image.get('href')
        except:
            pass
        return None
    
    def get_episodes_by_show(self, show_id: str, limit: int = 20) -> List[Dict]:
        """Get episodes for a specific show"""
        for feed_config in self.podcast_feeds:
            config_id = feed_config['name'].lower().replace(' ', '_').replace("'", '')
            if config_id == show_id:
                try:
                    feed = feedparser.parse(feed_config['url'])
                    episodes = []
                    for entry in feed.entries[:limit]:
                        # Skip excluded content
                        if self._is_excluded_content(entry.title, feed_config['name']):
                            continue
                        
                        episode = {
                            'id': hash(entry.get('link', entry.title)) % 100000,
                            'title': entry.title,
                            'description': self.clean_description(entry.get('description', '')),
                            'audio_url': self.extract_audio_url(entry),
                            'duration': self.extract_duration(entry),
                            'published_date': self.parse_date(entry.get('published_parsed')),
                            'cover_image': self.extract_cover_image(entry, feed),
                            'show_name': feed_config['name'],
                            'host': feed_config.get('host', 'Protocol Pulse'),
                            'color': feed_config.get('color', '#dc2626')
                        }
                        episodes.append(episode)
                    return episodes
                except Exception as e:
                    self.logger.error(f"Error fetching episodes for {show_id}: {e}")
        return []
    
    def clear_cache(self):
        """Clear the episode cache to force refresh"""
        self._episode_cache = {}
        self._cache_expiry = None
        self.logger.info("RSS episode cache cleared")
    
    def search_episodes(self, query: str, limit: int = 10) -> List[Dict]:
        """Search episodes by title or description"""
        all_episodes = self.get_latest_episodes(limit=50)
        query_lower = query.lower()
        results = [
            ep for ep in all_episodes
            if (query_lower in ep['title'].lower() or query_lower in ep['description'].lower())
            and not self._is_excluded_content(ep['title'], ep.get('show_name', ''))
        ]
        return results[:limit]


# Global instance for convenience
rss_service = RSSService()