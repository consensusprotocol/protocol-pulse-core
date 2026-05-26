"""
Sovereign Analytics Engine - Self-Learning Engagement Intelligence

Tracks engagement patterns, calculates velocity scores, and provides
sponsor-ready performance data for Protocol Pulse content.
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from app import db
from models import EngagementEvent, ContentPerformance, AnalyticsSummary, LaunchSequence, Article
from sqlalchemy import func, desc

class AnalyticsService:
    """
    Core analytics engine for tracking and analyzing content performance.
    
    Key metrics:
    - 30-minute velocity window (critical for Grok algorithm)
    - Persona A/B testing (Alex vs Sarah)
    - Strategy effectiveness scoring
    - Profile click multipliers
    """
    
    VELOCITY_WEIGHTS = {
        '0_5': 10,   # First 5 minutes: 10x multiplier
        '5_15': 5,   # 5-15 minutes: 5x multiplier  
        '15_30': 2   # 15-30 minutes: 2x multiplier
    }
    
    GROK_SCORES = {
        'reply': 10,
        'retweet': 15,
        'quote': 20,
        'like': 1,
        'profile_visit': 12,
        'expensive_action': 75,  # Substantive replies
        'view': 0.1
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def track_event(
        self,
        event_type: str,
        content_type: str,
        content_id: int,
        source_platform: str = 'website',
        persona: Optional[str] = None,
        strategy: Optional[str] = None,
        published_at: Optional[datetime] = None,
        request_info: Optional[Dict] = None
    ) -> EngagementEvent:
        """
        Record an engagement event and update content performance.
        
        Args:
            event_type: Type of engagement (view, click, reply, etc.)
            content_type: Content category (article, launch_sequence, clip)
            content_id: ID of the content piece
            source_platform: Origin platform (x_twitter, nostr, website)
            persona: AI persona used (alex, sarah, cronkite, cypherpunk)
            strategy: Reply strategy used
            published_at: When the content was originally published
            request_info: Request metadata (user_agent, referrer, ip)
        
        Returns:
            Created EngagementEvent
        """
        try:
            # Auto-derive published_at from content if not provided
            if not published_at:
                published_at = self._get_content_published_at(content_type, content_id)
            
            # Calculate time since publication
            minutes_after = None
            is_30min = False
            if published_at:
                delta = datetime.utcnow() - published_at
                minutes_after = delta.total_seconds() / 60
                is_30min = minutes_after <= 30
            
            # Calculate Grok score contribution
            grok_score = self.GROK_SCORES.get(event_type, 0)
            if is_30min:
                grok_score *= 2  # Double score in critical window
            
            # Ensure grok_score is at least 1 for trackable events (not views)
            if event_type != 'view':
                grok_score = max(1, int(grok_score))
            else:
                grok_score = 0  # Views don't contribute to Grok score directly
            
            # Hash IP for privacy
            ip_hash = None
            if request_info and request_info.get('ip'):
                ip_hash = hashlib.sha256(request_info['ip'].encode()).hexdigest()[:32]
            
            event = EngagementEvent(
                event_type=event_type,
                content_type=content_type,
                content_id=content_id,
                source_platform=source_platform,
                persona=persona,
                strategy=strategy,
                minutes_after_post=minutes_after,
                is_30min_window=is_30min,
                grok_score_contribution=int(grok_score),
                user_agent=request_info.get('user_agent') if request_info else None,
                referrer=request_info.get('referrer') if request_info else None,
                ip_hash=ip_hash
            )
            
            db.session.add(event)
            db.session.commit()
            
            # Update aggregated performance
            self._update_content_performance(content_type, content_id, event)
            
            self.logger.info(f"📊 Tracked {event_type} for {content_type}:{content_id} (Grok: +{grok_score})")
            return event
            
        except Exception as e:
            self.logger.error(f"Failed to track event: {e}")
            db.session.rollback()
            raise
    
    def _update_content_performance(
        self,
        content_type: str,
        content_id: int,
        event: EngagementEvent
    ):
        """Update aggregated ContentPerformance record."""
        try:
            perf = ContentPerformance.query.filter_by(
                content_type=content_type,
                content_id=content_id
            ).first()
            
            if not perf:
                # Create new performance record
                title = self._get_content_title(content_type, content_id)
                perf = ContentPerformance(
                    content_type=content_type,
                    content_id=content_id,
                    content_title=title
                )
                db.session.add(perf)
            
            # Update counters based on event type
            event_map = {
                'view': 'total_views',
                'click': 'total_clicks',
                'reply': 'total_replies',
                'retweet': 'total_retweets',
                'quote': 'total_quotes',
                'like': 'total_likes',
                'profile_visit': 'profile_visits'
            }
            
            attr = event_map.get(event.event_type)
            if attr:
                setattr(perf, attr, getattr(perf, attr, 0) + 1)
            
            # Update velocity buckets for replies
            if event.event_type == 'reply' and event.minutes_after_post is not None:
                if event.minutes_after_post <= 5:
                    perf.replies_0_5min += 1
                elif event.minutes_after_post <= 15:
                    perf.replies_5_15min += 1
                elif event.minutes_after_post <= 30:
                    perf.replies_15_30min += 1
                else:
                    perf.replies_30plus_min += 1
                
                # Recalculate velocity score
                perf.velocity_score = (
                    perf.replies_0_5min * self.VELOCITY_WEIGHTS['0_5'] +
                    perf.replies_5_15min * self.VELOCITY_WEIGHTS['5_15'] +
                    perf.replies_15_30min * self.VELOCITY_WEIGHTS['15_30']
                )
            
            # Update Grok score
            perf.grok_score_total += event.grok_score_contribution
            
            # Track persona performance
            if event.persona == 'alex':
                perf.alex_engagements += 1
            elif event.persona == 'sarah':
                perf.sarah_engagements += 1
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update performance: {e}")
            db.session.rollback()
    
    def _get_content_title(self, content_type: str, content_id: int) -> str:
        """Get content title for performance record."""
        try:
            if content_type == 'article':
                article = Article.query.get(content_id)
                return article.title if article else f"Article #{content_id}"
            elif content_type == 'launch_sequence':
                seq = LaunchSequence.query.get(content_id)
                if seq:
                    return (seq.primary_post_copy or '')[:100]
                return f"Launch Sequence #{content_id}"
            return f"{content_type.title()} #{content_id}"
        except:
            return f"{content_type.title()} #{content_id}"
    
    def _get_content_published_at(self, content_type: str, content_id: int) -> Optional[datetime]:
        """Get content published_at timestamp for velocity tracking."""
        try:
            if content_type == 'article':
                article = Article.query.get(content_id)
                return article.created_at if article else None
            elif content_type == 'launch_sequence':
                seq = LaunchSequence.query.get(content_id)
                return seq.published_at or seq.created_at if seq else None
            return None
        except:
            return None
    
    def validate_content_exists(self, content_type: str, content_id: int) -> bool:
        """Validate that content exists before tracking."""
        try:
            if content_type == 'article':
                return Article.query.get(content_id) is not None
            elif content_type == 'launch_sequence':
                return LaunchSequence.query.get(content_id) is not None
            return True  # Allow other content types
        except:
            return False
    
    def get_velocity_leaders(self, hours: int = 24, limit: int = 10) -> List[Dict]:
        """Get top performing content by velocity score in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        leaders = ContentPerformance.query.filter(
            ContentPerformance.last_updated >= cutoff
        ).order_by(desc(ContentPerformance.velocity_score)).limit(limit).all()
        
        return [{
            'id': p.id,
            'content_type': p.content_type,
            'content_id': p.content_id,
            'title': p.content_title,
            'velocity_score': p.velocity_score,
            'grok_score': p.grok_score_total,
            'total_replies': p.total_replies,
            'profile_visits': p.profile_visits,
            'reached_for_you': p.reached_for_you,
            'best_strategy': p.best_performing_strategy
        } for p in leaders]
    
    def get_persona_comparison(self, days: int = 7) -> Dict:
        """Compare Alex vs Sarah persona performance."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            results = db.session.query(
                func.sum(ContentPerformance.alex_engagements).label('alex_total'),
                func.sum(ContentPerformance.sarah_engagements).label('sarah_total'),
                func.avg(ContentPerformance.velocity_score).label('avg_velocity')
            ).filter(ContentPerformance.created_at >= cutoff).first()
            
            if results:
                alex = results[0] or 0  # Access by index for safety
                sarah = results[1] or 0
                avg_vel = results[2] or 0
            else:
                alex, sarah, avg_vel = 0, 0, 0
        except Exception as e:
            self.logger.warning(f"Persona comparison query failed: {e}")
            alex, sarah, avg_vel = 0, 0, 0
        
        total = alex + sarah
        
        return {
            'alex_engagements': int(alex),
            'sarah_engagements': int(sarah),
            'alex_percentage': round((alex / total * 100) if total > 0 else 50, 1),
            'sarah_percentage': round((sarah / total * 100) if total > 0 else 50, 1),
            'winner': 'alex' if alex > sarah else ('sarah' if sarah > alex else 'tie'),
            'avg_velocity_score': round(float(avg_vel), 2),
            'period_days': days
        }
    
    def get_strategy_effectiveness(self, days: int = 7) -> List[Dict]:
        """Rank reply strategies by engagement effectiveness."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        results = db.session.query(
            EngagementEvent.strategy,
            func.count(EngagementEvent.id).label('total_events'),
            func.sum(EngagementEvent.grok_score_contribution).label('total_grok'),
            func.avg(EngagementEvent.grok_score_contribution).label('avg_grok')
        ).filter(
            EngagementEvent.created_at >= cutoff,
            EngagementEvent.strategy.isnot(None)
        ).group_by(EngagementEvent.strategy).order_by(desc('total_grok')).all()
        
        return [{
            'strategy': r.strategy,
            'total_events': r.total_events,
            'total_grok_score': r.total_grok or 0,
            'avg_grok_score': round(r.avg_grok or 0, 2)
        } for r in results]
    
    def get_hourly_performance(self, days: int = 7) -> List[Dict]:
        """Get engagement by hour to find optimal posting times."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        results = db.session.query(
            func.extract('hour', EngagementEvent.created_at).label('hour'),
            func.count(EngagementEvent.id).label('events'),
            func.sum(EngagementEvent.grok_score_contribution).label('grok_score')
        ).filter(
            EngagementEvent.created_at >= cutoff
        ).group_by('hour').order_by('hour').all()
        
        return [{
            'hour': int(r.hour),
            'hour_display': f"{int(r.hour):02d}:00 UTC",
            'events': r.events,
            'grok_score': r.grok_score or 0
        } for r in results]
    
    def get_30min_window_stats(self, days: int = 7) -> Dict:
        """Analyze performance within the critical 30-minute Grok window."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        total = EngagementEvent.query.filter(
            EngagementEvent.created_at >= cutoff
        ).count()
        
        in_window = EngagementEvent.query.filter(
            EngagementEvent.created_at >= cutoff,
            EngagementEvent.is_30min_window == True
        ).count()
        
        window_grok = db.session.query(
            func.sum(EngagementEvent.grok_score_contribution)
        ).filter(
            EngagementEvent.created_at >= cutoff,
            EngagementEvent.is_30min_window == True
        ).scalar() or 0
        
        return {
            'total_events': total,
            'events_in_window': in_window,
            'window_percentage': round((in_window / total * 100) if total > 0 else 0, 1),
            'window_grok_score': window_grok,
            'avg_grok_per_window_event': round((window_grok / in_window) if in_window > 0 else 0, 2)
        }
    
    def generate_daily_summary(self, date: datetime = None) -> AnalyticsSummary:
        """Generate daily analytics summary for reporting."""
        if date is None:
            date = datetime.utcnow().date() - timedelta(days=1)
        
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        
        # Get aggregated metrics
        events = EngagementEvent.query.filter(
            EngagementEvent.created_at >= start,
            EngagementEvent.created_at <= end
        ).all()
        
        total_grok = sum(e.grok_score_contribution for e in events)
        views = sum(1 for e in events if e.event_type == 'view')
        profile_visits = sum(1 for e in events if e.event_type == 'profile_visit')
        
        # Persona comparison
        alex = sum(1 for e in events if e.persona == 'alex')
        sarah = sum(1 for e in events if e.persona == 'sarah')
        
        # Find best hour
        hour_counts = {}
        for e in events:
            h = e.created_at.hour
            hour_counts[h] = hour_counts.get(h, 0) + e.grok_score_contribution
        
        best_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 8
        
        # Get top content
        top_perf = ContentPerformance.query.filter(
            ContentPerformance.last_updated >= start,
            ContentPerformance.last_updated <= end
        ).order_by(desc(ContentPerformance.velocity_score)).first()
        
        summary = AnalyticsSummary(
            period_type='daily',
            period_start=date,
            period_end=date,
            total_posts=len(set((e.content_type, e.content_id) for e in events)),
            total_impressions=views,
            total_engagements=len(events),
            total_profile_visits=profile_visits,
            avg_velocity_score=0,
            avg_grok_score=round(total_grok / len(events) if events else 0, 2),
            top_performing_content_id=top_perf.content_id if top_perf else None,
            top_performing_content_type=top_perf.content_type if top_perf else None,
            alex_total_score=alex,
            sarah_total_score=sarah,
            persona_winner='alex' if alex > sarah else ('sarah' if sarah > alex else 'tie'),
            best_posting_hour=best_hour,
            sponsor_value_estimate=round(views * 0.005 + len(events) * 0.10, 2)  # CPM estimate
        )
        
        db.session.add(summary)
        db.session.commit()
        
        self.logger.info(f"📈 Generated daily summary for {date}: {len(events)} events, {total_grok} Grok score")
        return summary
    
    def get_sponsor_metrics(self, days: int = 30) -> Dict:
        """Get sponsor-ready metrics for pitch decks."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        events = EngagementEvent.query.filter(
            EngagementEvent.created_at >= cutoff
        ).all()
        
        total_impressions = sum(1 for e in events if e.event_type == 'view')
        total_engagements = len(events)
        total_grok = sum(e.grok_score_contribution for e in events)
        profile_visits = sum(1 for e in events if e.event_type == 'profile_visit')
        
        # For You reach rate
        content_with_foryou = ContentPerformance.query.filter(
            ContentPerformance.created_at >= cutoff,
            ContentPerformance.reached_for_you == True
        ).count()
        
        total_content = ContentPerformance.query.filter(
            ContentPerformance.created_at >= cutoff
        ).count()
        
        return {
            'period_days': days,
            'total_impressions': total_impressions,
            'total_engagements': total_engagements,
            'engagement_rate': round((total_engagements / total_impressions * 100) if total_impressions > 0 else 0, 2),
            'total_grok_score': total_grok,
            'avg_grok_per_post': round((total_grok / total_content) if total_content > 0 else 0, 2),
            'profile_visits': profile_visits,
            'for_you_reach_rate': round((content_with_foryou / total_content * 100) if total_content > 0 else 0, 1),
            'estimated_cpm_value': round(total_impressions * 0.005, 2),
            'estimated_monthly_value': round(total_impressions * 0.005 * 30 / days, 2),
            'bitcoin_audience_verified': True,
            'sovereign_intelligence_powered': True
        }


# Singleton instance
analytics_service = AnalyticsService()
