# heimdall_glm (z-ai/glm-5.3-flash, 168.4 s, $0.004, finish stop)

# heimdall_glm — CYCLE 2 REVIEW (pp-ingest, probe-claim uptake, diff a2a9386d → working tree)

Scope: the change under review is the 12-line diff to `pipeline/ingest/downsignal.py` (signature check, `probe_kw`, the `probe_due` call, the snapshot field). Everything else is context. The builder's diff (heimdall_health.py 11ed255f) is read-only, not under review. I re-walked the probe life cycle against the builder's diff line by line; the other reviewers' Cycle 1 outputs are addressed below.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting, against my Cycle 1 output (which was truncated at the `load_module` check — my reply hit its length limit mid-sentence, so my Sections 2–6 never existed):

- **Muse's table of module versions** (new / old / broken / missing → `takes_who`, `probe_kw`, call, result). I had the first three rows implicitly but never wrote the fourth (`self.hh is None` → `tick()` returns at once, `probe_kw` irrelevant). Their table is the cleanest statement of the fail-closed matrix; I missed writing it.
- **Muse's `__wrapped__` note**: `inspect.signature` follows the `__wrapped__` chain, so a future decorator without `functools.wraps` would show the wrapper's signature. I said "plain function, sound" and stopped; they named the one mechanism that could make the check lie. I did not.
- **Muse's observation that the check is defense-in-depth** — for a plain function loaded via `spec_from_file_location` + `exec_module`, `inspect.signature` cannot raise in CPython 3.10+; the `except` is for future shapes (a `functools.partial`, a C wrapper, a non-callable). I hedged ("can raise ValueError for unresolvable annotations") without noting that for *this* module, as loaded, it cannot. Their framing is more precise than mine.
- **Qwen's test-coverage observation** (taken into the consensus): the fallback path — `inspect.signature` raising — had no test. The consensus took it and it now exists (`test_a_probe_due_whose_signature_cannot_be_read_is_called_without_a_name`, in the 271-test inventory). I did not notice the gap.
- **Qwen's "no race conditions" paragraph**: `probe_kw` is written once in `__init__` (single-threaded, before the signal thread starts) and only read in `tick()` (the signal thread). I never stated the threading argument; they did, and it is right — `Service.__init__` constructs `DownSignal` before `run()` starts the threads (service.py:98, 690-691), so there is no publication race either (the `Thread` constructor's start() gives the happens-before).

Nothing in their outputs contradicts anything I said. My truncated review agreed with their verdicts on the three questions; the consensus record confirms it.

## 2. WHERE DO I AGREE OR DISAGREE?

**Q1 — the signature check.** Agree with all three, with one sharpening.

- Muse: "for a plain Python function, `inspect.signature()` never raises TypeError/ValueError in CPython 3.10" — agree, and it is the stronger claim: the except clause is dead code *today*, live only for future module shapes. One caveat muse missed: `inspect.signature` on a function whose `__signature__` is set to a non-Signature object raises TypeError — and the consensus's new test pins exactly that (a `__signature__` that is not a Signature). So the except clause is not dead *in the test's world*; it is dead only for the as-shipped module. Both statements are right; the test exercises the fallback by injecting the one defect that triggers it. Good.
- My Cycle 1 caveat 2 (positional-only `who`) — muse agreed it is theoretical; the consensus recorded it as "fail-closed and visible, not silent" (a TypeError inside `_call` → `_fail` → live.json at once, STATE after 30 min). I agree with that reading: `_call`'s broad except (downsignal.py:188-190) catches it, `_fail` records a stable text, and `check_notice` raises the notice after SIGNAL_NOTICE_S. It is not silent. I withdraw nothing; I note the consensus's framing is better than my "silently disable" — it is *visible* within 30 minutes.
- My Cycle 1 caveat 1 (the check is made once at `__init__`) — the deployment model answers it: the module is loaded once per process; a new module version arrives only via restart, which re-runs `__init__`. The consensus recorded it as "by design". Agree.

**Q2 — the probe life cycle.** Agree with muse's "no — and this is the critical correctness claim", and with their four-point walk. Two points deserve more than agreement:

- **The kept report (C2-1) now lands inside a slot the claim already stamped.** This is the one place the claim *could* have changed semantics, and it does not, because of the builder's answer-anchored re-stamp: `probe_result` re-stamps `last_probe_utc` when the report lands, so a kept report that succeeds moves the next-due *later* than the claim; a kept report that expires (dropped, `probe_reports_lost`) leaves the claim's stamp, so the slot is spent from the claim — exactly the builder's docstring. Either way there is no double-probe and no lost slot. Muse's step 3 says this; I said it in Cycle 1; the consensus recorded it. It is the load-bearing fact of the whole change and all three reviewers independently derived it. That is as strong as cross-validation gets.
- **The "probe not made" path (downsignal.py:243-246) interacts with the claim.** When every probe back-end is skipped/unavailable such that `AllBackendsFailed.outage` is True and nothing was called, `res = (None, ...)` → `probes_not_made` → no `probe_result` is sent → the slot stays spent from the claim. The change note says this explicitly ("a probe this watcher cannot make ... spends the slot from its claim"). Correct per the builder's contract, and it is the *right* semantics: the claim means "I am probing now"; if the prober could not call anyone, the slot is still consumed, which prevents a second prober from re-probing into a slot the first already owned. Muse's step 2 covers this ("no `probe_result` is ever sent. The slot is still spent"). Agree. One nuance neither of us wrote: this makes the *watcher's* probe cadence slightly bursty — a systematically-skipped probe back-end (e.g. both probe back-ends' keys missing) yields one claim per PROBE_EVERY_S with no report, forever, and `probes_not_made` climbing. That is observable in `snapshot()["counts"]` and is the designed failure mode, not a defect.

**Q3 — any path where `who` makes a call fail.** Agree with muse's exhaustive table; nothing to add. The one case muse's table's "Missing module" row implies but does not state: when `load_module` raises, `self.hh` is None and `tick()` returns at downsignal.py:153-154 *before* any `probe_due` call — so `probe_kw`'s content is irrelevant. Their table's "N/A" is exactly right.

**Recorded-not-changed items** (consensus): muse's BaseException-in-`_call` (agree: older than this change, same convention as `Service._loop`, KeyboardInterrupt reaches the main thread only); my two P3s (agree: recorded, fail-closed, deployment-model-consistent); my P2 note on the ~120 s + duration cadence under systematic report loss (agree: the builder's semantics, accepted). All correctly recorded, none warrants a change.

**Disagreements: none.** I have no finding where I think a Cycle 1 reviewer was wrong.

## 3. NEW FINDINGS FROM THIS REVIEW

Three things the combined Cycle 1 outputs did not state:

**N1 (P3, observation, no change): the snapshot's `probe_claimed_as` is the *intent*, not the *fact*.** `snapshot()` (downsignal.py:360) reports `self.probe_kw.get("who")` — what this watcher *would* claim as. What the shared state actually recorded (`last_probe_by`) is in the module's state file, which this watcher never reads (by design: the module's API only). So an operator comparing `probe_claimed_as: "pp-ingest probe"` against the state file's `last_probe_by: "pp-selectid probe"` (the builder's router won the slot) sees an apparent mismatch that is not one. The field name invites the misreading. A one-line docstring note, or renaming the key `probe_claims_as`, would prevent the question. Cosmetic; record, do not change.

**N2 (P3, observation): the claim makes `probe_due` a *writing* call, and `_call`'s failure path treats it like any other.** Before this change, `probe_due` was read-only; a failure to read it was "the signal is not read". Now a `probe_due` that raises *after* the module stamped the slot (e.g. `_save` succeeds, then something later in the `with _Locked` block raises — not possible in the builder's diff as written, since the stamp+save+return is the last thing in the block, but a future module edit could) would leave the slot claimed while this watcher reports "not read" and never starts a probe. With the builder's diff as committed, the stamp and the True are atomic under the flock, so this cannot happen today. Recorded for the future: the coupling between "probe_due returned True" and "the slot is stamped" is now load-bearing, and it holds only by the builder's discipline. If a future heimdall_health stamps-then-raises, this watcher's `_probing()` guard clears, the next tick's `probe_due` returns False (slot spent, <PROBE_EVERY_S), and the slot is silently skipped — one lost probe slot per incident, fail-closed, invisible except in the module's own state. Not this change's defect; noted for the next builder audit.

**N3 (P3, test-coverage): the new tests pin the watcher's side; nothing pins the *pair* end-to-end.** The three new tests (test_signal.py: `test_the_probe_claims_its_slot_by_name_and_a_slot_claimed_by_another_prober_is_left_alone`, `test_a_module_without_the_claim_is_called_without_a_name`, `test_a_probe_due_whose_signature_cannot_be_read_is_called_without_a_name`) exercise the watcher against a *stub* module. The builder's test pins the module's side (two probers, one slot; the claimer's name survives the report). Neither suite runs the real 11ed255f module against the real watcher. That is the integration seam the change exists to close, and it is covered only by the 02:27 ET deployment + this restart. Given the module is loaded by path from another worktree (`providers.json` down_signal.module → /home/ultron/worktrees/pp-selectid/pipeline/heimdall_health.py), a future builder-side rename or signature change would be caught by... the watcher's own `load_module` API check (downsignal.py:55-59) for the seven required names, but *not* for the `who` parameter — which would silently fall back to no-claim (two probers, two probes per slot, the pre-R12 behavior). That failure mode is graceful and exactly what the fallback exists for, but it is *silent*: nothing would log "the builder's module lost its who parameter; the claim is not being taken". `probe_claimed_as` in the snapshot would show `None`, which is the only trace. Suggest (P3, next cycle, not a condition): when `takes_who` is False while the module otherwise loads, log one line — "probe_due takes no who: the claim is not taken (pre-R12 module?)" — so the graceful fallback is a *visible* graceful fallback. This is the one genuinely new, actionable item of this cycle.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| The change itself (signature check, probe_kw, call, snapshot) | (truncated; verdict given: correct, minimal, fail-closed) | 9.5/10 | Unchanged verdict; N1/N3 are the only deductions, both P3, both observability-of-fallback, neither a defect |
| Probe life-cycle interaction (report-first, `_probing()`, C2-1 kept report, claim-anchored spent slot) | (truncated) | 10/10 | All three reviewers independently derived the same semantics; the C2-1/claim composition is exactly the builder's contract; no reviewer found a divergence |
| Law compliance (L-x, L-l, L-j, L-m, L-u, L-h, L-e, L-v, secrets, freeze) | (truncated) | 10/10 | Qwen's walk is complete and I concur: the change touches none of the law-relevant paths; the probe role's breaker-free, no-cache, no-transport-retry shape is unchanged |
| Security | (truncated) | 10/10 | No new input, no new secret, the override drill path unchanged; `who` is a constant string built from WHO |
| Backend quality | (truncated) | 9.5/10 | Threading argument (qwen) is sound; the one deduction is N3's silent-fallback observability |
| Tests | (truncated) | 9/10 | 271 collected, the three new ones pin the watcher's side including the injected-`__signature__` fallback; the deduction is the missing cross-worktree integration pin (N3) — covered only by deployment |

No score changed *direction*; the cycle added confidence and three P3 observations, no defects.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL: none.**
**P1 HIGH: none.**

**P2 MEDIUM: none.** (I considered promoting N3's silent-fallback log line, but the failure mode is graceful, correct, and observable in `probe_claimed_as`; it does not meet the P2 bar.)

**P3 (record, next cycle, not conditions):**
1. **downsignal.py:119-123** — when the module loads but `takes_who` is False, log one line (e.g. "probe_due takes no who: the slot claim is not taken (pre-R12 module 125e7381?)"). Today the graceful fallback is silent; the only trace is `probe_claimed_as: null` in the snapshot. One line, one cycle, closes the only observability gap the change has.
2. **downsignal.py:360** — `probe_claimed_as` reports the intent, not the state file's `last_probe_by`; note it in the field or the STATE doc so an operator does not read the (correct) mismatch as a defect. (N1)
3. **Coupling note for the next builder audit** — "probe_due True ⇔ slot stamped" is now load-bearing and holds by the builder's discipline (stamp+save+return atomic under the flock); a future stamp-then-raise would silently skip one slot per incident. (N2)
4. **Cross-worktree integration** — the watcher's tests stub the module; the builder's tests stub the watcher; the real pair is proven only by deployment. If either side's test suite could import the other's real module, the seam would be pinned. (N3)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Log one line when the module loads but `probe_due` has no `who` parameter — it converts the change's only silent path (the graceful no-claim fallback) into a visible one, and it is the difference between "the claim silently stopped working" and "the claim stopped working and someone knew within one tick".

## 7. PRODUCTION READY?

**Yes, with one condition.**

The change is correct, minimal, fail-closed, and its one subtle interaction (the C2-1 kept report landing inside a claim-anchored slot) is right by the builder's contract and independently derived by all three reviewers in Cycle 1. The signature check is sound for the module as loaded; the fallback is defense-in-depth whose one realistic trigger (a non-Signature `__signature__`) is now pinned by test; no path exists where `who` breaks a call on either module version, and the missing-module case never reaches the call.

**Condition (the only one):** before or at the next restart, add the one-line log when `takes_who` is False (downsignal.py:122-123) — the silent-fallback observability of N3/P3-1. It is three lines of code, it does not touch the call path, and it is the only thing between "the builder renames the parameter in a future module" and "nobody notices for a week while two probers double-probe every slot".

Everything else — N1's field-name clarification, N2's coupling note, N3's cross-worktree test — is recorded for the next cycle, not a condition. 271 tests collected; the three new ones cover the watcher's side of the contract including the injected-`__signature__` fallback. Ship it, log the fallback, and the change is done.