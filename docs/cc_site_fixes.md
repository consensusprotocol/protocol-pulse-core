Read PIPELINE_LAWS.md briefly. Then tackle all tasks below surgically.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SITE FIXES — FRIDAY DEMO BLOCKERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK 1 — Charts page real-time metrics broken
  curl http://localhost:5000/api/charts/price-history returns {"error":"upstream unavailable"}
  Find _fetch_btc_price() and _fetch_block_height() and _fetch_mempool_stats() in core/routes.py.
  These are failing because upstream APIs are timing out or returning errors.
  Fix strategy:
    1. Add multiple fallback sources for BTC price: try coinbase, then coingecko, then coindesk
    2. Add fallback for block height: try mempool.space/api/blocks/tip/height
    3. Add fallback for mempool: try mempool.space/api/mempool directly
    4. Increase timeout from default to 8 seconds
    5. Cache successful responses for 60 seconds to avoid hammering APIs
  Also check templates/charts.html — verify JS is fetching /api/charts/* endpoints
  and that those endpoints return the right JSON shape for the charts to render.
  Test: curl http://localhost:5000/api/charts/price-history should return valid JSON with prices array.

TASK 2 — Bad article titles (systemic issue from article generator)
  Problem: Articles have descriptive non-headline titles like:
    "This article delves into the current landscape..."
    "As Bitcoin's network grapples with..."
    "This article explores the latest dynamics..."
  These violate Protocol Pulse editorial standards. Titles must be proper headlines.
  
  Fix 1 (immediate): Find all articles in the DB where title starts with bad patterns
  and rename them using Claude to generate a proper headline from the article content.
  Bad patterns: ['This article', 'This update', 'This report', 'As Bitcoin', 
                 'While Bitcoin', 'Amidst', 'As the volatility', 'A detailed look',
                 'Recent fluctuations', 'An Overview', 'Current Bitcoin Network Landscape',
                 'Examining the Current State']
  
  For each bad-titled article: read first 500 chars of content, generate a punchy
  2-8 word headline (no "Bitcoin" as first word if possible, must be specific not generic).
  Update the DB: UPDATE articles SET title=? WHERE id=?
  
  Fix 2 (systemic): Find the article generator prompt in services/ or core/routes.py.
  Look for the GPT/Claude prompt that generates articles. Add to the title generation instruction:
  "Title must be a specific, punchy headline under 10 words. Never start with 'This article',
  'As Bitcoin', 'While Bitcoin', 'This update', 'Examining', 'An Overview', or similar
  vague descriptive phrases. Example good titles: 'Hashrate Hits All-Time High Despite Price Dip',
  'Lightning Network Capacity Surges Past 5,000 BTC', 'Miners Capitulate as Difficulty Adjusts -8%'"

TASK 3 — Media page book series black screen
  The showSeriesPanel() function exists in templates/media_hub.html (line 235).
  But when user clicks a series card, audio plays with black screen instead of modal.
  
  Diagnosis: Check if there's ALSO an onclick="playEp(...)" or href that fires before showSeriesPanel.
  Check line 185-200 of media_hub.html for conflicting onclick handlers.
  
  The series cards at line 191 have onclick="showSeriesPanel(this)" — correct.
  But there may be an audio element or another handler firing.
  
  Fix: 
    1. Ensure showSeriesPanel() is the ONLY onclick on series book cards
    2. Make sure the seriesModal div (line 198) has proper CSS to display as overlay
    3. Add event.preventDefault() and event.stopPropagation() at start of showSeriesPanel()
    4. Verify the modal has active class CSS showing it (display:flex or display:block)
    5. Test by checking: grep -A5 "sm-overlay" templates/media_hub.html

TASK 4 — Markets/Charts page shows "upstream unavailable" 
  /markets redirects to /charts (correct).
  /charts returns 301 to itself — check for redirect loops.
  The actual /charts template exists. The API endpoints return errors.
  After fixing Task 1 (chart APIs), verify /charts page loads with real data.
  Also verify the template is rendering: check curl http://localhost:5000/charts | head -c 100

AFTER ALL FIXES:
  git add -A
  git commit -m "fix(site): charts real-time APIs, bad article titles, media series modal, markets 404"
  git push
  
  # Reload gunicorn
  kill -1 $(pgrep -f "gunicorn.*5000" | grep -v golds | grep -v relay | head -1) 2>/dev/null
  
  # Test everything
  echo "Charts API:"; curl -s http://localhost:5000/api/charts/price-history | head -c 100
  echo "Charts page:"; curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/charts
  echo "Markets:"; curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/markets
