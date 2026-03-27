Read ~/protocol_pulse/templates/live_terminal.html lines 4511-4800 (nebula hero section).
Read ~/protocol_pulse/templates/live_terminal.html lines 7300-8200 (WebSocket code).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIVE TERMINAL HERO — REPLACE NEBULA WITH REAL TXID STREAM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Stellar Nebula glowing ball is WRONG. User wants REAL BITCOIN
TRANSACTION IDs streaming in real time. Actual TXIDs from the
mempool WebSocket. The living, breathing heartbeat of Bitcoin
is the ACTUAL TRANSACTIONS — not an abstraction.

REPLACE the #nebula-hero section entirely with this:

LAYOUT — Two zones inside a full-viewport dark hero:

LEFT 65% — MEMPOOL STREAM:
Scrolling list of incoming unconfirmed txs, newest at top.
Each tx card shows:
  - TXID: first 8 chars...last 8 chars (gold monospace, 11px)
  - Fee rate in sat/vB (colored: <=2=green, 3-20=white, >20=red)  
  - "X sats/vB · Y vB" size info
  - Slide+fade in from top when new tx arrives
  - Max 25 cards visible, oldest fade out at bottom
  - Top-left: "● 47 tx/min" counter (updates every 10s)
  - Top-right: "142,847 unconfirmed" mempool depth

RIGHT 35% — BLOCK FEED:
When block arrives (WebSocket "block" event):
  - Full-screen white flash 200ms on left zone
  - New block card slides in:
    - Block height (large gold number)
    - "BLOCK CONFIRMED" green badge
    - Tx count, fees, miner
  - Stack up to 5 blocks vertically

TOP HUD (60px, full width, above both zones):
  - BTC price (from /api/btc-price, 30s refresh)
  - Mempool vMB
  - Next-block fee rate
  - Hashrate EH/s  
  - FNG index + label
  - "● LIVE" pulsing red dot right-aligned

WEBSOCKET (reuse existing at line ~7328):
Subscribe: {"action":"want","data":["blocks","mempool-blocks","live-2h-chart","stats"]}
On "block" event: flash + block card
On "mempool-blocks": extract individual txs and add to stream
Each tx object: {txid, fee, vsize, value} from mempool.space API format

FIBONACCI applied to REAL DATA:
  - Card heights: txs grouped by fee tier, golden ratio spacing
  - Block confirmation flash duration = 200ms * (fees/avg_fees) capped at 600ms
  - Card enter animation: cubic-bezier(0.618, 0, 0.382, 1) — golden ratio easing

DESIGN:
  - Background: #0A0A0F (PIPELINE_LAWS brand color)
  - Red border frame (2px, matching BLACK DIAMOND bg from assembler)
  - TXIDs in Protocol Pulse Gold (#F8C15C) monospace
  - Amounts/fees in white
  - Labels in rgba(255,255,255,0.4) muted
  - Card bg: rgba(255,255,255,0.03) with 1px rgba(255,255,255,0.08) border
  - On hover: card lifts with rgba(248,193,92,0.1) border glow
  - Section divider: 1px red vertical line between zones

SIGNAL INTERRUPTED state:
  If WebSocket drops: show "⚡ SIGNAL INTERRUPTED — RECONNECTING"
  centered overlay, exponential backoff reconnect (2s, 4s, 8s, max 30s)

KEEP EVERYTHING BELOW THE HERO INTACT.
Only replace the content inside #nebula-hero.
Keep the div id="nebula-hero" itself.
Remove all nebula JS (the golden spiral, InstancedMesh, THREE.js bloom,
accretion rings — all of it). Replace with the TXID stream JS.

The node globe below uses its own Three.js init — keep it untouched.

VERIFY:
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:5000/live
  Must be 200.

COMMIT:
  git add templates/live_terminal.html
  git commit -m "feat(live): TXID stream hero — real mempool transactions, block feed, live HUD"
  git push
