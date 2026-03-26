"""
COMMANDER ONBOARDING EMAIL SEQUENCE
====================================
Day 1:  Welcome — intelligence layer active, top 3 signals
Day 7:  Check-in — most significant events from first week
Day 30: Milestone — stats summary, Founding Member badge
"""

import os
import logging
import json
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RESEND_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "Protocol Pulse <terminal@protocolpulse.io>"
SITE_URL = os.environ.get("SITE_URL", "https://protocolpulse.io")


def _send_email(to: str, subject: str, html: str) -> bool:
    if not RESEND_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return False
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html},
            headers={"Authorization": f"Bearer {RESEND_KEY}"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            logger.info("Onboarding email sent to %s: %s", to, subject)
            return True
        logger.error("Resend error %s for %s: %s", r.status_code, to, r.text[:200])
        return False
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def _email_wrap(body_html: str) -> str:
    return (
        '<div style="font-family:\'JetBrains Mono\',monospace;color:#E2E2EF;'
        'background:#0A0A0F;padding:32px;max-width:600px;margin:0 auto;">'
        f'{body_html}'
        '<p style="color:#374151;font-size:10px;margin-top:40px;border-top:1px solid #1a1a1a;padding-top:16px;">'
        'Protocol Pulse &middot; Sovereign Infrastructure<br>'
        f'<a href="{SITE_URL}/unsubscribe" style="color:#6b7280;">Unsubscribe</a>'
        '</p></div>'
    )


def send_day1_email(email: str, user_id: int = None) -> bool:
    """Day 1: Intelligence layer is active + top signals."""
    # Try to get today's top signals
    signals_html = ""
    try:
        from services.intelligence_service import get_signal_strength
        data = get_signal_strength()
        score = data.get("score", 0)
        label = data.get("classification", "NEUTRAL")
        signals_html = (
            f'<div style="background:#111;border-left:3px solid #dc2626;padding:16px;margin:16px 0;border-radius:4px;">'
            f'<div style="color:#dc2626;font-size:11px;letter-spacing:2px;margin-bottom:8px;">LIVE SIGNAL</div>'
            f'<div style="font-size:24px;font-weight:700;color:#fff;">{score}/100 — {label}</div>'
            f'</div>'
        )
    except Exception:
        pass

    html = _email_wrap(
        '<h1 style="color:#dc2626;font-size:16px;letter-spacing:2px;margin-bottom:24px;">YOUR INTELLIGENCE LAYER IS ACTIVE</h1>'
        '<p style="color:#e5e7eb;">Commander,</p>'
        '<p style="color:#9ca3af;">Your sovereign signal matrix is now processing data across six dimensions. '
        'Every block, every whale transfer, every narrative shift — monitored and scored in real time.</p>'
        f'{signals_html}'
        '<p style="color:#9ca3af;">Here is what Satomi found today:</p>'
        '<ul style="color:#9ca3af;padding-left:20px;">'
        '<li>Your Signal Terminal is live at <a href="' + SITE_URL + '/signal-terminal" style="color:#dc2626;">/signal-terminal</a></li>'
        '<li>The Oracle is waiting at <a href="' + SITE_URL + '/oracle-live" style="color:#dc2626;">/oracle-live</a></li>'
        '<li>Your daily brief will arrive each morning</li>'
        '</ul>'
        '<p style="margin-top:24px;">'
        '<a href="' + SITE_URL + '/intelligence" '
        'style="display:inline-block;padding:12px 28px;background:#dc2626;color:#fff;text-decoration:none;'
        'border-radius:6px;font-size:12px;letter-spacing:1px;">ENTER THE TERMINAL &rarr;</a>'
        '</p>'
    )
    return _send_email(email, "Your intelligence layer is active", html)


def send_day7_email(email: str, user_id: int = None) -> bool:
    """Day 7: First week recap."""
    html = _email_wrap(
        '<h1 style="color:#dc2626;font-size:16px;letter-spacing:2px;margin-bottom:24px;">ONE WEEK IN</h1>'
        '<p style="color:#e5e7eb;">Commander,</p>'
        '<p style="color:#9ca3af;">Seven days of sovereign intelligence. Your signal matrix has been tracking '
        'patterns that most analysts don\'t see until it\'s already priced in.</p>'
        '<div style="background:#111;border-left:3px solid #dc2626;padding:16px;margin:16px 0;border-radius:4px;">'
        '<div style="color:#dc2626;font-size:11px;letter-spacing:2px;margin-bottom:8px;">THIS WEEK</div>'
        '<p style="color:#e5e7eb;margin:0;">Check your intelligence feed for the full breakdown of this week\'s '
        'most significant signals — including whale movements, narrative shifts, and on-chain anomalies.</p>'
        '</div>'
        '<p style="color:#9ca3af;margin-top:20px;">Quick pulse check — how is the experience so far?</p>'
        '<div style="display:flex;gap:12px;margin:16px 0;font-size:24px;">'
        f'<a href="{SITE_URL}/feedback?score=5&uid={user_id}" style="text-decoration:none;">&#x1F929;</a>'
        f'<a href="{SITE_URL}/feedback?score=4&uid={user_id}" style="text-decoration:none;">&#x1F60E;</a>'
        f'<a href="{SITE_URL}/feedback?score=3&uid={user_id}" style="text-decoration:none;">&#x1F610;</a>'
        f'<a href="{SITE_URL}/feedback?score=2&uid={user_id}" style="text-decoration:none;">&#x1F615;</a>'
        f'<a href="{SITE_URL}/feedback?score=1&uid={user_id}" style="text-decoration:none;">&#x1F612;</a>'
        '</div>'
        '<p style="margin-top:24px;">'
        f'<a href="{SITE_URL}/intelligence" '
        'style="display:inline-block;padding:12px 28px;background:#dc2626;color:#fff;text-decoration:none;'
        'border-radius:6px;font-size:12px;letter-spacing:1px;">VIEW WEEKLY INTEL &rarr;</a>'
        '</p>'
    )
    return _send_email(email, "One week in. Here is what the signal caught.", html)


def send_day30_email(email: str, user_id: int = None) -> bool:
    """Day 30: Founding member milestone."""
    html = _email_wrap(
        '<h1 style="color:#dc2626;font-size:16px;letter-spacing:2px;margin-bottom:24px;">30 DAYS OF SOVEREIGN INTELLIGENCE</h1>'
        '<p style="color:#e5e7eb;">Commander,</p>'
        '<p style="color:#9ca3af;">One month. You\'ve had access to intelligence infrastructure that most '
        'of the market doesn\'t know exists. Pattern recognition. Anomaly detection. Real-time signal scoring.</p>'
        '<div style="background:#111;border:1px solid #dc2626;padding:20px;margin:20px 0;border-radius:8px;text-align:center;">'
        '<div style="font-size:12px;color:#dc2626;letter-spacing:2px;margin-bottom:12px;">DISTINCTION EARNED</div>'
        '<div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:8px;">FOUNDING MEMBER</div>'
        '<div style="font-size:11px;color:#6b7280;">You are among the first to operate at this level of signal intelligence.</div>'
        '</div>'
        '<p style="color:#9ca3af;">Your Founding Member distinction is permanently attached to your profile. '
        'As Protocol Pulse grows, founding members receive priority access to every new capability.</p>'
        '<p style="margin-top:24px;">'
        f'<a href="{SITE_URL}/signal-terminal" '
        'style="display:inline-block;padding:12px 28px;background:#dc2626;color:#fff;text-decoration:none;'
        'border-radius:6px;font-size:12px;letter-spacing:1px;">ENTER THE TERMINAL &rarr;</a>'
        '</p>'
    )
    return _send_email(email, "30 days of sovereign intelligence.", html)


def check_and_send_milestones():
    """Check all commander users for day 1/7/30 milestones and send emails.

    Called daily by APScheduler. Uses onboarding_completed_at as the anchor date.
    Stores sent milestones in UserProfile.profile_json to avoid duplicates.
    """
    try:
        from app import app, db
        import models

        with app.app_context():
            commanders = models.User.query.filter(
                models.User.subscription_tier.in_(["commander", "sovereign"]),
                models.User.onboarding_completed == True,
                models.User.onboarding_completed_at.isnot(None),
            ).all()

            now = datetime.utcnow()
            sent_count = 0

            for user in commanders:
                if not user.email:
                    continue

                anchor = user.onboarding_completed_at
                days_since = (now - anchor).days

                # Get or create profile
                profile = models.UserProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    profile = models.UserProfile(user_id=user.id, profile_json="{}")
                    db.session.add(profile)
                    db.session.flush()

                try:
                    pdata = json.loads(profile.profile_json or "{}")
                except (json.JSONDecodeError, TypeError):
                    pdata = {}

                milestones_sent = pdata.get("onboarding_milestones", [])

                # Day 1 (0-1 days)
                if days_since >= 0 and "day1" not in milestones_sent:
                    if send_day1_email(user.email, user.id):
                        milestones_sent.append("day1")
                        sent_count += 1

                # Day 7
                if days_since >= 7 and "day7" not in milestones_sent:
                    if send_day7_email(user.email, user.id):
                        milestones_sent.append("day7")
                        sent_count += 1

                # Day 30
                if days_since >= 30 and "day30" not in milestones_sent:
                    if send_day30_email(user.email, user.id):
                        milestones_sent.append("day30")
                        sent_count += 1

                pdata["onboarding_milestones"] = milestones_sent
                profile.profile_json = json.dumps(pdata)

            db.session.commit()
            logger.info("Onboarding milestone check: %d emails sent for %d commanders", sent_count, len(commanders))
            return {"sent": sent_count, "checked": len(commanders)}

    except Exception as e:
        logger.error("Milestone check failed: %s", e)
        return {"error": str(e)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        result = check_and_send_milestones()
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python onboarding_email_sequence.py check")
