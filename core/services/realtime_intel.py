"""
Real-Time Intelligence Engine - Protocol Pulse

Tracks live site activity, detects hot moments, generates content suggestions,
and creates automated tweet drafts when traffic peaks.
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from app import db
from models import PageView, HotMoment, ContentSuggestion, AutoTweet, Article
from sqlalchemy import func, desc

logger = logging.getLogger(__name__)


class RealTimeIntelService:
    """
    Core real-time analytics and intelligence engine.
    - Live page view tracking
    - Hot content detection with heat scores
    - AI-powered content suggestions
    - Peak-triggered tweet automation
    """

    HEAT_DECAY_MINUTES = 15
    PEAK_THRESHOLD_MULTIPLIER = 2.5
    MIN_VIEWS_FOR_PEAK = 10
    TWEET_COOLDOWN_MINUTES = 60

    PAGE_CATEGORIES = {
        '/live': 'terminal',
        '/whale-watcher': 'tools',
        '/scorecard': 'tools',
        '/drill': 'tools',
        '/operator-costs': 'tools',
        '/sovereign-custody': 'education',
        '/media': 'media',
        '/podcasts': 'media',
        '/bitcoin-music': 'culture',
        '/bitcoin-artists': 'culture',
        '/freedom-tech': 'topics',
        '/meetups': 'community',
        '/node-globe': 'network',
        '/article': 'articles',
        '/articles': 'articles',
        '/clips': 'media',
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def track_page_view(
        self,
        page_path: str,
        page_title: str = None,
        session_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        referrer: str = None,
        user_id: int = None,
        time_on_page: int = None,
        scroll_depth: int = None,
    ):
        """Track a page view event. Optionally update last view's time_on_page/scroll_depth."""
        try:
            ip_hash = None
            if ip_address:
                ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:32]

            category = self._categorize_page(page_path)

            view = PageView(
                page_path=page_path,
                page_title=page_title,
                page_category=category,
                session_id=session_id,
                ip_hash=ip_hash,
                user_agent=user_agent[:300] if user_agent else None,
                referrer=referrer[:500] if referrer else None,
                user_id=user_id,
                time_on_page=time_on_page or 0,
                scroll_depth=scroll_depth or 0,
            )
            db.session.add(view)
            db.session.commit()

            self._check_for_hot_moment(page_path, page_title, category)
            return view
        except Exception as e:
            self.logger.error(f"Failed to track page view: {e}")
            db.session.rollback()
            return None

    def update_page_view_engagement(self, session_id: str, page_path: str, time_on_page: int = None, scroll_depth: int = None):
        """Update the most recent page view for this session/path with engagement metrics."""
        try:
            q = PageView.query.filter_by(session_id=session_id, page_path=page_path).order_by(PageView.created_at.desc())
            view = q.first()
            if view:
                if time_on_page is not None:
                    view.time_on_page = time_on_page
                if scroll_depth is not None:
                    view.scroll_depth = max(view.scroll_depth or 0, scroll_depth)
                db.session.commit()
                return True
        except Exception as e:
            self.logger.error(f"Update page view engagement failed: {e}")
            db.session.rollback()
        return False

    def _categorize_page(self, page_path: str) -> str:
        for prefix, category in self.PAGE_CATEGORIES.items():
            if page_path.startswith(prefix):
                return category
        if page_path == '/' or not page_path:
            return 'home'
        return 'general'

    def _check_for_hot_moment(self, page_path: str, page_title: str, category: str):
        try:
            window_end = datetime.utcnow()
            window_start = window_end - timedelta(minutes=self.HEAT_DECAY_MINUTES)
            recent_views = PageView.query.filter(
                PageView.page_path == page_path,
                PageView.created_at >= window_start
            ).count()
            unique_visitors = db.session.query(
                func.count(func.distinct(PageView.ip_hash))
            ).filter(
                PageView.page_path == page_path,
                PageView.created_at >= window_start
            ).scalar() or 0
            baseline_window_start = window_end - timedelta(hours=24)
            baseline_views = PageView.query.filter(
                PageView.page_path == page_path,
                PageView.created_at >= baseline_window_start,
                PageView.created_at < window_start
            ).count()
            baseline_avg = baseline_views / (24 * 60 / self.HEAT_DECAY_MINUTES) if baseline_views > 0 else 1
            heat_score = (recent_views / max(baseline_avg, 1)) * (1 + unique_visitors * 0.1)
            is_peak = (
                recent_views >= self.MIN_VIEWS_FOR_PEAK and
                heat_score >= self.PEAK_THRESHOLD_MULTIPLIER
            )
            if is_peak:
                self._record_hot_moment(
                    page_path, page_title, category,
                    recent_views, unique_visitors, heat_score,
                    window_start, window_end
                )
        except Exception as e:
            self.logger.error(f"Hot moment check failed: {e}")

    def _record_hot_moment(
        self,
        page_path: str,
        page_title: str,
        category: str,
        views: int,
        unique_visitors: int,
        heat_score: float,
        window_start: datetime,
        window_end: datetime,
    ):
        try:
            recent_moment = HotMoment.query.filter(
                HotMoment.page_path == page_path,
                HotMoment.created_at >= datetime.utcnow() - timedelta(minutes=30)
            ).first()
            if recent_moment:
                recent_moment.views_in_window = views
                recent_moment.unique_visitors = unique_visitors
                recent_moment.heat_score = heat_score
                recent_moment.window_end = window_end
                db.session.commit()
                return
            moment = HotMoment(
                page_path=page_path,
                page_title=page_title,
                page_category=category,
                views_in_window=views,
                unique_visitors=unique_visitors,
                heat_score=heat_score,
                is_peak=True,
                peak_detected_at=datetime.utcnow(),
                window_start=window_start,
                window_end=window_end,
            )
            db.session.add(moment)
            db.session.commit()
            self.logger.info(f"Hot moment detected: {page_path} (heat: {heat_score:.1f})")
            self._maybe_generate_peak_tweet(moment)
        except Exception as e:
            self.logger.error(f"Failed to record hot moment: {e}")
            db.session.rollback()

    def _maybe_generate_peak_tweet(self, moment: HotMoment):
        try:
            recent_tweet = AutoTweet.query.filter(
                AutoTweet.trigger_page == moment.page_path,
                AutoTweet.created_at >= datetime.utcnow() - timedelta(minutes=self.TWEET_COOLDOWN_MINUTES)
            ).first()
            if recent_tweet or moment.heat_score < 3.0:
                return
            import random
            templates = [
                f"🔥 {moment.page_title or moment.page_path} is heating up. {moment.unique_visitors}+ operatives tuned in. →",
                f"⚡ Traffic spike on {moment.page_title or moment.page_path}. Join the intel briefing →",
            ]
            tweet_content = random.choice(templates)
            auto_tweet = AutoTweet(
                trigger_type='peak_traffic',
                trigger_page=moment.page_path,
                heat_score_at_trigger=moment.heat_score,
                tweet_content=tweet_content,
                hashtags='#Bitcoin #ProtocolPulse',
                status='draft'
            )
            db.session.add(auto_tweet)
            moment.tweet_drafted = True
            moment.tweet_content = tweet_content
            db.session.commit()
        except Exception as e:
            self.logger.error(f"Tweet generation failed: {e}")

    def get_hot_pages(self, limit: int = 5) -> List[Dict]:
        try:
            window_start = datetime.utcnow() - timedelta(minutes=30)
            hot_pages = db.session.query(
                PageView.page_path,
                PageView.page_title,
                PageView.page_category,
                func.count(PageView.id).label('view_count'),
                func.count(func.distinct(PageView.ip_hash)).label('unique_visitors')
            ).filter(
                PageView.created_at >= window_start
            ).group_by(
                PageView.page_path,
                PageView.page_title,
                PageView.page_category
            ).order_by(
                desc('view_count')
            ).limit(limit).all()

            results = []
            for page in hot_pages:
                heat_score = page.view_count * (1 + page.unique_visitors * 0.1)
                results.append({
                    'path': page.page_path,
                    'title': page.page_title or self._path_to_title(page.page_path),
                    'category': page.page_category,
                    'views': page.view_count,
                    'unique_visitors': page.unique_visitors,
                    'heat_score': round(heat_score, 1),
                    'is_hot': heat_score > 5
                })
            return results
        except Exception as e:
            self.logger.error(f"Failed to get hot pages: {e}")
            return []

    def _path_to_title(self, path: str) -> str:
        titles = {
            '/': 'Home',
            '/live': 'Live Terminal',
            '/whale-watcher': 'Whale Watcher',
            '/scorecard': 'Sovereign Scorecard',
            '/media': 'Media Hub',
            '/articles': 'Briefs',
            '/clips': 'Signal Clips',
        }
        return titles.get(path, path.replace('/', ' ').replace('-', ' ').title().strip())

    def get_realtime_stats(self) -> Dict:
        try:
            now = datetime.utcnow()
            last_15min = now - timedelta(minutes=15)
            last_hour = now - timedelta(hours=1)
            last_24h = now - timedelta(hours=24)
            views_15min = PageView.query.filter(PageView.created_at >= last_15min).count()
            views_1h = PageView.query.filter(PageView.created_at >= last_hour).count()
            views_24h = PageView.query.filter(PageView.created_at >= last_24h).count()
            active_sessions = db.session.query(
                func.count(func.distinct(PageView.session_id))
            ).filter(
                PageView.created_at >= last_15min
            ).scalar() or 0
            peak_moments = HotMoment.query.filter(
                HotMoment.created_at >= last_24h,
                HotMoment.is_peak == True
            ).count()
            top_referrers = db.session.query(
                PageView.referrer,
                func.count(PageView.id).label('count')
            ).filter(
                PageView.created_at >= last_24h,
                PageView.referrer != None,
                PageView.referrer != ''
            ).group_by(PageView.referrer).order_by(desc('count')).limit(5).all()
            return {
                'views_15min': views_15min,
                'views_1h': views_1h,
                'views_24h': views_24h,
                'active_sessions': active_sessions,
                'peak_moments_24h': peak_moments,
                'top_referrers': [{'referrer': r.referrer, 'count': r.count} for r in top_referrers],
                'timestamp': now.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get realtime stats: {e}")
            return {}

    def generate_content_suggestions(self) -> List:
        try:
            hot_pages = self.get_hot_pages(limit=10)
            suggestions = []
            for page in hot_pages:
                if page['heat_score'] > 3:
                    suggestion = self._create_suggestion_for_trend(page)
                    if suggestion:
                        suggestions.append(suggestion)
            category_counts = defaultdict(int)
            for page in hot_pages:
                if page['category']:
                    category_counts[page['category']] += page['views']
            if category_counts:
                top_category = max(category_counts, key=category_counts.get)
                category_suggestion = self._create_category_suggestion(top_category, category_counts[top_category])
                if category_suggestion:
                    suggestions.append(category_suggestion)
            return suggestions
        except Exception as e:
            self.logger.error(f"Content suggestion generation failed: {e}")
            return []

    def _create_suggestion_for_trend(self, page_data: Dict) -> Optional[ContentSuggestion]:
        try:
            existing = ContentSuggestion.query.filter(
                ContentSuggestion.based_on_page == page_data['path'],
                ContentSuggestion.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).first()
            if existing:
                return None
            template = {
                'type': 'article',
                'title': f"Trending: {page_data['title']}",
                'description': f"Create content about {page_data['title']} based on user interest.",
            }
            suggestion = ContentSuggestion(
                suggestion_type=template['type'],
                title=template['title'],
                description=template['description'],
                reasoning=f"Heat score {page_data['heat_score']}, {page_data['unique_visitors']} unique visitors.",
                based_on_page=page_data['path'],
                based_on_trend=page_data.get('category', ''),
                confidence_score=min(page_data['heat_score'] / 10, 1.0),
                status='pending'
            )
            db.session.add(suggestion)
            db.session.commit()
            return suggestion
        except Exception as e:
            self.logger.error(f"Failed to create trend suggestion: {e}")
            return None

    def _create_category_suggestion(self, category: str, view_count: int) -> Optional[ContentSuggestion]:
        try:
            existing = ContentSuggestion.query.filter(
                ContentSuggestion.based_on_trend == category,
                ContentSuggestion.created_at >= datetime.utcnow() - timedelta(hours=12)
            ).first()
            if existing:
                return None
            suggestion = ContentSuggestion(
                suggestion_type='marketing',
                title=f"Marketing Focus: {category.title()}",
                description=f"Category {category} has {view_count} views. Consider more content here.",
                reasoning=f"Category analysis: {category} top-performing.",
                based_on_trend=category,
                confidence_score=min(view_count / 100, 1.0),
                status='pending'
            )
            db.session.add(suggestion)
            db.session.commit()
            return suggestion
        except Exception as e:
            self.logger.error(f"Failed to create category suggestion: {e}")
            return None

    def get_pending_suggestions(self, limit: int = 10) -> List[Dict]:
        try:
            suggestions = ContentSuggestion.query.filter_by(
                status='pending'
            ).order_by(
                desc(ContentSuggestion.confidence_score)
            ).limit(limit).all()
            return [{
                'id': s.id,
                'type': s.suggestion_type,
                'title': s.title,
                'description': s.description,
                'reasoning': s.reasoning,
                'confidence': round(s.confidence_score * 100),
                'created_at': s.created_at.isoformat()
            } for s in suggestions]
        except Exception as e:
            self.logger.error(f"Failed to get suggestions: {e}")
            return []

    def get_pending_tweets(self, limit: int = 10) -> List[Dict]:
        try:
            tweets = AutoTweet.query.filter_by(
                status='draft'
            ).order_by(
                desc(AutoTweet.heat_score_at_trigger)
            ).limit(limit).all()
            return [{
                'id': t.id,
                'trigger_type': t.trigger_type,
                'trigger_page': t.trigger_page,
                'heat_score': round(t.heat_score_at_trigger, 1),
                'content': t.tweet_content,
                'hashtags': t.hashtags,
                'created_at': t.created_at.isoformat()
            } for t in tweets]
        except Exception as e:
            self.logger.error(f"Failed to get pending tweets: {e}")
            return []

    def approve_tweet(self, tweet_id: int) -> bool:
        try:
            tweet = AutoTweet.query.get(tweet_id)
            if tweet:
                tweet.status = 'approved'
                tweet.approved_at = datetime.utcnow()
                db.session.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to approve tweet: {e}")
        return False


realtime_intel = RealTimeIntelService()
