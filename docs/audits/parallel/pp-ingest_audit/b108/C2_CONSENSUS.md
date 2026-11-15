# b108: BATCH 3's money on pp-ingest's side (ruling 108; audits by ruling 107 (2)), cycle 2: consensus

Reviewers (Heimdall, diff-scoped; glm still down after cycle 1's two dropped connections, so muse stands in, ruling
107 (2)): qwen3.8-27b (63 s, $0.0032 reported): "No new correctness bugs"; its cycle-1 "critical logic error" (the
hourly line against the live share check) withdrawn as by design; P0 none. muse-spark-open (193 s, $0.0047
reported): "No new P0s. The core invariants (no lost notices, no paid call past share, hour figures final, cap
enforced) all hold, verified independently by both reviewers"; "still shippable with fixes". Cycle 2: $0.0079. The
audit: $0.0294 of its $1.00 cap (1,245 changed lines; COST.json: c1 qwen $0.0087, glm $0.0012 + $0.0014 booked at its
own rate for its two cut-off reviews, muse $0.0103; c2 qwen $0.0032, muse $0.0047).

## Agreed by both (verified)
- The C1 fixes are present; the invariants hold: line 1's writers lose and duplicate nothing; no paid call starts
  past the share (the check and the hold one step under RoleCaps.lock); an hour's figure is final; the driver cannot
  pass its cap and loses no review's cost.

## Fixed (each with a test that fails without it; 26 mutations killed in all, scratch copy)
- C2-1 (both: the abandoned-call lookups, three queries per model and role, the paid route's check running them under
  RoleCaps.lock): measured at 18.8 ms on the live table in cycle 1, but agreed by both, so done: the history behind
  ruling 107's basis is read in TWO grouped queries per count (batch.History), only when the count holds an abandoned
  call. Test: test_the_abandoned_calls_of_a_count_cost_two_grouped_queries... (12 abandoned calls on 4 models x 3
  roles: 3 queries; none abandoned: 1). Mutation M20 (a history per abandoned call) killed.
- C2-2 (muse N1, P1-2): an abandoned review was priced on the OTHER reviewers' mean prompt tokens; cycle 2 prompts
  differ (each carries its own cycle 1 review). Now its own prompt's length at the tokens per character measured on
  the reviews that answered (3 characters a token if none did). Test: test_an_abandoned_reviews_prompt_is_its_own...
  (M21 killed).
- C2-3 (qwen 3.1): the ledger records of a cycle are written in one write; a torn line is said on line 1 as an
  unreadable audit record, never counted silently (test_a_cost_priced_from_the_table_and_an_unreadable_audit_record).
- Found while writing this cycle's hourly figure (22:10): line 1 said "5 review(s)" for 5 ledger records (one is a
  correction) and "vendor-reported" over $0.0026 booked at glm's own rate. It now says "cost record(s)" and the
  audit dollars booked at a model's own rate apart (each record carries "reported"; an older one is read from its
  basis). Test: test_audit_dollars_booked_at_the_models_own_rate_are_said_apart... (M25 killed).

## Refuted or recorded
- qwen 3.2 (P2) "estimate() assumes the whole reply budget: refuses cycles that would fit": by design, it is the
  cap's check and must never under-count (cycle 1: qwen's reported $0.009 passed the doubled-average guess of $0.006,
  which is why the check became the list-price worst case). Under the $0.30 cap a qwen + glm cycle holds about $0.025
  (11 cycles); recorded.
- qwen 3.3 (P1) "the memo is per call, so the N+1 is worse": superseded by C2-1 (two grouped queries per count).
- qwen / muse "now + 1.0": kept with its comment ([t0, now]: a call recorded in this second counts); one clock writes
  and reads it.
- muse N2 "a second record() of the same cycle counts twice": record() runs only after real calls; a leg run again
  costs again, so both are kept (the cycle-1 glm rerun is exactly that case). Not a defect.
- muse N3 "prompt_for() built twice per reviewer": two string builds of ~100 KB; recorded.

Suite: tests/ingest 394 passed. Verdict: both reviewers "shippable", no P0 open; b108 goes live at the next watcher
restart.
