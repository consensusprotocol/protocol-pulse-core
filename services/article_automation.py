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
from services.story_dedup import is_topic_oversaturated_v2
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

# Banned title templates — LLM prompt bleed patterns that must never be published
BANNED_TITLE_TEMPLATES = [
    r"Is Bitcoin'?s? Network Strength Signaling",
    r"Is Bitcoin'?s? Network (Resilience|Activity|Strength) Reaching",
    r"Is Bitcoin'?s? Hash Rate Surge Signaling",
    r"Bitcoin network and market update",  # generic placeholder
]

def _sanitize_title(title):
    """Strip prompt bleed (everything after first newline) and normalize whitespace."""
    import re
    # Remove everything after first newline — that's prompt bleed
    title = re.sub(r'[\r\n].*', '', title, flags=re.DOTALL).strip()

].*', '', title, flags=re.DOTALL).strip()
    # Collapse internal whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def _is_banned_template(title):
    """Return True if title matches a known low-quality template pattern."""
    import re
    for pattern in BANNED_TITLE_TEMPLATES:
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False

def _detect_topic(title):
    """Detect primary topic of an article from its title."""
    tl = title.lower()
    scores = {}
    for topic, kws in TOPIC_COOLDOWN_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in tl)
        if score > 0:
            scores[topic] = score
    return max(scores, key=scores.get) if scores else "general"

def _is_topic_oversaturated(title, max_same=1, hours=24):
    """Check if topic was covered in the last `hours`. Returns True to skip."""
    try:
        import models
        from app import db
        from datetime import datetime, timedelta
        import logging

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = (
            models.Article.query
            .filter(models.Article.created_at >= cutoff)
            .order_by(models.Article.created_at.desc())
            .all()
        )

        new_topic = _detect_topic(title)
        if new_topic == "general":
            return False

        count = sum(1 for a in recent if _detect_topic(a.title) == new_topic)
        if count >= max_same:
            logging.getLogger("article_automation").info(
                f"TOPIC DIVERSITY: Skipping '{title[:80]}' -- topic '{new_topic}' "
                f"already covered {count}x in last {hours}h"
            )
            return True
        return False
    except Exception as e:
        import logging
        logging.getLogger("article_automation").warning(
            f"Topic cooldown check failed for '{title[:80]}': {e}"
        )
        return False

# ============================================================
# HEADLINE DIVERSITY — no more than 30% starting with "Bitcoin"
# ============================================================
def _check_headline_diversity(hours=72):
    """Check if recent headlines are too 'Bitcoin'-heavy.
    Returns dict with ratio info and whether a new 'Bitcoin'-starting headline is allowed.
    """
    try:
        import models
        from app import db
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = (
            models.Article.query
            .filter(models.Article.created_at >= cutoff)
            .order_by(models.Article.created_at.desc())
            .all()
        )
        if len(recent) < 3:
            return {"allowed": True, "ratio": 0, "total": len(recent), "bitcoin_starts": 0}

        bitcoin_starts = sum(1 for a in recent if a.title.strip().lower().startswith("bitcoin"))
        ratio = bitcoin_starts / len(recent)
        allowed = ratio < 0.30
        if not allowed:
            logger.info(
                f"HEADLINE DIVERSITY: {bitcoin_starts}/{len(recent)} ({ratio:.0%}) start with 'Bitcoin' "
                f"— blocking new 'Bitcoin'-starting headlines"
            )
        return {"allowed": allowed, "ratio": ratio, "total": len(recent), "bitcoin_starts": bitcoin_starts}
    except Exception as e:
        logger.warning(f"Headline diversity check failed: {e}")
        return {"allowed": True, "ratio": 0, "total": 0, "bitcoin_starts": 0}


def _rewrite_headline_without_bitcoin(openai_client, title):
    """Ask GPT to rewrite a headline so it doesn't start with 'Bitcoin'."""
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"""Rewrite this headline so it does NOT start with the word "Bitcoin". Keep the same meaning, same sharp tone, under 10 words. Return ONLY the new headline, nothing else.

Original: {title}"""}],
            max_tokens=60,
            temperature=0.7
        )
        new_title = resp.choices[0].message.content.strip().strip('"').strip("'")
        if new_title and not new_title.lower().startswith("bitcoin"):
            logger.info(f"HEADLINE REWRITE: '{title}' -> '{new_title}'")
            return new_title
        return title
    except Exception as e:
        logger.warning(f"Headline rewrite failed: {e}")
        return title


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
            # Use Grok for web search
            from services.grok_service import grok_service

            search_result = grok_service.web_search(query, max_results=5)

            if search_result:
                for item in search_result:
                    url = item.get('url', '')

                    if url in self.used_urls:
                        continue

                    articles.append({
                        'title': item.get('title', ''),
                        'summary': item.get('snippet', '')[:1000],
                        'url': url,
                        'source': 'web_search',
                        'type': 'web'
                    })

        except Exception as e:
            logger.warning(f"Web search error: {e}")

        return articles

    def select_best_source(self) -> Optional[Dict]:
        """Select the best source for the next article"""

        # Gather all sources
        sources = []

        # Priority 1: Fresh RSS news
        rss_news = self.fetch_rss_news(limit=15)
        for item in rss_news:
            item['priority'] = 1
            sources.append(item)

        # Priority 2: Trending Reddit
        reddit_posts = self.fetch_reddit_posts(limit=10)
        for item in reddit_posts:
            item['priority'] = 2
            sources.append(item)

        if not sources:
            logger.error("No sources found!")
            return None

        # Prefer recent RSS news, but mix in Reddit for variety
        rss_sources = [s for s in sources if s['type'] == 'rss']
        reddit_sources = [s for s in sources if s['type'] == 'reddit']

        # 70% chance RSS, 30% Reddit if both available
        if rss_sources and reddit_sources:
            if random.random() < 0.7:
                source = random.choice(rss_sources[:5])  # Top 5 RSS
            else:
                source = random.choice(reddit_sources[:3])  # Top 3 Reddit
        elif rss_sources:
            source = random.choice(rss_sources[:5])
        elif reddit_sources:
            source = random.choice(reddit_sources[:3])
        else:
            return None

        logger.info(f"Selected source: {source['title'][:50]}... from {source['source']}")
        return source

    def generate_article_from_source(self, source: Dict) -> Optional[Dict]:
        """Generate article from real source material"""

        # Check headline diversity and build constraint if needed
        diversity = _check_headline_diversity(hours=72)
        headline_constraint = ""
        if not diversity["allowed"]:
            headline_constraint = f"""
HEADLINE CONSTRAINT (MANDATORY): {diversity['bitcoin_starts']}/{diversity['total']} recent headlines ({diversity['ratio']:.0%}) already start with "Bitcoin". Your headline MUST NOT start with the word "Bitcoin". Lead with the action, the player, or the consequence instead. Examples: "Mining Revenue Hits..." not "Bitcoin Mining Revenue Hits...", "Wall Street's Next Move..." not "Bitcoin ETF..."
"""

        prompt = f"""You are the senior editor at Protocol Pulse, a Bitcoin-native intelligence outlet. Your voice: Matt Taibbi's edge, Lyn Alden's precision, Michael Lewis's storytelling instinct. You write articles people screenshot and send to friends.
{headline_constraint}

SOURCE MATERIAL (verified, factual — invent nothing beyond this):
Title: {source['title']}
Source: {source['source']}
Content: {source['summary']}
URL: {source['url']}

===================================================================
STRUCTURAL ARCHITECTURE (follow this exactly)
===================================================================

Your article has 5 sections. Each one has a job. No section is optional.

1. THE HOOK (1-2 sentences, max 30 words)
   - Open with the single most interesting, surprising, or counterintuitive fact from the source
   - Or open with a sharp analogy, a vivid image, or a one-line scene
   - NEVER open with the company/project name + what they did. That is a summary, not a hook.
   - Test: Would this sentence make someone stop scrolling on X? If no, rewrite it.

   BAD: "Robinhood's Layer 2 testnet has logged four million transactions."
   GOOD: "Four million transactions in seven days — and Robinhood didn't need Bitcoin to do it."

   BAD: "Coinbase is expanding its lending product to altcoins."
   GOOD: "Coinbase just made it easier to borrow against Dogecoin. Read that again."

2. THE FACTS (2-3 sentences)
   - Deliver the core news clearly: who, what, how much, when
   - Use specific numbers from the source. If the source has no numbers, say so.
   - No analysis here. Just clean, hard facts.

3. THE ANALYSIS (2-3 paragraphs — this is 60% of the article)
   - This is where you EARN the reader's time
   - Answer: Who wins? Who loses? What does this change? What is the second-order effect?
   - Use at least ONE concrete comparison, analogy, or historical parallel
   - Use the 1-1-3 CADENCE: Short sentence. Short sentence. Then a longer sentence that develops the idea and gives the reader room to absorb what you just said.
   - Embed ONE shareable line — a single sentence so sharp it could be posted alone on X and get engagement. Bold this line in the HTML using <strong> tags.
   - VARY your analytical angles across articles. Rotate between:
     * Market structure angle (who gets the money, who loses it)
     * Technology angle (what does this actually enable or break)
     * Regulatory angle (who gains or loses power)
     * Game theory angle (what are the incentives, who moves next)
     * Historical parallel (when has something like this happened before)

4. THE BITCOIN LENS (1-2 sentences — ONLY when it genuinely connects)
   Apply the following decision tree:

   IF the story is directly about Bitcoin: analyze it as Bitcoin news. No comparison needed.
   IF the story is about altcoins/DeFi: your angle is what it reveals about the market, NOT "but Bitcoin is better." You can note Bitcoin's structural differences in ONE specific, concrete sentence. Not a sermon.
   IF the story is about regulation/macro: connect to Bitcoin ONLY if there is a direct, factual link. Not every regulation story needs a Bitcoin take.
   IF there is no natural Bitcoin connection: SKIP THIS SECTION ENTIRELY. It is better to say nothing than to force a generic "Bitcoin remains king" sentence.

   WHEN you do reference Bitcoin, be SPECIFIC:
   BAD: "Bitcoin's decentralized nature makes it superior"
   GOOD: "Bitcoin settles $12 billion daily with no counterparty risk. No Layer 2 migration required."

   BAD: "Bitcoin remains the gold standard of digital assets"
   GOOD: "Ledn's bonds exist because one asset has 15 years of unbroken uptime. That is the collateral story."

5. THE CLOSE (1-2 sentences)
   - End with a forward-looking insight, a specific prediction, or a provocative statement
   - ROTATE your closing style. Never use the same format twice in a row:
     * The prediction: "If X happens, expect Y within 90 days."
     * The provocation: Make a bold claim the reader will want to argue with
     * The zoom-out: Connect this small story to a much larger trend
     * The one-liner: A single memorable sentence that sticks
   - NEVER end with: "The question remains..." or "Only time will tell..." or "Will X or Y?"
   - Test: Would someone quote your last sentence? If not, rewrite it.

===================================================================
WRITING RULES
===================================================================

RHYTHM AND CADENCE:
- Alternate sentence lengths aggressively. Three words. Then twelve. Then thirty that build and layer and pull the reader forward through the logic of your argument until they arrive at the point you wanted them to reach.
- Never stack more than 2 sentences of the same length back to back.
- Read it out loud. If it sounds monotone, break the pattern.

ANTI-REPETITION (CRITICAL):
- State every point ONCE. If you catch yourself reinforcing the same idea, you are padding.
- Never use two different metaphors to make the same point.
- If your article has 4+ paragraphs and they could be rearranged in any order without the reader noticing, your structure has failed. Each paragraph should depend on the one before it.

SHOW OVER TELL:
- Replace every abstract claim with a concrete fact, image, or comparison
- "This is significant" means DELETE. Show WHY by showing what changes.
- "Bitcoin is more secure" becomes "Bitcoin's network burns more energy than Argentina securing transactions. That is not a bug."

SPECIFICITY:
- Use exact numbers from the source: $188M not "nearly $200M"
- Name names: companies, people, protocols
- If the source does not give you numbers, write "the company did not disclose figures" — never fill the gap with vague language

TONE:
- Confident but not arrogant
- Skeptical but not cynical
- Opinionated when you have earned it with facts
- Conversational: contractions, direct address, occasional dry humor
- Think: smart colleague sharing intel over coffee, not a press release

===================================================================
BANNED PATTERNS
===================================================================

PHRASES (instant failure):
"It is worth noting" / "It's important to note" / "This underscores" / "This highlights"
"Furthermore" / "Moreover" / "In conclusion" / "The broader landscape"
"The real question is" / "Meanwhile, Bitcoin..." / "In the grand scheme"
"The question remains" / "Only time will tell" / "It remains to be seen"
"Paradigm" / "Burgeoning" / "Emblematic" / "Grapples with"
"At the forefront" / "Microcosm" / "A testament to" / "The intersection of"
"The convergence of" / "In the realm of" / "Compelling narrative"
"The evolving landscape" / "As we move forward" / "Rapidly evolving"
"In this context" / "The significance of" / "The trajectory of"
"A beacon of" / "A pillar of" / "Serves as a" / "Fostering"
"The dynamic nature of" / "In a world where" / "Stands as a silent testament"
"Unmatched" / "Unparalleled" / "Steadfast" / "Stalwart" / "Bedrock"
"Sets it apart" / "In a league of its own" / "Gold standard"

STRUCTURAL BANS:
- Never open with "[Company] has [done thing]" — that is a press release, not journalism
- Never close with "Will X happen, or will Y?" — that is a cop-out, not a close
- Never have 2 consecutive paragraphs that make the same point in different words
- Never use "Bitcoin is better" as analysis. Show the structural difference with a specific fact.
- Never end an altcoin story with a generic Bitcoin superiority statement

===================================================================
FORMAT
===================================================================

<h1 class="article-header">[Sharp, specific headline — under 10 words preferred]</h1>
<div class="tldr-section"><em><strong>TL;DR: [2-3 sentences. Pure facts. No opinion. Tight as possible.]</strong></em></div>
<p class="article-paragraph">[HOOK]</p>
<p class="article-paragraph">[FACTS]</p>
<p class="article-paragraph">[ANALYSIS — paragraph 1]</p>
<p class="article-paragraph">[ANALYSIS — paragraph 2, with <strong>shareable line</strong> embedded]</p>
<p class="article-paragraph">[BITCOIN LENS — only if natural, otherwise skip]</p>
<p class="article-paragraph">[CLOSE]</p>
<h2 class="article-header">Sources</h2>
<ul class="sources-list"><li><a href="{source['url']}">{source['source']}</a></li></ul>

Target: 450-650 words. No shorter than 400. Every sentence earns its place or gets cut.
Clean HTML only. No markdown. No backticks. No code fences.
"""

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o",  # Using GPT-4o for article generation
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )

            content = response.choices[0].message.content

            # Extract title from h1 tag
            import re
            title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
            title = title_match.group(1) if title_match else source['title']

            # Extract summary from tldr
            tldr_match = re.search(r'TL;DR:\s*([^<]+)', content)
            summary = tldr_match.group(1).strip() if tldr_match else source['summary'][:200]

            return {
                'title': title,
                'content': content,
                'summary': summary,
                'source_url': source['url'],
                'source_type': source['type'],
                'source_name': source['source']
            }

        except Exception as e:
            logger.error(f"Error generating article: {e}")

            # Fallback to Anthropic direct
            try:
                from services.ai_service import AIService
                ai = AIService()
                content = ai.generate_content_anthropic(prompt)

                if content:
                    import re
                    title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
                    title = title_match.group(1) if title_match else source['title']

                    # Try to extract TL;DR from generated content first
                    tldr_match2 = re.search(r'TL;DR:\s*([^<]+)', content)
                    fallback_summary = tldr_match2.group(1).strip()[:280] if tldr_match2 else source['summary'][:200]
                    return {
                        'title': title,
                        'content': content,
                        'summary': fallback_summary,
                        'source_url': source['url'],
                        'source_type': source['type'],
                        'source_name': source['source']
                    }
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")

        return None


def run_article_generation_cycle() -> Dict:
    """
    Main entry point for article generation.
    Fetches real news, generates article, reviews with Grok.
    """
    result = {
        "success": False,
        "article_id": None,
        "title": None,
        "published": False,
        "grok_score": 0,
        "error": None
    }

    try:
        generator = RealNewsArticleGenerator()

        # 1. Select best source
        source = generator.select_best_source()
        if not source:
            result["error"] = "No fresh sources available"
            return result

        # EARLY DEDUP: Check before wasting generation resources
        source_title = source.get('title', '')
        if source_title:
            # V5 dedup: GPT-4o-mini semantic + keyword count + category rotation
            if is_topic_oversaturated_v2(source_title, max_same=1, hours=24):
                logger.info(f"EARLY SKIP: Dedup blocked: {source_title[:80]}")
                return {
                    'success': False, 'skipped': True,
                    'reason': 'topic_oversaturated_early',
                    'title': source_title
                }

        # 2. Generate article from source
        article_data = generator.generate_article_from_source(source)
        if not article_data:
            result["error"] = "Failed to generate article"
            return result

        result["title"] = article_data['title']

        # 3. Review with Grok
        from services.grok_review_service import grok_review_service

        review = grok_review_service.review_article(
            article_data['title'],
            article_data['content'],
            topic=f"Source: {source['source']} - {source['title']}"
        )

        grok_score = review.get('score', 0)
        result["grok_score"] = grok_score

        # Log critical errors if any
        for error in review.get('critical_errors', []):
            logger.warning(f"  CRITICAL ERROR: {error}")

        # 4. Determine if publishable
        # Lower threshold for articles from trusted sources
        trusted_sources = ['bitcoinmagazine', 'coindesk', 'cointelegraph', 'decrypt', 'theblock']
        is_trusted = any(src in source.get('source', '').lower() for src in trusted_sources)

        threshold = 60 if is_trusted else 70  # Lower bar for trusted sources

        should_publish = (
            review.get('decision') == 'APPROVE' or 
            grok_score >= threshold
        )

        if is_trusted and grok_score >= 50:
            logger.info(f"Trusted source ({source['source']}) - considering for publication")

        # Use revised title if provided
        # SANITIZE: strip prompt bleed (everything after first newline)
        raw_title = review.get('revised_title') or article_data['title']
        final_title = _sanitize_title(raw_title)

        # BANNED TEMPLATE GATE: reject low-quality template headlines before any further work
        if _is_banned_template(final_title):
            logger.warning(f"BANNED TEMPLATE: rejecting article with template title: {final_title[:80]}")
            return {
                'success': False, 'skipped': True,
                'reason': 'banned_template_title',
                'title': final_title,
            }

        # 4b. Headline diversity gate — rewrite if over 30% "Bitcoin" starts
        diversity = _check_headline_diversity(hours=72)
        if not diversity["allowed"] and final_title.strip().lower().startswith("bitcoin"):
            final_title = _rewrite_headline_without_bitcoin(generator.openai, final_title)
            logger.info(f"  DIVERSITY REWRITE applied: '{article_data['title']}' -> '{final_title}'")

        # 5. POST-GENERATION DEDUP: check the final title too
        try:
            from services.story_dedup import is_semantic_duplicate
            if is_semantic_duplicate(final_title, hours=48):
                logger.info(f"POST-GEN SKIP: final title is semantic duplicate: {final_title[:80]}")
                return {
                    'success': False, 'skipped': True,
                    'reason': 'semantic_duplicate_post_gen',
                    'title': final_title,
                }
        except Exception as e:
            logger.warning(f"Post-gen dedup check failed (proceeding): {e}")

        # 6. Save to database
        from app import app, db
        from models import Article
        from services.image_service import ImageGenerationService

        with app.app_context():
            # Generate header image — Pexels→Grok→OpenAI→branded-fallback chain
            header_image = None
            try:
                img_service = ImageGenerationService()
                header_image = img_service.generate_article_header_image(
                    title=final_title,
                    category=article_data.get('category', 'Bitcoin')
                )
                if header_image:
                    logger.info(f"Header image generated: {header_image}")
                else:
                    logger.warning("Image service returned None — article will show branded fallback")
            except Exception as e:
                logger.error(f"Image generation failed entirely: {e}")
                header_image = None

            # HARD GATE: 24h topic cooldown
            if final_title and _is_topic_oversaturated(final_title, max_same=2, hours=48):
                logger.info('Skipping article due to 48h topic cooldown: ' + repr(final_title[:120]))
                return {'success': False, 'skipped': True, 'reason': 'topic_oversaturated', 'title': final_title}

            article = Article(
                title=final_title,
                content=article_data['content'],
                summary=article_data['summary'],
                author="Protocol Pulse AI",
                category="Bitcoin",
                source_url=article_data['source_url'],
                source_type=article_data['source_type'],
                published=should_publish,
                published_at=datetime.utcnow() if should_publish else None,
                cover_image_url=header_image
            )

            db.session.add(article)
            db.session.commit()

            result["article_id"] = article.id
            result["published"] = should_publish
            result["success"] = True

            logger.info(f"Article saved: id={article.id}, published={should_publish}, grok_score={grok_score}")

            if review.get('revised_title'):
                logger.info(f"  REVISED TITLE: {review['revised_title']}")

        return result

    except Exception as e:
        logger.error(f"Article generation cycle failed: {e}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)
        return result


# For backward compatibility
def get_unique_topic():
    """Deprecated - now using real news sources"""
    generator = RealNewsArticleGenerator()
    source = generator.select_best_source()
    return source['title'] if source else "Bitcoin market analysis"


def generate_article_with_review():
    """Wrapper for run_article_generation_cycle"""
    return run_article_generation_cycle()




def is_duplicate_title(title, hours=48):
    """Check if a similar article was published recently."""
    from datetime import datetime, timedelta
    import models
    from app import db

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    recent = models.Article.query.filter(
        models.Article.created_at > cutoff,
        models.Article.published == True
    ).all()

    new_words = set(title.lower().split())

    for article in recent:
        existing_words = set(article.title.lower().split())
        if not existing_words:
            continue
        overlap = len(new_words & existing_words) / max(len(new_words | existing_words), 1)
        if overlap > 0.45:
            return True
        new_start = ' '.join(title.lower().split()[:4])
        existing_start = ' '.join(article.title.lower().split()[:4])
        if new_start == existing_start and len(new_start) > 15:
            return True

    return False

def generate_affiliate_article(partner_key: str, topic: str = None) -> Dict:
    """
    Generate an editorial-style affiliate article for a partner.

    partner_key: one of 'meanwhile', 'curated_mining', 'trezor', 'river', 
                 'swan', 'fold', 'casa', 'unchained', 'strike', 'amazon'
    topic: optional specific angle. If None, uses default angle for partner.
    """
    import openai
    import os
    import re
    import logging
    from services.image_service import generate_article_header_image
    from app import db
    import models

    logger = logging.getLogger(__name__)

    PARTNERS = {
        "meanwhile": {
            "name": "Meanwhile",
            "url": "https://application.meanwhile.bm/start?referralCode=KKM73K",
            "description": "Bitcoin-denominated whole life insurance. Death benefit paid in Bitcoin, no fiat conversion.",
            "default_topic": "What happens to your Bitcoin when you die? Most Bitcoiners have no plan."
        },
        "curated_mining": {
            "name": "Curated Mining",
            "url": "https://curatedmining.com",
            "description": "White-glove Bitcoin mining partnership. Form your own LLC, 100% tax deductible, decade of deployment experience.",
            "default_topic": "The hidden tax advantage most high-earning Bitcoiners are missing: accelerated depreciation through mining."
        },
        "trezor": {
            "name": "Trezor",
            "url": "https://trezor.io/?ref=protocolpulse",
            "description": "Open-source hardware wallet for Bitcoin self-custody. Air-gapped signing, shamir backup.",
            "default_topic": "A self-custody security audit: the 5 weakest links in most Bitcoiners' setups."
        },
        "river": {
            "name": "River",
            "url": "https://river.com/?ref=protocolpulse",
            "description": "Bitcoin-only exchange with automatic DCA, Lightning withdrawals, and zero trading fees on recurring buys.",
            "default_topic": "Dollar-cost averaging into Bitcoin: the math behind why timing the market loses to time in the market."
        },
        "swan": {
            "name": "Swan Bitcoin",
            "url": "https://swanbitcoin.com/?ref=protocolpulse",
            "description": "Automatic Bitcoin DCA plans, IRA options, and advisor network for long-term stackers.",
            "default_topic": "Bitcoin in your retirement account: what most financial advisors won't tell you about self-directed IRAs."
        },
        "fold": {
            "name": "Fold",
            "url": "https://foldapp.com/?ref=protocolpulse",
            "description": "Bitcoin rewards debit card. Earn sats on every purchase without spending crypto.",
            "default_topic": "The quiet way Bitcoiners are stacking sats on groceries, gas, and coffee without changing their spending habits."
        },
        "casa": {
            "name": "Casa",
            "url": "https://keys.casa/?ref=protocolpulse",
            "description": "Multi-signature Bitcoin self-custody with guided setup, inheritance planning, and key recovery.",
            "default_topic": "The single point of failure problem: why your Bitcoin security model probably has a fatal flaw."
        },
        "unchained": {
            "name": "Unchained",
            "url": "https://unchained.com/?ref=protocolpulse",
            "description": "Bitcoin-backed loans and collaborative custody. Access liquidity without selling your stack.",
            "default_topic": "Need cash but refuse to sell your Bitcoin? The tax math behind borrowing against your stack instead."
        },
        "strike": {
            "name": "Strike",
            "url": "https://strike.me/?ref=protocolpulse",
            "description": "Instant Bitcoin purchases, Lightning-native payments, and get-paid-in-Bitcoin features.",
            "default_topic": "Getting paid in Bitcoin in 2026: how to set it up and why the Lightning Network makes it practical."
        },
        "amazon": {
            "name": "Amazon",
            "url": "https://www.amazon.com/?tag=protocolpulse-20",
            "description": "Bitcoin books, seed storage, Faraday bags, hardware accessories, and sovereignty tools on Amazon. IMPORTANT: You MUST name 3-5 SPECIFIC real products with approximate prices. Example: Billfodl steel seed backup (~$55), Coldcard Mk4 (~$150), The Bitcoin Standard by Saifedean Ammous (~$15), Mission Darkness Faraday Bag (~$30), Blockstream Jade hardware wallet (~$65). Use the affiliate tag protocolpulse-20 in any Amazon links. NEVER link to generic amazon.com — always link to specific product search URLs like https://www.amazon.com/s?k=billfodl+seed+storage&tag=protocolpulse-20",
            "default_topic": "The Bitcoiner's essential gear list: 5 physical products under $200 that every serious holder should own, with specific names and prices."
        }
    }

    partner = PARTNERS.get(partner_key)
    if not partner:
        return {"success": False, "error": f"Unknown partner: {partner_key}. Options: {list(PARTNERS.keys())}"}

    article_topic = topic or partner["default_topic"]

    prompt = f"""You are the senior editor at Protocol Pulse, a Bitcoin-native intelligence outlet. Your voice: Matt Taibbi's edge, Lyn Alden's precision, Michael Lewis's storytelling instinct. You write articles people screenshot and send to friends.

You are writing an EDITORIAL GUIDE — a genuinely useful article that helps Bitcoiners solve a real problem or level up their strategy. A product or service appears naturally as the best solution. The reader should feel like they learned something valuable, NOT like they read an ad.

PARTNER CONTEXT:
Partner: {partner["name"]}
Partner URL: {partner["url"]}
Partner Description: {partner["description"]}
Topic/Angle: {article_topic}

THE GOLDEN RULE: 80% EDUCATION, 20% PRODUCT. The article must be valuable even if the reader never clicks the link. If it reads like a sponsored post, you have failed.

STRUCTURAL ARCHITECTURE:
1. THE HOOK (1-2 sentences, max 30 words) - Open with a problem the reader recognizes. Product does NOT appear until section 4. NEVER open with the product name.
2. THE PROBLEM (2-3 paragraphs) - Deep dive into the actual problem. Teach something. Use specific scenarios, numbers, real examples. This section should be useful on its own.
3. THE LANDSCAPE (1-2 paragraphs) - Survey the options honestly. Mention alternatives including DIY. Build credibility by showing you know the space.
4. THE SOLUTION (2-3 paragraphs) - Introduce the partner product as the natural answer. Be SPECIFIC about what it does. Include ONE concrete detail only someone who researched the product would know. Embed ONE shareable line in <strong> tags about the broader principle. Include the affiliate link naturally.
5. THE CLOSE (1-2 sentences) - End with a principle, not a pitch. Zoom out to sovereignty, security, or freedom. Product-agnostic final sentence.

WRITING RULES:
- Write like a trusted expert friend, not a salesperson
- Skeptical by default. Earned praise means more.
- Use 1-1-3 cadence. Alternate sentence lengths aggressively.
- If the product has limitations, mention them briefly. It builds trust.
- Use exact numbers, real scenarios, named alternatives.

BANNED PATTERNS (instant failure):
"Game-changer" / "Must-have" / "Best in class" / "Industry-leading"
"We partnered with" / "Our friends at" / "Proud to announce"
"Use code" / "Limited time" / "Act now" / "Don't miss out"
"It is worth noting" / "This underscores" / "This highlights"
"Furthermore" / "Moreover" / "In conclusion" / "The broader landscape"
"Paradigm" / "Burgeoning" / "Emblematic" / "A testament to"
"Unmatched" / "Unparalleled" / "Stalwart" / "Bedrock" / "Gold standard"
Product NEVER appears in headline or TL;DR.
Product NEVER appears in first 2 paragraphs.
Article NEVER ends with a direct product CTA.

FORMAT:
<h1 class="article-header">[Problem-focused headline — product NOT mentioned]</h1>
<div class="tldr-section"><em><strong>TL;DR: [2-3 sentences about the PROBLEM and INSIGHT, not the product]</strong></em></div>
<p class="article-paragraph">[HOOK]</p>
<p class="article-paragraph">[PROBLEM paragraph 1]</p>
<p class="article-paragraph">[PROBLEM paragraph 2]</p>
<p class="article-paragraph">[LANDSCAPE]</p>
<p class="article-paragraph">[SOLUTION with <strong>shareable line</strong> and natural affiliate link]</p>
<p class="article-paragraph">[SOLUTION details]</p>
<p class="article-paragraph">[CLOSE — principle, not pitch]</p>
<h2 class="article-header">Sources</h2>
<ul class="sources-list"><li><a href="{partner["url"]}">{partner["name"]}</a></li></ul>

Target: 500-750 words. 80% education, 20% product. Clean HTML only. No markdown. No backticks.
"""

    try:
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.7
        )

        content = response.choices[0].message.content

        # Strip code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("html"):
                content = content[4:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
        title = title_match.group(1) if title_match else article_topic

        # Extract summary
        tldr_match = re.search(r'TL;DR:\s*([^<]+)', content)
        summary = tldr_match.group(1).strip() if tldr_match else article_topic[:200]

        # Generate editorial image
        header_image = None
        try:
            img_service = __import__("services.image_service", fromlist=["generate_article_header_image"])
            header_image = img_service.generate_article_header_image(title)
        except Exception as e:
            logger.warning(f"Image generation failed: {e}")

        # Save to DB
        article = models.Article(
            title=title,
            content=content,
            summary=summary,
            category="guides",
            tags=f"affiliate,{partner_key},{partner['name'].lower()}",
            source_url=partner["url"],
            source_type="affiliate",
            published=True,
            cover_image_url=header_image
        )
        db.session.add(article)
        db.session.commit()

        logger.info(f"Affiliate article saved: id={article.id}, partner={partner_key}")

        return {
            "success": True,
            "article_id": article.id,
            "title": title,
            "partner": partner_key,
            "word_count": len(content.split())
        }

    except Exception as e:
        logger.error(f"Affiliate article generation failed: {e}")
        return {"success": False, "error": str(e)}


def get_next_affiliate_partner() -> str:
    """
    Rotate through affiliate partners so content stays varied.
    Uses day-of-year + slot number to deterministically pick a partner.
    """
    from datetime import datetime
    import json
    from pathlib import Path

    partners = ["meanwhile", "curated_mining", "trezor", "river", "swan",
                "fold", "casa", "unchained", "strike", "amazon"]

    # Track what we've published today
    tracker_file = Path("config/affiliate_tracker.json")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    tracker = {}
    if tracker_file.exists():
        try:
            tracker = json.loads(tracker_file.read_text())
        except:
            tracker = {}

    # Reset if new day
    if tracker.get("date") != today:
        tracker = {"date": today, "published": []}

    published_today = tracker.get("published", [])

    # Pick next partner not yet published today
    day_offset = datetime.utcnow().timetuple().tm_yday
    for i in range(len(partners)):
        idx = (day_offset + len(published_today) + i) % len(partners)
        candidate = partners[idx]
        if candidate not in published_today:
            # Record it
            published_today.append(candidate)
            tracker["published"] = published_today
            tracker_file.parent.mkdir(parents=True, exist_ok=True)
            tracker_file.write_text(json.dumps(tracker))
            return candidate

    # All published today (shouldn't happen with 10 partners and 3 slots)
    return partners[day_offset % len(partners)]


def run_scheduled_affiliate_article() -> Dict:
    """
    Called by scheduler 3x/day. Picks next partner in rotation,
    generates editorial article, returns result.
    """
    import logging
    logger = logging.getLogger(__name__)

    partner = get_next_affiliate_partner()
    logger.info(f"[AFFILIATE] Generating editorial article for: {partner}")

    result = generate_affiliate_article(partner)

    if result.get("success"):
        logger.info(f"[AFFILIATE] Published: {result.get('title', '')[:50]} (partner={partner})")
    else:
        logger.error(f"[AFFILIATE] Failed for {partner}: {result.get('error', 'unknown')}")

    return result


def get_next_affiliate_partner() -> str:
    """
    Rotate through affiliate partners so content stays varied.
    Uses day-of-year + slot number to deterministically pick a partner.
    """
    from datetime import datetime
    import json
    from pathlib import Path

    partners = ["meanwhile", "curated_mining", "trezor", "river", "swan",
                "fold", "casa", "unchained", "strike", "amazon"]

    # Track what we've published today
    tracker_file = Path("config/affiliate_tracker.json")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    tracker = {}
    if tracker_file.exists():
        try:
            tracker = json.loads(tracker_file.read_text())
        except:
            tracker = {}

    # Reset if new day
    if tracker.get("date") != today:
        tracker = {"date": today, "published": []}

    published_today = tracker.get("published", [])

    # Pick next partner not yet published today
    day_offset = datetime.utcnow().timetuple().tm_yday
    for i in range(len(partners)):
        idx = (day_offset + len(published_today) + i) % len(partners)
        candidate = partners[idx]
        if candidate not in published_today:
            # Record it
            published_today.append(candidate)
            tracker["published"] = published_today
            tracker_file.parent.mkdir(parents=True, exist_ok=True)
            tracker_file.write_text(json.dumps(tracker))
            return candidate

    # All published today (shouldn't happen with 10 partners and 3 slots)
    return partners[day_offset % len(partners)]


def run_scheduled_affiliate_article() -> Dict:
    """
    Called by scheduler 3x/day. Picks next partner in rotation,
    generates editorial article, returns result.
    """
    import logging
    logger = logging.getLogger(__name__)

    partner = get_next_affiliate_partner()
    logger.info(f"[AFFILIATE] Generating editorial article for: {partner}")

    result = generate_affiliate_article(partner)

    if result.get("success"):
        logger.info(f"[AFFILIATE] Published: {result.get('title', '')[:50]} (partner={partner})")
    else:
        logger.error(f"[AFFILIATE] Failed for {partner}: {result.get('error', 'unknown')}")

    return result
