# DEPLOY ALL CHANGES TO REPLIT — EXECUTE NOW

CRITICAL: Do NOT use planning mode. Start executing IMMEDIATELY.

## CONTEXT

All new code has been built on Ultron and pushed to GitHub (repo: consensusprotocol/protocol-pulse-core). Replit is running the live site at protocolpulse.replit.app but has NOT pulled any of these changes yet. The user sees no updates on the live site.

Replit relay: POST https://protocolpulse.replit.app/api/admin/exec with JSON {"cmd": "..."}
Rate limit: 200 commands/day. BATCH operations.

## TASK 1: Pull Latest Code to Replit

Send via relay (batch into minimal commands):

```bash
# Command 1: Git pull
curl -s -X POST "https://protocolpulse.replit.app/api/admin/exec" \
  -H "Content-Type: application/json" \
  -d '{"cmd": "cd /home/runner/workspace && git stash && git pull origin main 2>&1 | tail -10"}'

# Command 2: Check what files updated
curl -s -X POST "https://protocolpulse.replit.app/api/admin/exec" \
  -H "Content-Type: application/json" \
  -d '{"cmd": "cd /home/runner/workspace && git log --oneline -8"}'
```

## TASK 2: Deploy Media Unified Phase 3

The media_reforge/ directory has the updated files that need to go to templates/ and static/:

```bash
curl -s -X POST "https://protocolpulse.replit.app/api/admin/exec" \
  -H "Content-Type: application/json" \
  -d '{"cmd": "cd /home/runner/workspace && cp media_reforge/templates/media_unified.html templates/media_unified.html && cp media_reforge/static/css/media_unified.css static/css/media_unified.css && cp media_reforge/static/js/media_unified.js static/js/media_unified.js && echo MEDIA_DEPLOYED && wc -l templates/media_unified.html static/css/media_unified.css static/js/media_unified.js"}'
```

## TASK 3: Ensure Routes Are Updated

Check if routes.py serves /media-unified and /media correctly:

```bash
curl -s -X POST "https://protocolpulse.replit.app/api/admin/exec" \
  -H "Content-Type: application/json" \
  -d '{"cmd": "cd /home/runner/workspace && grep -n \"media_unified\\|media-unified\\|media_hub\" routes.py | head -10"}'
```

If /media doesn't serve media_unified.html yet, patch it:
```bash
curl -s -X POST "https://protocolpulse.replit.app/api/admin/exec" \
  -H "Content-Type: application/json" \
  -d '{"cmd": "cd /home/runner/workspace && python3 -c \"r=open('"'"'routes.py'"'"').read(); r=r.replace('"'"'media_hub.html'"'"', '"'"'media_unified.html'"'"') if '"'"'media_hub.html'"'"' in r else r; open('"'"'routes.py'"'"','"'"'w'"'"').write(r); print('"'"'PATCHED'"'"')\""}'
```

## TASK 4: Restart Replit App

```bash
curl -s -X POST "https://protocolpulse.replit.app/api/admin/exec" \
  -H "Content-Type: application/json" \
  -d '{"cmd": "cd /home/runner/workspace && touch main.py && echo RESTARTING"}'
```

## TASK 5: Verify Live Site

```bash
# Check home page
curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/"

# Check media page
curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/media-unified"

# Check articles API
curl -s "https://protocolpulse.replit.app/api/articles/latest" | python3 -c "import json,sys;d=json.load(sys.stdin);print(f'Articles: {len(d) if isinstance(d,list) else \"check format\"}')"

# Check if Mining Intel article published
curl -s "https://protocolpulse.replit.app/api/articles/latest" | python3 -c "
import json,sys
d=json.load(sys.stdin)
if isinstance(d,list):
    for a in d[:5]:
        cat = a.get('category','')
        title = a.get('title','')[:60]
        print(f'[{cat}] {title}')
"
```

## TASK 6: Verify Key Pages Load

Check these routes return 200:
- / (home)
- /articles
- /media-unified (or /media)
- /stage
- /dossier

```bash
for path in / /articles /media-unified /stage /dossier; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app${path}")
    echo "$path → $code"
done
```

## GIT (on Ultron side — push any route fixes)
```bash
cd ~/protocol_pulse && git add -A && git commit -m "ops: deploy to Replit — media phase 3, route fixes" && git push origin main
```

Report: all HTTP status codes, article counts, any errors.

START EXECUTING NOW.

