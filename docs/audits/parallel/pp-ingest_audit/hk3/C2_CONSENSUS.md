# The hook pass mine-hook/3 (the orchestrator's 08:15 ruling 2), cycle 2: consensus

Reviewers (Heimdall), on the whole change (197b35ec..cb511908) with C1_CONSENSUS.md and CONTEXT_C2.md:
qwen3.8-27b (224 s, $0.023): "Yes with conditions"; glm-5.3-flash (292 s, $0.006): "Yes, with one condition" (P0 /
P1 none); muse-spark-open (428 s, $0.031): "Yes, with one condition" (P0 none). Cycle 2: $0.060. All three verified
the cycle 1 fixes (check_roles with flagcheck, the split note, the adapter test, the design's miner_route).

## Fixed: the one condition all three named (a test that fails on cb511908)
- C2-1 (qwen P1, muse P1-1, glm P2-1): a spotlight question that RAISED (a crash, not a model failure: those are
  AllBackendsFailed, handled inside mine_video) after the hook question had answered discarded that pass's hook rows;
  the retry re-asked both (free from the reply cache), and a deterministic crash would have looped without ever
  writing the hook rows. The spotlight question now runs in its own try / except: a crash is an event
  (`spotlight_crash`, with the traceback), the hook rows are written, the pass completes with its note ("the
  spotlight question crashed: ...") and is recorded as "mine-hook/3 (spotlight crashed)", so `hooks --rerun` asks it
  again; it does not loop. A ContractUnavailable still makes the whole pass wait, as before. Model failures of the
  spotlight question keep the joint retry (the hook question's replies come from the cache: stated in design 13).
  Test: test_service test_a_crashing_spotlight_question_never_holds_back_the_hook_rows.
- With it (trivial, asked as P3 / P2): the event carries `max_n_spotlight`, `spotlight_crash`, `seconds_hook` and
  `seconds_spotlight`, and the log line the seconds of each question (qwen P2-3, glm N2: watch the latency).

## Refuted or recorded
- qwen P2-2 / earlier muse "spot_rows: separate 'not asked' from 'asked, none'": NULL is 'not asked' (not a
  conversation, or the question crashed: the note says which), 0 is 'asked, none'; kept.
- qwen P2-1 / glm P3-4 "episode_measure runs twice per conversation": harmless (milliseconds); recorded.
- glm P3-3 "a moment line re-mined after a hook line inherits role_hint 'hook'": advisory (nothing reads it); recorded.
- muse P2-1 "hook_cost_usd accumulates over the video's passes": as the log says ("for the video's hook passes so
  far"); recorded. muse P2-2 (segment-timed durations near 12 / 35 s): the builder re-anchors on word timing;
  recorded. muse P2-3 (the 4-slot executor shared by both questions): by design (keeps the moment pass's slots), now
  measured per question in the log; recorded.

Suite after the fix: tests/ingest 306 passed. Audit total: c1 $0.064 + c2 $0.060 = $0.124 (Heimdall).
