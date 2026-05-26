"""
Sentiment Service: computes real-time market sentiment from the last 6 hours of feed items.
Scores content as RISK_ON, RISK_OFF, CONTENTIOUS, CONSENSUS_FORMING, or NEUTRAL.
When the state changes, auto-generates a PulseEvent and drafts an alert post for X.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SENTIMENT_STATES = ("RISK_ON", "RISK_OFF", "CONTENTIOUS", "CONSENSUS_FORMING", "NEUTRAL")


class SentimentService:
    def __init__(self):
        self._db = None

    def update_buffer(self):
        """
        Update rolling sentiment buffer from recent feed (CollectedSignal / FeedItem).
        Append one SentimentBuffer row with aggregate score and dominant theme.
        Returns dict with score, state, sample_size.
        """
        try:
            from app import app, db
            import models
            with app.app_context():
                window = datetime.utcnow() - timedelta(hours=6)
                signals = models.CollectedSignal.query.filter(
                    models.CollectedSignal.collected_at >= window
                ).limit(500).all()
                if not signals:
                    # Fallback: FeedItem
                    feed = models.FeedItem.query.filter(
                        models.FeedItem.created_at >= window
                    ).limit(500).all()
                    scores = [50.0] * len(feed)
                else:
                    # Simple heuristic: engagement and legendary => higher score
                    scores = []
                    for s in signals:
                        base = 50.0
                        if s.is_legendary:
                            base += 10
                        base += min(20, (s.engagement_score or 0) / 50)
                        scores.append(base)
                avg = sum(scores) / len(scores) if scores else 50.0
                state = "NEUTRAL"
                if avg >= 65:
                    state = "RISK_ON"
                elif avg <= 35:
                    state = "RISK_OFF"
                elif len(scores) > 20:
                    state = "CONSENSUS_FORMING"
                buf = models.SentimentBuffer(
                    sentiment_score=avg,
                    post_count=len(scores),
                    dominant_theme=state,
                )
                db.session.add(buf)
                db.session.commit()
                return {"score": avg, "state": state, "sample_size": len(scores)}
        except Exception as e:
            logger.warning("SentimentService update_buffer failed: %s", e)
            return {"score": 50.0, "state": "NEUTRAL", "sample_size": 0}

    def check_state_change_and_draft_alert(self):
        """
        Compare latest buffer to previous; if state changed, create PulseEvent and draft AutoPostDraft for X.
        """
        try:
            from app import app, db
            import models
            with app.app_context():
                recent = models.SentimentBuffer.query.order_by(
                    models.SentimentBuffer.timestamp.desc()
                ).limit(2).all()
                if len(recent) < 2:
                    return None
                new_state = recent[0].dominant_theme or "NEUTRAL"
                old_state = recent[1].dominant_theme or "NEUTRAL"
                if new_state == old_state:
                    return None
                event = models.PulseEvent(
                    event_type="sentiment_state_change",
                    from_state=old_state,
                    to_state=new_state,
                    score=recent[0].sentiment_score,
                )
                db.session.add(event)
                draft = models.AutoPostDraft(
                    platform="x",
                    body=f"Protocol Pulse sentiment update: {old_state} → {new_state}. Full analysis at protocolpulse.io.",
                    reason="Sentiment state change",
                    status="draft",
                )
                db.session.add(draft)
                db.session.commit()
                return {"event_id": event.id, "draft_id": draft.id}
        except Exception as e:
            logger.warning("check_state_change_and_draft_alert failed: %s", e)
            return None


sentiment_service = SentimentService()
