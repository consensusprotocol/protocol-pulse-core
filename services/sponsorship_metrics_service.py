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
