"""
CONTENT QUALITY SCORING SYSTEM
=================================
Multi-dimensional quality scoring for generated content.
Uses multiple LLMs as judges to evaluate content before it goes live.

Score Dimensions:
  - Factual accuracy (cross-reference claims)
  - Writing quality (readability, engagement)
  - Originality (not too similar to sources)
  - Brand voice consistency
  - SEO optimization
  - Social media potential (virality signals)

Usage:
    from services.video_engine.quality_scorer import QualityScorer
    scorer = QualityScorer()
    result = scorer.score_article(title, content, sources)
    if result["overall_score"] < 0.6:
        block_publication()
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("QualityScorer")

QUALITY_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "video_engine" / "quality_scores.json"

# Scoring thresholds
PUBLISH_THRESHOLD = 0.60   # Minimum score to auto-publish
WARNING_THRESHOLD = 0.50   # Below this, flag for manual review
BLOCK_THRESHOLD = 0.35     # Below this, auto-block

# Dimension weights
DIMENSION_WEIGHTS = {
    "factual_accuracy": 0.25,
    "writing_quality": 0.20,
    "originality": 0.15,
    "brand_voice": 0.15,
    "seo_optimization": 0.10,
    "social_potential": 0.15,
}

# Brand voice guidelines
BRAND_VOICE = {
    "tone": "authoritative but accessible, tech-savvy but not elitist",
    "perspective": "Bitcoin-first, sovereignty-focused, analytically grounded",
    "avoid": "hype, moonboy language, FUD, clickbait, generic crypto coverage",
    "style": "data-driven, source-backed, concise paragraphs, clear structure",
    "structure": "TL;DR, The Report, The Bitcoin Lens, Transactor Intelligence, Sources",
}

QUALITY_JUDGE_PROMPT = """You are a content quality judge for Protocol Pulse, a Bitcoin intelligence platform.

Evaluate this content on 6 dimensions. Score each 0.0 (terrible) to 1.0 (excellent).

BRAND VOICE GUIDELINES:
- Tone: {tone}
- Perspective: {perspective}
- Avoid: {avoid}
- Style: {style}

CONTENT TO EVALUATE:
Title: {title}
---
{content}
---

Sources referenced: {sources}

SCORE EACH DIMENSION (return ONLY valid JSON):
{{
    "factual_accuracy": {{
        "score": 0.0-1.0,
        "reasoning": "brief explanation"
    }},
    "writing_quality": {{
        "score": 0.0-1.0,
        "reasoning": "brief explanation"
    }},
    "originality": {{
        "score": 0.0-1.0,
        "reasoning": "brief explanation"
    }},
    "brand_voice": {{
        "score": 0.0-1.0,
        "reasoning": "brief explanation"
    }},
    "seo_optimization": {{
        "score": 0.0-1.0,
        "reasoning": "brief explanation"
    }},
    "social_potential": {{
        "score": 0.0-1.0,
        "reasoning": "brief explanation"
    }},
    "overall_notes": "any critical issues or suggestions"
}}"""


class QualityScorer:
    """Multi-dimensional content quality scorer."""

    def __init__(self):
        self._scores_log: List[Dict] = []

    def score_article(self, title: str, content: str,
                     sources: List[str] = None,
                     use_multi_llm: bool = True) -> Dict:
        """Score an article across all quality dimensions.

        Args:
            title: Article headline
            content: Full article text
            sources: List of source URLs/names referenced
            use_multi_llm: If True, use multiple LLMs for consensus

        Returns:
            {
                "overall_score": 0.0-1.0,
                "dimensions": {...},
                "decision": "publish" | "review" | "block",
                "judges": ["claude", "grok"],
                "suggestions": [...]
            }
        """
        sources_str = ", ".join(sources[:10]) if sources else "none provided"

        # Run scoring judges
        judge_results = []

        if use_multi_llm:
            # Try multiple LLMs
            for judge_name, judge_func in [
                ("claude", self._judge_claude),
                ("grok", self._judge_grok),
                ("openai", self._judge_openai),
            ]:
                try:
                    result = judge_func(title, content, sources_str)
                    if result:
                        judge_results.append({
                            "judge": judge_name,
                            "scores": result
                        })
                except Exception as e:
                    logger.warning(f"Judge {judge_name} failed: {e}")

        # Fallback: heuristic scoring
        if not judge_results:
            heuristic = self._heuristic_score(title, content, sources)
            judge_results.append({
                "judge": "heuristic",
                "scores": heuristic
            })

        # Merge judge scores (average across judges per dimension)
        merged = self._merge_scores(judge_results)

        # Calculate overall weighted score
        overall = sum(
            merged.get(dim, {}).get("score", 0) * weight
            for dim, weight in DIMENSION_WEIGHTS.items()
        )

        # Decision
        if overall >= PUBLISH_THRESHOLD:
            decision = "publish"
        elif overall >= WARNING_THRESHOLD:
            decision = "review"
        else:
            decision = "block"

        # Generate suggestions
        suggestions = self._generate_suggestions(merged, overall)

        result = {
            "title": title[:100],
            "overall_score": round(overall, 3),
            "decision": decision,
            "dimensions": merged,
            "judges": [j["judge"] for j in judge_results],
            "judge_count": len(judge_results),
            "suggestions": suggestions,
            "thresholds": {
                "publish": PUBLISH_THRESHOLD,
                "warning": WARNING_THRESHOLD,
                "block": BLOCK_THRESHOLD,
            },
            "scored_at": datetime.utcnow().isoformat(),
        }

        # Log the score
        self._log_score(result)

        return result

    def _judge_claude(self, title: str, content: str,
                     sources_str: str) -> Optional[Dict]:
        """Score using Claude."""
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            return None

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            prompt = QUALITY_JUDGE_PROMPT.format(
                title=title, content=content[:5000],
                sources=sources_str, **BRAND_VOICE
            )
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",  # Use Haiku for cost efficiency
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return self._parse_judge_response(resp.content[0].text)
        except Exception as e:
            logger.warning(f"Claude judge error: {e}")
            return None

    def _judge_grok(self, title: str, content: str,
                   sources_str: str) -> Optional[Dict]:
        """Score using Grok."""
        api_key = os.environ.get("XAI_API_KEY", "").strip()
        if not api_key:
            return None

        try:
            import openai
            client = openai.OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
            prompt = QUALITY_JUDGE_PROMPT.format(
                title=title, content=content[:5000],
                sources=sources_str, **BRAND_VOICE
            )
            resp = client.chat.completions.create(
                model="grok-3-mini-fast",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3,
            )
            return self._parse_judge_response(resp.choices[0].message.content)
        except Exception as e:
            logger.warning(f"Grok judge error: {e}")
            return None

    def _judge_openai(self, title: str, content: str,
                     sources_str: str) -> Optional[Dict]:
        """Score using OpenAI."""
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            prompt = QUALITY_JUDGE_PROMPT.format(
                title=title, content=content[:5000],
                sources=sources_str, **BRAND_VOICE
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-efficient
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3,
            )
            return self._parse_judge_response(resp.choices[0].message.content)
        except Exception as e:
            logger.warning(f"OpenAI judge error: {e}")
            return None

    def _parse_judge_response(self, text: str) -> Optional[Dict]:
        """Parse JSON response from judge LLM."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                # Validate structure
                for dim in DIMENSION_WEIGHTS:
                    if dim in data and isinstance(data[dim], dict):
                        score = data[dim].get("score", 0)
                        data[dim]["score"] = max(0.0, min(1.0, float(score)))
                return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse judge response: {e}")
        return None

    def _heuristic_score(self, title: str, content: str,
                        sources: List[str] = None) -> Dict:
        """Heuristic-based scoring when no LLMs are available."""
        scores = {}

        # Factual accuracy: based on source citation
        source_count = len(sources) if sources else 0
        has_links = bool(re.findall(r'https?://', content))
        scores["factual_accuracy"] = {
            "score": min(1.0, 0.3 + source_count * 0.15 + (0.2 if has_links else 0)),
            "reasoning": f"{source_count} sources, {'has' if has_links else 'no'} links"
        }

        # Writing quality: based on length, structure, readability
        word_count = len(content.split())
        has_headers = bool(re.findall(r'^#{1,3}\s|<h[1-3]>', content, re.M))
        has_paragraphs = content.count('\n\n') > 2
        wq_score = 0.3
        if 300 <= word_count <= 2000:
            wq_score += 0.3
        if has_headers:
            wq_score += 0.2
        if has_paragraphs:
            wq_score += 0.2
        scores["writing_quality"] = {
            "score": min(1.0, wq_score),
            "reasoning": f"{word_count} words, headers={'yes' if has_headers else 'no'}"
        }

        # Originality: harder to assess without comparison
        scores["originality"] = {
            "score": 0.6,
            "reasoning": "Heuristic default — needs LLM comparison"
        }

        # Brand voice: check for Bitcoin-specific content
        btc_keywords = ["bitcoin", "btc", "satoshi", "sovereignty", "protocol",
                        "network", "mining", "hash", "block"]
        keyword_hits = sum(1 for kw in btc_keywords if kw.lower() in content.lower())
        bv_score = min(1.0, 0.2 + keyword_hits * 0.1)
        scores["brand_voice"] = {
            "score": bv_score,
            "reasoning": f"{keyword_hits}/9 brand keywords found"
        }

        # SEO: check for title in content, meta-like structure
        title_words = set(title.lower().split())
        content_lower = content.lower()
        title_presence = sum(1 for w in title_words if w in content_lower) / max(len(title_words), 1)
        seo_score = 0.3 + title_presence * 0.4 + (0.3 if has_headers else 0)
        scores["seo_optimization"] = {
            "score": min(1.0, seo_score),
            "reasoning": f"Title keyword match: {title_presence:.0%}"
        }

        # Social potential: engaging title + content length
        title_len = len(title)
        has_numbers = bool(re.search(r'\d', title))
        has_question = '?' in title
        sp_score = 0.3
        if 30 <= title_len <= 70:
            sp_score += 0.2
        if has_numbers:
            sp_score += 0.15
        if has_question:
            sp_score += 0.15
        if word_count >= 300:
            sp_score += 0.2
        scores["social_potential"] = {
            "score": min(1.0, sp_score),
            "reasoning": f"Title: {title_len} chars, numbers={has_numbers}"
        }

        return scores

    def _merge_scores(self, judge_results: List[Dict]) -> Dict:
        """Merge scores from multiple judges (average per dimension)."""
        merged = {}
        for dim in DIMENSION_WEIGHTS:
            scores = []
            reasonings = []
            for jr in judge_results:
                dim_data = jr["scores"].get(dim, {})
                if isinstance(dim_data, dict) and "score" in dim_data:
                    scores.append(dim_data["score"])
                    reasonings.append(
                        f"[{jr['judge']}] {dim_data.get('reasoning', '')}")

            if scores:
                merged[dim] = {
                    "score": round(sum(scores) / len(scores), 3),
                    "judge_scores": scores,
                    "reasoning": "; ".join(reasonings)
                }
            else:
                merged[dim] = {"score": 0.5, "reasoning": "No judge data"}

        return merged

    def _generate_suggestions(self, scores: Dict, overall: float) -> List[str]:
        """Generate improvement suggestions based on scores."""
        suggestions = []

        for dim, data in scores.items():
            score = data.get("score", 0)
            if score < 0.5:
                suggestion_map = {
                    "factual_accuracy": "Add more source citations and cross-reference key claims",
                    "writing_quality": "Improve structure with clear headers and shorter paragraphs",
                    "originality": "Add more original analysis instead of summarizing sources",
                    "brand_voice": "Align more with Bitcoin-first, sovereignty-focused perspective",
                    "seo_optimization": "Include target keywords in headers and improve meta structure",
                    "social_potential": "Make the headline more engaging with specific data points",
                }
                suggestions.append(suggestion_map.get(dim, f"Improve {dim}"))

        if overall < PUBLISH_THRESHOLD:
            suggestions.insert(0, f"Overall score {overall:.2f} below publish threshold {PUBLISH_THRESHOLD}")

        return suggestions

    def _log_score(self, result: Dict):
        """Log quality score to file."""
        try:
            scores = []
            if QUALITY_DB_PATH.exists():
                try:
                    scores = json.loads(QUALITY_DB_PATH.read_text())
                except Exception:
                    pass

            scores.append(result)
            # Keep last 500 scores
            scores = scores[-500:]

            QUALITY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            QUALITY_DB_PATH.write_text(json.dumps(scores, indent=2, default=str))
        except Exception as e:
            logger.debug(f"Quality score logging failed: {e}")


class QualityGatekeeper:
    """Auto-gate content based on quality scores."""

    def __init__(self, scorer: QualityScorer = None):
        self.scorer = scorer or QualityScorer()

    def evaluate_for_publication(self, title: str, content: str,
                                sources: List[str] = None) -> Dict:
        """Evaluate content and return publication decision.

        Returns:
            {
                "approved": bool,
                "decision": "publish" | "review" | "block",
                "score": 0.0-1.0,
                "gate_details": {...}
            }
        """
        result = self.scorer.score_article(title, content, sources)

        return {
            "approved": result["decision"] == "publish",
            "decision": result["decision"],
            "score": result["overall_score"],
            "gate_details": result,
        }
