Read ~/protocol_pulse/oracle/avatar_server.py lines 1699-1730 (oracle/voice endpoint).
Run: grep -n "GREETING\|preload\|warm\|cache\|startup" ~/protocol_pulse/oracle/avatar_server.py | head -15
Run: tail -30 ~/protocol_pulse/logs/avatar_server.log 2>/dev/null | grep -i "error\|timeout\|slow\|mobile" | head -10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORACLE MOBILE FIX — Pre-render greeting, fix delays
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROOT CAUSE: On mobile, the very first oracle request triggers a cold 
GPU render of the greeting video (30+ seconds). Fix: pre-render the 
greeting video at server startup and serve it from cache.

FIX 1 — Pre-render greeting video at startup
In avatar_server.py, at startup (after the Flask app is initialized),
add a background thread that pre-renders the standard greeting:

  GREETING_TEXT = "Hey. I'm Satomi — your Protocol Pulse intelligence anchor. On-chain, macro, geopolitical. What can I help you with?"
  _GREETING_CACHE_PATH = '/tmp/satomi_greeting_cache.mp4'

  def _prerender_greeting():
      """Pre-render greeting video at startup so first mobile request is instant."""
      import time
      time.sleep(30)  # Wait for GPU to be ready
      try:
          if not os.path.exists(_GREETING_CACHE_PATH):
              logger.info('[STARTUP] Pre-rendering greeting video...')
              # Call our own TTS + render pipeline
              # (use existing render_avatar_video or similar internal function)
              result = render_greeting_cached(GREETING_TEXT, _GREETING_CACHE_PATH)
              if result:
                  logger.info(f'[STARTUP] Greeting pre-rendered: {os.path.getsize(_GREETING_CACHE_PATH)/1024:.0f}KB')
      except Exception as e:
          logger.warning(f'[STARTUP] Greeting pre-render failed: {e}')
  
  import threading
  threading.Thread(target=_prerender_greeting, daemon=True).start()

FIX 2 — Serve cached greeting instantly
In the /oracle/voice endpoint or wherever GREETING is handled:
  If the text matches the standard greeting, serve from cache immediately
  without GPU render:
  
  if text.strip() == GREETING_TEXT and os.path.exists(_GREETING_CACHE_PATH):
      logger.info('[GREETING] Serving from cache (instant)')
      return send_file(_GREETING_CACHE_PATH, mimetype='video/mp4')

FIX 3 — Reduce oracle response time for mobile
The oracle takes 10-30s because Chatterbox TTS + Wav2Lip both run sequentially.
Find where these are called and ensure:
  a) TTS runs first, returns audio quickly
  b) Wav2Lip runs on the audio
  c) Add a timeout: if render takes >25s, return audio-only fallback

In the oracle response pipeline, add:
  MAX_RENDER_SECONDS = 25
  # If render takes longer, return audio-only with static image

FIX 4 — Oracle page title and remaining Oracle→Satomi text
  grep -n "Oracle\|oracle" ~/protocol_pulse/templates/oracle_live.html | grep -v "route\|url\|class.*oracle\|id.*oracle\|/oracle" | head -10
  Change any visible "Oracle" text to "Satomi"
  The page title should read "Satomi · Protocol Pulse"

VERIFY:
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:8200/health
  # 200
  ls -la /tmp/satomi_greeting_cache.mp4 2>/dev/null
  # Should exist after 30s startup pre-render

COMMIT:
  git add oracle/avatar_server.py templates/oracle_live.html
  git commit -m "fix(oracle-mobile): pre-render greeting cache, reduce latency, Satomi rename complete"
  git push
