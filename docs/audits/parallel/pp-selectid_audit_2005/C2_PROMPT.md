# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2005
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 178 s finish=stop usage in 11316 / out 4706 usd~0.105 (upper-bound price)

# Audit: pp-selectid — RULING 82 second-vendor step-A failover chain

Scope note: I can only verify what the diff shows. `providers.Router.call`, `proof_ly.chains`, the router's `avoid_model` / `deadline_s` handling, and `providers.ProviderError` are referenced but not shown; where the diff's correctness depends on them I flag it as unverifiable rather than guess.

## P0 findings

None. The diff is internally consistent with the ruling; I found no defect that would break the build or a law.

## P1 findings

**P1-1 — `avoid_model` skip-set is keyed by `ra.backend`, but the router's skip semantics are unverified; a wrong key silently disables failover.**
`context_integrity.py:48` (`if not failover or ra.backend in skip: raise`) and `:50` (`skip.add(ra.backend)`) assume `ra.backend` is exactly the string the router matches against `avoid_model`. The test at `test_medley.py:263-269` builds the chain as `["xai:grok", "heimdall:deepseek", "heimdall:glm", "heimdall:qwen"]` while the production chain in `model_providers.json` is `heimdall:z-ai/glm-5.3-flash` / `heimdall:qwen/qwen3.8-27b` — the Fakes' back-end ids (`"heimdall:glm"`, `"heimdall:qwen"`) differ from the real keys. If the router's `avoid_model` membership test is exact-string against the chain's back-end ids, the test passes (Fake ids are self-consistent) but proves nothing about the production keys; if the router normalises (e.g. strips the vendor prefix), the production loop could re-ask the same model until the chain is spent on the first model. Concrete scenario: deepseek answers out of contract → `skip = {"heimdall:deepseek/deepseek-v4.1-flash"}` → if the router compares `avoid_model` against a *model* field rather than the back-end key, the next call may pick deepseek again, `ra.backend in skip` is True, and it raises after one attempt — failover silently dead, exactly the 19:23 failure mode, but now intermittent. Not provable from the diff; needs the router's `avoid_model` contract or a test with the real back-end ids.

**P1-2 — `failover` is coupled to `deadline_s is not None`, so the off-writer re-screen's failover depends on the same flag, and the coupling is implicit.**
`package.py:120` (`failover=deadline_s is not None`) means any future caller that passes `deadline_s` without wanting failover (or vice versa) gets the other behaviour silently. The ruling specifies both together for the second-vendor path, so today it's correct; but `prescreen`'s signature now has `deadline_s` as the *only* switch, and `second_screen` (`package.py:134-137`) and the stale re-screen (`package.py:144-147`) both rely on it. If someone later calls `prescreen(deadline_s=120)` from the *first-verdict* path, the first verdict's path silently gains failover, violating "the first verdict's path is unchanged". Low likelihood today (the first-verdict call sites shown pass neither), but the invariant is enforced only by convention, not by code or test. A test asserting the first-verdict call passes `deadline_s=None, failover=False` would close it.

**P1-3 — the "all three failing" test does not prove the *chain* is spent; it proves one round-trip through the skip-set.**
`test_medley.py:274-276`: after `qw.answer = "still not JSON"`, the expected failure is `ProviderError`. But trace the loop: xAI answers good (not consulted — writer's vendor avoided), deepseek fails 503 (router moves on, not via `skip`), glm answers `"not one JSON object"` → added to `skip`, qwen now answers `"still not JSON"` → added to `skip`. Next iteration: the router's chain still contains xAI (not avoided here — `writer_family={"grok"}` avoids the *family* grok, and the Fake xAI's family is "grok", so xAI *is* avoided) — wait, checking: `CI.step_a(r, CTX, {"xai"}, writer_family={"grok"}, ...)` — the test passes `{"xai"}` as `writer_vendor` and `{"grok"}` as `writer_family`, so xAI is avoided by both. Then the only untried back-ends are... none: deepseek (down, router-level), glm and qwen in `skip`. So the router raises ProviderError. But this exercises the *router's* chain-spent path, not the loop's: the loop's own termination when `ra.backend in skip` (line 48) is never hit, because the router raises before returning. The loop-termination branch (`if not failover or ra.backend in skip: raise`) is only exercised by the *non-failover* test at line 272-273, where `failover=False` short-circuits. So the `ra.backend in skip` termination condition — the one that guarantees the while-loop ends — appears untested. If the router, when given `avoid_model` covering the whole remaining chain, *loops internally* or returns a replay instead of raising, `step_a`'s while-loop could spin. Depends on router behaviour not shown.

**P1-4 — cost/ledger: abandoned-call accounting is stated, not shown, and the 120 s deadline changes what "spent" means.**
The known-cost note says ruling 48 books an abandoned cal

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 43 s finish=stop usage in 11306 / out 582 usd~0.071 (upper-bound price)

**P0: none verifiable from diff**  
**P1: none verifiable from diff**  
**P2: pipeline/context_integrity.py:48 (post-`router.reject(ra)`)**  
Concrete scenario visible in diff: when `failover=True`, `_strict` (or label check) raises `ValueError`/`TypeError`, `ra.backend` has already been seen in `skip`, the `if not failover or ra.backend in skip` short-circuits to `raise` (no infinite loop, no verdict produced). Matches "failover loop terminates" and "no answer out of contract can ever be a verdict".  

**P2: pipeline/package.py:136 and tests/package/test_medley.py:234**  
Concrete scenario visible in diff: every `second_screen` job and every off-writer re-screen in `build` now passes `batch=SECOND_VERDICT_BATCH` (==2) + `deadline_s=SECOND_VERDICT_DEADLINE_S` (==120.0) all the way to `prescreen` → `step_a(failover=True)`. First-verdict calls (no `deadline_s`) remain at defaults (`failover=False`, no deadline). Test expectations updated for chunking and call counts.  

**P2: pipeline/context_integrity.py:35-50 + test_medley.py:268**  
Concrete scenario visible in diff: `while True` + `skip` set + `avoid_model` only activates on parse failure when `failover=True`; successful parse breaks loop and all items receive that `ra.backend`. Without `failover` (first-verdict path) any bad parse still raises exactly as before. Test `test_ruling_82_the_second_vendor_step_a_fails_over_down_the_chain` verifies: deepseek (503) → glm (non-JSON) → qwen (good) yields qwen verdict; all three failing yields `ProviderError` (no verdict, no cache).  

**P2: pipeline/model_providers.json:82 + tests/package/test_ledger_build.py:163**  
Concrete scenario visible in diff: `context_verdict` chain becomes xai → deepseek → glm-5.3-flash → qwen (frozen legs removed). `second_screen` groups by first-verdict `(vendor, family)` and calls `prescreen(avoid=that)`, so second verdict cannot be xAI; re-screen avoids writer's family for quoted clips. `glm` entry declares `vendor=heimdall`, `family=glm` (distinct from deepseek). No diff shows any path caching a failed/out-of-contract reply.  

All five audit points listed in the query are satisfied by code+tests present in the diff. No violations of L-j, L-l, M12 or RULING 82 observable.  

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 91 s finish=stop usage in 12448 / out 3015 usd~0.083 (upper-bound price)

# Audit: pp-selectid-2005 (RULING 82)

## P0 Findings

**1. `pipeline/context_integrity.py` (diff lines 34–50): Failover loop can raise `ValueError` instead of `ProviderError` when the chain is exhausted.**

The loop logic is:
```python
while True:
    ra = router.call(...)
    try:
        A = _strict(...)
        ...
        break
    except (ValueError, TypeError):
        if hasattr(router, "reject"):
            router.reject(ra)
        if not failover or ra.backend in skip:
            raise          # <-- raises ValueError, not ProviderError
        skip.add(ra.backend)
```

Scenario: The router's chain for `context_verdict` (after frozen legs removed) is `[xai, deepseek, glm, qwen]`. The call is made with `avoid_vendor={"xai"}` (the first verdict's vendor). The router skips xAI and tries deepseek. Deepseek is down → router moves to glm. GLM is down → router moves to qwen. Qwen is down → **router raises `ProviderError`** (chain spent). This is correct.

But consider: deepseek is *up* but returns an out-of-contract answer. `skip = {deepseek}`. Next iteration: router is called with `avoid_model={deepseek}`. Router skips xAI (vendor), skips deepseek (avoid_model), tries glm. GLM is down → router moves to qwen. Qwen is down → **router raises `ProviderError`**. Correct.

Now the critical case: deepseek is up, returns out-of-contract. `skip = {deepseek}`. Next: router called with `avoid_model={deepseek}`. Router skips xAI, skips deepseek, tries glm. **GLM is up but also returns out-of-contract.** `skip = {deepseek, glm}`. Next: router called with `avoid_model={deepseek, glm}`. Router skips xAI, skips deepseek, skips glm, tries qwen. **Qwen is up but also returns out-of-contract.** `skip = {deepseek, glm, qwen}`. Next: router called with `avoid_model={deepseek, glm, qwen}`. Router skips xAI, skips all three Heimdall models. **Chain is spent → router raises `ProviderError`.** Correct.

Wait — re-examine. The `raise` on line 49 fires when `ra.backend in skip`. This means the router *returned* a response from a model already in `skip`. Can that happen? The router is told `avoid_model=skip`, so it should never return a response from a model in `skip`. If the router correctly honors `avoid_model`, then `ra.backend in skip` is never true, and the loop only exits via `break` (success) or the router raising `ProviderError` (chain spent). The `raise` on line 49 is a defensive guard against a router bug.

**However**, there is a subtle issue: if the router has a bug or the `avoid_model` kwarg is not properly forwarded (e.g., the router's `call` signature doesn't accept `avoid_model` and silently ignores it), the loop could cycle. But the diff shows `**({"avoid_model": set(skip)} if skip else {})` is passed to `router.call`. If the router doesn't support `avoid_model`, this would raise `TypeError` at the call site, not loop. So the loop terminates.

**Verdict: Not a P0.** The loop terminates correctly under all scenarios where the router honors its contract. The defensive `raise` is unreachable in correct operation.

**2. `pipeline/context_integrity.py` (diff line 48): The `raise` on line 48 re-raises the original `ValueError`/`TypeError`, not a `ProviderError`.**

If the defensive guard on line 48–49 ever fires (router returns a model already in `skip`), the exception raised is the original `ValueError` from `_strict`, not `ProviderError`. The docstring says "then ProviderError: no verdict." This is a contract mismatch, but as analyzed above, the guard is unreachable in correct operation. **Downgrade to P2.**

## P1 Findings

**3. `pipeline/package.py` (diff lines 134–137): `second_screen` passes `deadline_s=SECOND_VERDICT_DEADLINE_S` but does NOT pass `failover=True` explicitly.**

```python
return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log,
                 cache=cache, batch=SECOND_VERDICT_BATCH,
                 deadline_s=SECOND_VERDICT_DEADLINE_S)
```

In `prescreen` (diff lines 117–120):
```python
return CI.step_a(router, ..., deadline_s=deadline_s,
                 failover=deadline_s is not None), None
```

Since `deadline_s=120.0` (not `None`), `failover=True` is correctly derived. **This is correct.** No finding.

**4. `pipeline/package.py` (diff lines 144–147): The off-writer re-screen in `build()` passes `batch` and `deadline_s` but does NOT pass `failover`.**

```python
got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
                                 batch=SECOND_VERDICT_BATCH,
                                 deadline_s=SECOND_VERDICT_DEADLINE_S,
                                 n=len(stale), store=None, cache=step_a_cache)
```

Again, `prescreen` derives `failover=deadline_s is not None` → `True`. **Correct.** No finding.

**5. `pipeline/package.py` (diff lines 117–120): The FIRST screen (initial prescreen) does NOT

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 2005 (ruling 82: the second-vendor step A's failover chain): cycle 1 consensus

- **grok:** "SHIP: yes", no P0 or P1.
- **qwen:** "SHIP: yes with conditions". Its P0s were withdrawn in its own text after tracing; two conditions.
- **glm:** "SHIP: yes with conditions". No P0; three conditions.

## Implemented

- **qwen #9:** the defensive branch (the router returns a model already skipped) now raises
  providers.ProviderError, the documented "no verdict", not the original ValueError. A caller catching ProviderError
  never meets another type from the failover path. Without failover (the first verdict's path), a bad answer still
  raises ValueError, as before.
- **glm (3):** a test pins that the off-writer re-screen receives the deadline. In the Rig, the step-A calls carry
  [None (the first screen, unchanged), 120, 120 (the second screen's two chunks of 2), 120, 120 (both off-writer
  re-screens)].

## Confirmed from the code (conditions that ask for a check)

- **glm (1) / qwen (2): avoid_model is keyed exactly as ra.backend.** providers.Router.call walks the role's chain
  by name, and `_skip(name, ...)` refuses `name in am`. The Reply it returns carries that same `name` as `.backend`
  (`Reply(text, name, ...)`), so the skip set holds exactly the names the router compares. The failover test runs
  the REAL Router (tests/providers/test_providers.router) with fake back-ends: glm is skipped on the second call,
  and qwen answers.
- **glm (2): a late answer to an abandoned call is never cached.** On DeadlineExceeded, Router.call books the upper
  bound, logs `missed_deadline` to the Heimdall evidence file (item 55), and `continue`s. `_record` (the reply cache)
  runs only after an answer returned inside the deadline and was non-empty. prescreen stores a verdict only after
  step_a parsed it (an exception in a chunk is STEP_A_UNAVAILABLE, never stored). Unchanged code.
- **glm P1-5:** the first verdict's step A stays unbounded. That is the ruling's scope ("the second-vendor step A"),
  and the comment says so.

## Recorded (no change)

- **glm P1-3:** the all-three test spends the chain through router-level and contract failures together. Each is
  also exercised alone (deepseek down; glm out of contract).
- **qwen #10:** the test helper P_ProviderError imports at call time. Style.
- **Cost:** an abandoned call books its upper bound (about $0.24) on ruling 48's ledger, by the existing rule.
  Batches of 2 are what keep calls inside 120 s.

## Suites

All 15 OK (medley 160, ledger_build 37, ...).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_2005/C2_STEP.diff (300 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index 487cacb..69300ea 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -318,9 +318,11 @@ def check(router, package, sources, writer_vendor, seed=7):
   6 |      return check_contexts(router, package, contexts_from_sources(package, sources), writer_vendor, seed)
   7 |  
   8 |  
   9 | -def step_a(router, contexts, writer_vendor, seed=7, writer_family=None):
  10 | +def step_a(router, contexts, writer_vendor, seed=7, writer_family=None, deadline_s=None, failover=False):
  11 |      """Step A alone (context only, the package hidden): {label: item} for exactly the given labels, and the back-end.
  12 | -    Raises ValueError / ProviderError when it cannot be had or read."""
  13 | +    Raises ValueError / ProviderError when it cannot be had or read. RULING 82 (20:02 Nov 13): deadline_s bounds each
  14 | +    call (the router moves to the next model at it and logs the miss, item 55); failover=True also moves on when a
  15 | +    model's answer is out of contract, each model once, until the chain is spent (then ProviderError: no verdict)."""
  16 |      labels = list(contexts)
  17 |      for lb in labels:
  18 |          if len(contexts[lb]["text"]) > EXCERPT_MAX:
  19 | @@ -330,17 +332,26 @@ def step_a(router, contexts, writer_vendor, seed=7, writer_family=None):
  20 |            f'"{_q(contexts[lb].get("title") or "", 160)}" published="{contexts[lb].get("published") or "unknown"}" '
  21 |            f'show_date="{contexts[lb].get("show_date") or "unknown"}">{contexts[lb]["text"]}</excerpt>'
  22 |            for lb in labels]
  23 | -    ra = router.call("context_verdict", STEP_A.format(excerpts="\n".join(ex)), 4000, seed, avoid_vendor=writer_vendor,
  24 | -                     avoid_family=writer_family)
  25 | -    try:
  26 | -        A = _strict(ra.text, {"excerpts"}, {"excerpts": A_KEYS})
  27 | -        a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
  28 | -        if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
  29 | -            raise ValueError(f"step A must answer exactly the labels {labels}")
  30 | -    except (ValueError, TypeError):
  31 | -        if hasattr(router, "reject"):
  32 | -            router.reject(ra)
  33 | -        raise
  34 | +    prompt, skip = STEP_A.format(excerpts="\n".join(ex)), set()
  35 | +    while True:
  36 | +        ra = router.call("context_verdict", prompt, 4000, seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
  37 | +                         **({"avoid_model": set(skip)} if skip else {}),
  38 | +                         **({"deadline_s": deadline_s} if deadline_s else {}))
  39 | +        try:
  40 | +            A = _strict(ra.text, {"excerpts"}, {"excerpts": A_KEYS})
  41 | +            a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
  42 | +            if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
  43 | +                raise ValueError(f"step A must answer exactly the labels {labels}")
  44 | +            break
  45 | +        except (ValueError, TypeError) as e:
  46 | +            if hasattr(router, "reject"):
  47 | +                router.reject(ra)
  48 | +            if not failover:
  49 | +                raise
  50 | +            if ra.backend in skip:                       # audit 2005 C1: never a loop, and the documented error
  51 | +                import providers as P
  52 | +                raise P.ProviderError(f"context_verdict: {ra.backend} answered again though skipped: {e}") from e
  53 | +            skip.add(ra.backend)                         # ruling 82: the next model in the chain
  54 |      for lb in labels:
  55 |          a_by[lb] = dict(a_by[lb], backend=ra.backend, replayed=bool(getattr(ra, "replayed", False)),
  56 |                          speaker_verified=speaker_verified(a_by[lb], contexts[lb]["text"]))
  57 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
  58 | index 8ca333d..11238b1 100644
  59 | --- a/pipeline/model_providers.json
  60 | +++ b/pipeline/model_providers.json
  61 | @@ -143,6 +143,19 @@
  62 |     "family": "scribe",
  63 |     "price_usd_per_min": 0.012,
  64 |     "timeout_s": 300
  65 | +  },
  66 | +  "heimdall:z-ai/glm-5.3-flash": {
  67 | +   "vendor": "heimdall",
  68 | +   "model": "z-ai/glm-5.3-flash",
  69 | +   "price_usd_per_1m": [
  70 | +    3,
  71 | +    15
  72 | +   ],
  73 | +   "temperature": 0,
  74 | +   "min_out": 16000,
  75 | +   "family": "glm",
  76 | +   "base_url": "https://api-staging.heimdallm.com/api/v1",
  77 | +   "measured": "ruling 82 (orchestrator 20:02 Nov 13): pp-ingest measured it 24/24 on calibration (default reasoning)"
  78 |    }
  79 |   },
  80 |   "roles": {
  81 | @@ -179,9 +192,12 @@
  82 |      "xai:grok-4.20-0309-reasoning",
  83 |      "anthropic:claude-opus-5-5",
  84 |      "heimdall:deepseek/deepseek-v4.1-flash",
  85 | +    "heimdall:z-ai/glm-5.3-flash",
  86 | +    "heimdall:qwen/qwen3.8-27b",
  87 |      "local:gemma3:27b"
  88 |     ],
  89 | -   "what": "context_integrity.py step A (source context only) and step C (entailment); never the writer's vendor"
  90 | +   "what": "context_integrity.py step A (source context only) and step C (entailment); never the writer's vendor",
  91 | +   "ruling_82": "orchestrator 20:02 Nov 13: the second-vendor step A has a failover chain, deepseek -> glm-5.3-flash -> qwen3.8-27b, 120 s per call"
  92 |    },
  93 |    "viewer_takeaway": {
  94 |     "chain": [
  95 | diff --git a/pipeline/package.py b/pipeline/package.py
  96 | index 3f69be7..68384f1 100644
  97 | --- a/pipeline/package.py
  98 | +++ b/pipeline/package.py
  99 | @@ -72,6 +72,8 @@ PRESCREEN_N = None                 # RULING 58 (11:00 Nov 13): EVERY candidate i
 100 |                                     # miner's best first; a number keeps the old cap (the re-screens pass their own)
 101 |  PRESCREEN_BATCH = 8                # excerpts per step-A call
 102 |  PRESCREEN_WORKERS = 6              # ruling 58: the step-A batches run in parallel (about 19 batches at 72 h)
 103 | +SECOND_VERDICT_DEADLINE_S = 120.0  # RULING 82 (20:02 Nov 13): each second-vendor / off-writer step-A call; at it the next
 104 | +SECOND_VERDICT_BATCH = 2           # model (deepseek -> glm-5.3-flash -> qwen3.8-27b); small batches so one fits in it
 105 |  PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
 106 |  SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
 107 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
 108 | @@ -486,7 +488,7 @@ def src_of(x, sources):
 109 |  
 110 |  
 111 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 112 | -              store=None, log=print, cache=None):
 113 | +              store=None, log=print, cache=None, deadline_s=None):
 114 |      """Step A (context only, package-independent by law L-s): ({moment_id: A item}, {moment_id: [failing rules]},
 115 |      {vendor}, {family}). RULING 58 (11:00 Nov 13): n None (the default) screens EVERY usable moment, the miner's best
 116 |      first (rank_score); a number keeps the old cap (distinct channels first). Each moment is paid for ONCE: a verdict
 117 | @@ -538,7 +540,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 118 |      def screen(i, chunk):
 119 |          try:
 120 |              return CI.step_a(router, {m["moment_id"]: contexts[m["moment_id"]] for m in chunk}, writer_vendor,
 121 | -                             seed=7 + i * batch, writer_family=writer_family), None
 122 | +                             seed=7 + i * batch, writer_family=writer_family, deadline_s=deadline_s,
 123 | +                             failover=deadline_s is not None), None          # ruling 82: the chain, per call
 124 |          except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
 125 |              return None, e
 126 |      with ThreadPoolExecutor(max_workers=max(1, min(PRESCREEN_WORKERS, len(chunks)))) as ex:
 127 | @@ -581,12 +584,13 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 128 |      for mid, m in cleared.items():
 129 |          b = router.backends.get((a_by.get(mid) or {}).get("backend"))
 130 |          groups.setdefault((b.vendor, b.family) if b is not None else None, []).append(m)
 131 | -    jobs = [(k, g[i:i + PRESCREEN_BATCH]) for k, g in groups.items() if k is not None
 132 | -            for i in range(0, len(g), PRESCREEN_BATCH)]
 133 | +    jobs = [(k, g[i:i + SECOND_VERDICT_BATCH]) for k, g in groups.items() if k is not None
 134 | +            for i in range(0, len(g), SECOND_VERDICT_BATCH)]
 135 |      def one(k, chunk):                  # a chunk whose screen raises fails closed, never the build (audit 0640 C1)
 136 |          try:
 137 |              return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log,
 138 | -                             cache=cache)                    # ruling 58: a second verdict is paid for once too
 139 | +                             cache=cache, batch=SECOND_VERDICT_BATCH,    # ruling 58: a second verdict is paid once;
 140 | +                             deadline_s=SECOND_VERDICT_DEADLINE_S)       # ruling 82: the chain, 120 s a call
 141 |          except Exception as e:
 142 |              return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
 143 |                          for m in chunk}, set(), set()
 144 | @@ -2813,6 +2817,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 145 |                          router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
 146 |                      if stale:                                  # audit C2 K5: never judged by the writer's vendor
 147 |                          got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
 148 | +                                                         batch=SECOND_VERDICT_BATCH,      # ruling 82: off the writer,
 149 | +                                                         deadline_s=SECOND_VERDICT_DEADLINE_S,   # the chain, 120 s
 150 |                                                           n=len(stale), store=None, cache=step_a_cache)
 151 |                          bad = {}
 152 |                          for m in stale:
 153 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 154 | index b85c1f4..99f713c 100644
 155 | --- a/tests/package/test_ledger_build.py
 156 | +++ b/tests/package/test_ledger_build.py
 157 | @@ -762,6 +762,18 @@ class TestDriverRefuses(unittest.TestCase):
 158 |          self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
 159 |                           before)
 160 |  
 161 | +    def test_ruling_82_the_context_verdict_chain(self):
 162 | +        """RULING 82 (20:02 Nov 13): with the frozen legs out, step A's chain is xAI first, then the three Heimdall
 163 | +        models in the ruled order; glm-5.3-flash is a Heimdall back-end of its own family."""
 164 | +        sys.path.insert(0, HERE)
 165 | +        import proof_ly as PL
 166 | +        self.assertEqual(PL.chains()["context_verdict"], ["xai:grok-4.20-0309-reasoning",
 167 | +                                                          "heimdall:deepseek/deepseek-v4.1-flash",
 168 | +                                                          "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b"])
 169 | +        with open(os.path.join(REPO, "pipeline", "model_providers.json")) as f:
 170 | +            glm = json.load(f)["backends"]["heimdall:z-ai/glm-5.3-flash"]
 171 | +        self.assertEqual((glm["vendor"], glm["family"], glm["model"]), ("heimdall", "glm", "z-ai/glm-5.3-flash"))
 172 | +
 173 |      def test_ruling_76_the_window_is_never_widened_and_delivered_spans_carry_their_text(self):
 174 |          """RULING 76 (18:08 Nov 13): --hours over 12 refuses the run before anything is written; the delivered spans
 175 |          carry the approved text, for the same-speech rule."""
 176 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 177 | index 63732d9..d0d4bc6 100644
 178 | --- a/tests/package/test_medley.py
 179 | +++ b/tests/package/test_medley.py
 180 | @@ -538,7 +538,7 @@ class Rig:
 181 |          self.lock_check = lock_check                        # rulings 68 / 72: the render's lock (lock_precheck.check)
 182 |          self.visuals, self.visual_calls = dict(visuals or {}), []   # ruling 70: {moment id: record} (default: clean)
 183 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 184 | -        self.screens, self.events, self.a_seen = [], [], []
 185 | +        self.screens, self.events, self.a_seen, self.screen_deadlines = [], [], [], []
 186 |          self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
 187 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 188 |          self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}] + ([follow_up] if follow_up else [])
 189 | @@ -562,7 +562,8 @@ class Rig:
 190 |          self.write_avoid = []
 191 |  
 192 |      def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
 193 | -                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None):
 194 | +                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None):
 195 | +        self.screen_deadlines.append(deadline_s)           # ruling 82: which calls are bounded
 196 |          """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
 197 |          (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
 198 |          av, af = self.P._as_set(writer_vendor), self.P._as_set(writer_family)
 199 | @@ -1115,7 +1116,7 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 200 |          import context_integrity as CI
 201 |          from test_gates import a_item
 202 |  
 203 | -        def step_a(router_, contexts, wv, seed=7, writer_family=None):
 204 | +        def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False):
 205 |              calls.append((sorted(contexts), seed))
 206 |              if set(contexts) & set(fail):
 207 |                  raise RuntimeError("the batch reply was out of contract")
 208 | @@ -2345,7 +2346,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 209 |                    a_fail={("heimdall", "y"): ["REFERENT_OUTSIDE"]})
 210 |          out = rig.run()
 211 |          self.assertEqual(rig.screens[0], ("xai:grok", ["h", "x", "y", "z"]))          # the first screen, off heimdall
 212 | -        self.assertEqual(rig.screens[1], ("heimdall:deepseek", ["h", "x", "y", "z"]))  # the second, off xai
 213 | +        self.assertEqual(rig.screens[1:3], [("heimdall:deepseek", ["h", "x"]),          # the second, off xai, in
 214 | +                                            ("heimdall:deepseek", ["y", "z"])])         # ruling 82's chunks of 2
 215 |          self.assertLess(rig.events.index("step_a:heimdall:deepseek"), rig.events.index("angle_write"))
 216 |          sv = out["prescreen"]["second_vendor"]
 217 |          self.assertEqual(sv["h"], "PASS (heimdall:deepseek)")
 218 | @@ -2373,7 +2375,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 219 |          self.assertEqual(set(rig.a_seen[0].values()), {"heimdall:deepseek"})
 220 |          self.assertEqual(rig.write_avoid, [{"heimdall"}])          # and every write avoids Heimdall, so with the two
 221 |          # real vendors the writers never span both and a verdict off them always exists (audit 0640 C1, glm cond. 1)
 222 | -        self.assertEqual(len(rig.screens), 2)                      # and no re-screen was needed after the write
 223 | +        self.assertEqual(len(rig.screens), 3)                      # (the second screen in two chunks of 2) and no
 224 | +        #   re-screen was needed after the write
 225 |          self.assertIsNotNone(out["package"])
 226 |  
 227 |      def test_a_clip_that_fails_its_re_screen_is_swapped_out_alone_and_the_line_up_carries_on(self):
 228 | @@ -2389,8 +2392,10 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 229 |          self.assertIn("swapped {'y': 'z'}", out["tried"][0]["why"])
 230 |          self.assertIn("(out for good)", out["tried"][0]["why"])
 231 |          self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
 232 | -        self.assertEqual(rig.screens[2], ("openai:gpt", ["h", "x", "y"]))         # every verdict on a writer's vendor
 233 | -        self.assertEqual(rig.screens[3], ("openai:gpt", ["z"]))                   # only what changed is re-judged
 234 | +        self.assertEqual(rig.screens[3], ("openai:gpt", ["h", "x", "y"]))         # every verdict on a writer's vendor
 235 | +        self.assertEqual(rig.screens[4], ("openai:gpt", ["z"]))                   # only what changed is re-judged
 236 | +        self.assertEqual(rig.screen_deadlines, [None, 120.0, 120.0, 120.0, 120.0])   # audit 2005 C1: the first screen
 237 | +        #   unbounded as before; the second screen's two chunks and both off-writer re-screens at ruling 82's 120 s
 238 |  
 239 |      def test_a_re_screen_that_gives_no_verdict_is_never_a_pass(self):
 240 |          """The old branch read the stale verdict back when the re-screen returned nothing for a clip (a fail-open,
 241 | @@ -2435,10 +2440,12 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 242 |          ms = {m["moment_id"]: m for m in self.MS}
 243 |          a_by = {"h": {"backend": "xai:grok"}, "x": {"backend": "xai:grok"}, "y": {"backend": "nowhere:model"},
 244 |                  "z": {"backend": "heimdall:deepseek"}}
 245 | -        seen = []
 246 | +        seen, calls = [], []
 247 |  
 248 | -        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None):
 249 | +        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None, batch=None,
 250 | +                 deadline_s=None):
 251 |              seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
 252 | +            calls.append((batch, deadline_s))
 253 |              name = "heimdall:deepseek"          # off xai for h and x; for z (first verdict heimdall) the SAME vendor
 254 |              return {m["moment_id"]: {"backend": name} for m in chunk}, {m["moment_id"]: [] for m in chunk}, set(), set()
 255 |          saved = PK.prescreen
 256 | @@ -2451,6 +2458,43 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 257 |          self.assertEqual(sorted(two), ["h", "x"])
 258 |          self.assertTrue(fail["y"][0].startswith("STEP_A_UNKNOWN_BACKEND: the first verdict's back-end 'nowhere:model'"))
 259 |          self.assertTrue(fail["z"][0].startswith("STEP_A_SAME_VENDOR"))
 260 | +        self.assertEqual(set(calls), {(PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S)})   # ruling 82
 261 | +        self.assertEqual((PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S), (2, 120.0))
 262 | +
 263 | +    def test_ruling_82_the_second_vendor_step_a_fails_over_down_the_chain(self):
 264 | +        """RULING 82 (20:02 Nov 13): off the first verdict's vendor (xAI), deepseek -> glm-5.3-flash -> qwen3.8-27b,
 265 | +        each call bounded by 120 s; a model that is down, past the deadline, or answers out of contract hands over to
 266 | +        the next; all three failing is no verdict (never cached, never a pass)."""
 267 | +        import tempfile
 268 | +        import context_integrity as CI
 269 | +        sys.path.insert(0, os.path.join(REPO, "tests", "providers"))
 270 | +        from test_providers import Fake, router as mk_router
 271 | +        from test_gates import CTX, a_item
 272 | +        good = json.dumps({"excerpts": [a_item(lb) for lb in CTX]})
 273 | +        with tempfile.TemporaryDirectory() as d:
 274 | +            x = Fake("xai:grok", "xai", answer=good, family="grok")
 275 | +            ds = Fake("heimdall:deepseek", "heimdall", fail="503 from the gateway", family="deepseek")
 276 | +            glm = Fake("heimdall:glm", "heimdall", answer="not one JSON object", family="glm")
 277 | +            qw = Fake("heimdall:qwen", "heimdall", answer=good, family="qwen")
 278 | +            r = mk_router(d, [x, ds, glm, qw], {"context_verdict": ["xai:grok", "heimdall:deepseek", "heimdall:glm",
 279 | +                                                                      "heimdall:qwen"]})
 280 | +            asked = []
 281 | +            inner = r.call
 282 | +            r.call = lambda role, prompt, *a, **k: (asked.append(k.get("deadline_s")), inner(role, prompt, *a, **k))[1]
 283 | +            got, backend = CI.step_a(r, CTX, {"xai"}, writer_family={"grok"}, deadline_s=120.0, failover=True)
 284 | +            self.assertEqual((backend, x.calls, ds.calls, glm.calls, qw.calls), ("heimdall:qwen", 0, 1, 1, 1))
 285 | +            self.assertEqual(set(asked), {120.0})                      # every call of the chain bounded
 286 | +            self.assertEqual(sorted(got), sorted(CTX))
 287 | +            with self.assertRaises(ValueError):                        # without failover: as before, the bad answer
 288 | +                CI.step_a(r, CTX, {"xai"}, writer_family={"grok"})    # raises (the first verdict's path)
 289 | +            qw.answer = "still not JSON"
 290 | +            with self.assertRaises(P_ProviderError()):                 # all three spent: no verdict (law L-m)
 291 | +                CI.step_a(r, CTX, {"xai"}, writer_family={"grok"}, deadline_s=120.0, failover=True)
 292 | +
 293 | +
 294 | +def P_ProviderError():
 295 | +    import providers
 296 | +    return providers.ProviderError
 297 |  
 298 |  
 299 |  class TestRuling53Reposted(unittest.TestCase):
 300 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins). Only state what
you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- Step A is a context verdict on each clip (role context_verdict). The router (providers.Router.call) tries the
  role's chain in order. It skips a back-end on the vendor or family to avoid, or marked down. It moves on when a
  back-end is unavailable, refuses, misses the call's deadline_s (logged to the Heimdall evidence file, item 55), or
  answers empty. It raises ProviderError when the chain is spent.
- Step A's FIRST verdict is xAI's (grok). ORDER 06:22 item 45: every cuttable clip also gets a SECOND verdict off the
  first verdict's vendor and family (second_screen), BEFORE the angle step. Whichever vendor then writes, a verdict
  off the writer exists (law L-x: a generator never judges its own text). After a write, a clip whose usable verdict
  is on the writer's vendor or family is re-screened off it (the off-writer re-screen).
- Frozen vendors (openai, anthropic, local) are removed from every chain (tests/package/proof_ly.chains). So the
  second screen, which avoids xAI, had ONE model: Heimdall deepseek-v4.1-flash.
- On 19:23 / 19:4x Nov 13, a batch of step-A calls there spent its whole output budget with an empty answer. The
  chain was spent, 6 of 14 clips got no second verdict, and the build died at line-up formation.

The order, RULING 82 (orchestrator 20:02 Nov 13): "THE SECOND-VENDOR STEP A HAS A FAILOVER CHAIN. Off-writer verdict
order: Heimdall deepseek-v4.1-flash, then Heimdall z-ai/glm-5.3-flash (pp-ingest measured it 24/24 on calibration
today), then Heimdall qwen3.8-27b. Per-call deadline 120 s, not 300: at the deadline go to the next model at once,
record the miss in the Heimdall evidence file (item 55). The rule that matters is unchanged: the second verdict must
come from a model family different from the FIRST verdict's (xAI) and, for a clip the writer quotes, different from the
writer's. An outage verdict is never cached (as now)."

The change:
1. pipeline/model_providers.json:
   - a new back-end heimdall:z-ai/glm-5.3-flash (vendor heimdall, family glm);
   - context_verdict's chain is now xai, anthropic (frozen), heimdall deepseek, heimdall glm, heimdall qwen, local
     (frozen). With the frozen legs out: xai -> deepseek -> glm -> qwen.
2. context_integrity.step_a(..., deadline_s=None, failover=False):
   - deadline_s bounds each call (the router moves on and logs the miss);
   - failover=True also moves to the next model when an answer is OUT OF CONTRACT (each model once, via avoid_model).
     The router alone moves on only on errors and empty answers. When the chain is spent: ProviderError, so no
     verdict.
   - Without failover (the first verdict's path), a bad answer still raises, as before.
3. package.py:
   - SECOND_VERDICT_DEADLINE_S = 120 and SECOND_VERDICT_BATCH = 2;
   - prescreen(..., deadline_s) passes deadline_s and failover=(deadline_s is not None) to step_a;
   - second_screen chunks by 2 and passes the deadline;
   - the off-writer re-screen passes batch 2 and the deadline.
   Batches of 2 keep one call inside 120 s: deepseek took 284-304 s for 8 excerpts. Every verdict is still cached per
   moment (ruling 58), so no moment is paid for twice. A call that fails is never cached (unchanged).
4. Tests:
   - test_medley: the chain fails over (deepseek down, then glm out of contract, then qwen answers; every call
     asked with 120 s); without failover a bad answer raises; all three failing raises (no verdict). The second screen
     passes batch 2 and 120 s. Stubs accept the new arguments, and three tests' call counts follow the chunks of 2.
   - test_ledger_build: the frozen-out chain is exactly xai -> deepseek -> glm -> qwen; glm is family "glm".
   - Mutation runs: removing the failover, the deadline, or the batch / deadline in second_screen each fails a test.
   - 15 suites OK.

Known cost, by design: ruling 48's ledger books an ABANDONED call's upper bound (about $0.24 for a Heimdall call with
16000 output tokens) as spent, because no vendor report exists for it. Batches of 2 are meant to keep calls inside the
deadline.

Check, against the diff:
- the family rule: no second verdict can come from xAI (the first verdict's vendor), and none from the writer's family
  for a clip it quotes;
- that no answer out of contract can ever be a verdict, and the failover loop terminates;
- that the first verdict's path is unchanged (no failover there, no deadline);
- that nothing is cached from a call that failed;
- that the batch / deadline wiring reaches every second-vendor and off-writer call.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
