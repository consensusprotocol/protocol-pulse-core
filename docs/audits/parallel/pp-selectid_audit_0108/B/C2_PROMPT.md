# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0108B
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 208 s finish=stop usage in 37077 / out 6194 usd~0.204 (upper-bound price)

# Package B Audit — pp-selectid (verdict call sites, shadow, replay)

Scope: I audited only what the diff shows. Package A (`providers.call_parsed`, `Router`, `gateway`, the shadow recorder) is assumed to behave as the background states; where a finding depends on it, I say so.

---

## P0 findings

None. I could not construct a scenario in the diff where an out-of-contract answer becomes a verdict, or where an outage yields a pass.

---

## P1 findings

**B1. `context_integrity.step_a` — the `kind` kwarg is silently dropped when the router's `call` predates it (merge risk, not a logic bug).**
`pipeline/context_integrity.py:16-20` (diff lines): `kind` is passed via `**({"kind": kind} if kind else {})`. If the installed `providers.Router.call` (package A) does not accept `kind`, this raises `TypeError` at the call, which the surrounding `while True` loop's except clauses (`ProviderError, SpendLimit, ValueError, KeyError, TypeError` at diff line 119) catch — but note the except at line 119 wraps the *whole* block including steps B/C, so a `TypeError` from the very first `step_a` call would be reported as a step-A failure for every label, fail-closed. That is correct behavior, but it means a package A/B version skew (package B merged, package A's `kind` parameter not) fails *every* prescreen silently-as-`STEP_A_UNAVAILABLE`-style, with no distinguishing error. Since the addendum says the rebase was mechanical, verify package A's `call` signature includes `kind` and `call_parsed` — I cannot see either in this diff. **Condition, not a defect I can prove.**

**B2. `package.hook_ratings` — the old "one re-ask of the same model" is gone, and the except clause now catches `KeyError` where the old code's *retry* decision treated `KeyError` as retryable.**
Old code (diff lines 226-253): `except (ProviderError, SpendLimit, ValueError, TypeError, KeyError)` — on `ValueError/TypeError/KeyError` it `continue`d (re-ask, same model, next seed); on `ProviderError/SpendLimit` it `break`. New code (diff lines 263-268): one `except` of all five, returning the error. This matches the 20:33 order ("an out-of-contract answer moves on") *only if* `call_parsed` itself moves on on `ValueError/TypeError/KeyError` — which the background states it does. So the semantics are: previously 2 attempts of the same model; now 1 attempt × N chain models. That is the intended ruling-82 behavior, but it is a **behavioral change in attempt count** (2 → 1 per model) that the test at diff lines 1326-1343 does exercise (`len(c.calls) == 2` because the *chain* has 2 models, not because of a re-ask). Fine — but note the test's `chained` helper asserts `avoid_model` skipping, which depends on package A's `call_parsed` actually passing `avoid_model`-style skips; not visible here. Flagging as a coupling assumption, not a proven defect.

**B3. `replay85.decide` for `clips_alone`/`coherence` — the "older contract" tolerance diverges from the pipeline's own parser.**
`tests/package/replay85.py` diff lines 552-583: the replay accepts `set(v) - {"hook"} != want` (a legacy top-level `hook` rating) and `set(v["clips"])` in either the named labels or labels-minus-`hook`. The *pipeline's* parsers (the new `parse` closures in `package.coherence`/`medley`, diff lines 294-300, 323-331) require exactly `set(v) == {"through_line","clips","vo_point"}` (or `joins`) and `set(v["clips"]) == set(labs[1:])` — no legacy tolerance, no extra `hook` key. Consequence: a recorded Grok answer that the *replay* scores as a decision could be one the *production* parser would reject as out of contract (and, under the new code, move on from). This inflates the replay's unit counts and its agreement percentages relative to what the production chain would actually accept. It is arguably intentional (the replay must read *old* recordings), and the docstring at diff lines 553-555 says so ("both before ruling 61") — so this is disclosed, not hidden. But the TABLE.md agreement figures for `clips_alone`/`coherence` are therefore computed over a slightly more permissive contract than production's. **P1 because ruling 88(b) decisions (the hook chain reorder) were made from these numbers**; the hook path itself (`decide` for `k == "hook"`, diff lines 584-592) uses the *strict* contract (`set(v) == {"hooks"}`), matching production exactly — so the ruling-88(b) hook conclusion rests on the strict parser. Good. The divergence only affects the informational `clips_alone`/`coherence` rows. Downgrade-able to P2 if the orchestrator accepts the disclosed legacy tolerance.

**B4. `replay85.compare` for `step_a` — "both fail (for possibly different rules): the decision agrees" can mask a lost `REFERENT_OUTSIDE` refusal in the *table's* agree column, though the dedicated REFERENT_OUTSIDE section catches it.**
Diff lines 634-637: if Grok's failure tuple and Heimdall's failure tuple are both non-em

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 18 s finish=stop usage in 36336 / out 205 usd~0.187 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: none verifiable from diff** (all requested items check: parse funcs are identical contract logic extracted verbatim; call_parsed failures route to existing except blocks that treat ValueError/TypeError/KeyError/ProviderError/SpendLimit as no-verdict; outages produce measured=False structures with no cache; replay85.decide() reproduces pipeline bars (CI.a_failures, PK._line_ok/COHERENCE_MIN/HOOK_MIN/LY_MAX_BRIDGES, SP._norm) and explicitly labels step_c/fidelity proxies; shadow86.report() sets would_seal=False on any pin "looser" or "grok no verdict", forces clean_streak=0 on missing/unreadable shadows, and pin_texts() covers both medley & spotlight_pin per addendum; first_bounds/_second_bounds + kind= args match ruling 85/88 routing exactly; test updates exercise the move-on, bounds, and streak logic).

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
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
named = re.findall(r'"(clip_\d+)": 1

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0108, package B (the verdict call sites, the shadow report, the replay), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes (P0/P1/P2 none); qwen3.8-27b SHIP yes with conditions (P0 none); glm-5.3-flash SHIP yes
with conditions (P0 none).

## Implemented

1. glm (P1): with every shadow answer missing and no compared decision on the pin, the report said the pin "WOULD
   have sealed under Grok", which nothing supported. The streak was already safe (missing shadows reset it). FIXED:
   would_seal_under_grok is None in that case (tested).
2. qwen (P1-2): a comment in shadow86 now says that "grok no verdict" on a pin's decision counts as a stop (fail
   closed).
3. qwen (P2): package.hook_ratings' docstring still said "one re-ask" of the same model. It now says the reply out of
   contract moves on to the next model (call_parsed).

## Refuted, with evidence

- qwen P1-1 (replay85's manual 429 handling bypasses the Router's backoff and spend cap): the replay calls
  router.call, so every call is accounted on ruling 48's ledger and stops at its cap (SpendLimit). The manual part
  only lifts the run-long down mark the Router sets on a 429, after a pause, so one rate-limit does not end a
  measurement. The replay is a measurement tool, never a gate.
- glm (P1): the replay's clips-alone / coherence decisions accept two older Grok contracts (disclosed in decide()'s
  docstring) that production's parsers no longer accept. The ruling-88 (b) decision rests on the HOOK rows, which use
  the strict contract (glm confirms). The clips-alone / coherence rows changed no routing.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0108/B/C2_STEP.diff (1516 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index c30f043..3f32a94 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -318,7 +318,7 @@ def check(router, package, sources, writer_vendor, seed=7):
   6 |      return check_contexts(router, package, contexts_from_sources(package, sources), writer_vendor, seed)
   7 |  
   8 |  
   9 | -def step_a(router, contexts, writer_vendor, seed=7, writer_family=None, deadline_s=None, failover=False):
  10 | +def step_a(router, contexts, writer_vendor, seed=7, writer_family=None, deadline_s=None, failover=False, kind=None):
  11 |      """Step A alone (context only, the package hidden): {label: item} for exactly the given labels, and the back-end.
  12 |      Raises ValueError / ProviderError when it cannot be had or read. RULING 82 (20:02 Nov 13): deadline_s bounds each
  13 |      call (the router moves to the next model at it and logs the miss, item 55); failover=True also moves on when a
  14 | @@ -336,7 +336,8 @@ def step_a(router, contexts, writer_vendor, seed=7, writer_family=None, deadline
  15 |      while True:
  16 |          ra = router.call("context_verdict", prompt, 4000, seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
  17 |                           **({"avoid_model": set(skip)} if skip else {}),
  18 | -                         **({"deadline_s": deadline_s} if deadline_s is not None else {}))
  19 | +                         **({"deadline_s": deadline_s} if deadline_s is not None else {}),
  20 | +                         **({"kind": kind} if kind else {}))      # ruling 88: step_a_first / step_a_second
  21 |          try:
  22 |              A = _strict(ra.text, {"excerpts"}, {"excerpts": A_KEYS})
  23 |              a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
  24 | @@ -485,7 +486,7 @@ def check_contexts(router, package, contexts, writer_vendor, seed=7, a_by=None,
  25 |      try:
  26 |          if a_by is None:
  27 |              a_by, out["backends"]["A"] = step_a(router, {lb: contexts[lb] for lb in labels}, writer_vendor, seed,
  28 | -                                                writer_family)
  29 | +                                                writer_family, kind="step_a_first")
  30 |          else:
  31 |              missing = [lb for lb in labels if not isinstance(a_by.get(lb), dict) or set(A_KEYS) - set(a_by[lb])]
  32 |              if missing:
  33 | @@ -493,45 +494,56 @@ def check_contexts(router, package, contexts, writer_vendor, seed=7, a_by=None,
  34 |              a_by = {lb: a_by[lb] for lb in labels}
  35 |              out["backends"]["A"] = {lb: a_by[lb].get("backend") or "precomputed (unnamed)" for lb in labels}
  36 |          lab_list = ", ".join(all_labels)
  37 | -        r0 = router.call("viewer_takeaway", STEP_B.format(package=package_view(clips_alone(package)), labels=lab_list),
  38 | -                         3000, seed)
  39 | -        out["backends"]["B0"] = r0.backend
  40 | -        B0 = _strict(r0.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
  41 | +
  42 | +        def parse_b0(text):
  43 | +            B0 = _strict(text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
  44 | +                                                            "relations": ("labels", "relation")})
  45 | +            b0_by = {t["label"]: t for t in B0["takeaways"] if isinstance(t.get("label"), str)}
  46 | +            if not set(labels) <= set(b0_by):
  47 | +                raise ValueError(f"step B (clips alone) must answer at least {labels}")
  48 | +            return b0_by
  49 | +
  50 | +        def parse_b(text):
  51 | +            B = _strict(text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
  52 |                                                             "relations": ("labels", "relation")})
  53 | -        b0_by = {t["label"]: t for t in B0["takeaways"] if isinstance(t.get("label"), str)}
  54 | -        if not set(labels) <= set(b0_by):
  55 | -            raise ValueError(f"step B (clips alone) must answer at least {labels}")
  56 | -        rb = router.call("viewer_takeaway", STEP_B.format(package=package_view(package), labels=lab_list), 3000, seed,
  57 | -                         avoid_vendor=writer_vendor, avoid_family=writer_family)
  58 | +            b_by = {t["label"]: t for t in B["takeaways"] if isinstance(t.get("label"), str)}
  59 | +            if not set(labels) <= set(b_by) or any(not isinstance(b_by[lb].get("asserts"), str) for lb in labels):
  60 | +                raise ValueError(f"step B must answer at least {labels}")
  61 | +            pairs_want = {frozenset(p) for p in itertools.combinations(all_labels, 2)}
  62 | +            got = []
  63 | +            for rel in B["relations"]:
  64 | +                labs = rel.get("labels")
  65 | +                if not isinstance(labs, list) or len(labs) != 2 or not all(isinstance(x, str) for x in labs) or \
  66 | +                        labs[0] == labs[1] or rel.get("relation") not in RELATIONS:
  67 | +                    raise ValueError(f"step B relation out of contract: {json.dumps(rel)[:160]}")
  68 | +                got.append(frozenset(labs))
  69 | +            if len(got) != len(set(got)) or set(got) != pairs_want:
  70 | +                raise ValueError(f"step B must rate every pair of clips exactly once ({len(pairs_want)} pairs, got "
  71 | +                                 f"{len(set(got))} distinct of {len(got)})")
  72 | +            return B, b_by
  73 | +        # the 20:33 order: an answer out of contract moves on to the next model (providers.call_parsed)
  74 | +        r0, b0_by = P.call_parsed(router, "viewer_takeaway",
  75 | +                                  STEP_B.format(package=package_view(clips_alone(package)), labels=lab_list),
  76 | +                                  parse_b0, 3000, seed)
  77 | +        out["backends"]["B0"] = r0.backend
  78 | +        rb, (B, b_by) = P.call_parsed(router, "viewer_takeaway",
  79 | +                                      STEP_B.format(package=package_view(package), labels=lab_list), parse_b, 3000,
  80 | +                                      seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
  81 |          out["backends"]["B"] = rb.backend
  82 | -        B = _strict(rb.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
  83 | -                                                          "relations": ("labels", "relation")})
  84 | -        b_by = {t["label"]: t for t in B["takeaways"] if isinstance(t.get("label"), str)}
  85 | -        if not set(labels) <= set(b_by) or any(not isinstance(b_by[lb].get("asserts"), str) for lb in labels):
  86 | -            raise ValueError(f"step B must answer at least {labels}")
  87 | -        pairs_want = {frozenset(p) for p in itertools.combinations(all_labels, 2)}
  88 | -        got = []
  89 | -        for rel in B["relations"]:
  90 | -            labs = rel.get("labels")
  91 | -            if not isinstance(labs, list) or len(labs) != 2 or not all(isinstance(x, str) for x in labs) or \
  92 | -                    labs[0] == labs[1] or rel.get("relation") not in RELATIONS:
  93 | -                raise ValueError(f"step B relation out of contract: {json.dumps(rel)[:160]}")
  94 | -            got.append(frozenset(labs))
  95 | -        if len(got) != len(set(got)) or set(got) != pairs_want:
  96 | -            raise ValueError(f"step B must rate every pair of clips exactly once ({len(pairs_want)} pairs, got "
  97 | -                             f"{len(set(got))} distinct of {len(got)})")
  98 |          text_of = {sg["label"]: sg["text"] for sg in segs}
  99 |          pairs = "\n".join(f'<pair label="{lb}"><A>{_q(a_by[lb]["proposition"], 400)} (certainty: '
 100 |                            f'{a_by[lb]["certainty"]})</A><CLIP>{_q(text_of[lb], 900)}</CLIP><B>{_q(b_by[lb]["asserts"], 400)}'
 101 |                            f' (certainty: {b_by[lb]["certainty"]})</B></pair>' for lb in labels)
 102 | -        rc = router.call("context_verdict", STEP_C.format(pairs=pairs, vo=vo_words(package)), 2000, seed,
 103 | -                         avoid_vendor=writer_vendor, avoid_family=writer_family)
 104 | +        def parse_c(text):
 105 | +            C = _strict(text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
 106 | +                                                    "stronger_certainty", "raising_words")})
 107 | +            c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
 108 | +            if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
 109 | +                raise ValueError(f"step C must answer exactly the labels {labels}")
 110 | +            return c_by
 111 | +        rc, c_by = P.call_parsed(router, "context_verdict", STEP_C.format(pairs=pairs, vo=vo_words(package)), parse_c,
 112 | +                                 2000, seed, avoid_vendor=writer_vendor, avoid_family=writer_family, kind="step_c")
 113 |          out["backends"]["C"] = rc.backend
 114 | -        C = _strict(rc.text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
 115 | -                                                   "stronger_certainty", "raising_words")})
 116 | -        c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
 117 | -        if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
 118 | -            raise ValueError(f"step C must answer exactly the labels {labels}")
 119 |      except (P.ProviderError, P.SpendLimit, ValueError, KeyError, TypeError) as e:
 120 |          for r_ in (r0, rb, rc):
 121 |              if r_ is not None and isinstance(e, (ValueError, KeyError, TypeError)) and hasattr(router, "reject"):
 122 | diff --git a/pipeline/moments.py b/pipeline/moments.py
 123 | index cfed885..7d55d31 100644
 124 | --- a/pipeline/moments.py
 125 | +++ b/pipeline/moments.py
 126 | @@ -378,21 +378,19 @@ def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7
 127 |      if why:
 128 |          return {"verdict": "exclude", "why": why, "risks": ["ad_read"], "backend": "deterministic", "measured": True,
 129 |                  "replayed": False}
 130 | -    r = None
 131 | -    try:
 132 | -        r = router.call("exclusion_verdict", EXCLUSION_PROMPT.format(before=quote_data(before_text, 3000),
 133 | -                                                                     moment=quote_data(moment_text, 1500),
 134 | -                                                                     after=quote_data(after_text, 3000)), 800, seed,
 135 | -                        avoid_model=avoid_model)
 136 | -        obj = json.loads(r.text.strip())
 137 | +    def parse(text):
 138 | +        obj = json.loads(text.strip())
 139 |          if not isinstance(obj, dict) or set(obj) != {"risks", "about_bitcoin", "why"} or \
 140 |                  not isinstance(obj["risks"], list) or any(not isinstance(x, str) or x not in HARD_RISKS
 141 |                                                            for x in obj["risks"]) or \
 142 |                  obj["about_bitcoin"] not in ("yes", "no", "uncertain"):
 143 |              raise ValueError("the verdict does not match its contract")
 144 | +        return obj
 145 | +    try:                                      # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 146 | +        r, obj = P.call_parsed(router, "exclusion_verdict", EXCLUSION_PROMPT.format(
 147 | +            before=quote_data(before_text, 3000), moment=quote_data(moment_text, 1500),
 148 | +            after=quote_data(after_text, 3000)), parse, 800, seed, avoid_model=avoid_model)
 149 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 150 | -        if r is not None and isinstance(e, (ValueError, TypeError)):
 151 | -            router.reject(r)
 152 |          return {"verdict": "exclude", "why": f"no readable verdict ({type(e).__name__}: {str(e)[:160]})",
 153 |                  "risks": [], "backend": None, "measured": False, "replayed": False}
 154 |      meas = {"measured": True, "replayed": bool(getattr(r, "replayed", False))}
 155 | diff --git a/pipeline/package.py b/pipeline/package.py
 156 | index 4736b4f..80d079c 100644
 157 | --- a/pipeline/package.py
 158 | +++ b/pipeline/package.py
 159 | @@ -489,7 +489,7 @@ def src_of(x, sources):
 160 |  
 161 |  
 162 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 163 | -              store=None, log=print, cache=None, deadline_s=None):
 164 | +              store=None, log=print, cache=None, deadline_s=None, kind="step_a_first", failover=None):
 165 |      """Step A (context only, package-independent by law L-s): ({moment_id: A item}, {moment_id: [failing rules]},
 166 |      {vendor}, {family}). RULING 58 (11:00 Nov 13): n None (the default) screens EVERY usable moment, the miner's best
 167 |      first (rank_score); a number keeps the old cap (distinct channels first). Each moment is paid for ONCE: a verdict
 168 | @@ -542,7 +542,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 169 |          try:
 170 |              return CI.step_a(router, {m["moment_id"]: contexts[m["moment_id"]] for m in chunk}, writer_vendor,
 171 |                               seed=7 + i * batch, writer_family=writer_family, deadline_s=deadline_s,
 172 | -                             failover=deadline_s is not None), None          # ruling 82: the chain, per call
 173 | +                             failover=(deadline_s is not None) if failover is None else failover,   # ruling 82
 174 | +                             kind=kind), None
 175 |          except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
 176 |              return None, e
 177 |      with ThreadPoolExecutor(max_workers=max(1, min(PRESCREEN_WORKERS, len(chunks)))) as ex:
 178 | @@ -571,6 +572,23 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 179 |      return a_by, fails, vendors, families
 180 |  
 181 |  
 182 | +def first_bounds(router):
 183 | +    """The kwargs of step A's FIRST screen. RULING 85: under heimdall_first the first verdict is a Heimdall family's,
 184 | +    2 clips and 120 s a call (Heimdall needs a median 268 s on 8 clips); today it keeps its batches with no deadline.
 185 | +    One helper for both builds (the medley's and the spotlight's)."""
 186 | +    return {"batch": SECOND_VERDICT_BATCH, "deadline_s": SECOND_VERDICT_DEADLINE_S} \
 187 | +        if getattr(router, "routing", "today") == "heimdall_first" else {}
 188 | +
 189 | +
 190 | +def _second_bounds(router):
 191 | +    """(batch, deadline_s) of step A's second verdict. Today it is a Heimdall family's (ruling 82: 2 clips, 120 s a
 192 | +    call). RULING 88 (c), under heimdall_first, it is Grok confirming a Heimdall pass: Grok's own batch (8 clips) and no
 193 | +    deadline, since the per-clip cost falls with the batch."""
 194 | +    if getattr(router, "routing", "today") == "heimdall_first":
 195 | +        return PRESCREEN_BATCH, None
 196 | +    return SECOND_VERDICT_BATCH, SECOND_VERDICT_DEADLINE_S
 197 | +
 198 | +
 199 |  def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 200 |      """ORDER 06:22 item 45: step A from a SECOND vendor on every cuttable clip, BEFORE the angle step. The writer is
 201 |      known only when the angle call answers (Heimdall first, Grok on its failure: angle_write), and a verdict never
 202 | @@ -585,13 +603,14 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 203 |      for mid, m in cleared.items():
 204 |          b = router.backends.get((a_by.get(mid) or {}).get("backend"))
 205 |          groups.setdefault((b.vendor, b.family) if b is not None else None, []).append(m)
 206 | -    jobs = [(k, g[i:i + SECOND_VERDICT_BATCH]) for k, g in groups.items() if k is not None
 207 | -            for i in range(0, len(g), SECOND_VERDICT_BATCH)]
 208 | +    batch, dl = _second_bounds(router)
 209 | +    jobs = [(k, g[i:i + batch]) for k, g in groups.items() if k is not None
 210 | +            for i in range(0, len(g), batch)]
 211 |      def one(k, chunk):                  # a chunk whose screen raises fails closed, never the build (audit 0640 C1)
 212 |          try:
 213 |              return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log,
 214 | -                             cache=cache, batch=SECOND_VERDICT_BATCH,    # ruling 58: a second verdict is paid once;
 215 | -                             deadline_s=SECOND_VERDICT_DEADLINE_S)       # ruling 82: the chain, 120 s a call
 216 | +                             cache=cache, batch=batch, deadline_s=dl,    # ruling 58: a second verdict is paid once;
 217 | +                             kind="step_a_second", failover=True)        # ruling 82 / 88 (c): the chain
 218 |          except Exception as e:
 219 |              return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
 220 |                          for m in chunk}, set(), set()
 221 | @@ -687,8 +706,9 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
 222 |      """RULING 59 (a): the hook question of ruling 52 (HOOK_QUESTION: scroll / alone / setup, each 1-5) asked of EVERY
 223 |      given moment ALONE, in ONE batched call (coherence_verdict, never the writers' vendor or family), each rating
 224 |      DERIVED as the lowest part (HOOK_RULE). Cached (`cache`, shared by every build) by the moment id, the sha256 of its
 225 | -    text and the question's version: a moment is rated once, by a back-end off the writers. One re-ask on a reply out
 226 | -    of contract. -> ({moment id: {"scroll", "alone", "setup", "rating", "why", "backend", "cached"}}, the error or None).
 227 | +    text and the question's version: a moment is rated once, by a back-end off the writers. A reply out of contract
 228 | +    moves on to the next model of the chain (providers.call_parsed, ruling 82 as the 20:33 order extends it). ->
 229 | +    ({moment id: {"scroll", "alone", "setup", "rating", "why", "backend", "cached"}}, the error or None).
 230 |      A moment the call did not rate has no rating (law L-m: never a pass)."""
 231 |      import providers as P
 232 |      wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
 233 | @@ -709,35 +729,30 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
 234 |      cands = "\n".join(f'CANDIDATE id="{m["moment_id"]}" (on screen: {CI._q(_name(m, ctx), 80)}): '
 235 |                        f'"{CI._q(m["text"], 900)}"' for m in todo)
 236 |      keys = ", ".join(f'"{i}": {{"scroll": 1, "alone": 1, "setup": 1, "why": "..."}}' for i in ids)
 237 | -    err = None
 238 | -    for s in (seed, seed + 1):
 239 | -        r = None
 240 | -        try:
 241 | -            r = router.call("coherence_verdict", HOOKS_PROMPT.format(hooks=cands, keys=keys), 600 + 150 * len(ids), s,
 242 | -                            avoid_vendor=writer_vendor, avoid_family=writer_family)
 243 | -            v = json.loads(r.text.strip())
 244 | -            h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 245 | -            if not isinstance(h, dict) or set(h) != set(ids) or any(
 246 | -                    not isinstance(x, dict) or set(x) != set(HOOK_PARTS) | {"why"} or not isinstance(x["why"], str) or
 247 | -                    any(type(x[k]) is not int or not 1 <= x[k] <= 5 for k in HOOK_PARTS) for x in h.values()):
 248 | -                raise ValueError("hook ratings out of contract")
 249 | -        except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:
 250 | -            if r is not None and isinstance(e, (ValueError, TypeError, KeyError)):
 251 | -                router.reject(r)
 252 | -            err = f"{type(e).__name__}: {str(e)[:200]}"
 253 | -            if isinstance(e, (ValueError, TypeError, KeyError)):
 254 | -                continue                                 # out of contract: one re-ask
 255 | -            break                                        # unavailable or the spend guard: no verdict (law L-m)
 256 | -        new = {}
 257 | -        for m in todo:
 258 | -            x = h[m["moment_id"]]
 259 | -            rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
 260 | -                   "backend": r.backend, "rule": HOOK_OWN_RULE}       # ruling 61: scroll / alone
 261 | -            out[m["moment_id"]] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 262 | -            new[key(m)] = {r.backend: rec}
 263 | -        _cache_put(cache, new)
 264 | -        return out, None
 265 | -    return out, err
 266 | +
 267 | +    def parse(text):
 268 | +        v = json.loads(text.strip())
 269 | +        h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 270 | +        if not isinstance(h, dict) or set(h) != set(ids) or any(
 271 | +                not isinstance(x, dict) or set(x) != set(HOOK_PARTS) | {"why"} or not isinstance(x["why"], str) or
 272 | +                any(type(x[k]) is not int or not 1 <= x[k] <= 5 for k in HOOK_PARTS) for x in h.values()):
 273 | +            raise ValueError("hook ratings out of contract")
 274 | +        return h
 275 | +    try:                                         # the 20:33 order: an answer out of contract moves on to the next
 276 | +        r, h = P.call_parsed(router, "coherence_verdict", HOOKS_PROMPT.format(hooks=cands, keys=keys), parse,
 277 | +                             600 + 150 * len(ids), seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
 278 | +                             kind="hook")                                # ruling 88: the hook rating's own list
 279 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # (it was one re-ask of the same
 280 | +        return out, f"{type(e).__name__}: {str(e)[:200]}"     # model) unavailable, all out of contract, or the guard
 281 | +    new = {}
 282 | +    for m in todo:
 283 | +        x = h[m["moment_id"]]
 284 | +        rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
 285 | +               "backend": r.backend, "rule": HOOK_OWN_RULE}           # ruling 61: scroll / alone
 286 | +        out[m["moment_id"]] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 287 | +        new[key(m)] = {r.backend: rec}
 288 | +    _cache_put(cache, new)
 289 | +    return out, None
 290 |  
 291 |  TAKEAWAY_SAID = ("The takeaway may characterise what the clips SAID, never what WILL happen. Two kinds were refused: a "
 292 |                   "forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.'), and a superlative that "
 293 | @@ -1492,21 +1507,22 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 294 |      `hook`) is written to verdict["clips"]["hook"]; without one the verdict fails closed (law L-m). The clips after the
 295 |      hook and vo_point are rated as before; the judge sees the hook's text for context."""
 296 |      import providers as P
 297 | -    r = None
 298 |      labs = [sg["label"] for sg in pk["segments"]]
 299 |      own = hook_own(hook)
 300 | -    try:
 301 | -        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(
 302 | -                            package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
 303 | -                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 304 | -        v = json.loads(r.text.strip())
 305 | +
 306 | +    def parse(text):
 307 | +        v = json.loads(text.strip())
 308 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 309 |                  not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
 310 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 311 |              raise ValueError("coherence verdict out of contract")
 312 | +        return v
 313 | +    try:                                         # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 314 | +        r, v = P.call_parsed(router, "coherence_verdict", COHERENCE_PROMPT.format(
 315 | +                                 package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
 316 | +                             parse, 1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
 317 | +                             kind="coherence")                           # ruling 88: coherence's own list
 318 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 319 | -        if r is not None and isinstance(e, (ValueError, TypeError)):
 320 | -            router.reject(r)
 321 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False}
 322 |      v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 323 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 324 | @@ -1549,13 +1565,8 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 325 |      own = hook_own(segs[0]) if segs else None
 326 |      clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 327 |                        for lb, m in zip(labs, segs))
 328 | -    r = None
 329 | -    try:
 330 | -        r = router.call("coherence_verdict",
 331 | -                        MEDLEY_PROMPT.format(clips=clips, clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:]),
 332 | -                                             joins=", ".join(f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
 333 | -                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 334 | -        v = json.loads(r.text.strip())
 335 | +    def parse(text):
 336 | +        v = json.loads(text.strip())
 337 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
 338 |                  not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
 339 |                  any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
 340 | @@ -1563,9 +1574,15 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 341 |                  any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 342 |                      or not isinstance(x["why"], str) for x in v["joins"].values()):
 343 |              raise ValueError("clips-alone verdict out of contract")
 344 | +        return v
 345 | +    try:                                         # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 346 | +        r, v = P.call_parsed(router, "coherence_verdict",
 347 | +                             MEDLEY_PROMPT.format(clips=clips, clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:]),
 348 | +                                                  joins=", ".join(f'"{j}": {{"followable": true, "why": "..."}}'
 349 | +                                                                  for j in js)),
 350 | +                             parse, 1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
 351 | +                             kind="clips_alone")                         # ruling 88: clips-alone's own list
 352 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 353 | -        if r is not None and isinstance(e, (ValueError, TypeError)):
 354 | -            router.reject(r)
 355 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
 356 |      v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 357 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 358 | @@ -2289,7 +2306,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 359 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
 360 |      wv, wf = _writers(router)
 361 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 362 | -                                                   cache=step_a_cache)          # ruling 58: every candidate, once
 363 | +                                                   cache=step_a_cache, kind="step_a_first",   # ruling 85 / 88 (c)
 364 | +                                                   **first_bounds(router))
 365 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 366 |      levels = current_levels(sources.values(), ctx)
 367 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 368 | @@ -2493,8 +2511,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 369 |          return None
 370 |      for mid in cleared:
 371 |          a_by[mid] = off_writers(mid) or a_by[mid]
 372 | -    writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - \
 373 | -        {angle_reply.vendor}                   # every write stays on the angle's vendor, so a judge is always left
 374 | +    import providers as P
 375 | +    ab = router.backends.get(angle_reply.backend)       # every write stays on the angle's GATEWAY (ruling 85: under
 376 | +    writer_avoid = {P.gateway(router.backends[n]) for n in router.chain("angle_write") if n in router.backends} - \
 377 | +        {P.gateway(ab) if ab is not None else angle_reply.vendor}   # heimdall_first a family is its own maker, and
 378 | +    # a write may still fail over deepseek -> qwen as today); the verdicts avoid every writer's maker and family
 379 |      log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)" if candidate is None else
 380 |          f"  ruling 66: the candidate {candidate.get('source')} tried[{candidate.get('index')}] (angle "
 381 |          f"{candidate['ai'] + 1} line-up {candidate['n_lineup']}), as judged: its angle from {angle_reply.backend}, "
 382 | @@ -2857,10 +2878,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 383 |                      stale = [m for m in segs if (lambda b: b is None or b.vendor in writers_v or b.family in writers_f)(
 384 |                          router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
 385 |                      if stale:                                  # audit C2 K5: never judged by the writer's vendor
 386 | +                        rb, rdl = _second_bounds(router)
 387 |                          got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
 388 | -                                                         batch=SECOND_VERDICT_BATCH,      # ruling 82: off the writer,
 389 | -                                                         deadline_s=SECOND_VERDICT_DEADLINE_S,   # the chain, 120 s
 390 | -                                                         n=len(stale), store=None, cache=step_a_cache)
 391 | +                                                         batch=rb, deadline_s=rdl,        # ruling 82: off the writer,
 392 | +                                                         n=len(stale), store=None, cache=step_a_cache,
 393 | +                                                         kind="step_a_second", failover=True)   # ruling 88 (c)
 394 |                          bad = {}
 395 |                          for m in stale:
 396 |                              mid = m["moment_id"]
 397 | diff --git a/pipeline/speakers.py b/pipeline/speakers.py
 398 | index c479135..77c3efb 100644
 399 | --- a/pipeline/speakers.py
 400 | +++ b/pipeline/speakers.py
 401 | @@ -340,10 +340,10 @@ def attribute(router, seg, src, meta, seed=7, caps=None, lower_third=None):
 402 |      prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip(),
 403 |                             turn=turn["text"] if turn else f"(none: {turn_why})")
 404 |      r = None
 405 | -    try:
 406 | -        r = router.call("speaker_verdict", prompt, 900, seed)
 407 | -        v = _json(r.text)
 408 | -        rec = check(v, lines, clip, f"{before} {after}")
 409 | +    try:                                      # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 410 | +        r, (v, rec) = P.call_parsed(router, "speaker_verdict", prompt,
 411 | +                                    lambda t: (lambda v: (v, check(v, lines, clip, f"{before} {after}")))(_json(t)),
 412 | +                                    900, seed)
 413 |          ev = check_turn(v.get("turn"), rec["people"], turn["text"] if turn else "")
 414 |          rec = decide(rec, ev, rec["people"], lower_third)
 415 |          rec["turn"] = {"read": turn is not None, "why": turn_why, **({"source": cap_src, "start": turn["start"],
 416 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 417 | index 88ae8ad..d2bb3d4 100644
 418 | --- a/pipeline/spotlight.py
 419 | +++ b/pipeline/spotlight.py
 420 | @@ -776,7 +776,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 421 |      out["scorer"] = srec
 422 |      ms = [P.with_verdict(m, idx) for m in ms]
 423 |      wv, wf = P._writers(router)
 424 | -    a_by, fails, _, _ = P.prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log, cache=step_a_cache)
 425 | +    a_by, fails, _, _ = P.prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log, cache=step_a_cache,
 426 | +                                    kind="step_a_first", **P.first_bounds(router))   # as the medley's (rulings 85, 88)
 427 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 428 |      for m in ms:
 429 |          if m["moment_id"] not in cleared:
 430 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
 431 | index af4ccc1..d0bb83c 100644
 432 | --- a/pipeline/vo_fidelity.py
 433 | +++ b/pipeline/vo_fidelity.py
 434 | @@ -728,16 +728,13 @@ def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current
 435 |      import providers as P
 436 |      det = check_deterministic(segments, lines, manifest, current_levels)
 437 |      out = {"deterministic": det, "verdict": None, "backend": None, "measured": False, "replayed": False, "seed": seed}
 438 | -    r = None
 439 | -    try:
 440 | -        r = router.call("fidelity_verdict", verdict_prompt(segments, lines, manifest), 2500, seed,
 441 | -                        avoid_vendor=writer_vendor, avoid_family=writer_family)
 442 | +    try:                                      # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 443 | +        r, out["verdict"] = P.call_parsed(router, "fidelity_verdict", verdict_prompt(segments, lines, manifest),
 444 | +                                          lambda t: check_verdict(t, segments, lines, manifest), 2500, seed,
 445 | +                                          avoid_vendor=writer_vendor, avoid_family=writer_family)
 446 |          out["backend"], out["replayed"] = r.backend, bool(getattr(r, "replayed", False))
 447 | -        out["verdict"] = check_verdict(r.text, segments, lines, manifest)
 448 |          out["measured"] = True
 449 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 450 | -        if r is not None and isinstance(e, (ValueError, TypeError)) and hasattr(router, "reject"):
 451 | -            router.reject(r, str(e))
 452 |          out["verdict"] = {"ok": False, "claims": [], "violations": [{"slot": "-", "rule": "VERDICT_UNAVAILABLE",
 453 |                                                                        "detail": f"{type(e).__name__}: {str(e)[:200]}"}]}
 454 |      out["violations"] = det["violations"] + out["verdict"]["violations"]
 455 | diff --git a/tests/package/replay85.py b/tests/package/replay85.py
 456 | new file mode 100644
 457 | index 0000000..0644b02
 458 | --- /dev/null
 459 | +++ b/tests/package/replay85.py
 460 | @@ -0,0 +1,670 @@
 461 | +#!/usr/bin/env python3
 462 | +"""RULING 85.1 (orchestrator 21:15 Nov 13): THE REPLAY. Every recorded Grok verdict since the first ledger build is
 463 | +re-asked, with the SAME prompt, of Heimdall's model families: deepseek-v4.1-flash, z-ai/glm-5.3-flash, qwen3.8-27b.
 464 | +No new Grok spend: Grok's answers are read from the recordings (tests/package/fixtures/replies). Each answer is
 465 | +reduced to the pipeline's own DECISION with the pipeline's own parsers and bars, and compared with Grok's:
 466 | +- step A (context_verdict, <excerpt>): per clip, context_integrity.a_failures ([] passes). REFERENT_OUTSIDE is
 467 | +  counted on its own;
 468 | +- step C (context_verdict, <pair>): per clip, entails == "yes". This is a PROXY: the full rule also reads the
 469 | +  context window, which the prompt does not carry;
 470 | +- clips-alone (coherence_verdict, joins): the through-line stated, every clip >= COHERENCE_MIN, flagged joins <=
 471 | +  LY_MAX_BRIDGES; the flagged joins are compared too;
 472 | +- coherence (coherence_verdict, vo_point): the through-line, every rating >= COHERENCE_MIN;
 473 | +- hook rating (coherence_verdict, CANDIDATE): per hook, the lowest of scroll / alone >= HOOK_MIN (ruling 61);
 474 | +- fidelity (fidelity_verdict): per line, every claim "supported": "yes", or commentary with no test "yes". This is a
 475 | +  PROXY: the full check (verbatim supports) needs the package's inputs;
 476 | +- exclusion (exclusion_verdict): keep (no risk, about Bitcoin "yes") or exclude;
 477 | +- speaker (speaker_verdict): the speaker's name or "unknown". Naming no one where Grok named someone is "stricter".
 478 | +- step B (viewer_takeaway) has no decision of its own (it feeds step C): its contract and its time are reported.
 479 | +- The visual sheets (xai_vision) need their images. They are not in the recordings and come in a second pass.
 480 | +Stricter: Heimdall fails what Grok passed. Looser: Heimdall passes what Grok failed. An answer out of contract is
 481 | +"no verdict" (counted, never a pass). The anchors (the verdicts behind the delivered pins 0c68b589, 41f29b1f,
 482 | +37c5b5f5) must still pass; the step-A REFERENT_OUTSIDE refusals must still be refused.
 483 | +
 484 | +Spend: ruling 48's ledger (SPEND_LY.json, the order's $20 cap), roles "replay85_<model>", a reservation per call as
 485 | +always. Replies are recorded under tests/package/proof/replay85/replies, so a re-run is free. A call is abandoned at
 486 | +--deadline (300 s: production cuts at 120 s) and is then a timeout, with no decision; past-120 s answers are counted. RESULTS.jsonl is appended per (record, model); a re-run resumes.
 487 | +Usage: python3 -B tests/package/replay85.py [--workers 2] [--models deepseek,glm,qwen] [--types ...] [--limit N]
 488 | +                                            [--table-only]"""
 489 | +import argparse
 490 | +import glob
 491 | +import json
 492 | +import os
 493 | +import re
 494 | +import statistics
 495 | +import sys
 496 | +import threading
 497 | +import time
 498 | +from concurrent.futures import ThreadPoolExecutor
 499 | +
 500 | +HERE = os.path.dirname(os.path.abspath(__file__))
 501 | +REPO = os.path.dirname(os.path.dirname(HERE))
 502 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 503 | +sys.path.insert(0, HERE)
 504 | +import context_integrity as CI  # noqa: E402
 505 | +import package as PK  # noqa: E402
 506 | +import providers as P  # noqa: E402
 507 | +import speakers as SP  # noqa: E402
 508 | +
 509 | +WT = "/home/ultron/worktrees/pp-selectid"
 510 | +REPLIES = os.path.join(WT, "tests", "package", "fixtures", "replies")
 511 | +OUT = os.path.join(WT, "tests", "package", "proof", "replay85")
 512 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_LY.json")
 513 | +ENV = "/home/ultron/protocol_pulse/" + "." + "env"
 514 | +FIRST_LEDGER = "2026-11-13T07:37:38Z"          # ledger_20261113_073738: the first ledger build (UTC stamp)
 515 | +LIMIT_USD, LIMIT_BASIS = 20.0, "reported"      # ruling 83 (b): the order's cap, on the same ledger
 516 | +DEADLINE_S = 120.0                             # ruling 82's per-call deadline: answers past it are counted
 517 | +MODELS = {"deepseek": "heimdall:deepseek/deepseek-v4.1-flash", "glm": "heimdall:z-ai/glm-5.3-flash",
 518 | +          "qwen": "heimdall:qwen/qwen3.8-27b"}
 519 | +ANCHOR_PINS = {                                # the delivered pins (ruling 85.1's anchors)
 520 | +    "0c68b589": "tests/package/proof/ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json",
 521 | +    "41f29b1f": "tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json",
 522 | +    "37c5b5f5": "tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json",
 523 | +}
 524 | +TYPES = ("step_a", "step_c", "clips_alone", "coherence", "hook", "fidelity", "exclusion", "speaker", "step_b")
 525 | +DECIDING = tuple(t for t in TYPES if t != "step_b")      # step B has no decision of its own: not asked by default
 526 | +
 527 | +
 528 | +def kind(rec):
 529 | +    """The verdict type of a recorded call, from its role and its prompt's own template markers."""
 530 | +    role, pr = rec.get("role"), rec.get("prompt") or ""
 531 | +    if role == "context_verdict":
 532 | +        return "step_a" if '<excerpt label="' in pr else "step_c" if '<pair label="' in pr else None
 533 | +    if role == "coherence_verdict":
 534 | +        if 'CANDIDATE id="' in pr:
 535 | +            return "hook"
 536 | +        return "clips_alone" if '"followable"' in pr else "coherence" if '"vo_point"' in pr else None
 537 | +    return {"fidelity_verdict": "fidelity", "exclusion_verdict": "exclusion", "speaker_verdict": "speaker",
 538 | +            "viewer_takeaway": "step_b", "visual_check": "visual"}.get(role)
 539 | +
 540 | +
 541 | +def _json(text):
 542 | +    return json.loads(text.strip()) if isinstance(text, str) else None
 543 | +
 544 | +
 545 | +def decide(k, text, prompt):
 546 | +    """The DECISION a verdict's answer makes, by the pipeline's parsers and bars -> {unit: decision}; a decision is
 547 | +    True (pass / keep), False (fail / exclude), or a string (a name, for the speaker). Raises ValueError / TypeError /
 548 | +    KeyError for an answer out of contract (no verdict)."""
 549 | +    if k == "step_a":
 550 | +        labels = re.findall(r'<excerpt label="([^"]+)"', prompt)
 551 | +        A = CI._strict(text, {"excerpts"}, {"excerpts": CI.A_KEYS})
 552 | +        a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
 553 | +        if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
 554 | +            raise ValueError("step A must answer exactly the prompt's labels")
 555 | +        return {lb: tuple(sorted(CI.a_failures(a_by[lb]))) for lb in labels}
 556 | +    if k == "step_c":
 557 | +        labels = re.findall(r'<pair label="([^"]+)"', prompt)
 558 | +        C = CI._strict(text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
 559 | +                                                   "stronger_certainty", "raising_words")})
 560 | +        c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
 561 | +        if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
 562 | +            raise ValueError("step C must answer exactly the prompt's labels")
 563 | +        return {lb: c_by[lb]["entails"] == "yes" for lb in labels}
 564 | +    if k in ("clips_alone", "coherence"):
 565 | +        # the prompt's own template names the clip keys; an older template ('"<label>": 1') rated every CLIP label,
 566 | +        # the hook included, and an older contract also carried a top-level "hook" rating (both before ruling 61)
 567 | +        named = re.findall(r'"(clip_\d+)": 1\b', prompt)
 568 | +        labels = re.findall(r'CLIP label="([^"]+)"', prompt)
 569 | +        allowed = [set(named)] if named else [set(labels), set(labels) - {"hook"}]
 570 | +        v = _json(text)
 571 | +        want = {"through_line", "clips", "joins"} if k == "clips_alone" else {"through_line", "clips", "vo_point"}
 572 | +        if not isinstance(v, dict) or set(v) - {"hook"} != want or not isinstance(v["clips"], dict) or \
 573 | +                set(v["clips"]) not in allowed or any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()):
 574 | +            raise ValueError(f"{k} out of contract")
 575 | +        extra = []
 576 | +        if "hook" in v:
 577 | +            hv = v["hook"]
 578 | +            extra = [hv] if type(hv) is int else [x for x in hv.values() if type(x) is int] if isinstance(hv, dict) else []
 579 | +            if not extra or any(not 1 <= x <= 5 for x in extra):
 580 | +                raise ValueError(f"{k}: the hook's rating out of contract")
 581 | +            extra = [min(extra)]
 582 | +        if k == "coherence":
 583 | +            if type(v["vo_point"]) is not int or not 1 <= v["vo_point"] <= 5:
 584 | +                raise ValueError("coherence out of contract")
 585 | +            return {"package": PK._line_ok(v["through_line"]) and
 586 | +                    min(list(v["clips"].values()) + [v["vo_point"]] + extra) >= PK.COHERENCE_MIN}
 587 | +        joins = re.findall(r'"([^"]+ -> [^"]+)": \{"followable"', prompt)
 588 | +        if not isinstance(v["joins"], dict) or set(v["joins"]) != set(joins) or any(
 589 | +                not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 590 | +                for x in v["joins"].values()):
 591 | +            raise ValueError("clips-alone joins out of contract")
 592 | +        flagged = tuple(sorted(j for j in joins if v["joins"][j]["followable"] is False))
 593 | +        ok = PK._line_ok(v["through_line"]) and min(list(v["clips"].values()) + extra) >= PK.COHERENCE_MIN and \
 594 | +            len(flagged) <= PK.LY_MAX_BRIDGES
 595 | +        return {"lineup": ok, "flagged": flagged}
 596 | +    if k == "hook":
 597 | +        ids = re.findall(r'CANDIDATE id="([^"]+)"', prompt)
 598 | +        v = _json(text)
 599 | +        h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 600 | +        if not isinstance(h, dict) or set(h) != set(ids) or any(
 601 | +                not isinstance(x, dict) or any(type(x.get(p)) is not int or not 1 <= x[p] <= 5 for p in PK.HOOK_PARTS)
 602 | +                for x in h.values()):
 603 | +            raise ValueError("hook ratings out of contract")
 604 | +        return {i: min(h[i][p] for p in PK.HOOK_OWN) >= PK.HOOK_MIN for i in ids}
 605 | +    if k == "exclusion":
 606 | +        o = _json(text)
 607 | +        if not isinstance(o, dict) or set(o) != {"risks", "about_bitcoin", "why"} or not isinstance(o["risks"], list) \
 608 | +                or o["about_bitcoin"] not in ("yes", "no", "uncertain"):
 609 | +            raise ValueError("exclusion out of contract")
 610 | +        return {"moment": not o["risks"] and o["about_bitcoin"] == "yes"}
 611 | +    if k == "fidelity":
 612 | +        o = _json(text)
 613 | +        if not isinstance(o, dict) or set(o) != {"claims"} or not isinstance(o["claims"], list):
 614 | +            raise ValueError("fidelity out of contract")
 615 | +        by = {}
 616 | +        for c in o["claims"]:
 617 | +            if not isinstance(c, dict) or not isinstance(c.get("line"), str) or \
 618 | +                    c.get("supported") not in ("yes", "no", "uncertain", "n/a") or not isinstance(c.get("tests"), dict):
 619 | +                raise ValueError("fidelity claim out of contract")
 620 | +            ok = c["supported"] == "yes" or (c.get("class") == "commentary" and
 621 | +                                             not any(t == "yes" for t in c["tests"].values()))
 622 | +            by[c["line"]] = by.get(c["line"], True) and ok
 623 | +        return by
 624 | +    if k == "speaker":
 625 | +        v = SP._json(text)
 626 | +        if not isinstance(v, dict) or not isinstance(v.get("people"), list) or not isinstance(v.get("speaker"), dict):
 627 | +            raise ValueError("speaker out of contract")
 628 | +        n = SP._norm(v["speaker"].get("name") or "")
 629 | +        return {"speaker": n if n and n != SP.UNKNOWN else SP.UNKNOWN}
 630 | +    if k == "step_b":
 631 | +        labels = re.findall(r'"label": "([^"]+)"', prompt) or []
 632 | +        CI._strict(text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
 633 | +                                                      "relations": ("labels", "relation")})
 634 | +        return {"contract": True}
 635 | +    raise ValueError(f"no decision rule for {k}")
 636 | +
 637 | +
 638 | +def compare(k, g, h):
 639 | +    """Grok's decision g against Heimdall's h for one unit -> "agree" | "stricter" | "looser" | "different"."""
 640 | +    if g == h:
 641 | +        return "agree"
 642 | +    if k == "speaker":
 643 | +        if h == SP.UNKNOWN:
 644 | +            return "stricter"
 645 | +        return "looser" if g == SP.UNKNOWN else "different"
 646 | +    if k == "step_a":                                  # a tuple of failures: [] passes
 647 | +        if bool(g) == bool(h):
 648 | +            return "agree"                             # both fail (for possibly different rules): the decision agrees
 649 | +        return "stricter" if h else "looser"
 650 | +    if isinstance(g, tuple):                           # the flagged joins: compared as a set
 651 | +        return "different"
 652 | +    return "stricter" if g is True and h is False else "looser" if g is False and h is True else "different"
 653 | +
 654 | +
 655 | +def records(since=FIRST_LEDGER, anchors=()):
 656 | +    """Every recorded Grok verdict (xAI text back-end) since `since`, plus older ones whose prompt carries an anchor
 657 | +    pin's clip text. -> [(path, rec, kind, anchor names)]."""
 658 | +    out = []
 659 | +    for p in sorted(glob.glob(os.path.join(REPLIES, "*", "*.json"))):
 660 | +        try:
 661 | +            with open(p) as f:
 662 | +                r = json.load(f)
 663 | +        except (OSError, ValueError):
 664 | +            continue
 665 | +        if not str(r.get("backend", "")).startswith("xai:"):
 666 | +            continue
 667 | +        k = kind(r)
 668 | +        if k is None:
 669 | +            continue
 670 | +        pr = _norm(r.get("prompt") or "")
 671 | +        hit = sorted({name for name, texts in anchors for t in texts if t and t in pr})
 672 | +        if str(r.get("recorded_at", "")) >= since:
 673 | +            out.append((p, r, k, hit))
 674 | +        elif hit:                                      # an older anchor record: only where Grok's answer still reads
 675 | +            try:
 676 | +                decide(k, r["text"], r.get("prompt") or "")
 677 | +                out.append((p, r, k, hit))
 678 | +            except (ValueError, TypeError, KeyError):
 679 | +                pass
 680 | +    seen, uniq = {}, []                                # the same prompt asked again (another seed): asked once here
 681 | +    for x in out:
 682 | +        key = (x[1].get("role"), x[1].get("prompt"), x[1].get("system"), x[1].get("max_tokens"))
 683 | +        if key in seen:
 684 | +            seen[key][3].extend(a for a in x[3] if a not in seen[key][3])
 685 | +            continue
 686 | +        seen[key] = x
 687 | +        uniq.append(x)
 688 | +    return uniq
 689 | +
 690 | +
 691 | +def _norm(t):
 692 | +    """Lower case letters and digits, single spaces: a prompt quotes a clip through quote_data (escaping)."""
 693 | +    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(t).lower()).split())
 694 | +
 695 | +
 696 | +def anchor_texts():
 697 | +    """[(pin name, [its segments' approved texts, normalised, 60 characters from the 10th])]: a prompt that carries
 698 | +    one of them judged that clip."""
 699 | +    out = []
 700 | +    for name, rel in ANCHOR_PINS.items():
 701 | +        try:
 702 | +            with open(os.path.join(WT, rel)) as f:
 703 | +                pin = json.load(f)
 704 | +        except (OSError, ValueError):
 705 | +            out.append((name, []))
 706 | +            continue
 707 | +        segs = pin.get("segments") or (pin.get("package") or {}).get("segments") or []
 708 | +        out.append((name, [_norm(s.get("approved_text") or s.get("text") or "")[10:70] for s in segs
 709 | +                           if isinstance(s, dict)]))
 710 | +    return out
 711 | +
 712 | +
 713 | +def run(args):
 714 | +    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
 715 | +    res_path = os.path.join(OUT, "RESULTS.jsonl")
 716 | +    done = set()
 717 | +    if os.path.exists(res_path):
 718 | +        with open(res_path) as f:
 719 | +            for line in f:
 720 | +                try:
 721 | +                    x = json.loads(line)
 722 | +                    done.add((x["record"], x["model"]))
 723 | +                except (ValueError, KeyError):
 724 | +                    pass
 725 | +    anchors = anchor_texts()
 726 | +    recs = [x for x in records(anchors=anchors) if x[2] in args.types]
 727 | +    if args.limit:
 728 | +        recs = recs[:args.limit]
 729 | +    models = [m for m in args.models if m in MODELS]
 730 | +    chains = {f"replay85_{m}": [MODELS[m]] for m in models}
 731 | +    router = P.Router(env_path=ENV, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND, limit_usd=LIMIT_USD,
 732 | +                      limit_basis=LIMIT_BASIS, chains=chains)
 733 | +    lock = threading.Lock()
 734 | +    # round-robin by verdict type, the records since the first ledger build first, so an early table covers them all
 735 | +    order, by_type = [], {}
 736 | +    for x in sorted(recs, key=lambda x: str(x[1].get("recorded_at", "")) < FIRST_LEDGER):
 737 | +        by_type.setdefault(x[2], []).append(x)
 738 | +    while any(by_type.values()):
 739 | +        for k in list(by_type):
 740 | +            if by_type[k]:
 741 | +                order.append(by_type[k].pop(0))
 742 | +    jobs = [(p, r, k, hit, m) for (p, r, k, hit) in order for m in models
 743 | +            if (os.path.relpath(p, WT), m) not in done]
 744 | +    print(f"replay85: {len(recs)} Grok records, {len(models)} models, {len(jobs)} calls to make "
 745 | +          f"({len(done)} already in RESULTS)", flush=True)
 746 | +
 747 | +    def one(job):
 748 | +        p, r, k, hit, m = job
 749 | +        row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "anchors": hit,
 750 | +               "grok_recorded_at": r.get("recorded_at"), "grok_seconds": r.get("seconds"),
 751 | +               "grok_usd_reported": (r.get("usage") or {}).get("usd_reported")}
 752 | +        try:
 753 | +            row["grok"] = {u: (list(d) if isinstance(d, tuple) else d) for u, d in decide(k, r["text"], r["prompt"]).items()}
 754 | +        except (ValueError, TypeError, KeyError) as e:
 755 | +            row["grok"], row["grok_error"] = None, f"{type(e).__name__}: {str(e)[:160]}"
 756 | +        t0 = time.time()
 757 | +        router.down.pop(MODELS[m], None)               # a rate limit is never a verdict: each call is tried afresh
 758 | +        try:
 759 | +            rep = router.call(f"replay85_{m}", r["prompt"], int(r.get("max_tokens") or 2000), int(r.get("seed") or 7),
 760 | +                              system=r.get("system"), deadline_s=args.deadline or None)
 761 | +            row.update(seconds=round(rep.seconds or (time.time() - t0), 2), cached=bool(rep.cached),
 762 | +                       usd_reported=(rep.usage or {}).get("usd_reported"), usd_estimate=rep.usd)
 763 | +            try:
 764 | +                h = decide(k, rep.text, r["prompt"])
 765 | +                row["heimdall"] = {u: (list(d) if isinstance(d, tuple) else d) for u, d in h.items()}
 766 | +            except (ValueError, TypeError, KeyError) as e:
 767 | +                row["heimdall"], row["heimdall_error"] = None, f"out of contract: {type(e).__name__}: {str(e)[:160]}"
 768 | +                router.reject(rep)
 769 | +        except (P.ProviderError, P.SpendLimit) as e:
 770 | +            if "HTTP 429" in str(e):                   # rate limited (after the router's own backoff): no row, so a
 771 | +                time.sleep(30)                         # resume asks it again; never counted as the model's answer
 772 | +                return None
 773 | +            row.update(seconds=round(time.time() - t0, 2), heimdall=None,
 774 | +                       heimdall_error=f"{type(e).__name__}: {str(e)[:200]}")
 775 | +        if row.get("grok") is not None and row.get("heimdall") is not None:
 776 | +            row["compare"] = {u: compare(k, tuple(g) if isinstance(g, list) else g,
 777 | +                                         tuple(row["heimdall"].get(u)) if isinstance(row["heimdall"].get(u), list)
 778 | +                                         else row["heimdall"].get(u))
 779 | +                              for u, g in row["grok"].items()}
 780 | +        with lock:
 781 | +            with open(res_path, "a") as f:
 782 | +                f.write(json.dumps(row) + "\n")
 783 | +        return row
 784 | +
 785 | +    n_done = [0]
 786 | +
 787 | +    def per_model(m):                                  # one pool per model: a slow model never starves the others
 788 | +        mine = [j for j in jobs if j[4] == m]
 789 | +        with ThreadPoolExecutor(max_workers=args.per_model.get(m, args.workers)) as ex:
 790 | +            for _ in ex.map(one, mine):
 791 | +                with lock:
 792 | +                    n_done[0] += 1
 793 | +                    if n_done[0] % 10 == 0 or n_done[0] == len(jobs):
 794 | +                        print(f"  {n_done[0]}/{len(jobs)} at {time.strftime('%H:%M:%S')}", flush=True)
 795 | +    ts = [threading.Thread(target=per_model, args=(m,)) for m in models]
 796 | +    for t in ts:
 797 | +        t.start()
 798 | +    for t in ts:
 799 | +        t.join()
 800 | +    table()
 801 | +
 802 | +
 803 | +def grok_self():
 804 | +    """The baseline: Grok against GROK on the same prompt asked again (another seed, another build), from every
 805 | +    recorded Grok answer. -> {type: {"pairs": n, "agree": n}} by the same decide / compare."""
 806 | +    by = {}
 807 | +    for p in sorted(glob.glob(os.path.join(REPLIES, "*", "*.json"))):
 808 | +        try:
 809 | +            with open(p) as f:
 810 | +                r = json.load(f)
 811 | +        except (OSError, ValueError):
 812 | +            continue
 813 | +        if not str(r.get("backend", "")).startswith("xai:"):
 814 | +            continue
 815 | +        k = kind(r)
 816 | +        if k not in DECIDING:
 817 | +            continue
 818 | +        try:
 819 | +            d = decide(k, r["text"], r.get("prompt") or "")
 820 | +        except (ValueError, TypeError, KeyError):
 821 | +            continue
 822 | +        by.setdefault((k, r.get("role"), r.get("prompt"), r.get("max_tokens")), []).append(d)
 823 | +        if k == "step_a":                              # the same excerpt inside OTHER batches too (its own block)
 824 | +            for lb, blk in re.findall(r'<excerpt label="([^"]+)"(.*?)</excerpt>', r.get("prompt") or "", re.S):
 825 | +                if lb in d:
 826 | +                    by.setdefault(("step_a_excerpt", lb, blk), []).append({lb: d[lb]})
 827 | +    out = {}
 828 | +    for (k, *_), ds in by.items():
 829 | +        for i in range(len(ds)):
 830 | +            for j in range(i + 1, len(ds)):
 831 | +                for u, g in ds[i].items():
 832 | +                    if u not in ds[j]:
 833 | +                        continue
 834 | +                    o = out.setdefault(k, {"pairs": 0, "agree": 0})
 835 | +                    o["pairs"] += 1
 836 | +                    o["agree"] += compare("step_a" if k == "step_a_excerpt" else k, g, ds[j][u]) == "agree"
 837 | +    if (out.get("step_a_excerpt") or {}).get("pairs", 0) > (out.get("step_a") or {}).get("pairs", 0):
 838 | +        out["step_a_identical_prompt"] = out.get("step_a")
 839 | +        out["step_a"] = out["step_a_excerpt"]            # the bar for step A: the same excerpt, any batch
 840 | +    return out
 841 | +
 842 | +
 843 | +_PROMPTS = {}
 844 | +
 845 | +
 846 | +def anchor_units(row, anchors):
 847 | +    """The units of a row that are an anchor's OWN decision (a delivered pin's clip let through):
 848 | +    - step A, step C, hook: the unit whose own block (<excerpt>, <pair>, CANDIDATE line) quotes an anchor clip;
 849 | +    - clips-alone, coherence, fidelity: every unit, only when the prompt quotes ALL clips of one anchor pin (its own
 850 | +      line-up);
 851 | +    - exclusion, speaker: the one unit when the prompt quotes an anchor clip.
 852 | +    -> {unit: [pin names]}."""
 853 | +    if not row.get("anchors"):
 854 | +        return {}
 855 | +    pr = _PROMPTS.get(row["record"])
 856 | +    if pr is None:
 857 | +        try:
 858 | +            with open(os.path.join(WT, row["record"])) as f:
 859 | +                pr = _PROMPTS[row["record"]] = json.load(f).get("prompt") or ""
 860 | +        except (OSError, ValueError):
 861 | +            return {}
 862 | +    k, out = row["type"], {}
 863 | +    if k in ("step_a", "step_c", "hook"):
 864 | +        pat = {"step_a": r'<excerpt label="([^"]+)"(.*?)</excerpt>', "step_c": r'<pair label="([^"]+)"(.*?)</pair>',
 865 | +               "hook": r'CANDIDATE id="([^"]+)"([^\n]*)'}[k]
 866 | +        for u, blk in re.findall(pat, pr, re.S):
 867 | +            hit = [n for n, ts in anchors for t in ts if t and t in _norm(blk)]
 868 | +            if hit:
 869 | +                out[u] = sorted(set(hit))
 870 | +        return out
 871 | +    npr = _norm(pr)
 872 | +    if k in ("clips_alone", "coherence", "fidelity"):
 873 | +        whole = [n for n, ts in anchors if ts and all(t in npr for t in ts if t)]
 874 | +        return {u: whole for u in (row.get("grok") or {})} if whole else {}
 875 | +    hit = [n for n, ts in anchors for t in ts if t and t in npr]
 876 | +    return {u: sorted(set(hit)) for u in (row.get("grok") or {})} if hit else {}
 877 | +
 878 | +
 879 | +def table():
 880 | +    """TABLE.md from RESULTS.jsonl: per verdict type and model, with Grok's agreement with itself as the baseline."""
 881 | +    rows = []
 882 | +    with open(os.path.join(OUT, "RESULTS.jsonl")) as f:
 883 | +        for line in f:
 884 | +            try:
 885 | +                rows.append(json.loads(line))
 886 | +            except ValueError:
 887 | +                pass
 888 | +    out = ["# Ruling 85.1: the replay of Grok's recorded verdicts on Heimdall's families", "",
 889 | +           f"Built {time.strftime('%Y-%m-%d %H:%M %Z')} from {len(rows)} (record, model) rows. A unit is one decision "
 890 | +           "(a clip, a line-up, a hook, a line, a moment). Stricter: Heimdall fails what Grok passed. Looser: Heimdall "
 891 | +           "passes what Grok failed. Different: another name, or other flagged joins with the same decision.", "",
 892 | +           "| type | model | records | answered | no verdict | units | agree | stricter | looser | different | "
 893 | +           "agree % | median s | > 120 s | timeouts | errors | usd reported |", "|" + "---|" * 16]
 894 | +    for k in TYPES:
 895 | +        for m in MODELS:
 896 | +            rs = [r for r in rows if r["type"] == k and r["model"] == m]
 897 | +            if not rs:
 898 | +                continue
 899 | +            ans = [r for r in rs if r.get("heimdall") is not None]
 900 | +            nov = [r for r in rs if r.get("heimdall") is None and "out of contract" in str(r.get("heimdall_error"))]
 901 | +            tmo = [r for r in rs if r.get("heimdall") is None and "abandoned at the deadline" in
 902 | +                   str(r.get("heimdall_error"))]
 903 | +            err = [r for r in rs if r.get("heimdall") is None and r not in nov and r not in tmo]
 904 | +            cmp_ = [c for r in rs for c in (r.get("compare") or {}).values()]
 905 | +            n = {x: cmp_.count(x) for x in ("agree", "stricter", "looser", "different")}
 906 | +            secs = [r["seconds"] for r in rs if isinstance(r.get("seconds"), (int, float)) and not r.get("cached")]
 907 | +            usd = sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported")) and not r.get("cached"))
 908 | +            out.append(f"| {k} | {m} | {len(rs)} | {len(ans)} | {len(nov)} | {len(cmp_)} | {n['agree']} | "
 909 | +                       f"{n['stricter']} | {n['looser']} | {n['different']} | "
 910 | +                       f"{(100 * n['agree'] / len(cmp_)) if cmp_ else 0:.0f} | "
 911 | +                       f"{statistics.median(secs) if secs else 0:.0f} | {sum(1 for s in secs if s > DEADLINE_S)} | "
 912 | +                       f"{len(tmo)} | {len(err)} | {usd:.4f} |")
 913 | +    base = grok_self()
 914 | +    out += ["", "## The baseline: Grok against Grok (the same prompt asked again: another seed or build)", "",
 915 | +            "| type | unit pairs | agree | agree % |", "|---|---|---|---|"]
 916 | +    for k in DECIDING + ("step_a_excerpt",):
 917 | +        b = base.get(k)
 918 | +        if b:
 919 | +            out.append(f"| {k} | {b['pairs']} | {b['agree']} | {100 * b['agree'] / b['pairs']:.0f} |")
 920 | +    anchors = anchor_texts()
 921 | +    out += ["", "## Anchors: the delivered pins' own decisions that Grok passed must still pass", ""]
 922 | +    for m in MODELS:
 923 | +        units = bad = nov = 0
 924 | +        ex = []
 925 | +        for r in rows:
 926 | +            if r["model"] != m:
 927 | +                continue
 928 | +            au = anchor_units(r, anchors)
 929 | +            for u in au:
 930 | +                g = (r.get("grok") or {}).get(u)
 931 | +                if g is None or (r["type"] == "step_a" and g) or g is False:
 932 | +                    continue                           # Grok did not pass it: not a decision that let a clip through
 933 | +                units += 1
 934 | +                if r.get("heimdall") is None:
 935 | +                    nov += 1
 936 | +                    ex.append(f"{r['type']} {u} {au[u]}: no Heimdall verdict")
 937 | +                elif (r.get("compare") or {}).get(u) == "stricter":
 938 | +                    bad += 1
 939 | +                    ex.append(f"{r['type']} {u} {au[u]}: FAILED ({r['record'][-24:]})")
 940 | +        out.append(f"- {m}: {units} anchor decisions Grok passed; {bad} failed by {m}; {nov} without a verdict" +
 941 | +                   (": " + "; ".join(ex[:10]) if ex else ""))
 942 | +    out += ["", "## Step A's REFERENT_OUTSIDE refusals (Grok's) must still be refused", ""]
 943 | +    for m in MODELS:
 944 | +        tot = kept = ro = 0
 945 | +        for r in rows:
 946 | +            if r["model"] != m or r["type"] != "step_a" or not r.get("grok") or r.get("heimdall") is None:
 947 | +                continue                               # only the answered rows: no answer is no verdict either way
 948 | +            for u, g in r["grok"].items():
 949 | +                if "REFERENT_OUTSIDE" in (g or []):
 950 | +                    tot += 1
 951 | +                    h = (r.get("heimdall") or {}).get(u)
 952 | +                    kept += bool(h)
 953 | +                    ro += "REFERENT_OUTSIDE" in (h or [])
 954 | +        out.append(f"- {m}: Grok refused {tot} clips for REFERENT_OUTSIDE; Heimdall refuses {kept} of them "
 955 | +                   f"({ro} for REFERENT_OUTSIDE itself)")
 956 | +    vp = os.path.join(OUT, "VISUAL.jsonl")
 957 | +    if os.path.exists(vp):                             # the visual sheets (run_visual): the set of flags per sheet
 958 | +        with open(vp) as f:
 959 | +            vis = [json.loads(x) for x in f if x.strip()]
 960 | +        out += ["", "## The visual sheets (nemotron and qwen against Grok's flags)", "",
 961 | +                "| model | sheets | answered | agree | stricter | looser | different | median s | usd reported |",
 962 | +                "|---|---|---|---|---|---|---|---|---|"]
 963 | +        for m in VISION:
 964 | +            vs = [v for v in vis if v.get("model") == m]
 965 | +            if not vs:
 966 | +                continue
 967 | +            c = [v.get("compare") for v in vs if v.get("compare")]
 968 | +            secs = [v["seconds"] for v in vs if isinstance(v.get("seconds"), (int, float))]
 969 | +            out.append(f"| {m} | {len(vs)} | {len(c)} | {c.count('agree')} | {c.count('stricter')} | "
 970 | +                       f"{c.count('looser')} | {c.count('different')} | "
 971 | +                       f"{statistics.median(secs) if secs else 0:.0f} | "
 972 | +                       f"{sum(float(v.get('usd_reported') or 0) for v in vs):.4f} |")
 973 | +        skipped = [v for v in vis if v.get("skipped")]
 974 | +        if skipped:
 975 | +            out.append(f"- {len(skipped)} sheet(s) skipped: " + "; ".join(v["skipped"] for v in skipped)[:300])
 976 | +        sheets = {v["sheet"] for v in vis if v.get("sheet") and not v.get("skipped")}
 977 | +        flagged = {v["sheet"] for v in vis if v.get("grok")}
 978 | +        out.append(f"- Grok flagged {len(flagged)} of the {len(sheets)} sheets compared; agreement on unflagged sheets "
 979 | +                   f"says little about a model's eye for a flag.")
 980 | +    out += propose(rows, base)
 981 | +    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
 982 | +        f.write("\n".join(out) + "\n")
 983 | +    print("\n".join(out), flush=True)
 984 | +
 985 | +
 986 | +ROLES = {"context_verdict": ("step_a", "step_c"), "coherence_verdict": ("clips_alone", "coherence", "hook"),
 987 | +         "fidelity_verdict": ("fidelity",), "exclusion_verdict": ("exclusion",), "speaker_verdict": ("speaker",)}
 988 | +MIN_UNITS = 10
 989 | +
 990 | +
 991 | +def passes(rows, base, k, m):
 992 | +    """The PROPOSED rule (the orchestrator rules it): -> (pass, [reasons it fails])."""
 993 | +    rs = [r for r in rows if r["type"] == k and r["model"] == m]
 994 | +    cmp_ = [c for r in rs for c in (r.get("compare") or {}).values()]
 995 | +    why = []
 996 | +    if len(cmp_) < MIN_UNITS:
 997 | +        why.append(f"only {len(cmp_)} decisions (< {MIN_UNITS})")
 998 | +    anchors = anchor_texts()
 999 | +    if any((r.get("compare") or {}).get(u) == "stricter" for r in rs for u in anchor_units(r, anchors)):
1000 | +        why.append("an anchor decision Grok passed is failed")
1001 | +    if k == "step_a":
1002 | +        miss = sum(1 for r in rs if r.get("grok") and r.get("heimdall") is not None for u, g in r["grok"].items()
1003 | +                   if "REFERENT_OUTSIDE" in (g or []) and not r["heimdall"].get(u))
1004 | +        if miss:
1005 | +            why.append(f"{miss} REFERENT_OUTSIDE refusal(s) let through")
1006 | +    agree = 100 * cmp_.count("agree") / len(cmp_) if cmp_ else 0
1007 | +    b = base.get(k) or {}
1008 | +    bar = 100 * b["agree"] / b["pairs"] if b.get("pairs", 0) >= 5 else 75.0
1009 | +    if agree < bar:
1010 | +        why.append(f"agreement {agree:.0f}% < the bar {bar:.0f}%")
1011 | +    ans = [r for r in rs if r.get("heimdall") is not None]
1012 | +    nov = [r for r in rs if r.get("heimdall") is None and "out of contract" in str(r.get("heimdall_error"))]
1013 | +    if ans and len(ans) / max(1, len(ans) + len(nov)) < 0.9:
1014 | +        why.append(f"{len(nov)} of {len(ans) + len(nov)} answers out of contract")
1015 | +    secs = [r["seconds"] for r in rs if isinstance(r.get("seconds"), (int, float)) and not r.get("cached")]
1016 | +    if secs and statistics.median(secs) > DEADLINE_S:
1017 | +        why.append(f"median {statistics.median(secs):.0f} s > {DEADLINE_S:.0f} s")
1018 | +    return not why, why, agree, (statistics.median(secs) if secs else None)
1019 | +
1020 | +
1021 | +def propose(rows, base):
1022 | +    """The proposed Heimdall-first list per role: the families that pass EVERY type of the role, best agreement
1023 | +    first; Grok last; a role with fewer than two passing families keeps Grok as its second family."""
1024 | +    out = ["", "## The proposed routing (the rule is the orchestrator's to rule)", ""]
1025 | +    for role, types in ROLES.items():
1026 | +        ok, notes = [], []
1027 | +        for m in MODELS:
1028 | +            res = [(k, passes(rows, base, k, m)) for k in types]
1029 | +            if all(x[1][0] for x in res):
1030 | +                ok.append((m, min(x[1][2] for x in res)))
1031 | +            notes.append(f"{m}: " + ("PASSES" if all(x[1][0] for x in res) else
1032 | +                                     "; ".join(f"{k}: {', '.join(x[1])}" for k, x in res if not x[0])))
1033 | +        order = [m for m, _ in sorted(ok, key=lambda x: -x[1])]
1034 | +        tail = "Grok last" if len(order) >= 2 else "Grok as the second family (fewer than two Heimdall families pass)"
1035 | +        out.append(f"- {role} ({', '.join(types)}): {' -> '.join(order) or 'none'}; {tail}")
1036 | +        out += [f"  - {n}" for n in notes]
1037 | +    return out
1038 | +
1039 | +
1040 | +VISION = {"nemotron": "heimdall:nvidia/nemotron-3.5-super-vl", "qwen": "heimdall:qwen/qwen3.8-27b"}
1041 | +
1042 | +
1043 | +def run_visual(args):
1044 | +    """The visual sheets (ruling 85.1: "and nemotron for the visual sheets"). Every sheet Grok judged is in
1045 | +    tests/package/proof/VISUAL_CACHE.json, with its path, sha256 and frame times. The prompt is rebuilt exactly as
1046 | +    visual_pin.visual_for builds it (PROMPT.format(n, text) and the sheet image), and asked of nemotron and qwen. The
1047 | +    decision is visual_pin.flags of the verdict (the set of flags), compared with Grok's. A sheet whose bytes changed,
1048 | +    or whose moment text cannot be found, is skipped and said so."""
1049 | +    import base64
1050 | +    import hashlib
1051 | +    import visual_pin as VP
1052 | +    with open(os.path.join(WT, "tests", "package", "proof", "VISUAL_CACHE.json")) as f:
1053 | +        cache = json.load(f)
1054 | +    texts = {}
1055 | +    for p in sorted(glob.glob(os.path.join(WT, "tests", "package", "proof", "ledger_*", "inputs.json"))):
1056 | +        try:
1057 | +            with open(p) as f:
1058 | +                for m in json.load(f).get("moments") or []:
1059 | +                    texts.setdefault(m.get("moment_id"), m.get("text"))
1060 | +        except (OSError, ValueError):
1061 | +            continue
1062 | +    router = P.Router(env_path=ENV, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND, limit_usd=LIMIT_USD,
1063 | +                      limit_basis=LIMIT_BASIS, chains={f"replay85v_{m}": [n] for m, n in VISION.items()})
1064 | +    rows = []
1065 | +    for k, g in cache.items():
1066 | +        sh, mid = g.get("sheet") or {}, k.split(":")[0]
1067 | +        path = sh.get("path") or ""
1068 | +        try:
1069 | +            with open(path, "rb") as f:
1070 | +                raw = f.read()
1071 | +        except OSError:
1072 | +            rows.append({"sheet": k, "skipped": f"the sheet is not on disk: {path}"})
1073 | +            continue
1074 | +        if hashlib.sha256(raw).hexdigest() != sh.get("sha256") or texts.get(mid) is None:
1075 | +            rows.append({"sheet": k, "skipped": "the sheet's bytes changed, or its moment's text is not found"})
1076 | +            continue
1077 | +        prompt = {"text": VP.PROMPT.format(n=len(sh.get("times") or []), text=str(texts[mid]).replace('"', "'")),
1078 | +                  "images": [base64.b64encode(raw).decode()]}
1079 | +        grok = sorted(g.get("flags") or [])
1080 | +        for m in VISION:
1081 | +            t0 = time.time()
1082 | +            row = {"sheet": k, "model": m, "grok": grok}
1083 | +            try:
1084 | +                r = router.call(f"replay85v_{m}", prompt, 1500, 7)
1085 | +                row.update(seconds=round(r.seconds or (time.time() - t0), 2),
1086 | +                           usd_reported=(r.usage or {}).get("usd_reported"))
1087 | +                try:
1088 | +                    row["heimdall"] = sorted(VP.flags(VP.check(VP._json(r.text))))
1089 | +                    h, gg = set(row["heimdall"]), set(grok)
1090 | +                    row["compare"] = "agree" if h == gg else "stricter" if h > gg else "looser" if h < gg \
1091 | +                        else "different"
1092 | +                except (ValueError, TypeError, KeyError) as e:
1093 | +                    row["heimdall"], row["error"] = None, f"out of contract: {type(e).__name__}: {str(e)[:120]}"
1094 | +                    router.reject(r)
1095 | +            except (P.ProviderError, P.SpendLimit) as e:
1096 | +                row.update(heimdall=None, error=f"{type(e).__name__}: {str(e)[:160]}",
1097 | +                           seconds=round(time.time() - t0, 2))
1098 | +            rows.append(row)
1099 | +            print(json.dumps(row)[:300], flush=True)
1100 | +    with open(os.path.join(OUT, "VISUAL.jsonl"), "w") as f:
1101 | +        f.write("".join(json.dumps(r) + "\n" for r in rows))
1102 | +    return rows
1103 | +
1104 | +
1105 | +def main():
1106 | +    ap = argparse.ArgumentParser()
1107 | +    ap.add_argument("--workers", type=int, default=2, help="calls in flight per model")
1108 | +    ap.add_argument("--models", default="deepseek,glm,qwen")
1109 | +    ap.add_argument("--per-model", default="", help="calls in flight per model, e.g. deepseek=12,glm=8")
1110 | +    ap.add_argument("--deadline", type=float, default=300.0,
1111 | +                    help="seconds a call may take (abandoned past it: a timeout; production cuts at 120 s)")
1112 | +    ap.add_argument("--types", default=",".join(DECIDING))
1113 | +    ap.add_argument("--limit", type=int, default=0)
1114 | +    ap.add_argument("--table-only", action="store_true")
1115 | +    ap.add_argument("--visual", action="store_true", help="the visual sheets only (nemotron and qwen)")
1116 | +    a = ap.parse_args()
1117 | +    a.models, a.types = a.models.split(","), a.types.split(",")
1118 | +    a.per_model = {k: int(v) for k, v in (x.split("=") for x in a.per_model.split(",") if x)}
1119 | +    if a.table_only:
1120 | +        table()
1121 | +        return 0
1122 | +    if a.visual:
1123 | +        run_visual(a)
1124 | +        return 0
1125 | +    run(a)
1126 | +    return 0
1127 | +
1128 | +
1129 | +if __name__ == "__main__":
1130 | +    sys.exit(main())
1131 | diff --git a/tests/package/shadow86.py b/tests/package/shadow86.py
1132 | new file mode 100644
1133 | index 0000000..51790bd
1134 | --- /dev/null
1135 | +++ b/tests/package/shadow86.py
1136 | @@ -0,0 +1,148 @@
1137 | +#!/usr/bin/env python3
1138 | +"""RULING 86 (orchestrator 21:18 Nov 13): THE SHADOW'S SIDE-BY-SIDE. A heimdall_first build writes SHADOW86.jsonl in
1139 | +its build directory: one line per verdict Heimdall decided, with Grok's answer to the SAME prompt (asked in shadow,
1140 | +never deciding: providers.Router). This reads it with the replay's decision rules (replay85.kind / decide / compare)
1141 | +and writes SHADOW86.md there:
1142 | +- every decision where Heimdall and Grok differ, and which side was stricter;
1143 | +- whether the pin would have sealed under Grok: a verdict on the pin's clips where Grok fails what Heimdall passed
1144 | +  would have stopped it. This is read from the verdicts themselves; the gates that depend on them are not re-run;
1145 | +- verdict types without a decision rule (the visual sheets, step B) are listed as "not compared".
1146 | +tests/package/proof/SHADOW86.json keeps the pins in order and the streak of pins with no decision-changing
1147 | +difference; the build driver stops asking the shadow when the streak reaches routing.shadow_until_clean_pins (3).
1148 | +Usage: python3 -B tests/package/shadow86.py <build dir>   (re-reads a build's SHADOW86.jsonl, rewrites its report)"""
1149 | +import json
1150 | +import os
1151 | +import sys
1152 | +import time
1153 | +
1154 | +HERE = os.path.dirname(os.path.abspath(__file__))
1155 | +sys.path.insert(0, HERE)
1156 | +import replay85 as R  # noqa: E402
1157 | +
1158 | +STATE = os.path.join(HERE, "proof", "SHADOW86.json")
1159 | +
1160 | +
1161 | +def _load(path=STATE):
1162 | +    try:
1163 | +        with open(path) as f:
1164 | +            d = json.load(f)
1165 | +        return d if isinstance(d, dict) and isinstance(d.get("pins"), list) else {"pins": [], "clean_streak": 0}
1166 | +    except (OSError, ValueError):
1167 | +        return {"pins": [], "clean_streak": 0}
1168 | +
1169 | +
1170 | +def clean_streak(path=STATE):
1171 | +    """The pins in a row with no decision-changing difference (0 when nothing is recorded or the file cannot be read:
1172 | +    the shadow then keeps running, which is the safe side)."""
1173 | +    return int(_load(path).get("clean_streak") or 0)
1174 | +
1175 | +
1176 | +def pin_texts(res):
1177 | +    """The SEALED pins' clip texts, normalised as replay85 matches prompts: the medley's (res["pin"], set by the pin
1178 | +    stage, with res["package"] as sealed, adopted texts included) and the spotlight's (RULING 90: res["spotlight_pin"],
1179 | +    with res["spotlight"]["package"]). None sealed (no package, or the pin stage refused it): []."""
1180 | +    pks = ([res.get("package") or {}] if res.get("pin") else []) + \
1181 | +        ([(res.get("spotlight") or {}).get("package") or {}] if res.get("spotlight_pin") else [])
1182 | +    return [R._norm(s.get("text") or "")[10:70] for pk in pks for s in pk.get("segments") or [] if isinstance(s, dict)]
1183 | +
1184 | +
1185 | +def compare_lines(lines, texts=()):
1186 | +    """-> rows: one per (shadow line, unit): {type, unit, heimdall, grok, compare, on_pin, deciding, shadow}."""
1187 | +    rows, skipped = [], []
1188 | +    for x in lines:
1189 | +        k = R.kind({"role": x.get("role"), "prompt": x.get("prompt") or ""})
1190 | +        sh = x.get("shadow") or {}
1191 | +        if k is None or k not in R.DECIDING or "text" not in sh:
1192 | +            skipped.append({"role": x.get("role"), "type": k, "why": sh.get("error") or "no decision rule"})
1193 | +            continue
1194 | +        pr = x.get("prompt") or ""
1195 | +        on_pin = bool(texts) and any(t and t in R._norm(pr) for t in texts)
1196 | +        try:
1197 | +            h = R.decide(k, (x.get("deciding") or {}).get("text"), pr)
1198 | +        except (ValueError, TypeError, KeyError) as e:
1199 | +            skipped.append({"role": x.get("role"), "type": k, "why": f"Heimdall's answer unreadable: {e}"})
1200 | +            continue
1201 | +        try:
1202 | +            g = R.decide(k, sh["text"], pr)
1203 | +        except (ValueError, TypeError, KeyError) as e:
1204 | +            g = None
1205 | +            rows.append({"type": k, "unit": "*", "heimdall": "answered", "grok": f"out of contract: {e}"[:120],
1206 | +                         "compare": "grok no verdict", "on_pin": on_pin,
1207 | +                         "deciding": (x.get("deciding") or {}).get("backend"), "shadow": sh.get("backend")})
1208 | +        if g is None:
1209 | +            continue
1210 | +        for u, hv in h.items():
1211 | +            gv = g.get(u)
1212 | +            rows.append({"type": k, "unit": u, "heimdall": hv, "grok": gv, "compare": R.compare(k, gv, hv),
1213 | +                         "on_pin": on_pin, "deciding": (x.get("deciding") or {}).get("backend"),
1214 | +                         "shadow": sh.get("backend")})
1215 | +    return rows, skipped
1216 | +
1217 | +
1218 | +def report(out_dir, res, missing=0, path=STATE, update_streak=True):
1219 | +    """SHADOW86.md for one build, and (update_streak) the pins' streak updated when it sealed one. -> a summary."""
1220 | +    lines = []
1221 | +    p = os.path.join(out_dir, "SHADOW86.jsonl")
1222 | +    if os.path.exists(p):
1223 | +        with open(p) as f:
1224 | +            for ln in f:
1225 | +                try:
1226 | +                    lines.append(json.loads(ln))
1227 | +                except ValueError:
1228 | +                    pass
1229 | +    texts = pin_texts(res)
1230 | +    rows, skipped = compare_lines(lines, texts)
1231 | +    diff = [r for r in rows if r["compare"] != "agree"]
1232 | +    pin_diff = [r for r in diff if r["on_pin"]]
1233 | +    on_pin = [r for r in rows if r["on_pin"]]
1234 | +    #   "grok no verdict" on a pin's decision counts as a stop: a pin is said to seal under Grok only when Grok's own
1235 | +    #   answer passed every one of its decisions (fail closed, qwen 0108 C1). With missing shadows and no compared
1236 | +    #   decision on the pin, nothing was verified: None, never True (audit 0108 C1, glm)
1237 | +    would_seal = None if not texts or (missing and not on_pin) else \
1238 | +        not any(r["compare"] in ("looser", "grok no verdict") for r in pin_diff)
1239 | +    usd = sum(float((x.get("shadow") or {}).get("usd_reported") or 0) for x in lines
1240 | +              if not (x.get("shadow") or {}).get("cached"))
1241 | +    summ = {"verdicts": len(lines), "compared_units": len(rows), "differ": len(diff), "on_pin_differ": len(pin_diff),
1242 | +            "not_compared": len(skipped), "missing": int(missing), "shadow_usd_reported": round(usd, 4),
1243 | +            "pin": bool(texts), "would_seal_under_grok": would_seal}
1244 | +    summ["summary"] = (f"{len(lines)} verdicts shadowed, {len(rows)} decisions compared, {len(diff)} differ "
1245 | +                       f"({len(pin_diff)} on the pin's clips); {len(skipped)} not compared; {int(missing)} still "
1246 | +                       f"running; shadow cost ${usd:.4f} reported" +
1247 | +                       ("" if would_seal is None else f"; the pin WOULD {'' if would_seal else 'NOT '}have sealed "
1248 | +                                                      f"under Grok"))
1249 | +    out = ["# Ruling 86: the shadow's side-by-side (Heimdall decided; Grok asked the same prompts)", "",
1250 | +           f"Build {os.path.basename(out_dir)}, written {time.strftime('%Y-%m-%d %H:%M %Z')}. {summ['summary']}.", "",
1251 | +           "Heimdall stricter: Heimdall failed what Grok passed. Heimdall looser: Heimdall passed what Grok failed "
1252 | +           "(on the pin's clips, Grok would have stopped it).", "",
1253 | +           "| type | unit | Heimdall | Grok | compare | on the pin | Heimdall model |", "|---|---|---|---|---|---|---|"]
1254 | +    for r in diff:
1255 | +        out.append(f"| {r['type']} | {r['unit']} | {r['heimdall']} | {r['grok']} | {r['compare']} | "
1256 | +                   f"{'yes' if r['on_pin'] else ''} | {r['deciding']} |")
1257 | +    if skipped:
1258 | +        out += ["", "## Not compared", ""] + [f"- {s['role']} ({s['type']}): {s['why']}" for s in skipped]
1259 | +    with open(os.path.join(out_dir, "SHADOW86.md"), "w") as f:
1260 | +        f.write("\n".join(out) + "\n")
1261 | +    if texts and update_streak:                  # a sealed pin: the streak moves (once, by the build itself)
1262 | +        st = _load(path)
1263 | +        changed = bool(pin_diff) or bool(missing)
1264 | +        st["pins"].append({"build": os.path.basename(out_dir), "decision_changing": len(pin_diff),
1265 | +                           "missing": int(missing), "would_seal_under_grok": would_seal,
1266 | +                           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
1267 | +        st["clean_streak"] = 0 if changed else int(st.get("clean_streak") or 0) + 1
1268 | +        tmp = f"{path}.{os.getpid()}.tmp"
1269 | +        with open(tmp, "w") as f:
1270 | +            json.dump(st, f, indent=1)
1271 | +        os.replace(tmp, path)
1272 | +        summ["clean_streak"] = st["clean_streak"]
1273 | +    return summ
1274 | +
1275 | +
1276 | +def main():
1277 | +    d = sys.argv[1]
1278 | +    with open(os.path.join(d, "package.json")) as f:
1279 | +        res = json.load(f)
1280 | +    print(json.dumps(report(d, res, update_streak=False), indent=1))     # a re-read never moves the streak
1281 | +
1282 | +
1283 | +if __name__ == "__main__":
1284 | +    main()
1285 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
1286 | index 71cc033..c0a2d96 100644
1287 | --- a/tests/package/test_gates.py
1288 | +++ b/tests/package/test_gates.py
1289 | @@ -22,7 +22,7 @@ class Canned:
1290 |          self.answers, self.calls, self.rejected = {k: list(v) for k, v in answers.items()}, [], []
1291 |  
1292 |      def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
1293 | -             avoid_family=None, deadline_s=None):
1294 | +             avoid_family=None, deadline_s=None, kind=None):
1295 |          self.calls.append((role, avoid_vendor, avoid_family))
1296 |          q = self.answers.get(role)
1297 |          if not q:
1298 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1299 | index 0497719..af3a02d 100644
1300 | --- a/tests/package/test_medley.py
1301 | +++ b/tests/package/test_medley.py
1302 | @@ -564,7 +564,8 @@ class Rig:
1303 |          self.write_avoid = []
1304 |  
1305 |      def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
1306 | -                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None):
1307 | +                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None, kind=None,
1308 | +                  failover=None):
1309 |          self.screen_deadlines.append(deadline_s)           # ruling 82: which calls are bounded
1310 |          """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
1311 |          (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
1312 | @@ -1177,7 +1178,7 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
1313 |          import context_integrity as CI
1314 |          from test_gates import a_item
1315 |  
1316 | -        def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False):
1317 | +        def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False, kind=None):
1318 |              calls.append((sorted(contexts), seed))
1319 |              if set(contexts) & set(fail):
1320 |                  raise RuntimeError("the batch reply was out of contract")
1321 | @@ -1293,14 +1294,35 @@ class TestRuling59HookFirst(unittest.TestCase):
1322 |          self.assertIn('CANDIDATE id="b"', prompts[0])
1323 |          self.assertIn("Judge each one ALONE", prompts[0])
1324 |  
1325 | -    def test_a_reply_out_of_contract_is_asked_once_more_then_nothing_is_rated(self):
1326 | +    def chained(self, *replies):
1327 | +        """A canned chain: each call is answered by the next model (fake:1, fake:2, ...), and a model the caller
1328 | +        skips (avoid_model) is never asked."""
1329 | +        c = self.canned(*replies)
1330 | +        call, n = c.call, [0]
1331 | +
1332 | +        def nxt(role, prompt, *a, avoid_model=None, **k):
1333 | +            r = call(role, prompt, *a, **k)
1334 | +            n[0] += 1
1335 | +            name = f"fake:{n[0]}"
1336 | +            assert name not in (avoid_model or ()), "a skipped model was asked"
1337 | +            c.asked_skip = getattr(c, "asked_skip", []) + [sorted(avoid_model or ())]
1338 | +            import providers as P
1339 | +            return P.Reply(r.text, name, "fake")
1340 | +        c.call = nxt
1341 | +        return c
1342 | +
1343 | +    def test_a_reply_out_of_contract_moves_on_to_the_next_model_then_nothing_is_rated(self):
1344 | +        """The 20:33 order (ruling 82's chain on every verdict): an answer out of contract moves on to the NEXT model
1345 | +        (it was one re-ask of the same model); the chain spent is no verdict (law L-m)."""
1346 |          ms = [pm("a", "A", 12.0)]
1347 |          ok = {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}
1348 | -        c = self.canned({"hooks": {"a": {"scroll": 9, "alone": 4, "setup": 4, "why": "w"}}}, ok)
1349 | +        c = self.chained({"hooks": {"a": {"scroll": 9, "alone": 4, "setup": 4, "why": "w"}}}, ok)
1350 |          got, err = PK.hook_ratings(c, ms, ctx(), set(), set())
1351 | -        self.assertEqual((err, got["a"]["rating"], len(c.calls), len(c.rejected)), (None, 4, 2, 1))
1352 | +        self.assertEqual((err, got["a"]["rating"], got["a"]["backend"], len(c.calls), c.rejected),
1353 | +                         (None, 4, "fake:2", 2, ["fake:1"]))
1354 | +        self.assertEqual(c.asked_skip, [[], ["fake:1"]])                   # the second ask skips the first model
1355 |          for bad in ({"hooks": {}}, {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4}}}, {"x": 1}, "no json"):
1356 | -            got, err = PK.hook_ratings(self.canned(bad, bad), ms, ctx(), set(), set())
1357 | +            got, err = PK.hook_ratings(self.chained(bad, bad), ms, ctx(), set(), set())
1358 |              self.assertEqual(got, {})
1359 |              self.assertIn("Error", err)
1360 |          got, err = PK.hook_ratings(self.canned(), ms, ctx(), set(), set())   # unavailable: no verdict (law L-m)
1361 | @@ -2482,6 +2504,51 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
1362 |          self.assertEqual(rig.screen_deadlines, [None, 120.0, 120.0, 120.0, 120.0])   # audit 2005 C1: the first screen
1363 |          #   unbounded as before; the second screen's two chunks and both off-writer re-screens at ruling 82's 120 s
1364 |  
1365 | +    def test_ruling_85_the_first_screen_is_bounded_under_heimdall_first(self):
1366 | +        """RULING 85: under heimdall_first the FIRST step-A verdict is a Heimdall family's, so it gets ruling 82's
1367 | +        bounds too (2 clips a call, 120 s); under today's routing it stays unbounded (Grok's), as before."""
1368 | +        batches = []
1369 | +        for routing in ("today", "heimdall_first"):
1370 | +            rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
1371 | +                      angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
1372 | +            rig.router.routing = routing
1373 | +            pre = rig.prescreen
1374 | +
1375 | +            def spy(*a, batch=PK.PRESCREEN_BATCH, **k):
1376 | +                batches.append((routing, batch))
1377 | +                return pre(*a, batch=batch, **k)
1378 | +            rig.prescreen = spy
1379 | +            rig.run()
1380 | +            self.assertEqual(rig.screen_deadlines[0], None if routing == "today" else PK.SECOND_VERDICT_DEADLINE_S)
1381 | +        self.assertEqual([b for r, b in batches if r == "heimdall_first"][0], PK.SECOND_VERDICT_BATCH)
1382 | +        self.assertEqual([b for r, b in batches if r == "today"][0], PK.PRESCREEN_BATCH)
1383 | +
1384 | +    def test_ruling_88_grok_confirms_in_its_own_batches_under_heimdall_first(self):
1385 | +        """RULING 88 (c): under heimdall_first the second step-A verdict is Grok confirming Heimdall's passes: Grok's own
1386 | +        batch (8) and no deadline, the move-on rule kept; under today it stays a Heimdall family's (2 clips, 120 s)."""
1387 | +        self.assertEqual(PK._second_bounds(type("R", (), {"routing": "today"})()),
1388 | +                         (PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S))
1389 | +        self.assertEqual(PK._second_bounds(type("R", (), {"routing": "heimdall_first"})()), (PK.PRESCREEN_BATCH, None))
1390 | +        got = []
1391 | +
1392 | +        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None, batch=None,
1393 | +                 deadline_s=None, kind=None, failover=None):
1394 | +            got.append((len(chunk), batch, deadline_s, kind, failover))
1395 | +            return {m["moment_id"]: {"backend": "xai:grok"} for m in chunk}, {m["moment_id"]: [] for m in chunk}, \
1396 | +                set(), set()
1397 | +        router = type("R", (), {"routing": "heimdall_first", "backends": {
1398 | +            "heimdall:qwen": type("B", (), {"vendor": "heimdall/qwen", "family": "qwen"})(),
1399 | +            "xai:grok": type("B", (), {"vendor": "xai", "family": "grok"})()}})()
1400 | +        ms = [dict(m, moment_id=f"m{i}") for i, m in enumerate(self.MS * 3)][:9]
1401 | +        saved = PK.prescreen
1402 | +        PK.prescreen = fake
1403 | +        try:
1404 | +            PK.second_screen(router, {m["moment_id"]: m for m in ms}, {m["moment_id"]: {"backend": "heimdall:qwen"}
1405 | +                                                                       for m in ms}, {}, ctx())
1406 | +        finally:
1407 | +            PK.prescreen = saved
1408 | +        self.assertEqual(sorted(got), [(1, 8, None, "step_a_second", True), (8, 8, None, "step_a_second", True)])
1409 | +
1410 |      def test_a_re_screen_that_gives_no_verdict_is_never_a_pass(self):
1411 |          """The old branch read the stale verdict back when the re-screen returned nothing for a clip (a fail-open,
1412 |          flagged with ORDER 06:22): no verdict off the writers keeps the clip out."""
1413 | @@ -2528,7 +2595,7 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
1414 |          seen, calls = [], []
1415 |  
1416 |          def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None, batch=None,
1417 | -                 deadline_s=None):
1418 | +                 deadline_s=None, kind=None, failover=None):
1419 |              seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
1420 |              calls.append((batch, deadline_s))
1421 |              name = "heimdall:deepseek"          # off xai for h and x; for z (first verdict heimdall) the SAME vendor
1422 | diff --git a/tests/package/test_shadow86.py b/tests/package/test_shadow86.py
1423 | new file mode 100644
1424 | index 0000000..928f7a7
1425 | --- /dev/null
1426 | +++ b/tests/package/test_shadow86.py
1427 | @@ -0,0 +1,88 @@
1428 | +#!/usr/bin/env python3
1429 | +"""RULING 86 (orchestrator 21:18 Nov 13): the shadow's side-by-side (tests/package/shadow86.py). Offline: a
1430 | +synthetic SHADOW86.jsonl in a temporary build directory and a temporary streak file."""
1431 | +import json
1432 | +import os
1433 | +import sys
1434 | +import tempfile
1435 | +import unittest
1436 | +
1437 | +HERE = os.path.dirname(os.path.abspath(__file__))
1438 | +sys.path.insert(0, HERE)
1439 | +import shadow86 as SH  # noqa: E402
1440 | +
1441 | +CLIP = "Bitcoin only dropped like five, six percent while tech stocks fell much further that week."
1442 | +PROMPT = ('Judge this moment. <before>...</before> <moment>"' + CLIP + '"</moment> Return {"risks": [], '
1443 | +          '"about_bitcoin": "yes|no|uncertain", "why": "..."}')
1444 | +
1445 | +
1446 | +def line(h, g, prompt=PROMPT):
1447 | +    return {"role": "exclusion_verdict", "prompt": prompt, "deciding": {"backend": "heimdall:z-ai/glm-5.3-flash",
1448 | +            "text": json.dumps(h)}, "shadow": {"backend": "xai:grok", "text": json.dumps(g), "usd_reported": 0.01}}
1449 | +
1450 | +
1451 | +KEEP = {"risks": [], "about_bitcoin": "yes", "why": "w"}
1452 | +EXCL = {"risks": ["imperative"], "about_bitcoin": "yes", "why": "w"}
1453 | +
1454 | +
1455 | +class TestShadow(unittest.TestCase):
1456 | +    def setUp(self):
1457 | +        self.d = tempfile.TemporaryDirectory()
1458 | +        self.state = os.path.join(self.d.name, "SHADOW86.json")
1459 | +
1460 | +    def tearDown(self):
1461 | +        self.d.cleanup()
1462 | +
1463 | +    def build(self, name, lines, pin):
1464 | +        b = os.path.join(self.d.name, name)
1465 | +        os.makedirs(b)
1466 | +        with open(os.path.join(b, "SHADOW86.jsonl"), "w") as f:
1467 | +            f.write("".join(json.dumps(x) + "\n" for x in lines))
1468 | +        res = {"package": {"segments": [{"text": CLIP}]}, "pin": {"path": "x"}} if pin else \
1469 | +            {"package": {"segments": [{"text": CLIP}]}}           # a package the pin stage refused is no pin
1470 | +        return b, res
1471 | +
1472 | +    def test_a_pin_grok_would_have_stopped_and_the_streak(self):
1473 | +        b, res = self.build("b1", [line(KEEP, KEEP), line(KEEP, EXCL)], pin=True)
1474 | +        s = SH.report(b, res, path=self.state)
1475 | +        self.assertEqual((s["differ"], s["on_pin_differ"], s["would_seal_under_grok"], s["clean_streak"]),
1476 | +                         (1, 1, False, 0))
1477 | +        md = open(os.path.join(b, "SHADOW86.md")).read()
1478 | +        self.assertIn("| exclusion | moment | True | False | looser | yes |", md)   # Heimdall passed what Grok failed
1479 | +        for i in range(3):                                                           # three clean pins in a row
1480 | +            b, res = self.build(f"c{i}", [line(KEEP, KEEP)], pin=True)
1481 | +            self.assertEqual(SH.report(b, res, path=self.state)["clean_streak"], i + 1)
1482 | +        self.assertEqual(SH.clean_streak(self.state), 3)
1483 | +        b, res = self.build("n", [line(KEEP, EXCL)], pin=False)                      # no pin: the streak stays
1484 | +        self.assertIsNone(SH.report(b, res, path=self.state)["would_seal_under_grok"])
1485 | +        self.assertEqual(SH.clean_streak(self.state), 3)
1486 | +
1487 | +    def test_unreadable_answers_and_missing_shadows_are_counted_never_clean(self):
1488 | +        bad = dict(line(KEEP, KEEP), shadow={"backend": "xai:grok", "error": "Unavailable: xAI down"})
1489 | +        b, res = self.build("b", [bad, line(KEEP, KEEP)], pin=True)
1490 | +        s = SH.report(b, res, missing=1, path=self.state)
1491 | +        self.assertEqual((s["not_compared"], s["missing"], s["clean_streak"]), (1, 1, 0))
1492 | +        self.assertEqual(SH.clean_streak(os.path.join(self.d.name, "none.json")), 0)
1493 | +
1494 | +    def test_missing_shadows_on_a_pin_never_say_it_would_seal(self):
1495 | +        """Audit 0108 C1 (glm): a sealed pin whose shadow answers are all missing was verified by nothing."""
1496 | +        b, res = self.build("b9", [{"role": "exclusion_verdict", "prompt": PROMPT,
1497 | +                                    "deciding": {"backend": "heimdall:z-ai/glm-5.3-flash", "text": json.dumps(KEEP)}}],
1498 | +                            pin=True)
1499 | +        out = SH.report(b, res, missing=1, path=self.state)
1500 | +        self.assertIsNone(out["would_seal_under_grok"])
1501 | +
1502 | +    def test_a_sealed_spotlight_is_a_pin_too(self):
1503 | +        """RULING 90: a spotlight pin is judged by the shadow like a medley pin (ruling 86's "the first pin sealed")."""
1504 | +        seg = [{"text": CLIP}]
1505 | +        self.assertEqual(SH.pin_texts({"pin": None, "spotlight_pin": {"story_id": "s"},
1506 | +                                       "spotlight": {"package": {"segments": seg}}}),
1507 | +                         SH.pin_texts({"pin": {"story_id": "m"}, "package": {"segments": seg}}))
1508 | +        self.assertEqual(len(SH.pin_texts({"pin": {"story_id": "m"}, "package": {"segments": seg},
1509 | +                                           "spotlight_pin": {"story_id": "s"},
1510 | +                                           "spotlight": {"package": {"segments": seg}}})), 2)
1511 | +        self.assertEqual(SH.pin_texts({"spotlight": {"package": {"segments": seg}}}), [])   # not sealed: no pin
1512 | +
1513 | +
1514 | +if __name__ == "__main__":
1515 | +    unittest.main()
1516 | 
```

---

You are auditing PACKAGE B of a change on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins). It
is the verdict call sites, the shadow's side-by-side report and the replay driver. Package A (the router, the
Heimdall health state, the provider config, the build driver) is audited separately. Only state what you can verify
from the diff; if uncertain, say so; do not guess.

Background (static):
- providers.Router.call(role, ...) tries the role's chain of back-ends. It moves on when a back-end is down, refuses,
  misses its deadline or answers empty. The chain spent raises ProviderError (no verdict, never a pass). Before this
  change, a verdict whose answer was OUT OF CONTRACT (unreadable JSON, wrong keys) was rejected (its recording
  dropped) and gave no verdict. The hook ratings re-asked the SAME model once with another seed.
- providers.call_parsed(router, role, prompt, parse, ...) (package A) calls the chain, and on an answer out of
  contract (parse raises ValueError / TypeError / KeyError) rejects it and asks the NEXT model, each model once.
- Under the new routing "heimdall_first" (package A), Heimdall's families decide every verdict and Grok is last.
  Grok's answers are then asked "in shadow" and recorded, never deciding.

The orders (verbatim excerpts):
- 20:33 Nov 13: "Ruling 82's chain (deepseek -> glm-5.3-flash -> qwen3.8-27b, 120 s a call, an out-of-contract answer
  moves on, an outage is never a verdict) applies to every step that today has one Heimdall model as its only route
  when xAI is the writer or is down: the fidelity verdict, coherence / clips-alone / hook ratings, step B, the speaker
  and exclusion verdicts."
- RULING 85.1 (21:15): "REPLAY, no new Grok spend: every recorded Grok verdict since the first ledger build (prompt +
  answer are in your records ...) is re-asked, same prompt, of Heimdall's model families: deepseek-v4.1-flash,
  z-ai/glm-5.3-flash, qwen3.8-27b ... Report per verdict type and per model: agreement with Grok on the DECISION
  (pass / fail, flagged join, rating at or above the bar), the disagreements split into 'Heimdall stricter' and
  'Heimdall looser', median seconds, timeouts, cost. The delivered videos are the anchor: every verdict that let
  0c68b589, 41f29b1f and 37c5b5f5's clips through must still pass, and the ... REFERENT_OUTSIDE refusals must still be
  refused."
- RULING 86 (21:18): the shadow. "every decision where they differ, which was stricter, and whether the pin would have
  sealed under Grok. ... After three pins with no decision-changing difference, the shadow stops."
- RULING 85 (21:15): the first step-A verdict becomes a Heimdall family's under heimdall_first.

- RULING 88 (22:15): "(c) STEP A stays two families with Grok as one of them, but the ORDER changes: the Heimdall
  verdict is asked FIRST; a clip Heimdall refuses is refused and Grok is never asked; only a clip Heimdall passes goes
  to Grok to confirm." The types get their own lists: each call names its kind.

The change (package B):
1. Every verdict call site now uses providers.call_parsed, so an answer out of contract moves on to the next model:
   - vo_fidelity.check (fidelity);
   - moments exclusion (exclusion);
   - speakers (speaker);
   - package.hook_ratings (the hook ratings; the same-model seed re-ask is gone);
   - package.coherence;
   - package.medley (clips-alone);
   - context_integrity: step B twice (step B's relations check is now inside its parser, so a bad relation also moves
     on) and step C.
   Each parse function is the old inline contract check, moved unchanged. The except clauses keep their old outcomes:
   no verdict; never a pass.
2. RULING 88: every call names its kind (prescreen kind="step_a_first" for the first screen, "step_a_second" for the
   second screen and the off-writer re-screen; step C "step_c"; the hook ratings "hook"; clips-alone "clips_alone";
   coherence "coherence"). Under heimdall_first, package._second_bounds gives the second screen (Grok confirming)
   Grok's own batch (8) and no deadline, with the move-on rule kept (prescreen failover=True); under today it stays
   2 clips and 120 s.
3. package.build:
   - the writes avoid the other writers by GATEWAY (providers.gateway), so a Heimdall write may still fail over
     deepseek -> qwen when each Heimdall family is its own maker (heimdall_first);
   - under heimdall_first, the FIRST step-A screen runs SECOND_VERDICT_BATCH (2) clips per call with
     SECOND_VERDICT_DEADLINE_S (120 s): Heimdall needs a median 268 s on 8 clips.
4. tests/package/replay85.py (new): the replay.
   - Each recorded Grok answer is reduced to the pipeline's DECISION with the pipeline's parsers and bars (step A:
     context_integrity.a_failures; clips-alone and coherence: _line_ok, COHERENCE_MIN, LY_MAX_BRIDGES; hooks: the
     lowest of scroll / alone >= HOOK_MIN; exclusion; speaker name; step C and fidelity by stated proxies).
   - The same prompt is then asked of each Heimdall family (its own recordings; ruling 48's ledger; resumable), and
     the decisions compared (agree / stricter / looser / different).
   - Anchors are matched by the delivered pins' clip texts in a prompt.
   - The output is TABLE.md.
5. tests/package/shadow86.py (new): the side-by-side.
   - It reads a build's SHADOW86.jsonl with the replay's decide / compare and writes SHADOW86.md: the differences,
     which side was stricter, and whether the pin would have sealed under Grok (a decision on the pin's clips where
     Heimdall passed and Grok failed).
   - The streak in SHADOW86.json counts pins with no decision-changing difference. A pin with a missing shadow or an
     unreadable one is never clean. A re-read never moves the streak.
6. Tests:
   - test_medley: Grok confirms in its own batches under heimdall_first; the hook ratings move on to the next model; the first screen's bounds under each routing.
   - test_shadow86: a pin Grok would have stopped; the streak to 3; no pin leaves it; unreadable or missing shadows.

Check, against the diff:
- that every parse function is the old contract check, unchanged, and that no out-of-contract answer can become a
  verdict;
- that an outage is never a verdict and nothing is cached from a failed call;
- that the except clauses of every call site still catch what call_parsed can raise;
- that the replay's decision functions match the pipeline's own rules (and where they are proxies, that this is said);
- that the shadow report cannot call a pin clean when a shadow is missing or unreadable;
- the "would have sealed under Grok" logic.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

ADDENDUM (00:4x ET Nov 14): this change is now rebased onto the branch's newer HEAD 07321410. That HEAD adds the
SPOTLIGHT pin kind (rulings 90-92: pipeline/spotlight.py, package_pin's spotlight contract) and RULING 93 (DEC-12d per
clip: visual_pin's burned-in text question). Both were audited separately (2322, 0003). The merge points, to check:
- package.first_bounds(router): one helper for step A's FIRST screen. Under heimdall_first it is 2 clips and 120 s a
  call; under today, {}. The medley build and spotlight.build both call prescreen(..., kind="step_a_first",
  **first_bounds(router)).
- proof_ledger.py keeps both module constants (SPOTLIGHTS for ruling 90; STATE_MD for ruling 87). The spotlight runs
  on the same Router after the medley search, so its calls are shadowed (ruling 86) and noted for Plan B (ruling 87)
  like the medley's.
- shadow86.pin_texts covers a sealed spotlight pin (res["spotlight_pin"] with res["spotlight"]["package"]) as well as
  the medley pin, so ruling 86's "first pin sealed under Heimdall-first" holds whatever the pin's kind.
- The spotlight's value verdict (ruling 91) stays ONE call with no move-on ("one write, one verdict; anything short of
  a clear yes means no line"); its layout verdict (ruling 92) is one vision call, and failing it means not measured.

ADDENDUM 2 (01:1x ET Nov 14):
- The change is now rebased onto HEAD 2f081cba, which adds RULINGS 94 and 95 (audited separately, 0041):
  - stand_alone's hook opener rule (first/second-person pronouns free, third-person ones need the scorer);
  - package._can_open's re-check with the verdict and its spotlight-only deferral;
  - hook trim variants;
  - spotlight.next_attempt.
  The merge was mechanical (git merge-file, no conflict). The one hand-applied line is spotlight.build's step-A call:
  kind="step_a_first" with package.first_bounds(router), as the medley's.
- THE REPLAY IS COMPLETE (884 rows; tests/package/proof/replay85/TABLE.md). Ruling 88 (b) was conditional on the
  full table:
  - it holds for the HOOK rating: qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %. model_providers.json's
    heimdall_first "coherence_verdict:hook" is now qwen -> glm -> deepseek -> Grok (Grok was first);
  - it does not hold for STEP C: glm 97 %, deepseek 96 %, and qwen's 98 % is barred by (e). Step C stays Grok first.
  routing.ruling_88's note records both.


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
