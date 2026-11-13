# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 27 s finish=stop usage in 21890 / out 1675 usd~0.151 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0007 (speakers + batch)**  
**Review scope:** Only the provided C2_STEP.diff (speakers.py new, package_pin.py updates, proof_batch/ledger/ly.py callers, test updates). All Cycle 1 reviewer output and the implemented consensus fixes (K1–K3) were visible.

### 1. WHAT DID THEY CATCH THAT YOU MISSED?
- GLM P1-1 / P1-2: broad `except Exception` + `_json` fence stripping. My Cycle 1 focused on seal surface but missed that a non-dict JSON reply or markdown-wrapped reply would route to “unknown” only because of the broad catch; I did not verify the exact stripping logic.
- Qwen P1 (basis `_norm` substring) and P2 (memorial lines in `source_lines`). I overlooked how `_norm` + substring can accept reordered phrases and that description lines are accepted without participant-context filters.
- Grok P2 on intermediate JSON write before `attribute_package`. The proof_batch.py ordering (write → speakers → rewrite) was not flagged in my first pass.
- Consensus K1/K2: the exact gap between `check()` guarantees and `speaker_problems` / unmeasured pinning. I rated the original speaker_problems gap P3; Cycle 1 correctly elevated it.

### 2. WHERE DO YOU AGREE OR DISAGREE?
- **K1 (speaker_problems strengthening)**: Fully agree. The new `speaker_problems` (lines 69–82) now mirrors exactly what `check()` emits (named speaker must be in `people` with identical line + role). The 4 new must-fail tests close the public-API bypass.
- **K2 (unmeasured retry + pinning)**: Agree. Retrying once with seed=8 (lines 291–292) and keeping `measured=False` + “unknown” satisfies “nothing measured is never a pass” while still allowing the pin to form. The `STATE` marker comment is sufficient.
- **Basis / `_norm` (qwen P1)**: Partially agree. The substring-on-normalized-text can accept non-verbatim reorderings in theory, but `BASIS_MIN_WORDS=3`, the prompt’s “exact words” instruction, and the test suite (test_speakers.py:722–723, 727–731) make practical false positives low. The normalization is a pragmatic trade-off; tightening to contiguous token match would be nice but not required for ship.
- **Memorial / description lines (qwen P2)**: Agree it is a real P2. `source_lines` + `check` accept any description line that contains the name. No participant-context filter exists. Documented in the module docstring but not mitigated.
- GLM P1-3 (original gap on `people` membership): Agree it was a real gap; now fixed.

### 3. NEW FINDINGS FROM THIS REVIEW
**P2-1 — pipeline/speakers.py:224 (`_json`)**: Fence stripping only triggers on text that *starts with* ```` after `.strip()`. A model reply “Sure, here is the JSON:\n```json\n{…}\n```” never enters the fence path, `json.loads` fails on the whole string → `except Exception` → “unknown, measured=False”. Fails closed, but systematically discards valid fenced replies that have leading prose. Concrete: feed the canned fenced verdict wrapped in explanatory text → attribute returns unknown even though a correct speaker record was produced. (glm P1-2 partially saw this; the exact startswith condition was missed.)

**P2-2 — pipeline/speakers.py:256 (`nb in _norm(clip) or nb in _norm(around)`)**: Substring match after normalization accepts a basis that is a proper subsequence if extra normalized words exist between BASIS_MIN_WORDS tokens. Concrete input: basis = “when i wrote the price”, normalized clip contains “when i wrote technology the price of tomorrow” → match succeeds even though the exact phrase never appeared contiguously. Test suite does not exercise this reordering case. (Extends qwen’s false-positive observation.)

**P2-3 — tests/package/proof_batch.py:415 and proof_ly.py:521**: `attribute_package` is called *after* the build JSON is written (build:402–403) and *before* the second write (seal:416–417). A concurrent reader or crashed run sees a package without speaker records. The test fixtures now inject speakers via `spk()` helper, but the on-disk intermediate does not. Same pattern exists in proof_ledger.py:501. (Grok noted the ordering; the concurrent-read exposure was not explicitly called out.)

No P0 or P1 found in the fixed diff. All original Cycle 1 P1 scenarios are now prevented by the tightened `speaker_problems`, the retry logic, the seal inclusion, and the test battery.

### 4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Speaker validation & seal | 1 P1, 3 P2 | 0 P1, 3 P2 | K1 fixes closed the to_pin bypass; remaining issues are robustness / test coverage, not correctness blockers. |
| Exception / failure handling | 2 P1 | 0 P1, 1 P2 | Broad `except Exception` now explicitly documented and tested (test_speakers.py:768–773); still not ideal but fail-closed. |
| Batch build & delivered spans | 1 P2 | 1 P2 | No change; L-p and render-clock logic unchanged and correct. |
| Test coverage          | 2 P2 | 2 P2 | New tests cover the fixed shapes but not the new P2-1/P2-2 edge cases. |

### 5. FINAL PRIORITY LIST
**P2 (must address before long-term maintenance but not ship blocker):**
- speakers.py:224 – improve JSON extraction to handle leading/trailing prose (e.g. regex or LLM JSON mode). Concrete failure: valid fenced verdict with explanatory prefix → silent unknown.
- speakers.py:256 – tighten basis check to require word-sequence token match (split and consecutive) rather than substring on normalized string.
- proof_batch.py:402 vs 415 (and equivalent in ly/ledger) – write the final package with speakers in one pass or document the intermediate JSON limitation.
- speakers.py:208 – `source_lines` still accepts memorial / non-participant description lines (qwen P2); add optional participant-context keywords or document risk.

No P0 or P1 remain.

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The combined Cycle 1 feedback produced exactly the right change: `speaker_problems` (package_pin.py:69–82) now enforces the identical contract `check()` produces, closing the “record that check would never emit can still pin” gap while keeping the seal self-verifying.

### 7. PRODUCTION READY?
**Yes with conditions.**  
Conditions (all P2):
1. Add a more robust JSON extractor in `_json` (or switch the provider role to structured output) before any production batch that could receive non-compliant model prose.
2. Extend `test_speakers.py` with the reordering / leading-prose cases so the P2-1/P2-2 scenarios are explicitly regression-tested.
3. Document in the module docstring (speakers.py:133) that “people” includes any name appearing in description lines, even memorial context.

**SHIP: yes with conditions**

**Verdict rationale:** The diff implements the 00:05 ET Nov 13 order, satisfies all standing laws (L-m, L-j, L-p, L-v 3, sealed package), prevents wrong names from reaching a pin, and the test suite now exercises every malformed shape. The three P2 items are robustness improvements, not correctness or security defects. The code can ship.