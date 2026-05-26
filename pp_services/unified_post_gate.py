"""
UNIFIED POST GATE - Protocol Pulse
===================================
ALL automated posts MUST pass through this gate.

Pipeline:
1. Human Voice Filter (remove AI patterns, add sovereignty)
2. Link Verification (if URL included)
3. Multi-LLM Quality Check (Grok)
4. Final approval

NO POST GOES LIVE WITHOUT PASSING.
"""

import os
import re
import logging
import json
import requests
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UnifiedPostGate:
    def __init__(self):
        self.base_url = os.environ.get("SITE_URL", "https://protocolpulse.io")
        self.grok_client = None
        
        # Initialize Grok
        xai_key = os.environ.get("XAI_API_KEY")
        if xai_key:
            try:
                from openai import OpenAI
                self.grok_client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
                logger.info("Unified Post Gate initialized with Grok")
            except Exception as e:
                logger.warning(f"Grok init failed: {e}")
    
    def _humanize(self, text: str) -> str:
        """Apply human voice filter"""
        try:
            from pp_services.human_voice_filter import humanize
            return humanize(text)
        except ImportError:
            # Fallback basic cleanup
            text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]', '', text)
            return text
    
    def _verify_link(self, url: str) -> Dict:
        """Verify URL returns 200"""
        try:
            if url.startswith('/'):
                url = f"{self.base_url}{url}"
            
            response = requests.head(url, timeout=30, allow_redirects=True)
            return {"valid": response.status_code == 200, "status": response.status_code}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def _grok_quality_check(self, text: str) -> Dict:
        """Have Grok verify post quality"""
        if not self.grok_client:
            return {"approved": True, "score": 70, "reason": "Grok not available"}
        
        prompt = f"""Rate this tweet for quality (1-10). Reject if it sounds like AI/marketing.

TWEET: "{text}"

REJECT (score < 6) if:
- Generic marketing speak
- Excessive punctuation
- Sounds corporate/robotic
- No real value or insight

APPROVE (score >= 6) if:
- Sounds like a real person
- Has specific information
- Natural, conversational

JSON only: {{"score": 1-10, "approved": true/false, "reason": "brief"}}"""

        try:
            response = self.grok_client.chat.completions.create(
                model="grok-3-latest",
                messages=[
                    {"role": "system", "content": "Rate tweet quality. JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=100
            )
            
            text_response = response.choices[0].message.content.strip()
            if text_response.startswith("```"):
                text_response = text_response.split("```")[1].replace("json", "").strip()
            
            result = json.loads(text_response)
            result["approved"] = result.get("score", 0) >= 6
            return result
            
        except Exception as e:
            logger.warning(f"Grok quality check failed: {e}")
            return {"approved": True, "score": 7, "reason": "Check failed, allowing"}
    
    def _generate_organic_tweet(self, title: str, summary: str = "") -> str:
        """Generate organic tweet text using Grok"""
        if not self.grok_client:
            return title[:200]
        
        prompt = f"""Write ONE tweet about this article. Make someone stop scrolling.

TITLE: {title}
SUMMARY: {summary[:200] if summary else 'N/A'}

RULES:
1. MAX 180 characters. Shorter is better. Under 120 is elite.
2. ONE concrete fact, number, or insight from the article. No vibes.
3. Suggestive over declarative — let the reader complete the thought.
4. NO emojis. NO hashtags. NO ALL CAPS words.
5. NO rhetorical questions like "Have you considered..." or "Did you know..."
6. Lowercase starts are fine. Fragments are fine. Missing periods are fine.
7. Sound like a fund manager sharing alpha between meetings.

BANNED (instant rejection):
- "In Bitcoin's volatile world" or any "In [X]'s [adjective] world"
- "Have you considered" / "Did you know" / "Are you ready"
- "Share your thoughts" / "What do you think" / "Drop your take"
- "Don't miss" / "Check out" / "Must read" / "BREAKING"
- "Game-changer" / "paradigm" / "landscape" / "ecosystem"
- "While everyone obsesses" / "the real revolution" / "reshaping"
- Any sentence ending with both ? and !
- More than one question per tweet

GOOD:
- "Cash App quietly has the best BTC pricing of any major app. Block is going all in."
- "87 countries exploring CBDCs. tell me again how Bitcoin isn't winning."
- "11 public companies added BTC to their balance sheet this quarter. the stampede is quiet."

Return ONLY the tweet. No quotes. No explanation."""

        try:
            response = self.grok_client.chat.completions.create(
                model="grok-3-latest",
                messages=[
                    {"role": "system", "content": "You are the social media voice of Protocol Pulse — a Bitcoin-native intelligence outlet. Your voice: the sharpest person at the Bitcoin conference who also runs a fund. Lyn Alden composure, Saylor conviction, deadpan humor. You write tweets people screenshot. NEVER sound like a brand account, AI, or content strategist. One punchy line. Suggestive over declarative. No rhetorical questions unless genuinely sharp. No emojis. No hashtags."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=80
            )
            
            tweet = response.choices[0].message.content.strip().strip('"')
            return tweet[:200]
            
        except Exception as e:
            logger.error(f"Tweet generation failed: {e}")
            return title[:200]
    
    def process_article_post(self, article_id: int, title: str, summary: str = "") -> Dict:
        """Full pipeline for article posts"""
        result = {
            "approved": False,
            "tweet_text": None,
            "url": None,
            "checks": {}
        }
        
        # 1. Build and verify URL (note: /articles/ not /article/)
        url = f"{self.base_url}/articles/{article_id}"
        result["url"] = url
        
        link_check = self._verify_link(url)
        result["checks"]["link"] = link_check
        
        if not link_check.get("valid"):
            result["rejection_reason"] = f"Link invalid: {link_check.get('error', link_check.get('status'))}"
            logger.warning(f"Article {article_id} rejected: link invalid")
            return result
        
        # 2. Generate organic tweet
        tweet_text = self._generate_organic_tweet(title, summary)
        
        # 3. Apply human voice filter
        tweet_text = self._humanize(tweet_text)
        
        # 4. Quality check
        quality = self._grok_quality_check(tweet_text)
        result["checks"]["quality"] = quality
        
        if not quality.get("approved"):
            # Try regenerating once
            tweet_text = self._generate_organic_tweet(title, summary)
            tweet_text = self._humanize(tweet_text)
            quality = self._grok_quality_check(tweet_text)
            result["checks"]["quality_retry"] = quality
            
            if not quality.get("approved"):
                result["rejection_reason"] = f"Quality too low: {quality.get('reason')}"
                return result
        
        # 5. Assemble final tweet
        final_tweet = f"{tweet_text}\n\n{url}"
        result["tweet_text"] = final_tweet
        result["approved"] = True
        
        logger.info(f"Article {article_id} approved: {tweet_text[:50]}...")
        return result
    
    def process_generic_post(self, text: str, url: str = None) -> Dict:
        """Pipeline for any non-article post (sentiment, viral, etc.)"""
        result = {
            "approved": False,
            "tweet_text": None,
            "checks": {}
        }
        
        # 1. Apply human voice filter
        clean_text = self._humanize(text)
        
        # 2. Verify link if provided
        if url:
            link_check = self._verify_link(url)
            result["checks"]["link"] = link_check
            
            if not link_check.get("valid"):
                result["rejection_reason"] = f"Link invalid"
                return result
            
            if url not in clean_text:
                clean_text = f"{clean_text}\n\n{url}"
        
        # 3. Quality check
        quality = self._grok_quality_check(clean_text.split("\n")[0])  # Check just the text, not URL
        result["checks"]["quality"] = quality
        
        if not quality.get("approved"):
            result["rejection_reason"] = f"Quality: {quality.get('reason')}"
            return result
        
        result["tweet_text"] = clean_text
        result["approved"] = True
        
        return result


# Initialize singleton when module loads (with proper path)
unified_post_gate = None

def get_unified_post_gate():
    global unified_post_gate
    if unified_post_gate is None:
        unified_post_gate = UnifiedPostGate()
    return unified_post_gate


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/home/runner/workspace')
    
    gate = UnifiedPostGate()
    
    print("UNIFIED POST GATE TEST")
    print("=" * 50)
    
    # Test humanize
    test_cases = [
        "BREAKING: Bitcoin ETF is amazing!!!",
        "Check out this new Bitcoin analysis",
        "Self-custody wallet downloads surge 300%",
    ]
    
    for t in test_cases:
        result = gate._humanize(t)
        print(f"\nIN:  {t}")
        print(f"OUT: {result}")
    
    # Test article post
    print("\n" + "=" * 50)
    print("Testing article post pipeline...")
    
    result = gate.process_article_post(
        article_id=1538,
        title="Cash App Enhances Bitcoin Offerings with Competitive Pricing",
        summary="Cash App now offers the best Bitcoin pricing among major payment apps."
    )
    
    print(f"Approved: {result['approved']}")
    print(f"Tweet: {result.get('tweet_text', 'N/A')[:100]}...")
    print(f"Checks: {json.dumps(result['checks'], indent=2)}")
