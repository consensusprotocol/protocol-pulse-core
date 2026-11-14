# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 241.0 s, $0.025, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (diff a2a9386d → working tree)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting:**

My Cycle 1 was the longest (468s) and most exhaustive — I produced the 4-row truth table (new/old/broken/missing module), the report-first ordering proof, the claim-anchored vs answer-anchored analysis, and the `__wrapped__` decorator note. The other two reviewers did not catch anything I missed on the diff itself — all three answered the three questions identically: signature check sound, lifecycle unchanged, no failing path.

What they *did* add that I should credit:

- **GLM's positional-only `who` caveat (P3):** I checked parameter *name* presence but did not explicitly note the positional-only edge (`def probe_due(..., who, /)`). GLM did. My analysis implicitly covered it — `_call` catches `Exception` so it would be "not read" / fail-closed — but I should have named it. It's theoretical (builder's diff shows `who=""` as normal param) but worth stating.
- **GLM's staleness caveat (P3):** The check is cached at `__init__` and never re-evaluated on reload. I noted "no concurrent mutation" but did not explicitly call out the deployment constraint ("module loaded once per process, restart takes up new version"). GLM stated it cleanly.
- **Qwen's conciseness:** Qwen's review was correct but added nothing beyond the consensus. No miss on my part there.

**What nobody caught that I did catch:** The `functools.wraps` / `__wrapped__` chain subtlety, the exhaustive 4-row table, and the `_probing()` + claim interaction with the C2-1 kept-report window were unique to my review.

**Net:** No substantive finding from the other models that invalidates or materially amends my Cycle 1 verdict. Two P3 caveats worth recording, both already fail-safe.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | Verdict | Why |
|---|---|---|---|
| Signature check sound (plain function, TypeError/ValueError fallback) | All three | **Agree** | `load_module` via `spec_from_file_location` + `exec_module` yields plain function. `inspect.signature` on it never raises in CPython 3.10, but the except is correct defense-in-depth for `partial`/C-wrapper/broken module. |
| `takes_who` cached at `__init__`, stale on reload | GLM P3 | **Agree** | True, but by design: module loaded once per process, restart picks up new version. Documented constraint, not a bug. |
| Positional-only `who` would raise TypeError inside `_call` | GLM P3 | **Agree** | Would be caught by `_call`'s `except Exception` → `_fail()` → "not read" (live.json at once, STATE after 30 min). Fail-closed, visible. Theoretical — builder's diff is `who=""` normal param. |
| Claim leaves lifecycle unchanged (report-first, `_probing()` guards process, claim guards fleet, C2-1 kept report inside claimed slot) | All three | **Agree** | Verified step-by-step. No reorder, no new race (`probe_kw` set once single-threaded, read only in signal thread). |
| No path where `who` makes call fail on either module version | All three | **Agree** | Exhaustive table holds. Old module: `probe_kw={}` → no `who` passed. New: `who="pp-ingest probe"` → claimed. Broken sig: fallback to `{}`. Missing module: `hh is None` → `tick()` returns. |
| Qwen P3: test for `inspect.signature` fallback | Consensus Taken | **Agree** | Already added: `test_a_probe_due_whose_signature_cannot_be_read_is_called_without_a_name`. Good. |
| Muse P2 "catch BaseException in `_call`" | Recorded, not changed | **Agree with "not changed"** | Pre-existing, same in every loop. `KeyboardInterrupt` only to main thread; `SystemExit` from builder module would be builder bug. Out of scope for this diff. |
| GLM P2 "systematic report loss → probe every ~120s + duration" | Recorded, not changed | **Agree with "not changed"** | Builder's semantics (claim-anchored), accepted. Not this watcher's bug. |

**No disagreements.** The three reviewers converged completely on the diff.

## 3. NEW FINDINGS FROM THIS REVIEW

Combined analysis reveals nothing new that changes the verdict. One observation worth making explicit for the record (synthesis of all three reviews):

**The claim's interaction with `_start_probe()` failure is intentional and correct, but deserves a one-line comment in the code for future readers.** Currently `downsignal.py:114` says "a claimer that never reports leaves the slot spent from its claim" — good. What could be added (P3, not blocking): a comment at `tick():170` noting that if `_start_probe()` fails to actually make the call (every probe backend skipped/frozen → `answered is None` → `probes_not_made`), the slot is still spent from the claim. This is already handled (no `probe_result` sent, `last_probe_utc` already stamped), but a reader might wonder. Not a bug — just documentation.

**No new P0/P1/P2 found.** The diff is 7 lines of logic + 1 line of observability (`probe_claimed_as` in `snapshot()`), all correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| **Correctness (the diff)** | 10/10 | **10/10** | No change. All three reviewers agree: correct, minimal, fail-closed. |
| **Law compliance** | 10/10 | **10/10** | No change. No law touched. |
| **Security** | 10/10 | **10/10** | No change. No secrets, no injection, no auth. |
| **Backend quality** | 10/10 | **10/10** | No change. No new DB/API/cron/memory risk. `probe_claimed_as` in snapshot is good observability. |
| **Whole-package (pre-existing)** | 9/10 (noted `BaseException`, yt-dlp pinning, spend query) | **9/10** | No change. Pre-existing items recorded, not introduced by diff. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — none.**
**P1 HIGH — none.**

**P2 MEDIUM — none blocking ship.** (Recorded for completeness, not gating:)

- `downsignal.py:184-194` `_call` catches `Exception` not `BaseException` — pre-existing, same in `Service._loop`, not introduced by diff. `KeyboardInterrupt` → main thread only; `SystemExit` from builder module = builder bug. Not changed (consensus).

**P3 LOW — informational, not gating:**

- `downsignal.py:120` positional-only `who` in a future builder module would make `probe_due(..., who=...)` raise `TypeError` inside `_call` → "not read" (fail-closed, visible). Theoretical; builder's contract is `who=""` normal param.
- `downsignal.py:119-123` `takes_who` cached at `__init__` — stale if module reloaded without restart. By design (module loaded once per process).
- `downsignal.py:170` Consider a comment that a claimed slot where `_start_probe()` never actually calls (all probe backends skipped) is intentionally spent from the claim.

**No file:line requires a change before ship.**

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Ship it — the 7-line claim uptake is correct, fail-closed on every module version, and makes two probers do one probe per slot instead of two.

## 7. PRODUCTION READY?

**Yes — ready for production. Deploy on next restart.**

Conditions: None beyond the normal restart (the watcher loads the module once at start, so the restart is what takes up `11ed255f`). No code change required. The 271 tests pass (27 in `test_signal.py` including the three new probe-claim tests: `test_the_probe_claims_its_slot_by_name_and_a_slot_claimed_by_another_prober_is_left_alone`, `test_a_module_without_the_claim_is_called_without_a_name`, `test_a_probe_due_whose_signature_cannot_be_read_is_called_without_a_name`).
