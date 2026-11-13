# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 110 s finish=stop usage in 48072 / out 1088 usd~0.268 (upper-bound price)

**P0: pipeline/package.py:226 (assemble_medley / _package)**
- `assemble_medley` (and `_package`) never writes `"runtime_s_estimate"` into the returned `pk` dict.
- `cheap_checks` (line 597) does `RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]` unconditionally; `ly_shape`, `r4`, logging, and `_takeaway_record` also read it.
- Concrete failure: `medley_pk()` (or any `assemble_medley` call with 39 s clips + 8-word takeaway) → `KeyError` in `cheap_checks` (or `rt_ok=False` / RUNTIME gate FAIL). The new test at `tests/package/test_medley.py:1692` asserts exactly this key with a specific numeric value; it cannot pass against the implementation shown. All medley packages are blocked before any gate inventory is written (violates L-j, LAW 20).

**P1: pipeline/package.py:484 (write_takeaway budget intersection) + 828 (redo message)**
- When a flagged join exists and no bridge has been written yet, `takeaway_budget(..., other=w(LY_BRIDGE_MIN_WORDS))` and `...w(LY_BRIDGE_WORDS)` are computed; their intersection is taken only if both succeed and `both[0] <= both[1]`, else `long_` is used.
- The redo text appended to a RUNTIME violation assumes a `(lo, hi)` pair exists (`if v["rule"] == "RUNTIME" ... (a takeaway of {b[0]}-{b[1]} words ...)`).
- Concrete failure: clip seconds that make the min-bridge budget return `None` while the max-bridge budget succeeds → `budget=None`, fallback to `(LY_TAKEAWAY_MIN_WORDS, CAP)`, then a later RUNTIME violation produces a malformed redo string containing the literal "None" (writer receives garbage extra prompt). Matches the "qwen P1, grok P2" comment but is not guarded; violates "never change what a check accepts to make a render pass" (LAW 20 / M2) and fail-closed (M12).

**P2: pipeline/package_pin.py:1002 (bridge_slots + line_problems) + pipeline/package.py:569 (ly_shape text match)**
- Both perform exact `!=` / `.strip() !=` on VO/bridge lines and `sorted(bridged) != sorted(med["flagged"])`.
- LAW L-k requires *every* text comparison to route through `canon.py` (entities, split tokens, spoken forms, numbers, signs). No `canon.same(...)` or `canon.canon_tokens` call is present.
- Concrete failure: writer returns bridge `"S&P"` while `vo["bridges"]` normalizes to `"S & P"` (or canonical apostrophe / comma variant per L-h/L-g); `line_problems` or `ly_shape` treats them as mismatch → `PinRefused` even though a listener hears identical words and the bytes sent to render are semantically identical. Blocks L-j authorisation on otherwise clean gates. (Exact string is appropriate for "these bytes" but the governing law is violated as written.)

**P2: tests/package/proof_ly.py:1293 (table) + 1302 (firsts)**
- `judged = [x for x in takes if x.get("passed") is not None]`; `firsts = [x for x in judged if x.get("write") == 1]`.
- `_takeaway_record` can leave `"passed": None` when cheap gates stop before the classifying verdict (explicitly documented).
- Concrete failure: a write stopped by LY_SHAPE or R4 before fidelity verdict runs → counted in `tot["judged"]` / `tot["first_judged"]` but its `None` is silently ignored in pass-rate math, under-counting "judged" relative to the gate inventory that actually ran. The table shipped to STATE therefore misreports the takeaway pass rate. (Minor but violates "honest" recording required by L-y 6 and the proof's own comment.)

No other violations of the listed governing laws (L-a through L-l, SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-c dissent-until-disproved on final bytes, L-j exact inventory, L-k canon where semantic, L-l strict JSON contracts, M12 fail-closed, LAW 22 v2f byte-identical) could be verified from the diff alone; early CUTTABLE/L-v 2 filtering, medley contract strictness, `ly_shape` must-fail cases, vendor-reported cost ledger, prompt changes for commentary tests, and loop control (clips-alone first, doomed moments, reline on declined bridge) all match the stated L-y rules and ROUND-2 amendments. The removed `plain_vo` / styles code is correctly dead after L-y.

**Verdict: SHIP: no** (P0 runtime key omission must be fixed before merge; it breaks every medley path and the new test suite).