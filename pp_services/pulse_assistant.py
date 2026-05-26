"""
Pulse Assistant — RAG-powered AI chat for Protocol Pulse.

Searches published articles for relevant passages, builds context,
and generates conversational answers using available LLM providers.
Falls back gracefully when no API keys are configured.
"""

import hashlib
import json
import logging
import math
import os
import re
import time
import threading
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_CONTEXT_CHARS = 6000  # Max article context sent to LLM
_MAX_ARTICLES = 5  # Max articles to include in context
_CACHE_TTL = 300  # Cache article index for 5 minutes
_RATE_LIMIT_WINDOW = 60  # Rate limit window in seconds
_RATE_LIMIT_MAX = 10  # Max requests per window per visitor

# Rate limiter
_rate_limits: Dict[str, List[float]] = {}
_rate_lock = threading.Lock()

# Article index cache
_article_cache = {"data": None, "expires": 0}
_cache_lock = threading.Lock()

SYSTEM_PROMPT = """You are Alex, the Protocol Pulse AI analyst. You are an expert on Bitcoin,
cryptocurrency markets, blockchain technology, and the topics covered by Protocol Pulse articles.

Your personality:
- Knowledgeable but approachable — explain complex Bitcoin concepts clearly
- Data-driven — cite specific articles and facts when available
- Concise — keep answers focused and under 300 words unless depth is needed
- Honest — if you don't know something or the articles don't cover it, say so

When answering:
1. Use the provided article context to give accurate, sourced answers
2. Cite articles by title when referencing them: [Article Title](/articles/ID)
3. If no relevant articles exist, provide your general knowledge but note the limitation
4. For price predictions, always caveat that these are analytical perspectives, not financial advice
5. Use Markdown formatting for readability

You are NOT a generic chatbot. You specifically represent Protocol Pulse's editorial perspective
on Bitcoin and cryptocurrency intelligence."""


# ---------------------------------------------------------------------------
# Article retrieval (simple TF-IDF search)
# ---------------------------------------------------------------------------

def _get_article_index() -> List[Dict]:
    """Load and cache published articles for search."""
    now = time.time()
    with _cache_lock:
        if _article_cache["data"] is not None and now < _article_cache["expires"]:
            return _article_cache["data"]

    try:
        from app import db
        from models import Article

        with db.session.no_autoflush:
            articles = (
                Article.query
                .filter_by(published=True)
                .order_by(Article.published_at.desc())
                .limit(500)
                .all()
            )

        index = []
        for a in articles:
            content = a.content or ""
            summary = a.summary or ""
            title = a.title or ""
            tags = a.tags or ""
            category = a.category or ""

            # Build searchable text
            text = f"{title} {title} {tags} {category} {summary} {content}"
            # Simple tokenization
            tokens = re.findall(r'\b[a-z]{2,}\b', text.lower())

            index.append({
                "id": a.id,
                "title": title,
                "summary": summary[:300],
                "content": content,
                "category": category,
                "tags": tags,
                "published_at": (a.published_at or a.created_at or datetime.utcnow()).isoformat(),
                "tokens": Counter(tokens),
                "slug": getattr(a, "slug", None) or str(a.id),
            })

        with _cache_lock:
            _article_cache["data"] = index
            _article_cache["expires"] = now + _CACHE_TTL

        return index
    except Exception as e:
        logger.error("Failed to load article index: %s", e)
        return []


def _search_articles(query: str, limit: int = _MAX_ARTICLES) -> List[Dict]:
    """Search articles using TF-IDF similarity."""
    index = _get_article_index()
    if not index:
        return []

    # Tokenize query
    query_tokens = re.findall(r'\b[a-z]{2,}\b', query.lower())
    if not query_tokens:
        return []

    query_counter = Counter(query_tokens)

    # IDF from corpus
    doc_count = len(index)
    idf = {}
    for token in query_counter:
        df = sum(1 for doc in index if token in doc["tokens"])
        idf[token] = math.log((doc_count + 1) / (df + 1)) + 1

    # Score each document
    scored = []
    for doc in index:
        score = 0.0
        doc_tokens = doc["tokens"]
        doc_total = sum(doc_tokens.values()) or 1

        for token, qf in query_counter.items():
            if token in doc_tokens:
                tf = doc_tokens[token] / doc_total
                score += tf * idf.get(token, 1) * qf

        if score > 0:
            scored.append((score, doc))

    # Sort by score, take top results
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:limit]]


def _extract_relevant_passages(article: Dict, query: str, max_chars: int = 1200) -> str:
    """Extract the most relevant passages from an article for the given query."""
    content = article.get("content", "")
    if not content:
        return article.get("summary", "")[:max_chars]

    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', content)
    clean = re.sub(r'\s+', ' ', clean).strip()

    # Split into paragraphs
    paragraphs = [p.strip() for p in clean.split('\n') if len(p.strip()) > 40]
    if not paragraphs:
        paragraphs = [clean[i:i + 300] for i in range(0, len(clean), 300)]

    query_terms = set(re.findall(r'\b[a-z]{3,}\b', query.lower()))

    # Score paragraphs by query term overlap
    scored = []
    for p in paragraphs:
        p_lower = p.lower()
        hits = sum(1 for t in query_terms if t in p_lower)
        scored.append((hits, p))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top paragraphs up to max_chars
    result = []
    total = 0
    for _, p in scored:
        if total + len(p) > max_chars:
            break
        result.append(p)
        total += len(p)

    return "\n\n".join(result) if result else clean[:max_chars]


def _build_context(query: str) -> Tuple[str, List[Dict]]:
    """Build RAG context from article search results."""
    articles = _search_articles(query)
    if not articles:
        return "", []

    context_parts = []
    sources = []
    total_chars = 0

    for article in articles:
        passage = _extract_relevant_passages(article, query)
        if not passage:
            continue

        if total_chars + len(passage) > _MAX_CONTEXT_CHARS:
            break

        context_parts.append(
            f"=== Article: {article['title']} ===\n"
            f"Category: {article['category']} | Published: {article['published_at'][:10]}\n"
            f"{passage}"
        )
        sources.append({
            "id": article["id"],
            "title": article["title"],
            "category": article["category"],
            "slug": article["slug"],
            "url": f"/articles/{article['slug']}",
        })
        total_chars += len(passage)

    return "\n\n---\n\n".join(context_parts), sources


# ---------------------------------------------------------------------------
# LLM query
# ---------------------------------------------------------------------------

def _query_llm(messages: List[Dict]) -> Optional[str]:
    """Query available LLM with fallback chain: Anthropic -> OpenAI -> Grok -> Ollama."""

    # Try Anthropic Claude
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            # Extract system message
            system = ""
            user_messages = []
            for m in messages:
                if m["role"] == "system":
                    system = m["content"]
                else:
                    user_messages.append(m)

            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=user_messages,
            )
            return resp.content[0].text
        except Exception as e:
            logger.warning("Anthropic failed: %s", e)

    # Try OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning("OpenAI failed: %s", e)

    # Try Grok/xAI
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
            resp = client.chat.completions.create(
                model="grok-3-mini",
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning("xAI/Grok failed: %s", e)

    # Try local Ollama
    try:
        import requests
        ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
        resp = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": "llama3.1",
                "messages": messages,
                "stream": False,
            },
            timeout=30,
        )
        if resp.ok:
            return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        logger.warning("Ollama failed: %s", e)

    return None


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def _check_rate_limit(visitor_id: str) -> bool:
    """Returns True if the visitor is within rate limits."""
    now = time.time()
    with _rate_lock:
        if visitor_id not in _rate_limits:
            _rate_limits[visitor_id] = []

        # Clean old entries
        _rate_limits[visitor_id] = [
            t for t in _rate_limits[visitor_id] if now - t < _RATE_LIMIT_WINDOW
        ]

        if len(_rate_limits[visitor_id]) >= _RATE_LIMIT_MAX:
            return False

        _rate_limits[visitor_id].append(now)
        return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chat(query: str, visitor_id: str = "", history: Optional[List[Dict]] = None) -> Dict:
    """
    Process a chat query using RAG.

    Args:
        query: User's question
        visitor_id: Hashed IP or session ID for rate limiting
        history: Previous conversation messages [{role, content}, ...]

    Returns:
        {answer, sources, query, has_context, rate_limited}
    """
    if not query or not query.strip():
        return {
            "answer": "Please ask me a question about Bitcoin or cryptocurrency.",
            "sources": [],
            "query": "",
            "has_context": False,
            "rate_limited": False,
        }

    query = query.strip()[:500]  # Cap query length

    # Rate limit check
    if visitor_id and not _check_rate_limit(visitor_id):
        return {
            "answer": "You've reached the rate limit. Please wait a moment before asking another question.",
            "sources": [],
            "query": query,
            "has_context": False,
            "rate_limited": True,
        }

    # Build RAG context
    context, sources = _build_context(query)

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add context if available
    if context:
        messages.append({
            "role": "system",
            "content": f"ARTICLE CONTEXT (use this to answer the user's question):\n\n{context}",
        })

    # Add conversation history (last 6 messages)
    if history:
        for msg in history[-6:]:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"][:1000]})

    # Add current query
    messages.append({"role": "user", "content": query})

    # Query LLM
    answer = _query_llm(messages)

    if not answer:
        # Fallback: provide article-based answer without LLM
        if sources:
            answer = f"I found {len(sources)} relevant article(s) that may help:\n\n"
            for s in sources:
                answer += f"- **[{s['title']}]({s['url']})** ({s['category']})\n"
            answer += "\n*AI response unavailable — please check these articles directly.*"
        else:
            answer = (
                "I couldn't find specific articles about that topic, and the AI model "
                "is currently unavailable. Try browsing our [Intel Briefs](/articles) "
                "or ask a different question."
            )

    return {
        "answer": answer,
        "sources": sources,
        "query": query,
        "has_context": bool(context),
        "rate_limited": False,
    }
