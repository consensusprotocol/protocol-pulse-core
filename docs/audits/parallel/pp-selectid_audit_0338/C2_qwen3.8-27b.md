# qwen3.8-27b (qwen/qwen3.8-27b) 72 s finish=stop usage in 12506 / out 2559 usd~0.076 (upper-bound price)

# CYCLE 2 — FINAL AUDIT: pp-selectid-0338

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (implicitly, as the "you" in the prompt) did not produce a distinct output block, but the consensus and other models covered the ground. Reviewing their findings against the code:

*   **GLM-5.3-FLASH** correctly identified the risk of "unmatched interlopers" in the gap (P1-1) and the acoustic vs. word-timing distinction (P1-3). It was cautious, flagging them as conditions rather than blockers.
*   **GROK-4.20** was the most concise, correctly identifying that the canonical match logic is sound and that the tests cover the critical boundaries. It missed the subtle nuance about the `head` condition being a distinct path from `pause` (which Qwen analyzed in depth).
*   **QWEN3.8-27B** performed the deepest logical trace of the `head` vs `pause` vs `ends` logic. It correctly concluded that `head` is not dead code and that the logic is compliant with Ruling 38's specific wording ("holds no speech" at file head, vs "measured pause" elsewhere).

**What I missed (or would have missed without their input):**
*   The explicit verification that `self_repair` cannot trigger when `j = -1` (K2 in consensus). I would have needed to trace `self_repair`'s guard clause `if not 0 <= i < len(words) - 1: return False` to confirm this.
*   The confirmation that `canon_tokens` handles bare symbols like `%` and `$` safely (K4). I would have needed to inspect the `canon` module's behavior, which is not in the diff.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM P1-1 (Unmatched word in gap):** **AGREE** it is a theoretical risk, but **DISAGREE** it is a P1 defect. The consensus (K1) correctly notes that the ruling defines the pause based on the *recogniser's* output. If the recogniser missed a word, it is not in `ws`, so it is not "speech" in the context of the independent check. The acoustic check is a separate stage (G16). This is a **condition**, not a bug.
*   **GLM P1-3 (Acoustic vs Word Timing):** **AGREE**. The code measures word timing. The ruling says "measured pause... with no speech." In the context of `transcript_truth.py`, "speech" is defined by the recogniser's word list. This is compliant.
*   **QWEN P0 #1 (Head logic):** **DISAGREE** it is a P0. Qwen's own analysis concludes it is compliant. The `head` condition (`wav_start <= 0.0` and `prev is None`) is a distinct, valid path for the "file's first spoken word" case. It does not subsume `pause`; it is an alternative acceptance criterion.
*   **GROK P2 (Canonical match):** **AGREE**. The logic `c_first is not None and _canon_from(ws, i) == c_first` is safe. `_canon_from` returns the *first* token of the canonicalized run. If the clip starts with "25", and the recogniser says "Twenty-five percent", `canon_tokens("Twenty-five percent...")` -> `['25', 'percent', ...]`. `c[0]` is `'25'`. Match. If the recogniser says "Twenty-six", `c[0]` is `'26'`. No match.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1: `t_open` calculation when `j = -1` (No previous word)**
*   **File:** `pipeline/transcript_truth.py:87`
*   **Scenario:** If `prev is None` (no word before the clip in the window), `j` is `-1`.
*   **Code:** `t_open = float(ws[j + 1]["start"])` -> `ws[0]["start"]`.
*   **Analysis:** This is correct. `ws[0]` is the first word in the window. If `prev is None`, it means the clip's opening word *is* the first word in the window (or the first word after a gap). Wait, let's trace carefully.
    *   `ci` finds the index `i` of the clip's opening word in `ws`.
    *   `j = i - 1`.
    *   If `i = 0`, `j = -1`. `prev = None`.
    *   `t_open = ws[0]["start"]`. This is the start time of the clip's opening word.
    *   `gap = t_open - 0.0` (since `j < 0`).
    *   This measures the time from the start of the WAV file to the first word.
    *   This is correct for the `head` case (file head) and the `pause` case (window starts mid-pause).
    *   **Verdict:** No defect.

**P2-2: `self_repair` interaction with `t_open`**
*   **File:** `pipeline/transcript_truth.py:80-87`
*   **Scenario:** A self-repair occurs. `j` is decremented.
*   **Code:**
    ```python
    if self_repair(ws, j, first):
        repair, j = ws[j]["text"], j - 1
    prev = ws[j]["text"] if j >= 0 else None
    t_open = float(ws[j + 1]["start"])
    ```
*   **Analysis:**
    *   Original `i` is the clip's first word.
    *   `j = i - 1`.
    *   `self_repair` checks if `ws[j]` is a false start. If so, it returns `True`.
    *   `j` becomes `j - 1` (the word *before* the false start).
    *   `t_open = ws[j + 1]["start"]`. Since `j` was decremented, `j + 1` is the *false start* word.
    *   **Wait.** The comment says `# the clip's opening word (its self-repair, when there is one)`.
    *   If there is a self-repair, the "opening word" of the *sentence* is the false start. The pause should be measured before the false start.
    *   `gap = t_open - (end of ws[j])`.
    *   `ws[j]` is the word before the false start.
    *   `t_open` is the start of the false start.
    *   This correctly measures the pause before the false start.
    *   **Verdict:** Correct.

**P2-3: `canon_tokens` on empty string**
*   **File:** `pipeline/transcript_truth.py:36`
*   **Code:** `c = canon.canon_tokens(" ".join(...))`
*   **Scenario:** If `ws[i:i+CANON_RUN]` contains words with empty text (e.g., `{"text": ""}`).
*   **Analysis:** `w.get("text") or ""` handles this. If all are empty, `canon_tokens("")` likely returns `[]`. `c[0] if c else None` handles this.
*   **Verdict:** Safe.

**P2-4: `verify_segment` fallback `wav_start`**
*   **File:** `pipeline/transcript_truth.py:109`
*   **Code:** `off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S))`
*   **Analysis:** If `wav_start` is `None` (shouldn't happen with `audio_window`), it falls back to `start - 4.0`. This is consistent with the new pad.
*   **Verdict:** Correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **IN Edge Logic** | 8/10 | 9/10 | Confirmed `head`/`pause`/`ends` logic is sound and compliant with Ruling 38. |
| **OUT Edge Logic** | 9/10 | 9/10 | Canonical match is correct. No changes to OUT logic other than matching. |
| **Window/Padding** | 8/10 | 9/10 | `PAD_BEFORE_S` is correctly applied in `audio_window` and `verify_segment`. |
| **Tests** | 8/10 | 9/10 | Tests cover the critical boundaries (700ms, file head, canonical numbers). |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`pipeline/transcript_truth.py:88`**: The `gap` calculation relies on `ws[j].get("end")`. If a word has `start` but no `end`, it falls back to `start`. This is standard, but worth noting that the pause is measured to the *start* of the previous word if `end` is missing, which might slightly overestimate the pause. (Low risk, standard behavior).
2.  **`pipeline/transcript_truth.py:74`**: The canonical match `_canon_from(ws, i) == c_first` compares the *first* token of the canonicalized run. If the clip's first word is a number, and the recogniser's run starts with a different number, it fails. This is correct. However, if the clip's first word is "Bitcoin" and the recogniser says "Bit- coin", `canon_tokens` might not merge them (as noted in K4). This is a false negative, not a false positive. Acceptable.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The expansion of `PAD_BEFORE_S` to 4.0 seconds is the highest-leverage change, as it directly addresses the measured funnel loss (3 of 5 stage-3 losses) by ensuring the recogniser hears the preceding sentence context, enabling the 700ms pause and file-head rules to function as intended.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Acoustic Verification:** The orchestrator must ensure that the `check_cut_acoustics` stage (G16) is run on all clips accepted by `transcript_truth.py` to confirm the "no speech" in the 700ms pause is acoustically valid (i.e., not just a recogniser miss). The code in `transcript_truth.py` is compliant with the *word-timing* definition of the ruling, but the *acoustic* intent requires the downstream check.
2.  **Canonicalizer Robustness:** Monitor for false negatives in the canonical match (e.g., hyphenated words like "Bit- coin"). If this becomes a significant source of failures, consider enhancing `canon_tokens` to handle hyphen splits. This is not a blocker for this diff, as it is a pre-existing limitation of the canonicalizer, not a regression.