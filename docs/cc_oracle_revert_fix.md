Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/oracle/avatar_server.py fully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORACLE AVATAR — REVERT BAD AUDIT FIX + LIVE TESTING MANDATE
The previous cross-LLM audit introduced a broken semaphore fix
that silenced the Oracle. Revert it. Test live. Prove it works.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTEXT — WHAT BROKE:
Commit 2c542a0d changed oracle_speak() from:
  # Old (correct):
  if not _render_semaphore.acquire(timeout=5):
      return jsonify({"error": "GPU busy"}), 503
  _render_semaphore.release()  # release, generate_inline re-acquires
  return generate_inline(text)

To:
  # New (BROKEN — private attribute access, not thread-safe):
  if _render_semaphore._value == 0:
      return jsonify({"error": "GPU busy"}), 503
  return generate_inline(text)  # missing release before this

Result: Oracle accepts requests but generate_inline never gets semaphore
properly, causing infinite render loop. Oracle shows "rendering" forever.

STEP 1 — CROSS-LLM AUDIT (mandatory before touching code)
Register in utils/cross_llm_audit.py:
  FEATURE_MAP["oracle-speak-revert"] = ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["oracle-speak-revert"] = ["oracle/avatar_server.py"]

Each LLM must answer:
Q1: Is _render_semaphore._value safe to read directly in a threaded Flask app?
    What is the correct thread-safe way to check semaphore availability?
Q2: The old code did acquire+release before generate_inline. generate_inline
    then re-acquires. Is this pattern correct? What race window does it create?
Q3: What is the minimal correct fix — preserve the intent (bail if GPU busy)
    without the private attribute access and without blocking generate_inline?
Q4: After the fix is applied, what exact curl commands prove Oracle speaks?

python3 utils/cross_llm_audit.py --feature oracle-speak-revert
Save: docs/audits/oracle_speak_revert_c1.json
Cycle 2: python3 utils/cross_llm_audit.py --feature oracle-speak-revert \
  --cycle 2 --cycle1-results docs/audits/oracle_speak_revert_c1.json
Save: docs/audits/oracle_speak_revert_c2.json
Synthesize consensus answer to all 4 questions.

STEP 2 — IMPLEMENT CONSENSUS FIX
Based on audit consensus, fix oracle_speak() in oracle/avatar_server.py.
The fix must:
  a) Not use _render_semaphore._value (private, not thread-safe)
  b) Not block generate_inline from acquiring the semaphore
  c) Bail fast if GPU genuinely busy
  d) Be <= 6 lines of change

Recommended pattern (verify with audit consensus first):
  acquired = _render_semaphore.acquire(timeout=5)
  if not acquired:
      return jsonify({"error": "GPU busy warming cache — try again shortly",
                      "status": "warming", "retry_after": 30}), 503
  _render_semaphore.release()  # release immediately, generate_inline re-acquires
  return generate_inline(text)

Also fix line 1563 which has the same _value access pattern:
  grep -n "_render_semaphore._value" oracle/avatar_server.py
  Fix each occurrence with the thread-safe equivalent.

STEP 3 — RESTART AVATAR SERVER
After code change:
  pkill -f avatar_server.py 2>/dev/null
  sleep 3
  cd ~/protocol_pulse/oracle && python3 avatar_server.py > ~/protocol_pulse/oracle/logs/watchdog.log 2>&1 &
  sleep 8
  curl -s --max-time 5 http://localhost:8200/health | python3 -m json.tool
  # Must return {"status": "ok", "model_loaded": true}

STEP 4 — LIVE END-TO-END TESTS (ALL MUST PASS BEFORE COMMIT)

TEST 1 — Health check:
  curl -s http://localhost:8200/health | python3 -m json.tool | grep status
  EXPECTED: "status": "ok"
  FAIL = do not commit

TEST 2 — Oracle speak (pre-cached response):
  curl -s -X POST http://localhost:8200/oracle/speak \
    -H "Content-Type: application/json" \
    -d '{"session_id": "test_speak_001"}'
  EXPECTED: HTTP 200 with JSON containing job_id or video bytes
  FAIL = do not commit, debug first

TEST 3 — Oracle chat (full flow):
  RESPONSE=$(curl -s -X POST http://localhost:8200/oracle/chat \
    -H "Content-Type: application/json" \
    -d '{"text": "what is bitcoin", "session_id": "test_chat_001", "avatar_source": "default"}')
  echo $RESPONSE | python3 -m json.tool
  JOB_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id','NONE'))")
  echo "JOB_ID: $JOB_ID"
  EXPECTED: job_id present in response
  FAIL = do not commit

TEST 4 — Job polling (verify render completes):
  sleep 20
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/oracle/job/$JOB_ID
  EXPECTED: 200 (video ready) or 202 (still rendering, acceptable)
  404 = FAIL, do not commit

TEST 5 — Semaphore not locked after request:
  # After tests complete, verify semaphore is free
  curl -s -X POST http://localhost:8200/oracle/speak \
    -H "Content-Type: application/json" \
    -d '{"session_id": "test_speak_002"}'
  EXPECTED: 200 (not 503 "GPU busy")
  503 = semaphore stuck, FAIL

Document ALL test results in commit message. If ANY test fails, debug and
fix before committing. Do not commit broken code.

STEP 5 — VERIFY WATCHDOG LOG
tail -20 ~/protocol_pulse/oracle/logs/watchdog.log
Look for any ERROR lines. All oracle speak/chat requests should show 200.
No 503s, no "GPU busy", no "render timed out".

STEP 6 — COMMIT ONLY AFTER ALL TESTS PASS
bash ~/protocol_pulse/regression_test.sh — 0 FAILs required
git add oracle/avatar_server.py docs/audits/oracle_speak_revert_c1.json \
  docs/audits/oracle_speak_revert_c2.json utils/cross_llm_audit.py
git commit -m "fix(oracle): revert broken semaphore fix, restore thread-safe acquire/release pattern
- Reverts _render_semaphore._value (private attr, not thread-safe)
- Restores acquire(timeout=5) + release() before generate_inline
- All 5 live endpoint tests passing: health, speak, chat, job poll, semaphore free
- Cross-LLM audit: 2 cycles, consensus confirmed correct pattern"
git push

CRITICAL REMINDER: This spec exists because the previous audit fixed code
theoretically but broke it practically. Every fix must be tested LIVE
against the running server before committing. The test results must be
documented in the commit message. No exceptions.
