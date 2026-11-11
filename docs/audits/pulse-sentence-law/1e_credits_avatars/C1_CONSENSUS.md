# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 03:10
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness — Avatar Pipeline | 7/10 | 9/10 | 8/10 | **8/10** |
| Correctness — Sentence Law | N/A | N/A | N/A | **N/A (not in diff)** |
| Law: CREDITS | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| Law: M12 FAIL CLOSED | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| Law: SENTENCE LAW | NOT ADDRESSED | NOT ADDRESSED | NOT ADDRESSED | **NOT ADDRESSED** |
| Law: LAW 22 | UNCERTAIN | NOT ADDRESSED | NOT ADDRESSED | **UNCERTAIN** |
| Law: SELECTION LOCK | NOT ADDRESSED | COMPLIANT | COMPLIANT | **DEFERRED** |
| Law: LAW 20 / M2 | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| Tests | MISSING | MISSING | MISSING | **MISSING** |
| Overall Verdict | NOT READY | READY | READY | **NOT READY** |

> **Score note:** Gemini is correct to flag NOT READY. The 2-to-1 "READY" votes from GPT-4o and Grok evaluate only the D4 avatar sub-scope in isolation; Gemini correctly evaluates the full stated scope. Consensus defers to the stricter assessment when scope completeness is in question.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Missing test file is a critical gap
- **What:** The feature description explicitly requires `pipeline/test_pulse_20261110_mustfail.py`. All three models noted its complete absence. Without it there is no machine-verifiable proof that the new avatar gates catch the exact errors from the problematic run.
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py` — does not exist in diff
- **Change:** Create the must-fail fixture suite. It must include at minimum: (a) a test that feeds a non-square image and asserts `validate_avatar` raises `ValueError`; (b) a test that feeds a hash-mismatched avatar and asserts `_find_avatar` raises; (c) a test that feeds a missing `channels.json` entry and asserts `_find_avatar` raises; (d) a test that feeds the original warped-avatar fixture from `pulse_20261110` and asserts the render aborts.

### U2 — `cmd_register` uses brittle regex in-place JSON editing
- **What:** All three models independently flagged `cmd_register` (lines 117–141 of `avatar_onboard.py`) as modifying `channels.json` via regular-expression string surgery. If the file's whitespace, key ordering, or structure changes by even one character, the regex may corrupt the file or silently produce invalid JSON. The final `json.loads(text)` sanity check catches corruption but does not make the approach robust.
- **File/Line:** `pipeline/avatar_onboard.py:117–141`
- **Change:** Replace the regex loop with: `data = json.loads(path.read_text())` → modify `data` as a Python dict → `path.write_text(json.dumps(data, indent=2, ensure_ascii=False))`. This is atomic, encoding-safe, and immune to formatting drift.

### U3 — Sentence-Law code is entirely absent from the diff
- **What:** The feature is named `pulse-sentence-law`. All three models noted that no sentence-boundary, onset, snap-limit, or selection-lock code appears anywhere in the diff. The diff exclusively addresses D4 (avatar warping). Defects D1–D3 and D5–D6 are unrepresented.
- **File/Line:** N/A — systemic scope gap
- **Change:** Either (a) implement the sentence-law changes in this pass, or (b) formally split the feature into `pulse-d4-avatar-fix` (this diff, which can be READY) and `pulse-sentence-law` (new branch, new audit cycle). Do not ship a branch named `pulse-sentence-law` that contains zero sentence-law code.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Disabled channel entry lacks documentation (Saylor / line 575)
- **Models:** Grok + GPT-4o
- **What:** A channel entry is set to `enabled: false` with no accompanying comment explaining why it was disabled or when it may be re-enabled. Future maintainers have no context.
- **File/Line:** `pipeline/channels.json:575` (and line 829 per GPT-4o — both are the same pattern)
- **Change:** Add an inline comment in the JSON (or a companion `_disabled_reason` field) stating the reason and the date. Example: `"_disabled_reason": "No square avatar available 2026-11-10; re-enable after manual fetch"`.

### M2 — Duplicate SHA prefix check is advisory-only with no enforcement
- **Models:** Grok + Gemini (Gemini addresses this implicitly through the hash-mismatch gate discussion)
- **What:** The SHA prefix check in `cmd_fetch` (lines 108–111) logs a warning for duplicate avatars but does not block registration. This means two channels could end up sharing the same avatar file without the pipeline aborting.
- **File/Line:** `pipeline/avatar_onboard.py:108–111`
- **Change:** Promote the duplicate-SHA warning to a hard error (raise an exception or exit non-zero) so that the contact-sheet manual verification step sees an explicit failure rather than a buried log line.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — Hardcoded absolute paths in `channels.json` (Gemini only)
- **Assessment: IMPLEMENT**
- **What:** `avatar_path` entries use absolute filesystem paths (`/home/ultron/...`). The pipeline cannot run on any machine other than the one where the paths were written, and paths will silently break if the home directory changes or the project is moved.
- **Fix:** Store paths relative to the project root (e.g., `avatars/UC.../avatar.png`) and resolve them at runtime via `PROJECT_ROOT / entry["avatar_path"]`. Alternatively, store only the filename and derive the full path from a configured `AVATAR_DIR` constant.
- **Priority:** P2 (does not affect correctness on the current machine, but is a portability landmine).

### UI2 — LAW 22 byte-identical render reference may be violated by this fix (Gemini only)
- **Assessment: INVESTIGATE FURTHER**
- **What:** LAW 22 requires the frozen reference (`v2f_2026-11-06`) to re-render byte-identically. The avatar fix intentionally changes visual output (replacing warped/missing avatars with correct ones), which will produce a different render hash. Gemini correctly flags that it is unclear whether LAW 22 has an exemption for bug-fix render changes.
- **Action:** Clarify with the protocol owner whether LAW 22 requires updating the frozen reference after a confirmed bug fix, or whether the law only applies to non-bug-fix render passes. Document the decision in `PULSE_SENTENCE_LAW_GOSPEL.md` before closing this feature. Do not ship without resolution.
- **Priority:** P1 (legal ambiguity that could invalidate the entire feature retroactively).

### UI3 — `avatar_url()` has no timeout or retry on `yt-dlp` subprocess (GPT-4o implicitly; unique explicit gap)
- **Assessment: IMPLEMENT (P2)**
- **What:** `avatar_url()` calls `yt-dlp` as a subprocess with no timeout guard. A hung network request will stall the pipeline indefinitely. This is a robustness issue in a CI/batch context.
- **Fix:** Add `timeout=30` (or configurable) to the subprocess call and catch `subprocess.TimeoutExpired`, converting it to a descriptive exception.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Overall verdict: READY vs NOT READY
- **GPT-4o and Grok:** READY
- **Gemini:** NOT READY
- **Tiebreaker: Gemini is correct.**
- **Reasoning:** GPT-4o and Grok evaluated the D4 avatar fix in isolation and found it sound—which is accurate. However, neither model enforced the scope contract. A branch named `pulse-sentence-law` that ships zero sentence-law code is not ready by definition, regardless of how good the avatar sub-fix is. Gemini's NOT READY verdict is the correct frame. The avatar work can be cherry-picked or re-scoped, but the branch as named cannot be merged.

### C2 — SHA prefix check: advisory vs. hard stop
- **Grok:** Duplicate check is "only advisory" (severity: none, acceptable)
- **Gemini (implicit):** Hard stops for integrity failures are required by M12
- **Tiebreaker: Gemini's principle is correct; promote to hard error (see M2 above).**
- **Reasoning:** M12 FAIL CLOSED mandates that integrity anomalies abort the pipeline. A duplicate avatar SHA is an integrity anomaly (two channels sharing one avatar is almost certainly wrong). Logging and continuing violates the spirit of M12.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

1. **New `_find_avatar` implementation (shoutout.py lines 970–987):** The fail-closed design — requiring a `channels.json` entry, a live file, a matching SHA prefix, and valid dimensions before proceeding — is a textbook M12 implementation. All three models praised this. Do not relax any of these gates.

2. **New `validate_avatar` gate (shoutout.py lines 863–873):** The use of named constants (`AVATAR_SQUARE_TOL`, `AVATAR_MIN_PX`) and hard `ValueError` raises on failure is correct and compliant. Do not soften the exception to a warning.

3. **Removal of on-demand avatar fetching and placeholder generation:** Eliminating the old permissive `_find_avatar` path (which was the root cause of D4) is the right architectural decision. All three models affirmed this. Do not reintroduce any fallback or placeholder path.

4. **Two-step manual verification workflow (`avatar_onboard.py`):** The design of fetch → contact-sheet → manual check → register is sound. The fail-fast behavior in `fetch_one()` (raising on non-square or undersized images at fetch time) correctly prevents bad data from ever reaching the registry. Do not collapse this into a single automated step.

5. **`avatar_url()` square-avatar selection logic:** The yt-dlp integration correctly targets channel-level square avatars (not video thumbnails) and raises when none are available. Do not change the selection criteria.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Confidence | Notes |
|---|---|---|---|
| CREDITS | **COMPLIANT** | High (3/3) | Real verified square avatars only; gates prevent anything else |
| M12 FAIL CLOSED | **COMPLIANT** | High (3/3) | All failure paths raise exceptions; no silent pass |
| LAW 20 / M2 | **COMPLIANT** | High (3/3) | Named constants for thresholds; hard stops on failure |
| SENTENCE LAW | **NOT ADDRESSED** | High (3/3) | Zero sentence-law code in diff |
| SELECTION LOCK | **NOT ADDRESSED** | Medium (2/3 explicit) | No evidence of violation but also no coverage |
| SNAP LIMIT | **NOT ADDRESSED** | High (3/3) | Outside diff scope |
| ONSET / TAIL | **NOT ADDRESSED** | High (3/3) | Outside diff scope |
| LAW 22 | **UNCERTAIN** | Low (1/3 flagged) | Bug fix may alter frozen reference render; needs protocol clarification |

---

## SECURITY CONSENSUS

No models flagged active security vulnerabilities. The following hardening items are worth noting in priority order:

1. **SHA prefix check (8 hex chars):** While sufficient for accidental collision detection, 8 characters (~32 bits) is not cryptographically strong against adversarial substitution. For the current threat model (internal pipeline, no adversarial actors) this is acceptable. If the pipeline ever processes externally-supplied avatar files, upgrade to full SHA-256 comparison.

2. **`yt-dlp` subprocess without timeout:** A network-stall denial-of-service against the CI pipeline is possible (see UI3). Low severity in the current context; fix opportunistically.

3. **Absolute paths in `channels.json`:** An accidental path disclosure risk if the file is committed to a public repository. Relative paths eliminate this exposure (see UI1).

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models)*

1. **No machine-verifiable proof of the fix (2+/3 models):** A world-class bug fix ships with a regression test that runs against the original bad fixture and asserts the new behavior. The contact sheet provides human verification but not CI verification. The `test_pulse_20261110_mustfail.py` file is the minimum bar.

2. **Brittle JSON modification pattern (3/3 models):** World-class pipeline tooling never modifies structured data files with string surgery. The regex approach in `cmd_register` is a maintenance debt that will eventually corrupt state. Standard JSON load/modify/dump is the floor.

3. **Scope-name mismatch (3/3 models, all noted absence of sentence-law code):** A world-class feature branch delivers what it promises. Shipping a branch named `pulse-sentence-law` with no sentence-law implementation is a process failure that erodes trust in the audit and delivery system itself.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Create test_pulse_20261110_mustfail.py with must-fail fixtures
            | pipeline/test_pulse_20261110_mustfail.py (new file)
            | models: all (3/3)
            | Without machine-verifiable proof the fix is unproven; CI cannot
            | confirm regression is closed

P0 CRITICAL | Resolve scope gap: implement sentence-law code or formally
            | rename/split the branch
            | Branch name vs. diff content — systemic
            | models: all (3/3)
            | A branch named pulse-sentence-law with zero sentence-law code
            | cannot be merged; either implement D1-D3/D5-D6 or scope the
            | branch to pulse-d4-avatar-fix and open a new branch for
            | sentence-law work

P1 HIGH     | Replace regex JSON surgery in cmd_register with json.load/dump
            | pipeline/avatar_onboard.py:117-141
            | models: all (3/3)
            | File corruption risk on any formatting change; standard pattern
            | is 5 lines and eliminates the entire risk class

P1 HIGH     | Clarify and document LAW 22 position on bug-fix render changes
            | docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md + render reference
            | models: gemini (unique but HIGH impact)
            | Legal ambiguity that could invalidate the feature retroactively;
            | must be resolved before merge

P1 HIGH     | Promote duplicate-SHA check to hard error (raise, not log)
            | pipeline/avatar_onboard.py:108-111
            | models: grok + gemini (2/3)
            | M12 FAIL CLOSED requires integrity anomalies to abort; a shared
            | avatar SHA between two channels is almost certainly wrong

P2 MEDIUM   | Replace absolute avatar_path values with project-relative paths
            | pipeline/channels.json (all avatar_path entries)
            | models: gemini (unique)
            | Pipeline is non-portable; will silently break on any path change
            | or new dev machine; fix: store relative paths, resolve at runtime

P2 MEDIUM   | Document disabled channel entries with reason and date
            | pipeline/channels.json:575 (and any other enabled:false entries)
            | models: grok + gpt4o (2/3)
            | Zero-context disables are maintenance hazards; add
            | _disabled_reason field or inline comment

P2 MEDIUM   | Add subprocess timeout to avatar_url() yt-dlp call
            | pipeline/avatar_onboard.py (avatar_url function)
            | models: unique observation (robustness gap)
            | Hung network call stalls CI indefinitely; timeout=30 + exception
            | handler is 2-line fix
```

---

## CYCLE 1 VERDICT

**NOT READY — Fundamental rework required on two dimensions.**

The D4 avatar fix itself is well-implemented and would be READY if evaluated as a standalone feature. The core logic (fail-closed `_find_avatar`, `validate_avatar` gate, two-step onboarding) is sound and should not be changed.

However, the branch cannot merge as `pulse-sentence-law` because:
1. It contains zero sentence-law implementation (the stated primary purpose of the branch).
2. It contains zero machine-verifiable tests proving the D4 fix holds under CI.
3. The LAW 22 reference-render question is unresolved.

**Recommended path:** Split the work. Rename the current branch `pulse-d4-avatar-fix`, apply the P0/P1 fixes from this report (tests + JSON refactor + LAW 22 clarification), and merge it. Open a fresh `pulse-sentence-law` branch for the actual sentence-law implementation with its own audit cycle.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law (Cycle 1 post-audit).
Three independent models (Gemini 2.5 Pro, GPT-4o, Grok-3) reviewed the
first build. Implement every P0 and P1 item below. Use judgment on P2.

════════════════════════════════════════════════════════
PRIORITY ACTION PLAN
════════════════════════════════════════════════════════

P0 CRITICAL | Create pipeline/test_pulse_20261110_mustfail.py
  - Must include at minimum four tests:
    (a) Feed a non-square image → assert validate_avatar raises ValueError
    (b) Feed a hash-mismatched avatar → assert _find_avatar raises
    (c) Feed a channels.json with no entry for the channel → assert _find_avatar raises
    (d) Feed the original warped-avatar fixture from pulse_20261110 →
        assert the render pipeline aborts before writing output
  - Tests must FAIL before the fix and PASS after. Verify this.
  - No vacuous passes: each test must assert the exception type and message.

P0 CRITICAL | Resolve branch scope gap
  - If sentence-law code (D1–D3, D5–D6) is ready: implement it now.
  - If not: rename this branch to pulse-d4-avatar-fix and open a new
    branch pulse-sentence-law for the sentence-law work. Update all
    commit messages and gospel references accordingly.
  - Do not ship a branch named pulse-sentence-law with zero sentence-law code.

P1 HIGH | Refactor cmd_register in pipeline/avatar_onboard.py:117-141
  - Remove ALL regex-based string surgery on channels.json.
  - Replace with: data = json.loads(path.read_text())
                  [modify data dict]
                  path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
  - Keep the final json.loads validation check as a sanity gate.
  - Ensure the resulting file is UTF-8, 2-space indented, and passes
    json.loads without error.

P1 HIGH | Clarify LAW 22 position on this bug fix
  - Add a section to PULSE_SENTENCE_LAW_GOSPEL.md titled
    "LAW 22 — Bug Fix Render Exception" explaining:
    (a) That the D4 fix intentionally changes credit-scene visual output
    (b) Whether the frozen reference (v2f_2026-11-06) must be updated
    (c) If yes: update the reference and document the new hash
    (d) If no: document why this fix is exempt
  - Do not leave this unresolved.

P1 HIGH | Promote duplicate-SHA check to hard error
  - pipeline/avatar_onboard.py:108-111
  - Change: log.warning(...) → raise ValueError(f"Duplicate avatar SHA: ...")
  - Two channels sharing one avatar file is an integrity anomaly.
  - M12 FAIL CLOSED requires abort, not log-and-continue.

════════════════════════════════════════════════════════
P2 MEDIUM (use judgment — implement if low-risk)
════════════════════════════════════════════════════════

P2 | Replace absolute avatar_path values in channels.json with paths
    relative to PROJECT_ROOT. Resolve at runtime via:
    PROJECT_ROOT / entry["avatar_path"]
    Define PROJECT_ROOT = Path(__file__).parent.parent in avatar_onboard.py
    and shoutout.py.

P2 | Add _disabled_reason field to every enabled:false entry in
    channels.json explaining why it was disabled and when to re-enable.

P2 | Add timeout=30 to the yt-dlp subprocess call in avatar_url() and
    catch subprocess.TimeoutExpired, re-raising as a descriptive
    RuntimeError("yt-dlp timed out for channel {channel_id}").

════════════════════════════════════════════════════════
VALIDATED — DO NOT TOUCH (all 3 models confirmed excellent)
════════════════════════════════════════════════════════

- _find_avatar in shoutout.py (lines 970-987): fail-closed design with
  channels.json lookup + file existence + SHA prefix + dimension checks.
  Do NOT relax any gate. Do NOT add fallbacks or placeholders.

- validate_avatar in shoutout.py (lines 863-873): named constants +
  hard ValueError raises. Do NOT soften to warnings.

- Removal of on-demand avatar fetching and placeholder generation:
  the old permissive _find_avatar is gone. Do NOT reintroduce any
  fallback or placeholder path under any condition.

- Two-step onboarding workflow (fetch → contact-sheet → manual check →
  register): do NOT collapse into single automated step.

- avatar_url() square-avatar selection logic: correctly targets
  channel-level square avatars, not thumbnails. Do NOT change criteria.

════════════════════════════════════════════════════════
COMPLETION CRITERIA
════════════════════════════════════════════════════════

After implementing:
1. regression_test.sh must show zero FAILs
2. python -m pytest pipeline/test_pulse_20261110_mustfail.py -v must show
   all tests PASSED
3. json.loads(open('pipeline/channels.json').read()) must succeed
4. LAW 22 position must be documented in the gospel

Then:
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements C1"
git push origin combo-letterbox-quoteonly-v2
```