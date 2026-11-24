# Batch 117 (ruling 133 R16, service heartbeats), cycle 1

Seats: qwen27b (Heimdall, effort medium, 249.7 s) and gptoss (Heimdall, effort medium, 17.8 s). No Grok (Heimdall only).

- gptoss: PASS, no findings, confidence 0.0. Its reasoning stops before tracing the code: recorded, carries no weight.
- qwen27b F1 (low), session_watchdog.py: float(pass_at) sat outside the guarded read; a corrupted pass_at would end every
  heartbeat check of that pass. ACCEPTED, fixed (pass_at parsed inside the try; AttributeError caught for a non-dict
  record), with a test (test_an_unreadable_record_reads_as_missing_and_never_ends_the_check).
- qwen27b F2 (low), judge_serve.py: the patch works only if local_judge.main looks serve_once up at call time. VERIFIED in
  the code: local_judge.py:330 `n = serve_once(log=...)`, a bare module-global name read each pass. A test now runs the
  REAL local_judge.main through the launcher and sees the pass mark
  (test_the_real_local_judge_main_calls_the_wrapped_serve_once).
