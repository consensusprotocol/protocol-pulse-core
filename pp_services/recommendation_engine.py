"""
Recommendation Engine - Intelligent Article Recommendations for Protocol Pulse

Uses TF-IDF text similarity, tag overlap, category matching, recency weighting,
and diversity enforcement to surface relevant content for readers.

No external ML libraries required -- built on collections.Counter and math.
"""

import logging
import math
import re
import string
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app import db
from models import Article, PageView

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level cache for expensive computations
# ---------------------------------------------------------------------------
_tfidf_cache: Dict[str, object] = {
    "corpus_vectors": {},       # article_id -> tfidf vector (Counter)
    "idf_scores": {},           # term -> idf value
    "doc_count": 0,
    "built_at": 0.0,            # timestamp of last full rebuild
    "ttl": 300,                 # cache lives 5 minutes
}

# Stop words for Bitcoin / crypto / tech domain -- lightweight built-in list
_STOP_WORDS = frozenset(
    "a about above after again against all am an and any are aren't as at be "
    "because been before being below between both but by can't cannot could "
    "couldn't did didn't do does doesn't doing don't down during each few for "
    "from further get got had hadn't has hasn't have haven't having he he'd "
    "he'll he's her here here's hers herself him himself his how how's i i'd "
    "i'll i'm i've if in into is isn't it it's its itself let's me more most "
    "mustn't my myself no nor not of off on once only or other ought our ours "
    "ourselves out over own same shan't she she'd she'll she's should shouldn't "
    "so some such than that that's the their theirs them themselves then there "
    "there's these they they'd they'll they're they've this those through to "
    "too under until up very was wasn't we we'd we'll we're we've were weren't "
    "what what's when when's where where's which while who who's whom why why's "
    "with won't would wouldn't you you'd you'll you're you've your yours "
    "yourself yourselves also just like will can new one two even still get "
    "may much many well could said says using used use article read".split()
)


# ---------------------------------------------------------------------------
# Text processing helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, remove stop words, return token list."""
    if not text:
        return []
    text = text.lower()
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Replace non-alpha with space (keep hyphens inside words for terms like "proof-of-work")
    text = re.sub(r"[^a-z0-9\-]", " ", text)
    tokens = text.split()
    # Filter stop words and very short tokens
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _build_tf(tokens: List[str]) -> Counter:
    """Term frequency as raw counts."""
    return Counter(tokens)


def _cosine_similarity(vec_a: Counter, vec_b: Counter) -> float:
    """Compute cosine similarity between two Counter-based sparse vectors."""
    if not vec_a or not vec_b:
        return 0.0
    # Intersection of terms for dot product
    common_terms = set(vec_a.keys()) & set(vec_b.keys())
    if not common_terms:
        return 0.0

    dot = sum(vec_a[t] * vec_b[t] for t in common_terms)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# TF-IDF corpus builder (cached)
# ---------------------------------------------------------------------------

def _get_published_articles() -> List[Article]:
    """Fetch all published articles ordered by recency."""
    return (
        Article.query
        .filter_by(published=True)
        .order_by(Article.published_at.desc().nullslast())
        .all()
    )


def _rebuild_corpus_if_stale() -> None:
    """Rebuild the TF-IDF corpus vectors and IDF scores if the cache is stale."""
    now = time.time()
    if (
        _tfidf_cache["built_at"]
        and (now - _tfidf_cache["built_at"]) < _tfidf_cache["ttl"]
        and _tfidf_cache["doc_count"] > 0
    ):
        return  # cache still fresh

    articles = _get_published_articles()
    if not articles:
        return

    doc_count = len(articles)
    # document frequency: how many docs each term appears in
    df: Counter = Counter()
    corpus_tfs: Dict[int, Counter] = {}

    for article in articles:
        text = f"{article.title or ''} {article.title or ''} {article.content or ''}"
        tokens = _tokenize(text)
        tf = _build_tf(tokens)
        corpus_tfs[article.id] = tf
        # Count each unique term once per document
        for term in tf:
            df[term] += 1

    # IDF = log(N / df_t) with smoothing
    idf_scores: Dict[str, float] = {}
    for term, freq in df.items():
        idf_scores[term] = math.log((doc_count + 1) / (freq + 1)) + 1.0

    # Build TF-IDF vectors (tf * idf)
    corpus_vectors: Dict[int, Counter] = {}
    for art_id, tf in corpus_tfs.items():
        tfidf_vec = Counter()
        for term, count in tf.items():
            tfidf_vec[term] = count * idf_scores.get(term, 1.0)
        corpus_vectors[art_id] = tfidf_vec

    _tfidf_cache["corpus_vectors"] = corpus_vectors
    _tfidf_cache["idf_scores"] = idf_scores
    _tfidf_cache["doc_count"] = doc_count
    _tfidf_cache["built_at"] = now

    logger.info("Recommendation corpus rebuilt: %d articles indexed", doc_count)


def _invalidate_cache() -> None:
    """Force the next call to rebuild the corpus."""
    _tfidf_cache["built_at"] = 0.0


# ---------------------------------------------------------------------------
# Tag and category helpers
# ---------------------------------------------------------------------------

def _parse_tags(tags_str: Optional[str]) -> set:
    """Parse comma-separated tags string into a normalized set."""
    if not tags_str:
        return set()
    return {t.strip().lower() for t in tags_str.split(",") if t.strip()}


def _tag_overlap_score(tags_a: set, tags_b: set) -> float:
    """Jaccard-like overlap score for two tag sets."""
    if not tags_a or not tags_b:
        return 0.0
    intersection = tags_a & tags_b
    union = tags_a | tags_b
    return len(intersection) / len(union)


def _recency_weight(published_at: Optional[datetime], half_life_days: float = 30.0) -> float:
    """
    Exponential decay weighting based on article age.
    An article published today gets 1.0; one published half_life_days ago gets 0.5.
    """
    if not published_at:
        return 0.1  # unknown date gets minimal weight
    now = datetime.utcnow()
    age_days = max((now - published_at).total_seconds() / 86400, 0)
    return math.exp(-0.693 * age_days / half_life_days)  # ln(2) ~ 0.693


def _extract_subtopic(article: Article) -> str:
    """
    Extract a rough sub-topic label for diversity enforcement.
    Uses the first tag if available, otherwise the first significant word in the title.
    """
    tags = _parse_tags(article.tags)
    if tags:
        return sorted(tags)[0]
    if article.title:
        tokens = _tokenize(article.title)
        if tokens:
            return tokens[0]
    return article.category or "general"


# ---------------------------------------------------------------------------
# Article serializer
# ---------------------------------------------------------------------------

def _article_to_dict(article: Article, score: float = 0.0) -> dict:
    """Convert an Article model instance to a recommendation dict."""
    return {
        "id": article.id,
        "title": article.title,
        "summary": article.summary or "",
        "category": article.category or "",
        "tags": article.tags or "",
        "score": round(score, 4),
        "published_at": (
            article.published_at.isoformat() if article.published_at else None
        ),
        "image_url": getattr(article, "header_image_url", None) or None,
    }


# ---------------------------------------------------------------------------
# 1. Content-based recommendations for a given article
# ---------------------------------------------------------------------------

def get_recommendations(article_id: int, limit: int = 6) -> List[dict]:
    """
    Get content-based recommendations for a given article.

    Scoring formula per candidate:
        score = (0.50 * tfidf_similarity)
              + (0.20 * tag_overlap)
              + (0.10 * category_match)
              + (0.20 * recency_weight)

    After scoring, diversity enforcement caps articles from the same sub-topic
    at a maximum of 2 per result set.

    Returns a list of dicts sorted by descending score.
    """
    try:
        source = Article.query.get(article_id)
        if not source:
            logger.warning("Recommendation source article %d not found", article_id)
            return []

        _rebuild_corpus_if_stale()

        corpus_vectors = _tfidf_cache["corpus_vectors"]
        source_vec = corpus_vectors.get(article_id)
        source_tags = _parse_tags(source.tags)
        source_category = (source.category or "").lower().strip()

        candidates = (
            Article.query
            .filter(Article.published == True, Article.id != article_id)
            .order_by(Article.published_at.desc().nullslast())
            .limit(500)
            .all()
        )

        scored: List[Tuple[float, Article]] = []

        for candidate in candidates:
            # --- TF-IDF text similarity ---
            cand_vec = corpus_vectors.get(candidate.id)
            text_sim = _cosine_similarity(source_vec, cand_vec) if source_vec and cand_vec else 0.0

            # --- Tag overlap ---
            cand_tags = _parse_tags(candidate.tags)
            tag_score = _tag_overlap_score(source_tags, cand_tags)

            # --- Category match ---
            cand_category = (candidate.category or "").lower().strip()
            cat_score = 1.0 if (source_category and cand_category == source_category) else 0.0

            # --- Recency ---
            recency = _recency_weight(candidate.published_at)

            # --- Weighted composite score ---
            score = (
                0.50 * text_sim
                + 0.20 * tag_score
                + 0.10 * cat_score
                + 0.20 * recency
            )

            scored.append((score, candidate))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # --- Diversity enforcement ---
        # Cap at 2 articles per sub-topic to avoid monotonous recommendations.
        subtopic_counts: Counter = Counter()
        max_per_subtopic = 2
        results: List[dict] = []

        for score, candidate in scored:
            if len(results) >= limit:
                break
            subtopic = _extract_subtopic(candidate)
            if subtopic_counts[subtopic] >= max_per_subtopic:
                continue
            subtopic_counts[subtopic] += 1
            results.append(_article_to_dict(candidate, score))

        logger.info(
            "Generated %d recommendations for article %d",
            len(results), article_id,
        )
        return results

    except Exception as exc:
        logger.exception("Error generating recommendations for article %d: %s", article_id, exc)
        return []


# ---------------------------------------------------------------------------
# 2. Personalized recommendations (user-based or trending fallback)
# ---------------------------------------------------------------------------

def get_personalized(user_id: Optional[int] = None, limit: int = 10) -> List[dict]:
    """
    Get personalized article recommendations.

    If user_id is provided:
      - Analyze their PageView history to identify preferred categories and topics.
      - Recommend published articles they have not yet read, scored by alignment
        with their preferences and recency.

    If user_id is None or the user has no history:
      - Fall back to trending/popular articles (most-viewed in last 30 days).

    Returns a list of article dicts.
    """
    try:
        if user_id:
            results = _personalized_for_user(user_id, limit)
            if results:
                return results

        # Fallback: trending / popular articles
        return _trending_articles(limit)

    except Exception as exc:
        logger.exception("Error generating personalized recommendations: %s", exc)
        return []


def _personalized_for_user(user_id: int, limit: int) -> List[dict]:
    """Build personalized recs from a user's reading history."""
    # Fetch user's page views for article pages (path like /article/...)
    cutoff = datetime.utcnow() - timedelta(days=90)
    views = (
        PageView.query
        .filter(
            PageView.user_id == user_id,
            PageView.created_at >= cutoff,
            PageView.page_path.like("/article/%"),
        )
        .order_by(PageView.created_at.desc())
        .limit(200)
        .all()
    )

    if not views:
        return []

    # Extract article IDs the user has read
    read_article_ids: set = set()
    for view in views:
        # Extract numeric article id from path like /article/123 or /article/123/slug
        match = re.search(r"/article/(\d+)", view.page_path or "")
        if match:
            read_article_ids.add(int(match.group(1)))

    if not read_article_ids:
        return []

    # Load the articles the user has read to build a preference profile
    read_articles = Article.query.filter(Article.id.in_(read_article_ids)).all()
    if not read_articles:
        return []

    # Build preference profile: category counts and aggregated tag counts
    category_counts: Counter = Counter()
    tag_counts: Counter = Counter()

    for article in read_articles:
        if article.category:
            category_counts[article.category.lower().strip()] += 1
        for tag in _parse_tags(article.tags):
            tag_counts[tag] += 1

    # Normalize preference scores
    max_cat = max(category_counts.values()) if category_counts else 1
    max_tag = max(tag_counts.values()) if tag_counts else 1

    # Fetch candidate articles the user has NOT read
    candidates = (
        Article.query
        .filter(
            Article.published == True,
            ~Article.id.in_(read_article_ids),
        )
        .order_by(Article.published_at.desc().nullslast())
        .limit(300)
        .all()
    )

    scored: List[Tuple[float, Article]] = []

    for candidate in candidates:
        # Category preference score
        cand_cat = (candidate.category or "").lower().strip()
        cat_pref = category_counts.get(cand_cat, 0) / max_cat if cand_cat else 0.0

        # Tag preference score (average of matching tag scores)
        cand_tags = _parse_tags(candidate.tags)
        if cand_tags:
            tag_scores = [tag_counts.get(t, 0) / max_tag for t in cand_tags]
            tag_pref = sum(tag_scores) / len(tag_scores)
        else:
            tag_pref = 0.0

        # Recency boost
        recency = _recency_weight(candidate.published_at, half_life_days=14.0)

        # Composite personalization score
        score = (
            0.35 * cat_pref
            + 0.35 * tag_pref
            + 0.30 * recency
        )

        scored.append((score, candidate))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = [_article_to_dict(art, score) for score, art in scored[:limit]]

    logger.info(
        "Personalized recommendations for user %d: %d results "
        "(read %d articles, %d categories, %d unique tags)",
        user_id, len(results), len(read_article_ids),
        len(category_counts), len(tag_counts),
    )
    return results


def _trending_articles(limit: int) -> List[dict]:
    """
    Fallback: return trending articles based on recent page views.
    Joins PageView counts with Article recency for a blended trending score.
    """
    cutoff = datetime.utcnow() - timedelta(days=30)

    # Count page views per article path in the last 30 days
    view_counts = (
        db.session.query(
            PageView.page_path,
            db.func.count(PageView.id).label("view_count"),
        )
        .filter(
            PageView.created_at >= cutoff,
            PageView.page_path.like("/article/%"),
        )
        .group_by(PageView.page_path)
        .order_by(db.func.count(PageView.id).desc())
        .limit(100)
        .all()
    )

    # Map article IDs to view counts
    article_views: Dict[int, int] = {}
    for path, count in view_counts:
        match = re.search(r"/article/(\d+)", path or "")
        if match:
            art_id = int(match.group(1))
            article_views[art_id] = article_views.get(art_id, 0) + count

    if not article_views:
        # No view data -- just return the most recent published articles
        recent = (
            Article.query
            .filter_by(published=True)
            .order_by(Article.published_at.desc().nullslast())
            .limit(limit)
            .all()
        )
        return [_article_to_dict(a, score=0.0) for a in recent]

    # Load articles
    article_ids = list(article_views.keys())
    articles = Article.query.filter(
        Article.id.in_(article_ids),
        Article.published == True,
    ).all()
    articles_by_id = {a.id: a for a in articles}

    max_views = max(article_views.values()) if article_views else 1

    scored: List[Tuple[float, Article]] = []
    for art_id, view_count in article_views.items():
        article = articles_by_id.get(art_id)
        if not article:
            continue
        popularity = view_count / max_views
        recency = _recency_weight(article.published_at, half_life_days=14.0)
        score = 0.6 * popularity + 0.4 * recency
        scored.append((score, article))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_article_to_dict(art, score) for score, art in scored[:limit]]


# ---------------------------------------------------------------------------
# 3. Trending topics
# ---------------------------------------------------------------------------

def get_trending_topics(limit: int = 10) -> List[dict]:
    """
    Extract trending topics from recent articles (last 30 days).

    Analyzes titles and tags of published articles, scores each topic by
    a combination of frequency, recency, and associated page views.

    Returns a list of dicts: {topic, count, trending_score}.
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=30)

        recent_articles = (
            Article.query
            .filter(
                Article.published == True,
                db.or_(
                    Article.published_at >= cutoff,
                    db.and_(
                        Article.published_at.is_(None),
                        Article.created_at >= cutoff,
                    ),
                ),
            )
            .order_by(Article.published_at.desc().nullslast())
            .limit(200)
            .all()
        )

        if not recent_articles:
            return []

        # Collect page view counts for scoring boost
        view_counts = _get_article_view_counts(cutoff)

        # Extract topics from tags and titles
        topic_data: Dict[str, dict] = defaultdict(
            lambda: {"count": 0, "total_recency": 0.0, "total_views": 0}
        )

        for article in recent_articles:
            recency = _recency_weight(article.published_at, half_life_days=15.0)
            art_views = view_counts.get(article.id, 0)

            # Extract from tags
            tags = _parse_tags(article.tags)
            for tag in tags:
                topic_data[tag]["count"] += 1
                topic_data[tag]["total_recency"] += recency
                topic_data[tag]["total_views"] += art_views

            # Extract key terms from title (top 3 non-stop-word tokens)
            if article.title:
                title_tokens = _tokenize(article.title)
                # Use bigrams for more meaningful topic phrases
                for token in title_tokens[:5]:
                    if len(token) > 3:  # skip very short terms
                        topic_data[token]["count"] += 1
                        topic_data[token]["total_recency"] += recency * 0.5
                        topic_data[token]["total_views"] += art_views

        if not topic_data:
            return []

        # Score topics
        max_count = max(d["count"] for d in topic_data.values()) or 1
        max_views = max(d["total_views"] for d in topic_data.values()) or 1

        scored_topics: List[dict] = []
        for topic, data in topic_data.items():
            freq_score = data["count"] / max_count
            avg_recency = data["total_recency"] / data["count"] if data["count"] else 0
            view_score = data["total_views"] / max_views

            trending_score = (
                0.40 * freq_score
                + 0.30 * avg_recency
                + 0.30 * view_score
            )

            # Filter out topics that appear only once (noise)
            if data["count"] >= 2:
                scored_topics.append({
                    "topic": topic,
                    "count": data["count"],
                    "trending_score": round(trending_score, 4),
                })

        # Sort by trending score descending
        scored_topics.sort(key=lambda x: x["trending_score"], reverse=True)

        logger.info(
            "Trending topics: %d topics scored from %d recent articles",
            len(scored_topics[:limit]), len(recent_articles),
        )
        return scored_topics[:limit]

    except Exception as exc:
        logger.exception("Error computing trending topics: %s", exc)
        return []


def _get_article_view_counts(cutoff: datetime) -> Dict[int, int]:
    """Get page view counts per article ID since the cutoff date."""
    view_rows = (
        db.session.query(
            PageView.page_path,
            db.func.count(PageView.id).label("cnt"),
        )
        .filter(
            PageView.created_at >= cutoff,
            PageView.page_path.like("/article/%"),
        )
        .group_by(PageView.page_path)
        .all()
    )

    counts: Dict[int, int] = {}
    for path, cnt in view_rows:
        match = re.search(r"/article/(\d+)", path or "")
        if match:
            art_id = int(match.group(1))
            counts[art_id] = counts.get(art_id, 0) + cnt
    return counts
