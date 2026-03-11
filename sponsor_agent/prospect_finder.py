"""
Prospect Finder — Sponsor Agent V2
===================================
Discovers Bitcoin-industry sponsor prospects via Serper.dev,
enriches with Hunter.io contact data, stores in SponsorOutreach table.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

CATEGORIES = {
    "hardware": [
        "bitcoin hardware wallet company",
        "bitcoin cold storage device manufacturer",
    ],
    "exchanges": [
        "bitcoin exchange sponsor podcast",
        "cryptocurrency exchange advertising partnership",
    ],
    "mining": [
        "bitcoin mining hardware company sponsor",
        "bitcoin ASIC miner manufacturer",
    ],
    "financial": [
        "bitcoin financial services company",
        "bitcoin lending platform sponsor",
    ],
    "education": [
        "bitcoin education platform sponsor",
        "bitcoin course training company",
    ],
}


def _serper_key() -> str:
    return os.environ.get("SERPER_API_KEY", "")


def _hunter_key() -> str:
    return os.environ.get("HUNTER_API_KEY", "")


def _search_serper(query: str, num: int = 5) -> list[dict]:
    """Run a Serper.dev organic search and return results."""
    key = _serper_key()
    if not key:
        logger.warning("SERPER_API_KEY not set — skipping search")
        return []

    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            json={"q": query, "num": num},
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("organic", [])
    except requests.RequestException as exc:
        logger.error("Serper search failed for %r: %s", query, exc)
        return []


def _extract_domain(url: str) -> str:
    """Extract root domain from URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _find_email_hunter(domain: str) -> str | None:
    """Find a verified contact email for domain via Hunter.io.
    Only returns emails that Hunter has actually found — never fabricates."""
    key = _hunter_key()
    if not key:
        return None

    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": key, "limit": 1},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        emails = data.get("emails", [])
        if emails:
            return emails[0].get("value")
    except requests.RequestException as exc:
        logger.error("Hunter.io lookup failed for %s: %s", domain, exc)

    return None


def _relevance_score(title: str, snippet: str, category: str) -> float:
    """Simple keyword-match relevance score 0-1."""
    text = f"{title} {snippet}".lower()
    bitcoin_terms = ["bitcoin", "btc", "crypto", "lightning", "satoshi"]
    biz_terms = ["sponsor", "advertise", "partner", "media", "podcast"]

    btc_hits = sum(1 for t in bitcoin_terms if t in text)
    biz_hits = sum(1 for t in biz_terms if t in text)

    score = min(1.0, (btc_hits * 0.15 + biz_hits * 0.1 + 0.2))
    return round(score, 2)


def _log_activity(db, outreach_id: int, action: str, details: str = None,
                  old_status: str = None, new_status: str = None):
    """Record a state change in the activity log."""
    from models import SponsorActivityLog
    log = SponsorActivityLog(
        outreach_id=outreach_id,
        action=action,
        old_status=old_status,
        new_status=new_status,
        details=details,
    )
    db.session.add(log)


def find_new_prospects(count: int = 5, category: str | None = None) -> list[dict]:
    """
    Find new sponsor prospects.

    Args:
        count: Max number of new prospects to return
        category: Optional category filter (hardware/exchanges/mining/financial/education)

    Returns:
        List of prospect dicts: {company, domain, email, category, source_url, relevance_score}
    """
    from app import db
    from models import SponsorOutreach

    categories = {category: CATEGORIES[category]} if category and category in CATEGORIES else CATEGORIES
    prospects = []
    seen_domains = set()

    # Load existing domains to deduplicate
    existing = {r.domain for r in db.session.query(SponsorOutreach.domain).all()}

    for cat, queries in categories.items():
        if len(prospects) >= count:
            break

        for query in queries:
            if len(prospects) >= count:
                break

            results = _search_serper(query, num=5)
            for result in results:
                if len(prospects) >= count:
                    break

                url = result.get("link", "")
                domain = _extract_domain(url)

                if not domain or domain in seen_domains or domain in existing:
                    continue

                # Skip generic domains
                skip_domains = {
                    "google.com", "youtube.com", "reddit.com", "twitter.com",
                    "x.com", "facebook.com", "linkedin.com", "wikipedia.org",
                    "amazon.com", "github.com",
                }
                if domain in skip_domains:
                    continue

                seen_domains.add(domain)

                title = result.get("title", "")
                snippet = result.get("snippet", "")
                email = _find_email_hunter(domain)
                score = _relevance_score(title, snippet, cat)

                company_name = title.split(" - ")[0].split(" | ")[0].strip()[:200]

                prospect = {
                    "company": company_name,
                    "domain": domain,
                    "email": email,
                    "category": cat,
                    "source_url": url[:500],
                    "relevance_score": score,
                }
                prospects.append(prospect)

                outreach = SponsorOutreach(
                    company=prospect["company"],
                    domain=prospect["domain"],
                    email=prospect["email"],
                    category=prospect["category"],
                    status="prospect",
                )
                db.session.add(outreach)
                db.session.flush()

                _log_activity(db, outreach.id, "created", f"Prospect found via Serper: {domain}",
                              new_status="prospect")

    try:
        db.session.commit()
        logger.info("Stored %d new prospects", len(prospects))
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to store prospects: %s", exc)
        prospects = []

    return prospects
