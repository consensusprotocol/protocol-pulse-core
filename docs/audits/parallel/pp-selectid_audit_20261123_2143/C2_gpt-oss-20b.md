# gpt-oss-20b (openai/gpt-oss-20b) 26 s finish=stop usage in 10329 / out 4002 usd_reported=0.000566 usd~0.091 (upper-bound price)

**1. What the other models caught that I missed**

| Finding | Source | What I missed |
|---------|--------|---------------|
| **F1 – `fallback_fields` crashes on an empty channel list** | GLM‑5.3‑FLASH | I did not notice the `chans[0]` access when `chans` is empty. The patch added a guard, but I didn’t flag it. |
| **F2 – `fallback_subject` duplicates “Bitcoin” when the best run is “Bitcoin”** | None of the models flagged it | The code always returns `f"{best[0]} and Bitcoin"`. If the only run that meets the rule is “Bitcoin”, the subject becomes “Bitcoin and Bitcoin”. |
| **F3 – `fallback_subject` may silently drop a run that contains a channel word** | GLM‑5.3‑FLASH | I didn’t see that the skip set includes all channel words, so a run like “Bitcoin Magazine” is dropped entirely. The rule allows this, but it is worth noting. |
| **F4 – `fallback_fields` returns `None` when no template fits the budget** | GPT‑OSS‑20B | I didn’t comment on the intentional “None” return path. It is correct, but worth documenting. |
| **F5 – `inventory` flag logic depends on `soft` and `fallback_line`** | GPT‑OSS‑20B | I didn’t verify that the flag is only added when `soft` is true and a fallback line is present. The code is correct, but the interaction with `_build` could be clearer. |
| **F6 – `LINE_ONLY_WRITES` comment mismatch** | GPT‑OSS‑20B | The comment still says “up to 4 writes a line” while the code now allows 3 alone‑writes plus the initial write. I didn’t note the comment inconsistency. |
| **F7 – `fallback_subject` uses `first.setdefault(run, (i, mm.start()))` only for runs that pass the filter** | GLM‑5.3‑FLASH | I didn’t realize that `first` is only populated for runs that survive the skip logic, which is fine but worth documenting. |

**2. Agreement / disagreement with their key findings**

| Model | Finding | My stance | Reason |
|-------|---------|-----------|--------|
| GLM‑5.3‑FLASH | F1 – crash on empty `chans` | **Agree** | The patch correctly guards against the IndexError. |
| GLM‑5.3‑FLASH | F2 – duplicate “Bitcoin” | **Disagree** | The model did not flag this; I did. |
| GPT‑OSS‑20B | F3 – skip set includes channel words | **Agree** | The rule explicitly says to skip channel words; the implementation matches. |
| GPT‑OSS‑20B | F4 – `None` return path | **Agree** | It is intentional; no change needed. |
| GPT‑OSS‑20B | F5 – flag logic | **Agree** | The flag is only added when `soft` and a fallback line exist. |
| GPT‑OSS‑20B | F6 – comment mismatch | **Agree** | The comment should be updated to reflect the new logic. |
| GPT‑OSS‑20B | F7 – `first` population | **Agree** | The logic is correct; no action needed. |

**3. New findings from this review**

1. **Duplicate “Bitcoin” in `fallback_subject`** – when the only qualifying run is “Bitcoin”, the subject becomes “Bitcoin and Bitcoin”.  
2. **Potential over‑long title when many channel names** – if `chans` contains many names, the title `"{subject}: {names}"` may exceed `HS.TITLE_MAX_WORDS` or `LINE_CHARS["title"]`. The current fallback logic falls back to `"{subject}, in their words"`, but the test only covers a few names; a larger lineup could still overflow.  
3. **`fallback_fields` uses `budget is not None` inside the generator** – harmless but unnecessary; could be simplified.  
4. **`fallback_fields` does not enforce that the chosen template is the *shortest* that fits the budget** – it picks the first that satisfies the budget, not the shortest. The rule says “the shortest that lands the takeaway_budget”.  
5. **`fallback_subject` does not enforce that the run is the *first* that never opens a sentence** – it only checks that the preceding character is not a sentence terminator, but it does not ensure that the run is the first such occurrence in the clip. The rule says “its first never opening a sentence”.  
6. **`fallback_subject` does not enforce that the run is *not* a channel word** – it skips channel words, but if a channel name is “Bitcoin” the run “Bitcoin” is skipped, which is correct. However, if a channel name is “Bitcoin Magazine”, the run “Bitcoin Magazine” is skipped entirely, which may be acceptable but should be documented.  
7. **`fallback_fields` does not check that the chosen closing template is *unique*** – if multiple templates fit the budget, any could be chosen; the rule does not require uniqueness, but the test expects the chosen text to be one of the templates, so this is fine.

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `fallback_fields` | P1 (IndexError) | **P1** (still present) | Crash fixed, but still a defect if `chans` empty. |
| `fallback_subject` | P2 (complex logic) | **P1** (duplicate Bitcoin) | New defect discovered. |
| `inventory` flag logic | P3 (comment mismatch) | **P2** (comment mismatch) | Minor but should be fixed. |
| `LINE_ONLY_WRITES` comment | P3 | **P2** | Comment mismatch. |
| `fallback_fields` budget selection | P3 | **P2** | Should pick shortest template. |
| `fallback_subject` first‑run rule | P3 | **P2** | Should enforce first occurrence. |

**5. Final priority list**

| Severity | Item | File:Line | Action |
|----------|------|-----------|--------|
| **P0** | None | – | – |
| **P1** | Duplicate “Bitcoin” in `fallback_subject` | `pipeline/package.py` line 52‑54 | Add guard: if best[0] == "Bitcoin" return "Bitcoin" else return f"{best[0]} and Bitcoin". |
| **P1** | `fallback_fields` may return a non‑shortest template | `pipeline/package.py` line 77‑78 | Change selection to pick the shortest template that fits the budget. |
| **P1** | `fallback_subject` does not enforce first‑run rule | `pipeline/package.py` line 44‑47 | Track first occurrence per clip and only consider the earliest run that satisfies the rule. |
| **P2** | `LINE_ONLY_WRITES` comment mismatch | `pipeline/package.py` line 98‑100 | Update comment to match new logic. |
| **P2** | `inventory` flag comment mismatch | `pipeline/package_pin.py` line 178 | Update comment to reflect that `fallback_line` is a soft gate. |
| **P2** | `fallback_fields` unnecessary `budget is not None` check | `pipeline/package.py` line 77 | Simplify generator expression. |
| **P2** | `fallback_subject` skip set may drop entire run containing channel word | `pipeline/package.py` line 40 | Document behavior; no code change needed. |
| **P3** | `fallback_fields` returns `None` when no template fits | `pipeline/package.py` line 79‑80 | Add explicit comment explaining intentional behavior. |

**6. The single highest‑leveraged change**

Add a guard in `fallback_subject` to avoid returning “Bitcoin and Bitcoin” when the only qualifying run is “Bitcoin”.

**7. Production ready?**

**No** – the duplicate “Bitcoin” bug and the non‑shortest template selection in `fallback_fields` are critical defects that must be fixed before shipping. Once those are addressed, the remaining P2 items can be resolved in a subsequent patch.