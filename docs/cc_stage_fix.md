Read ~/protocol_pulse/templates/stage.html — find how it loads the video, what it reads from latest.json or broadcast_queue.json.
Read ~/protocol_pulse/services/stage_broadcast_service.py — find where latest.json is written and if video_url is included.
Read ~/protocol_pulse/core/routes.py — find /api/stage/consume-broadcast and /api/stage/signal endpoints.

Current state from live diagnostics:
  broadcast_queue.json: 5 items, ORACLE_BRIEF items HAVE video_url
  latest.json: video_url = MISSING (None/not set)
  Stage shows: black screen with "TUNING SIGNAL..."
  Avatar server: healthy, uptime 10991s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE BLACK SCREEN + BANNER SPEED FIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1 — STAGE AUTO-PLAYS FIRST QUEUED VIDEO ON LOAD:
The stage.html shows "TUNING SIGNAL..." indefinitely because
latest.json has no video_url. The fix: on page load, stage.html
should immediately call /api/stage/consume-broadcast to get the
next queued item and play it.

In stage.html JS, find the initialization code (onload / DOMContentLoaded).
It should:
  1. Call GET /api/stage/consume-broadcast on page load
  2. If response has video_url → play it immediately
  3. If no video_url → show "TUNING SIGNAL..." and poll every 10s

Also fix latest.json writing: in stage_broadcast_service.py,
when writing latest.json, always include video_url if the item has one:
  latest_data = {
      "type": item.get("type"),
      "script": item.get("script"),
      "video_url": item.get("video_url", ""),  # MUST include this
      "timestamp": item.get("timestamp"),
      "brief_id": item.get("brief_id", "")
  }

FIX 2 — CONSUME-BROADCAST ENDPOINT returns video_url:
In core/routes.py find /api/stage/consume-broadcast.
Ensure it returns video_url from the queue item.
If the item has video_url, return it. The stage.html should
use it directly without re-rendering via avatar server.

FIX 3 — STAGE BANNER ANIMATION SPEED (mobile):
The rotating ticker banner spins too fast on mobile.
In stage.html find the CSS animation for the ticker/banner.
Look for: animation: ticker or marquee or scroll
Slow it down: if it's 10s change to 30s, if 20s change to 45s.
Add a media query for mobile:
  @media (max-width: 768px) {
      .stage-ticker, .ticker-band { animation-duration: 45s !important; }
  }

VERIFICATION:
  curl -s --max-time 5 http://localhost:5000/stage — should 200
  curl -s --max-time 5 http://localhost:5000/api/stage/consume-broadcast — should return JSON with video_url
  Check stage.html loads video on open in browser

COMMIT:
  git add templates/stage.html services/stage_broadcast_service.py core/routes.py
  git commit -m "fix(stage): auto-play queued video on load + latest.json video_url + banner speed"
  git push
