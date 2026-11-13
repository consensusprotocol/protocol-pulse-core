# pp-selectid audit of the L-y diff, ROUND 2: cycle 3 consensus (synthesis by the pp-selectid session, 21:30 ET Nov 12)

**Run.** Cycle 3 is a fresh first review of the final diff, which includes the post-cycle-2 changes, QUESTION items
11-15. C3_STEP.diff is 129,213 bytes; the prompt is 166,034 bytes. Reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP no (one P0, refuted below).
- qwen/qwen3.8-27b (Heimdall, effort none): SHIP no (one P0, refuted below).
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions.

**Spend:** about $0.84 at the config's upper-bound prices.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K6 | the takeaway budget for a flagged join's FIRST write (glm P0-2 / P1-2; qwen P2-2) | IMPLEMENTED. Two gaps: when the 3-word and 12-word budgets did not overlap, or the 12-word one did not exist, the code fell back to the 12-word budget or to (8, 30), and a legal bridge could then miss 60-70 s. Now package.bridge_budget(content) returns the largest bridge limit n <= 12 for which ANY bridge of 3..n words with the stated takeaway range lands 60-70 s; BRIDGE_ASK tells the writer "at most n words". When no bridge length fits, write_takeaway raises NoBridgeFits BEFORE any model call, and build() drops the clip after the flagged join and re-picks (no write paid). A redo with no landing length raises the same. Tests: test_an_offered_bridge_leaves_a_budget_that_holds_for_any_bridge_it_allows (94 clip lengths: every bridge of 3..n words at both takeaway bounds lands 60-70 s; where none fits, no prompt is sent), test_a_flagged_join_no_bridge_can_fill_drops_the_line_up_before_any_write |
| K7 | the table's takeaway pass rate hides the writes stopped before their verdict (grok P2; glm P1-9 / P2-3) | IMPLEMENTED. The table shows passed / judged / WRITTEN per universe and in total. The summary states that a write stopped first by another gate (runtime, shape, a lost clip) is not judged |

## Refuted with evidence

| finding | evidence |
|---|---|
| grok P0: "_package never writes runtime_s_estimate" | package._package sets `pk["runtime_s_estimate"] = runtime(segs, vo_lines)`. test_no_intro_and_one_takeaway_after_the_last_clip asserts its value (39.0 + 8 / 2.5 + 1.0 + 14.30), and 145 tests pass |
| grok P1: a RUNTIME redo can print "None" | the redo's detail branches on the budget: "(a takeaway of N-M words lands it)" or "(no takeaway length lands it: shorten the bridge)". Since K6, a redo with no landing length is refused before the call (NoBridgeFits) |
| grok P2: L-k says the text comparisons must go through canon | the comparisons are between two copies of the package's OWN bytes: the bridge record's text vs the VO line, and the gated line vs the shipped line. L-j wants these exact; canon is for transcripts against locked text |
| qwen P0-6: the ledger's read-modify-write races | Router._lock() opens a new descriptor and takes fcntl.flock(LOCK_EX) for every _reserve / _settle, so threads and processes serialize on it. The ledger also releases the reservations of processes that are gone |
| glm P1-3: truth_for runs twice and the second result overwrites the first | truth_for is cached per moment (`if m["moment_id"] not in cache`): the line-up's call returns the pre-screen's record; no second transcription |
| glm P1-1 / P2-4: ly_shape fails a package that writes after_clip 0 | no producer writes it. assemble_medley folds a hook-join bridge into vo.intro, and the factory (pinned.moments_vo, R11) refuses an after_clip that is not a clip index 1..n. Failing it in ly_shape matches the consumer |
| glm P2-14: the gate_problems guard goes on to the next line-up, not the next angle | after the write loop, `if out["packages"] or not relined: break`, and relined is False on that path, so the loop moves to the next angle, as the record says |

## Unique, implemented (cheap and right)

- glm P2-1: providers._num accepted inf. Now math.isfinite: a non-finite vendor figure is no figure, and the estimate
  stands. Tests cover inf and nan.

## Unique, kept

- glm P1-10: a doomed moment's absence in a later angle's record is explained only on the earlier record. Kept: the
  earlier record states why (rec["lost_why"]).
- glm P1-11: a clips-alone verdict that is not measured ends the angle. Kept, fail closed: the router already fails
  over within the verdict's chain.
- glm P2-7: pin_and_verify skips R11 when the factory copy lacks it. Kept and documented: the READY check runs against
  both the deployed tree and the integrator's ly-shape branch.
