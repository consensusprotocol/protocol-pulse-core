Read ~/protocol_pulse/docs/live_terminal_design_v2.md IN FULL — this is the build bible.
Read ~/protocol_pulse/templates/live_terminal.html lines 7099-7200 (Three.js imports and init).
Read ~/protocol_pulse/templates/live_terminal.html lines 7726-7995 (node globe Three.js code).
Read ~/protocol_pulse/PIPELINE_LAWS.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIVE TERMINAL — STELLAR NEBULA BUILD
Incorporate best elements from ALL THREE LLMs per the design spec.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The design spec in live_terminal_design_v2.md is your complete guide.
Build the Stellar Nebula visualization as the HERO SECTION of /live.

KEY RULES:
- BANNED: Three.js VR, DAO, quantum auth, genetic algorithms (per PIPELINE_LAWS)
- Three.js r128 already loaded — use it, do not upgrade
- UnrealBloom already available — use it
- WebSocket to wss://mempool.space/api/v1/ws for live data
- InstancedMesh for particles (performance critical)
- MAX 2000 particles desktop, 500 mobile (check window.innerWidth < 768)
- Graceful degradation: if WebSocket fails, show demo mode with simulated data
- Do NOT break any existing route or Flask endpoint
- KEEP the node globe — it moves BELOW the hero nebula section

WHAT TO BUILD:
1. Replace the current hero section of live_terminal.html with the
   full Stellar Nebula WebGL visualization (full-viewport canvas)
2. Central pulsing star (hashrate=pulse freq, price=brightness)
3. Mempool particle cloud on golden spiral paths
4. Block confirmation shockwave (WebSocket block event)
5. Accretion disk rings (confirmed blocks)
6. Fear & Greed ambient lighting (scene color temperature)
7. Data HUD overlay (top-right: price, mempool, hashrate, FNG)
8. Keep everything BELOW the hero intact (node globe, charts, etc.)

The node globe code at line 7726 stays — just moves below the nebula.

FIBONACCI PHYSICS (exact from spec):
  phi = 1.6180339887
  b = Math.log(phi) / (Math.PI / 2)  // 0.3063
  // Spiral path: r = a * e^(b * theta)
  // Golden angle for accretion rings: 137.5 degrees = 2.399963 radians
  // Fibonacci sphere distribution for particle spawn points

WEBSOCKET DATA:
  Connect to wss://mempool.space/api/v1/ws
  Subscribe: {"action":"want","data":["blocks","mempool-blocks","live-2h-chart"]}
  On block: trigger shockwave + new accretion ring
  On mempool-block: update particle density and fee colors
  Graceful reconnect on disconnect (exponential backoff, max 30s)

PERFORMANCE:
  Use THREE.InstancedMesh for all particles
  Use THREE.BufferGeometry for rings
  requestAnimationFrame — target 60fps desktop, 30fps mobile
  Reduce particle count and bloom on mobile/low-end

VERIFICATION:
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:5000/live
  Must be 200. Page must load without JS errors in console.
  The existing /live page routes must still work.

COMMIT:
  git add templates/live_terminal.html
  git commit -m "feat(live): Stellar Nebula — WebGL Bitcoin heartbeat visualization with golden spiral physics"
  git push
