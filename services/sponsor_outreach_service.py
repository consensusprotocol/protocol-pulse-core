"""
Sponsor Outreach & Guest Booking Service
==========================================
Two automated drip campaigns:
  1. Sponsor acquisition — 4-step sequence targeting Bitcoin podcast advertisers
  2. Guest booking — 3-step sequence for Cypherpunkd podcast guests

Email generation: Grok (XAI) for personalized copy
Email delivery: Resend API (same infra as newsletter)
"""

import os
import json
import uuid
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
FROM_EMAIL = "sponsors@protocolpulse.io"
RESEND_BASE = "https://api.resend.com"
RESEND_TIMEOUT = 30

SPONSOR_SEQUENCE = [
    {
        "step": 0, "day": 0, "type": "intro",
        "subject_template": "Quick question about {company} + Bitcoin audience",
    },
    {
        "step": 1, "day": 4, "type": "data",
        "subject_template": "Protocol Pulse audience data (970k+ monthly reach)",
    },
    {
        "step": 2, "day": 10, "type": "value",
        "subject_template": "{company} + Cypherpunkd?",
    },
    {
        "step": 3, "day": 18, "type": "breakup",
        "subject_template": "Last thought — pilot sponsorship?",
    },
]

GUEST_SEQUENCE = [
    {
        "step": 0, "day": 0, "type": "intro",
        "subject_template": "Cypherpunkd episode idea — {topic_angle}",
    },
    {
        "step": 1, "day": 7, "type": "followup",
        "subject_template": "Following up — {guest_name} on Cypherpunkd",
    },
    {
        "step": 2, "day": 21, "type": "last_touch",
        "subject_template": "Last note — would love to have you on",
    },
]

# Default guest list seeded into DB on first run
DEFAULT_GUESTS = [
    {"name": "Lawrence Lepard", "handle": "@LawrenceLepard", "topics": ["Austrian economics", "sound money", "macro outlook"]},
    {"name": "Bob Burnett", "handle": "@boaboromisa", "topics": ["Bitcoin mining", "Barefoot Mining", "energy"]},
    {"name": "Charlie Shrem", "handle": "@CharlieShrem", "topics": ["Bitcoin OG stories", "early days", "entrepreneurship"]},
    {"name": "CJ Konstantinos", "handle": "@caboromeister", "topics": ["Bitcoin culture", "grassroots adoption"]},
    {"name": "Natalie Brunell", "handle": "@nataboromell", "topics": ["Bitcoin journalism", "women in Bitcoin", "mainstream adoption"]},
    {"name": "Luke Dashjr", "handle": "@LukeDashjr", "topics": ["Bitcoin Core development", "BIP proposals", "decentralization"]},
    {"name": "Peter McCormack", "handle": "@PeterMcCormack", "topics": ["What Bitcoin Did", "UK perspective", "football + Bitcoin"]},
    {"name": "Marty Bent", "handle": "@MartyBent", "topics": ["TFTC", "energy", "freedom tech"]},
    {"name": "Stephan Livera", "handle": "@stephanlivera", "topics": ["Austrian economics", "Lightning Network", "Bitcoin education"]},
    {"name": "Preston Pysh", "handle": "@PrestonPysh", "topics": ["macro investing", "Lightning", "value-for-value"]},
    {"name": "Guy Swann", "handle": "@TheGuySwann", "topics": ["Bitcoin Audible", "Bitcoin philosophy", "deep reads"]},
    {"name": "Lyn Alden", "handle": "@LynAldenContact", "topics": ["macro analysis", "fiscal dominance", "Bitcoin as savings"]},
    {"name": "Michael Saylor", "handle": "@saboromaylor", "topics": ["Bitcoin treasury strategy", "corporate adoption", "MicroStrategy"]},
    {"name": "Saifedean Ammous", "handle": "@saaboromifedean", "topics": ["The Bitcoin Standard", "Austrian economics", "fiat critique"]},
    {"name": "Matt Odell", "handle": "@ODELL", "topics": ["privacy", "FOSS", "sovereignty", "Citadel Dispatch"]},
    {"name": "Adam Back", "handle": "@adam3us", "topics": ["hashcash", "Blockstream", "cypherpunk history"]},
    {"name": "Greg Foss", "handle": "@FossGregfoss", "topics": ["credit markets", "Bitcoin as insurance", "bond analysis"]},
    {"name": "Gabor Gurbacs", "handle": "@gaborgurbacs", "topics": ["ETFs", "institutional Bitcoin", "tokenization"]},
    {"name": "Jeff Booth", "handle": "@JeffBooth", "topics": ["deflation", "Price of Tomorrow", "technology + abundance"]},
    {"name": "Parker Lewis", "handle": "@parkeraboromis", "topics": ["Gradually Then Suddenly", "Zaprite", "Bitcoin education"]},
]


def _resend_api_key() -> str:
    return os.environ.get("RESEND_API_KEY", "")


def _grok_generate(prompt: str, max_tokens: int = 2000) -> Optional[str]:
    """Generate text via Grok API."""
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        logger.warning("XAI_API_KEY not set — cannot generate outreach copy")
        return None
    try:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "grok-3-latest", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        logger.error("Grok API error %d: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("Grok request failed: %s", e)
    return None


def _send_via_resend(to_email: str, subject: str, html_body: str) -> Optional[str]:
    """Send email via Resend API. Returns message ID or None."""
    key = _resend_api_key()
    if not key:
        logger.warning("RESEND_API_KEY not set — email not sent to %s", to_email)
        return None
    try:
        r = requests.post(
            f"{RESEND_BASE}/emails",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "from": FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
            timeout=RESEND_TIMEOUT,
        )
        if r.status_code in (200, 201):
            msg_id = r.json().get("id", "")
            logger.info("Email sent to %s — Resend ID: %s", to_email, msg_id)
            return msg_id
        logger.error("Resend error %d: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("Resend request failed: %s", e)
    return None


# ── Sponsor Email Generation ────────────────────────────────────────────────

def generate_sponsor_email(company: str, contact_name: str, category: str, sequence_step: int) -> Dict[str, str]:
    """Generate a personalized sponsor outreach email using Grok.
    Returns dict with 'subject' and 'body' (HTML).
    """
    step = SPONSOR_SEQUENCE[min(sequence_step, len(SPONSOR_SEQUENCE) - 1)]
    subject = step["subject_template"].format(company=company)

    prompts = {
        "intro": f"""Write a cold outreach email from Protocol Pulse to {contact_name} at {company} ({category}).

Protocol Pulse is the "ESPN SportsCenter for Bitcoin" — premium daily intelligence platform.
- 970K+ monthly audience reach across web, newsletter, podcast (Cypherpunkd), and video
- Audience: Bitcoin builders, investors, operators (85% male, 25-55, high income, high net worth)
- Content: Daily articles, Cypherpunkd podcast, Pulse Check videos, daily newsletter, live terminal
- Events: BitcoinDay Naples, BTC in DC at the Kennedy Center

This is step 1 (intro). Write 3-4 paragraphs:
1. Mention you noticed {company} is active in the Bitcoin space and advertising on podcasts
2. Briefly intro Protocol Pulse and why our audience is a perfect fit for {category} products
3. Mention one specific placement (newsletter sponsorship, homepage banner, or podcast read)
4. End with a soft CTA — "Worth a 15-minute call?"

Tone: Confident peer-to-peer. Not salesy. Bitcoin-native. Short paragraphs.
Output: Just the email body in clean HTML (<p> tags). No subject line.""",

        "data": f"""Write follow-up email #2 to {contact_name} at {company}.
Previous email introduced Protocol Pulse. This one leads with DATA.

Key stats to weave in:
- 970K+ monthly reach (web + social + newsletter + podcast)
- 45% open rate on newsletter (industry avg: 22%)
- 89% of audience holds Bitcoin
- Average reader net worth: $500K+
- 3.2 min average article read time
- Top referral sources: Twitter/X, direct, Nostr

Write 3 paragraphs: lead with a stat hook, explain what this means for {company}'s marketing spend, end with CTA.
Tone: Data-driven but human. Short sentences.
Output: Just the email body in clean HTML (<p> tags).""",

        "value": f"""Write follow-up email #3 to {contact_name} at {company}.
This email pitches a specific collaboration: sponsoring the Cypherpunkd podcast.

Cypherpunkd is Protocol Pulse's weekly long-form podcast:
- Host-read ads (authentic, never skipped)
- 15K+ downloads per episode
- Guests include top Bitcoin voices
- Available: pre-roll (15s), mid-roll (60s), post-roll (30s)

Write 2-3 paragraphs: pitch the podcast sponsorship specifically for {company}, give a package hint ($2K-5K/month range), soft close.
Tone: Enthusiastic but not desperate. Peer-to-peer.
Output: Just the email body in clean HTML (<p> tags).""",

        "breakup": f"""Write a "breakup" email #4 to {contact_name} at {company}.
This is the last email in the sequence. Classic breakup technique — express genuine respect, leave the door open.

Write 2 short paragraphs:
1. Acknowledge they're busy, express this is the last follow-up
2. Leave with a specific offer: "If timing works better in Q3, reply 'later' and I'll circle back"

Tone: Respectful, no guilt, genuine. Keep it under 100 words.
Output: Just the email body in clean HTML (<p> tags).""",
    }

    prompt = prompts.get(step["type"], prompts["intro"])
    body_html = _grok_generate(prompt)

    if not body_html:
        # Fallback static template
        body_html = f"""<p>Hi {contact_name},</p>
<p>I lead partnerships at Protocol Pulse — the daily Bitcoin intelligence platform reaching 970K+ monthly.
Our audience is Bitcoin builders, investors, and operators with high purchasing intent in the {category} space.</p>
<p>Would a 15-minute call make sense to explore a fit?</p>
<p>Best,<br>Protocol Pulse Partnerships<br>sponsors@protocolpulse.io</p>"""

    return {"subject": subject, "body": body_html}


# ── Guest Email Generation ──────────────────────────────────────────────────

def generate_guest_email(guest_name: str, topic_angle: str, sequence_step: int) -> Dict[str, str]:
    """Generate a personalized guest booking email using Grok.
    Returns dict with 'subject' and 'body' (HTML).
    """
    step = GUEST_SEQUENCE[min(sequence_step, len(GUEST_SEQUENCE) - 1)]
    subject = step["subject_template"].format(guest_name=guest_name, topic_angle=topic_angle)

    prompts = {
        "intro": f"""Write an email inviting {guest_name} to be a guest on the Cypherpunkd podcast.

Cypherpunkd is Protocol Pulse's flagship Bitcoin podcast:
- Long-form conversations (60-90 min)
- Focus: Bitcoin conviction, sovereignty, cypherpunk ethos
- Audience: serious Bitcoiners, not crypto tourists
- Distribution: Apple, Spotify, YouTube, Fountain, RSS

Topic angle for this episode: {topic_angle}

Write 3 short paragraphs:
1. Reference their recent work or known positions — show you've done homework
2. Pitch the specific episode angle: "{topic_angle}" — explain why NOW is the right time
3. Logistics: remote (Riverside.fm), 60-90 min, flexible scheduling

Tone: Genuine admiration. Not fanboy. Peer-to-peer. Brief.
Output: Just the email body in clean HTML (<p> tags).""",

        "followup": f"""Write a gentle follow-up email to {guest_name} about the Cypherpunkd podcast invitation.

Previous email pitched an episode on: {topic_angle}

Write 2 paragraphs:
1. Brief reference to previous email, acknowledge they're busy
2. Add a new angle or timely hook (reference something happening in Bitcoin right now)

Tone: Warm, not pushy. Under 80 words.
Output: Just the email body in clean HTML (<p> tags).""",

        "last_touch": f"""Write a final gentle touch email to {guest_name} about Cypherpunkd.

Write 2 short paragraphs:
1. "Just one more note" — express that you'd genuinely love to have them on when timing works
2. Leave the door open: "No pressure at all. If a future episode makes sense, just reply whenever."

Tone: Gracious, zero pressure. Under 60 words.
Output: Just the email body in clean HTML (<p> tags).""",
    }

    prompt = prompts.get(step["type"], prompts["intro"])
    body_html = _grok_generate(prompt)

    if not body_html:
        body_html = f"""<p>Hi {guest_name},</p>
<p>I'd love to have you on Cypherpunkd — Protocol Pulse's Bitcoin podcast. We're planning an episode on "{topic_angle}"
and your perspective would be perfect.</p>
<p>It's a 60-90 min remote conversation via Riverside.fm. Flexible scheduling. Would you be open to it?</p>
<p>Best,<br>Protocol Pulse<br>podcast@protocolpulse.io</p>"""

    return {"subject": subject, "body": body_html}


# ── Daily Outreach Runner ───────────────────────────────────────────────────

def run_daily_sponsor_outreach() -> Dict:
    """Pull sponsor contacts needing their next sequence step today, generate and send emails."""
    from app import db
    from models import SponsorOutreach, OutreachEmail

    results = {"sent": 0, "skipped": 0, "errors": 0}
    today = datetime.utcnow().date()

    # Find prospects that need next outreach
    prospects = SponsorOutreach.query.filter(
        SponsorOutreach.status.in_(["prospect", "outreach_drafted", "contacted"]),
        SponsorOutreach.email.isnot(None),
        SponsorOutreach.email != "",
    ).all()

    for prospect in prospects:
        try:
            # Determine which step they're on
            sent_count = OutreachEmail.query.filter_by(
                outreach_type="sponsor",
                recipient_email=prospect.email,
            ).count()

            if sent_count >= len(SPONSOR_SEQUENCE):
                continue  # Sequence complete

            step = SPONSOR_SEQUENCE[sent_count]
            # Check if it's time for this step
            if prospect.sent_at:
                days_since = (datetime.utcnow() - prospect.sent_at).days
                if days_since < step["day"]:
                    results["skipped"] += 1
                    continue

            # Generate email
            contact_name = prospect.company.split()[0] if prospect.company else "there"
            email_data = generate_sponsor_email(
                company=prospect.company,
                contact_name=contact_name,
                category=prospect.category or "Bitcoin",
                sequence_step=sent_count,
            )

            # Send via Resend
            resend_id = _send_via_resend(prospect.email, email_data["subject"], email_data["body"])

            if resend_id:
                # Log the send
                log = OutreachEmail(
                    outreach_type="sponsor",
                    recipient_email=prospect.email,
                    recipient_name=prospect.company,
                    subject=email_data["subject"],
                    body=email_data["body"],
                    sequence_step=sent_count,
                    resend_id=resend_id,
                )
                db.session.add(log)

                # Update prospect status
                prospect.sent_at = datetime.utcnow()
                prospect.subject = email_data["subject"]
                prospect.body = email_data["body"]
                if prospect.status == "prospect":
                    prospect.status = "contacted"

                db.session.commit()
                results["sent"] += 1
            else:
                results["errors"] += 1

        except Exception as e:
            logger.error("Sponsor outreach error for %s: %s", prospect.company, e)
            db.session.rollback()
            results["errors"] += 1

    logger.info("Sponsor outreach complete: %s", results)
    return results


def run_daily_guest_outreach() -> Dict:
    """Send next-step guest booking emails."""
    from app import db
    from models import GuestOutreach, OutreachEmail

    results = {"sent": 0, "skipped": 0, "errors": 0}

    guests = GuestOutreach.query.filter(
        GuestOutreach.status.in_(["identified", "emailed"]),
        GuestOutreach.email.isnot(None),
        GuestOutreach.email != "",
    ).all()

    for guest in guests:
        try:
            sent_count = OutreachEmail.query.filter_by(
                outreach_type="guest",
                recipient_email=guest.email,
            ).count()

            if sent_count >= len(GUEST_SEQUENCE):
                continue

            step = GUEST_SEQUENCE[sent_count]
            if guest.last_outreach_at:
                days_since = (datetime.utcnow() - guest.last_outreach_at).days
                if days_since < step["day"]:
                    results["skipped"] += 1
                    continue

            # Parse first topic from JSON array
            topics = []
            if guest.topics:
                try:
                    topics = json.loads(guest.topics)
                except (json.JSONDecodeError, TypeError):
                    topics = [guest.topics]
            topic_angle = topics[0] if topics else "Bitcoin and sovereignty"

            email_data = generate_guest_email(
                guest_name=guest.name,
                topic_angle=topic_angle,
                sequence_step=sent_count,
            )

            resend_id = _send_via_resend(guest.email, email_data["subject"], email_data["body"])

            if resend_id:
                log = OutreachEmail(
                    outreach_type="guest",
                    recipient_email=guest.email,
                    recipient_name=guest.name,
                    subject=email_data["subject"],
                    body=email_data["body"],
                    sequence_step=sent_count,
                    resend_id=resend_id,
                )
                db.session.add(log)

                guest.last_outreach_at = datetime.utcnow()
                if guest.status == "identified":
                    guest.status = "emailed"

                db.session.commit()
                results["sent"] += 1
            else:
                results["errors"] += 1

        except Exception as e:
            logger.error("Guest outreach error for %s: %s", guest.name, e)
            db.session.rollback()
            results["errors"] += 1

    logger.info("Guest outreach complete: %s", results)
    return results


def seed_default_guests():
    """Seed the guest pipeline with default targets if empty."""
    from app import db
    from models import GuestOutreach

    if GuestOutreach.query.first():
        return 0

    count = 0
    for g in DEFAULT_GUESTS:
        guest = GuestOutreach(
            name=g["name"],
            handle=g["handle"],
            topics=json.dumps(g["topics"]),
            status="identified",
        )
        db.session.add(guest)
        count += 1

    db.session.commit()
    logger.info("Seeded %d default guests", count)
    return count


# ── Default Sponsor Prospects ────────────────────────────────────────────────

DEFAULT_SPONSORS = [
    {"company": "River Financial", "email": "", "category": "exchange", "website": "river.com"},
    {"company": "Swan Bitcoin", "email": "", "category": "exchange", "website": "swanbitcoin.com"},
    {"company": "Unchained Capital", "email": "", "category": "custody", "website": "unchained.com"},
    {"company": "Foundation Devices", "email": "", "category": "hardware_wallet", "website": "foundationdevices.com"},
    {"company": "Coinkite", "email": "", "category": "hardware_wallet", "website": "coinkite.com"},
    {"company": "Start9", "email": "", "category": "node", "website": "start9.com"},
    {"company": "Blockstream", "email": "", "category": "infrastructure", "website": "blockstream.com"},
    {"company": "Zaprite", "email": "", "category": "payments", "website": "zaprite.com"},
    {"company": "Fold App", "email": "", "category": "rewards", "website": "foldapp.com"},
    {"company": "Strike", "email": "", "category": "payments", "website": "strike.me"},
    {"company": "Bitkey", "email": "", "category": "hardware_wallet", "website": "bitkey.world"},
    {"company": "Compass Mining", "email": "", "category": "mining", "website": "compassmining.io"},
    {"company": "Riot Platforms", "email": "", "category": "mining", "website": "riotplatforms.com"},
    {"company": "Marathon Digital", "email": "", "category": "mining", "website": "mara.com"},
    {"company": "Braiins", "email": "", "category": "mining_software", "website": "braiins.com"},
    {"company": "Mempool.space", "email": "", "category": "explorer", "website": "mempool.space"},
    {"company": "BTCPay Server", "email": "", "category": "payments", "website": "btcpayserver.org"},
    {"company": "Wasabi Wallet", "email": "", "category": "privacy", "website": "wasabiwallet.io"},
    {"company": "Bull Bitcoin", "email": "", "category": "exchange", "website": "bullbitcoin.com"},
    {"company": "CoinCards", "email": "", "category": "gift_cards", "website": "coincards.com"},
]


def seed_default_sponsors():
    """Seed the sponsor pipeline with default Bitcoin company prospects if empty."""
    from app import db
    from models import SponsorOutreach

    if SponsorOutreach.query.first():
        return 0

    count = 0
    for s in DEFAULT_SPONSORS:
        prospect = SponsorOutreach(
            company=s["company"],
            domain=s["website"],
            email=s["email"],
            category=s["category"],
            status="prospect",
        )
        db.session.add(prospect)
        count += 1

    db.session.commit()
    logger.info("Seeded %d default sponsor prospects", count)
    return count


def list_sponsors(status_filter: str = None) -> List[Dict]:
    """List all sponsor prospects, optionally filtered by status."""
    from models import SponsorOutreach, OutreachEmail

    query = SponsorOutreach.query.order_by(SponsorOutreach.created_at.desc())
    if status_filter:
        query = query.filter(SponsorOutreach.status == status_filter)

    results = []
    for s in query.all():
        emails_sent = OutreachEmail.query.filter_by(
            outreach_type="sponsor",
            recipient_email=s.email,
        ).count() if s.email else 0

        results.append({
            "id": s.id,
            "company": s.company,
            "domain": s.domain,
            "email": s.email or "(no email)",
            "category": s.category or "general",
            "status": s.status,
            "emails_sent": emails_sent,
            "deal_value": s.deal_value,
            "last_contact": s.sent_at.strftime("%Y-%m-%d") if s.sent_at else "never",
            "notes": s.notes or "",
        })
    return results


def add_sponsor(company: str, email: str, category: str = "general", domain: str = "", notes: str = "") -> Dict:
    """Add a new sponsor prospect to the CRM."""
    from app import db
    from models import SponsorOutreach

    if not domain:
        # Extract domain from email
        domain = email.split("@")[1] if "@" in email else company.lower().replace(" ", "") + ".com"

    existing = SponsorOutreach.query.filter_by(domain=domain).first()
    if existing:
        return {"error": f"Prospect with domain {domain} already exists (ID: {existing.id})"}

    prospect = SponsorOutreach(
        company=company,
        domain=domain,
        email=email,
        category=category,
        status="prospect",
        notes=notes,
    )
    db.session.add(prospect)
    db.session.commit()
    logger.info("Added sponsor prospect: %s (%s)", company, email)
    return {"id": prospect.id, "company": company, "email": email, "status": "prospect"}


def draft_outreach(company_name: str) -> Dict:
    """Generate a draft outreach email for a sponsor prospect (does not send)."""
    from models import SponsorOutreach, OutreachEmail

    prospect = SponsorOutreach.query.filter(
        SponsorOutreach.company.ilike(f"%{company_name}%")
    ).first()

    if not prospect:
        return {"error": f"No prospect found matching '{company_name}'"}

    # Determine sequence step
    emails_sent = OutreachEmail.query.filter_by(
        outreach_type="sponsor",
        recipient_email=prospect.email,
    ).count() if prospect.email else 0

    step = min(emails_sent, len(SPONSOR_SEQUENCE) - 1)
    contact_name = prospect.company.split()[0] if prospect.company else "there"

    email_data = generate_sponsor_email(
        company=prospect.company,
        contact_name=contact_name,
        category=prospect.category or "Bitcoin",
        sequence_step=step,
    )

    return {
        "prospect_id": prospect.id,
        "company": prospect.company,
        "to": prospect.email or "(no email set)",
        "sequence_step": step,
        "subject": email_data["subject"],
        "body": email_data["body"],
        "note": "Draft only — not sent. Use 'sponsor-outreach' to send.",
    }


# ── Campaign Metrics ────────────────────────────────────────────────────────

def get_campaign_metrics(campaign_id: int, days_back: int = 30) -> Dict:
    """Get analytics for a specific sponsor campaign."""
    from app import db
    from models import SponsorCampaign, AdImpression, AdClick, PageView
    from sqlalchemy import func

    campaign = SponsorCampaign.query.get(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}

    since = datetime.utcnow() - timedelta(days=days_back)

    # Impressions
    total_impressions = AdImpression.query.filter(
        AdImpression.campaign_id == campaign_id,
        AdImpression.created_at >= since,
    ).count()

    # Clicks
    total_clicks = AdClick.query.filter(
        AdClick.campaign_id == campaign_id,
        AdClick.created_at >= since,
    ).count()

    # CTR
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

    # Unique visitors during campaign period
    unique_visitors = db.session.query(
        func.count(func.distinct(PageView.session_id))
    ).filter(PageView.created_at >= since).scalar() or 0

    # Daily impressions breakdown
    daily_impressions = db.session.query(
        func.date(AdImpression.created_at).label("day"),
        func.count(AdImpression.id).label("count"),
    ).filter(
        AdImpression.campaign_id == campaign_id,
        AdImpression.created_at >= since,
    ).group_by(func.date(AdImpression.created_at)).order_by("day").all()

    # Daily clicks
    daily_clicks = db.session.query(
        func.date(AdClick.created_at).label("day"),
        func.count(AdClick.id).label("count"),
    ).filter(
        AdClick.campaign_id == campaign_id,
        AdClick.created_at >= since,
    ).group_by(func.date(AdClick.created_at)).order_by("day").all()

    # Top articles where ad appeared
    top_pages = db.session.query(
        AdImpression.page_path,
        func.count(AdImpression.id).label("views"),
    ).filter(
        AdImpression.campaign_id == campaign_id,
        AdImpression.created_at >= since,
    ).group_by(AdImpression.page_path).order_by(func.count(AdImpression.id).desc()).limit(10).all()

    # Placement breakdown
    placement_stats = {}
    if campaign.placement:
        placement_stats[campaign.placement] = {"impressions": total_impressions, "clicks": total_clicks}

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "sponsor_name": campaign.sponsor.name if campaign.sponsor else "Unknown",
        "placement": campaign.placement,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "status": campaign.status,
        "period_days": days_back,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "ctr": round(ctr, 2),
        "unique_reach": unique_visitors,
        "daily_impressions": [{"date": str(d.day), "count": d.count} for d in daily_impressions],
        "daily_clicks": [{"date": str(d.day), "count": d.count} for d in daily_clicks],
        "top_pages": [{"path": p.page_path, "views": p.views} for p in top_pages],
        "placement_breakdown": placement_stats,
        "generated_at": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Protocol Pulse Sponsor Agent — CRM & Outreach",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--list", action="store_true", help="List all sponsor prospects")
    parser.add_argument("--list-status", type=str, metavar="STATUS",
                        help="Filter prospects by status (prospect/contacted/replied/closed)")
    parser.add_argument("--add", nargs=2, metavar=("COMPANY", "EMAIL"),
                        help='Add a new prospect: --add "Company Name" "email@company.com"')
    parser.add_argument("--add-category", type=str, default="general",
                        help="Category for --add (exchange/wallet/mining/custody/payments/etc)")
    parser.add_argument("--draft", type=str, metavar="COMPANY",
                        help='Generate draft outreach email: --draft "Company Name"')
    parser.add_argument("--tiers", action="store_true",
                        help="Show sponsorship tier pricing based on current audience metrics")
    parser.add_argument("--metrics", action="store_true",
                        help="Show aggregate audience metrics for sponsorship deck")
    parser.add_argument("--seed-sponsors", action="store_true",
                        help="Seed default Bitcoin company prospects")
    parser.add_argument("--seed-guests", action="store_true",
                        help="Seed default podcast guest targets")
    parser.add_argument("--sponsor-outreach", action="store_true",
                        help="Run daily sponsor drip campaign (sends emails)")
    parser.add_argument("--guest-outreach", action="store_true",
                        help="Run daily guest booking drip campaign (sends emails)")

    args = parser.parse_args()

    # Route to app context — add project root, core/, and services/ to resolve all imports
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    services_dir = os.path.join(project_root, "services")
    core_dir = os.path.join(project_root, "core")
    for p in [project_root, services_dir, core_dir]:
        if p not in sys.path:
            sys.path.insert(0, p)
    from app import app

    with app.app_context():
        if args.list or args.list_status:
            prospects = list_sponsors(status_filter=args.list_status)
            if not prospects:
                print("No sponsor prospects found. Run --seed-sponsors to add defaults.")
            else:
                print(f"\n{'ID':>4}  {'Company':<22} {'Email':<30} {'Category':<15} {'Status':<12} {'Sent':>4}  {'Last Contact':<12}  Notes")
                print("-" * 140)
                for p in prospects:
                    notes_preview = (p['notes'][:30] + '...') if len(p['notes']) > 30 else p['notes']
                    print(f"{p['id']:>4}  {p['company']:<22} {p['email']:<30} {p['category']:<15} {p['status']:<12} {p['emails_sent']:>4}  {p['last_contact']:<12}  {notes_preview}")
                print(f"\nTotal: {len(prospects)} prospects")

        elif args.add:
            result = add_sponsor(
                company=args.add[0],
                email=args.add[1],
                category=args.add_category,
            )
            if "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                print(f"Added: {result['company']} ({result['email']}) — ID: {result['id']}")

        elif args.draft:
            result = draft_outreach(args.draft)
            if "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                print(f"\n{'='*60}")
                print(f"DRAFT OUTREACH — {result['company']}")
                print(f"{'='*60}")
                print(f"To: {result['to']}")
                print(f"Step: {result['sequence_step']} of {len(SPONSOR_SEQUENCE)}")
                print(f"Subject: {result['subject']}")
                print(f"\n--- Body ---")
                # Strip HTML for terminal display
                import re
                body_text = re.sub(r'<[^>]+>', '', result['body']).strip()
                body_text = re.sub(r'\n{3,}', '\n\n', body_text)
                print(body_text)
                print(f"\n{result['note']}")

        elif args.tiers:
            from sponsorship_metrics_service import get_sponsorship_tiers
            tiers = get_sponsorship_tiers()
            print(f"\n{'='*60}")
            print("PROTOCOL PULSE — SPONSORSHIP TIERS")
            print(f"{'='*60}")
            for t in tiers["tiers"]:
                print(f"\n  {t['name']} — ${t['price_usd']}/mo")
                for item in t["includes"]:
                    print(f"    - {item}")
                print(f"    Est. CPM: ${t['estimated_cpm']:.2f}")
            print(f"\nAudience basis:")
            print(f"  Newsletter subscribers: {tiers['audience']['newsletter_subscribers']:,}")
            print(f"  Monthly site visitors: {tiers['audience']['monthly_site_visitors']:,}")
            print(f"  Social reach: {tiers['audience']['social_reach']:,}")
            print(f"\nGenerated: {tiers['generated_at']}")

        elif args.metrics:
            from sponsorship_metrics_service import get_sponsorship_metrics
            from app import db
            metrics = get_sponsorship_metrics(db_session=db.session, days_back=30)
            print(f"\n{'='*60}")
            print("PROTOCOL PULSE — AUDIENCE METRICS (30-day)")
            print(f"{'='*60}")
            print(f"  YouTube views: {metrics['youtube_views']:,} (source: {metrics['youtube_source']})")
            print(f"  Website unique visits: {metrics['website_unique_visits']:,} (source: {metrics['website_source']})")
            print(f"  Social impressions: {metrics['social_impressions']:,} (source: {metrics['social_source']})")
            print(f"\nGenerated: {metrics['generated_at']}")

        elif args.seed_sponsors:
            n = seed_default_sponsors()
            print(f"Seeded {n} sponsor prospects")

        elif args.seed_guests:
            n = seed_default_guests()
            print(f"Seeded {n} guests")

        elif args.sponsor_outreach:
            r = run_daily_sponsor_outreach()
            print(f"Sponsor outreach: {r}")

        elif args.guest_outreach:
            r = run_daily_guest_outreach()
            print(f"Guest outreach: {r}")

        else:
            parser.print_help()
