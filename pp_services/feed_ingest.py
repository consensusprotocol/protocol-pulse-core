import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import feedparser
import requests

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def load_supported_sources():
    try:
        with open('data/supported_sources.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load supported_sources.json: {e}")
        return {}


def parse_rss_feed(url: str, source_name: str, tier: str, source_type: str = 'rss') -> list:
    items = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            
            items.append({
                'source': source_name,
                'source_type': source_type,
                'tier': tier,
                'title': entry.get('title', '')[:500],
                'url': entry.get('link', ''),
                'published_at': published,
                'author': entry.get('author', source_name),
                'summary': entry.get('summary', '')[:1000] if entry.get('summary') else '',
                'platform_icon': 'fa-rss' if source_type == 'rss' else 'fa-video',
                'verified': True
            })
    except Exception as e:
        logger.error(f"Failed to parse RSS feed {url}: {e}")
    return items


def ingest_rss_sources():
    from app import app, db
    from models import FeedItem
    
    sources = load_supported_sources()
    rss_sources = sources.get('rss_sources', [])
    rumble_sources = sources.get('rumble_sources', [])
    
    all_items = []
    
    for source in rss_sources:
        items = parse_rss_feed(
            source['rss_url'],
            source['name'],
            source['tier'],
            'rss'
        )
        all_items.extend(items)
    
    for source in rumble_sources:
        items = parse_rss_feed(
            source['rss_url'],
            source['name'],
            source['tier'],
            'rumble'
        )
        all_items.extend(items)
    
    with app.app_context():
        new_count = 0
        for item in all_items:
            if not item.get('url'):
                continue
            existing = FeedItem.query.filter_by(url=item['url']).first()
            if not existing:
                feed_item = FeedItem(
                    source=item['source'],
                    source_type=item['source_type'],
                    tier=item['tier'],
                    title=item['title'],
                    url=item['url'],
                    published_at=item['published_at'],
                    author=item['author'],
                    summary=item['summary'],
                    platform_icon=item['platform_icon'],
                    verified=item['verified']
                )
                db.session.add(feed_item)
                new_count += 1
        
        try:
            db.session.commit()
            logger.info(f"Ingested {new_count} new RSS feed items")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save feed items: {e}")
    
    return new_count


def ingest_youtube_rss():
    from app import app, db
    from models import FeedItem
    
    sources = load_supported_sources()
    youtube_channels = sources.get('youtube_channels', [])
    
    all_items = []
    
    for channel in youtube_channels:
        channel_id = channel.get('channel_id')
        if not channel_id:
            continue
        
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        items = parse_rss_feed(
            rss_url,
            channel['name'],
            channel['tier'],
            'youtube'
        )
        for item in items:
            item['platform_icon'] = 'fa-youtube'
        all_items.extend(items)
    
    with app.app_context():
        new_count = 0
        for item in all_items:
            if not item.get('url'):
                continue
            existing = FeedItem.query.filter_by(url=item['url']).first()
            if not existing:
                feed_item = FeedItem(
                    source=item['source'],
                    source_type=item['source_type'],
                    tier=item['tier'],
                    title=item['title'],
                    url=item['url'],
                    published_at=item['published_at'],
                    author=item['author'],
                    summary=item['summary'],
                    platform_icon=item['platform_icon'],
                    verified=item['verified']
                )
                db.session.add(feed_item)
                new_count += 1
        
        try:
            db.session.commit()
            logger.info(f"Ingested {new_count} new YouTube feed items")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save YouTube items: {e}")
    
    return new_count


def run_full_ingestion():
    logger.info("Starting full feed ingestion...")
    rss_count = ingest_rss_sources()
    yt_count = ingest_youtube_rss()
    logger.info(f"Feed ingestion complete: {rss_count} RSS + {yt_count} YouTube items")
    return rss_count + yt_count


def get_recent_feed_items(tier: Optional[str] = None, verified_only: bool = False, limit: int = 50):
    from app import app
    from models import FeedItem
    
    with app.app_context():
        query = FeedItem.query.order_by(FeedItem.published_at.desc())
        
        if tier and tier != 'all':
            query = query.filter(FeedItem.tier == tier)
        
        if verified_only:
            query = query.filter(FeedItem.verified == True)
        
        items = query.limit(limit).all()
        
        return [{
            'id': item.id,
            'source': item.source,
            'source_type': item.source_type,
            'tier': item.tier,
            'title': item.title,
            'url': item.url,
            'published_at': item.published_at.isoformat() if item.published_at else None,
            'author': item.author,
            'summary': item.summary[:200] if item.summary else '',
            'platform_icon': item.platform_icon,
            'verified': item.verified
        } for item in items]


if __name__ == '__main__':
    run_full_ingestion()
