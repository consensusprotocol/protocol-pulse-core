Read core/templates/live_terminal.html lines 1-50 (to confirm it's the SovereignTerminal version).
Read services/merch_routes.py.
Read services/printful_service.py lines 1-50.
Read templates/merch.html lines 1-50.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIVE TERMINAL + MERCH WIRING — ALL FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK 1 — Fix TXID particles to show fresh real-time transactions
In static/js/visualizer.js the WebSocket connection subscribes to mempool.space.
Find the connectWS() or connect() method and the subscription message.
Current issue: particles show TXIDs from hours ago.
Fix: On WebSocket connect, send subscription for live unconfirmed transactions:
  {"action": "want", "data": ["live-2h-chart", "stats", "mempool-blocks"]}
Then for each new tx received, add it to the particle pool AND immediately drop
the oldest particle if pool is full (maxParticles). This ensures the orb shows
only the freshest TXIDs within the last few minutes.
Also set particle lifetime: any particle older than 10 minutes should fade out
and be replaced by a new tx particle.
The particle.txid should always link to mempool.space/tx/{txid}.
Test by checking the WebSocket subscription in the browser console.

TASK 2 — Make Mempool Heatmap real-time
In core/templates/live_terminal.html, find the Mempool Heatmap section.
Currently it shows static bar widths. 
Add a JS function updateMempoolHeatmap() that:
  - Fetches from https://mempool.space/api/v1/fees/mempool-blocks every 30 seconds
  - Updates the fee-tier bars to reflect actual mempool block sizes and fee rates
  - Each bar width = proportional to the vsize of that fee band
  - Color gradient already exists, just update the widths dynamically
Call updateMempoolHeatmap() on page load and setInterval every 30s.

TASK 3 — Make Epoch Progress real-time
In core/templates/live_terminal.html, find the Epoch Progress section.
Add updateEpochProgress() that:
  - Fetches from https://mempool.space/api/v1/difficulty-adjustment
  - Updates: blocks mined this epoch, blocks remaining, estimated adjustment %, time remaining
  - Updates the progress bar width = (blocksInEpoch / 2016) * 100
Call on load and setInterval every 60s.

TASK 4 — Health Score hover popup
In core/templates/live_terminal.html, find the Health Score widget (98.7% HEALTH SCORE).
Add a hover/click tooltip that appears as a glassmorphic popup explaining:
  "Health Score is computed from 5 live metrics:
   • Hashrate trend (30d) — currently Optimal
   • Mempool congestion — currently Clear  
   • Block time deviation from 10min target
   • Fee rate stability
   • Node count / decentralization signal
  Each metric is weighted and normalized to 100. This score updates every 5 minutes."
Style: dark glass card, red accent border, appears on hover above the widget.
Dismiss on click-outside.

TASK 5 — Wire Merch + Printful into Flask
Read services/merch_routes.py — extract all the route functions.
Add them to core/routes.py by reading the route file and inserting:
  1. Import PrintfulService at top of routes.py: 
     try:
         from services.printful_service import PrintfulService
         printful_service = PrintfulService()
     except Exception as e:
         logging.warning(f"Printful not available: {e}")
         printful_service = None
  
  2. Add all routes from services/merch_routes.py to core/routes.py
     (the /merch, /checkout, /webhook/stripe, /webhook/printful routes)
  
  3. Copy templates/merch.html to core/templates/merch.html (if not already there)
     cp templates/merch.html core/templates/merch.html

  4. Copy templates/merch_success.html to core/templates/merch_success.html
     cp templates/merch_success.html core/templates/merch_success.html

  5. Test: curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:5000/merch
     Expected: 200 (even without PRINTFUL_API_KEY, should show empty product grid)

TASK 6 — Install stripe if not present
  pip install stripe --break-system-packages 2>/dev/null || echo already installed

TASK 7 — Add PRINTFUL_API_KEY note to .env
  grep -q PRINTFUL_API_KEY ~/protocol_pulse/.env || echo "PRINTFUL_API_KEY=" >> ~/protocol_pulse/.env
  echo "Note: PBX needs to add Printful API key from https://www.printful.com/dashboard/developer/api"

AFTER ALL TASKS:
  # Reload gunicorn (HUP via python)
  python3 -c "import subprocess; pids=subprocess.check_output(['pgrep','-f','gunicorn.*5000']).decode().split(); [__import__('os').kill(int(p),1) for p in pids if p.strip()]" 2>/dev/null || true
  sleep 8
  
  # Verify merch route
  curl -s --max-time 8 -o /dev/null -w "%{http_code}" http://localhost:5000/merch
  echo MERCH_STATUS
  
  git add -A
  git commit -m "feat(merch+live): wire Printful/Stripe merch, real-time heatmap/epoch, health score popup, fresh TXID particles"
  git push
