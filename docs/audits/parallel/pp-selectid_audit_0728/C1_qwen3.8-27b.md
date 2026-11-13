# qwen3.8-27b (qwen/qwen3.8-27b) 24 s finish=stop usage in 5989 / out 802 usd~0.030 (upper-bound price)

# Audit: pp-selectid C1_STEP.diff

## Verification of the core change

The diff tightens two checks from "first canonical token is in TRIM_WORDS" to "exactly one canonical token, and it is in TRIM_WORDS." This aligns the branch's `trim_variant` (package.py) and `trim_problems` (package_pin.py) with the integrator's `pinned.validate_schema`, which requires `len(tok) != 1 or tok[0] not in L.TRIMMABLE_LEADING` to refuse.

**Does it accept exactly what the render accepts?**
- Render accepts: `len(canon.canon_tokens(tl)) == 1` AND `tok[0] in TRIMMABLE_LEADING`.
- Branch now accepts: `len(canon.canon_tokens(w)) == 1` AND `tok[0] in TRIM_WORDS`.
- These are structurally identical (assuming `TRIM_WORDS == TRIMMABLE_LEADING`, which the background confirms: "the six words"). Punctuation is stripped by `canon.canon_tokens` (e.g., `"But,"` → `['but']`), so a single word with trailing punctuation still yields one token and passes. **Match confirmed.**

**Does it refuse anything that was valid at the render?**
- Previously valid at render = exactly one canonical token in the six words. The new branch check accepts exactly that set. Nothing valid at the render is newly refused. **Confirmed.**

**Does it now refuse things that previously passed the branch but were invalid at the render?**
- `"But so"` → `['but', 'so']` (2 tokens): previously passed branch (`[:1]` → `['but']`), now refused. Render would have refused it. **Correctly closed.**
- `"and/or"` → `['and', 'or']` (2 tokens): same. **Correctly closed.**
- `"Because"` → `['because']` (1 token, not in TRIM_WORDS): refused both before and after. Unchanged. **Correct.**

**Nothing else changed?**
- The diff touches only the two `canon.canon_tokens` call sites and their guard conditions, plus the error message string in `package_pin.py` (cosmetic: "is not one of" → "must be ONE word, one of"). The `MIN_STATEMENT_TOKENS` check in `trim_variant` (line 14) is untouched. The `num` lambda and `untrimmed_start` validation in `trim_problems` (lines 30–32) are untouched. No other files, no logic changes beyond the token-count guard. **Confirmed.**

## Findings

**P0:** None.

**P1:** None.

**P2:**
- `package_pin.py:29` — The error message now says "must be ONE word, one of …" but the check is on canonical tokens, not raw words. A string like `"But, so"` (two words, two tokens) would produce the message "must be ONE word," which is accurate in spirit. However, a hypothetical single-word string that canon expands to two tokens (none known in the six-word set, but canon rules could theoretically do this for a non-TRIM word) would produce a slightly misleading message. This is cosmetic and does not affect correctness. No action required.

## SHIP: yes

The change is minimal, correctly closes the gap between the branch's checks and the render's `validate_schema`, introduces no new rejections of render-valid pins, and the tests cover the two concrete failure cases (`"But so"`, `"and/or"`) plus the existing valid/invalid cases. All other suites pass. No law violations, no scope creep, no new dependencies.