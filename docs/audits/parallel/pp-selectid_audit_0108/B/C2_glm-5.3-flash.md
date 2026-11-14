# glm-5.3-flash (z-ai/glm-5.3-flash) 209 s finish=stop usage in 37773 / out 5187 usd~0.191 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-0108B (package B: verdict call sites, shadow, replay)

**Reviewer: claude (cycle 2, final).** Scope: the FIXED diff only. Package A (`providers.call_parsed`, `Router`, `gateway`) assumed to behave as the background states; where a finding depends on it, I say so.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against the three Cycle 1 outputs:

- **glm's B1 (the `kind` kwarg / package A-B version skew).** I verified the call sites pass `kind` but did not systematically ask "what happens if the installed `Router.call` predates the parameter." glm's failure mode is precise: the `TypeError` lands inside the `while True` loop's broad except at `context_integrity.py:119`, so a skew fails *every* prescreen as a step-A failure, indistinguishable from a real outage. I missed the *diagnosability* angle (fail-closed but silent-as-anything). Partially excusable — it's a condition, not a provable defect — but it's the right question to ask of a mechanical rebase.
- **glm's B3 (replay's legacy tolerance vs production's strict parsers).** I noted the replay's `decide` accepts older contracts but did not trace the consequence: the `clips_alone`/`coherence` agreement percentages in TABLE.md are computed over a *more permissive* contract than production's. glm's mitigation is the key fact — ruling 88(b) rests on the HOOK rows, which use the strict contract (`set(v) == {"hooks"}`, replay85.py:599) — so the divergence is informational. I under-weighted this.
- **qwen's P2-1 (stale comment in `hook_ratings`).** Trivial; I missed it. It's now fixed in the diff (package.py:227-229, 279-280) — the comment correctly describes the move-on semantics.
- **qwen's P1-2 ("grok no verdict" semantics in `would_seal`).** I had the fail-closed intuition but not the *labeling* argument: "would_seal_under_grok" implies a counterfactual *decision*, and an unreadable shadow answer is not a decision. The consensus fix (comment at shadow86.py:1234-1236) resolves it correctly — fail-closed, disclosed.

What I caught that they didn't (carried into §3): the `compare`-vs-`grok` unit-set mismatch in the anchors section, the `grok_self` step_a_excerpt key leak, and the `usd_reported`/`_num` coupling.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| glm B1 (`kind` kwarg, A/B skew) | **Agree, P2** | Fail-closed, so not a blocker; but the except at context_integrity.py:119 wraps steps A+B+C, so a skew reports as a step-A failure for every label. Verify package A's `call` signature; the diff cannot. |
| glm B2 (attempt count 2→1) | **Agree, P2** | It's the intended ruling-82 semantics, and the test at test_medley.py:1343-1354 now exercises it correctly (`backend: "fake:2"`, `rejected: ["fake:1"]`, `asked_skip` asserts the second ask skips the first model). Behavioral change, disclosed, tested. |
| glm B3 (replay legacy tolerance) | **Agree, P2** | Disclosed in the docstring (replay85.py:565-569); ruling 88(b) rests on the strict HOOK path. Informational only. |
| glm B4 (compare masks differing failure rules) | **Agree, P2** | The dedicated REFERENT_OUTSIDE section (replay85.py:942-955) catches the one case the ruling names. The agree column can overcount, but the ruling's requirement is checked separately. |
| qwen P1-1 (429 handling) | **Agree with the consensus refutation** | The replay calls `router.call`, so ruling 48's ledger and SpendLimit still bound it; the manual `down.pop` + `sleep(30)` only lifts the run-long down-mark so one 429 doesn't end a measurement. The replay is a measurement tool, never a gate. The "burn the cap" scenario requires 429s to be billed, which the ledger's "reported" basis makes unlikely. Not a defect. |
| qwen P1-2 (would_seal semantics) | **Agree, resolved** | Fail-closed is correct for a fail-closed pipeline; the comment at shadow86.py:1234-1236 now says so, and test_shadow86.py:1494-1500 pins it. |
| qwen P2-1 (stale comment) | **Agree, fixed** | package.py:227-229. |

No disagreements with the consensus. The one place I'd push back gently: grok-4.20's "none verifiable from diff" is technically accurate but skips the *coupling assumptions* (does package A's `call` really accept `kind`? does `call_parsed` really reject-then-advance on each of ValueError/TypeError/KeyError?) that glm correctly flagged as unverifiable. "Not verifiable" and "not present" are different claims.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2). `replay85.py:931` — the anchors section counts a unit only when Grok *passed* it, but the `compare` lookup can disagree with the unit's presence in `grok`.**
```python
g = (r.get("grok") or {}).get(u)
if g is None or (r["type"] == "step_a" and g) or g is False:
    continue
...
elif (r.get("compare") or {}).get(u) == "stricter":
```
`compare` (line 776) is built by iterating `row["grok"].items()`, so its keys are exactly `grok`'s keys — good. But `anchor_units` (line 863-876) returns units from the *prompt's* blocks (`<excerpt>`, `<pair>`, CANDIDATE), which for `step_a`/`step_c`/`hook` are the same keys `decide` produced (both derive from the same prompt markers) — so the key sets coincide. The residual risk: for `clips_alone`/`coherence`/`fidelity`, `anchor_units` returns `{u: whole for u in (row.get("grok") or {})}` — the *grok* keys — while `compare`'s keys are also the grok keys. Consistent. So this is weaker than I thought in cycle 1; the real residual issue is that a unit where **Grok's own answer was out of contract** (`row["grok"] is None`, line 753-755) silently contributes nothing to the anchor count — a pin whose Grok record is unreadable loses its anchor coverage without any note. The ruling says "every verdict that let the pins' clips through must still pass"; if Grok's recorded answer can't be parsed, nobody checks whether Heimdall passes it. **Concrete scenario:** an old recording whose answer predates ruling 61's contract; `decide` raises; `row["grok"] = None`; the anchors section skips it; TABLE.md reports fewer anchor units than the ruling demanded, with no "unverifiable" line. P2: the anchors that *do* parse still gate, and the ruling's anchors are recent (post-07:37) so likely parse.

**N2 (P2). `replay85.py:837-839` — `grok_self`'s key substitution can leak `step_a_excerpt` into the baseline table's `DECIDING` loop.**
Line 916: `for k in DECIDING + ("step_a_excerpt",):` — if `out["step_a_excerpt"]` exists, line 838-839 *moves* `out["step_a"]` into `out["step_a_identical_prompt"]` and *rebinds* `out["step_a"] = out["step_a_excerpt"]`. Then the loop at 916 iterates `step_a` (now the excerpt-based numbers — intended) **and** `step_a_excerpt` (the same dict, printed twice) **and** `step_a_identical_prompt` (also the same dict, a third time). Cosmetic: the baseline table prints the same step-A row three times under three names. But it also means `propose`'s `base.get(k)` for `k == "step_a"` uses the excerpt-pair numbers — which is *intended* per the comment ("the bar for step A: the same excerpt, any batch") — yet `passes()` for `step_a` compares production's whole-batch agreement against a baseline computed over *single-excerpt* pairs, a subtly different unit. Disclosed in spirit (the comment says so) but the triple-print is an unintended artifact. P2, cosmetic + a disclosed-but-soft unit mismatch.

**N3 (P2). `replay85.py:907` — `usd` sums `float(r["usd_reported"])` but the guard is `P._num(...)`.**
```python
usd = sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported")) and not r.get("cached"))
```
If `P._num` returns the *value* (a common convention: `x if isinstance(x, (int, float)) else None`), the truthiness works; if it returns a bool, it also works. But if a recorded `usd_reported` is a *string* (e.g. `"0.0123"` — the recordings' usage blocks are provider-reported and not guaranteed numeric), `float()` succeeds while `_num`'s behavior on strings is unknown from this diff. Same pattern at line 972 (`float(v.get('usd_reported') or 0)` — that one is safe). Low risk, unverifiable without package A. P2, conditional.

**N4 (P2). `shadow86.py:1237-1238` — `would_seal`'s `missing` guard has an asymmetry.**
```python
would_seal = None if not texts or (missing and not on_pin) else \
    not any(r["compare"] in ("looser", "grok no verdict") for r in pin_diff)
```
If `missing > 0` **and** `on_pin` is non-empty, `would_seal` is computed from the *present* shadow answers only — a pin with 10 decisions, 1 shadowed (agreeing) and 9 missing reports `would_seal_under_grok: True` on the strength of one decision. The consensus fix (glm's) only covered the *all-missing* case. The streak logic (line 1263: `changed = bool(pin_diff) or bool(missing)`) correctly treats missing as not-clean, so the *streak* is safe; only the *report's* boolean overclaims. Concrete scenario: the shadow's Grok calls start failing mid-build (spend cap); 1 of 10 pin decisions shadowed; the report says the pin would have sealed under Grok; the ruling-86 reader (the orchestrator) is told more than was verified. P2 — the summary line does print `missing`, so a careful reader sees it, but the boolean field is the machine-readable one. **This is the strongest new finding.**

**N5 (P2, conditional on package A). `package.py:374-378` — the gateway-avoidance rewrite changes semantics when `angle_reply.backend` is not in `router.backends`.**
```python
ab = router.backends.get(angle_reply.backend)
writer_avoid = {P.gateway(router.backends[n]) for n in router.chain("angle_write") if n in router.backends} - \
    {P.gateway(ab) if ab is not None else angle_reply.vendor}
```
Old code: `{...vendor...} - {angle_reply.vendor}`. If `ab is None` (the angle's backend record was evicted/renamed), the new code subtracts `angle_reply.vendor` from a set of *gateways* — comparing a vendor string against gateway strings. Whether that's a no-op depends on whether `P.gateway(b) == b.vendor` for the old single-vendor back-ends; if the gateway of a Grok back-end is `"xai"`, it coincides and the behavior is unchanged; if gateways are finer-grained (e.g. `"xai:grok"`), the subtraction misses and the writes may avoid nothing (or the wrong thing), leaving "no judge" possible — the exact failure the comment says this prevents. Unverifiable from this diff (package A defines `gateway`); flagging as a coupling condition. The comment (lines 375-378) discloses the intent but not this fallback.

**N6 (P2). `replay85.py:753` — `decide(k, r["text"], r["prompt"])` uses `r["prompt"]` but `records()` dedupes on the *raw* prompt while `anchor_units` re-reads it.** Consistency check: `records()` (line 682) dedupes on `(role, prompt, system, max_tokens)` — the raw prompt; `anchor_units` (line 855-861) re-reads the record's prompt from disk. Both use the raw prompt, and `decide`'s regexes run on the raw prompt. But `anchor_texts`/`anchor_units` match via `_norm` (line 691-693) while `kind()` (line 528-538) matches on raw markers. No bug found — noting that the prompt is used in three roles (kind detection, decision parsing, anchor matching) and any future normalization change must keep all three consistent. Not a finding, a caution. Downgraded to a note.

**N7 (P2). `test_medley.py:1408` — the ruling-88(c) test's expected tuples.**
```python
self.assertEqual(sorted(got), [(1, 8, None, "step_a_second", True), (8, 8, None, "step_a_second", True)])
```
9 moments grouped by one (vendor, family) key → chunks of 8 → `[8, 1]`; `sorted` gives `[(1,...), (8,...)]`. Correct. But the fake `prescreen` (line 1392-1396) returns `{"backend": "xai:grok"}` for *every* moment while the grouping key came from `a_by`'s `heimdall:qwen` — the test never exercises the case where the second screen's *own* verdict lands on a different vendor than the grouping assumed. That's the `stale` re-screen path (package.py:382-393), which has its own coverage. Acceptable.

**N8 (P2). `shadow86.py:1191` — `compare_lines` skips a line whose Heimdall answer is unreadable, adding it to `skipped`, but a line whose *shadow* is missing entirely (`"text" not in sh`) is also "no decision rule" — the two causes are conflated in the report's "Not compared" section.** Line 1191-1193: the `why` is `sh.get("error") or "no decision rule"`, so a shadow line with no `error` key and no `text` (the "still running" case, which `missing` counts) shows as "no decision rule" — misleading in the MD. Cosmetic; the `missing` count in the summary carries the truth. P2.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Verdict call sites (fidelity, exclusion, speaker, hook, coherence, medley, step B/C) | 9/10 | 9/10 | Parses are verbatim moves; except clauses catch the full raise-set of `call_parsed` (ValueError/TypeError/KeyError + ProviderError/SpendLimit) at every site (moments.py:149, package.py:279, 318, 352, context_integrity.py:119, vo_fidelity.py:449, speakers.py:409's surrounding try). The `kind`-skew condition (glm B1) remains unverifiable here. |
| Routing bounds (first/second, ruling 85/88) | 9/10 | 9/10 | `first_bounds`/`_second_bounds` match the rulings; tests 1365-1408 pin both routings; the gateway-avoidance fallback (N5) is the one soft spot. |
| replay85 | 8.5/10 | 8.5/10 | The legacy-tolerance disclosure (glm B3) and the anchors/grok-unreadable gap (N1) and the baseline triple-print (N2) are all informational; the ruling-88(b) HOOK conclusion rests on the strict path. |
| shadow86 | 9/10 | 8.5/10 | N4: the partial-missing `would_seal` overclaim is real and nobody caught it in cycle 1; the streak is safe but the report's boolean can overclaim. |
| Tests | 9/10 | 9/10 | The chained-helper test (1343-1354) is exactly the right regression for the 2→1 attempt change; the ruling-85/88 bounds tests are precise. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none. I cannot construct a scenario in this diff where an out-of-contract answer becomes a verdict, or where an outage yields a pass: every call site's except clause catches the full `call_parsed` raise-set and returns the old no-verdict shape (`measured: False` / fails / `STEP_A_UNAVAILABLE`), and nothing is cached before the parse succeeds (`_cache_put` only after the loop, package.py:288; the exclusion/fidelity/coherence/medley paths return before any cache write).

**P1 HIGH** — none.

**P2 MEDIUM:**
1. **shadow86.py:1237-1238 (N4)** — `would_seal_under_grok` is computed from the *present* shadows when some are missing; a pin with 1 of 10 decisions shadowed reports the boolean. Fix: `None` unless every pin decision has a compared shadow, or report `would_seal` alongside `missing` in the machine-readable summary (it already does — but the boolean itself should be `None` when `missing` covers any *pin* decision, not just when `on_pin` is empty). Concrete: 1 agreeing shadow + 9 missing → `True` with 90% unverified.
2. **package.py:374-378 (N5)** — the `ab is None` fallback subtracts a *vendor* from a set of *gateways*; verify `P.gateway(b) == b.vendor` for legacy back-ends or the writes' avoidance silently weakens. Condition on package A.
3. **replay85.py:931 + 753-755 (N1)** — a pin decision whose Grok recording is unreadable silently drops out of the anchors count; add an "unverifiable" line so the ruling's "must still pass" is auditable.
4. **replay85.py:837-839 + 916 (N2)** — the baseline prints the step-A excerpt numbers three times (`step_a`, `step_a_excerpt`, `step_a_identical_prompt`); and `passes("step_a")`'s bar compares whole-batch agreement against single-excerpt-pair agreement. Disclosed, but print once and note the unit difference.
5. **replay85.py:907 (N3)** — `float(r["usd_reported"])` vs `P._num`'s contract; if a recorded usage value is a string, this either works or raises; guard with the same `or 0` pattern as line 972.
6. **glm B1, carried** — verify package A's `Router.call` accepts `kind` (and `call_parsed` exists with the reject-then-advance semantics for exactly ValueError/TypeError/KeyError) before merging; a skew fails every prescreen as an undifferentiated step-A failure (context_integrity.py:119).
7. **shadow86.py:1191-1193 (N8)** — "no decision rule" is reported for a shadow that is merely still-running; distinguish the causes in the MD.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Make `would_seal_under_grok` `None` whenever any *pin* decision's shadow is missing (not just when all are) — it is the one machine-readable field the ruling-86 consumer reads, and today it can say "verified" on the strength of a fraction of the pin's decisions.

## 7. PRODUCTION READY?

**Yes with conditions:**

1. **(package A, must verify before merge)** `providers.Router.call` accepts `kind` and `providers.call_parsed` exists with exactly: reject on ValueError/TypeError/KeyError, advance to the next model, each model once, raise ProviderError/SpendLimit when the chain is spent. Every except clause in this diff is written to that contract; a skew fails every prescreen as an undifferentiated step-A failure.
2. **(package A, must verify)** `P.gateway(b)` equals `b.vendor` for the legacy (pre-heimdall_first) back-ends, or the `ab is None` fallback at package.py:377-378 must subtract a gateway, not a vendor.
3. **(should fix, small)** shadow86.py:1237 — `would_seal` → `None` when any pin decision's shadow is missing, not only when `on_pin` is empty; add the one-line test.
4. **(should fix, trivial)** replay85.py:907 — guard the `usd` sum with `or 0` as line 972 does; replay85.py:916 — print the step-A baseline once.
5. **(disclosed, accept)** the replay's legacy-contract tolerance for `clips_alone`/`coherence` (replay85.py:565-580) — it changed no routing; ruling 88(b) rests on the strict HOOK rows.

Everything else — the parse functions are the old contract checks moved unchanged (I compared each against its deleted inline block: moments.py:137-144 vs 139-143-old, package.py:267-274 vs 244-248-old, coherence 306-312 vs 308-311-old, medley 335-344 vs 337-343-old, step B/C 42-72/104-110 vs 40-55/82-97/114-118-old, fidelity 443-445 vs 440-447-old, speakers 409-412 vs 406-408-old) — checks out; the except clauses catch the full raise-set; the outage paths return the old no-verdict shapes; the caches are written only after a successful parse; the shadow's streak resets on missing/unreadable; the ruling-88(b) hook conclusion rests on the strict contract. Ship.