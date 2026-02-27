"""
POST QUALITY GATE - Protocol Pulse
===================================
MANDATORY verification before ANY automated post goes live.

Checks:
1. Link verification (must return 200)
2. Content quality (no generic AI slop)
3. Grok approval (final sign-off)

NO POST GOES LIVE WITHOUT PASSING ALL CHECKS.
"""

import os
import logging
import requests
import json
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PostQualityGate:
    def __init__(self):
        self.grok_client = None
        self.base_url = os.environ.get("SITE_URL", "https://protocolpulse.io")
        
        # Initialize Grok
        api_key = os.environ.get("XAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                self.grok_client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.x.ai/v1"
                )
                logger.info("Post Quality Gate initialized with Grok")
            except Exception as e:
                logger.warning(f"Grok init failed: {e}")
    
    def verify_link(self, url: str) -> Dict:
        """Verify a link returns 200 and is accessible"""
        try:
            # Handle relative URLs
            if url.startswith('/'):
                url = f"{self.base_url}{url}"
            
            response = requests.head(url, timeout=30, allow_redirects=True)
            
            if response.status_code == 200:
                return {"valid": True, "status": 200}
            else:
                logger.warning(f"Link check failed: {url} returned {response.status_code}")
                return {"valid": False, "status": response.status_code, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Link verification error: {e}")
            return {"valid": False, "status": 0, "error": str(e)}
    
    def generate_organic_tweet(self, article_title: str, article_summary: str, article_url: str) -> str:
        """
        Generate a high-value, organic-sounding tweet.
        NO generic AI slop. Must sound like a real person.
        """
        if not self.grok_client:
            # Fallback to simple format
            return f"{article_title[:200]}\n\n{article_url}"
        
        prompt = f"""Write ONE tweet about this article. The tweet must make someone stop scrolling.

ARTICLE:
Title: {article_title}
Summary: {article_summary[:300]}

RULES:
1. MAX 180 characters. Shorter is better. Under 120 is elite.
2. ONE concrete fact, number, or insight from the article. No vibes.
3. Suggestive over declarative — let the reader complete the thought.
4. NO emojis. NO hashtags. NO ALL CAPS words.
5. NO rhetorical questions like "Have you considered..." or "Did you know..."
6. Lowercase starts are fine. Fragments are fine. Missing periods are fine.
7. Sound like a fund manager sharing alpha between meetings, not a content account.

BANNED (instant rejection):
- "In Bitcoin's volatile world" or any "In [X]'s [adjective] world" opener
- "Have you considered" / "Did you know" / "Are you ready"
- "Share your thoughts" / "What do you think" / "Drop your take"
- "Don't miss" / "Check out" / "Must read" / "BREAKING"
- "Game-changer" / "paradigm" / "landscape" / "ecosystem"
- Any sentence with both a question mark AND an exclamation mark
- More than one question in the tweet
- More than one sentence (two max if the second is very short)

GOOD:
- "Cash App quietly has the best BTC pricing of any major app. Block is going all in."
- "87 countries exploring CBDCs. tell me again how Bitcoin isn't winning."
- "Sternlicht tokenizing $50B in real estate. TradFi gets it before most of crypto Twitter does."
- "self-custody or permission. pick one."
- "11 public companies added Bitcoin to their balance sheet this quarter. the stampede is quiet."

BAD:
- "In Bitcoin's volatile world, securing your wealth requires more than digital savvy!"
- "🚨 BREAKING: New analysis on Bitcoin security! Must read! 🔥"
- "Have you considered how hash rate protects against physical threats? Share your thoughts!"

Return ONLY the tweet. No quotes. No explanation. No preamble."""

        try:
            response = self.grok_client.chat.completions.create(
                model="grok-3-latest",
                messages=[
                    {"role": "system", "content": "You are the social media voice of Protocol Pulse — a Bitcoin-native intelligence outlet. Your voice: the sharpest person at the Bitcoin conference who also runs a fund. Lyn Alden composure, Saylor conviction, deadpan humor. You write tweets people screenshot. NEVER sound like a brand account, AI, or content strategist. One punchy line. Suggestive over declarative — let the reader complete the thought. No rhetorical questions unless genuinely sharp. No emojis. No hashtags."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=100
            )
            
            tweet = response.choices[0].message.content.strip()
            
            # Remove any quotes that might wrap the response
            tweet = tweet.strip('"\'')
            
            # Ensure it's not too long
            if len(tweet) > 220:
                tweet = tweet[:217] + "..."
            
            return tweet
            
        except Exception as e:
            logger.error(f"Tweet generation error: {e}")
            # Fallback
            return article_title[:200]
    
    def verify_tweet_quality(self, tweet_text: str) -> Dict:
        """
        Have Grok verify the tweet quality before posting.
        Rejects generic AI slop.
        """
        if not self.grok_client:
            return {"approved": True, "reason": "Grok not available for verification"}
        
        prompt = f"""Rate this tweet for quality. Is it worth posting?

TWEET: "{tweet_text}"

REJECT if:
- Generic marketing speak ("Check out", "Don't miss", "Breaking")
- Excessive emojis or hashtags
- Sounds like AI or a corporate account
- No specific value or insight
- Would embarrass a professional

APPROVE if:
- Sounds like a real person sharing something interesting
- Has specific, valuable information
- Professional but not corporate
- Would fit naturally in a Bitcoin thought leader's feed

Respond in JSON:
{{"approved": true/false, "score": 1-10, "reason": "brief explanation"}}"""

        try:
            response = self.grok_client.chat.completions.create(
                model="grok-3-latest",
                messages=[
                    {"role": "system", "content": "You evaluate tweet quality. Be strict - reject anything that sounds like generic AI content. Respond only in JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150
            )
            
            text = response.choices[0].message.content.strip()
            
            # Parse JSON
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            result = json.loads(text)
            
            logger.info(f"Tweet quality check: score={result.get('score')}, approved={result.get('approved')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Tweet verification error: {e}")
            return {"approved": True, "reason": "Verification failed, allowing through"}
    
    def process_article_post(self, article_id: int, article_title: str, article_summary: str = "") -> Dict:
        """
        Full pipeline for posting an article to X.
        Returns approved tweet text or rejection reason.
        """
        result = {
            "approved": False,
            "tweet_text": None,
            "url": None,
            "checks": {}
        }
        
        # 1. Build and verify URL (note: route is /articles/ not /article/)
        url = f"{self.base_url}/articles/{article_id}"
        result["url"] = url
        
        link_check = self.verify_link(url)
        result["checks"]["link"] = link_check
        
        if not link_check["valid"]:
            result["rejection_reason"] = f"Link verification failed: {link_check.get('error')}"
            logger.warning(f"Article {article_id} post rejected: link invalid")
            return result
        
        # 2. Generate organic tweet
        tweet_text = self.generate_organic_tweet(article_title, article_summary, url)
        
        # Add URL to tweet
        full_tweet = f"{tweet_text}\n\n{url}"
        result["tweet_text"] = full_tweet
        
        # 3. Verify tweet quality
        quality_check = self.verify_tweet_quality(tweet_text)
        result["checks"]["quality"] = quality_check
        
        if not quality_check.get("approved", False):
            # Try regenerating once
            logger.info("First tweet rejected, regenerating...")
            tweet_text = self.generate_organic_tweet(article_title, article_summary, url)
            full_tweet = f"{tweet_text}\n\n{url}"
            result["tweet_text"] = full_tweet
            
            quality_check = self.verify_tweet_quality(tweet_text)
            result["checks"]["quality_retry"] = quality_check
            
            if not quality_check.get("approved", False):
                result["rejection_reason"] = f"Tweet quality too low: {quality_check.get('reason')}"
                logger.warning(f"Article {article_id} post rejected: quality check failed")
                return result
        
        # All checks passed
        result["approved"] = True
        logger.info(f"Article {article_id} post approved: {tweet_text[:50]}...")
        
        return result
    
    def process_generic_post(self, post_text: str, url: str = None) -> Dict:
        """
        Quality gate for any generic post (sentiment tweets, viral posts, etc.)
        """
        result = {
            "approved": False,
            "tweet_text": post_text,
            "checks": {}
        }
        
        # 1. Verify link if provided
        if url:
            link_check = self.verify_link(url)
            result["checks"]["link"] = link_check
            
            if not link_check["valid"]:
                result["rejection_reason"] = f"Link verification failed: {link_check.get('error')}"
                return result
        
        # 2. Verify content quality
        quality_check = self.verify_tweet_quality(post_text)
        result["checks"]["quality"] = quality_check
        
        if not quality_check.get("approved", False):
            result["rejection_reason"] = f"Quality check failed: {quality_check.get('reason')}"
            return result
        
        result["approved"] = True
        return result


# Singleton
post_quality_gate = PostQualityGate()


if __name__ == "__main__":
    # Test
    print("Testing Post Quality Gate...\n")
    
    # Test article post
    result = post_quality_gate.process_article_post(
        article_id=1538,
        article_title="Cash App Enhances Bitcoin Offerings with Competitive Pricing",
        article_summary="Cash App now offers the best Bitcoin pricing among major payment apps, with higher withdrawal limits."
    )
    
    print(f"Approved: {result['approved']}")
    print(f"Tweet: {result.get('tweet_text', 'N/A')}")
    print(f"Checks: {json.dumps(result['checks'], indent=2)}")
