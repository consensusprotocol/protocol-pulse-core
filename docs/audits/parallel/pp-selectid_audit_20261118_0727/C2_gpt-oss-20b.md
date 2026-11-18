# gpt-oss-20b (openai/gpt-oss-20b) 29 s finish=stop usage in 5363 / out 4984 usd_reported=0.000783 usd~0.091 (upper-bound price)

**1. What did the other models catch that I missed?**  
- **Gemma** identified the *upper‑bound blind spot*: shifting `a_now` back by `(hours‑12)` hours causes the ingest adapter to treat the current time as 14 h ago, so **any moments published in the last 14 h are excluded** from the query.  
- **GPT‑OSS‑20B** pointed out that `package_pin.WINDOW_H` is widened but never restored, that `a_now` can become a future time when `a.hours < base_h`, and that the test patches (`ledger_entries`, `stdout`) and the `seen[-1]` assertion are fragile.  
- **Qwen** noted a redundant `import tempfile`, the fragile `seen[-1]` check, and the confusing variable name `a_now`.

**2. Agreement / disagreement with each key finding**

| Model | Finding | Agree / Disagree | Why |
|-------|---------|------------------|-----|
| Gemma | P0 “blind spot” causes loss of recent moments | **Agree** (but intentional) | The exception is *designed* to widen the window for a *single* build that only processes older moments. The blind spot is therefore a deliberate side‑effect, not a bug. It should be documented, but it does not violate the rule set. |
| GPT‑OSS‑20B | P2 “WINDOW_H widened not restored” | **Agree** | The code sets `PP.WINDOW_H = a.hours` but never resets it. If the same interpreter runs multiple builds, the widened window will persist and affect later runs. |
| GPT‑OSS‑20B | P2 “a_now can be future when a.hours < base_h” | **Agree** | The arithmetic `now - timedelta(hours=a.hours - base_h)` assumes `a.hours ≥ base_h`. If a caller passes a smaller value (e.g., 8 h), `a_now` becomes *after* `now`, which could incorrectly advance the ingest clock. |
| GPT‑OSS‑20B | P3 “test patches ledger_entries” | **Agree** | Patching `ledger_entries` hides any side‑effects that might be introduced if the implementation changes. |
| GPT‑OSS‑20B | P3 “test patches stdout” | **Agree** | The patch suppresses output but does not restore it automatically, potentially leaking into other tests. |
| GPT‑OSS‑20B | P3 “tolerance 0.05 h” | **Agree** | The tolerance is generous but acceptable; tightening it would improve precision. |
| GPT‑OSS‑20B | P3 “custom rows raising Past” | **Agree** | The test only verifies the clock shift, not the actual filtering logic. |
| GPT‑OSS‑20B | P3 “calculation confusion” | **Agree** | Using `now` in the test calculation is confusing; clearer variable names would aid readability. |
| Qwen | P3 “redundant import tempfile” | **Agree** | Minor style issue. |
| Qwen | P3 “seen[-1] fragile” | **Agree** | If `LB.rows` is called twice, the test would silently validate the second call. |
| Qwen | P3 “variable name a_now” | **Agree** | The name could be clearer (`adapter_now` or `shifted_now`). |

**3. New findings from this combined review**

1. **Side‑effect of widening `PP.WINDOW_H`** – must be restored in a `finally` block.  
2. **Potential future‑time `a_now`** – guard against `a.hours < base_h`.  
3. **Test fragility** – patch `ledger_entries` and `stdout` in a context manager, assert call count, and use clearer variable names.  
4. **Documentation** – add a comment explaining the intentional blind spot and the single‑build exception.  
5. **Redundant import** – remove the duplicate `import tempfile` in the test.  

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Main code (`proof_ledger.py`) | 0 | **1** | Added P2 for `WINDOW_H` side‑effect and P2 for future‑time guard. |
| Tests (`test_ruling_137.py`) | 0 | **1** | Added P2 for test fragility (patching, call count). |
| Documentation | 0 | 0 | No new critical issues. |

**5. Final priority list**

| Severity | Finding | File:Line | Action |
|----------|---------|-----------|--------|
| **P1** | `PP.WINDOW_H` is widened but never restored | `proof_ledger.py:18‑21` | Wrap the widening in a `try…finally` that restores the original value. |
| **P1** | `a_now` can become a future time when `a.hours < base_h` | `proof_ledger.py:27‑30` | Add a guard that clamps `a_now` to `now` or raises an error if `a.hours < base_h`. |
| **P2** | Test patches (`ledger_entries`, `stdout`) are fragile | `test_ruling_137.py:76‑84` | Use context managers (`mock.patch.object`, `mock.patch`) and assert that `LB.rows` is called exactly once. |
| **P2** | Test uses `seen[-1]` without checking length | `test_ruling_137.py:80` | Add `self.assertEqual(len(seen), 1)` before accessing `seen[-1]`. |
| **P2** | Redundant `import tempfile` inside test | `test_ruling_137.py:56` | Remove the duplicate import. |
| **P2** | Confusing variable name `a_now` | `proof_ledger.py:27` | Rename to `adapter_now` or `shifted_now`. |
| **P2** | Documentation of intentional blind spot | `proof_ledger.py:30‑32` | Add a comment explaining why moments published in the last 14 h are excluded under the exception. |

**6. Single highest‑leverage change**

> **Add a `finally` block in `proof_ledger.main` that restores `PP.WINDOW_H` to its original value after the exception build completes.**  
> This prevents the widened window from leaking into subsequent builds or tests, which is a critical side‑effect that could silently alter pipeline behaviour.

**7. Production ready?**  
**Yes, with conditions** – after applying the P1 changes (restoring `PP.WINDOW_H` and guarding `a_now`) and the P2 test improvements, the code behaves as intended and the test suite is robust. The intentional blind spot should be documented to avoid future confusion.

**P1_OR_WORSE: 0**