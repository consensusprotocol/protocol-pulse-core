# CLAUDE CODE PROMPT — MINING INTEL: BLOCKWARE INTELLIGENCE ARTICLE ENGINE

## MISSION

Build an automated system that monitors the Blockware Intelligence newsletter (published on Substack), extracts key mining/market data and insights, and generates original Protocol Pulse "Mining Intel" articles that add value beyond the source material. NOT plagiarism — enhanced analysis with Protocol Pulse editorial voice.

## CONTEXT

Blockware Intelligence publishes a weekly Bitcoin mining and market research newsletter on Substack. It contains hashrate data, miner profitability analysis, difficulty adjustments, ASIC pricing, energy costs, and market structure insights. Protocol Pulse should use this as a DATA SOURCE (along with others) to produce original Mining Intel articles that are more accessible, more opinionated, and better visualized than the raw newsletter.

## WHAT TO BUILD

Location: `~/protocol_pulse/mining_intel/`

### 1. `newsletter_monitor.py` — Substack Fetcher

Monitor Blockware's Substack RSS feed for new issues:

```python
BLOCKWARE_RSS = "https://blockwareintelligence.substack.com/feed"

# Check for new posts since last check
# Parse RSS, get latest post URL and publish date
# Download full post content (HTML)
# Extract key data points and text
# Store in local cache: newsletters/YYYY-MM-DD.json
```

Also monitor these additional mining data sources:
- `https://hashrateindex.com` — ASIC pricing, hashprice
- `mempool.space/api` — difficulty, hashrate, block data
- `https://compassmining.io/education` — mining educational content
- `https://braiins.com/blog` — mining pool insights

### 2. `data_extractor.py` — Intelligence Parser

Extract structured data from newsletter content:

```python
{
    "date": "2026-03-01",
    "source": "Blockware Intelligence",
    "metrics": {
        "hashrate": "850 EH/s",
        "difficulty": "next adjustment: +3.2%",
        "hashprice": "$52.40/PH/day",
        "btc_price_at_publish": "$96,500",
        "avg_tx_fee": "12 sat/vB",
        "miner_revenue_daily": "$45.2M",
        "asic_s21_price": "$2,800",
        "energy_cost_avg": "$0.05/kWh"
    },
    "key_insights": [
        "Hashrate hit new ATH despite difficulty increase",
        "Miner selling pressure decreased 15% WoW",
        "New generation ASICs now breakeven at $0.07/kWh"
    ],
    "market_structure": {
        "miner_reserves": "trending down",
        "exchange_flows": "net outflow",
        "otc_desk_activity": "elevated"
    }
}
```

Use Claude API to extract structured data from raw HTML — much more reliable than regex parsing.

### 3. `article_generator.py` — Mining Intel Writer

Generate original Protocol Pulse articles using the extracted data:

```python
MINING_INTEL_PROMPT = """You are writing a "Mining Intel" article for Protocol Pulse — a Bitcoin intelligence platform. 

VOICE: Sharp, analytical, slightly provocative. You're writing for sophisticated Bitcoin investors and miners. No hand-holding, no "what is Bitcoin mining" — your audience knows. 

FORMAT:
- Headline: Punchy, specific, number-driven (e.g., "Hashrate Hits 850 EH/s While Miners Quietly Accumulate")
- Opening: Lead with the most surprising or important data point
- Body: 400-600 words, 3-4 key insights with data backing each one
- Analysis: What this means for miners, hodlers, and the market
- Closing: Forward-looking statement or question

DATA SOURCES (use these, do NOT plagiarize the analysis):
{extracted_data}

Additional market context:
- Current BTC price: {btc_price}
- Fear & Greed Index: {fng}
- Recent Protocol Pulse articles: {recent_articles}

RULES:
- NEVER copy sentences from the source newsletter
- ALWAYS add original analysis beyond what the source provides
- Use specific numbers and data points
- Include at least one insight the source DIDN'T mention
- Reference Protocol Pulse's own data (article count, sentiment, etc.)
- Mention the source: "According to Blockware Intelligence's latest research..."
- Category: "Mining Intel"

Output as JSON:
{{
    "title": "...",
    "subtitle": "...",
    "body_html": "...",
    "category": "Mining Intel",
    "tags": ["mining", "hashrate", ...],
    "cover_image_query": "bitcoin mining facility hardware",
    "sources": ["Blockware Intelligence", "mempool.space", ...]
}}
"""
```

### 4. `publisher.py` — Article Publisher

Publish the generated article to Protocol Pulse:

```python
# Option 1: Direct DB insert (if running on Replit or with DB access)
# Option 2: Via API endpoint if one exists
# Option 3: Via Replit relay

# Check for existing publishing mechanism:
# grep -r "def create_article\|def publish\|Article(" ~/protocol_pulse/app.py ~/protocol_pulse/routes.py
```

The article needs:
- title, subtitle, body (HTML)
- category: "Mining Intel"
- cover_image_url: Pexels photo from the query
- author: "Protocol Pulse Intelligence"
- published_at: current timestamp
- tags: array
- source_attribution: "Data sourced from Blockware Intelligence, mempool.space"

### 5. `mining_intel_scheduler.py` — Orchestrator

```python
def run():
    # 1. Check for new Blockware newsletter
    new_issue = check_for_new_newsletter()
    if not new_issue:
        print("No new newsletter. Checking supplementary sources...")
    
    # 2. Fetch supplementary data regardless
    mempool_data = fetch_mempool_data()
    hashrate_data = fetch_hashrate_data()
    
    # 3. Extract intelligence
    intel = extract_data(new_issue, mempool_data, hashrate_data)
    
    # 4. Generate article
    article = generate_article(intel)
    
    # 5. Fetch cover image from Pexels
    cover_url = fetch_pexels_image(article['cover_image_query'])
    article['cover_image_url'] = cover_url
    
    # 6. Fact-check with Grok (existing fact-check pipeline)
    article = fact_check_with_grok(article)
    
    # 7. Publish
    publish_article(article)
    
    # 8. Log
    log_publication(article)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Generate but do not publish')
    parser.add_argument('--force', action='store_true', help='Generate even without new newsletter')
    args = parser.parse_args()
    run(test=args.test, force=args.force)
```

### Schedule

Run twice per week (matches Blockware's newsletter cadence):
```bash
# Wednesday and Sunday at 10 AM EST
0 10 * * 3,0 cd /home/ultron/protocol_pulse/mining_intel && python3 mining_intel_scheduler.py >> ~/protocol_pulse/logs/mining_intel.log 2>&1
```

Also run a daily "Mining Snapshot" using just mempool.space data on days when there's no newsletter:
```bash
# Daily at 8 AM EST (if no newsletter that day)
0 8 * * * cd /home/ultron/protocol_pulse/mining_intel && python3 mining_intel_scheduler.py --snapshot-only >> ~/protocol_pulse/logs/mining_intel.log 2>&1
```

## FACT-CHECKING INTEGRATION

Protocol Pulse uses Grok for article fact-checking. Find the existing fact-checker:
```bash
find ~/protocol_pulse -name "*.py" | xargs grep -l "grok\|fact.check\|verify" 2>/dev/null
```

Integrate Mining Intel articles into the same fact-check pipeline before publishing.

## ARTICLE PUBLISHING INTEGRATION

Find how existing articles get published:
```bash
# Check the article generation pipeline
find ~/protocol_pulse -name "*.py" | xargs grep -l "Article(\|article_gen\|publish_article\|create_article" 2>/dev/null | head -10
# Check the article model
find ~/protocol_pulse -name "models.py" -exec head -100 {} \;
```

Use the EXACT same publishing mechanism as the existing auto-generated articles.

## TEST RUN

```bash
cd ~/protocol_pulse/mining_intel
python3 mining_intel_scheduler.py --test --force
```

Test mode:
- Fetches real data from all sources
- Generates a real article with Claude
- Does NOT publish to the database
- Saves output to `output/test_mining_intel_YYYYMMDD.json`
- Prints the full article to stdout

## VERIFICATION

1. Article reads naturally — not a copy of Blockware's newsletter
2. Contains specific data points with sources cited
3. Has original analysis beyond what the source provides
4. Cover image is a relevant Pexels photo
5. JSON structure matches what the publisher expects
6. If published in test mode, verify it would display correctly on /articles

## RULES

- Work on `main` branch
- NEVER plagiarize — extract DATA, write ORIGINAL analysis
- Always attribute: "According to Blockware Intelligence..."
- Use Claude API for article generation (claude-sonnet-4-6)
- Use Grok for fact-checking (existing pipeline)
- Pexels for cover images (existing pipeline)
- Git commit + push when done
- Report: sample article output, source data extracted, publishing mechanism used
