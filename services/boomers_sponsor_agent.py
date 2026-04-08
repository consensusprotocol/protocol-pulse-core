"""
Bitcoin Boomers Sponsor Agent
==============================
CRM and outreach automation for The Bitcoin Boomers podcast.
Standalone SQLite-backed sponsor pipeline with 3 tiers and drip sequences.

Hosts: Gary Leland, Lawrence Lepard, Bob Burnett
Audience: Boomers/Gen X — high net worth, decision-makers, business owners
Revenue split: 70/30 (Mel Sands / Protocol Pulse)

CLI:
  python3 services/boomers_sponsor_agent.py --list
  python3 services/boomers_sponsor_agent.py --tiers
  python3 services/boomers_sponsor_agent.py --draft "Swan Bitcoin"
  python3 services/boomers_sponsor_agent.py --metrics
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "boomers_sponsors.db")
FROM_EMAIL = "sponsors@protocolpulse.io"
RESEND_BASE = "https://api.resend.com"
RESEND_TIMEOUT = 30

# ── Tiers ────────────────────────────────────────────────────────────────────

TIERS = [
    {
        "name": "Boomer Signal",
        "price_usd": 750,
        "includes": [
            "Pre-roll mention (15s)",
            "Show notes link",
        ],
    },
    {
        "name": "Boomer Broadcast",
        "price_usd": 1500,
        "includes": [
            "Pre-roll mention (15s)",
            "Mid-roll mention (60s)",
            "Newsletter feature",
            "Social media post",
        ],
    },
    {
        "name": "Boomer Full Stack",
        "price_usd": 3000,
        "includes": [
            "Pre-roll mention (15s)",
            "Mid-roll mention (60s)",
            "Newsletter feature",
            "Social media post",
            "Dedicated 2-min sponsor segment",
            "Guest spot opportunity",
        ],
    },
]

# ── Drip Sequence ────────────────────────────────────────────────────────────

SPONSOR_SEQUENCE = [
    {
        "step": 0, "day": 0, "type": "intro",
        "subject_template": "Quick question about {company} + Bitcoin Boomers audience",
    },
    {
        "step": 1, "day": 4, "type": "data",
        "subject_template": "The Bitcoin Boomers audience — why it matters for {company}",
    },
    {
        "step": 2, "day": 10, "type": "value",
        "subject_template": "{company} + The Bitcoin Boomers?",
    },
    {
        "step": 3, "day": 18, "type": "breakup",
        "subject_template": "Last thought — pilot sponsorship on Bitcoin Boomers?",
    },
]

# ── Default Prospects (20 Bitcoin companies targeting affluent demographics) ─

DEFAULT_PROSPECTS = [
    {"company": "Swan Bitcoin", "email": "", "category": "exchange", "website": "swanbitcoin.com"},
    {"company": "Unchained", "email": "", "category": "custody", "website": "unchained.com"},
    {"company": "River Financial", "email": "", "category": "exchange", "website": "river.com"},
    {"company": "Casa", "email": "", "category": "custody", "website": "keys.casa"},
    {"company": "Foundation Devices", "email": "", "category": "hardware_wallet", "website": "foundationdevices.com"},
    {"company": "Fold App", "email": "", "category": "rewards", "website": "foldapp.com"},
    {"company": "Strike", "email": "", "category": "payments", "website": "strike.me"},
    {"company": "BitKey", "email": "", "category": "hardware_wallet", "website": "bitkey.world"},
    {"company": "Multisig", "email": "", "category": "custody", "website": "multisig.com"},
    {"company": "AnchorWatch", "email": "", "category": "insurance", "website": "anchorwatch.com"},
    {"company": "Theya", "email": "", "category": "custody", "website": "theya.us"},
    {"company": "Bitcoin Magazine", "email": "", "category": "media", "website": "bitcoinmagazine.com"},
    {"company": "Bitcoin Well", "email": "", "category": "exchange", "website": "bitcoinwell.com"},
    {"company": "Relai", "email": "", "category": "exchange", "website": "relai.app"},
    {"company": "Coinkite", "email": "", "category": "hardware_wallet", "website": "coinkite.com"},
    {"company": "Knox Custody", "email": "", "category": "custody", "website": "knoxcustody.com"},
    {"company": "Onramp Bitcoin", "email": "", "category": "custody", "website": "onrampbitcoin.com"},
    {"company": "Oshi", "email": "", "category": "rewards", "website": "oshi.tech"},
    {"company": "Bisq", "email": "", "category": "exchange", "website": "bisq.network"},
    {"company": "Start9", "email": "", "category": "node", "website": "start9.com"},
]


# ── Database ─────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boomers_sponsors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            domain TEXT,
            email TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            status TEXT DEFAULT 'prospect',
            deal_value REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            sent_at TEXT,
            subject TEXT,
            body TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boomers_outreach_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_email TEXT,
            recipient_name TEXT,
            subject TEXT,
            body TEXT,
            sequence_step INTEGER DEFAULT 0,
            resend_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


# ── API Helpers ──────────────────────────────────────────────────────────────

def _grok_generate(prompt: str, max_tokens: int = 2000) -> Optional[str]:
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
    key = os.environ.get("RESEND_API_KEY", "")
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


# ── Email Generation ─────────────────────────────────────────────────────────

def generate_sponsor_email(company: str, contact_name: str, category: str, sequence_step: int) -> Dict[str, str]:
    step = SPONSOR_SEQUENCE[min(sequence_step, len(SPONSOR_SEQUENCE) - 1)]
    subject = step["subject_template"].format(company=company)

    host_line = "Hosted by Lawrence Lepard (investment manager, billions AUM), Bob Burnett (mining CEO, Barefoot Mining), and Gary Leland (Bitcoin pioneer since 2013)"
    audience_line = "Your brand in front of high-net-worth Bitcoin adopters — Boomers and Gen X decision-makers with real purchasing power"
    tagline = "The podcast your parents will actually listen to"

    prompts = {
        "intro": f"""Write a cold outreach email from The Bitcoin Boomers podcast to {contact_name} at {company} ({category}).

The Bitcoin Boomers is a weekly Bitcoin podcast for the grown-ups:
- {host_line}
- 47+ episodes, growing YouTube channel
- Audience: Boomers/Gen X demographic — high net worth, business owners, decision-makers
- "{tagline}"
- {audience_line}

This is step 1 (intro). Write 3-4 paragraphs:
1. Mention you noticed {company} is active in the Bitcoin space and resonates with serious adopters
2. Introduce The Bitcoin Boomers — who the hosts are and why the audience is uniquely valuable
3. Mention one specific placement (pre-roll mention, mid-roll segment, or dedicated sponsor segment)
4. End with a soft CTA — "Worth a 15-minute call?"

Note: Pricing reflects full production value (media partnership with Protocol Pulse).

Tone: Confident peer-to-peer. Not salesy. Bitcoin-native. Speak to business people. Short paragraphs.
Output: Just the email body in clean HTML (<p> tags). No subject line.""",

        "data": f"""Write follow-up email #2 to {contact_name} at {company}.
Previous email introduced The Bitcoin Boomers podcast. This one leads with AUDIENCE DATA.

Key stats to weave in:
- {host_line}
- Audience demographic: 45-70 age range, median net worth $1M+
- 47+ episodes, consistent weekly publishing
- Growing YouTube channel with high engagement
- Listeners are business owners, retirees with investable assets, and professional investors
- The demographic that actually has money to spend on {category} products

Write 3 paragraphs: lead with a demographic hook, explain why Boomer/Gen X Bitcoin adopters are the most valuable audience for {company}, end with CTA.
Tone: Data-driven but human. Speak to ROI.
Output: Just the email body in clean HTML (<p> tags).""",

        "value": f"""Write follow-up email #3 to {contact_name} at {company}.
This email pitches a specific sponsorship tier on The Bitcoin Boomers podcast.

Available tiers:
- $750/mo "Boomer Signal": Pre-roll mention (15s) + show notes link
- $1,500/mo "Boomer Broadcast": Pre-roll + mid-roll + newsletter + social post
- $3,000/mo "Boomer Full Stack": All above + dedicated 2-min segment + guest spot opportunity

Write 2-3 paragraphs: recommend the tier that best fits a {category} company like {company}, explain the value, soft close.
Tone: Enthusiastic but not desperate. Business-to-business.
Output: Just the email body in clean HTML (<p> tags).""",

        "breakup": f"""Write a "breakup" email #4 to {contact_name} at {company}.
This is the last email in the sequence for The Bitcoin Boomers podcast sponsorship.

Write 2 short paragraphs:
1. Acknowledge they're busy, express this is the last follow-up
2. Leave with a specific offer: "If timing works better next quarter, reply 'later' and I'll circle back"

Tone: Respectful, no guilt, genuine. Keep it under 100 words.
Output: Just the email body in clean HTML (<p> tags).""",
    }

    prompt = prompts.get(step["type"], prompts["intro"])
    body_html = _grok_generate(prompt)

    if not body_html:
        body_html = f"""<p>Hi {contact_name},</p>
<p>I'm reaching out on behalf of The Bitcoin Boomers — the weekly podcast hosted by Lawrence Lepard (investment manager),
Bob Burnett (mining CEO), and Gary Leland (Bitcoin pioneer). Our audience is Boomers and Gen X — high-net-worth
decision-makers who are serious about Bitcoin and have real purchasing power in the {category} space.</p>
<p>Would a 15-minute call make sense to explore a sponsorship fit?</p>
<p>Best,<br>Bitcoin Boomers Partnerships<br>sponsors@protocolpulse.io</p>"""

    return {"subject": subject, "body": body_html}


# ── CRM Operations ───────────────────────────────────────────────────────────

def seed_default_prospects() -> int:
    db = _get_db()
    existing = db.execute("SELECT COUNT(*) FROM boomers_sponsors").fetchone()[0]
    if existing > 0:
        db.close()
        return 0
    count = 0
    for p in DEFAULT_PROSPECTS:
        db.execute(
            "INSERT INTO boomers_sponsors (company, domain, email, category, status) VALUES (?, ?, ?, ?, 'prospect')",
            (p["company"], p["website"], p["email"], p["category"]),
        )
        count += 1
    db.commit()
    db.close()
    logger.info("Seeded %d Boomers sponsor prospects", count)
    return count


def list_sponsors(status_filter: str = None) -> List[Dict]:
    db = _get_db()
    if status_filter:
        rows = db.execute(
            "SELECT * FROM boomers_sponsors WHERE status = ? ORDER BY id", (status_filter,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM boomers_sponsors ORDER BY id").fetchall()

    results = []
    for r in rows:
        emails_sent = db.execute(
            "SELECT COUNT(*) FROM boomers_outreach_emails WHERE recipient_email = ?",
            (r["email"],),
        ).fetchone()[0] if r["email"] else 0
        results.append({
            "id": r["id"],
            "company": r["company"],
            "domain": r["domain"] or "",
            "email": r["email"] or "(no email)",
            "category": r["category"] or "general",
            "status": r["status"],
            "emails_sent": emails_sent,
            "deal_value": r["deal_value"] or 0,
            "last_contact": r["sent_at"] or "never",
            "notes": r["notes"] or "",
        })
    db.close()
    return results


def add_sponsor(company: str, email: str, category: str = "general", domain: str = "", notes: str = "") -> Dict:
    if not domain:
        domain = email.split("@")[1] if "@" in email else company.lower().replace(" ", "") + ".com"
    db = _get_db()
    existing = db.execute("SELECT id FROM boomers_sponsors WHERE domain = ?", (domain,)).fetchone()
    if existing:
        db.close()
        return {"error": f"Prospect with domain {domain} already exists (ID: {existing['id']})"}
    cur = db.execute(
        "INSERT INTO boomers_sponsors (company, domain, email, category, status, notes) VALUES (?, ?, ?, ?, 'prospect', ?)",
        (company, domain, email, category, notes),
    )
    db.commit()
    row_id = cur.lastrowid
    db.close()
    logger.info("Added Boomers sponsor prospect: %s (%s)", company, email)
    return {"id": row_id, "company": company, "email": email, "status": "prospect"}


def draft_outreach(company_name: str) -> Dict:
    db = _get_db()
    row = db.execute(
        "SELECT * FROM boomers_sponsors WHERE company LIKE ?", (f"%{company_name}%",)
    ).fetchone()
    if not row:
        db.close()
        return {"error": f"No prospect found matching '{company_name}'"}

    emails_sent = db.execute(
        "SELECT COUNT(*) FROM boomers_outreach_emails WHERE recipient_email = ?",
        (row["email"],),
    ).fetchone()[0] if row["email"] else 0
    db.close()

    step = min(emails_sent, len(SPONSOR_SEQUENCE) - 1)
    contact_name = row["company"].split()[0] if row["company"] else "there"

    email_data = generate_sponsor_email(
        company=row["company"],
        contact_name=contact_name,
        category=row["category"] or "Bitcoin",
        sequence_step=step,
    )

    return {
        "prospect_id": row["id"],
        "company": row["company"],
        "to": row["email"] or "(no email set)",
        "sequence_step": step,
        "subject": email_data["subject"],
        "body": email_data["body"],
        "note": "Draft only — not sent. Use --send to execute outreach.",
    }


def run_daily_outreach() -> Dict:
    db = _get_db()
    results = {"sent": 0, "skipped": 0, "errors": 0}

    prospects = db.execute(
        "SELECT * FROM boomers_sponsors WHERE status IN ('prospect', 'contacted') AND email != ''"
    ).fetchall()

    for prospect in prospects:
        try:
            sent_count = db.execute(
                "SELECT COUNT(*) FROM boomers_outreach_emails WHERE recipient_email = ?",
                (prospect["email"],),
            ).fetchone()[0]

            if sent_count >= len(SPONSOR_SEQUENCE):
                continue

            step = SPONSOR_SEQUENCE[sent_count]
            if prospect["sent_at"]:
                last_sent = datetime.fromisoformat(prospect["sent_at"])
                days_since = (datetime.utcnow() - last_sent).days
                if days_since < step["day"]:
                    results["skipped"] += 1
                    continue

            contact_name = prospect["company"].split()[0] if prospect["company"] else "there"
            email_data = generate_sponsor_email(
                company=prospect["company"],
                contact_name=contact_name,
                category=prospect["category"] or "Bitcoin",
                sequence_step=sent_count,
            )

            resend_id = _send_via_resend(prospect["email"], email_data["subject"], email_data["body"])

            if resend_id:
                now = datetime.utcnow().isoformat()
                db.execute(
                    "INSERT INTO boomers_outreach_emails (recipient_email, recipient_name, subject, body, sequence_step, resend_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (prospect["email"], prospect["company"], email_data["subject"], email_data["body"], sent_count, resend_id),
                )
                new_status = "contacted" if prospect["status"] == "prospect" else prospect["status"]
                db.execute(
                    "UPDATE boomers_sponsors SET sent_at = ?, subject = ?, body = ?, status = ? WHERE id = ?",
                    (now, email_data["subject"], email_data["body"], new_status, prospect["id"]),
                )
                db.commit()
                results["sent"] += 1
            else:
                results["errors"] += 1

        except Exception as e:
            logger.error("Boomers outreach error for %s: %s", prospect["company"], e)
            results["errors"] += 1

    db.close()
    logger.info("Boomers sponsor outreach complete: %s", results)
    return results


def get_metrics() -> Dict:
    db = _get_db()
    total = db.execute("SELECT COUNT(*) FROM boomers_sponsors").fetchone()[0]
    by_status = {}
    for row in db.execute("SELECT status, COUNT(*) as cnt FROM boomers_sponsors GROUP BY status").fetchall():
        by_status[row["status"]] = row["cnt"]
    total_emails = db.execute("SELECT COUNT(*) FROM boomers_outreach_emails").fetchone()[0]
    by_step = {}
    for row in db.execute("SELECT sequence_step, COUNT(*) as cnt FROM boomers_outreach_emails GROUP BY sequence_step").fetchall():
        by_step[f"step_{row['sequence_step']}"] = row["cnt"]
    db.close()
    return {
        "total_prospects": total,
        "by_status": by_status,
        "total_emails_sent": total_emails,
        "emails_by_step": by_step,
        "tiers": [{"name": t["name"], "price": f"${t['price_usd']}/mo"} for t in TIERS],
        "revenue_split": "70/30 (Mel Sands / Protocol Pulse)",
        "generated_at": datetime.utcnow().isoformat(),
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Bitcoin Boomers Sponsor Agent — CRM & Outreach",
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
                        help="Show Bitcoin Boomers sponsorship tier pricing")
    parser.add_argument("--metrics", action="store_true",
                        help="Show CRM pipeline metrics")
    parser.add_argument("--seed", action="store_true",
                        help="Seed default Bitcoin company prospects")
    parser.add_argument("--send", action="store_true",
                        help="Run daily sponsor drip campaign (sends emails)")

    args = parser.parse_args()

    if args.list or args.list_status:
        prospects = list_sponsors(status_filter=args.list_status)
        if not prospects:
            print("No sponsor prospects found. Run --seed to add defaults.")
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
            body_text = re.sub(r'<[^>]+>', '', result['body']).strip()
            body_text = re.sub(r'\n{3,}', '\n\n', body_text)
            print(body_text)
            print(f"\n{result['note']}")

    elif args.tiers:
        print(f"\n{'='*60}")
        print("THE BITCOIN BOOMERS — SPONSORSHIP TIERS")
        print(f"{'='*60}")
        for t in TIERS:
            print(f"\n  {t['name']} — ${t['price_usd']:,}/mo")
            for item in t["includes"]:
                print(f"    - {item}")
        print(f"\nHosts:")
        print(f"  Lawrence Lepard — Investment manager, billions AUM")
        print(f"  Bob Burnett — CEO, Barefoot Mining")
        print(f"  Gary Leland — Bitcoin pioneer since 2013")
        print(f"\nAudience: Boomers/Gen X — high net worth, decision-makers")
        print(f"Revenue split: 70/30 (Mel Sands / Protocol Pulse)")

    elif args.metrics:
        m = get_metrics()
        print(f"\n{'='*60}")
        print("THE BITCOIN BOOMERS — PIPELINE METRICS")
        print(f"{'='*60}")
        print(f"  Total prospects: {m['total_prospects']}")
        for status, count in m['by_status'].items():
            print(f"    {status}: {count}")
        print(f"  Total emails sent: {m['total_emails_sent']}")
        for step, count in m['emails_by_step'].items():
            print(f"    {step}: {count}")
        print(f"\n  Revenue split: {m['revenue_split']}")
        print(f"  Generated: {m['generated_at']}")

    elif args.seed:
        n = seed_default_prospects()
        if n == 0:
            print("Prospects already seeded.")
        else:
            print(f"Seeded {n} Boomers sponsor prospects")

    elif args.send:
        r = run_daily_outreach()
        print(f"Boomers outreach: {r}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
