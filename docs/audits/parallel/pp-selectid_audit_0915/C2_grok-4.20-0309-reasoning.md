# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 29 s finish=stop usage in 21795 / out 1168 usd~0.138 (upper-bound price)

1. WHAT DID THEY CATCH THAT YOU MISSED?
Grok and GLM both flagged the exact vo_fidelity ValueError-vs-GateNotMeasured mismatch (lines 89-94 + universe_levels:65) and the test at test_exam_adapter.py:454-455 that cannot pass; I had only noted the private _parse_time and v1.1 schema optionality in my Cycle 1. Qwen caught the build-stage float(m["start"]) crash path (now fixed at spotlight:320 but still assumes numeric). The combined C1 also highlighted the caption_evidence 3-tuple assumption and len(units)<2 risk—both now guarded but I had not traced the NaN/refusal interaction.

2. WHERE DO YOU AGREE OR DISAGREE?
- Grok <critical> on ValueError (title="" or zoneless built_at): fully agree—still present in the "fixed" diff; vo_fidelity's try only catches ReplayMiss, so harness sees raw ValueError instead of GateNotMeasured(ERROR).
- GLM on universe_levels subscript vs .get and "v1 unchanged": partially agree—the new guard at :93 prevents calling on None, but missing "news" still KeyErrors at :67 (not caught).
- Qwen on caption_evidence empty/units shape: disagree on "not a bug"—C1 mutations S11/S12 were killed only because the new diff moved counting inside the try/except (now correct).
- All on private E._parse_time: agree—brittle.
- All on router/make_router and spotlight amended logic (markers_refuse, evidence in cache key/prompt, next_attempt unmarked filter): agree—implemented cleanly, tests comprehensive, no cache reuse under changed evidence.

3. NEW FINDINGS FROM THIS REVIEW
<critical> moments_gate_adapter.py:94 (`levels = universe_levels(case["universe"])`): concrete input `v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13"))` raises ValueError("the universe's clock built_at=... is not a zoned time") from line 66; test_exam_adapter.py:454 asserts GateNotMeasured (and harness law L-m requires ERROR). No conversion in vo_fidelity (try at 95 only catches ReplayMiss). Same for `v11(title="")` at line 89 and missing-"news" KeyError at :67.
<critical> moments_gate_adapter.py:64 (`E._parse_time`): private API; concrete change in eligibility.py breaks universe_levels and all tests using it.
<high> spotlight.py:320 (`float(m["start"])` inside build loop): if a moment record has `"start": None` or non-numeric (possible from upstream), uncaught exception crashes whole build (not recorded as failure). TestBuild only stubs numeric cases.
<medium> spotlight.py:173 (`ev.get('turns_per_min')` in f-string): when measured=False the evidence_text path is taken but test_spotlight.py:609 only checks the "could not be read" literal; a None turns_per_min produces literal "None speaker turns..." in LAYOUT_PROMPT (cache key also affected).

4. REVISED SCORES
| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| R-29 (moments_gate_adapter) | critical | critical | C1 ValueError/GateNotMeasured mismatch survives in "fixed" diff; new test makes it verifiable |
| Spotlight/ruling-92 (caption_evidence + source_test) | high | medium | Guard, isfinite, markers_refuse, evidence caching, and 17 killed mutations now correct; only residual float() and f-string edge cases |
| Router/exam harness | medium | low | make_router shared, test_heimdall_first_on_vendor_reported_dollars_bounded_at_5 passes, no ledger crossover |
| Overall | critical (no-ship) | critical (no-ship) | Core harness contract (GateNotMeasured) still violated |

5. FINAL PRIORITY LIST
P0 CRITICAL
- moments_gate_adapter.py:89-94 (and universe_levels:65-67): wrap title/universe checks in `try/except ValueError as e: raise GateNotMeasured(str(e)) from e`; add `if not isinstance(universe.get("news"), list): raise ValueError...` before subscript.
- moments_gate_adapter.py:64: replace `E._parse_time` with public zoned-time parse or inline the logic.
P1 HIGH
- spotlight.py:320: guard `float(m.get("start") or 0)` / `float(m.get("end") or 0)` or let caption_evidence raise caught inside its own try.
P2 MEDIUM
- spotlight.py:173: `turns_per_min=ev.get("turns_per_min") or 0` (or explicit "unknown" text) so prompt never contains literal "None".

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Make vo_fidelity convert every validation failure (title, universe clock, news list) into GateNotMeasured so the harness, test, and law L-m treat unreadable v1.1 cases as ERROR instead of crashing or guessing.

7. PRODUCTION READY?
No. Must fix the GateNotMeasured conversion (critical test/harness contract break), guard missing "news" key, stop using private E._parse_time, and add the float guard before any spotlight build can run on real moments. With those four changes the 21 mutations stay killed, all 559 tests pass, and both R-29 and amended ruling 92 are correctly implemented.

SHIP: no