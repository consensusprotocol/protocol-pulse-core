Read PIPELINE_LAWS.md first. Then run a full cross-LLM audit of the Oracle Avatar server.

## CONTEXT
File: ~/protocol_pulse/oracle/avatar_server.py (984 lines)
The avatar server is "working" at the engine level (Wav2Lip generating) but broken in practice:

KNOWN ISSUES (from forensic analysis):
1. avg_latency: 48.92 seconds per generation — completely unusable for live Oracle briefings
2. apply_blink() creates BLACK OVAL ARTIFACTS on the face — known bug, fix = replace function body with `return frame` (no-op)
3. blinks_enabled: false, eye_landmarks_detected: false — blink system non-functional
4. /status route returns 404 — frontend calling a route that doesn't exist
5. GFPGAN face enhancer adding ~5-10s per frame batch, possibly causing artifacts
6. Jessica voice ID cgSgspJ2msm6clMCkdW9 — verify it's still valid in ElevenLabs
7. BATCH_SIZE=64 on GPU 1 — may be causing VRAM pressure

## AUDIT TASK
Run the cross-LLM audit using ~/protocol_pulse/utils/cross_llm_audit.py on the actual code.

If cross_llm_audit.py doesn't cover non-pipeline files, do a manual audit:
1. Read oracle/avatar_server.py in full
2. Read oracle/blink_engine.py
3. Read oracle/face_enhancer.py
4. Read oracle/model_registry.py

Then identify and fix ALL of these in priority order:

P0 - CRITICAL (fix first, these break everything):
- apply_blink() black oval artifact: find apply_blink_gradient() call in post_process_frames(), wrap with try/except that returns the original frame on ANY exception, OR just no-op it entirely per the known fix
- /status 404: add a /status route that returns same data as /health (frontend expects it)
- Latency: 48s is unacceptable. Target <10s. Investigate: is GFPGAN running per-frame? Should batch. Is BATCH_SIZE=64 causing OOM forcing CPU fallback? Check GPU utilization during generation.

P1 - HIGH:
- Blink system: if apply_blink creates artifacts, disable it entirely for now (enable_blinks=False in post_process_frames call) rather than crashing silently
- Face enhancer: if it's adding >5s latency, make it optional via config flag ENABLE_FACE_ENHANCEMENT=false default
- BATCH_SIZE: try 48 (proven at 134fps) instead of 64

P2 - MEDIUM:
- Add /status route aliasing /health
- Add request timeout (currently none — hangs forever on GPU stall)
- Add proper error responses with error codes instead of 500s

After all fixes:
1. Restart avatar server: pkill -f avatar_server; sleep 2; cd ~/protocol_pulse/oracle && nohup python3 avatar_server.py > logs/avatar_server.log 2>&1 &
2. Wait 15s for model load
3. Test: curl -X POST http://localhost:8200/generate -H 'Content-Type: application/json' -d '{"text":"Bitcoin is the hardest money ever created."}' -o /tmp/test_avatar.mp4
4. Check: curl http://localhost:8200/health — verify avg_latency < 15s
5. git add -A && git commit -m "fix(avatar): P0 blink artifact, /status 404, latency reduction, BATCH_SIZE=48" && git push