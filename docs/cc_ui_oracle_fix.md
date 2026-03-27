Read ~/protocol_pulse/templates/oracle_live.html FULLY.
Read ~/protocol_pulse/templates/stage.html lines 160-200 (stage avatar wrap CSS).
Read ~/protocol_pulse/oracle/avatar_server.py lines 200-220 (semaphore) and 1240-1260 (generate_inline).
Read ~/protocol_pulse/oracle/oracle_cache_manager.py lines 1-50 (warmer semaphore).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3 SURGICAL FIXES — UI + ORACLE RESPONSIVENESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1 — REMOVE STATIC IMAGE OVERLAY FROM ORACLE VIDEO WRAP
In oracle_live.html, find this CSS rule on .video-wrap:
  background: #050508 url('/static/oracle_avatar.png') center/cover no-repeat;
Change to:
  background: #050508;
The static image bleeds through behind the live video during
load. Black background only. The gate/login screen has its own
static image (line ~634) which is correct and should stay.
Also check if the <video> element has width:100% height:100%
object-fit:cover — it must fill the container completely.

FIX 2 — REMOVE STATIC IMAGE OVERLAY FROM STAGE AVATAR WRAP
In stage.html, find this CSS (around line 166):
  #06080f url('/static/img/oracle_avatar_static.png') center top / cover no-repeat;
Change to:
  background: #06080f;
Same fix — stage avatar wrap should be dark background only,
no static image showing through the live video.

FIX 3 — ORACLE NOT RESPONDING AFTER USER INPUT
Root cause: LOCK_TIMEOUT=120s. When cache warmer holds the GPU
during one of its 11 render cycles (~90s each), and a user
sends a chat message, generate_inline() tries to acquire the
semaphore with timeout=120s. The warmer finishes in ~90s but
the 120s wait causes the frontend to time out its own polling
and show failure before the render even starts.

The WARMER_SEMAPHORE fix is in oracle_cache_manager.py but
verify it is actually working:
  grep -n "WARMER_SEMAPHORE\|deferred" oracle/oracle_cache_manager.py

If WARMER_SEMAPHORE exists and the "deferred" log message
appears, the warmer IS yielding. But the generate_inline
timeout is still 120s — reduce LOCK_TIMEOUT to 30s so that
if GPU is busy, the user gets a fast "try again" response
rather than a 2-minute hang.

In avatar_server.py:
  Find: LOCK_TIMEOUT = int(os.environ.get("AVATAR_LOCK_TIMEOUT", "120"))
  Change default to: "30"

Also verify the SSE stream from Phase 2 (cb190342) is working:
  grep -n "job.*stream\|SSE\|EventSource\|event_queue" oracle/avatar_server.py | head -10
If SSE endpoint exists, the frontend should be using it.
Check oracle_live.html JS — is it using EventSource or still polling?
  grep -n "EventSource\|stream\|SSE" templates/oracle_live.html | head -10

If frontend is still polling (not using SSE), that's why it
appears unresponsive — the poll window closes before the render.
If SSE is in place, find why it's not being triggered.

LIVE TESTS (external via https://protocolpulse.io):

TEST 1 — Static overlay gone:
  Load https://protocolpulse.io/oracle-live in browser
  Before avatar speaks: confirm NO static image visible
  Only black background during video load

TEST 2 — Oracle responds to follow-up:
  After welcome line, submit "what is the bitcoin price today"
  EXPECTED: response starts within 30s, NOT a 2-min hang

TEST 3 — Stage background clean:
  curl -s https://protocolpulse.io/stage | grep oracle_avatar_static
  EXPECTED: 0 matches (static image reference removed)

TEST 4 — Gunicorn reload to pick up template changes:
  kill -HUP $(pgrep -f "gunicorn.*app:app" | grep -v golds) 2>/dev/null
  sleep 5
  curl -s -o /dev/null -w "%{http_code}" https://protocolpulse.io/oracle-live
  EXPECTED: 200

All 4 tests must pass. Commit only after.

COMMIT:
git add templates/oracle_live.html templates/stage.html oracle/avatar_server.py
git commit -m "fix(ui+oracle): remove static image overlays + reduce lock timeout to 30s
- oracle_live.html: .video-wrap background = #050508 only (no static PNG)
- stage.html: stage avatar wrap background = #06080f only (no static PNG)
- avatar_server.py: LOCK_TIMEOUT default 120s -> 30s (fast fail for user)
- Verified SSE endpoint wired + frontend using EventSource
- All 4 external tests passed"
git push
