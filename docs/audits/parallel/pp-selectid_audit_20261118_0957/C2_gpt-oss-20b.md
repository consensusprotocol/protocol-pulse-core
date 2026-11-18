# gpt-oss-20b (openai/gpt-oss-20b) 25 s finish=stop usage in 6255 / out 4184 usd_reported=0.000711 usd~0.082 (upper-bound price)

**1. What the other models caught that I missed**

| Finding | Source | What I missed |
|---------|--------|---------------|
| `approved_tokens` can be mis‑used (non‑canonical, mismatched to `approved`) | GPT‑OSS‑20B | I didn’t note that the new optional argument could be passed incorrectly by future developers. |
| Backward‑compatibility guard / signature change | GPT‑OSS‑20B | I didn’t explicitly mention that the signature change could confuse callers or tooling. |
| Inconsistent `texts` tuple when `approved_tokens` is supplied | GPT‑OSS‑20B | I didn’t point out that `texts = (spoken, approved)` is still built even when the token list is used. |
| `autojunk` flag difference between the two diff paths | QWEN3.8‑27B | I didn’t note that `SequenceMatcher` is called with `autojunk=False` only in the new branch, which could produce different opcodes for very long sequences. |
| No guard that `approved_tokens` is a list of strings | QWEN3.8‑27B | I didn’t mention that the function accepts any iterable, which could silently break if a non‑string element is passed. |
| Docstring missing the invariant that `approved_tokens` must be the canon tokens of `approved` | QWEN3.8‑27B | I didn’t add a clear pre‑condition in the docstring. |

**2. Agreement / disagreement**

| Finding | Agreement | Why |
|---------|-----------|-----|
| Mis‑use of `approved_tokens` | **Agree** | It is a real risk for future maintainers. |
| Backward‑compatibility guard | **Agree** | The signature change is harmless now but should be documented. |
| Inconsistent `texts` tuple | **Agree** | The tuple is still used for the critical‑word test; if callers pass mismatched data it could mis‑report. |
| `autojunk` flag difference | **Partially agree** | In practice transcripts are <200 tokens, so the difference is unlikely to surface, but documenting the invariant is prudent. |
| No guard on token type | **Agree** | Adding a type hint or runtime check would make the contract explicit. |
| Docstring missing invariant | **Agree** | A single sentence would close the gap. |
| No new logic errors / law violations | **Agree** | All other reviewers found none. |

**3. New findings from this review**

* The change introduces a **new public API surface** (`approved_tokens` argument). Even though only `class_131` currently uses it, the signature change can affect tooling (type checkers, IDE autocompletion) and future callers.  
* The **critical‑word test** still uses the joined string (`approved`), but the token comparison now uses the supplied list. If a caller mistakenly passes a token list that does not correspond to the string, the test will still run on the wrong text, potentially hiding a real difference.  
* The **SequenceMatcher `autojunk` flag** is only set in the new branch. If `diff()` uses the default `autojunk=True`, the two paths could diverge for very long sequences (theoretically >200 tokens). Adding a comment or a shared helper would make the invariant explicit.  
* The **type of `approved_tokens`** is not enforced. A generator or a set would be silently accepted, leading to subtle bugs if the caller is not careful.  

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `pipeline/attest.py` (class_84) | 0 | 0 | No functional defects; only style/guard improvements needed. |
| `pipeline/attest.py` (class_131) | 0 | 0 | No change. |
| `tests/package/test_lock_precheck.py` | 0 | 0 | Tests cover the new behaviour. |

**5. Final priority list**

| Priority | Item | File:Line | Notes |
|----------|------|-----------|-------|
| **P0** | None | – | No critical defects. |
| **P1** | None | – | No gate‑passing bugs. |
| **P2** | Add type hint and guard for `approved_tokens` | `pipeline/attest.py` line 9‑10 | `def class_84(spoken: str, approved: str, approved_tokens: Sequence[str] | None = None):` |
| **P2** | Clarify invariant in docstring | `pipeline/attest.py` lines 11‑23 | Add sentence: “`approved_tokens` must be the canon tokens of `approved`.” |
| **P2** | Add comment about `autojunk=False` | `pipeline/attest.py` line 30 | Explain why `autojunk` is set and that `diff()` should use the same setting. |
| **P2** | Document that `texts` tuple remains unchanged | `pipeline/attest.py` line 24 | Note that the critical‑word test still uses the joined string. |
| **P3** | Optional: add runtime check that `approved_tokens` is a list of strings | `pipeline/attest.py` line 28‑30 | Not strictly required but improves safety. |

**6. The single highest‑leverage change**

Add a clear type hint and a short invariant sentence to the `class_84` docstring so that future developers understand that `approved_tokens` must be the canon tokens of `approved` and that the function will not re‑tokenise the joined string.

**7. Production ready?**

Yes, with the above style/guard improvements. The functional behaviour is correct, all tests pass, and no law violations were introduced. The only remaining work is to add the suggested documentation and type hints, which are non‑blocking.

**P1_OR_WORSE: 0**