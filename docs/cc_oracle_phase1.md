Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/cc_oracle_speed_implementation.md FULLY — this is the audit you implement from.
Read ~/protocol_pulse/oracle/avatar_server.py FULLY.
Read ~/protocol_pulse/oracle/model_registry.py FULLY.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORACLE SPEED — PHASE 1 IMPLEMENTATION
3 surgical changes. Expected: 15-25s → 8-15s render time.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY: Cross-LLM audit already done (oracle-speed, f987db8d).
These 3 fixes are consensus-agreed. Implement exactly as specified.
No new audit needed — execute from the existing roadmap.

FIX T1.1 — VIDEO ENCODING PRESET REGRESSION [P0 CRITICAL]
File: oracle/avatar_server.py
Find ALL occurrences of: "-preset", "medium"
Replace with: "-preset", "ultrafast"
Find ALL occurrences of: "-crf", "18"
Replace with: "-crf", "23"

The audit identified this as a confirmed regression from the documented
spec (header line 12: "CRF 28, preset ultrafast"). Saves 4-8s per render.

Verify with grep after change:
  grep -n "preset\|crf" oracle/avatar_server.py | grep -v "#"
  Should show "ultrafast" and "23" — no "medium" or "18" remaining.

FIX T1.2 — COMBINE TTS FFMPEG POST-PROCESSING [P1 HIGH]
File: oracle/avatar_server.py lines ~653-687

Find the two sequential subprocess calls for:
  1) audio resample (24kHz → 16kHz)
  2) loudnorm to -14 LUFS

Replace with single ffmpeg command:
  ffmpeg -y -loglevel error -i {input} \
    -af "aresample=16000,loudnorm=I=-14:TP=-1.5:LRA=11" \
    -ac 1 {output}

Eliminates one subprocess spawn + intermediate temp file disk I/O.
Read the exact current code carefully before changing — preserve all
temp file cleanup logic and error handling.

FIX T1.3 — ADD torch.compile TO WAV2LIP [P1 HIGH]
File: oracle/model_registry.py

After the line: model = model.to(DEVICE).half().eval()
Add:
  try:
      import torch._dynamo
      torch._dynamo.config.suppress_errors = True
      model = torch.compile(model, mode="reduce-overhead")
      logger.info("Wav2Lip compiled with torch.compile (reduce-overhead)")
  except Exception as e:
      logger.warning(f"torch.compile unavailable, running eager: {e}")

The try/except ensures graceful fallback if compile fails.
First inference will be slower (JIT warmup) — existing 5-frame warmup
at startup already handles this.

LIVE TESTING (MANDATORY — all must pass before commit)
After changes, restart avatar_server and run all 5 tests:

TEST 1: curl -s http://localhost:8200/health | python3 -m json.tool | grep status
EXPECTED: "status": "ok"

TEST 2: Time a full oracle speak request:
  time curl -s -X POST http://localhost:8200/oracle/speak \
    -H "Content-Type: application/json" \
    -d '{"session_id": "phase1_test_001"}' > /tmp/test_speak.mp4
  EXPECTED: Returns video. Time should be measurably faster than before.

TEST 3 — Benchmark vs baseline:
  Before: encoding was medium/CRF18
  After: encoding is ultrafast/CRF23
  Verify grep confirms no "medium" or "crf 18" in avatar_server.py

TEST 4 — torch.compile loaded:
  Check startup logs for: "Wav2Lip compiled with torch.compile"
  tail -20 ~/protocol_pulse/oracle/logs/watchdog.log | grep compile

TEST 5 — Full conversation flow:
  RESP=$(curl -s -X POST http://localhost:8200/oracle/chat \
    -H "Content-Type: application/json" \
    -d '{"text":"what is bitcoin price today","session_id":"phase1_test_002","avatar_source":"default"}')
  JOB_ID=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id','NONE'))")
  echo "JOB: $JOB_ID"
  sleep 20
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/oracle/job/$JOB_ID)
  echo "VIDEO STATUS: $HTTP"
  EXPECTED: 200 (video ready within 20s — was 25s+ before)

Document all 5 test results in commit message.

COMMIT (only after all 5 tests pass):
bash ~/protocol_pulse/regression_test.sh — 0 FAILs
git add oracle/avatar_server.py oracle/model_registry.py
git commit -m "perf(oracle): Phase 1 speed — ultrafast encoding, combined ffmpeg, torch.compile
- T1.1: -preset ultrafast + CRF 23 (was medium + CRF 18) — saves 4-8s
- T1.2: single ffmpeg resample+loudnorm (was 2 sequential subprocesses)
- T1.3: torch.compile reduce-overhead on Wav2Lip model
- All 5 live tests passed: [paste results here]
- Expected render time: 15-25s → 8-15s"
git push
