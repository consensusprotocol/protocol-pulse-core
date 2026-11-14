### The orders this change answers (verbatim)
- ORCHESTRATOR 08:15 ET Nov 14, F1: "FIX IT. A calibration replayed from the reply cache measures nothing. The daily
  calibration, and the one that gates 'allowed to answer' after an outage, must be asked LIVE (cache bypassed for
  calibration prompts only), and the log line must say live or replayed."
- ORCHESTRATOR 10:05 ET Nov 14, RULING 87 AMENDED: "'Down' means NO SUCCESSFUL ANSWER of any kind for 15 minutes: any
  answered call OR answered probe resets the clock to zero. [...] A probe must be a real model call on the family that
  failed (and one other), not a ping." (The module that keeps the clock is the builder's; it is being amended there.)

### Background
Ruling 40 P1: the watcher's second-model check may release an imperative / single_source_breaking flag only on an
answer from a back-end that answered every calibration quote right (16 quotes: 4 yes + 4 no for each of the two
flags). F1 (live since 08:07 ET, audited 2 cycles as pp-ingest_audit/f1/): every calibration quote is asked live
(router use_cache=False), unanswered quotes re-asked up to 3 rounds; the result is stored in the queue kv
'check_calibration' as {backend: {model, right, of, unmeasured, asked_at (the calibration's start, one value for all
back-ends), seconds, wrong: [...]}}; when none passed and one still could (an outage), the next calibration comes
after CHECK_RETRY_S (600 s), doubling up to a day; otherwise daily (CHECK_RECALIBRATE_S = 86400). Until this change
EVERY start asked all 32 quotes live (2 back-ends x 16) and check_once waited for them (1-2 minutes).
Why it matters now: at 09:01 ET a restart's live calibration ended on one muse 502; the watcher was quiet (a Saturday:
no real call followed), and by the shared module's rule then in force a probe answer did not stop the 15-minute clock,
so the shared signal switched to plan_b at 09:16 (a false outage; the paid route opened at 09:21 and made 0 calls).
The orchestrator has since amended ruling 87 (above); this change removes the start's 32 calls in any case.

### The change under review (32fd1d99; diff base c4f733db)
- service._reuse_calibration(): at start only (check_once, once: self._reuse_tried), the stored calibration is kept
  instead of asking again when ALL hold: the record is a non-empty dict whose key set equals router.effective(ROLE)
  (the role's callable back-ends now); every entry's model equals the back-end's current model; the entries carry ONE
  asked_at, a zoned ISO time (config.aware) with 0 <= now - asked_at < CHECK_RECALIBRATE_S; at least one back-end has
  of == right == 16 (len(flagcheck.watcher_probes())) and no unmeasured. Then check_allowed = those back-ends,
  check_calibrated = asked_at (so the next calibration stays due a day after the LIVE one), check_recal_s =
  CHECK_RECALIBRATE_S, an event 'check_calibration_reused' and a log line. Otherwise nothing changes: the live
  calibration runs as before.
- flagcheck: WATCHER_FLAGS and watcher_probes() factored out (the same 16 quotes watcher_checkers asks).
- tests (tests/ingest/test_service.py): a restart within a day reuses and asks no quote; an old record (25 h, one
  shared asked_at), a changed model, a record without asked_at (the cached era), one where nobody passed: asked live.
  Each gate mutation-checked (removing it fails its case).
- design 16: the restart paragraph.
- ALSO IN THE DIFF (already audited 2 cycles as pp-ingest_audit/a19/, review only if you see a defect): purge.py's
  A19 report fixes (unresolved names every failing delivery), service.purge_once storing one_copy_per_delivery in
  purge_last, tools/ingest_watch.py listing unresolved videos.

### Questions for the reviewers
1. Can any path let a back-end answer that was not measured live within the day (a cached-era record, a record of
   another model, a crash record, a future asked_at, two asked_at values)?
2. Does the reuse interact wrongly with the outage retry (CHECK_RETRY_S doubling) or with the daily schedule?
3. Is F1's "the one that gates 'allowed to answer' after an outage must be asked LIVE" kept? (A reused record must
   itself be a live calibration in which a back-end passed; an outage calibration is never reused.)

### Cycle 1 (592c2443): what changed since 32fd1d99 (details in C1_CONSENSUS.md)
- service._reuse_calibration: every refusal is logged with its reason ("check: the stored calibration is not reused
  (<why>): asked live now": none stored; its back-ends or models are not the role's now; no single zoned asked_at (a
  record of the cached era); asked N h ago (negative: the clock went back); no back-end passed it). The gates are the
  same; the code is restructured to name the reason.
- tests: a fake-clock test pins that after a reuse the next calibration is due a day after the LIVE calibration's start
  (none a minute before, a live one just after), not a day after the restart; the four refusal tests assert the logged
  reason. Each fails with its fix reverted.
- design 16: the refusal is logged.
