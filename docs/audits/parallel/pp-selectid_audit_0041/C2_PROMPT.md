# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0041
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 314 s finish=stop usage in 17716 / out 9239 usd~0.192 (upper-bound price)

# Audit: pp-selectid-0041 — Rulings 94/95

Scope: I verified what the diff shows. Where a behaviour depends on code outside the diff (`verdict_of`, `trim_variant`, `affirmed`, `sv`, `pm`, `Rig`, `episode_turns`, `P.utc_z`, `PPN.WINDOW_H`), I say so.

## Findings

### 1. `<high>` — `pending_verdict` can seal a third-person hook with a synthetic (5, None) that no gate later re-checks on the medley path

`package.py:49–66` (diff lines 49–66): `_can_open(m, pending_verdict=True)` substitutes `sc = (5, None)` when `verdict_of(m)` is `None` and `third_opener(m)`. The comment says "the spotlight's ALONE >= 4 decides it later (never sealed without a verdict: stand_alone_check reads the real one)".

But the medley path calls `_can_open` in `spotlight.py` build (diff line 212) with `pending_verdict=True` for **every** opener, not only spotlight moments. If the medley's later stages (hook_ratings → check_edl / stand_alone_check) do not themselves rate a third-person hook, the synthetic 5 is the only affirmation ever consulted, and a hook with a real ALONE score of 3 could be sealed. The diff's `check_edl` change (stand_alone.py:268–271) does add third-person hooks to `need`, so the render-side `check_edl` will rate it — but only if `rate` is not None and the medley's gate actually calls `check_edl` with a working `rate`. From the diff alone I cannot see the call site that guarantees this for the medley (the only `check_edl`-adjacent evidence in the diff is the test at stand_alone.py:305–307, which passes `rate=...` explicitly). **Concrete scenario**: a medley whose hook is `"This is ultimately a bipartisan issue."` with no `scorer_verdict` and a later ALONE verdict of 3.0 — whether it seals depends on code not in the diff. If `check_edl`'s `rate` is wired, this downgrades to informational; if not, it's a real leak of the synthetic 5 into a sealed pin, violating L-m ("nothing measured is never a pass") — the 5 was never measured.

Related, same mechanism: `pending_verdict=True` is passed unconditionally at spotlight.py:212. For a moment that already has a verdict, `v` is truthy so the branch is inert — fine. For a non-third-person opener, `third_opener(m)` is False so the branch is inert — fine. So the leak, if any, is exactly the third-person-no-verdict case above.

### 2. `<high>` — `hook_trim` uses `SA._words(text)[:1]`, but the pool's trim decision runs on the *snapped* moment `v`, whose text may differ from the original's

`spotlight.py:129–131` (diff lines 129–131): `v, target = m, SNAP_TO_S + (TRIM_MARGIN_S if P.hook_trim(m) else 0.0)` — `hook_trim` is evaluated on the **original** `m`, good. But at diff lines 142–150, after snapping, `if P.hook_trim(v):` re-checks on the snapped `v`. If `snap()` extends the moment outward, its `text` is rebuilt from more sentences; its first word is still the same (snap extends at the *end* first: "the next ones first... then the ones before it" — the "sentence before" case, `a - 1`, **prepends** a sentence, changing the first word). Concrete scenario: a 12.9 s moment opening on "So" whose preceding sentence extends it to 14.2 s; the snapped `v` now opens on the *previous* sentence's first word (e.g. "Bitcoin"), so `P.hook_trim(v)` is False, the trim-variant block at 142–150 is skipped, and the moment enters the pool untrimmed — while `target` was already inflated by the margin. Result: the moment is snapped to 13.7+ but never trimmed, so ruling 94(a)'s "that variant is what is rated as an opener" is silently not enforced on the spotlight path; the untrimmed "So..." original can then be sealed as the spotlight hook if `SA.opener("hook", ...)` at diff line 151 passes — which, post-94, it does **not** for a conjunction... wait, it does not: `opener("hook")` returns False for a conjunction, and the `not ok and not P.third_opener(v)` guard (line 154) then rejects it. So the concrete failure is: **the moment is dropped from the pool entirely** (why[mid] = "it cannot open cold") even though ruling 94(a) promised its trim variant would open. Either way the 13.7 s margin was paid and no trimmed spotlight is produced. Test `test_a_conjunction_opener_is_trimmed...` (test_spotlight.py:465–480) uses `snap_rig([S5, so, S20, S5], 1)` — whether the snap extends backwards there depends on `snap_rig`/`S5` (not in the diff), so the test may not cover the backward-extension case.

### 3. `<medium>` — `next_attempt`'s `state()` reads `rs[0]` for `published_at`/`channel_name` without checking the rows agree

`spotlight.py:177–193` (diff lines 177–193): `pub = P.utc_z(rs[0].get("published_at"))` and `channel: rs[0].get("channel_name")`. Rows are grouped only by `video_id` (diff lines 172–175); nothing in the diff guarantees all rows for one `video_id` carry the same `published_at`/`channel_name`. If the adapter's rows for one video disagree (e.g. a re-ingest with a corrected `published_at`

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 83 s finish=stop usage in 17500 / out 453 usd~0.099 (upper-bound price)

<medium> pipeline/spotlight.py:170 (next_attempt def): 'now' parameter is declared but never read or used in the function body or any nested state() call; concrete input `next_attempt([{"video_id":"v1","published_at":"2026-11-13T10:00:00+00:00","episode":{"turns_per_min":2.0}}], {}, datetime(2026,11,14,0,0,tzinfo=timezone.utc), None)` produces identical output regardless of the passed `now` value, so "when the next qualifying episode could arrive" (ruling 95 docstring) cannot depend on current time.  
<medium> pipeline/spotlight.py:178: `pub = P.utc_z(...)` while the only new import is `package_pin as PPN`; verifiable that no local `P=` binding exists inside next_attempt (other file-level `P` / `PP` imports are outside the added function and unshown).  
<medium> pipeline/package.py:59 and spotlight.py:212: `pending_verdict=True` path fakes `(5, None)` only for third_opener with no verdict; concrete input `{"text":"This is ultimately a bipartisan issue for Bitcoin.","eligibility":{"hook":{"ok":False,"reasons":["opener"]}},"scorer_verdict":None}` reaches `openers` dict in spotlight.build but is rejected by stand_alone.check_edl(..., rate=None) per the added test at test_stand_alone.py:307 (fail-closed preserved).  
No verifiable violations of SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, L-b/L-c edge-word fidelity, L-j release auth on exact bytes, or L-k canon.py routing from the diff alone (all new paths route through existing stand_alone.opener / trim_variant / hook_onset_for / check_edl). Tests cover first/second-person pass-without-verdict, third-person requiring affirming score on exact text, trim-variant-only for TRIM_WORDS hooks, unclean-trim HOLD, and next_attempt state facts.  

SHIP: yes with conditions (remove or implement the unused 'now'; qualify P.utc_z or confirm module scope)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 35 s finish=stop usage in 19375 / out 1847 usd~0.086 (upper-bound price)

I have reviewed the diff against the governing laws and the specific audit checklist. Here are my findings.

<critical>
**1. `pending_verdict` bypasses the "Fail Closed" law (L-m / M12) in `spotlight.py`**
*   **File:** `pipeline/spotlight.py` (lines 212-213 in diff, corresponding to `build()` function) and `pipeline/package.py` (lines 59-60 in diff, `_can_open`).
*   **Scenario:** In `spotlight.py`'s `build()`, the code calls `P._can_open(m, pending_verdict=True)`. Inside `_can_open`, if `pending_verdict` is True and the moment is a `third_opener` but has no verdict (`v is None`), it sets `sc = (5, None)`. This hardcodes a score of 5 (pass) to allow the moment to proceed to the `openers` list.
*   **Violation:** Law L-m states "nothing measured is never a pass." The spotlight's `ALONE` scorer gate (which requires a score >= 4) is intended to be the *decider*. By injecting a fake score of 5 in `_can_open`, the code allows a third-person hook with **no measured verdict** to pass the initial eligibility check. While the spotlight `pool()` function later checks `SA.opener` (which will fail closed if `score is None`), the `build()` function's logic relies on `_can_open` to filter candidates. If the `pool()` check is bypassed or if the flow changes, this hardcoded `5` creates a path where an unmeasured hook is treated as affirmed. More critically, the audit requirement states: *"pending_verdict cannot leak into the medley or into a sealed pin"*. The `pending_verdict` flag is explicitly designed for the spotlight to *defer* judgment, but the implementation in `_can_open` actively *fakes* a pass (`sc = (5, None)`) rather than just allowing the check to proceed to the next stage. This violates the spirit of "Fail Closed" because it assumes success before measurement.
*   **Fix:** `_can_open` should not fabricate a score. It should return `True` (allowing the moment to proceed to the spotlight's specific `ALONE` gate) only if the *other* conditions (hook onset, etc.) are met, leaving the pronoun judgment entirely to the spotlight's `pool()` or `build()` specific scorer call, which must fail closed if the verdict is missing.

<high>
**2. `hook_trim` variant may violate SNAP LIMIT / SELECTION LOCK if the trim word is not in the gap**
*   **File:** `pipeline/package.py` (lines 33-38 in diff, `hook_trim` function) and `pipeline/spotlight.py` (lines 142-150 in diff, `pool` function).
*   **Scenario:** `hook_trim` checks if the first word is in `TRIM_WORDS`. The `pool` function then calls `P.trim_variant(v, sources)`. The `trim_variant` function (not shown in diff but implied by context) cuts the first word.
*   **Violation:** The **SNAP LIMIT** law states: *"a cut may move only inside the heard gap between the chosen sentence and its neighbour... it may never add or drop a word."* However, Ruling 33 explicitly allows dropping *one* leading word if it's a conjunction/reply word. The risk here is that `trim_variant` might drop a word that is *not* actually a standalone conjunction in the audio (e.g., if the ASR merged "So" with the next word, or if the "So" is part of a compound). The code relies on `SA._words` (text-based) to identify the trim word. If the text says "So Bitcoin..." but the audio onset of "So" is not cleanly separable (i.e., no gap), the `hook_onset` check in `spotlight.py` `build()` (line 210-211) checks `trim.get("pass")`. This is good. However, in `package.py` `build()` (line 75-77), the trim variant is added to the pool *before* the `hook_onset` check is performed in the spotlight. If this trim variant is used in a **Medley** (not just Spotlight), does the Medley path verify the `hook_onset` trim cleanliness? The diff shows `spotlight.py` `build()` checking it. The `package.py` `build()` adds the trim to `ms`. If the Medley renderer uses this `ms` list, it must also verify the trim cut. The audit says *"a trimmed hook is only ever the variant... and is sealed with its affirmation"*. If the Medley path does not re-verify the `hook_onset` trim pass for the `~trim` variant, it could seal a pin with a dirty cut.
*   **Fix:** Ensure that any path using the `~trim` variant (Medley or Spotlight) explicitly checks `hook_onset["trim"]["pass"]` before sealing.

<medium>
**3. `next_attempt` uses `published_at` which may be timezone-naive or inconsistent**
*   **File:** `pipeline/spotlight.py` (lines 178-190 in diff, `next_attempt` function).
*   **Scenario:** The function parses `pub` using `datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ")`. If the `published_at` field in the database/adapter rows contains a timezone offset other than `Z` (e.g., `+00:00` or `+05:00`), `strptime` will raise a `ValueError`.
*   **Violation:** **M12 FAIL CLOSED**: An exception here would crash the `next_attempt` call. While `proof_ledger.py` wraps the call in a `try/except` (line 351-352), this means the "Ruling 95" report will be 

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0041 (rulings 94 + 95), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes with conditions; qwen3.8-27b SHIP no (one critical); glm-5.3-flash SHIP yes with
conditions.

## Implemented

1. qwen <critical> / glm <high> 1, 8: _can_open(pending_verdict=True) put a synthetic (5, None) in place of a missing
   verdict. It never sealed anything: the spotlight's ALONE >= 4 gate reads the real verdict, and stand_alone_check
   reads it at the pin. The placeholder is gone all the same. An explicit `defer` (spotlight only, a third-person
   opener with NO verdict yet) skips the opener test without assuming a score, and the medley never defers. glm's
   condition is met with a test: a third-person spotlight whose ALONE verdict is 3.0 is refused by the opener rule;
   with no verdict it waits and is refused at the ALONE stage ("no rating"); at 4.0 it reaches the package.
2. glm <high> 24: the pool's trim variant is now checked again by usable() and against the pool's ids before it
   replaces the snapped moment.
3. grok: next_attempt's `now` was unused. It now gives each upload's age in hours (a measured fact for ruling 95).
4. The integrator's merged stand_alone.py (409188ef, sha256 14f30115...) replaces this branch's copy byte for byte:
   the same rule, with its comments and messages. Its test file is not taken: it imports run_fresh.moments_screen,
   which only the render side has. This branch keeps its own ruling-94 cases.

## Refuted, with evidence

- glm <high> 2 (the snap may prepend a sentence, so the trim never happens): when the snap adds the sentence BEFORE,
  the moment no longer opens on the conjunction. The new first word is judged by the opener rule like any other, and
  the moment is trimmed only when it still opens on a trim word. That is the ruling (a conjunction is the opener's
  fault only when it is heard first).
- grok: P.utc_z is in module scope (spotlight.py imports package as P at the top).
- glm <high> 15 (affirmed() for moments=True reads the score alone): this is ruling 60's moments rule, the same as
  the clip rule's (score >= 3.5 alone).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0041/C2_STEP.diff (563 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index 65c73c4..213a069 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -436,7 +436,7 @@ def _span(span, ctx, role):
   6 |      if conj:
   7 |          targets.append(f"opens on the conjunction{'s' if len(conj) > 1 else ''} {' '.join(conj)!r}")
   8 |      if rest:                       # pronoun / reply-word openers are not in L-o: still hard, after any conjunction too
   9 | -        sc = (ctx.scorer or {}).get(span.key) if role == "clip" else None
  10 | +        sc = (ctx.scorer or {}).get(span.key) if role in ("clip", "hook") else None   # ruling 94 (b): the hook too
  11 |          ok, why = stand_alone.opener(role, rest, *(sc if sc else (None, None)))
  12 |          if not ok:
  13 |              R("opener", why + (f" (after {' '.join(conj)!r})" if conj else ""))
  14 | diff --git a/pipeline/package.py b/pipeline/package.py
  15 | index 07c997d..4736b4f 100644
  16 | --- a/pipeline/package.py
  17 | +++ b/pipeline/package.py
  18 | @@ -1167,7 +1167,8 @@ def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name, ex
  19 |          left = [(m, no_role_on_screen(m), no_topic(m)) for m in
  20 |                  ({k: x for k, x in m.items() if k != "scorer_verdict"} for m in ms)]
  21 |          ask = [m for m, o, t in left if o and not t] + \
  22 | -            [v for m, o, t in left if o or t for v in [trim_variant(m, sources)] if v]
  23 | +            [v for m, o, t in left if o or t or hook_trim(m) for v in [trim_variant(m, sources)] if v] + \
  24 | +            [m for m, o, t in left if not o and not t and third_opener(m)]      # ruling 94 (a), (b): the hook's
  25 |          have = {(m["moment_id"], text_sha(m["text"])) for m in ask}
  26 |          for m in extra or ():                            # ruling 90: once each (same id and text)
  27 |              k = (m["moment_id"], text_sha(m["text"]))
  28 | @@ -1221,14 +1222,37 @@ def can_open(m):
  29 |      return _can_open(m)
  30 |  
  31 |  
  32 | -def _can_open(m):
  33 | +def hook_trim(m):
  34 | +    """RULING 94 (a): the moment opens on a conjunction or reply word that ruling 33's ONE-word trim may cut
  35 | +    (TRIM_WORDS): its trim variant is what may open, whatever its clip role."""
  36 | +    import stand_alone as SA
  37 | +    w = SA._words(m.get("text") or "")[:1]
  38 | +    return bool(w) and w[0] in TRIM_WORDS
  39 | +
  40 | +
  41 | +def third_opener(m):
  42 | +    """RULING 94 (b): the moment opens on a third-person or demonstrative pronoun: as a hook it needs the clip scorer's
  43 | +    affirmation (stand_alone.THIRD)."""
  44 | +    import stand_alone as SA
  45 | +    w = SA._words(m.get("text") or "")[:1]
  46 | +    return bool(w) and w[0] in SA.THIRD
  47 | +
  48 | +
  49 | +def _can_open(m, pending_verdict=False):
  50 |      """Whether a moment may OPEN a line-up: hook-eligible, its hook onset measured and passed (G17a), a first word the
  51 |      render's STAND_ALONE takes for a hook (stand_alone.opener), and, once the build has rated the pool's hooks (RULING
  52 |      59: build() sets "hook_rating" on every cleared moment before any line-up), rated >= HOOK_MIN on the hook's own job
  53 |      (an unmeasured rating is never a pass, law L-m). A moment without the key is judged as before ruling 59."""
  54 |      import stand_alone as SA
  55 | -    if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True
  56 | -            and SA.opener("hook", m.get("text") or "")[0]):
  57 | +    v = verdict_of(m)                                    # RULING 94 (b): the scorer's verdict on its current text
  58 | +    sc = (v["score"], v["fault"]) if v else (None, None)
  59 | +    defer = pending_verdict and v is None and third_opener(m)    # the spotlight only: a third-person opener with NO
  60 | +    #   verdict yet is left to its own ALONE >= 4 gate, which reads the real verdict; nothing is assumed about it here,
  61 | +    #   and the medley never defers (audit 0041 C1: qwen, glm)
  62 | +    opens = lambda: defer or SA.opener("hook", m.get("text") or "", *sc, moments=True)[0]
  63 | +    hook = (m.get("eligibility") or {}).get("hook") or {}
  64 | +    elig = hook.get("ok") or (set(hook.get("reasons") or []) == {"opener"} and opens())   # the ledger had no verdict
  65 | +    if not (elig and (m.get("hook_onset") or {}).get("pass") is True and opens()):
  66 |          return False
  67 |      if "hook_rating" not in m:
  68 |          return True                                      # not rated yet: judged as before ruling 59
  69 | @@ -2253,11 +2277,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  70 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
  71 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
  72 |      admitted = sorted(m["moment_id"] for m in ms if verdict_of(m) and m["moment_id"] not in no_role)   # ruling 56
  73 | -    trims = {m["moment_id"]: with_verdict(v, scorer["index"]) for m in ms if m["moment_id"] in no_role
  74 | -             for v in [trim_variant(m, sources)] if v}
  75 | +    trims = {m["moment_id"]: with_verdict(v, scorer["index"]) for m in ms
  76 | +             if m["moment_id"] in no_role or hook_trim(m)                   # ruling 94 (a): a hook's trim variant
  77 | +             for v in [trim_variant(m, sources)] if v}                      # joins the pool (the original stays a clip)
  78 |      trim_out = {k: why for k, v in trims.items() for why in [trim_refused(v)] if why}   # ruling 56: never sealed
  79 |      trims = {k: v for k, v in trims.items() if k not in trim_out}
  80 | -    ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42)
  81 | +    ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42);
  82 | +    #   a variant of a moment that keeps its own place (ruling 94 a) sits beside it: one line-up never takes both (one
  83 | +    #   video at most once, L-y 4)
  84 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  85 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  86 |      wv, wf = _writers(router)
  87 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
  88 | index effb73e..88ae8ad 100644
  89 | --- a/pipeline/spotlight.py
  90 | +++ b/pipeline/spotlight.py
  91 | @@ -60,6 +60,8 @@ CLOSING_MAX_WORDS = PP.SPOT_CLOSING_MAX_WORDS   # 12
  92 |  COMMENT_MAX_LINES = 2                  # ruling 90: "one or two short casual lines"
  93 |  COMMENT_MAX_WORDS = 30
  94 |  MARKER_TOL_S = 1.0                     # = ledger_build.MARKER_EDGE_S: a caption marker this close to an edge is not in
  95 | +TRIM_MARGIN_S = 1.0                    # RULING 94 (a): a moment to be trimmed is snapped this much further, so the
  96 | +                                       # ONE trimmed word never takes it back under SNAP_TO_S
  97 |  LAYOUTS = ("conversation", "first_hand", "recap", "reaction", "other")
  98 |  LAYOUT_OK = ("conversation", "first_hand")
  99 |  CONVERSATION_TPM = 1.0                 # ruling 92's caption half (see source_test)
 100 | @@ -106,7 +108,7 @@ def record_spotlit(path, row):
 101 |      os.replace(path + ".tmp", path)
 102 |  
 103 |  
 104 | -def snap(m, sources, ctx, captions_for=None):
 105 | +def snap(m, sources, ctx, captions_for=None, target=SNAP_TO_S):
 106 |      """RULING 90 with ruling 32's snap: a moment shorter than SNAP_TO_S is snapped OUTWARD to the speaker's whole
 107 |      thought: whole sentences of the SAME word record, the next ones first (the speaker going on), then the ones before
 108 |      it, until it lasts SNAP_TO_S, never past SPOT_S[1] and never across a caption speaker-change marker (ruling 69's
 109 | @@ -145,10 +147,10 @@ def snap(m, sources, ctx, captions_for=None):
 110 |      dur, why = measure(a, b)
 111 |      if dur is None:
 112 |          return None, f"the moment itself: {why}"
 113 | -    if dur >= SNAP_TO_S:
 114 | +    if dur >= target:
 115 |          return m, None                                 # long enough: no snap, the moment as it is
 116 |      blocked = []
 117 | -    while dur < SNAP_TO_S:
 118 | +    while dur < target:
 119 |          step = None
 120 |          for na, nb, side in ((a, b + 1, "the next sentence"), (a - 1, b, "the sentence before")):
 121 |              if na < 0 or nb >= n:
 122 | @@ -203,11 +205,11 @@ def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), ca
 123 |          if m["channel_id"] in taken:
 124 |              why[mid] = f"ruling 90: this channel already has a spotlight on {day} (ET)"
 125 |              continue
 126 | -        v = m
 127 | -        if float(m["duration_s"]) < SNAP_TO_S:
 128 | -            v, w = snap(m, sources, ctx, captions_for)
 129 | +        v, target = m, SNAP_TO_S + (TRIM_MARGIN_S if P.hook_trim(m) else 0.0)
 130 | +        if float(m["duration_s"]) < target:
 131 | +            v, w = snap(m, sources, ctx, captions_for, target=target)
 132 |              if v is None:
 133 | -                why[mid] = f"ruling 90: {m['duration_s']} s is under {SNAP_TO_S:g} s and the snap fails: {w}"
 134 | +                why[mid] = f"ruling 90: {m['duration_s']} s is under {target:g} s and the snap fails: {w}"
 135 |                  continue
 136 |              ok, w2 = P.usable([v], ctx, delivered, optout, seg_max=SPOT_S[1])
 137 |              if not ok:
 138 | @@ -217,9 +219,22 @@ def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), ca
 139 |          if v["moment_id"] in seen:
 140 |              why[mid] = f"the same span as {v['moment_id']}, already in the pool"
 141 |              continue
 142 | +        if P.hook_trim(v):                             # RULING 94 (a): ruling 33's one-word trim variant is what
 143 | +            t = P.trim_variant(v, sources)             # opens; the trim must cut cleanly (build: hook_onset's trim
 144 | +            if t is None:                              # record) and the ALONE scorer must affirm it
 145 | +                why[mid] = f"ruling 94 (a): it opens on {SA._words(v.get('text') or '')[:1]} and has no trim variant"
 146 | +                continue
 147 | +            if t["duration_s"] < SNAP_TO_S:
 148 | +                why[mid] = f"ruling 94 (a): trimmed, {t['duration_s']} s is under {SNAP_TO_S:g} s"
 149 | +                continue
 150 | +            ok_t, w_t = P.usable([t], ctx, delivered, optout, seg_max=SPOT_S[1])     # the variant is a moment too
 151 | +            if not ok_t or t["moment_id"] in seen:
 152 | +                why[mid] = f"ruling 94 (a): its trim variant is out: {w_t.get(t['moment_id']) or 'already in the pool'}"
 153 | +                continue
 154 | +            v = t
 155 |          ok, w = SA.opener("hook", v.get("text") or "")
 156 | -        if not ok:
 157 | -            why[mid] = f"ruling 90: it cannot open cold (the render's STAND_ALONE hook rule): {w}"
 158 | +        if not ok and not P.third_opener(v):           # RULING 94 (b): a third-person opener is judged by the ALONE
 159 | +            why[mid] = f"ruling 90: it cannot open cold (the render's STAND_ALONE hook rule): {w}"   # scorer (>= 4)
 160 |              continue
 161 |          top = P.no_topic(v)
 162 |          if top:
 163 | @@ -269,6 +284,45 @@ def source_test(turns, layout):
 164 |                                        if (turns or {}).get("measured") else "; captions unmarked")
 165 |  
 166 |  
 167 | +def next_attempt(rows, word_pass, now, captions_for=None):
 168 | +    """RULING 95 (00:40 ET Nov 14): when a build ends with no medley and no spotlight, when the next qualifying episode
 169 | +    could arrive. The NEWEST conversation upload among the adapter's rows: caption turns from pp-ingest's `episode`
 170 | +    (mine-hook/2 rows), else episode_turns(), at least CONVERSATION_TPM a minute (an unmarked episode is not counted:
 171 | +    unknown). Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready or still
 172 | +    waiting (word_pass: ledger_build.word_pass_index's {moment_id: row}). -> {"conversation": {...} or None,
 173 | +    "newest_upload": {...} or None}."""
 174 | +    from datetime import datetime, timedelta, timezone
 175 | +    import package_pin as PPN
 176 | +    by_vid = {}
 177 | +    for r in rows or ():
 178 | +        if isinstance(r, dict) and r.get("video_id"):
 179 | +            by_vid.setdefault(r["video_id"], []).append(r)
 180 | +
 181 | +    def state(vid, rs):
 182 | +        pub = P.utc_z(rs[0].get("published_at"))
 183 | +        ep = next((r.get("episode") for r in rs if isinstance(r.get("episode"), dict)), None)
 184 | +        tpm, frm = (ep or {}).get("turns_per_min"), "pp-ingest episode"
 185 | +        if not isinstance(tpm, (int, float)) and not (ep or {}).get("unmarked"):
 186 | +            t = episode_turns(vid, captions_for)
 187 | +            tpm, frm = t.get("turns_per_min"), "the caption record (recount)"
 188 | +        passes = {}
 189 | +        for r in rs:
 190 | +            k = f"{(r.get('mined') or {}).get('pass')}/{(r.get('mined') or {}).get('prompt_version')}"
 191 | +            passes[k] = passes.get(k, 0) + 1
 192 | +        ready = sum(1 for r in rs if (word_pass.get(r.get("moment_id")) or {}).get("sentence_ready"))
 193 | +        exp = (datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) +
 194 | +               timedelta(hours=PPN.WINDOW_H)).strftime("%Y-%m-%dT%H:%M:%SZ") if pub else None
 195 | +        age = E.age_hours(rs[0].get("published_at"), now)
 196 | +        return {"video_id": vid, "channel": rs[0].get("channel_name"), "published_at": pub, "expires_at": exp,
 197 | +                "age_h": round(age, 1) if age is not None else None,
 198 | +                "turns_per_min": tpm, "turns_from": frm, "rows": len(rs), "passes": passes,
 199 | +                "word_pass_ready": ready, "word_pass_waiting": len(rs) - ready}
 200 | +    sts = sorted((state(v, rs) for v, rs in by_vid.items()), key=lambda x: x["published_at"] or "", reverse=True)
 201 | +    conv = [x for x in sts if isinstance(x["turns_per_min"], (int, float)) and x["turns_per_min"] >= CONVERSATION_TPM]
 202 | +    return {"conversation": conv[0] if conv else None, "newest_upload": sts[0] if sts else None,
 203 | +            "rule": f"the newest upload with >= {CONVERSATION_TPM:g} caption turns a minute (ruling 95)"}
 204 | +
 205 | +
 206 |  LAYOUT_PROMPT = """You see a contact sheet of {n} frames of ONE clip from a Bitcoin video, left to right and top to
 207 |  bottom. The clip's words, as spoken: "{text}"
 208 |  From the frames only, classify the SOURCE's format:
 209 | @@ -748,8 +802,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 210 |          m["hook_onset"] = P.hook_onset_for(m, sources, work_dir, hk)
 211 |          m.pop("hook_rating", None)                       # a rating is this build's own (its cache's)
 212 |          m.pop("visual_hook_block", None)
 213 | -        if P._can_open(m):
 214 | -            openers[mid] = m
 215 | +        trim = (m["hook_onset"] or {}).get("trim") or {}
 216 | +        if m.get("trimmed_leading") and trim.get("pass") is not True:          # RULING 94 (a): the trim cuts cleanly
 217 | +            stop(mid, f"ruling 94 (a): the trimmed cut is not clean: {trim.get('why') or 'not measured'}")
 218 | +        elif P._can_open(m, pending_verdict=True):     # ruling 94 (b): a third-person opener waits for the ALONE
 219 | +            openers[mid] = m                           # scorer, which must give >= 4 below
 220 |          else:
 221 |              stop(mid, f"it cannot open cold: hook eligibility, G17a ({(m['hook_onset'] or {}).get('why')}) or the "
 222 |                        f"render's hook rule")
 223 | diff --git a/pipeline/stand_alone.py b/pipeline/stand_alone.py
 224 | index a8b2f45..201634f 100644
 225 | --- a/pipeline/stand_alone.py
 226 | +++ b/pipeline/stand_alone.py
 227 | @@ -24,6 +24,11 @@ PRONOUNS = {"i", "me", "my", "it", "its", "this", "that", "these", "those", "the
 228 |  REPLY_FRAGMENTS = {"yeah", "yes", "yep", "no", "nope", "right", "exactly", "absolutely", "totally", "sure", "okay",
 229 |                     "ok", "oh", "well", "um", "uh", "agreed", "true", "correct", "indeed", "anyway", "anyways"}
 230 |  BACKREF = {"it", "its", "this", "that", "these", "those", "they"}
 231 | +# RULING 94 (b) (orchestrator 2026-11-14 '00:40'): a first- or second-person pronoun opener is NOT a cold-open fault
 232 | +# ("I will bet you one Bitcoin that..." is a fine first line); only a third-person or demonstrative pronoun with no
 233 | +# referent in the clip is, and the clip scorer judges exactly that (affirmed: it opens; else a fault, fail closed)
 234 | +FIRST_SECOND = {"i", "me", "my", "we", "us", "our", "you", "your"}
 235 | +THIRD = PRONOUNS - FIRST_SECOND
 236 |  BITCOIN = re.compile(r"\b(bitcoin|btc)\b", re.I)
 237 |  FIGURE = re.compile(r"\$\s?\d|\d\s?%|\bpercent\b|\b\d{1,3}(?:\s?,\s?\d{3})+\b|\b\d+(?:\s?\.\s?\d+)?\s?(?:k|thousand|million|billion)\b",
 238 |                      re.I)
 239 | @@ -78,9 +83,15 @@ def opener(kind, text, score=None, fault=None, moments=False):
 240 |          return False, "empty segment"
 241 |      w = ws[0]
 242 |      if kind == "hook":
 243 | -        for group, name in ((PRONOUNS, "pronoun"), (CONJUNCTIONS, "conjunction"), (REPLY_FRAGMENTS, "reply fragment")):
 244 | -            if w in group:
 245 | +        for group, name in ((CONJUNCTIONS, "conjunction"), (REPLY_FRAGMENTS, "reply fragment")):
 246 | +            if w in group:          # ruling 94 (a): only ruling 33's one-word trim variant opens (check_edl's trim rule)
 247 |                  return False, f"hook opens on the {name} {w!r}: nothing is heard before a hook"
 248 | +        if w in THIRD:              # ruling 94 (b): a referent the clip may not carry: the scorer judges it
 249 | +            if score is None:
 250 | +                return False, f"hook opens on the pronoun {w!r} and no clip-scorer verdict is available (fail closed)"
 251 | +            if affirmed(score, fault, moments):
 252 | +                return True, f"hook opens on {w!r}; the clip scorer affirms it stands alone ({score}, fault {fault})"
 253 | +            return False, f"hook opens on {w!r}; the clip scorer does not affirm it stands alone ({score}, fault {fault})"
 254 |          return True, f"opens on {w!r}"
 255 |      if w in CONJUNCTIONS or w in REPLY_FRAGMENTS:
 256 |          if score is None:
 257 | @@ -164,15 +175,17 @@ def trimmed_opener(word, score, fault, moments=False):
 258 |  
 259 |  def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None, moments=False):
 260 |      """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
 261 | -    clips opening on a conjunction / reply fragment (the clip scorer) and for every segment whose lock trims a leading
 262 | -    word (ruling 33 part 2, the hook included); without it they fail closed.
 263 | +    clips opening on a conjunction / reply fragment (the clip scorer), for every segment whose lock trims a leading
 264 | +    word (ruling 33 part 2, the hook included) and for a hook opening on a third-person or demonstrative pronoun
 265 | +    (ruling 94 (b)); without it they fail closed.
 266 |      screen (ruling 34, a moments package's carried BTC_SCREEN, compiled): each segment's TOPIC test is the screen,
 267 |      and the medley must name Bitcoin (BITCOIN: bitcoin / btc) in at least one segment, the hook or a clip, in the
 268 |      speaker's own words. screen None: every segment names the subject, as before (the story path).
 269 |      moments (ruling 60, a moments pin): the scorer's verdict is read with affirmed(..., moments=True), the score alone."""
 270 |      segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
 271 |      need = [(label, s) for label, kind, s in segs if trimmed_word(s) or (kind == "clip" and _words(s.get("text"))[:1]
 272 | -            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS))]
 273 | +            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS))
 274 | +            or (kind == "hook" and _words(s.get("text"))[:1] and _words(s.get("text"))[0] in THIRD)]   # ruling 94 (b)
 275 |      scores, rate_error = {}, None
 276 |      if need and rate is not None:
 277 |          try:
 278 | diff --git a/pipeline/test_stand_alone.py b/pipeline/test_stand_alone.py
 279 | index cdb3ce3..972272f 100644
 280 | --- a/pipeline/test_stand_alone.py
 281 | +++ b/pipeline/test_stand_alone.py
 282 | @@ -23,16 +23,28 @@ DATADASH = ("Bitcoin has now seen a 16 % decline from the overall high from $88
 283 |  
 284 |  class TestOpener(unittest.TestCase):
 285 |      def test_hook_must_fail(self):
 286 | -        for text in (RUN6_HOOK, "I don't check it on an hourly basis. It seemed to have bounced.",
 287 | -                     "It seemed to have bounced very nicely at $74,000.", "Yeah, Bitcoin is down 16 %.",
 288 | -                     "So Bitcoin is down.", "We've seen Bitcoin lose 16 %."):
 289 | +        for text in (RUN6_HOOK, "It seemed to have bounced very nicely at $74,000.", "Yeah, Bitcoin is down 16 %.",
 290 | +                     "So Bitcoin is down.", "They sold it all at the bottom."):
 291 |              ok, why = S.opener("hook", text)
 292 |              self.assertFalse(ok, (text, why))
 293 |  
 294 |      def test_hook_must_pass(self):
 295 | -        for text in (DATADASH, "Michael Saylor is back. Strategy purchased 1 ,036 Bitcoin."):
 296 | +        for text in (DATADASH, "Michael Saylor is back. Strategy purchased 1 ,036 Bitcoin.",
 297 | +                     "I don't check it on an hourly basis. It seemed to have bounced.",      # RULING 94 (b): first or
 298 | +                     "We've seen Bitcoin lose 16 %.", "I will bet you one Bitcoin that it gets there."):   # second person
 299 |              self.assertTrue(S.opener("hook", text)[0], text)
 300 |  
 301 | +    def test_ruling_94_a_third_person_hook_needs_the_scorer(self):
 302 | +        text = "This is ultimately a bipartisan issue."
 303 | +        self.assertFalse(S.opener("hook", text)[0])                                  # no verdict: fail closed
 304 | +        self.assertTrue(S.opener("hook", text, 4.0, "none", moments=True)[0])
 305 | +        self.assertFalse(S.opener("hook", text, 3.0, "none", moments=True)[0])
 306 | +        self.assertEqual(S.PRONOUNS, S.FIRST_SECOND | S.THIRD)
 307 | +        edl = {"hook": {"channel": "H", "text": text}, "clips": []}
 308 | +        r = S.check_edl(edl, rate=lambda ps: {p["pid"]: (4.0, "r", "none") for p in ps}, moments=True)
 309 | +        self.assertTrue(r["rows"][0]["opener"]["pass"], r["rows"][0])                # the hook is rated (check_edl)
 310 | +        self.assertFalse(S.check_edl(edl, rate=None, moments=True)["rows"][0]["opener"]["pass"])
 311 | +
 312 |      def test_clip_conjunction_needs_the_scorer(self):
 313 |          self.assertTrue(S.opener("clip", RUN6_CLIP01, 5.0, "none")[0])
 314 |          self.assertFalse(S.opener("clip", RUN6_CLIP01, 3.0, "starts_mid_thought")[0])
 315 | @@ -102,7 +114,8 @@ class TestAutoSelectionScreen(unittest.TestCase):
 316 |      def test_selection_uses_the_same_rule(self):
 317 |          import editorial_select as es
 318 |          subj = S.subject_terms("Binance exchange", "Binance hacked for six billion dollars")
 319 | -        self.assertFalse(es._stand_alone_ok("hook", "We just had, of course, Binance with $6 .3 billion in hacks.", subj)[0])
 320 | +        self.assertFalse(es._stand_alone_ok("hook", "They just had, of course, Binance with $6 .3 billion in hacks.",
 321 | +                                            subj)[0])                # ruling 94 (b): a third-person opener, no verdict
 322 |          self.assertTrue(es._stand_alone_ok("hook", "Binance confirmed the hack this morning. It means six billion "
 323 |                                                     "dollars of customer money left the exchange.", subj)[0])
 324 |          self.assertFalse(es._stand_alone_ok("clip", RUN6_CLIP02, S.subject_terms("Bitcoin / US spot Bitcoin ETFs"))[0])
 325 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
 326 | index cd89e2d..583fe06 100644
 327 | --- a/tests/eligibility/test_eligibility.py
 328 | +++ b/tests/eligibility/test_eligibility.py
 329 | @@ -194,6 +194,14 @@ class TestSource(unittest.TestCase):
 330 |          self.assertIs(E.eligible(nobody, ctx("evidence")).facts["layout_eligible"], False)
 331 |          self.assertIn("layout_ineligible", E.eligible(nobody, ctx("clip")).names())
 332 |  
 333 | +    def test_ruling_94_pronoun_openers_on_the_hook(self):
 334 | +        first = source(["I will bet you one Bitcoin that it gets back to the highs before the end of next year."])
 335 | +        self.assertNotIn("opener", E.eligible(E.Span(first, 0, 0), ctx("hook")).names())    # (b): no fault
 336 | +        third = source(["They sold every Bitcoin they had at the very bottom of the market last week."])
 337 | +        r = E.eligible(E.Span(third, 0, 0), ctx("hook"))
 338 | +        self.assertIn("opener", r.names())                         # no verdict at the ledger: the pin stage decides
 339 | +        self.assertIn("no clip-scorer verdict", r.why())
 340 | +
 341 |      def test_on_screen_needs_a_sentence_ready_word_record(self):
 342 |          seg = source([HOOK_TXT], timing="segment", method="yt_auto:en")
 343 |          self.assertTrue(E.eligible(seg, ctx("evidence")).ok)
 344 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 345 | index 1a1371b..74013a1 100644
 346 | --- a/tests/package/proof_ledger.py
 347 | +++ b/tests/package/proof_ledger.py
 348 | @@ -257,6 +257,10 @@ def main(argv=None):
 349 |                      spotlit=spotlit)
 350 |      res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
 351 |                                                  "scorer_waited_s", "lock_stop", "scorer")}
 352 | +    try:                                                 # RULING 95: when the next qualifying episode could arrive
 353 | +        res["next_attempt"] = SPOT.next_attempt(rows, wp, now)
 354 | +    except Exception as e:                               # noqa: BLE001  a report, never the build
 355 | +        res["next_attempt"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
 356 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 357 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 358 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 359 | @@ -313,6 +317,11 @@ def main(argv=None):
 360 |              res["spotlight_pin_refused"] = f"{type(e).__name__}: {e}"
 361 |              say(f"SPOTLIGHT PIN REFUSED: {e}")
 362 |      else:
 363 | +        na = (res.get("next_attempt") or {}).get("conversation") or {}
 364 | +        say(f"  RULING 95: the newest conversation upload: {na.get('channel')} {na.get('video_id')} published "
 365 | +            f"{na.get('published_at')} (expires {na.get('expires_at')}), {na.get('turns_per_min')} turns a minute, "
 366 | +            f"rows {na.get('passes')}, word pass {na.get('word_pass_ready')} ready / {na.get('word_pass_waiting')} "
 367 | +            f"waiting" if na else "  RULING 95: no conversation upload in the window")
 368 |          say(f"no spotlight ({sp.get('why_none')})" + "".join(
 369 |              f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
 370 |              f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
 371 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 372 | index f1f2942..0497719 100644
 373 | --- a/tests/package/test_medley.py
 374 | +++ b/tests/package/test_medley.py
 375 | @@ -14,6 +14,8 @@ import json
 376 |  import re
 377 |  import os
 378 |  import sys
 379 | +import shutil
 380 | +import tempfile
 381 |  import unittest
 382 |  from datetime import timedelta
 383 |  
 384 | @@ -1090,6 +1092,65 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 385 |          self.assertIn("id=b~trim ", next(p for r, p in rig2.prompts if r == "angle_write"))   # stays as a clip
 386 |  
 387 |  
 388 | +class TestRuling94HookOpeners(unittest.TestCase):
 389 | +    """RULING 94 (00:40 ET Nov 14): (a) a hook opening on a conjunction or reply word opens as ruling 33's one-word trim
 390 | +    variant, whatever its clip role (the trim cuts cleanly, the scorer affirms it); (b) a first/second-person opener is
 391 | +    no fault; a third-person or demonstrative one needs the clip scorer's affirmation."""
 392 | +
 393 | +    def opener(self, text, reasons=(), verdict=None):
 394 | +        m = dict(pm("o", "O", 13.0), text=text, hook_onset={"pass": True, "measured": True})
 395 | +        m["eligibility"] = {"hook": {"ok": not reasons, "reasons": list(reasons)}, "clip": {"ok": True}}
 396 | +        return dict(m, scorer_verdict=verdict) if verdict else m
 397 | +
 398 | +    def test_first_and_second_person_open_and_third_person_needs_the_scorer(self):
 399 | +        self.assertTrue(PK._can_open(self.opener("I will bet you one Bitcoin that it gets there.")))
 400 | +        self.assertTrue(PK._can_open(self.opener("You know, Bitcoin is not done.")))
 401 | +        t = "This is ultimately a bipartisan issue for Bitcoin."
 402 | +        self.assertTrue(PK.third_opener({"text": t}))
 403 | +        self.assertFalse(PK._can_open(self.opener(t, ["opener"])))                         # no verdict: closed
 404 | +        self.assertTrue(PK._can_open(self.opener(t, ["opener"], sv(t, 4.0))))              # affirmed: open
 405 | +        self.assertFalse(PK._can_open(self.opener(t, ["opener"], sv(t, 3.0))))
 406 | +        self.assertTrue(PK._can_open(self.opener(t, ["opener"]), pending_verdict=True))   # the spotlight waits
 407 | +        self.assertFalse(PK._can_open(self.opener(t, ["opener", "hook_lead"], sv(t, 4.0))))   # another reason holds
 408 | +        self.assertFalse(PK._can_open(self.opener("So Bitcoin is down.")))                 # (a): only the trim opens
 409 | +        self.assertTrue(PK.hook_trim({"text": "So Bitcoin is down."}))
 410 | +        self.assertFalse(PK.hook_trim({"text": "Because Bitcoin is down."}))               # not a ruled trim word
 411 | +
 412 | +    def test_the_scorer_is_asked_for_a_hook_trim_and_a_third_person_opener(self):
 413 | +        d = tempfile.mkdtemp()
 414 | +        try:
 415 | +            src = source(["So Bitcoin has rarely seen six negative weeks back to back in its whole history."],
 416 | +                         vid="vS")
 417 | +            a, b = src.sentences[0]
 418 | +            so = dict(pm("s", "S", 0.0, vid="vS"), text=E.spoken(src.tokens[a:b + 1]), words=[a, b],
 419 | +                      start=float(src.tokens[a]["start"]), end=float(src.tokens[b]["end"]))
 420 | +            so = dict(so, scorer_verdict=sv(so["text"], 4.0))          # its CLIP role is affirmed as it is
 421 | +            this = dict(pm("t", "T", 12.0), text="This is ultimately a bipartisan issue for Bitcoin.")
 422 | +            plain = dict(pm("p", "P", 12.0), text="Bitcoin is the hardest money there is.")
 423 | +            PK.scorer_pass([so, this, plain], {"vS": src}, E.Context(NOW, REG), None,
 424 | +                           os.path.join(d, "c.json"), "b")
 425 | +            asked = [c["pid"] for c in json.load(open(os.path.join(d, "c.json")))["candidates"]]
 426 | +            self.assertIn("s~trim", asked)                              # (a): its hook trim variant
 427 | +            self.assertIn("t", asked)                                   # (b): the third-person opener itself
 428 | +            self.assertNotIn("p", asked)
 429 | +        finally:
 430 | +            shutil.rmtree(d, ignore_errors=True)
 431 | +
 432 | +    def test_a_hook_trim_variant_joins_the_pool_beside_its_affirmed_original(self):
 433 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
 434 | +              dict(pm("s", "E", 13.0), text="So Bitcoin x.")]
 435 | +        v = dict(ms[4], moment_id="s~trim", text="Bitcoin x.", trimmed_leading="So", untrimmed_start=0.0)
 436 | +        saved = PK.trim_variant
 437 | +        try:
 438 | +            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "s" else None
 439 | +            ok = {"s": fv("So Bitcoin x.", 4.0), "s~trim": fv("Bitcoin x.", 4.0)}   # the clip role affirmed as it is
 440 | +            out = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], verdicts=ok).run()
 441 | +        finally:
 442 | +            PK.trim_variant = saved
 443 | +        self.assertEqual(out["trimmed"], {"s": "s~trim"})               # ruling 94 (a): not only for no_role ones
 444 | +        self.assertIsNotNone(out["package"])
 445 | +
 446 | +
 447 |  class TestRuling58StepAEveryCandidate(unittest.TestCase):
 448 |      """RULING 58 (11:00): EVERY candidate is screened at step A, the miner's best first, and a verdict is cached by the
 449 |      moment id + its text sha (and the exact context step A reads), so a moment is paid for once, not once per build."""
 450 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 451 | index 438d123..7a7d327 100644
 452 | --- a/tests/package/test_spotlight.py
 453 | +++ b/tests/package/test_spotlight.py
 454 | @@ -17,7 +17,7 @@ import shutil
 455 |  import sys
 456 |  import tempfile
 457 |  import unittest
 458 | -from datetime import timedelta
 459 | +from datetime import datetime, timedelta, timezone
 460 |  from unittest import mock
 461 |  
 462 |  HERE = os.path.dirname(os.path.abspath(__file__))
 463 | @@ -389,7 +389,7 @@ class TestPool(unittest.TestCase):
 464 |          caps = lambda vid: (None, None)
 465 |          long_ok = moment(mid="l", dur=30.0, channel="A")
 466 |          too_long = moment(mid="t", dur=36.0, channel="B", text=TEXT.replace("money", "asset"))
 467 | -        conj = moment(mid="c", channel="C", text="And " + TEXT.replace("money", "thing"))
 468 | +        conj = moment(mid="c", channel="C", text="Because " + TEXT.replace("money", "thing"))   # not a trim word
 469 |          got, why = SPOT.pool([long_ok, too_long, conj], {}, ctx, spotlit=[], captions_for=caps)
 470 |          self.assertEqual([m["moment_id"] for m in got], ["l"])               # 30 s: a medley's 20 s does not bind
 471 |          self.assertIn("35.0 s", why["t"])
 472 | @@ -411,6 +411,71 @@ class TestPool(unittest.TestCase):
 473 |                  os.remove(p)
 474 |  
 475 |  
 476 | +class TestRuling94And95(unittest.TestCase):
 477 | +    def test_a_conjunction_opener_is_trimmed_and_a_third_person_one_waits_for_the_alone_scorer(self):
 478 | +        so = "So Bitcoin keeps moving and people keep watching it closely right now in every single market we follow."
 479 | +        m, srcs, ctx, caps = snap_rig([S5, so, S20, S5], 1)
 480 | +        got, why = SPOT.pool([m], srcs, ctx, spotlit=[], captions_for=caps)
 481 | +        self.assertEqual(len(got), 1, why)
 482 | +        v = got[0]
 483 | +        self.assertEqual(v["trimmed_leading"], "So")                    # ruling 94 (a): the variant opens
 484 | +        self.assertTrue(v["moment_id"].endswith("~trim"))
 485 | +        self.assertGreaterEqual(v["duration_s"], SPOT.SNAP_TO_S)       # snapped with the margin, then trimmed
 486 | +        this = moment(mid="t", channel="T", text="This is ultimately a bipartisan issue for Bitcoin and for every "
 487 | +                                                   "holder of it, whatever their politics, as far as I can tell.")
 488 | +        got, why = SPOT.pool([this], {}, E.Context(NOW, REG), spotlit=[], captions_for=lambda vid: (None, None))
 489 | +        self.assertEqual([x["moment_id"] for x in got], ["t"])          # (b): the ALONE scorer decides later
 490 | +        they = moment(mid="u", channel="U", text="And " + TEXT)             # no word record: no trim variant
 491 | +        got, why = SPOT.pool([they], {}, E.Context(NOW, REG), spotlit=[], captions_for=lambda vid: (None, None))
 492 | +        self.assertIn("ruling 94 (a)", why["u"])
 493 | +
 494 | +    def test_a_third_person_spotlight_needs_the_alone_scorer_at_four(self):
 495 | +        t = ("This is ultimately a bipartisan issue for Bitcoin and for every holder of it, whatever their politics, "
 496 | +             "as far as I can tell.")
 497 | +        b = TestBuild()
 498 | +        for alone, sealed, why in ((3.0, False, "cannot open cold"),        # a verdict that does not affirm: the
 499 | +                                   (None, False, "ALONE scorer: no rating"),  # opener rule itself refuses; none yet:
 500 | +                                   (4.0, True, None)):                          # deferred, then refused at ALONE
 501 | +            m = moment(mid="t", channel="T", text=t, scorer_verdict=None)
 502 | +            m.pop("scorer_verdict")
 503 | +            out, calls = b.run_build([m], {"t": 5}, alone=[alone])
 504 | +            self.assertEqual("package_for" in calls, sealed, (alone, out["moments"]["t"].get("out")))
 505 | +            if why:
 506 | +                self.assertIn(why, out["moments"]["t"]["out"])
 507 | +
 508 | +    def test_an_unclean_trim_cut_is_stopped(self):
 509 | +        b = TestBuild()
 510 | +        ms = [moment(mid="a~trim", channel="A", trimmed_leading="So", untrimmed_start=0.0)]
 511 | +        out, calls = b.run_build(ms, {"a~trim": 5}, onset={"pass": True, "measured": True,
 512 | +                                                         "trim": {"pass": False, "why": "it bleeds"}})
 513 | +        self.assertIn("ruling 94 (a): the trimmed cut is not clean: it bleeds", out["moments"]["a~trim"]["out"])
 514 | +        self.assertNotIn("package_for", calls)
 515 | +
 516 | +    def test_ruling_95_the_newest_conversation_upload_and_its_mining_state(self):
 517 | +        rows = [{"video_id": "old", "channel_name": "Talk", "published_at": "2026-11-13T18:00:00+00:00",
 518 | +                 "moment_id": "o1", "episode": {"turns_per_min": 2.0}, "mined": {"pass": "hook",
 519 | +                                                                                "prompt_version": "mine-hook/2"}},
 520 | +                {"video_id": "new", "channel_name": "Solo", "published_at": "2026-11-13T22:00:00+00:00",
 521 | +                 "moment_id": "n1", "episode": {"turns_per_min": 0.4}, "mined": {"pass": "moment",
 522 | +                                                                                "prompt_version": "mine/2"}},
 523 | +                {"video_id": "mid", "channel_name": "Panel", "published_at": "2026-11-13T20:00:00+00:00",
 524 | +                 "moment_id": "m1", "episode": {"turns_per_min": 1.5}, "mined": {"pass": "hook",
 525 | +                                                                                "prompt_version": "mine-hook/2"}},
 526 | +                {"video_id": "mid", "channel_name": "Panel", "published_at": "2026-11-13T20:00:00+00:00",
 527 | +                 "moment_id": "m2", "episode": {"turns_per_min": 1.5}, "mined": {"pass": "moment",
 528 | +                                                                                "prompt_version": "mine/2"}}]
 529 | +        na = SPOT.next_attempt(rows, {"m1": {"sentence_ready": True}}, NOW)
 530 | +        c = na["conversation"]
 531 | +        self.assertEqual((c["video_id"], c["published_at"], c["expires_at"]),
 532 | +                         ("mid", "2026-11-13T20:00:00Z", "2026-11-14T08:00:00Z"))
 533 | +        self.assertEqual((c["rows"], c["word_pass_ready"], c["word_pass_waiting"]), (2, 1, 1))
 534 | +        self.assertEqual(c["passes"], {"hook/mine-hook/2": 1, "moment/mine/2": 1})
 535 | +        self.assertEqual(na["newest_upload"]["video_id"], "new")           # newer, but not a conversation
 536 | +        self.assertEqual(c["age_h"], round((NOW - datetime(2026, 11, 13, 20, 0, tzinfo=timezone.utc)).total_seconds()
 537 | +                                           / 3600, 1))
 538 | +        self.assertIsNone(SPOT.next_attempt([], {}, NOW)["conversation"])
 539 | +
 540 | +
 541 |  class TestPackageFor(unittest.TestCase):
 542 |      def test_the_closing_line_ships_only_with_every_gate(self):
 543 |          pk, why, router, asked, fids = package()
 544 | @@ -495,7 +560,8 @@ class TestPackageFor(unittest.TestCase):
 545 |  class TestBuild(unittest.TestCase):
 546 |      """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""
 547 |  
 548 | -    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None, visual=None):
 549 | +    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None, visual=None,
 550 | +                  onset=None):
 551 |          ctx = E.Context(NOW, REG)
 552 |          calls = {}
 553 |  
 554 | @@ -521,7 +587,7 @@ class TestBuild(unittest.TestCase):
 555 |          stubs = [(SPOT.P, "prescreen", prescreen), (SPOT.P, "hook_ratings", hook_ratings),
 556 |                   (SPOT.P, "second_screen", second), (SPOT, "package_for", package_for),
 557 |                   (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
 558 | -                 (SPOT.P, "hook_onset_for", lambda m, s, w, c: {"pass": True, "measured": True}),
 559 | +                 (SPOT.P, "hook_onset_for", lambda m, s, w, c: onset or {"pass": True, "measured": True}),
 560 |                   (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
 561 |                   (VP, "visual_for", lambda r, m, w, c: dict({"measured": True, "flags": [], "burned_in": [],
 562 |                                                                "backend": "fake:vis"}, **(visual or {}))),
 563 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of sealed "moments" pins that another
session renders into short Bitcoin videos). Only state what you can verify from the diff; if uncertain, say so; do
not guess. Be specific: file:line and a concrete input that breaks it.

Background (static):
- A pin's HOOK opens the video cold. The render's STAND_ALONE (stand_alone.py, the same rule on the render's side and
  this builder's pin stage) refused a hook whose first word is a conjunction, a reply word or any pronoun. A CLIP
  opening on a conjunction or reply word passes only with the render's clip scorer's affirmation (the "ALONE scorer":
  verdicts on exactly the text, read through package.verdict_of).
- Ruling 33 part 2: a moment opening on ONE of TRIM_WORDS (but, and, so, well, now, yeah) may be cut one word in (a
  "~trim" variant carrying trimmed_leading / untrimmed_start). The variant is judged like any moment, its trimmed cut
  must open cleanly (hook_onset's "trim" record), and the scorer must affirm the trimmed text (trim_refused /
  check_edl's trimmed_opener). Until now the medley built trim variants only for moments with no on-screen role.
- The medley build rates hooks (hook_ratings) only for moments that can open (package._can_open: hook eligibility from
  the ledger, G17a, the opener rule). The spotlight (pipeline/spotlight.py) is a one-clip pin that needs, among
  others, the ALONE scorer >= 4 on its text.
- Law L-m: nothing measured is never a pass. Fail closed.

The order (verbatim): "94. Of the 23 Bitcoin Magazine interview moments, 13 never reach a judge because they open on
a conjunction or a pronoun. For SPOTLIGHT and for a medley HOOK alike: (a) a leading conjunction or reply word gets
ruling 33's ONE-word trim variant and that variant is what is rated as an opener (the trim must cut cleanly and the
ALONE scorer must affirm it, as for a clip); (b) a first-person or second-person pronoun opener ('I', 'we', 'you',
'my', 'our') is NOT a cold-open fault at all: 'I will bet you one Bitcoin that...' is a fine first line; only a
THIRD-person or demonstrative pronoun with no referent in the clip ('he', 'they', 'it', 'this', 'that') is, and the
ALONE scorer + step A already judge exactly that. ... This touches the render's hook opener rule too: agree the change
with the integrator, one audited change each side." and "95. When a build ends with no medley and no spotlight, STATE
line 1 carries the three nearest ...; Add the time the next qualifying episode could arrive (the newest conversation
upload's publish time + its mining state)."
The integrator AGREED (01:0x ET) the hook rule below, with check_edl rating a third-person hook; its side is audited
separately.

The change:
1. stand_alone.py: FIRST_SECOND = {i, me, my, we, us, our, you, your}; THIRD = PRONOUNS - FIRST_SECOND. opener("hook"):
   a conjunction or reply word is still a fault (only a trim variant opens); FIRST_SECOND is ok; THIRD is ok only
   with an affirming scorer verdict (affirmed(score, fault, moments)), else a fault. check_edl asks the scorer about a
   hook whose first word is in THIRD.
2. eligibility.py: the hook role, like the clip role, reads the scorer verdict when the ledger has one (it does not:
   a third-person hook fails "opener" at the ledger and is decided at the pin stage).
3. package.py: hook_trim(m) and third_opener(m); _can_open re-checks a hook whose ONLY failing eligibility reason is
   "opener" with the verdict now attached (pending_verdict=True lets the spotlight defer a third-person opener to its
   ALONE >= 4 gate); scorer_pass asks for the trim variant of every hook_trim moment and for every third-person
   opener; build() adds a trim variant for every hook_trim moment (the original keeps its own place as a clip; a
   line-up never takes one video twice).
4. spotlight.py: pool() snaps a moment to be trimmed TRIM_MARGIN_S further, then takes its trim variant (refused when
   none exists or it ends under 13.7 s); a third-person opener enters the pool for the ALONE scorer to decide; build()
   stops a trimmed moment whose trimmed cut is not clean and opens with _can_open(m, pending_verdict=True).
   next_attempt() (ruling 95): the newest upload with >= 1.0 caption turns a minute among the adapter's rows, its
   publish time, its expiry (12 h), its rows by mining pass and its word-pass windows ready / waiting; the driver
   records and logs it.
5. Tests: the hook rule's cases (stand_alone and eligibility), _can_open, the scorer's candidates, a hook trim variant
   beside its affirmed original in a medley build, the spotlight's trim and third-person paths and the unclean trim
   cut, next_attempt.

Check: that no third-person hook can open, or be sealed, without an affirming verdict on its exact text (and that
pending_verdict cannot leak into the medley or into a sealed pin); that a trimmed hook is only ever the variant (never
the untrimmed original) and is sealed with its affirmation; that a first/second-person opener is the only new pass
without a verdict; that the margin keeps a trimmed spotlight at or over 13.7 s; that next_attempt reports only measured
facts. Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
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
