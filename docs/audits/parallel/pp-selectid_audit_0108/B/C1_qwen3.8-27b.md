# qwen3.8-27b (qwen/qwen3.8-27b) 90 s finish=stop usage in 41352 / out 2177 usd~0.157 (upper-bound price)

# Code Audit: Package B (pp-selectid-0108B)

## P0 Findings (Blockers)

**None found.** The core safety invariants (fail-closed on out-of-contract, no pass on outage, exact contract preservation) are maintained.

## P1 Findings (Major)

**1. `tests/package/replay85.py:745` — Rate-limit handling bypasses the Router's backoff and may cause infinite loops or spend cap exhaustion.**
```python
router.down.pop(MODELS[m], None)               # a rate limit is never a verdict: each call is tried afresh
...
if "HTTP 429" in str(e):                   # rate limited (after the router's own backoff): no row, so a
    time.sleep(30)                         # resume asks it again; never counted as the model's answer
    return None
```
*   **Scenario:** If a Heimdall model is persistently rate-limited (429), the script sleeps 30s and returns `None` (no row written). The `run` function's `ex.map` will simply move to the next job. However, because no row is written to `RESULTS.jsonl`, the `done` set does not update. If the script is re-run (or if the loop logic were to retry, though `ex.map` doesn't), it will ask again. More critically, `router.down.pop` forcibly clears the "down" state. If the Router's internal backoff logic relies on `down` to prevent immediate re-hits, this manual pop combined with the manual `sleep(30)` creates a race condition or bypasses the intended exponential backoff. If the 429 persists, the script will burn through the `LIMIT_USD` ($20) cap on *failed* calls (if the provider charges for 429s or if the "spend" is estimated before the error is fully processed) or simply hang/slow down significantly without making progress, potentially violating the "no new Grok spend" spirit if the Heimdall calls are expensive and failing.
*   **Recommendation:** Verify that `P.Router`'s `call` method handles 429s internally with backoff and that `router.down` is the correct mechanism. If the Router already backs off, the manual `pop` and `sleep` are redundant and potentially harmful. If the Router does *not* handle 429s, the manual sleep is a band-aid. Ensure that 429s do not count against the `LIMIT_USD` cap if they are not successful calls.

**2. `tests/package/shadow86.py:1221` — "Would seal under Grok" logic is overly strict regarding "grok no verdict".**
```python
would_seal = None if not texts else not any(r["compare"] in ("looser", "grok no verdict") for r in pin_diff)
```
*   **Scenario:** If Grok returns an out-of-contract answer (no verdict) for a clip on the pin, `compare` is set to `"grok no verdict"`. The logic treats this as "Grok would have stopped it" (i.e., `would_seal` becomes `False`). However, an out-of-contract answer is a *failure of the model*, not a *decision to exclude*. In the production pipeline (Package A/B), an out-of-contract answer moves to the next model. If Grok is the *last* model in the chain, it results in a "no verdict" (fail-closed). So, technically, if Grok is the final arbiter and it fails, the pin *would* not seal. But if Grok is in shadow (non-deciding), its "no verdict" is irrelevant to the actual seal. The report is comparing Heimdall (deciding) vs Grok (shadow). If Grok (shadow) fails to parse, it doesn't mean the pin *would* have failed under Grok's *decision logic*, only that Grok's *output* was unreadable. The label "would_seal_under_grok" implies a counterfactual decision. If Grok's output is garbage, we don't know its decision. Treating "no verdict" as "would have stopped" is a conservative (safe) assumption, but it may be misleading if the intent is to measure *agreement on decisions*.
*   **Recommendation:** Clarify the semantics. If "would_seal_under_grok" means "would the pin have passed if Grok were the deciding model in the same chain position?", then "no verdict" (fail-closed) is correct. If it means "would Grok's *judgment* have allowed it?", then "no verdict" should be excluded from the "would have stopped" set, or reported separately. Given the "fail-closed" law, the current logic is likely *correct* for the pipeline's behavior, but the report should explicitly state that "grok no verdict" is treated as a fail-closed stop.

## P2 Findings (Minor)

**1. `pipeline/package.py:263-268` — `hook_ratings` error message truncation.**
```python
except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # (it was one re-ask of the same
    return out, f"{type(e).__name__}: {str(e)[:200]}"     # model) unavailable, all out of contract, or the guard
```
*   **Issue:** The comment says "it was one re-ask of the same model", but the code now uses `P.call_parsed` which moves to the *next* model. The comment is stale.
*   **Recommendation:** Update the comment to reflect the new "move on to next model" behavior.

**2. `tests/package/replay85.py:555-557` — Regex for clip keys in `decide` function.**
```python
named = re.findall(r'"(clip_\d+)": 1\b', prompt)
labels = re.findall(r'CLIP label="([^"]+)"', prompt)
allowed = [set(named)] if named else [set(labels), set(labels) - {"hook"}]
```
*   **Issue:** The regex `"(clip_\d+)": 1\b` assumes the prompt format is exactly `"clip_0": 1`. If the prompt format changes (e.g., `"clip_0": 1,` or different spacing), the regex may fail. The `labels` fallback is more robust. However, if `named` is found but is incomplete (e.g., only some clips are named in the prompt), the `allowed` set will be wrong.
*   **Recommendation:** Verify that the prompt format is stable. If not, prefer the `labels` extraction or make the regex more flexible.

**3. `tests/package/shadow86.py:1170` — `pin_texts` normalization.**
```python
return [R._norm(s.get("text") or "")[10:70] for pk in pks for s in pk.get("segments") or [] if isinstance(s, dict)]
```
*   **Issue:** The slice `[10:70]` is arbitrary. It assumes that the first 10 characters are not useful for matching. If the clip text is short (< 70 chars), this may truncate the entire text. If the clip text starts with a common prefix (e.g., "Bitcoin..."), the first 10 chars might be the most distinctive part.
*   **Recommendation:** Use a more robust matching strategy, such as checking if the normalized text is a substring of the prompt, or using a longer slice.

**4. `pipeline/context_integrity.py:74-76` — `parse_b0` does not check relations.**
```python
def parse_b0(text):
    B0 = _strict(text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
                                                        "relations": ("labels", "relation")})
    b0_by = {t["label"]: t for t in B0["takeaways"] if isinstance(t.get("label"), str)}
    if not set(labels) <= set(b0_by):
        raise ValueError(f"step B (clips alone) must answer at least {labels}")
    return b0_by
```
*   **Issue:** `parse_b0` validates the structure of `relations` via `_strict` but does not validate the *content* of the relations (e.g., that every pair is covered exactly once). `parse_b` (for the full step B) does this validation. Since `parse_b0` is for "clips alone" (B0), it may be intentional that relations are not fully validated here. However, if B0's relations are used downstream, this could be a gap.
*   **Recommendation:** Confirm that B0's relations are not used for decision-making, or add the same validation as `parse_b`.

## SHIP: Yes with conditions

**Conditions:**
1.  **Verify P1-1:** Confirm that the manual `router.down.pop` and `time.sleep(30)` in `replay85.py` do not bypass the Router's intended backoff logic or cause spend cap issues. If the Router handles 429s internally, remove the manual handling.
2.  **Clarify P1-2:** Add a comment in `shadow86.py` explaining that "grok no verdict" is treated as a fail-closed stop for the "would_seal_under_grok" calculation.
3.  **Update P2-1:** Fix the stale comment in `package.py` regarding `hook_ratings`.
4.  **Run Tests:** Ensure `test_medley.py`, `test_shadow86.py`, and `test_gates.py` pass with the new `kind` parameter and `call_parsed` integration.