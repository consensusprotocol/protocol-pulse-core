Load ~/protocol_pulse/PIPELINE_LAWS.md first. Then execute a full site audit and fix in priority order. Do not touch video pipeline files.

CONTEXT:
- Flask app: ~/protocol_pulse/app.py
- Templates: ~/protocol_pulse/templates/
- DB: ~/protocol_pulse/instance/protocol_pulse.db (57 articles, ALL have cover_image_url=/static/images/default-header.png broken)
- Live site: protocolpulse.io via Cloudflare tunnel
- articles.protocolpulse.io = separate Next.js frontend ~/protocol_pulse/frontend/ (wrong nav/header)
- PEXELS_API_KEY is in .env (check it)

TRACK 1 - ARTICLE IMAGES (do first):
Every article shows /static/images/default-header.png. image_service is failing silently.

Step 1: Read ~/protocol_pulse/services/image_service.py - find why it fails
Step 2: Build a Pexels backfill script:
  - For each article in DB with default-header.png cover:
    * Extract 2-3 keywords from title
    * GET https://api.pexels.com/v1/search?query={keywords}&per_page=5&orientation=landscape
    * Header: Authorization: {PEXELS_API_KEY}
    * Pick best photo (prefer width>1200, landscape)
    * Use photo.src.large2x URL
    * UPDATE articles SET cover_image_url=? WHERE id=?
  - Run it immediately against all 57 articles
  - Special keyword logic:
    * Title contains "saylor/MicroStrategy": query = "michael saylor bitcoin"
    * Title contains "mining/hashrate/miner": query = "bitcoin mining server farm"
    * Title contains "ETF/institutional": query = "bitcoin institutional finance"
    * Title contains "price/market/bull/bear": query = "bitcoin cryptocurrency chart"
    * Title contains "lightning/layer2": query = "lightning network technology"
    * Default: query = first 3 meaningful words from title + " bitcoin"
Step 3: Fix article_automation.py to use Pexels for all NEW articles (replace broken image_service call)
Step 4: Verify: curl http://localhost:5000/articles | grep -c "pexels"

TRACK 2 - ARTICLES SUBDOMAIN:
articles.protocolpulse.io serves wrong site. Fix:
  1. Check: pgrep -la cloudflared
  2. Check which config routes traffic: grep -l "protocolpulse.io" /etc/cloudflared/config.yml ~/.cloudflared/config.yml
  3. Add to active config before main entry:
       - hostname: articles.protocolpulse.io
         service: http://localhost:5000
  4. If /etc/ needs sudo: write the command to ~/protocol_pulse/docs/sudo_needed.txt for PBX to run
  5. If user cloudflared: restart it

TRACK 3 - SITE AUDIT:
Run curl on each route, fix every 500 and broken element:
  routes = ['/', '/articles', '/stage', '/oracle-live', '/media-unified']
  For each: curl -s -o /dev/null -w "%{http_code} %{url_effective}" http://localhost:5000{route}
  
  Known fix needed: Homepage "Daily Pulse Check" section shows "Episodes coming soon"
  Fix: Add Flask route GET /api/latest-episode that reads:
    ~/protocol_pulse/video_pipeline_v3/output/2026-03-20/script.json -> episode_title
    ~/protocol_pulse/video_pipeline_v3/output/2026-03-20/qc_report.json -> duration
    ~/protocol_pulse/static/episode_latest.mp4 -> exists check
  Returns: {title, date, duration_sec, video_url: "/static/episode_latest.mp4"}
  Then update homepage JS to fetch /api/latest-episode and populate the section.

TRACK 4 - ARTICLE QUALITY:
Some articles have subtitle "The Wire — Protocol Pulse editorial column." which is a placeholder.
Find in article_automation.py where subtitle/summary is set, ensure it generates real content.
Also verify cron: crontab -l | grep trigger-automation

RULES:
- Do not touch: assembler.py, tts_engine.py, overnight_render_loop.py, gemini_grade.py, daily_producer.py
- Flask routes, templates, services, DB only
- git add + commit + push after each track
- bash ~/protocol_pulse/regression_test.sh before final commit
