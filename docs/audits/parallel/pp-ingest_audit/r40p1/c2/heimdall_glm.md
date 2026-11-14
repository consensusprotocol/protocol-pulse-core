# heimdall_glm (z-ai/glm-5.3-flash, 262.3 s, $0.004, finish stop)

# CYCLE 2 — FINAL REVIEW, pp-ingest ruling 40 P1/P2 diff

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **Muse's `published_at`-None sort analysis (service.py:492-493).** I noted the sort in passing but never traced the *ordering dependency* — that `todo.sort(key=lambda x: (x[0], x[1]))` is only safe because `ledger.expiry(l)` gates undated rows out earlier in the same loop (service.py:486-487). Muse called it "no bug, fragile ordering dependency" — correct, and I should have flagged the fragility explicitly. A future edit that moves the expiry gate after the sort, or changes `expiry` to return a non-None for undated rows, silently reintroduces a `TypeError: '<' between 'str' and 'NoneType'` in a 30 s loop thread. My miss: I verified the invariant held but didn't record it as a latent coupling.

- **Muse's N+1 / full-file-read note.** I flagged the 30 s re-read cost in B3's neighborhood but didn't quantify it as a *repeated* cost. The implemented skip (size+mtime, service.py:466-474) addresses it; I noted the fix landed in the consensus table but didn't credit that it was *my* finding (glm P1) that got implemented with a test. Fair.

- **Qwen's SpendBook-before-cache-write ordering (providers.py:838 vs 855).** I never looked at providers.py in Cycle 1 — my scope note said "ledger.py, flagcheck.py, service.py, stats.py" and I stuck to it. Qwen's point that spend is recorded before the cache write (so a failed cache write records spend with no stored reply) is real but, as Qwen itself says, fail-closed-acceptable. Agree, P3.

- **Qwen's "carry_forward reads before append writes" P0.** This one I *did* address in my own B1/B2 (I traced it to closure via `wlock`), and the consensus table refutes it with the ruling-80 precedent. Agree with the refutation: `service._append` (service.py:283-285) holds `wlock` across `ledger.carry_forward`'s read AND `ledger.append`'s write, and there is one service per store (flock, service.py:118-132). Qwen's P0 is wrong as stated — it's single-process-atomic. But Qwen's *mechanism* description ("the read and write must be atomic under the same lock") is exactly what the code does; the finding is a mislabel, not a miss.

- **Muse's point 3 (miners dict grows across re-mines).** I covered this as my B5 (latent, not active). Muse independently reached the same conclusion. Convergent, no new information.

What nobody caught, including me, in Cycle 1 — see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Who | Verdict |
|---|---|---|
| Calibration blocks the check loop; no `can_spend` on it | glm (me, B3) | Agree with myself, and muse's consensus table *refuted* the cost-guard half ("48 short calls a day, ~$0.003, recorded in calls + live.json"). I accept the refutation: the guard is unnecessary; the *blocking* half stands but is P2, not P0-adjacent. Downgrading my own B3. |
| `check_next`/`check_inflight` race | glm B4, muse #1 | Both of us concluded "no bug" after tracing. Muse's trace is more complete (it notes the except-branch also sets `check_next`, so a crash before the finally still guarantees retry). Agree, no bug. |
| Stale `latest` read | glm B1, muse #2 | Both closed it via `carry_forward` under `wlock`. Agree. Muse adds the sharper formulation: `carry_forward` re-reads `video_lines` under `wlock` *inside* `_append`, so the read-merge-write is one step. Exactly. |
| `miners` from ledger, not queue | glm B5, muse #3 | Agree, latent-only. Today: mine/hook chain = (qwen, local_gemma), flagcheck chain = (glm, muse) — disjoint by construction in providers.json:80-86. The failure mode (checker pool → [], silent) is real but requires a config edit. P2. |
| `published_at`-None sort | muse #4 | Agree, fragile-not-broken. P2. |
| Ledger append race (qwen #1) | qwen | Disagree with the P0 label; the code is correct. The consensus table's refutation is right and cites the ruling-80 precedent. |
| Router lost-update / duplicate calls (qwen #2) | qwen | Partially agree. Duplicate concurrent calls for the same prompt do happen (no in-flight dedup), but the cost is bounded by the semaphores and the throttle; the "disk full → inconsistent state" half is wrong (spend recorded, reply not cached → next call re-asks: fail-closed, consistent). P3. |
| Stats N+1 (qwen #3) | qwen | Agree it's O(12 h of events) per 10 min, disagree it's a bottleneck at this scale. P3. |
| `check_valid` model-string comparison (qwen #4) | qwen | Agree it's correct; qwen's own analysis concludes compliance. Note qwen's *reasoning* contains an error: it says "if the miner used qwen and the checker used qwen (different backend, same model), this fails. This is correct behavior" — actually the law says no single *model*, so same-model-different-backend failing IS the intended gate. Qwen reached the right verdict through a slightly confused sentence. No impact. |

## 3. NEW FINDINGS FROM THIS REVIEW

Tracing the *combination* of the check loop with the consensus-accepted fixes, three things nobody raised:

**N1 (P2, real): the calibration result is stored but never *re-validated* against the answers it releases — and `watcher_checkers`'s "answered EVERY probe" gate has an off-by-one trap when the probe set changes.** `watcher_checkers` (flagcheck.py:316-320) requires `c["of"] == len(PROBES) and c["right"] == c["of"]`. `c["of"]` counts *answered* probes. If a back-end answers 23 of 24 (one unmeasured), it is excluded — correct. But `calibrate`'s `by_flag` dict is built from `FLAGS` (flagcheck.py:291), which includes `accusation` — so the watcher's daily calibration spends 8 of its 24 probes (a third) measuring accusation, a flag that **can never be released** (ledger.py:212) and whose answers the adapter never reads. Under the ruling's own P2, those 8 answers are dead weight in the hot path: 8 extra Heimdall calls × 2 back-ends × every 24 h, plus 8/24 of the calibration's latency blocking the check loop at start (my Cycle-1 B3). Not a correctness bug — the gate is *stricter* than needed — but the ruling-40-P2 note in flagcheck.py:52-54 says the sharpened re-measure happens in the *tool*, and the watcher's calibration still burns the accusation probes. Nobody flagged that the watcher's recurring calibration cost is 1/3 spent on a flag the watcher never releases.

**N2 (P2, real, and it interacts with the consensus-accepted `record(ans, version)` fix): `check_row`'s appended line can carry a *stale* `risk_checks` entry that `check_valid` then counts, because `carry_forward`'s "the new line's own answer wins" (ledger.py:207-209) uses `setdefault` — which is correct — but the *new* line's own answers were merged by `check_row` via `new.setdefault("risk_checks", {}).update(got)` (service.py:434) BEFORE `carry_forward` runs inside `_append`.** Trace it: `check_row` builds `new` from the stale line `l` (which may already carry `risk_checks` from an earlier pass, copied by `json.loads(json.dumps(l))`), then `.update(got)` overwrites those keys with the fresh answers — good. Then `_append` → `carry_forward(lines, earlier)`: for the same moment_id, earlier lines' `risk_checks` are applied with `setdefault(f, c)` — since `new` already has those keys (its own fresh answers), `setdefault` keeps the fresh ones. Correct. **But** the fresh answer's `prompt_version` is stamped by `record(ans, version=PROMPT_VERSION)` — the *default* — while `check_row` calls `flagcheck.record(...)` with no version argument (service.py:426). So the watcher always records under `flagcheck/1`. If the sharpened accusation answers ever enter the ledger via a future watcher change, they'd be mis-stamped — but today the watcher only asks RELEASE_ON_CHECK flags, never accusation, so the default is always right. Latent, one-argument-deep. Nobody caught that the safety of the default depends on the watcher never asking a sharpened flag; the guard is convention, not code.

**N3 (P1→P2, the one I'd actually fix): `check_once`'s skip-optimization can starve retries when the ledger is unchanged but a retry comes due — no, wait, it can't: `due = min(self.check_next.values())` (service.py:472) is checked *outside* the seen-comparison (service.py:473), so a due retry forces the read. Correct. But the *inverse* has a hole: `self._check_seen = seen` is only set when `len(todo) <= CHECK_INFLIGHT - len(self.check_inflight)` (service.py:494-495) — i.e., when everything due fits. If it doesn't fit, `_check_seen` keeps its OLD value; next loop, `seen == _check_seen` (ledger unchanged) AND `clock() < due` (no retry due) → early return (service.py:473-474) — **but there were rows left in `todo` that were never started and never recorded as waiting.** They'll be picked up next loop only because `_check_seen` is stale... no: next loop, `seen` (unchanged ledger) == `_check_seen` (old value, also unchanged) → and `due` is inf (no retries) → early return. The leftover rows wait until the ledger changes or a retry comes due. With CHECK_ROWS=8, CHECK_INFLIGHT=4, and a 12 h window of flagged rows, this is the *common* case at startup: the ledger is静止, 8+ rows are due, 4 start, and the other 4+ wait for... nothing. They wait until some OTHER row's answer appends to the ledger (changing size/mtime) or 10 min (CHECK_RETRY_S) — no, they have no `check_next` entry, so `due` stays inf. **They wait until the ledger's next append.** At 3 a.m. with no new uploads, a backlog of flagged rows drains one-LEDGER-CHANGE-at-a-time, not one-loop-at-a-time. This is a real throughput bug in the steady state, nobody caught it, and it's exactly the kind of thing the "every 30 s" claim (service.py:12) promises.**

Let me double-check N3 against the code once more, because it's my only new P1-adjacent claim. service.py:471-499:

```python
with self.clock_lock:
    due = min(self.check_next.values(), default=float("inf"))   # 472 — computed BEFORE the seen check? No:
if seen is not None and seen == getattr(self, "_check_seen", None) and self.clock() < due:
    return 0                                                    # 473-474 — early return
```
`due` is computed at 472, used at 473. A due retry (check_next populated) makes `clock() < due` false → no early return → read proceeds. Good.

Then, inside the second `clock_lock` block (484-499): if `len(todo) <= CHECK_INFLIGHT - len(inflight)`, set `_check_seen = seen`. Suppose 12 rows due, room = 4: `_check_seen` NOT updated (stays at, say, the value from a previous smaller pass — or absent, `getattr(..., None)`). Next loop: `seen` == `_check_seen`? If `_check_seen` was never set, `getattr` returns None, and `seen is not None` → `seen == None` is False → no early return → proceeds. So the FIRST backlog pass works. But after the first pass where everything-due-fits (setting `_check_seen`), then more rows arrive... they'd change the ledger (new lines → new size/mtime) → `seen != _check_seen` → proceeds. The stuck case: `_check_seen` set at time T (everything due fit), ledger unchanged, but MORE than CHECK_INFLIGHT rows due at T+30s that were NOT due at T. Can that happen? Rows become due when: (a) new ledger lines (changes `seen` — not stuck), (b) `check_next` expiry (changes `due` — not stuck), (c) `check_inflight` frees up — **(c) is the hole.** At T, 4 rows are inflight, 0 in todo, `_check_seen = seen(T)`. At T+30, those 4 finish (inflight → 0), their answers appended (ledger changed → seen differs) — unless they recorded nothing (all unanswered → `check_next` set → due changes). Either way the guard breaks. What if the 4 inflight rows' appends happen between T and T+30 but the ledger's size+mtime... appends always change both. So (c) always breaks the guard too. **N3 is actually closed by the same events that free the capacity.** Downgrade N3 to a note: the skip-optimization is correct because every capacity-freeing event also invalidates the guard. Good — I almost shipped a wrong P1. This is why you re-trace.

So the honest new-findings list: N1 (accusation probes in the watcher's recurring calibration — wasted third of the calibration, and 1/3 of its start-up blocking latency) and N2 (the watcher's prompt_version stamping is convention-guarded, not code-guarded). Both P2. Neither ship-blocking.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| ledger.py (release logic, carry_forward, effective_risk) | 9.2 | 9.3 | Both reviewers + my own re-trace converge: the release gates are exactly the ruling's. N2's convention-guarded version stamp is the only deduction. |
| flagcheck.py (ask/calibrate/record/remeasure) | 8.8 | 8.9 | The `record(ans, version)` fix (mine, implemented) closes the stale-version trap; N1's wasted accusation probes in the watcher's calibration is the remaining deduction. |
| service.py (check loop) | 8.5 | 8.8 | The skip-optimization I doubted in Cycle 1 (B3's "every 30 s is false during calibration") survives re-trace; the inflight/retry/seen-guard interaction is correct (N3, verified then self-refuted). Calibration blocking the loop stays the deduction. |
| stats.py | 9.0 | 9.0 | Unchanged; the 12 h event scan is fine at this scale (qwen's N+1 noted, not actionable). |
| providers.py (reviewed by others, not me) | — | 8.5 | On qwen's + muse's evidence: the router's fail-closed paths are right; the duplicate-call and spend-before-cache notes are P3. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none. Both Cycle-1 reviewers' "no P0" conclusions survive; my own re-trace of the one candidate (N3) self-refuted.

**P1 HIGH**
- None. (N3 was my candidate; it is closed because every capacity-freeing event — an answer appended, or a retry recorded — also invalidates the `_check_seen`/`due` guard. service.py:471-499.)

**P2 MEDIUM**
1. **Watcher's daily calibration spends 8/24 probes on accusation, which the watcher never releases** (flagcheck.py:86-121, 271-302, 316-320; ledger.py:212). Cost is cents; the real cost is 1/3 of the calibration's *latency* blocking the check loop at start and every 24 h (service.py:457-463). Fix: `watcher_checkers` calibrates on `RELEASE_ON_CHECK` probes only, or the ruling-40-P2 sharpened probes replace them once accusation joins the release set.
2. **`record`'s prompt_version safety is conventional, not enforced** (flagcheck.py:305-313; service.py:426 calls it with the default). If the watcher ever asks a sharpened flag, answers are mis-stamped `flagcheck/1` and the adapter counts them under the wrong definitions. Fix: `check_row` passes the version matching the prompt it asked, or `ask` returns the version it used.
3. **`miners`-from-ledger shrinks the checker pool on any future re-mine by a flagcheck-chain back-end** (service.py:479-482; flagcheck.py:241-247). Silent: `checkers` → [], nothing checked, logged only at calibration. Fix: log at `check_once` when `checkers` is empty for a row, or scope `miners` to `mined.pass == "moment"`-style lines.
4. **`published_at`-None sort fragility** (service.py:486-493): the sort's type-safety depends on the expiry gate's position. Fix: `str(l.get("published_at") or "")` is already the key — it IS safe today; add a comment or a test pinning the ordering dependency.
5. **Calibration runs inside the 30 s loop thread and blocks it** (service.py:457-463; flagcheck.py:271-302): the "every 30 s" docstring (service.py:12) is false during the start-up and daily calibration. Accepted as by-design (muse's consensus note); document it in the docstring.

**P3** — qwen's spend-before-cache-write; duplicate concurrent calls for the same prompt; stats' 12 h event scan; the flock in `ledger.append` redundant-but-safe under the single-service guarantee.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Make the watcher's calibration ask only the flags it can release** (P2 #1): it simultaneously cuts the check loop's start-up and daily blocking latency by a third, removes the only wasted Heimdall calls in the hot path, and — when accusation's sharpened answers eventually earn release — forces the `record`-version question (P2 #2) into the open, where it belongs, instead of leaving it as a convention.

## 7. PRODUCTION READY?

**Yes, with two conditions.**

The diff does what ruling 40 P1/P2 says, fail-closed at every gate I and the other two reviewers could construct, with the Cycle-1 consensus fixes (the skip-optimization, the version-stamped `record`, the always-string sort key) implemented and tested. Both other reviewers' "no P0" verdicts are correct, and my one new P1 candidate self-refuted on re-trace — the strongest evidence yet that the concurrency design (one service, one `wlock`, `carry_forward` inside the lock) is genuinely closed.

Conditions:
1. **Ship with P2 #1** (calibrate only the releasable flags, or document that 1/3 of the calibration is accusation-reserved): it is the only finding that costs the hot path *latency* rather than just correctness-fragility, and the ruling's own P2 makes the accusation probes' eventual replacement mandatory anyway.
2. **Ship with P2 #2** (the version stamp): one argument, one line, and it converts the adapter's "counts only the current PROMPT_VERSION" guarantee from a convention into code — the same class of trap the Cycle-1 consensus already fixed once (`record(ans, version)`); finish the job at the call site.

Everything else — the `miners`-pool shrink, the sort-key coupling, the calibration's blocking — is documented-fragile, not wrong, and the 238-test suite pins the behaviors that matter.