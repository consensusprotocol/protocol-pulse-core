"""
Generate 10 unique, current-topic articles with pre-generated hyper-realistic header images.
Uses Claude (Anthropic) as the primary AI since OpenAI is over quota.
"""
import os
import sys
import logging
import time

logging.basicConfig(level=logging.INFO)

from app import app, db
from models import Article
from pp_services.ai_service import AIService
from datetime import datetime

ARTICLES = [
    {
        "topic": "Bitcoin drops to $68,000 amid extreme fear index readings not seen since FTX collapse — orderly deleveraging with $8.7 billion in realized losses, VanEck analysts say this is healthy correction, futures open interest dropped 20%",
        "image": "/static/images/headers/hyper_btc_fear_correction.png",
        "category": "Bitcoin",
    },
    {
        "topic": "Brazil reintroduces legislation to acquire 1 million BTC (~$69 billion) as strategic reserve, intensifying the nation-state Bitcoin accumulation race alongside El Salvador and proposed US strategic reserve",
        "image": "/static/images/headers/hyper_brazil_btc_reserve.png",
        "category": "Bitcoin",
    },
    {
        "topic": "X (Twitter) prepares to launch in-app crypto and stock trading with Smart Cashtags feature — users will tap tickers to see live prices and trade directly, massive implications for Bitcoin adoption",
        "image": "/static/images/headers/hyper_x_crypto_trading.png",
        "category": "Bitcoin",
    },
    {
        "topic": "US Bitcoin ETFs flip to net sellers in 2026 after purchasing 46,000 BTC in early 2025 — digital asset funds recorded $1.7 billion outflows, year-to-date outflows total $1 billion",
        "image": "/static/images/headers/hyper_etf_outflows.png",
        "category": "Markets",
    },
    {
        "topic": "Grayscale files S-1 for spot AAVE ETF while Bitwise files similar product — the crypto ETF race expands beyond Bitcoin and Ethereum into DeFi tokens for the first time",
        "image": "/static/images/headers/hyper_defi_etf.png",
        "category": "DeFi",
    },
    {
        "topic": "Bitcoin mining difficulty holds at 146 T while network hashrate approaches 1 EH/s — network security remains robust despite 30% price correction from the October 2025 all-time high of $126,000",
        "image": "/static/images/headers/hyper_mining_difficulty.png",
        "category": "Bitcoin",
    },
    {
        "topic": "Kevin Warsh nominated to replace Jerome Powell as Federal Reserve Chair — markets assess what new Fed leadership means for interest rate policy, risk assets, and Bitcoin's macro trajectory",
        "image": "/static/images/headers/hyper_fed_chair.png",
        "category": "Macro",
    },
    {
        "topic": "Lightning Network payment volume hits new records as merchants accelerate adoption during the bear market — building infrastructure through the downturn as transaction costs near zero",
        "image": "/static/images/headers/hyper_lightning_network.png",
        "category": "Lightning",
    },
    {
        "topic": "IRS Form 1099-DA creates new tax compliance burden for US crypto holders in 2026 — how the reporting requirements reshape self-custody strategies and what transactors need to know",
        "image": "/static/images/headers/hyper_irs_crypto_tax.png",
        "category": "Regulation",
    },
    {
        "topic": "Solana crashes to $88 two-year low while Ethereum loses 33% in one week — altcoin carnage deepens as capital rotates back to Bitcoin dominance, Fear & Greed Index at levels last seen during FTX collapse",
        "image": "/static/images/headers/hyper_altcoin_crash.png",
        "category": "Markets",
    },
]

SYSTEM_PROMPT = """You are Sarah, the lead intelligence analyst at Protocol Pulse — a Bitcoin-first intelligence publication. 
Your editorial voice channels Walter Cronkite: authoritative, measured, trustworthy.

Write every piece as a peer-to-peer intelligence briefing for "transactors" (active Bitcoin users).

MANDATORY ARTICLE STRUCTURE (use this EXACT HTML formatting):

1. Start with: <div class="tldr-section"><em><strong>TL;DR: [2-3 sentence summary]</strong></em></div>

2. <h2 class="article-header">The Report</h2>
   <p class="article-paragraph">[Main news coverage - 3-4 paragraphs of factual reporting]</p>

3. <h2 class="article-header">The Bitcoin Lens</h2>
   <p class="article-paragraph">[How this connects to Bitcoin's thesis - monetary sovereignty, decentralization, sound money - 2-3 paragraphs]</p>

4. <h2 class="article-header">Transactor Intelligence</h2>
   <p class="article-paragraph">[Actionable insights for Bitcoin holders - what to watch, what to do, key levels - 2-3 paragraphs]</p>

5. <h2 class="article-header">Sources</h2>
   <ul class="sources-list"><li>[Real source URLs from major outlets like CoinDesk, Bloomberg, CNBC, Reuters]</li></ul>

RULES:
- Target 800-1200 words
- Use ONLY real, verifiable facts from February 2026
- NO fabricated statistics or made-up quotes
- Headline must be a declarative statement (NOT a question)
- Start your response with the headline on its own line, then the article HTML
- Do NOT wrap in markdown code blocks"""


def generate_article_with_claude(topic, image_url, category, index):
    """Generate a single article using Claude and save with pre-generated image."""
    print(f"\n{'='*60}")
    print(f"[{index+1}/10] Generating: {topic[:70]}...")
    print(f"{'='*60}")
    
    with app.app_context():
        try:
            ai = AIService()
            
            if not ai.anthropic_client:
                print(f"  FAILED: Anthropic client not available")
                return None
            
            prompt = f"Write a comprehensive intelligence briefing article about: {topic}"
            
            response = ai.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response or not response.content:
                print(f"  FAILED: No response from Claude")
                return None
            
            full_text = response.content[0].text.strip()
            
            lines = full_text.split('\n', 1)
            title = lines[0].strip().strip('#').strip('"').strip("'").strip()
            if title.startswith("**") and title.endswith("**"):
                title = title[2:-2]
            content = lines[1].strip() if len(lines) > 1 else full_text
            
            if len(content) < 500:
                print(f"  FAILED: Content too short ({len(content)} chars)")
                return None
            
            print(f"  Title: {title}")
            print(f"  Content: {len(content)} chars")
            print(f"  Image: {image_url}")
            
            article = Article(
                title=title,
                content=content,
                summary="",
                category=category,
                tags="bitcoin,crypto,intelligence",
                seo_title=title,
                seo_description=title[:150],
                cover_image_url=image_url,
                source_url="",
                source_type="ai_generated",
                published=True,
                created_at=datetime.utcnow(),
            )
            
            db.session.add(article)
            db.session.commit()
            
            print(f"  SUCCESS: Article ID {article.id}")
            return article.id
            
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return None


def main():
    print("=" * 60)
    print("PROTOCOL PULSE - 10 Article Batch Generation")
    print("Claude (Anthropic) + Hyper-Realistic Header Images")
    print("=" * 60)
    
    results = []
    for i, art in enumerate(ARTICLES):
        article_id = generate_article_with_claude(art["topic"], art["image"], art["category"], i)
        results.append(article_id)
        if article_id and i < len(ARTICLES) - 1:
            time.sleep(1)
    
    print("\n" + "=" * 60)
    print("BATCH GENERATION COMPLETE")
    print(f"  Success: {sum(1 for r in results if r is not None)}/10")
    print(f"  Failed:  {sum(1 for r in results if r is None)}/10")
    print(f"  Article IDs: {[r for r in results if r is not None]}")
    print("=" * 60)


if __name__ == "__main__":
    main()
