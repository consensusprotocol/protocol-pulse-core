# CLAUDE CODE PROMPT — ACTIVATE ALL SYSTEMS: TEST, SCHEDULE, DEPLOY

## MISSION

Everything has been built. Now ACTIVATE it all. Run the image backfill, verify mining intel, set up cron schedules, and deploy frontend changes to Replit.

## TASK 1: RUN IMAGE BACKFILL (Pexels photos for articles)

The script `~/protocol_pulse/scripts/image_backfill_pexels.py` (385 lines) was built but never run.

```bash
# First, understand how it works:
head -50 ~/protocol_pulse/scripts/image_backfill_pexels.py
grep -n "def main\|def run\|if __name__" ~/protocol_pulse/scripts/image_backfill_pexels.py

# Check how many articles need images:
python3 -c "
import sqlite3
db = sqlite3.connect('instance/protocol_pulse.db')
total = db.execute('SELECT COUNT(*) FROM article').fetchone()[0]
no_img = db.execute(\"SELECT COUNT(*) FROM article WHERE cover_image_url IS NULL OR cover_image_url='' OR cover_image_url LIKE '%placeholder%'\").fetchone()[0]
pexels = db.execute(\"SELECT COUNT(*) FROM article WHERE cover_image_url LIKE '%pexels%'\").fetchone()[0]
print(f'Total: {total}, Need images: {no_img}, Already Pexels: {pexels}')
"

# Check Pexels API key:
grep PEXELS ~/protocol_pulse/.env 2>/dev/null
python3 -c "from scripts.image_backfill_pexels import *; print('Script imports OK')" 2>&1

# DRY RUN first (if supported):
python3 scripts/image_backfill_pexels.py --dry-run 2>/dev/null || echo "No dry-run flag"

# FULL RUN:
cd ~/protocol_pulse && python3 scripts/image_backfill_pexels.py 2>&1 | tee logs/image_backfill_run.log
```

After running, verify:
```bash
python3 -c "
import sqlite3
db = sqlite3.connect('instance/protocol_pulse.db')
pexels = db.execute(\"SELECT COUNT(*) FROM article WHERE cover_image_url LIKE '%pexels%'\").fetchone()[0]
no_img = db.execute(\"SELECT COUNT(*) FROM article WHERE cover_image_url IS NULL OR cover_image_url='' OR cover_image_url LIKE '%placeholder%'\").fetchone()[0]
print(f'Pexels images: {pexels}, Still need: {no_img}')
"
```

**NOTE:** Pexels API rate limit is 200 req/hour. If we have 1300+ articles, the script should pace at 1 req/2s and may take ~45 minutes. Let it run — don't interrupt.

## TASK 2: VERIFY MINING INTEL

Mining Intel was built and already has a test output. Verify it's publishable:

```bash
# Check test output:
cat ~/protocol_pulse/mining_intel/output/test_mining_intel_20260302_195201.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'Title: {d[\"title\"]}')
print(f'Category: {d[\"category\"]}')
print(f'Body length: {len(d[\"body_html\"])} chars')
print(f'Tags: {d.get(\"tags\",[])}')
"

# Run a fresh test to confirm it still works:
cd ~/protocol_pulse/mining_intel
python3 mining_intel_scheduler.py --test 2>&1 | tee ~/protocol_pulse/logs/mining_intel_test.log

# If test passes, do a REAL publish:
# python3 mining_intel_scheduler.py --force 2>&1 | tee ~/protocol_pulse/logs/mining_intel_publish.log
# Only publish if test succeeded
```

## TASK 3: VERIFY SPACES SCRAPER

The spaces scraper was built in a prior session (2,007 lines). Check if it runs:

```bash
# Check what it needs:
cat ~/protocol_pulse/spaces_scraper/requirements.txt
head -30 ~/protocol_pulse/spaces_scraper/main.py
grep -n "def main\|if __name__" ~/protocol_pulse/spaces_scraper/main.py

# Install dependencies:
pip install -r ~/protocol_pulse/spaces_scraper/requirements.txt --break-system-packages 2>/dev/null

# Test run:
cd ~/protocol_pulse/spaces_scraper
python3 main.py --test 2>&1 | head -50
```

## TASK 4: SET UP CRON SCHEDULES

Create a master crontab for all automated systems:

```bash
# View current crontab:
crontab -l 2>/dev/null || echo "No crontab"

# Set up the full schedule:
cat > /tmp/pp_crontab << 'CRON'
# Protocol Pulse — Automated Pipelines
# Updated: $(date)

# Mining Intel — Twice weekly (Wed + Sun at 10 AM EST)
0 10 * * 3,0 cd /home/ultron/protocol_pulse/mining_intel && python3 mining_intel_scheduler.py >> /home/ultron/protocol_pulse/logs/mining_intel.log 2>&1

# Image Backfill — Weekly check for new articles needing images (Monday 3 AM)
0 3 * * 1 cd /home/ultron/protocol_pulse && python3 scripts/image_backfill_pexels.py >> /home/ultron/protocol_pulse/logs/image_backfill.log 2>&1

# Spaces Scraper — Check for live spaces every 15 minutes
*/15 * * * * cd /home/ultron/protocol_pulse/spaces_scraper && python3 main.py --check >> /home/ultron/protocol_pulse/logs/spaces_scraper.log 2>&1

# Oracle Briefing — Daily at 7 AM EST (after pipeline is built)
# 0 7 * * * cd /home/ultron/protocol_pulse/oracle_briefing && python3 briefing_producer.py >> /home/ultron/protocol_pulse/logs/oracle_briefing.log 2>&1

# Pulse Check V4 — Daily at 8 AM EST (after pipeline is built)
# 0 8 * * * cd /home/ultron/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py >> /home/ultron/protocol_pulse/logs/pulse_check.log 2>&1

# Log rotation — Weekly
0 0 * * 0 find /home/ultron/protocol_pulse/logs -name "*.log" -size +50M -exec truncate -s 0 {} \;
CRON

# Install the crontab:
crontab /tmp/pp_crontab
crontab -l
echo "Crontab installed"
```

## TASK 5: DEPLOY TO REPLIT

Push latest code to Replit so the live site reflects all changes:

```bash
# First, make sure GitHub is up to date:
cd ~/protocol_pulse
git add -A && git commit -m "feat: activate all systems — backfill, mining intel, cron" && git push origin main

# Then deploy to Replit via relay:
# The Replit app pulls from GitHub
curl -s --max-time 30 "https://protocolpulse.replit.app/api/admin/exec" \
  -X POST -H "Content-Type: application/json" \
  -d '{"cmd":"cd /home/runner/workspace && git pull origin main 2>&1 | tail -5 && touch main.py && echo DEPLOYED"}'

# If relay doesn't work, deploy specific files:
for f in templates/media_unified.html static/css/media_unified.css static/js/media_unified.js; do
  curl -s --max-time 15 "https://protocolpulse.replit.app/api/admin/exec" \
    -X POST -H "Content-Type: application/json" \
    -d "{\"cmd\":\"cd /home/runner/workspace && curl -sL https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/media_reforge/$f -o $f && echo OK $f\"}"
done

# Restart Replit app:
curl -s --max-time 15 "https://protocolpulse.replit.app/api/admin/exec" \
  -X POST -H "Content-Type: application/json" \
  -d '{"cmd":"touch main.py && echo RESTARTED"}'
```

## TASK 6: VERIFY LIVE SITE

```bash
# Check key pages:
curl -s -o /dev/null -w "%{http_code}" https://protocolpulse.replit.app/
curl -s -o /dev/null -w "%{http_code}" https://protocolpulse.replit.app/media-unified
curl -s -o /dev/null -w "%{http_code}" https://protocolpulse.replit.app/articles
curl -s -o /dev/null -w "%{http_code}" https://protocolpulse.replit.app/stage

# Check that articles have images:
curl -s https://protocolpulse.replit.app/api/articles/latest | python3 -c "
import json,sys
articles = json.load(sys.stdin)
if isinstance(articles, list):
    for a in articles[:5]:
        img = a.get('cover_image_url','NONE')[:50]
        print(f'{a.get(\"title\",\"?\")[:40]} | img: {img}')
"
```

## VERIFICATION SUMMARY

Run this at the end:
```bash
echo "=== ACTIVATION REPORT ==="
echo ""
echo "1. Image Backfill:"
python3 -c "
import sqlite3
db=sqlite3.connect('instance/protocol_pulse.db')
p=db.execute(\"SELECT COUNT(*) FROM article WHERE cover_image_url LIKE '%pexels%'\").fetchone()[0]
n=db.execute(\"SELECT COUNT(*) FROM article WHERE cover_image_url IS NULL OR cover_image_url=''\").fetchone()[0]
print(f'   Pexels: {p} | Still need: {n}')
"
echo ""
echo "2. Mining Intel:"
ls -la ~/protocol_pulse/mining_intel/output/ 2>/dev/null | tail -3
echo ""
echo "3. Crontab:"
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" | wc -l
echo "   active cron jobs"
echo ""
echo "4. Git:"
cd ~/protocol_pulse && git log --oneline -3
echo ""
echo "5. Services:"
curl -s http://localhost:8200/health 2>/dev/null && echo " | Avatar OK" || echo "   Avatar DOWN"
echo ""
echo "=== END REPORT ==="
```

## RULES
- Work on `main` branch
- Let image backfill run to completion (may take 30-45 min due to rate limiting)
- Don't break existing services
- Git commit + push after each major task
- Report: backfill stats, mining intel test result, cron jobs installed, deploy status
