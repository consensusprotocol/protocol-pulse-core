Load ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/gospels/STAGE_BROADCAST_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/stage-broadcast/FINAL_CONSENSUS.md.
Read ~/protocol_pulse/templates/stage.html IN FULL.
Read ~/protocol_pulse/templates/oracle_live.html IN FULL (for push-to-speak reference).
Read ~/protocol_pulse/services/stage_brief_pipeline.py (for data fetch patterns).
Read ~/protocol_pulse/oracle/avatar_server.py lines 468-560 (Kokoro af_heart TTS).

MISSION: Transform /stage into a 24/7 autonomous Bitcoin broadcast station AND fix all P0/P1 security issues identified in the cross-LLM audit. Female avatar. Kokoro af_heart voice (already proven, fast, on cuda:1). Always broadcasting. Visitor can interrupt.

=======================================================================
PART A — FIX ALL AUDIT P0/P1 ISSUES FIRST (do before any new features)
=======================================================================

P0.1 — Server-side rate limiting (templates/stage.html + core/routes.py)
  Add Flask-Limiter or manual Redis/memory rate limiting to these routes:
  /api/oracle/chat, /api/stage/transcripts, /api/stage/brief, /oracle/speak
  Return 429 with Retry-After header. Handle 429 in stage.html JS with
  user-visible "Too many requests — please wait Xs" message.
  Client-side busy flag stays as UX only, not security.

P0.2 — Replace custom esc() function with safe sanitization (stage.html ~1057)
  Delete esc(). Replace all innerHTML assignments that use external/API data with:
  - textContent for plain text output
  - DOMPurify.sanitize() for any intentional HTML (load DOMPurify from CDN)
  Audit every innerHTML in stage.html. Fix line ~965 (sidebarSentimentLine).

P0.3 — Fix stageChat race condition (stage.html ~1290, ~1309)
  setBusy(false) currently fires in .finally() when HTTP request completes.
  Move setBusy(false) to fire only AFTER video playback ends (onended callback
  or after the polling interval that confirms video played successfully).

P0.4 — Add missing #txDots DOM element (stage.html ~865)
  Add <div id="txDots"></div> inside .stage-transcripts-wrap.
  Replace window.renderTranscripts monkey-patch (lines ~1476-1480) with a
  custom DOM event: dispatchEvent(new CustomEvent('transcriptsRendered'))
  and listen for it in initTxDots.

P1.1 — ARIA labels + keyboard navigation (stage.html throughout)
  Add aria-label to all icon-only buttons (mic button ~810, mode toggles ~855).
  Add role="status" and aria-live="polite" to dynamic content regions (price, sentiment).

P1.2 — Speech recognition timeout (stage.html ~1339)
  Add 10-second timeout that auto-cancels _stageRecognition and shows toast.
  Populate onerror with user-visible message.

P1.3 — playVid autoplay timeout (stage.html ~1155-1158)
  Add 30-second timeout that rejects the playVid promise if user never taps.
  Show recovery UI: "Tap anywhere to play" overlay.

P1.4 — Reduce polling to 30s (stage.html ~1451, ~1482)
  Change setInterval calls for price/sentiment/Nostr from 2-3 min to 30s.
  Add "last updated Xs ago" indicator near live data displays.

P1.5 — URL.revokeObjectURL in all paths (stage.html ~1136)
  Wrap in finally block with null check to prevent blob URL memory leaks.

=======================================================================
PART B — BUILD THE BROADCAST SYSTEM
=======================================================================

STEP 1: services/stage_broadcast_service.py (new file)

Background worker — run via cron every 5 min:
  python3 ~/protocol_pulse/services/stage_broadcast_service.py

Queue file: ~/protocol_pulse/video_pipeline_v3/data/stage_briefs/broadcast_queue.json

Queue item schema:
{
  "id": "uuid4",
  "type": "PRICE_ALERT|THOUGHT_LEADER|SPACE_TAP|ARTICLE_TEASER|METRICS_PULSE|NOSTR_SIGNAL|FILLER_INSIGHT",
  "priority": 1-5,
  "script": "30-90 second spoken script for female anchor",
  "source_label": "📡 PRICE ALERT",
  "topic_preview": "Bitcoin breaks $87k resistance",
  "generated_at": "ISO",
  "expires_at": "ISO"  // PRICE_ALERT: 15min, THOUGHT_LEADER: 2hr, rest: 4hr
}

Max queue depth: 8 items. Auto-remove expired. Priority sort (1=first).

Signal checks each run (import data fetch patterns from stage_brief_pipeline.py):
  1. PRICE_ALERT (pri=1): GET /api/btc-price, compare to cached price in
     /tmp/stage_last_price.json. If >0.8% move: generate alert script.
     Cache current price after check.

  2. THOUGHT_LEADER (pri=2): Read raw_tweets.json (fresh Nitter tweets).
     Find tweets from priority-1 handles (saylor, natbrunell, jack, gladstein,
     PrestonPysh, MartyBent, LynAldenContact, JeffBooth, ODELL, aantonop,
     adam3us) with created_at in last 2 hours. Max 1 per run.

  3. SPACE_TAP (pri=2): Check x_spaces_scraper/cache/ for clips.json files
     newer than 2 hours. If found, generate "we intercepted a live space" script.

  4. ARTICLE_TEASER (pri=3): Query DB for articles published in last 30 min.
     SELECT title, subtitle FROM articles ORDER BY created_at DESC LIMIT 1.

  5. METRICS_PULSE (pri=3): Check /tmp/stage_last_metrics.json - if last
     metrics broadcast was >20 min ago: fetch hashrate, FNG, mempool fees,
     block height. Generate pulse script. Update timestamp.

  6. NOSTR_SIGNAL (pri=4): Read video_pipeline_v3/data/intelligence/
     narrative_context.json. If dominant_narrative exists and updated in
     last 4 hours: generate nostr discourse script.

  7. FILLER_INSIGHT (pri=5): Always add if queue has <2 items.
     Rotate through 20 pre-written Bitcoin/cypherpunk insight scripts
     stored in the service file itself as a list. Never repeat consecutively.

Script generation via Claude claude-haiku-4-5-20251001:
  - Female anchor voice: authoritative, calm, data-precise, cypherpunk worldview
  - Never hype, never FUD, always data-backed
  - Each script 30-90 seconds when spoken at ~150 words/minute
  - Always inject REAL data (price, metrics) into every script
  - End each script with natural segue: "Stay with me, more coming..."
  - Use Anthropic API (ANTHROPIC_API_KEY from .env)

Add to crontab:
  */5 * * * * python3 ~/protocol_pulse/services/stage_broadcast_service.py >> ~/protocol_pulse/logs/broadcast_service.log 2>&1

STEP 2: New Flask routes in core/routes.py

  GET /api/stage/broadcast-queue
    Returns next 3 items from queue sorted by priority, does NOT consume.
    Response: {items: [...], queue_depth: N, session_start: ISO}

  POST /api/stage/consume-broadcast
    Body: {consumed_id: "uuid"}
    Atomically removes consumed item (file lock), returns next item.
    If queue empty: generates a FILLER_INSIGHT immediately via Haiku and returns it.
    Response: {next_item: {...} or null, queue_depth: N}

  GET /api/stage/broadcast-status
    Response: {live: true, current_topic: str, queue_depth: N, next_topic: str}

  Rate limit all three: 30/minute per IP.

STEP 3: Transform templates/stage.html

PRESERVE: All existing avatar rendering logic, Wav2Lip calls, avatar server integration.
REPLACE: The brief-based system with the broadcast queue consumer.

New UI elements to ADD (do not remove existing layout, just add to it):

A) ON AIR indicator (top of avatar panel, before avatar video element):
   <div id="onAirBadge">
     <span class="on-air-dot"></span> ON AIR
     <span id="signalSourceLabel">📡 INITIALIZING</span>
   </div>
   CSS: pulsing red dot, red text, positioned absolute top-left of avatar panel

B) Broadcast ticker (bottom strip, full width):
   <div id="broadcastTicker">
     <span class="ticker-label">UP NEXT</span>
     <div id="tickerContent">Loading broadcast queue...</div>
   </div>
   CSS: scrolling marquee animation, dark strip at page bottom

C) Session timer (top-right corner):
   <div id="sessionTimer">Broadcasting for <span id="sessionTime">0:00</span></div>
   JS: starts on page load, increments every second

D) Push-to-speak button — COPY EXACTLY from oracle_live.html:
   - Same first-time modal: "The anchor is live. Tap to ask a question."
   - Same mic permission request with retry
   - Same recording UX (hold or tap)
   - When recording: fade broadcast audio to 20% volume
   - After response: "Returning to broadcast in 3..." countdown then resume

E) Broadcast queue consumer (JS):
   async function startBroadcast() {
     const queue = await fetch('/api/stage/broadcast-queue').then(r=>r.json())
     if (!queue.items?.length) {
       // Generate filler inline
       await consumeAndPlay(null)
       return
     }
     await playBroadcastItem(queue.items[0])
   }

   async function playBroadcastItem(item) {
     document.getElementById('signalSourceLabel').textContent = item.source_label
     updateTicker(item)  // show next 2 items in ticker
     // Render avatar via existing avatar server call with item.script
     // When video ends: consumeAndPlay(item.id)
   }

   async function consumeAndPlay(consumedId) {
     const res = await fetch('/api/stage/consume-broadcast', {
       method: 'POST', body: JSON.stringify({consumed_id: consumedId})
     })
     const data = await res.json()
     if (data.next_item) await playBroadcastItem(data.next_item)
     else setTimeout(startBroadcast, 5000)  // retry in 5s
   }

   // Pre-render next segment while current plays (reduce dead air)
   // After current video starts playing, immediately request next avatar render
   // Store pre-rendered video blob, play instantly when current ends

F) Interrupt flow:
   When push-to-speak pressed:
   - document.querySelector('#broadcastVideo').pause() (or current video element)
   - volume fade to 20%
   - Record visitor question
   - POST /api/oracle/chat with question + {context: currentBroadcastTopic}
   - Render response via avatar server
   - Play response video
   - After response ends: show "Returning to broadcast in 3..." (3s countdown)
   - Resume: consumeAndPlay(null) to get next item without consuming current

=======================================================================
PART C — VALIDATION & COMMIT
=======================================================================

1. python3 -m py_compile services/stage_broadcast_service.py && echo OK
2. curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/stage  # must be 200
3. curl -s http://localhost:5000/api/stage/broadcast-queue  # must return JSON
4. python3 services/stage_broadcast_service.py  # run once, check queue populates
5. bash ~/protocol_pulse/regression_test.sh  # ZERO FAILs

COMMIT (3 separate commits):
  Commit 1: git add templates/stage.html && git commit -m "fix(stage): P0/P1 audit fixes — rate limiting, XSS, race condition, txDots, ARIA, polling"
  Commit 2: git add services/stage_broadcast_service.py && git commit -m "feat(broadcast): Stage broadcast service — signal-driven queue, 7 segment types, Haiku scripts"  
  Commit 3: git add core/routes.py && git commit -m "feat(broadcast): broadcast-queue, consume-broadcast, broadcast-status routes + rate limiting"
  git push

DO NOT TOUCH: video pipeline, assembler, tts_engine, overnight_render_loop, oracle/avatar_server.py
TOUCH ONLY: templates/stage.html, services/stage_broadcast_service.py, core/routes.py
