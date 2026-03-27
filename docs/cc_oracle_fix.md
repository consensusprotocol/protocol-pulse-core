Read ~/protocol_pulse/oracle/avatar_server.py — find LOCK_TIMEOUT and the cache warmer semaphore logic.
Read ~/protocol_pulse/oracle/oracle_cache_manager.py — find the warmer loop and semaphore.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORACLE RESPONSE DELAY FIX — TARGET: <5s PERCEIVED RESPONSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIRMED ROOT CAUSE from live logs:
  [STARTUP] Lock timeout: 120s
  POST /generate → 503 (lock timeout)
  ReadTimeout after 120s

The LOCK_TIMEOUT=30 fix from a previous commit did not survive
service restart. The env var is not in .env, so it falls back
to the default in the code.

FIX 1 — HARD-CODE LOCK_TIMEOUT to 30s in avatar_server.py:
  Find: LOCK_TIMEOUT = int(os.environ.get("AVATAR_LOCK_TIMEOUT", "120"))
  OR:   LOCK_TIMEOUT = int(os.environ.get("AVATAR_LOCK_TIMEOUT", "30"))
  Change the default to 30 regardless. Also add to .env:
    echo "AVATAR_LOCK_TIMEOUT=30" >> /home/ultron/protocol_pulse/.env

FIX 2 — CACHE WARMER must IMMEDIATELY yield to interactive requests:
  In oracle_cache_manager.py find the warmer loop.
  The warmer should check before EACH render cycle:
    if interactive_request_pending: skip this cycle, sleep 5s, check again
  Add a threading.Event() that interactive requests set:
    INTERACTIVE_REQUEST_EVENT = threading.Event()
  In generate_inline() (avatar_server.py): set the event before acquiring lock
  In cache warmer: check event before each render, yield if set

FIX 3 — THINKING VIDEO must start playing IMMEDIATELY on user input:
  When user submits a question, the frontend should:
  1. Immediately show the thinking video (already implemented in Phase 2)
  2. Submit to /oracle/chat which queues the job
  3. Frontend polls /oracle/job/<id>/stream (SSE) for completion
  Verify this flow is working end-to-end:
    grep -n "thinking\|oracle/chat\|oracle/job\|EventSource" ~/protocol_pulse/templates/oracle_live.html | head -20
  If SSE is not being used (frontend still polling), switch to SSE.

FIX 4 — STARTUP LOGGING: add LOCK_TIMEOUT to startup log:
  Find the startup log line that says "Lock timeout: Xs"
  Make sure it reflects the actual value after fix.

VERIFICATION:
  Restart avatar server: tmux send-keys -t avatar_server "C-c" Enter && sleep 2 && tmux send-keys -t avatar_server "cd ~/protocol_pulse && python3 oracle/avatar_server.py" Enter
  Check startup log: grep "Lock timeout" ~/protocol_pulse/oracle/logs/watchdog.log | tail -3
  Expected: "Lock timeout: 30s"
  Test live: curl -s https://protocolpulse.io/oracle-live — page loads
  Then submit a test question via curl to /oracle/chat and time the response

COMMIT:
  git add oracle/avatar_server.py oracle/oracle_cache_manager.py
  git commit -m "fix(oracle): hard-code LOCK_TIMEOUT=30s + warmer yields to interactive requests"
  git push
