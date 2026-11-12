# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-12 04:25
Models: Grok only (+2 failed: Gemini [no API key], GPT-4o [credit exhausted])

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | N/A | N/A | FAIL | FAIL |
| Law Compliance — L-e / L-g / L-h | N/A | N/A | UNVERIFIABLE | UNVERIFIABLE |
| Law Compliance — Selection / Cut / EDL | N/A | N/A | NOT VERIFIABLE | NOT VERIFIABLE |
| Law Compliance — L-j / L-l / M12 (oracle path) | N/A | N/A | COMPLIANT | COMPLIANT (narrow scope) |
| Oracle/Judge test quality | N/A | N/A | PASS | PASS |
| Diff Scope / Feature Coverage | N/A | N/A | CRITICAL GAP | CRITICAL GAP |
| Overall Readiness | N/A | N/A | NOT READY | NOT READY |

> **Confidence note:** With only 1 of 3 models operational, all findings carry single-model confidence. No majority or unanimous cross-model validation is possible this cycle. Findings are reported as-is; second-pass implementer must apply additional scrutiny.

---

## UNANIMOUS FINDINGS (all 1 operational models agree — implement unconditionally)

### U1 — Wrong diff submitted for the named feature
**What it is:** The artefact under review (`tests/oracle/*` + docs, ~2562 lines) contains zero implementation of the feature named in the ticket. The feature "pulse-sentence-law" is defined by laws L-e, L-g, L-h, L-b, and DEC-10, all of which govern whole punctuated sentence boundaries, spoken-form reading, edge-word handling at cuts, and pause gating. None of this logic appears anywhere in the diff.

**Which file/line:** Entire submitted diff — `tests/oracle/` tree + supporting docs.

**What to change:** Replace the submitted artefact with the actual implementation files:
- `sentence_law.py` (or equivalent module enforcing L-e / L-g / L-h)
- `pipeline/run_fresh.py` cut/EDL logic
- `edge_fades` and `gate_g17_edges` functions
- `edl.json` schema handling
- Corresponding unit/integration tests that exercise sentence-boundary enforcement on real caption and word-timed transcripts

---

### U2 — Oracle/judge tests are sound but entirely out of scope
**What it is:** The existing `tests/oracle/*` tests correctly validate the oracle line-up proposal and blind judge path. Must-fail fixtures (empty replies, malformed schemas, altcoin smuggling, unknown IDs) all raise the documented exceptions. No vacuous assertions exist. These tests are good and must be preserved — but they test a different subsystem.

**Which file/line:** `tests/oracle/*` (all lines)

**What to change:** Preserve all existing oracle/judge tests unchanged. Do not remove or weaken them. They belong to a different feature scope.

---

### U3 — Backtest report explicitly disclaims acoustic sentence law coverage
**What it is:** The backtest report supplied with the diff states in writing that "the acoustic sentence law at the cut (pauses, edge words: DEC-10 / L-b)" is **not measured** by these tests. This is not a documentation gap — it is a confirmed scope mismatch explicitly acknowledged within the artefact itself.

**Which file/line:** Backtest report / diff header.

**What to change:** Either (a) supply the missing implementation and tests so the report's disclaimer is resolved, or (b) formally split the feature ticket so oracle tests ship under a different feature name and pulse-sentence-law remains open until its actual implementation is complete.

---

## MAJORITY FINDINGS (2 of 1 models agree)

*Not applicable. Only one model was operational. All findings are single-model findings.*

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### I1 — Selection-lock / snap-limit / neighbour / onset-tail laws entirely unexercised
**Source:** Grok (both cycles)

**What it is:** Beyond the sentence-boundary laws, the selection-lock, snap-limit, neighbour-window, and onset/tail laws (collectively governing how candidate segments are selected, clamped, and stitched) have zero test coverage anywhere in the diff. These are production-critical for preventing illegal cuts near hard boundaries.

**Assessment:** **Implement.** These are not edge-case laws. Any cut-based feature that ships without enforcement and test coverage for selection-lock and snap-limit will produce audibly illegal cuts in production. This gap would exist even if the correct diff had been submitted.

---

### I2 — No production code path ever invokes sentence_law, edge_fades, or gate_g17_edges
**Source:** Grok Cycle 2

**What it is:** Grok explicitly confirmed that no call site in the submitted diff ever invokes `sentence_law`, `edge_fades`, or `gate_g17_edges`. This means even if these functions exist elsewhere in the codebase, they are not wired into any pipeline path that the submitted tests exercise.

**Assessment:** **Investigate further.** Before the second pass, confirm whether `sentence_law.py`, `edge_fades`, and `gate_g17_edges` exist anywhere in the repo at all. If they exist but are not imported/called in `pipeline/run_fresh.py` or equivalent, the wiring is missing. If they do not exist, they must be written from scratch.

---

### I3 — Spoken-form reading enforcement (L-g) not testable from current artefact
**Source:** Grok Cycle 1 (noted as compliant via inline comment reference) → revised to UNVERIFIABLE in Cycle 2

**What it is:** L-g requires that all numeric values, symbols, and abbreviations in pulse sentences be rendered in spoken form before cut selection. The oracle tests reference this in docstrings but no code path converts "€1.2B" → "one point two billion euros" or similar. No test exercises a must-fail case where a non-spoken-form string reaches the cut layer.

**Assessment:** **Implement.** L-g is not optional. Any sentence containing markup, symbols, or numerals in non-spoken form that reaches the audio layer will produce unintelligible output. Must-fail test: feed a sentence containing "$", "%", or a year like "2024" and assert the law fires before cut.

---

## CONFLICTS (models disagree — tiebreaker)

No conflicts. Only one model was operational. No contradictory recommendations exist.

---

## VALIDATED STRENGTHS (all operational models agree — do NOT change in second pass)

### V1 — Oracle/judge must-fail paths are correctly fail-closed
Every malformed-reply, missing-field, unknown-ID, and altcoin-smuggling fixture correctly raises `OracleFailed` or `JudgeFailed`. No path emits PASS on bad input. These tests are production-quality and must not be weakened or removed.

### V2 — Byte-identity, hash-mismatch, and spend-guard tests are concrete
No vacuous assertions. Each test has explicit positive and negative cases with deterministic expected values.

### V3 — L-j / L-l / M12 compliance on the oracle path
The oracle subsystem correctly requires whole replies and fails closed on partial schemas. Lines 483–523 and 535–558 (as identified by Grok Cycle 1) implement this correctly.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|---|---|---|
| L-e (whole punctuated sentences) | UNVERIFIABLE | No sentence-boundary code in diff |
| L-g (spoken-form reading) | UNVERIFIABLE | No spoken-form conversion code in diff |
| L-h (no markup in output) | UNVERIFIABLE | No output rendering code in diff |
| L-b (edge-word handling at cut) | UNVERIFIABLE | No cut or edge_fades code in diff |
| DEC-10 (pause gating) | UNVERIFIABLE | No gate_g17_edges or acoustic code in diff |
| L-j (whole oracle replies) | COMPLIANT | Tests enforce this correctly |
| L-l (fail-closed on malformed) | COMPLIANT | Tests enforce this correctly |
| M12 (oracle schema) | COMPLIANT | Tests enforce this correctly |
| Selection-lock / Snap-limit | UNVERIFIABLE | No cut/EDL code in diff |
| L-a / L-b / Credits | UNVERIFIABLE | No render/sign-off code in diff |
| L-d / L-22 (v2f reference path) | UNVERIFIABLE | No v2f path in diff |

**Final determination:** 7 of 14 tracked laws are unverifiable because the wrong diff was submitted. 3 laws are confirmed compliant on the oracle path only. The feature cannot be certified law-compliant until the sentence-law / cut / edge-word implementation is supplied and audited.

---

## SECURITY CONSENSUS

No security issues were identified within the oracle/judge test code itself (the only code present). However:

**Gap:** If `sentence_law.py` and `gate_g17_edges` are eventually submitted, the following must be audited for security:
1. **Injection via caption/transcript input** — malformed or adversarially crafted word-timed transcripts must not cause silent failures or bypass sentence-boundary enforcement.
2. **EDL schema validation** — `edl.json` handling must reject unexpected fields and unknown segment types fail-closed, not fail-open.
3. **Spend-guard bypass** — any path that calls `edge_fades` or `gate_g17_edges` must pass through the spend-guard already tested in the oracle path.

These are pre-emptive flags, not confirmed defects, because the relevant code is absent.

---

## WORLD-CLASS GAP CONSENSUS

*Only items mentioned by 2+ models are included. With one operational model, this section reports single-model findings that are structurally significant enough to include regardless.*

### Gap 1 — No sentence-boundary enforcement exists in the submitted artefact
A world-class implementation of a feature named "pulse-sentence-law" would have deterministic, unit-tested enforcement of every sentence-boundary rule before any cut is permitted. The current artefact has none. This is the defining gap.

### Gap 2 — No must-fail tests for mid-sentence cuts, speaker-change splits, or missing terminal punctuation
World-class sentence-law coverage requires:
- Input with no terminal punctuation → cut rejected
- Input where cut falls mid-clause → cut rejected
- Input where speaker changes mid-sentence → cut rejected or flagged
- Input with numerals/symbols → spoken-form conversion verified before cut

None of these test cases exist.

### Gap 3 — Acoustic enforcement (DEC-10 / pause gating) is entirely absent
A world-class implementation would verify that the actual audio waveform satisfies pause requirements at the cut point, not just that the transcript text ends with punctuation. `gate_g17_edges` is the stated mechanism; it does not appear.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Submit the correct diff: sentence_law.py, pipeline/run_fresh.py cut/EDL logic,
              edge_fades, gate_g17_edges, edl.json schema handler
            | sentence_law.py, pipeline/run_fresh.py, edl.json (all absent)
            | models: Grok (sole operational model, confirmed both cycles)
            | Why: The named feature does not exist in the submitted artefact.
              Nothing else can be audited, certified, or shipped until
              the actual implementation is present.

P0 CRITICAL | Add must-fail sentence-boundary tests: mid-sentence cut, missing terminal
              punctuation, speaker-change split, non-spoken-form strings reaching cut layer
            | tests/sentence_law/ (directory to be created)
            | models: Grok
            | Why: L-e, L-g, L-h, L-b compliance cannot be verified without these.
              Silent pass-through of illegal cuts is a production audio defect.

P1 HIGH     | Confirm existence of sentence_law.py, edge_fades, gate_g17_edges in repo.
              If absent: implement from scratch per PULSE_SENTENCE_LAW_GOSPEL.md.
              If present but unwired: add import and call sites in pipeline/run_fresh.py.
            | pipeline/run_fresh.py (call sites), sentence_law.py (implementation)
            | models: Grok (I2)
            | Why: No production code path invokes the sentence-law functions.
              Even if they exist, they have no effect unless called.

P1 HIGH     | Implement and test L-g spoken-form conversion with must-fail fixture:
              sentence containing "$", "%", year "2024", or "€1.2B" must be
              rejected or converted before reaching cut layer.
            | sentence_law.py (spoken_form_check function)
            | models: Grok (I3)
            | Why: L-g is not optional. Non-spoken-form strings produce
              unintelligible audio output in production.

P1 HIGH     | Implement and test selection-lock, snap-limit, neighbour-window,
              and onset/tail laws with deterministic must-fail fixtures.
            | sentence_law.py, pipeline/run_fresh.py
            | models: Grok (I1)
            | Why: These laws prevent illegal cuts near hard boundaries.
              No coverage exists anywhere in the submitted artefact.

P2 MEDIUM   | Formally resolve the backtest report disclaimer:
              Either (a) add acoustic sentence law measurement to the backtest report,
              or (b) split the ticket so oracle tests ship under a different feature name
              and pulse-sentence-law remains open until implementation is complete.
            | docs/audits/, backtest report
            | models: Grok (U3)
            | Why: Shipping a feature with an in-document disclaimer that its
              core law is not measured is a compliance and audit trail risk.

P2 MEDIUM   | Pre-emptive security audit of EDL schema validation and caption/transcript
              input handling once sentence_law.py is submitted:
              — edl.json must reject unknown segment types fail-closed
              — word-timed transcripts must reject adversarial input without silent bypass
            | sentence_law.py, edl.json handler
            | models: Grok (security gap, pre-emptive)
            | Why: Input-layer validation failures on the cut path will produce
              either silent bad cuts or exploitable bypass of sentence-law enforcement.
```

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

**Absolute final blocker:** The code under review is not the code that implements the named feature. The diff contains only oracle-selection tests for a different subsystem. The sentence-law / cut / edge-word / acoustic-pause implementation — the entire substance of the "pulse-sentence-law" feature — is absent from the submitted artefact.

No amount of iteration on the oracle tests will resolve this. The feature cannot be certified, law-compliant, or production-ready until the correct implementation is submitted and audited.

The oracle/judge tests that *are* present are sound and should ship with their own feature. They must not be lost or weakened.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The feature was reviewed by 1 independent AI model across 2 cycles.
The audit determined that the submitted artefact contained only oracle/judge
tests and did not include the sentence-law implementation. Implement every
P0 and P1 item below. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Submit/implement the correct modules: sentence_law.py,
              pipeline/run_fresh.py cut/EDL logic, edge_fades, gate_g17_edges,
              edl.json schema handler — all currently absent from the artefact.
            | Files: sentence_law.py, pipeline/run_fresh.py, edl.json handler

P0 CRITICAL | Create tests/sentence_law/ and add must-fail tests for:
              — mid-sentence cut (no terminal punctuation) → rejected
              — speaker-change mid-sentence → rejected or flagged
              — non-spoken-form string ("$", "%", "2024", "€1.2B") reaching
                cut layer → rejected or converted
              — missing terminal punctuation → cut blocked
            | Files: tests/sentence_law/ (new directory)

P1 HIGH     | Verify sentence_law.py, edge_fades, gate_g17_edges exist in repo.
              If absent: implement per PULSE_SENTENCE_LAW_GOSPEL.md.
              If present but unwired: add import and call sites in
              pipeline/run_fresh.py so the functions are actually invoked
              on every cut decision.
            | Files: pipeline/run_fresh.py, sentence_law.py

P1 HIGH     | Implement L-g spoken-form conversion in sentence_law.py.
              Add must-fail unit test: any sentence with numerals, currency
              symbols, or abbreviations must fail or be converted before
              the cut layer accepts it.
            | Files: sentence_law.py, tests/sentence_law/test_spoken_form.py

P1 HIGH     | Implement and test selection-lock, snap-limit, neighbour-window,
              and onset/tail laws in sentence_law.py and pipeline/run_fresh.py.
              Add deterministic must-fail fixtures for each boundary condition.
            | Files: sentence_law.py, pipeline/run_fresh.py,
                     tests/sentence_law/test_selection_laws.py

P2 MEDIUM   | Resolve the backtest report disclaimer about acoustic sentence law
              not being measured. Either add DEC-10 / pause gating measurement
              to the backtest report, or formally split the feature ticket.
            | Files: docs/audits/, backtest report

P2 MEDIUM   | Once sentence_law.py is implemented, audit edl.json schema
              validation for fail-closed behaviour on unknown segment types
              and adversarial word-timed transcript input.
            | Files: sentence_law.py, edl.json handler

VALIDATED (do NOT touch — confirmed excellent by audit):
— All existing tests/oracle/* tests: oracle/judge must-fail paths are
  correctly fail-closed. Do not remove, weaken, or modify these tests.
— Byte-identity, hash-mismatch, and spend-guard tests: concrete and correct.
— L-j / L-l / M12 compliance on the oracle path: correctly implemented.

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

## WINNER: Grok

Grok delivered the only operationally valid analysis in both cycles, correctly identifying the critical scope mismatch ("wrong diff for the stated feature") in Cycle 1 and then self-auditing honestly in Cycle 2 by acknowledging where its Cycle 1 findings could have been more precise — without inflating or retracting correct conclusions. With Gemini and GPT-4o absent, Grok's findings cannot be cross-validated by majority, but on the four criteria: its accuracy proved out in the consensus, it found the depth issue (oracle vs. sentence-law subsystem mismatch) others would have confirmed, its recommendations were specific and implementable (named exact missing files), and it covered every scoreable section despite the diff being deliberately narrow.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by severity and logical dependency. Items marked **BLOCKER** must be resolved before any other work proceeds.

---

### P0 — BLOCKER: Submit the correct diff

**Action:** Discard the current artefact. The reviewer, CI gate, and any downstream implementer are evaluating the wrong code. Open a corrected PR containing:

| Required file | Why required |
|---|---|
| `sentence_law.py` | Core enforcement of L-e, L-g, L-h — whole punctuated sentence boundary logic |
| `pipeline/run_fresh.py` | Cut logic and EDL handling that calls `sentence_law` |
| `edge_fades()` | Edge-word fade enforcement at cut boundaries (DEC-10) |
| `gate_g17_edges()` | Pause gating at G17 edges |
| `edl.json` schema + handler | Structured edit decision list consumed by the cut path |
| Tests for all of the above | Must exercise positive and negative cases for every law listed below |

**Do not re-review until this replacement diff is submitted.**

---

### P1 — BLOCKER: Verify L-e enforcement (whole punctuated sentences)

**Action:** Confirm that `sentence_law.py` rejects any cut whose start or end point does not coincide with a sentence boundary (period, question mark, exclamation mark — no mid-sentence splits). Write a must-fail test with a mid-sentence cut and confirm it raises the documented exception. Write a must-pass test with a clean sentence boundary.

---

### P2 — BLOCKER: Verify L-g enforcement (spoken-form reading)

**Action:** Confirm that any text passed to the voice pipeline has been converted to spoken form (numbers, abbreviations, symbols expanded) before the cut is finalized. Write a must-fail fixture containing raw numerals or symbols and confirm rejection.

---

### P3 — BLOCKER: Verify L-h enforcement (no markup)

**Action:** Confirm that no markdown, HTML, or formatting tokens survive into the cut output. Write a must-fail fixture containing markup and confirm rejection.

---

### P4 — BLOCKER: Verify L-b / DEC-10 edge-word handling

**Action:** Confirm that `edge_fades()` and `gate_g17_edges()` are invoked on every cut, that the first and last words of each cut are tested against the DEC-10 boundary rules, and that cuts with disallowed edge words are rejected. Write explicit onset and tail fixtures.

---

### P5 — HIGH: Verify Selection-Lock and Snap-Limit laws

**Action:** These were marked NOT VERIFIABLE in both cycles because no cut or EDL code appeared in the diff. Once the correct diff is submitted, confirm:
- Selection lock prevents recomputation of first/last words after a selection is committed
- Snap limit is enforced (no cut beyond the allowed snap distance)
- Neighbour constraints are respected

Write must-fail fixtures for each violation type.

---

### P6 — HIGH: Verify EDL schema completeness

**Action:** Confirm that `edl.json` schema validation rejects malformed or partial edit decision records. Write must-fail fixtures for missing required fields (cut-in point, cut-out point, source ID, sentence boundary markers).

---

### P7 — MEDIUM: Preserve and integrate existing oracle/judge tests

**Action:** The oracle/judge tests in the submitted artefact are correctly written and must not be discarded. They are out of scope for the pulse-sentence-law feature but are valid tests for the oracle subsystem. Integrate them into the oracle test suite under their own CI target, separate from the sentence-law CI target, so they do not create false coverage signals for this feature.

---

### P8 — MEDIUM: Add cross-subsystem integration test

**Action:** Once P0–P6 are resolved, add one end-to-end integration test that exercises the full path: oracle proposes a line-up → pipeline calls `sentence_law` → cut is validated against L-e / L-g / L-h / L-b / DEC-10 → EDL is written → output is confirmed to contain only clean whole-sentence cuts in spoken form with no markup and valid edge words.

---

### P9 — LOW: Confidence flag on all findings this cycle

**Action:** Tag all findings from this cycle in your tracking system as **single-model confidence** (Grok only). Before closing any P0–P6 item as resolved, obtain at least one independent review — human or second LLM — to restore cross-model validation that the API failures prevented.