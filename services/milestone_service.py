"""
MILESTONE SERVICE — F6 Marketing OS
====================================
Monitors BTC price milestones and fires marketing campaigns.
Milestones fire ONCE only — never repeat. already_fired() is the safety gate.

GOSPEL LAWS:
- LAW 1: Launch gate (9 items) must all be ✓ before campaigns fire
- LAW 2: Price milestones fire once per threshold, never repeat
- LAW 3: Each milestone fires 5 actions: video, nostr, newsletter, banner, oracle ctx
- LAW 4: performance_metrics + milestone_fired tables track everything
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Milestone Definitions ──────────────────────────────────────────────────
MILESTONES: List[Dict] = [
    {"price": 100_000,   "label": "SIX FIGURES",   "campaign": "btc_100k"},
    {"price": 120_000,   "label": "$120K",           "campaign": "btc_120k"},
    {"price": 150_000,   "label": "$150K",           "campaign": "btc_150k"},
    {"price": 175_000,   "label": "$175K",           "campaign": "btc_175k"},
    {"price": 200_000,   "label": "TWO HUNDRED",     "campaign": "btc_200k"},
    {"price": 250_000,   "label": "$250K",           "campaign": "btc_250k"},
    {"price": 500_000,   "label": "HALF MILLION",    "campaign": "btc_500k"},
    {"price": 1_000_000, "label": "ONE MILLION",     "campaign": "btc_1m"},
]

# Banner duration after milestone fires
BANNER_DURATION_HOURS = 48


class MilestoneService:
    """
    Checks BTC price against milestone thresholds.
    Called every 5 min by APScheduler. Thread-safe via DB atomicity.
    """

    def check_price(self, current_price: float) -> List[Dict]:
        """
        Called every 5 min by price monitor cron.
        Returns list of milestones fired this cycle (usually empty).
        """
        fired = []
        for milestone in MILESTONES:
            if current_price >= milestone["price"] and not self.already_fired(milestone["price"]):
                result = self.fire_milestone(milestone, current_price)
                if result.get("success"):
                    fired.append(milestone)
        return fired

    def already_fired(self, price: int) -> bool:
        """
        Checks if milestone has been fired. Uses DB as source of truth.
        Critical safety gate — prevents double-trigger on price oscillation.
        """
        try:
            from app import db
            from models import MilestoneFired
            return db.session.query(MilestoneFired).filter_by(price_threshold=price).first() is not None
        except Exception as e:
            # On DB error: assume fired (fail-safe — better to miss than double-fire)
            logger.error("already_fired() DB error for price=%s: %s", price, e)
            return True

    def fire_milestone(self, milestone: Dict, actual_price: float) -> Dict:
        """
        Fires all 5 milestone actions atomically.
        If any action fails, we still proceed (partial success OK — banner is priority).
        DB record is written FIRST to prevent double-fire on retry.
        """
        from app import db
        from models import MilestoneFired, PerformanceMetrics

        price = milestone["price"]
        label = milestone["label"]
        campaign = milestone["campaign"]

        logger.info("🚀 MILESTONE TRIGGERED: %s (%.0f >= %s)", label, actual_price, price)

        results = {
            "milestone": milestone,
            "actual_price": actual_price,
            "success": False,
            "actions": {},
        }

        # ── Step 0: Mark as fired FIRST (prevents double-fire race) ──────────
        # Uses unique constraint on price_threshold — if two concurrent checks both
        # pass already_fired(), the second INSERT will raise IntegrityError and abort.
        # This provides true atomic safety beyond the application-level check.
        try:
            record = MilestoneFired(
                price_threshold=price,
                label=label,
                campaign=campaign,
                actual_price=actual_price,
                fired_at=datetime.utcnow(),
            )
            db.session.add(record)
            db.session.commit()
            results["actions"]["db_logged"] = True
        except Exception as e:
            db.session.rollback()
            # IntegrityError means a concurrent process already fired this milestone — safe to ignore
            from sqlalchemy.exc import IntegrityError
            if isinstance(e, IntegrityError):
                logger.warning("Milestone %s already fired by concurrent process — skipping.", label)
            else:
                logger.error("CRITICAL: Could not log milestone to DB: %s", e)
            results["actions"]["db_logged"] = False
            # Don't proceed — we can't guarantee no-duplicate without the DB record
            return results

        # ── Step 1: Update performance_metrics with milestone label ──────────
        try:
            today = datetime.utcnow().date()
            metric = PerformanceMetrics.query.filter_by(metric_date=today).first()
            if metric:
                metric.milestone_triggered = label
                db.session.commit()
            results["actions"]["performance_metrics_updated"] = True
        except Exception as e:
            db.session.rollback()
            logger.warning("Could not update performance_metrics: %s", e)
            results["actions"]["performance_metrics_updated"] = False

        # ── Step 2: Post Nostr note ──────────────────────────────────────────
        try:
            nostr_content = self._build_nostr_note(milestone, actual_price)
            from services.nostr_broadcaster import nostr_broadcaster
            nostr_result = nostr_broadcaster.broadcast_note(nostr_content)
            results["actions"]["nostr"] = nostr_result
        except Exception as e:
            logger.warning("Nostr broadcast failed for %s: %s", label, e)
            results["actions"]["nostr"] = {"success": False, "error": str(e)}

        # ── Step 3: Send newsletter blast ────────────────────────────────────
        try:
            from services.newsletter_engine import NewsletterEngine
            engine = NewsletterEngine()
            subscribers = engine.get_subscribers()
            if subscribers:
                subject = f"⚡ BITCOIN JUST HIT {label} — History Is Being Made"
                html = self._build_newsletter_html(milestone, actual_price)
                send_result = engine.send_newsletter(subscribers, subject=subject, html=html)
                results["actions"]["newsletter"] = send_result
            else:
                results["actions"]["newsletter"] = {"success": True, "note": "no subscribers yet"}
        except Exception as e:
            logger.warning("Newsletter blast failed for %s: %s", label, e)
            results["actions"]["newsletter"] = {"success": False, "error": str(e)}

        # ── Step 4: Activate homepage banner (48h) ───────────────────────────
        try:
            self._activate_banner(milestone, actual_price)
            results["actions"]["banner"] = True
        except Exception as e:
            logger.warning("Banner activation failed for %s: %s", label, e)
            results["actions"]["banner"] = False

        # ── Step 5: Trigger emergency video episode (async) ──────────────────
        try:
            self._trigger_milestone_episode(milestone, actual_price)
            results["actions"]["video_triggered"] = True
        except Exception as e:
            logger.warning("Video trigger failed for %s: %s", label, e)
            results["actions"]["video_triggered"] = False

        results["success"] = True
        logger.info("Milestone %s fired. Actions: %s", label, results["actions"])
        return results

    # ─── Banner Management ────────────────────────────────────────────────────

    def _activate_banner(self, milestone: Dict, actual_price: float) -> None:
        """Write banner state to a JSON file. Homepage reads this on each request."""
        import json
        from pathlib import Path

        banner_data = {
            "active": True,
            "label": milestone["label"],
            "campaign": milestone["campaign"],
            "actual_price": actual_price,
            "price_threshold": milestone["price"],
            "fired_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=BANNER_DURATION_HOURS)).isoformat(),
        }

        banner_file = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data" / "milestone_banner.json"
        banner_file.parent.mkdir(exist_ok=True)
        with open(banner_file, "w") as f:
            json.dump(banner_data, f)
        logger.info("Banner activated for %s — expires in %dh", milestone["label"], BANNER_DURATION_HOURS)

    @staticmethod
    def get_active_banner() -> Optional[Dict]:
        """Returns banner data if active and not expired. Called from route context processor."""
        try:
            import json
            from pathlib import Path

            banner_file = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data" / "milestone_banner.json"
            if not banner_file.exists():
                return None

            with open(banner_file) as f:
                data = json.load(f)

            if not data.get("active"):
                return None

            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() > expires_at:
                # Expired — deactivate
                data["active"] = False
                with open(banner_file, "w") as f:
                    json.dump(data, f)
                return None

            return data
        except Exception as e:
            logger.debug("get_active_banner error (non-fatal): %s", e)
            return None

    # ─── Content Builders ─────────────────────────────────────────────────────

    def _build_nostr_note(self, milestone: Dict, actual_price: float) -> str:
        price_fmt = f"${actual_price:,.0f}"
        label = milestone["label"]
        return (
            f"⚡ BITCOIN JUST HIT {label} — {price_fmt}\n\n"
            f"This is not a drill. The protocol keeps winning.\n\n"
            f"Intelligence for Transactors → https://protocolpulse.io\n\n"
            f"#Bitcoin #BTC #{milestone['campaign']} #ProtocolPulse"
        )

    def _build_newsletter_html(self, milestone: Dict, actual_price: float) -> str:
        price_fmt = f"${actual_price:,.0f}"
        label = milestone["label"]
        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Bitcoin Hits {label}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: #e0e0e0; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
  .banner {{ background: linear-gradient(135deg, #dc2626, #991b1b); border-radius: 12px; padding: 32px; text-align: center; margin-bottom: 32px; }}
  .banner h1 {{ color: #fff; font-size: 32px; font-weight: 900; margin: 0 0 8px; letter-spacing: -0.5px; }}
  .banner .price {{ color: #fca5a5; font-size: 48px; font-weight: 900; font-family: 'JetBrains Mono', monospace; margin: 12px 0; }}
  .banner p {{ color: rgba(255,255,255,0.85); margin: 0; font-size: 16px; }}
  .body-text {{ font-size: 16px; line-height: 1.7; color: #a0a0a0; margin: 24px 0; }}
  .cta {{ display: block; background: #dc2626; color: #fff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: 700; font-size: 16px; text-align: center; margin: 32px 0; }}
  .footer {{ font-size: 12px; color: #555; text-align: center; margin-top: 40px; }}
</style>
</head>
<body>
<div class="container">
  <div class="banner">
    <h1>⚡ BITCOIN HITS {label}</h1>
    <div class="price">{price_fmt}</div>
    <p>History is being made. Protocol Pulse is here for every milestone.</p>
  </div>
  <p class="body-text">Bitcoin just crossed <strong>{label}</strong> ({price_fmt}). This milestone joins the permanent record of the hardest money in human history.</p>
  <p class="body-text">Get the full intelligence briefing on Protocol Pulse — live market analysis, expert commentary, and the numbers that matter.</p>
  <a href="https://protocolpulse.io" class="cta">Read the Full Briefing →</a>
  <div class="footer">
    Protocol Pulse — Intelligence for Transactors<br>
    <a href="https://protocolpulse.io/unsubscribe" style="color:#555;">Unsubscribe</a>
  </div>
</div>
</body>
</html>
"""

    def _trigger_milestone_episode(self, milestone: Dict, actual_price: float) -> None:
        """
        Triggers emergency Pulse Check episode generation.
        Non-blocking — writes request to queue file and returns immediately.

        TODO: A separate consumer process (video_pipeline_v3/daily_run.py or a dedicated
        milestone_episode_worker.py) should tail milestone_episode_queue.jsonl and generate
        the episode. V1 uses queue-file pattern to decouple from the trigger path.
        """
        import json
        from pathlib import Path

        queue_file = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data" / "milestone_episode_queue.jsonl"
        queue_file.parent.mkdir(exist_ok=True)

        entry = {
            "milestone": milestone,
            "actual_price": actual_price,
            "requested_at": datetime.utcnow().isoformat(),
            "status": "queued",
        }
        with open(queue_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info("Episode generation queued for milestone %s", milestone["label"])


# ─── Weekly Performance Analysis ─────────────────────────────────────────────

def run_weekly_performance_analysis() -> Dict:
    """
    Runs every Sunday 00:00 UTC.
    Aggregates last 7 days of performance_metrics into a summary.
    Stored to data/weekly_performance_YYYY-WNN.json.
    """
    import json
    from pathlib import Path

    results = {"success": False, "error": None, "summary": {}}

    try:
        from app import db
        from models import PerformanceMetrics

        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)

        rows = PerformanceMetrics.query.filter(
            PerformanceMetrics.metric_date >= start_date,
            PerformanceMetrics.metric_date <= end_date,
        ).order_by(PerformanceMetrics.metric_date).all()

        if not rows:
            results["summary"] = {"week": str(end_date), "note": "no data for this week"}
            results["success"] = True
            return results

        summary = {
            "week_ending": str(end_date),
            "week_start": str(start_date),
            "days_with_data": len(rows),
            "total_page_views": sum(r.page_views or 0 for r in rows),
            "total_unique_visitors": sum(r.unique_visitors or 0 for r in rows),
            "total_articles_published": sum(r.articles_published or 0 for r in rows),
            "total_videos_rendered": sum(r.videos_rendered or 0 for r in rows),
            "total_oracle_sessions": sum(r.oracle_sessions or 0 for r in rows),
            "total_briefings_generated": sum(r.briefings_generated or 0 for r in rows),
            "total_newsletter_opens": sum(r.newsletter_opens or 0 for r in rows),
            "total_newsletter_clicks": sum(r.newsletter_clicks or 0 for r in rows),
            "btc_open": rows[0].btc_price_open if rows else None,
            "btc_close": rows[-1].btc_price_close if rows else None,
            "milestones_triggered": [r.milestone_triggered for r in rows if r.milestone_triggered],
            "generated_at": datetime.utcnow().isoformat(),
        }

        # BTC performance
        if summary["btc_open"] and summary["btc_close"]:
            pct = ((summary["btc_close"] - summary["btc_open"]) / summary["btc_open"]) * 100
            summary["btc_weekly_pct_change"] = round(pct, 2)

        # Save to file
        week_label = end_date.strftime("%Y-W%U")
        output_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data" / "weekly_reports"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"weekly_performance_{week_label}.json"
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)

        results["summary"] = summary
        results["success"] = True
        logger.info("Weekly performance report generated: %s", output_file)

    except Exception as e:
        results["error"] = str(e)
        logger.error("Weekly performance analysis failed: %s", e)

    return results


# ─── Singleton ────────────────────────────────────────────────────────────────
milestone_service = MilestoneService()
