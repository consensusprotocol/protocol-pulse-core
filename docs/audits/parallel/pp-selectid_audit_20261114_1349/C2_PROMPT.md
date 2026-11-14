# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1349
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 826 s finish=length usage in 28528 / out 24000 usd~0.446 (upper-bound price)

# AUDIT — pp-selectid, RULING 102 (step A's second family) + $19 stop

Scope: I verified only what the diff + stated facts support. Line numbers refer to the diff's own numbering (C1_STEP.diff) unless noted.

---

## Findings

### <medium> M1 — `held_why` mislabels a real verdict's failure as HELD when the error is a `ValueError` starting with "CONTEXT_TOO_LONG" only by convention; but the real risk is the opposite: a genuine refusal path can be swallowed into HELD and retried forever

**Where:** package.py:57–64 (diff lines 57–64), test_ruling_102.py:793–803.

`held_why` maps *every* exception type except the `CONTEXT_TOO_LONG`-prefixed `ValueError` to HELD. The stated facts say a verdict that FAILS the clip is "a refusal, cached as a verdict" and unchanged. That holds only while the failing-verdict path never raises. But `test_a_verdict_that_fails_the_clip_is_a_refusal_not_held` (test_ruling_102.py:719–725) proves it by *mocking* `PK.CI.a_failures` to return `["REFERENT_OUTSIDE"]` — it never exercises the real path where the leg answers but `context_integrity.step_a` raises while validating the reply. If `step_a` raises (e.g. a transient decode error on an in-contract reply), `held_why` stamps HELD, the moment is retried next build, and — because a failed batch writes nothing to the exception path (package.py:608, stated) — nothing is cached, so the same transient error repeats every build. That is the ruling's intent (retry next build), so not a bug, but the test's coverage of "refusal vs held" is mock-only; the real `a_failures`-raises path is unproven from the diff.

**Sequence:** leg answers in contract → `step_a`'s validation raises `RuntimeError` mid-parse → `held_what` → HELD → not cached → next build, identical failure → held forever with no escalation. No escalation/counter exists anywhere in the diff.

**Severity:** medium (matches ruling intent; the gap is evidence, not behavior).

---

### <medium> M2 — `is_held` uses `all(...)` over the moment's reasons, so a moment with BOTH a held reason and a real refusal reason is classified HELD, hiding the refusal

**Where:** package.py:67–69 (diff lines 67–69); consumed at package.py:226, 275 (diff), spotlight.py:356 (diff), proof_ledger.py:389 (diff).

`is_held(why)` = `all(str(w).startswith(HELD) for w in why)`. A moment's `fails[mid]` list can accumulate more than one reason (e. g. the writers' re-screen at package.py:263–266 (diff) does `bad[mid] = list(fails_a.get(mid) or [HELD...])` — it *replaces*, so single-element there). But `second_screen`'s fail path (package.py:190–194 (diff)) does `fail[mid] = list(fails.get(mid) or [HELD...])` — again replace, not append. So within this diff, reason lists are single-element. However, `test_ruling_102.py:803` itself asserts `is_held([held_reason, "REFERENT_OUTSIDE"])` is False — i.e. the design intends mixed lists to read as refused. The risk: `prescreen`'s failed-batch path (package.py:91–94 (diff)) *overwrites* `fails[m["moment_id"]] = [held_why(e)]` per chunk; if a moment appears in two chunks (shouldn't, but nothing in the diff asserts 1:1 moment↔chunk), the later chunk's reason silently replaces the earlier's, and a prior refusal reason recorded by another screen is lost. Nothing in the diff or facts guarantees a moment cannot appear in two batches.

**Sequence:** moment in two prescreen batches → first batch fails with a real verdict-failure reason, second batch's call raises → `fails[mid]` overwritten with HELD → `held_102` counts it as held, the refusal reason is erased from the record (not from behavior — the moment is out either way).

**Severity:** medium (record-accuracy only; the moment is out of the build either way, and the ruling only governs "no leg answered").

---

### <medium> M3 — `second_screen`'s same-vendor/family check runs AFTER the held check, so a second verdict from the first's own vendor is classified by `is_held`-adjacent logic correctly, but the HELD default reason string is built with an f-string whose "no second verdict (law L-m)" text is duplicated in the spotlight's stop message, and the spotlight's `is_held` check reads `off_fail` keyed by the SAME mid set as `two` — a mid in `off_fail` but not in `clean` is silently dropped from `held_102`

**Where:** spotlight.py:352–361 (diff lines 352–361).

The spotlight loop (diff lines 353–359) iterates `clean.items()`; `out["held_102"]` (diff line 360) is `sorted(mid for mid in clean if P.is_held(off_fail.get(mid)))`. A mid in `off_fail` but not in `clean` never reaches `held_102` — correct, since it was stopped earlier. But `P.is_held(off_fail.get(mid))` with `off_fail.get(mid) = None` → `is_held(None)` → `bool(None) and ...` → `False`. Fine. The real subtlety: `stop(mid, "HELD (ruling 102), step A from the second family gave no answer: " + "; ".join(off_fail[mid]))` (diff line 357) indexes `off_fail[mid]` directl

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 27862 / out 618 usd~0.155 (upper-bound price)

<medium>tests/package/test_ruling_102.py:690</medium> (test_the_order_is_deepseek_glm_gemini_the_judge loops over down=(DS,), (DS,G), (DS,G,GEM) and asserts second verdict backend exactly matches the next in [DS,G,GEM,LJ]; matches ruling 102 order and "first that ANSWERS" via providers.Router.call + context_integrity.failover=True skipping Unavailable/DeadlineExceeded/RequestRejected; no sequence found that asks a leg twice or skips one that should be reached).

<medium>package.py:192 (second_screen) + 275 (re-screen) + test_ruling_102.py:710</medium> (is_held + held_why on ProviderError/Unavailable/DeadlineExceeded from every leg or default "no second verdict"; sets HELD not cached, build continues with swap_lineup if possible, spotlight stops with "HELD (ruling 102)"; a real CI.a_failures verdict remains refusal and is cached; no verified sequence where no-answer produces refusal or infinite retry of a cached refusal).

<medium>package.py:310 (inventory context_a dict(row(), **last_resort if any)) + 243 (pin_last_resort) + spotlight.py:347 + test_ruling_102.py:808</medium> (last_resort key added only when last_resort_of(a_two) non-empty; plain inventory() without it byte-matches old pins; seal hashes gates as-is so existing pins recompute identically; gate_problems only inspects required status/replayed per facts; no sequence where local_judge verdict reaches pin without record or changes seal of non-last-resort pin).

<medium>providers.py:331 (announce conditional on mode()==plan_b else ruling-102 text) + test_heimdall_health.py:914 + proof_ledger.py:394</medium> (STATE line 1 uses exact ruling-102 capitals for local judge outside Plan B; Plan B announcement preserved; Router first-use + test with explicit mode=lambda confirms once-per-router; no hang > ruling-87 40 min verified as LocalJudgeBackend.wait_s=2400s unchanged).

<medium>proof_ly.py:446 (LY_STOP_USD=19.0) + proof_ledger.py:420 (start_refused >=19.0 says "SAY IT ON STATE LINE 1 IN CAPITALS") + test_ruling_102.py:862</medium> (build refuses start at $19 with exact orchestrator text; 18.99 proceeds; per-call reserve + $20 cap facts prevent ending >$20; no verified build that starts >=19 or ends >20).

No critical/high findings; all ATTACK vectors (a-f) covered by diff + tests with no breaking sequence verifiable from provided facts and unchanged code (Router.call skipping, prescreen cache only on parsed verdict, confirm_ahead Grok-only via CONFIRM_VENDOR, parallel only with usable _confirm_leg). SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 63 s finish=stop usage in 31453 / out 3127 usd~0.141 (upper-bound price)

To audit the `pp-selectid` branch, I have analyzed the diff against the Governing Laws, the Orchestrator's Ruling 102, and the provided background facts.

### Findings

**<critical> (a) Refusal vs. Held Ambiguity in `held_why`**
*   **File:** `pipeline/package.py` (lines 57-64 in diff)
*   **Issue:** The function `held_why(e)` determines if a failure is a "Held" (retry next build) or a "Refusal" (permanent fail). It checks `if isinstance(e, ValueError) and str(e).startswith("CONTEXT_TOO_LONG")`.
*   **Sequence:** If a model returns a `ValueError` that does *not* start with "CONTEXT_TOO_LONG" (e.g., a parsing error wrapped in a ValueError, or a different context error), it is classified as `HELD`. However, if a *valid* verdict is returned that fails the integrity check (e.g., `REFERENT_OUTSIDE`), that is handled elsewhere. The risk is if a *transient* error is misclassified as a *permanent* refusal, or vice versa.
    *   *Correction:* The code explicitly handles `CONTEXT_TOO_LONG` as a Refusal. All other exceptions (including `ProviderError`, `RuntimeError`, `DeadlineExceeded`) are treated as `HELD`. This aligns with Ruling 102 ("an unavailable leg moves on... never a refusal").
    *   *However*, look at `second_screen` (line 193-194 in diff). If `fails.get(mid)` is empty and `a2 is None`, it defaults to `HELD`. If `a2` exists but fails the vendor check, it is `STEP_A_SAME_VENDOR` (a Refusal). This logic seems sound.
    *   *Real Critical Risk:* In `prescreen` (line 91-94 in diff), if `got is None`, it calls `held_why(e)`. If `e` is a `ValueError` from `context_integrity.step_a` that is *not* `CONTEXT_TOO_LONG` (e.g., a bug in the integrity check itself), it will be marked `HELD` and retried forever, potentially masking a code bug. But more importantly, **does `context_integrity.step_a` raise `ValueError` for other reasons?** The background says `step_a` raises `ValueError` for `CONTEXT_TOO_LONG`. If it raises other `ValueError`s, they are now `HELD`. If it raises `RuntimeError` for logic errors, they are `HELD`. This is fail-open for logic errors, but fail-closed for availability. Given "M12 FAIL CLOSED: missing data... rejects", treating a *logic* error as "unavailable" (Held) might violate the spirit of fail-closed if the logic error is deterministic. But Ruling 102 explicitly says "STEP_A_UNAVAILABLE MUST NEVER END A CLIP". So this is likely intended.

**<high> (b) Chain Order and Vendor Exclusion in `confirm_ahead`**
*   **File:** `pipeline/package.py` (lines 169-175 in diff)
*   **Issue:** `confirm_ahead` is supposed to ask Grok *only*. The code constructs `hv` and `hf` (vendors/families to exclude) as *all* backends where `b.vendor != CONFIRM_VENDOR` (i.e., everything except xAI).
    ```python
    hv = {b.vendor for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}
    hf = {b.family for b in router.backends.values() if b.family != CONFIRM_VENDOR} # BUG?
    ```
    Wait, `CONFIRM_VENDOR` is `"xai"`. `b.family` is e.g., `"grok"`, `"deepseek"`. `b.family != "xai"` is always True. So `hf` becomes the set of *all* families.
    Then `prescreen` is called with `set(wv) | hv` and `set(wf) | hf`.
    `prescreen` uses these sets to *exclude* backends.
    If `hf` contains all families, then *all* backends are excluded from the `confirm_ahead` call?
    Let's check `prescreen` logic (line 86-97 in diff). It iterates `router.chain(...)`. It checks `if b.vendor in set(wv) or b.family in set(wf)`.
    If `hf` is `{grok, deepseek, glm, gemini, gemma}`, then `b.family in hf` is True for *all* backends.
    Therefore, `confirm_ahead` will **skip every backend** and return no verdicts.
    *   **Sequence:**
        1.  `confirm_ahead` is called.
        2.  `hv` = `{heimdall/deepseek, heimdall/glm, google, local_judge}`.
        3.  `hf` = `{deepseek, glm, grok, gemini, gemma}` (since no family is "xai").
        4.  `prescreen` is called with `wv = {heimdall/deepseek, heimdall/glm, google, local_judge, xai}` (writers + hv) and `wf = {deepseek, glm, grok, gemini, gemma}` (writers + hf).
        5.  The chain for `step_a_second` is `[Grok, Deepseek, Glm, Gemini, LocalJudge]`.
        6.  Grok: `vendor="xai"` is in `wv`. Skipped.
        7.  Deepseek: `family="deepseek"` is in `wf`. Skipped.
        8.  Glm: `family="glm"` is in `wf`. Skipped.
        9.  Gemini: `family="gemini"` is in `wf`. Skipped.
        10. LocalJudge: `family="gemma"` is in `wf`. Skipped.
    *   **Result:** `confirm_ahead` produces **no verdicts**. The parallel optimization (Ruling 101) is broken. The build will fall back to sequential, or if it relies on `confirm_ahead` for the second verdict, it will fail.
    *   **Fix:** `hf` should be the set of families *other than* the confirm vendor's family? No, the goal is to ask *only* Grok. So we should exclude everyone *except* Grok.
    *   The current logic excludes everyone 

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 20261114_1349 (ruling 102, STEP_A_UNAVAILABLE must never end a clip; the 13:02 $19 stop; glm's H1 and M2 from audit 20261114_1246), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes. Its five <medium> notes each say what it verified, with no breaking sequence.
- qwen3.8-27b: SHIP no. One <critical>, refuted below from the diff's own line. One <high>, documented
  (ruling 87's 40 minutes). One <medium>, taken: a new test.
- glm-5.3-flash (826 s, finish=length at its 24,000 cap, so no SHIP line): no <critical>. Its one <high>, H1, it
  downgrades to medium itself. One point taken (M3: the pin note's words); the rest documented.

## Refuted

- **qwen <critical>: "confirm_ahead excludes every family, so it never asks anyone".** Its quote of the code is not
  the code. The diff computes BOTH sets by the back-end's VENDOR (package.py, confirm_ahead):
  `hf = {b.family for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}`.
  - Grok's family "grok" is therefore never in hf, and Grok's vendor "xai" never in hv.
  - The test asserts the exact sets: wf == {deepseek, glm, gemini, gemma}, with no "grok".
  - Taken from the same point: the test checked only the sets. A new test,
    test_through_the_real_chain_grok_answers_ahead_and_no_fallback_is_ever_asked, runs a real providers.Router over
    the five legs with the real prescreen and step_a:
    - every new moment gets Grok's verdict;
    - with Grok down, none does;
    - deepseek, glm, Gemini and the judge are asked 0 times.

## Taken

- **glm M3, the pin note's words.** The note said "no faster leg of step A's SECOND family answered". In Plan B (ruling
  87), the first screen's chain ends in the local judge too, so a FIRST verdict can be the judge's, and the note would
  then misstate why. The rule text now holds in both cases: "ruling 87's last resort: no faster leg answered, so the
  local gemma3:27b on GPU0 (the integrator's judge service) gave this step-A verdict (the last leg of step A's second
  family under ruling 102, or of Plan B's chain under ruling 87)". The test asserts both parts.

## Documented, no change

- **qwen <high> / glm M1, the local judge can hold a build up to 40 minutes, and a moment can be held build after
  build.**
  - The 40 minutes is ruling 87's own allowance (LocalJudgeBackend.WAIT_S 2400, unchanged); ruling 102 names the
    judge as the last leg.
  - A moment held every build stays visible: each build's RULING 102 line counts and names the held moments, in
    capitals on STATE line 1, so the orchestrator sees a repeat.
  - The ruling says held, never refused, and retried next build. No counter is ruled.
- **glm M2, mixed reasons hiding a refusal.** Within this diff each moment's step-A reason list has one entry:
  - prescreen's chunks partition `todo` (`[todo[i:i + batch] for i in range(0, len(todo), batch)]`), so a moment is in
    exactly one chunk;
  - second_screen and the writers' re-screen REPLACE the list.
  - A mixed list (one held, one r

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_1349/C2_STEP.diff (936 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index ede12b2..535c340 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -168,14 +168,14 @@
   6 |     ],
   7 |     "min_out": 8000,
   8 |     "timeout_s": 300,
   9 | -   "what": "RULING 87 (21:18 Nov 13): PLAN B only. The GEMINI_API_KEY_MEDLEY key is fenced to this pipeline. Gemini reports no cost: the price-table estimate (list price, thinking counted as output) is booked, labelled."
  10 | +   "what": "RULING 87 (21:18 Nov 13): PLAN B only. The GEMINI_API_KEY_MEDLEY key is fenced to this pipeline. Gemini reports no cost: the price-table estimate (list price, thinking counted as output) is booked, labelled. RULING 102 (13:02 Nov 14): also step A's second family after Heimdall's deepseek and glm, reached without declaring Heimdall down (probed 12:5x ET Nov 14: answered in 2.2 s)."
  11 |    },
  12 |    "local_judge:gemma3:27b": {
  13 |     "vendor": "local_judge",
  14 |     "model": "gemma3:27b",
  15 |     "family": "gemma",
  16 |     "deadline_floor_s": 2400,
  17 | -   "what": "RULING 87 (21:18 Nov 13): PLAN B ONLY, step A's verdict when one outside family answers: the integrator's GPU0 judge service (request files in tests/package/proof/judge_requests, answers in /home/ultron/protocol_pulse/data/local_judge/results). Free. A render comes first: up to 40 min."
  18 | +   "what": "RULING 87 (21:18 Nov 13): PLAN B ONLY, step A's verdict when one outside family answers: the integrator's GPU0 judge service (request files in tests/package/proof/judge_requests, answers in /home/ultron/protocol_pulse/data/local_judge/results). Free. A render comes first: up to 40 min. RULING 102 (13:02 Nov 14): also the LAST leg of step A's second family (ruling 87's last resort), reached without declaring Heimdall down; recorded as such on the pin and on STATE line 1."
  19 |    }
  20 |   },
  21 |   "roles": {
  22 | @@ -359,8 +359,10 @@
  23 |     ],
  24 |     "context_verdict:step_a_second": [
  25 |      "xai:grok-4.20-0309-reasoning",
  26 | +    "heimdall:deepseek/deepseek-v4.1-flash",
  27 |      "heimdall:z-ai/glm-5.3-flash",
  28 | -    "heimdall:deepseek/deepseek-v4.1-flash"
  29 | +    "google:gemini-2.5-pro",
  30 | +    "local_judge:gemma3:27b"
  31 |     ],
  32 |     "context_verdict:step_c": [
  33 |      "xai:grok-4.20-0309-reasoning",
  34 | @@ -459,6 +461,7 @@
  35 |    },
  36 |    "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first.",
  37 |    "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
  38 | -  "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged."
  39 | +  "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged.",
  40 | +  "ruling_102": "RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) -> Heimdall glm -> GEMINI through the fenced key -> the local gemma3:27b on GPU0 through the integrator's judge service (ruling 87's last resort, recorded as such on the pin and on STATE line 1). Grok stays first (ruling 88 (c): Grok confirms a Heimdall pass); the second verdict is still off the first verdict's vendor and family. The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if no leg answers is the clip held for THIS build (STEP_A_HELD, not refused), and retried next build."
  41 |   }
  42 |  }
  43 | diff --git a/pipeline/package.py b/pipeline/package.py
  44 | index 7825b27..28bcc89 100644
  45 | --- a/pipeline/package.py
  46 | +++ b/pipeline/package.py
  47 | @@ -444,6 +444,39 @@ def assemble_medley(order, by_id, fields, ctx, vo_kind):
  48 |  # ── step A once per moment (orchestrator 05:25 item 5) ──
  49 |  
  50 |  STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]
  51 | +HELD = "STEP_A_HELD (ruling 102)"   # RULING 102 (13:02 Nov 14): no leg ANSWERED: held for THIS build, never refused, never
  52 | +LAST_RESORT = "local_judge:"       # cached, retried next build. The local judge's verdicts: ruling 87's last resort,
  53 | +#                                    recorded as such on the pin (last_resort_note: the medley's context_a row, the
  54 | +#                                    spotlight's step_a_two_families row) and on STATE line 1 (the build's line)
  55 | +
  56 | +
  57 | +def held_why(e):
  58 | +    """RULING 102: the reason a step-A call that gave no verdict leaves on its moments: HELD for this build, retried
  59 | +    next build (every leg unavailable, past its deadline, breaker-open, refused or out of contract; ruling 48's cap; any
  60 | +    error of the call), never a refusal. The one exception is the moment's own context: CONTEXT_TOO_LONG (law L-s never
  61 | +    truncates a window, so no retry can answer it) -> STEP_A_REFUSED."""
  62 | +    if isinstance(e, ValueError) and str(e).startswith("CONTEXT_TOO_LONG"):
  63 | +        return f"STEP_A_REFUSED: {str(e)[:200]}"
  64 | +    return f"{HELD}: no step-A verdict ({type(e).__name__}: {str(e)[:160]}); held for this build, retried next build"
  65 | +
  66 | +
  67 | +def is_held(why):
  68 | +    """RULING 102: a moment's step-A reasons say HELD (no answer), not a verdict's refusal."""
  69 | +    return bool(why) and all(str(w).startswith(HELD) for w in why)
  70 | +
  71 | +
  72 | +def last_resort_of(verdicts):
  73 | +    """RULING 102: the back-ends among `verdicts` (A items) that are the local judge's (ruling 87's last resort)."""
  74 | +    return sorted({str(a.get("backend")) for a in verdicts or () if isinstance(a, dict)
  75 | +                   and str(a.get("backend")).startswith(LAST_RESORT)})
  76 | +
  77 | +
  78 | +def last_resort_note(by):
  79 | +    """RULING 102: the pin's record of the local judge's step-A verdicts ({label or moment id: back-end}), or None."""
  80 | +    return {"rule": "ruling 87's last resort: no faster leg answered, so the local gemma3:27b on GPU0 (the "
  81 | +                    "integrator's judge service) gave this step-A verdict (the last leg of step A's second family "
  82 | +                    "under ruling 102, or of Plan B's chain under ruling 87)",
  83 | +            "verdicts": dict(sorted(by.items()))} if by else None
  84 |  
  85 |  
  86 |  def _load_store(store):
  87 | @@ -556,9 +589,9 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  88 |          res = list(ex.map(lambda ic: screen(*ic), enumerate(chunks)))   # map keeps the chunks' order: zipped below
  89 |      new = {}
  90 |      for chunk, (got, e) in zip(chunks, res):
  91 | -        if got is None:
  92 | +        if got is None:                                 # ruling 102: no answer is HELD, never a refusal, never cached
  93 |              for m in chunk:
  94 | -                fails[m["moment_id"]] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:160]}"]
  95 | +                fails[m["moment_id"]] = [held_why(e)]
  96 |              continue
  97 |          items, backend = got
  98 |          b = router.backends.get(backend)
  99 | @@ -618,6 +651,28 @@ def _heimdall(b):
 100 |      return P.gateway(b) == "heimdall"
 101 |  
 102 |  
 103 | +CONFIRM_VENDOR = "xai"             # RULING 101: "Grok's confirm", the one vendor the confirm-ahead asks (ruling 102's
 104 | +#                                    Gemini and the local judge are the second screen's fallbacks, never asked ahead)
 105 | +
 106 | +
 107 | +def _usable(router, name, wv, wf):
 108 | +    """A leg a live call could take now: in the router, off the writers, not down this run, not breaker-open."""
 109 | +    b = router.backends.get(name)
 110 | +    return b is not None and b.vendor not in set(wv) and b.family not in set(wf) and \
 111 | +        name not in getattr(router, "down", {}) and not (hasattr(router, "breaker_open") and router.breaker_open(name))
 112 | +
 113 | +
 114 | +def _confirm_leg(router, wv, wf):
 115 | +    """RULING 101 (glm, audit 20261114_1246 C2 H1): the leg Grok's confirm-ahead would ask: the step_a_second chain's
 116 | +    first xAI back-end that is usable now; None when there is none (Grok writes, is down or breaker-open), and then a
 117 | +    confirm-ahead could ask nothing: the plan is sequential."""
 118 | +    for name in router.chain("context_verdict", kind="step_a_second"):
 119 | +        b = router.backends.get(name)
 120 | +        if b is not None and b.vendor == CONFIRM_VENDOR and _usable(router, name, wv, wf):
 121 | +            return name
 122 | +    return None
 123 | +
 124 | +
 125 |  def step_a_plan(router, ms, sources, ctx, wv, wf, store=None, cache=None, **first):
 126 |      """RULING 101 (12:16 Nov 14): does step A ask the Heimdall filter and Grok's confirm IN PARALLEL? Yes when more than
 127 |      STEP_A_PARALLEL_NEW moments are NEW to the first screen (no verdict in this build's ledger or the shared cache) AND
 128 | @@ -625,25 +680,30 @@ def step_a_plan(router, ms, sources, ctx, wv, wf, store=None, cache=None, **firs
 129 |      PRESCREEN_WORKERS) x the deadline of the filter's leading leg (the step_a_first chain's first back-end off the
 130 |      writers, not down and not breaker-open, at ruling 100's deadline for it: Router.effective_deadline). The filter is
 131 |      Heimdall's: when no Heimdall family leads (Grok leads: every family is the writer's, down or breaker-open), the first
 132 | -    verdicts are Grok's own, which a confirm off Heimdall could never serve: sequential, whatever the wait.
 133 | -    -> {"parallel", "new": [moments], "n_new", "est_wait_s", "leg"}."""
 134 | +    verdicts are Grok's own, which a confirm off Heimdall could never serve: sequential, whatever the wait. So it is
 135 | +    when no confirm leg is usable (_confirm_leg). -> {"parallel", "new": [moments], "n_new", "est_wait_s", "leg",
 136 | +    "confirm", "why"} (why: the reason it is sequential, None when parallel)."""
 137 |      new = prescreen(router, ms, sources, ctx, wv, wf, store=store, cache=cache, plan_only=True,
 138 |                      **{k: v for k, v in first.items() if k in ("batch", "kind")})
 139 |      if len(new) <= STEP_A_PARALLEL_NEW:                  # under the line: sequential whatever the wait
 140 | -        return {"parallel": False, "new": new, "n_new": len(new), "est_wait_s": None, "leg": None}
 141 | +        return {"parallel": False, "new": new, "n_new": len(new), "est_wait_s": None, "leg": None, "confirm": None,
 142 | +                "why": f"not over {STEP_A_PARALLEL_NEW} new moments"}
 143 |      leg, dl, heim = None, None, False
 144 |      for name in router.chain("context_verdict", kind="step_a_first"):
 145 |          b = router.backends.get(name)
 146 | -        if b is None or b.vendor in set(wv) or b.family in set(wf) or name in getattr(router, "down", {}) or \
 147 | -                (hasattr(router, "breaker_open") and router.breaker_open(name)):
 148 | +        if not _usable(router, name, wv, wf):
 149 |              continue
 150 |          leg, dl, heim = name, router.effective_deadline("context_verdict", b, first.get("deadline_s")), _heimdall(b)
 151 |          break
 152 |      batch = first.get("batch") or PRESCREEN_BATCH
 153 |      rounds = math.ceil(math.ceil(len(new) / batch) / PRESCREEN_WORKERS) if new else 0
 154 |      wait = rounds * dl if dl else 0.0
 155 | -    return {"parallel": heim and len(new) > STEP_A_PARALLEL_NEW and wait > STEP_A_PARALLEL_WAIT_S, "new": new,
 156 | -            "n_new": len(new), "est_wait_s": round(wait, 1), "leg": leg}
 157 | +    confirm = _confirm_leg(router, wv, wf)
 158 | +    why = ("no Heimdall family leads the filter" if not heim else
 159 | +           f"the filter's wait is not over {STEP_A_PARALLEL_WAIT_S / 60:.0f} min" if wait <= STEP_A_PARALLEL_WAIT_S
 160 | +           else "no confirm leg (Grok writes, is down or breaker-open)" if confirm is None else None)
 161 | +    return {"parallel": why is None and len(new) > STEP_A_PARALLEL_NEW, "new": new, "n_new": len(new),
 162 | +            "est_wait_s": round(wait, 1), "leg": leg, "confirm": confirm, "why": why}
 163 |  
 164 |  
 165 |  def confirm_ahead(router, new, sources, ctx, wv, wf, log=print, cache=None):
 166 | @@ -652,8 +712,8 @@ def confirm_ahead(router, new, sources, ctx, wv, wf, log=print, cache=None):
 167 |      (it then reuses the verdict off the first's vendor; 'a clip passes only if BOTH pass' is unchanged, and a moment
 168 |      whose first verdict came from Grok itself is screened off it as before). -> {"asked", "verdicts", "usd", "calls",
 169 |      "by": {moment id: back-end}}: the spend is reported per build (a verdict the second screen cannot use is extra)."""
 170 | -    hv = {b.vendor for b in router.backends.values() if _heimdall(b)}
 171 | -    hf = {b.family for b in router.backends.values() if _heimdall(b)}
 172 | +    hv = {b.vendor for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}    # ruling 102: Grok only, never
 173 | +    hf = {b.family for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}    # Gemini or the local judge
 174 |      tally = _Tally(router)
 175 |      try:
 176 |          got, _fails, _, _ = prescreen(tally, new, sources, ctx, set(wv) | hv, set(wf) | hf, n=len(new), store=None,
 177 | @@ -710,8 +770,7 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 178 |                               cache=cache, batch=batch, deadline_s=dl,    # ruling 58: a second verdict is paid once;
 179 |                               kind="step_a_second", failover=True)        # ruling 82 / 88 (c): the chain
 180 |          except Exception as e:
 181 | -            return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
 182 | -                        for m in chunk}, set(), set()
 183 | +            return {}, {m["moment_id"]: [held_why(e)] for m in chunk}, set(), set()
 184 |      with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as ex:
 185 |          res = list(ex.map(lambda j: one(*j), jobs))          # Executor.map keeps the order of jobs: zipped below
 186 |      two, fail = {}, {}
 187 | @@ -719,8 +778,9 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 188 |          for m in chunk:
 189 |              mid, a2 = m["moment_id"], got.get(m["moment_id"])
 190 |              b2 = router.backends.get((a2 or {}).get("backend"))
 191 | -            if fails.get(mid) or a2 is None:
 192 | -                fail[mid] = list(fails.get(mid) or ["STEP_A_UNAVAILABLE: no second verdict (law L-m)"])
 193 | +            if fails.get(mid) or a2 is None:            # ruling 102: no verdict at all is HELD, retried next build
 194 | +                fail[mid] = list(fails.get(mid) or [f"{HELD}: no second verdict (law L-m); held for this build, "
 195 | +                                                    f"retried next build"])
 196 |              elif b2 is None or b2.vendor == k[0] or (k[1] and b2.family == k[1]):
 197 |                  fail[mid] = [f"STEP_A_SAME_VENDOR: the second verdict came from {a2.get('backend')}, not off the "
 198 |                               f"first's vendor {k[0]} and family {k[1]} (law L-m)"]
 199 | @@ -2486,7 +2546,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 200 |      ahead_pool = ThreadPoolExecutor(max_workers=1) if plan["parallel"] else None
 201 |      ahead = ahead_pool.submit(confirm_ahead, router, plan["new"], sources, ctx, wv, wf, log, step_a_cache) \
 202 |          if ahead_pool is not None else None              # Grok's confirm beside the Heimdall filter, at once
 203 | -    par = {**{k: plan[k] for k in ("parallel", "n_new", "est_wait_s", "leg")}, "used": 0}
 204 | +    par = {**{k: plan.get(k) for k in ("parallel", "n_new", "est_wait_s", "leg", "confirm", "why")}, "used": 0}
 205 |      try:
 206 |          a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 207 |                                                         cache=step_a_cache, kind="step_a_first",   # ruling 85 / 88 (c)
 208 | @@ -2503,7 +2563,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 209 |             "reposted": reposted,
 210 |             "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 211 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 212 | -                         "failed": {mid: f for mid, f in fails.items() if f}, "parallel_101": par},
 213 | +                         "failed": {mid: f for mid, f in fails.items() if f}, "parallel_101": par,
 214 | +                         "held_102": {"first": sorted(mid for mid, f in fails.items() if is_held(f)), "second": []},
 215 | +                         "last_resort_87": {}},                  # RULING 102: held, never refused; the local judge
 216 |             "angles": [], "takeaways": [],
 217 |             "package": None}
 218 |      log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
 219 | @@ -2599,8 +2661,17 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 220 |      a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log,
 221 |                                      cache=step_a_cache)                  # ORDER 06:22 item 45
 222 |      out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
 223 | -                                         "FAIL: " + "; ".join(off_fail.get(mid) or ["no second verdict"])
 224 | +                                         ("HELD: " if is_held(off_fail.get(mid)) else "FAIL: ") +
 225 | +                                         "; ".join(off_fail.get(mid) or ["no second verdict"])
 226 |                                           for mid in cleared}
 227 | +    out["prescreen"]["held_102"]["second"] = sorted(mid for mid in cleared if is_held(off_fail.get(mid)))
 228 | +    out["prescreen"]["last_resort_87"] = {mid: last_resort_of(a_two[mid]) for mid in sorted(a_two)    # RULING 102
 229 | +                                          if last_resort_of(a_two[mid])}
 230 | +    h = out["prescreen"]["held_102"]
 231 | +    if h["first"] or h["second"] or out["prescreen"]["last_resort_87"]:
 232 | +        log(f"  RULING 102: held for this build (no leg answered; retried next build): {len(h['first'])} at the first "
 233 | +            f"screen, {len(h['second'])} at the second {h['second']}; the local judge (ruling 87's last resort) gave "
 234 | +            f"{len(out['prescreen']['last_resort_87'])} step-A verdict(s): {sorted(out['prescreen']['last_resort_87'])}")
 235 |      cleared = {mid: m for mid, m in cleared.items() if mid in a_two}
 236 |      log(f"  {len(cleared)} of them clear step A from both vendors too (order 06:22 item 45: whichever vendor writes, "
 237 |          f"a verdict off it exists) ({time.time() - t0:.0f} s)")
 238 | @@ -2689,6 +2760,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 239 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
 240 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 241 |  
 242 | +    def pin_last_resort(pk):
 243 | +        """RULING 102: the pin's record of the local judge's step-A verdicts on its clips (either screen's), by label."""
 244 | +        return last_resort_note({sg["label"]: ", ".join(last_resort_of(a_two.get(sg["moment_id"])))
 245 | +                                 for sg in pk["segments"] if last_resort_of(a_two.get(sg["moment_id"]))})
 246 | +
 247 |      def off_writers(mid):
 248 |          """ORDER 06:22 item 45: the moment's passing step-A verdict from a back-end off every writer's vendor and
 249 |          family so far, else None (the re-screen after a write decides, item 44). The FIRST qualifying one in a_two's
 250 | @@ -2874,7 +2950,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 251 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 252 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 253 |                                  stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 254 | -                                visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]])
 255 | +                                visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 256 | +                                last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 257 |          import package_pin
 258 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 259 |          if problems:
 260 | @@ -3126,16 +3203,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 261 |                                  a_by[mid] = got_a[mid]
 262 |                                  a_two.setdefault(mid, []).append(got_a[mid])
 263 |                              else:                              # no verdict off the writers is never a pass (L-m)
 264 | -                                bad[mid] = list(fails_a.get(mid) or ["STEP_A_UNAVAILABLE: no verdict off the writers "
 265 | -                                                                     "(law L-m)"])
 266 | +                                bad[mid] = list(fails_a.get(mid) or [f"{HELD}: no verdict off the writers (law L-m);"
 267 | +                                                                     f" held for this build, retried next build"])
 268 |                          if bad:                                # ORDER 06:22 item 44: only these clips go, for good,
 269 |                              dropped |= set(bad)                # with their reason; the next-best cuttable clip takes
 270 |                              doomed |= set(bad)                 # each place (ruling 41's swap); the clips-alone verdict
 271 |                              out["prescreen"].setdefault("rescreen_failed", {}).update(bad)     # re-judges the line-up
 272 |                              swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed),
 273 |                                                           keep_hook=True)
 274 | -                            rec["why"] = (f"step A, re-screened off the writer's vendor, fails {sorted(bad)} (out for "
 275 | -                                          f"good): " + (f"swapped {swaps}, re-judged (order 06:22 item 44)"
 276 | +                            held = sorted(k for k, v in bad.items() if is_held(v))    # ruling 102: no answer
 277 | +                            rec["why"] = (f"step A, re-screened off the writer's vendor, fails "
 278 | +                                          f"{sorted(set(bad) - set(held))} (out for good)"
 279 | +                                          + (f", gives no answer for {held} (HELD, ruling 102: out of this build "
 280 | +                                             f"only, retried next build)" if held else "") + ": " +
 281 | +                                          (f"swapped {swaps}, re-judged (order 06:22 item 44)"
 282 |                                                          if swapped is not None else
 283 |                                                          "no swap fits the line-up rules: re-lined"))
 284 |                              relined = True
 285 | @@ -3288,7 +3369,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 286 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 287 |                                              stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 288 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 289 | -                                            value=val)                       # ruling 91: the takeaway earned its place
 290 | +                                            value=val,                       # ruling 91: the takeaway earned its place
 291 | +                                            last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 292 |                      if not ok_c:
 293 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 294 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 295 | @@ -3386,7 +3468,7 @@ def _spent(spend):
 296 |  
 297 |  
 298 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 299 | -              hook=None, stand=None, visual=None, value=None):
 300 | +              hook=None, stand=None, visual=None, value=None, last_resort=None):
 301 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 302 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 303 |      value: ruling 91's value verdict on the medley's takeaway (takeaway_value) -> the "takeaway_value" row, its "text"
 304 | @@ -3421,9 +3503,10 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 305 |          "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 306 |                                f"{FINAL_TAIL_S} s tail)"),
 307 |          "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
 308 | -        "context_a": row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
 309 | -                         sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 310 | -                         n=len(a_rows)),
 311 | +        "context_a": dict(row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
 312 | +                              sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 313 | +                              n=len(a_rows)),
 314 | +                          **({"last_resort": last_resort} if last_resort else {})),   # RULING 102: the local judge
 315 |          "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
 316 |                                measured=bool(ctx_.get("measured"))), **votes_of(ctx_)),
 317 |          "context_c": dict(row(ctx_.get("ok") is True and not (viol & {"NOT_ENTAILED", "POLARITY", "STRONGER"}),
 318 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 319 | index 1b9a14b..336f0fe 100644
 320 | --- a/pipeline/providers.py
 321 | +++ b/pipeline/providers.py
 322 | @@ -1260,8 +1260,14 @@ class Router:
 323 |              if isinstance(b, LocalJudgeBackend) and self.state_md and not getattr(self, "_announced_local", False):
 324 |                  import heimdall_health as HH
 325 |                  self._announced_local = True                    # ruling 87: "and STATE line 1 says so"
 326 | +                try:
 327 | +                    plan_b = self.mode() == "plan_b"
 328 | +                except ProviderError:                           # an unreadable health state: the ruling-102 words
 329 | +                    plan_b = False
 330 |                  HH.announce(self.state_md, "PLAN B WITH ONE OUTSIDE FAMILY: STEP A'S VERDICT IS ASKED OF THE LOCAL "
 331 | -                                           "GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE)")
 332 | +                                           "GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE)" if plan_b else
 333 | +                            "RULING 102: NO FASTER LEG OF STEP A'S SECOND FAMILY ANSWERED, SO ITS VERDICT IS ASKED OF "
 334 | +                            "THE LOCAL GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE): RULING 87'S LAST RESORT")
 335 |  
 336 |              def abandon(b=b, key=key, name=name, deadline_s=dl):   # RULING 83 (a): booked at its PROMPT tokens, an
 337 |                  booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
 338 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 339 | index 2d4ce7b..84ef788 100644
 340 | --- a/pipeline/spotlight.py
 341 | +++ b/pipeline/spotlight.py
 342 | @@ -735,7 +735,9 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 343 |                                         fams, None if any(not isinstance(a.get("replayed"), bool) for a in a_two or [])
 344 |                                         else any(a.get("replayed") for a in a_two or []),
 345 |                                         measured=len(a_two or []) == 2,
 346 | -                                       rule="ruling 90: step A from both families as routed (package.second_screen)")
 347 | +                                       rule="ruling 90: step A from both families as routed (package.second_screen)",
 348 | +                                       **({"last_resort": P.last_resort_note({m["moment_id"]: ", ".join(
 349 | +                                           P.last_resort_of(a_two))})} if P.last_resort_of(a_two) else {}))   # 102
 350 |      rows["spotlight_source"] = _row(src_rec["ok"], (src_rec.get("layout") or {}).get("backend"),
 351 |                                      bool((src_rec.get("layout") or {}).get("replayed", False)),
 352 |                                      measured=(src_rec.get("layout") or {}).get("measured") is True,
 353 | @@ -907,8 +909,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 354 |      for mid, m in clean.items():
 355 |          if mid in two:
 356 |              both[mid] = m
 357 | +        elif P.is_held(off_fail.get(mid)):              # RULING 102: no leg answered: held, retried next build
 358 | +            stop(mid, "HELD (ruling 102), step A from the second family gave no answer: " + "; ".join(off_fail[mid]))
 359 |          else:
 360 |              stop(mid, "step A from the second family: " + "; ".join(off_fail.get(mid) or ["no verdict (law L-m)"]))
 361 | +    out["held_102"] = sorted(mid for mid in clean if P.is_held(off_fail.get(mid)))       # RULING 102
 362 | +    out["last_resort_87"] = {mid: P.last_resort_of(v) for mid, v in sorted(two.items()) if P.last_resort_of(v)}
 363 |      passed(both, 6)
 364 |      waited = 0.0
 365 |      if both and scorer_verdicts_path and wait_s > 0 and \
 366 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 367 | index b6bd9ae..d2b60dd 100644
 368 | --- a/tests/package/proof_ledger.py
 369 | +++ b/tests/package/proof_ledger.py
 370 | @@ -131,6 +131,32 @@ def applied(router):
 371 |      return applies
 372 |  
 373 |  
 374 | +def start_refused(spent0):
 375 | +    """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
 376 | +    STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD. -> the refusal line, or None."""
 377 | +    if spent0 >= PL.LY_STOP_USD:
 378 | +        return (f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
 379 | +                f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator "
 380 | +                f"decides (13:02 Nov 14: SAY IT ON STATE LINE 1 IN CAPITALS)")
 381 | +    return None
 382 | +
 383 | +
 384 | +def ruling_102_line(pre, sp):
 385 | +    """RULING 102 (13:02 Nov 14): the build's line, for STATE line 1: the moments HELD for this build (no leg answered;
 386 | +    never refused, never cached, retried next build) and every step-A verdict the local judge gave (ruling 87's last
 387 | +    resort, recorded as such on the pin). -> str or "" (nothing held, no local verdict)."""
 388 | +    pre, sp = pre or {}, sp or {}
 389 | +    h = pre.get("held_102") or {}
 390 | +    first, second, spot = list(h.get("first") or []), list(h.get("second") or []), list(sp.get("held_102") or [])
 391 | +    last = sorted(set(pre.get("last_resort_87") or {}) | set(sp.get("last_resort_87") or {}))
 392 | +    if not (first or second or spot or last):
 393 | +        return ""
 394 | +    return (f"  RULING 102: HELD for this build, retried next build (no leg answered; never refused): {len(first)} at "
 395 | +            f"step A's first screen, {len(second)} at the medley's second screen {second}, {len(spot)} at the "
 396 | +            f"spotlight's {spot}; THE LOCAL JUDGE (RULING 87'S LAST RESORT) GAVE {len(last)} STEP-A VERDICT(S)"
 397 | +            + (f": {last}" if last else ""))
 398 | +
 399 | +
 400 |  def ruling_101_line(par):
 401 |      """RULING 101 (12:16 Nov 14): the build's line on step A's order, with the extra spend when Grok's confirm ran in
 402 |      parallel (its verdicts the second screen could not use: the dollars sequential would have saved). -> str or ""."""
 403 | @@ -146,8 +172,8 @@ def ruling_101_line(par):
 404 |                  f"saved" + (f"; {par['error']}" if par.get("error") else ""))
 405 |      wait = par.get("est_wait_s")
 406 |      return (f"  RULING 101: step A sequential ({par.get('n_new')} new moments" +
 407 | -            (f"; the filter's wait about {wait / 60:.1f} min on {par.get('leg')})" if isinstance(wait, (int, float))
 408 | -             else f", not over {PK.STEP_A_PARALLEL_NEW})"))
 409 | +            (f"; the filter's wait about {wait / 60:.1f} min on {par.get('leg')}" if isinstance(wait, (int, float))
 410 | +             else f", not over {PK.STEP_A_PARALLEL_NEW}") + (f": {par['why']})" if par.get("why") else ")"))
 411 |  
 412 |  
 413 |  def main(argv=None):
 414 | @@ -248,9 +274,9 @@ def main(argv=None):
 415 |      say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 416 |          f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 417 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 418 | -    if spent0 >= PL.LY_STOP_USD:
 419 | -        say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
 420 | -            f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator decides")
 421 | +    refused = start_refused(spent0)
 422 | +    if refused:
 423 | +        say(refused)
 424 |          logf.close()
 425 |          return 3
 426 |      say(f"  spend (ruling 48): ${spent0:.2f} of ${PL.LY_LIMIT_USD:.2f} vendor-reported before this build (no build "
 427 | @@ -387,6 +413,9 @@ def main(argv=None):
 428 |          say(f"no spotlight ({sp.get('why_none')})" + "".join(
 429 |              f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
 430 |              f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
 431 | +    line102 = ruling_102_line(res.get("prescreen"), sp)  # RULING 102: held, never refused; the local judge's verdicts
 432 | +    if line102:
 433 | +        say(line102)
 434 |      hp = res.get("hook_pool") or {}                      # RULING 76 (d): the four counts STATE line 1 carries;
 435 |      #   `moments` is the adapter's pool from LB.build_inputs, BEFORE usable() filters it (audit 1810 C3)
 436 |      res["ruling_76"] = {"inside_12h": sum(not PK.expired(m, now) for m in moments),
 437 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 438 | index 702160b..154aa11 100644
 439 | --- a/tests/package/proof_ly.py
 440 | +++ b/tests/package/proof_ly.py
 441 | @@ -49,8 +49,10 @@ OUT = os.path.join(HERE, "proof")
 442 |  SPEND = os.path.join(OUT, "SPEND_LY.json")
 443 |  LY_LIMIT_USD = 20.0                # RULING 83 (b) (20:33 Nov 13): $20.00 VENDOR-REPORTED for this order (ruling 48's
 444 |  LY_LIMIT_BASIS = "reported"        # $12 before; the old $40 cap by the price-table estimate read ~12x high);
 445 | -LY_STOP_USD = 16.0                 # the estimate counts only where a vendor reports none. At $16 no build starts.
 446 | -                                   # Each paid call still RESERVES its price-table upper bound while in flight.
 447 | +LY_STOP_USD = 19.0                 # the estimate counts only where a vendor reports none. The orchestrator 13:02 Nov
 448 | +                                   # 14: the $16 stop passed with leave; at $19 no build starts and STATE line 1 says
 449 | +                                   # so in capitals; no build may end over $20 (the cap: each paid call still RESERVES
 450 | +                                   # its price-table upper bound while in flight, and none passes the limit).
 451 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
 452 |  DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
 453 |  RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
 454 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 455 | index 2f4a7a3..cc9b1e8 100644
 456 | --- a/tests/package/test_ledger_build.py
 457 | +++ b/tests/package/test_ledger_build.py
 458 | @@ -871,7 +871,8 @@ class TestRuling85NoXai(unittest.TestCase):
 459 |          self.assertEqual(ch["fidelity_verdict"], [G, Q, X])                       # 96: glm -> qwen -> Grok
 460 |          self.assertEqual(ch["exclusion_verdict"], [G, DS, X])                      # 96: glm -> deepseek -> Grok
 461 |          self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, X])           # 06:12 (2): glm -> deepseek, no qwen
 462 | -        self.assertEqual(ch["context_verdict:step_a_second"], [X, G, DS])          # (c) Grok confirms; 06:12 (2)
 463 | +        self.assertEqual(ch["context_verdict:step_a_second"], [X, DS, G, GEM, "local_judge:gemma3:27b"])   # (c) Grok
 464 | +        #   confirms; RULING 102 (13:02 Nov 14): then deepseek, glm, Gemini, the local judge (ruling 87's last resort)
 465 |          self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
 466 |          self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
 467 |          self.assertEqual(ch["coherence_verdict:hook"], [Q, G, DS, X])              # 88 (b) / 96: the hook moved
 468 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 469 | index 2943c94..9d8e2ca 100644
 470 | --- a/tests/package/test_medley.py
 471 | +++ b/tests/package/test_medley.py
 472 | @@ -588,7 +588,7 @@ class Rig:
 473 |              mid = m["moment_id"]
 474 |              v = self.router.backends[name].vendor if name else None
 475 |              if name is None or (v, mid) in self.unavailable:
 476 | -                fails[mid] = ["STEP_A_UNAVAILABLE: ProviderError"]
 477 | +                fails[mid] = [PK.held_why(self.P.ProviderError("context_verdict: every back-end unavailable"))]
 478 |                  continue
 479 |              got[mid] = dict(self.A_OK, backend=name)
 480 |              fails[mid] = list(self.a_fail.get((v, mid), []))
 481 | @@ -1287,7 +1287,8 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 482 |              cache = os.path.join(d, "c.json")
 483 |              a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 484 |              self.assertEqual(len(a_by), 2)                                # the other batch (2) only
 485 | -            self.assertEqual(fails["m09"], ["STEP_A_UNAVAILABLE: RuntimeError: the batch reply was out of contract"])
 486 | +            self.assertEqual(fails["m09"], [f"{PK.HELD}: no step-A verdict (RuntimeError: the batch reply was out of "
 487 | +                                            f"contract); held for this build, retried next build"])   # ruling 102
 488 |              with open(cache) as f:
 489 |                  self.assertEqual(len(json.load(f)), 2)                    # a failure is never remembered
 490 |              calls.clear()
 491 | @@ -2513,7 +2514,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 492 |          rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],
 493 |                    unavailable={("heimdall", "y")})
 494 |          out = rig.run()
 495 | -        self.assertTrue(out["prescreen"]["second_vendor"]["y"].startswith("FAIL: STEP_A_UNAVAILABLE"))
 496 | +        self.assertTrue(out["prescreen"]["second_vendor"]["y"].startswith(f"HELD: {PK.HELD}"))      # ruling 102
 497 | +        self.assertEqual(out["prescreen"]["held_102"], {"first": [], "second": ["y"]})
 498 |          self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
 499 |  
 500 |      def test_the_verdict_used_is_the_one_off_the_writers_vendor(self):
 501 | @@ -2591,8 +2593,9 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 502 |                  self.open_ = set(open_)
 503 |  
 504 |              def chain(self, role, kind=None):
 505 | -                assert (role, kind) == ("context_verdict", "step_a_first")
 506 | -                return ["heimdall:glm", "heimdall:ds", "xai:grok"]
 507 | +                assert role == "context_verdict"
 508 | +                return {"step_a_first": ["heimdall:glm", "heimdall:ds", "xai:grok"],
 509 | +                        "step_a_second": ["xai:grok", "heimdall:ds", "heimdall:glm"]}[kind]
 510 |  
 511 |              def effective_deadline(self, role, b, deadline_s=None):
 512 |                  assert (role, deadline_s) == ("context_verdict", PK.SECOND_VERDICT_DEADLINE_S)   # the first screen's
 513 | @@ -2612,7 +2615,19 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 514 |          p = plan(21, R(open_={"heimdall:glm"}))           # glm's breaker open: deepseek leads, 2 x 300 s = 10 minutes
 515 |          self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 600.0, "heimdall:ds"))   # not OVER 10
 516 |          p = plan(37, R(open_={"heimdall:glm"}))           # 19 batches, 4 rounds x 300 s = 20 minutes
 517 | -        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (True, 1200.0, "heimdall:ds"))
 518 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"], p["confirm"], p["why"]),
 519 | +                         (True, 1200.0, "heimdall:ds", "xai:grok", None))
 520 | +        p = plan(37, R(open_={"heimdall:glm", "xai:grok"}))   # glm C2 H1: Grok breaker-open, no confirm leg
 521 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["confirm"]), (False, 1200.0, None))
 522 | +        self.assertIn("no confirm leg", p["why"])
 523 | +        p = plan(37, R(open_={"heimdall:glm"}), wv={"xai"})   # Grok writes: a confirm ahead could ask nothing
 524 | +        self.assertEqual((p["parallel"], p["leg"], p["confirm"]), (False, "heimdall:ds", None))
 525 | +        down = R()
 526 | +        down.down = {"heimdall:glm": "HTTP 503"}               # glm down this run: deepseek leads, as breaker-open
 527 | +        p = plan(37, down)
 528 | +        self.assertEqual((p["parallel"], p["leg"], p["confirm"]), (True, "heimdall:ds", "xai:grok"))
 529 | +        down.down = {"heimdall:glm": "HTTP 503", "xai:grok": "HTTP 503"}   # Grok down: no confirm leg
 530 | +        self.assertEqual(plan(37, down)["confirm"], None)
 531 |          p = plan(37, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # the writer's family: Grok leads,
 532 |          self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 472.4, "xai:grok"))   # 4 x 118.1 s
 533 |          p = plan(80, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # 40 batches, 7 rounds: over 10 minutes
 534 | @@ -2677,8 +2692,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 535 |          self.assertEqual((par["parallel"], par["n_new"], par["asked"], par["leg"]),
 536 |                           (True, len(self.MS), len(self.MS), "heimdall:glm"))
 537 |          main = threading.get_ident()
 538 | -        ahead = [t for k, wv, t in seen if k == "step_a_second" and wv == {"heimdall", "heimdall/glm"}]   # off every
 539 | -        # Heimdall family and the writers
 540 | +        ahead = [t for k, wv, t in seen if k == "step_a_second" and wv == {"heimdall", "heimdall/glm", "openai"}]
 541 | +        # off every vendor but Grok's (ruling 102: never Gemini or the local judge ahead) and off the writers
 542 |          self.assertEqual(len(ahead), 1)                                   # Grok's confirm: once,
 543 |          self.assertNotEqual(ahead[0], main)                               # on its own thread,
 544 |          self.assertIn(("step_a_first", {"heimdall"}, main), seen)         # beside the filter on the build's thread
 545 | @@ -2729,7 +2744,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 546 |                    [None, None], angle_from=("xai:grok", "xai", "grok"), unavailable={("openai", "y")})
 547 |          out = rig.run()
 548 |          self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
 549 | -        self.assertTrue(out["prescreen"]["rescreen_failed"]["y"][0].startswith("STEP_A_UNAVAILABLE"))
 550 | +        self.assertTrue(out["prescreen"]["rescreen_failed"]["y"][0].startswith(PK.HELD))           # ruling 102
 551 | +        self.assertIn("gives no answer for ['y'] (HELD, ruling 102", out["tried"][0]["why"])
 552 |          self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
 553 |  
 554 |      def test_when_no_swap_fits_the_line_up_re_lines_and_the_clip_stays_out(self):     # audit 0640 C1, glm P2-9
 555 | @@ -2756,7 +2772,7 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 556 |              PK.prescreen = saved
 557 |          self.assertEqual(two, {})
 558 |          self.assertEqual(sorted(fail), ["h", "x", "y", "z"])
 559 | -        self.assertTrue(all(f[0].startswith("STEP_A_UNAVAILABLE: RuntimeError") for f in fail.values()))
 560 | +        self.assertTrue(all(f[0].startswith(f"{PK.HELD}: no step-A verdict (RuntimeError") for f in fail.values()))
 561 |  
 562 |      def test_second_screen_fails_closed_on_an_unknown_back_end_or_the_same_vendor(self):
 563 |          B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 564 | diff --git a/tests/package/test_ruling_102.py b/tests/package/test_ruling_102.py
 565 | new file mode 100644
 566 | index 0000000..fd2aab7
 567 | --- /dev/null
 568 | +++ b/tests/package/test_ruling_102.py
 569 | @@ -0,0 +1,338 @@
 570 | +#!/usr/bin/env python3
 571 | +"""RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family after
 572 | +Grok: Heimdall deepseek -> Heimdall glm -> Gemini -> the local gemma3:27b (ruling 87's last resort, recorded as such on
 573 | +the pin and on STATE line 1). The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once,
 574 | +is never a refusal and is never cached; only when no leg answers is the clip HELD for this build, retried next build.
 575 | +
 576 | +Offline: a real providers.Router over fake legs, the real context_integrity.step_a, package.prescreen and
 577 | +package.second_screen; a temporary step-A cache."""
 578 | +import json
 579 | +import os
 580 | +import re
 581 | +import sys
 582 | +import tempfile
 583 | +import unittest
 584 | +from unittest import mock
 585 | +
 586 | +HERE = os.path.dirname(os.path.abspath(__file__))
 587 | +REPO = os.path.dirname(os.path.dirname(HERE))
 588 | +for _p in ("pipeline", "tests/package", "tests/providers", "tests/eligibility"):
 589 | +    sys.path.insert(0, os.path.join(REPO, _p))
 590 | +import package as PK  # noqa: E402
 591 | +import providers as P  # noqa: E402
 592 | +import proof_ledger as PLG  # noqa: E402
 593 | +import spotlight as SPOT  # noqa: E402
 594 | +import test_angles as TA  # noqa: E402
 595 | +import test_medley as TM  # noqa: E402
 596 | +import test_spotlight as TS  # noqa: E402
 597 | +from test_gates import a_item  # noqa: E402
 598 | +
 599 | +X, DS, G = "xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash", "heimdall:z-ai/glm-5.3-flash"
 600 | +GEM, LJ = "google:gemini-2.5-pro", "local_judge:gemma3:27b"
 601 | +LEGS = (X, DS, G, GEM, LJ)
 602 | +VENDOR = {X: ("xai", "grok", None), DS: ("heimdall/deepseek", "deepseek", "heimdall"),
 603 | +          G: ("heimdall/glm", "glm", "heimdall"), GEM: ("google", "gemini", None), LJ: ("local_judge", "gemma", None)}
 604 | +
 605 | +
 606 | +def answer(prompt):
 607 | +    """A step-A reply in contract for exactly the excerpts the prompt carries (each passes: test_gates.a_item)."""
 608 | +    return json.dumps({"excerpts": [a_item(lb) for lb in re.findall(r'<excerpt label="([^"]+)"', prompt)]})
 609 | +
 610 | +
 611 | +class Leg(P.Backend):
 612 | +    """One leg of the chain: answers in contract, or fails with `fail` (an exception), or answers out of contract."""
 613 | +
 614 | +    def __init__(self, name, fail=None, out_of_contract=False):
 615 | +        vendor, family, gw = VENDOR[name]
 616 | +        super().__init__(name, {"model": name.split(":", 1)[1], "family": family, "price_usd_per_1m": [1, 1]},
 617 | +                         "/nonexistent")
 618 | +        self.vendor, self.fail, self.ooc, self.calls = vendor, fail, out_of_contract, 0
 619 | +        if gw:
 620 | +            self.gateway = gw
 621 | +
 622 | +    def complete(self, prompt, max_tokens, seed, system=None):
 623 | +        self.calls += 1
 624 | +        if self.fail is not None:
 625 | +            raise self.fail
 626 | +        return ("this is not JSON" if self.ooc else answer(prompt)), {"in": 10, "out": 10}, 0.01
 627 | +
 628 | +
 629 | +class Judge(P.LocalJudgeBackend):
 630 | +    """The local judge (a LocalJudgeBackend: the Router's announcement), answering at once."""
 631 | +
 632 | +    def __init__(self):
 633 | +        super().__init__(LJ, {"model": "gemma3:27b", "family": "gemma"}, "/nonexistent")
 634 | +        self.calls = 0
 635 | +
 636 | +    def complete(self, prompt, max_tokens, seed, system=None):
 637 | +        self.calls += 1
 638 | +        return answer(prompt), {"in": 0, "out": 0}, 0.01
 639 | +
 640 | +
 641 | +def router(d, legs, **kw):
 642 | +    cfg = os.path.join(d, "cfg.json")
 643 | +    with open(cfg, "w") as f:
 644 | +        json.dump({"schema": "pp.providers/1",
 645 | +                   "backends": {b.name: {"vendor": "openai", "model": b.model} for b in legs},
 646 | +                   "roles": {"context_verdict": {"chain": [b.name for b in legs]}},
 647 | +                   "routing": {"mode": "heimdall_first", "verdict_roles": ["context_verdict"],
 648 | +                               "verdict_deadline_s": {"heimdall": 120},
 649 | +                               "heimdall_first": {"context_verdict:step_a_second": list(LEGS)}}}, f)
 650 | +    r = P.Router(cfg, env_path="/nonexistent", routing="heimdall_first", **kw)
 651 | +    r.backends = {b.name: b for b in legs}
 652 | +    return r
 653 | +
 654 | +
 655 | +def pool(n=2):
 656 | +    return TM.TestRuling58StepAEveryCandidate.pool(None, n)
 657 | +
 658 | +
 659 | +class TestTheSecondFamily(unittest.TestCase):
 660 | +    """package.second_screen on the moments whose FIRST verdict is Grok's (the two hook-4 candidates' case)."""
 661 | +
 662 | +    def setUp(self):
 663 | +        self.d = tempfile.TemporaryDirectory()
 664 | +        self.addCleanup(self.d.cleanup)
 665 | +        self.cache = os.path.join(self.d.name, "STEP_A_CACHE.json")
 666 | +        self.ms, self.srcs = pool(2)
 667 | +        self.cleared = {m["moment_id"]: m for m in self.ms}
 668 | +
 669 | +    def screen(self, legs, first=X):
 670 | +        r = router(self.d.name, legs)
 671 | +        a_by = {mid: dict(a_item(mid), backend=first) for mid in self.cleared}
 672 | +        return PK.second_screen(r, self.cleared, a_by, self.srcs, TM.ctx(), log=lambda *_: None, cache=self.cache)
 673 | +
 674 | +    def cached(self):
 675 | +        if not os.path.exists(self.cache):
 676 | +            return {}
 677 | +        with open(self.cache) as f:
 678 | +            return {k: sorted(v) for k, v in json.load(f).items()}
 679 | +
 680 | +    def test_every_faster_leg_unavailable_the_local_judge_answers_and_is_the_last_resort(self):
 681 | +        legs = [Leg(X), Leg(DS, P.Unavailable("HTTP 503")), Leg(G, P.Unavailable("HTTP 503")),
 682 | +                Leg(GEM, P.Unavailable("HTTP 429")), Leg(LJ)]
 683 | +        two, fail = self.screen(legs)
 684 | +        self.assertEqual(fail, {})
 685 | +        self.assertEqual({mid: [a["backend"] for a in v] for mid, v in two.items()},
 686 | +                         {mid: [X, LJ] for mid in self.cleared})                 # off Grok: the last leg answered
 687 | +        self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])               # in order, each once, never Grok
 688 | +        self.assertEqual({mid: PK.last_resort_of(v) for mid, v in two.items()}, {mid: [LJ] for mid in self.cleared})
 689 | +
 690 | +    def test_the_order_is_deepseek_glm_gemini_the_judge(self):
 691 | +        for down, want in (((), DS), ((DS,), G), ((DS, G), GEM), ((DS, G, GEM), LJ)):
 692 | +            legs = [Leg(n, P.Unavailable("down") if n in down else None) for n in LEGS]
 693 | +            two, fail = self.screen(legs)
 694 | +            self.assertEqual({v[1]["backend"] for v in two.values()}, {want}, down)
 695 | +            os.path.exists(self.cache) and os.remove(self.cache)
 696 | +        legs = [Leg(n) for n in LEGS]                         # a first verdict from glm: Grok confirms, as before
 697 | +        two, _ = self.screen(legs, first=G)
 698 | +        self.assertEqual({v[1]["backend"] for v in two.values()}, {X})
 699 | +
 700 | +    def test_a_leg_out_of_contract_or_past_its_deadline_moves_on_at_once_and_is_never_a_refusal(self):
 701 | +        legs = [Leg(X), Leg(DS, out_of_contract=True), Leg(G, P.DeadlineExceeded("no answer within 60 s")),
 702 | +                Leg(GEM, P.RequestRejected("refused this request")), Leg(LJ)]
 703 | +        two, fail = self.screen(legs)
 704 | +        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {LJ}))
 705 | +        self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])
 706 | +
 707 | +    def test_no_leg_answers_the_clip_is_held_never_cached_and_retried_next_build(self):
 708 | +        legs = [Leg(X)] + [Leg(n, P.Unavailable("down")) for n in (DS, G, GEM, LJ)]
 709 | +        two, fail = self.screen(legs)
 710 | +        self.assertEqual(two, {})
 711 | +        self.assertEqual(sorted(fail), sorted(self.cleared))
 712 | +        self.assertTrue(all(PK.is_held(f) for f in fail.values()), fail)          # HELD, not a refusal
 713 | +        self.assertTrue(all("retried next build" in f[0] for f in fail.values()))
 714 | +        self.assertEqual(self.cached(), {})                                        # nothing remembered
 715 | +        legs = [Leg(X), Leg(DS, P.Unavailable("down")), Leg(G), Leg(GEM), Leg(LJ)]   # the next build: glm is back
 716 | +        two, fail = self.screen(legs)
 717 | +        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {G}))   # retried and answered
 718 | +        self.assertEqual(set(sum(self.cached().values(), [])), {G})                # only an answer is cached
 719 | +
 720 | +    def test_a_verdict_that_fails_the_clip_is_a_refusal_not_held(self):
 721 | +        legs = [Leg(n) for n in LEGS]
 722 | +        with mock.patch.object(PK.CI, "a_failures", lambda a: ["REFERENT_OUTSIDE"]):
 723 | +            two, fail = self.screen(legs)
 724 | +        self.assertEqual(two, {})
 725 | +        self.assertFalse(any(PK.is_held(f) for f in fail.values()))
 726 | +        self.assertEqual(set(map(tuple, fail.values())), {("REFERENT_OUTSIDE",)})
 727 | +
 728 | +
 729 | +class TestInTheBuild(unittest.TestCase):
 730 | +    """package.build (the rig: every model stubbed): HELD moments are recorded per screen, and a pin whose clips were
 731 | +    judged by the local judge carries the record (ruling 87's last resort) in its sealed context_a row."""
 732 | +    MS = TM.TestBuildLoop.MS
 733 | +
 734 | +    def test_a_moment_held_at_the_first_screen_is_recorded_as_held(self):
 735 | +        rig = TM.Rig(self.MS, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None], unavailable={("xai", "z")})
 736 | +        out = rig.run()
 737 | +        self.assertEqual(out["prescreen"]["held_102"], {"first": ["z"], "second": []})
 738 | +        self.assertTrue(PK.is_held(out["prescreen"]["failed"]["z"]))
 739 | +        self.assertIsNotNone(out["package"])                      # the build goes on without it
 740 | +
 741 | +    def test_a_pin_judged_by_the_local_judge_says_so(self):
 742 | +        rig = TM.Rig(self.MS, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None])
 743 | +        rig.router.backends[LJ] = type("B", (), {"vendor": "local_judge", "family": "gemma"})()
 744 | +        pre = rig.prescreen
 745 | +
 746 | +        def judged(router_, ms, *a, kind=None, **k):          # the second family: only the local judge answers
 747 | +            if k.get("plan_only"):                              # ruling 101's plan: nothing asked
 748 | +                return pre(router_, ms, *a, kind=kind, **k)
 749 | +            got, fails, v, f = pre(router_, ms, *a, kind=kind, **k)
 750 | +            if kind == "step_a_second":
 751 | +                got = {mid: dict(a, backend=LJ) for mid, a in got.items()}
 752 | +            return got, fails, v, f
 753 | +        rig.prescreen = judged
 754 | +        out = rig.run()
 755 | +        segs = out["package"]["segments"]
 756 | +        self.assertEqual(out["prescreen"]["last_resort_87"], {mid: [LJ] for mid in sorted(out["prescreen"]
 757 | +                                                                                         ["last_resort_87"])})
 758 | +        self.assertTrue({sg["moment_id"] for sg in segs} <= set(out["prescreen"]["last_resort_87"]))
 759 | +        row = out["package"]["gates"]["context_a"]
 760 | +        self.assertEqual(row["last_resort"]["verdicts"], {sg["label"]: LJ for sg in segs})
 761 | +        self.assertEqual(row["status"], "PASS")
 762 | +
 763 | +    def test_a_re_screen_off_the_writers_with_no_verdict_and_no_reason_is_held(self):
 764 | +        """The writers' re-screen (order 06:22 item 44): a clip it returns nothing at all for is HELD (its default
 765 | +        reason), out of this build only, never a refusal."""
 766 | +        rig = TM.Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)],
 767 | +                     [None, None], angle_from=("xai:grok", "xai", "grok"))
 768 | +        pre = rig.prescreen
 769 | +
 770 | +        def silent(router_, ms, sources_, ctx_, writer_vendor, *a, **k):
 771 | +            res = pre(router_, ms, sources_, ctx_, writer_vendor, *a, **k)
 772 | +            if k.get("plan_only") or not {"xai", "heimdall"} <= P._as_set(writer_vendor):
 773 | +                return res
 774 | +            got, fails, v, f = res                              # the writers' re-screen: y gets nothing at all
 775 | +            return {m: x for m, x in got.items() if m != "y"}, {m: x for m, x in fails.items() if m != "y"}, v, f
 776 | +        rig.prescreen = silent
 777 | +        out = rig.run()
 778 | +        self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
 779 | +        self.assertTrue(PK.is_held(out["prescreen"]["rescreen_failed"]["y"]))
 780 | +        self.assertIn("no verdict off the writers", out["prescreen"]["rescreen_failed"]["y"][0])
 781 | +
 782 | +    def test_the_default_no_second_verdict_is_held(self):
 783 | +        ms, srcs = pool(1)
 784 | +        mid = ms[0]["moment_id"]
 785 | +        r = type("R", (), {"backends": {X: Leg(X), DS: Leg(DS)}, "routing": "heimdall_first"})()
 786 | +        with mock.patch.object(PK, "prescreen", lambda *a, **k: ({}, {}, set(), set())):   # no verdict, no reason
 787 | +            two, fail = PK.second_screen(r, {mid: ms[0]}, {mid: dict(a_item(mid), backend=X)}, srcs, TM.ctx(),
 788 | +                                         log=lambda *_: None)
 789 | +        self.assertEqual(two, {})
 790 | +        self.assertTrue(PK.is_held(fail[mid]), fail)
 791 | +
 792 | +
 793 | +class TestHeldWhy(unittest.TestCase):
 794 | +    def test_no_verdict_is_held_except_a_context_law_l_s_will_never_shorten(self):
 795 | +        for e in (P.ProviderError("context_verdict: every back-end unavailable"), P.SpendLimit("over $20"),
 796 | +                  RuntimeError("anything")):
 797 | +            why = PK.held_why(e)
 798 | +            self.assertTrue(PK.is_held([why]), e)
 799 | +            self.assertIn(type(e).__name__, why)
 800 | +        why = PK.held_why(ValueError("CONTEXT_TOO_LONG: m1's window is 9000 characters (> 6000); never truncated"))
 801 | +        self.assertTrue(why.startswith("STEP_A_REFUSED: CONTEXT_TOO_LONG"))
 802 | +        self.assertFalse(PK.is_held([why]))
 803 | +        self.assertFalse(PK.is_held([]))
 804 | +        self.assertFalse(PK.is_held([PK.held_why(RuntimeError("x")), "REFERENT_OUTSIDE"]))   # one refusal: refused
 805 | +
 806 | +
 807 | +class TestOnThePinAndOnState(unittest.TestCase):
 808 | +    def test_the_medley_pin_records_the_local_judge_and_a_pin_without_it_is_unchanged(self):
 809 | +        base = TA.TestInventory.base(None)
 810 | +        plain = PK.inventory(**base)
 811 | +        self.assertNotIn("last_resort", plain["context_a"])                          # every other pin as before
 812 | +        g = PK.inventory(**base, last_resort=PK.last_resort_note({"clip_01": LJ}))
 813 | +        self.assertEqual(g["context_a"]["last_resort"]["verdicts"], {"clip_01": LJ})
 814 | +        rule = g["context_a"]["last_resort"]["rule"]
 815 | +        self.assertTrue(rule.startswith("ruling 87's last resort") and "under ruling 102" in rule, rule)
 816 | +        self.assertEqual({k: v for k, v in g["context_a"].items() if k != "last_resort"}, plain["context_a"])
 817 | +
 818 | +    def test_the_spotlight_pin_records_the_local_judge(self):
 819 | +        m = TS.moment()
 820 | +
 821 | +        def row(a_two):
 822 | +            return SPOT.inventory(*TS.package()[0:1], m, TS.FID_OK, [], True, [], TS.CX_OK, a_two[0], a_two,
 823 | +                                  {"verdict": "keep", "measured": True, "replayed": False},
 824 | +                                  {"ok": True, "edges": {"cuttable": True}}, TS.pre_of(m), m["spotlight_source"],
 825 | +                                  {"now": TS.NOW, "day": "d", "never_delivered": True,
 826 | +                                   "one_per_channel_day": True})["step_a_two_families"]
 827 | +        self.assertNotIn("last_resort", row(TS.two()))
 828 | +        judged = [TS.two()[0], dict(TS.two()[1], backend=LJ)]
 829 | +        r = row(judged)
 830 | +        self.assertEqual((r["status"], r["last_resort"]["verdicts"]), ("PASS", {m["moment_id"]: LJ}))
 831 | +
 832 | +    def test_state_line_1_is_told_once_in_the_ruling_s_words_and_plan_b_keeps_its_own(self):
 833 | +        for plan_b, words in ((False, "RULING 102: NO FASTER LEG OF STEP A'S SECOND FAMILY ANSWERED"),
 834 | +                              (True, "PLAN B WITH ONE OUTSIDE FAMILY")):
 835 | +            with tempfile.TemporaryDirectory() as d:
 836 | +                state = os.path.join(d, "STATE.md")
 837 | +                with open(state, "w") as f:
 838 | +                    f.write("line one\nline two\n")
 839 | +                judge = Judge()
 840 | +                r = router(d, [Leg(X), Leg(DS, P.Unavailable("down")), Leg(G, P.Unavailable("down")),
 841 | +                               Leg(GEM, P.Unavailable("down")), judge], state_md=state)
 842 | +                r.mode = lambda: "plan_b" if plan_b else "heimdall_first"
 843 | +                ms, srcs = pool(2)
 844 | +                a_by = {m["moment_id"]: dict(a_item(m["moment_id"]), backend=X) for m in ms}
 845 | +                for _ in range(2):                                           # two screens: one announcement
 846 | +                    PK.second_screen(r, {m["moment_id"]: m for m in ms}, a_by, srcs, TM.ctx(), log=lambda *_: None,
 847 | +                                     cache=None)
 848 | +                with open(state) as f:
 849 | +                    first = f.read().split("\n")[0]
 850 | +                self.assertEqual(first.count(words), 1, first)
 851 | +                self.assertTrue(first.endswith("| line one"), first)
 852 | +                self.assertEqual(judge.calls, 2)
 853 | +
 854 | +    def test_the_build_line(self):
 855 | +        self.assertEqual(PLG.ruling_102_line({"held_102": {"first": [], "second": []}, "last_resort_87": {}}, {}), "")
 856 | +        line = PLG.ruling_102_line({"held_102": {"first": ["a"], "second": ["b"]}, "last_resort_87": {"c": [LJ]}},
 857 | +                                   {"held_102": ["d"], "last_resort_87": {"e": [LJ]}})
 858 | +        self.assertIn("HELD for this build, retried next build", line)
 859 | +        self.assertIn("1 at step A's first screen, 1 at the medley's second screen ['b'], 1 at the spotlight's ['d']",
 860 | +                      line)
 861 | +        self.assertIn("THE LOCAL JUDGE (RULING 87'S LAST RESORT) GAVE 2 STEP-A VERDICT(S): ['c', 'e']", line)
 862 | +
 863 | +    def test_no_build_starts_at_19_dollars_and_one_starts_below(self):
 864 | +        """The orchestrator 13:02 Nov 14: the $16 stop passed with leave; at $19 stop and say so in capitals."""
 865 | +        self.assertIsNone(PLG.start_refused(18.99))
 866 | +        why = PLG.start_refused(19.0)
 867 | +        self.assertIn("at or over the $19.00 stop: no build starts", why)
 868 | +        self.assertIn("SAY IT ON STATE LINE 1 IN CAPITALS", why)
 869 | +
 870 | +
 871 | +class TestTheConfirmAheadIsGrokOnly(unittest.TestCase):
 872 | +    """RULING 101 beside 102: Grok's confirm-ahead never asks Gemini or the local judge (the second family's
 873 | +    fallbacks are the second screen's, asked only when it needs them)."""
 874 | +
 875 | +    def test_through_the_real_chain_grok_answers_ahead_and_no_fallback_is_ever_asked(self):
 876 | +        """qwen, audit 20261114_1349 C1: the confirm-ahead must GET Grok's verdict, not only avoid the rest. A real
 877 | +        Router over the five legs, the real prescreen and step_a: every new moment gets Grok's verdict; with Grok down,
 878 | +        none, and no other leg (deepseek, glm, Gemini, the judge) is ever asked."""
 879 | +        ms, srcs = pool(3)
 880 | +        for grok_down in (False, True):
 881 | +            with tempfile.TemporaryDirectory() as d:
 882 | +                legs = [Leg(X, P.Unavailable("down") if grok_down else None)] + [Leg(n) for n in LEGS[1:]]
 883 | +                r = router(d, legs)
 884 | +                res = PK.confirm_ahead(r, ms, srcs, TM.ctx(), {"heimdall/deepseek"}, {"deepseek"}, log=lambda *_: None,
 885 | +                                       cache=os.path.join(d, "c.json"))
 886 | +                self.assertEqual(res["asked"], 3)
 887 | +                self.assertEqual(res.get("by", {}), {} if grok_down else {m["moment_id"]: X for m in ms})
 888 | +                self.assertEqual([b.calls for b in legs[1:]], [0, 0, 0, 0])      # never a fallback ahead
 889 | +                self.assertEqual(legs[0].calls, 1)                               # one batch of 3
 890 | +
 891 | +    def test_every_vendor_but_grok_s_is_avoided_ahead(self):
 892 | +        legs = {n: Leg(n) for n in LEGS}
 893 | +        got = {}
 894 | +
 895 | +        def fake(router_, new, sources, ctx_, wv, wf, n=None, kind=None, cache=None, **k):
 896 | +            got.update(wv=set(wv), wf=set(wf), kind=kind)
 897 | +            return {}, {}, set(), set()
 898 | +        r = type("R", (), {"backends": legs})()
 899 | +        with mock.patch.object(PK, "prescreen", fake):
 900 | +            PK.confirm_ahead(r, [{"moment_id": "a"}], {}, None, {"heimdall/deepseek"}, {"deepseek"})
 901 | +        self.assertEqual(got["wv"], {"heimdall/deepseek", "heimdall/glm", "google", "local_judge"})
 902 | +        self.assertEqual(got["wf"], {"deepseek", "glm", "gemini", "gemma"})
 903 | +        self.assertEqual(got["kind"], "step_a_second")
 904 | +
 905 | +
 906 | +if __name__ == "__main__":
 907 | +    unittest.main()
 908 | diff --git a/tests/providers/test_deadline_table.py b/tests/providers/test_deadline_table.py
 909 | index ac2cb87..e1e770a 100644
 910 | --- a/tests/providers/test_deadline_table.py
 911 | +++ b/tests/providers/test_deadline_table.py
 912 | @@ -140,6 +140,11 @@ class TestRouter(unittest.TestCase):
 913 |          self.assertEqual(self.router(None).effective_deadline("context_verdict", r.backends[DS]), 120.0)   # no table
 914 |          self.assertEqual(r.role_deadline("context_verdict", r.backends[DS]), 120.0)   # the gateway's number, as before
 915 |          self.assertIsNone(r.role_deadline("context_verdict", r.backends[GROK]))
 916 | +        table = {"rows": dict(self.TABLE["rows"], **{f"{DS}|shadow86:context_verdict": {"deadline_s": 300.0},
 917 | +                                                    f"{DS}|probe87:{DS}": {"deadline_s": 300.0}})}
 918 | +        r = self.router(table)                       # glm, audit 20261114_1246 C2 M2: a shadow or a probe is no verdict
 919 | +        self.assertEqual(r.effective_deadline("shadow86:context_verdict", r.backends[DS], 120.0), 120.0)
 920 | +        self.assertEqual(r.effective_deadline(f"probe87:{DS}", r.backends[DS], 60.0), 60.0)
 921 |  
 922 |      def test_a_live_call_waits_its_own_deadline_and_the_breaker_measures_against_it(self):
 923 |          """Router.call itself: the deadline the call is held to (and the breaker's miss is measured against: ruling 99)
 924 | diff --git a/tests/providers/test_heimdall_health.py b/tests/providers/test_heimdall_health.py
 925 | index 139c4b1..fb1d0f4 100644
 926 | --- a/tests/providers/test_heimdall_health.py
 927 | +++ b/tests/providers/test_heimdall_health.py
 928 | @@ -403,6 +403,7 @@ class TestLocalJudge(unittest.TestCase):
 929 |          open(md, "w").write("21:50 ET: line one.\n")
 930 |          r = P.Router(cfg, env_path="/nonexistent", state_md=md)
 931 |          r.backends["local_judge:gemma3:27b"] = self.b
 932 | +        r.mode = lambda: "plan_b"           # Plan B's words (ruling 102's, outside Plan B: test_ruling_102)
 933 |          seen = {}
 934 |          orig = P._within
 935 |  
 936 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- STEP A (law L-s) screens each moment's own context twice. The FIRST screen (package.prescreen, kind step_a_first,
  chain [glm, deepseek, Grok], 2 clips a call) runs on every usable moment. Later, the SECOND screen
  (package.second_screen, kind step_a_second, 8 clips a call) runs on the moments that cleared, were cuttable and
  passed the hook rules; it asks for a verdict OFF the first verdict's vendor and family. A clip passes only if BOTH
  pass. Each Heimdall family is its own vendor under heimdall_first ("heimdall/deepseek", "heimdall/glm").
- Verdicts are cached across builds in a shared step-A cache, per back-end.
- At 12:24 and 12:40 ET two spotlight candidates with hooks rated 4 (Blockware Solutions 06d34e15, Strategy 933f9d33)
  died at the second screen with "STEP_A_UNAVAILABLE". Their first verdict was Grok's, so Grok was excluded; glm's and
  deepseek's breakers were open. Ruling 100 (committed e87f4c3f) gave deepseek its own 300 s deadline.
- RULING 87 (Nov 13): Plan B (Heimdall declared down) uses outside families, with the local judge last: the
  integrator's gemma3:27b on GPU0, reached through request files; it waits up to 40 min because a render comes first.
  Ruling 87 also says the local judge's use is announced on STATE line 1.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- providers.Router.call walks the chain:
  - a breaker-open leg is skipped (providers.py:1249);
  - DeadlineExceeded books a miss and moves on (:1287);
  - RequestRejected moves on (:1294);
  - Unavailable marks the leg down for the run and moves on (:1299);
  - when every leg fails it raises ProviderError("<role>: every back-end unavailable: ...") (:1338).
- context_integrity.step_a (context_integrity.py:321): with failover=True, an answer out of contract skips that model
  and asks the next (:355), each model once, until the chain is spent.
- package.prescreen (package.py:525): only a PARSED verdict is written to the cache (_cache_put(cache, new), :608). A
  failed batch writes nothing. second_screen (:748) calls it with failover=True and kind step_a_second.
- Router.chain (providers.py:780) uses the routing's "<role>:<kind>" list. Plan B's lists apply only while the shared
  health says Heimdall is down.
- Router.call announces the local judge on STATE line 1 the first time it asks it (heimdall_health.announce; once per
  router).
- providers.LocalJudgeBackend (providers.py:288): WAIT_S 2400 s (:305). No answer, an error or an unreadable file is
  Unavailable. It is free.
- google:gemini-2.5-pro uses the fenced GEMINI_API_KEY_MEDLEY. It already sits in heimdall_first's
  coherence_verdict:clips_alone list (ruling 06:12 (1)). It was probed once at 12:5x ET (answered in 2.2 s).
- package_pin.seal (package_pin.py:188) hashes the gates dict as it stands. gate_problems (:347) checks only each
  required row's status and replayed. Pins already sealed carry no new key and recompute unchanged.

THE ORCHESTRATOR'S RULING (13:02 ET Nov 14), verbatim:
"102. STEP_A_UNAVAILABLE MUST NEVER END A CLIP (two hook-4 candidates, Blockware Solutions 06d34e15 and Strategy
933f9d33, died of it twice). Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) ->
Heimdall glm -> GEMINI through the fenced key (probe it once; it is a different family from xAI and from Heimdall's
models, and PBX named it for exactly this) -> the local gemma3:27b on GPU0 through the integrator's judge service
(ruling 87's last resort, recorded as such on the pin and on STATE line 1). The first of these that ANSWERS gives the
second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if all four give no
answer is the clip held for THIS build (not refused), and retried next build. Do this BEFORE the next build if it is
small (the chain already exists for Plan B; this is the same chain reached without declaring Heimdall down)."
The same message: "THE $16 STOP: PASSED WITH MY LEAVE. Build on to the $20.00 cap ... At $19 stop and tell me on line 1
in capitals; do not start a build that would end over $20."

THE CHANGE (the diff follows):
1. model_providers.json: heimdall_first's context_verdict:step_a_second becomes [Grok, deepseek, glm,
   google:gemini-2.5-pro, local_judge:gemma3:27b], from [Grok, glm, deepseek].
   - Grok stays first: ruling 88 (c) has Grok confirm a Heimdall pass; for a Grok first verdict it is skipped as the
     first's vendor.
   - Plus the ruling's text, and notes on the two back-ends.
2. package.held_why(e) / is_held / HELD:
   - A step-A call that gives no verdict leaves "STEP_A_HELD (ruling 102): no step-A verdict (<error>); held for this
     build, retried next build" on its moments. This covers prescreen's failed batch (either screen), second_screen's
     raising chunk, its "no second verdict" default, and the writers' re-screen.
   - The one exception is CONTEXT_TOO_LONG, a ValueError that step_a raises before any call (law L-s never truncates):
     STEP_A_REFUSED.
   - A verdict that FAILS the clip is unchanged (a refusal, cached as a verdict).
   - The build records out.prescreen.held_102 {first, second}; second_vendor says "HELD: ...". The writers' re-screen
     says the held moments are out of this build only. The spotlight stops a held moment with "HELD (ruling 102) ..."
     and records held_102.
3. The local judge, recorded as such:
   - last_resort_of(verdicts) finds the back-ends named "local_judge:...".
   - out.prescreen.last_resort_87 and the spotlight's last_resort_87 record them.
   - On the pin: the medley's sealed context_a row and the spotlight's step_a_two_families row carry
     "last_resort": {rule, verdicts} ONLY when the local judge gave one of the pin's step-A verdicts. Every other pin is
     byte-identical in shape.
   - STATE line 1: the Router's first-use announcement names ruling 102 outside Plan B (Plan B keeps its words). The
     build prints a RULING 102 line (proof_ledger.ruling_102_line) in capitals for the local judge.
4. Ruling 101 beside 102 (carried from audit 20261114_1246 C2, glm H1):
   - confirm_ahead asks Grok only. Every vendor and family but xAI's is added to its writer sets, so Gemini and the
     local judge are never asked ahead.
   - step_a_plan is parallel only when a confirm leg is usable now (_confirm_leg: the step_a_second chain's first xAI
     back-end off the writers, not down, not breaker-open).
   - The plan reports why it is sequential.
5. glm M2 (same audit): a test that a shadow86:/probe87: role takes no deadline row (no code change).
6. The $19 stop: proof_ly.LY_STOP_USD 16.0 -> 19.0. proof_ledger.start_refused(spent0) is the start check; its line
   says to put it on STATE line 1 in capitals. The per-call cap is unchanged.
7. Tests: test_ruling_102.py (new, 16). It uses a real providers.Router over fake legs with the real step_a,
   prescreen and second_screen, and covers:
   - the chain order;
   - unavailable, past-deadline, refused and out-of-contract legs moving on;
   - held, never cached, and retried next build;
   - a failing verdict still a refusal;
   - the pin rows, the announcement, the build line and the $19 stop;
   - Grok-only confirm-ahead;
   - the writers' re-screen's default reason (no verdict, no reason) is HELD.
   Other suites updated: test_medley, test_ledger_build, test_deadline_table, test_heimdall_health (its ruling-87
   announcement test now names Plan B mode, since outside Plan B the words are ruling 102's). 31 mutations.

ATTACK:
(a) Can a moment still END (be refused, or have a failure cached) because no leg answered? Can a refusal by a real
    verdict now be mislabelled HELD and silently retried forever?
(b) The chain: can the second verdict come from the first verdict's own vendor or family? Is the order exactly the
    ruling's? Can a leg be skipped that should be asked, or asked twice?
(c) The local judge: can its verdict reach a pin without the record? Can the record change an existing pin's seal?
    Can the build hang on it longer than ruling 87 allows?
(d) Ruling 101 beside it: can the confirm-ahead now ask Gemini or the local judge? Can the plan go parallel with no
    usable confirm leg?
(e) The $19 stop and the $20 cap: can a build start at or over $19? Can one end over $20?
(f) Anything else that could seal a wrong pin, starve a build, or spend past ruling 48's cap.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
