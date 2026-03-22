STAGE BROADCAST SYSTEM — SPEC FOR CROSS-LLM AUDIT

SYSTEM: Protocol Pulse Stage — autonomous 24/7 Bitcoin broadcast station.
AVATAR: Female (Kokoro af_heart voice, Wav2Lip lip-sync, proven working in avatar_server.py)
STACK: Flask/Python backend, vanilla JS frontend, avatar_server.py port 8200

ARCHITECTURE:
─────────────
stage_broadcast_service.py (background worker, cron every 5 min)
  - Polls 6 live signal sources
  - Generates 30-90s spoken scripts via Claude Haiku
  - Pushes to broadcast_queue.json (file-based queue)
  - Manages TTL/expiry of stale items

broadcast_queue.json schema:
  [{id, type, priority(1-5), script, source_label, topic_preview, generated_at, expires_at}]

Flask routes (core/routes.py):
  GET /api/stage/broadcast-queue   → returns next 3 queued items
  POST /api/stage/consume-broadcast → pops consumed item, returns next
  GET /api/stage/broadcast-status  → {live, current_topic, queue_depth, session_duration_sec}

stage.html frontend changes:
  - ON AIR pulsing indicator + signal source label
  - Broadcast ticker (scrolling upcoming topics)
  - Session timer
  - Queue consumer loop: fetch → render avatar video → play → consume → repeat
  - Never dead air: if queue empty, generate FILLER_INSIGHT inline via direct Haiku call
  - Push-to-speak interrupt (copy from oracle_live.html): first-time modal, mic permission,
    audio fade to 20% while listening, respond in character, resume broadcast

SIGNAL TYPES (priority order):
  1. PRICE_ALERT (pri=1): BTC moves >0.8% in 15min
  2. THOUGHT_LEADER (pri=2): New tweet from Priority-1 handle (saylor, natbrunell, jack, etc)
  3. SPACE_TAP (pri=2): New live X Spaces clip from x_spaces_scraper cache
  4. ARTICLE_TEASER (pri=3): Article published in last 30min
  5. METRICS_PULSE (pri=3): Every 20min — hashrate, FNG, mempool, block height
  6. NOSTR_SIGNAL (pri=4): Trending nostr topic from nostr_monitor output
  7. FILLER_INSIGHT (pri=5): Fallback — rotates 20 cypherpunk/Bitcoin insights

EXISTING INFRASTRUCTURE TO REUSE:
  - avatar_server.py /generate endpoint (Wav2Lip + Kokoro af_heart) — DO NOT change
  - /api/oracle/chat endpoint — reuse for interrupt responses
  - Kokoro af_heart already on cuda:1, 2-3s latency
  - stage_brief_pipeline.py — reference for data fetching patterns
  - raw_tweets.json — Nitter-scraped, 2505 tweets, fresh daily
  - x_spaces_scraper/cache/ — Space Tap clips
  - /api/btc-price — live BTC price endpoint

AUDIT QUESTIONS FOR LLMs:
1. Is the file-based queue (broadcast_queue.json) robust enough or does it need SQLite?
2. Race condition risk: multiple browser tabs all consuming from queue simultaneously?
3. Avatar render latency: 2-3s for Kokoro + ~8-10s for Wav2Lip = 10-13s between segments. Is there a pre-render strategy?
4. What happens if avatar_server is down? Graceful degradation?
5. Is cron-every-5-min sufficient for PRICE_ALERT responsiveness?
6. The interrupt flow pauses audio but not video — will lip-sync look wrong?
7. Memory/GPU impact of running broadcast_service.py every 5min alongside render loop?
8. Should FILLER_INSIGHT be pre-generated (cache of 20 rendered videos) vs generated on-demand?
9. Security: /api/stage/consume-broadcast should it be authenticated?
10. Mobile UX: push-to-speak on mobile Safari — known MediaRecorder issues?
