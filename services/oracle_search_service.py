from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import models
from services import ollama_runtime

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]{2,}", re.IGNORECASE)


@dataclass
class SearchHit:
    source: str
    title: str
    body: str
    score: float
    ref_id: int
    created_at: str


def _tokens(text: str) -> List[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


def _score(query_tokens: List[str], text: str) -> float:
    if not query_tokens:
        return 0.0
    hay = " " + (text or "").lower() + " "
    score = 0.0
    for t in query_tokens:
        if f" {t} " in hay:
            score += 1.8
        elif t in hay:
            score += 1.0
    return score / max(1, len(query_tokens))


def _collect_records(limit_per_source: int = 80) -> List[SearchHit]:
    out: List[SearchHit] = []

    briefs = (
        models.DailyBrief.query.order_by(models.DailyBrief.created_at.desc())
        .limit(limit_per_source)
        .all()
    )
    for b in briefs:
        out.append(
            SearchHit(
                source="daily_brief",
                title=(b.headline or "daily brief"),
                body=(b.body or "")[:1800],
                score=0.0,
                ref_id=b.id,
                created_at=(b.created_at.isoformat() if b.created_at else ""),
            )
        )

    posts = (
        models.CuratedPost.query.order_by(models.CuratedPost.submitted_at.desc())
        .limit(limit_per_source)
        .all()
    )
    for p in posts:
        out.append(
            SearchHit(
                source="value_stream",
                title=(p.title or p.original_url or "curated post"),
                body=(p.content_preview or p.original_url or "")[:1800],
                score=0.0,
                ref_id=p.id,
                created_at=(p.submitted_at.isoformat() if p.submitted_at else ""),
            )
        )

    queue = (
        models.SentryQueue.query.order_by(models.SentryQueue.created_at.desc())
        .limit(limit_per_source)
        .all()
    )
    for q in queue:
        out.append(
            SearchHit(
                source="sentry_queue",
                title=f"sentry {q.status}",
                body=(q.content or "")[:1800],
                score=0.0,
                ref_id=q.id,
                created_at=(q.created_at.isoformat() if q.created_at else ""),
            )
        )
    return out


def _special_partner_hint(question: str) -> List[Dict]:
    q = (question or "").lower()
    if "mortgage" not in q and "partner" not in q:
        return []
    partners = (
        models.AffiliatePartner.query.filter(models.AffiliatePartner.is_active.is_(True))
        .order_by(models.AffiliatePartner.created_at.desc())
        .limit(20)
        .all()
    )
    ranked: List[Dict] = []
    for p in partners:
        cat = (p.category or "").lower()
        s = 0.2
        if "mortgage" in cat:
            s += 2.5
        if any(k in cat for k in ("lending", "borrow", "finance")):
            s += 1.5
        ranked.append(
            {
                "source": "affiliate_partner",
                "title": p.name or p.slug,
                "excerpt": (p.benefit or "")[:220],
                "score": round(s, 3),
                "ref_id": p.id,
                "url": p.url,
                "created_at": p.created_at.isoformat() if p.created_at else "",
            }
        )
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:5]


def semantic_search(question: str, limit: int = 8) -> Dict:
    started = datetime.utcnow()
    query_tokens = _tokens(question)
    records = _collect_records()

    for r in records:
        joined = f"{r.title}\n{r.body}"
        r.score = _score(query_tokens, joined)

    hits = [r for r in records if r.score > 0]
    hits.sort(key=lambda r: (r.score, r.created_at), reverse=True)

    result_rows = [
        {
            "source": h.source,
            "title": h.title,
            "excerpt": (h.body[:260] + "...") if len(h.body) > 260 else h.body,
            "score": round(h.score, 3),
            "ref_id": h.ref_id,
            "created_at": h.created_at,
        }
        for h in hits[:limit]
    ]
    result_rows.extend(_special_partner_hint(question))
    result_rows = sorted(result_rows, key=lambda x: x.get("score", 0), reverse=True)[:limit]

    context = "\n\n".join(
        [f"[{r['source']}] {r['title']}\n{r['excerpt']}" for r in result_rows[:6]]
    )
    prompt = (
        "answer the operator question with high-signal brevity.\n"
        "use only provided context. if uncertain, say so.\n"
        "tone: tactical, lowercase.\n\n"
        f"question: {question}\n\ncontext:\n{context}"
    )
    answer = ""
    available = set(ollama_runtime.list_models())
    preferred_order = [
        "llama3.1",
        "llama3.1:70b",
        "llama3.3",
        "llama3.2:3b",
    ]
    selected_model = next((m for m in preferred_order if m in available), "")
    if selected_model:
        answer = ollama_runtime.generate(
            prompt,
            preferred_model=selected_model,
            options={"temperature": 0.25, "num_predict": 180},
            timeout=7,
        )
    if not answer:
        answer = (
            "local oracle summary: "
            + (result_rows[0]["excerpt"] if result_rows else "no strong consensus found in current local data.")
        )

    elapsed_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
    return {
        "question": question,
        "answer": answer.strip(),
        "hits": result_rows,
        "latency_ms": elapsed_ms,
    }

