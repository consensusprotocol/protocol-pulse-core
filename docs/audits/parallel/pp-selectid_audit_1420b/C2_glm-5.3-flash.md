# glm-5.3-flash (z-ai/glm-5.3-flash) 68 s finish=stop usage in 9240 / out 2078 usd~0.059 (upper-bound price)

# pp-selectid-1420b — cycle 2 review

## 1. What did they catch that I missed?

- **glm P1-1** (`res["registry"] = True` set before the guarded block): I did not flag that the flag can lie when the guarded save fails. It's a real, if narrow, inconsistency — the record claims the outcomes are in the registry when the save raised. Their G1 rationale (only the `--from-candidate` record's outcome is lost, and that candidate stays open and is retried) is correct, so it's a P2, not a P1.
- **grok's test-coverage note** (no test for a build that raises, or for a second due candidate after the first clamps to 0): fair; I also didn't demand those.
- **qwen's self-refuted P1**: correctly withdrawn by qwen itself; the clamp does make negative `lineups` impossible. Nothing missed there.

## 2. Agree / disagree

- **glm P1-1 → agree, but downgrade to P2.** The scenario (save fails → record says `registry: true` → next run trusts it) is real, but the next run's `run_due` re-tries the still-open candidate anyway; the only lost thing is the *outcome* of the `--from-candidate` try, which is idempotent to redo. glm's own "record stands but lies" framing overstates it: the record's *paid* content (package.json) is intact; only the flag is wrong. G1's reasoning is sound.
- **glm P1-2 → agree it's a P2.** The clamp at diff lines 21–24 caps `judged` at `lineups` and the subtraction can't go negative; the `left > 0` guard at line 66 covers the angle build. I verified: `judged = int(judged or 0)`; if out of `[0, lineups]`, `judged = lineups`; `lineups -= judged` ⇒ `0 <= lineups` always. Total charged across tries + angle build ≤ 8. F2 holds.
- **glm P1-3 / grok P2 / qwen P2 (malformed `found_at` refusal path) → agree, and the new test closes it.** `test_a_malformed_candidate_registry_refuses_the_run_before_anything_is_written` (diff 141–164) now proves: exit 2, "registry" on stderr, the registry file byte-identical, no new `ledger_*`/CANDIDATES.json. This was the one genuinely unverifiable-from-diff item; it's now verified by test. Residual: the test pins `REGISTRY` via `mock.patch.object(PLG, "REGISTRY", reg)` — if the driver reads the registry through anything other than the module global, the test would silently test the wrong file. From the diff I can't see the read site; the byte-identical assertion would catch it only if the patched path is the one actually read. Say: verified *if* `REGISTRY` is the sole access path — plausible, not proven from this diff.
- **grok P1 (F3, all paths non-crashing) → agree, now closed.** The `try/except` around `PK.build` (diff 56–61) returns the 4-tuple; `run_due`'s `outcome(e, "budget", ...)` leaves the candidate as it was (A2); the minimal dict at line 70 covers `last` empty; the guarded block (82–92) covers the post-write failures. The one path I'd still note: inside the guarded block, if `CA.outcome` raises *after* mutating the entry in place, the catch logs and the record stands — the in-registry entry may be half-moved, but the next run's `due()`/`outcome` tolerate any state, so no wedge. P2 at most.
- **qwen P2 (`--from-candidate` judged not clamped) → agree, informational.** Line 47 takes `res["search"]["lineups"]` raw. It's a record field, not a budget control; the F2 clamp governs the due path only. Fine.

## 3. New findings (this review)

- **P2 — `tests/package/proof_ledger.py:44–47` (F4): the `--from-candidate` try's `why` truncates to 300 but `judged` can exceed the truth, and — more substantively — the entry's `fresh` flag is `bool(cand.get("write_seed"))`, which is the *current* seed-eligibility, not whether this try actually used fresh writes.** If the candidate had `write_seed` set by a previous run's fresh try (the flag persists after use per the F2/`fresh_used` machinery), the recorded `fresh: True` may not match what this build did. Informational only — the due path derives `fresh` from the actual try. Nobody flagged this in cycle 1. It's a record-accuracy nit, not a behavior bug.
- **P2 — `test_ledger_build.py:149–164`: the new refusal test's `before`/`after` comparison lists `proof/` but the driver writes into `proof/` only via `out_dir` under it; if the driver creates any scratch (e.g. a `.tmp` registry) before the refusal, the test's "nothing written" assertion would miss it** — except the registry `.tmp` is only written in the guarded block, long after the refusal. Verified consistent from the diff; noting it because the test's strength depends on the driver's first write being `package.json`, which the diff's line ordering (76 before 82) supports.
- **P2 — `candidates.py:11–12`: the sort key is now a tuple whose first element mixes aware datetimes only** (`_at` returns aware; `old` is aware-UTC), so no naive/aware comparison crash — verified. But `_at(x[1]["found_at"])` is evaluated for *every* due candidate on *every* comparison? No — `sorted`'s key function runs once per element; fine. No finding; recorded to close the question.
- **P2 — the guarded block's `CA.outcome` (diff 83–85) runs for `--from-candidate` *in addition to* the outcome already applied... wait, no: in the `--from-candidate` branch (39–47) the old code's inline `CA.outcome` was *removed* (diff 41–43 deleted) and moved into the guarded block.** Verified: the deletion at 41–43 and the addition at 83–85 are the same call, now post-write and guarded. No double-outcome. This closes a question I had in cycle 1.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| F1 (time sort) | good, refusal path unproven | good, proven | the new driver test (141–164) closes the only gap |
| F2 (clamp) | good | good | qwen's negative-`lineups` worry self-resolved; the clamp is airtight |
| F3 (crash safety) | good, outer surface unproven | good | try/except + minimal dict + guarded block; no wedge state found |
| F4 (record shape) | unverified | good, one nit | the `fresh` flag semantics (my new finding) |
| Tests | adequate | strong | 2 new tests target exactly the cycle-1 unknowns |

## 5. Final priority list

**P0:** none.

**P1:** none.

**P2:**
1. `tests/package/proof_ledger.py:44–47` — the `--from-candidate` `candidate_tries` entry's `fresh` reflects `write_seed` (current eligibility), not what this try did; and its `judged` is the build's self-report, unclamped. Informational; consider a comment.
2. `tests/package/proof_ledger.py:73` vs 82–92 — `res["registry"] = True` precedes the guarded save; on save failure the flag lies (glm P1-1, recorded as G1). Accepted; a one-line comment or setting the flag after the block would make the record honest.
3. `test_ledger_build.py:158` — the refusal test's validity rests on `REGISTRY` being the driver's only registry access; not provable from this diff.

## 6. The single highest-leverage change

Move `res["registry"] = True` (line 73) to after the guarded block (or set it to the save's success), so the record's claim about the registry is never false — it's the only remaining place where the record can assert something the code didn't guarantee.

## 7. Production ready?

**Yes, with one condition:** relocate (or truth-ify) the `res["registry"] = True` flag relative to the guarded save — a two-line change. Everything else in the increment is verified from the diff: F1 orders by time across offsets with a zoneless-UTC and missing-oldest rule and refuses on a malformed time before any write (now test-proven); F2's clamp makes exceeding 8 judged line-ups impossible; F3 never closes/rests a candidate on a crash, never loses package.json, and leaves no wedged registry state; F4's record shape is present. All 13 suites pass.