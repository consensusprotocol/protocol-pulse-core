
"""
Claude-First Article Generation Service
========================================
Uses Claude (Anthropic) as the PRIMARY article generator.
Falls back to Gemini only if Claude fails.
Skips OpenAI entirely (quota issues).
"""

import os
import logging
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ClaudeArticleService:
    """
    Generates high-quality Bitcoin articles using Claude.
    
    Article Structure (6 sections, 1200+ words):
    1. TL;DR (3 bullets)
    2. The Report (main story)
    3. Exclusive Data Analysis
    4. The Bitcoin Lens (sovereignty angle)
    5. Transactor Intelligence (actionable insights)
    6. Sources
    """
    
    def __init__(self):
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        
        if self.anthropic_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.anthropic_key)
                logger.info("Claude article service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Claude: {e}")
    
    def _get_ground_truth_metrics(self) -> Dict[str, Any]:
        """Fetch real Bitcoin network metrics for accuracy."""
        try:
            import requests
            
            # Try blockchain.info first (more reliable)
            r = requests.get("https://blockchain.info/q/hashrate", timeout=10)
            if r.ok:
                # Returns in H/s, convert to EH/s
                hashrate_hs = float(r.text.strip())
                hashrate_eh = hashrate_hs / 1e18
                if hashrate_eh > 100:  # Sanity check
                    logger.info(f"Ground truth hashrate: {round(hashrate_eh, 2)} EH/s")
                    return {
                        "hashrate_eh": round(hashrate_eh, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            # Fallback to mempool.space
            r2 = requests.get("https://mempool.space/api/v1/mining/hashrate/1d", timeout=10)
            if r2.ok:
                data = r2.json()
                if data:
                    # Get the most recent entry
                    latest = data[-1] if isinstance(data, list) else data
                    hashrate_eh = latest.get("avgHashrate", 0) / 1e18
                    if hashrate_eh > 100:
                        logger.info(f"Ground truth hashrate (mempool): {round(hashrate_eh, 2)} EH/s")
                        return {
                            "hashrate_eh": round(hashrate_eh, 2),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
        except Exception as e:
            logger.warning(f"Could not fetch ground truth: {e}")
        
        # Conservative fallback - tell Claude to look up current data
        logger.warning("Using estimated hashrate - Claude should verify")
        return {"hashrate_eh": 650.0, "timestamp": datetime.utcnow().isoformat(), "estimated": True}
    
    def generate_article(self, topic: str, content_type: str = "breaking_news") -> Optional[Dict]:
        """
        Generate a complete article with all 6 sections.
        
        Returns:
            {
                "title": str,
                "content": str (HTML),
                "category": str,
                "tags": str,
                "word_count": int,
                "seo_title": str,
                "seo_description": str
            }
        """
        if not self.client:
            logger.error("Claude client not initialized")
            return self._fallback_to_gemini(topic, content_type)
        
        metrics = self._get_ground_truth_metrics()
        
        # The Cronkite-style editorial prompt
        system_prompt = """You are a senior investigative journalist for Protocol Pulse, a premium Bitcoin intelligence publication.

EDITORIAL VOICE:
- Cronkite-style: authoritative, measured, factual
- Bitcoin-first perspective (not crypto-bro, not maximalist preaching)
- Write for "transactors" - serious Bitcoin users who value sovereignty
- Dry wit acceptable, but substance over style

ACCURACY MANDATE:
- Use provided ground truth metrics when available
- Never fabricate statistics or quotes
- If uncertain, say "reports indicate" rather than stating as fact
- Current Bitcoin hashrate: {hashrate_eh} EH/s

HEADLINE STYLE:
- Question-based headlines for SEO (How, What, Why, Is, Will, Can)
- Or strong declarative statements
- NO clickbait, NO "You Won't Believe"
- Max 70 characters

STRUCTURE (MANDATORY - ALL 6 SECTIONS):
1. <div class="tldr-section"><h3>TL;DR</h3><ul> - 3 bullet points
2. <h2>The Report</h2> - Main story, 400-600 words
3. <h2>Exclusive Data Analysis</h2> - Charts context, metrics, 200-300 words
4. <h2>The Bitcoin Lens</h2> - Sovereignty/freedom angle, 200-300 words
5. <h2>Transactor Intelligence</h2> - Actionable insights, what to watch, 150-200 words
6. <h2>Sources</h2> - List of sources with links

MINIMUM: 1200 words total. This is non-negotiable.
""".format(**metrics)
        
        user_prompt = f"""Write a comprehensive article about:

TOPIC: {topic}

TYPE: {content_type}

Remember:
- All 6 sections required
- 1200+ words minimum
- Question-based headline preferred
- Use the ground truth hashrate: {metrics['hashrate_eh']} EH/s
- HTML formatting for all sections
- No placeholder text or "[insert here]" markers

Begin with the headline, then the full article."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            content = response.content[0].text if response.content else ""
            
            if not content or len(content) < 500:
                logger.warning("Claude returned insufficient content, trying Gemini")
                return self._fallback_to_gemini(topic, content_type)
            
            # Extract title and content
            lines = content.strip().split("\n")
            title = lines[0].strip().lstrip("#").strip() if lines else topic
            article_content = "\n".join(lines[1:]).strip() if len(lines) > 1 else content
            
            # Clean title
            title = re.sub(r'<[^>]+>', '', title)  # Remove HTML
            title = title.replace("**", "").strip('"').strip("'")
            
            word_count = len(re.sub(r'<[^>]+>', ' ', article_content).split())
            
            logger.info(f"Claude generated article: {word_count} words")
            
            return {
                "title": title[:100],
                "content": article_content,
                "category": self._determine_category(topic),
                "tags": "Bitcoin, Analysis, Intelligence",
                "word_count": word_count,
                "seo_title": title[:60],
                "seo_description": f"Protocol Pulse analysis: {topic[:100]}"
            }
            
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            return self._fallback_to_gemini(topic, content_type)
    
    def _fallback_to_gemini(self, topic: str, content_type: str) -> Optional[Dict]:
        """Fallback to Gemini if Claude fails."""
        if not self.gemini_key:
            logger.error("No Gemini key available for fallback")
            return None
        
        try:
            from pp_services.gemini_service import gemini_service
            
            prompt = f"""Write a comprehensive Bitcoin article about: {topic}

Required sections:
1. TL;DR (3 bullets)
2. The Report (main story, 500+ words)
3. Exclusive Data Analysis (200+ words)
4. The Bitcoin Lens (sovereignty angle, 200+ words)
5. Transactor Intelligence (actionable insights, 150+ words)
6. Sources

Use HTML formatting. Minimum 1200 words total."""

            content = gemini_service.generate_content(prompt)
            
            if content and len(content) > 500:
                lines = content.strip().split("\n")
                title = lines[0].strip().lstrip("#").strip() if lines else topic
                
                return {
                    "title": title[:100],
                    "content": content,
                    "category": self._determine_category(topic),
                    "tags": "Bitcoin, Analysis",
                    "word_count": len(content.split()),
                    "seo_title": title[:60],
                    "seo_description": f"Bitcoin analysis: {topic[:100]}"
                }
        except Exception as e:
            logger.error(f"Gemini fallback failed: {e}")
        
        return None
    
    def _determine_category(self, topic: str) -> str:
        """Determine article category from topic."""
        topic_lower = topic.lower()
        
        if any(w in topic_lower for w in ["mining", "hashrate", "difficulty", "miner"]):
            return "Mining"
        elif any(w in topic_lower for w in ["lightning", "layer 2", "l2", "payment"]):
            return "Lightning"
        elif any(w in topic_lower for w in ["regulation", "sec", "government", "legal"]):
            return "Regulation"
        elif any(w in topic_lower for w in ["etf", "institutional", "fund", "investment"]):
            return "Markets"
        elif any(w in topic_lower for w in ["privacy", "security", "self-custody"]):
            return "Privacy"
        else:
            return "Bitcoin"


# Singleton
claude_article_service = ClaudeArticleService()
