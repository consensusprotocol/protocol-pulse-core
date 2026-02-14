# Protocol Pulse — Articles System: Complete Implementation Guide for Cursor

This document contains EVERYTHING needed to implement the Protocol Pulse articles system in your Cursor project, including:

1. Importing the existing 1,370-article backlog from the database export
2. The exact article generation pipeline (prompts, validation, fact-checking)
3. The automated scheduler that generates articles every 15 minutes
4. The articles page UI (dark terminal theme, bento grid, scanlines)
5. Image sourcing with red/black gradient overlay
6. Duplicate detection (3-tier system)

---

## PART 1: DATABASE MODEL — Article Schema

Your Article model MUST have these exact fields. Every article in the backlog uses this schema.

```python
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Full HTML content
    summary = db.Column(db.Text)  # Usually empty — TL;DR is embedded in content
    author = db.Column(db.String(100), default="Protocol Pulse AI")
    category = db.Column(db.String(50), default="Web3")  # Bitcoin, DeFi, Regulation, Privacy, Innovation, Web3
    tags = db.Column(db.String(500))  # Comma-separated tags
    source_url = db.Column(db.String(500))
    source_type = db.Column(db.String(50))  # reddit, ai_generated, manual
    featured = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    seo_title = db.Column(db.String(200))
    seo_description = db.Column(db.String(300))
    substack_url = db.Column(db.String(500))
    header_image_url = db.Column(db.String(500))
    screenshot_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
```

---

## PART 2: IMPORTING THE ARTICLE BACKLOG

The file `articles/all_articles_export.json` on the GitHub repo contains all 1,370 articles. Each article is a JSON object with the fields above.

### Import Script

```python
import json
from datetime import datetime
from app import app, db
from models import Article

def import_articles_from_json(filepath='articles/all_articles_export.json'):
    """Import all articles from the exported JSON file into the database"""
    with open(filepath, 'r') as f:
        articles_data = json.load(f)
    
    imported = 0
    skipped = 0
    
    with app.app_context():
        for item in articles_data:
            # Check if article already exists by title
            existing = Article.query.filter_by(title=item.get('title', '')).first()
            if existing:
                skipped += 1
                continue
            
            article = Article()
            article.title = item.get('title', 'Untitled')
            article.content = item.get('content', '')
            article.summary = item.get('summary', '')
            article.author = item.get('author', 'Protocol Pulse AI')
            article.category = item.get('category', 'Bitcoin')
            article.tags = item.get('tags', '')
            article.source_url = item.get('source_url')
            article.source_type = item.get('source_type', 'ai_generated')
            article.featured = item.get('featured', False)
            article.published = item.get('published', True)
            article.seo_title = item.get('seo_title', item.get('title', ''))
            article.seo_description = item.get('seo_description', '')
            article.header_image_url = item.get('header_image_url')
            
            # Parse date
            created_str = item.get('created_at')
            if created_str:
                try:
                    article.created_at = datetime.fromisoformat(created_str.replace('Z', '+00:00').replace('+00:00', ''))
                except:
                    article.created_at = datetime.utcnow()
            
            db.session.add(article)
            imported += 1
            
            # Commit in batches
            if imported % 100 == 0:
                db.session.commit()
                print(f"Imported {imported} articles...")
        
        db.session.commit()
        print(f"DONE: {imported} imported, {skipped} skipped (already exist)")

if __name__ == '__main__':
    import_articles_from_json()
```

---

## PART 3: THE ARTICLE GENERATION PIPELINE

This is the EXACT system that generated all 1,370 articles. You must replicate it precisely.

### 3A: The Three Prompt Templates

There are 3 content types, each with a different prompt template. All three share the same system prompt (see 3B).

#### PROMPT 1: `news_article` (1200-1800 words)

```
Write an EXCEPTIONALLY HIGH-VALUE intelligence briefing about {topic} for TRANSACTORS (active Bitcoin users who self-custody). Your goal is to create content SO valuable that readers cannot find equivalent analysis anywhere else.

HEADLINE STYLE: {headline_style}

MANDATORY SECTIONS (in order):
1. TL;DR - 3 punchy sentences on why this matters for sovereignty
2. The Report - Factual news with verified metrics (350+ words)
3. Exclusive Data Analysis - On-chain metrics, historical comparisons, UNIQUE insights (300+ words)
4. The Bitcoin Lens - Philosophy + expert perspectives from thought leaders (400+ words)
5. Transactor Intelligence - Specific, actionable advice with concrete steps (250+ words)
6. Sources - At least 5 credible sources

HIGH-VALUE REQUIREMENTS:
- Include ON-CHAIN METRICS not covered by mainstream (UTXO age, realized cap, SOPR, MVRV)
- Reference expert perspectives (Saifedean Ammous, Michael Saylor, Lyn Alden, Parker Lewis)
- Provide SPECIFIC NUMBERS and percentages, not vague claims
- Every section must answer: "What can the reader DO with this information?"
- Connect to historical precedents with specific dates

CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
- Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
- Use <h2 class="article-header"> for main section headers
- Use <h3 class="article-subheader"> for sub-section headers
- Use <p class="article-paragraph"> for all paragraphs
- End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
- NO MARKDOWN SYNTAX - ONLY CLEAN HTML

Target length: 1200-1800 words
```

#### PROMPT 2: `analysis_piece` (1500-2500 words)

```
Write a PREMIUM-TIER expert analysis about {topic} that delivers insights worth $1000+ from paid research services. Target audience: sophisticated Bitcoin holders who want EXCLUSIVE intelligence.

HEADLINE STYLE: {headline_style}

MANDATORY SECTIONS (in order):
1. TL;DR - Executive summary for busy transactors
2. The Report - Comprehensive factual foundation (400+ words)
3. Exclusive Data Analysis - Deep on-chain intelligence with SPECIFIC metrics (400+ words)
4. The Bitcoin Lens - Expert perspectives and philosophical grounding (500+ words)
5. Transactor Intelligence - Actionable strategy with risk/reward analysis (300+ words)
6. Sources - 6+ credible sources including on-chain data providers

EXCLUSIVE VALUE REQUIREMENTS:
- Reference specific on-chain data (Glassnode, CryptoQuant metrics)
- Include contrarian perspectives and counter-arguments
- Connect macro trends to Bitcoin thesis
- Provide the "expert friend" perspective readers don't have access to

CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
- Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
- Use <h2 class="article-header"> for main section headers
- Use <h3 class="article-subheader"> for sub-section headers
- Use <p class="article-paragraph"> for all paragraphs
- End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
- NO MARKDOWN SYNTAX - ONLY CLEAN HTML

Target length: 1500-2500 words
```

#### PROMPT 3: `breaking_news` (800-1000 words)

```
Write an URGENT high-value intelligence briefing about {topic}. Breaking news that transactors need NOW, but still with exclusive analysis they cannot find elsewhere.

HEADLINE STYLE: {headline_style}

MANDATORY SECTIONS:
1. TL;DR - Urgent summary with immediate action items
2. The Report - What happened, verified facts only (300+ words)
3. Exclusive Data Analysis - Rapid on-chain response metrics (200+ words)
4. The Bitcoin Lens - Expert quick-take perspectives (250+ words)
5. Transactor Intelligence - IMMEDIATE actions to take (200+ words)
6. Sources - Credible sources only

CRITICAL FORMATTING - CLEAN HTML ONLY:
- Start with TL;DR: <div class="tldr-section"><em><strong>TL;DR: [summary]</strong></em></div>
- Use <h2 class="article-header"> for section headers
- Use <p class="article-paragraph"> for paragraphs
- End with Sources: <ul class="sources-list"><li>sources</li></ul>

Target length: 800-1000 words
```

### 3B: The System Prompt (Applied to ALL Articles)

This is the Walter Cronkite editorial voice. It wraps around every prompt template:

```
You are a world-class journalist writing for Protocol Pulse with the trust and authority
of Walter Cronkite but in a natural, human style that feels engaging and real.

{metrics_context}

{accuracy_mandate}

{headline_style_mandate}

=== HEADLINE DIRECTIVE FOR THIS ARTICLE ===
{headline_prompt}
THIS IS A MANDATORY REQUIREMENT. Your headline MUST follow this style.

{locked_structure_mandate}

EDITORIAL MANDATE: Write every article like a world-class journalist with the trust and
authority of Walter Cronkite but in a natural, human style that feels engaging and real.
Begin with a clear and factual account of the news, then provide thoughtful context that
connects events to history, economics, and society. Always deliver unique analysis that
uncovers deeper meaning, using data, historical parallels, and quotes from credible sources
to establish authority. Avoid jargon where a simpler, clearer explanation will do.

Every piece must be written through a Bitcoin-first lens: reinforce that Bitcoin is money,
the only truly decentralized currency, and the foundation of freedom, privacy, and sovereignty.
When other crypto projects are mentioned, they should be framed as secondary, never rivaling
Bitcoin's role.

MANDATORY 5-SECTION STRUCTURE:
1. TL;DR (punchy 3-sentence summary)
2. 'The Report' (factual news reporting - 300+ words)
3. 'The Bitcoin Lens' (philosophical analysis - 300+ words)
4. 'Transactor Intelligence' (actionable advice for miners and users - 200+ words)
5. 'Sources' (formatted list of data sources)

This reinforces the separation between unbiased news, philosophical commentary, and actionable intelligence.

CRITICAL: OUTPUT ONLY CLEAN HTML - NO MARKDOWN SYNTAX ALLOWED.
Use <div class="tldr-section"><em><strong>TL;DR: content</strong></em></div> for summaries.
Use <h2 class="article-header"> for all main sections.
Use <h3 class="article-subheader"> for sub-sections within each main section.
Use <p class="article-paragraph"> for all paragraphs.
Never use **, ***, ##, ### or any markdown syntax - only HTML tags.

MINIMUM: 800 words total. Build the full narrative around the ground truth metrics.
```

### 3C: Accuracy Mandate (Injected into System Prompt)

```
=== EDITORIAL ACCURACY MANDATE - ZERO TOLERANCE FOR FABRICATION ===

GROUND TRUTH DATA LOCKDOWN:
- Use real-time Bitcoin metrics from mempool.space API when available
- If real-time data unavailable, DO NOT report specific metrics — focus on qualitative analysis

STRICTLY PROHIBITED - IMMEDIATE REJECTION IF VIOLATED:
- NEVER hallucinate hashrate figures (do not invent numbers)
- NEVER assume difficulty is always increasing - it can DECREASE during miner stress periods
- NEVER fabricate "network strengthening" narratives without verified data
- NEVER use phrases like "surge," "soaring," or "record-breaking" for metrics you cannot verify

TECHNICAL STORYTELLING - EDITORIAL APPROACH:
Write every piece as a peer-to-peer intelligence briefing for "transactors" (active Bitcoin users),
NOT for "tourists" (passive chart-watchers seeking price speculation):
- Transactors care about: network security, difficulty adjustments, hashrate distribution, mining economics, protocol fundamentals
- Tourists care about: price predictions, moon shots, get-rich-quick narratives (AVOID THIS)
- Frame content as actionable intelligence that helps transactors make informed decisions

THE BITCOIN LENS - PHILOSOPHICAL GROUNDING:
Every article must connect technical Bitcoin metrics back to the philosophy of "The Hardest Money":
- Difficulty represents computational security protecting the soundest monetary base layer
- Hashpower demonstrates global commitment to decentralized, censorship-resistant money
- Each difficulty adjustment proves the protocol's self-regulating nature vs fiat's arbitrary manipulation
- Frame all network metrics as evidence of Bitcoin's position as incorruptible, trustless money
```

### 3D: Headline Style System

Each article randomly gets either a QUESTION or STATEMENT headline style. This is critical for variety.

```python
import random

headline_style = random.choice(['question', 'statement'])

headline_instructions = {
    'question': 'HEADLINE FORMAT: Use a QUESTION-STYLE headline that provokes thought. Example: "Is Bitcoin Mining Becoming More Decentralized?" The headline MUST end with a question mark (?).',
    'statement': '''HEADLINE FORMAT: MANDATORY STATEMENT-STYLE HEADLINE - NO QUESTIONS ALLOWED.
DO NOT use a question for the headline. DO NOT end with "?"
Your headline MUST be a declarative statement of fact.

WRONG FORMATS (DO NOT USE):
- "How Does X Impact Y?" ❌
- "Is Bitcoin X?" ❌

CORRECT FORMATS (USE THESE):
- "Bitcoin Network Processes Record 1 Million Daily Transactions" ✓
- "Lightning Network Capacity Surpasses 5,000 BTC Milestone" ✓

Your headline MUST be a factual statement. Start with a noun, NOT with "How", "Why", "Is", "Are", "Will", "Does", or "Can".'''
}
```

### 3E: Post-Generation Headline Enforcement

After the AI generates the article, you MUST verify the headline matches the requested style. If it doesn't, rewrite it with another AI call:

```python
def enforce_headline_style(title, headline_style, topic):
    is_question = title.strip().endswith('?')
    
    if headline_style == 'statement' and is_question:
        # AI gave us a question but we wanted a statement — rewrite it
        rewrite_prompt = f"""Rewrite this headline as a factual STATEMENT, NOT a question.
CURRENT HEADLINE (WRONG): {title}
TOPIC CONTEXT: {topic[:200]}
REQUIREMENTS:
- Must be a declarative statement, NOT a question
- Do NOT end with "?"
- Keep it under 15 words
- Start with a noun
Return ONLY the new headline, nothing else."""
        new_title = openai_generate(rewrite_prompt)  # Use your AI call
        if new_title and not new_title.strip().endswith('?'):
            return new_title.strip().strip('"').strip("'")
    
    elif headline_style == 'question' and not is_question:
        # AI gave us a statement but we wanted a question — rewrite it
        rewrite_prompt = f"""Rewrite this headline as a thought-provoking QUESTION.
CURRENT HEADLINE (WRONG): {title}
TOPIC CONTEXT: {topic[:200]}
REQUIREMENTS:
- Must be a question that ends with "?"
- Start with "Is", "Are", "Will", "Can", "How", "What", or "Why"
Return ONLY the new headline, nothing else."""
        new_title = openai_generate(rewrite_prompt)
        if new_title and new_title.strip().endswith('?'):
            return new_title.strip().strip('"').strip("'")
    
    return title
```

### 3F: Article Structure Validation (with Auto-Retry)

After generation, validate the article has all 6 sections and meets word count. If validation fails, retry up to 2 times:

```python
import re

def validate_article_structure(content):
    errors = []
    
    required_sections = [
        ('tldr-section', 'TL;DR section'),
        ('The Report', 'The Report section'),
        ('Exclusive Data Analysis', 'Exclusive Data Analysis section'),
        ('The Bitcoin Lens', 'The Bitcoin Lens section'),
        ('Transactor Intelligence', 'Transactor Intelligence section'),
        ('Sources', 'Sources section')
    ]
    
    for marker, name in required_sections:
        if marker not in content:
            errors.append(f"Missing {name}")
    
    # Count words (strip HTML tags first)
    clean_text = re.sub(r'<[^>]+>', ' ', content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    word_count = len(clean_text.split())
    
    if word_count < 1200:
        errors.append(f"Only {word_count} words (minimum 1200 required)")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'word_count': word_count
    }
```

**Retry logic:**
```python
content = None
max_retries = 2

for attempt in range(max_retries + 1):
    content = generate_with_ai(formatted_prompt, system_prompt)  # Try OpenAI, fallback Gemini, fallback Anthropic
    
    if not content:
        raise Exception("Failed to generate content with any AI service")
    
    validation = validate_article_structure(content)
    
    if validation['valid']:
        break  # Good article, proceed
    else:
        if attempt < max_retries:
            # Add retry instruction to prompt
            formatted_prompt += f"\n\nPREVIOUS ATTEMPT FAILED VALIDATION: {', '.join(validation['errors'])}. You MUST include all 6 sections and write at least 1200 words."
            content = None  # Reset for retry
```

### 3G: AI Provider Fallback Chain

The system tries AI providers in this order:
1. **OpenAI** (GPT-4o / GPT-5) — primary, best at following structured output
2. **Google Gemini** — fallback if OpenAI fails
3. **Anthropic Claude** — final fallback

```python
content = None

# Try OpenAI first
try:
    content = openai_client.chat.completions.create(
        model="gpt-4o",  # or gpt-5
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_prompt}
        ],
        max_tokens=4000,
        temperature=0.7
    ).choices[0].message.content
except Exception as e:
    print(f"OpenAI failed: {e}")

# Fallback to Gemini
if not content:
    try:
        # Use your Gemini client
        content = gemini_generate(formatted_prompt, system_prompt)
    except Exception as e:
        print(f"Gemini failed: {e}")

# Fallback to Anthropic
if not content:
    try:
        content = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": formatted_prompt}]
        ).content[0].text
    except Exception as e:
        print(f"Anthropic failed: {e}")

if not content:
    raise Exception("All AI providers failed")
```

### 3H: Real-Time Bitcoin Metrics (Ground Truth)

Before generating any article, fetch live metrics from mempool.space:

```python
import requests

def get_network_stats():
    try:
        # Block height and difficulty
        tip = requests.get('https://mempool.space/api/blocks/tip/height', timeout=10).json()
        difficulty = requests.get('https://mempool.space/api/v1/difficulty-adjustment', timeout=10).json()
        hashrate = requests.get('https://mempool.space/api/v1/mining/hashrate/1m', timeout=10).json()
        fees = requests.get('https://mempool.space/api/v1/fees/recommended', timeout=10).json()
        mempool = requests.get('https://mempool.space/api/mempool', timeout=10).json()
        
        return {
            'height': tip,
            'difficulty_progress': f"{difficulty.get('progressPercent', 0):.1f}%",
            'remaining_blocks': difficulty.get('remainingBlocks'),
            'hashrate': hashrate.get('currentHashrate'),
            'fees': fees,
            'mempool_size': mempool.get('count'),
            'status': 'operational'
        }
    except Exception as e:
        return None

# Build context string for AI
network_stats = get_network_stats()
if network_stats:
    metrics_context = f"""
VERIFIED REAL-TIME BITCOIN NETWORK DATA (as of {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}):
- Current Block Height: {network_stats.get('height', 'Unknown')}
- Current Hashrate: {network_stats.get('hashrate', 'Unknown')}
- Network Status: {network_stats.get('status', 'Unknown')}
- Difficulty Adjustment Progress: {network_stats.get('difficulty_progress', 'Unknown')}
- Blocks Until Adjustment: {network_stats.get('remaining_blocks', 'Unknown')}

YOU MUST USE THESE VERIFIED METRICS. Do not invent different numbers.
"""
else:
    metrics_context = """
WARNING: Real-time network data unavailable.
DO NOT report specific Bitcoin metrics in this article.
Focus on qualitative analysis only. No fabricated numbers allowed.
"""
```

---

## PART 4: DUPLICATE DETECTION (3-Tier System)

This is CRITICAL. Without this, you'll generate the same article over and over.

### Tier 1: Core Topic Category Matching (Fastest)

```python
CORE_TOPICS = {
    'mining_difficulty': ['mining', 'difficulty', 'hash', 'hashrate'],
    'lightning_network': ['lightning', 'network', 'payment', 'volume'],
    'defi_tvl': ['defi', 'tvl', 'locked', 'value'],
    'etf_inflows': ['etf', 'inflow', 'inflows', 'demand'],
    'institutional': ['institutional', 'treasury', 'billion'],
    'strategic_reserve': ['reserve', 'reserves', 'strategic', 'nation', 'sovereign'],
    'regulation': ['regulation', 'regulatory', 'sec', 'cftc', 'law', 'bill'],
    'price_milestone': ['price', 'milestone', 'ath', 'high', 'record'],
    'adoption': ['adoption', 'accept', 'acceptance', 'mainstream'],
    'halving': ['halving', 'halvening', 'block', 'reward', 'subsidy'],
}

def get_core_topic(text):
    text_lower = text.lower()
    words = set(re.findall(r'\b[a-zA-Z]{3,}\b', text_lower))
    for topic_id, keywords in CORE_TOPICS.items():
        matches = sum(1 for kw in keywords if kw in words)
        if matches >= 2:
            return topic_id
    return None
```

### Tier 2: Keyword Jaccard Similarity

```python
def get_topic_keywords(text):
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'bitcoin', 'btc', 'crypto', 'market', 'surge', 'record', 'high', 'new'}
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return set(word for word in words if word not in stop_words)

def check_keyword_similarity(new_topic, existing_title, threshold=0.35):
    new_kw = get_topic_keywords(new_topic)
    existing_kw = get_topic_keywords(existing_title)
    if not new_kw or not existing_kw:
        return False
    intersection = len(new_kw & existing_kw)
    union = len(new_kw | existing_kw)
    similarity = intersection / union if union > 0 else 0
    return similarity >= threshold
```

### Tier 3: AI Semantic Duplicate Check (via Gemini)

```python
def is_semantic_duplicate(new_headline, recent_headlines):
    if not recent_headlines:
        return False
    
    headlines_list = "\n".join([f"- {h}" for h in recent_headlines[:10]])
    prompt = f"""You are a senior news editor. Your job is to prevent duplicate coverage.

NEW HEADLINE TO CHECK: "{new_headline}"

EXISTING HEADLINES FROM LAST 48 HOURS:
{headlines_list}

Are any existing headlines covering the EXACT SAME news event as the new headline?
Focus on the CORE EVENT, not wording.
Reply with ONLY one word: "DUPLICATE" or "UNIQUE" """

    response = gemini_generate(prompt)
    if response and "DUPLICATE" in response.strip().upper():
        return True
    return False
```

### Combined Check (Run All 3 Tiers)

```python
def is_topic_similar_to_recent(topic, hours=48):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    recent_articles = Article.query.filter(
        Article.created_at >= cutoff,
        Article.published == True
    ).all()
    
    if not recent_articles:
        return False
    
    # TIER 1: Core topic matching
    new_core = get_core_topic(topic)
    if new_core:
        for article in recent_articles:
            if get_core_topic(article.title) == new_core:
                return True
    
    # TIER 2: Keyword similarity
    for article in recent_articles:
        if check_keyword_similarity(topic, article.title):
            return True
    
    # TIER 3: AI semantic check
    recent_headlines = [a.title for a in recent_articles[:5]]
    if is_semantic_duplicate(topic, recent_headlines):
        return True
    
    return False
```

---

## PART 5: TOPIC POOL AND SELECTION

The scheduler picks topics from this pool. It shuffles them and checks each against duplicates:

```python
TOPICS = [
    "Bitcoin mining difficulty reaches new all-time high as hash rate surges",
    "Major institutional investors allocate billions to Bitcoin treasury reserves",
    "Lightning Network payment volume breaks monthly records",
    "DeFi protocols implement revolutionary new yield farming mechanisms",
    "Central banks accelerate CBDC development in response to Bitcoin adoption",
    "Major corporations announce Bitcoin payment integration plans",
    "Renewable energy Bitcoin mining initiatives expand globally",
    "DeFi total value locked reaches new milestone despite market volatility",
    "Bitcoin ETF inflows surge as retail and institutional demand grows",
    "Layer 2 scaling solutions see unprecedented adoption rates",
    "Bitcoin node count reaches new highs as decentralization strengthens",
    "Nostr protocol adoption grows as censorship-resistant social media expands",
    "Bitcoin self-custody solutions see record downloads amid banking concerns",
    "Hardware wallet manufacturers report surge in demand",
    "Bitcoin development activity increases with new BIP proposals",
    "Stablecoin regulations face scrutiny as Bitcoin alternative gains attention",
    "Bitcoin ordinals and inscriptions drive on-chain activity surge",
    "Countries explore strategic Bitcoin reserve policies",
    "Bitcoin privacy improvements proposed in new protocol upgrades",
    "Cross-border Bitcoin payments reduce remittance costs globally"
]

def get_unique_topic(max_attempts=10):
    available = TOPICS.copy()
    random.shuffle(available)
    
    for topic in available[:max_attempts]:
        if not is_topic_similar_to_recent(topic):
            return topic
    
    # All predefined topics similar — generate dynamic ones
    dynamic_topics = [
        f"Bitcoin adoption trends and market analysis for {datetime.utcnow().strftime('%B %Y')}",
        f"Weekly Bitcoin network statistics show evolving usage patterns",
        f"Bitcoin's role in the evolving global monetary landscape",
        f"Technical analysis of Bitcoin's current market cycle position",
        f"Bitcoin mining industry developments and energy usage trends"
    ]
    
    for topic in dynamic_topics:
        if not is_topic_similar_to_recent(topic):
            return topic
    
    return None  # All topics exhausted
```

---

## PART 6: THE AUTOMATED SCHEDULER

This is the part Cursor keeps getting wrong. Here is EXACTLY how it works:

### Core Automation Function

```python
def generate_article_with_tracking():
    """This is the function the scheduler calls every 15 minutes"""
    with app.app_context():
        # Step 1: Acquire lock (prevent duplicate runs)
        run = acquire_lock()
        if not run:
            return {'skipped': True}
        
        try:
            generator = ContentGenerator()  # This class has all 3 prompts + system prompt
            
            # Step 2: Get a unique topic (runs 3-tier duplicate check)
            topic = get_unique_topic()
            if not topic:
                release_lock(run, 'skipped', 'No unique topics available')
                return {'skipped': True}
            
            # Step 3: Generate the article (uses prompt template + system prompt + metrics)
            article_data = generator.generate_article(
                topic=topic,
                content_type='breaking_news',  # Default type for automated articles
                source_type='ai_generated'
            )
            
            # Step 4: Save to database
            if article_data:
                article = Article()
                article.title = article_data['title']
                article.content = article_data['content']
                article.summary = ""
                article.category = article_data.get('category', 'Bitcoin')
                article.tags = article_data.get('tags', 'bitcoin,breaking,news')
                article.author = "Al Ingle"
                article.seo_title = article_data.get('seo_title', article_data['title'])
                article.seo_description = article_data.get('seo_description', '')
                article.published = True
                article.featured = True
                db.session.add(article)
                db.session.commit()
                
                release_lock(run, 'success')
                return {'success': True, 'article_id': article.id, 'title': article.title}
            else:
                release_lock(run, 'failed', 'No article data generated')
                return {'success': False}
                
        except Exception as e:
            release_lock(run, 'failed', e)
            return {'success': False, 'error': str(e)}
```

### Scheduler Setup (APScheduler)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BackgroundScheduler()

def run_automation():
    """Wrapper that the scheduler calls"""
    try:
        with app.app_context():
            from models import Article
            Article.query.first()  # Verify DB accessible
            
            result = generate_article_with_tracking()
            if result.get('success'):
                print(f"Article #{result.get('article_id')} - {result.get('title', '')[:50]}...")
            elif result.get('skipped'):
                print("Skipped: Another process running or no unique topics")
            else:
                print(f"Failed: {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"Automation error: {e}")

# Schedule article generation every 15 minutes
scheduler.add_job(
    func=run_automation,
    trigger=IntervalTrigger(minutes=15),
    id='article_automation',
    name='Generate article every 15 minutes',
    replace_existing=True,
    max_instances=1  # CRITICAL: prevents overlapping runs
)

scheduler.start()

# Trigger first run immediately on startup
scheduler.add_job(
    func=run_automation,
    id='initial_run',
    name='Initial article generation',
    replace_existing=True
)
```

### Execution Locking (Prevents Duplicate Runs)

You MUST implement locking. Without it, multiple scheduler threads will generate duplicate articles.

```python
# You need an AutomationRun model:
class AutomationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), default='article_generation')
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='running')  # running, success, failed, skipped
    error = db.Column(db.Text)

def acquire_lock(task_name='article_generation', ttl_minutes=10):
    # Clean up stale locks (older than 30 minutes)
    stale_threshold = datetime.utcnow() - timedelta(minutes=30)
    AutomationRun.query.filter(
        AutomationRun.status == 'running',
        AutomationRun.started_at < stale_threshold,
        AutomationRun.finished_at == None
    ).update({'status': 'failed', 'error': 'Stale lock', 'finished_at': datetime.utcnow()})
    db.session.commit()
    
    # Check for active locks
    cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
    active = AutomationRun.query.filter(
        AutomationRun.task_name == task_name,
        AutomationRun.started_at >= cutoff,
        AutomationRun.finished_at == None
    ).first()
    
    if active:
        return None  # Lock held
    
    # Create new lock
    run = AutomationRun(task_name=task_name, started_at=datetime.utcnow(), status='running')
    db.session.add(run)
    db.session.commit()
    return run

def release_lock(run, status='success', error=None):
    run.finished_at = datetime.utcnow()
    run.status = status
    if error:
        run.error = str(error)[:500]
    db.session.commit()
```

---

## PART 7: ARTICLES PAGE UI

### Route

```python
@app.route('/articles')
def articles():
    now = datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)
    cutoff_48h = now - timedelta(hours=48)
    
    today_articles = Article.query.filter(
        Article.published == True,
        Article.created_at >= cutoff_24h
    ).order_by(Article.created_at.desc()).all()
    
    yesterday_articles = Article.query.filter(
        Article.published == True,
        Article.created_at >= cutoff_48h,
        Article.created_at < cutoff_24h
    ).order_by(Article.created_at.desc()).all()
    
    # FALLBACK: If no recent articles, show most recent ones in the layout
    if not today_articles and not yesterday_articles:
        all_recent = Article.query.filter(
            Article.published == True
        ).order_by(Article.created_at.desc()).limit(50).all()
        
        today_articles = all_recent[:10]
        yesterday_articles = all_recent[10:20]
        archive_articles = all_recent[20:]
    else:
        archive_articles = Article.query.filter(
            Article.published == True,
            Article.created_at < cutoff_48h
        ).order_by(Article.created_at.desc()).limit(20).all()
    
    for article in today_articles:
        time_diff = (now - article.created_at).total_seconds() / 3600
        article.is_pressing = time_diff < 1
    
    return render_template('articles.html',
        today_articles=today_articles,
        yesterday_articles=yesterday_articles,
        archive_articles=archive_articles,
        last_updated=now)
```

### Template Filter (clean_preview)

This extracts readable preview text from the HTML article content:

```python
@app.template_filter('clean_preview')
def clean_preview_filter(content, max_length=150):
    if not content:
        return ""
    
    # First try to extract TL;DR content
    import re
    tldr_match = re.search(r'<div class="tldr-section">.*?<strong>TL;DR:\s*(.*?)</strong>', content, re.DOTALL | re.IGNORECASE)
    if tldr_match:
        tldr_text = tldr_match.group(1)
        # Strip remaining HTML from TL;DR
        tldr_text = re.sub(r'<[^>]+>', '', tldr_text).strip()
        if len(tldr_text) > max_length:
            return tldr_text[:max_length].rsplit(' ', 1)[0] + '...'
        return tldr_text
    
    # Fallback: strip all HTML and take first N chars
    clean = re.sub(r'<[^>]+>', ' ', content)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if len(clean) > max_length:
        return clean[:max_length].rsplit(' ', 1)[0] + '...'
    return clean
```

### The Full Template

The complete `templates/articles.html` file is already synced to the GitHub repo. Pull it from there. It uses:

- **Fonts**: Crimson Pro (headlines), DM Sans (body), JetBrains Mono (data/timestamps)
- **Colors**: `--dark-bg: #050505`, `--accent-red: #dc2626`, `--btc-gold: #f7931a`
- **Layout**: CSS Grid bento layout (4 columns, hero card spans 2x2)
- **Effects**: Scanline animation, red glow borders on hover, pulse dot on "Live Feed"
- **Sections**: "The 24-Hour Pulse" (bento grid) → "The Morning After" (list) → "The Vault" (archive behind button)

---

## PART 8: HEADER IMAGE SOURCING + RED/BLACK GRADIENT OVERLAY

### Image Sourcing (Backend)

For each generated article, attempt to find a relevant header image:

```python
import requests
from bs4 import BeautifulSoup

ALLOWED_IMAGE_DOMAINS = [
    'coindesk.com', 'cointelegraph.com', 'theblock.co', 'bitcoinmagazine.com',
    'cryptoslate.com', 'decrypt.co', 'bloomberg.com', 'cnbc.com', 'reuters.com',
    'ft.com', 'forbes.com', 'yahoo.com', 'blockworks.co', 'coinmarketcap.com',
    'messari.io', 'wsj.com', 'nytimes.com', 'bbc.com', 'theguardian.com',
    'fortune.com', 'businessinsider.com', 'investopedia.com', 'nasdaq.com',
    'seekingalpha.com', 'zerohedge.com', 'dlnews.com', 'protos.com',
    'thestreet.com', 'ambcrypto.com', 'fxstreet.com', 'investing.com',
    'benzinga.com', 'pymnts.com', 'axios.com', 'beincrypto.com',
    'u.today', 'coingape.com', 'bankless.com', 'ledgerinsights.com',
    'cryptobriefing.com', 'crypto.news', 'cryptopotato.com', 'newsBTC.com',
    'bitcoin.com', 'bitcoinist.com', 'coinbureau.com', 'chainwire.org',
    'thecryptotimes.com', 'thedefiant.io', 'coininsider.com'
]

def pick_header_image(article):
    """Find a relevant, high-quality header image for the article"""
    # 1) If source_url exists, try OG image from that page
    if article.source_url:
        og_image = extract_og_image(article.source_url)
        if og_image and is_valid_image(og_image):
            return og_image
    
    # 2) Fallback: deterministic local pool
    return get_deterministic_local_header(article.title)

def extract_og_image(url):
    """Extract OpenGraph image from a URL"""
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Try og:image first
        og = soup.find('meta', property='og:image')
        if og and og.get('content'):
            return og['content']
        
        # Fallback to twitter:image
        tw = soup.find('meta', attrs={'name': 'twitter:image'})
        if tw and tw.get('content'):
            return tw['content']
    except:
        pass
    return None

def is_valid_image(url):
    """Validate the image URL is usable"""
    if not url or not url.startswith('http'):
        return False
    # Reject tiny icons/logos/favicons
    blocklist = ['logo', 'sprite', 'avatar', 'icon', 'favicon', '1x1', 'pixel']
    url_lower = url.lower()
    return not any(bad in url_lower for bad in blocklist)

def get_deterministic_local_header(seed):
    """Pick a consistent local header image based on article title hash"""
    import hashlib
    # You should have 10-20 generic Bitcoin/crypto header images in /static/images/headers/
    headers = [f'/static/images/headers/header_{i}.jpg' for i in range(1, 11)]
    index = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(headers)
    return headers[index]
```

### Red/Black Gradient Overlay (CSS)

This overlay goes on top of every header image in the article cards:

```css
.card-image {
    position: relative;
    overflow: hidden;
    border-radius: 8px;
    height: 180px;
    background: #0a0a0a;
}

.card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    filter: saturate(1.05) contrast(1.05);
}

/* Red/black Protocol Pulse overlay */
.card-image::after {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
        linear-gradient(135deg, rgba(220,38,38,0.28) 0%, rgba(0,0,0,0) 60%),
        linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.3) 40%, transparent 70%),
        radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.4) 100%);
    mix-blend-mode: multiply;
}
```

---

## PART 9: COMPLETE GENERATION FLOW (Step by Step)

Here is the EXACT sequence of events when the scheduler fires every 15 minutes:

```
1. Scheduler fires → calls run_automation()
2. run_automation() → calls generate_article_with_tracking()
3. acquire_lock() → checks if another generation is running (prevents duplicates)
4. get_unique_topic() → shuffles TOPICS list, runs 3-tier duplicate check on each:
   a. Core topic category check (keyword buckets)
   b. Jaccard similarity check (keyword overlap > 0.35)
   c. Gemini AI semantic check ("is this the same story?")
5. If topic found → ContentGenerator().generate_article(topic, content_type='breaking_news')
6. generate_article() does:
   a. Random headline style selection (question vs statement)
   b. AI Gatekeeper duplicate check via Gemini (compares topic to last 10 headlines)
   c. Fetch real-time Bitcoin metrics from mempool.space
   d. Build system prompt (Cronkite voice + accuracy mandate + structure mandate + metrics)
   e. Format prompt template with topic + headline instructions
   f. Generate content: OpenAI → Gemini fallback → Anthropic fallback
   g. Validate 6-section structure + 1200 word minimum
   h. If validation fails → retry up to 2 times with error feedback in prompt
   i. Extract or generate SEO title
   j. Clean title (strip markdown, HTML tags, "Protocol Pulse:" prefix)
   k. Enforce headline style (rewrite via AI if wrong style)
   l. Run fact-checker verification
   m. Generate tags and determine category
7. Save Article to database (published=True, featured=True, author="Al Ingle")
8. release_lock() → mark run as success
9. Wait 15 minutes → repeat
```

---

## PART 10: FILES TO PULL FROM GITHUB

All these files are synced to `github.com/consensusprotocol/protocol-pulse-core`:

| File | Purpose |
|------|---------|
| `templates/articles.html` | Full articles page UI with CSS |
| `templates/article_detail.html` | Individual article view |
| `services/content_generator.py` | Complete generation pipeline (879 lines) |
| `services/automation.py` | Scheduler automation + duplicate detection |
| `main.py` | Scheduler setup (APScheduler jobs) |
| `routes.py` | Article routes + clean_preview filter |
| `models.py` | Article model + AutomationRun model |
| `articles/all_articles_export.json` | All 1,370 articles as JSON |

---

## CRITICAL NOTES FOR CURSOR

1. **DO NOT skip the duplicate detection.** Without the 3-tier system, the scheduler will generate the same "Bitcoin mining difficulty" article 50 times.

2. **DO NOT skip the structure validation.** Without it, AI will sometimes return articles missing sections or under word count. The retry logic catches this.

3. **DO NOT skip headline enforcement.** AI models frequently ignore headline style instructions. The post-generation check + rewrite is essential for variety.

4. **The scheduler MUST use `max_instances=1`.** This prevents overlapping runs when one generation takes longer than 15 minutes.

5. **The execution lock is NOT optional.** With Gunicorn multi-worker, without locking you'll get 2-4 articles generated simultaneously from the same trigger.

6. **The content MUST be clean HTML, not markdown.** The templates render raw HTML. If the AI returns markdown, it will display as literal `**bold**` text instead of **bold** text.

7. **Always fetch real-time metrics BEFORE generating.** This prevents the AI from hallucinating fake Bitcoin stats.
