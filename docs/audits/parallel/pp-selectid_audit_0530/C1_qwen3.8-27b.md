# qwen3.8-27b (qwen/qwen3.8-27b) 55 s finish=stop usage in 17132 / out 3711 usd~0.107 (upper-bound price)

I’ll audit the diff strictly against the stated laws, the orchestrator’s Ruling 33 / item 42, and the render contract. I’ll focus on whether (a) and (c) are truly enforced at the pin stage, whether the scorer’s pending status is honestly represented, whether the pin fields match the render contract, and whether untrimmed/legacy behavior is preserved.

## P0 Findings

**P0-1: `pipeline/package.py:106-109` — Acoustic onset rule (a) is applied to the *original* cut, not the *trimmed* cut.**
*   **Scenario:** A moment `m` starts at `t=1.0s` with the word "But". The trimmed variant `v` starts at `t=1.2s` (the next word). The code computes `hook_onset` for `m` (the original moment) in the `cleared` dict. Then it checks `if m.get("trimmed_leading") ...` on the *original* moment `m` (which does *not* have `trimmed_leading` set; only the variant `v` does).
    *   Wait, let's look closer at `build()`.
    *   `ms` is filtered to remove `no_role` moments.
    *   `trims` are created from `no_role` moments.
    *   `ms` becomes `[originals] + [trims]`.
    *   `ad_read` is computed on `ms`.
    *   `cleared` is computed on `ms` (which includes trims).
    *   `hook_onset` is measured for `cleared` moments.
    *   The check at line 106: `trim_cut = {mid: ... for mid, m in cleared.items() if m.get("trimmed_leading") and m["hook_onset"].get("pass") is not True}`.
    *   Here `m` is the *trimmed variant* (because it has `trimmed_leading`).
    *   Does `hook_onset` measure the *trimmed* cut?
    *   `hook_onset` is likely a function that checks the audio before `m["start"]`.
    *   For the trimmed variant `v`, `v["start"]` is the start of the *kept* words (e.g., "Bitcoin...").
    *   The acoustic onset rule (Ruling 33a) requires "genuine sub-speech audio before the first onset".
    *   If `hook_onset` checks the silence before `v["start"]`, it is checking the gap between "But" and "Bitcoin".
    *   However, the law says: "The START OF PLAYBACK keeps the D1 rule unchanged: a source that starts speaking at its file head, and the hook, need >= 80 ms of genuine sub-speech audio before the first onset".
    *   For a *clip* (not a hook), the law says: "Inside the video there is no lead / tail minimum (DEC-10: v2f's approved edges: 0 ms)."
    *   BUT, Ruling 33(a) specifically says: "the acoustic onset rule is met on the **trimmed cut**".
    *   The "trimmed cut" is the point where "But" ends and "Bitcoin" begins.
    *   If `hook_onset` is designed for hooks (checking file head or lead-in), does it apply to clips?
    *   The code applies `hook_onset` to *all* cleared moments, including clips.
    *   If `hook_onset` fails for a clip because there isn't 80ms of silence before "Bitcoin" (because "But" was just spoken), the clip is rejected.
    *   Is this correct? Ruling 33(a) says "acoustic onset rule is met on the trimmed cut". This implies the cut point (start of "Bitcoin") must have the required quiet.
    *   The code *does* reject if `hook_onset` fails. So (a) is enforced.
    *   **However**, there is a subtle issue. `hook_onset` is typically a "hook" check. Does it behave correctly for a mid-video clip?
    *   The comment says: "G17a at the pin stage: genuine quiet before the first onset".
    *   If the "first onset" is "Bitcoin", and "But" ended 50ms ago, is that "genuine quiet"?
    *   The law says "Inside the video there is no lead / tail minimum".
    *   If `hook_onset` enforces an 80ms lead-in for *clips*, it might be too strict or incorrect for non-hook segments.
    *   But Ruling 33(a) explicitly invokes the "acoustic onset rule" for the trimmed cut.
    *   Let's check if `hook_onset` is the right function. The code uses `m["hook_onset"]`.
    *   If `hook_onset` is only valid for hooks, applying it to clips might be a logic error.
    *   **Correction:** The code applies `hook_onset` to *all* cleared moments. If `hook_onset` is a generic "is there quiet before this start time" check, it's fine. If it's specifically "is this a valid hook start (file head or 80ms lead)", it might be misapplied to clips.
    *   Given the ambiguity, I will flag this as a potential P1/P2, but let's look for harder failures.

**P0-2: `pipeline/package.py:30` — `stand_alone_check` does not pass `rate` to `SA.check_edl` for trimmed segments, but claims to record `scorer_pending`.**
*   **Scenario:** `stand_alone_check` calls `SA.check_edl(edl, rate=None, ...)`.
*   In `stand_alone.py`, `check_edl` with `rate=None` will fail closed for any segment that needs the scorer (conjunctions or trimmed words).
*   The code in `package.py` line 30: `r["scorer_pending"] = [lb for lb, m in zip(labels(len(segs)), segs) if m.get("trimmed_leading")]`.
*   This records *which* segments are pending.
*   But `r` (the result of `check_edl`) will have `ok: False` for those segments because `rate=None` causes `trimmed_opener` to return `False` (fail closed).
*   The `stand_alone_check` function returns `r`.
*   In `build()`, `stand_alone_check` is called? No, `stand_alone_check` is called in `inventory` or similar?
*   Actually, `stand_alone_check` is defined in `package.py`. It is called by `inventory` (line 113-121 in diff).
*   `inventory` puts `stand` into the output.
*   The pin stage (`package_pin.py`) checks `gate_problems`.
*   If `stand_alone` gate is `FAIL` (because `rate=None`), the pin is refused.
*   **BUT**, the orchestrator's item 42 says: "the scorer's verdict is PENDING AT THE RENDER... the pin stage records it, and the render holds a trimmed pin its scorer refuses".
*   This implies the **pin stage should NOT fail** on the scorer verdict. It should allow the pin to be created, marking it as pending, so the *render* can fail it later.
*   However, `package_pin.to_pin` calls `gate_problems`. If `stand_alone` is `FAIL`, `to_pin` raises `PinRefused`.
*   **This is a contradiction.** The code fails the pin at the pin stage because the scorer didn't run. The orchestrator's order says the pin should be created (with pending status) and the *render* should hold it.
*   **Wait**, let's re-read the "Stated Assumption": "The render's check_edl with rate=None fails a trimmed segment closed. Per item 42 ('use it now'), the scorer's verdict is PENDING AT THE RENDER: the pin stage records it, and the render holds a trimmed pin its scorer refuses... (a) and (c) ARE judged at the pin stage."
*   If (a) and (c) are judged at the pin stage, and they pass, but the scorer (b) is pending, does the pin pass?
*   The assumption says "the render holds a trimmed pin its scorer refuses". This implies the pin *exists* and is *valid* at the pin stage, but the *render* refuses it.
*   But `package_pin.to_pin` refuses if `gate_problems` is non-empty.
*   Does `gate_problems` consider `stand_alone` a required gate?
*   `required_gates(pk)` likely includes `stand_alone`.
*   If `stand_alone` is `FAIL` (due to `rate=None`), `gate_problems` returns an error, and `to_pin` raises `PinRefused`.
*   **Therefore, the pin is never created.** The "pending at the render" logic is unreachable because the pin creation fails first.
*   **This is a P0.** The code does not implement the "pending at the render" workflow. It implements "fail at the pin" workflow.
*   To fix this, `stand_alone_check` or `gate_problems` must treat `scorer_pending` as a "PASS" (or "PENDING") at the pin stage, allowing the pin to be sealed, so the render can later check the scorer.
*   Currently, `stand_alone_check` returns `r` where `r["ok"]` is `False` for trimmed segments.
*   `inventory` records `stand`.
*   `package_pin.to_pin` checks `gate_problems`.
*   If `gate_problems` sees `stand_alone: FAIL`, it refuses.
*   **Conclusion:** The pin cannot be created for trimmed segments. This violates the orchestrator's order to "use it now" and "record it as pending".

**P0-3: `pipeline/package.py:19-20` — `trimmed_leading` and `untrimmed_start` are added to the segment dict in `_package`, but `_package` is called *after* `stand_alone_check`?**
*   Let's trace the flow.
*   `build()` creates `ms` (moments).
*   `build()` calls `stand_alone_check`? No, `stand_alone_check` is called in `inventory`.
*   `inventory` is called with `stand` (the result of `stand_alone_check`).
*   `stand_alone_check` is called *where*?
*   In `build()`, I don't see `stand_alone_check` being called directly.
*   Wait, `stand_alone_check` is defined in `package.py`.
*   In `build()`, line 112: `if len({m["channel_id"] for m in cleared.values()}) < 3:` ...
*   Line 113-121 in diff is `inventory`.
*   `inventory` is called at the end of `build`?
*   The diff shows `inventory` being modified.
*   `stand_alone_check` is likely called *before* `inventory` to generate the `stand` dict.
*   If `stand_alone_check` is called on `segs` (the final segments), and `segs` are the trimmed variants, then `m.get("trimmed_leading")` is present.
*   `stand_alone_check` creates an `edl` from `segs`.
*   `SA.check_edl` is called with `rate=None`.
*   As established in P0-2, this fails.
*   So the pin is refused.

## P1 Findings

**P1-1: `pipeline/package.py:57` — `canon.canon_tokens(word)[:1] not in ([t] for t in TRIM_WORDS)` is inefficient and potentially buggy.**
*   `canon.canon_tokens(word)` returns a list of tokens.
*   `[:1]` gets the first token.
*   `([t] for t in TRIM_WORDS)` is a generator of single-element lists.
*   `in` checks if the list `['but']` is equal to any of `['but']`, `['and']`, etc.
*   This works, but it's ugly.
*   More importantly, `TRIM_WORDS` are lowercase. `canon.canon_tokens` likely lowercases.
*   If `word` is "But", `canon_tokens` returns `['but']`.
*   `['but'] in (['but'], ['and'], ...)` is `True`.
*   So `not in` is `False`.
*   The condition `if ... not in ...: return None` means if it's NOT a trim word, return None.
*   This logic is correct.

**P1-2: `pipeline/transcript_truth.py:262-266` — The `trimmed` logic in `edges` assumes the trimmed word is *immediately* before the clip's first word.**
*   `j` is the index of the clip's first word in the recogniser's words.
*   `ws[j-1]` is the word before it.
*   The code checks if `ws[j-1]` matches `trimmed`.
*   If it does, it sets `j -= 1` and reads the IN rule before *that* word.
*   This is correct for the "But Bitcoin" case.
*   However, what if there is a pause or another word?
*   The code requires `heard == tw`. If the recogniser heard "And" but we trimmed "But", it fails.
*   This is correct (fail closed).

**P1-3: `pipeline/package_pin.py:159` — `0 <= float(u) < float(s["start"])` check.**
*   `u` is `untrimmed_start`.
*   `s["start"]` is the trimmed start.
*   This ensures the untrimmed start is before the trimmed start.
*   Correct.

## P2 Findings

**P2-1: `pipeline/package.py:64` — `trimmed_leading` strips punctuation.**
*   `word.strip().strip(".,!?;:\"'()\u201c\u201d\u2014\u2026")`
*   This is good for canonical comparison.

**P2-2: `pipeline/stand_alone.py:219` — `need` list includes trimmed segments.**
*   `if trimmed_word(s) or ...`
*   This ensures the scorer is *requested* for trimmed segments.
*   But since `rate=None`, it fails.

## Summary of Critical Issue (P0-2)

The core problem is that the code **fails the pin** for trimmed segments because the scorer is not run at the pin stage. The orchestrator's order explicitly states that the scorer's verdict is **pending at the render**, implying the pin should be **created** (sealed) and the **render** should be the one to hold/fail it.

The current code:
1.  `stand_alone_check` calls `SA.check_edl` with `rate=None`.
2.  `SA.check_edl` fails trimmed segments (fail closed).
3.  `stand_alone_check` returns `ok: False`.
4.  `package_pin.to_pin` sees `stand_alone: FAIL` and raises `PinRefused`.
5.  **Result:** No pin is created. The "pending at the render" logic is never reached.

To comply with the orchestrator's order, the pin stage must **allow** the `stand_alone` gate to be "PENDING" (or "PASS" with a flag) for trimmed segments, so the pin can be sealed. The render stage must then check the `scorer_pending` flag and run the scorer, failing the render if the scorer rejects.

The diff does **not** implement this. It implements a hard fail at the pin stage.

## SHIP: No

**Reason:** The code fails to create pins for trimmed segments (P0-2), violating the orchestrator's explicit order to treat the scorer verdict as "pending at the render" rather than a pin-stage failure. The pin stage must seal the pin with a `scorer_pending` flag, and the render stage must enforce the scorer check. Currently, the pin is refused before it can be rendered.