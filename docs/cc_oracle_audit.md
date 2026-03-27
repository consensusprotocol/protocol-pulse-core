Read ~/protocol_pulse/docs/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/docs/audits/oracle_avatar_audit/ directory for prior audit context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORACLE AVATAR — CROSS-LLM AUDIT + SURGICAL FIX
Two confirmed bugs. Audit the code. Reach consensus. Fix both.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIRMED BUGS FROM WATCHDOG LOG (4:45 AM ET):
BUG 1 — JOB POLLING 404:
  POST /oracle/chat → 200 (render job 03229d7834a34820 created)
  GET /oracle/job/03229d7834a34820/audio → 404
  The async render job starts but the client polling route is dead/missing.
  Oracle generates text + starts render, frontend never gets the video back.

BUG 2 — GPU SEMAPHORE 503:
  POST /generate → 503 repeatedly (3:41, 3:43, 3:45, 4:19 AM)
  render_semaphore locked by pipeline render (render_main on cuda:1)
  Avatar server and video pipeline fighting over same GPU.
  Stage gets 503s → "warming up" forever.

STEP 1 — AUDIT: REGISTER + FIRE CROSS-LLM AUDIT

Add to utils/cross_llm_audit.py FEATURE_MAP:
  "oracle-avatar-fix": ("PIPELINE_LAWS.md", "main")

Add to EXPLICIT_FILES:
  "oracle-avatar-fix": [
      "oracle/avatar_server.py",
      "core/blueprints/oracle.py",
  ]

Fire cycle 1 — each LLM answers these 4 questions independently:

Q1 — JOB POLLING: In avatar_server.py, find the route that handles
/oracle/job/<job_id>/audio. Does it exist? If yes, why does it return 404?
If no, where should it be added and what should it return?
Trace the full async job lifecycle from creation to delivery.

Q2 — GPU SEMAPHORE: The _render_semaphore is shared between the Oracle
interactive flow and the pipeline video render (daily_producer.py calls
localhost:8200/generate). How should GPU allocation be separated so
Oracle never gets 503 when the pipeline is running?
Options: separate CUDA device, priority queue, pre-emption, dedicated process.

Q3 — RENDER TIMEOUT: The brief render at 04:17 took >120s and timed out.
Wav2Lip on 4090 should render 415 chars in ~15s (from prior logs showing
14.3s video in 16.7s render). Why is it taking 120s+ now?
What changed? Check for GPU memory pressure, batch_size regression,
or blocking operation in the render path.

Q4 — ORACLE RESPONSE DELIVERY: Trace the complete flow from
POST /oracle/chat → text generation → async render → client polling.
Map every route involved. Identify every point where the chain can break.
What is the correct polling mechanism the frontend should use?

python3 utils/cross_llm_audit.py --feature oracle-avatar-fix
Save output to: docs/audits/oracle_avatar_fix_c1.json

STEP 2 — CYCLE 2 CROSS-EXAMINATION
python3 utils/cross_llm_audit.py --feature oracle-avatar-fix --cycle 2 --cycle1-results docs/audits/oracle_avatar_fix_c1.json
Save: docs/audits/oracle_avatar_fix_c2.json

STEP 3 — IMPLEMENT CONSENSUS FIXES

FIX 1 — JOB POLLING ROUTE:
Based on audit consensus, implement the correct /oracle/job/<id>/audio route.
It must: check job completion status, return video bytes when ready,
return {"status":"pending","eta":N} when still rendering,
return 404 only if job_id genuinely does not exist.

FIX 2 — GPU ISOLATION:
Assign avatar_server to cuda:2 (dedicated, not cuda:1 which pipeline uses).
In avatar_server.py find DEVICE or cuda assignment, change to cuda:2.
In daily_producer.py or assembler.py find the /generate call to localhost:8200,
add GPU device header or confirm it uses the server's assigned device.
Restart avatar_server after change.

FIX 3 — RENDER TIMEOUT ROOT CAUSE:
If audit identifies a regression in render speed, fix it.
If it's GPU memory pressure from pipeline, isolation above fixes it.
If batch_size degraded, restore to batch_size=48.

STEP 4 — END-TO-END VERIFY
Test the full Oracle flow:
  curl -X POST http://localhost:8200/oracle/speak
  # get session ID and job ID
  sleep 20
  curl http://localhost:8200/oracle/job/<job_id>/audio
  # must return video bytes, not 404

Test with pipeline running simultaneously:
  # ensure avatar returns 200 even when render_main is active

STEP 5 — QWEN_CONTEXT_BIBLE ENTRY
Document both bugs and fixes in ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md

STEP 6 — COMMIT
bash ~/protocol_pulse/regression_test.sh — 0 FAILs
git add -A
git commit -m "fix(oracle): job polling 404 + GPU isolation from pipeline — Oracle response delivery restored"
git push
