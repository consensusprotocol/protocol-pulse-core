**CYCLE 2 REVIEW — pulse-sentence-law**

### 1. What did they catch that I missed?
- Gemini correctly highlighted the state-machine robustness in `canon.py` (the `owed` variable handling for spoken "dollars") and the precise fix in `gate_g3b` (reading from `selection_lock` text rather than an isolated token). I noted the G3b change but under-emphasized how critical the multi-word context was.
- All three models converged on verifying *every* caller of `word_overlap` / `_fuzzy_word_overlap`, not just the function itself. I flagged the empty-reference fix but did not stress downstream call-site verification as strongly.
- GPT-4o and Gemini both noted that the `_key` tolerance for dropping "dollars/percent" is narrow and could break if ASR emits other units.

### 2. Where do I agree or disagree?
**Agree:**
- U1 (`sys.path.insert` hygiene) — unanimous and correct. This is the clearest remaining defect.
- U2 (empty-reference `word_overlap` returning 0.0) — the fix is present; call-site verification is still needed.
- M1 (G3b last-word context from `selection_lock`) — the fix is in the diff and materially improves L-g compliance.

**Partially agree:**
- The `_key` fragility (punctuation.py:124-125) is real but low-risk given current ASR behavior. It is not a blocker.

**Disagree:**
- None of the models identified any functional regression or law violation. The code is sound on correctness and law compliance.

### 3. New findings from this review
The `_canon()` helper in `qa_gates.py:282-287` performs a `sys.path.insert` on *every* call (it is not guarded by a module-level flag in all paths). This is worse than the four static inserts in `gates.py` because it can execute thousands of times per clip. No model caught the repeated execution risk in Cycle 1.

### 4. Revised scores

| Subsystem            | Cycle 1 | Cycle 2 | Why changed |
|----------------------|---------|---------|-------------|
| Correctness          | 9/10    | 9/10    | No change |
| Law Compliance       | 9/10    | 9/10    | No change |
| Test Quality         | 9/10    | 9/10    | No change |
| Security / Robustness| 7/10    | 6/10    | Repeated `sys.path.insert` inside `_canon()` is worse than initially assessed |
| Overall Readiness    | 9/10    | 8/10    | Import hygiene is the only remaining material issue |

### 5. Final priority list

**P0 CRITICAL**
- `gates.py:73,92` and `qa_gates.py:218,284-286` — replace every `sys.path.insert` with proper package-relative imports or a single bootstrap `importlib` call at process start.

**P1 HIGH**
- `qa_gates.py` and all callers of `word_overlap` / `_fuzzy_word_overlap` — add explicit checks that a 0.0 return produces a FAIL disposition (no short-circuit swallowing).

**P2 MEDIUM**
- `punctuation.py:124-125` (`_key`) — consider making the "dollars/percent after number" rule more general or moving it into `canon.py` if other units appear.

### 6. The single highest-leverage change
Replace every dynamic `sys.path.insert` with proper imports so the canonicaliser is loaded once at startup instead of polluting `sys.path` on every gate or comparison.

### 7. Production ready?
**Yes with conditions.**  
Ship once the four `sys.path.insert` sites (and the repeated `_canon()` helper) are removed. All functional, law-compliance, and test requirements are already met.