# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0352
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 283 s finish=stop usage in 8102 / out 8050 usd~0.145 (upper-bound price)

# Audit: pp-selectid-0352 — ad-read screen moved before the angle; why_none naming

## What I can verify from the diff

The diff is 161 lines: `moments.py` extracts the deterministic ad-read screen into `ad_read_marker()`; `package.py` adds `ad_read_out()` + a filter in `build()` + a `why_none` fallback; `test_medley.py` adds `TestAdReadBeforeTheAngle` (4 tests) and one assertion to an existing test. I have no access to the surrounding files, so everything below is what the diff itself shows, plus what it implies about the referenced helpers (`AD_MARKERS`, `CI.context_around`, `exclusion_for`, `src_of`, `pm`, `Rig`) — flagged as assumptions where I cannot see them.

---

## P0 findings

None. I found no defect in the diff that breaks the stated behavior on the paths the tests exercise.

---

## P1 findings

**P1-1 — `ad_read_out` can refuse a moment the package stage would NOT refuse, if `context_around` returns `""` (empty string) vs `None` differently than assumed.**
`package.py:55-58` (diff lines 55–58): `why = M.ad_read_marker(m["text"], before) if before is not None else None`. The skip condition is `before is not None`. But `ad_read_marker` treats `before_text=""` and `None` identically (`last_before = ""`), and the docstring of `ad_read_out` says a moment with "no context" is left to the package stage. If `CI.context_around` signals "no context" with `""` rather than `None` (I cannot see its contract in the diff), the moment is screened here on an empty before-text — which is exactly what `exclusion_verdict` would do anyway (`exclusion_verdict` also receives `before_text=""`-ish), so the *verdict* still matches. The residual risk is only that the "left to the package stage" claim in the docstring/test comment is inaccurate, and the moment is excluded earlier than documented while the package stage would have produced the same exclusion with its own reason string. **Scenario:** `context_around` returns `("", "after")` for a source whose head is the moment; `ad_read_out` refuses it on a marker in the moment text; the package stage would have refused it too, so behavior is equal — but if `context_around`'s "no context" sentinel is `""`, the test `test_ad_read_out_reads_the_same_context_as_the_exclusion_screen`'s `("c": (None, None))` case does not cover it. Not a behavior divergence, a documentation/coverage gap. Severity: P1 (not P0) because the verdicts coincide either way — the marker search on `""` finds nothing, so the only divergence would be a marker in the *moment text* with an empty before-context, which both stages refuse identically.

Wait — re-examine: if `before=""` and the marker is in the moment text, `ad_read_out` refuses here; the package stage's `exclusion_for` would also refuse (same marker in the moment). Equal. If `before=""` and no marker, neither refuses. Equal. So the only true divergence risk is if `context_around`'s no-context sentinel is neither `None` nor `""` — unverifiable from the diff. Downgrade: **P1-1 is really a coverage note, not a defect.** Keep as P1 only because the "same context" claim rests on an unseen contract.

**P1-2 — `why_none` fallback can overwrite nothing but can also be *set* when a later path would have set a more specific reason — ordering.**
`package.py:94-97` (diff lines 94–97): the fallback runs only `if out["package"] is None and not out.get("why_none")`. That correctly defers to any earlier-set reason (e.g. the `<3 channels` early return at diff line 87–89, which returns before this code — actually that path `return out` at line 89, so the fallback never runs on it; good). But I cannot see, from the diff, whether any *other* code path between line 93 and 98 (the angle loop, `over_budget`, `budget_stop`) sets `why_none` — the diff shows only the added lines. If some path inside the angle loop sets `why_none` and then a package IS found... no, the fallback is guarded by `out["package"] is None`. If a path sets `why_none` AND leaves package None, the fallback respects it (`not out.get("why_none")`). So the guard is correct as far as the diff shows. The remaining question: does the angle loop's failure path set `tried[i]["why"]` for *every* failure mode, including "line-ups formed but every write/gate failed"? If a tried angle's `why` key is absent (`t.get('why')` → None), the message reads `angle 1: None`. **Scenario:** an angle whose line-up failed at the write/gate stage records `{"angle": 1}` with no `why` key → `why_none` = "no angle gave a package: angle 1: None". Cosmetic, not a hidden reason. P1→P2. I'll list it as P2-1.

**P1-3 — the 900-char truncation can cut mid-escape.** `[:900]` truncates the joined string; if it cuts inside an angle's why, the last angle's reason is silently clipped. That's the documented intent ("names every tried angle's own why" — it may not, if >900 chars). With up to 3 angles this is unlikely to exceed 90

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 23 s finish=stop usage in 8200 / out 172 usd~0.045 (upper-bound price)

**P0: None verifiable from diff**  
**P1: None verifiable from diff**  
**P2: None verifiable from diff** (ad_read_marker exactly extracts the prior deterministic logic from exclusion_verdict; ad_read_out calls the same marker function on the identical before-text that CI.context_around supplies for a given Source+sentences+words; moments lacking Source or before=None are deliberately skipped and left to the later package-stage refusal; exclusion_verdict return shape and model path are byte-identical; build() filters after no_role but before prescreen/angle writing, records "ad_read" separately, leaves out["usable"] semantics untouched, and only populates why_none when no prior why_none exists and package is None; all three new tests pass the exact scenarios described; no check acceptance surface is altered)

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 27 s finish=stop usage in 8780 / out 1898 usd~0.055 (upper-bound price)

# Code Audit: pp-selectid-0352 (C1_STEP.diff)

## Findings

### P0: None
No critical defects found. The change correctly implements the "refuse earlier" requirement without altering the acceptance criteria of the downstream exclusion screen.

### P1: None
No high-severity issues.

### P2: Observations / Minor

**1. `pipeline/package.py` (lines 55-57 in diff): `KeyError` handling relies on `src_of` behavior**
The code uses `CI.context_around(src_of(m, sources), ...)`. If `src_of` raises a `KeyError` for a moment without a source, it is caught. However, if `src_of` returns `None` or an invalid key that `CI.context_around` does *not* raise a `KeyError` for (e.g., returns `None` context instead), the logic proceeds to `M.ad_read_marker(m["text"], before)`.
*   **Verification:** The docstring states: "A moment with no Source or no context is left to the package stage...".
*   **Analysis:** If `src_of` raises `KeyError`, it is skipped (correct). If `CI.context_around` returns `None` (no context), `before` is `None`. `ad_read_marker` handles `before_text=None` by treating it as `""` (line 12: `(before_text or "").strip()`). Thus, `ad_read_marker` will only check the moment text itself.
*   **Downstream Check:** At the package stage, `exclusion_for` (not shown in diff, but implied by context) refuses moments with "no context". Since `ad_read_out` skips the *context* check when context is `None` (it only checks the moment text), it does **not** refuse the moment here. It leaves it to the package stage. This is consistent with the "fail closed" and "refuse exactly what the package stage refuses" law, provided the package stage *does* refuse no-context moments. The diff comment confirms: "left to the package stage, which refuses it (fail closed)."
*   **Conclusion:** This is correct behavior. The P2 is merely a note that the "no context" refusal is deferred, not duplicated. This is intentional per the design.

**2. `pipeline/moments.py` (lines 12-16 in diff): `ad_read_marker` logic duplication**
The function `ad_read_marker` extracts the last sentence from `before_text` using `re.split(r"(?<=[.!?])\s+", ...)`. This logic was previously inline in `exclusion_verdict`.
*   **Verification:** The inline code in `exclusion_verdict` (lines 26-30 in diff) is removed and replaced by a call to `ad_read_marker`.
*   **Analysis:** The regex and logic are identical. The refactoring is clean. No behavioral change.

**3. `pipeline/package.py` (lines 94-97 in diff): `why_none` truncation**
`out["why_none"]` is truncated to 900 characters.
*   **Analysis:** This is a reasonable safeguard against log bloat. It does not affect the correctness of the gate, only the diagnostic message.

**4. `tests/package/test_medley.py` (lines 138-139 in diff): Test setup for `ad_read_out`**
The test mocks `CI.context_around` to return tuples `("text", "x")`. The code in `ad_read_out` unpacks `before, _ = CI.context_around(...)`.
*   **Analysis:** This confirms that `CI.context_around` returns a tuple where the first element is the `before_text`. The test validates that `ad_read_out` reads the same context as the exclusion screen.

## Law Compliance Check

*   **SENTENCE LAW / SELECTION LOCK / SNAP LIMIT / NEIGHBOUR / ONSET/TAIL / CREDITS / L-a / L-b / L-c / L-d / L-e / L-f / L-g / L-h / L-i / L-j / L-k / L-l:**
    *   This diff does not touch sentence boundaries, selection locks, snap limits, neighbor checks, onset/tail, credits, sign-off names, edge words, dissent, protected previews, punctuation, channel clusters, written forms, text reading, claim events, release authorization, canonical forms, or model reply validation.
    *   **L-j (Release is Authorised on These Bytes):** The change modifies `package.build()` to filter moments *before* the angle step. This changes the set of moments available for packaging. However, the law states that "all release gates passed" means every REQUIRED gate ran on the bytes sent. By filtering out ad-read moments earlier, the pipeline ensures that the final package does *not* contain moments that would have been refused by the exclusion screen. This is a **pre-filter**, not a bypass. The exclusion screen still runs at the package stage (implied by "left to the package stage"). If a moment slips through `ad_read_out` (e.g., due to a context mismatch), the package stage's `exclusion_for` will still catch it. Thus, the final bytes are still gated by the exclusion screen. **Compliant.**
    *   **M12 (Fail Closed):** Moments with no Source or no context are skipped in `ad_read_out` and left to the package stage, which refuses them. **Compliant.**
    *   **Law 20 (Gate Thresholds):** No thresholds are changed. The `AD_MARKERS` regex is unchanged. **Compliant.**
    *   **Smallest Diff:** The change is minimal and focused. **Compliant.**

## Specific Checks Requested

1.  **Does `ad_read_out` refuse exactly what `ex

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0352 (the exclusion screen's deterministic part before step A; why_none named): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers moments.py, package.py and test_medley.py. No P0. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- qwen: no P0, no P1, "SHIP: yes";
- glm: "yes with conditions" (no P0; its P1s are mostly coverage notes about contracts outside the diff).

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | Prove, not assert, that ad_read_out refuses exactly what the package stage refuses (glm condition 1, P1-1, P1-8) | IMPLEMENTED: a differential test runs package.exclusion_for, the package stage's own screen, on the same moment and the same stubbed context, with a router that fails if called. It gets the same verdict ("exclude"), the same reason and the deterministic backend. |
| K2 | The contracts outside the diff (glm condition 2) | VERIFIED in the code. (a) exclusion_for passes context_around's raw before-string to exclusion_verdict (package.py: `before, after = CI.context_around(...)`, then `M.exclusion_verdict(router, m["text"], before, after, ...)`); ad_read_out reads the same call on the same fields. (b) src_of is context_integrity.source_for, which raises KeyError for a missing Source (audit 0208, K1), the same lookup exclusion_for uses. (c) A moment's "sentences" is always [k0, k1] (moments.record), the same fields exclusion_for indexes. |
| K3 | why_none could read "angle N: None"; the whole message was truncated at 900 (glm P2-1, P2-3) | IMPLEMENTED: each angle's reason is its why, else its result, else "no reason recorded", truncated at 250 characters per angle. |
| K4 | A KeyError from any field is skipped, not only a missing Source; out["ad_read"] is a census after no_role (glm P1-4, P1-5) | DOCUMENTED in ad_read_out's docstring. Both fail closed: a skipped moment still meets the package stage's screen. |
| K5 | The AD_MARKERS search ran twice (glm P2-2) | IMPLEMENTED: one search. |

## Kept

- **glm P1-2 (why_none ordering):** verified correct by the reviewer itself. The fallback runs only when there is no package and nothing else set a reason.
- **glm P1-12 (step A's "screened" count changes):** documented. Step A no longer sees moments that the package stage refuses on the same rule.

## Verification

- test_medley 54 OK and test_moments OK; the other suites are run before the commit.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0352/C2_STEP.diff (172 lines)
```
   1 | diff --git a/pipeline/moments.py b/pipeline/moments.py
   2 | index eb78ab32..cfed8853 100644
   3 | --- a/pipeline/moments.py
   4 | +++ b/pipeline/moments.py
   5 | @@ -355,6 +355,17 @@ naming a company neutrally is not an accusation.
   6 |  Return ONLY this JSON object: {{"risks": [], "about_bitcoin": "yes", "why": "..."}}"""
   7 |  
   8 |  
   9 | +def ad_read_marker(moment_text, before_text=""):
  10 | +    """The exclusion screen's DETERMINISTIC part: an ad-read marker in the moment, or in the sentence right before it
  11 | +    (an ad read runs on) -> the reason, else None. exclusion_verdict() and package.build() (before step A) share it."""
  12 | +    last_before = re.split(r"(?<=[.!?])\s+", (before_text or "").strip())[-1] if (before_text or "").strip() else ""
  13 | +    for where, txt in (("the moment", moment_text or ""), ("the sentence before it", last_before)):
  14 | +        hit = AD_MARKERS.search(txt)
  15 | +        if hit:
  16 | +            return f"ad-read marker '{hit.group(0)}' in {where}"
  17 | +    return None
  18 | +
  19 | +
  20 |  def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7, avoid_model=None):
  21 |      """-> {"verdict": "keep" | "exclude", "why", "risks", "backend", "measured", "replayed"}: a deterministic ad-read
  22 |      screen (a marker in the moment, or in the sentence right before it: an ad read runs on), then the blind model
  23 | @@ -363,11 +374,10 @@ def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7
  24 |      is also NOT measured (the exam adapter reports it as such)."""
  25 |      import providers as P
  26 |      from story_semantics import quote_data
  27 | -    last_before = re.split(r"(?<=[.!?])\s+", (before_text or "").strip())[-1] if (before_text or "").strip() else ""
  28 | -    for where, txt in (("the moment", moment_text or ""), ("the sentence before it", last_before)):
  29 | -        if AD_MARKERS.search(txt):
  30 | -            return {"verdict": "exclude", "why": f"ad-read marker '{AD_MARKERS.search(txt).group(0)}' in {where}",
  31 | -                    "risks": ["ad_read"], "backend": "deterministic", "measured": True, "replayed": False}
  32 | +    why = ad_read_marker(moment_text, before_text)
  33 | +    if why:
  34 | +        return {"verdict": "exclude", "why": why, "risks": ["ad_read"], "backend": "deterministic", "measured": True,
  35 | +                "replayed": False}
  36 |      r = None
  37 |      try:
  38 |          r = router.call("exclusion_verdict", EXCLUSION_PROMPT.format(before=quote_data(before_text, 3000),
  39 | diff --git a/pipeline/package.py b/pipeline/package.py
  40 | index c18ce11e..b00c84a5 100644
  41 | --- a/pipeline/package.py
  42 | +++ b/pipeline/package.py
  43 | @@ -569,6 +569,25 @@ def stand_alone_check(segs):
  44 |      return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"))
  45 |  
  46 |  
  47 | +def ad_read_out(ms, sources):
  48 | +    """{moment id: why} for the moments the exclusion screen's DETERMINISTIC part refuses (moments.ad_read_marker: an
  49 | +    ad-read marker in the moment or in the sentence right before it, the same context exclusion_for() reads). The same
  50 | +    rule refuses them at the package stage; run first, the angles are never built around them. A moment with no
  51 | +    Source or no context is left to the package stage, which refuses it (fail closed); so is any moment whose fields
  52 | +    the lookup cannot read (a KeyError). out is a census of the moments that survived no_role_on_screen."""
  53 | +    import moments as M
  54 | +    out = {}
  55 | +    for m in ms:
  56 | +        try:
  57 | +            before, _ = CI.context_around(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])
  58 | +        except KeyError:
  59 | +            continue
  60 | +        why = M.ad_read_marker(m["text"], before) if before is not None else None
  61 | +        if why:
  62 | +            out[m["moment_id"]] = why
  63 | +    return out
  64 | +
  65 | +
  66 |  def no_role_on_screen(m):
  67 |      """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
  68 |      opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
  69 | @@ -1024,17 +1043,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  70 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
  71 |      no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m)] if r}
  72 |      ms = [m for m in ms if m["moment_id"] not in no_role]
  73 | +    ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  74 | +    ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  75 |      wv, wf = _writers(router)
  76 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
  77 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  78 |      levels = current_levels(sources.values(), ctx)
  79 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
  80 | -           "no_role": no_role,
  81 | +           "no_role": no_role, "ad_read": ad_read,
  82 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
  83 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
  84 |             "package": None}
  85 |      log(f"  {n_usable} usable, {len(no_role)} of them left out (they open on a conjunction or reply fragment, which "
  86 | -        f"the render's STAND_ALONE fails with no clip scorer), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  87 | +        f"the render's STAND_ALONE fails with no clip scorer), {len(ad_read)} on an ad-read marker (the exclusion "
  88 | +        f"screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  89 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
  90 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
  91 |          return out
  92 | @@ -1402,6 +1424,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  93 |              if out["packages"] or out.get("budget_stop") or over_budget(ai):
  94 |                  break
  95 |      out["package"] = out["packages"][0] if out["packages"] else None
  96 | +    if out["package"] is None and not out.get("why_none"):       # every angle ended without a package: say why
  97 | +        out["why_none"] = ("no angle gave a package: " + "; ".join(
  98 | +            f"angle {t.get('angle')}: {str(t.get('why') or t.get('result') or 'no reason recorded')[:250]}"
  99 | +            for t in out["tried"])) if out["tried"] else "no angle gave a line-up to try"
 100 |      out["seconds"] = round(time.time() - t0, 1)
 101 |      out["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 102 |      return out
 103 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 104 | index c6316620..52608ab6 100644
 105 | --- a/tests/package/test_medley.py
 106 | +++ b/tests/package/test_medley.py
 107 | @@ -506,6 +506,8 @@ class TestBuildLoop(unittest.TestCase):
 108 |          self.assertIsNone(out["package"])
 109 |          self.assertEqual(rig.write_calls, [])
 110 |          self.assertIn("no through-line", out["tried"][0]["why"])
 111 | +        self.assertTrue(out["why_none"].startswith("no angle gave a package: angle 1: the clips alone have no "
 112 | +                                                   "through-line"), out["why_none"])     # never None (03:39 build)
 113 |  
 114 |      def test_a_weak_clip_alone_is_dropped_and_the_line_up_re_picked(self):
 115 |          rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
 116 | @@ -723,6 +725,55 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
 117 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 118 |  
 119 |  
 120 | +class TestAdReadBeforeTheAngle(unittest.TestCase):
 121 | +    """The exclusion screen's deterministic part (moments.ad_read_marker) runs before step A, so no angle is built
 122 | +    around a moment the package stage would refuse. The 03:39 build lost its line-up's hook to it after the write."""
 123 | +
 124 | +    def test_the_marker_in_the_moment_or_the_sentence_before_it(self):
 125 | +        import moments as M
 126 | +        self.assertEqual(M.ad_read_marker("Bitcoin is money.", "Use my code at checkout. Link in the description."),
 127 | +                         "ad-read marker 'Link in the description' in the sentence before it")
 128 | +        self.assertEqual(M.ad_read_marker("This episode is sponsored by a wallet. Bitcoin is money.", ""),
 129 | +                         "ad-read marker 'sponsored' in the moment")
 130 | +        self.assertIsNone(M.ad_read_marker("Bitcoin is money.", "Link in the description. Bitcoin rose today."))
 131 | +        self.assertIsNone(M.ad_read_marker("Bitcoin is money.", None))
 132 | +
 133 | +    def test_ad_read_out_reads_the_same_context_as_the_exclusion_screen(self):
 134 | +        import context_integrity as CI
 135 | +        ctxs = {"a": ("Grab it now. Link in the description.", "x"), "b": ("Bitcoin rose today.", "x"),
 136 | +                "c": (None, None)}
 137 | +        saved = CI.context_around
 138 | +        try:
 139 | +            CI.context_around = lambda src, *a: ctxs[src]
 140 | +            ms = [dict(pm(k, k.upper(), 12.0), sentences=[0, 0], words=[0, 1]) for k in ("a", "b", "c", "d")]
 141 | +            got = PK.ad_read_out(ms, {"va": "a", "vb": "b", "vc": "c"})       # d has no Source: left to the package
 142 | +        finally:
 143 | +            CI.context_around = saved
 144 | +        self.assertEqual(got, {"a": "ad-read marker 'Link in the description' in the sentence before it"})
 145 | +        try:                                     # DIFFERENTIAL (audit 0352 C1, glm): the package stage's own screen,
 146 | +            CI.context_around = lambda src, *a: ctxs[src]     # exclusion_for, on the same moments and context
 147 | +            never = type("R", (), {"call": lambda *a, **k: (_ for _ in ()).throw(AssertionError("no model call"))})()
 148 | +            for m in ms[:2]:
 149 | +                v = PK.exclusion_for(never, m, {"va": "a", "vb": "b"}, {}) if m["moment_id"] == "a" else None
 150 | +                if v is not None:
 151 | +                    self.assertEqual((v["verdict"], v["why"], v["backend"]), ("exclude", got["a"], "deterministic"))
 152 | +        finally:
 153 | +            CI.context_around = saved
 154 | +
 155 | +    def test_build_leaves_an_ad_read_moment_out_before_the_angle(self):
 156 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
 157 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 158 | +        saved = PK.ad_read_out
 159 | +        try:
 160 | +            PK.ad_read_out = lambda ms_, sources: {"q": "ad-read marker 'promo code' in the moment"}
 161 | +            out = rig.run()
 162 | +        finally:
 163 | +            PK.ad_read_out = saved
 164 | +        self.assertEqual(out["ad_read"], {"q": "ad-read marker 'promo code' in the moment"})
 165 | +        self.assertFalse(any("id=q " in p for role, p in rig.prompts if role == "angle_write"))
 166 | +        self.assertIsNotNone(out["package"])
 167 | +
 168 | +
 169 |  class TestNoVoiceRealGates(unittest.TestCase):
 170 |      """Audit 2240 C2 (glm N8): a no-voice package through the REAL VO-fidelity and context-integrity decisions (canned
 171 |      model replies, no stubbed gate): every required row, the medley rows included, exactly PASS, and the pin is
 172 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
package.build() turns moments into a sealed package, in this order:
1. usable();
2. the render's STAND_ALONE opener filter (no_role_on_screen);
3. step A (L-s context, a paid verdict per batch of 8 moments);
4. L-v 2 + CUTTABLE (a second recogniser per moment);
5. the hook onset;
6. the ANGLE step (one paid writer call proposes up to 3 angles, each a set of moments in play order);
7. per angle, line-ups, writes, and the per-clip gates. One of those gates is the exclusion screen: package.exclusion_for
   calls moments.exclusion_verdict on each segment's moment text and the context before it.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: the 03:39 ET build's angle 1, line-up 1 passed the clips-alone verdict, and its takeaway passed the cheap checks.
Then the exclusion screen's DETERMINISTIC part refused the HOOK ("ad-read marker 'link in the description' in the
sentence before it"). The angle was re-lined; no angle could form another line-up; the build ended with no package.
And its record said why_none = None ("no package (None)"), because no code path names the reason when every angle ends
without a package. Both are flagged defects (law K2: flag, do not silently delete).

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. This change must refuse exactly what the package
  stage already refuses, only EARLIER, and must not pass anything new.

The change:
1. pipeline/moments.py: ad_read_marker(moment_text, before_text) holds exclusion_verdict's deterministic screen (an
   AD_MARKERS match in the moment, or in the last sentence of the context before it) and returns the reason, else None.
   exclusion_verdict calls it, with the same return record as before. The model verdict after it is unchanged.
2. pipeline/package.py:
   - ad_read_out(ms, sources): for each moment, the SAME context exclusion_for reads (CI.context_around on the
     moment's Source, by source_key else video_id). A moment ad_read_marker refuses is recorded with its reason.
   - A moment with no Source (KeyError) or no context (None) is skipped here and left to the package stage, which
     refuses a moment without context (exclusion_for: "no context" -> exclude).
   - build() leaves those moments out right after the STAND_ALONE opener filter, before step A. They are recorded in
     out["ad_read"] and on the log line. out["usable"] is unchanged in meaning.
   - build(): when no package was made and nothing else set why_none, why_none names every tried angle's own why:
     "no angle gave a package: angle N: <why>; ...", or "no angle gave a line-up to try".
3. tests/package/test_medley.py:
   - the marker in the moment or the sentence before, and no marker earlier in the context;
   - ad_read_out reads the same context, and skips a moment with no Source or no context;
   - build() leaves an ad-read moment out of the angle prompt and still packages the rest;
   - why_none is named when every angle fails.

Check in particular:
- that ad_read_out refuses exactly what exclusion_verdict's deterministic part would refuse at the package stage, on
  the same text and the same context, and nothing more;
- that the exclusion verdict at the package stage is unchanged (its deterministic part and its model verdict);
- that a moment skipped here (no Source, no context) still cannot pass the package stage;
- that why_none never hides a reason another path already set.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".


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
