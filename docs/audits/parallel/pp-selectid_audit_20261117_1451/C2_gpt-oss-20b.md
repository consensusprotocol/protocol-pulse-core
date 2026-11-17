# gpt-oss-20b (openai/gpt-oss-20b) 22 s finish=stop usage in 9973 / out 3429 usd_reported=0.000733 usd~0.081 (upper-bound price)

**1. WHAT THEY CATCHED THAT I MISSED**

| # | Finding | Severity | What I missed |
|---|---------|----------|---------------|
| 1 | `_FORM_END` regex over‑strips any trailing `s`/`'` (e.g. “class” → “clas”) | [P2] | I didn’t note that the regex is too permissive and could mis‑classify non‑plural/possessive tokens as word‑form pairs. |
| 2 | `attest.class_131` guard may suppress critical‑token handling when a word‑form pair is present | [P3] | I assumed the guard was correct; the other model flagged a potential logic flaw, but on closer inspection the guard is actually correct because the entire slice is the word‑form pair. |
| 3 | `_NUM_HYPHEN` does not cover “24 - 7” (space after hyphen) | [P3] | I noted it but didn’t explicitly state it’s by design; the rule only targets “24 -7”. |
| 4 | Bare apostrophe (`'`) in `_FORM_END` matches a non‑possessive token | [P3] | I didn’t mention that the regex also matches a lone `'`, but the `bool(a)` guard prevents it from being a true word‑form pair. |

**2. WHERE I AGREE / DISAGREE**

| # | Model | Agreement | Reason |
|---|-------|-----------|--------|
| 1 | Gemma | **Agree** | The regex is indeed too broad; a stricter pattern would avoid false positives. |
| 2 | GPT‑OSS‑20B | **Agree** on the guard issue, **Disagree** on its severity. The guard is correct because the entire slice is the word‑form pair; no other critical tokens can exist outside it. |
| 3 | Qwen | **Agree** on the “24 - 7” note; it’s outside the rule’s scope. |
| 4 | Claude | **Agree** on the regex and the guard; both are correct but the regex could be tightened. |

**3. NEW FINDINGS FROM THIS REVIEW**

* The only real defect is the overly permissive `_FORM_END` regex.  
* No hidden P0/P1 defects were uncovered.  
* The guard logic in `attest.class_131` is sound; the concern was a false alarm.

**4. REVISED SCORES**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| canon.py | 0 | 0 | Only a P2 issue (regex) – no P0/P1. |
| attest.py | 0 | 0 | Guard logic is correct; no defect. |
| lock_precheck.py | 0 | 0 | No new issues. |
| tests | 0 | 0 | Tests cover new logic; no failures. |

**5. FINAL PRIORITY LIST**

| Severity | Item | File:Line | Action |
|----------|------|-----------|--------|
| **P2** | Over‑broad `_FORM_END` regex may mis‑classify non‑plural/possessive tokens as word‑form pairs. | `pipeline/canon.py:46‑61` | Tighten the regex to match only true possessive or plural endings (`(?:'s|s'|s|')$`) and add a length guard (`len(t) > 1`). |
| **P3** | Comment indentation in `lock_precheck.py` (line 76‑78) | `pipeline/lock_precheck.py:76‑78` | Align comment with surrounding style (optional cosmetic). |
| **P3** | `_NUM_HYPHEN` not covering “24 - 7” | `pipeline/canon.py:33` | Document that this is intentional; no code change needed. |

**6. SINGLE HIGHEST‑LEVERAGE CHANGE**

*Refine the `_FORM_END` regex in `canon.py` to match only genuine possessive or plural endings, preventing accidental word‑form exemptions for tokens like “class” or “glass”.*

**7. PRODUCTION READY?**

**Yes, with conditions.**  
- Apply the regex fix in `canon.py` (P2).  
- Verify that the change does not break existing tests (the new `TestRuling142` covers word‑form logic).  
- No P0/P1 defects remain; all tests pass.  

**P1_OR_WORSE: 0**