================================================================================
PROTOCOL PULSE — COMPLETE ARTICLE SYSTEM AUDIT
================================================================================

============================================================
FILE: services/content_engine.py (54848 chars)
============================================================
from __future__ import annotations
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
from app import db
from services.ai_service import AIService
from services.gemini_service import gemini_service

def strip_html_fences(content):
    """Remove ```html fences that Claude sometimes wraps around content."""
    if not content:
        return content
    content = content.strip()
    if content.startswith("```html"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


try:
    from services.grok_service import grok_service
except Exception:
    grok_service = None
try:
    from services.substack_service import SubstackService
except ModuleNotFoundError:
    SubstackService = None
try:
    from services.elevenlabs_service import ElevenLabsService
except ModuleNotFoundError:
    ElevenLabsService = None
try:
    from services.heygen_service import HeyGenService
except ModuleNotFoundError:
    HeyGenService = None
try:
    from substack import Api
    from substack.post import Post
except ModuleNotFoundError:
    Api = None
    Post = None


class ContentEngine:
    """
    Main content generation and publishing engine for Protocol Pulse
    Coordinates AI generation, Substack publishing, and cross-platform distribution
    """
    
    # EDITORIAL ACCURACY MANDATE - Applied to all generated content
    ACCURACY_MANDATE = """
=== EDITORIAL ACCURACY MANDATE - ZERO TOLERANCE FOR FABRICATION ===

🚨 CRITICAL DATE AWARENESS 🚨
TODAY'S DATE: February 18, 2026
YOU ARE WRITING NEWS, NOT PREDICTIONS.

ABSOLUTELY FORBIDDEN - WILL CAUSE IMMEDIATE REJECTION:
- DO NOT invent specific prices (e.g., "$67,400 on February 18")
- DO NOT invent specific dates for events (e.g., "on February 14, MicroStrategy...")
- DO NOT invent institutional holdings numbers (e.g., "214,400 BTC")
- DO NOT invent hashrate figures (e.g., "650 EH/s")
- DO NOT invent Fed decisions, regulatory rulings, or policy changes
- DO NOT write as if you have access to real-time data you don't have
- DO NOT use phrases like "as of today" or "currently trading at" with invented numbers

WHAT TO DO INSTEAD:
- Write about TRENDS and THEMES, not specific numbers
- Use phrases like "Bitcoin continues to..." or "The network has seen..."
- Reference PAST events that actually happened (pre-2025)
- Focus on PHILOSOPHY, PRINCIPLES, and ANALYSIS over data points
- If you need specific data, say "according to recent reports" without inventing numbers

SAFE TOPICS THAT WON'T GET REJECTED:
- Bitcoin's role in financial sovereignty
- Decentralization principles and why they matter
- Historical context (halving cycles, adoption milestones)
- Philosophical perspectives on sound money
- Educational content about how Bitcoin works
- Analysis of long-term trends (without specific predictions)

UNSAFE TOPICS THAT WILL GET REJECTED:
- Specific price movements with numbers
- Specific institutional purchases with amounts
- Specific hashrate or difficulty numbers
- Specific regulatory decisions with dates
- Any "breaking news" with invented details

BEFORE DRAFTING ANY ARTICLE, YOU MUST:
1. VERIFY the latest Bitcoin metrics (Difficulty, Hashrate, Price) via real-time data fetch ONLY
2. DO NOT rely on training data or assumptions about network conditions
3. State the ACTUAL current date and ACTUAL current metrics correctly
4. If real-time data is not provided in the source material, DO NOT report on metrics

STRICTLY PROHIBITED - IMMEDIATE REJECTION IF VIOLATED:
- NEVER claim "all-time high," "record high," "unprecedented," or "new record" for ANY Bitcoin metric
- NEVER hallucinate hashrate figures (e.g., do not invent "1.2 ZH/s" or any number)
- NEVER assume difficulty is increasing - it can DECREASE during miner stress periods
- NEVER fabricate "network strengthening" narratives without verified data
- NEVER use phrases like "surge," "soaring," or "record-breaking" for metrics you cannot verify

REALITY CHECK - As of January 2026:
- Bitcoin hashrate has DECLINED approximately 15% from its October 2024 peak
- Difficulty ATH: 155.9T (November 2025). Do not claim "all-time high" unless current difficulty exceeds this.
- Difficulty adjustments can be NEGATIVE (downward) - this is normal during miner stress
- The network is NOT always hitting "new highs" - it fluctuates based on miner economics

IF WRITING ABOUT BITCOIN NETWORK METRICS:
- Only report what is EXPLICITLY stated in verified source material
- If source says "difficulty adjustment" without direction, ask for clarification or omit
- Use qualified language: "according to [source]," "data from [provider] shows"
- If you cannot verify a claim, DO NOT MAKE IT

Hallucinating record highs when the network is experiencing miner stress is STRICTLY PROHIBITED and will result in content rejection.
"""

    REVIEW_PROMPT_LIVE_FACT = (
        "Review this article for accuracy, depth, and Bitcoin facts. "
        "Verify against current data: block reward is 3.125 BTC in 2026 (post-halving), not 6.25. "
        "Decision: APPROVE or REJECT. Reason: detailed. Score: 1-10."
    )
    
    def __init__(self):
        self.ai_service = AIService()
        self.substack_service = None
        self.elevenlabs_service = None
        self.heygen_service = None
        if SubstackService is not None:
            try:
                self.substack_service = SubstackService()
            except Exception as e:
                logging.warning("Substack service initialization failed: %s", e)
        else:
            logging.warning("Substack service not available (module not found)")
        if ElevenLabsService is not None:
            try:
                self.elevenlabs_service = ElevenLabsService()
            except Exception as e:
                logging.warning("ElevenLabs service initialization failed: %s", e)
        if HeyGenService is not None:
            try:
                self.heygen_service = HeyGenService()
            except Exception as e:
                logging.warning("HeyGen service initialization failed: %s", e)
        logging.info("Content Engine initialized")

    def _single_review_openai(self, title: str, content: str, topic: str) -> Dict:
        """One reviewer via OpenAI. Returns {decision, reason, score}."""
        import json
        try:
            prompt = f"""{self.REVIEW_PROMPT_LIVE_FACT}

TITLE: {title}
TOPIC: {topic}
CONTENT (excerpt): {(content or '')[:4000]}

Respond with JSON only: {{"decision": "APPROVE" or "REJECT", "reason": "...", "score": N}}"""
            response = self.ai_service.generate_content_openai(prompt)
            data = json.loads(response)
            return {
                "decision": (data.get("decision") or "REJECT").upper()[:7],
                "reason": data.get("reason", ""),
                "score": int(data.get("score", 0)),
                "provider": "openai",
            }
        except Exception as e:
            logging.warning("OpenAI review failed: %s", e)
            return {"decision": "ABSTAIN", "reason": str(e), "score": 0, "provider": "openai"}

    def _single_review_anthropic(self, title: str, content: str, topic: str) -> Dict:
        """One reviewer via Anthropic. Returns {decision, reason, score}."""
        import json
        try:
            prompt = f"""{self.REVIEW_PROMPT_LIVE_FACT}

TITLE: {title}
TOPIC: {topic}
CONTENT (excerpt): {(content or '')[:4000]}

Respond with JSON only: {{"decision": "APPROVE" or "REJECT", "reason": "...", "score": N}}"""
            response = self.ai_service.generate_content_anthropic(prompt)
            data = json.loads(response)
            return {
                "decision": (data.get("decision") or "REJECT").upper()[:7],
                "reason": data.get("reason", ""),
                "score": int(data.get("score", 0)),
                "provider": "anthropic",
            }
        exce

============================================================
FILE: services/article_automation.py (41506 chars)
============================================================
"""
Article Automation Service - FIXED
===================================
Now fetches REAL data before writing articles.
NO MORE HALLUCINATIONS.

Pipeline:
1. Fetch real news from multiple sources (RSS, web search, Reddit)
2. Pass real content to Claude to rewrite in our style
3. Grok fact-checks against the original source
4. Publish only if verified
"""

import os
import logging
import random
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from openai import OpenAI

def strip_html_fences(content):
    """Remove ```html fences that Claude sometimes wraps around content."""
    if not content:
        return content
    content = content.strip()
    if content.startswith("```html"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()



logger = logging.getLogger(__name__)

# Bitcoin news RSS feeds
NEWS_FEEDS = [
    "https://bitcoinmagazine.com/.rss/full/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
]



# ============================================================
# TOPIC DIVERSITY — prevent 15 articles about the same thing
# ============================================================
TOPIC_COOLDOWN_KEYWORDS = {
    "mining": ["mining", "miner", "hashrate", "hash rate", "hash power", "difficulty adjustment"],
    "price": ["price", "rally", "crash", "correction", "bull", "bear", "floor", "ath", "all-time"],
    "etf": ["etf", "blackrock", "fidelity", "grayscale", "spot bitcoin", "ishares"],
    "regulation": ["regulation", "sec", "congress", "law", "ban", "policy", "senator", "legislation"],
    "network": ["network", "resilience", "node", "mempool", "fee", "block size", "stress test"],
    "institutional": ["institution", "wall street", "fund", "bank", "corporate", "treasury", "microstrategy"],
    "lightning": ["lightning", "layer 2", "l2", "channel", "payment"],
    "stablecoin": ["stablecoin", "usdt", "usdc", "tether", "circle"],
    "defi": ["defi", "lending", "yield", "protocol", "liquidity"],
    "privacy": ["privacy", "surveillance", "kyc", "aml"],
    "energy": ["energy", "power", "grid", "renewable", "stranded"],
    "geopolitics": ["china", "russia", "el salvador", "uae", "brics", "tariff"],
    "self-custody": ["self-custody", "hardware wallet", "seed", "cold storage"],
    "exodus": ["exodus", "leaving", "flee", "migration", "capitulation"],
}

def _detect_topic(title):
    """Detect primary topic of an article from its title."""
    tl = title.lower()
    scores = {}
    for topic, kws in TOPIC_COOLDOWN_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in tl)
        if score > 0:
            scores[topic] = score
    return max(scores, key=scores.get) if scores else "general"

def _is_topic_oversaturated(title, max_same=1, lookback=15):
    """Check if topic covered too recently. Returns True to skip."""
    try:
        import models
        from app import db
        recent = models.Article.query.order_by(models.Article.id.desc()).limit(lookback).all()
        new_topic = _detect_topic(title)
        if new_topic == "general":
            return False
        count = sum(1 for a in recent if _detect_topic(a.title) == new_topic)
        if count >= max_same:
            import logging
            logging.getLogger("article_automation").info(
                f"TOPIC DIVERSITY: Skipping '{title[:40]}' — '{new_topic}' covered {count}x in last {lookback}")
            return True
        return False
    except Exception:
        return False

# Reddit sources
REDDIT_SUBS = ["bitcoin", "bitcoinmarkets", "cryptocurrency"]


class RealNewsArticleGenerator:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.used_urls = set()  # Track used sources to avoid duplicates
        self._load_used_urls()



    def _load_used_urls(self):
            """Load previously used source URLs"""
            try:
                from app import app
                from models import Article

                with app.app_context():
                    cutoff = datetime.utcnow() - timedelta(days=7)
                    recent = Article.query.filter(
                        Article.created_at >= cutoff,
                        Article.source_url != None
                    ).all()

                    self.used_urls = {a.source_url for a in recent if a.source_url}
                    logger.info(f"Loaded {len(self.used_urls)} used source URLs")
            except Exception as e:
                logger.error(f"Error loading used URLs: {e}")

    def fetch_rss_news(self, limit: int = 20) -> List[Dict]:
        """Fetch recent news from RSS feeds"""
        articles = []

        for feed_url in NEWS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:5]:  # Top 5 from each feed
                    url = entry.get('link', '')

                    # Skip if already used
                    if url in self.used_urls:
                        continue

                    # Get publish date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])

                    # Skip old articles (>48 hours)
                    if pub_date and (datetime.utcnow() - pub_date) > timedelta(hours=48):
                        continue

                    articles.append({
                        'title': entry.get('title', ''),
                        'summary': entry.get('summary', entry.get('description', ''))[:1000],
                        'url': url,
                        'source': feed_url.split('/')[2],
                        'published': pub_date.isoformat() if pub_date else None,
                        'type': 'rss'
                    })

            except Exception as e:
                logger.warning(f"Error fetching {feed_url}: {e}")

        logger.info(f"Fetched {len(articles)} fresh RSS articles")
        return articles[:limit]

    def fetch_reddit_posts(self, limit: int = 10) -> List[Dict]:
        """Fetch trending Bitcoin posts from Reddit"""
        posts = []

        try:
            from services.reddit_service import reddit_service

            for sub in REDDIT_SUBS:
                try:
                    hot_posts = reddit_service.get_hot_posts(sub, limit=5)

                    for post in hot_posts:
                        url = post.get('url', '')

                        if url in self.used_urls:
                            continue

                        # Only include substantial posts
                        if post.get('score', 0) < 50:
                            continue

                        posts.append({
                            'title': post.get('title', ''),
                            'summary': post.get('selftext', '')[:1000] or post.get('title', ''),
                            'url': f"https://reddit.com{post.get('permalink', '')}",
                            'source': f"r/{sub}",
                            'score': post.get('score', 0),
                            'type': 'reddit'
                        })

                except Exception as e:
                    logger.warning(f"Error fetching r/{sub}: {e}")

        except ImportError:
            logger.warning("Reddit service not available")

        logger.info(f"Fetched {len(posts)} Reddit posts")
        return sorted(posts, key=lambda x: x.get('score', 0), reverse=True)[:limit]

    def fetch_web_news(self, query: str = "Bitcoin news today") -> List[Dict]:
        """Fetch news via web search (using Grok's web capabilities)"""
        articles = []

        try:
            # Us

============================================================
FILE: services/ai_service.py (12595 chars)
============================================================
import os
import json
import logging
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None
from .grok_service import grok_service
from .gemini_service import gemini_service

class AIService:
    def __init__(self):
        # Initialize OpenAI client (optional if openai package missing or old)
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key and OpenAI is not None:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
            except Exception:
                self.openai_client = None
        else:
            self.openai_client = None
        
        # Initialize Anthropic client (optional if anthropic package missing)
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key and Anthropic is not None:
            try:
                self.anthropic_client = Anthropic(api_key=anthropic_key)
            except Exception:
                self.anthropic_client = None
        else:
            self.anthropic_client = None
        
        self.default_openai_model = "gpt-4o"
        self.default_anthropic_model = "claude-sonnet-4-20250514"
        
        # AI service integrations - check availability
        try:
            self.grok_available = grok_service.test_connection()
        except:
            self.grok_available = False
        
        try:
            self.gemini_available = gemini_service.test_connection()
        except:
            self.gemini_available = False
    
    def generate_content_openai(self, prompt, system_prompt=None):
        """Generate content using OpenAI GPT-4o"""
        if not self.openai_client:
            raise ValueError("API key required")
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an investigative journalist for Protocol Pulse."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")
            raise
    
    def generate_content_anthropic(self, prompt, system_prompt=None):
        """Generate content using Anthropic Claude"""
        if not self.anthropic_client:
            raise ValueError("API key required")
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = self.anthropic_client.messages.create(
                model=self.default_anthropic_model,
                max_tokens=8192,
                temperature=0.7,
                system="You are an investigative journalist for Protocol Pulse.",
                messages=messages
            )
            
            # Handle Anthropic response properly - extract text from content blocks
            if response and response.content and len(response.content) > 0:
                content_block = response.content[0]
                # Use getattr to safely access text attribute regardless of block type
                text_content = getattr(content_block, 'text', None)
                if text_content is not None:
                    return str(text_content)
                else:
                    # Fallback to string conversion for other block types
                    return str(content_block)
            return ""
            
        except Exception as e:
            logging.error(f"Anthropic API error: {str(e)}")
            raise
    
    def generate_structured_content(self, prompt, system_prompt=None, provider="openai"):
        """Generate structured content with JSON response"""
        if provider == "openai" and self.openai_client:
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.openai_client.chat.completions.create(
                    model=self.default_openai_model,
                    messages=messages,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                if content:
                    return json.loads(content)
                else:
                    return {}
                
            except Exception as e:
                logging.error(f"OpenAI structured content error: {str(e)}")
                # Fallback to regular generation
                return self.generate_content_openai(prompt, system_prompt)
        
        elif provider == "anthropic" and self.anthropic_client:
            return self.generate_content_anthropic(prompt, system_prompt)
        
        elif provider == "openai" and not self.openai_client:
            raise ValueError("API key required")
        
        elif provider == "anthropic" and not self.anthropic_client:
            raise ValueError("API key required")
        
        else:
            raise ValueError("API key required")
    
    def summarize_text(self, text, max_words=150):
        """Summarize text content"""
        prompt = f"Summarize the following text in {max_words} words or less, focusing on key points relevant to Web3, cryptocurrency, and blockchain technology:\n\n{text}"
        
        try:
            # Try OpenAI first, fallback to Anthropic
            if self.openai_client:
                return self.generate_content_openai(prompt)
            elif self.anthropic_client:
                return self.generate_content_anthropic(prompt)
            else:
                raise ValueError("API key required")
                
        except Exception as e:
            logging.error(f"Summarization error: {str(e)}")
            return text[:500] + "..." if len(text) > 500 else text
    
    def generate_seo_metadata(self, title, content):
        """Generate SEO title and description"""
        prompt = f"""
        Generate SEO-optimized metadata for this article:
        Title: {title}
        Content: {content[:500]}...
        
        Provide a compelling SEO title (60 chars max) and meta description (155 chars max) that includes relevant Web3/crypto keywords.
        Respond in JSON format: {{"seo_title": "...", "seo_description": "..."}}
        """
        
        system_prompt = "You are an SEO expert specializing in Web3 and cryptocurrency content."
        
        try:
            if self.openai_client:
                result = self.generate_structured_content(prompt, system_prompt, "openai")
                if isinstance(result, dict):
                    return result
            elif self.anthropic_client:
                response = self.generate_content_anthropic(prompt, system_prompt)
                return {
                    "seo_title": title[:60],
                    "seo_description": content[:155] + "..." if len(content) > 155 else content
                }
            else:
                raise ValueError("API key required")
            
        except Exception as e:
            logging.error(f"SEO generation error: {str(e)}")
            return {
                "seo_title": title[:60],
                "seo_description": content[:155] + "..." if len(content) > 155 else content
            }
    
    
    def generate_content_grok(self, topic, content_type="bitcoin_news"):
        """Generate content using Grok"""
        if not self.grok_available:
            raise ValueError("API key required")
        
        try:
            if content_type == "bitcoin_news":
                return grok_service.generate_bitcoin_article(topic, "news")
            elif content_t

============================================================
FILE: services/affiliate_article_generator.py (27989 chars)
============================================================
"""
Affiliate Article Generator — Problem-First Educational Content Engine
======================================================================

Generates 2 articles per day that educate readers on a genuine, interesting problem
and then naturally position an affiliate product as the solution.

Design philosophy:
- 90% education, 10% solution (the product mention feels like a natural conclusion)
- Think-tank level psychological execution: reader should DISCOVER the solution themselves
- Walter Cronkite editorial voice: authoritative, trusted, never salesy
- Every article must pass Grok fact-checking gate before publishing
- Problems are REAL and verified — never fabricated to sell a product

Psychological framework:
1. PROBLEM AWARENESS — Reader learns about a threat they didn't fully understand
2. COST OF INACTION — Data-driven evidence of what happens if they do nothing
3. SOCIAL PROOF — Experts and institutions addressing this same problem
4. NATURAL BRIDGE — The solution category emerges organically from the analysis
5. SPECIFIC RECOMMENDATION — One clear, tasteful mention with affiliate link
"""

import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app import app, db
from models import Article

logger = logging.getLogger(__name__)

AFFILIATE_PRODUCTS = {
    "meanwhile": {
        "name": "Meanwhile",
        "url": "https://application.meanwhile.bm/start?referralCode=KKM73K",
        "category": "Bitcoin Life Insurance",
        "tagline": "Bitcoin-denominated whole life insurance",
        "one_liner": "Meanwhile offers Bitcoin-denominated whole life insurance — your policy, your keys, your sovereignty.",
        "cta_class": "meanwhile-cta",
    },
    "trezor": {
        "name": "Trezor",
        "url": "https://trezor.io/?ref=protocolpulse",
        "category": "Hardware Wallet",
        "tagline": "Open-source hardware wallets for self-custody",
        "one_liner": "Trezor's open-source hardware wallets provide air-gapped security for long-term Bitcoin holders.",
        "cta_class": "trezor-cta",
    },
    "river": {
        "name": "River",
        "url": "https://river.com/?ref=protocolpulse",
        "category": "Bitcoin Exchange",
        "tagline": "Bitcoin-only exchange with automatic DCA",
        "one_liner": "River is a Bitcoin-only exchange built for recurring purchases and automatic dollar-cost averaging.",
        "cta_class": "river-cta",
    },
    "unchained": {
        "name": "Unchained",
        "url": "https://unchained.com/?ref=protocolpulse",
        "category": "Multi-sig & Bitcoin-Backed Loans",
        "tagline": "Collaborative custody and Bitcoin-backed lending",
        "one_liner": "Unchained provides collaborative multi-signature custody and Bitcoin-backed loans without selling your stack.",
        "cta_class": "unchained-cta",
    },
    "fold": {
        "name": "Fold",
        "url": "https://foldapp.com/?ref=protocolpulse",
        "category": "Bitcoin Rewards Card",
        "tagline": "Earn Bitcoin on every purchase",
        "one_liner": "The Fold Card lets you earn Bitcoin rewards on everyday purchases — turning spending into stacking.",
        "cta_class": "fold-cta",
    },
    "swan": {
        "name": "Swan Bitcoin",
        "url": "https://swanbitcoin.com/?ref=protocolpulse",
        "category": "Automatic DCA",
        "tagline": "Set-and-forget Bitcoin accumulation",
        "one_liner": "Swan Bitcoin automates dollar-cost averaging with recurring buys and zero withdrawal fees.",
        "cta_class": "swan-cta",
    },
    "casa": {
        "name": "Casa",
        "url": "https://keys.casa/?ref=protocolpulse",
        "category": "Multi-sig Self-Custody",
        "tagline": "Premium multi-signature key management",
        "one_liner": "Casa provides guided multi-signature self-custody — eliminating single points of failure in your security setup.",
        "cta_class": "casa-cta",
    },
    "strike": {
        "name": "Strike",
        "url": "https://strike.me/?ref=protocolpulse",
        "category": "Lightning Payments & DCA",
        "tagline": "Send, spend, and stack Bitcoin via Lightning",
        "one_liner": "Strike enables instant Bitcoin purchases and Lightning payments with industry-leading low fees.",
        "cta_class": "strike-cta",
    },
}

PROBLEM_SOLUTION_PLAYBOOK = [
    {
        "product": "meanwhile",
        "problems": [
            {
                "topic": "The Silent Threat to Bitcoin Wealth: What Happens to Your Keys When You're Gone?",
                "problem_angle": "Estate planning for Bitcoin holders is catastrophically underprepared. Studies show 89% of crypto holders have no succession plan. When a holder dies without one, their family faces permanent loss of generational wealth.",
                "education_focus": "inheritance planning, probate court limitations with digital assets, key-man risk in self-custody, real cases of lost Bitcoin estates",
                "bridge": "Traditional life insurance pays out in depreciating fiat. For a Bitcoin-standard family, the solution needs to be denominated in the same asset they're protecting.",
            },
            {
                "topic": "Why Traditional Life Insurance Is Quietly Destroying Bitcoin Families' Purchasing Power",
                "problem_angle": "Life insurance payouts are denominated in dollars that lose 2-7% purchasing power annually. A $1M policy taken out in 2010 would buy 40% less today. Bitcoin families face a unique dilemma: their savings appreciate while their insurance depreciates.",
                "education_focus": "fiat debasement impact on insurance payouts, M2 money supply growth, purchasing power erosion data, the gap between Bitcoin savings and fiat insurance",
                "bridge": "The logical conclusion: insurance denominated in the same sound money you've chosen to save in.",
            },
            {
                "topic": "The $68 Billion Problem: Why Most Bitcoin Will Never Reach Its Intended Heirs",
                "problem_angle": "An estimated $68 billion in cryptocurrency may be permanently lost due to inadequate estate planning. The unique challenge of digital bearer assets means traditional inheritance mechanisms fail completely.",
                "education_focus": "digital asset inheritance challenges, jurisdictional complications, the difference between custodial and non-custodial inheritance, case studies of families losing access",
                "bridge": "A Bitcoin-native insurance product bridges the gap between self-sovereign savings and family protection.",
            },
        ],
    },
    {
        "product": "trezor",
        "problems": [
            {
                "topic": "Exchange Hacks Cost Users $3.8 Billion in 2024 — Here's the Pattern Nobody Talks About",
                "problem_angle": "Major exchange breaches follow a predictable pattern: insider access, hot wallet compromise, delayed disclosure. The common thread in every case is counterparty risk — trusting someone else with your keys.",
                "education_focus": "history of exchange hacks (Mt. Gox, FTX, WazirX), counterparty risk analysis, hot wallet vs cold storage security models, the 'not your keys' principle with real data",
                "bridge": "The only way to eliminate counterparty risk entirely is hardware-level key isolation — keeping private keys in a device that never connects to the internet.",
            },
            {
                "topic": "The Hidden Risk in Your Mobile Wallet: Why Phone-Based Bitcoin Storage Is a Ticking Time Bomb",
                "problem_angle": "Mobile wallets store private keys on general-purpose devices running millions of lines of unaudited code. SIM-swap attacks, malware, and OS vulnerabilities create an attack surface most holders don't understand.",
                "education_focus": "SIM-swap attack statistic

============================================================
FILE: services/content_generator.py (52386 chars)
============================================================
import os
import logging
import hashlib
from pathlib import Path
import json
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta
from app import app, db
from models import ContentPrompt, Article
from services.ai_service import AIService
from services.reddit_service import RedditService
from services.x_service import get_social_feedback
from services import x_service
from services.image_service import image_service
from services.gemini_service import gemini_service
from services.node_service import NodeService
from services.fact_checker import fact_checker, verify_article_before_publish


def _get_local_header_image_pool() -> list[str]:
    """Build a pool of local header images served from /static/images/headers/.

    This avoids relying on external CDNs (Unsplash) and guarantees the UI can always show a header image.
    """
    try:
        project_root = Path(__file__).resolve().parents[1]
        headers_dir = project_root / "core" / "static" / "images" / "headers"
        if not headers_dir.exists():
            return ["/static/images/default-header.png"]
        names = sorted([p.name for p in headers_dir.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}])
        urls = [f"/static/images/headers/{n}" for n in names]
        # Always include the generic fallback first.
        return ["/static/images/default-header.png"] + urls
    except Exception:
        return ["/static/images/default-header.png"]


# Cached at import time; safe to use across requests.
ARTICLE_HEADER_IMAGE_POOL = _get_local_header_image_pool()


def get_article_header_url(seed: str) -> str:
    """Always return default — real images come from image_service.py GPT-4o generation."""
    return "/static/images/default-header.png"


def _load_allowed_news_domains() -> set[str]:
    """Load allowlisted source domains from config/allowed_news_domains.json."""
    try:
        project_root = Path(__file__).resolve().parents[1]
        p = project_root / "config" / "allowed_news_domains.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        domains = data.get("domains") or []
        return {str(d).strip().lower().lstrip(".") for d in domains if str(d).strip()}
    except Exception:
        return set()


ALLOWED_NEWS_DOMAINS = _load_allowed_news_domains()


def _hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().strip(".")
    except Exception:
        return ""


def is_allowed_source_url(url: str) -> bool:
    """True if url's hostname is allowlisted (suffix match; subdomains allowed)."""
    host = _hostname(url)
    if not host:
        return False
    for d in (ALLOWED_NEWS_DOMAINS or set()):
        if host == d or host.endswith("." + d):
            return True
    return False


def infer_source_type(url: str) -> str:
    """Return a short source label from a URL hostname."""
    host = _hostname(url)
    if not host:
        return ""
    for d in sorted(ALLOWED_NEWS_DOMAINS or set(), key=len, reverse=True):
        if host == d or host.endswith("." + d):
            return d
    return host


def _extract_urls_from_html(html: str) -> list[str]:
    if not html:
        return []
    hrefs = re.findall(r'href=[\'"]([^\'"]+)[\'"]', html, flags=re.I)
    bare = re.findall(r'https?://[^\s<>"\']+', html, flags=re.I)
    out: list[str] = []
    for u in hrefs + bare:
        u = (u or "").strip()
        if u.startswith("http://") or u.startswith("https://"):
            out.append(u)
    seen = set()
    uniq: list[str] = []
    for u in out:
        if u not in seen:
            uniq.append(u)
            seen.add(u)
    return uniq


def pick_primary_source_url(article_html: str) -> str:
    """Pick the first allowlisted URL mentioned in the article content."""
    urls = _extract_urls_from_html(article_html)
    for u in urls:
        if is_allowed_source_url(u):
            return u
    return urls[0] if urls else ""


def _extract_og_image(source_url: str) -> str:
    """Return og:image (or twitter:image) from a source page, if available."""
    if not source_url or not is_allowed_source_url(source_url):
        return ""
    try:
        import requests
        r = requests.get(
            source_url,
            timeout=6,
            headers={"User-Agent": "ProtocolPulseBot/1.0 (+https://protocolpulse.io)"},
        )
        if r.status_code >= 400:
            return ""
        html = r.text or ""
        for pat in [
            r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
            r'<meta[^>]+name=[\'"]twitter:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
        ]:
            m = re.search(pat, html, flags=re.I)
            if m:
                img = (m.group(1) or "").strip()
                if img:
                    return urljoin(source_url, img)
        return ""
    except Exception:
        return ""


def resolve_header_image_url(title: str, article_html: str) -> tuple[str, str, str]:
    """Return (header_image_url, source_url, source_type) for a generated article.

    - First try AI-generated hyper-realistic header image via DALL-E.
    - Then try allowlisted source URL og:image.
    - Fall back to deterministic local header pool so cards never render without images.
    """
    src_url = pick_primary_source_url(article_html)
    src_type = infer_source_type(src_url) if src_url else ""

    header = ""
    if image_service.openai_client:
        try:
            summary = image_service.extract_summary_from_content(article_html) if article_html else title
            generated = image_service.generate_article_header_image(title, summary)
            if generated and generated != "/static/images/default-header.png":
                header = generated
        except Exception as e:
            logging.warning(f"DALL-E image generation failed for '{title[:40]}': {e}")

    if not header:
        og_img = _extract_og_image(src_url) if src_url else ""
        header = (og_img or "").strip() or "/static/images/default-header.png"

    return header, (src_url or ""), (src_type or "")


def is_topic_duplicate_via_gemini(proposed_topic):
    """
    AI GATEKEEPER: Check if the proposed topic duplicates any recent article.
    Returns True if duplicate (should skip), False if unique (proceed).
    """
    try:
        with app.app_context():
            # Fetch last 10 published article titles
            recent_articles = Article.query.filter_by(published=True).order_by(
                Article.created_at.desc()
            ).limit(10).all()
            
            if not recent_articles:
                return False  # No articles to compare, proceed
            
            headlines_list = "\n".join([f"- {a.title}" for a in recent_articles])
            
            prompt = f"""You are a senior news editor preventing duplicate coverage.

PROPOSED NEW TOPIC: "{proposed_topic}"

LAST 10 PUBLISHED HEADLINES:
{headlines_list}

CRITICAL QUESTION: Is the proposed topic covering the EXACT SAME news event as ANY of these existing headlines?

RULES:
- Focus on the CORE EVENT, not wording
- "Bitcoin reaches new high" and "BTC price surges to record" = SAME EVENT
- "Nations adopt Bitcoin reserves" and "Countries add BTC to treasuries" = SAME EVENT
- "Bitcoin mining difficulty rises" and "New mining hardware released" = DIFFERENT EVENTS

Reply with ONLY one word: "DUPLICATE" or "UNIQUE" - nothing else."""

            response = gemini_service.generate_content(prompt)
            if response:
                answer = response.strip().upper()
                if "DUPLICATE" in answer:
                    logging.info(f"🚫 GATEKEEPER BLOCKED: '{proposed_topic[:50]}...' is duplicate of existing story")
                    return True
                logging.info(f"✅ GATEKEEPER APPROVED: '{proposed_topic[:50]}...' is unique")
            return False
    except Exception as e:
        logging.warning(f"Gatekeeper ch

============================================================
ARTICLE ROUTES (from routes.py)
============================================================
@app.route('/admin/viral-moments', methods=['POST'])
@login_required
@admin_required
def admin_create_viral_moments_job():
    """Create a ClipJob for the Viral Moments reel pipeline.

    Expects JSON: {"video_id": "...", "channel_name": "..."}
    Returns: {"success": true, "job_id": <int>}
    """
    import json

    data = request.get_json(silent=True) or {}
    video_id = str(data.get('video_id') or '').strip()
    channel_name = str(data.get('channel_name') or '').strip()

    if not video_id:
        return jsonify({"success": False, "error": "video_id is required"}), 400

    # Local import to avoid circular import issues during app boot.
    from app import db
    import models

    job = models.ClipJob(
        video_id=video_id,
        channel_name=channel_name or None,
        # Legacy columns are NOT NULL in the current schema; populate them even if V2 fields are used.
        timestamps_json=json.dumps([]),
        narrative_context="",
        # V2 fields
        segments_json=json.dumps([]),
        status="Planned",
        metadata_json=json.dumps({"source": "admin/viral-moments"}),
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({"success": True, "job_id": int(job.id)})


def premium_required(f):
    """Require Commander ($99/mo) or higher for premium hub access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Sign in to access the Premium Hub.')
            return redirect(url_for('login') + '?next=' + request.path)
        if not getattr(current_user, 'has_commander_tier', lambda: False)():
            flash('Premium Hub requires a Commander ($99/mo) subscription.')
            return redirect(url_for('premium_page'))
        return f(*args, **kwargs)
    return decorated_function


def premium_hub_required(f):
    """Require any paid tier (Operator / Commander / Sovereign) for hub access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        remote = str(request.remote_addr or "")
        if (
            is_enabled("ENABLE_SELF_CHECK_BYPASS")
            and request.headers.get("X-Self-Check") == "1"
            and ("127.0.0.1" in remote or remote in ("::1", "localhost"))
        ):
            return f(*args, **kwargs)
        if not current_user.is_authenticated:
            flash('Sign in to access the Premium Hub.')
            return redirect(url_for('login') + '?next=' + request.path)
        if getattr(current_user, 'is_admin', False):
            return f(*args, **kwargs)
        if not getattr(current_user, 'has_premium', lambda: False)():
            flash('Premium Hub requires a paid subscription (Operator $21/mo or higher).')
            return redirect(url_for('premium_page'))
        return f(*args, **kwargs)
    return decorated_function


# Commander gate alias for compatibility with prior specs/routes.
commander_required = premium_hub_required


@app.route('/admin/x-replies')
@login_re

============================================================
TEMPLATE: templates/articles.html (32313 chars)
============================================================
{% extends "base.html" %}

{% block title %}Latest Intelligence - Protocol Pulse{% endblock %}

{% block head %}
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "Bitcoin News & Analysis",
    "description": "Breaking Bitcoin news, mining reports, and market analysis from Protocol Pulse.",
    "publisher": {
        "@type": "Organization",
        "name": "Protocol Pulse",
        "url": "https://protocolpulse.io"
    }
}
</script>

<!-- Open Graph -->
<meta property="og:title" content="Bitcoin News & Analysis — Protocol Pulse">
<meta property="og:description" content="Breaking Bitcoin news, mining reports, regulatory updates, and institutional analysis.">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Protocol Pulse">
<meta property="og:image" content="{{ url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}">
<meta property="og:url" content="{{ request.url }}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@ProtocolPulse">
<meta name="twitter:title" content="Bitcoin News & Analysis — Protocol Pulse">
<meta name="twitter:description" content="Breaking Bitcoin news, mining reports, regulatory updates, and institutional analysis.">

<link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,500&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    :root {
        --btc-gold: #f7931a;
        --btc-gold-glow: rgba(247, 147, 26, 0.25);
        --dark-bg: #030303;
        --surface-1: #0a0a0a;
        --surface-2: #111111;
        --surface-3: #181818;
        --text-primary: #f0f0f0;
        --text-secondary: #999999;
        --text-tertiary: #5a5a5a;
        --border-subtle: rgba(255,255,255,0.06);
        --border-accent: rgba(220, 38, 38, 0.15);
        --accent-red: #dc2626;
        --accent-red-dim: rgba(220, 38, 38, 0.08);
    }

    body { background-color: var(--dark-bg); color: var(--text-primary); }

    .articles-page {
        min-height: 100vh;
        background: var(--dark-bg);
    }

    .masthead {
        border-bottom: 1px solid var(--border-subtle);
        padding: 2.5rem 0 2rem;
    }

    .masthead-inner {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 1.5rem;
    }

    .edition-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.35em;
        color: var(--accent-red);
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    .edition-label::before {
        content: '';
        width: 5px;
        height: 5px;
        background: var(--accent-red);
        border-radius: 50%;
        box-shadow: 0 0 8px var(--accent-red);
        animation: livePulse 2s infinite;
    }

    @keyframes livePulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }

    .masthead-title {
        font-family: 'Crimson Pro', Georgia, serif;
        font-size: 3.5rem;
        font-weight: 900;
        color: #fff;
        letter-spacing: -0.03em;
        line-height: 1;
        margin: 0.5rem 0 0.25rem;
    }

    .masthead-date {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-tertiary);
        letter-spacing: 0.05em;
    }

    .main-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 1.5rem;
    }

    .zone-divider {
        display: flex;
        align-items: center;
        gap: 16px;
        margin: 3rem 0 2rem;
        position: relative;
    }

    .zone-divider::after {
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, var(--border-accent), transparent);
    }

    .zone-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.25em;
        color: var(--accent-red);
        font-weight: 600;
        white-space: nowrap;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        background: var(--accent-red-dim);
        border: 1px solid rgba(220,38,38,0.2);
        border-radius: 4px;
    }

    .zone-count {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        color: var(--text-tertiary);
        letter-spacing: 0.05em;
    }

    .hero-article {
        display: grid;
        grid-template-columns: 1.15fr 1fr;
        gap: 0;
        background: var(--surface-1);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        overflow: hidden;
        transition: border-color 0.4s ease;
        margin-bottom: 1.5rem;
    }

    .hero-article:hover {
        border-color: rgb

============================================================
TEMPLATE: templates/article_detail.html (23124 chars)
============================================================
{% extends "base.html" %}

{% block title %}{{ article.title }} - Protocol Pulse{% endblock %}

{% block meta_description %}{{ article.summary if article.summary else article.content[:150] }}{% endblock %}

{% block head %}
<!-- Open Graph meta tags for social media sharing -->
<meta property="og:title" content="{{ article.title }}">
<meta property="og:description" content="{{ article.content[:200] }}...">
<meta property="og:image" content="{{ header_image_url or url_for('dynamic_og_image', og_type='article', id=article.id) }}">
<meta property="og:url" content="{{ request.url }}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Protocol Pulse">

<!-- Twitter Card meta tags -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@protocolpulse">
<meta name="twitter:title" content="{{ article.title }}">
<meta name="twitter:description" content="{{ article.content[:200] }}...">
<meta name="twitter:image" content="{{ header_image_url or url_for('dynamic_og_image', og_type='article', id=article.id) }}">

<!-- SEO meta tags -->
<meta name="description" content="{{ article.seo_description or article.summary }}">
<meta name="keywords" content="{{ article.tags }}, Bitcoin, DeFi, Protocol Pulse">
<link rel="canonical" href="{{ request.url }}">

<!-- NewsArticle Schema for Google + AI crawlers -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    "headline": "{{ article.title }}",
    "description": "{{ article.summary or article.content[:200] }}",
    "image": "{{ header_image_url or '' }}",
    "datePublished": "{{ article.created_at.isoformat() if article.created_at else '' }}",
    "dateModified": "{{ article.created_at.isoformat() if article.created_at else '' }}",
    "author": {
        "@type": "Organization",
        "name": "Protocol Pulse",
        "url": "https://protocolpulse.io"
    },
    "publisher": {
        "@type": "Organization",
        "name": "Protocol Pulse",
        "logo": {
            "@type": "ImageObject",
            "url": "{{ url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}"
        }
    },
    "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": "{{ request.url }}"
    },
    "articleSection": "{{ article.category or 'Bitcoin' }}",
    "keywords": "{{ article.tags or 'Bitcoin, cryptocurrency' }}"
}
</script>

{% endblock %}

{% block content %}
<div class="reading-progress"></div>

<article class="py-5">
    <div class="container">
        <!-- Article Header -->
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="mb-4">
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item"><a href="{{ url_for('index') }}" class="text-primary">Home</a></li>
                            <li class="breadcrumb-item"><a href="{{ url_for('articles') }}" class="text-primary">News</a></li>
                            <li class="breadcrumb-item active text-muted" aria-current="page">{{ article.title[:50] }}...</li>
                        </ol>
                    </nav>
                </div>

                <header class="article-header-professional">
                    <!-- Category Badge -->
                    <div class="category-section mb-4">
                        <span class="category-badge">{{ article.category }}</span>
                    </div>

                    <!-- Article Title -->
                    <h1 class="article-title-professional">{{ article.title }}</h1>
                    
                    <!-- Author and Date -->
                    <div class="article-meta-professional mb-4">
                        <div class="meta-item">
                            <span class="meta-label">By</span>
                            <span class="meta-value">{{ article.author }}</span>
                        </div>
                        <div class="meta-divider">•</div>
                        <div class="meta-item">
                            <span class="meta-value">{{ article.created_at.strftime('%B %d, %Y at %I:%M %p') }}</span>
                        </div>
                        <div class="meta-divider">•</div>
                        <div class="meta-item">
                            <span class="meta-value">{{ ((article.content | length) / 1000 * 3) | round | int }} min read</span>
                        </div>
                    </div>

                    {% set detail_image = header_image_url or '/static/images/default-header.png' %}
                    <div class="article-image-hero mb-4">
                        <img src="{{ detail_image }}" alt="{{ article.title }}" class="img-fluid w-100">
                    </div>

                    <!-- Share Buttons -->
                    <div class="share-social-section">
            

============================================================
TEMPLATE: templates/media_hub.html (35819 chars)
============================================================
{% extends "base.html" %}
{% block title %}The Network — Protocol Pulse Media Hub{% endblock %}
{% block meta_description %}Bitcoin intelligence network. Live signals from Nostr and X.{% endblock %}
{% block head %}
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist+Mono:wght@400;500;600&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--void:#000;--deep:#040408;--card:#08080e;--elevated:#0e0e16;--hover:#14141e;--border:rgba(255,255,255,0.05);--border-h:rgba(255,255,255,0.1);--bright:#f5f5f5;--pri:#e0e0e0;--sec:rgba(255,255,255,0.5);--mut:rgba(255,255,255,0.25);--red:#dc2626;--red-g:rgba(220,38,38,0.12);--btc:#f7931a;--purple:#a855f7;--blue:#3b82f6;--green:#22c55e;--cyan:#06b6d4}
*{box-sizing:border-box;margin:0;padding:0}
.mh{font-family:'DM Sans',-apple-system,sans-serif;background:var(--void);color:var(--pri);min-height:100vh;padding-top:80px}
.mono{font-family:'Geist Mono',monospace}
.wrap{max-width:1440px;margin:0 auto;padding:0 clamp(16px,4vw,48px)}
.hero{position:relative;padding:80px 0 60px;overflow:hidden}
.hero-bg{position:absolute;inset:0;overflow:hidden}
.hero-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(220,38,38,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(220,38,38,0.03) 1px,transparent 1px);background-size:60px 60px;animation:gridDrift 20s linear infinite}
@keyframes gridDrift{from{transform:translate(0,0)}to{transform:translate(60px,60px)}}
.hero-orb{position:absolute;border-radius:50%;filter:blur(80px);animation:orbFloat 8s ease-in-out infinite}
.hero-orb-1{width:400px;height:400px;background:rgba(220,38,38,0.08);top:-100px;left:20%}
.hero-orb-2{width:300px;height:300px;background:rgba(247,147,26,0.05);bottom:-80px;right:15%;animation-delay:-3s}
.hero-orb-3{width:200px;height:200px;background:rgba(168,85,247,0.04);top:40%;left:60%;animation-delay:-5s}
@keyframes orbFloat{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(30px,-20px) scale(1.1)}}
.hero-scanline{position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,rgba(220,38,38,0.3),transparent);animation:scanDown 4s linear infinite;opacity:0.4}
@keyframes scanDown{from{top:0}to{top:100%}}
.hero-vignette{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 40%,transparent 40%,var(--void) 100%)}
.hero-inner{position:relative;z-index:2}
.hero-tag{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;background:rgba(220,38,38,0.08);border:1px solid rgba(220,38,38,0.15);border-radius:24px;margin-bottom:28px;opacity:0;animation:fadeUp .6s ease forwards}
.hero-tag-dot{width:6px;height:6px;border-radius:50%;background:var(--red);animation:tagPulse 2s infinite}
@keyframes tagPulse{0%,100%{opacity:1}50%{opacity:0.3}}
.hero-tag-text{font-family:'Geist Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--red)}
.hero-h{font-family:'Instrument Serif',Georgia,serif;font-size:clamp(56px,10vw,120px);font-weight:400;line-height:0.95;color:var(--bright);letter-spacing:-3px;margin-bottom:20px;opacity:0;animation:fadeUp .6s ease .1s forwards}
.hero-h em{font-style:italic;background:linear-gradient(135deg,var(--red),var(--btc));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:17px;font-weight:300;color:var(--sec);max-width:480px;line-height:1.6;opacity:0;animation:fadeUp .6s ease .2s forwards}
.hero-metrics{display:flex;gap:40px;margin-top:40px;opacity:0;animation:fadeUp .6s ease .3s forwards}
.hero-metric{position:relative;padding:16px 0}
.hero-metric::after{content:'';position:absolute;right:-20px;top:50%;transform:translateY(-50%);width:1px;height:24px;background:var(--border)}
.hero-metric:last-child::after{display:none}
.hero-metric-val{font-family:'Geist Mono',monospace;font-size:28px;font-weight:600;color:var(--bright)}
.hero-metric-lab{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:1.5px;margin-top:4px}
.hero-status{display:flex;gap:24px;margin-top:32px;opacity:0;animation:fadeUp .6s ease .4s forwards}
.hero-status-item{display:flex;align-items:center;gap:6px;font-family:'Geist Mono',monospace;font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:1px}
.hero-status-dot{width:5px;height:5px;border-radius:50%}
.hero-status-dot.live{background:var(--green);box-shadow:0 0 6px var(--green)}
.hero-status-dot.sync{background:var(--btc);animation:tagPulse 1.5s infinite}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.sec{padding:64px 0;border-top:1px solid var(--border)}
.sec-lab{font-family:'Geist Mono',monospace;font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--red);margin-bottom:14px}
.sec-h{font-family:'Instrument Serif',Georgia,serif;font-size:clamp(26px,4vw,38px);font-weight:400;color:var(--bright);letter-spacing:-0.5px;margin-bottom:10px}
.sec-desc{font-

============================================================
MASTER AUTOMATION (17170 chars)
============================================================

#!/usr/bin/env python3
"""
PROTOCOL PULSE - MASTER AUTOMATION
===================================
The "leave it running overnight" script.

Runs continuously:
- Article generation every 15 minutes (Claude + Grok review)
- Sentiment monitoring every 5 minutes
- X engagement every 30 minutes (if enabled)
- Article posting to X every hour (if enabled)

Usage:
    python3 master_automation.py

Environment variables:
    ENABLE_ARTICLE_AUTOMATION_15M=true  (required)
    ENABLE_AUTO_PUBLISH=true            (required)
    AUTOPOST_X=true                     (optional)
    ENABLE_X_ENGAGE=true                (optional)
"""

import os
import json
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta
from threading import Event
from services.radar_automation import run_radar_cycle_safe

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/master_automation.log")
    ]
)
logger = logging.getLogger("MasterAutomation")

# Ensure directories
os.makedirs("logs", exist_ok=True)

class MasterAutomation:
    """
    Main automation orchestrator.
    """
    
    def __init__(self):
        self.stop_event = Event()
        
        # Intervals (seconds)
        self.article_interval = 15 * 60  # 15 min
        self.sentiment_interval = 5 * 60  # 5 min
        self.engage_interval = 30 * 60   # 30 min
        self.post_interval = 6 * 60 * 60  # 6 hours
        self.pulse_interval = 6 * 60 * 60  # 6 hours - Partner channel intelligence
        
        # Last run times
        self.last_article = None
        self.last_sentiment = None
        self.last_engage = None
        self.last_post = None
        self.last_pulse = None
        
        # Stats
        self.stats = {
            "articles_generated": 0,
            "articles_published": 0,
            "sentiment_checks": 0,
            "x_posts": 0,
            "x_engagements": 0,
            "pulse_runs": 0,
            "errors": 0,
            "started_at": datetime.utcnow().isoformat()
        }
    
    def should_run(self, last_time: datetime, interval: int) -> bool:
        """Check if task should run."""
        if last_time is None:
            return True
        return (datetime.utcnow() - last_time).total_seconds() >= interval
    
    def run_article_generation(self):
        """Generate a new article."""
        try:
            from services.article_automation import run_article_generation_cycle
            
            result = run_article_generation_cycle()
            
            self.stats["articles_generated"] += 1
            if result.get("published"):
                self.stats["articles_published"] += 1
                
                # Post to X if enabled
                if os.environ.get("AUTOPOST_X", "").lower() == "true":
                    self.post_to_x(result.get("article_id"))
            
            return result
            
        except Exception as e:
            logger.error(f"Article generation error: {e}")
            self.stats["errors"] += 1
            return {"success": False, "error": str(e)}
    
    def run_sentiment_check(self):
        """Check multi-platform sentiment."""
        try:
            from services.sentiment_aggregator import sentiment_aggregator
            
            sentiment = sentiment_aggregator.get_aggregated_sentiment()
            self.stats["sentiment_checks"] += 1
            
            logger.info(f"Sentiment: {sentiment['sentiment']} (score: {sentiment['score']})")
            return sentiment
            
        except Exception as e:
            logger.warning(f"Sentiment check error: {e}")
            self.stats["errors"] += 1
            return None
    
    def run_x_engagement(self):
        """Auto-engage on X."""
        if os.environ.get("ENABLE_X_ENGAGE", "").lower() != "true":
            return None
        
        try:
            from services.x_automation_service import x_automation_service
            
            result = x_automation_service.auto_engage(max_actions=5)
            self.stats["x_engagements"] += result.get("actions", 0)
            
            logger.info(f"X engagement: {result.get('actions', 0)} actions")
            return result
            
        except Exception as e:
            logger.warning(f"X engagement error: {e}")
            self.stats["errors"] += 1
            return None
    

    def run_pulse_intelligence(self):
        """Run partner channel intelligence pulse"""
        try:
            from services.pulse_intelligence import pulse_intelligence
            
            logger.info("Running Pulse Intelligence...")
            result = pulse_intelligence.run_daily_pulse()
            
            self.stats["pulse_runs"] += 1
            
            if result.get("status") == "success":
                logger.info(f"Pulse complete: {result.get('videos_processed', 0)} videos processed")
                
                # Post top X hook if we have one
                x_posts = result.get("x_posts", [])
                if x_posts and os.environ.get("AUTOPOST_X", "").lower() == "true":
                    try:
                        from services.x_service import XService
                        
                        from datetime import datetime
                        
                        POSTED_FILE = "data/posted_urls.json"
                        DAILY_LIMIT = 2  # Max pulse posts per day
                        
                        # Load posted data
                        os.makedirs("data", exist_ok=True)
                        if os.path.exists(POSTED_FILE):
                            with open(POSTED_FILE, 'r') as f:
                                posted_data = json.load(f)
                        else:
                            posted_data = {"urls": [], "daily_posts": {}, "last_cleanup": N

============================================================
FILE: services/image_service.py (19717 chars)
============================================================
# Protocol Pulse Editorial Image Service
# GPT-4o native image generation with red/black brand overlay
import os, re, time, base64, logging, requests
from pathlib import Path
from PIL import Image, ImageDraw
from io import BytesIO

logger = logging.getLogger(__name__)
HEADERS_DIR = Path("static/images/headers")
HEADERS_DIR.mkdir(parents=True, exist_ok=True)

# NO MORE TOPIC_VISUALS — every image is unique, generated from the headline itself

def _match_visual(title):
    """Generate a unique visual concept from the article title.
    NEVER returns a generic Bitcoin coin image. Instead, interprets
    the STORY behind the headline as a cinematic editorial scene."""
    
    import hashlib
    h = hashlib.md5(title.encode()).hexdigest()
    
    # Extract the core story from the title
    title_lower = title.lower()
    
    # Map story themes to SCENES (not objects)
    # The key insight: show the METAPHOR, not the literal subject
    
    scenes = []
    
    # Mining/hashrate stories → industrial, labor, machinery
    if any(w in title_lower for w in ["mining", "hashrate", "hash rate", "miner", "difficulty"]):
        scenes = [
            "abandoned industrial factory floor with single shaft of light through broken ceiling, dust particles floating, photojournalistic",
            "lone figure standing before massive wall of blinking server lights in dark warehouse, silhouette editorial",
            "heavy machinery gears grinding to halt with sparks flying, dramatic macro photography",
            "aerial shot of industrial landscape transitioning from active to dormant, golden hour editorial",
            "close-up of calloused hands adjusting heavy equipment dials, dramatic side lighting, documentary style",
            "vast empty warehouse where machines once hummed, single overhead light swinging, cinematic noir",
            "power plant cooling towers releasing steam against dramatic stormy sky, wide angle editorial",
            "worker walking away from facility at dawn, long shadow stretching behind, editorial portrait",
        ]
    
    # Network/resilience stories → infrastructure, systems, connectivity
    elif any(w in title_lower for w in ["network", "resilience", "node", "protocol"]):
        scenes = [
            "vast underground cable tunnel stretching to vanishing point, emergency lighting casting red glow",
            "massive bridge structure enduring violent storm, long exposure showing motion blur of waves",
            "spider web covered in morning dew catching golden light, extreme macro showing structural perfection",
            "electrical grid substation at blue hour with all connections illuminated, industrial editorial",
            "roots of ancient tree exposed showing massive underground network, cross-section nature photography",
            "air traffic control room with multiple screens glowing in darkness, cinematic documentary",
            "massive dam holding back turbulent water, shot from below looking up, dramatic wide angle",
            "telephone wires converging at horizon against dramatic sunset, minimalist editorial landscape",
        ]
    
    # Price/market stories → tension, pressure, movement
    elif any(w in title_lower for w in ["price", "market", "rally", "crash", "correction", "floor", "bull", "bear"]):
        scenes = [
            "tightrope walker silhouette between two skyscrapers at dusk, dramatic editorial photography",
            "pressure gauge needle in red zone with steam escaping, industrial macro photography",
            "ocean wave frozen at peak moment before breaking, dramatic high-speed photography",
            "chess pieces mid-game with dramatic raking light across the board, editorial still life",
            "fault line in cracked earth with light emerging from below, dramatic landscape editorial",
            "boxing ring ropes with sweat droplets frozen mid-air, dramatic sports editorial",
            "pendulum at apex of swing, motion blur trails, scientific photography style",
            "sand dune ridge line with wind sculpting patterns, aerial desert photography",
        ]
    
    # Regulation/government stories → power, institutions, authority
    elif any(w in title_lower for w in ["regulation", "sec", "fed", "congress", "law", "policy", "ban", "government"]):
        scenes = [
            "grand marble corridor with light streaming through distant doorway, architectural editorial",
            "massive gavel shadow cast across documents on desk, dramatic overhead lighting",
            "iron gates slowly closing with light narrowing between them, cinematic noir",
            "scales of justice with one side tipping, dramatic chiaroscuro studio photography",
            "labyrinthine bureaucratic filing system stretching endlessly, wide angle editorial",
            "single red pen on stack of white papers, minimalist editorial still life",
            "grand staircase in government building with figur

============================================================
MODEL: Article
============================================================
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    author = db.Column(db.String(100), default="Protocol Pulse AI")
    category = db.Column(db.String(50), default="Web3")
    tags = db.Column(db.String(500))
    source_url = db.Column(db.String(500))
    source_type = db.Column(db.String(50))
    featured = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    # Premium gating: None/'operator'/'commander'/'sovereign' — minimum tier to view
    premium_tier = db.Column(db.String(30), default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    seo_title = db.Column(db.String(200))
    seo_description = db.Column(db.String(300))
    substack_url = db.Column(db.String(500))
    header_image_url = db.Column(db.String(500))
    screenshot_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
