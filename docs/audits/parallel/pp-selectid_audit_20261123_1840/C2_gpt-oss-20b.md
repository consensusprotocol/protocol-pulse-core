# gpt-oss-20b (openai/gpt-oss-20b) 19 s finish=stop usage in 10695 / out 2941 usd_reported=0.000478 usd~0.076 (upper-bound price)

**1. What did the other models catch that I missed?**  
- **P2 – Sponsor‑row `n` is wrong** – the `n` field reports `len(exc)` (all moments that hit the exclusion screen) instead of the number of flagged moments that are kept.  
- **P3 – Fragile string‑matching in `ad_before_soft`** – the function filters `ad_read` entries by `v.endswith("in the sentence before it")`.  Any change to the wording of the marker string would silently break the soft‑gate logic.  
- **P3 – In‑place mutation of `ms` in `ad_before_soft`** – the helper pops and re‑sets `ad_before` on the moment dicts it receives.  The signature does not document this side‑effect, so callers that reuse the same list of moments could see stale marks.  
- **P3 – Gate‑problems loop now checks every FLAGGED row outside the required set** – while the logic is correct, it adds a new code path that could surface a false‑positive if a future soft‑gate is added without flags.  

**2. Agreement / disagreement with each key finding**

| Model | Finding | My stance | Reason |
|-------|---------|-----------|--------|
| Gemma | “All logic correct, no defects.” | **Disagree** – the sponsor‑row `n` bug is a functional reporting issue. | The `n` field is part of the sealed gate report; a mismatch can mislead reviewers. |
| GPT‑OSS | Same as Gemma | **Disagree** – same reason. |
| Qwen | **P2 – sponsor‑row `n` wrong** | **Agree** – this is a real defect that should be fixed before shipping. |
| Qwen | **P3 – fragile string matching** | **Agree** – not a current bug but a maintenance‑risk that should be addressed. |
| Qwen | **P3 – mutation side‑effect** | **Agree** – side‑effects are undesirable; a copy‑on‑write approach would be cleaner. |
| Qwen | **P3 – gate‑problems loop** | **Agree** – the logic is sound, but the added check could surface false positives if new soft gates are added without flags. |

**3. New findings from this review**

- The **`n` field in the sponsor gate row** is inconsistent with the other FLAGGED rows; it should count only flagged, kept moments.  
- The **`ad_before_soft` helper’s reliance on a hard‑coded suffix** makes the soft‑gate fragile to future changes in the marker string.  
- The **in‑place mutation of the moment list** in `ad_before_soft` is a hidden side‑effect that could cause subtle bugs if the same list is reused.  
- The **gate‑problems loop now inspects all FLAGGED rows outside the required set**; while correct, it introduces a new code path that could surface false positives if a future soft‑gate is added without flags.

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `pipeline/package.py` – `ad_before_soft` | P0 | P3 | Side‑effect and fragile string match. |
| `pipeline/package.py` – `inventory` sponsor row | P0 | P2 | `n` field mis‑counts. |
| `pipeline/package_pin.py` – `gate_problems` | P0 | P3 | New loop adds a potential false‑positive path. |
| Overall | P1_OR_WORSE: 0 | P1_OR_WORSE: 0 | No new P0/P1 defects found. |

**5. Final priority list**

| Priority | Issue | File:Line | Action |
|----------|-------|-----------|--------|
| **P2** | Sponsor‑row `n` reports total exclusions instead of flagged kept moments | `pipeline/package.py:1336` | Change `n` to `len([e for e in exc.values() if e.get("ad_before") and e.get("verdict") == "keep"])`. |
| **P3** | `ad_before_soft` uses fragile `endswith` string match | `pipeline/package.py:55` | Replace with a structured return from `ad_read_marker` or a sentinel value; e.g., `if soft and v == "in the sentence before it"`. |
| **P3** | `ad_before_soft` mutates caller’s moment list | `pipeline/package.py:53‑58` | Make a copy of `ms` or return a new list; document that the function does not mutate input. |
| **P3** | New `gate_problems` loop may flag legitimate rows if soft‑gate added without flags | `pipeline/package_pin.py:159‑162` | Add a comment clarifying that only soft gates with flags are allowed; consider adding a guard that skips rows that are known soft gates. |

**6. The single highest‑leverage change**  
Fix the sponsor‑row `n` field to count only flagged, kept moments; this eliminates a misleading report that could cause human reviewers to misinterpret the gate status.

**7. Production ready?**  
**Yes, with conditions** – the remaining P3 items are maintenance‑risk issues that should be addressed before shipping to avoid future regressions. Once the `n` field bug is fixed and the fragile string match / mutation side‑effect are resolved, the code meets all functional requirements.  

**P1_OR_WORSE: 0**