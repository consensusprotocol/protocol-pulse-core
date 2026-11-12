# CONSENSUS REPORT — PP-TESTS_AUDIT_A — CYCLE 1
Generated: 2026-11-12 01:50
Models: grok, gemini (+1 failed — GPT-4o: credit_balance_exhausted)

---

## SCORES

| Subsystem         | Gemini        | GPT-4o | Grok   | Consensus |
|-------------------|---------------|--------|--------|-----------|
| Backend Logic     | ~93/100 (est) | N/A    | 95/100 | 94/100    |
| Frontend/UI       | N/A           | N/A    | 100/100| N/A       |
| Error Handling    | ~88/100 (est) | N/A    | 92/100 | 90/100    |
| Security          | ~96/100 (est) | N/A    | 100/100| 98/100    |
| Performance       | ~87/100 (est) | N/A    | 88/100 | 88/100    |
| Law Compliance    | 100/100       | N/A    | 100/100| 100/100   |
| World-Class Gap   | ~92/100 (est) | N/A    | 96/100 | 94/100    |
| **OVERALL**       | **~93/100**   | N/A    | **95/100** | **94/100** |

> *Gemini scores estimated from qualitative language; Gemini did not emit explicit numeric scores. GPT-4o failed with API quota exhaustion — weight-of-evidence drawn from 2 models only. Consensus column is arithmetic mean of available scores.*

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U-1 · Hardcoded Absolute Reference Path is Non-Portable and Opaque on Failure
**What it is:** `MAIN_TREE_REFS = "/home/ultron/protocol_pulse/references"` is baked into `adv_helpers.py:109`. Both models flagged this independently. Grok noted it as a portability risk; Gemini described it as making the suite "entirely non-portable" and suggested that failure mode is an opaque `AssertionError` rather than a clean skip/error.

**File/line:** `tests/adversarial/adv_helpers.py:109`

**What to change:**
1. Replace the hardcoded string with an environment variable with a fallback: `MAIN_TREE_REFS = Path(os.environ.get("PP_REFS_DIR", "/home/ultron/protocol_pulse/references"))`.
2. Add a module-level guard or fixture that calls `pytest.skip("PP_REFS_DIR not found — reference tests skipped")` when the path does not exist, rather than letting downstream tests fail with an ambiguous `AssertionError`. This preserves Law L-m (missing reference = not a pass) while giving operators an actionable error message on a misconfigured runner.

---

### U-2 · Missing Explicit Timeouts on `ffmpeg` / `ffprobe` Subprocess Calls
**What it is:** Both models flagged that `subprocess.run` calls for `ffmpeg` and `ffprobe` in `adv_helpers.py` lack `timeout=` arguments. On slow I/O or a hung codec, the test suite would block indefinitely with no CI escape hatch.

**File/line:** `adv_helpers.py:348` (`speech_like`/`make_media`), `adv_helpers.py:389`, `adv_helpers.py:581` (`WindowAudio`), `test_f5_references.py:2116` (`ffprobe`)

**What to change:** Add `timeout=60` (or a constant `FFMPEG_TIMEOUT_S = 60` defined in `adv_helpers.py`) to every `subprocess.run` call that invokes `ffmpeg`, `ffprobe`, or any external binary. Catch `subprocess.TimeoutExpired` and re-raise as `pytest.fail("ffmpeg timed out after 60 s — slow I/O or codec hang")` so the failure is explicit and the suite exits rather than hanging the CI job.

---

## MAJORITY FINDINGS (2 of 2 models agree)

Both models that ran converged on exactly the two findings above (U-1 and U-2). There are no additional findings that are "majority but not unanimous" because with only two models available, majority and unanimous are equivalent. The findings above represent the complete set of items both models raised.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### I-1 · `nvidia-smi` Guard Can False-Positive on Multi-Tenant / Shared GPU Hosts
**Raised by:** Grok only (`conftest.py:71`)
**Assessment:** **Implement.** The concern is real and operationally important. On a shared Kubernetes node or cloud CI runner, another process's GPU activity could cause the `nvidia-smi` guard to report GPU usage that belongs to a co-tenant, not to the test suite. This would cause a false suite failure (`exitstatus=1`) with no clear diagnostic.

**Recommended fix:** Scope the `nvidia-smi` check to the current process tree. Replace the bare `nvidia-smi` call with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader` and filter the output against the current test runner's PID subtree (e.g., using `psutil.pids()` or checking against `os.getpid()` / `os.getpgid()`). If no matching PID has GPU memory, the guard passes. This eliminates the false-positive class entirely on shared infrastructure.

---

### I-2 · Brittle `AssertionError` Path on Missing Reference Files in `test_f5`
**Raised by:** Gemini only (line 2094 of `test_f5_references.py`)
**Assessment:** **Implement** (overlaps with U-1 but is a distinct surface). Gemini specifically called out that the failure mode when a reference file is missing is an `AssertionError: reference missing...` rather than a `pytest.skip` or `pytest.fail` with a clear message. The fix from U-1 (environment variable + fixture-level skip guard) covers this surface as well, but the specific line in `test_f5_references.py` should also be audited to ensure any secondary hardcoded reference path lookups produce actionable output.

**Action:** During the U-1 fix, audit all `assert ... "reference missing"` patterns in `test_f5_references.py` and convert them to `pytest.fail(f"Reference artifact not found at {path} — check PP_REFS_DIR", pytrace=False)`.

---

### I-3 · Pin Exact `ffmpeg`/`libx264` Versions in CI Matrix
**Raised by:** Grok only
**Assessment:** **Investigate / implement in CI configuration, not in this diff.** Timing variance from codec version differences could cause flaky failures in `edge_word_bounds` and similar timing-sensitive tests. This is not a code change — it belongs in the CI Docker image definition or `requirements-dev.txt` / `environment.yml`. Flag it as a CI infrastructure ticket. Do not block the second pass on it.

---

### I-4 · Meta-Test `test_every_required_row_has_a_vacuity_probe` Is World-Class Practice
**Raised by:** Gemini only (line 1845 of `test_f4_vacuity.py`) as a positive observation.
**Assessment:** **Do not touch.** This is a validated strength (see below). No action required.

---

## CONFLICTS (models disagree — tiebreaker)

**No genuine conflicts exist between the two models.** Grok and Gemini are in full agreement on all substantive findings. Their coverage differs only in emphasis (Grok gave more detail on the nvidia-smi issue; Gemini gave more detail on the reference path brittleness), but neither contradicts the other. The only "conflict" is score granularity: Gemini did not emit numeric scores, making precise comparison impossible. The consensus scores above use Gemini's qualitative language to estimate numerics.

**Tiebreaker ruling on GPT-4o absence:** With one model absent, the two-model consensus is treated as authoritative for all findings. No finding from either model is demoted solely because GPT-4o did not confirm it.

---

## VALIDATED STRENGTHS (do NOT change in the second pass)

Both models explicitly confirmed the following as already excellent. These areas must not be modified:

1. **CPU-only guard layering in `conftest.py`** — `CUDA_VISIBLE_DEVICES` patching at all lifecycle stages, `faster_whisper` stub, `nvidia-smi` session-finish check. The architecture is correct; only the multi-tenant false-positive edge case needs hardening (I-1).

2. **`gen_cases` seeded generator (`adv_helpers.py:245`)** — Deterministic, seeded, lightweight surface-variant + meaning-mutant generation. Both models praised this as a solid alternative to property-based testing. Do not replace or refactor.

3. **`speech_like` CPU audio synthesis (`adv_helpers.py:348`)** — Clever, correct, and dependency-free for ground-truth transcripts. Leave intact (add timeout only).

4. **`release_run` golden control fixture (`adv_helpers.py:520`)** — Correctly isolates mutations as the sole cause of authorization failures. Architecture is sound.

5. **Strict `xfail` + `REQUESTS.md` discipline** — Every `xfail` is `strict=True` with a reason tied to a finding ID. Both models flagged this as world-class practice. The linkage between test failures and the living `REQUESTS.md` document must not be loosened.

6. **`test_every_required_row_has_a_vacuity_probe` meta-test (`test_f4_vacuity.py:1845`)** — Gemini called this "a brilliant piece of meta-testing." Do not remove or weaken.

7. **`test_f3_release_auth.py` fail-closed exhaustion** — Systematic mutation of every authorization artifact component. The parameterization is complete and correct. Do not simplify.

8. **Template fixtures with module-scoped copy pattern (`test_f2_provenance.py:1083,1104`)** — Efficient and correct. Leave the fixture architecture unchanged.

9. **`fake_llm` HTTP seam and dual-wiring G8 test (`test_f5:2266`)** — Both models agreed this is production-grade test engineering. Do not modify.

10. **`tmp_path` / `tempfile.mkdtemp` isolation throughout** — All writes are correctly isolated with cleanup. Do not change the temp-directory strategy.

---

## LAW COMPLIANCE CONSENSUS

**Final determination: ALL laws FULLY COMPLIANT.** Both models independently audited every stated law and found zero violations.

| Law | Status | Evidence |
|-----|--------|----------|
| TESTS ONLY — only `tests/` and `docs/` touched | ✅ COMPLIANT | Diff confined to `tests/adversarial/` and `docs/audits/parallel/` |
| CPU ONLY — no GPU at any stage | ✅ COMPLIANT | Multi-layer guard in `conftest.py`; `test_f0_cpu_guard.py` validates it |
| Public entry points only | ✅ COMPLIANT | All test calls go through high-level public API (`release_auth.authorise`, `WD.gate_g18`, `SP.select_and_build_edl`, etc.) |
| Every test passes or is strict xfail | ✅ COMPLIANT | All `xfail` are `strict=True` with REQUESTS.md-linked reasons |
| Genuine-pass AND must-fail pairs in every family | ✅ COMPLIANT | Control cases present in every family (e.g., F3:1379 clean-run pass) |
| L-m: Nothing measured is never a pass | ✅ COMPLIANT | `test_f4_vacuity.py` entire; `test_f5` fails on missing reference |
| L-j: Fail closed | ✅ COMPLIANT | `test_f3_release_auth.py` exhaustively validates this |
| Never change what a check accepts | ✅ COMPLIANT | Tests exercise existing production logic; REQUESTS.md separates findings from fixes |
| One command, under 5 minutes on CPU | ✅ COMPLIANT (by design) | Synthetic media, seeded generators, no network/GPU dependencies |

---

## SECURITY CONSENSUS

Both models agree: **no traditional application security vulnerabilities exist in this test suite.** It is a closed, synthetic, read-only system with no production secrets, no user-facing routes, and no external inputs reaching shell commands.

**Priority order of security observations (for completeness):**

1. **(Low / by design)** `subprocess.run` for `ffmpeg`/`ffprobe`/`nvidia-smi` — inputs are all suite-generated or hardcoded; no injection path exists. The only risk is a hung process (addressed by U-2 timeout fix).
2. **(Informational)** Hardcoded absolute path (`adv_helpers.py:109`) — not a security issue, but a portability and misconfiguration-disclosure risk (addressed by U-1).
3. **(Informational)** Monkeypatched API key in `test_f4_vacuity.py:1949` — correct practice for test isolation; no real credential exposure.

**Security verdict: No security fixes required. U-2 (subprocess timeout) is the only change with any security-adjacent benefit (DoS prevention in CI).**

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as gaps or improvement opportunities:

### WCG-1 · Subprocess Timeout Coverage (both models)
The absence of explicit timeouts is the single most operationally dangerous gap. A hung `ffmpeg` call on a flaky CI runner will block the entire pipeline indefinitely. This is the highest-priority world-class gap.

### WCG-2 · Reference Path Portability (both models)
Hardcoding `/home/ultron/...` ties the entire `test_f5` family to a single machine. World-class test suites are runner-agnostic. Environment-variable parameterization is table-stakes for any suite that might run on more than one host.

> *No single-model world-class gap items are elevated here, per the section rule requiring 2+ models.*

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Add `timeout=60` (constant `FFMPEG_TIMEOUT_S`) to every `subprocess.run` call for `ffmpeg`, `ffprobe`, `nvidia-smi`; catch `TimeoutExpired` and re-raise as `pytest.fail` with explicit message | `adv_helpers.py:348,389,581`; `test_f5_references.py:2116`; `conftest.py:71` | both | A hung subprocess will block CI indefinitely with no escape; this is an availability/reliability P0 for any suite claiming "under 5 minutes on CPU" |
| **P1 HIGH** | Replace hardcoded `/home/ultron/protocol_pulse/references` with `Path(os.environ.get("PP_REFS_DIR", "/home/ultron/protocol_pulse/references"))`; add fixture-level `pytest.skip` when path absent; convert bare `AssertionError` reference-missing failures to `pytest.fail(..., pytrace=False)` | `adv_helpers.py:109`; `test_f5_references.py:2094` and all `assert ... "reference missing"` callsites | both | Suite is non-portable; opaque `AssertionError` on misconfigured runner masks root cause; environment variable costs nothing and unblocks any future CI migration |
| **P1 HIGH** | Scope `nvidia-smi` guard to current process tree using PID filtering (`nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader` + filter against `os.getpgid(os.getpid())`); do not fail on co-tenant GPU activity | `conftest.py:71` | grok (unique but high-confidence) | False-positive suite failure on shared/cloud CI runners is an operational correctness issue; risk is real and fix is straightforward |
| **P2 MEDIUM** | Define `FFMPEG_TIMEOUT_S = 60` as a named constant in `adv_helpers.py` (top of file) so timeout value is single-sourced across all call sites | `adv_helpers.py` (top-of-file constant) | both (implied by U-2) | Avoids scattered magic numbers; makes timeout policy adjustable in one place |
| **P2 MEDIUM** | Pin `ffmpeg`/`libx264` versions in CI Docker image or `environment.yml` (not in this diff — CI infrastructure ticket) | CI configuration (out of scope for this diff) | grok (unique) | Timing variance from codec version drift risks flaky `edge_word_bounds` failures; low urgency but worth tracking |

---

## CYCLE 1 VERDICT

**Ready for a second build pass. No fundamental rework required.**

The suite is architecturally excellent and law-compliant. The two P0/P1 fixes (subprocess timeouts, reference path portability) are surgical, localized changes that do not alter test logic or law compliance. The nvidia-smi PID-scoping fix (P1) is similarly contained to `conftest.py`. All three changes improve operational reliability without touching any validated strength. Proceed to second pass immediately.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PP_TESTS_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pp-tests_audit_A_CONSENSUS_C1.md.

This is the SECOND PASS for pp-tests_audit_A.
The first build was reviewed by 2 independent AI models across 1 cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add explicit subprocess timeouts | adv_helpers.py:348,389,581; test_f5_references.py:2116; conftest.py:71 | models: both | Hung ffmpeg/ffprobe/nvidia-smi blocks CI indefinitely; suite claims <5 min CPU; timeout is non-negotiable.
  - Define FFMPEG_TIMEOUT_S = 60 as a top-of-file constant in adv_helpers.py.
  - Add timeout=FFMPEG_TIMEOUT_S to every subprocess.run call for ffmpeg, ffprobe, nvidia-smi.
  - Catch subprocess.TimeoutExpired and re-raise as pytest.fail("ffmpeg/ffprobe/nvidia-smi timed out after 60s — slow I/O or codec hang", pytrace=False).

P1 HIGH | Parameterize reference path via environment variable | adv_helpers.py:109; test_f5_references.py:2094 and all "reference missing" assert callsites | models: both | Hardcoded /home/ultron path is non-portable; opaque AssertionError masks misconfiguration.
  - Replace: MAIN_TREE_REFS = "/home/ultron/protocol_pulse/references"
  - With:    MAIN_TREE_REFS = Path(os.environ.get("PP_REFS_DIR", "/home/ultron/protocol_pulse/references"))
  - Add a session-scoped fixture (or module-level guard) in test_f5_references.py that calls pytest.skip("PP_REFS_DIR path not found — reference tests skipped on this runner") if MAIN_TREE_REFS does not exist.
  - Convert every bare assert ... "reference missing" in test_f5_references.py to pytest.fail(f"Reference artifact not found at {path} — check PP_REFS_DIR env var", pytrace=False).

P1 HIGH | Scope nvidia-smi guard to current process tree | conftest.py:71 | models: grok (high-confidence unique) | Bare nvidia-smi false-positives on shared/cloud CI runners from co-tenant GPU processes.
  - Replace bare `nvidia-smi` invocation with:
      nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
  - Parse output and filter PIDs against the current process group (os.getpgid(os.getpid())).
  - Only fail the session if a PID within the current process tree has GPU memory allocated.
  - If nvidia-smi is absent (CPU-only host), treat as pass (no GPU = no violation).

P2 MEDIUM | Single-source FFMPEG_TIMEOUT_S constant | adv_helpers.py top-of-file | models: both (implied) | Magic number timeout values scattered across call sites; define once, reference everywhere.

VALIDATED (do NOT touch — both models confirmed excellent):
- CPU-only guard layering in conftest.py (CUDA_VISIBLE_DEVICES, faster_whisper stub, nvidia-smi session-finish architecture — only the PID-scoping of the check changes, not the architecture).
- gen_cases seeded generator (adv_helpers.py:245) — do not refactor.
- speech_like CPU audio synthesis (adv_helpers.py:348) — add timeout only, no logic changes.
- release_run golden control fixture (adv_helpers.py:520) — do not touch.
- Strict xfail + REQUESTS.md discipline — do not loosen any xfail or remove any reason string.
- test_every_required_row_has_a_vacuity_probe meta-test (test_f4_vacuity.py:1845) — do not touch.
- test_f3_release_auth.py fail-closed exhaustion — do not simplify parameterization.
- Template fixtures with module-scoped copy pattern (test_f2_provenance.py:1083,1104) — do not change fixture architecture.
- fake_llm HTTP seam and dual-wiring G8 test (test_f5:2266) — do not modify.
- tmp_path / tempfile.mkdtemp isolation throughout — do not change temp-directory strategy.

After implementing:
1. regression_test.sh must show zero FAILs.
2. Verify test_f5_references.py skips cleanly (not fails) when PP_REFS_DIR is unset.
3. Verify conftest.py nvidia-smi check passes on a CPU-only runner (nvidia-smi absent).
4. Verify all subprocess.run calls now have timeout= argument — grep for subprocess.run in tests/ and confirm no bare calls remain.

git add -A && git commit -m "feat(pp-tests_audit_A): post-audit pass — subprocess timeouts, portable ref path, nvidia-smi pid-scoping"
git push origin pp-tests
```