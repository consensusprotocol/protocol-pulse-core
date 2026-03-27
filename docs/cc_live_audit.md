Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/VISUAL_DESIGN_SYSTEM.md lines 1-100.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIVE TERMINAL — CROSS-LLM VISUAL DESIGN AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is a PRODUCT DESIGN audit, not a code correctness audit.
Goal: Each LLM independently designs the most breathtaking
possible real-time visualization of live Bitcoin network data.
Then we synthesize the winner.

CONTEXT — what exists today:
  ~/protocol_pulse/templates/live_terminal.html (9,534 lines)
  - Three.js r128 with UnrealBloom post-processing
  - Node globe (Three.js WebGL)
  - 2D canvas mempool bar chart
  - Multiple Chart.js panels
  - WebSocket to wss://mempool.space/api/v1/ws (partially implemented)
  - Data: BTC price, mempool size/fees, hashrate, FNG, block height

The page has GREAT bones but the visualization feels like a
collection of widgets rather than one coherent living thing.

BRIEF for each LLM — answer these 8 questions independently:

Q1. HERO VISUALIZATION: Design the centerpiece. What does the
    "heartbeat of Bitcoin" look like in WebGL? Be specific about:
    - What each particle/node represents
    - How transactions appear and travel
    - How block confirmations manifest visually
    - Color language (what does fee pressure look like? fear vs greed?)
    - How Fibonacci ratios or golden spiral physics apply

Q2. DATA MAPPING: Map each live data point to a visual property.
    BTC price → ? Mempool size → ? Hashrate → ? FNG → ?
    Block time → ? Fee rate → ? Transaction count → ?

Q3. LAYOUT: How should the page be organized? The hero vis plus
    what supporting elements? What gets cut from the current page?

Q4. PERFORMANCE: Given Three.js r128 on mobile, what are the
    specific optimizations needed? Particle count limits?
    Instanced mesh vs individual meshes?

Q5. FIBONACCI/SACRED GEOMETRY: How specifically would you apply
    golden ratio or Fibonacci spiral to the particle physics?
    Give concrete math, not vague references.

Q6. EMOTIONAL IMPACT: What should a first-time visitor feel
    in the first 5 seconds? Design that moment specifically.

Q7. DATA FRESHNESS: How do you handle the WebSocket connection
    dropping or mempool.space being slow? Graceful degradation?

Q8. KILLER FEATURE: What is the ONE feature that makes this
    page something people screenshot and share on Twitter?

INSTRUCTIONS FOR RUNNING AUDIT:
  python3 utils/cross_llm_audit.py \
    --feature live-terminal-design \
    --files templates/live_terminal.html \
    --question "Design the most breathtaking possible real-time visualization of live Bitcoin network data for a browser page. Answer all 8 questions in the brief at docs/cc_live_audit.md with specific, implementable details. Be bold. Compete to win." \
    --cycles 2

Save the full audit output to:
  docs/live_terminal_audit_results.md

Then synthesize:
  - Which model's hero visualization concept is strongest?
  - What data mapping is most coherent?
  - What is the consensus killer feature?
  - Draft the winning design spec in docs/live_terminal_design_v2.md

DO NOT build any code yet. Audit and design spec only.
The build happens in a separate CC session after review.

OUTPUT FORMAT for docs/live_terminal_design_v2.md:
  ## WINNING CONCEPT
  ## DATA MAPPING TABLE
  ## FIBONACCI PHYSICS SPEC
  ## LAYOUT PLAN (keep/cut/add)
  ## FIRST 5 SECONDS EXPERIENCE
  ## PERFORMANCE BUDGET
  ## KILLER FEATURE
  ## IMPLEMENTATION NOTES FOR BUILD SESSION
