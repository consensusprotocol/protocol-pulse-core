# gemma-4-31b-it (google/gemma-4-31b-it) 277 s finish=stop usage in 7965 / out 2974 usd_reported=0.000616 usd~0.069 (upper-bound price)

The code implements a surgical fix for a tokenization bug in `pipeline/attest.py` where the "spaced-thousands" rule in `canon.py` caused false-positive "holds" during the render lock pre-check.

### Analysis

**1. The Defect**
The issue occurred in `class_131` when it joined a list of canon tokens (the merged reading) into a string and then passed that string to `class_84`. `class_84` would then re-tokenize that string. Because `canon.canon_tokens` treats a digit, a space, and three digits as a single number (e.g., `"7 365"` $\rightarrow$ `["7365"]`), the tokens `['24', '7', '365']` became `['24', '7365']`. This created a perceived number difference against the spoken text `['24', '7', '365']`, triggering a "hold" under Law L-v 2 (implied by the "number difference" rule in `class_84`).

**2. The Fix**
The modification to `class_84` introduces an optional `approved_tokens` parameter. 
- If provided, it bypasses the `diff(spoken, approved)` call (which performs the problematic re-tokenization of the `approved` string).
- Instead, it uses the provided tokens directly and computes the `SequenceMatcher` opcodes.
- `class_131` now passes the `merged` token list directly to `class_84`.

**3. Law Compliance**
- **L-k (One Canonical Form):** The fix maintains strict adherence to `canon.py`. It uses `canon.canon_tokens(spoken)` for the spoken side and preserves the existing canon tokens for the approved side, ensuring no ad-hoc normalization is introduced.
- **Law 20 / M2:** This is not a threshold change to force a pass; it is a correction of a logic error (a false positive "hold") that was incorrectly identifying a difference where none existed in the canonical tokens.
- **M12 (Fail Closed):** The logic still "holds" if a genuine difference (e.g., `365` vs `366`) is detected, as verified by the new tests.

**4. Verification of Questions**
- **Genuine differences:** A genuine number, name, or negation difference will still result in a non-equal opcode. Since these are not in the `FILLERS` list or categorized as "function words," they will still return `class: None` and cause a "hold."
- **Critical-word test:** The `texts = (spoken, approved)` assignment remains unchanged, ensuring that the strings used for logging and the critical-word test remain identical to the previous version.
- **Side effects:** The change is isolated to `class_84` and `class_131`. Other callers of `class_84` do not pass `approved_tokens`, so their behavior remains unchanged.

### Findings

No violations of the Governing Laws or technical defects were found. The implementation is correct and the tests are comprehensive.

P1_OR_WORSE: 0