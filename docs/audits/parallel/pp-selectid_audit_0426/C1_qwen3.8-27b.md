# qwen3.8-27b (qwen/qwen3.8-27b) 93 s finish=stop usage in 14325 / out 3311 usd~0.093 (upper-bound price)

# Audit: pp-selectid-0426 (Ruling 34 — BTC Screen)

## P0 Findings (Blockers)

**1. `pipeline/stand_alone.py`: `topical_screen` fails closed for Clips when `screen` is `None`**
*   **Scenario:** The `check_edl` function (line 219) accepts `screen=None` to preserve the "story path" (old behavior). However, the internal logic at line 234-235 is:
    ```python
    t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
        topical(kind, s.get("text"), prev, subject)
    ```
    While this *looks* correct, look at `topical_screen` (line 203). If `screen` is passed as `None` (which shouldn't happen due to the ternary, but let's look at the `no_topic` function in `package.py`), it calls `SA.topical_screen("clip", m["text"], "Bitcoin", E.BTC_SCREEN)`.
    
    Wait, the critical issue is in **`pipeline/eligibility.py`** and **`pipeline/package.py`** interaction with the **Story Path**.
    
    Actually, looking closer at `stand_alone.py` line 234:
    ```python
    t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
        topical(kind, s.get("text"), prev, subject)
    ```
    This is safe.
    
    **However**, there is a **P0 Logic Error in `pipeline/stand_alone.py` `check_edl` regarding the `medley_names_bitcoin` check.**
    
    Line 243-249:
    ```python
    if screen is not None:                                   # ruling 34: the MEDLEY names Bitcoin, once at least
        named = [r["segment"] for (label, kind, s), r in zip(segs, rows) if BITCOIN.search(s.get("text") or "")]
        out["medley_names_bitcoin"] = {"pass": bool(named), "segments": named, ...}
        out["ok"] = out["ok"] and bool(named)
    ```
    The variable `BITCOIN` is used here. Where is it defined?
    In `pipeline/eligibility.py` (line 8), `BITCOIN_TERMS` is defined.
    In `pipeline/stand_alone.py`, is `BITCOIN` imported or defined?
    The diff for `stand_alone.py` does **not** show an import of `BITCOIN` or `BITCOIN_TERMS`.
    The diff for `eligibility.py` defines `BITCOIN_TERMS`.
    If `stand_alone.py` does not import `BITCOIN` (or `BITCOIN_TERMS` and alias it), this code will raise a `NameError` at runtime whenever `screen is not None`.
    
    *Verification:* The diff for `stand_alone.py` (lines 194-250) shows changes to `topical` and `check_edl`. It does **not** show any `import` statements being added or modified at the top of the file. The existing code in `stand_alone.py` (not shown in diff, but implied by context) likely imports `re` and other things. If `BITCOIN` is not a global in `stand_alone.py`, this is a crash.
    
    *Assumption:* If `BITCOIN` is not defined in `stand_alone.py`, this is a **P0 Crash**.
    *Counter-Assumption:* Perhaps `BITCOIN` is defined in `stand_alone.py` in the base code? The diff doesn't show it. The `eligibility.py` diff defines `BITCOIN_TERMS`. It is highly likely `stand_alone.py` needs to import it or define it. Given the "Smallest diff" law, if the import is missing, it's a bug.
    
    Let's look at `pipeline/eligibility.py` line 8: `BITCOIN_TERMS = re.compile(...)`.
    In `stand_alone.py`, the code uses `BITCOIN.search(...)`.
    If `stand_alone.py` does not have `BITCOIN` defined, it crashes.
    
    **Finding P0-1:** `pipeline/stand_alone.py` line 244 uses `BITCOIN` which is not defined in the diff and likely not imported. This will cause a `NameError` for all Moments Medleys (where `screen` is not None).

**2. `pipeline/eligibility.py`: `BTC_SCREEN` Regex Syntax Error / Inconsistency**
    Line 13-14:
    ```python
    BTC_SCREEN = re.compile(r"\b(bitcoins?|btc|sats|satoshis?|halving|hash ?rate|lightning network|self[- ]custody|"
                            r"cold storage|microstrategy|mstr|ibit|saylor)\b", re.I)
    ```
    The test `test_the_screen_is_the_miners_verbatim` (line 259) attempts to parse the source file `pp-ingest pipeline/ingest/mine.py@8e6afb61` using a regex:
    ```python
    m = _re.search(r'BTC_SCREEN = re.compile\(r"(.*?)"\s*\n\s*r"(.*?)", re.I\)', r.stdout)
    ```
    This test regex expects the source code to be formatted as:
    `BTC_SCREEN = re.compile(r"..." \n r"...", re.I)`
    
    However, the code in `eligibility.py` is:
    `BTC_SCREEN = re.compile(r"..." \n r"...", re.I)`
    
    The test asserts `E.BTC_SCREEN.pattern == m.group(1) + m.group(2)`.
    If the source file `mine.py` has the regex on a single line, or formatted differently, the test fails.
    More importantly, the test relies on `git show` from a specific worktree `/home/ultron/worktrees/pp-ingest`. If this path doesn't exist in the CI/CD environment or the audit environment, the test is skipped (`skipTest`). This is acceptable for local dev, but the **P0** is the potential `NameError` in `stand_alone.py`.

**3. `pipeline/package.py`: `no_topic` Logic Flaw**
    Line 73:
    ```python
    ok, why = SA.topical_screen("clip", m["text"], "Bitcoin", E.BTC_SCREEN)
    ```
    `topical_screen` signature: `def topical_screen(kind, text, prev_text, screen):`
    Here, `prev_text` is hardcoded to `"Bitcoin"`.
    
    The docstring says: "a clip is judged per line-up... it completes the previous claim".
    `topical_screen` calls `topical(kind, text, prev_text, ("bitcoin", "btc"))` if the screen doesn't match.
    `topical` checks if `text` completes `prev_text`.
    By hardcoding `prev_text="Bitcoin"`, `no_topic` is checking if the moment completes the claim "Bitcoin".
    
    Is this correct?
    The docstring for `no_topic` says: "it fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that names Bitcoin (its most favourable place)."
    
    If a segment names Bitcoin, its text is likely "Bitcoin ...".
    If the next clip is "It fell 5%.", does it complete "Bitcoin"?
    `topical` likely checks for pronouns or conjunctions.
    If `topical` expects the *full* previous text to determine context, passing just "Bitcoin" might be too weak or too strong.
    However, the comment says "its most favourable place". If it can't complete "Bitcoin", it can't complete a longer sentence starting with Bitcoin?
    Actually, if the previous text is "Bitcoin crashed hard.", and the clip is "It lost 10%.", `topical` might pass.
    If `prev_text` is just "Bitcoin", `topical` might fail because "It" doesn't link to "Bitcoin" without the verb?
    This depends on `topical`'s implementation (not in diff).
    
    **Risk:** If `topical` requires more context than just the word "Bitcoin" to resolve pronouns, `no_topic` might incorrectly drop valid clips that *would* pass in a real line-up where the previous text is longer.
    Conversely, if `topical` is very loose, it might keep invalid clips.
    Given "Fail Closed" (L-j), dropping valid clips is a P1 (loss of content), but keeping invalid ones is P0 (bad render).
    The prompt says: "no_topic drops ONLY moments that can take no place under the render's rule".
    If `no_topic` is too strict (drops valid), it's a P1.
    If `no_topic` is too loose (keeps invalid), it's a P0.
    
    Let's look at `topical` (line 198 in diff, but it's the old function).
    `topical` checks `first` word. If `first` is a conjunction, it fails.
    If `first` is a pronoun, it checks `prev_text`.
    If `prev_text` is "Bitcoin", and `text` is "It fell.", `topical` might pass.
    This seems reasonable for a "most favourable place" check.

**4. `pipeline/package_pin.py`: `screen_problems` Validation**
    Line 155: `if not isinstance(pat, str) or not pat.strip() or len(pat) > 500 ...`
    Line 158: `re.compile(pat, re.I)`
    
    This matches the render's acceptance criteria described in the prompt.
    
    **However**, `seal` (line 120) takes `btc_screen=None`.
    `to_pin` (line 182) calls `seal(..., pk.get("btc_screen"))`.
    If `pk` is a Medley, `pk["btc_screen"]` is set in `assemble_medley` (line 41).
    If `pk` is a Story, `pk` might not have `btc_screen`.
    `pk.get("btc_screen")` returns `None`.
    `seal` handles `None` by not adding it to the body.
    This ensures old pins recompute correctly.

## P1 Findings (Major)

**1. `pipeline/stand_alone.py`: Missing Import/Definition for `BITCOIN`**
    As noted in P0-1, if `BITCOIN` is not defined, it's a crash. If it *is* defined in the base file but not shown in the diff, it's fine. But `eligibility.py` defines `BITCOIN_TERMS`. It is standard practice to import it. The diff does not show `import eligibility as E` or `from eligibility import BITCOIN_TERMS as BITCOIN` in `stand_alone.py`.
    *Action:* Verify `stand_alone.py` has access to `BITCOIN`. If not, add import.

**2. `pipeline/eligibility.py`: `BTC_SCREEN` vs `BITCOIN_TERMS`**
    `BITCOIN_TERMS` (line 8) is `\b(bitcoins?|btcs?)\b`.
    `BTC_SCREEN` (line 13) is much broader (sats, halving, etc.).
    The `medley_names_bitcoin` check in `stand_alone.py` uses `BITCOIN` (presumably `BITCOIN_TERMS`).
    The `topic` check uses `BTC_SCREEN`.
    This is consistent with Ruling 34: "The MEDLEY must name Bitcoin: at least one clip or the hook says it in the speaker's own words." (Implies the literal word Bitcoin/BTC).
    "The miner's about-Bitcoin screen is the per-clip test." (Implies the broader screen).
    So the logic is:
    - Topic: Broad Screen.
    - Medley Rule: Narrow Bitcoin/BTC.
    This is correct per the ruling.

**3. `tests/eligibility/test_eligibility.py`: Hardcoded Path**
    Line 262: `["git", "--no-optional-locks", "-C", "/home/ultron/worktrees/pp-ingest", ...]`
    This test will fail or skip in any environment that is not the specific Ultron server with that exact worktree path.
    While `skipTest` is used, it means the "mirror test" (verifying the regex matches the source) is **not** run in CI.
    This is a P1 because the integrity of the "sealed" regex is not verified in the automated pipeline.

## P2 Findings (Minor)

**1. `pipeline/package.py`: Log Message**
    Line 96-98: The log message is updated to reflect the new rule. Good.

**2. `pipeline/stand_alone.py`: `topical_screen` Docstring**
    Line 204-207: Docstring is clear.

**3. `pipeline/package_pin.py`: `screen_problems`**
    Line 143-161: Validation is robust.

## SHIP: NO

**Reasons:**
1.  **P0 Crash Risk:** `pipeline/stand_alone.py` uses `BITCOIN` in `check_edl` (line 244) without a visible import or definition in the diff. If `BITCOIN` is not already defined in the base `stand_alone.py` (which is unlikely given `eligibility.py` defines `BITCOIN_TERMS`), this will crash all Moments Medley pins.
2.  **P1 Test Integrity:** The test verifying the regex matches the source (`test_the_screen_is_the_miners_verbatim`) relies on a hardcoded local path and will be skipped in CI, leaving the "sealed" regex unverified in the automated pipeline.

**Conditions for Ship:**
1.  Add `from eligibility import BITCOIN_TERMS as BITCOIN` (or similar) to `pipeline/stand_alone.py` if not already present.
2.  Refactor `test_the_screen_is_the_miners_verbatim` to not rely on a hardcoded worktree path, or ensure the CI environment has this path available. Alternatively, embed the expected pattern in the test and compare, removing the `git show` dependency for the core assertion (though the `git show` is good for "verbatim" proof, it shouldn't be the *only* check in CI).