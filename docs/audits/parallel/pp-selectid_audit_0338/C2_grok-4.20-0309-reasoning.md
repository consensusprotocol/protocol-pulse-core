# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 27 s finish=stop usage in 11678 / out 1305 usd~0.091 (upper-bound price)

**P0: None**

**P1: None**

**P2:**
- `pipeline/transcript_truth.py:88` (gap when `j < 0` and `wav_start > 0`): still measures from WAV start (0.0) rather than `wav_start`. Matches ruling wording ("recogniser heard no word") and is exercised by the new test at line 169, but a missed word inside the window start would inflate the pause (same class as Cycle-1 documented uncertainty).
- `pipeline/transcript_truth.py:74` and `40` (`_canon_from`/`_canon_to` + list comp): `ci`/`co` can contain multiple candidates; `ci[0]` selects the earliest time match. A repeated identical canonical token inside the 0.6 s window could theoretically be skipped if an earlier non-matching 4-letter candidate appears first (no test case). The new spoken-number tests (lines 196-203) only exercise distinct tokens.
- `pipeline/transcript_truth.py:108` (fallback `max(0.0, start - PAD_BEFORE_S)`): correct after the signature change, but the magic `PAD_BEFORE_S` import path is fragile if the constant is ever moved.

**SHIP: yes with conditions**

---

**CYCLE 2 REVIEW**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   GLM's P1-1 (intervening unmatched word inside a measured gap) and Qwen's initial head/pause subsumption analysis. I had not fully traced that `ci[0]` selection + the `j = i-1` (then possible self-repair decrement) could skip a canon-mismatched word that still occupies time. The consensus refutation (words are time-sorted, self_repair is guarded before j=-1) is solid, but I missed the interaction. Grok's explicit verification of the `self_repair` guard at line 138 and the safe slicing bounds also escaped my Cycle 1 pass.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - **K1 (word-timing-only pause measurement)**: Fully agree. The code now explicitly implements the ruling's "recogniser heard no word" test; the acoustic check remains downstream in `check_cut_acoustics` / G16. The added `pause_ms` and verbose "why" strings (lines 94-99) make this transparent.  
   - **K2/K3 (self_repair guard, caller compatibility)**: Agree — both verified safe. The new test at line 174 exercises the exact self-repair + pause-before-repair path.  
   - **K4 (canon edge cases)**: Agree. `canon.canon_tokens` normalises "%" → "percent", "$5" → "5000000 dollars", and the OR-semantic (4-letter OR canon) cannot remove previously-accepted matches. The "26 %" vs "25 %" test (line 202) confirms a different number never matches.  
   - GLM P1-1: Disagree after data (all fixtures are time-sorted; no counter-example possible under current recogniser contract).  
   - Qwen P0 (dead `head` code): Disagree — the updated logic (lines 89-91) and test at line 166 clearly separate `head`, `pause`, and fallback "window starts at the clip" reasons. The Cycle-1 apparent inversion was resolved by the expanded `why` decision tree.

3. **NEW FINDINGS FROM THIS REVIEW**  
   Only the three P2 items above. The combined Cycle-1 analysis plus the FIXED diff revealed no previously unseen P0/P1. The new test class (lines 129-218) comprehensively exercises every acceptance path, the 4 s pad clamp, and the canonical run length. No off-by-one in `j+1` after self-repair (test line 178 confirms `pause_ms=800` is measured before the false-start). No widening of OUT rule, speaker checks, or `verify_segment` compare logic.

4. **REVISED SCORES**  
   | Subsystem              | Cycle 1     | Cycle 2          | Why changed |
   |------------------------|-------------|------------------|-------------|
   | IN-edge pause/head     | P1 (gap measurement) | P2 (documented uncertainty only) | Consensus + explicit ruling quote + new tests lowered severity |
   | Canonical edge match   | P2          | P2               | No change; repeated-token scenario still untested but low probability |
   | Window / audio_window  | P2          | P2               | Minor fallback fragility remains |
   | Overall defect risk    | Low         | Very low         | All Cycle-1 P1s either refuted or reduced by added test coverage and why-strings |

5. **FINAL PRIORITY LIST**  
   **P2 MEDIUM** (must address before long-term maintenance, not ship blockers):  
   - `transcript_truth.py:88` — document that gap measurement trusts the recogniser (already noted in ruling).  
   - `transcript_truth.py:74` — add a test case with two identical canonical tokens inside the 0.6 s window to guarantee `ci[0]` selects the correct instance.  
   - `transcript_truth.py:108` — replace magic fallback with an explicit constant lookup or require `wav_start`.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   The expanded `why` strings (lines 94-99) plus the dedicated `TestEdgesRulings38And39` class — they turn every future mismatch into an immediately debuggable artifact instead of a silent acceptance regression.

7. **PRODUCTION READY?**  
   **Yes with conditions.**  
   Conditions: (a) the three P2 items above are either fixed or explicitly documented as ruling-compliant; (b) the orchestrator's downstream acoustic check (`check_cut_acoustics` + G16) remains the final gate for any pause that passes on recogniser timing alone; (c) the new 4 s WAV files are confirmed cached and do not trigger extra recogniser cost in production. With those satisfied, the diff implements rulings 38 and 39 exactly, preserves fail-closed behavior, and adds substantial test surface. Ship.