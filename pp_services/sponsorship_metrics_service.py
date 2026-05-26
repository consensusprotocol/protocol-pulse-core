"""
Sponsorship deck metrics: aggregate YouTube views, website unique visits, social impressions.
Data sources: CSV (YouTube, X analytics) and DB (PageView, AnalyticsSummary).
"""

import csv
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Paths relative to project root (caller must set or use app.root_path)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def get_sponsorship_metrics(
    data_dir: Path = None,
    db_session=None,
    days_back: int = 30,
) -> Dict[str, Any]:
    """
    Aggregate metrics for the Real-Time Sponsorship Deck.
    Returns: youtube_views, website_unique_visits, social_impressions, and optional breakdowns.
    """
    data_dir = data_dir or DATA_DIR
    out = {
        "youtube_views": 0,
        "youtube_source": "none",
        "website_unique_visits": 0,
        "website_source": "db",
        "social_impressions": 0,
        "social_source": "none",
        "period_days": days_back,
        "generated_at": datetime.utcnow().isoformat(),
    }

    # YouTube: from spreadsheet/CSV (e.g. data/youtube_views.csv with columns: date, views or total_views)
    yt_csv = data_dir / "youtube_views.csv"
    if yt_csv.exists():
        try:
            total = 0
            with open(yt_csv, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    v = row.get("views") or row.get("total_views") or row.get("Views") or 0
                    try:
                        total += int(v)
                    except (TypeError, ValueError):
                        pass
            out["youtube_views"] = total
            out["youtube_source"] = "csv"
        except Exception as e:
            logger.warning("youtube_views.csv read failed: %s", e)

    # Website unique visits: from PageView (distinct session_id in period)
    if db_session is not None:
        try:
            import models
            since = datetime.utcnow() - timedelta(days=days_back)
            from sqlalchemy import func
            q = db_session.query(func.count(func.distinct(models.PageView.session_id))).filter(
                models.PageView.created_at >= since
            )
            out["website_unique_visits"] = q.scalar() or 0
            out["website_source"] = "db"
        except Exception as e:
            logger.warning("PageView unique visits query failed: %s", e)

    # Social impressions: from AnalyticsSummary or X analytics CSV
    try:
        if db_session is not None:
            import models
            since = datetime.utcnow() - timedelta(days=days_back)
            rows = db_session.query(models.AnalyticsSummary).filter(
                models.AnalyticsSummary.period_start >= since.date()
            ).all()
            total = sum(r.total_impressions or 0 for r in rows)
            if total > 0:
                out["social_impressions"] = total
                out["social_source"] = "db"
    except Exception as e:
        logger.warning("AnalyticsSummary impressions failed: %s", e)

    if out["social_impressions"] == 0:
        x_csv = data_dir / "x_analytics.csv"
        if not x_csv.exists():
            x_csv = data_dir / "x_impressions.csv"
        if x_csv.exists():
            try:
                total = 0
                with open(x_csv, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        v = row.get("impressions") or row.get("Impressions") or row.get("total_impressions") or 0
                        try:
                            total += int(v)
                        except (TypeError, ValueError):
                            pass
                out["social_impressions"] = total
                out["social_source"] = "csv"
            except Exception as e:
                logger.warning("X analytics CSV read failed: %s", e)

    return out


# ── Sponsorship Tier Calculator ─────────────────────────────────────────────

SPONSORSHIP_TIERS = [
    {
        "name": "Signal",
        "price_usd": 500,
        "includes": [
            "Newsletter mention (1x/week)",
            "1 article mention per month",
            "Logo on sponsors page",
        ],
    },
    {
        "name": "Broadcast",
        "price_usd": 1000,
        "includes": [
            "Newsletter banner (every issue)",
            "2 article mentions per month",
            "1 social post per week (X + Nostr)",
            "Logo on sponsors page",
            "Monthly performance report",
        ],
    },
    {
        "name": "Full Stack",
        "price_usd": 2500,
        "includes": [
            "Newsletter banner (every issue)",
            "Unlimited article mentions",
            "Cypherpunkd podcast mention (host-read)",
            "2 social posts per week (X + Nostr)",
            "Homepage banner placement",
            "Pulse Check video mention",
            "Dedicated sponsor dashboard",
            "Weekly performance report",
        ],
    },
]


def get_sponsorship_tiers(
    data_dir: Path = None,
    db_session=None,
) -> Dict[str, Any]:
    """
    Calculate sponsorship tier pricing with estimated CPM based on current audience metrics.
    """
    metrics = get_sponsorship_metrics(data_dir=data_dir, db_session=db_session, days_back=30)

    # Audience numbers for CPM calculation
    newsletter_subs = _get_newsletter_count(db_session)
    monthly_visitors = metrics["website_unique_visits"]
    social_reach = metrics["social_impressions"]

    # Total monthly reach estimate (newsletter sends + site visitors + social)
    # Newsletter: ~20 sends/mo * subscribers
    newsletter_monthly_impressions = newsletter_subs * 20
    total_monthly_reach = newsletter_monthly_impressions + monthly_visitors + social_reach

    tiers_out = []
    for tier in SPONSORSHIP_TIERS:
        # Estimate impressions per tier based on placement coverage
        if tier["name"] == "Signal":
            est_impressions = newsletter_monthly_impressions * 0.3 + monthly_visitors * 0.05
        elif tier["name"] == "Broadcast":
            est_impressions = newsletter_monthly_impressions + monthly_visitors * 0.15 + social_reach * 0.1
        else:  # Full Stack
            est_impressions = newsletter_monthly_impressions + monthly_visitors * 0.4 + social_reach * 0.3

        est_cpm = (tier["price_usd"] / max(est_impressions / 1000, 1)) if est_impressions > 0 else 0

        tiers_out.append({
            "name": tier["name"],
            "price_usd": tier["price_usd"],
            "includes": tier["includes"],
            "estimated_impressions": int(est_impressions),
            "estimated_cpm": round(est_cpm, 2),
        })

    return {
        "tiers": tiers_out,
        "audience": {
            "newsletter_subscribers": newsletter_subs,
            "monthly_site_visitors": monthly_visitors,
            "social_reach": social_reach,
            "total_monthly_reach": total_monthly_reach,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


def _get_newsletter_count(db_session=None) -> int:
    """Get current newsletter subscriber count."""
    if db_session is None:
        return 0
    try:
        from core.models import NewsletterSubscriber
        return db_session.query(NewsletterSubscriber).filter(
            NewsletterSubscriber.subscribed == True
        ).count()
    except Exception:
        try:
            from models import NewsletterSubscriber
            return db_session.query(NewsletterSubscriber).filter(
                NewsletterSubscriber.subscribed == True
            ).count()
        except Exception as e:
            logger.warning("Newsletter subscriber count failed: %s", e)
            return 0
