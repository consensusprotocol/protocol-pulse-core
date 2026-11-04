#!/usr/bin/env python3
"""Repair botched article titles/content in the Protocol Pulse DB.

Fixes:
- Titles that are literally "```html" or start with "```"
- Titles starting with "TL;DR"
- Titles longer than 140 chars
- Content starting with code fences
- Content with placeholder "source 1" / "source 2" list items

Uses Ollama (Qwen, free) for fallback headline generation.
Idempotent. Run with --dry-run first.

Usage:
    python3 scripts/repair_botched_articles.py --dry-run
    python3 scripts/repair_botched_articles.py
"""
import argparse
import logging
import re
import sqlite3
import sys
import time
import requests
from pathlib import Path
from unicodedata import normalize

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("repair")

DB_PATH = Path.home() / "protocol_pulse" / "instance" / "protocol_pulse.db"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma3:27b"


# ---------- sanitization (mirrors article_automation.sanitize_article_output) ----------

def sanitize_content(text):
    if not text:
        return text
    text = text.strip()
    text = re.sub(r'^```(?:html|json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()

    def _is_placeholder_sources(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(0), re.IGNORECASE | re.DOTALL)
        if not items:
            return True
        return all(re.match(r'^\s*(source\s*\d*\s*)?$', it, re.IGNORECASE) for it in items)

    text = re.sub(
        r'<h2[^>]*>\s*Sources?\s*</h2>\s*<ul[^>]*>.*?</ul>',
        lambda m: '' if _is_placeholder_sources(m) else m.group(0),
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r'<p[^>]*>\s*</p>', '', text, flags=re.IGNORECASE)
    return text.strip()


def is_bad_title(title):
    if not title:
        return True
    if '```' in title:
        return True
    if title.strip().lower().startswith('tl;dr'):
        return True
    if len(title) > 140:
        return True
    return False


def extract_title_from_content(content):
    """Try to extract a title from HTML content."""
    if not content:
        return None
    # TITLE: line
    m = re.search(r'^TITLE:\s*(.+)', content, re.MULTILINE)
    if m:
        t = m.group(1).strip().strip('"').strip("'")
        if t and not is_bad_title(t):
            return t
    # <h1>
    m = re.search(r'<h1[^>]*>([^<]+)</h1>', content, re.IGNORECASE)
    if m:
        t = m.group(1).strip()
        if t and not is_bad_title(t):
            return t
    # <h2 class="article-header">
    m = re.search(r'<h2[^>]*class="article-header"[^>]*>([^<]+)</h2>', content, re.IGNORECASE)
    if m:
        t = m.group(1).strip()
        if t and not is_bad_title(t):
            return t
    return None


def ollama_generate_title(content_snippet):
    """Generate a headline via Ollama Qwen (free, local)."""
    prompt = f"""Generate a concise 8-12 word headline for the following article content.
Return ONLY the headline, nothing else. No quotes.

Content:
{content_snippet[:1500]}"""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 60},
            },
            timeout=60,
        )
        resp.raise_for_status()
        title = resp.json().get("message", {}).get("content", "").strip()
        # Take first line only
        title = title.split('\n')[0].strip().strip('"').strip("'")
        if title and not is_bad_title(title) and len(title) <= 110:
            return title
    except Exception as e:
        log.warning("Ollama title gen failed: %s", e)
    return None


def make_slug(title, existing_slugs, article_id):
    """Generate a URL slug from a title, ensuring uniqueness."""
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    slug = slug[:80]
    if not slug:
        slug = f"article-{article_id}"
    base = slug
    counter = 2
    while slug in existing_slugs:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def main():
    parser = argparse.ArgumentParser(description="Repair botched article titles/content")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    args = parser.parse_args()

    if not DB_PATH.exists():
        log.error("DB not found: %s", DB_PATH)
        sys.exit(1)

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    c = db.cursor()

    # Find all botched articles
    c.execute("""
        SELECT id, title, content, slug, category, summary, tags, published
        FROM articles
        WHERE title LIKE '%```%'
           OR title LIKE 'TL;DR%'
           OR length(title) > 140
           OR content LIKE '```%'
           OR content LIKE '%<li>source 1</li>%'
    """)
    rows = c.fetchall()
    log.info("Found %d botched articles", len(rows))

    if not rows:
        print("No botched articles found.")
        return

    # Load all existing slugs
    c.execute("SELECT slug FROM articles WHERE slug IS NOT NULL AND slug != ''")
    existing_slugs = {r[0] for r in c.fetchall()}

    fixed = 0
    unpublished = 0
    title_fixed = 0
    content_fixed = 0

    for row in rows:
        aid = row['id']
        old_title = row['title'] or ''
        content = row['content'] or ''
        old_slug = row['slug'] or ''

        # Sanitize content
        new_content = sanitize_content(content)
        content_changed = (new_content != content)

        # Try to fix title
        new_title = None
        if is_bad_title(old_title):
            # Try extracting from content
            new_title = extract_title_from_content(new_content or content)
            if not new_title:
                # Use Ollama
                new_title = ollama_generate_title(new_content or content)
            if not new_title:
                # Still no valid title — unpublish
                if args.dry_run:
                    log.info("[DRY-RUN] id=%d: would UNPUBLISH (no valid title derivable)", aid)
                else:
                    c.execute("UPDATE articles SET published=0, updated_at=CURRENT_TIMESTAMP WHERE id=?", (aid,))
                unpublished += 1
                continue
        else:
            new_title = old_title

        # Determine slug
        title_actually_changed = (new_title != old_title)
        slug_is_bad = old_slug and ('```' in old_slug or old_slug.startswith('tl-dr'))
        if title_actually_changed or slug_is_bad or not old_slug:
            new_slug = make_slug(new_title, existing_slugs, aid)
            existing_slugs.add(new_slug)
        else:
            new_slug = old_slug

        if args.dry_run:
            changes = []
            if title_actually_changed:
                changes.append(f"title: '{old_title[:50]}' -> '{new_title[:50]}'")
            if content_changed:
                changes.append("content: sanitized")
            if new_slug != old_slug:
                changes.append(f"slug: '{old_slug}' -> '{new_slug}'")
            if changes:
                log.info("[DRY-RUN] id=%d: %s", aid, " | ".join(changes))
        else:
            c.execute("""
                UPDATE articles
                SET title=?, content=?, slug=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (new_title, new_content if content_changed else content, new_slug, aid))

            # Rebuild FTS entry
            try:
                c.execute("DELETE FROM articles_fts WHERE rowid=?", (aid,))
                c.execute("""
                    INSERT INTO articles_fts(rowid, title, summary, category, tags)
                    VALUES (?, ?, ?, ?, ?)
                """, (aid, new_title, row['summary'] or '', row['category'] or '', row['tags'] or ''))
            except Exception as e:
                log.warning("FTS rebuild failed for id=%d: %s", aid, e)

        if title_actually_changed:
            title_fixed += 1
        if content_changed:
            content_fixed += 1
        fixed += 1

        # Progress log every 50 articles
        if fixed % 50 == 0:
            log.info("Progress: %d/%d processed", fixed, len(rows))
            if not args.dry_run:
                db.commit()

    if not args.dry_run:
        db.commit()

    log.info("=== REPAIR COMPLETE ===")
    log.info("Total botched: %d", len(rows))
    log.info("Titles fixed: %d", title_fixed)
    log.info("Content sanitized: %d", content_fixed)
    log.info("Unpublished (no valid title): %d", unpublished)
    log.info("Mode: %s", "DRY-RUN" if args.dry_run else "LIVE")

    # Post-repair counts
    c.execute("SELECT COUNT(*) FROM articles WHERE title LIKE '%```%' OR title LIKE 'TL;DR%'")
    remaining = c.fetchone()[0]
    log.info("Remaining bad titles: %d", remaining)

    db.close()


if __name__ == "__main__":
    main()
