# STAGE BROADCAST SYSTEM — GOSPEL
## Feature: stage-broadcast
## Files: services/stage_broadcast_service.py, core/routes.py (/api/stage/broadcast-queue, /api/stage/consume-broadcast, /api/stage/broadcast-status), templates/stage.html

### What is being built
Transform protocolpulse.io/stage into a 24/7 autonomous Bitcoin broadcast station:
- Female avatar (Kokoro af_heart + Wav2Lip, already running in avatar_server.py port 8200)
- Always broadcasting — never idle, never dead air
- Signal-driven script queue: price alerts, thought leader tweets, Space Tap intercepts, metrics pulses, Nostr signals, article teasers
- Visitor can interrupt broadcast with push-to-speak (first-time modal like oracle_live.html)
- Avatar acknowledges visitor, responds, resumes broadcast
- ON AIR indicator, scrolling upcoming-topics ticker, session timer

### Architecture
stage_broadcast_service.py (cron every 5min):
  - Polls 6 data sources (BTC price, raw_tweets.json, x_spaces_scraper/cache/, DB articles, nostr output, mempool)
  - Generates 30-90s spoken scripts via Claude Haiku
  - Writes to broadcast_queue.json (file-based, TTL-managed)
  - Priority system: PRICE_ALERT=1, THOUGHT_LEADER=2, SPACE_TAP=2, ARTICLE_TEASER=3, METRICS_PULSE=3, NOSTR_SIGNAL=4, FILLER_INSIGHT=5

Frontend queue consumer (stage.html JS):
  - On load: GET /api/stage/broadcast-queue
  - Call avatar_server /generate with script
  - Play rendered video
  - On video end: POST /api/stage/consume-broadcast → get next
  - If queue empty: generate FILLER_INSIGHT inline
  - Push-to-speak: pause audio, record, POST /api/oracle/chat, play response, resume

### Audit focus areas
1. File-based queue race condition: two browser tabs both call consume-broadcast simultaneously, both get the same item — need atomic pop (file lock or SQLite)
2. Pre-render strategy: 10-13s Wav2Lip render latency between segments = dead air. Should pre-render next segment while current plays
3. Avatar server failure handling: if port 8200 is down, fall back to audio-only (Kokoro without Wav2Lip) or display static avatar image with audio
4. Cron every 5min for PRICE_ALERT: a 5% candle happens in seconds, not minutes. PRICE_ALERT needs a separate faster poll (WebSocket or 30s interval from frontend directly hitting /api/btc-price)
5. GPU contention: stage_broadcast_service.py runs Claude Haiku (CPU) but avatar_server uses cuda:1. If overnight render loop is also running on cuda:0/1, Wav2Lip during render may cause OOM. Need GPU availability check before rendering avatar during active video pipeline render
6. Mobile Safari push-to-speak: MediaRecorder API has known issues — getUserMedia may fail silently, need explicit error path with "use Chrome" fallback message
7. Script generation quality: Claude Haiku at 30-90s scripts — need strict prompt to prevent hallucinated price data. Must inject REAL current price/metrics into every script prompt
8. Interrupt UX: pausing audio but continuing video means avatar mouth keeps moving with no sound — jarring. Better: pause entire video element, show "INTERRUPTED" overlay
9. Session duration timer: client-side JS timer resets on page refresh — consider server-side session start timestamp stored in broadcast-status endpoint
10. FILLER_INSIGHT inline generation: calling Claude Haiku from frontend JS means exposing API pattern. Should be POST /api/stage/generate-filler (server-side) not direct from client
11. broadcast_queue.json grows unbounded if service runs but nobody consumes — need max queue depth (10 items) and TTL cleanup
12. Missing: no mechanism to inject BREAKING content immediately (e.g. BTC flash crash) ahead of queue — need priority bump / queue-jump for P1 events
