Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/cc_oracle_speed_implementation.md — T1.4 and T2.1 sections.
Read ~/protocol_pulse/oracle/avatar_server.py FULLY.
Read ~/protocol_pulse/templates/oracle_live.html lines 750-1250 (full JS section).
Read ~/protocol_pulse/oracle/oracle_cache_manager.py FULLY.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORACLE SPEED — PHASE 2: THINKING VIDEOS + SSE PUSH
T1.4: Pre-render "thinking" loop. T2.1: SSE replaces polling.
Expected: 8-15s → 4-8s perceived latency.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CROSS-LLM AUDIT FIRST (mandatory before any code):
Register in utils/cross_llm_audit.py:
  FEATURE_MAP["oracle-phase2"] = ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["oracle-phase2"] = [
      "oracle/avatar_server.py",
      "oracle/oracle_cache_manager.py",
      "templates/oracle_live.html",
  ]

Each LLM answers independently:

Q1 — THINKING VIDEO ARCHITECTURE:
Where in oracle_live.html does the video element exist?
When /oracle/chat returns a job_id, what does the frontend
currently do while waiting? What is the minimal change to make
it play a looping "thinking" video immediately on chat submit,
then cross-fade to the real video when job completes?
The thinking video should be a 3-4s loop of the avatar with
neutral animation (head movement, blinks) — no mouth movement,
no audio. Where should it be generated and stored?

Q2 — SSE ARCHITECTURE FOR FLASK:
Flask threaded mode with long-lived SSE connections: what is
the correct implementation pattern? generator + Response with
mimetype text/event-stream? What are the thread-safety concerns
with per-job event queues? How does render_async (which runs in
a thread pool) push events to the SSE generator?
Specifically: threading.Event per job, or a queue.Queue?

Q3 — SSE PAYLOAD DESIGN:
What events should the SSE stream send?
  - audio_ready: triggers client to fetch /oracle/job/<id>/audio
  - video_ready: triggers client to fetch /oracle/job/<id>
  - error: render failed
What should happen if client disconnects mid-stream?
How long should the SSE connection stay open?

Q4 — FRONTEND CROSS-FADE:
In oracle_live.html, how should the cross-fade from thinking
video to real video work without glitching?
CSS opacity transition? Two overlapping video elements?
What is the minimum thinking video duration before real video
arrives that makes the UX feel responsive vs jarring?

python3 utils/cross_llm_audit.py --feature oracle-phase2
Save C1 to docs/audits/oracle_phase2_c1.json
Cycle 2: python3 utils/cross_llm_audit.py --feature oracle-phase2 \
  --cycle 2 --cycle1-results docs/audits/oracle_phase2_c1.json
Save C2 to docs/audits/oracle_phase2_c2.json
Synthesize consensus on all 4 questions.

IMPLEMENT T1.4 — THINKING VIDEO (after audit):

1. Generate thinking video at avatar_server startup (after model load):
   In avatar_server.py, after warmup completes, generate:
   ~/protocol_pulse/oracle/cache/thinking_loop.mp4
   - 4 seconds, 30fps, 512x512
   - Avatar face with head movement + blinks ONLY
   - No mouth movement (use a silent wav of zeros)
   - No audio track in the file
   - Re-generate if file is missing or >7 days old

2. Serve it via new endpoint:
   @app.route("/oracle/thinking")
   def oracle_thinking():
       path = os.path.join(ORACLE_DIR, "cache", "thinking_loop.mp4")
       if os.path.exists(path):
           return send_file(path, mimetype="video/mp4")
       return jsonify({"error": "not ready"}), 404

3. In oracle_live.html JS:
   On chat submit (before fetch to /oracle/chat):
   - Set vid.src = avatarBase + "/oracle/thinking"
   - Set vid.loop = true
   - vid.play()
   - Show a subtle "thinking..." indicator

IMPLEMENT T2.1 — SSE PUSH (after audit):

1. Add per-job SSE event queue in avatar_server.py:
   _job_events = {}  # job_id -> threading.Event
   _job_events_lock = threading.Lock()

2. New SSE endpoint:
   @app.route("/oracle/job/<job_id>/stream")
   def oracle_job_stream(job_id):
       def generate():
           event = threading.Event()
           with _job_events_lock:
               _job_events[job_id] = event
           try:
               # Wait up to 60s for render to complete
               if event.wait(timeout=60):
                   job = _render_jobs.get(job_id, {})
                   if job.get("status") == "done":
                       yield f"event: video_ready\ndata: {job_id}\n\n"
                   elif job.get("audio_bytes"):
                       yield f"event: audio_ready\ndata: {job_id}\n\n"
                   else:
                       yield f"event: error\ndata: render_failed\n\n"
               else:
                   yield f"event: error\ndata: timeout\n\n"
           finally:
               with _job_events_lock:
                   _job_events.pop(job_id, None)
       return Response(generate(), mimetype="text/event-stream",
                       headers={"Cache-Control": "no-cache",
                                "X-Accel-Buffering": "no"})

3. In render_async, after storing audio and video in _render_jobs,
   signal the SSE event:
   with _job_events_lock:
       ev = _job_events.get(job_id)
       if ev:
           ev.set()

4. In oracle_live.html JS — replace polling with SSE:
   After /oracle/chat returns job_id:
   - Open: const evtSource = new EventSource(avatarBase + "/oracle/job/" + jobId + "/stream")
   - On audio_ready: fetch /oracle/job/<id>/audio, play audio, keep thinking loop running
   - On video_ready: fetch /oracle/job/<id>, cross-fade from thinking to real video
   - On error: stop thinking loop, show retry UI
   - evtSource.close() after video received
   - Keep existing polling as FALLBACK if EventSource not supported (check window.EventSource)

LIVE TESTING (all must pass before commit):

TEST 1: thinking_loop.mp4 exists and is valid
  ls -la ~/protocol_pulse/oracle/cache/thinking_loop.mp4
  ffprobe ~/protocol_pulse/oracle/cache/thinking_loop.mp4 2>&1 | grep "Duration"
  EXPECTED: ~4s duration

TEST 2: /oracle/thinking endpoint returns video
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/oracle/thinking
  EXPECTED: 200

TEST 3: SSE stream opens and stays alive
  curl -s --max-time 5 http://localhost:8200/oracle/job/test123/stream
  EXPECTED: connection opens, eventually returns "event: error\ndata: timeout"
  (since test123 doesn't exist)

TEST 4: Full conversation flow with SSE
  RESP=$(curl -s -X POST http://localhost:8200/oracle/chat \
    -H "Content-Type: application/json" \
    -d '{"text":"what is bitcoin","session_id":"phase2_test","avatar_source":"default"}')
  JOB_ID=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id','NONE'))")
  curl -s --max-time 45 http://localhost:8200/oracle/job/$JOB_ID/stream
  EXPECTED: receives "event: video_ready" within 20s

TEST 5: Verify no regression on /oracle/speak
  curl -s -X POST http://localhost:8200/oracle/speak \
    -H "Content-Type: application/json" -d '{"session_id":"test"}'
  EXPECTED: 200

Document all 5 test results in commit message.

COMMIT (only after all 5 pass):
bash ~/protocol_pulse/regression_test.sh — 0 FAILs
git add oracle/avatar_server.py oracle/oracle_cache_manager.py \
  templates/oracle_live.html \
  docs/audits/oracle_phase2_c1.json docs/audits/oracle_phase2_c2.json \
  utils/cross_llm_audit.py
git commit -m "perf(oracle): Phase 2 — thinking video loop + SSE push delivery
- T1.4: thinking_loop.mp4 generated at startup, served via /oracle/thinking
- T2.1: SSE endpoint /oracle/job/<id>/stream replaces 2s polling
- Frontend: thinking video plays immediately on chat submit
- Cross-fade from thinking → real video on SSE video_ready event
- Fallback: polling retained if EventSource not supported
- All 5 live tests passed: [paste results]
- Expected perceived latency: 8-15s → 4-8s"
git push
