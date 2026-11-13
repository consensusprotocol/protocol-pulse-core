# glm-5.3-flash (z-ai/glm-5.3-flash) 121 s finish=stop usage in 12509 / out 3619 usd~0.092 (upper-bound price)

# pp-selectid-1655 — CYCLE 2 FINAL REVIEW

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **The no-voice fallback site (ruling 3).** I flagged in P1-1 that the "all paths" claim was asserted, not proven, and that the tests only covered first-formed and swapped. That was the right doubt, but I didn't name the no-voice fallback as the concrete second judgment site. The consensus ruling did: `medley()` is called at two sites, and the no-voice one was unchecked. That's the miss — I had the question but not the answer, and the answer was "the fix was incomplete as diffed in C1."
- **The reorder / pool-fill paths.** I said "not verifiable from the diff" and left it there. The C2 diff adds `test_a_reordered_or_pool_filled_line_up_is_skipped_too`, which closes exactly the gap I hedged on. Grok's P2-1 pointed at the same hole.
- **Grok's P2-2 (key() not in diff).** I accepted `key(lu)` on the background's word. Grok was right that it's unverifiable from the diff alone; the consensus answers it (candidates.py:28, `"+".join(lineup)`), which is consistent with the test's expected keys (`"h+y+x"`, `"d+e+f"`), so it's now corroborated.

What I caught that they underweighted: my P1-3 (the all-skipped build shape) was the only finding about what happens when *every* angle's line-up is registered — the C2 diff now shows the answer (`why_none` starting "no angle gave a package: angle 1: ruling 66: a registered candidate (open; ...)" in test_medley.py:293-294), which resolves it.

## 2. WHERE DO I AGREE OR DISAGREE?

**Grok P2-1 (formation-site coverage) — AGREE, now resolved.** The C2 diff shows the fix: `held_map` (package.py:53) is read at both judgment sites — the main loop (line 78) and the no-voice fallback (lines 61-63, where the clip that would complete a registered line-up is `continue`d past and recorded in `note["registered_skipped"]`). The new tests exercise reorder and pool-fill. My Cycle 1 hedge was correct and is now discharged.

**Grok P2-2 (key() undefined in diff) — AGREE, resolved by consensus.** `key = "+".join(lineup)` at candidates.py:28, corroborated by the test expectations. Not a defect.

**Qwen P2-1 (registered silently ignored when candidate is not None) — AGREE, by design.** The C2 diff makes it explicit: `held_map = dict(registered or {}) if candidate is None else {}` (package.py:53) and the docstring (line 49: "A build from a candidate ignores it"). The test at test_medley.py:268-271 proves the candidate's own try is judged even when registered. Correct.

**Qwen P2-2 (refused_only patches os.makedirs broadly) — PARTIALLY AGREE, still a latent fragility.** The guard (test_ledger_build.py:157-164) patches `os.makedirs` globally for the duration of the `with` block. It's safe today because the refusal path only reads, and the driver's first write is `os.makedirs(out_dir)` (proof_ledger.py:135, per consensus). But note: `tempfile.TemporaryDirectory` cleanup does not use `os.makedirs`, and `json.load`/`open` don't either, so the current tests pass. It remains true that any future code added inside the refusal block that calls `os.makedirs` (e.g., ensuring a scratch dir) will fail with a bare `AssertionError` whose message ("a refused run went on to write a proof dir") will be misleading. P2, unchanged.

**Qwen P2-3 (lu!r verbosity) — AGREE, negligible.** Registry is the branch's own short-JSON. No change.

**GLM P1-2 (ordering fragility: registered computed after run_due) — AGREE, correctly recorded not fixed.** The C2 diff comments it (proof_ledger.py:108: "the search never re-forms a registered line-up") and the states are post-try, which is what the `why` string needs ("resting until 22:29" must reflect the state *after* the candidate tries, since the search runs after them). If someone moves the call, the recorded state could go stale — but the comment now anchors it. Fragility, not defect.

**GLM P1-3 (all-skipped build) — AGREE, now answered by the diff.** test_medley.py:289-294: when the only line-up of the only angle is registered (open), the build returns `package=None` with a `why_none` naming ruling 66. The driver's `res is None and left > 0` path (proof_ledger.py:108-109) then... — actually, note: `res` is not None here (build returned its out), so the driver proceeds with a None package. That's the pre-existing no-package path; the diff doesn't show the driver's handling of `res["package"] is None` but it's unchanged behavior. No new defect.

**GLM's truncation** — its output cut off mid-sentence at P1-3; I treat its finding as stated.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2) — package.py:61-63: the no-voice skip records the key but the `continue` also skips the `order, added = cand, mid; break` assignment, so a registered completion is skipped even when it's the *only* clip that lands the duration window — correct per the fix's intent, but the loop then falls to `if added is None` and the `why_not` gains the ruling-66 suffix. Verified consistent (test_medley.py:296-308: `nv["registered_skipped"] == ["h+x+y+z"]`, `why_not` contains "ruling 66: ['h+x+y+z'] left to the registry", package is None). One subtlety: `note.setdefault("registered_skipped", []).append(...)` — if the loop tries *several* candidate clips and more than one forms registered line-ups, all are recorded, which is right. But the `why_not` f-string (lines 68-70) reads `note['registered_skipped']` via `note.get(...)` in the condition yet indexes it directly in the interpolation — safe because the condition guards it. No defect; noting the asymmetry (`note.get` in the condition, `note[...]` in the value) is fine since they're evaluated together.

**N2 (P2) — package.py:78-86: the main-loop skip records `rec["registered"] = dict(held)` — a copy, good — but `rec["why"]` embeds `held.get('state')` and `held.get('source')`/`held.get('index')` via f-string; if a registry entry ever lacked `source` or `index` (KeyError at candidates.py:20-21 would have caught it at driver-read time, since `registered()` reads them directly and the driver calls it in the refusal block, proof_ledger.py:98). So the f-string can't see a missing key. Verified safe.

**N3 (P2) — proof_ledger.py:98: `CA.registered(reg)` is called in the refusal block, and *again* at line 109 after `run_due`.** The registry is read twice; if `run_due`'s candidate tries mutate the registry (they do — states change, e.g. open→resting), the second call is the one that matters and is correctly placed after. But the first call (line 98) is purely a validation pass — its result is discarded. That's intentional (fail fast before anything is written), and the test at test_ledger_build.py:192-203 proves a malformed entry exits 2 with the registry bytes unchanged. Correct, but it means the *validation* and the *use* are two separate parses; if `run_due` were to add a malformed entry mid-run (it can't — it only mutates state, not lineups, per the background), the second call would raise *outside* the refusal try, crashing the driver with a traceback instead of exit 2. From the diff, `run_due`'s mutations are state/until only, so this is theoretical. P2.

**N4 (P2) — test_medley.py:257: `self.assertEqual([c[0] for c in rig.medley_calls], ["x"])`** — this asserts angle 2's line-up is `["x"]`, a single-clip "line-up" judged by medley. That's the rig's configured medleys, not the production shape (hook + 2-4 clips); it's the test's own fixture, consistent with the Rig's contract. Not a defect, but it means the test does not exercise the "hook + 2-4 clips" constraint on the *skipped* side — the skipped line-up `["h","x","y"]` (3 ids, hook+2 clips) is at the minimum. Fine.

**N5 — the second `held`-check placement vs. `spins` guard.** package.py:87-89: `n_lineup += 1; spins += 1` come *after* the skip's `break`, so a skipped line-up consumes neither. The `spins > 4 * lineups` guard (line 89) is therefore never advanced by a skip — but since the skip `break`s the angle, the guard's "never turn forever" concern doesn't apply within the angle, and the angle loop is bounded by `max_angles`. Verified: no loop risk. This confirms my Cycle 1 P1-3 reasoning, now with the diff's own lines.

**N6 (P2, the one genuinely new thing) — test_medley.py:289: the pool-fill test's second Rig is constructed with `registered=held(lu, "open")` where `lu` is captured from the *first* rig's output (`filled["tried"][0]["lineup"]`).** This is good practice (the test doesn't hardcode the pool-filled line-up), but it means the test's assertion at line 291 (`out["tried"][0]["pool_filled"] == ["z"]`) depends on the first rig producing the same pool-fill. If the pool-fill logic were nondeterministic across the two rigs (same inputs, same seeds — it isn't, both rigs get identical moments and no_hook sets), the test could flake. From the diff, both rigs get identical inputs and the Rig is seeded deterministically (`self.seeds` recorded), so this is safe. Noting it because it's the only test that depends on cross-rig determinism.

**N7 — the `why_none` assertion (test_medley.py:293-294) uses `out["why_none"].startswith(...)` with `out["why_none"]` as the second arg to assertTrue** — if `why_none` were absent, `out["why_none"]` raises AttributeError, which is a fine failure. But if the build *succeeded* (package not None), `why_none` might be absent/None and the test would fail confusingly. In this fixture the package is None by construction (the only angle's only line-up is skipped). Safe.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| candidates.registered() validation | 8/10 | 9/10 | key() now corroborated (candidates.py:28 + test expectations); malformed-entry path proven exit-2 with bytes unchanged (test_ledger_build.py:192-203) |
| package.build skip (main loop) | 7/10 | 9/10 | Placement verified: after `segs is None` guard, before `n_lineup`/`spins`, `break` not `continue`; all-skipped shape now shown (why_none) |
| package.build skip (no-voice fallback) | 5/10 (unverifiable from C1 diff) | 9/10 | C2 diff shows the second check site + `registered_skipped` note + why_not suffix, with a dedicated test |
| Driver integration (refusal + post-run_due) | 8/10 | 8.5/10 | Double-parse of the registry (N3) is theoretical; the post-`run_due` placement is commented and correct |
| Tests | 7/10 | 9/10 | Reorder + pool-fill + no-voice now covered; mutation runs reported; refused_only() hardening closes the "test ran the driver on" gap |
| Gates/verdicts/seal untouched | 9/10 | 9/10 | Diff adds no gate/verdict/seal logic; only new `tried` record keys (`registered`, `why` text, `registered_skipped`) — additive, no acceptance change |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** none.

**P1 HIGH:** none.

**P2 MEDIUM:**
1. **test_ledger_build.py:163** — `refused_only()`'s `os.makedirs` patch is global to the with-block; any future `os.makedirs` inside the refusal path (or in code it calls) fails with the guard's AssertionError, masking the real refusal. Condition: acceptable as-is; if the refusal block ever grows a write, switch to a targeted patch.
2. **proof_ledger.py:98 vs 109** — the registry is parsed twice; the second call sits outside the refusal try, so a mid-run mutation that broke an entry would crash rather than exit 2. Currently impossible (run_due mutates state only); note it in the code, don't fix.
3. **package.py:68-70** — `why_not`'s ruling-66 suffix indexes `note['registered_skipped']` directly while the condition uses `.get`; safe today (guarded together) but brittle if the condition and the interpolation ever diverge. Cosmetic.
4. **test_medley.py:289** — the pool-fill skip test depends on cross-rig determinism (lineup captured from rig 1, replayed in rig 2). Safe with the Rig's seeding; would flake if seeding ever changed. Worth a comment, not a change.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

None required — the C2 diff closed the only substantive gap (the no-voice fallback judgment site, which my Cycle 1 correctly doubted but could not name); the highest-leverage *remaining* act is documentation, not code: a one-line comment at proof_ledger.py:109 noting that the second `CA.registered(reg)` call is the authoritative post-`run_due` snapshot and must stay after `run_due`.

## 7. PRODUCTION READY?

**Yes.** No conditions.

Rationale, compressed: the skip is a `break` placed after the line-up is formed and before `n_lineup`/`spins`/any verdict (package.py:78-88), so a registered line-up is neither judged nor counted, and the angle ends — no loop risk (the angle loop is bounded by `max_angles`); the no-voice fallback, the one second judgment site, now checks `held_map` too and records what it skipped (package.py:61-70, test_medley.py:296-308); a candidate build's `held_map` is empty by construction (package.py:53) and the test proves its own try is judged (test_medley.py:268-271); the driver validates the registry in the refusal block before anything is written (proof_ledger.py:98, exit 2, bytes unchanged — test_ledger_build.py:192-203) and passes the post-`run_due` snapshot to the search (line 109); the refusal guard's patches are scoped to their `with`-blocks (test_ledger_build.py:162-164) and both refusal tests now run under it; and the diff adds only new keys to the `tried` record — no gate, verdict, or seal acceptance changes. All four required checks pass from the diff, with the C1's one open question (formation-site coverage) now answered in code and in tests, including the reorder and pool-fill paths.