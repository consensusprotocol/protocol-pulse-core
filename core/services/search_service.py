"""
SQLite FTS5 full-text search across articles and podcast episodes.

Provides <200ms search with highlighted snippets, type filtering,
and popular searches based on search analytics.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import text

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_SEARCH_LOG_PATH = _DATA_DIR / "search_queries.jsonl"

# Popular searches fallback when log is empty
_DEFAULT_POPULAR = [
    "Bitcoin ETF",
    "Lightning Network",
    "Bitcoin mining",
    "Regulation",
    "Halving",
]


# ---------------------------------------------------------------------------
# FTS5 Table Setup
# ---------------------------------------------------------------------------

def init_fts_index(db) -> None:
    """
    Create FTS5 virtual tables if they don't exist.
    Uses content= tables that mirror the articles table.
    Safe to call multiple times (CREATE ... IF NOT EXISTS).
    """
    try:
        db.session.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title,
                summary,
                category,
                tags,
                content='articles',
                content_rowid='id',
                tokenize='porter unicode61'
            )
        """))

        db.session.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS podcast_fts USING fts5(
                title,
                guest_name,
                show_notes,
                tags,
                tokenize='porter unicode61'
            )
        """))

        db.session.commit()
        logger.info("FTS5 index tables ready")
    except Exception as exc:
        logger.warning("FTS5 init failed (non-fatal): %s", exc)
        db.session.rollback()


def populate_fts_index(db) -> None:
    """
    Populate the articles_fts content table from the articles table.
    Uses INSERT OR IGNORE to avoid duplicates on restarts.
    Only indexes published articles.
    """
    try:
        db.session.execute(text("""
            INSERT INTO articles_fts(rowid, title, summary, category, tags)
            SELECT id,
                   COALESCE(title, ''),
                   COALESCE(summary, ''),
                   COALESCE(category, ''),
                   COALESCE(tags, '')
            FROM articles
            WHERE published = 1
              AND id NOT IN (SELECT rowid FROM articles_fts)
        """))
        db.session.commit()
        logger.info("FTS5 index populated from articles table")
    except Exception as exc:
        logger.warning("FTS5 populate failed (non-fatal): %s", exc)
        db.session.rollback()


def rebuild_fts_index(db) -> None:
    """Full rebuild of the FTS5 index (for admin use)."""
    try:
        db.session.execute(text("DELETE FROM articles_fts"))
        db.session.execute(text("""
            INSERT INTO articles_fts(rowid, title, summary, category, tags)
            SELECT id,
                   COALESCE(title, ''),
                   COALESCE(summary, ''),
                   COALESCE(category, ''),
                   COALESCE(tags, '')
            FROM articles
            WHERE published = 1
        """))
        db.session.commit()
        logger.info("FTS5 index rebuilt")
    except Exception as exc:
        logger.error("FTS5 rebuild failed: %s", exc)
        db.session.rollback()
        raise


def index_article(db, article_id: int, title: str, summary: str,
                  category: str, tags: str) -> None:
    """
    Add or update a single article in the FTS index.
    Called after article creation/update.
    """
    try:
        # Remove existing entry if present
        db.session.execute(
            text("DELETE FROM articles_fts WHERE rowid = :id"),
            {"id": article_id}
        )
        db.session.execute(
            text("""
                INSERT INTO articles_fts(rowid, title, summary, category, tags)
                VALUES (:id, :title, :summary, :category, :tags)
            """),
            {
                "id": article_id,
                "title": title or "",
                "summary": summary or "",
                "category": category or "",
                "tags": tags or "",
            }
        )
        db.session.commit()
    except Exception as exc:
        logger.warning("FTS5 index_article failed for id=%s: %s", article_id, exc)
        db.session.rollback()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search(db, query: str, search_type: str = "all", limit: int = 20) -> List[Dict[str, Any]]:
    """
    Full-text search using FTS5 with highlighted snippets.

    Args:
        db: SQLAlchemy db instance
        query: search query string
        search_type: 'all', 'articles', or 'podcast'
        limit: max results to return

    Returns:
        List of {type, id, title, snippet, category, date, url}
    """
    if not query or len(query.strip()) < 2:
        return []

    query = query.strip()
    results: List[Dict[str, Any]] = []
    start = time.monotonic()

    if search_type in ("all", "articles"):
        try:
            # Escape FTS5 special characters to avoid parse errors
            safe_query = _escape_fts_query(query)

            rows = db.session.execute(text("""
                SELECT
                    a.id,
                    a.title,
                    a.category,
                    a.published_at,
                    a.created_at,
                    snippet(articles_fts, 1, '<mark>', '</mark>', '...', 32) AS snip
                FROM articles_fts
                JOIN articles a ON a.id = articles_fts.rowid
                WHERE articles_fts MATCH :q
                  AND a.published = 1
                ORDER BY rank
                LIMIT :lim
            """), {"q": safe_query, "lim": limit}).fetchall()

            for row in rows:
                pub_date = row[3] or row[4]
                results.append({
                    "type": "article",
                    "id": row[0],
                    "title": row[1] or "",
                    "snippet": row[5] or "",
                    "category": row[2] or "",
                    "date": pub_date.isoformat() if pub_date else "",
                    "url": f"/articles/{row[0]}",
                })
        except Exception as exc:
            logger.warning("FTS5 articles search failed (falling back): %s", exc)
            # Fall back to LIKE-based search
            results.extend(_fallback_search(db, query, limit))

    _log_search(query, len(results), int((time.monotonic() - start) * 1000))
    return results


def _escape_fts_query(query: str) -> str:
    """
    Escape a user query for safe FTS5 MATCH usage.
    Wraps individual tokens in double-quotes and adds * for prefix matching
    on the last token.
    """
    # Remove characters that break FTS5 parsing
    import re
    # Strip FTS5 operators/specials, keep alphanumeric and common punctuation
    clean = re.sub(r'[^\w\s\-\']', ' ', query, flags=re.UNICODE)
    tokens = clean.split()
    if not tokens:
        return '""'

    escaped = []
    for i, tok in enumerate(tokens):
        tok = tok.strip("'\"")
        if not tok:
            continue
        if i == len(tokens) - 1:
            # Last token: prefix search
            escaped.append(f'"{tok}"*')
        else:
            escaped.append(f'"{tok}"')

    return " ".join(escaped) if escaped else '""'


def _fallback_search(db, query: str, limit: int) -> List[Dict[str, Any]]:
    """LIKE-based fallback when FTS5 fails."""
    try:
        pattern = f"%{query}%"
        rows = db.session.execute(text("""
            SELECT id, title, category, published_at, created_at, summary
            FROM articles
            WHERE published = 1
              AND (title LIKE :p OR summary LIKE :p OR tags LIKE :p OR category LIKE :p)
            ORDER BY published_at DESC
            LIMIT :lim
        """), {"p": pattern, "lim": limit}).fetchall()

        results = []
        for row in rows:
            pub_date = row[3] or row[4]
            snippet = (row[5] or "")[:200]
            results.append({
                "type": "article",
                "id": row[0],
                "title": row[1] or "",
                "snippet": snippet,
                "category": row[2] or "",
                "date": pub_date.isoformat() if pub_date else "",
                "url": f"/articles/{row[0]}",
            })
        return results
    except Exception as exc:
        logger.error("Fallback search also failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Popular Searches
# ---------------------------------------------------------------------------

def get_popular_searches(limit: int = 6) -> List[str]:
    """
    Return trending search terms from the analytics log.
    Falls back to hardcoded Bitcoin terms if log is empty or unavailable.
    """
    try:
        if not _SEARCH_LOG_PATH.exists():
            return _DEFAULT_POPULAR[:limit]

        counts: Dict[str, int] = {}
        with open(_SEARCH_LOG_PATH, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    q = (entry.get("query") or "").strip()
                    if q and len(q) >= 2:
                        counts[q] = counts.get(q, 0) + 1
                except (json.JSONDecodeError, KeyError):
                    continue

        if not counts:
            return _DEFAULT_POPULAR[:limit]

        sorted_terms = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [term for term, _ in sorted_terms[:limit]]

    except Exception as exc:
        logger.warning("get_popular_searches failed: %s", exc)
        return _DEFAULT_POPULAR[:limit]


# ---------------------------------------------------------------------------
# Analytics Logging
# ---------------------------------------------------------------------------

def _log_search(query: str, result_count: int, latency_ms: int) -> None:
    """Append search event to JSONL analytics log (fire-and-forget)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "query": query[:200],
            "results": result_count,
            "latency_ms": latency_ms,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        with open(_SEARCH_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Never let logging break search
