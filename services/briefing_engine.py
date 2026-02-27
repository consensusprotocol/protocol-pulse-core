"""
Sarah's Daily Intelligence Briefing — flagship morning report (06:00 UTC).
Collects verified signals from DB (CollectedSignal / FeedItem), fetches live Bitcoin
network data from Mempool.space, uses OpenAI/Gemini to compose a structured briefing.
Handles emergency flash alerts when sentiment drift exceeds threshold.
"""

import logging
from datetime import datetime, date, timedelta

from app import app, db
import models
from services.node_service import NodeService
from services.ai_service import AIService

logger = logging.getLogger(__name__)

# Legendary handles get 3x priority in signal weighting (align with editorial rule)
LEGENDARY_HANDLES = {
    "saylor", "lynaldencontact", "adam3us", "jeffbooth", "prestonpysh", "saifedean",
    "breedlove22", "jack", "lopp", "odell", "pierre_rochard", "martybent", "marshalllong",
    "_checkmatey_", "woonomic", "natbrunell", "nvk", "coryklippsten",
}


class BriefingEngine:
    def __init__(self):
        self.ai_service = AIService()
        self._node_service = NodeService

    def get_top_signals(self, limit: int = 3, hours_back: int = 48):
        """Get top verified signals from CollectedSignal, optionally from FeedItem fallback."""
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        signals = (
            models.CollectedSignal.query.filter(
                models.CollectedSignal.collected_at >= cutoff,
                models.CollectedSignal.is_verified == True,
            )
            .order_by(
                models.CollectedSignal.is_legendary.desc(),
                models.CollectedSignal.engagement_score.desc(),
            )
            .limit(limit * 2)  # fetch extra then take top by score
            .all()
        )
        if not signals:
            # Fallback: use FeedItem if available
            feed = (
                models.FeedItem.query.filter(models.FeedItem.created_at >= cutoff)
                .order_by(models.FeedItem.created_at.desc())
                .limit(limit * 2)
                .all()
            )
            return [
                {
                    "title": getattr(f, "title", None) or getattr(f, "content", "")[:200],
                    "source": getattr(f, "source", "Unknown"),
                    "url": getattr(f, "url", "") or "#",
                    "impact": 5.0,
                    "content": getattr(f, "summary", "") or getattr(f, "content", "")[:500],
                }
                for f in feed[:limit]
            ]
        # Score: legendary boost + engagement
        scored = []
        for s in signals:
            score = (s.engagement_score or 0) + (30 if s.is_legendary else 0)
            scored.append((score, s))
        scored.sort(key=lambda x: -x[0])
        return [
            {
                "title": (s.content or "")[:300],
                "source": s.author_name or s.author_handle,
                "url": s.url or "#",
                "impact": min(10.0, (s.engagement_score or 0) / 10.0 + 5.0),
                "content": (s.content or "")[:500],
            }
            for _, s in scored[:limit]
        ]

    def generate_daily_brief(self):
        """
        Generate Sarah's daily intelligence brief. Creates Article + SarahBrief.
        Returns article_id if successful, None if already exists for today or no signals.
        """
        with app.app_context():
            today = date.today()
            existing = models.SarahBrief.query.filter_by(brief_date=today).first()
            if existing:
                logger.info("Sarah brief already exists for today")
                return existing.article_id

            signals = self.get_top_signals(limit=3, hours_back=48)
            if not signals:
                logger.warning("No signals available for daily brief")
                return None

            try:
                network_stats = self._node_service.get_network_stats()
            except Exception as e:
                logger.warning("Network stats unavailable: %s", e)
                network_stats = {}

            prompt = self._build_brief_prompt(signals, network_stats)
            try:
                body_html = self.ai_service.generate_content_openai(prompt)
            except Exception as e:
                logger.exception("AI brief generation failed: %s", e)
                try:
                    from services.gemini_service import gemini_service
                    body_html = gemini_service.generate_content(prompt, system_prompt="")
                except Exception as e2:
                    logger.exception("Gemini fallback failed: %s", e2)
                    return None

            if not body_html or len(body_html.strip()) < 100:
                logger.warning("Brief content too short")
                return None

            title = f"Sarah's Daily Intelligence Brief — {today.strftime('%B %d, %Y')}"
            article = models.Article(
                title=title,
                content=body_html,
                summary="Daily intelligence briefing for Bitcoin operators.",
                category="Briefing",
                author="Sarah (Protocol Pulse)",
                published=False,
            )
            db.session.add(article)
            db.session.flush()

            sb = models.SarahBrief(
                article_id=article.id,
                brief_date=today,
                macro_state=network_stats.get("status", "OPERATIONAL"),
                network_calibration=network_stats.get("difficulty_progress", ""),
                signal_1_title=signals[0].get("title", "")[:500] if len(signals) > 0 else None,
                signal_1_source=signals[0].get("source", "")[:500] if len(signals) > 0 else None,
                signal_1_url=signals[0].get("url", "")[:500] if len(signals) > 0 else None,
                signal_1_impact=signals[0].get("impact", 0) if len(signals) > 0 else 0,
                signal_2_title=signals[1].get("title", "")[:500] if len(signals) > 1 else None,
                signal_2_source=signals[1].get("source", "")[:500] if len(signals) > 1 else None,
                signal_2_url=signals[1].get("url", "")[:500] if len(signals) > 1 else None,
                signal_2_impact=signals[1].get("impact", 0) if len(signals) > 1 else 0,
                signal_3_title=signals[2].get("title", "")[:500] if len(signals) > 2 else None,
                signal_3_source=signals[2].get("source", "")[:500] if len(signals) > 2 else None,
                signal_3_url=signals[2].get("url", "")[:500] if len(signals) > 2 else None,
                signal_3_impact=signals[2].get("impact", 0) if len(signals) > 2 else 0,
                mempool_state=network_stats.get("difficulty_progress", ""),
                hashrate_state=network_stats.get("hashrate", ""),
            )
            db.session.add(sb)
            db.session.commit()
            logger.info("Sarah daily brief created: article_id=%s", article.id)
            return article.id

    def _build_brief_prompt(self, signals, network_stats):
        date_str = date.today().strftime("%B %d, %Y")
        signals_text = "\n".join(
            f"- [{s.get('source')}] {s.get('title', '')[:200]} (impact: {s.get('impact', 5)})"
            for s in signals
        )
        network_text = (
            f"Block height: {network_stats.get('height', 'N/A')}, "
            f"Hashrate: {network_stats.get('hashrate', 'N/A')}, "
            f"Difficulty progress: {network_stats.get('difficulty_progress', 'N/A')}."
        )
        return f"""You are Sarah, Protocol Pulse's macro strategist. Generate a Daily Brief for {date_str}.

VOICE: Clinical, sovereignty-focused. Like Lyn Alden meets a cypherpunk intelligence officer.
AUDIENCE: Bitcoin operators who value signal over noise.

TODAY'S TOP SIGNALS:
{signals_text}

NETWORK DATA:
{network_text}

Generate the brief with:
1. OPENING (2-3 sentences): Clinical macro overview of the last 24 hours.
2. THREE SIGNALS: For each signal above, one-line summary and why it matters to sovereigns.
3. CLOSING: Call-to-action referencing /drill (Recovery Drill) or /operator-costs (Cost Calculator).

Output ONLY clean HTML. Use <p> for paragraphs, <h3> for section headers. No markdown.
Keep total length under 400 words. No emojis. No hashtags."""

    def check_emergency_flash(self):
        """
        Check for emergency sentiment drift (e.g. 40%+ in 60 min). Creates EmergencyFlash if triggered.
        Returns flash dict if new flash created, None otherwise.
        """
        with app.app_context():
            window_start = datetime.utcnow() - timedelta(minutes=60)
            recent = (
                models.SentimentBuffer.query.filter(
                    models.SentimentBuffer.timestamp >= window_start
                )
                .order_by(models.SentimentBuffer.timestamp.asc())
                .all()
            )
            if len(recent) < 2:
                return None
            first_score = recent[0].sentiment_score
            last_score = recent[-1].sentiment_score
            drift = abs(last_score - first_score)
            if drift < 40.0:
                return None
            # Create flash
            direction = "RISK_ON" if last_score > first_score else "RISK_OFF"
            flash = models.EmergencyFlash(
                previous_score=first_score,
                current_score=last_score,
                drift_magnitude=drift,
                direction=direction,
                trigger_reason=f"Sentiment drift {drift:.1f}% in 60 minutes",
            )
            db.session.add(flash)
            db.session.commit()
            return {
                "id": flash.id,
                "direction": direction,
                "drift_magnitude": drift,
                "trigger_reason": flash.trigger_reason,
            }


# Singleton for routes
briefing_engine = BriefingEngine()
