# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-12 04:26
Models: grok (+2 failed: gemini [no key], gpt4o [quota exhausted])

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness — parse_oracle / parse_judge | NOT RUN | NOT RUN | PASS | PASS (single-model) |
| Correctness — Ledger / spend guard | NOT RUN | NOT RUN | PASS | PASS (single-model) |
| Correctness — call_backend / ContextTooLong | NOT RUN | NOT RUN | PASS | PASS (single-model) |
| Correctness — export / SHA / sentence_law | NOT RUN | NOT RUN | PASS | PASS (single-model) |
| Correctness — replay write guard | NOT RUN | NOT RUN | PASS | PASS (single-model, unverified edge cases) |
| Law Compliance (L-j/l/m/x/h/k) | NOT RUN | NOT RUN | PASS | PASS (single-model) |
| Tests — must-fail fixtures | NOT RUN | NOT RUN | FAIL | FAIL (confirmed absent) |
| Overall | NOT RUN | NOT RUN | READY WITH CONDITIONS | CONDITIONAL — test gap is blocker |

> **Confidence discount applied throughout.** All findings derive from a single model across two cycles. The normal 3-model corroboration that would elevate a PASS to high-confidence is absent. Every PASS below carries an implicit "(unconfirmed by independent models)" qualifier.

---

## UNANIMOUS FINDINGS (all 1 models agree — implement unconditionally)

### U-1 · Missing must-fail test suite
**What it is:** No test files appear in the diff. The fail-closed contracts for `parse_oracle`/`parse_judge`, `Ledger` cap enforcement, `ContextTooLong` pre-send rejection, SHA re-verification, and the replay write-guard are implemented but entirely untested within this changeset.

**Files/lines affected:**
- `lineup.py:777-827` — `parse_oracle`, `parse_judge` → need schema-violation fixtures
- `llm.py:1064-1095` — `Ledger.reserve`/`settle` → need over-cap fixture
- `providers.py:1615-1664` — `call_backend` → need `ContextTooLong` rejection fixture
- `export.py:456-505` — SHA re-verification → need SHA-mismatch fixture
- `replay.py:1824-1893` — write guard → need write-attempt fixture

**What to change:** Deliver Package B (the test suite). At minimum, one must-FAIL fixture per enforcement point, exercised in CI before any merge that touches real spend or the live transcript store.

---

## MAJORITY FINDINGS (2 of 1 models agree)

> **Not applicable.** Only one model completed review. This section is structurally empty — no majority can form from a single source. All findings are reported either as Unanimous (Grok C1 + Grok C2 agree) or Unique.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### I-1 · replay.py write-guard completeness against tempfile / shutil / pathlib edges
**Source:** Grok Cycle 2  
**Observation:** `no_writes_under` (replay.py:1824-1893) monkey-patches known OS builtins but may not intercept `tempfile`, `shutil.copy*`, `pathlib.Path.write_*`, or third-party libraries that open file handles internally.  
**Assessment: INVESTIGATE FURTHER — implement if gaps found.**  
Rationale: The write-guard is the single most security-critical new code path. A gap here would violate the "never write under main tree" rule silently. Audit the monkey-patch list against Python's stdlib surface for file mutation and add stubs for any uncovered calls. If coverage is already complete, document it explicitly.

### I-2 · ab.py swap construction / _agree logic off-by-one risk on must-fail items
**Source:** Grok Cycle 2  
**Observation:** The AB harness overlap calculation and `WITHDRAWN` filtering is intricate. A single off-by-one could silently drop required negative cases, allowing a PASS on malformed data.  
**Assessment: INVESTIGATE FURTHER.**  
Rationale: This is a low-probability but high-impact failure mode (silent PASS). A lightweight property test — generate random must-fail inputs, assert they never appear in the PASS bucket — would close this risk cheaply.

### I-3 · Stale-file protection depends on every downstream consumer calling fresh()
**Source:** Grok Cycle 2  
**Observation:** `run.py:fresh` + `oracle_sha256` protect against stale artefacts, but only if every consumer of `GROUPS.json`, `WITNESS.json`, and `SCORE.json` calls `fresh()` before reading. One missed call creates a silent data-integrity hole.  
**Assessment: IMPLEMENT — low effort, high safety margin.**  
Rationale: Add an explicit `fresh()` call (or assertion) at the top of every consumer that reads those three files. Can be a one-liner guard that raises immediately if the SHA does not match.

### I-4 · Three independent exports should be byte-identical on same input
**Source:** Grok Cycle 2  
**Observation:** No test verifies that the three export paths produce byte-identical output for the same transcript.  
**Assessment: IMPLEMENT (P2).**  
Rationale: A lightweight property test here catches any divergence introduced by future refactors at near-zero cost.

---

## CONFLICTS (models disagree — your tiebreaker)

**No conflicts.** Only one model completed review. Where Grok C1 and Grok C2 differed (overall verdict: "READY" → "READY WITH CONDITIONS"), this represents a single model updating its own assessment — not a cross-model conflict. The C2 assessment (conditional) is correct and supersedes C1.

---

## VALIDATED STRENGTHS (all models agree this is already excellent — do NOT change)

The following were confirmed correct in both Grok cycles. Do not modify these in the second pass:

1. **`parse_oracle` / `parse_judge` fail-closed schema enforcement** (lineup.py:777-827) — raises `OracleFailed`/`JudgeFailed` on any missing, mistyped, or inconsistent field; never returns partial answers.

2. **`Ledger.reserve` / `settle` exclusive-lock + pid-check + cap enforcement** (llm.py:1064-1095) — `SpendStop` fires before any remote request; no race condition path identified.

3. **`call_backend` ContextTooLong pre-send rejection + key hygiene** (providers.py:1615-1664) — rejects oversized context before the wire; vendor-side errors treated as retryable; keys never logged.

4. **`export_run` / `tokens` / `sentences` SHA re-verification + sentence_law delegation** (export.py:456-505) — transcript SHA verified on read; sentence boundaries delegated exclusively to `sentence_law.is_terminal`; no recomputation of first/last words post-selection.

5. **L-j / L-l / L-m / L-x / L-h / L-k compliance** — vendor separation, judge-chain isolation, local GPU0 lease-only, canon import flat, selection lock, snap limit — all confirmed by construction.

6. **`replay.py` no-writes guard implementation** (replay.py:1824-1893) — guard is present and aggressive (edge-case completeness flagged separately but core implementation is sound).

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|---|---|---|
| L-j (judge independence) | **COMPLIANT** | lineup.py:740-746, 806-827; judge chain never includes writer vendor |
| L-l (lineup integrity) | **COMPLIANT** | lineup.py confirmed; no partial returns |
| L-m (model separation) | **COMPLIANT** | providers.py:1680-1693; ab.py:258-262 |
| L-x (vendor isolation / key hygiene) | **COMPLIANT** | providers.py:1439-1444, 1521-1546, 1670-1693; local GPU0 under lease only |
| L-h (hash / canon) | **COMPLIANT** | export.py:394, 456, 484; canon imported flat |
| L-k (selection lock / snap limit) | **COMPLIANT** | export.py:375; lineup.py:841-894; backtest never edits cuts |
| Sentence law | **COMPLIANT** | `sentence_law.is_terminal` is the sole boundary authority |

> **Confidence caveat:** All law compliance determinations rest on a single model's review. No independent corroboration was possible this cycle due to key/quota failures.

---

## SECURITY CONSENSUS

Ranked by risk (single-model assessment):

1. **[P0] Untested write-guard** — `replay.py:1824-1893` is the only barrier preventing replay from corrupting the main transcript store. Untested = unverified barrier.

2. **[P1] write-guard coverage gaps** — `tempfile`, `shutil`, `pathlib.Path.write_*` and third-party file-opening libs may bypass the monkey-patch. A bypass here is a silent data-corruption vector.

3. **[P1] Stale-artefact consumer gap** — Any consumer of `GROUPS.json` / `WITNESS.json` / `SCORE.json` that skips `fresh()` can silently operate on stale data, producing a PASS on old evidence.

4. **[P2] ab.py silent-drop risk** — Off-by-one in must-fail overlap could allow a PASS verdict on malformed data without raising any exception.

---

## WORLD-CLASS GAP CONSENSUS

> Items 2+ models would need to flag for this section. With only one model completing review, no items meet the threshold by definition.

**Noted for record (single-model only, not consensus):**
- Absence of a must-fail test suite is the dominant gap. A world-class audit system enforces its fail-closed contracts through tests, not only through code.
- No property-based / generative testing exists for the AB harness or export idempotency.
- `no_writes_under` completeness is not documented; a world-class implementation would include an explicit coverage matrix for all file-mutation entry points patched.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Deliver must-fail test fixtures: schema violations → `OracleFailed`/`JudgeFailed`; over-cap → `SpendStop` before any remote call; oversized context → `ContextTooLong`; SHA mismatch → `ExportError`; write-attempt under MAIN_TREE → `PermissionError` | lineup.py:777-827, llm.py:1064-1095, providers.py:1615-1664, export.py:456-505, replay.py:1824-1893 (new test file) | grok (C1+C2) | Untested fail-closed code is the only remaining systemic risk; every other subsystem confirmed correct |
| **P1 HIGH** | Audit `no_writes_under` monkey-patch list against full stdlib file-mutation surface (`tempfile`, `shutil.copy*`/`move`, `pathlib.Path.write_bytes`/`write_text`/`open`, `io.open`, `os.open`, `os.rename`, `os.replace`); add stubs for any uncovered entry points; document coverage matrix | replay.py:1824-1893 | grok C2 | Single missed entry point silently violates "never write under main tree" |
| **P1 HIGH** | Add explicit `fresh()` guard (raises on SHA mismatch) at the entry point of every consumer of `GROUPS.json`, `WITNESS.json`, `SCORE.json` | run.py + all consumer call-sites | grok C2 | One missed call = silent data-integrity hole; stale PASS verdict possible |
| **P2 MEDIUM** | Add property test: generate N random must-fail oracle/judge inputs, assert none appear in the PASS bucket (catches ab.py off-by-one in overlap / WITHDRAWN filtering) | ab.py:258-262 (new test) | grok C2 | Low-probability, high-impact silent-PASS failure mode; cheap to close |
| **P2 MEDIUM** | Add byte-identity property test: same transcript through all three export paths must produce identical output | export.py:456-505 (new test) | grok C2 | Zero-cost regression guard against future divergence |

---

## CYCLE 2 VERDICT

**CONDITIONAL — not production-ready until P0 is closed.**

The implementation logic is well-constructed and law-compliant as reviewed. Every enforcement point (strict parsing, spend cap, context rejection, SHA re-verification, write guard) is fail-closed by design. No silent-PASS path was identified in the code itself.

**The absolute final blocker is the absence of Package B (the test suite).**

Untested defensive code is not the same as defended code. The fail-closed contracts — `OracleFailed`, `JudgeFailed`, `SpendStop`, `ContextTooLong`, SHA mismatch rejection, write-guard — must be exercised by must-fail fixtures in CI before any run that touches real spend or the live transcript store.

**Additional blocker-class risk:** The `no_writes_under` monkey-patch completeness (P1) must be verified before the replay subsystem is used in any environment with write access to the main tree.

Once P0 is closed and P1 is verified, the implementation meets the stated laws and the fail-closed contract. P2 items are strongly recommended before the system handles production volume.

**Confidence in this verdict: MODERATE.** Two of three intended reviewers failed due to infrastructure issues (no Gemini key, GPT-4o quota exhausted). The normal independent corroboration that justifies high confidence in a "PASS" is absent. The P0 test requirement becomes doubly important as a compensating control for the reduced review coverage.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 1 independent AI model across 2 cycles
(2 of 3 models failed due to missing Gemini key and GPT-4o quota exhaustion).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Deliver must-fail test suite (Package B) | new test file covering lineup.py:777-827, llm.py:1064-1095, providers.py:1615-1664, export.py:456-505, replay.py:1824-1893 | models: grok C1+C2 | Untested fail-closed code is the only remaining systemic risk
  Required fixtures:
    - Schema violation (missing field) → OracleFailed
    - Schema violation (mistyped field) → OracleFailed
    - Inconsistent verdict → JudgeFailed
    - Ledger over-cap → SpendStop fires BEFORE any remote call is made
    - Context too long → ContextTooLong rejected pre-send
    - SHA mismatch on transcript read → ExportError
    - Write attempt under MAIN_TREE during replay → PermissionError

P1 HIGH | Audit and complete no_writes_under monkey-patch | replay.py:1824-1893 | models: grok C2 | Single uncovered entry point silently violates write isolation
  Verify coverage of: tempfile.*, shutil.copy/copy2/move/copyfile, pathlib.Path.write_bytes/write_text/open, io.open, os.open, os.rename, os.replace, os.link, os.symlink
  Document the coverage matrix as a comment block adjacent to the guard

P1 HIGH | Add fresh() guard at every consumer entry point | run.py + all call-sites reading GROUPS.json / WITNESS.json / SCORE.json | models: grok C2 | Missed call = silent stale-data PASS

P2 MEDIUM | Property test: N random must-fail oracle/judge inputs → none appear in PASS bucket | ab.py:258-262 (new test) | models: grok C2 | Closes ab.py off-by-one silent-drop risk cheaply

P2 MEDIUM | Byte-identity property test: same transcript through all three export paths → identical output | export.py:456-505 (new test) | models: grok C2 | Zero-cost regression guard

VALIDATED (do NOT touch — confirmed excellent by all completed reviews):
- parse_oracle / parse_judge fail-closed schema enforcement (lineup.py:777-827)
- Ledger.reserve / settle exclusive-lock + pid-check + SpendStop cap (llm.py:1064-1095)
- call_backend ContextTooLong pre-send rejection + key hygiene (providers.py:1615-1664)
- export_run / tokens / sentences SHA re-verification + sentence_law.is_terminal delegation (export.py:456-505)
- L-j / L-l / L-m / L-x / L-h / L-k law compliance (all confirmed by construction)
- replay.py no_writes_under core implementation (replay.py:1824-1893) — extend coverage, do not rewrite

NOTE: Two of three intended Cycle 2 reviewers failed (no Gemini key in .env per backtest
order; GPT-4o quota exhausted). The P0 test suite is doubly important as a compensating
control for the reduced independent review coverage. Do not ship to production until
Package B is delivered, reviewed, and passes CI.

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

# WINNER: Grok

Grok delivered the only substantive analysis across both cycles, correctly identifying law compliance, fail-closed parsing behavior, spend guard mechanics, and the replay write-guard — all of which held up under Cycle 2 scrutiny. Critically, Grok self-corrected in Cycle 2 by acknowledging the test-coverage gap it had underweighted in Cycle 1, demonstrating the kind of honest recalibration that distinguishes a high-quality audit from a rubber-stamp.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by risk-to-correctness, highest first.

---

## P0 — BLOCKERS (must resolve before any PASS is elevated to confirmed)

### P0-1 · Must-fail test suite (U-1, confirmed absent)
The single highest-risk gap. Every fail-closed contract is implemented but unverified by executable fixtures.

| Target | Required fixture |
|---|---|
| `lineup.py:777-827` | Schema-violation input → assert `OracleFailed`/`JudgeFailed` raised, never a partial return |
| `llm.py:1064-1095` | Spend at exactly cap, then one-over → assert `SpendStop` before any HTTP call |
| `providers.py:1615-1664` | Prompt at token limit → assert `ContextTooLong` raised pre-send; vendor 4xx → assert retry, not propagation |
| `export.py:456-505` | Corrupt SHA in transcript → assert re-verification raises, never silently passes |
| `replay.py:1824-1893` | Attempt write under main tree via `pathlib`, `os`, `shutil`, `tempfile` → assert each is blocked |

**Acceptance bar:** Every fixture must assert the *exception type and message*, not just that an exception occurred. No vacuous `pytest.raises(Exception)`.

---

## P1 — HIGH RISK (implement before production deployment)

### P1-1 · Replay write-guard completeness
**Risk:** The monkey-patching at `replay.py:1824-1893` is the single most security-critical new code block. Gaps in coverage (symlinks resolving outside the guard, `tempfile.NamedTemporaryFile`, third-party libraries opening file handles) would silently violate the "never write under main tree" invariant.

**Required actions:**
1. Enumerate every write surface: `open()`, `pathlib.Path.write_text/write_bytes/touch`, `os.open`, `os.rename`, `shutil.copy/move`, `tempfile.*`
2. Verify each is patched or proxied through the guard
3. Add a symlink-traversal fixture: create a symlink pointing into the main tree, attempt write through replay, assert blocked

---

### P1-2 · `ab.py` swap / `_agree` logic for must-fail items
**Risk:** A single off-by-one in overlap calculation or incorrect `WITHDRAWN` filtering could silently drop required negative cases, allowing a corrupt artefact to score as PASS.

**Required actions:**
1. Add unit tests for `_agree` with boundary inputs: exactly zero overlap, exactly one overlap, all-WITHDRAWN set
2. Verify swap construction preserves must-fail item indices under all reorder permutations
3. Assert that a WITHDRAWN item never contributes a positive vote to the consensus

---

## P2 — MEDIUM RISK (resolve within one sprint)

### P2-1 · Stale-file protection completeness
**Risk:** `run.py:fresh` + `oracle_sha256` is correctly implemented, but its protection is only as strong as every downstream consumer (score, report, witness) actually calling it. A consumer that skips the freshness check silently reads stale artefacts.

**Required actions:**
1. Audit every call site that reads oracle/transcript files; confirm each calls `fresh()` before read
2. Add an integration test: write a stale artefact, invoke each downstream consumer, assert each raises or refuses

---

### P2-2 · Confidence discount on all single-model PASSes
**Risk:** Every PASS in the consensus table carries zero independent corroboration. This is a process gap, not a code gap, but it inflates apparent confidence.

**Required actions:**
1. Re-run Cycle 1 with at least one additional model (Gemini or GPT-4o) once quota/key issues resolve
2. Promote single-model PASSes to confirmed only after ≥2 models independently agree
3. Document the confidence level explicitly in the final audit report header

---

## P3 — LOW RISK (track, do not block release)

### P3-1 · `ContextTooLong` retry classification
Grok noted vendor-side errors are treated as retryable. Confirm `ContextTooLong` is explicitly *non-retryable* (retrying an over-length prompt will always fail and waste spend budget).

### P3-2 · `sentence_law.is_terminal` delegation audit
Export correctly delegates sentence boundaries exclusively to `sentence_law.is_terminal`. Verify no caller in the new diff imports or invokes any alternative boundary detector, even as a fallback.

---

## SUMMARY TABLE

| Priority | Item | Files | Blocking release? |
|---|---|---|---|
| P0-1 | Must-fail test suite | `lineup.py`, `llm.py`, `providers.py`, `export.py`, `replay.py` | **YES** |
| P1-1 | Replay write-guard completeness | `replay.py:1824-1893` | YES |
| P1-2 | `ab.py` swap / `_agree` must-fail logic | `ab.py` | YES |
| P2-1 | Stale-file consumer audit | `run.py` + all downstream | No, but sprint-bound |
| P2-2 | Multi-model corroboration | Process | No, but sprint-bound |
| P3-1 | `ContextTooLong` non-retryable check | `providers.py` | No |
| P3-2 | `is_terminal` delegation audit | `export.py` + callers | No |