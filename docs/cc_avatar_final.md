Read PIPELINE_LAWS.md and ~/protocol_pulse/oracle/avatar_server.py in full before doing anything.

## NEW RULE IN EFFECT: Fix entirely before moving on. Verify live. No exceptions.

## FORENSIC FINDINGS - WHAT IS ACTUALLY BROKEN RIGHT NOW

From live logs:
1. GFPGAN is still loading at startup despite previous commit claiming to disable it
   Log proof: "2026-03-12 04:43:40 INFO GFPGAN loaded OK" — AFTER the "fix" commit
2. POST /generate returning HTTP 503 — server busy/locked, frontend gets error
3. A 50.48s audio clip (1517 frames) was processed — normal Oracle clips are 10-30s, this suggests no input length guard
4. blinks_enabled: False is correct but blink_engine is still imported

## YOUR TASKS - DO NOT SKIP ANY, DO NOT MARK DONE UNTIL VERIFIED LIVE

### TASK 1: Read the actual current code
Read these files completely:
- oracle/avatar_server.py
- oracle/face_enhancer.py  
- oracle/model_registry.py

Find EVERY place GFPGAN is imported, loaded, or called. List them all before touching anything.

### TASK 2: Kill GFPGAN completely
- Remove or comment out ALL gfpgan imports in avatar_server.py and face_enhancer.py
- In model_registry.py, find where GFPGAN model is loaded — comment it out entirely
- In face_enhancer.py, find enhance_frames_batch() — replace body with: return frames (no-op passthrough)
- In avatar_server.py, find every call to enhance_frames_batch() or any GFPGAN function — remove them
- Replace face enhancement with ONLY the existing sharpen_mouth_region() CV2 filter (no ML, instant)
- Verify: grep -r "gfpgan\|GFPGAN\|enhance_frames" oracle/ -- should return zero hits after

### TASK 3: Fix 503 busy lock
The server is single-threaded Flask. Find the generate endpoint — it uses a threading.Lock() or similar.
- Add a lock timeout: if lock is held >30s, return 503 with {"error":"busy","retry_after":5}  
- Add Flask threaded=True if not already set in app.run()
- Add a request queue limit: if more than 2 requests are queued, return 503 immediately instead of hanging

### TASK 4: Add input length guard  
In the generate endpoint, before processing:
- Get audio duration from the TTS response
- If audio > 30s, split into chunks of max 20s, process each, concatenate output videos
- This prevents 1500-frame processing that locks the server for 90s

### TASK 5: Restart and VERIFY
After all code changes:
1. Kill current process: pkill -f avatar_server.py; sleep 5
2. Start fresh: cd ~/protocol_pulse/oracle && nohup python3 avatar_server.py > logs/avatar_server.log 2>&1 &
3. Wait 20s for model load: sleep 20
4. Check logs — GFPGAN must NOT appear: grep -i "gfpgan" logs/avatar_server.log | head -5
5. Test health: curl http://localhost:8200/health -- verify avg_latency NOT carried over from old process
6. Run a TIMED live generate test with a 15-word sentence:
   time curl -s -X POST http://localhost:8200/generate -H 'Content-Type: application/json' -d '{"text":"Bitcoin fixes the broken money system one block at a time."}' -o /tmp/verify_avatar.mp4
7. Check output: ls -lh /tmp/verify_avatar.mp4 -- must be >50KB and valid mp4
8. Check latency: ffprobe /tmp/verify_avatar.mp4 2>&1 | grep Duration
9. Run a SECOND generate immediately after -- verify no 503

### TASK 6: Commit ONLY after live verification passes
git add oracle/ && git commit -m "fix(avatar): fully remove GFPGAN, fix 503 busy lock, add input guard - VERIFIED LIVE" && git push

### TASK 7: Report results
After committing, output:
- Time taken for generate test
- Video file size
- Video duration
- Whether GFPGAN appears anywhere in logs
- HTTP code of second consecutive generate call
- Current avg_latency_sec from /health

DO NOT commit until all 7 verification steps pass. DO NOT report done until you have run the live test and confirmed it works.