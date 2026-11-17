# gpt-oss-20b (openai/gpt-oss-20b) 34 s finish=stop usage in 16746 / out 4811 usd_reported=0.001115 usd~0.122 (upper-bound price)

**1. WHAT THEY CATCHED THAT WE MISSED**  
- **Inventory function uses an undefined variable `med`** – the function signature passes `medl` but the body refers to `medley`, causing a `NameError`.  
- **Inventory fails to emit join‑sentences for soft‑only failures when the cached verdict is *not* measured (`medley[0] == False`)** – the `chain` variable is `None`, so `chain_sentences` is never called.  
- **`coherence_soft` does not enforce the VO‑point floor when a panel is present** – it only type‑checks the VO‑point, not its value.  
- **`lineup_soft` and `coherence_soft` assume the presence of `clip`/`vo_point` keys in the `floors` dict without guarding against missing keys** – a malformed verdict would raise a `KeyError`.  
- **`over_budget(ai)` check before the retry logic can silently suppress a retry when the per‑angle budget is exhausted** – the loop breaks before the `total >= lineups` check.  
- **Duplicate kept candidates are appended to `kept` without deduplication** – harmless but wasteful.  
- **Test‑suite assertion in `test_the_retry_takes_the_fewest_flags_and_the_budget_end_retries_too` is hard to read** – not a functional bug but a maintainability issue.

**2. WHERE WE AGREE / DISAGREE**  

| Finding | Source | Our Position | Severity | Comment |
|---------|--------|--------------|----------|---------|
| Inventory uses undefined `med` | GPT‑OSS | **Agree** – this is a real bug. | **P0** | Causes runtime failure. |
| Inventory missing join‑sentences when `medley[0]` is False | GPT‑OSS | **Agree** – test‑suite does not cover this, but the logic is wrong. | **P1** | Flags would be omitted. |
| `coherence_soft` missing VO‑point floor check | Qwen | **Agree** – potential logic gap. | **P1** | Could allow a low VO‑point to pass. |
| `lineup_soft`/`coherence_soft` assume `floors` keys exist | Qwen | **Agree** – could raise `KeyError`. | **P1** | Defensive coding needed. |
| `over_budget(ai)` before retry | Qwen | **Partially agree** – if `over_budget` is per‑angle, fine; if it’s the judged‑line‑up budget, it’s wrong. | **P2** | Clarify semantics. |
| Duplicate kept entries | Qwen | **Agree** – harmless but wasteful. | **P3** | Minor. |
| Test‑suite assertion readability | Qwen | **Agree** – readability issue. | **P3** | Minor. |
| `lineup_soft` treating question‑hook flagged join as soft | GPT‑OSS | **Disagree** – tests expect it to be soft; rule interpretation is ambiguous but current behaviour matches spec. | **P3** | No change. |
| `inventory` uses `med[0]` instead of `medley[0]` | GPT‑OSS | **Disagree** – `med[0]` is correct (tuple). | **P3** | No change. |
| `inventory` uses `med` variable | GPT‑OSS | **Agree** – same as first point. | **P0** | Already noted. |

**3. NEW FINDINGS FROM THIS REVIEW**  
- **`inventory` refers to `medley` instead of the passed `medl`** – the bug is the same as the undefined `med` issue but more explicit.  
- **`inventory` does not guard against missing `floors` keys** – could raise `KeyError` if a verdict omits them.  
- **`coherence_soft` does not check that the main VO‑point meets the floor when a panel is present** – could allow a low VO‑point to be accepted.  
- **`over_budget(ai)` may prematurely terminate the retry loop** – depends on the semantics of `over_budget`.  
- **`soft_joins_of` is used in several places but never defined before its first use** – actually defined earlier, so fine.  
- **`best_kept` uses `c["low"]` but `low` is only set when a candidate is appended to `kept`** – safe.  
- **`inventory` builds `coh_fl` using `coh["soft"]` but `coh` may not have a `soft` key** – guarded by `coh.get("soft")`.  

**4. REVISED SCORES**  

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `inventory` | 0 | **4** | Undefined variable, missing join‑sentences, missing VO‑point check, missing floor guard. |
| `lineup_soft` | 0 | 0 | Tests confirm behaviour; no change. |
| `coherence_soft` | 0 | **1** | Missing VO‑point floor check. |
| `over_budget` logic | 0 | **1** | Potential premature break. |
| `kept` deduplication | 0 | 0 | Minor, no functional impact. |
| Test‑suite readability | 0 | 0 | Minor. |

**P1_OR_WORSE: 4** (1 P0 + 3 P1)

**5. FINAL PRIORITY LIST**  

| Priority | Issue | File:Line | Action |
|----------|-------|-----------|--------|
| **P0** | `inventory` refers to undefined `med` / `medley` variable | `pipeline/package.py` line 235‑238 | Rename `medl` to `medley` in signature and body; add guard to use passed tuple. |
| **P0** | `inventory` fails to emit join‑sentences when cached verdict is not measured | `pipeline/package.py` line 236‑238 | Add `chain_sentences` call even when `medley[0]` is False, or explicitly include soft‑join sentences. |
| **P1** | `coherence_soft` does not enforce VO‑point floor when a panel is present | `pipeline/package.py` line 64‑70 | Add `coh["vo_point"] >= fl["vo_point"]` check when `ans` is non‑empty. |
| **P1** | `lineup_soft` / `coherence_soft` assume `floors` keys exist | `pipeline/package.py` line 37, 63, 67, 71 | Guard accesses with `.get()` and default to standard floors; return `None` if missing. |
| **P1** | `over_budget(ai)` may suppress retry prematurely | `pipeline/package.py` line 140‑144 | Clarify semantics; if `over_budget` is per‑angle, move retry check before it or add exception for cached retry. |
| **P2** | Duplicate kept entries | `pipeline/package.py` line 173‑179 | Add check `if key not in {k["key"] for k in kept}` before appending. |
| **P3** | Test‑suite assertion readability | `tests/package/test_ruling_137.py` line 427‑429 | Split into two assertions for clarity. |
| **P3** | Minor documentation mismatches (e.g., `med_fl` comment) | `pipeline/package.py` line 236‑238 | Update comments. |

**6. SINGLE HIGHEST‑LEVERAGE CHANGE**  
Fix the `inventory` function to use the passed `medl` tuple correctly and to emit join‑sentences even when the cached verdict is not measured – this eliminates a runtime crash and ensures all soft‑join flags are reported.

**7. PRODUCTION READY?**  
**No** – the undefined variable in `inventory` will cause a crash, and missing VO‑point floor checks could allow low‑quality content to be accepted. All P0 issues must be resolved before shipping. Once fixed, the remaining P1/P2/P3 issues can be addressed in a subsequent patch.