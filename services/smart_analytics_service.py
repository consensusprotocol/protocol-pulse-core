"""
Smart Analytics Service - Protocol Pulse

Aggregates all site metrics for the admin dashboard: page views, user preferences,
segments, affiliate clicks, revenue. Powers data-driven content and targeting.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from sqlalchemy import func, desc

from app import db
from models import (
    PageView,
    Article,
    User,
    AffiliateProduct,
    AffiliateProductClick,
)

logger = logging.getLogger(__name__)


class SmartAnalyticsService:
    def get_overview(self, days: int = 7) -> Dict:
        """High-level metrics for dashboard header."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            views = PageView.query.filter(PageView.created_at >= since).count()
            unique_sessions = db.session.query(
                func.count(func.distinct(PageView.session_id))
            ).filter(PageView.created_at >= since).scalar() or 0
            affiliate_clicks = AffiliateProductClick.query.filter(
                AffiliateProductClick.created_at >= since
            ).count()
            premium_users = User.query.filter(
                User.subscription_tier != 'free',
                User.subscription_tier != None
            ).count()
            return {
                'page_views': views,
                'unique_sessions': unique_sessions,
                'affiliate_clicks': affiliate_clicks,
                'premium_subscribers': premium_users,
                'days': days,
            }
        except Exception as e:
            logger.error(f"Smart analytics overview failed: {e}")
            return {}

    def get_top_pages(self, days: int = 7, limit: int = 15) -> List[Dict]:
        """Pages by view count — understand what users prefer."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            rows = (
                db.session.query(
                    PageView.page_path,
                    PageView.page_title,
                    PageView.page_category,
                    func.count(PageView.id).label('views'),
                    func.count(func.distinct(PageView.session_id)).label('sessions'),
                )
                .filter(PageView.created_at >= since)
                .group_by(
                    PageView.page_path,
                    PageView.page_title,
                    PageView.page_category,
                )
                .order_by(desc('views'))
                .limit(limit)
                .all()
            )
            return [
                {
                    'path': r.page_path,
                    'title': r.page_title or r.page_path,
                    'category': r.page_category,
                    'views': r.views,
                    'sessions': r.sessions,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Top pages failed: {e}")
            return []

    def get_user_preferences_by_category(self, days: int = 30) -> List[Dict]:
        """Aggregate views by category — which topics get most engagement."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            rows = (
                db.session.query(
                    PageView.page_category,
                    func.count(PageView.id).label('views'),
                    func.count(func.distinct(PageView.session_id)).label('sessions'),
                )
                .filter(
                    PageView.created_at >= since,
                    PageView.page_category != None,
                    PageView.page_category != '',
                )
                .group_by(PageView.page_category)
                .order_by(desc('views'))
                .all()
            )
            return [
                {'category': r.page_category, 'views': r.views, 'sessions': r.sessions}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Category preferences failed: {e}")
            return []

    def get_top_referrers(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Where traffic comes from — for targeting and partnerships."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            rows = (
                db.session.query(
                    PageView.referrer,
                    func.count(PageView.id).label('count'),
                )
                .filter(
                    PageView.created_at >= since,
                    PageView.referrer != None,
                    PageView.referrer != '',
                )
                .group_by(PageView.referrer)
                .order_by(desc('count'))
                .limit(limit)
                .all()
            )
            return [{'referrer': r.referrer, 'count': r.count} for r in rows]
        except Exception as e:
            logger.error(f"Top referrers failed: {e}")
            return []

    def get_article_performance(self, days: int = 30, limit: int = 20) -> List[Dict]:
        """Article views and engagement — which briefs convert."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            # PageView paths like /article/123
            article_views = (
                db.session.query(
                    PageView.page_path,
                    PageView.page_title,
                    func.count(PageView.id).label('views'),
                    func.count(func.distinct(PageView.session_id)).label('sessions'),
                    func.avg(PageView.time_on_page).label('avg_time'),
                    func.max(PageView.scroll_depth).label('max_scroll'),
                )
                .filter(
                    PageView.created_at >= since,
                    PageView.page_path.like('/article/%'),
                )
                .group_by(PageView.page_path, PageView.page_title)
                .order_by(desc('views'))
                .limit(limit)
                .all()
            )
            return [
                {
                    'path': r.page_path,
                    'title': r.page_title or r.page_path,
                    'views': r.views,
                    'sessions': r.sessions,
                    'avg_time_sec': round(r.avg_time or 0),
                    'max_scroll': r.max_scroll or 0,
                }
                for r in article_views
            ]
        except Exception as e:
            logger.error(f"Article performance failed: {e}")
            return []

    def get_affiliate_performance(self, days: int = 30) -> List[Dict]:
        """Clicks per product — which affiliate content converts."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            rows = (
                db.session.query(
                    AffiliateProductClick.product_id,
                    AffiliateProductClick.link_type,
                    func.count(AffiliateProductClick.id).label('clicks'),
                )
                .filter(AffiliateProductClick.created_at >= since)
                .group_by(AffiliateProductClick.product_id, AffiliateProductClick.link_type)
                .order_by(desc('clicks'))
                .all()
            )
            product_ids = [r.product_id for r in rows if r.product_id]
            products = {}
            if product_ids:
                for p in AffiliateProduct.query.filter(
                    AffiliateProduct.id.in_(product_ids)
                ).all():
                    products[p.id] = p.name
            return [
                {
                    'product_id': r.product_id,
                    'product_name': products.get(r.product_id, 'Unknown'),
                    'link_type': r.link_type,
                    'clicks': r.clicks,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Affiliate performance failed: {e}")
            return []

    def get_daily_traffic(self, days: int = 14) -> List[Dict]:
        """Views per day for trend chart."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            rows = (
                db.session.query(
                    func.date(PageView.created_at).label('day'),
                    func.count(PageView.id).label('views'),
                    func.count(func.distinct(PageView.session_id)).label('sessions'),
                )
                .filter(PageView.created_at >= since)
                .group_by(func.date(PageView.created_at))
                .order_by('day')
                .all()
            )
            return [
                {'day': r.day.isoformat() if r.day else None, 'views': r.views, 'sessions': r.sessions}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Daily traffic failed: {e}")
            return []

    def get_smart_dashboard_data(self, days: int = 7) -> Dict:
        """Single call for the full smart analytics dashboard."""
        return {
            'overview': self.get_overview(days=days),
            'top_pages': self.get_top_pages(days=days),
            'user_preferences': self.get_user_preferences_by_category(days=min(30, days * 4)),
            'top_referrers': self.get_top_referrers(days=days),
            'article_performance': self.get_article_performance(days=min(30, days * 4)),
            'affiliate_performance': self.get_affiliate_performance(days=min(30, days * 4)),
            'daily_traffic': self.get_daily_traffic(days=min(14, days * 2)),
        }


smart_analytics_service = SmartAnalyticsService()
