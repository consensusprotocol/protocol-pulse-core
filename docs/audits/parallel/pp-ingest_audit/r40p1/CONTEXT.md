### The order this change answers (orchestrator 19:22 ET Nov 13, verbatim)
"RULING 40, on your table (good work): P1 YES: 'imperative' and 'single_source_breaking' stand as hard flags only when
BOTH models agree; a row where the checker says no keeps the miner's label as a recorded note, not an exclusion. P2
YES: re-measure 'accusation' under the sharpened definition before anything is released; until then accusation stays
hard as the miner labels it (52 % precision is poor, but a wrongly released accusation is the one error we cannot
afford). P3 accepted: no miner-prompt change. Run the second-model check inside the watcher on each new flagged row
(it is cents), audited as one change after the hook pass is live."

### How it is built (diff since a9a5491a)
- ledger.py: `RELEASE_ON_CHECK = (imperative, single_source_breaking)`. `check_valid(line, flag)`: a recorded answer
  counts only for those two flags, answered yes / no / unsure, by a model other than the line's miner (mined.model),
  under the current definitions (flagcheck.PROMPT_VERSION). `effective_risk(line)`: a flag whose counting answer is
  "no" moves to `risk_notes` (a recorded note); every other flag stays. The adapter (best_unused_moments) excludes on
  the EFFECTIVE flags and returns a copy of such a line with `risk` = the effective flags and `risk_notes`; the stored
  ledger line keeps the miner's labels. `carry_forward` carries `risk_checks` from earlier lines of the same moment
  (the same words); the new line's own answer wins.
- flagcheck.py: `record(answer)` = what a line carries (answer, evidence, why, model, backend, prompt_version, at);
  `watcher_checkers(router)`: the role's back-ends that answer EVERY calibration quote right; only they may answer in
  the watcher. `ask(..., allowed=...)`.
- service.py: the `check` loop (every 30 s): the ledger's latest lines of moments still usable (not expired) whose
  imperative / single_source_breaking flag has no counting answer, newest first, 4 rows at once; each flag asked of
  the second model (never a model or back-end that mined any line of the video); the measured answers go into a new
  line of the moment through the service's one append lock (carry_forward + append); an unanswered question records
  nothing and is asked again after 10 min (the flag stands meanwhile); the checker is re-calibrated at start and daily;
  none passing: nothing is checked, every flag stands.
- stats.py: live.json `second_model_checks_12h` (rows checked, answers, released, cost, the calibration).
- Also in this diff, the P2 measurement tool: `flagcheck --rerun` asks accusation under the SHARPENED definition with
  insinuation probes added to the calibration (a measurement only; nothing it answers is read by the adapter).

### Questions for the reviewers (file:line)
1. Can the adapter release ANY flag without a counting "no" (another model than the miner, the current definitions)?
   Can it ever release accusation, or a flag other than imperative / single_source_breaking?
2. Can an answer be attached to the wrong moment or words, survive a definition change, or come from the miner's own
   model? Can a later line drop an answer, or carry a stale one past a re-mine that changed the words?
3. Can a checker that failed the calibration answer? Is every failure (outage, crash, invalid reply, unreadable
   ledger) fail closed: the flag stands?
4. Does anything change what is excluded for rows without answers, or weaken any other gate (L-u, expiry, delivered,
   opt-out, drift)?
