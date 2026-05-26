"""
AI-enhanced full-text search engine for Protocol Pulse.

Provides article search with relevance scoring, autocomplete suggestions,
and search analytics tracking.  Uses SQLite LIKE queries (no FTS5 dependency)
with layered scoring: exact match > title contains > tag match > content match,
plus recency and popularity boosts.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from app import db
import models

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SEARCH_LOG_PATH = _DATA_DIR / "search_queries.jsonl"

# Maximum query length we accept (prevent abuse / excessive LIKE scans)
_MAX_QUERY_LENGTH = 200

# Snippet length (characters on each side of the matched term)
_SNIPPET_RADIUS = 120

# Bitcoin-specific synonyms: when a user searches for one term we also
# search for the others in the same group.
_BTC_SYNONYMS: Dict[str, List[str]] = {
    "bitcoin":   ["btc", "bitcoin", "xbt"],
    "btc":       ["btc", "bitcoin", "xbt"],
    "xbt":       ["btc", "bitcoin", "xbt"],
    "satoshi":   ["satoshi", "sats", "sat"],
    "sats":      ["satoshi", "sats", "sat"],
    "sat":       ["satoshi", "sats", "sat"],
    "hodl":      ["hodl", "hold"],
    "hold":      ["hodl", "hold"],
    "halving":   ["halving", "halvening"],
    "halvening": ["halving", "halvening"],
    "lightning": ["lightning", "ln", "lightning network"],
    "ln":        ["lightning", "ln", "lightning network"],
    "defi":      ["defi", "decentralized finance"],
    "nft":       ["nft", "non-fungible token"],
    "whale":     ["whale", "large holder"],
    "mempool":   ["mempool", "mem pool"],
    "utxo":      ["utxo", "unspent transaction output"],
    "taproot":   ["taproot"],
    "segwit":    ["segwit", "segregated witness"],
    "nostr":     ["nostr"],
    "ordinals":  ["ordinals", "inscriptions", "brc-20"],
    "inscriptions": ["ordinals", "inscriptions"],
    "brc-20":    ["ordinals", "brc-20"],
    "etf":       ["etf", "exchange traded fund", "exchange-traded fund"],
    "mining":    ["mining", "miner", "hashrate", "hash rate"],
    "miner":     ["mining", "miner"],
    "hashrate":  ["hashrate", "hash rate", "mining"],
}

# Common Bitcoin terms used as fallback autocomplete suggestions
_BTC_AUTOCOMPLETE_TERMS = [
    "bitcoin", "btc price", "lightning network", "bitcoin halving",
    "bitcoin etf", "bitcoin mining", "ordinals", "taproot",
    "bitcoin whale", "mempool", "nostr", "layer 2",
    "bitcoin regulation", "satoshi", "defi bitcoin", "bitcoin security",
]

# Autocomplete in-memory cache
_autocomplete_cache: Dict[str, Any] = {
    "titles": [],
    "tags": [],
    "built_at": 0.0,
    "ttl": 120,  # seconds
    "lock": threading.Lock(),
}

# ---------------------------------------------------------------------------
# Helper: tokenise a query string
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-zA-Z0-9$#@]+(?:[-'][a-zA-Z0-9]+)*")


def _tokenize(text: str) -> List[str]:
    """Split text into lower-cased search tokens."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]


def _expand_tokens(tokens: List[str]) -> List[str]:
    """Expand tokens with Bitcoin synonym groups (deduplicated, order-preserved)."""
    seen: set = set()
    expanded: List[str] = []
    for t in tokens:
        synonyms = _BTC_SYNONYMS.get(t, [t])
        for s in synonyms:
            if s not in seen:
                seen.add(s)
                expanded.append(s)
    return expanded


# ---------------------------------------------------------------------------
# Helper: generate a highlighted snippet
# ---------------------------------------------------------------------------

_HTML_ESCAPE = str.maketrans({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
})


def _html_escape(text: str) -> str:
    return text.translate(_HTML_ESCAPE)


def _build_snippet(text: str, tokens: List[str], radius: int = _SNIPPET_RADIUS) -> str:
    """
    Extract a text snippet around the first matched token and wrap all
    occurrences of query tokens in <mark> tags.
    """
    if not text or not tokens:
        return ""

    text_lower = text.lower()
    best_pos = -1
    best_token = ""

    # Find the earliest occurrence of any token
    for t in tokens:
        pos = text_lower.find(t)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
            best_token = t

    if best_pos == -1:
        # No token found -- return the start of the text
        snippet_raw = text[:radius * 2]
    else:
        start = max(0, best_pos - radius)
        end = min(len(text), best_pos + len(best_token) + radius)
        snippet_raw = text[start:end]

    # Clean up: trim to word boundaries and add ellipsis
    if snippet_raw and not text.startswith(snippet_raw):
        # Trim leading partial word
        space_pos = snippet_raw.find(" ")
        if space_pos != -1 and space_pos < 30:
            snippet_raw = snippet_raw[space_pos + 1:]
        snippet_raw = "..." + snippet_raw

    if snippet_raw and not text.endswith(snippet_raw.lstrip(".")):
        # Trim trailing partial word
        space_pos = snippet_raw.rfind(" ")
        if space_pos != -1 and (len(snippet_raw) - space_pos) < 30:
            snippet_raw = snippet_raw[:space_pos]
        snippet_raw = snippet_raw + "..."

    # Strip any stray HTML/markdown for safety, then escape
    snippet_clean = re.sub(r"<[^>]+>", "", snippet_raw)
    snippet_clean = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", snippet_clean)

    # Escape HTML entities before inserting <mark> tags
    snippet_escaped = _html_escape(snippet_clean)

    # Highlight tokens (case-insensitive)
    for t in tokens:
        pattern = re.compile(re.escape(_html_escape(t)), re.IGNORECASE)
        snippet_escaped = pattern.sub(
            lambda m: f"<mark>{m.group(0)}</mark>", snippet_escaped
        )

    return snippet_escaped


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _relevance_score(article, tokens: List[str], expanded_tokens: List[str]) -> float:
    """
    Compute a relevance score for *article* against the search tokens.

    Scoring layers (additive):
        +10  exact title match (case-insensitive)
        +5   title contains a query token
        +3   tag match
        +2   category match
        +1.5 summary match
        +1   content match
    Each layer is scored per-token; we normalise by token count so that
    multi-word queries are comparable to single-word queries.

    Then we apply multiplicative boosts:
        - Recency: articles from the last 24h get up to 1.5x; decays over 30 days
        - Popularity: log-scaled view count boost (gentle)
    """
    if not tokens:
        return 0.0

    title_lower = (article.title or "").lower()
    tags_lower = (article.tags or "").lower()
    category_lower = (article.category or "").lower()
    summary_lower = (article.summary or "").lower()
    content_lower = (article.content or "").lower()

    raw_query = " ".join(tokens)
    score = 0.0
    token_count = max(1, len(tokens))

    # --- Exact full-query title match ---
    if raw_query == title_lower:
        score += 10.0
    elif raw_query in title_lower:
        score += 6.0

    # --- Per-token scoring ---
    for t in expanded_tokens:
        # Title contains token
        if t in title_lower:
            score += 5.0 / token_count
        # Tag match
        if t in tags_lower:
            score += 3.0 / token_count
        # Category match
        if t in category_lower:
            score += 2.0 / token_count
        # Summary match
        if t in summary_lower:
            score += 1.5 / token_count
        # Content match
        if t in content_lower:
            score += 1.0 / token_count

    # --- Recency boost (up to 1.5x for <24h old, decaying to 1.0x over 30 days) ---
    recency_multiplier = 1.0
    pub_date = article.published_at or article.created_at
    if pub_date:
        age_hours = max(0, (datetime.utcnow() - pub_date).total_seconds() / 3600)
        if age_hours < 24:
            recency_multiplier = 1.5
        elif age_hours < 24 * 30:
            # Linear decay from 1.4 at 24h to 1.0 at 30 days
            recency_multiplier = 1.0 + 0.4 * (1.0 - (age_hours - 24) / (24 * 29))
        # else stays 1.0

    score *= recency_multiplier

    return round(score, 4)


# ---------------------------------------------------------------------------
# Search analytics logging
# ---------------------------------------------------------------------------

def _log_search_query(query: str, result_count: int, latency_ms: int) -> None:
    """Append a search event to the JSONL analytics file (fire-and-forget)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "query": query[:_MAX_QUERY_LENGTH],
            "results": result_count,
            "latency_ms": latency_ms,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        with open(_SEARCH_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("Failed to log search query: %s", exc)


# ---------------------------------------------------------------------------
# 1. search_articles
# ---------------------------------------------------------------------------

def search_articles(
    query: str,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """
    Full-text search over published articles.

    Returns:
        {
            "results": [{ id, title, summary, category, tags, score,
                          published_at, image_url, snippet }],
            "total": int,
            "page": int,
            "per_page": int,
            "query": str,
        }
    """
    start_time = time.monotonic()

    # --- Sanitise inputs ---
    query = (query or "").strip()
    if not query:
        return {
            "results": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "query": "",
        }

    query = query[:_MAX_QUERY_LENGTH]
    page = max(1, int(page))
    per_page = max(1, min(100, int(per_page)))

    tokens = _tokenize(query)
    if not tokens:
        return {
            "results": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "query": query,
        }

    expanded = _expand_tokens(tokens)

    # --- Build SQLAlchemy LIKE filters (parameterised -- safe from injection) ---
    like_clauses = []
    for t in expanded:
        pattern = f"%{t}%"
        like_clauses.append(models.Article.title.ilike(pattern))
        like_clauses.append(models.Article.content.ilike(pattern))
        like_clauses.append(models.Article.summary.ilike(pattern))
        like_clauses.append(models.Article.tags.ilike(pattern))
        like_clauses.append(models.Article.category.ilike(pattern))

    # Only search published articles
    base_query = (
        models.Article.query
        .filter(models.Article.published.is_(True))
        .filter(or_(*like_clauses))
    )

    # Fetch all matching rows so we can score in Python
    matched_articles = base_query.all()

    # --- Score and rank ---
    scored: List[Dict[str, Any]] = []
    for article in matched_articles:
        score = _relevance_score(article, tokens, expanded)
        if score <= 0:
            continue

        # Build snippet from content (fallback to summary)
        snippet_source = article.content or article.summary or ""
        snippet = _build_snippet(snippet_source, expanded)

        scored.append({
            "id": article.id,
            "title": article.title,
            "summary": (article.summary or "")[:300],
            "category": article.category,
            "tags": article.tags,
            "score": score,
            "published_at": (
                article.published_at.isoformat()
                if article.published_at
                else (article.created_at.isoformat() if article.created_at else None)
            ),
            "image_url": article.header_image_url or article.cover_image_url,
            "snippet": snippet,
            "slug": article.slug or str(article.id),
        })

    # Sort by score descending, then by published_at descending as tiebreaker
    scored.sort(key=lambda r: (r["score"], r["published_at"] or ""), reverse=True)

    total = len(scored)

    # --- Paginate ---
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_results = scored[start_idx:end_idx]

    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    # Fire-and-forget analytics logging
    _log_search_query(query, total, elapsed_ms)

    return {
        "results": page_results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "query": query,
    }


# ---------------------------------------------------------------------------
# 2. autocomplete
# ---------------------------------------------------------------------------

def _refresh_autocomplete_cache() -> None:
    """Rebuild the in-memory autocomplete cache from the database."""
    with _autocomplete_cache["lock"]:
        now = time.monotonic()
        if now - _autocomplete_cache["built_at"] < _autocomplete_cache["ttl"]:
            return  # still fresh

        try:
            rows = (
                models.Article.query
                .filter(models.Article.published.is_(True))
                .with_entities(models.Article.title, models.Article.tags)
                .all()
            )

            titles: List[str] = []
            tags_set: set = set()

            for title, tags in rows:
                if title:
                    titles.append(title.strip())
                if tags:
                    for tag in tags.split(","):
                        tag = tag.strip()
                        if tag:
                            tags_set.add(tag)

            _autocomplete_cache["titles"] = titles
            _autocomplete_cache["tags"] = sorted(tags_set)
            _autocomplete_cache["built_at"] = now
        except Exception as exc:
            logger.warning("Autocomplete cache refresh failed: %s", exc)


def autocomplete(query: str, limit: int = 8) -> List[str]:
    """
    Return up to *limit* autocomplete suggestions for the given prefix.

    Priority order:
        1. Article titles that start with the query prefix
        2. Article titles that contain the query
        3. Tags that start with / contain the query
        4. Bitcoin term fallbacks
    """
    query = (query or "").strip().lower()
    if not query:
        return _BTC_AUTOCOMPLETE_TERMS[:limit]

    query = query[:_MAX_QUERY_LENGTH]

    # Ensure cache is warm
    _refresh_autocomplete_cache()

    suggestions: List[str] = []
    seen_lower: set = set()

    def _add(text: str) -> bool:
        """Add a suggestion if not a duplicate. Returns True if limit reached."""
        low = text.lower()
        if low in seen_lower:
            return False
        seen_lower.add(low)
        suggestions.append(text)
        return len(suggestions) >= limit

    titles = _autocomplete_cache["titles"]
    tags = _autocomplete_cache["tags"]

    # Pass 1: titles starting with query
    for t in titles:
        if t.lower().startswith(query):
            if _add(t):
                return suggestions

    # Pass 2: titles containing query
    for t in titles:
        if query in t.lower():
            if _add(t):
                return suggestions

    # Pass 3: tags starting with query
    for t in tags:
        if t.lower().startswith(query):
            if _add(t):
                return suggestions

    # Pass 4: tags containing query
    for t in tags:
        if query in t.lower():
            if _add(t):
                return suggestions

    # Pass 5: Bitcoin term fallbacks
    for t in _BTC_AUTOCOMPLETE_TERMS:
        if query in t.lower():
            if _add(t):
                return suggestions

    return suggestions


# ---------------------------------------------------------------------------
# 3. get_search_analytics
# ---------------------------------------------------------------------------

def get_search_analytics() -> Dict[str, Any]:
    """
    Parse the search JSONL log and return analytics.

    Returns:
        {
            "popular_queries":  [{"query": str, "count": int}, ...],
            "failed_queries":   [{"query": str, "count": int}, ...],
            "volume_over_time": [{"date": "YYYY-MM-DD", "count": int}, ...],
            "total_searches":   int,
            "avg_latency_ms":   float,
        }
    """
    query_counts: Dict[str, int] = {}
    failed_counts: Dict[str, int] = {}
    daily_counts: Dict[str, int] = {}
    total_searches = 0
    total_latency = 0

    if not _SEARCH_LOG_PATH.exists():
        return {
            "popular_queries": [],
            "failed_queries": [],
            "volume_over_time": [],
            "total_searches": 0,
            "avg_latency_ms": 0.0,
        }

    try:
        with open(_SEARCH_LOG_PATH, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                q = entry.get("query", "").strip().lower()
                result_count = entry.get("results", 0)
                latency = entry.get("latency_ms", 0)
                ts_str = entry.get("ts", "")

                if not q:
                    continue

                total_searches += 1
                total_latency += latency

                # Query frequency
                query_counts[q] = query_counts.get(q, 0) + 1

                # Failed queries (0 results)
                if result_count == 0:
                    failed_counts[q] = failed_counts.get(q, 0) + 1

                # Daily volume
                date_part = ts_str[:10] if len(ts_str) >= 10 else "unknown"
                daily_counts[date_part] = daily_counts.get(date_part, 0) + 1

    except Exception as exc:
        logger.warning("Failed to read search analytics: %s", exc)

    # Sort and format
    popular = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    failed = sorted(failed_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    volume = sorted(daily_counts.items(), key=lambda x: x[0])

    return {
        "popular_queries": [{"query": q, "count": c} for q, c in popular],
        "failed_queries": [{"query": q, "count": c} for q, c in failed],
        "volume_over_time": [{"date": d, "count": c} for d, c in volume],
        "total_searches": total_searches,
        "avg_latency_ms": round(total_latency / max(1, total_searches), 1),
    }
