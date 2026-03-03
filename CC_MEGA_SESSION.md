# ═══════════════════════════════════════════════════════════════
# PROTOCOL PULSE — MASTER BUILD SESSION (10-HOUR AUTONOMOUS)
# ═══════════════════════════════════════════════════════════════
# 
# YOU ARE WORKING ON: /home/ultron/protocol_pulse/
# This is a Flask/Python site with Jinja2 templates.
# After editing files here, you MUST sync them to the live Replit server.
#
# ═══════════════════════════════════════════════════════════════
# MANDATORY FIRST STEP: READ THE FULL CONTEXT DOCUMENT
# ═══════════════════════════════════════════════════════════════

cat /home/ultron/protocol_pulse/CLAUDE_CODE_CONTEXT.md

# READ EVERY WORD. This contains the architecture, DB schema, design standards,
# what works, what's broken, and critical rules. You are blind without it.

# ═══════════════════════════════════════════════════════════════
# HOW TO DEPLOY CHANGES TO LIVE SITE
# ═══════════════════════════════════════════════════════════════
#
# The live site runs on Replit at protocolpulse.replit.app
# Replit is NOT a git clone — you must push files via HTTP relay.
#
# SYNC FUNCTION — use this after EVERY phase to push changes live:
#
# sync_to_replit() {
#   # Push a single file from Ultron to Replit
#   local FILE_PATH="$1"  # e.g., templates/podcasts.html
#   local FULL_PATH="/home/ultron/protocol_pulse/$FILE_PATH"
#   local REPLIT_PATH="/home/runner/workspace/$FILE_PATH"
#   
#   if [ ! -f "$FULL_PATH" ]; then
#     echo "ERROR: $FULL_PATH does not exist"
#     return 1
#   fi
#   
#   local B64=$(base64 -w0 "$FULL_PATH")
#   local RESULT=$(curl -s -X POST "https://protocolpulse.replit.app/api/admin/exec" \
#     -H "Content-Type: application/json" \
#     -d "{\"token\":\"581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552\",\"cmd\":\"echo '$B64' | base64 -d > $REPLIT_PATH && wc -c $REPLIT_PATH\"}")
#   echo "Synced $FILE_PATH → $RESULT"
# }
#
# restart_replit() {
#   curl -s -X POST "https://protocolpulse.replit.app/api/admin/exec" \
#     -H "Content-Type: application/json" \
#     -d '{"token":"581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552","cmd":"kill -HUP $(pgrep -f gunicorn | head -1) 2>/dev/null; sleep 3; echo RESTARTED"}'
# }
#
# IMPORTANT: For files larger than ~50KB, the base64 string may be too long 
# for a single JSON command. In that case, split the file into chunks or
# use the Ultron relay /push to write to a temp location, then copy.
# But most templates are under 50KB so the above method works.
#
# ALSO: After all files are synced, ALWAYS run restart_replit() to reload templates.
#
# ALSO: After all changes, ALWAYS git commit and push:
# cd /home/ultron/protocol_pulse && git add -A && git commit -m "description" && git push origin main

# ═══════════════════════════════════════════════════════════════
# CRITICAL RULES — VIOLATIONS WILL RUIN THE SITE
# ═══════════════════════════════════════════════════════════════
#
# 1. NEVER delete working code. Comment it out with clear markers.
# 2. NEVER rewrite a 7000-line file from scratch. Make surgical edits.
# 3. NEVER use animated glow/pulse box-shadow effects on cards.
# 4. NEVER use pbs.twimg.com URLs (Twitter blocks hotlinking).
# 5. ALWAYS test by curling the live page after sync.
# 6. ALWAYS git commit + push after each phase.
# 7. ALWAYS restart Replit gunicorn after syncing template changes.
# 8. Design standard: dark cinematic (blacks, #CC2222 red, monospace headers).
# 9. Every template extends base.html: {% extends 'base.html' %}
# 10. TREAT EACH PHASE AS IF IT'S THE ONLY TASK. Triple-verify before moving on.

# ═══════════════════════════════════════════════════════════════
# PHASE 1 OF 8: PODCASTS PAGE REDESIGN
# ═══════════════════════════════════════════════════════════════
# Time estimate: 60-90 minutes
# Template: templates/podcasts.html
# Route: grep -n "'/podcasts'" routes.py
#
# PROBLEMS:
# - Terrible design, doesn't match site aesthetic
# - "Intelligence Operators" section has broken Twitter images
# - Hardcoded quotes that aren't real data
# - Animated glow effects (already removed by earlier fix, but verify)
#
# REQUIREMENTS:
# 1. Read the full current template first: cat templates/podcasts.html
# 2. Check if podcast data comes from DB:
#    python3 -c "import psycopg2,os; c=psycopg2.connect(os.environ.get('DATABASE_URL','')); cur=c.cursor(); cur.execute('SELECT id,title,cover_image_url FROM podcast ORDER BY id DESC LIMIT 5'); print(cur.fetchall()); c.close()" 2>/dev/null || echo "No DB access from Ultron — check routes.py for how podcast data is passed to template"
# 3. Redesign the page with:
#    - Page title: "Cypherpunk'd" with tagline "Exploring Bitcoin, Web3, and Digital Liberty"
#    - Platform links: Apple Podcasts, Spotify, Fountain, YouTube (as icon buttons)
#    - If podcasts exist in DB: Featured latest episode (large card), then episode grid
#    - If no podcasts: Professional "coming soon" / "subscribe" layout
#    - Intelligence Operators: Remove entirely from this page OR redesign with:
#      - Static curated data (no Twitter API dependency)
#      - Generic avatar circles with initials (MS, LA, NB, etc.) instead of Twitter images
#      - Remove fake timestamps like "2h ago"
#      - Keep real quotes if they're genuine, remove if placeholder
#    - Card style: background rgba(20,20,20,0.8), border 1px solid rgba(255,255,255,0.08)
#    - NO glow effects anywhere
#    - Red accent (#CC2222) for section headers and CTAs
#    - Mobile responsive
#
# DEPLOY:
# sync_to_replit "templates/podcasts.html"
# restart_replit
#
# VERIFICATION GATE — DO NOT PROCEED UNTIL ALL PASS:
# V1: curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/podcasts"
#     → Must be 200
# V2: curl -s "https://protocolpulse.replit.app/podcasts" | grep -c "pbs.twimg"
#     → Must be 0
# V3: curl -s "https://protocolpulse.replit.app/podcasts" | grep -ci "cypherpunk"
#     → Must be > 0
# V4: curl -s "https://protocolpulse.replit.app/podcasts" | grep -c "animation.*glow\|pulse-glow"
#     → Must be 0
# V5: Mentally render the page. Does it look like a professional podcast page?
#     Does it match the dark cinematic aesthetic? Is it mobile-friendly?
#
# If ANY check fails, fix and re-verify. Do not move on.
# 
# git add -A && git commit -m "Phase 1: redesign podcasts page" && git push origin main

# ═══════════════════════════════════════════════════════════════
# PHASE 2 OF 8: SIGNAL CLIPS PAGE OVERHAUL  
# ═══════════════════════════════════════════════════════════════
# Time estimate: 45-60 minutes
#
# PROBLEMS:
# - Shows "0 clips" with ugly broken UI
# - No explanation of what Signal Clips is
# - Empty state looks like the site is broken
#
# REQUIREMENTS:
# 1. Find the template: grep -n "'/clips'" routes.py
#    Then: cat templates/[whatever].html
# 2. Also check what channels are monitored:
#    grep -r "channel\|CHANNEL\|youtube" services/video_engine/sources/youtube_scanner.py 2>/dev/null | head -30
# 3. Redesign with:
#    - Header: "Signal Clips" — "High-signal moments from Bitcoin's top voices"
#    - Explanation: "Our AI monitors 14+ Bitcoin YouTube channels around the clock,
#      extracts the most important clips, and delivers them here."
#    - "Sources" bar showing monitored channel names/icons
#    - Professional empty state: "Pipeline Activating" with monitoring indicator
#      (subtle CSS pulsing dot, not JS heavy)
#    - Pre-designed clip card layout (for when clips arrive):
#      - Thumbnail placeholder area (16:9 ratio)
#      - Source channel name, timestamp, duration badge
#      - Title and "Watch" button
#    - Show 3-4 placeholder cards with "Coming Soon" state
#    - Dark cinematic aesthetic, no glow effects
#
# DEPLOY:
# sync_to_replit "templates/[clips_template].html"
# restart_replit
#
# VERIFICATION GATE:
# V1: curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/clips" → 200
# V2: curl -s "https://protocolpulse.replit.app/clips" | grep -ci "signal clips" → > 0
# V3: Page does NOT show raw text like "No reels yet. Auto-job runs every 30m"
# V4: curl -s "https://protocolpulse.replit.app/clips" | grep -ci "monitor\|extract\|intelligence" → > 0
#
# git add -A && git commit -m "Phase 2: redesign clips page" && git push origin main

# ═══════════════════════════════════════════════════════════════
# PHASE 3 OF 8: ONBOARDING REWRITE
# ═══════════════════════════════════════════════════════════════
# Time estimate: 90-120 minutes (most complex phase)
#
# PROBLEMS:
# - Repeats same question 4 times
# - Form submission fails
# - Affiliate recommendations too aggressive
#
# REQUIREMENTS:
# 1. Read current code:
#    cat templates/oracle_onboarding.html
#    cat services/onboarding_service.py | head -200
#    grep -n "onboarding" routes.py | head -10
# 2. Check DB schema:
#    Look at the onboarding_session table structure in routes.py
# 3. Complete rewrite as 4-step conversational flow:
#    Step 1: "What brought you to Bitcoin?" 
#      → Investment, Philosophy, Technology, Privacy, Inflation hedge, Curiosity
#      (multi-select with styled checkboxes)
#    Step 2: "Where are you on your journey?"
#      → Beginner, Intermediate, Advanced, OG (single select with cards)
#    Step 3: "What interests you most?"
#      → Market analysis, Deep dives, Network stats, Podcasts, Community, Self-custody, Mining
#      (multi-select)
#    Step 4: "What are your goals?"
#      → Build a stack, Protect wealth, Learn tech, Stay informed, Find community
#      (multi-select)
#    Results: Personalized page recommendations based on answers
#      - Beginner + Market → "Start with Live Pulse and the Sovereign Dossier"
#      - Self-custody → "Check out our Sovereign Custody guide"
#      - Protect wealth → subtle mention of Legacy Leak article (NOT aggressive affiliate push)
#    
# 4. Implementation:
#    - All 4 steps in ONE page with JS state management
#    - Progress bar showing current step
#    - Smooth CSS transitions between steps (no page reloads)
#    - "Back" button to go to previous step
#    - No question repetition — track completed steps
#    - Results page with cards linking to relevant pages
#    - Affiliate links ONLY if genuinely relevant, labeled "Tools to explore"
#    - Store results: POST to the existing onboarding route
#    - Dark cinematic style matching site
#
# DEPLOY:
# sync_to_replit "templates/oracle_onboarding.html"
# If you changed routes.py: sync_to_replit "routes.py"
# If you changed onboarding_service.py: sync_to_replit "services/onboarding_service.py"
# restart_replit
#
# VERIFICATION GATE:
# V1: curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/onboarding" → 200 (or 308→200)
# V2: curl -s "https://protocolpulse.replit.app/onboarding" | grep -ci "what brought you\|journey" → > 0
# V3: Page has valid HTML (no unclosed tags, no missing JS variables)
#     curl -s "https://protocolpulse.replit.app/onboarding" | grep -c "undefined\|SyntaxError" → 0
# V4: Step navigation works (verify JS logic mentally — each step hides/shows correctly)
# V5: Results page shows recommendations (check the JS rendering logic)
#
# git add -A && git commit -m "Phase 3: rewrite onboarding flow" && git push origin main

# ═══════════════════════════════════════════════════════════════
# PHASE 4 OF 8: CHARTS PAGE — MULTI-ASSET COMPARISON
# ═══════════════════════════════════════════════════════════════
# Time estimate: 60-90 minutes
#
# REQUIREMENTS:
# 1. Find the charts template:
#    grep -n "'/charts'" routes.py
#    Read the template
# 2. Add comparison charts showing "Everything Measured in Bitcoin":
#    - Gold (XAU) priced in BTC
#    - Silver (XAG) priced in BTC  
#    - S&P 500 priced in BTC
#    - US Dollar (DXY) priced in BTC (inverted)
#    - Real Estate index priced in BTC
# 3. Data approach:
#    - Check what chart library is already used (Chart.js? Recharts? Custom?)
#    - Check if there's a price_service: cat services/price_service.py | head -50
#    - If real-time BTC-denominated data isn't available, create chart containers
#      with hardcoded historical datapoints and a "Live data coming soon" note
#    - Use CoinGecko API for BTC price if available
# 4. Design:
#    - Section header: "PURCHASING POWER DECAY" 
#    - Subtitle: "Every asset measured against the hardest money ever created"
#    - Time toggles: 1M, 3M, 1Y, 5Y, ALL
#    - Dark chart backgrounds, red (#CC2222) line for BTC performance,
#      gray lines for other assets
#    - Each chart in its own card with clean layout
#    - Existing BTC chart should remain untouched at top
#    - New charts go below in a 2-column grid
#
# DEPLOY:
# sync_to_replit "templates/[charts_template].html"
# If you modified routes.py: sync_to_replit "routes.py"
# restart_replit
#
# VERIFICATION GATE:
# V1: curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/charts" → 200
# V2: curl -s "https://protocolpulse.replit.app/charts" | grep -ci "gold\|silver\|purchasing" → > 0
# V3: Existing BTC chart still renders
# V4: No JS errors (check for undefined vars, missing libraries)
#
# git add -A && git commit -m "Phase 4: charts multi-asset comparison" && git push origin main

# ═══════════════════════════════════════════════════════════════
# PHASE 5 OF 8: MAPS PAGE FIX
# ═══════════════════════════════════════════════════════════════
# Time estimate: 30-45 minutes
#
# REQUIREMENTS:
# 1. Find map template: grep -n "'/map'" routes.py && find templates -name "*map*"
# 2. Read and understand current implementation (Leaflet? Mapbox? Google Maps?)
# 3. Fix darkness issue:
#    - If using dark tile layer, switch to lighter variant OR
#    - Add CSS filter: brightness(1.3) contrast(1.1) to the map container
#    - Keep the dark UI around the map, just make the map tiles readable
# 4. Add Bitcoin event markers:
#    - Naples, FL (26.142, -81.795): "BitcoinDay Naples"
#    - Tampa, FL (27.950, -82.457): "BitcoinDay Tampa"  
#    - Washington, DC (38.907, -77.037): "BitcoinDay DC"
#    - Nashville, TN (36.163, -86.781): "Bitcoin 2026"
#    - Each marker: red pin, popup with event name + "Visit /events for details"
# 5. Check for existing event data:
#    cat data/pulse_events.jsonl 2>/dev/null | head -5
#    Use it if available, add hardcoded markers if not
#
# DEPLOY:
# sync_to_replit "templates/[map_template].html"
# restart_replit
#
# VERIFICATION GATE:
# V1: curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/map" → 200
# V2: curl -s "https://protocolpulse.replit.app/map" | grep -ci "naples\|bitcoinday\|event" → > 0
# V3: Map still renders (check for JS library includes)
#
# git add -A && git commit -m "Phase 5: map page lighter tiles + events" && git push origin main

# ═══════════════════════════════════════════════════════════════
# PHASE 6 OF 8: LIVE PULSE REORGANIZATION
# ═══════════════════════════════════════════════════════════════
# Time estimate: 60-90 minutes
# Template: templates/live_terminal.html (WARNING: 7000+ lines)
#
# THIS IS THE MOST DANGEROUS PHASE. Be extremely careful.
#
# REQUIREMENTS:
# 1. Read the file structure first — do NOT read all 7000 lines:
#    grep -n "section\|<h2\|<h3\|class=\"pp-\|module\|widget\|panel\|SECTION" templates/live_terminal.html | head -60
# 2. Identify sections that DON'T belong on the market dashboard:
#    - Intelligence Operators → belongs on homepage
#    - Podcast widgets → /podcasts
#    - Social feeds / X feed → /media 
#    - Nostr widgets → /nostr-signal
# 3. COMMENT OUT (do NOT delete) misplaced sections:
#    <!-- MOVED TO /podcasts: [section description] -->
#    ... commented content ...
#    <!-- END MOVED SECTION -->
# 4. What STAYS on Live Pulse:
#    - Bitcoin price (large, prominent)
#    - Price chart (24h/7d/30d)
#    - Network stats (hashrate, difficulty, mempool, fees)
#    - Fear & Greed index
#    - Sentiment indicators
#    - Legacy Leak CTA (links to /articles/1838)
#    - The TXID orb (if present — PBX likes this, DO NOT REMOVE)
# 5. Improve layout of remaining widgets:
#    - BTC price as the hero element — massive, centered
#    - Network stats in clean grid below
#    - Chart full-width
# 6. Be SURGICAL. Edit specific line ranges. Do not reformat the entire file.
#
# DEPLOY:
# sync_to_replit "templates/live_terminal.html"
# restart_replit
#
# VERIFICATION GATE:
# V1: curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/market" → 200
# V2: curl -s "https://protocolpulse.replit.app/market" | grep -ci "bitcoin\|btc" → > 0
# V3: BTC price element still present
# V4: Page loads without JS errors
# V5: TXID orb still present (if it was there): 
#     curl -s "https://protocolpulse.replit.app/market" | grep -ci "txid\|orb"
#
# git add -A && git commit -m "Phase 6: reorganize live pulse" && git push origin main

# ═══════════════════════════════════════════════════════════════
# PHASE 7 OF 8: STAGE PAGE — AVATAR SHOWCASE
# ═══════════════════════════════════════════════════════════════
# Time estimate: 45-60 minutes
# Template: templates/stage.html
#
# REQUIREMENTS:
# 1. Read current template: cat templates/stage.html
# 2. Reference Oracle page for API integration:
#    grep -B5 -A30 "oracle/speak\|SPEAK_URL\|askOracle" templates/oracle.html | head -60
# 3. Redesign as Oracle showcase:
#    - Large circular avatar (350-400px) centered
#    - Static oracle avatar image with CSS breathing animation (subtle scale pulse)
#    - "Ask The Oracle" input below avatar
#    - When user submits: POST to /api/oracle/speak
#    - Play returned video in the avatar circle + audio
#    - Below: "Latest Intelligence" — show 3 most recent article titles
#    - Dark "broadcast studio" aesthetic
#    - Remove any placeholder sponsor grids or fake partner data
# 4. The /api/oracle/speak endpoint returns:
#    {response: "text", audio_base64: "...", video_base64: "...", pipeline_time: 14.5}
#    Video is MP4, audio is MP3. Decode base64, create blob URLs, play.
# 5. Avatar image path: check for existing avatar images:
#    find static/images -name "*oracle*" -o -name "*avatar*" 2>/dev/null | head -5
#    OR find oracle/ -name "*.png" -o -name "*.jpg" 2>/dev/null | head -5
#
# DEPLOY:
# sync_to_replit "templates/stage.html"
# restart_replit
#
# VERIFICATION GATE:
# V1: curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.replit.app/stage" → 200
# V2: curl -s "https://protocolpulse.replit.app/stage" | grep -ci "oracle\|avatar" → > 0
# V3: Page has the /api/oracle/speak fetch call
# V4: Dark cinematic aesthetic, no glow effects
#
# git add -A && git commit -m "Phase 7: stage page oracle showcase" && git push origin main

# ═══════════════════════════════════════════════════════════════
# PHASE 8 OF 8: FINAL VERIFICATION SWEEP
# ═══════════════════════════════════════════════════════════════
# Time estimate: 20-30 minutes
#
# Run ALL these checks. Fix any failures.

echo "════════════════════════════════════════"
echo "FINAL VERIFICATION SWEEP"
echo "════════════════════════════════════════"

echo "=== All Pages Status ==="
for page in "" articles market oracle stage events dossier podcasts clips map merch whale-watcher solo-slayers about contact search donate pulse-check; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://protocolpulse.replit.app/$page")
  printf "%-25s %s\n" "/$page" "$CODE"
done

echo ""
echo "=== Glow Effects (should be 0) ==="
grep -rl "pulse-glow\|animation.*glow" templates/ 2>/dev/null | wc -l

echo "=== Broken Twitter Images (should be 0) ==="
grep -rl "pbs.twimg.com" templates/ 2>/dev/null | wc -l

echo "=== Git Status ==="
cd /home/ultron/protocol_pulse
git status --short
git log --oneline -10

# If anything fails, fix it and commit.
# Final commit:
# git add -A && git commit -m "Phase 8: final verification sweep" && git push origin main

echo "════════════════════════════════════════"
echo "ALL PHASES COMPLETE"
echo "════════════════════════════════════════"
echo ""
echo "Summary of changes made:"
echo "Phase 1: Podcasts page redesign"
echo "Phase 2: Signal Clips page overhaul"
echo "Phase 3: Onboarding rewrite"
echo "Phase 4: Charts multi-asset comparison"
echo "Phase 5: Maps page fix"
echo "Phase 6: Live Pulse reorganization"
echo "Phase 7: Stage page avatar showcase"
echo "Phase 8: Final verification"
echo ""
echo "Next: Owner should visually review each page in browser."
