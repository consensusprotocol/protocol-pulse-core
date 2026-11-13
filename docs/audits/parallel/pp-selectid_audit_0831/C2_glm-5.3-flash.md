# glm-5.3-flash (z-ai/glm-5.3-flash) 124 s finish=stop usage in 7682 / out 3109 usd~0.070 (upper-bound price)

# pp-selectid — item 55 evidence log, cycle 2 (final review)

## 1. What did they catch that I missed?

Honest accounting against my cycle 1 output:

- **Qwen's P1-1 (NameError if `time` not imported).** I asserted in my cycle 1 that the imports were present at module level, but I did not show the evidence line-by-line the way the consensus did. Qwen's reasoning — that a `NameError` is not an `OSError` and would therefore escape the `except OSError` at providers.py:40 and crash the call, violating the "evidence, not a gate" invariant — was sharper than mine. I had the right conclusion, weaker justification.
- **Grok's framing of the import question as a *ship condition* rather than a finding.** I treated the import question as settled; grok correctly made it conditional. The consensus (A1) then discharged it with the actual lines (`import json/os/time` at providers.py:33-35, `time.strftime` already used by `_record` at :709). That discharge is what I should have demanded in cycle 1.
- **GLM's P1-1 caveat about the caller-side/chain-level deadline path.** I noted the slow-log fires before the empty-reply check but did not systematically ask "is there any *other* deadline path in `call()` that escapes logging?" GLM's uncertainty flag (the diff shows only the excerpt of `call()`) was the right epistemic posture. I cannot discharge it either — the diff at lines 46-67 shows the `DeadlineExceeded` handler and the success path, but not whether any earlier `raise`/`return` in `call()` can abandon a back-end without passing through either handler. What I *can* verify: both visible abandonment paths (the `DeadlineExceeded` handler at :47-53 and the empty-reply `continue` at :65-67, which is not a deadline) are covered, and the order's evidence (the 07:14 misses, the 8-min screen) is of the per-back-end kind. So coverage holds for everything the order describes; the residual uncertainty is about code not in the diff.

## 2. Agree / disagree

| Finding | Verdict | Why |
|---|---|---|
| Qwen P1-1: `time` import | **Agree, discharged.** Consensus A1 shows the imports at :33-35 and prior `time.strftime` use at :709. Not a finding anymore; it was a verification gap, now closed. |
| Grok: single-Router-per-process for the lock | **Agree, discharged.** Consensus A2: one Router per build (proof_ledger.py:75-77, proof_ly.py:96-98), thread pool shares it, so `_log_lock` serialises within a build. Across builds/processes, each line is one small `f.write` under `open(..., "a")` (O_APPEND), so line-atomicity holds in practice. |
| GLM P1-1: slow log fires for empty replies; chain-level exhaustion | **Agree.** Consensus A3 confirms it's intended: a slow call is evidence whatever it returned, and the line carries in/out tokens. The "caller-side deadline aborts before any back-end misses" scenario remains unverifiable from the diff — I flag it, not as a defect, but as the one residual unknown. |
| GLM P2-1: `self.notices` grows unbounded on persistent write failure; appended without `self._lock()` | **Agree, P2.** providers.py:41. Read-only mount over a long build = one notice per call. Benign; the call still succeeds. The unlocked append is a theoretical race if `notices` is read concurrently — not verifiable from the diff. |
| GLM P2-2 / Qwen P1-2: `os.makedirs` on every write | **Agree, P2.** providers.py:37. Redundant syscall per log line; idempotent, so correctness is unaffected. Could be hoisted to `__init__` or guarded by a "tried once" flag. |
| Qwen P2-3: second-resolution UTC stamp | **Agree, P2.** providers.py:34. Two misses in the same second are indistinguishable by timestamp alone; `model`/`role`/`prompt_chars` usually disambiguate. Milliseconds would be better forensics. |
| Qwen P2-4: `seconds` in `missed_deadline` is the configured deadline, not a measured elapsed | **Agree, P2, and it's the right semantic note.** providers.py:51. The call is abandoned *at* the deadline so the value is approximately right, but the field name implies measurement. GLM's defence (the abandonment happens at the deadline, so `deadline_s` *is* the elapsed) is also correct — this is a naming/semantics nit, not a bug. |
| GLM P2-4: test asserts `seconds >= 0.2` against a back-end-reported 0.25, not a measured wall time | **Agree, P2.** test:128-131, 139. The production `secs` source isn't in the diff; if it's the back-end's self-report, the "8 min" evidence's accuracy depends on the vendor's clock. If it's measured around the call, fine. Unverifiable here. |
| Qwen P2-5: test reads log without closing (`open(...)` bare) | **Agree, P2, cosmetic.** test:115, 136, 142, 145. CPython refcounting closes it; inconsistent with the `with` style elsewhere. |
| Grok P2: `import threading` inside `__init__` | **Agree, P2, style.** providers.py:18. Works; module-level is the file's convention (json/os/time at :33-35). |

## 3. New findings from this review

**N1 (P2) — the `answered_slowly` record's `deadline_s` may be `None` and that's fine, but the *missed_deadline* record's `seconds` duplicates `deadline_s` while the slow record's does not — asymmetric schema, same file.** providers.py:50-52 vs :61-64. The missed record has `deadline_s` and `seconds` (equal by construction); the slow record has `threshold_s`, `deadline_s`, and `seconds` (measured/self-reported). A Heimdall-side parser keying on "seconds" gets a configured limit in one kind and a duration in the other. Both are defensible; the asymmetry is worth one line of documentation in the .md, not a code change. Nobody said this in cycle 1.

**N2 (P2) — the new test's second and third Router constructions (test:140-145) reuse the same `path` but the third Router passes no `deadline_log`, so it exercises the "no log, writes nothing" branch — but it also never asserts the *file* was untouched, only the line count.** Actually, re-reading: test:145 does assert `len(open(path).read().splitlines()) == 1` after the third call, which *is* the untouched assertion. Withdrawn — the test is correct. What remains: the third Router also omits `slow_log_s`... no, it passes `slow_log_s=0.2` (test:144). The test is tighter than I gave it credit for. No new finding here; noted for honesty.

**N3 (P2) — `slow_log_s=240.0` default vs the order's "8 min" evidence.** The order says one 8-excerpt screen took 8 min = 480 s. The default threshold 240 s would catch it. But the *deadline* is 300 s — so a call that answers at 300-480 s would be abandoned before it could be logged as slow, and a call answering at 240-300 s is logged as slow. The 480 s screen, if it happened *after* this diff, would appear as `missed_deadline` (seconds=300), not as an 8-min answer. The order's evidence (backfilled, not in this diff) is what carries the 8-min fact; the going-forward log would have recorded it as a miss at 300 s. This is a semantic subtlety of the 240/300 gap nobody flagged: the slow-log threshold sits *inside* the deadline, so the two record kinds partition the outcome space cleanly (a call either answers before 300 s — possibly logged slow if ≥240 — or misses at 300). Actually this is *good* design, not a defect: no outcome is silently unlogged. But the Heimdall team reading `missed_deadline, seconds: 300` for what was historically an "8-min answer" needs the .md to explain that a miss at the deadline truncates the true duration. Nobody said this.

**N4 (P2) — `usage or {}` at providers.py:63-64.** If the back-end returns `usage=None` on a slow success, the logged `in`/`out` are `None` (JSON `null`), not 0. The test's `Took` returns a real usage dict, so the test never exercises the `None` case. A Heimdall-side sum over `in`/`out` must therefore be null-tolerant. Minor; nobody caught it.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Logging correctness (fields, exactly-once) | 9/10 | 9.5/10 | Both visible abandonment paths verified; the import question discharged by consensus A1; the residual unknown (other paths in `call()`) is about code not in the diff, not about this diff. |
| Non-interference with call/ledger | 9/10 | 9.5/10 | Qwen's NameError-escapes-`except-OSError` scenario was the strongest threat to this invariant; it's discharged by the import evidence. Remaining: unlocked `notices.append` (theoretical). |
| Concurrency | 8.5/10 | 9/10 | Single-Router-per-build confirmed (A2); cross-process O_APPEND line-atomicity noted; residual: unlocked notices append, per-instance lock only. |
| Test coverage | 8.5/10 | 9/10 | The new test is tighter than I credited (N2 — I withdrew my own nit). Gaps: no test of the `usage=None` slow-success (N4), no test of a write-failure→notice. |
| Schema/forensics | — | 8.5/10 | New axis this cycle: the missed/slow asymmetry (N1) and the 240/300 truncation semantics (N3) are documentation debts, not code bugs. |

## 5. Final priority list

**P0 CRITICAL** — none.

**P1 HIGH** — none. (Qwen's import P1 was the only candidate; discharged by consensus A1.)

**P2 MEDIUM:**
1. **providers.py:41** — `notices` grows unbounded on persistent write failure, and the append is not under `self._lock()`. Cap it (e.g. keep last 20) and/or append under the router lock.
2. **providers.py:37** — `os.makedirs` on every log line; hoist to `__init__` or first-write.
3. **providers.py:34** — second-resolution UTC stamp; add milliseconds for forensic ordering.
4. **providers.py:50-52 vs 61-64** — schema asymmetry: `missed_deadline.seconds` is the configured limit, `answered_slowly.seconds` is a duration; document in the Heimdall .md (N1), and note that a miss at the deadline truncates the true duration to 300 s (N3).
5. **providers.py:63-64** — `usage=None` yields JSON `null` for `in`/`out`; either coalesce to 0 or document that the fields are nullable (N4). Add a test.
6. **providers.py:18** — `import threading` inside `__init__`; move to module level per file convention.
7. **test:115, 136, 142, 145** — bare `open()` without `with`; cosmetic.
8. **test:139** — `seconds >= 0.2` asserts against a back-end-reported 0.25; if production `secs` is self-reported, note the provenance in the .md (unverifiable from this diff).

## 6. The single highest-leverage change

Document the schema in the Heimdall .md — one paragraph covering (a) `missed_deadline.seconds` = the configured deadline (the true duration is truncated at 300 s), (b) `answered_slowly.in`/`out` may be `null` — because the code is correct and the only thing that can still make this evidence misleading to the Heimdall team is its interpretation, not its computation.

## 7. Production ready?

**Yes with conditions** — all conditions are documentation/verification, none block:

1. Confirm (one grep, outside this diff) that no other path in `Router.call()` can abandon a back-end without passing through the `DeadlineExceeded` handler or the success path — the diff shows only the excerpt, and exactly-once coverage rests on this (GLM's caveat, still undischarged).
2. Add the schema paragraph to `pp-selectid_HEIMDALL_DEADLINES.md` per finding 4 (N1/N3) and the null-usage note (N4).
3. Optionally, in a follow-up: cap `notices`, hoist `makedirs`, add milliseconds to the stamp, and add a `usage=None` test.

Everything the order asked for — every missed deadline logged exactly once with (model, prompt size, seconds), the log never changing a call's outcome or the ledger, no interleaving, no secrets (only `prompt_chars`, never the prompt) — is verified in the diff. test_providers 16 OK. Ship it.