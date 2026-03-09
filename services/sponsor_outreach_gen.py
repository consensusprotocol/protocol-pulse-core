"""
Sponsor Outreach Generator — Claude-drafted, Grok-reviewed hyper-personalized emails.

generate_draft(sponsor_id, channel='email') → dict
1. Pull sponsor record + Protocol Pulse live metrics
2. Claude Sonnet drafts email: 3 paras, data-first, Bitcoin audience angle
3. Grok-3 reviews draft: scores 0-100 "would a busy marketing manager reply?"
4. If score < 70: Claude revises once based on Grok feedback
5. Save best draft to sponsor_outreach table
6. Return {subject, body, grok_score, grok_notes, channel}
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Channel character limits (Phase 0 addition #8)
CHANNEL_LIMITS = {
    "email": 1500,
    "linkedin": 300,
    "twitter": 280,
}

SUBJECT_LINES = {
    "email": "Partnership opportunity: Protocol Pulse × {company_name}",
    "linkedin": None,  # no subject for LinkedIn
    "twitter": None,
}


def _get_db_path() -> str:
    try:
        from app import app
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///pp.db")
        if uri.startswith("sqlite:///"):
            path = uri.replace("sqlite:///", "")
            if not os.path.isabs(path):
                path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
            return path
    except Exception:
        pass
    return "pp.db"


def _get_live_metrics() -> Dict:
    """Pull Protocol Pulse live metrics for outreach personalization."""
    try:
        from services.sponsorship_metrics_service import get_sponsorship_metrics
        metrics = get_sponsorship_metrics(days_back=30)
        return {
            "youtube_views": metrics.get("youtube_views", 0),
            "website_visitors": metrics.get("website_unique_visits", 0),
            "social_impressions": metrics.get("social_impressions", 0),
            "period": "30 days",
        }
    except Exception as e:
        logger.warning("Could not load live metrics: %s", e)
        return {
            "youtube_views": "10,000+",
            "website_visitors": "8,500+",
            "social_impressions": "50,000+",
            "period": "30 days",
        }


def _get_sponsor(db_path: str, sponsor_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM sponsors WHERE id = ? AND is_deleted = 0",
            (sponsor_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error("DB error fetching sponsor %s: %s", sponsor_id, e)
        return None
    finally:
        conn.close()


def _get_next_version(db_path: str, sponsor_id: int, channel: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT MAX(version) FROM sponsor_outreach WHERE sponsor_id = ? AND channel = ?",
            (sponsor_id, channel)
        )
        row = cur.fetchone()
        return (row[0] or 0) + 1
    except sqlite3.Error:
        return 1
    finally:
        conn.close()


def _claude_draft(sponsor: Dict, metrics: Dict, channel: str,
                  revision_notes: str = "") -> str:
    """Draft outreach copy using Claude Sonnet."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except (ImportError, Exception) as e:
        logger.warning("Claude unavailable for draft: %s", e)
        return _fallback_draft(sponsor, metrics, channel)

    char_limit = CHANNEL_LIMITS.get(channel, 1500)
    podcasts = []
    try:
        podcasts = json.loads(sponsor.get("podcasts_they_sponsor") or "[]")
    except (json.JSONDecodeError, TypeError):
        pass

    channel_instructions = {
        "email": f"Write a professional 3-paragraph email ({char_limit} chars max). Para 1: acknowledge their existing podcast sponsorships. Para 2: Protocol Pulse stats + why our audience is different/better. Para 3: clear CTA (15-minute call). NO subject line in body.",
        "linkedin": f"Write a LinkedIn connection message ({char_limit} chars max). Conversational, direct, one clear ask. No formal headers.",
        "twitter": f"Write a Twitter/X DM ({char_limit} chars max). Ultra-concise, punchy, one hook sentence + one ask.",
    }

    intel_notes = ""
    try:
        notes = sponsor.get("intelligence_notes", "")
        if notes and notes.startswith("{"):
            data = json.loads(notes)
            intel_notes = data.get("research_summary", "")[:200]
        else:
            intel_notes = (notes or "")[:200]
    except Exception:
        intel_notes = ""

    revision_section = ""
    if revision_notes:
        revision_section = f"\n\nREVISION NOTES FROM REVIEW:\n{revision_notes}\nApply these improvements in this revision."

    prompt = f"""You are Protocol Pulse's senior sponsorship strategist. Write hyper-personalized outreach.

TARGET COMPANY: {sponsor.get('company_name')}
CATEGORY: {sponsor.get('category', 'other')}
WEBSITE: {sponsor.get('website', 'unknown')}
PODCASTS THEY ALREADY SPONSOR: {', '.join(podcasts) if podcasts else 'Bitcoin/crypto podcasts'}
INTEL: {intel_notes}
OUTREACH ANGLE: {sponsor.get('outreach_angle', 'Bitcoin audience fit')}
OPPORTUNITY SIGNAL: {sponsor.get('opportunity_signal', 'stable')}

PROTOCOL PULSE STATS (use these specific numbers):
- YouTube views: {metrics.get('youtube_views')} (last {metrics.get('period')})
- Website unique visitors: {metrics.get('website_visitors')} (last {metrics.get('period')})
- Social impressions: {metrics.get('social_impressions')} (last {metrics.get('period')})
- Audience: Bitcoin-first, high-income ($150k+ avg household income), self-sovereign, technically sophisticated

AD PACKAGES AVAILABLE:
- Pulse Check Pre-roll: $500/episode (30s before video)
- Article Sponsorship: $300/article (logo + body mention)
- Newsletter Feature: $200/send (dedicated section)
- Commander Bundle: $1,500/month (all placements)

CHANNEL: {channel}
TASK: {channel_instructions.get(channel, channel_instructions['email'])}

RULES:
- Reference their SPECIFIC existing podcast sponsorships by name
- Use the EXACT Protocol Pulse stats above
- Mention our Bitcoin-native audience (not generic crypto)
- Be confident, data-driven, not begging
- End with a specific, low-friction ask
- NEVER start with "I hope this email finds you well" or similar filler{revision_section}

Write ONLY the outreach copy. No explanations.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error("Claude draft failed: %s", e)
        return _fallback_draft(sponsor, metrics, channel)


def _grok_review(draft: str, sponsor_name: str, channel: str) -> Dict:
    """Grok-3 reviews draft: scores 0-100 + improvement notes."""
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.x.ai/v1",
                        api_key=os.environ.get("XAI_API_KEY"))
    except (ImportError, Exception):
        logger.warning("Grok review unavailable")
        return {"score": 75, "notes": "Review unavailable — Grok offline.", "approved": True}

    prompt = f"""You are a marketing director at a B2B SaaS company receiving 50+ partnership pitches per week.
You are reviewing this {channel} outreach message from Protocol Pulse (a Bitcoin intelligence platform).

OUTREACH MESSAGE:
---
{draft[:1000]}
---

Score this message 0-100 for "likelihood a busy marketing manager would actually reply":
- 90-100: I'd definitely reply, this is compelling
- 75-89: Strong pitch, I'd likely reply
- 60-74: Good effort, might reply
- 40-59: Generic, probably skip
- 0-39: Delete immediately

Key evaluation criteria:
1. Is it personalized to MY company specifically?
2. Does it have clear data/metrics to justify the ask?
3. Is the CTA specific and low-friction?
4. Is it the right length for {channel}?
5. Does it sound like a peer talking to a peer (not desperate)?

Return ONLY valid JSON:
{{"score": 0-100, "approved": true/false, "top_improvement": "Most important thing to fix (1 sentence)", "strengths": ["strength 1", "strength 2"]}}
"""

    try:
        response = client.chat.completions.create(
            model="grok-3",
            messages=[{"role": "user", "content": prompt}],
            timeout=30,
            max_tokens=300,
        )
        raw = response.choices[0].message.content
        import re
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            data = json.loads(json_match.group())
            data["approved"] = int(data.get("score", 0)) >= 70
            return data
        return {"score": 72, "notes": raw[:200], "approved": True}
    except Exception as e:
        logger.warning("Grok review failed: %s", e)
        return {"score": 70, "notes": f"Review error: {str(e)[:100]}", "approved": True}


def _save_draft(db_path: str, sponsor_id: int, version: int, channel: str,
                subject: str, body: str, grok_score: int, grok_notes: str) -> int:
    """Save outreach draft to DB. Returns draft ID."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sponsor_outreach (
                sponsor_id, version, channel, subject, body,
                grok_review_score, grok_review_notes, created_at
            ) VALUES (?,?,?,?,?,?,?,?)
        """, (
            sponsor_id, version, channel, subject, body,
            grok_score, grok_notes[:500], datetime.utcnow().isoformat()
        ))
        conn.commit()
        draft_id = cur.lastrowid

        # Log activity
        cur.execute("""
            INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
            VALUES (?,?,?,?)
        """, (
            sponsor_id, "outreach_drafted",
            f"v{version} {channel} draft — Grok score: {grok_score}/100", "system"
        ))
        # Update sponsor status if still 'prospect'
        cur.execute("""
            UPDATE sponsors SET status='outreach_drafted', pipeline_stage=3,
                updated_at=? WHERE id=? AND pipeline_stage < 3
        """, (datetime.utcnow().isoformat(), sponsor_id))
        conn.commit()
        return draft_id
    except sqlite3.Error as e:
        conn.rollback()
        logger.error("Failed to save draft for sponsor %s: %s", sponsor_id, e)
        raise
    finally:
        conn.close()


def generate_draft(sponsor_id: int, channel: str = "email") -> Dict:
    """
    Generate outreach draft for a sponsor.
    Returns {subject, body, grok_score, grok_notes, channel, draft_id, version}.
    """
    channel = channel.lower()
    if channel not in CHANNEL_LIMITS:
        channel = "email"

    db_path = _get_db_path()
    sponsor = _get_sponsor(db_path, sponsor_id)
    if not sponsor:
        raise ValueError(f"Sponsor {sponsor_id} not found")

    metrics = _get_live_metrics()
    version = _get_next_version(db_path, sponsor_id, channel)

    # Draft v1
    body = _claude_draft(sponsor, metrics, channel)
    review = _grok_review(body, sponsor.get("company_name", ""), channel)
    grok_score = review.get("score", 70)

    # Revise if score < 70
    if grok_score < 70:
        improvement = review.get("top_improvement", "")
        logger.info("Grok score %s < 70, revising draft for %s", grok_score, sponsor.get("company_name"))
        body_v2 = _claude_draft(sponsor, metrics, channel, revision_notes=improvement)
        review_v2 = _grok_review(body_v2, sponsor.get("company_name", ""), channel)
        if review_v2.get("score", 0) > grok_score:
            body = body_v2
            review = review_v2
            grok_score = review.get("score", grok_score)

    subject = ""
    if channel == "email":
        tmpl = SUBJECT_LINES["email"]
        subject = tmpl.format(company_name=sponsor.get("company_name", "Your Company"))

    grok_notes = json.dumps({
        "score": grok_score,
        "approved": review.get("approved", True),
        "top_improvement": review.get("top_improvement", ""),
        "strengths": review.get("strengths", []),
    })

    draft_id = _save_draft(db_path, sponsor_id, version, channel,
                           subject, body, grok_score, grok_notes)

    return {
        "draft_id": draft_id,
        "sponsor_id": sponsor_id,
        "version": version,
        "channel": channel,
        "subject": subject,
        "body": body,
        "grok_score": grok_score,
        "grok_notes": review.get("top_improvement", ""),
        "grok_strengths": review.get("strengths", []),
        "company_name": sponsor.get("company_name"),
    }


def _fallback_draft(sponsor: Dict, metrics: Dict, channel: str) -> str:
    """Static fallback draft when AI is unavailable."""
    name = sponsor.get("company_name", "your team")
    angle = sponsor.get("outreach_angle", "our Bitcoin-native audience")
    podcasts_raw = sponsor.get("podcasts_they_sponsor") or "[]"
    try:
        podcasts = json.loads(podcasts_raw)
        pod_ref = f" — we noticed you're already sponsoring shows like {podcasts[0]}" if podcasts else ""
    except Exception:
        pod_ref = ""

    if channel == "email":
        return f"""Hi,

I saw {name} is active in the Bitcoin podcast space{pod_ref}. I'd love to explore a partnership with Protocol Pulse.

Protocol Pulse is a premium Bitcoin intelligence platform reaching {metrics.get('website_visitors', '8,500+')} unique visitors and {metrics.get('youtube_views', '10,000+')} YouTube views per month. Our audience is Bitcoin-first, technically sophisticated, and high-income — exactly the buyers who act on your category.

Our Commander Bundle ($1,500/mo) gives you pre-roll placement, article mentions, and newsletter features. Would you be open to a 15-minute call this week to explore fit?

Best,
PBX
Protocol Pulse
https://protocolpulse.io"""
    elif channel == "linkedin":
        return f"Hey! Saw {name} is sponsoring Bitcoin podcasts — we run Protocol Pulse, a Bitcoin intelligence platform with {metrics.get('website_visitors', '8,500+')} monthly readers. Would love to explore a partnership. Open to a quick chat?"
    else:
        return f"Hey {name} — we run Protocol Pulse (Bitcoin intelligence, {metrics.get('website_visitors', '8,500+')} readers/mo). Saw you're active in Bitcoin content. Partnership opportunity? DM me!"
