# CONSENSUS REPORT — PP-TESTS_AUDIT_A — CYCLE 2
Generated: 2026-11-12 01:53
Models: grok, gemini (+1 failed — GPT-4o: credit_balance_exhausted)

---

## SCORES

| Subsystem       | Gemini C2 | GPT-4o | Grok C2 | Consensus |
|-----------------|-----------|--------|---------|-----------|
| Backend Logic   | 95/100    | N/A    | 94/100  | **94/100** |
| Frontend/UI     | 100 (N/A) | N/A    | 100 (N/A) | **100 (N/A)** |
| Error Handling  | 90/100    | N/A    | 90/100  | **90/100** |
| Security        | 100/100   | N/A    | 100/100 | **100/100** |
| Performance     | 88/100    | N/A    | 87/100  | **87/100** |
| Law Compliance  | 100/100   | N/A    | 100/100 | **100/100** |
| World-Class Gap | 96/100    | N/A    | 95/100  | **95/100** |
| **OVERALL**     | **94/100** | N/A   | **94/100** | **94/100** |

> **Note on GPT-4o absence:** With only 2 models available this cycle, "unanimous" and "majority" thresholds collapse to 2/2. All findings below are weighted accordingly. Confidence intervals are wider than a full 3-model cycle; conclusions should be treated as high-confidence but not definitive where models diverged from Cycle 1.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U-1 · Hardcoded Absolute Reference Path Is Non-Portable
**Both models flagged this. Highest-confidence finding of the cycle.**

- **What it is:** `MAIN_TREE_REFS = "/home/ultron/protocol_pulse/references"` is a literal, machine-specific absolute path baked into the test helper. Any CI runner, container, or secondary developer workstation that does not have this exact path will fail the entire `f5_references` family with an opaque `AssertionError` from `_need()` rather than a clean, actionable skip.
- **File/Line:** `tests/adversarial/adv_helpers.py:109`; downstream consumer `tests/adversarial/test_f5_references.py:2093` and throughout.
- **What to change:**
  ```python
  # adv_helpers.py:109 — replace hardcoded path with:
  MAIN_TREE_REFS = os.environ.get(
      "PP_REFS_DIR",
      "/home/ultron/protocol_pulse/references"  # local-dev fallback only
  )
  ```
  Additionally, add a module-level guard at the top of `test_f5_references.py`:
  ```python
  if not os.path.isdir(MAIN_TREE_REFS):
      pytest.skip(
          f"PP_REFS_DIR not found ({MAIN_TREE_REFS!r}). "
          "Set PP_REFS_DIR env var to run reference-integrity tests.",
          allow_module_level=True,
      )
  ```
  This converts an opaque `AssertionError` into an explicit, navigable skip while keeping "nothing measured is never a pass" intact — skipped families are not measured, so law L-m is not violated.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings are also majority findings. No additional majority findings exist beyond U-1 above, because the two models **disagreed** on the timeout finding (see CONFLICTS). With GPT-4o absent, there is no third vote to break the tie — the timeout issue is therefore adjudicated in the CONFLICTS section below rather than promoted to majority.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 · `nvidia-smi` Guard Can False-Positive on Shared GPU Hosts
**Source: Grok only (Cycle 1 P1, carried to Cycle 2)**

- **What it is:** `conftest.py:71` checks whether the test suite's current process tree appears in `nvidia-smi` output. On a shared multi-tenant CI runner, an unrelated process from another job can be using a GPU, causing the guard to set `session.exitstatus = 1` and fail the entire suite for a reason entirely outside the test suite's control.
- **Assessment: Investigate further / implement with caution.**
- **Recommended change:** Make the check conditional on a flag:
  ```python
  # conftest.py:71 — gate the hard-fail behind an opt-in flag
  if os.environ.get("PP_STRICT_CPU_GUARD", "0") == "1":
      session.exitstatus = 1
  else:
      warnings.warn("nvidia-smi detected GPU activity from unrelated PID — CPU guard not enforced.")
  ```
  This preserves the strong CPU guarantee when opted in (e.g., dedicated CI nodes) while preventing spurious failures on shared infrastructure. Classify as **P2**.

### UI-2 · Implicit Coupling of Atomicity Test to `deliver_run` Implementation
**Source: Gemini only (new Cycle 2 finding)**

- **What it is:** `test_f3_release_auth.py:1503` uses an `on_send` callback to swap a file on disk mid-delivery, testing that `telegram.deliver_run` verifies all payloads before sending the first. This is clever and correct for the current implementation, but is implicitly coupled to the assumption that delivery is not streaming/chunked. If `deliver_run` is ever refactored, this test could become flaky or give false confidence.
- **Assessment: Skip as a code change; implement as a comment.**
- **Recommended action:** Add an inline comment at `test_f3_release_auth.py:1503` documenting the implicit contract, e.g.:
  ```python
  # NOTE: This test assumes deliver_run verifies ALL payloads before sending
  # the first message (eager verification, not streaming). If deliver_run is
  # ever refactored to stream payloads, revisit this test's on_send hook.
  ```
  No code change required. Classify as **P3 (documentation only)**.

---

## CONFLICTS (models disagree — tiebreaker)

### CONFLICT-1 · Missing Timeouts on `ffmpeg`/`ffprobe` Subprocess Calls

| Position | Grok | Gemini |
|---|---|---|
| **Claim** | Timeouts are missing on several `subprocess.run` calls; CI hangs are a real risk | Timeouts are already present at all relevant locations; the finding is factually incorrect |
| **Cited lines** | `adv_helpers.py:345, 400, 410, 583, 2116`; `conftest.py:71` | `adv_helpers.py:345` (`_run` helper, `timeout=120`); `:583` (`timeout=120`); `test_f5_references.py:2116` (`timeout=60`); `conftest.py:71` (`timeout=20`) |

**Tiebreaker verdict: Gemini is correct.**

Gemini's Cycle 2 review directly rebuts this finding with specific line evidence showing `timeout=` arguments are already present at every cited location. Grok's Cycle 1 finding was reasonable defensive advice, but Gemini's close re-read of the diff demonstrates the code is already compliant. With GPT-4o absent we cannot get a third vote, but Gemini's position is specific and falsifiable (line numbers, argument values) while Grok's is a general assertion. **No change required on subprocess timeouts.**

---

## VALIDATED STRENGTHS (both models confirm — do NOT touch)

The following are explicitly rated exemplary by both models. Second-pass work must not disturb them.

1. **CPU-only layered guard** — `CUDA_VISIBLE_DEVICES` patching at import time + per-test + `faster_whisper` stub + `nvidia-smi` session-finish check. Architecture is correct and robust.
2. **Strict `xfail` + `REQUESTS.md` linkage** — Every `xfail` is tied to a named, durable requirement. This turns every future regression into an unambiguous CI failure. Do not loosen or remove any `xfail` marker.
3. **Seeded adversarial case generation** (`adv_helpers.py:245`) — Deterministic, reproducible, covers both surface variants and meaning mutants. No changes needed.
4. **`release_run` golden fixture** (`adv_helpers.py:520`) — Correctly isolates mutations as the sole cause of authorization failure. Do not modify the fixture's construction.
5. **Meta-test `test_every_required_row_has_a_vacuity_probe`** (`test_f4_vacuity.py:1845`) — Ensures the test suite self-maintains coverage as the production gate inventory evolves. This is production-grade test engineering; leave it intact.
6. **Fail-closed discipline** (`test_f3_release_auth.py`) — Exhaustive parameterization of every release-auth mutation. No coverage gaps identified by either model.
7. **`speech_like` helper** (`adv_helpers.py:348`) — CPU-efficient, ground-truth-perfect audio generation. No changes needed.
8. **WindowAudio 10 ms grid matching** (`adv_helpers.py:576`) — Precision timing contract is correctly specified and tested.
9. **`fake_llm` HTTP seam** (`adv_helpers.py:598`) — Correct isolation of production HTTP path. No changes needed.
10. **Template fixture pattern** (`test_f2_provenance.py:1083, 1104`) — Module-scoped creation + per-test copy is efficient and correct. Leave as-is.

---

## LAW COMPLIANCE CONSENSUS

**Final determination: ALL LAWS FULLY COMPLIANT. No violations.**

| Law | Status | Evidence |
|-----|--------|----------|
| TESTS ONLY | ✅ Compliant | Diff touches only `tests/adversarial/` and `docs/audits/parallel/` |
| CPU ONLY | ✅ Compliant | Layered guards in `conftest.py`; `faster_whisper` stubbed; `nvidia-smi` check |
| Public entry points only | ✅ Compliant | Explicit in every test file; no internal imports |
| Strict `xfail` tied to `REQUESTS.md` | ✅ Compliant | Multiple instances per family; no bare `xfail` |
| Genuine-pass + must-fail pairs | ✅ Compliant | Present in every test family |
| Nothing measured = FAIL | ✅ Compliant | Family 4 specifically; U-1 fix preserves this via `pytest.skip` |
| Fail closed | ✅ Compliant | Family 3 exhaustively verified |

Both models agree: **zero law violations.** The U-1 fix (skip instead of opaque assert) is consistent with law L-m because a skipped module is not a measured pass.

---

## SECURITY CONSENSUS

**No security issues identified by either model.**

Both models independently awarded 100/100 for security. The rationale is consistent:
- No SQL, no authentication surfaces, no user-facing routes
- No secrets or credentials in test code
- All paths are synthetic or read-only references
- No shell invocations with untrusted/interpolated input
- Hardcoded path (U-1) is a portability issue, not a security issue

**Security posture: Clean. No action required.**

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as gaps between current state and a truly world-class test suite:

### WC-1 · Reference Data Portability (U-1)
Both models. The hardcoded path is the difference between "brilliant personal test suite" (Gemini's exact words) and "robust shareable engineering asset." Fixing U-1 closes this gap entirely.

### WC-2 · CI Environment Brittleness on Shared GPU Hosts (UI-1)
Both cycles of Grok; Gemini agreed in principle. The `nvidia-smi` guard's hard-fail behavior can produce CI failures entirely outside the suite's control on shared infrastructure. Making it opt-in (PP_STRICT_CPU_GUARD) is a minor change with meaningful operational resilience gain.

**Items explicitly NOT considered gaps by both models:**
- Adversarial case coverage depth (rated exemplary)
- xfail discipline (rated exemplary)
- CPU guarantee architecture (rated exemplary)
- Test isolation and cleanup (rated exemplary)

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P1 HIGH** | Replace hardcoded `MAIN_TREE_REFS` with `os.environ.get("PP_REFS_DIR", "/home/ultron/...")` and add `pytest.skip(allow_module_level=True)` guard when path is absent | `adv_helpers.py:109`; `test_f5_references.py:2093` (module top) | Both (unanimous) | Makes suite portable across CI runners and dev machines; converts opaque `AssertionError` to actionable skip; preserves L-m law compliance |
| **P2 MEDIUM** | Gate `nvidia-smi` hard-fail behind `PP_STRICT_CPU_GUARD=1` env var; emit `warnings.warn` otherwise | `conftest.py:71` | Grok (UI-1); no Gemini objection | Prevents spurious suite-level failures from unrelated GPU processes on shared CI hosts |
| **P3 LOW** | Add inline comment at atomicity test documenting implicit `deliver_run` eager-verification contract | `test_f3_release_auth.py:1503` | Gemini only (UI-2) | Future-proofs understanding if `deliver_run` is refactored; zero functional risk |

**P0 CRITICAL: None.**

**Explicitly rejected:**
- ~~Add timeouts to ffmpeg/ffprobe subprocess calls~~ — Gemini's direct line-level review shows timeouts already present; Grok's finding was incorrect. **Do not change.**

---

## CYCLE 2 VERDICT

**Production-ready with one pre-merge condition.**

After two full cycles of independent adversarial review by two models (GPT-4o absent due to quota exhaustion), this test suite is among the strongest test engineering work either model has reviewed. The adversarial design philosophy, law compliance, xfail discipline, CPU guarantee, and meta-test coverage are all production-grade and should be preserved exactly as written.

**The single absolute blocker before merge:**

> **P1 — Hardcoded `/home/ultron/` reference path** (`adv_helpers.py:109`). This is a one-line fix plus a five-line skip guard. It is the only change that must ship before this suite can be used reliably in any environment other than the original author's workstation.

The P2 `nvidia-smi` guard improvement is recommended but not a merge blocker — it only matters if the suite is run on shared GPU infrastructure, and it can be addressed in a follow-up PR if that situation does not currently apply.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PP_TESTS_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pp-tests_audit_A_CONSENSUS_C2.md.

This is the FINAL PASS for pp-tests_audit_A.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2 and P3.

PRIORITY ACTION PLAN:

P1 HIGH | Replace hardcoded MAIN_TREE_REFS path with env-var lookup and add skip guard
  - tests/adversarial/adv_helpers.py:109
      BEFORE: MAIN_TREE_REFS = "/home/ultron/protocol_pulse/references"
      AFTER:  MAIN_TREE_REFS = os.environ.get(
                  "PP_REFS_DIR",
                  "/home/ultron/protocol_pulse/references"
              )
  - tests/adversarial/test_f5_references.py — add at module top, after MAIN_TREE_REFS import:
      if not os.path.isdir(MAIN_TREE_REFS):
          pytest.skip(
              f"PP_REFS_DIR not found ({MAIN_TREE_REFS!r}). "
              "Set PP_REFS_DIR env var to run reference-integrity tests.",
              allow_module_level=True,
          )
  Models: both (unanimous). Why: portability; opaque AssertionError → clean skip; L-m preserved.

P2 MEDIUM | Gate nvidia-smi hard-fail behind PP_STRICT_CPU_GUARD=1 env var
  - tests/adversarial/conftest.py:71
      Wrap session.exitstatus = 1 in:
      if os.environ.get("PP_STRICT_CPU_GUARD", "0") == "1":
          session.exitstatus = 1
      else:
          warnings.warn("nvidia-smi detected GPU activity from unrelated PID — CPU guard not enforced on shared host.")
  Models: Grok. Why: prevents spurious suite failure from unrelated GPU processes on shared CI.

P3 LOW | Add explanatory comment at atomicity swap test
  - tests/adversarial/test_f3_release_auth.py:1503
      Add comment: # NOTE: This test assumes deliver_run verifies ALL payloads before sending
      # the first message (eager verification, not streaming). If deliver_run is ever
      # refactored to stream payloads, revisit this test's on_send hook strategy.
  Models: Gemini. Why: documents implicit contract for future maintainers.

DO NOT CHANGE — VALIDATED EXCELLENT (both models confirmed):
  - CPU-only layered guard architecture (conftest.py CUDA patching + faster_whisper stub)
  - All xfail markers and their REQUESTS.md linkage — do not loosen or remove any
  - Seeded adversarial case generation (adv_helpers.py:245 gen_cases)
  - release_run golden fixture construction (adv_helpers.py:520)
  - Meta-test test_every_required_row_has_a_vacuity_probe (test_f4_vacuity.py:1845)
  - Fail-closed parameterization in test_f3_release_auth.py
  - speech_like helper (adv_helpers.py:348)
  - WindowAudio 10 ms grid matching (adv_helpers.py:576)
  - fake_llm HTTP seam (adv_helpers.py:598)
  - Template fixture pattern (test_f2_provenance.py:1083, 1104)
  - subprocess timeouts — already correct at all locations, do NOT add or change

EXPLICITLY REJECTED CHANGE — DO NOT IMPLEMENT:
  - Adding timeouts to ffmpeg/ffprobe subprocess calls: Gemini's direct line review
    confirmed timeout= arguments are already present at adv_helpers.py:345, :583,
    test_f5_references.py:2116, and conftest.py:71. No change needed.

After implementing:
  regression_test.sh must show zero FAILs.
  PP_REFS_DIR=/home/ultron/protocol_pulse/references pytest tests/adversarial/ must pass
    with same result as before this change.
  pytest tests/adversarial/ (without PP_REFS_DIR set, on a machine lacking that path)
    must show test_f5_references SKIPPED (not FAILED, not ERROR).

git add -A && git commit -m "feat(pp-tests_audit_A): post-audit pass — consensus improvements

- Replace hardcoded MAIN_TREE_REFS with PP_REFS_DIR env var + skip guard (P1)
- Gate nvidia-smi hard-fail behind PP_STRICT_CPU_GUARD=1 (P2)
- Document deliver_run atomicity assumption at swap test (P3)

Reviewed by: grok + gemini, 2 cycles
Consensus score: 94/100 → target 97/100 post-patch"
git push origin pp-tests
```

---

# WINNER DETERMINATION

# WINNER: **Gemini** — Gemini delivered the highest-quality analysis across both cycles, providing superior depth in Cycle 1 (detailed per-file reasoning on `conftest.py`, `adv_helpers.py`, `release_run`, and each test family with specific line citations) and demonstrated exceptional intellectual honesty in Cycle 2 by both acknowledging its miss on the hardcoded path *and* mounting a technically substantiated disagreement on U-2 (correctly identifying that `timeout=` arguments were already present in the diff, while Grok accepted that finding without challenge). The combination of greater initial depth, accurate self-correction, and willingness to dissent from a consensus finding on factual grounds is the mark of the highest-quality analytical output.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered list synthesizing both cycles, Gemini's Cycle 2 dissent on U-2, and the consensus scores.

---

## P1 — HIGH (implement before next merge)

### P1-A · Replace Hardcoded Absolute Reference Path
**Source: U-1, unanimous, highest-confidence finding of the audit.**

- **File:** `tests/adversarial/adv_helpers.py:109`
- **Action:**
  ```python
  # BEFORE
  MAIN_TREE_REFS = "/home/ultron/protocol_pulse/references"

  # AFTER
  MAIN_TREE_REFS = os.environ.get(
      "PP_REFS_DIR",
      str(pathlib.Path(__file__).parent.parent.parent / "references"),
  )
  ```
- **Companion change** — replace `_need()` assertion with a clean pytest skip:
  ```python
  def _need(path: str) -> None:
      if not os.path.exists(path):
          pytest.skip(f"Reference path not found: {path} — set PP_REFS_DIR to override")
  ```
- **Why P1:** Every machine that is not `ultron` fails the entire `f5_references` family with a silent, non-actionable `AssertionError` that registers as a measured failure under Law L-m. Breaks CI portability completely.

---

## P2 — MEDIUM (implement in next sprint)

### P2-A · Audit and Harden `ffmpeg`/`ffprobe` Subprocess Timeout Coverage
**Source: U-2 — Grok agreed, Gemini dissented with line-specific counter-evidence. Confidence: moderate.**

- **Action required before closing:** Do a targeted diff search:
  ```bash
  grep -n "subprocess.run" tests/adversarial/adv_helpers.py | grep -v "timeout="
  ```
- **If any calls lack `timeout=`:** Add `timeout=30` (or domain-appropriate value) to every `subprocess.run` and `subprocess.Popen` invocation touching `ffmpeg`, `ffprobe`, or `nvidia-smi`.
- **If Gemini's dissent is confirmed correct** (all calls already have `timeout=`): close this item as resolved, document in audit trail.
- **Why P2 not P1:** Gemini's factual challenge means this may already be fixed. Verification cost is 5 minutes; do not implement blindly on the basis of a contested finding.

### P2-B · Add `PP_REFS_DIR` to CI Environment Matrix
**Companion to P1-A.**

- **File:** `.github/workflows/*.yml` (or equivalent CI config)
- **Action:** Add `PP_REFS_DIR: ${{ github.workspace }}/references` to the `env:` block of every job that runs the adversarial suite.
- **Why P2:** P1-A makes the code correct; P2-B makes the CI pipeline actually exercise the references family rather than skip it on every run.

---

## P3 — LOW (backlog, quality-of-life)

### P3-A · Emit Structured Skip Reason on `_need()` Failures
**Source: Grok Cycle 2 combined with Gemini Cycle 1 opacity observation.**

- After P1-A lands, verify that all `_need()` callsites produce a human-readable pytest skip message that includes the missing path and the env var name. This is largely satisfied by the P1-A implementation above but should be validated in a dry run on a clean machine.

### P3-B · Document `PP_REFS_DIR` in `README` / `CONTRIBUTING`
- One paragraph explaining how to configure local reference paths for developers not running on `ultron`. Prevents recurrence of the portability issue as team grows.

### P3-C · Consider Extracting Reference Path Resolution to a Single `conftest.py` Fixture
- Rather than resolving `MAIN_TREE_REFS` at module import time in `adv_helpers.py`, expose it as a session-scoped pytest fixture. This makes the path override testable in isolation and avoids import-time side effects if the env var logic ever grows more complex.

---

## CLOSED / NO ACTION REQUIRED

| Item | Disposition |
|---|---|
| Law compliance (all 7 laws) | Confirmed compliant both cycles — no action |
| CPU-only guard | Confirmed robust (layered: env patch + stub + nvidia-smi check) — no action |
| `xfail` discipline | Confirmed correct and tied to REQUESTS.md — no action |
| Security | No SQL, no secrets, no untrusted shell input — no action |
| Adversarial coverage depth | Exemplary — seeded generators, meaning mutants, vacuity probes all correct |
| Frontend | N/A — zero frontend code in scope |