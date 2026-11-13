# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1635
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 113 s finish=stop usage in 7701 / out 2623 usd~0.062 (upper-bound price)

# Audit: pp-selectid-1635 — cost basis reporting fix (RULING 70)

## Scope of what I verified
Static review of the 141-line diff only. I did not run the tests; I take the stated results (test_visual_pin 11, test_medley 138 OK) as reported, not verified.

## Findings

### P1-1 — `usd_basis` leaks into the cached record's `usage`-adjacent fields? No — but the cache-exclusion list is the load-bearing line
`pipeline/visual_pin.py:76` (diff line 76): `cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd", "usd_basis")}`.

This is correct and is the key invariant: neither `usd` nor `usd_basis` enters the cache, so a later read cannot mistake a stored basis for fresh evidence. Verified consistent with the two cache-hit return paths (diff lines 56–57, 61–63) which re-add `usd=0.0, usd_basis="cached"` on the way out. No path stores a basis. Good.

### P1-2 — `cost()` bool guard is correct, but only on the reported branch
`pipeline/visual_pin.py:44` (diff line 44): `isinstance(rep, (int, float)) and not isinstance(rep, bool)`.

In Python, `True`/`False` are instances of `int`, so without the `not isinstance(rep, bool)` clause a literal `True` in `usage["usd_reported"]` would round to `1.0` and be labelled "reported" — $1.00, not $0.04. The guard is present and correct. Note the asymmetry: the **estimate** branch (diff line 46) has no bool guard — `float(getattr(r, "usd", 0.0) or 0.0)`. If a Reply ever carried `usd=True`, it would become `1.0` labelled "estimate". That's a latent, not active, defect: the background states Reply.usd is a price-table float, so I cannot show a concrete scenario today. P2.

### P2-1 — Estimate branch: `or 0.0` silently converts a legitimate 0.0 the same as a missing one
`pipeline/visual_pin.py:46` (diff line 46): `float(getattr(r, "usd", 0.0) or 0.0)`.

`0.0 or 0.0` → `0.0`, so this is behaviourally identical for the zero case; the `or` only matters for `None`/missing. No defect, noted for completeness. The `usd_basis` is still "estimate" either way, so the label is honest. No action.

### P2-2 — `estimated_calls` counts only the estimate branch, by design — confirm the log's conditional matches
`pipeline/package.py:24` (diff line 24): `out_visual["estimated_calls"] += 1` sits inside the `elif rec.get("usd_basis") == "estimate":` branch. The driver (diff lines 90–93) prints the "+ $Y ... for N call(s)" clause only `if vis.get("estimated_calls")`. So a run that is all-reported prints no estimate clause, and a run that is all-estimate prints no "vendor-reported" clause — wait, it does: the "$X vendor-reported" clause is unconditional (diff line 90) and prints `$0.0000 vendor-reported` when everything was estimated. That's cosmetic, not a mislabel: the figure printed is genuinely the reported-basis sum, which is legitimately $0.0000. Not a defect; the label stays truthful.

### P1-3 — Cached replies: the `usd=0.0` in the record vs. the ledger's "cached" counter — no double-count, verified
Cache-hit paths (diff lines 56–57, 62–63) return `usd=0.0, usd_basis="cached"`. In `package.build` (diff lines 20–24), a record with `usd_basis == "cached"` matches **neither** the `if` nor the `elif` — it adds to neither `usd_reported` nor `usd_estimate`, and not to `estimated_calls`. It only increments the `cached` counter (diff line 18). So a cached reply contributes $0.00 to both sums and is counted once, in `cached`. Correct: a reply served from its recording costs nothing, and it is not silently counted as a "reported" $0.00. Good.

### P1-4 — The `rec.get("usd_basis")` read in package.build vs. records that predate this change
`pipeline/package.py:20` (diff line 20): `if rec.get("usd_basis") == "reported":`.

Scenario: a visual record produced by the **old** code (pre-branch, e.g. replayed from a persisted package or a cache written before this change) has `usd` but no `usd_basis` key. Then:
- `usd_reported` += 0, `usd_estimate` += 0, `estimated_calls` += 0 — the cost silently vanishes from both sums.

But: the cache-exclusion change (diff line 76) means a cache written by the *new* code never holds `usd` either, so the only stale-`usd`-without-basis records are those persisted by the old code. Whether such records survive into a fresh build depends on whether `visual_cache` is persisted across builds — the diff shows `VP.load_cache(visual_cache)` (diff line 8), which implies yes. If the 2026-11-13 first-build's cache (the $0.3646 run) is reused, its records carry `usd` but no `usd_basis`, and the new build's ledger would print $0.0000 for calls that actually cost $0.0890.

**However** — the cache-hit paths (diff lines 56–57) return `usd=0.0, usd_basis="cached"` regardless, because a cache hit is by definition not a new call. The stale-`usd`-in-cache scenario only matters if `package.build`'s `see()` sums over records that came from the cache *miss* path of a *previous* build

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 22 s finish=stop usage in 7716 / out 151 usd~0.042 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: none verifiable from diff** (cost() exclusively selects one basis; bool/missing/None rep routes to "estimate" via explicit `isinstance(..., (int,float)) and not isinstance(..., bool)` at visual_pin.py:44; package.py:20-24 only mutates the split counters on exact string match; no gate, seal, or cache-key mutation present—usd/usd_basis explicitly stripped before cache write at visual_pin.py:76 and omitted from sealed test at test_visual_pin.py:139; all paths in modified visual_for and build see() carry a basis; test coverage added for the three cases).  

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 22 s finish=stop usage in 8380 / out 1433 usd~0.047 (upper-bound price)

# Audit: pp-selectid-1635 (C1_STEP.diff)

## Scope Verification
I reviewed the diff for `pipeline/package.py`, `pipeline/visual_pin.py`, `tests/package/proof_ledger.py`, `tests/package/test_medley.py`, and `tests/package/test_visual_pin.py`. The change is strictly a reporting/accounting fix for RULING 70 (separating vendor-reported cost from price-table estimates). It does not touch sentence law, selection locks, snap limits, credits, sign-off, edge words, dissent, protected preview, punctuation, channel-first, written forms, text-as-spoken, claim-is-event, release auth, canonical form, or model-reply validation. No gate thresholds, seal contents, or cache keys are modified.

## Findings

### P0 (Blocking)
None.

### P1 (Major)
None.

### P2 (Minor / Observations)

1. **`pipeline/visual_pin.py:44` — Bool guard is correct but worth noting**
   The check `isinstance(rep, (int, float)) and not isinstance(rep, bool)` correctly prevents `True`/`False` from being treated as a reported cost (since `bool` is a subclass of `int` in Python). This satisfies the requirement that "a bool ... never counts as reported." Verified correct.

2. **`pipeline/visual_pin.py:46` — Estimate fallback uses `Reply.usd`**
   When no vendor figure is present, the code falls back to `float(getattr(r, "usd", 0.0) or 0.0)`. This is the price-table estimate as documented. The `or 0.0` guard handles `None` or `0` gracefully. No issue.

3. **`pipeline/visual_pin.py:76` — Cache exclusion of `usd_basis`**
   The cache write excludes `"usd"` and `"usd_basis"` from the stored record. This is correct: cost is per-invocation, not a property of the visual judgment. The seal (`sealed()`) already excludes cost fields per the existing test at line 138–140. No change to seal or cache key.

4. **`pipeline/package.py:20–24` — Split accounting**
   `usd_reported` and `usd_estimate` are accumulated separately. `estimated_calls` counts only the estimate-basis calls. They are never summed under a single label. Correct.

5. **`tests/package/proof_ledger.py:88–93` — Log line**
   The driver prints `"$X vendor-reported"` and conditionally appends `"+ $Y price-table estimate for N call(s) with no vendor figure"` only when `estimated_calls > 0`. This matches the fix spec. No path labels an estimate as reported or vice versa.

6. **`tests/package/test_medley.py:106` — Test fixture**
   The mock visual record now includes `"usd_basis": "reported"`. The assertion at line 115 checks `(usd_reported, usd_estimate) == (0.006, 0.0)`, confirming the split. Three sheets at $0.002 each = $0.006 reported, $0.00 estimate. Correct.

7. **`tests/package/test_visual_pin.py:127–136` — Three bases covered**
   - `usd_reported` present → `{"usd": 0.041144, "usd_basis": "reported"}` ✓
   - `usd_reported` absent → `{"usd": 0.37, "usd_basis": "estimate"}` ✓
   - `cached=True` → `{"usd": 0.0, "usd_basis": "cached"}` ✓
   All three paths verified.

8. **No gate, seal, or cache-key changes**
   - Gates: No gate logic is touched. `MEDLEY_GATES` membership is unchanged (test line 116).
   - Seal: `sealed()` is not modified in this diff; the existing test confirms cost fields are excluded.
   - Cache key: The key `k` is computed before the cost logic and is unchanged. Only the *value* stored excludes `usd`/`usd_basis`.

9. **Smallest diff / no new renderer, compositor, or selector (M1)**
   The diff adds one small function (`cost`), modifies two accumulation sites, and updates tests. No new modules, no new rendering paths. Compliant.

10. **GPU0 only / no publishing**
    No GPU or publishing code is touched. Compliant.

## Specific Checks Requested

| Check | Result |
|---|---|
| No path labels an estimate as reported (or reverse) | **Pass.** `cost()` returns `"reported"` only when `usage["usd_reported"]` is a non-bool number. `package.build` routes to `usd_reported` only on `"reported"` basis, to `usd_estimate` only on `"estimate"` basis. Log line prints them separately. |
| Bool or missing figure never counts as reported | **Pass.** `isinstance(rep, bool)` is explicitly excluded. Missing `usd_reported` (KeyError → `None` via `.get()`) falls through to estimate. |
| Nothing changes a gate | **Pass.** No gate code modified. |
| Nothing changes the seal | **Pass.** `sealed()` untouched; cost fields already excluded. |
| Nothing changes the cache key | **Pass.** Key computation unchanged; only stored value excludes cost fields. |

## Uncertainties
- I cannot verify the actual runtime behavior of `providers.Router` or the xAI/Heimdall backends from this diff alone. The assumption that `Reply.usage["usd_reported"]` is the correct field for vendor-reported cost is taken from the background description and is consistent with the code.
- The diff does not show the full `sealed()` function, so I rely on the existing test (line 138–140) to confirm cost exclusion from the seal.

## SHIP: yes

Th

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1635 (ruling 70's cost report: the vendor's figure, an estimate labelled): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", no findings.
  - qwen: "SHIP: yes", P2 observations, each "verified correct".
  - glm: "SHIP: yes with conditions": two confirmations and one optional test.
- No P0 or P1 holds. Nothing changes in the code; cycle 2 reviews the same diff.

## Answered (glm's conditions)

| # | condition | the answer |
|---|---|---|
| A1 | No other reader of the renamed out["visual"]["usd"]? | grep over pipeline/ and tests/ for visual"]["usd"], .get("usd") on the visual summary and out_visual["usd"] finds none. The only reader is the driver's log line, which this diff updates. |
| A2 | Does VP.sealed() keep usd_basis out of the seal? | sealed() is an INCLUSION list: it copies only version, measured, flags, third_person, on_screen_text, lower_third, backend, replayed and why, plus the sheet's name, sha256 and times (visual_pin.sealed). usd, usd_basis, usage and cached can never reach the seal, whatever the record carries. |
| A3 | glm P1-4: a record without usd_basis (one written before this change) would add to neither sum | Every record build() can see carries a basis now. visual_for's fresh path sets it through cost(); both cache-hit paths set "cached", and they serve records cached before this change too. Since the cost of a cache hit is 0, nothing is lost. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-2: the estimate branch has no bool guard | Reply.usd is the back-end's price-table float (Backend.usd), never a bool. glm: "latent, not active". |
| G2 | glm (optional): a build-level test of the estimate branch | cost()'s three bases are unit-tested; the build's split is tested with reported records. |

## Verification

- test_visual_pin 11 and test_medley 138 OK on dev27 (base 57e7239f).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1635/C2_STEP.diff (141 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index ce8c6e4..dc2f3fc 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -2065,7 +2065,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
   6 |      usd0 = _spent(spend)
   7 |      import visual_pin as VP                            # ruling 70
   8 |      vcache = VP.load_cache(visual_cache) if visual_cache else {}
   9 | -    out_visual = {"calls": 0, "cached": 0, "usd": 0.0, "unmeasured": 0, "flags": 0}
  10 | +    out_visual = {"calls": 0, "cached": 0, "usd_reported": 0.0, "usd_estimate": 0.0, "estimated_calls": 0,
  11 | +                  "unmeasured": 0, "flags": 0}   # ruling 70: the vendor's figure and the estimate never mixed
  12 |  
  13 |      def see(ms_):                                      # RULING 70: the clips' sheets, judged (cached per moment)
  14 |          todo = [m for m in ms_ if not (m.get("visual") or {}).get("measured")]
  15 | @@ -2075,7 +2076,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  16 |              for m, rec in zip(todo, recs):
  17 |                  m["visual"] = rec
  18 |                  out_visual["cached" if rec.get("cached") else "calls"] += 1     # audit 1541 C1: every attempt
  19 | -                out_visual["usd"] = round(out_visual["usd"] + float(rec.get("usd") or 0.0), 6)
  20 | +                if rec.get("usd_basis") == "reported":
  21 | +                    out_visual["usd_reported"] = round(out_visual["usd_reported"] + float(rec.get("usd") or 0.0), 6)
  22 | +                elif rec.get("usd_basis") == "estimate":
  23 | +                    out_visual["usd_estimate"] = round(out_visual["usd_estimate"] + float(rec.get("usd") or 0.0), 6)
  24 | +                    out_visual["estimated_calls"] += 1
  25 |                  out_visual["unmeasured"] += 0 if rec.get("measured") else 1
  26 |                  out_visual["flags"] += len(rec.get("flags") or [])
  27 |              VP.save_cache(visual_cache, vcache)
  28 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
  29 | index 6cb6417..4cecca8 100644
  30 | --- a/pipeline/visual_pin.py
  31 | +++ b/pipeline/visual_pin.py
  32 | @@ -228,6 +228,19 @@ def sealed(rec):
  33 |      return out
  34 |  
  35 |  
  36 | +def cost(r):
  37 | +    """A reply's cost as RULING 70 reports it: {"usd": the vendor-reported figure where the reply carries one (xAI
  38 | +    cost_in_usd_ticks, Heimdall usage.cost: Reply.usage["usd_reported"]), "usd_basis": "reported"}; else the price-table
  39 | +    estimate (Reply.usd, an upper bound) with "usd_basis": "estimate"; a reply served from its recording costs nothing
  40 | +    ("cached")."""
  41 | +    if getattr(r, "cached", False):
  42 | +        return {"usd": 0.0, "usd_basis": "cached"}
  43 | +    rep = (getattr(r, "usage", None) or {}).get("usd_reported")
  44 | +    if isinstance(rep, (int, float)) and not isinstance(rep, bool):
  45 | +        return {"usd": round(float(rep), 6), "usd_basis": "reported"}
  46 | +    return {"usd": round(float(getattr(r, "usd", 0.0) or 0.0), 6), "usd_basis": "estimate"}
  47 | +
  48 | +
  49 |  def visual_for(router, m, work_dir, cache, seed=7, log=print):
  50 |      """The clip's visual record (cached per moment and span). Not measured on any failure: never a pass (law L-m).
  51 |      -> {"version", "measured", "flags", "third_person", "on_screen_text", "lower_third", "sheet" {"name", "sha256",
  52 | @@ -238,12 +251,12 @@ def visual_for(router, m, work_dir, cache, seed=7, log=print):
  53 |      if hit is not None:                              # the judged sheet, still on disk with the judged bytes
  54 |          p = os.path.join(work_dir, "visual", (hit.get("sheet") or {}).get("name") or "-")
  55 |          if _sha_of(p) == (hit.get("sheet") or {}).get("sha256"):
  56 | -            return dict(hit, cached=True, usd=0.0, sheet=dict(hit["sheet"], path=p))
  57 | +            return dict(hit, cached=True, usd=0.0, usd_basis="cached", sheet=dict(hit["sheet"], path=p))
  58 |      try:
  59 |          video = fetch(m["video_id"], float(m["start"]), float(m["end"]), work_dir)
  60 |          path, sha, ts = sheet(video, float(m["start"]), float(m["end"]), work_dir)
  61 |          if hit is not None and sha == hit["sheet"]["sha256"]:        # rebuilt, the same bytes: the same verdict
  62 | -            return dict(hit, cached=True, usd=0.0, sheet=dict(hit["sheet"], path=path))
  63 | +            return dict(hit, cached=True, usd=0.0, usd_basis="cached", sheet=dict(hit["sheet"], path=path))
  64 |          with open(path, "rb") as f:
  65 |              b64 = base64.b64encode(f.read()).decode()
  66 |      except Exception as e:                       # noqa: BLE001  no sheet: not measured (law L-m), never a crash
  67 | @@ -258,10 +271,10 @@ def visual_for(router, m, work_dir, cache, seed=7, log=print):
  68 |              rec = {"version": VERSION, "measured": True, **v, "flags": flags(v),
  69 |                     "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path},
  70 |                     "backend": r.backend, "replayed": bool(getattr(r, "replayed", False)),
  71 | -                   "usd": 0.0 if getattr(r, "cached", False) else float(getattr(r, "usd", 0.0) or 0.0),
  72 | +                   **cost(r),
  73 |                     "usage": getattr(r, "usage", None), "cached": bool(getattr(r, "cached", False))}
  74 |              if cache is not None and not rec["replayed"]:
  75 | -                cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd")}
  76 | +                cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd", "usd_basis")}
  77 |              return rec
  78 |          except Exception as e:                   # noqa: BLE001  fail closed; each try's reason is kept (C2)
  79 |              if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)) and hasattr(router, "reject"):
  80 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  81 | index 6647ab8..63f93ab 100644
  82 | --- a/tests/package/proof_ledger.py
  83 | +++ b/tests/package/proof_ledger.py
  84 | @@ -245,8 +245,10 @@ def main(argv=None):
  85 |                                "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
  86 |      vis = res.get("visual") or {}
  87 |      say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) asked ({vis.get('unmeasured', 0)} not measured), "
  88 | -        f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); measured cost ${vis.get('usd', 0):.4f} "
  89 | -        f"(the router's figure: vendor-reported where the reply carries it)")
  90 | +        f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); cost ${vis.get('usd_reported', 0):.4f} "
  91 | +        f"vendor-reported" + (f" + ${vis.get('usd_estimate', 0):.4f} price-table estimate for "
  92 | +                              f"{vis.get('estimated_calls', 0)} call(s) with no vendor figure"
  93 | +                              if vis.get("estimated_calls") else ""))
  94 |      say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
  95 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
  96 |      try:                                                 # audit 1420 C2: a registry failure never loses the record;
  97 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  98 | index ee2d718..dea7ca8 100644
  99 | --- a/tests/package/test_medley.py
 100 | +++ b/tests/package/test_medley.py
 101 | @@ -624,7 +624,8 @@ class Rig:
 102 |                                   "finding": "no third person"},
 103 |                  "on_screen_text": [], "lower_third": {"name": None, "text": None},
 104 |                  "sheet": {"name": f"visual_{m['moment_id']}.jpg", "sha256": "0" * 64, "times": [0.0], "path": "/x"},
 105 | -                "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "cached": False}
 106 | +                "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "usd_basis": "reported",
 107 | +                "cached": False}
 108 |          return dict(base, **self.visuals.get(m["moment_id"], {}))
 109 |  
 110 |      def onset(self, m, *a, **k):
 111 | @@ -1623,6 +1624,7 @@ class TestRuling70Visual(unittest.TestCase):
 112 |          self.assertEqual([sg["visual"]["sheet"]["name"] for sg in pk["segments"]],
 113 |                           ["visual_h.jpg", "visual_x.jpg", "visual_y.jpg"])
 114 |          self.assertNotIn("path", pk["segments"][0]["visual"]["sheet"])  # never a scratch path in the seal
 115 | +        self.assertEqual((out["visual"]["usd_reported"], out["visual"]["usd_estimate"]), (0.006, 0.0))
 116 |          self.assertIn("visual", package_pin.MEDLEY_GATES)
 117 |          pin = package_pin.to_pin(spk(pk), "r")
 118 |          self.assertIn("visual", pin["segments"][1])
 119 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
 120 | index df3c51b..22f9647 100644
 121 | --- a/tests/package/test_visual_pin.py
 122 | +++ b/tests/package/test_visual_pin.py
 123 | @@ -63,6 +63,17 @@ class TestContract(unittest.TestCase):
 124 |          self.assertIn("not measured", VP.hook_block({"measured": False}))
 125 |          self.assertIn("not measured", VP.hook_block(None))
 126 |  
 127 | +    def test_the_cost_is_the_vendors_figure_and_an_estimate_is_labelled(self):
 128 | +        class R:
 129 | +            cached, usd = False, 0.37
 130 | +        r = R()
 131 | +        r.usage = {"in": 2760, "out": 6226, "usd_reported": 0.041144}
 132 | +        self.assertEqual(VP.cost(r), {"usd": 0.041144, "usd_basis": "reported"})
 133 | +        r.usage = {"in": 2760, "out": 6226}
 134 | +        self.assertEqual(VP.cost(r), {"usd": 0.37, "usd_basis": "estimate"})
 135 | +        r.cached = True
 136 | +        self.assertEqual(VP.cost(r), {"usd": 0.0, "usd_basis": "cached"})
 137 | +
 138 |      def test_the_seal_never_holds_a_scratch_path_or_a_cost(self):
 139 |          s = VP.sealed({"version": "v", "measured": True, "flags": [], "third_person": {}, "on_screen_text": [],
 140 |                         "lower_third": {}, "backend": "b", "replayed": False, "usd": 0.01, "cached": True,
 141 | 
```

---

You are auditing a SMALL reporting fix on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins).
Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- The router (providers.Router) returns a Reply whose .usd is the PRICE-TABLE ESTIMATE (usage x the config's
  upper-bound $ per 1M). Where a vendor reports its own cost, the back-end puts it in Reply.usage["usd_reported"]:
  xAI's cost_in_usd_ticks / 1e10, Heimdall's usage.cost.
- The spend ledger keeps the two apart (usd_reported vs usd_estimate), per the project's rule: record the vendor's
  figure, label an estimate as an estimate.
- RULING 70 (orchestrator 15:29 Nov 13): "Report the measured cost on the first build."

The defect:
- visual_pin.visual_for recorded "usd" from Reply.usd (the estimate).
- The build summed that, and the driver's log line called it "measured cost ... vendor-reported where the reply
  carries it".
- On the first build it printed $0.3646 for 3 sheets. The ledger shows the vendor-reported cost was $0.0890; the
  $0.3646 is the price-table upper bound.

The fix:
1. visual_pin.cost(reply) returns the cost and its basis:
   - {"usd": usage["usd_reported"], "usd_basis": "reported"} when the vendor reported one;
   - else {"usd": Reply.usd, "usd_basis": "estimate"};
   - {"usd": 0.0, "usd_basis": "cached"} for a reply served from its recording.
   Cache hits carry usd_basis "cached". Neither usd nor usd_basis enters the cache or the seal.
2. package.build's out["visual"] keeps usd_reported and usd_estimate apart (plus estimated_calls); they are never
   summed under one label.
3. The driver's log line prints "$X vendor-reported", and, only when some call carried no vendor figure,
   "+ $Y price-table estimate for N call(s) with no vendor figure".
4. Tests: test_visual_pin covers the three bases; test_medley covers the build's split totals. test_visual_pin 11,
   test_medley 138 OK.

Check: that no path labels an estimate as reported (or the reverse), and that a bool or a missing figure never counts
as reported. Also that nothing here changes a gate, the seal or the cache key.

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
