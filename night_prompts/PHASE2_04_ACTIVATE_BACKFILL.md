# ACTIVATE IMAGE BACKFILL + MINING INTEL + X SPACES — EXECUTE NOW

CRITICAL: Do NOT use planning mode or todolists. Start executing IMMEDIATELY.

## CONTEXT

The previous night runner BUILT these systems. Now we need to TEST and ACTIVATE them.

## TASK 1: Run Image Backfill on Live Database

The script exists: ~/protocol_pulse/scripts/image_backfill_pexels.py

```bash
cd ~/protocol_pulse

# First: check how many articles need images
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
    print(f'Total: {total}, Need images: {no_img}')
"

# Run the backfill
python3 scripts/image_backfill_pexels.py
```

If the above import doesn't work, read the script to understand how it accesses the DB and fix it. The DB is at instance/protocol_pulse.db (SQLite on Ultron copy) or PostgreSQL on Replit.

If it uses Replit relay to update: note the 200/day limit. Batch updates.

After running, report: how many updated, how many failed, sample URLs.

## TASK 2: Test Mining Intel Pipeline

```bash
cd ~/protocol_pulse/mining_intel

# Check the test output from the night run
cat output/test_mining_intel_20260302_195201.json | python3 -m json.tool | head -30

# Run a fresh test
python3 mining_intel_scheduler.py --test --force

# Check output
ls -la output/
cat output/test_mining_intel_*.json | python3 -m json.tool | head -50
```

Verify:
- Article title is punchy and specific
- Body is 400-600 words of original analysis (NOT copied from Blockware)
- Sources are cited
- cover_image_query produces a relevant Pexels search term

If the test looks good, do a REAL publish:
```bash
python3 mining_intel_scheduler.py --force
```

Check if it appeared in the article database.

## TASK 3: Activate X Spaces Scraper

The spaces_scraper was fully built. It needs:

1. Check if the API server runs:
```bash
cd ~/protocol_pulse/spaces_scraper
python3 api_server.py &
sleep 3
curl -s http://localhost:8210/ | python3 -m json.tool
kill %1
```

2. Set up as a persistent tmux service:
```bash
tmux new-session -d -s spaces
tmux send-keys -t spaces 'cd ~/protocol_pulse/spaces_scraper && python3 main.py' Enter
```

3. For Cloudflare tunnel (needs config update — just prepare the config, don't run sudo):
```bash
cat > /tmp/spaces_tunnel.yml << EOF
tunnel: $(grep tunnel /etc/cloudflared/config.yml | head -1 | awk '{print $2}')
credentials-file: /home/ultron/.cloudflared/$(grep credentials /etc/cloudflared/config.yml | awk -F/ '{print $NF}')

ingress:
  - hostname: spaces.protocolpulse.io
    service: http://localhost:8210
  - hostname: avatar.protocolpulse.io
    service: http://localhost:8200
  - hostname: relay.protocolpulse.io
    service: http://localhost:8201
  - service: http_status:404
EOF
echo "Tunnel config ready at /tmp/spaces_tunnel.yml"
echo "To activate: sudo cp /tmp/spaces_tunnel.yml /etc/cloudflared/config.yml && sudo systemctl reload cloudflared"
echo "Also need CNAME: spaces.protocolpulse.io in Cloudflare DNS"
```

## TASK 4: Set Up Cron Jobs for All Automated Systems

```bash
# Show current crontab
crontab -l 2>/dev/null || echo "No crontab"

# Add all scheduled tasks
(crontab -l 2>/dev/null; cat << 'CRON'
# Mining Intel — Twice weekly (Wed + Sun 10 AM EST)
0 10 * * 3,0 cd /home/ultron/protocol_pulse/mining_intel && python3 mining_intel_scheduler.py >> ~/protocol_pulse/logs/mining_intel.log 2>&1

# Oracle Briefing — Daily 7 AM EST
0 7 * * * cd /home/ultron/protocol_pulse/oracle_briefing && python3 briefing_producer.py >> ~/protocol_pulse/logs/oracle_briefing.log 2>&1

# Pulse Check — Daily 9 AM EST
0 9 * * * cd /home/ultron/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py >> ~/protocol_pulse/logs/pulse_check.log 2>&1

# Image Backfill — Weekly Sunday midnight (catch new articles)
0 0 * * 0 cd /home/ultron/protocol_pulse && python3 scripts/image_backfill_pexels.py >> ~/protocol_pulse/logs/image_backfill.log 2>&1
CRON
) | sort -u | crontab -

# Verify
crontab -l
```

## TASK 5: Verify All Services Running

```bash
echo "=== TMUX SESSIONS ==="
tmux ls

echo "=== LISTENING PORTS ==="
ss -tlnp | grep -E "8200|8201|8210"

echo "=== GPU USAGE ==="
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader

echo "=== DISK ==="
df -h / | tail -1

echo "=== CRONTAB ==="
crontab -l

echo "=== RECENT GIT ==="
cd ~/protocol_pulse && git log --oneline -5
```

## GIT
```bash
cd ~/protocol_pulse && git add -A && git commit -m "ops: activate backfill, mining intel, spaces scraper, cron jobs" && git push origin main
```

Report everything: backfill count, mining intel article sample, spaces API response, cron jobs installed, service status.

START EXECUTING NOW.
