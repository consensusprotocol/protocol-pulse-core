"""
Sponsor Radar V2 — Grok-powered prospect scanner for Protocol Pulse.
Phase 1: Scans 20 Bitcoin podcasts for active sponsors (last 90 days).
Phase 2: Grok deep research per prospect (company profile, ad spend signals, multi-source fusion).
Phase 3: Claude scores each prospect 0-100 for Protocol Pulse fit + deal probability.
Phase 4: Persists to sponsors table with activity log.

Run: python3 -m services.sponsor_radar_v2 --scan
Cron: Sundays at 2 AM UTC.
"""

import json
import logging
import os
import re
import socket
import sqlite3
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BITCOIN_PODCASTS = [
    "What Bitcoin Did", "Bitcoin Fundamentals", "The Bitcoin Standard Podcast",
    "Stephan Livera Podcast", "Tales from the Crypt", "Citadel Dispatch",
    "Bitcoin Audible", "The Pomp Podcast", "Unchained Podcast", "Bankless",
    "We Study Billionaires", "The Investor's Podcast", "Peter McCormack",
    "BTC Sessions Podcast", "Bitcoin Magazine Podcast", "The Bitcoin Layer",
    "Rabbit Hole Recap", "TFTC", "Your Friendly Neighborhood Bitcoin Podcast",
    "Bitcoin Bottom Line"
]

CATEGORY_MAP = {
    "wallet": "hardware_wallet",
    "ledger": "hardware_wallet",
    "trezor": "hardware_wallet",
    "coldcard": "hardware_wallet",
    "exchange": "exchange",
    "trading": "exchange",
    "coinbase": "exchange",
    "kraken": "exchange",
    "gemini": "exchange",
    "vpn": "vpn",
    "nordvpn": "vpn",
    "expressvpn": "vpn",
    "fintech": "fintech",
    "lending": "fintech",
    "loan": "fintech",
    "credit": "fintech",
    "health": "health",
    "supplement": "health",
    "insurance": "other",
    "mining": "other",
    "node": "other",
}

# Category conversion rate baselines (from industry data)
CATEGORY_BASE_RATES = {
    "hardware_wallet": 0.18,
    "exchange": 0.14,
    "fintech": 0.12,
    "vpn": 0.10,
    "health": 0.09,
    "other": 0.07,
}


# ---------------------------------------------------------------------------
# Email validation helper
# ---------------------------------------------------------------------------

def validate_email_deliverability(email: str) -> bool:
    """Light validation: format check + MX record lookup."""
    if not email or "@" not in email:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        return False
    try:
        domain = email.split("@")[1]
        socket.getaddrinfo(domain, None, socket.AF_UNSPEC, socket.SOCK_DGRAM)
        return True
    except (socket.gaierror, IndexError):
        return False


# ---------------------------------------------------------------------------
# Deal probability calculator (Phase 0 addition #7)
# ---------------------------------------------------------------------------

def compute_deal_probability(
    relevance_score: int,
    category: str,
    opportunity_signal: str,
    days_since_contact: Optional[int],
    grok_score_signals: int = 0,
) -> int:
    """
    Compute deal_probability_pct (0-100) from multiple signals.
    Uses category base rates + score weighting + signal momentum.
    """
    base_rate = CATEGORY_BASE_RATES.get(category, 0.07)
    # Normalize relevance_score (0-100) → multiplier
    score_mult = (relevance_score / 100) * 2.5  # max 2.5x base rate
    prob = base_rate * score_mult

    # Signal momentum boost
    if opportunity_signal == "growing":
        prob *= 1.35
    elif opportunity_signal == "declining":
        prob *= 0.65

    # Grok signal boost (0-10 scale passed in)
    prob += grok_score_signals * 0.005

    # Recency decay: if never contacted, no penalty; if contacted > 30d ago, small decay
    if days_since_contact is not None and days_since_contact > 30:
        prob *= max(0.5, 1.0 - (days_since_contact - 30) / 200)

    return min(99, max(1, int(prob * 100)))


# ---------------------------------------------------------------------------
# Grok research engine
# ---------------------------------------------------------------------------

def _grok_client():
    """Returns an xAI OpenAI-compatible client or None."""
    try:
        from openai import OpenAI
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            logger.warning("XAI_API_KEY not set — Grok research offline")
            return None
        return OpenAI(base_url="https://api.x.ai/v1", api_key=api_key)
    except ImportError:
        logger.warning("openai package not installed — Grok offline")
        return None


def _claude_client():
    """Returns an Anthropic client or None."""
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("anthropic package not installed")
        return None


def grok_scan_podcasts(progress_callback=None) -> List[Dict]:
    """
    Phase 1+2: Ask Grok to identify active sponsors across Bitcoin podcasts
    with multi-source signal fusion.
    Returns list of prospect dicts.
    """
    client = _grok_client()
    if not client:
        return _fallback_prospects()

    if progress_callback:
        progress_callback("scan_start", "Initiating Grok deep research scan...")

    prompt = f"""You are a B2B sales intelligence analyst specializing in the Bitcoin/crypto podcast ecosystem.

Search for and identify companies that are ACTIVELY sponsoring Bitcoin/crypto podcasts RIGHT NOW (last 90 days).
Target podcasts include: {', '.join(BITCOIN_PODCASTS[:12])}, and others.

For each sponsor company found, provide structured intelligence:

Return a JSON array (max 25 companies) with this exact structure:
{{
  "companies": [
    {{
      "company_name": "Company Name",
      "website": "https://...",
      "category": "hardware_wallet|exchange|fintech|vpn|health|other",
      "contact_email": "partnerships@company.com or null",
      "contact_name": "Name or null",
      "estimated_monthly_spend": "$5k-$15k/mo",
      "podcasts_they_sponsor": ["Pod Name 1", "Pod Name 2"],
      "opportunity_signal": "growing|stable|declining",
      "outreach_angle": "One sentence hook for why Bitcoin audience is perfect for them",
      "signal_sources": {{
        "podcast_ads_detected": true,
        "recent_funding": false,
        "hiring_growth": false,
        "competitor_ads": false,
        "confidence_score": 75
      }},
      "intelligence_summary": "2-3 sentences of key intel about their ad strategy and Bitcoin audience fit"
    }}
  ]
}}

IMPORTANT:
- Only include companies you have REAL evidence are sponsoring Bitcoin content recently
- Do not hallucinate companies or metrics
- Focus on companies likely to convert: they're already spending on crypto/Bitcoin content
- Include their actual spend signals (episode count, frequency)
- Note if they're growing their crypto ad budget or pulling back
"""

    try:
        response = client.chat.completions.create(
            model="grok-3",
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
            max_tokens=4000,
        )
        raw = response.choices[0].message.content
        if progress_callback:
            progress_callback("scan_raw", f"Grok returned {len(raw)} chars of intelligence")

        # Extract JSON
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            data = json.loads(json_match.group())
            companies = data.get("companies", [])
            if progress_callback:
                progress_callback("scan_found", f"Found {len(companies)} active sponsors")
            return companies
        else:
            logger.warning("Could not parse Grok JSON response")
            return _fallback_prospects()
    except Exception as e:
        logger.error("Grok scan error: %s", e, exc_info=True)
        if progress_callback:
            progress_callback("scan_error", f"Grok error: {str(e)[:100]}. Using fallback data.")
        return _fallback_prospects()


def grok_deep_research(company_name: str, website: str, progress_callback=None) -> Dict:
    """
    Phase 2 deep research: Grok investigates a specific company for ad spend signals.
    Returns enriched intelligence dict.
    """
    client = _grok_client()
    if not client:
        return {"notes": f"Grok offline. Manual research needed for {company_name}.", "score": 50}

    prompt = f"""Search for recent news and intelligence about {company_name} (website: {website}).

Provide a structured intelligence report:

1. RECENT NEWS: Any funding rounds, product launches, or expansions in last 6 months?
2. AD SPEND SIGNALS: Evidence they're actively buying podcast/media ads? Which shows?
3. BITCOIN AUDIENCE FIT: How well does their product fit a Bitcoin-first, high-income, self-sovereign audience?
4. DECISION MAKER SIGNALS: Any signals about their marketing budget or team size?
5. OPPORTUNITY SIGNAL: Is their crypto ad spend growing, stable, or declining based on evidence?
6. RED FLAGS: Any controversies, regulatory issues, or reasons to avoid?

Return JSON:
{{
  "research_summary": "3-4 sentence executive summary",
  "recent_news": ["news item 1", "news item 2"],
  "ad_spend_signals": ["signal 1", "signal 2"],
  "bitcoin_audience_fit": "High/Medium/Low — reason",
  "opportunity_signal": "growing|stable|declining",
  "red_flags": ["flag 1"] or [],
  "estimated_monthly_spend": "$X-$Yk/mo",
  "recommended_package": "Pulse Check Pre-roll|Article Sponsorship|Commander Bundle",
  "confidence_score": 0-100
}}

Be specific and factual. If uncertain, say so. Do not hallucinate metrics.
"""

    try:
        response = client.chat.completions.create(
            model="grok-3",
            messages=[{"role": "user", "content": prompt}],
            timeout=45,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            return json.loads(json_match.group())
        return {"notes": raw[:500], "score": 50}
    except Exception as e:
        logger.warning("Grok deep research failed for %s: %s", company_name, e)
        return {"notes": f"Research failed: {str(e)[:100]}", "score": 40}


def claude_score_prospect(company_data: Dict, progress_callback=None) -> Tuple[int, str]:
    """
    Phase 3: Claude scores prospect 0-100 for Protocol Pulse fit.
    Returns (score, outreach_angle).
    """
    client = _claude_client()
    if not client:
        return 60, "Bitcoin audience alignment — high-income, self-sovereign users"

    prompt = f"""You are Protocol Pulse's sponsorship intelligence engine.

Protocol Pulse is a premium Bitcoin intelligence platform:
- Audience: Bitcoin-first, high-income, technically sophisticated, self-sovereign
- Content: Daily briefings, market analysis, on-chain data, Bitcoin news
- Reach: Growing podcast + website with engaged crypto-native audience

Score this sponsor prospect 0-100 for Protocol Pulse partnership fit:

COMPANY: {company_data.get('company_name', 'Unknown')}
CATEGORY: {company_data.get('category', 'other')}
WEBSITE: {company_data.get('website', 'unknown')}
PODCASTS THEY SPONSOR: {json.dumps(company_data.get('podcasts_they_sponsor', []))}
INTELLIGENCE: {company_data.get('intelligence_summary', '')[:300]}
OPPORTUNITY SIGNAL: {company_data.get('opportunity_signal', 'stable')}

Scoring rubric:
90-100: Perfect fit — already proven Bitcoin/crypto spend, product fits our audience exactly
75-89: Strong fit — adjacent crypto spend or audience overlap is high
60-74: Good fit — general tech/finance product, audience has clear use case
40-59: Moderate fit — stretch category but possible angle exists
0-39: Poor fit — wrong audience, wrong category, or red flags

Respond with ONLY valid JSON:
{{"score": 0-100, "angle": "One compelling sentence hook for outreach", "reasoning": "1-2 sentences why"}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        data = json.loads(text.strip())
        return int(data.get("score", 60)), data.get("angle", "Bitcoin audience fit")
    except Exception as e:
        logger.warning("Claude scoring failed: %s", e)
        return 60, "Bitcoin audience alignment — high-income, self-sovereign users"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_db_path() -> str:
    from app import app
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///pp.db")
    if uri.startswith("sqlite:///"):
        path = uri.replace("sqlite:///", "")
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
        return path
    return "pp.db"


def ensure_tables() -> None:
    """Create sponsor tables if they don't exist (migration-safe)."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS sponsors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                category TEXT DEFAULT 'other',
                website TEXT,
                contact_email TEXT,
                contact_name TEXT,
                contact_linkedin TEXT,
                estimated_monthly_spend TEXT,
                podcasts_they_sponsor TEXT,
                relevance_score INTEGER DEFAULT 0,
                deal_probability_pct INTEGER DEFAULT 0,
                opportunity_signal TEXT DEFAULT 'stable',
                outreach_angle TEXT,
                intelligence_notes TEXT,
                signal_sources TEXT,
                status TEXT DEFAULT 'prospect',
                pipeline_stage INTEGER DEFAULT 1,
                deal_value_monthly INTEGER,
                notes TEXT,
                is_deleted INTEGER DEFAULT 0,
                email_verified INTEGER DEFAULT 0,
                auto_followup_enabled INTEGER DEFAULT 0,
                last_contacted_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sponsor_outreach (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sponsor_id INTEGER REFERENCES sponsors(id),
                version INTEGER DEFAULT 1,
                channel TEXT DEFAULT 'email',
                subject TEXT,
                body TEXT,
                grok_review_score INTEGER,
                grok_review_notes TEXT,
                sent_at DATETIME,
                resend_message_id TEXT,
                opened_at DATETIME,
                replied_at DATETIME,
                bounce_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sponsor_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sponsor_id INTEGER REFERENCES sponsors(id),
                action TEXT NOT NULL,
                detail TEXT,
                actor TEXT DEFAULT 'system',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sponsor_config (
                id INTEGER PRIMARY KEY DEFAULT 1,
                auto_draft_enabled INTEGER DEFAULT 0,
                auto_draft_threshold INTEGER DEFAULT 85,
                daily_send_limit INTEGER DEFAULT 25,
                followup_days_1 INTEGER DEFAULT 3,
                followup_days_2 INTEGER DEFAULT 7,
                followup_days_3 INTEGER DEFAULT 14,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            INSERT OR IGNORE INTO sponsor_config (id) VALUES (1);

            CREATE INDEX IF NOT EXISTS idx_sponsors_status ON sponsors(status);
            CREATE INDEX IF NOT EXISTS idx_sponsors_score ON sponsors(relevance_score);
            CREATE INDEX IF NOT EXISTS idx_sponsors_deleted ON sponsors(is_deleted);
            CREATE INDEX IF NOT EXISTS idx_activity_sponsor ON sponsor_activity_log(sponsor_id);
            CREATE INDEX IF NOT EXISTS idx_outreach_sponsor ON sponsor_outreach(sponsor_id);
        """)
        conn.commit()
        logger.info("Sponsor tables ensured")
    except sqlite3.Error as e:
        conn.rollback()
        logger.error("Table creation error: %s", e)
        raise
    finally:
        conn.close()


def _upsert_sponsor(conn: sqlite3.Connection, company: Dict, score: int, angle: str,
                    deep_intel: Dict, deal_prob: int) -> Tuple[int, bool]:
    """
    Insert sponsor or update if company_name matches. Returns (id, is_new).
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM sponsors WHERE company_name = ? AND is_deleted = 0 LIMIT 1",
        (company.get("company_name"),)
    )
    row = cur.fetchone()
    podcasts_json = json.dumps(company.get("podcasts_they_sponsor", []))
    signals_json = json.dumps(company.get("signal_sources", {}))
    intel = json.dumps(deep_intel) if isinstance(deep_intel, dict) else str(deep_intel)

    now = datetime.utcnow().isoformat()
    if row:
        cur.execute("""
            UPDATE sponsors SET
                website=?, category=?, estimated_monthly_spend=?,
                podcasts_they_sponsor=?, relevance_score=?, deal_probability_pct=?,
                opportunity_signal=?, outreach_angle=?, intelligence_notes=?,
                signal_sources=?, updated_at=?
            WHERE id=?
        """, (
            company.get("website"), company.get("category", "other"),
            company.get("estimated_monthly_spend"),
            podcasts_json, score, deal_prob,
            deep_intel.get("opportunity_signal", company.get("opportunity_signal", "stable")),
            angle, intel, signals_json, now, row[0]
        ))
        return row[0], False
    else:
        email = company.get("contact_email") or ""
        email_ok = 1 if validate_email_deliverability(email) else 0
        cur.execute("""
            INSERT INTO sponsors (
                company_name, category, website, contact_email, contact_name,
                estimated_monthly_spend, podcasts_they_sponsor, relevance_score,
                deal_probability_pct, opportunity_signal, outreach_angle,
                intelligence_notes, signal_sources, status, pipeline_stage,
                email_verified, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'prospect',1,?,?,?)
        """, (
            company.get("company_name"), company.get("category", "other"),
            company.get("website"), email,
            company.get("contact_name"),
            company.get("estimated_monthly_spend"),
            podcasts_json, score, deal_prob,
            company.get("opportunity_signal", "stable"),
            angle, intel, signals_json, email_ok, now, now
        ))
        return cur.lastrowid, True


def _log_activity(conn: sqlite3.Connection, sponsor_id: int, action: str,
                  detail: str, actor: str = "system") -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor) VALUES (?,?,?,?)",
        (sponsor_id, action, detail[:500], actor)
    )


def get_daily_send_count(db_path: str) -> int:
    """Count emails sent today for rate limiting (Phase 0 addition #6)."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM sponsor_outreach WHERE date(sent_at) = date('now') AND sent_at IS NOT NULL"
        )
        return cur.fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main scan runner
# ---------------------------------------------------------------------------

def run_scan(progress_callback=None) -> Dict[str, Any]:
    """
    Full scan pipeline. Returns summary stats.
    progress_callback(event_type: str, message: str) called for SSE streaming.
    """
    ensure_tables()
    db_path = _get_db_path()

    if progress_callback:
        progress_callback("init", "Sponsor radar scan initiated")

    # Phase 1+2: Grok scans
    companies = grok_scan_podcasts(progress_callback=progress_callback)

    stats = {"scanned": len(companies), "new": 0, "updated": 0, "errors": 0}

    conn = sqlite3.connect(db_path)
    try:
        for i, company in enumerate(companies):
            name = company.get("company_name", f"Unknown-{i}")
            if progress_callback:
                progress_callback("research", f"Researching {name} ({i+1}/{len(companies)})...")

            try:
                # Phase 2: Deep research
                deep_intel = grok_deep_research(
                    name, company.get("website", ""), progress_callback=progress_callback
                )

                # Phase 3: Claude scores
                score, angle = claude_score_prospect(company, progress_callback=progress_callback)

                # Deal probability (Phase 0 #7)
                conf = company.get("signal_sources", {}).get("confidence_score", 50)
                deal_prob = compute_deal_probability(
                    score, company.get("category", "other"),
                    deep_intel.get("opportunity_signal", company.get("opportunity_signal", "stable")),
                    days_since_contact=None,
                    grok_score_signals=conf // 10,
                )

                # Phase 4: Save to DB
                sponsor_id, is_new = _upsert_sponsor(conn, company, score, angle, deep_intel, deal_prob)
                action = "scan_found" if is_new else "scan_updated"
                _log_activity(conn, sponsor_id, action,
                              f"Score: {score}/100, Deal prob: {deal_prob}%")
                conn.commit()

                if is_new:
                    stats["new"] += 1
                else:
                    stats["updated"] += 1

                if progress_callback:
                    progress_callback(
                        "prospect_saved",
                        f"{'NEW' if is_new else 'UPDATED'}: {name} — Score {score}/100, Deal {deal_prob}%"
                    )

            except Exception as e:
                conn.rollback()
                stats["errors"] += 1
                logger.error("Error processing %s: %s", name, e, exc_info=True)
                if progress_callback:
                    progress_callback("error", f"Error on {name}: {str(e)[:80]}")

        if progress_callback:
            progress_callback(
                "complete",
                f"Scan complete. New: {stats['new']}, Updated: {stats['updated']}, Errors: {stats['errors']}"
            )

    finally:
        conn.close()

    return stats


# ---------------------------------------------------------------------------
# Fallback data (when Grok is offline)
# ---------------------------------------------------------------------------

def _fallback_prospects() -> List[Dict]:
    """Return seed prospect data when Grok is unavailable."""
    return [
        {
            "company_name": "Ledger",
            "website": "https://www.ledger.com",
            "category": "hardware_wallet",
            "contact_email": "partnerships@ledger.com",
            "contact_name": None,
            "estimated_monthly_spend": "$20k-$50k/mo",
            "podcasts_they_sponsor": ["What Bitcoin Did", "Bitcoin Fundamentals", "Stephan Livera"],
            "opportunity_signal": "stable",
            "outreach_angle": "Protocol Pulse readers are exactly your target — self-sovereign Bitcoin holders who take security seriously.",
            "signal_sources": {"podcast_ads_detected": True, "confidence_score": 90},
            "intelligence_summary": "Ledger is the dominant hardware wallet brand, consistently sponsoring Bitcoin podcasts. Very high fit for Protocol Pulse's self-sovereign audience."
        },
        {
            "company_name": "Swan Bitcoin",
            "website": "https://www.swanbitcoin.com",
            "category": "fintech",
            "contact_email": "marketing@swanbitcoin.com",
            "contact_name": None,
            "estimated_monthly_spend": "$10k-$25k/mo",
            "podcasts_they_sponsor": ["What Bitcoin Did", "The Bitcoin Standard Podcast"],
            "opportunity_signal": "growing",
            "outreach_angle": "Protocol Pulse's daily briefing audience includes exactly the serious Bitcoiners Swan targets for auto-DCA.",
            "signal_sources": {"podcast_ads_detected": True, "confidence_score": 85},
            "intelligence_summary": "Swan Bitcoin is actively expanding their podcast sponsorship budget. Strong alignment with Protocol Pulse's Bitcoin-first audience."
        },
        {
            "company_name": "Unchained Capital",
            "website": "https://www.unchained.com",
            "category": "fintech",
            "contact_email": "partners@unchained.com",
            "contact_name": None,
            "estimated_monthly_spend": "$8k-$20k/mo",
            "podcasts_they_sponsor": ["Stephan Livera Podcast", "Tales from the Crypt"],
            "opportunity_signal": "stable",
            "outreach_angle": "Multi-sig custody solutions resonate perfectly with Protocol Pulse's security-conscious audience.",
            "signal_sources": {"podcast_ads_detected": True, "confidence_score": 80},
            "intelligence_summary": "Unchained sponsors Bitcoin-focused shows regularly. Their collaborative custody product is a strong fit for Protocol Pulse's technically-sophisticated audience."
        },
        {
            "company_name": "River Financial",
            "website": "https://www.river.com",
            "category": "exchange",
            "contact_email": "partnerships@river.com",
            "contact_name": None,
            "estimated_monthly_spend": "$5k-$15k/mo",
            "podcasts_they_sponsor": ["Bitcoin Fundamentals", "Rabbit Hole Recap"],
            "opportunity_signal": "growing",
            "outreach_angle": "River's Bitcoin-only focus aligns perfectly with Protocol Pulse readers who reject altcoins.",
            "signal_sources": {"podcast_ads_detected": True, "confidence_score": 78},
            "intelligence_summary": "River Financial is growing rapidly and expanding marketing spend. Bitcoin-only exchange is a perfect ideological match for Protocol Pulse audience."
        },
        {
            "company_name": "Mullvad VPN",
            "website": "https://www.mullvad.net",
            "category": "vpn",
            "contact_email": "press@mullvad.net",
            "contact_name": None,
            "estimated_monthly_spend": "$3k-$10k/mo",
            "podcasts_they_sponsor": ["Citadel Dispatch", "Bitcoin Audible"],
            "opportunity_signal": "stable",
            "outreach_angle": "Mullvad accepts Bitcoin — privacy-first users and Protocol Pulse's audience overlap heavily.",
            "signal_sources": {"podcast_ads_detected": True, "confidence_score": 72},
            "intelligence_summary": "Mullvad is the privacy VPN of choice in the Bitcoin community, accepts Bitcoin payments, and regularly sponsors Bitcoin shows."
        },
    ]


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Protocol Pulse Sponsor Radar V2")
    parser.add_argument("--scan", action="store_true", help="Run full prospect scan")
    parser.add_argument("--ensure-tables", action="store_true", help="Create DB tables only")
    args = parser.parse_args()

    if args.ensure_tables:
        ensure_tables()
        print("Tables ensured.")
        sys.exit(0)

    if args.scan:
        # Load app context for DB path
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        def printer(evt, msg):
            print(f"[{evt.upper()}] {msg}")

        stats = run_scan(progress_callback=printer)
        print(f"\nScan complete: {stats}")
        sys.exit(0)

    parser.print_help()
