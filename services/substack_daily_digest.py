#!/usr/bin/env python3
"""
substack_daily_digest.py
Publishes a curated daily digest to Substack — 3 to 6 top Protocol Pulse
articles, selected by a composite score (read_count + category diversity +
recency), formatted as a single branded Substack post.

Runs once daily at 17:00 ET (after the X top-article publisher at 14:00).
Tracks published_article_ids in a local JSON ledger so the same article
never appears in two digests.
"""

import os, sys, re, json, logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
sys.path.insert(0, str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("substack_digest")

LEDGER_PATH = BASE / "data" / "substack_digest_ledger.json"
SITE_URL     = "https://protocolpulse.io"
MIN_ARTICLES = 3
MAX_ARTICLES = 6


# ── Ledger: track which articles have been Substacked already ────────────────

def _load_ledger() -> set:
    try:
        if LEDGER_PATH.exists():
            return set(json.loads(LEDGER_PATH.read_text()).get("published_ids", []))
    except Exception:
        pass
    return set()

def _save_ledger(ids: set) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps({"published_ids": sorted(ids)}, indent=2))


# ── Article selection ────────────────────────────────────────────────────────

def select_top_articles(n_min=MIN_ARTICLES, n_max=MAX_ARTICLES) -> list:
    """
    Pick the best articles from the last 24 h that haven't been Substacked yet.
    Scoring: read_count (primary) + category_diversity bonus + recency bonus.
    Always tries to include at least one article from each major category bucket.
    """
    from dotenv import load_dotenv; load_dotenv(BASE / ".env")
    from app import app
    import models

    already_published = _load_ledger()
    cutoff = datetime.utcnow() - timedelta(hours=168)

    with app.app_context():
        articles = (
            models.Article.query
            .filter(models.Article.published == True)
            .filter(models.Article.created_at >= cutoff)
            .all()
        )

        candidates = []
        for a in articles:
            if a.id in already_published:
                continue
            slug   = a.slug or str(a.id)
            score  = (a.read_count or 0) * 3          # reads matter most
            # Recency bonus — newer = better
            age_h  = (datetime.utcnow() - (a.created_at or datetime.utcnow())).total_seconds() / 3600
            score += max(0, 10 - age_h)               # up to +10 for brand new
            candidates.append({
                "id":       a.id,
                "title":    a.title,
                "summary":  (a.summary or "")[:280],
                "category": a.category or "Bitcoin",
                "slug":     slug,
                "url":      f"{SITE_URL}/articles/{slug}",
                "cover":    a.cover_image_url or "",
                "score":    score,
                "content":  a.content or "",
            })

    if not candidates:
        logger.warning("No fresh unpublished articles found in last 24h")
        return []

    # Sort by score
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Ensure category diversity — deduplicate categories greedily
    seen_cats = set()
    selected  = []
    # First pass: one per category
    for a in candidates:
        if a["category"] not in seen_cats:
            selected.append(a)
            seen_cats.add(a["category"])
        if len(selected) >= n_max:
            break
    # Second pass: fill up to n_max by score if we have room
    for a in candidates:
        if len(selected) >= n_max:
            break
        if a not in selected:
            selected.append(a)

    # Enforce minimum
    if len(selected) < n_min:
        logger.info(f"Only {len(selected)} articles available (min {n_min}) — publishing anyway")

    logger.info(f"Selected {len(selected)} articles for digest")
    for a in selected:
        logger.info(f"  [{a['id']}] {a['category']:12s} score={a['score']:.1f} {a['title'][:55]}")

    return selected[:n_max]


# ── Build digest content ─────────────────────────────────────────────────────

def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()

def build_digest_doc(articles: list, date_str: str) -> dict:
    """Build a Substack Prosemirror doc for the digest."""
    nodes = []

    # Intro paragraph
    nodes.append({
        "type": "paragraph",
        "attrs": {"textAlign": "left"},
        "content": [{"type": "text", "text":
            f"Your Protocol Pulse intelligence briefing for {date_str}. "
            f"{len(articles)} briefs — curated from today's signal stream. "
            f"Read time: ~{len(articles) * 2} minutes."
        }]
    })

    # Horizontal rule
    nodes.append({"type": "horizontalRule"})

    for i, article in enumerate(articles, 1):
        # Article number + category badge
        nodes.append({
            "type": "heading",
            "attrs": {"level": 2, "textAlign": "left"},
            "content": [{"type": "text", "text": f"{i}. {article['title']}"}]
        })

        # Category label
        nodes.append({
            "type": "paragraph",
            "attrs": {"textAlign": "left"},
            "content": [
                {"type": "text", "marks": [{"type": "bold"}],
                 "text": f"[{article['category'].upper()}]"}
            ]
        })

        # Summary / first paragraph of content
        summary = article["summary"]
        if not summary:
            # Extract first real paragraph from content
            match = re.search(r'<p[^>]*>(.*?)</p>', article["content"], re.DOTALL)
            if match:
                summary = _strip_html(match.group(1))[:300]

        if summary:
            nodes.append({
                "type": "paragraph",
                "attrs": {"textAlign": "left"},
                "content": [{"type": "text", "text": summary}]
            })

        # Read full brief link
        nodes.append({
            "type": "paragraph",
            "attrs": {"textAlign": "left"},
            "content": [
                {"type": "text", "text": "→ "},
                {"type": "text",
                 "marks": [{"type": "link", "attrs": {"href": article["url"], "target": "_blank"}}],
                 "text": "Read the full brief on Protocol Pulse"}
            ]
        })

        # Divider between articles (except last)
        if i < len(articles):
            nodes.append({"type": "horizontalRule"})

    # Footer CTA
    nodes.append({"type": "horizontalRule"})
    nodes.append({
        "type": "paragraph",
        "attrs": {"textAlign": "left"},
        "content": [
            {"type": "text", "text": "Stay sovereign. — "},
            {"type": "text",
             "marks": [{"type": "link", "attrs": {"href": SITE_URL, "target": "_blank"}}],
             "text": "Protocol Pulse"}
        ]
    })

    return {"type": "doc", "content": nodes}


def get_best_cover_image(articles: list) -> str | None:
    """Return the cover image of the highest-scored article that has one."""
    for a in articles:
        cover = a.get("cover", "")
        if cover and cover != "/static/images/default-header.png":
            if cover.startswith("/static/"):
                return f"{SITE_URL}{cover}"
            if cover.startswith("http"):
                return cover
    return None


# ── Publish ──────────────────────────────────────────────────────────────────

def publish_daily_digest() -> bool:
    from dotenv import load_dotenv; load_dotenv(BASE / ".env")
    from services.substack_publisher import _api_request, publish_draft

    articles = select_top_articles()
    if not articles:
        logger.error("No articles to digest — skipping")
        return False

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    title = f"Protocol Pulse Daily Brief — {today}"
    subtitle = f"{len(articles)} intelligence signals for transactors"

    doc = build_digest_doc(articles, today)
    cover = get_best_cover_image(articles)

    pub_id = int(os.getenv("SUBSTACK_PUBLICATION_ID", "4276014"))

    payload = {
        "draft_title":    title,
        "draft_subtitle": subtitle,
        "draft_body":     json.dumps(doc),
        "audience":       "everyone",
        "type":           "newsletter",
        "publication_id": pub_id,
        "draft_bylines":  [{"id": 316907961, "is_guest": False}],
        "should_send_email": True,
        "write_comment_permissions": "everyone",
    }
    if cover:
        payload["cover_image"] = cover
        payload["cover_image_attribution_url"] = SITE_URL

    draft = _api_request("POST", "/drafts", payload)
    if not draft or not draft.get("id"):
        logger.error(f"Draft creation failed: {draft}")
        return False

    draft_id = draft["id"]
    logger.info(f"Digest draft created: id={draft_id} title='{title}'")

    pub = publish_draft(draft_id)
    if pub:
        logger.info(f"Digest published: {title}")
        # Mark articles as Substacked
        ledger = _load_ledger()
        for a in articles:
            ledger.add(a["id"])
        _save_ledger(ledger)
        print(f"SUCCESS: Published digest with {len(articles)} articles")
        print(f"  Articles: {[a['id'] for a in articles]}")
        return True
    else:
        logger.error("Publish failed")
        return False


if __name__ == "__main__":
    import sys
    if "--dry-run" in sys.argv:
        # Show what would be published without actually publishing
        articles = select_top_articles()
        print(f"\nWould publish {len(articles)} articles:")
        for a in articles:
            print(f"  [{a['id']}] {a['category']:12s} score={a['score']:.1f} {a['title'][:60]}")
    else:
        publish_daily_digest()
