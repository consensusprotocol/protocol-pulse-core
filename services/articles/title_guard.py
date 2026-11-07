"""
title_guard.py — Single source of truth for article title validation.

Every article save path MUST call derive_title() before persisting.
Returns a clean title string or None (meaning: do not save this article).
"""
import re
import logging

logger = logging.getLogger(__name__)

# Max/min title length
MAX_TITLE_LEN = 110
MIN_TITLE_LEN = 15


def derive_title(raw_text: str, content_html: str) -> str | None:
    """Extract or generate a title from raw LLM output and article HTML.

    Priority:
      1. Explicit TITLE: line in raw_text
      2. First <h1> tag in content_html
      3. First <h2 class="article-header"> in content_html
      4. None — caller must generate via LLM or skip saving

    Hard reject rules (returns None):
      - Starts with 'TL;DR'
      - Contains backticks (```)
      - Longer than MAX_TITLE_LEN chars
      - Shorter than MIN_TITLE_LEN chars
    """
    title = None

    # 1. TITLE: line
    if raw_text:
        m = re.search(r'(?:^|\n)\s*TITLE:\s*(.+)', raw_text, re.IGNORECASE)
        if m:
            title = m.group(1).strip()

    # 2. <h1>
    if not title and content_html:
        m = re.search(r'<h1[^>]*>([^<]+)</h1>', content_html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()

    # 3. <h2 class="article-header">
    if not title and content_html:
        m = re.search(r'<h2[^>]*class="article-header"[^>]*>([^<]+)</h2>', content_html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()

    if not title:
        return None

    # Clean: strip code fences, prompt bleed after newline, collapse whitespace
    title = re.sub(r'^```(?:html|json)?\s*', '', title, flags=re.IGNORECASE).strip()
    title = re.sub(r'```\s*$', '', title).strip()
    title = title.lstrip('`').strip()
    title = re.sub(r'[\r\n].*', '', title, flags=re.DOTALL).strip()
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.strip('"').strip("'")

    # Hard reject rules
    if _should_reject(title):
        return None

    return title


def validate_title(title: str) -> bool:
    """Return True if title passes all quality gates."""
    if not title:
        return False
    return not _should_reject(title)


def _should_reject(title: str) -> bool:
    """Return True if title violates any hard rule."""
    if not title:
        return True
    if title.lower().startswith('tl;dr'):
        logger.warning("Title rejected (TL;DR): %s", title[:80])
        return True
    if '```' in title:
        logger.warning("Title rejected (backticks): %s", title[:80])
        return True
    if len(title) > MAX_TITLE_LEN:
        logger.warning("Title rejected (too long %d chars): %s", len(title), title[:80])
        return True
    if len(title) < MIN_TITLE_LEN:
        logger.warning("Title rejected (too short %d chars): %s", len(title), title[:80])
        return True
    return False
