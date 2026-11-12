# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-12 04:24
Models: grok (+2 failed)

---

## ⚠️ AUDIT INTEGRITY NOTICE

**Only 1 of 3 models completed review.** Gemini 2.5 Pro failed (no API key in `.env`); GPT-4o failed (exhausted credits). All "consensus" conclusions below are derived from a **single model (Grok-3)**. This materially reduces confidence. No true consensus, majority, or conflict analysis is possible. All findings should be treated as **single-reviewer opinions**, not ensemble validation.

Recommended remediation before treating this report as authoritative:
1. Add a valid Gemini key to `/home/ultron/protocol_pulse/.env`
2. Reload GPT-4o credits or substitute Claude/another model
3. Re-run Cycle 1 with all 3 models before proceeding to build pass

Proceeding with the report structure as requested, with appropriate confidence discounting throughout.

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness — parse\_oracle / parse\_judge | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Correctness — Ledger.reserve / settle | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Correctness — call\_backend | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Correctness — export\_run / tokens / sentences | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Correctness — replay | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Law Compliance — L-j / L-l / L-m | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Law Compliance — L-x | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Law Compliance — L-h / L-k | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Sentence Law / SELECTION LOCK / SNAP LIMIT | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Security — key hygiene | ❌ NOT RUN | ❌ NOT RUN | ✅ PASS | ⚠️ UNCONFIRMED |
| Tests — must-fail fixtures | ❌ NOT RUN | ❌ NOT RUN | ⚠️ NOT VERIFIED | ⚠️ UNCONFIRMED |
| Overall Verdict | ❌ NOT RUN | ❌ NOT RUN | ✅ READY | ⚠️ LOW CONFIDENCE |

---

## UNANIMOUS FINDINGS (all 1 active models agree — implement unconditionally)

**With only 1 model, "unanimous" means Grok's uncontested findings. Confidence is LOWER than a true unanimous finding from 3 models.**

### Finding U-1: Test Coverage Is Unverified
- **What:** Grok explicitly noted no test files appear in this diff (Package A). Must-fail fixtures and vacuous assertion absence cannot be confirmed.
- **File/Line:** Test suite — location unspecified (not in diff)
- **What to change:** Test files covering `parse_oracle`/`parse_judge` failure paths, `Ledger.reserve` cap enforcement, `call_backend` `ContextTooLong` rejection, `export_run` SHA re-verification, and `replay` write-guard must be audited and confirmed present. If absent, they must be created.
- **Confidence:** Single-model observation — but structurally valid; a diff without tests is a universal code review flag regardless of model count.

---

## MAJORITY FINDINGS (2 of 1 models agree)

**Not applicable.** Only 1 model completed review. No majority threshold can be computed. This section is structurally empty by definition.

> No majority findings can be reported. This section will be populated in Cycle 2 if all 3 models run successfully.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

Since all findings originate from Grok alone, every observation below is a "unique insight" by definition. Assessment is provided for each.

### Insight G-1: `parse_oracle`/`parse_judge` raise on partial answers (lineup.py:777–827)
- **Grok's claim:** These functions never return a partial answer; they raise `OracleFailed`/`JudgeFailed` on any missing/mistyped field.
- **Assessment:** **ACCEPT — but verify independently.** This is exactly the correct behavior for hard failure semantics. However, with no second model to corroborate, edge cases (e.g., a field present but typed as `None`, or a verdict field containing an unexpected enum value that happens to coerce truthy) remain unconfirmed. Recommend adding a negative-fixture test that feeds each failure mode explicitly.

### Insight G-2: Ledger exclusive lock + pid check (llm.py:1064–1095)
- **Grok's claim:** `reserve`/`settle` use an exclusive lock and PID check; calls past the cap raise `SpendStop` before any remote request.
- **Assessment:** **ACCEPT — but verify race condition path.** The exclusive lock claim is reassuring, but Grok did not comment on what happens if the process holding the lock dies between `reserve` and `settle` (lock orphan / leaked reservation). This is a classic concurrency gap. **Investigate further.**

### Insight G-3: `call_backend` never prints keys (providers.py:1615–1664)
- **Grok's claim:** No key material appears in logs or exceptions.
- **Assessment:** **ACCEPT — but add a negative test.** Key-in-log bugs are subtle and often introduced by future changes (e.g., logging a full request dict). A test that asserts no log output matches a key pattern would make this durable. Flag as P2.

### Insight G-4: `export_run`/`tokens`/`sentences` re-verify transcript SHA (export.py:505–467)
- **Grok's claim:** SHA re-verification occurs; sentence boundaries exclusively from `sentence_law.is_terminal`; no recomputation of first/last words after selection.
- **Assessment:** **ACCEPT — high importance.** The SELECTION LOCK and SNAP LIMIT invariants are core to the law. If these hold, they should be protected by regression tests that mutate the transcript and assert failure. Confirm tests exist.

### Insight G-5: `replay` write-guard (replay.py:1824–1893, 1909–1962)
- **Grok's claim:** `replay` never writes under the main tree; stops on first `NotRerun`.
- **Assessment:** **ACCEPT — verify the guard is a hard path, not a soft check.** If the guard is an `if` with a log rather than a `raise`, future callers could bypass it. Confirm it raises or exits non-zero.

### Insight G-6: Line number discrepancy in export.py
- **Grok's claim:** References `export_run / tokens / sentences (export.py:505-467)` — line 505 to 467 is a **reverse range** (505 > 467). This is either a typo in Grok's output or a copy-paste inversion.
- **Assessment:** **INVESTIGATE.** Minor clerical issue in the review, but raises the question of whether Grok actually read these lines in the correct order or whether the function boundaries are non-standard. Flag for Cycle 2 verification.

---

## CONFLICTS (models disagree — your tiebreaker)

**Not applicable.** Only 1 model completed review. No conflicting assessments exist. This section will be populated in Cycle 2.

---

## VALIDATED STRENGTHS (all active models agree this is already excellent)

> **Caveat:** "All models" = Grok only. These are Grok-validated strengths, not ensemble-validated. Do not treat as immutable until confirmed by ≥2 models.

The following areas received explicit PASS from Grok with no defects identified. **Do NOT change these in the second pass unless Cycle 2 reveals a conflict:**

1. **Hard failure semantics across all new functions** — no silent exceptions, no partial returns, no PASS-on-missing-data paths. (`lineup.py`, `llm.py`, `providers.py`, `export.py`, `replay.py`)
2. **L-x vendor isolation** — only `providers.py` names vendors; local GPU0 only under lease; judge chain never includes writer vendor. (`providers.py:1439–1444, 1521–1546, 1670–1693`)
3. **L-h / L-k canon compliance** — `export.py` uses `read_text` + `canon`; canon imported flat. (`export.py:394, 456, 484`)
4. **Sentence law delegation** — `sentence_law.is_terminal` is the sole authority for sentence boundaries; no recomputation after selection. (`export.py:375, lineup.py:841–894`)
5. **v2f reference path** — untouched and not at risk from this diff.
6. **Key hygiene** — no key material in logs or exceptions. (`providers.py:1615–1664`)

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Evidence | Confidence |
|---|---|---|---|
| L-j (judge verdict structure) | ✅ COMPLIANT | lineup.py:740–746, 806–827 | ⚠️ Single model |
| L-l (lineup integrity) | ✅ COMPLIANT | lineup.py:740–746; ab.py:258–262 | ⚠️ Single model |
| L-m (model assignment) | ✅ COMPLIANT | providers.py:1680–1693 | ⚠️ Single model |
| L-x (vendor isolation) | ✅ COMPLIANT | providers.py:1439–1444, 1521–1546, 1670–1693 | ⚠️ Single model |
| L-h (hash/canon) | ✅ COMPLIANT | export.py:394, 456, 484 | ⚠️ Single model |
| L-k (canon import) | ✅ COMPLIANT | export.py:394, 456, 484 | ⚠️ Single model |
| Sentence Law | ✅ COMPLIANT | export.py:375; lineup.py:841–894 | ⚠️ Single model |
| SELECTION LOCK | ✅ COMPLIANT | export.py:375; lineup.py:841–894 | ⚠️ Single model |
| SNAP LIMIT | ✅ COMPLIANT | by construction per Grok | ⚠️ Single model |
| Spend Guard | ✅ COMPLIANT | llm.py:1064–1095 | ⚠️ Single model |

**Final determination:** No law violations detected by the 1 active reviewer. Full ensemble confirmation required before treating compliance as audited. Re-run Cycle 1 with all 3 models.

---

## SECURITY CONSENSUS

Only Grok reviewed. Single-model security findings:

| Issue | Severity | File | Status |
|---|---|---|---|
| Key material in logs/exceptions | HIGH | providers.py:1615–1664 | ✅ Not present (Grok confirmed) |
| SpendStop enforcement before remote call | HIGH | llm.py:1064–1095 | ✅ Enforced |
| Replay write-guard (no main-tree writes) | HIGH | replay.py:1824–1893 | ✅ Enforced |
| Lock orphan on process death (reserve/settle) | MEDIUM | llm.py:1064–1095 | ⚠️ NOT EVALUATED by Grok |
| Negative test for key-in-log | LOW | Test suite | ⚠️ MISSING |

**Priority order:**
1. Lock orphan risk (uninvestigated — could cause spend accounting corruption)
2. Negative test for key hygiene (makes the confirmed strength durable)
3. All else confirmed clean by Grok

---

## WORLD-CLASS GAP CONSENSUS

> Per instructions: only include items 2+ models mentioned. With only 1 model active, **no item meets the ≥2 model threshold.** This section is structurally empty.

The single-model gap identified by Grok (missing test file verification) is noted under U-1 and the action plan below, but **cannot be elevated to "world-class gap consensus" with only 1 reviewer.**

> To populate this section meaningfully: re-run with Gemini + GPT-4o in Cycle 2.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Confirm test files exist for all new functions' failure paths — specifically must-fail fixtures for `parse_oracle`/`parse_judge` missing-field, `Ledger.reserve` cap-exceeded, `call_backend` ContextTooLong, `replay` write-guard, `export_run` SHA mismatch | Test suite (location TBD) | Grok (unique) | Grok explicitly could not verify tests; a diff without tests is unauditable; failure paths are the entire correctness guarantee |
| **P0 CRITICAL** | Re-run Cycle 1 with working Gemini key and funded GPT-4o account before treating any finding as ensemble-validated | `.env` / billing | Structural (audit process) | 2 of 3 models did not run; this report has fundamentally reduced confidence; ship-blocking |
| **P1 HIGH** | Investigate lock-orphan path in `Ledger.reserve`/`settle`: confirm behavior if holding process dies between reserve and settle; add timeout or dead-lock detection if absent | llm.py:1064–1095 | Grok (gap noted implicitly) | Exclusive lock + PID check is correct but does not automatically handle process death; leaked reservations could allow over-spend |
| **P1 HIGH** | Confirm `replay` write-guard raises or exits non-zero (not a soft log-and-continue) | replay.py:1824–1893 | Grok (unique) | A soft guard can be bypassed by future callers; hard failure is required by law |
| **P1 HIGH** | Clarify reverse line range in Grok's report: `export.py:505-467` — confirm actual function boundaries and that Grok reviewed them in correct order | export.py:467–505 | Grok (self-inconsistency) | Line inversion suggests possible review artifact; re-verify SHA re-verification logic is at correct lines |
| **P2 MEDIUM** | Add negative regression test: assert no log output matches key-pattern when `call_backend` raises or logs a vendor error | providers.py:1615–1664 + test suite | Grok (unique) | Confirmed clean today; durable only with a test that survives future log-dict changes |
| **P2 MEDIUM** | Add explicit test: mutate transcript SHA and assert `export_run` fails hard | export.py:375–505 | Grok (unique) | SELECTION LOCK invariant confirmed by code review; must be protected against regression |

---

## CYCLE 1 VERDICT

**⚠️ CONDITIONAL — NOT READY FOR STANDARD SECOND PASS**

The code as reviewed by Grok-3 shows no defects and appears law-compliant. However:

- **2 of 3 required reviewers did not run.** This is not a minor gap — it means the ensemble's primary purpose (catching what any single reviewer misses) was entirely defeated.
- The P0 action above (re-run with all models) must be completed before the codebase can be considered audited.
- If operational constraints require proceeding anyway (e.g., deadline), the second pass may proceed with the understanding that it is acting on **single-reviewer intelligence only**, and a Cycle 2 full-ensemble audit should be scheduled immediately after.

**Recommendation:** Fix API access → Re-run Cycle 1 as Cycle 1b with all 3 models → produce a new consensus report → then fire the second pass prompt.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

> ⚠️ **Fire this prompt only after resolving the P0 API access issues and re-running Cycle 1 with all 3 models, OR with explicit acknowledgment that you are proceeding on single-reviewer findings.**

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 1 of 3 independent AI models in Cycle 1
(Gemini: no key; GPT-4o: no credits; Grok: completed).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Confirm or create must-fail test fixtures for all new
            | functions' failure paths: parse_oracle/parse_judge
            | (missing field, mistyped field, inconsistent verdict),
            | Ledger.reserve cap-exceeded (SpendStop before remote call),
            | call_backend ContextTooLong rejection, replay write-guard
            | (attempt write under main tree → must raise/exit non-zero),
            | export_run SHA mismatch (mutate transcript → must fail hard).
            | File: test suite (locate existing test dir; add fixtures there)
            | Why: Grok could not verify tests; unverified failure paths are
            |      not audited failure paths.

P1 HIGH     | Investigate Ledger.reserve/settle lock-orphan path.
            | If the process holding the exclusive lock dies between reserve
            | and settle, confirm the reservation is not leaked (causing
            | over-spend). Add timeout or dead-lock detection if absent.
            | File: llm.py:1064-1095

P1 HIGH     | Confirm replay write-guard at replay.py:1824-1893 raises an
            | exception or exits non-zero — NOT a log-and-continue. If it
            | is currently a soft check, harden it to a hard raise.
            | File: replay.py:1824-1893

P1 HIGH     | Verify export.py function boundaries for export_run/tokens/
            | sentences. Grok reported line range 505-467 (reverse order —
            | likely a typo). Confirm correct line range and that SHA
            | re-verification logic is present and correct at those lines.
            | File: export.py (lines ~467-505)

P2 MEDIUM   | Add negative regression test: when call_backend logs or raises
            | on a vendor error, assert no log record contains key material.
            | File: providers.py:1615-1664 + test suite

P2 MEDIUM   | Add regression test: mutate transcript SHA → assert export_run
            | fails hard (does not silently continue or return partial data).
            | File: export.py:375-505 + test suite

VALIDATED (do NOT touch — Grok confirmed excellent, pending full ensemble):
- Hard failure semantics: parse_oracle, parse_judge, Ledger, call_backend,
  export_run, replay — no silent exceptions, no partial returns.
- L-x vendor isolation: providers.py:1439-1444, 1521-1546, 1670-1693.
- L-h/L-k canon compliance: export.py:394, 456, 484.
- Sentence law delegation to sentence_law.is_terminal exclusively:
  export.py:375, lineup.py:841-894.
- v2f reference path: untouched.
- Key hygiene: no key material in logs/exceptions (providers.py:1615-1664).

After implementing:
  regression_test.sh must show zero FAILs.
  git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
  git push origin combo-letterbox-quoteonly-v2

NOTE FOR REVIEWER: This second pass is based on single-model (Grok-3)
audit findings. Schedule a full 3-model Cycle 2 audit after this pass
to validate the improvements with ensemble intelligence.
```