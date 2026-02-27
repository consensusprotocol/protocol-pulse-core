"""
Content Analyzer: scores incoming content from Twitter, Reddit, and websites on a 1–10 newsworthiness
scale using Gemini. Only content scoring 6+ (Twitter), 7+ (Reddit), or 8+ (websites) gets turned into
article drafts. Quality gate for the social monitoring pipeline.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Minimum score to pass the gate by source type (Replit spec)
MIN_SCORE_TWITTER = 6
MIN_SCORE_REDDIT = 7
MIN_SCORE_WEBSITE = 8


class ContentAnalyzer:
    def __init__(self):
        self._gemini = None
        self._openai = None

    def _get_gemini(self):
        if self._gemini is None:
            try:
                from services.gemini_service import gemini_service
                self._gemini = gemini_service
            except Exception as e:
                logger.warning("ContentAnalyzer: Gemini not available: %s", e)
        return self._gemini

    def _get_openai(self):
        if self._openai is None:
            try:
                from services.ai_service import AIService
                self._openai = AIService()
            except Exception as e:
                logger.warning("ContentAnalyzer: OpenAI not available: %s", e)
        return self._openai

    def score_newsworthiness(self, title: str, body: str, source_type: str = "website") -> Dict:
        """
        Score content on 1–10 newsworthiness for Protocol Pulse (Bitcoin/DeFi, transactor-relevant).
        source_type: 'twitter' | 'reddit' | 'website'.
        Returns: { score: int 1-10, passed_gate: bool, reason: str }.
        """
        prompt = f"""You are a senior editor for Protocol Pulse, a Bitcoin and DeFi intelligence outlet.

Score the following content for NEWSWORTHINESS (1-10) for our audience (transactors, sovereign stackers, operators).
Consider: relevance to Bitcoin/sound money, uniqueness, credibility, actionable intelligence, macro significance.

SOURCE TYPE: {source_type}
TITLE: {title}
BODY (excerpt): {body[:2000]}

Respond with JSON only: {{"score": <1-10>, "reason": "<one sentence>"}}"""

        try:
            gemini = self._get_gemini()
            if gemini:
                raw = gemini.generate_content(prompt, system_prompt="")
            else:
                ai = self._get_openai()
                raw = ai.generate_content_openai(prompt) if ai else None
            if not raw:
                return {"score": 0, "passed_gate": False, "reason": "Scoring unavailable"}
            import json
            text = raw.strip()
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            data = json.loads(text)
            score = int(data.get("score", 0))
            reason = data.get("reason", "")
            min_score = {
                "twitter": MIN_SCORE_TWITTER,
                "reddit": MIN_SCORE_REDDIT,
                "website": MIN_SCORE_WEBSITE,
            }.get(source_type.lower(), MIN_SCORE_WEBSITE)
            passed = score >= min_score
            return {"score": score, "passed_gate": passed, "reason": reason}
        except Exception as e:
            logger.warning("score_newsworthiness failed: %s", e)
            return {"score": 0, "passed_gate": False, "reason": str(e)}

    def should_generate_article(self, title: str, body: str, source_type: str = "website") -> bool:
        """Convenience: return True if content passes the gate for article generation."""
        result = self.score_newsworthiness(title, body, source_type)
        return result.get("passed_gate", False)


content_analyzer = ContentAnalyzer()
