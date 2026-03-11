"""
Email Writer — Sponsor Agent V2
================================
Drafts cold outreach emails for sponsor prospects using Claude API.
Does NOT send — drafts only, for human review.
"""

import os
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You write cold outreach emails for Protocol Pulse, a Bitcoin intelligence media company. "
    "Platform: protocolpulse.io - daily AI-generated Bitcoin news, Oracle AI briefings, "
    "Pulse Check video episodes. "
    "Audience: Bitcoin investors, cypherpunks, mining professionals. Growing platform. "
    "Write short (100-130 words), direct, non-cringe outreach emails. No buzzwords."
)


def draft_email(prospect: dict) -> dict:
    """
    Draft an outreach email for a prospect.

    Args:
        prospect: dict with 'company' and optional 'category' keys

    Returns:
        dict with 'subject' and 'body' keys
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set — cannot draft emails")
        return {"subject": "", "body": ""}

    company = prospect.get("company", "Unknown")
    description = prospect.get("category", "Bitcoin company")

    user_prompt = (
        f"Write outreach to {company} about sponsoring Protocol Pulse. "
        f"They do: {description}"
    )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text.strip()

        # Parse subject from first line if it starts with "Subject:"
        lines = text.split("\n", 1)
        if lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
        else:
            subject = f"Partnership opportunity — Protocol Pulse x {company}"
            body = text

        return {"subject": subject, "body": body}

    except Exception as exc:
        logger.error("Email draft failed for %s: %s", company, exc)
        return {"subject": "", "body": ""}


def draft_emails_for_prospects() -> int:
    """
    Draft emails for all prospects with status='prospect'.
    Updates status to 'draft' after drafting.

    Returns:
        Number of emails drafted
    """
    from app import db
    from models import SponsorOutreach

    prospects = SponsorOutreach.query.filter_by(status="prospect", is_deleted=False).all()
    drafted = 0

    for outreach in prospects:
        prospect_data = {
            "company": outreach.company,
            "category": outreach.category or "Bitcoin company",
        }

        result = draft_email(prospect_data)
        if result["subject"] and result["body"]:
            outreach.subject = result["subject"]
            outreach.body = result["body"]
            outreach.status = "draft"
            drafted += 1

            from models import SponsorActivityLog
            log = SponsorActivityLog(
                outreach_id=outreach.id,
                action="email_drafted",
                old_status="prospect",
                new_status="draft",
                details=f"Subject: {result['subject'][:100]}",
            )
            db.session.add(log)

            logger.info("Drafted email for %s (id=%d)", outreach.company, outreach.id)
        else:
            logger.warning("Empty draft for %s (id=%d) — skipping", outreach.company, outreach.id)

    try:
        db.session.commit()
        logger.info("Drafted %d emails", drafted)
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to save drafts: %s", exc)
        drafted = 0

    return drafted
