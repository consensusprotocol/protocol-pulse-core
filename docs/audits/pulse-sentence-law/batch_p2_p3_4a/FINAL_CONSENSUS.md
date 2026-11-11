# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 05:49
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem      | Gemini | GPT-4o | Grok | Consensus |
|----------------|--------|--------|------|-----------|
| Correctness    | 8/10   | 8/10   | 9/10 | **8/10**  |
| Law Compliance | 9/10   | 9/10   | 9/10 | **9/10**  |
| Test Quality   | 9/10   | 8/10   | 9/10 | **9/10**  |
| Security       | —      | 7/10   | 7/10 | **7/10**  |
| Overall        | READY w/ conditions | READY w/ conditions | READY w/ conditions | **CONDITIONAL READY** |

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### UF-1 — Silent "uncertain" label on face-detection failure
- **What it is:** When face detection fails in `vertical_layout.py:1818`, the shot is silently classified as `"uncertain"` with no log emission. The only way to discover it is manual inspection of contact sheets.
- **File/Line:** `vertical_layout.py:1818`
- **What to change:** Emit a structured warning log immediately when the label is set to `"uncertain"`. Minimum payload: clip ID, frame index, timestamp (seconds). Example:
  ```python
  logger.warning(
      "uncertain_detection",
      clip=clip_id, frame=frame_idx, t=round(frame_idx / fps, 3)
  )
  ```
- **Why unanimous:** All three models independently called this out as a zero-risk, high-observability improvement that turns a silent failure into a surfaced anomaly visible in the gate report.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### MF-1 — Credits rendering defect D4 not fixed — only made visible
- **Models:** Gemini (P1 HIGH), GPT-4o (P2 MEDIUM)
- **What it is:** The new `verify_pack.py` (line 1691) surfaces the "warped avatar" credits defect via a contact sheet, but the underlying rendering path in `render_vertical.py` still allows a visually defective asset to be produced. The monitoring control exists; the preventative control does not.
- **File/Line:** `render_vertical.py` (credits/shoutout dispatch path); `verify_pack.py:1691`
- **What to change:**
  1. In the vertical rendering dispatcher, detect when the segment type is `credits` or `shoutout` and validate that the resulting layout plan is not applying face-crop logic to a graphical card.
  2. If the plan would produce a distorted render, `raise RuntimeError("D4: credits reframe would warp avatar — aborting")`. This closes the M12 FAIL CLOSED loop.
  3. Add a one-line comment at `verify_pack.py:1691` documenting that this contact-sheet check is an interim detection control and that the preventative guard above is the permanent fix.
- **Disagreement note:** Grok assessed the verify_pack workaround as "intentional interim control" and did not escalate to P1. Gemini escalated it to P1 and the strongest finding of Cycle 2. See CONFLICTS section.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 — Potential off-by-one in `_cut_frame` (GPT-4o only)
- **Model:** GPT-4o
- **What it is:** GPT-4o raised a concern about frame index bounds in the `_cut_frame` function in `vertical_layout.py:1780–1802`.
- **Assessment:** **Skip.** Gemini re-examined the specific logic `a, b = max(1, mid - half), min(n_frames - 1, mid + half)` and `cap.set(cv2.CAP_PROP_POS_FRAMES, a - 1)` and confirmed the 0-indexed positioning is correct. The `max`/`min` clamping prevents out-of-bounds reads. GPT-4o's concern was speculative and is not substantiated by the code. No change required.

### UI-2 — ML model hash pinning as a reproducibility best practice (Gemini only)
- **Model:** Gemini
- **What it is:** Gemini highlighted that `face_scrfd.py:19,35–37` pins the ONNX model via SHA256 and fails closed on mismatch as a textbook implementation of reproducibility in an ML pipeline.
- **Assessment:** **No action — validated strength.** This is a positive observation, not a defect. Captured in VALIDATED STRENGTHS.

### UI-3 — Shell command injection safety (Gemini only)
- **Model:** Gemini
- **What it is:** Gemini verified that `word_diff.py:2084` and related scripts use array-form `subprocess.run` and correctly quote shell variables in `pulse_check_run.sh`, confirming no injection risk.
- **Assessment:** **No action — validated strength.** Security posture confirmed sound in this area. Captured in VALIDATED STRENGTHS.

### UI-4 — `ffmpeg` 4.x xfade frame-slip fix significance (Gemini, corroborated by Grok)
- **Model:** Gemini primary; Grok mentioned it
- **What it is:** `transitions.py:1570–1574` corrects a known `ffmpeg` 4.x bug where audio leads video by exactly one frame after a dissolve, by subtracting `1 / FPS` from the xfade offset.
- **Assessment:** **No action — validated strength.** Both models confirm this is correct and sophisticated. Captured in VALIDATED STRENGTHS.

---

## CONFLICTS (models disagree — tiebreaker)

### CONFLICT-1 — Severity of the credits D4 defect (MF-1)

| Model  | Position |
|--------|----------|
| Gemini | P1 HIGH — verify_pack is monitoring only; fail-closed guard required; Cycle 1 READY verdict was premature |
| GPT-4o | P2 MEDIUM — document in backlog if not fixed immediately; not a release blocker |
| Grok   | P2 — intentional interim control; underlying path correctly left out of this diff |

**Tiebreaker — Gemini is correct on the substance; Grok/GPT-4o are correct on release posture.**

The technical argument is Gemini's: a system that knowingly produces a defective output and then detects it after the fact is not M12 FAIL CLOSED compliant. The M12 principle requires prevention, not detection-after-production. The verify_pack contact sheet is a monitoring control, not a preventative one.

However, Grok's operational reading is also valid: if this diff's scope was explicitly bounded to *not* fix the credits rendering path, shipping with a monitoring control and a documented deferral is acceptable pipeline governance — provided the deferral is explicitly committed to a backlog item with an owner.

**Final ruling:** Implement the fail-closed guard as **P1 HIGH**. If implementation is blocked by scope, the deferral must be committed to the backlog with an explicit tracking reference added as a comment at `verify_pack.py:1691` and `render_vertical.py` (credits dispatch). The monitoring-only posture is **not acceptable indefinitely** under M12.

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

1. **`face_scrfd.py` — SHA256 model pinning and fail-closed on mismatch** (lines 19, 35–37): Textbook implementation of ML reproducibility. Touch nothing.

2. **`transitions.py` — `ffmpeg` 4.x xfade frame-slip correction** (lines 1570–1574): Correctly subtracts `1/FPS` from xfade offset to prevent one-frame A/V desync after a dissolve. Sophisticated and correct. Touch nothing.

3. **`word_diff.py` — `gate_g18` word-for-word enforcement and `norm` function** (lines 2027, 2093–2111): Correctly enforces first/last words against sealed `selection_lock`; `norm` comprehensively handles ASR inconsistencies. Touch nothing.

4. **`render_vertical.py:253` — Hard `RuntimeError` on reframe failure**: Correctly implements M12 FAIL CLOSED for the standard reframe path. Touch nothing.

5. **`transitions.py` — `plan` function speech-room bounding** (lines 1402, 1417–1419): Correctly prevents transitions from overlapping speech by bounding duration to available non-speech room. Touch nothing.

6. **`face_scrfd.py` — Global `_SESSION` initialization**: Efficient single-load, thread-safe in a single-process pipeline. Touch nothing.

7. **Shell command injection safety** (`word_diff.py:2084`, `pulse_check_run.sh`): Array-form `subprocess.run` and correct variable quoting throughout. Touch nothing.

8. **`_transition_concat`** (`render16.py:147`): Correctly returns `None` when `TRANSITIONS.json` is absent, preserving the frozen v2f hard-cut path as the default. Touch nothing.

9. **Test suite** (`test_word_diff.py:1276–1288`, `test_vertical_layout.py:1054`): Tests correctly target must-fail fixtures from `pulse_20261110`; no vacuous assertions. Touch nothing.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|-----|--------|-------|
| **SENTENCE LAW** | ✅ COMPLIANT | `gate_g18` enforces word-for-word match against sealed `selection_lock`; no recomputation of expected words post-selection |
| **SELECTION LOCK** | ✅ COMPLIANT | `lock_text` from `edl.json` used throughout; G16/G18 gates read sealed lock only |
| **SNAP LIMIT** | ✅ COMPLIANT | Shot boundaries determined by measured lead/tail; not recomputed beyond initial detection |
| **ONSET/TAIL** | ✅ COMPLIANT | G17 checks added (`run_fresh.py:458`); `head_tail` calls bound cuts correctly |
| **CREDITS** | ⚠️ PARTIAL — monitoring only | G12/G15 preserved and included in verify_pack; however D4 preventative guard absent (see MF-1) |
| **LAW 20 / M2** | ✅ COMPLIANT | Gate thresholds are constants; no alteration to pass |
| **M12 FAIL CLOSED** | ⚠️ PARTIAL — credits path gap | Standard reframe path: compliant. Credits reframe path: monitoring control only, not preventative |
| **LAW 22 / v2f frozen** | ✅ COMPLIANT | `TRANSITIONS.json` absence defaults to hard-cut v2f path explicitly |

**Summary:** Two laws carry a partial compliance flag, both traceable to the same root cause: the credits rendering path lacks a fail-closed guard. All other laws are fully compliant.

---

## SECURITY CONSENSUS

Both models that scored security (GPT-4o: 7/10, Grok: 7/10) found no active vulnerabilities. Gemini's separate confirmation of safe subprocess usage corroborates this.

**Priority order of security observations:**

1. ✅ **SHA256 model hash pinning** — prevents supply-chain substitution of the ONNX model. Already implemented correctly.
2. ✅ **Array-form subprocess calls** — prevents shell injection. Already implemented correctly.
3. ℹ️ **No network calls in hot path** — inference is local; no exfiltration surface identified.

**Security verdict:** No actionable security findings. Score of 7/10 reflects the inherent baseline risk of an ONNX inference pipeline and ffmpeg subprocess usage, not specific defects.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models:

### WCG-1 — Observability: silent failure modes surface only in contact sheets
- **Models:** All three
- **Gap:** The pipeline currently requires a human to open a contact sheet to discover uncertain detections or D4 defects. A world-class pipeline emits structured, machine-readable anomaly signals at every failure boundary so that gate reports, alerting, and dashboards can surface issues without human review of visual artifacts.
- **Minimum viable improvement:** Structured `logger.warning` on `uncertain` path (UF-1 above). Stretch: emit a JSON anomaly record per clip per gate that downstream tooling can aggregate.

### WCG-2 — Preventative vs. detective controls for known defects
- **Models:** Gemini, GPT-4o
- **Gap:** The credits D4 defect is currently handled as a detective control (verify_pack contact sheet) rather than a preventative one (fail-closed guard). A world-class pipeline never allows a known-bad output to be produced; it fails before writing the file. The pattern of "produce → detect → flag" is acceptable for unknown failures but is below the bar for known, categorized defects.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P1 HIGH** | Add fail-closed `RuntimeError` guard in credits/shoutout vertical rendering dispatch path. If layout plan would apply face-crop logic to a graphical card, raise `RuntimeError("D4: credits reframe would warp avatar — aborting")` before writing any output file. | `render_vertical.py` (credits dispatch) | Gemini (P1), GPT-4o (P2), tiebreaker → P1 | M12 FAIL CLOSED requires prevention, not detection-after-production. Known defect must be blocked at the source. |
| **P1 HIGH** | Emit `logger.warning("uncertain_detection", clip=clip_id, frame=frame_idx, t=round(frame_idx/fps,3))` when shot label becomes `"uncertain"` due to detection failure. | `vertical_layout.py:1818` | All three models | Zero-risk. Turns silent failure into surfaced anomaly in gate report. Required for operational observability. |
| **P2 MEDIUM** | Add one-line comment at credits contact-sheet check documenting that D4 fix is deferred and that this verification is a monitoring (not preventative) control. Include backlog ticket reference. | `verify_pack.py:1691` | Gemini, Grok | Prevents future maintainers from assuming the contact sheet check constitutes full M12 compliance. |
| **P2 MEDIUM** | Add one-line comment in credits rendering area of `render_vertical.py` documenting the deferred D4 guard, with backlog reference, until P1 guard above is implemented. | `render_vertical.py` (credits area) | Gemini, Grok | Same rationale — explicit deferral documentation is required if P1 is not implemented in this pass. |

**Items explicitly excluded:**
- ~~`_cut_frame` off-by-one~~ — GPT-4o only, refuted by Gemini's analysis. Skip.
- ~~`ffmpeg` xfade fix~~ — Validated strength. Touch nothing.
- ~~`gate_g18` / `norm` function~~ — Validated strength. Touch nothing.

---

## CYCLE 2 VERDICT

**CONDITIONAL READY**

The feature is architecturally sound, legally compliant on all axes except the credits rendering path, and demonstrates exceptional engineering quality in several areas (xfade frame-slip fix, model hash pinning, `norm` function comprehensiveness, speech-room bounding in transitions).

**Absolute final blockers before unconditional READY:**

1. **BLOCKER 1 (P1):** Fail-closed guard for credits vertical rendering — either implement the `RuntimeError` guard in `render_vertical.py` or commit a dated backlog item and add the documenting comment to both `render_vertical.py` and `verify_pack.py:1691`. The monitoring-only posture is not M12 compliant.

2. **BLOCKER 2 (P1):** Structured logging on the `uncertain` detection path in `vertical_layout.py:1818` — one line, zero risk, required for gate report observability.

Both blockers are low-effort, high-confidence changes. Neither requires architectural rework. Ship after both are implemented and `regression_test.sh` shows zero FAILs.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P1 HIGH | Add fail-closed RuntimeError guard for credits/shoutout vertical
        | rendering. In the vertical rendering dispatcher, detect when segment
        | type is 'credits' or 'shoutout'. If the layout plan would apply
        | face-crop logic to a graphical card, raise:
        |   RuntimeError("D4: credits reframe would warp avatar — aborting")
        | before any output file is written.
        | File: render_vertical.py (credits dispatch path)
        | Models: gemini (P1), gpt4o (P2), consensus tiebreaker → P1
        | Why: M12 FAIL CLOSED requires prevention not detection-after-production.

P1 HIGH | Add structured warning log on uncertain detection path:
        |   logger.warning(
        |       "uncertain_detection",
        |       clip=clip_id, frame=frame_idx, t=round(frame_idx/fps,3)
        |   )
        | File: vertical_layout.py:1818 (immediately when label set to "uncertain")
        | Models: all three
        | Why: turns silent failure into surfaced anomaly visible in gate report.

P2 MEDIUM | Add one-line comment documenting that D4 fix is deferred and that
          | the contact-sheet check is a monitoring (not preventative) control.
          | Include backlog ticket reference.
          | File: verify_pack.py:1691
          | Models: gemini, grok

P2 MEDIUM | Add one-line comment in credits rendering area documenting deferred
          | D4 guard with backlog reference, if P1 guard above is not in this pass.
          | File: render_vertical.py (credits area)
          | Models: gemini, grok

VALIDATED (do NOT touch — all models confirmed excellent):
- face_scrfd.py:19,35-37 — SHA256 model hash pinning and fail-closed on mismatch
- transitions.py:1570-1574 — ffmpeg 4.x xfade frame-slip correction (1/FPS offset)
- word_diff.py:2027,2093-2111 — gate_g18 enforcement and norm() function
- render_vertical.py:253 — hard RuntimeError on standard reframe failure
- transitions.py:1402,1417-1419 — plan() speech-room bounding for transitions
- face_scrfd.py:23,27-41 — global _SESSION single-load initialization
- word_diff.py:2084 + pulse_check_run.sh — array-form subprocess / shell quoting
- render16.py:101,147 — _transition_concat None return preserving v2f hard-cut default
- test_word_diff.py:1276-1288, test_vertical_layout.py:1054 — must-fail fixture tests

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

**WINNER: Gemini** — Gemini demonstrated the deepest analytical insight across both cycles, uniquely identifying the architectural distinction between monitoring controls and preventative controls (the D4 credits defect), recognizing the ffmpeg 4.x frame-slip fix as exceptional domain expertise rather than merely noting the code existed, and producing the most substantive Cycle 2 self-correction by explicitly naming what it missed and why. Its analysis was the most complete, the most actionable in explaining *why* findings mattered, and the only one to escalate its own Cycle 1 gaps with genuine technical depth rather than surface-level agreement.

---

## FINAL SECOND-PASS PRIORITY LIST

**P0 — Blocking (must implement before merge)**
*(None — all models confirmed CONDITIONAL READY; no P0 items exist)*

**P1 — High (implement in this sprint)**

1. **`vertical_layout.py:1818` — Emit structured warning on `"uncertain"` detection**
   Add `logger.warning("uncertain_detection", clip=clip_id, frame=frame_idx, t=round(frame_idx / fps, 3))` immediately when the label is set. This is zero-risk, unanimously agreed, and converts a silent observability black hole into a surfaced gate-report anomaly.

2. **`render_vertical.py` (credits path) — Implement preventative control for D4**
   The current verify_pack contact-sheet check is a monitoring control only. The underlying avatar-warp rendering path remains unguarded. Add a pre-render guard that either raises `RuntimeError` on detected credits-segment vertical reframe or routes credits to the frozen v2f hard-cut path until a corrected reframe implementation is available.

**P2 — Medium (implement before next release)**

3. **`verify_pack.py:1691` + `render_vertical.py` (credits path) — Document D4 deferral explicitly**
   If P1 item 2 is deferred beyond this sprint, add a one-line inline comment at both the dispatch site and the verify_pack check explicitly stating that D4 fix is deferred and contact-sheet verification is the sole current control. This prevents future reviewers from mistaking the monitoring control for a fix.

4. **`vertical_layout.py` — Validate frame indices in `_cut_frame`**
   Add a bounds check confirming frame indices fall within `[0, total_frames - 1]` before use. The potential off-by-one is low-probability but zero-cost to guard and prevents silent truncation errors on short clips.

**P3 — Low (backlog)**

5. **`transitions.py:1570-1574` — Add inline comment citing ffmpeg 4.x frame-slip issue**
   The `- 1 / FPS` offset corrects a known upstream bug. Document the specific ffmpeg version behavior and the fix rationale so future maintainers do not remove it as an apparent magic number.

6. **Gate report — Surface `"uncertain"` count as a named metric**
   Beyond the per-instance log from P1 item 1, aggregate the total uncertain-detection count per run into the gate summary report so threshold alerts can be set without log-scraping.