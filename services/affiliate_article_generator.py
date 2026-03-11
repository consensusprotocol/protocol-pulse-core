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
                "education_focus": "SIM-swap attack statistics, mobile malware targeting crypto wallets, the difference between secure enclaves and dedicated signing devices, attack surface analysis",
                "bridge": "Dedicated hardware signing devices remove the operating system attack surface entirely, isolating keys from internet-connected environments.",
            },
            {
                "topic": "What the $5 Wrench Attack Reveals About Bitcoin Security Theater",
                "problem_angle": "Most Bitcoin security advice focuses on digital threats while ignoring physical coercion. The '$5 wrench attack' thought experiment reveals gaps in single-signature setups that pure software solutions cannot address.",
                "education_focus": "physical security threat models, plausible deniability features, passphrase-protected hidden wallets, multi-location key distribution strategies",
                "bridge": "Modern hardware wallets with passphrase support enable hidden wallet architectures that provide plausible deniability under duress.",
            },
        ],
    },
    {
        "product": "river",
        "problems": [
            {
                "topic": "Why 73% of First-Time Bitcoin Buyers Choose the Wrong Exchange — And Pay the Price",
                "problem_angle": "Most newcomers buy Bitcoin on platforms that also sell thousands of speculative tokens, creating confusion and exposure to scams. Fee structures on major exchanges are deliberately opaque, often costing 2-5x what informed buyers pay.",
                "education_focus": "hidden fee structures on major exchanges, the altcoin casino problem, how spread-based pricing works, regulatory risks of platforms offering unregistered securities",
                "bridge": "A Bitcoin-only exchange eliminates the noise, the temptation, and the regulatory risk — with transparent fee structures designed for recurring buyers.",
            },
            {
                "topic": "The Psychology of Lump-Sum vs. DCA: What 15 Years of Bitcoin Data Actually Shows",
                "problem_angle": "Most people who want Bitcoin exposure agonize over timing. Research shows dollar-cost averaging into Bitcoin has outperformed lump-sum investing in 78% of 3-year windows, yet most platforms make DCA unnecessarily complicated.",
                "education_focus": "DCA performance data across Bitcoin cycles, psychological benefits of automated investing, volatility smoothing mathematics, behavioral economics of time-in-market vs timing",
                "bridge": "The most effective DCA strategy is one that runs on autopilot — automatic recurring purchases that remove emotion from the equation.",
            },
        ],
    },
    {
        "product": "unchained",
        "problems": [
            {
                "topic": "The Tax Trap: Why Selling Bitcoin for Liquidity Could Cost You More Than You Think",
                "problem_angle": "Bitcoin holders who need liquidity face a brutal choice: sell and trigger capital gains taxes (up to 37% for short-term), or find an alternative. Each sale is a taxable event that permanently reduces your stack.",
                "education_focus": "capital gains tax rates on crypto, the compounding cost of selling vs borrowing, real-world scenarios comparing sell vs borrow strategies, tax-loss harvesting limitations",
                "bridge": "Bitcoin-backed lending lets you access liquidity without selling — preserving your position and avoiding taxable events.",
            },
            {
                "topic": "Single-Signature Self-Custody: The Security Model That Keeps Experts Up at Night",
                "problem_angle": "A single seed phrase is a single point of failure. If it's compromised, stolen, or lost, there's no recovery. Security professionals increasingly advocate for eliminating single points of failure through distributed key management.",
                "education_focus": "single point of failure analysis, seed phrase theft vectors, the 2-of-3 multisig security model, key ceremony best practices, institutional-grade vs consumer-grade security",
                "bridge": "Collaborative multi-signature custody distributes trust across multiple keys and locations — no single compromise can result in loss.",
            },
        ],
    },
    {
        "product": "fold",
        "problems": [
            {
                "topic": "The Rewards Card Paradox: You're Earning Depreciating Points While You Could Be Stacking Sats",
                "problem_angle": "Americans earn $40+ billion in credit card rewards annually — but those rewards are denominated in airline miles, hotel points, and cashback dollars that all lose value over time. Meanwhile, Bitcoin has been the best-performing asset of the last decade.",
                "education_focus": "credit card rewards devaluation data, airline miles inflation, the opportunity cost of non-Bitcoin rewards, comparative returns of cashback vs BTC rewards over 5-year periods",
                "bridge": "Bitcoin rewards cards flip the script — turning everyday spending into accumulation of the hardest money ever created.",
            },
        ],
    },
    {
        "product": "swan",
        "problems": [
            {
                "topic": "Why Most People Fail at Bitcoin Accumulation — And the Simple System That Fixes It",
                "problem_angle": "The #1 reason people underperform in Bitcoin is emotional decision-making: buying high on FOMO, selling low on fear, and sitting on the sidelines during the best accumulation windows. Automation eliminates the human weakness.",
                "education_focus": "behavioral finance research on crypto investors, FOMO/FUD cycle analysis, historical data on automated vs manual Bitcoin buying, the time-in-market advantage",
                "bridge": "Automated dollar-cost averaging removes emotion entirely — set your amount, set your schedule, and let compound discipline work.",
            },
        ],
    },
    {
        "product": "casa",
        "problems": [
            {
                "topic": "The $240 Million Lesson: How Single Points of Failure Have Destroyed Bitcoin Fortunes",
                "problem_angle": "From James Howells' landfill hard drive to Stefan Thomas' locked IronKey, single points of failure have resulted in hundreds of millions in permanent Bitcoin loss. As holdings grow, the security model must evolve.",
                "education_focus": "famous Bitcoin loss cases with dollar amounts, security model maturation (exchange → software wallet → hardware → multisig), the security-convenience spectrum, when to upgrade your setup",
                "bridge": "Guided multi-signature custody eliminates every single point of failure — including you. No single key compromise, no single location disaster, no single human error can result in loss.",
            },
        ],
    },
    {
        "product": "strike",
        "problems": [
            {
                "topic": "Why International Remittances Still Cost 6.2% in 2026 — And the Lightning-Speed Alternative",
                "problem_angle": "The World Bank reports the global average remittance cost is 6.2% — meaning billions of dollars are extracted from the world's most vulnerable workers every year. Legacy payment rails are slow, expensive, and exclusionary.",
                "education_focus": "remittance cost data by corridor, settlement time comparisons (SWIFT vs Lightning), financial inclusion statistics, the unbanked population's relationship with mobile money",
                "bridge": "Lightning Network payments settle in seconds for fractions of a cent — making legacy remittance fees look like a relic of a broken system.",
            },
        ],
    },
]


class AffiliateArticleGenerator:
    """Generates educational problem-first articles with tasteful affiliate integration."""

    GENERATION_PROMPT = """You are a senior intelligence analyst writing for Protocol Pulse, a Bitcoin-focused media platform known for research-grade analysis. Your editorial voice channels Walter Cronkite: authoritative, measured, deeply trustworthy. You NEVER sound like a salesperson.

TODAY'S DATE: {today}

=== ASSIGNMENT ===
Write a deeply educational article about the following REAL problem:

TOPIC: {topic}
PROBLEM CONTEXT: {problem_angle}
EDUCATION FOCUS: {education_focus}

=== PSYCHOLOGICAL ARCHITECTURE (INVISIBLE TO READER) ===

Your article follows a think-tank research structure. The reader should feel like they're reading a Brookings Institution policy brief, not a product review:

1. PROBLEM AWARENESS (30% of article) — Open with a striking data point or real-world case that makes the problem visceral. The reader should think: "I didn't realize this was so serious."

2. COST OF INACTION (25% of article) — Use verifiable data to show what happens when this problem goes unaddressed. Historical examples, statistics, expert warnings. The reader should think: "I need to do something about this."

3. EXPERT CONSENSUS (20% of article) — Show that credible experts and institutions are already addressing this problem. Quote real people with real credentials. The reader should think: "Smart people are already solving this."

4. SOLUTION CATEGORY (15% of article) — Naturally introduce the CATEGORY of solution (not the product yet). Explain how this type of solution addresses the root cause. The reader should think: "This makes sense as a solution approach."

5. SPECIFIC TOOL (10% of article) — In the final section, mention ONE specific tool/service that implements this solution. This is where the affiliate product appears — but it should feel like a helpful recommendation from a trusted advisor, not an advertisement.

THE BRIDGE CONCEPT: {bridge}

=== AFFILIATE PRODUCT (USE SPARINGLY) ===
Product: {product_name}
URL: {product_url}
Description: {product_one_liner}

RULES FOR PRODUCT MENTION:
- Mention the product ONLY ONCE in the entire article, near the end
- Frame it as "one option worth exploring" or "a notable player in this space" — never as the only or best solution
- Include the affiliate link naturally in context, not as a call-to-action button
- The product mention should be NO MORE than 2 sentences
- Do NOT use words like "best," "only," "must-have," "game-changer," or any superlatives
- The article must be 90% education, 10% recommendation
- A reader who ignores the product mention should still find the article extremely valuable

=== ARTICLE STRUCTURE (MANDATORY) ===

Output clean HTML with these sections:

1. <div class="tldr-section"><em><strong>TL;DR: [3 punchy sentences about the PROBLEM and why it matters — do NOT mention the product here]</strong></em></div>

2. <h2 class="article-header">The Report</h2>
   Factual account of the problem with verified data (400+ words)

3. <h2 class="article-header">Exclusive Data Analysis</h2>
   Deep data on the problem's scope and cost (300+ words)
   Include specific numbers, percentages, historical comparisons

4. <h2 class="article-header">The Bitcoin Lens</h2>
   How this problem connects to Bitcoin philosophy and sovereignty (350+ words)
   Include expert perspectives from real, named individuals

5. <h2 class="article-header">Transactor Intelligence</h2>
   Actionable steps the reader can take to address this problem (250+ words)
   The affiliate product appears HERE — as one of several options or as a natural recommendation
   Format the affiliate link as: <a href="{product_url}" target="_blank" rel="sponsored">{product_name}</a>

6. <h2 class="article-header">Sources</h2>
   <ul class="sources-list"> with 5+ credible source URLs </ul>

=== FORMATTING ===
- Use <h2 class="article-header"> for section headers
- Use <h3 class="article-subheader"> for sub-sections
- Use <p class="article-paragraph"> for all paragraphs
- NO MARKDOWN — clean HTML only
- Target length: 1400-2000 words
- Use <ul class="sources-list"><li>https://...</li></ul> for sources

=== CRITICAL RULES ===
- ALL statistics must be verifiable — do NOT invent data points
- ALL expert quotes must be from real, named individuals who have publicly discussed this topic
- The article should be so educational that removing the product mention would NOT reduce its value
- Write as if you're briefing a Congressional committee, not selling a product
- The tone is analytical, not promotional
- Never use exclamation points
- Never say "you should buy" or "sign up today" or any direct sales language
"""

    def __init__(self):
        self.ai_service = None
        self._last_products_used: List[str] = []

    def _get_ai_service(self):
        if not self.ai_service:
            from services.ai_service import AIService
            self.ai_service = AIService()
        return self.ai_service

    def _pick_problem(self) -> Tuple[Dict, Dict]:
        """Pick a product and problem, rotating to avoid repetition."""
        with app.app_context():
            recent = Article.query.filter(
                Article.source_type == "affiliate_education",
                Article.created_at >= datetime.utcnow() - timedelta(days=7),
            ).all()
            recent_products = set()
            for a in recent:
                tags = a.tags or ""
                if tags.startswith("affiliate:"):
                    recent_products.add(tags.split("affiliate:", 1)[1].strip())

        available = [
            entry for entry in PROBLEM_SOLUTION_PLAYBOOK
            if entry["product"] not in recent_products
        ]
        if not available:
            available = PROBLEM_SOLUTION_PLAYBOOK

        entry = random.choice(available)
        problem = random.choice(entry["problems"])
        product = AFFILIATE_PRODUCTS[entry["product"]]
        return {**product, "id": entry["product"]}, problem

    def generate_affiliate_article(self, product_id: str = None, problem_index: int = None) -> Optional[Dict]:
        """Generate a single problem-first educational article with affiliate integration.

        Returns dict with article_id, title, product, or None on failure.
        """
        try:
            if product_id and product_id in AFFILIATE_PRODUCTS:
                entry = next((e for e in PROBLEM_SOLUTION_PLAYBOOK if e["product"] == product_id), None)
                if not entry:
                    logger.warning(f"No playbook entry for product: {product_id}")
                    return None
                product = {**AFFILIATE_PRODUCTS[product_id], "id": product_id}
                idx = problem_index if problem_index is not None and problem_index < len(entry["problems"]) else random.randint(0, len(entry["problems"]) - 1)
                problem = entry["problems"][idx]
            else:
                product, problem = self._pick_problem()

            today = datetime.utcnow().strftime("%B %d, %Y")
            prompt = self.GENERATION_PROMPT.format(
                today=today,
                topic=problem["topic"],
                problem_angle=problem["problem_angle"],
                education_focus=problem["education_focus"],
                bridge=problem["bridge"],
                product_name=product["name"],
                product_url=product["url"],
                product_one_liner=product["one_liner"],
            )

            ai = self._get_ai_service()
            content = ai.generate_content_anthropic(prompt)
            if not content or len(content) < 500:
                content = ai.generate_content_openai(prompt)
            if not content or len(content) < 500:
                logger.error("AI generation failed for affiliate article")
                return None

            title = problem["topic"]

            from services.content_generator import is_topic_duplicate_via_gemini
            if is_topic_duplicate_via_gemini(title):
                logger.info(f"Affiliate article duplicate detected: {title[:60]}")
                return None

            from services.content_engine import content_engine
            review = content_engine.multi_ai_review(title, content, topic=problem["education_focus"])

            if review.get("decision") != "APPROVE":
                logger.warning(
                    f"GROK REJECTED affiliate article: {title[:60]} — "
                    f"reason: {review.get('reason', 'unknown')[:200]}"
                )
                with app.app_context():
                    article = Article(
                        title=review.get("revised_title", title),
                        content=content,
                        category="education",
                        source_type="affiliate_education",
                        published=False,
                        tags=f"affiliate:{product['id']}",
                        seo_description=json.dumps({
                            "affiliate_product": product["id"],
                            "affiliate_url": product["url"],
                            "grok_rejected": True,
                            "grok_reason": review.get("reason", "")[:500],
                        })[:300],
                    )
                    db.session.add(article)
                    db.session.commit()
                    return {
                        "article_id": article.id,
                        "title": article.title,
                        "product": product["id"],
                        "published": False,
                        "grok_decision": "REJECT",
                        "grok_reason": review.get("reason", ""),
                    }

            final_title = review.get("revised_title") or title

            from services.content_generator import resolve_header_image_url
            header_img, src_url, src_type = resolve_header_image_url(final_title, content)

            with app.app_context():
                from services.content_generator import auto_publish_enabled
                should_publish = auto_publish_enabled()

                article = Article(
                    title=final_title,
                    content=content,
                    category="education",
                    source_type="affiliate_education",
                    cover_image_url=header_img,
                    published=should_publish,
                    tags=f"affiliate:{product['id']}",
                    seo_description=f"Affiliate: {product['name']}",
                )
                db.session.add(article)
                db.session.commit()

                logger.info(
                    f"AFFILIATE ARTICLE {'PUBLISHED' if should_publish else 'DRAFTED'}: "
                    f"id={article.id}, product={product['id']}, title='{final_title[:60]}'"
                )
                return {
                    "article_id": article.id,
                    "title": final_title,
                    "product": product["id"],
                    "published": should_publish,
                    "grok_decision": "APPROVE",
                    "grok_score": review.get("score", 0),
                }

        except Exception as e:
            logger.exception(f"Affiliate article generation failed: {e}")
            return None

    def generate_daily_pair(self) -> List[Dict]:
        """Generate 2 affiliate articles, each for a DIFFERENT product."""
        results = []
        used_products = set()

        for i in range(2):
            for attempt in range(3):
                result = self.generate_affiliate_article()
                if result and result.get("product") not in used_products:
                    used_products.add(result["product"])
                    results.append(result)
                    break
                elif result:
                    logger.info(f"Retry {attempt+1}: got duplicate product {result.get('product')}, trying again")

        logger.info(f"Daily affiliate pair complete: {len(results)} articles generated")
        return results


affiliate_article_generator = AffiliateArticleGenerator()
