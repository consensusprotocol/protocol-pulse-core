# Batch 8c (DEC-10 d in run_fresh.stage_cut: an edge cut at its envelope minimum is judged by G16, not by cut_accept's M19 quota): dispositions

Why: the DEC-10 recut (12:03 ET, runs/pinned_20261111_170153, HEAD ae965c95) HELD at stage cut: cut_accept
rejected exactly the two edges the sentence-law cutter placed at the envelope minimum (Natalie OUT 80.93
"no genuine pause with >= 60 ms ahead"; Yahoo IN 38.20 "no boundary dip in the prior 100 ms"). DEC-10 d: "a
clip is rejected for edges only if (i), (ii) or (iii) cannot be met"; the M19 quotas are none of them.

Audited: the working-tree diff (run_fresh.py, test_dec10_edges.py). Cross-LLM GPT-4o + Gemini (Grok blocked
by the xAI ceiling); Heimdall deepseek + qwen27b per file, and a second pass on the fixed run_fresh diff
(heimdall_r2/).

## Implemented
- Heimdall consensus [high] (deepseek F1, both agree): the deferred valley edge was recorded `pass: True`.
  Now `pass: None` with `deferred_to: "G16 neighbour_clear (DEC-10 c-ii)"` and its M19 reading as `m19`; the
  clip passes the cut stage only if every NON-valley edge has a truthy cut_accept pass (a missing pass fails).
- Tests (from the not-agreed test findings, cheap and real): valley_out covered as well as valley_in;
  cut_accept is asserted to run on every cut (call_count); G16 ('sentence_law') is asserted to be the stage
  right after 'cut' in run_fresh.main.

## Rejected, with evidence
- Cross-LLM P1 [both] "wrap check_cut_acoustics in try/except so a dependency failure is fail-closed": the
  call is unchanged by this diff (HEAD run_fresh.py:430), and any exception in a stage already reaches
  main()'s handler (`except Exception as e:  # defensive: anything unexpected is HOLD`: verdict HOLD, the
  exception text appended to status.holds, REPORT.md written). That is M12 fail-closed.
- Cross-LLM P2 [Gemini] "check that d has 'in' and 'out'": check_cut_acoustics always builds both; a missing
  key would raise and HOLD through the same handler; a missing 'pass' on a non-valley edge now fails
  (`bool(d[s].get("pass"))`).
- Heimdall r2 consensus [medium] (deepseek F2, both agree in the vote) "defer a valley edge only when its M19
  failure is one of (i)-(iii)": cut_accept never measures (i)-(iii); its only reasons are the 60 ms guard and
  the 100 ms dip quota, which DEC-10 b / d replace for an edge cut at its minimum. (ii) and the lock (iii) are
  enforced by G16 on that very cut in the next stage, (i) by G17b on the render. A valley edge that M19 happens
  to pass is still deferred to G16 (nothing is lost; its reading is kept under "m19").
- Heimdall r2 deepseek F1 [critical, agree 0] "a deferred valley edge is still recorded pass True at the edge
  level": the edge record is `pass: None` (asserted: test_a_valley_edge_is_deferred_to_g16_...); the
  clip-level `pass` is the cut stage's verdict, which G16 follows.
- Heimdall test findings F2-F4 (agree 0): F2 answered by the call_count assertion; F3 "only the cutter can set
  the flag": valley_in / valley_out are written only by sentence_law.accepted_cut / write_lock_cut_table
  (grep), and pinned.write_pinned_cut_table writes a fixed field list without them; F4 answered by the
  stage-order test.

## Verification
pipeline suites (test_dec10_edges, test_pinned, test_prepare_retry, test_replay, test_pulse_20261110_mustfail,
test_telegram_delivery): 78 passed, 17 subtests; regression_test.sh 26 PASS / 0 FAIL; pipeline/regression.sh
PASS (parity 0.041 s).
