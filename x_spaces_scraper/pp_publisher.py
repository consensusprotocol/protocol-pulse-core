"""
pp_publisher.py — Publish generated articles to Protocol Pulse.

Inserts articles directly into the Protocol Pulse SQLite database
using the Article model, tagged with source_type='x_spaces'.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def publish_to_db(article: dict, auto_publish: bool = False) -> Optional[int]:
    """
    Insert an article into the Protocol Pulse database.

    Args:
        article: Generated article dict (from article_generator)
        auto_publish: If True, set published=True immediately

    Returns:
        Article ID on success, None on failure.
    """
    try:
        from app import app, db
        from models import Article

        with app.app_context():
            new_article = Article(
                title=article.get("title", "Untitled X Space Recap"),
                content=article.get("content", ""),
                summary=article.get("summary", ""),
                author="Protocol Pulse AI",
                category="Bitcoin",
                tags=json.dumps(article.get("tags", ["bitcoin", "x-spaces"])),
                source_url=article.get("space_url", ""),
                source_type="x_spaces",
                published=auto_publish,
                published_at=datetime.utcnow() if auto_publish else None,
                seo_title=article.get("seo_title", article.get("title", "")[:200]),
                seo_description=article.get("seo_description", article.get("summary", "")[:300]),
            )

            db.session.add(new_article)
            db.session.commit()
            article_id = new_article.id

            status = "PUBLISHED" if auto_publish else "DRAFT"
            logger.info(f"Article #{article_id} saved as {status}: {article.get('title', '')[:80]}")
            return article_id

    except ImportError as e:
        logger.error(f"Cannot import Flask app (run from project root): {e}")
        return None
    except Exception as e:
        logger.error(f"DB publish failed: {e}")
        return None


def publish_via_api(article: dict, base_url: str = "https://protocolpulse.replit.app") -> Optional[int]:
    """
    Publish via the Replit relay exec endpoint as a fallback.
    Constructs a Python command that inserts the article on the remote side.
    """
    import requests

    relay_url = f"{base_url}/api/admin/exec"
    token = os.environ.get(
        "REPLIT_RELAY_TOKEN",
        "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552",
    )

    # Build a safe Python insert command
    safe_title = article.get("title", "").replace("'", "\\'")
    safe_summary = article.get("summary", "").replace("'", "\\'")
    tags_json = json.dumps(article.get("tags", ["bitcoin", "x-spaces"]))
    source_url = article.get("space_url", "")

    # For content, we base64 encode to avoid escaping nightmares
    import base64
    content_b64 = base64.b64encode(article.get("content", "").encode()).decode()

    cmd = (
        f"python3 -c \""
        f"import base64, json; "
        f"from app import app, db; "
        f"from models import Article; "
        f"ctx = app.app_context(); ctx.push(); "
        f"a = Article("
        f"title='{safe_title}',"
        f"content=base64.b64decode('{content_b64}').decode(),"
        f"summary='{safe_summary}',"
        f"author='Protocol Pulse AI',"
        f"category='Bitcoin',"
        f"tags='{tags_json}',"
        f"source_url='{source_url}',"
        f"source_type='x_spaces',"
        f"published=False); "
        f"db.session.add(a); db.session.commit(); "
        f"print(f'OK:{{a.id}}')\""
    )

    try:
        r = requests.post(
            relay_url,
            json={"token": token, "cmd": cmd},
            timeout=30,
        )
        if r.status_code == 200:
            output = r.json().get("output", "")
            if output.startswith("OK:"):
                article_id = int(output.split(":")[1].strip())
                logger.info(f"Published via API relay: article #{article_id}")
                return article_id
        logger.error(f"API publish failed: {r.status_code} — {r.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"API publish error: {e}")
        return None


def publish_article(article: dict, auto_publish: bool = False) -> Optional[int]:
    """
    Publish article — tries local DB first, falls back to API relay.
    """
    # Try local DB insert first
    article_id = publish_to_db(article, auto_publish=auto_publish)
    if article_id:
        return article_id

    # Fallback: API relay to Replit
    logger.info("Local DB insert failed, trying API relay...")
    return publish_via_api(article)


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python pp_publisher.py <article_file.json> [--publish]")
        sys.exit(1)

    article_file = Path(sys.argv[1])
    if not article_file.exists():
        print(f"File not found: {article_file}")
        sys.exit(1)

    article = json.loads(article_file.read_text())
    auto_pub = "--publish" in sys.argv

    article_id = publish_article(article, auto_publish=auto_pub)
    if article_id:
        print(f"Published as article #{article_id}")
    else:
        print("Publishing failed.")
