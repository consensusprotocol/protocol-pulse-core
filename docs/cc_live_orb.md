Read ~/protocol_pulse/templates/live_terminal.html lines 4511-4900 (current TXID stream hero).
Read ~/protocol_pulse/templates/live_terminal.html lines 7100-7200 (Three.js imports).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIVE TERMINAL HERO — ORB + TXID STREAM HYBRID
Protocol Pulse brand colors: Red #CC0000, Gold #F8C15C, Dark #0A0A0F
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Replace the current hero section (#nebula-hero) with this two-panel layout:

LAYOUT — Full viewport hero, two panels side by side:

LEFT PANEL (45% width) — TXID STREAM (glassmorphic window)
A stunning glassmorphic card with:
  - backdrop-filter: blur(20px) saturate(180%)
  - background: rgba(10,10,15,0.7) 
  - border: 1px solid rgba(204,0,0,0.3)
  - border-radius: 16px
  - box-shadow: 0 0 40px rgba(204,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.05)
  - Red gradient glow on top edge
  - Header: "● MEMPOOL STREAM" in red monospace, "LIVE" badge pulsing
  - Scrolling list of incoming unconfirmed transactions:
    Each tx card: TXID (first 8...last 8) in #F8C15C gold monospace
    Fee rate colored bar (left edge): green=low, white=medium, red=high
    BTC amount in white
    "Xs ago" timestamp in muted gray
    Hover: card lifts, gold border glow, cursor pointer
    Click: opens mempool.space/tx/{full_txid} in new tab
    Slide+fade in animation when new tx arrives (translateY -20px → 0, opacity 0→1)
    Max 20 cards, oldest fade out gracefully
  - Bottom bar: "● Xk unconfirmed · X tx/min"

RIGHT PANEL (55% width) — THE ORB
Three.js WebGL canvas, full panel height.
Central glowing orb representing Bitcoin network state.

ORB CONSTRUCTION:
  - Core sphere: THREE.SphereGeometry(1.2, 64, 64)
    Material: MeshPhongMaterial, color #CC0000, emissive #880000
    Wireframe overlay: thin red lines, opacity 0.3
  - Outer glow: 3 nested spheres at 1.4, 1.6, 1.8 radius
    Each: MeshBasicMaterial with decreasing opacity (0.06, 0.04, 0.02)
    Color: #F8C15C (gold) for price-driven glow, #CC0000 for hashrate pulse
  - UnrealBloom post-processing: strength 1.5, radius 0.4, threshold 0.1
  - PointLight inside orb: color #F8C15C, intensity driven by BTC price
  - Ambient light: color shifts with Fear & Greed (navy fear → gold greed)

TRANSACTION PARTICLES:
  As each new tx arrives from WebSocket:
  - A glowing particle spawns at the edge of the scene
  - Travels toward the orb center on a curved arc
  - Color: fee rate (gold=low, white=medium, red=high)  
  - Size: proportional to tx value
  - On reaching the orb: small flash, orb pulse, particle absorbed
  - InstancedMesh for performance (max 300 particles desktop, 80 mobile)

BLOCK CONFIRMATION:
  When new block arrives via WebSocket:
  - Orb flashes brilliant white (0.3s)
  - Expanding ring emanates from orb outward
  - All remaining particles sweep into orb simultaneously
  - Block height displayed briefly in large gold text: "BLOCK 889,432"
  - Orb settles with slightly brighter glow for 10s

ORB DATA BINDINGS:
  - BTC price → orb core brightness (higher price = brighter)
  - Hashrate → rotation speed (higher hashrate = faster spin)
  - Fear & Greed → ambient light color temperature
  - Mempool congestion → particle density/color (red cloud = congested)
  - Block time elapsed → tension buildup (orb gets redder as block overdue)

HUD BAR (full width, above both panels, 56px):
  - Dark glass bar: rgba(0,0,0,0.8) backdrop-blur
  - Left: ● BTC $71,XXX (+1.3%) updated from /api/btc-price every 30s
  - Center: MEMPOOL: XX MB · NEXT BLOCK: X sat/vB · HASHRATE: XXX EH/s
  - Right: FNG: XX GREED · ● LIVE (pulsing red dot)

BACKGROUND:
  Behind both panels: subtle dark radial gradient
  Red corner glows (brand aesthetic)
  Optional: if ~/protocol_pulse/static/videos/server_room.mp4 exists,
  play it as a very subtle (opacity 0.08) looping background video behind everything

WEBSOCKET:
  Reuse existing WebSocket connection in live_terminal.html
  wss://mempool.space/api/v1/ws
  Subscribe: {"action":"want","data":["blocks","mempool-blocks","stats"]}

MOBILE:
  On width < 768px: stack panels vertically (orb on top, TXID below)
  Reduce particle count to 40, disable bloom on mobile for performance

KEEP ALL CONTENT BELOW THE HERO INTACT.
Only replace #nebula-hero contents.

VERIFY: curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:5000/live
Must be 200.

COMMIT:
  git add templates/live_terminal.html
  git commit -m "feat(live): Stellar Nebula — WebGL Bitcoin heartbeat visualization with golden spiral physics"
  git push
