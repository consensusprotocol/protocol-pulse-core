# glm-5.3-flash (z-ai/glm-5.3-flash) 154 s finish=stop usage in 22279 / out 3735 usd~0.123 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-0915)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against the consensus and the two substantive reviewers:

- **grok-4.20's `hashlib` import** (spotlight.py:274): I missed that the diff adds `import math` (line 106) but not `import hashlib` to spotlight.py. However, the pre-existing file already imports hashlib at line 104 (`import hashlib` is in the context hunk, unchanged) — the diff hunk at lines 103-109 shows `import base64 / import hashlib / import json / +import math`. So grok's <high> is **refuted by the diff's own context lines**: hashlib was already imported (layout_for's sheet-sha check at line 279 uses it, pre-existing). Grok's test_spotlight.py:573 evidence (a *test* importing hashlib locally) is consistent with the test file, not the pipeline. **Grok's critical/high pair is wrong; its two <medium>s are its real contribution.**
- **glm's ValueError→GateNotMeasured conversion**: glm's own text walks it back mid-paragraph ("Downgrade: not critical", "Not a break") but still headlines it as <critical>. The mechanism: `vo_fidelity` raises ValueError from `universe_levels`/title checks *outside* the try (lines 88-94), and the test at 448-455 asserts `GateNotMeasured`. Neither glm nor anyone else located the conversion. **This is the one genuinely unresolved question in the whole review** — see §3.
- **qwen's 2-tuple/None-unit case**: qwen initially said the guard catches it, then corrected itself; the consensus implemented it (counting inside the try, finite check). I missed the NaN-compares-False-both-bounds subtlety — a NaN time silently reading as `changes_near=0` → a *refusal* from unreadable evidence, violating "no evidence, never a refusal". That's the best catch of the cycle and it's now tested (test lines 601-612).

## 2. AGREE / DISAGREE

| Finding | Verdict | Why |
|---|---|---|
| glm: ValueError not converted to GateNotMeasured | **Agree it's the open question; disagree it's proven** | The diff shows no conversion, but the diff is partial (718 lines, hunks only). `vo_fidelity`'s caller or a decorator could convert. However: the test at 452-455 uses `assertRaises(A.GateNotMeasured)` and the consensus says "20 suites, 559 tests, all pass" — if that's a *run* result, the conversion exists somewhere unseen. If it's an aspiration, the test fails. **Must be resolved before ship.** |
| grok: missing `import hashlib` | **Disagree** | Diff lines 103-109: `import hashlib` is context (pre-existing), only `+import math` is added. Grok cited the test file's local import as evidence — wrong file. |
| grok: `minutes` IndexError on 1 unit | **Disagree (moot)** | Guard at 142-144 returns early on falsy; 1 unit → `minutes=0.0` → `turns_per_min=None` via the ternary at 151. No IndexError. Grok's "len(units) < 2" concern is handled. |
| grok: next_attempt filters on overall tpm vs per-clip changes_near | **Partially agree** | Real conceptual gap: `next_attempt` (line 236-237) admits an upload on *episode-level* evidence, but `build`'s refusal is *per-clip* (`changes_near==0`). An upload admitted at report time can still have every clip refused at build time. Not a correctness bug (the report is advisory, "when could the next attempt be"), but the report's `rule` string (240-241) says "the layout decides per clip" — accurate. Cosmetic. |
| qwen: `float(m["start"])` unguarded in build (line 320) | **Partially agree** | True that a None/non-numeric start crashes the build uncaught. But `m["start"]` comes from the moments ledger, which ruling-94/95 code already treats as numeric (TRIM_MARGIN_S math). Low probability, and the consensus "refuted" it — I'd call it <medium> defensive- coding, not <high>. |
| qwen: `E._parse_time` private access | **Agree, <medium>** | Real coupling; eligibility._parse_time is not in the diff so its None-on-unreadable contract is assumed, not verified. The `if now is None` check at 65-66 depends on it. |
| Consensus: caption_evidence counting inside the guard + finite check | **Agree** | Correct fix; S11/S12 mutations killed; the NaN→false-refusal case is exactly the failure mode the ruling warns about. |

## 3. NEW FINDINGS (not caught by anyone in Cycle 1)

**N1. `universe_levels` reads `universe["built_at"]` and `universe["news"]` by subscript (lines 64, 67) but the test's "no news list" case is `v11(universe={"news": []})` — which *has* built_at. Nobody tested a v1.1 case whose `universe` dict lacks `built_at` entirely.** Trace: line 64 `universe["built_at"]` → KeyError, not ValueError → not GateNotMeasured (unless the unseen conversion catches *all* exceptions). The test at 450 includes `v11(universe={"news": []})` — that one *passes* built_at, so it exercises the `now is None`... no wait, `{"news": []}` has no `built_at` key at all → line 64 raises KeyError. So the test at 450-451 *does* cover it, and asserts GateNotMeasured — meaning either KeyError→GateNotMeasured conversion exists, or the test fails. This strengthens the glm finding: **the test suite itself proves a broad conversion (KeyError AND ValueError → GateNotMeasured) must exist, and it's not in the diff.** If the conversion is `except Exception` around the whole pre-try block, fine; if it's `except (ValueError, KeyError)`, also fine; if nothing, 2+ tests fail. Either way the diff as shown is incomplete — flag as <high> "verify, not necessarily broken".

**N2. `evidence_text` for a *marked* episode with `minutes=0`** (line 173-175): `turns_per_min` is None when `minutes <= 0` (line 151), so the prompt reads "None speaker turns a minute across the episode (3 in 0.0 min)". Grammatically fine, judge-robust. But: a clip whose episode has exactly one marker at t=0 and another at t=0 (duplicate timestamps) → minutes=0.0, turns=2, tpm=None. `markers_refuse` still works (changes_near counted). No break — noting for completeness, <medium> at most.

**N3. Cache-key collision window** (line 274): the evidence hash is truncated to 12 hex chars (48 bits) *and* the key already contains moment_id + sheet sha + LAYOUT_VERSION. Two different evidence texts colliding in 48 bits: negligible. But the *real* subtlety: `evidence_text` returns the same string for `{"measured": True, "marked": False}` and `{"measured": True, "marked": False, "turns": 999}` — both "the captions carry no speaker-change markers". That's *correct* (the judge only sees the text), and the test at 634-636 confirms a different evidence → different key. Actually this is a feature: the cache keys on exactly what the judge sees. **No finding — but nobody stated the invariant, and it's the justification for hashing ev_text rather than the evidence dict.** Worth one line in the docstring.

**N4. `next_attempt`'s `unmarked` propagation from the recount path** (line 223): `tpm, frm, unmarked = t.get("turns_per_min"), "the caption record (recount)", t.get("unmarked") is True`. But `episode_turns` (pre-existing, lines 121-122 context) returns `"unmarked"` only in *some* shapes — the diff shows its return dict includes `"file"`, `"sha256"`, and (per the old source_test) `"measured": False, "unmarked": True` for unreadable. If `episode_turns` returns a *measured* record with turns but no `unmarked` key, `t.get("unmarked") is True` → False, and a genuinely-unmarked episode recounted this way gets `unmarked=False, tpm=None` → the filter at 236-237: `x["unmarked"] or not (isinstance(tpm,(int,float)) and tpm <= 0)` → `False or not (False and ...)` → `not False` → **True: admitted**. Good — a None tpm is admitted either way. And a recounted *marked* episode with 0.0 turns: `unmarked=False`, tpm=0.0 → `not (True and 0.0<=0)` → `not True` → False → excluded. Correct. **No break; the filter's truth table works for all four (unmarked × tpm) combinations.** Verified, not guessed.

**N5. `run_exam_record.py` line 339-340: `A._router = A.make_router(chains=...)`** — this sets the module global *directly*, bypassing `router()`'s lazy init. Correct (that's the point: the recorder pins chains). But the harness's replay path calls `router()`, which returns the *cached* `_router` — if anything imported the adapter and called `router()` *before* run_exam_record sets `_router`... no, run_exam_record is the recorder, not the harness; they're separate processes. The replay's `router()` builds via `make_router()` with `PP_GATES_REPLAY=1` and *no* chains — it uses "the routing's own lists" (line 41: `chains=chains or None`). **The replay walks the routing's default chain order; the recording walked the pinned chains. If the routing's heimdall_first list for a role differs from what the recorder pinned (e.g. the recorder's `--chain context_verdict=xai:x` pinned ONE leg, but the replay's heimdall_first list has [xai:grok-4.20, other]), the replay tries legs the recording never made.** The Router serves "the first back-end in its chain that has a recording" — so extra legs are harmless (ReplayMiss → next leg? or error?). *If* ReplayMiss on a leg falls through to the next leg, extra legs are safe. If it raises, the recorder's `--chain` pinning would break the replay. The test at 507-510 only proves the recorder *passes* chains to make_router; nothing proves the replay's unpinned heimdall_first list matches. **<medium>: the safety depends on Router's ReplayMiss fall-through, which is not in the diff.** This is the strongest genuinely-new finding.

**N6. Test line 489: `r.chain("context_verdict", "step_c")[0] == "xai:grok-4.20-0309-reasoning"`** — asserts the *default* heimdall_first routing's first leg. If providers.ROUTING's heimdall_first list changes, this test breaks — but that's a test- brittleness, not a code bug. Skip.

**N7. `caption_evidence`'s `opens` uses `zip(times, units)` (line 148) after the finite check on `times` (146-147) — but `u[2]` is evaluated inside the zip comprehension, *inside* the try. Good. However `times = [float(u[0]) for u in units]` (145) — a unit that's a *string* like "abc": `float("abc")` → ValueError, caught. A unit that's a 2-char string "ab": `float("a")` → ValueError. Caught. All inside the try. ✓** (qwen's 2-tuple case: `u[2]` on a 2-tuple → IndexError, inside try, caught → measured False. ✓ — the consensus implemented this correctly; the *old* code had the comprehension outside the try, which was the bug.)

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| R-29 adapter (title/universe→gate) | 8/10 | 7.5/10 | The GateNotMeasured conversion's absence from the diff is now *proven necessary* by the test's KeyError case (N1); until someone points to the conversion, the diff is incomplete. |
| make_router / exam economics | 8.5/10 | 8/10 | N5: replay-vs-recording chain equivalence rests on unseen Router fall-through. |
| Ruling 92 amended (spotlight) | 9/10 | 9/10 | Survived every attack; the NaN/1-tuple/None-unit guard is exemplary. |
| Tests | 8.5/10 | 8.5/10 | 559 tests, 21/21 mutations; the KeyError case at 450 quietly does double duty. |
| Overall | 8.5/10 | 8/10 | Two "verify before ship" items, no proven break. |

## 5. FINAL PRIORITY LIST

- **P0 (must resolve, likely by pointing at existing code, not by changing it):**
  1. **moments_gate_adapter.py:64,67,88-90 + test_exam_adapter.py:448-455** — show the ValueError/KeyError→GateNotMeasured conversion. The test's `v11(universe={"news": []})` (no built_at → KeyError) and the zoneless case (ValueError) both assert GateNotMeasured; neither exception is converted *in the shown diff*. If the conversion exists (caller or wrapper), cite it; if not, the new test suite fails on arrival.
- **P1:**
  2. **spotlight.py:236-241 + moments_gate_adapter replay** — confirm the Router's ReplayMiss fall-through: the recorder may pin `--chain role=xai:x` (one leg) while the replay walks heimdall_first's full list; extra legs must fall through, not error, or the replay diverges from the recording (background: "the replay must walk the same chains as the recording").
- **P2:**
  3. **spotlight.py:320** — `float(m["start"])`/`float(m["end"])` unguarded in build; a None start crashes the build instead of recording a stage failure. Wrap or assert at ledger-ingest.
  4. **moments_gate_adapter.py:64** — `E._parse_time` private coupling; its None-on-unreadable contract is assumed, not shown. One-line comment or make it public.
  5. **spotlight.py:173-175** — "None speaker turns a minute" reaches the judge when minutes=0; harmless, but a `0.0`-vs-`None` wording choice would read cleaner.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Point at (or add) the exception→GateNotMeasured conversion around `vo_fidelity`'s pre-try block — the entire R-29 test suite's ERROR contract hangs on it, and it is the one thing the diff shows but does not prove.

## 7. PRODUCTION READY?

**Yes with conditions.**
1. (P0) Cite or add the ValueError/KeyError→GateNotMeasured conversion for the pre-try block of `vo_fidelity` (lines 64-94); demonstrate test_exam_adapter.py:448-455 passing.
2. (P1) Confirm in providers.Router that a ReplayMiss on a non-first chain leg falls through to the next leg (or that the recorder's default run pins no chains), so the $5-exam's replay walks the recorded chains.
3. (P2, non-blocking) Guard `float(m["start"|"end"])` in build, and note the `E._parse_time` contract.

Everything else — the ruling-92-amended evidence path, the NaN/short-unit guard, the cache-keyed-on-what-the-judge-sees invariant, the ruling-95 unmarked-episode fix — I've attacked and it held. 21/21 mutations, 559 tests, and the two consensus fixes are genuinely in. Ship after conditions 1-2 are discharged.