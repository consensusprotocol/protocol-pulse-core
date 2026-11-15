# b108: BATCH 3's money on pp-ingest's side (ruling 108; audits by ruling 107 (2)), cycle 1: consensus

Reviewers (Heimdall, diff-scoped: the laws, CONTEXT.md and `git diff HEAD` of pipeline/ingest, tools/ingest_watch.py and
tests/ingest; no whole files): qwen3.8-27b (185 s, $0.0087 reported): "ready for production with minor fixes", one P0
and one P1 of the driver's (below); glm-5.3-flash: DOWN, its connection dropped by the gateway twice without an answer
(420 s, then 511 s), each booked at glm's own rate ($0.0012 + $0.0014: the stricter reading this change makes, found
on this very cycle, see C1-1); so, by ruling 107 (2) ("a third when one of the two is down"; the paid frontier
reviewers stay out under pp-ingest's freeze), muse-spark-open (315 s, $0.0103 reported): "production-ready infra",
two P1s (below). Cycle 1: $0.0215 of the $1.00 cap (1,096 changed lines; COST.json). qwen reviewed the diff at launch;
glm's second try and muse the working tree with C1-1 and C1-2 already in (PACKAGE_as_qwen_saw_it.md keeps the first).

## Agreed by both (verified)
- Line 1's writers cannot lose or duplicate a notice: one flock, one os.replace, the batch and alarm writers refuse
  '|' and newlines, the switch line is the tail (muse 1.6, qwen 1.4).
- No paid call starts past the share: the check and the hold are one step under RoleCaps.lock, every capped call in
  flight held, an unreadable or NaN share lets none start, outside a batch nothing is left (muse 1.7, qwen 1.1).
- An hour's figure is final once out: every count reads ts < the hour's mark, and a late record carries its insert
  time (muse 1.8). The driver cannot spend past its cap (the check is before any call) nor lose a review's cost
  (muse 1.9, qwen 1.6).

## Fixed (each with a test that fails without it)
- C1-1 (found by this cycle itself): glm's dropped connection after 420 s was booked "failed before any cost" ($0):
  false, it was in flight for 7 minutes. A call or review that fails after >= 30 s in flight with no answer (no HTTP
  status) is now booked at the model's own rate, like a timeout, in the watcher's accounting (batch.abandoned) and in
  the driver (book); an error the vendor answered (a status: the muse 502s of Nov 14, "tunnel: dispatch failed") and
  a refused connection stay at what was reported. The two glm records are re-booked (COST.json "corrected", the
  ledger's correction record). Tests: test_a_call_cut_off_in_flight..., test_a_review_cut_off_in_flight...
- C1-2 (found while writing the tests, before any reviewer): an abandoned call's rate and average prompt read the
  model's whole history, so a past hour's figure moved when later calls came; both now read only calls before the
  hour's mark (mutations M1 / M1b killed). And a session line right under the notices that started like the batch line
  ("BATCH 3 ingest spend: ..." is how this session wrote the figure before the watcher could) would have been taken
  for the batch notice and replaced: the batch and alarm notices are now recognised on line 1 only (M19 killed).
- C1-3 (qwen P0, its severity overstated): COST.json was written in place; a torn file stops every later cycle of the
  audit (cap_check cannot read it: fail closed, but the record is lost). Written to a temp file and os.replace'd.
- C1-4 (qwen 1.4): line 1 split its batch and alarm notices only in that order; a hand edit with the alarm first would
  have folded the switch line into the batch notice (the next hour's figure would replace it). Both are taken from
  the front in any order. Test: test_a_hand_edited_line_1_with_the_alarm_before...
- C1-5 (muse P3): the batch file's cache was keyed by mtime and size; a same-size edit inside one mtime tick would be
  missed. Keyed by its content now (a few hundred bytes, read every time). Test: test_a_same_size_edit...
- C1-6 (muse P1 "no alerting on share exhaustion"): the share's stop now carries ruling 108's question with its
  default on line 1 ("QUESTION (RULING 108): MAY THE PAID ROUTE TAKE PART OF ANOTHER SESSION'S SHARE? RECOMMENDED:
  NO ... DEFAULT IN 20 MIN: NO, NOTHING MORE IS SPENT"): ruling 106 (a). The default spends nothing, so nothing waits on
  a human after it; a real Heimdall outage of 45 minutes is the alarm's own case (ruling 106 (d)).
- C1-7 (muse P3): a test that 8 threads asking at once for a share with room for one call get exactly one hold.
- Docstrings: the share is counted to NOW (the check is live; only line 1 waits for the hour: qwen 1.1); "+1 s" in
  share_left means [t0, now] (qwen P2, muse P2).

## Refuted or recorded
- muse P1 "abandoned_usd N+1 query storm on the hot path": measured on the live calls table (2,289 rows): one
  watcher_spend over 3 days (2,013 calls, 2 abandoned) takes 18.8 ms; the lookups are memoised per (model, role) and
  a paid call's check runs one. First to index (model, role, ts) if the table passes ~100k rows. Recorded.
- qwen P1 "results / errors dicts written by threads without a lock": each thread writes its own key, and a dict item
  assignment is atomic under the GIL; the dicts are read only after every join. Refuted.
- qwen P3 "cap_usd not validated": batch.load does not read cap_usd (the $8.00 is the builder's ledger; the watcher
  enforces only its share). Refuted.
- muse P2 "the abandoned prompt is an average, not the call's own": true; it is ruling 107's basis as the builder
  applied it to calls without a logged prompt; the calls table records no prompt size for a failed call. Recorded for
  its own change (a prompt_chars column).
- muse P2 "no reconciliation CLI": line 1 is the ordered interface (the builder reads it every hour). Recorded.
- muse P3 estimate() builds the cycle-2 prompt once per reviewer: two reviewers, milliseconds. Recorded.

Suite: tests/ingest 391 passed; 19 mutations killed (M1-M19, scratch copy).
