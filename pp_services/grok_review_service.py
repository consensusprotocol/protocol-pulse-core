
"""
Grok Article Review & Fact-Check Service
=========================================
Uses xAI Grok to:
1. Fact-check articles against real-time knowledge before publishing
2. Verify claims about current events, people, policies, prices
3. Revise content when factual errors are found
4. Get real-time X sentiment for topics

MANDATORY GATE: Grok must approve every article before it goes live.
If Grok finds factual inaccuracies, it will REJECT and provide corrections.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class GrokReviewService:
    """
    Grok-powered article review, fact-checking, and revision service.
    Acts as the MANDATORY editorial gate before any article is published.
    """
    
    def __init__(self):
        self.api_key = os.environ.get("XAI_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.x.ai/v1"
                )
                logger.info("Grok review service initialized")
            except Exception as e:
                logger.warning(f"Grok client init failed: {e}")
    
    def review_article(self, title: str, content: str, topic: str = "") -> Dict:
        """
        Comprehensive real-time fact-check and editorial review.
        
        This is the MANDATORY gate before publishing. Grok uses its real-time
        knowledge to verify every factual claim in the article.
        
        Returns:
            {
                "approved": bool,
                "decision": "APPROVE" or "REJECT",
                "score": int (0-100),
                "issues": list,
                "suggestions": list,
                "fact_check_notes": str,
                "revised_title": str or None,
                "revised_content": str or None,
                "critical_errors": list
            }
        """
        if not self.client:
            logger.warning("GROK NOT CONFIGURED - articles will not be fact-checked. This is a risk.")
            return {
                "approved": False,
                "decision": "REJECT",
                "score": 0,
                "issues": ["Grok fact-checker not configured - cannot verify article accuracy"],
                "suggestions": [],
                "fact_check_notes": "Grok not configured - REJECTING by default for safety",
                "revised_title": None,
                "revised_content": None,
                "critical_errors": ["No fact-checking available"]
            }
        
        prompt = f"""You are the FINAL EDITORIAL GATE at Protocol Pulse, a Bitcoin intelligence publication.
Your job is to fact-check this article using your REAL-TIME knowledge before it goes live to readers.

TODAY'S DATE: {datetime.utcnow().strftime('%B %d, %Y')}
SOURCE CONTEXT: {topic}

=== IMPORTANT: TRUSTED SOURCE HANDLING ===
If the article cites a reputable source (Bitcoin Magazine, CoinDesk, Cointelegraph, Decrypt, The Block),
you should TRUST that the source article exists. Your job is to:
1. Check that our article ACCURATELY represents what the source says
2. Catch any ADDITIONS or FABRICATIONS we made beyond the source
3. Verify the article doesn't make up quotes, numbers, or claims not in the source
4. Flag if anything in OUR article contradicts known facts

DO NOT reject an article just because you can't independently verify the source article exists.
If we cite "Bitcoin Magazine reports X" - trust that Bitcoin Magazine reported X.
Only reject if OUR interpretation is clearly wrong or we've added false information.

=== CRITICAL FACT-CHECK REQUIREMENTS ===

1. CURRENT EVENTS VERIFICATION:
   - Are all claims about recent events ACTUALLY TRUE right now?
   - Has anything changed since this article was written?
   - Are the people, policies, and developments described ACCURATELY?
   - Example: If article says "X person nominated for Y position" — is that STILL true? Was it reversed?

2. PRICE & DATA ACCURACY:
   - Are Bitcoin/crypto prices approximately correct for today?
   - Are network statistics (hashrate, difficulty, etc.) in the right ballpark?
   - Are institutional flow numbers verifiable?

3. CLAIM VERIFICATION:
   - Every specific claim (legislation, appointments, product launches, partnerships) must be verifiable
   - Flag anything that sounds plausible but may be outdated, reversed, or fabricated
   
4. HEADLINE ACCURACY:
   - Does the headline accurately represent verified facts?
   - If the headline makes a claim that is wrong, provide a corrected headline

=== ARTICLE TO REVIEW ===

TITLE: {title}
TOPIC CONTEXT: {topic or 'Not provided'}

FULL CONTENT:
{content[:8000]}

=== YOUR RESPONSE ===

Respond in JSON format:
{{
    "approved": true or false,
    "score": 0-100 (below 70 = reject),
    "critical_errors": ["List any factually WRONG claims that would embarrass the publication"],
    "issues": ["List any concerns, inaccuracies, or things that need correction"],
    "suggestions": ["Improvements that would make the article stronger"],
    "fact_check_notes": "Detailed summary of your fact-checking findings. What did you verify? What couldn't you verify? What is wrong?",
    "revised_title": "Corrected title if the original is factually wrong, otherwise null",
    "revised_content_sections": "If you find factual errors in the content, describe what needs to change and how"
}}

DECISION RULES:
- If article FABRICATES information not in the cited source → approved: false, score < 50
- If article accurately represents its source but you can't independently verify → approved: TRUE, score 70-80
- If article is factually solid and matches source → approved: true, score 80+

CRITICAL: You are reviewing in February 2026. Bitcoin prices in the $60,000-$100,000 range are NORMAL.
Do NOT reject articles for mentioning current Bitcoin prices just because your training data is older.
If the article cites CoinDesk, Bitcoin Magazine, etc. saying "Bitcoin at $66,000" - that is REAL NEWS, not hallucination.

TRUST THE SOURCE. Only reject if WE added false information beyond what the source says.

Be thorough. Our readers trust us to be accurate."""

        try:
            response = self.client.chat.completions.create(
                model="grok-3-latest",
                messages=[
                    {"role": "system", "content": "You are a fact-checker for Protocol Pulse in February 2026. Your job is to verify articles accurately represent their sources. IMPORTANT: Today is February 2026. Bitcoin prices around $65,000-$70,000 are ACCURATE. TRUST reputable sources (CoinDesk, Bitcoin Magazine, Cointelegraph). Only reject if OUR article adds FALSE information beyond what the source says. Do NOT reject just because you cannot independently verify - trust the cited source. Respond only in valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2500
            )
            
            text = response.choices[0].message.content.strip()
            
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            result = json.loads(text)
            
            result.setdefault("approved", result.get("score", 0) >= 70 and not result.get("critical_errors"))
            result.setdefault("score", 70)
            result.setdefault("issues", [])
            result.setdefault("suggestions", [])
            result.setdefault("fact_check_notes", "Reviewed")
            result.setdefault("revised_title", None)
            result.setdefault("revised_content_sections", None)
            result.setdefault("critical_errors", [])
            
            if result.get("critical_errors"):
                result["approved"] = False
                if result.get("score", 100) >= 70:
                    result["score"] = 40
            
            result["decision"] = "APPROVE" if result["approved"] else "REJECT"
            
            logger.info(f"GROK REVIEW: score={result['score']}, decision={result['decision']}, "
                        f"critical_errors={len(result.get('critical_errors', []))}, "
                        f"title='{title[:50]}...'")
            
            if result.get("critical_errors"):
                for err in result["critical_errors"]:
                    logger.warning(f"  CRITICAL ERROR: {err}")
            
            if result.get("revised_title"):
                logger.info(f"  REVISED TITLE: {result['revised_title']}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Grok response not valid JSON: {e}")
            return {
                "approved": False,
                "decision": "REJECT",
                "score": 0,
                "issues": ["Grok review response could not be parsed"],
                "suggestions": [],
                "fact_check_notes": "Parse error - rejecting for safety",
                "revised_title": None,
                "critical_errors": ["Review parse failure"]
            }
        except Exception as e:
            logger.error(f"Grok review error: {e}")
            return {
                "approved": False,
                "decision": "REJECT",
                "score": 0,
                "issues": [str(e)],
                "suggestions": [],
                "fact_check_notes": f"Error: {e} - rejecting for safety",
                "revised_title": None,
                "critical_errors": [f"Review service error: {e}"]
            }
    
    def get_x_sentiment(self, topic: str = "Bitcoin") -> Dict:
        """
        Get real-time X (Twitter) sentiment using Grok's knowledge.
        """
        if not self.client:
            return {"sentiment": "neutral", "score": 0, "trending_topics": [], "summary": "Grok not configured"}
        
        prompt = f"""Analyze current X (Twitter) sentiment about: {topic}

Consider:
- What are major voices saying?
- Overall mood (bullish/bearish/neutral)?
- What events are driving discussion?
- Any notable debates?

Respond in JSON:
{{
    "sentiment": "bullish" | "bearish" | "neutral",
    "score": -100 to 100,
    "trending_topics": ["topic1", "topic2"],
    "key_discussions": ["description1", "description2"],
    "notable_accounts": ["@account1"],
    "summary": "2-3 sentence summary"
}}"""

        try:
            response = self.client.chat.completions.create(
                model="grok-3-latest",
                messages=[
                    {"role": "system", "content": "Social media analyst with X/Twitter access. JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "").strip()
            
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"Grok sentiment error: {e}")
            return {"sentiment": "neutral", "score": 0, "trending_topics": [], "summary": f"Error: {e}"}
    
    def suggest_trending_topics(self, count: int = 5) -> List[Dict]:
        """Get trending topic suggestions from X."""
        if not self.client:
            return []
        
        prompt = f"""Based on current X (Twitter) Bitcoin discussions, suggest {count} timely article topics.

For each:
1. Specific headline angle
2. Why it's relevant NOW
3. Key accounts discussing
4. Sentiment around it
5. Urgency (high/medium/low)

JSON format:
{{
    "topics": [
        {{
            "headline": "suggested headline",
            "angle": "specific angle",
            "relevance": "why now",
            "key_voices": ["@account1"],
            "sentiment": "bullish/bearish/neutral",
            "urgency": "high/medium/low"
        }}
    ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model="grok-3-latest",
                messages=[
                    {"role": "system", "content": "Bitcoin news editor with real-time X access."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "").strip()
            
            data = json.loads(text)
            return data.get("topics", [])
            
        except Exception as e:
            logger.error(f"Grok topics error: {e}")
            return []


grok_review_service = GrokReviewService()
