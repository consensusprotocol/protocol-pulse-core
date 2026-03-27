Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/services/stage_brief_pipeline.py FULLY.
Read ~/protocol_pulse/services/stage_broadcast_service.py FULLY.
Read ~/protocol_pulse/templates/stage.html lines 1380-1550 (JS broadcast loop).
Read ~/protocol_pulse/core/routes.py lines 11014-11130 (stage API routes).
Read ~/protocol_pulse/oracle/avatar_server.py lines 440-490 (post_process_frames, blink).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE + ORACLE BLINK — FIX BOTH. LIVE EXTERNAL TESTS ONLY.
Tests MUST use https://protocolpulse.io — NOT localhost.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIRMED BUGS (diagnosed, fix these):

BUG 1 — Stage queue items have no video_url
The broadcast queue in broadcast_queue.json contains items with
script text but NO video_url field. The stage.html consumeAndPlay()
function expects an item with a video URL to play. Without it the
page gets stuck "warming".

The fix: stage_brief_pipeline.py already generates an MP4 and saves
it to video_pipeline_v3/data/stage_briefs/brief_YYYYMMDD_HHMM.mp4
When adding the item to broadcast_queue.json, include:
  "video_url": "/data/stage_briefs/brief_20260324_2351.mp4"

Also check stage_broadcast_service.py — when it generates
queue items from scripts (not full renders), those have no video.
Those text-only items need to trigger a render OR be excluded from
the queue until a video exists.

BUG 2 — /data/stage_briefs/ returns 404 externally
The MP4 files exist at:
  ~/protocol_pulse/video_pipeline_v3/data/stage_briefs/
But there is NO Flask route serving /data/stage_briefs/*.
Add a route to routes.py:
  @app.route('/data/stage_briefs/<path:filename>')
  def serve_stage_brief(filename):
      return send_from_directory(
          os.path.join(BASE, 'video_pipeline_v3', 'data', 'stage_briefs'),
          filename)
Where BASE = ~/protocol_pulse

BUG 3 — Oracle avatar blinks not visible
Health check shows blinks_enabled: true and blink_config present.
Check post_process_frames() in avatar_server.py — specifically
whether apply_blink_gradient is being called and what it does.
The prior session noted apply_blink() creates black oval artifacts
and suggested replacing with return frame no-op. Check if that
no-op is in place and that's why blinks aren't visible.
If apply_blink_gradient is a no-op, restore the proper blink
implementation or find why it produces artifacts and fix that.
The blink should be visible — a subtle eye closure every 2.5-5s.

MANDATORY — READ THE STAGE.HTML consumeAndPlay() LOGIC:
Trace exactly what fields it expects in next_item.
Confirm what happens when video_url is absent.
Fix the frontend to handle missing video gracefully AND
fix the backend to always include video_url when a video exists.

LIVE EXTERNAL TESTS (use https://protocolpulse.io — NOT localhost):

TEST 1 — Video URL accessible externally:
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" \
    https://protocolpulse.io/data/stage_briefs/brief_20260324_2351.mp4
  EXPECTED: 200 (not 404)

TEST 2 — Consume returns video_url:
  curl -s -X POST https://protocolpulse.io/api/stage/consume-broadcast \
    -H "Content-Type: application/json" -d '{"consumed_id":null}' \
    | python3 -m json.tool | grep video_url
  EXPECTED: "video_url" field present with valid path

TEST 3 — Generate a fresh brief and verify it queues with video:
  python3 ~/protocol_pulse/services/stage_brief_pipeline.py
  curl -s https://protocolpulse.io/api/stage/broadcast-status | python3 -m json.tool
  EXPECTED: queue_depth increases, item has video_url

TEST 4 — Stage page no longer stuck:
  curl -s https://protocolpulse.io/stage | grep -c "warming"
  EXPECTED: 0 (no warming references visible in initial HTML)

TEST 5 — Oracle blink visible:
  Generate a 10s oracle video and check frame count of blink events:
  curl -s -X POST http://localhost:8200/oracle/speak \
    -H "Content-Type: application/json" \
    -d '{"session_id":"blink_test"}' -o /tmp/blink_test.mp4
  python3 -c "
import subprocess
r = subprocess.run(['ffprobe','-v','error','-count_frames',
  '-select_streams','v:0','-show_entries','stream=nb_read_frames',
  '-of','default=nokey=1:noprint_wrappers=1','/tmp/blink_test.mp4'],
  capture_output=True, text=True)
print('frames:', r.stdout.strip())
"
  # Then visually inspect: does post_process_frames log blink events?
  tail -20 ~/protocol_pulse/oracle/logs/watchdog.log | grep -i blink

All 5 tests must pass before commit.
Document results in commit message.

COMMIT:
bash ~/protocol_pulse/regression_test.sh — 0 FAILs
git add core/routes.py services/stage_brief_pipeline.py \
  services/stage_broadcast_service.py oracle/avatar_server.py
git commit -m "fix(stage+oracle): stage video serving + queue video_url + oracle blinks
- Added /data/stage_briefs/<file> route to serve MP4s externally
- stage_brief_pipeline.py now includes video_url in queue items
- text-only queue items excluded until render completes
- Oracle blinks restored/fixed
- All 5 EXTERNAL tests passed via https://protocolpulse.io"
git push
