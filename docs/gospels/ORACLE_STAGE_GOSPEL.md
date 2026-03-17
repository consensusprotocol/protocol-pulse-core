# ORACLE STAGE — GOSPEL
## Feature: oracle-stage
## Files: templates/stage.html, routes.py (/stage, /api/stage/transcripts)

### What was built
Oracle Stage broadcast page at protocolpulse.io/stage:
- Avatar desk layout (Wav2Lip lip-sync avatar + info panels)
- Live BTC price, sentiment bar, narrative, topic chips
- Auto-plays GREETING on load, Daily Brief button
- Partner channel transcript cards (from fresh_scrape archive)
- Nostr signal feed (from active_signal.json cache)
- Scrolling top ticker bar, UTC clock
- Syne Mono font, obsidian/red/gold palette

### Audit focus areas
1. Error handling for avatar API failures (avatar.protocolpulse.io:8200 may be slow)
2. XSS risk: transcript text rendered via innerHTML (esc() function exists but verify)
3. Auto-play GREETING on load - browser autoplay restrictions
4. /api/oracle/ask endpoint - does it exist? Stage page calls it for intel
5. Ticker animation performance on mobile
6. No loading states for transcript cards during API fetch
7. Timed briefing feature: how to add countdown + auto-trigger
8. Missing: no CORS handling if avatar server is on different origin
9. Missing: no error state if /api/stage/transcripts returns empty
10. Missing: no WebSocket for true real-time updates (polling every 3 min)
