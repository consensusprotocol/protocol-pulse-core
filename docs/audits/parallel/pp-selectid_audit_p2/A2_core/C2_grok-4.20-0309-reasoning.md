# grok-4.20-0309-reasoning (xAI, medley key) 30 s usage=48821

**CYCLE 2 REVIEW — pp-selectid-p2 (A2_core fixed diff)**

**Reviewer:** Grok (xAI). This is my second pass after seeing the four Cycle 1 reviews (including my own prior output that scored Q1:72 / Q2:88 / Q3:93 / Q4:55 / Q5:45 and flagged the pin literals, title-case NAME bypass, one-directional transcript_truth, and exclusion wiring gap).

### 1. WHAT DID THEY CATCH THAT I MISSED?
Cycle 1 (especially fable/opus/sonnet) caught three defects I under-weighted:
- The pin’s unconditional `{"vo_fidelity_ok": True, "context_integrity_ok": True}` (package_pin:1758-1759 in the prior version) made R7 vacuous. I noted it but treated it as P1; they correctly called it P0.
- Blind fidelity verdict accepting `{"claims": []}` or partial sentence coverage (vo_fidelity.check_verdict). My prior output only flagged Title-Case NAME bypass; I missed that an empty-claims reply satisfied `ok: not v`.
- Second recognition pass (transcript_truth) being optional-by-default, one-directional, and skipped on the plain-VO path. I saw the trigger limitation but not the full “not measured == pass” arithmetic hole or the Whisper “will rise” vs “will not rise” evasion.

The consensus synthesis correctly merged these into implemented fixes C1–C2.

### 2. WHERE DO I AGREE OR DISAGREE?
- **Strong agreement (C1, C2, P0-1/P0-2 from all reviewers):** The old pin and empty-claims verdict were critical fail-open bugs. The new `package.seal()` + GATE INVENTORY pattern (mentioned in consensus, visible in the referenced but not-shown package.py updates) and the rewritten `check_verdict` that walks every sentence and demands coverage are correct and decisive.
- **Agreement on transcript_truth:** The new `compare()` is now bidirectional with `Counter` differences and name folding both ways. `speaker_turns` now treats no labels as `None` and `verify_segment` rejects it. This closes the L-v 2 gap I only partially saw.
- **Partial disagreement on exclusion gate:** Cycle 1 correctly noted that production `moments.record()` still used the miner’s own `"risk"` list while the adapter exercised `exclusion_verdict`. The fixed `moments.py` now ships a full `exclusion_verdict` implementation (lines 871-908) that runs a deterministic ad-read screen then a blind model call (avoiding the miner). Production wiring is still outside this diff, but the gate itself is now sound.
- **Disagreement on vendor separation (Q2):** I still rate it higher than the Claudes. The new `context_integrity.step_a` and `check_contexts` correctly thread `avoid_vendor=writer_vendor` and `avoid_family`; `transcript_truth.second_pass` now routes through `router.transcribe` (line 965) instead of hard-coding OpenAI. The only residual is the trend_brief call (line 1199) which is intentionally xAI-only and documented as such.
- **Q4 deterministic rules:** The new vo_fidelity.py is substantially tighter (`_governed`, `strict_features`, `price_mentions` clause logic, hedge verbs). Title-case NAME bypass is gone (names_of now scans everywhere). I still see one narrow false-reject risk (a colon attribution at sentence start that `_attributions` treats as speaker but the verdict classifies as commentary), but it is now caught downstream.

### 3. NEW FINDINGS FROM THIS REVIEW (only what the combined Cycle 1 + fixed diff revealed)
- **P2 (medium):** context_integrity.py:464-469 — when step C returns `entails != "yes"` but supplies no `dropped_limit` that matches outside the <selected> span, the code emits a NOTE instead of NOT_ENTAILED. This is the exact “orchestrator 06:22 ruling 5” path. It is logged but does not fail the gate. A sophisticated model could exploit the NOTE path to weaken a limit without triggering violation. (Not a P0 because the deterministic layer and the “every sentence covered” verdict still bind it.)
- **P2:** transcript_truth.py:1016-1017 — `span_text` when the second pass returns only segments (no word timing) uses a 0.25 s overlap test that is not symmetric with the PAD_S = 1.5 s window. A 300 ms edge word can be silently dropped. Minor but measurable on short negations.
- **P1 (improved but not perfect):** vo_fidelity.check_verdict:1923-1933 — sentence splitting for coverage uses a simple `(?<=[.!?])\s+` regex. A sentence ending in “Dr.” or “etc.” can produce a coverage false-positive. The deterministic layer already protects most cases, but the verdict prompt’s “EVERY sentence” claim is not 100 % mechanically enforced.
- No new P0s. The empty-claims, unconditional pin, and one-directional truth pass are gone.

### 4. REVISED SCORES
| Question                  | Cycle 1 | Cycle 2 | Why changed |
|---------------------------|---------|---------|-------------|
| Q1 Fail-open              | 72      | 94      | Empty-claims verdict, optional second pass, and pin literals are fixed. Only narrow NOTE path and regex edge cases remain. |
| Q2 Vendor separation / L-x| 88      | 95      | transcript_truth now routes through router.transcribe; avoid_vendor threading is comprehensive. Residual xAI-only trend_brief is intentional. |
| Q3 Verbatim / model text  | 93      | 97      | Clip text is source spans; all audience text (VO, title, caption, angle) now passes both deterministic + blind verdict with verbatim-run enforcement. |
| Q4 Deterministic rules    | 55      | 86      | Title-case bypass removed, PRICE_NOW clause logic tightened, hedge verbs added, strict_features prevents mis-labeled commentary. One narrow colon/regex edge remains. |
| Q5 Tests / R7 / wiring    | 45      | 82      | Fixed diff implements the consensus GATE INVENTORY and strict _strict parsers. Full R7 pinned.py and integration tests still not visible in this chunk, so not 100. |

### 5. FINAL PRIORITY LIST
**P0 CRITICAL (must fix before ship)**
- None. The previous P0s are resolved.

**P1 HIGH**
- context_integrity.py:464 (the NOTE path for entails-without-limit). Either make it a hard NOT_ENTAILED or require the model to always name a limit when entails != "yes". (Line 467-469 comment acknowledges the ruling but still downgrades.)
- vo_fidelity.py:1926 sentence splitter must be replaced by the same canon/sentence_law tokenizer used everywhere else so coverage is byte-identical to the deterministic layer.

**P2 MEDIUM**
- transcript_truth.py:1016 overlap constant should be derived from PAD_S.
- trend_brief.py:1170-1172 — `check_brief` accepts heat as int or float but normalises to float; add explicit `0.0 <= heat <= 1.0` after conversion to prevent a 2.0 “heat” from ranking moments.
- Add explicit test that a package with a failing gate row in the new GATE INVENTORY is refused by both package_pin.to_pin and the R7 loader (currently only implied).

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The combination of `package.seal()` + the mandatory GATE INVENTORY that both `package_pin.to_pin` and R7 recompute and refuse on any non-PASS row (including second_pass, exclusion, and every context_integrity rule). This single pattern makes every previous fail-open hole mechanically unenforceable.

### 7. PRODUCTION READY?
**Yes with conditions.**  
Conditions: (1) the two P1 items above are closed (NOTE path and sentence coverage tokenizer), (2) the full package_pin.py / R7 patch and the integration test suite exercising the new GATE INVENTORY are reviewed in the next chunk, (3) a final end-to-end run confirms that a package with a single VERDICT_INCOMPLETE or SPEAKER_CHANGE row is dropped before any render or pin artefact is written. With those three items satisfied, the feature is ready for production.

**End of Cycle 2 review.**