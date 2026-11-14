# heimdall_glm (z-ai/glm-5.3-flash, 306.3 s, $0.006, finish stop)

# FORENSIC CODE REVIEW — pp-ingest, F1 change (live calibration + retry schedule)

## SECTION 1: CORRECTNESS

### 1.1 The core F1 fix — does it do what it claims?

**Yes, the central mechanism is correct.** `flagcheck.calibrate` (flagcheck.py:274-318) now passes `use_cache=not fresh` to `router.run` (flagcheck.py:290), and `watcher_checkers` (flagcheck.py:333-341) calls it with `fresh=True, rounds=CALIBRATION_ROUNDS`. The router's cache path (providers.py:910-925) is only consulted when `use_cache` is truthy (providers.py:851), so a live calibration genuinely calls the model. A successful live reply still writes the cache (providers.py:992-1001), which is the documented "a successful live reply still refreshes the cache file" behaviour — correct and desirable, since the measurement CLI (A35) then reproduces the report.

**Verified: the rounds loop aggregates correctly.** In `calibrate` (flagcheck.py:294-301):
- `answers` is keyed `(bid, i)`; each round's `ex.map(one, todo)` overwrites only unanswered entries (`todo = [j for j in todo if answers[j] is None]`, flagcheck.py:299). A re-asked quote's *latest* answer is the only one counted, because the final aggregation (flagcheck.py:303-318) reads `answers[(bid, i)]` once per `(bid, i)` in `jobs`. No double counting: `r["of"] += 1` happens exactly once per job. Correct.
- A back-end that answers in round 1 is never re-asked (it's not in `todo`). Correct — the test asserts `asked_first == 4 and len(b.calls) == 15 + 4` (only the failed quote re-asked, 3× in round 1 including its 2 transport retries, once more in round 2).
- `max(1, int(rounds))` (flagcheck.py:295) guards `rounds=0`/`None` — defensive, fine.
- A back-end with no effective entry: `jobs` is built from `router.effective(ROLE)` (flagcheck.py:281), so a disabled/frozen back-end simply gets no jobs and no `res` entry; `watcher_checkers`'s comprehension (flagcheck.py:341) then never admits it. Correct.

**One subtle aggregation nuance (not a bug, but worth stating):** `by_flag` is initialised for all of `FLAGS` (flagcheck.py:307) even when `probes` is the 16-quote subset — the watcher's calibration report shows `imperative: [16,16]`, `accusation: [0,0]`, `single_source_breaking: [16,16]`. Harmless; the report's calibration table (flagcheck.py:456-458) prints zeros for accusation, which is accurate ("not asked here").

### 1.2 The retry schedule in `check_once` (service.py:489-509)

Walk the paths:

- **First calibration** (`check_allowed is None`, `check_recal_s` initialised to `CHECK_RECALIBRATE_S` at service.py:126): if a back-end passed → `check_recal_s` stays 86400. If none passed and none *could* → 86400. If none passed and one could → `check_recal_s >= CHECK_RECALIBRATE_S` → set to 600. ✓
- **Consecutive failures**: 600 → (still failing, `check_recal_s=600 < 86400`) → `min(86400, 2*600)=1200` → 2400 → … → capped at 86400 by the `min`. ✓ Bounded.
- **Pass after failures**: `self.check_allowed` truthy → 86400. ✓ (test asserts this).
- **The cap**: once `check_recal_s == 86400` and it fails again with `could` non-empty, the branch `elif self.check_recal_s >= CHECK_RECALIBRATE_S` fires → resets to 600. So the documented "after the cap it starts again at 600" (change description) holds. ✓
- **Tight loop?** `check_once` runs every 30 s (service.py:756); calibration only re-fires when `clock() - check_calibrated >= check_recal_s` (service.py:489) and `check_calibrated` is set *after* the calibration returns (service.py:492). Minimum 600 s between failed calibrations. No tight loop. ✓

**Edge: `could` semantics.** `could = [b for b, c in cal.items() if c["unmeasured"] and not c["wrong"]]` (service.py:496). A back-end with `unmeasured=0` and `wrong=2` → not in `could` → if it's the only back-end, `not could` → daily. Matches A34 ("a back-end that answered a quote wrong waits for the daily one"). A back-end with *both* wrong answers and unanswered quotes (e.g. 1 wrong, 1 unanswered) → in `could` → retried in 600 s. At temperature 0 the wrong quote will be wrong again, but the unanswered one may now answer — so the retry is not pointless. Correct.

**Edge: `cal` empty.** If `router.effective(ROLE)` is empty (all frozen/disabled), `calibrate` returns `{}`; `watcher_checkers` returns `([], {})`; `could = []` → `not could` → 86400. Then `if not self.check_allowed: return 0` (service.py:510-511). Fine — but note this means a *transient* condition (e.g. spend meter trips → metered back-ends reordered, still effective; or both flagcheck back-ends' budgets exhausted) waits a full day before recalibrating, even though `effective()` could change. Minor; see P2.

### 1.3 Race conditions

- **`check_row` vs `check_once`**: `check_inflight`/`check_next` are guarded by `clock_lock` (service.py:462-463, 477-478, 517-545). A row's key is added to `check_inflight` under the lock (service.py:544-545) before submission and discarded in `check_row`'s `finally` (service.py:482-483). Duplicate submission of the same moment_id in one loop is prevented by the `key in self.check_inflight` test (service.py:533). ✓
- **`_append` under `wlock`** (service.py:299-308): `carry_forward` reads the ledger then appends, both under `self.wlock` — but `ledger.append` itself takes an flock (ledger.py:47). Two *processes* are prevented by the service lock (service.py:139-153). Within the process, the `wlock` serialises read-modify-write. ✓ However: `check_row`'s `new = json.loads(json.dumps(l))` (service.py:465) then `_append(v, [new])` — if the *hook* pass appended a newer line for the same moment between `check_once`'s read (service.py:522) and `check_row`'s append, `carry_forward` (ledger.py:187-209) merges the earlier line's flags into the new one, and the adapter's "latest line wins" (ledger.py:314-317) keeps the risk_checks. The design anticipates this. ✓
- **`_check_seen` optimisation** (service.py:512-520, 540-541): `seen = (st.st_size, st.st_mtime_ns)`. If the ledger's mtime+size are unchanged *and* no `check_next` is due, the loop skips the read. But `check_row` appends to the ledger, changing both — so a just-written answer is picked up next loop. One subtlety: `self._check_seen = seen` is only assigned when `len(todo) <= CHECK_INFLIGHT - len(self.check_inflight)` (service.py:540-541), i.e. when everything due was started. If more rows were due than room, `seen` is not updated, so the next loop re-reads. Correct.

### 1.4 N+1 / performance

- `check_once` reads the ledger tail (service.py:522) once per loop when the ledger changed — bounded by `offset_before` (ledger.py:122-149) to the last ~13 h + 1 day margin. Acceptable.
- `check_row` → `flagcheck.ask` → `router.run(..., only=bid)` per flag (service.py:455). Two flags = two router runs, each potentially 3 attempts. With `CHECK_INFLIGHT=4` rows × 2 flags = 8 concurrent calls max, under the global 20. ✓
- `calibrate` uses `ThreadPoolExecutor(workers)` with `workers=4` (service.py:491 → `watcher_checkers(router)` default) — 32 jobs (2 back-ends × 16 probes) at 4 concurrent. Each probe is a short prompt; at glm's measured ~26 s median (providers.json:32) this is ~3.5 min per calibration round. With 3 rounds worst case: ~10 min inside the check loop, *blocking* it (the loop's other duties — nothing, it only checks — but the 30 s cadence is lost). Not a correctness issue; the loop thread just spends its 30 s slot. Note `service._loop` catches exceptions (service.py:720-724) so a calibration crash doesn't kill the thread. ✓

### 1.5 Edge cases that will bite

**E1 — `asked_at` is the calibration *start*, not per-back-end.** service.py:490: `asked = config.iso()` taken *before* `watcher_checkers` runs; it's stored identically for every back-end (service.py:503-505). The design says "asked_at per back-end" (section 16) — it's per *calibration*, not per back-end. With a 3-round retry, a back-end that answered in round 3 was "asked" up to ~10 min after `asked_at`. Cosmetic/observability drift, not a correctness bug. P3.

**E2 — `watcher_checkers`'s `rounds` parameter is not plumbed from the service.** service.py:491 calls `flagcheck.watcher_checkers(self.router)` — the default `rounds=CALIBRATION_ROUNDS` (3) applies. Fine, but the service cannot tune it. P3.

**E3 — the `wrong`-but-also-`unmeasured` back-end.** Covered above: it's in `could`, retried at 600 s. But its *wrong* answers are re-asked too (all 16 probes go out again, fresh). At temperature 0 the wrong ones stay wrong — 16 wasted calls per retry, doubling. Worst case: 8 calibrations/day × 2 back-ends × 16 = 256 calls. The design's own arithmetic ("about eight calibrations a day at worst, each at most 3 rounds of 32 short questions", section 16) acknowledges this. Cost is negligible ($0.003/day claimed). Accept.

**E4 — `test_f1_a_quote_not_answered...`'s `asked_first == 3` arithmetic.** The FakeBackend raises `BackendError("network", "down")` for the first 3 *calls* (the test's `fn` counts `failed.append(p)` — one per call, and the router's `transport_retries=3` default (providers.json:130) means the router calls the backend up to 4× per `run`... wait: `transport_left = int(rc.get("transport_retries", ...))` = 3, and the loop `while attempt < attempts` with `attempts=2` for role flagcheck (providers.json:112). Actually for the *probe* path here it's the flagcheck role: `attempts: 2`. So one `router.run` = up to 2 attempts; each attempt = 1 backend call; a `network` error is retryable (providers.py:44) with `transport_left=3` → the error path (providers.py:965-969) decrements and continues, but `attempt` only increments on success (providers.py:978). So a persistent network error loops: attempt 1 fails, transport_left 3→2, sleep, attempt... until `transport_left` hits 0 → `h.record(False...)` → return. That's 4 calls (1 + 3 retries) per `run`. The test's `len(failed) < 3` means the first 3 *calls* fail; the 4th succeeds. With rounds=1: round 1's `one()` for that quote does 4 calls (3 fail, 1 succeeds) → answered! But the test asserts `asked_first == 3` for rounds=1... Let me recount: `fn` fails while `len(failed) < 3`. Call 1: failed=[p], raises. Call 2: failed=[p,p], raises. Call 3: failed=[p,p,p], raises. Call 4: succeeds. So one `run` = 4 calls, 3 failures + 1 success → answered in round 1, `asked_first == 4`... but the test says 3 for rounds=1.

Hmm — unless the FakeBackend's `fn` is called once per *attempt* and the router's retry sleep... Actually re-read: the test's comment says "the router's call and its 2 transport retries" — implying 3 calls total. That means `transport_retries` is 2 in the test's router, or the role's `attempts: 2` interacts: attempt 1 fails (call 1), transport_left 3→2, continue; attempt 2... no, `attempt` doesn't increment on the error path. Let me re-trace `_try` (providers.py:941-971): `while attempt < attempts` (2). Iteration 1: `th.wait()`, call → BackendError("network"). `r.retryable` True, `transport_left=3 > 0` → `transport_left=2`, sleep, `continue`. Iteration 2: `attempt` still 0... wait, `attempt += 1` only happens at providers.py:978 on success. So the while loop condition `attempt < attempts` = `0 < 2` — it never exits via attempts! It exits via `transport_left` hitting 0: iterations 1-4 (transport_left 3,2,1,0), 4 calls, then `h.record(False)`, return ("unavailable" or "rejected"). So 4 calls per `run` for a persistent network error.

The test: `len(failed) < 3` → calls 1,2,3 fail; call 4 succeeds → `run` returns ok. So round 1: `asked_first` = 4 calls. But the test asserts `asked_first == 3` for rounds=1 and `== 4` for rounds=3. For rounds=3: round 1 = 4 calls (3 fail, 1 succeeds) → answered → no round 2 → still 4. The test's numbers (3 and 4) imply the *first* round's `run` makes exactly 3 calls (all failing) and the quote stays unanswered, then round 2's `run` makes 1 more (succeeding) = 4 total.

That means the test's router must have `transport_retries=2`. The test calls `_router([b], ...)` — a fixture we can't see. If `_router` builds a config with `throttle.transport_retries: 2`, then: round 1 = 3 calls (1+2 retries, all fail) → unanswered; rounds=3 → round 2: 1 call (succeeds, `len(failed)=3` not < 3) → answered. Total 4. ✓ consistent. For rounds=1: 3 calls, unanswered, `unmeasured=1`, `of=15`. ✓. So the test is *self-consistent only if* `_router` sets `transport_retries=2`. This is unverifiable from the package — the fixture is not shown. Flag it: **the test's arithmetic depends on an unseen fixture constant**. If `_router` uses the production `transport_retries: 3` (providers.json:130), the assertions `asked_first == 3` / `== 4` / `len(b.calls) == 15+3` / `15+4` are all wrong (they'd be 4 / 4 / 15+4 / 15+4, and rounds=1 would *pass* the calibration, contradicting `allowed == []`). P1 — verify the fixture.

**E5 — `b.calls` records prompts, and `gold[p]` keys by prompt.** In the rounds=3 test, round 2 re-asks only the failed quote; `b.calls` grows by 1. But `gold[p][1] == first` — `first = FC.PROBES[0][2]` (the *text*), and `gold` maps prompt→(gold, text). Two probes could share identical text? No — PROBES texts are distinct. ✓

**E6 — `check_row`'s `v` fallback** (service.py:467): `self.q.video(l["video_id"]) or {"video_id": ..., "discovered_ts": self.clock()}`. Then `_append(v, [new])` uses `v.get("discovered_ts")` for the `since` (service.py:305). If the video row vanished (purge doesn't delete queue rows; only a manual wipe), `discovered_ts = now` → `since = now - 86400` → `carry_forward` reads the last day of the video's lines. Correct enough. ✓

**E7 — the bundled WARNING change** (service.py:745-748): pure text. The claim "ruling 98's capped paid route is a separate role" is accurate (providers.json:114-117, `freeze_lifted` + `daily_cap_usd`; providers.py:806-818 `available(bid, breaker, freeze_lifted)`; providers.py:931 `if self.frozen(bid) and not rc.get("freeze_lifted")`). ✓

### 1.6 Silent failures

- `calibrate`'s `one()` catches only `AllBackendsFailed` (flagcheck.py:291) — a *different* exception (e.g. the FakeBackend's `fn` raising, or a bug in `prompt()`) propagates out of `ex.map`... actually `ex.map` yields results; exceptions propagate when the generator is consumed (flagcheck.py:297-298). They'd escape `calibrate` → escape `watcher_checkers` → caught by `check_once`'s caller? No — `check_once` has no try/except around the calibration (service.py:489-509). It's called from `_loop` (service.py:720-724) which catches `Exception` and logs. So a calibration crash = the check loop logs and retries in 30 s, with `check_allowed` still `None` (first time) → recalibration attempted again. But `check_calibrated` was not updated (the exception precedes service.py:492)... actually if `watcher_checkers` raises, service.py:491-509 never runs, `check_calibrated` stays 0 → next loop recalibrates. 30 s cadence, no tight loop. ✓ But: **a persistent calibration crash (e.g. a validator bug) means the check loop spins every 30 s, calling the model 32× each time** — 32 calls/30 s = 64k calls/day. The doubling schedule only applies to *answered-but-failed* calibrations, not *crashed* ones. P2.

- `record()` returns None for an unmeasured answer (flagcheck.py:325-326); `check_row` skips it and schedules a retry (service.py:456-463). ✓

## SECTION 2: LAW COMPLIANCE

- **L-x (no single model, ≥2 back-ends/role, one provider interface)**: COMPLIANT. `flagcheck` role: 2 back-ends (providers.json:112-113); `load_config` enforces ≥2 (providers.py:158-161); the calibration's `watcher_checkers` admits a *subset* (even 1 or 0) — that's the ruling's own "only back-ends that passed may answer", not a violation. Vendors/models only in providers.json (test_inventory: test_no_vendor_or_model_name_outside_the_provider_config).
- **L-l (reply counts only whole; nothing repaired; failed call never a pass)**: COMPLIANT. Strict validator (flagcheck.py:175-202); `Invalid` never repaired (providers.py:982-989 re-asks with the reason, 3 attempts... here `attempts: 2` for flagcheck); unanswered → `unmeasured` → `check_valid` returns None → flag stands (ledger.py:215-226, 229-241). The calibration: `of == len(probes) and right == of` (flagcheck.py:341) — an unanswered quote (`of=15` of 16) fails the admission. ✓ Exactly the F1 finding's remedy.
- **L-j / L-m (fail closed; nothing measured is never a pass)**: COMPLIANT, and this change *is* the L-m fix. `unmeasured` counts, never agrees (flagcheck.py:341, 365-369); the schedule's `could` logic keeps the flag standing while retrying (service.py:510-511 `if not self.check_allowed: return 0`).
- **L-u (hard exclusions; a wrong label is not L-u)**: COMPLIANT. The check *measures*; the adapter releases only on a counting "no" (ledger.py:212, 229-241); accusation never released (ledger.py:212, test).
- **Spend freeze**: COMPLIANT. Calibration calls go to `heimdall_glm53flash`/`heimdall_muse` (vendor heimdall, not frozen, providers.json:5-8, 28-46). The live calibration adds real calls — noted by the downsignal (see 1.4/Q4). `mine` chain untouched.
- **Secrets**: COMPLIANT. Keys via `Keyring` (providers.py:180-221), `redact` on error paths (providers.py:953-955), never in `__repr__` (providers.py:210-211, 238-239). No key in the diff.
- **B1 (90% tripwire notifies, never halts)**: untouched, COMPLIANT (spend.py:163-184; the calibration's extra Heimdall calls are metered via `spend_meter: true` on both flagcheck back-ends, providers.json:34, 44 — they add to `local_since` via providers.py:976-977. Correct: the meter's estimate includes this service's own spend).
- **B2 (nothing lost)**: untouched; the check loop's failures never drop a flag (it stands). COMPLIANT.
- **B4 (age gate)**: untouched.

**No violations found.** One *partial* worth naming: the design's "asked_at per back-end" (section 16) is implemented as one shared `asked` timestamp (service.py:490, 503-505) — PARTIAL, cosmetic.

## SECTION 3: SECURITY

- **SQL injection**: none. All queue access is parameterised (queue.py:96-102, 178-180, 185-186, 191-193, 199-201). The dynamic column lists in `set_state`/`set_hook`/`channel_update` (queue.py:130-133, 159-166, 203-208) come from code, not user input, and are validated against `VIDEO_FIELDS`/`HOOK_COLUMNS` (queue.py:160-162, 204-206). ✓
- **Auth**: N/A (no routes; local tmux process). The gateway bearer key never follows a redirect (providers.py:322-327, 304-306) — ✓, and the override host allowlist (providers.py:168-177) keeps the key on this machine or the configured host. ✓
- **Rate limiting / spend**: the calibration adds 32 live calls per calibration, up to ~8×/day worst case (E3) — bounded by the doubling schedule. Both flagcheck back-ends have `spend_meter: true` but **no `daily_budget_usd`** (providers.json:28-46) — unlike the frontier back-ents (providers.json:61, 69, 76). A pathological calibration loop (E6's 30 s crash spin) has no hard spend ceiling. P2.
- **Secrets in code**: none. `env_file` path hardcoded (providers.json:10) — by design.
- **Unvalidated input**: `prompt()` interpolates channel/title/text into the prompt with `_untrusted` (flagcheck.py:169-172, mine.py:294-297) — `<` → `‹` prevents closing the `<quote>` block. `>>` markers deliberately kept (mine.py:296). Prompt-injection surface is the transcript itself, mitigated by the SECURITY lines (flagcheck.py:144-151) and the strict JSON+evidence-quoted-from-quote validator (flagcheck.py:193-198) — the evidence check (`f" {e} " not in q`) is a genuine, if weak, grounding test. ✓
- **`_norm` evidence check** (flagcheck.py:161-162, 194-198): normalises both sides; a model could copy a *short* substring ("yes") that appears anywhere in the quote — weak but harmless (the answer, not the evidence, is what releases).

## SECTION 4: FRONTEND QUALITY

No UI in this diff. The "frontend" here is the STATE file line 1, live.json, and the log line.

- **STATE line 1**: the switch/notice machinery (spend.py:35-64, 199-216) keeps switches first, newest first, one physical line, under the notices' flock — matches the design. The new calibration does not write STATE (correct: it's not a switch). ✓
- **live.json**: `second_model_checks_12h.calibration` now carries `asked_at` (service.py:503-505) — the promised observability. But it's the calibration-start time, identical for both back-ends (E1). Also: the *stored* calibration is overwritten wholesale on every calibration, so after a failed-then-passed sequence you only see the latest. Acceptable.
- **Log line** (service.py:507-509): `got = [(b, c["right"], c["of"], c["unmeasured"]) ...]` — labelled "(right, answered, unanswered)". Clear. The `next calibration in {check_recal_s:.0f} s` makes the schedule auditable. Good.
- **Empty/error states**: `check_allowed == []` → "none (every flag stands)" in the log (service.py:508) — the fail-closed state is *visible*. ✓
- Loading states: N/A (no async UI).

Score: this is a headless service; within that constraint the observability is above average. 82/100.

## SECTION 5: BACKEND QUALITY

- **DB writes**: the queue is the only DB; `x()`/`rows()` are parameterised; `isolation_level=None` (autocommit) with WAL + `synchronous=FULL` (queue.py:81-87). No explicit try/rollback, but every statement is single-row autocommit — a crash mid-`set_state` leaves the prior state, and `recover()` (queue.py:210-216) heals `probing`/`mining` on restart. The `check_calibration` kv write (service.py:503) is a single UPSERT. ✓
- **External calls**: every model call goes through `Router._try` — timeout per back-end (providers.json:33,43: 300/600 s), transport retries (providers.py:965-969), throttle backoff (providers.py:654-681), breaker (providers.py:575-639). Graceful degradation: `AllBackendsFailed` → `unmeasured` → flag stands. ✓
- **Loop failure**: `_loop` catches `Exception` (service.py:720-724), logs, continues. A calibration crash cannot kill the service. ✓ (But see E6: no backoff on *crash* loops.)
- **Memory**: `calibrate`'s `answers` dict is 32 entries; `check_once`'s `latest`/`miners` dicts are bounded by the 13 h+1d ledger tail. `check_row`'s `json.loads(json.dumps(l))` deep-copies one line. No leaks. The `ThreadPoolExecutor(workers)` in `calibrate` is created *per calibration* (flagcheck.py:296) — 8+ executors/day, each properly context-managed. ✓
- **Logging**: `check_row` logs answers with moment_id, channel, flag, answer, released-ness (service.py:472-475); crashes log the traceback (service.py:479). The calibration logs the outcome + next wait (service.py:507-509). Good context. One gap: the calibration's *wrong* answers are stored in `cal[b]["wrong"]` (flagcheck.py:317) but only the counts reach the kv/log — the wrong quote's text/gold/answer is dropped. To debug "why is glm barred" you'd need the calibration object, which is discarded. P2.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Genuinely excellent (say so):**
- The F1 diagnosis→fix arc is textbook: measured (32 cache rows, timestamps of the cached answers), root-caused (the router's own comment, providers.py:852-853), fixed at the mechanism (not a symptom), and *fail-closed preserved* (unanswered → not admitted → flag stands). The `rounds` retry inside the calibration, plus the doubling *between* calibrations, is a considered cost/latency tradeoff with the reasoning written down (A34).
- The schedule's `could` distinction (unanswered→retry soon; wrong→wait, because temperature 0) is the kind of domain-specific reasoning (providers.json:112 `attempts: 2`, temperature 0 at providers.py:367) that separates production code from prototype. Few teams would notice that a wrong answer at temperature 0 is *deterministic* and therefore not worth retrying.
- The tests assert *call counts* (`len(b.calls) == 32`), not just outcomes — they'd catch a regression to cache-answering.

**Material gaps:**

1. **No calibration crash backoff** (E6). A deterministic crash (bad prompt, validator regression) → 32 calls every 30 s, indefinitely, with no `daily_budget_usd` on either flagcheck back-end. One `try/except` + the existing doubling machinery would close it. This is the highest-value missing piece.
2. **Calibration results are fire-and-forget.** `cal[b]["wrong"]` (the actual misanswered quotes) never survives the call. Store it in the kv (it's ≤3 dicts) — the next "why did the checker stop releasing flags?" incident becomes a 5-second lookup instead of a re-run.
3. **`asked_at` per calibration, not per back-end** (E1) — the design promised per back-end; with 3 rounds the discrepancy is minutes. Either take the timestamp inside `calibrate` per (bid, first-ask) or rename the field.
4. **The `could` heuristic ignores *why* nothing was answered.** An outage (breaker open, 300 s) and a *config* error (back-end disabled, key missing) both produce `unmeasured` — but the latter will never succeed, yet gets retried at 600→1200→…→86400 forever. `AllBackendsFailed.tried` already distinguishes `skipped` (providers.py:63-70); surfacing "all skipped" into the schedule (→ daily, like `wrong`) would be nearly free.
5. **No calibration-duration guard.** 3 rounds × 2 back-ends × 16 probes at glm's p90 74 s (providers.json:32) ≈ 10+ min inside the check loop, during which `check_once` does nothing else. Fine today (the loop has no other duty) but it's latent: if the check loop ever gains a second duty, the calibration blocks it. A `deadline` parameter would future-proof it.

Everything else — the ledger, the router, the purge, the signal — is already at or above the bar for a single-process, stdlib-only service. Do not add frameworks.

## SECTION 7: SCORES

- Backend logic: 88/100 (the rounds aggregation and schedule are correct; the unseen-fixture test arithmetic (E4) and the crash-loop gap (E6) cost it)
- Frontend/UI: 82/100 (headless; observability good, `asked_at` semantics sloppy)
- Error handling: 86/100 (fail-closed everywhere; the one hole is the unbackoffed crash path)
- Security: 90/100 (parameterised SQL, redaction, no-redirect, override allowlist; missing per-back-end spend ceiling on flagcheck)
- Performance: 85/100 (bounded reads, bounded concurrency; 10-min calibration blocking the loop is latent)
- Law compliance: 96/100 (the change *is* an L-m remediation; the only deduction is the "asked_at per back-end" partial)
- World-class gap: 84/100 (the diagnosis/fix discipline is exemplary; the missing crash backoff, discarded `wrong` detail, and skipped-vs-down blindness are the residue)
- **OVERALL: 87/100**

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Wrap the calibration in try/except with the existing doubling backoff, so a deterministic crash cannot call the model 32× every 30 s | service.py:489-509 (plus flagcheck.py:274-318) | a validator/prompt regression spins 57k+ calls/day against back-ends with no `daily_budget_usd` (providers.json:28-46), silently

P1 HIGH | Verify/fix the `test_f1_a_quote_not_answered...` arithmetic against the unseen `_router` fixture: the asserted call counts (3, 4, 15+3, 15+4) only hold if `throttle.transport_retries == 2`, but production is 3 (providers.json:130) and the role's `attempts: 2` never bounds the loop because `attempt` increments only on success (providers.py:941-978) | tests/ingest/test_flagcheck.py (new test 2), providers.py:938-969 | if the fixture uses the production throttle, the test's assertions are wrong and the rounds mechanism's retry-count guarantee is unproven

P1 HIGH | Persist `cal[b]["wrong"]` (flag, gold, answer, text) into the `check_calibration` kv | service.py:503-505, flagcheck.py:317 | debugging a barred checker currently requires re-running the calibration; the data already exists and is discarded

P2 MEDIUM | Distinguish "all back-ends skipped" (config: disabled/missing key/frozen) from "called and unanswered" in the schedule, via `AllBackendsFailed.tried` statuses (providers.py:63-70); skipped → daily, like `wrong` | service.py:496-502, flagcheck.py:288-292 | a permanently misconfigured back-end is retried at 600→…→86400 forever, wasting 32 calls/day on a known-dead path

P2 MEDIUM | Add `daily_budget_usd` to `heimdall_glm53flash` and `heimdall_muse` | providers.json:28-46 | they are the only metered back-ends without a spend ceiling; the calibration is their first bursty workload

P2 MEDIUM | Record the calibration's wall-clock duration and, if it exceeds a threshold, log it | service.py:490-492 | 3 rounds × 32 probes at glm p90 74 s (providers.json:32) can hold the check loop ~10+ min; invisible today, surprising tomorrow

P3 LOW | Make `asked_at` per back-end (timestamp inside `calibrate` at each (bid,·) first ask) or rename it `calibration_started_at` | service.py:490, 503-505 | the design (section 16) says "asked_at per back-end"; with 3 rounds the single timestamp is minutes stale for the later-answered back-end

P3 LOW | Plumb `rounds` (and `workers`) from the service into `watcher_checkers` | service.py:491, flagcheck.py:333 | the constant is currently unreachable from the caller, so tuning it means editing flagcheck.py

P3 LOW | Include the wrong-quote summary (flag + gold + answer, no text) in the calibration log line | service.py:507-509 | one-line cost, closes most "why barred" questions without the kv

## SECTION 9: THE ONE THING

Put the calibration under the same doubling-backoff discipline you just built for its *failures* — right now a crashed calibration (not a failed one) calls the model 32 times every 30 seconds forever, with no budget ceiling on either back-end, which is exactly the class of silent-spend bug F1 just taught you to hunt.

## SECTION 10: FINAL VERDICT

Ready for production. The F1 fix is correct, minimal, fail-closed, and honestly tested — the rounds aggregation, the `could`-vs-`wrong` schedule, and the preserved fail-closed semantics (unanswered → flag stands) all check out against the code. Before merge: confirm the unseen `_router` fixture's `transport_retries` (the second test's arithmetic depends on it), and add the crash-path backoff + a spend ceiling on the two flagcheck back-ends; everything else is polish.