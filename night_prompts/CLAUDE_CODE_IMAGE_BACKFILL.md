# CLAUDE CODE PROMPT — ARTICLE IMAGE BACKFILL: PEXELS PHOTO UPGRADE

## MISSION

Replace all placeholder/missing article images in the Protocol Pulse database with high-quality, relevant Pexels stock photos. There are approximately 1,350 articles that need real cover images. This is a batch operation — no UI work, pure database + API grinding.

## CONTEXT

Protocol Pulse auto-generates Bitcoin intelligence articles every 15 minutes. Many older articles have placeholder images or broken URLs in their `cover_image_url` column. A previous session fixed ~1,563 placeholders, but more have accumulated. The rule is: 90% Pexels stock photos, 10% Grok hyper-realistic (for top articles with named people/brands only). This task handles the 90% — Pexels only.

## DATABASE

PostgreSQL on Replit. Access via the Flask app's SQLAlchemy models or direct SQL.

```bash
# Check current state of images
cd ~/protocol_pulse
python3 -c "
from app import create_app, db
from models import Article
app = create_app()
with app.app_context():
    total = Article.query.count()
    no_img = Article.query.filter(
        (Article.cover_image_url == None) | 
        (Article.cover_image_url == '') |
        (Article.cover_image_url.like('%placeholder%')) |
        (Article.cover_image_url.like('%via.placeholder%'))
    ).count()
    has_img = total - no_img
    print(f'Total articles: {total}')
    print(f'Need images: {no_img}')
    print(f'Have images: {has_img}')
"
```

If the above doesn't work (models import path might differ), try:
```bash
# Direct SQL via Replit relay
curl -s "https://protocolpulse.replit.app/api/admin/exec" -X POST \
  -H "Content-Type: application/json" \
  -d '{"cmd": "python3 -c \"import sqlite3; c=sqlite3.connect(\\\"instance/protocol_pulse.db\\\"); print(c.execute(\\\"SELECT COUNT(*) FROM article WHERE cover_image_url IS NULL OR cover_image_url=\\\\\\\"\\\\\\\" OR cover_image_url LIKE \\\\\\\"%placeholder%\\\\\\\"\\\").fetchone())\""}' 
```

Or check if there's a management script:
```bash
find ~/protocol_pulse -name "*.py" | xargs grep -l "backfill\|cover_image\|pexels" 2>/dev/null
```

## PEXELS API

```bash
# Get the Pexels API key
python3 -c "
import os
key = os.environ.get('PEXELS_API_KEY', '')
if not key:
    # Check .env file
    for line in open('.env'):
        if 'PEXELS' in line:
            key = line.split('=',1)[1].strip()
            break
if not key:
    # Check config
    import importlib
    try:
        from config import PEXELS_API_KEY
        key = PEXELS_API_KEY
    except: pass
print(f'Key: {key[:10]}...' if key else 'NOT FOUND — check relay.py get_key()')
"
```

Pexels API: `https://api.pexels.com/v1/search?query=QUERY&per_page=1&orientation=landscape`
Header: `Authorization: YOUR_KEY`
Response: `photos[0].src.large2x` (1880×1000) or `photos[0].src.large` (940×627)

## THE ALGORITHM

For each article without an image:

1. **Extract keywords** from the article title
   - Strip common words (Bitcoin, crypto, analysis, etc. — too generic)
   - Keep specific nouns: "mining", "lightning", "regulation", "El Salvador", "hashrate"
   - If title has a person's name, skip Pexels (those are the 10% Grok candidates — log them separately)
   
2. **Build smart search query**
   - Map Bitcoin-specific terms to visual queries:
     - "mining" → "bitcoin mining facility"
     - "lightning network" → "lightning electricity technology"  
     - "regulation" → "government law gavel"
     - "ETF" → "stock market trading floor"
     - "DeFi" → "blockchain technology abstract"
     - "El Salvador" → "El Salvador city"
     - "inflation" → "money printing currency"
     - "halving" → "bitcoin gold digital"
     - "mempool" → "network data technology"
     - "whale" → "ocean whale" (lol but it works)
   - Fallback: "bitcoin technology digital finance"

3. **Fetch from Pexels** with retry
   - Rate limit: 200 requests/hour — pace at 1 request per 2 seconds
   - Cache results: same query → same image is fine for different articles
   - If no results: try broader query, then use category fallback

4. **Update database**
   - Set `cover_image_url` to the Pexels URL
   - Use Replit relay OR direct DB access (whichever works)
   - Batch updates: commit every 50 articles

5. **Log everything**
   - `logs/image_backfill.log`: article_id, old_url, new_url, query_used, timestamp
   - `logs/image_backfill_grok.log`: articles that need Grok images (people/brands)
   - Progress: print every 50 articles

## BATCH PROCESSING

```python
import time

BATCH_SIZE = 50
RATE_LIMIT_DELAY = 2  # seconds between Pexels calls

articles = get_articles_needing_images()
print(f"Processing {len(articles)} articles...")

for i, article in enumerate(articles):
    query = build_search_query(article.title, article.category)
    image_url = fetch_pexels_image(query)
    
    if image_url:
        update_article_image(article.id, image_url)
    else:
        log_failed(article.id, article.title, query)
    
    if (i + 1) % BATCH_SIZE == 0:
        db.session.commit()
        print(f"Progress: {i+1}/{len(articles)} ({(i+1)*100//len(articles)}%)")
    
    time.sleep(RATE_LIMIT_DELAY)

db.session.commit()
print(f"Done. {success_count} updated, {fail_count} failed, {grok_count} need Grok.")
```

## DB UPDATE METHOD

Try direct SQLAlchemy first. If that doesn't work (Replit DB is remote), use the relay:
```python
# Via Replit relay
import requests
def update_via_relay(article_id, image_url):
    resp = requests.post(
        "https://protocolpulse.replit.app/api/admin/exec",
        json={"cmd": f"python3 -c \"from app import create_app, db; from models import Article; app=create_app(); ctx=app.app_context(); ctx.push(); a=Article.query.get({article_id}); a.cover_image_url='{image_url}'; db.session.commit(); print('OK')\""},
        timeout=15
    )
    return resp.ok
```

**WARNING:** Replit relay has 200 calls/day limit. If using relay, batch SQL updates into single calls that update 20-50 articles at once:
```python
# Batch update via single relay call
ids_and_urls = [(1, 'url1'), (2, 'url2'), ...]
sql = "; ".join([f"UPDATE article SET cover_image_url='{url}' WHERE id={id}" for id, url in ids_and_urls])
```

## VERIFICATION

```bash
# After completion, check the numbers again
python3 -c "
from app import create_app, db
from models import Article
app = create_app()
with app.app_context():
    no_img = Article.query.filter(
        (Article.cover_image_url == None) | 
        (Article.cover_image_url == '') |
        (Article.cover_image_url.like('%placeholder%'))
    ).count()
    pexels = Article.query.filter(Article.cover_image_url.like('%pexels%')).count()
    print(f'Still need images: {no_img}')
    print(f'Pexels images: {pexels}')
"

# Spot check: load a few article pages
curl -s https://protocolpulse.replit.app/articles | grep -c 'pexels.com'
```

## RULES

- Work on `main` branch
- Pace Pexels API calls (2s between requests minimum)
- Don't overwrite existing non-placeholder images
- Log articles with people/brands separately for future Grok processing
- Commit to git: the backfill script itself + logs
- Report: total processed, success count, fail count, Grok candidates count
