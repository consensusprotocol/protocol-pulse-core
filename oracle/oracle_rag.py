"""
RAG retrieval for Oracle dialogue engine.
Uses simple TF-IDF similarity (no external vector DB needed).
Indexes knowledge base on startup, retrieves top-3 chunks per query.
"""

import os
import json
import math
import re
import logging
from pathlib import Path

logger = logging.getLogger("oracle_rag")

KB_DIR = Path(__file__).parent / 'knowledge_base'
_index = {}   # word -> {chunk_id -> tf-idf score}
_chunks = {}  # chunk_id -> {"text": str, "source": str, "title": str}
_built = False

# Stopwords to skip in indexing (common English words that don't carry meaning)
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "not", "no", "nor",
    "so", "if", "then", "than", "that", "this", "these", "those", "it",
    "its", "you", "your", "we", "our", "they", "their", "he", "she", "his",
    "her", "my", "me", "him", "them", "us", "who", "what", "which", "when",
    "where", "how", "why", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "very", "just",
    "about", "above", "after", "before", "between", "into", "through",
    "during", "also", "over", "under", "again", "further", "once",
})


def _tokenize(text):
    """Tokenize text into lowercase alphanumeric words, filtering stopwords."""
    tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _load_articles_from_db():
    """Try to load articles from the Protocol Pulse DB into the articles index."""
    try:
        import sqlite3
        db_path = Path(__file__).parent.parent / 'instance' / 'protocol_pulse.db'
        if not db_path.exists():
            return []

        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute(
            "SELECT title, content FROM articles "
            "WHERE content IS NOT NULL AND length(content) > 100 "
            "ORDER BY created_at DESC LIMIT 20"
        )
        chunks = []
        for title, content in c.fetchall():
            # Chunk into ~200 word segments
            words = content.split()
            for i in range(0, len(words), 200):
                segment = " ".join(words[i:i + 200])
                chunks.append({
                    "title": title,
                    "source": "protocol_pulse_articles",
                    "text": f"{title}: {segment}"[:400],
                })
        conn.close()
        return chunks
    except Exception as e:
        logger.debug(f"Article loading failed: {e}")
        return []


def build_index():
    """Load all knowledge base files and build TF-IDF index."""
    global _index, _chunks, _built
    _index = {}
    _chunks = {}

    if not KB_DIR.exists():
        _built = True
        return

    chunk_id = 0
    for f in sorted(KB_DIR.glob('*.json')):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load {f}: {e}")
            continue

        file_chunks = data.get('chunks', [])

        # For articles index, try dynamic DB load if empty
        if f.stem == 'articles_index' and not file_chunks:
            file_chunks = _load_articles_from_db()

        for item in file_chunks:
            text = item.get('text', '')
            tokens = _tokenize(text)
            if len(tokens) < 5:
                continue
            _chunks[chunk_id] = {
                'text': text[:400],
                'source': item.get('source', f.stem),
                'title': item.get('title', ''),
            }
            # Term frequency
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for t, count in tf.items():
                if t not in _index:
                    _index[t] = {}
                _index[t][chunk_id] = count / len(tokens)
            chunk_id += 1

    # Apply IDF weighting
    N = max(chunk_id, 1)
    for word, docs in _index.items():
        idf = math.log(N / (len(docs) + 1))
        for cid in docs:
            _index[word][cid] *= idf

    _built = True
    logger.info(f"[RAG] Indexed {chunk_id} chunks from {len(list(KB_DIR.glob('*.json')))} files")


def retrieve(query: str, top_k: int = 3) -> list:
    """Return top_k most relevant chunks for the query."""
    if not _built:
        build_index()

    if not _chunks:
        return []

    tokens = _tokenize(query)
    scores = {}
    for t in tokens:
        if t in _index:
            for cid, score in _index[t].items():
                scores[cid] = scores.get(cid, 0) + score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for cid, score in ranked[:top_k]:
        if score > 0.01:
            results.append(_chunks[cid])
    return results


# Build on import
build_index()
