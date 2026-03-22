Load ~/protocol_pulse/PIPELINE_LAWS.md first. Fix and blast articles. One focused session.

CONTEXT:
- /api/trigger-automation returns "Another process is running" even with no stuck locks
- SKIP_IF_RAN_WITHIN_MINUTES = 10 in services/automation.py
- The acquire_lock() function at line 233 uses ttl_minutes=SKIP_IF_RAN_WITHIN_MINUTES (10 min)
- This means it blocks if ANY run started within the last 10 minutes, not just running ones
- The blast loop fired 20+ requests in quick succession, saturating the lock window
- The DB currently has all "skipped" runs, no "running" locks
- articles.protocolpulse.io serves a Next.js frontend from ~/protocol_pulse/frontend/ with different nav
- Main Flask app at protocolpulse.io/articles returns 200 and works correctly

STEP 1 - Clear lock state and generate 20 articles:
  cd ~/protocol_pulse
  python3 -c "
  import sys, os, time
  sys.path.insert(0, '/home/ultron/protocol_pulse')
  os.chdir('/home/ultron/protocol_pulse')
  from app import app, db
  import models
  from datetime import datetime
  from services.automation import generate_article_with_tracking

  with app.app_context():
      # Force clear ALL automation_run rows to reset lock state completely
      db.session.execute(db.text('DELETE FROM automation_run'))
      db.session.commit()
      print('Lock table cleared')

      for i in range(20):
          print(f'Generating article {i+1}/20...')
          try:
              result = generate_article_with_tracking(force=True)
              if result.get('success'):
                  print(f'  OK: {result.get("title", "")[:60]}')
              elif result.get('skipped'):
                  print(f'  SKIPPED: {result.get("message")}')
                  # Clear lock again and retry
                  db.session.execute(db.text('DELETE FROM automation_run'))
                  db.session.commit()
              else:
                  print(f'  ERROR: {result.get("error", "unknown")}')
          except Exception as e:
              print(f'  EXCEPTION: {e}')
          time.sleep(3)

      count = db.session.execute(db.text('SELECT COUNT(*) FROM articles')).scalar()
      print(f'Total articles in DB: {count}')
  "

STEP 2 - Verify articles are showing on site:
  curl -s https://protocolpulse.io/articles | grep -c "article-[0-9]"
  Expected: >20

STEP 3 - Fix articles subdomain (this is a Next.js app, NOT Flask):
  ~/protocol_pulse/frontend/ is a Next.js app serving articles.protocolpulse.io
  It has its own nav/header separate from the main site.
  The fix: redirect articles.protocolpulse.io to protocolpulse.io/articles

  Check if cloudflared is running as system service or user:
    systemctl status cloudflared 2>/dev/null | head -5
    pgrep -la cloudflared

  The system cloudflared at /usr/bin/cloudflared uses /etc/cloudflared/config.yml
  The user cloudflared at ~/.local/bin/cloudflared uses ~/.cloudflared/config.yml

  Add a redirect to whichever config is actually routing traffic:
  - Find which config has protocolpulse.io listed
  - Add before the main entry:
      - hostname: articles.protocolpulse.io
        service: http_status:301
        originRequest:
          httpHostHeader: protocolpulse.io
  Actually the correct approach: add articles.protocolpulse.io pointing to localhost:5000 (same as main site)
  since Flask already handles /articles correctly.

  Update the active config file and restart cloudflared.

STEP 4 - Kill the Next.js frontend process if running:
  pgrep -la node | grep next
  If found: kill it (it serves the broken articles subdomain)

STEP 5 - Commit automation.py fix if you change SKIP_IF_RAN_WITHIN_MINUTES:
  Lower it to 1 minute so the cron can fire every 6 hours without lock conflicts
  git add services/automation.py && git commit -m "fix(articles): lower automation lock TTL to 1min, enable rapid generation" && git push

Do NOT touch video pipeline, assembler, or tts_engine.
