# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261118_0758
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 175 s finish=stop usage in 11687 / out 3313 usd_reported=0.000773 usd~0.085 (upper-bound price)

The code implements **RULING 146 (1) and (2)**, introducing a "Never-Empty" (soft) pass that allows specific visual and audio failures to pass provided they are flagged and the output is restricted to 16:9.

### Analysis against Governing Laws & Requirements

1.  **9:16 Protection (Ruling 146-1):**
    *   The `soft_graphics` function explicitly sets `m["visual"] = dict(v, formats=["16x9"], ...)`. 
    *   Because `package_pin.formats_of` (referenced in the logic) seals the package based on the most restrictive clip format, any package containing a "soft graphics" clip is forced to `["16x9"]`.
    *   The `vbad` (visual bad) check in `_build` (lines 68-69 and 78-79) specifically excludes clips where `soft and soft_graphics(m)` is True. Since these clips are marked `16x9` only, they can never appear in a 9:16 render.
    *   **Verdict:** Compliant.

2.  **Hard Failures (Third Person, Unmeasured, Mid-word):**
    *   **Third Person:** `visual_pin.graphics_only` returns `None` if `hook_block(rec)` is not None. Third persons are handled by `hook_block`, ensuring they stay HARD.
    *   **Unmeasured:** `visual_pin.graphics_only` requires `rec.get("measured") is True`. Unmeasured records stay HARD.
    *   **Mid-word Cuts:** In `_build` (line 46), the `ONSET_QUIET` regex specifically targets the "ms of genuine quiet... <" string. A mid-word cut (which would have a different `why` string) will not trigger `soft=True` and will remain a HARD failure.
    *   **Verdict:** Compliant.

3.  **Clean Pass Integrity:**
    *   All "soft" logic in `_build` is guarded by the `soft` boolean (passed by the orchestrator).
    *   The `_can_open` check (line 36) allows `on.get("soft") is True`, but `soft` is only assigned to the `hook_onset` record during the soft pass.
    *   **Verdict:** Compliant.

4.  **Inventory and Flagging:**
    *   The `inventory` function correctly adds the `FLAGGED` status and the required descriptive sentences for both `hook_onset` (abrupt start) and `graphics` (ticker/bug/etc. in 16:9).
    *   `package_pin.SOFT_GATES` is updated to include these, ensuring they do not block the final pin.
    *   **Verdict:** Compliant.

5.  **Test Coverage:**
    *   `TestRuling146` covers the critical edge cases:
        *   `test_the_shows_own_graphics_and_what_stays_hard`: Validates that third persons, old versions, and unmeasured records are rejected.
        *   `test_a_clip_with_the_shows_ticker_seals_16x9_only_flagged`: Validates the end-to-end flow of a ticker forcing 16:9 and the correct flag string.
        *   `test_a_hook_with_a_quiet_shortfall_opens_flagged`: Validates G17a soft pass.
        *   `test_an_unmeasured_or_other_onset_failure_stays_hard`: Validates that mid-word cuts are still HARD.
    *   **Verdict:** Comprehensive.

### Final Review
The implementation is precise. It correctly distinguishes between a "measured shortfall" (which is acceptable in a desperate "never-empty" scenario) and a "structural failure" (mid-word cut or third person), while ensuring that visual artifacts that would be cropped in 9:16 are only permitted in 16:9.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 733 s finish=stop usage in 11087 / out 18026 usd_reported=0.013368 usd~0.304 (upper-bound price)



# Code Audit — RULING 146 (1) + (2), `pp-selectid` branch

## Scope confirmed

The diff implements two soft-pass relaxations, active **only** in the never-empty pass (`soft=True`):

1. **RULING 146 (1):** A clip whose *sole* visual refusal is the source's own burned-in graphics (ticker, crawl, lower-third, channel bug) is unblocked and the package is sealed 16:9-only, flagged per-clip.
2. **RULING 146 (2):** A hook whose *sole* measured G17a failure is a quiet-before-onset shortfall (matching the specific `why` string) is marked `soft: True` and allowed to open, flagged "The opening clip may start abruptly."

Both are added to `SOFT_GATES` so the pin mechanism treats them as review flags, not hard stops.

---

## Answers to the four requested checks

**(1) Can a 9:16 version ever carry a clip whose burned text our crop cuts?**
**No.** `soft_graphics` overwrites `m["visual"]["formats"]` to `["16x9"]`. `package_pin.formats_of` then seals the *entire* package 16:9-only (same mechanism as RULING 123's hook). No 9:16 render is produced. The `RENDER_16X9_ONLY` guard in `graphics_only` adds a second safety: if the render cannot pass a 16:9-only pin, `graphics_only` returns `None` and the clip stays hard.

**(2) Can a third person, an unmeasured record, or a mid-word cut pass?**
**No, all three stay HARD.**
- Third person: `graphics_only` returns `None` when `hook_block(rec) is not None` (RULING 70).
- Unmeasured / stale record: `graphics_only` requires `measured is True` and `version == VERSION`.
- Mid-word cut: `ONSET_QUIET` matches only the substring `"ms of genuine quiet before the hook's first onset <"`. A mid-word `why` (e.g. `"the cut lands inside a word"`) does not match, so `soft` is never set and `_can_open` rejects. The test `test_an_unmeasured_or_other_onset_failure_stays_hard` confirms both cases.

**(3) Is the clean pass unchanged?**
**Yes.** Every new code path is gated by `soft` (the never-empty flag): `for m in (cleared.values() if soft else ())`, `for m in (rated_open if soft else ())`, `and not (soft and soft_graphics(m))`, and the inventory FLAGGED rows use `if soft and …`. With `soft=False` (clean pass) none of the new logic executes. The test `test_a_clip_with_the_shows_ticker_seals_16x9_only_flagged` asserts `clean["package"] is None` for the ticker case, confirming the clean pass still rejects.

**(4) Are the tests adequate?**
The four tests cover: unit-level `graphics_only` / `soft_graphics` (including third-person, unmeasured, stale, empty, and no-graphics cases); end-to-end ticker → 16:9-only seal with exact flag text; end-to-end quiet-shortfall → flagged open; and the two hard-stay cases (unmeasured, mid-word). The clean-pass non-regression is asserted in the same end-to-end tests. Coverage is solid for the stated scope.

---

## Findings

### [P2] `ONSET_QUIET` regex is coupled to a specific English sentence in the `why` field

```python
ONSET_QUIET = re.compile(r"ms of genuine quiet before the hook's first onset <")
```

This matches a *prose* substring produced by the onset-measurement code. If that code's wording changes (e.g. "70ms" without a space, "quiet before the hook's first onset is below", or a different unit), the regex silently stops matching and the soft pass is never triggered. The failure mode is **fail-closed** (the onset stays HARD, the package is not produced), so there is no safety risk, but the RULING 146 (2) feature would silently stop working with no error or log.

**Recommendation:** Either (a) have the onset-measurement code set a structured field (e.g. `h["failure_kind"] = "quiet_shortfall"`) and match on that, or (b) add a unit test that asserts the *actual* `why` string produced by `sentence_law.edge_plan` / `head_tail` matches `ONSET_QUIET`, so a wording change breaks the test rather than silently disabling the feature.

### [P2] `soft_graphics` mutates the moment's visual record inside a dict-comprehension filter

```python
vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order
        if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))
        and not (soft and soft_graphics(m))}
```

`soft_graphics(m)` reassigns `m["visual"]` to a new dict with `formats=["16x9"]`. This is a **side effect in a filter predicate**, evaluated in two separate dict comprehensions (main line-up ≈ L3869, no-voice order ≈ L4178). The mutation is intentional and idempotent (the second call reads the cached `graphics_16x9`), but:

- A reader scanning the filter sees a pure predicate; the mutation is only discoverable by reading `soft_graphics`'s body.
- If a future refactor moves the `vbad` computation or adds a third call site, the mutation's visibility and ordering become harder to reason about.

**Recommendation:** Extract the mutation into a separate loop before the `vbad` comprehension, or at minimum add 

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261118_0758, ruling 146 (1) + (2))

SEATS ANSWERED: 2 of 3. qwen3.8-27b and gemma-4-31b-it: P0/P1 none. gpt-oss-20b: out of tokens, no answer. Suites:
dev59 42 files / 933 tests, exit 0. Mutations 7 of 8 (F7 equivalent: gate_problems checks only required rows).

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261118_0758/C2_STEP.diff (233 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5bd269c..c962a66 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1764,6 +1764,24 @@ def hook_own(m):
   6 |                  rule=HOOK_OWN_RULE, **({"flagged": flag} if flag else {}))
   7 |  
   8 |  
   9 | +GRAPHIC_WORDS = {"ticker": "ticker", "crawl": "crawl", "lower_third": "lower third", "bug": "channel bug"}
  10 | +ONSET_QUIET = re.compile(r"ms of genuine quiet before the hook's first onset <")   # RULING 146 (2): G17a's shortfall
  11 | +
  12 | +
  13 | +def soft_graphics(m):
  14 | +    """RULING 146 (1), the never-empty pass: a clip whose ONLY visual refusal is the source's own on-screen graphics
  15 | +    (VP.graphics_only) plays in a package sealed 16:9 only, where nothing is cut: its visual record (this pass's copy)
  16 | +    is marked formats ['16x9'] (package_pin.formats_of then seals the package 16:9 only) and "graphics_16x9" (its
  17 | +    flag's words). -> True when it is. OUR 9:16 crop cutting burned text or a face stays HARD: no 9:16 version."""
  18 | +    import visual_pin as VP
  19 | +    v = m.get("visual") or {}
  20 | +    kinds = v.get("graphics_16x9") or VP.graphics_only(v)
  21 | +    if not kinds:
  22 | +        return False
  23 | +    m["visual"] = dict(v, formats=["16x9"], graphics_16x9=kinds)
  24 | +    return True
  25 | +
  26 | +
  27 |  def opens_16x9(m):
  28 |      """RULING 123 (2): this moment opens a package sealed formats ['16x9']: the build found no hook for both formats
  29 |      and its own frames are refused only by ruling 93's 9:16 crop (visual_pin.crop_only), still so on its sealed record.
  30 | @@ -1810,7 +1828,8 @@ def _can_open(m, pending_verdict=False):
  31 |      opens = lambda: defer or SA.opener("hook", m.get("text") or "", *sc, moments=True)[0]
  32 |      hook = (m.get("eligibility") or {}).get("hook") or {}
  33 |      elig = hook.get("ok") or (set(hook.get("reasons") or []) == {"opener"} and opens())   # the ledger had no verdict
  34 | -    if not (elig and (m.get("hook_onset") or {}).get("pass") is True and opens()):
  35 | +    on = m.get("hook_onset") or {}                      # RULING 146 (2): a measured quiet shortfall the never-empty
  36 | +    if not (elig and (on.get("pass") is True or on.get("soft") is True) and opens()):   # pass marked "soft" opens
  37 |          return False
  38 |      if "hook_rating" not in m:
  39 |          return True                                      # not rated yet: judged as before ruling 59
  40 | @@ -3485,6 +3504,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  41 |      cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}     # hook lead decides only whether it
  42 |      # may OPEN the medley (hook_onset "pass", need_onset), never whether it may play as a clip (audit 0710 C1, qwen)
  43 |      out["prescreen"]["trim_cut"] = trim_cut
  44 | +    for m in (cleared.values() if soft else ()):          # RULING 146 (2): G17a's quiet before the hook's first word
  45 | +        h = m.get("hook_onset") or {}                      # is SOFT in the never-empty pass (measured shortfalls only;
  46 | +        if h.get("measured") is True and h.get("pass") is not True and ONSET_QUIET.search(str(h.get("why") or "")):
  47 | +            m["hook_onset"] = dict(h, soft=True)          # a cut mid-word or an unmeasured onset stays HARD)
  48 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
  49 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
  50 |      for m in cleared.values():                                           # a rating is this build's own (its
  51 | @@ -3524,6 +3547,11 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  52 |                  blocked.pop(m["moment_id"], None)
  53 |                  m["visual"] = dict(m["visual"], formats=["16x9"])                     # sealed: package_pin.formats
  54 |                  m["sixteen_nine_only"] = sixteen[m["moment_id"]] = why_c
  55 | +    for m in (rated_open if soft else ()):                # RULING 146 (1): a hook refused only by the show's own
  56 | +        if m.get("visual_hook_block") and soft_graphics(m):    # graphics opens a package sealed 16:9 only, flagged
  57 | +            m.pop("visual_hook_block", None)
  58 | +            blocked.pop(m["moment_id"], None)
  59 | +            m["sixteen_nine_only"] = sixteen[m["moment_id"]] = "the show's own on-screen graphics (ruling 146 (1))"
  60 |      out["visual"] = out_visual
  61 |      if rated_open:
  62 |          log(f"  visual (ruling 70): {len(rated_open)} hook(s) seen, {len(blocked)} may not open"
  63 | @@ -3841,7 +3869,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  64 |              return None
  65 |          see(order)                                        # RULING 70: the added clip is seen too
  66 |          vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
  67 | -                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}   # included, law L-m)
  68 | +                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))   # included, law L-m)
  69 | +                and not (soft and soft_graphics(m))}      # RULING 146 (1): the show's own graphics, 16:9 only
  70 |          if vbad:
  71 |              note["why_not"] = ("rulings 70 / 93: " + "; ".join(f"{k}: {v}" for k, v in vbad.items()))[:400]
  72 |              return None
  73 | @@ -4149,7 +4178,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  74 |                      vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  75 |                                  "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip
  76 |                              for m in segs if VP.layout_block(m.get("visual"))                  # (L-m included); the
  77 | -                            and not (m is segs[0] and opens_16x9(m))}      # cause named; ruling 123 (2): the 16:9-only
  78 | +                            and not (m is segs[0] and opens_16x9(m))       # cause named; ruling 123 (2): the 16:9-only
  79 | +                            and not (soft and soft_graphics(m))}           # RULING 146 (1): the show's own graphics
  80 |                      if vbad or segs[0].get("visual_hook_block"):                               # HOOK only
  81 |                          vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  82 |                          dropped |= set(vbad)
  83 | @@ -4628,8 +4658,18 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  84 |             if style is not None else {}),
  85 |          **({"hook_onset": dict(row(hook.get("pass") is True, "hook_onset.measure (sentence_law.edge_plan + head_tail "
  86 |                                     "on the source audio: G17a at the pin stage)", measured=hook.get("measured") is True),
  87 | -                               lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
  88 | -           if hook is not None else {}),
  89 | +                               lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"),
  90 | +                               **({"status": "FLAGGED", "flags": ["The opening clip may start abruptly."]}   # RULING
  91 | +                                  if soft and hook.get("soft") is True and hook.get("pass") is not True else {}))}   # 146
  92 | +           if hook is not None else {}),                                                                      # (2)
  93 | +        **({"graphics": {"status": "FLAGGED", "by": "visual_pin.graphics_only (ruling 146 (1)): the show's own "
  94 | +                                                    "on-screen graphics, whole in a package sealed 16:9 only",
  95 | +                         "replayed": False, "n": len(visual), "flags": [
  96 | +                             f"The clip ({(who or {}).get(lb) or 'its channel'}) shows the show's own "
  97 | +                             f"{' / '.join(GRAPHIC_WORDS.get(k, k.replace('_', ' ')) for k in v['graphics_16x9'])}; "
  98 | +                             f"this package is 16:9 only." for lb, v in zip(labels(len(visual)), visual)
  99 | +                             if (v or {}).get("graphics_16x9")]}}
 100 | +           if soft and visual and any((v or {}).get("graphics_16x9") for v in visual) else {}),
 101 |          **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
 102 |                                      "stage, moments=True: the render's clip scorer's verdicts as the integrator's "
 103 |                                      "service gave them, stand-alone only, the score alone (rulings 56, 60); without an "
 104 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 105 | index 34d7bce..0fe03dc 100644
 106 | --- a/pipeline/package_pin.py
 107 | +++ b/pipeline/package_pin.py
 108 | @@ -43,7 +43,10 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 109 |                          #   ratings and unbridged joins of a kept candidate (the through-line and every other L-y check
 110 |                          #   stay HARD; the takeaway's value rows are not soft)
 111 |                          "stand_alone",                     # RULING 141 (2): a clip's STAND_ALONE opener (the topic
 112 | -                        "pbx_exception"})                  # RULING 144: EXCEPTION_GATE, only on the one excepted pin
 113 | +                        "pbx_exception",                   # RULING 144: EXCEPTION_GATE, only on the one excepted pin
 114 | +                        "hook_onset",                      # RULING 146 (2): G17a's quiet shortfall (a cut mid-word stays
 115 | +                        #   HARD)
 116 | +                        "graphics"})                       # RULING 146 (1): the show's own graphics, 16:9 only
 117 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 118 |  REVIEW_FLAGS_MAX = 3
 119 |  EXCEPTION_GATE = "pbx_exception"   # RULING 144 (PBX 07:05 ET Nov 18): a named, logged exception to a HARD rule for ONE
 120 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
 121 | index 3153ca7..401f4c0 100644
 122 | --- a/pipeline/visual_pin.py
 123 | +++ b/pipeline/visual_pin.py
 124 | @@ -345,6 +345,18 @@ def crop_only(rec):
 125 |      return "; ".join(w for w in why if w)
 126 |  
 127 |  
 128 | +def graphics_only(rec):
 129 | +    """RULING 146 (1) (orchestrator 07:55 ET Nov 18): the kinds of the source's OWN on-screen graphics (ticker, crawl,
 130 | +    lower third, bug) when they are a measured, current record's ONLY refusal (ruling 93's burned_block), else None.
 131 | +    They are refused only because OUR 9:16 crop cuts them; a package sealed 16:9 only shows them whole, so there they
 132 | +    are SOFT. A third person (ruling 70), an unmeasured or older record, or a render that cannot pass a 16:9-only pin:
 133 | +    None."""
 134 | +    if not ((rec or {}).get("measured") is True and rec.get("version") == VERSION and
 135 | +            isinstance(rec.get("burned_in"), list)) or hook_block(rec) is not None or not RENDER_16X9_ONLY:
 136 | +        return None
 137 | +    return sorted({x["kind"] for x in rec["burned_in"] if burned_block(x)}) or None
 138 | +
 139 | +
 140 |  def hook_block(rec):
 141 |      """Why this clip may not be the HOOK (ruling 70), or None."""
 142 |      if not (rec or {}).get("measured"):
 143 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 144 | index f2832ff..346acd4 100644
 145 | --- a/tests/package/test_ruling_137.py
 146 | +++ b/tests/package/test_ruling_137.py
 147 | @@ -631,6 +631,85 @@ class TestRuling144TheOneException(unittest.TestCase):
 148 |              PP.WINDOW_H = saved
 149 |  
 150 |  
 151 | +class TestRuling146(unittest.TestCase):
 152 | +    """RULING 146 (orchestrator 07:55 ET Nov 18), the never-empty pass: (1) the source's own on-screen graphics (a ticker,
 153 | +    a lower third, a bug) are SOFT in a package sealed 16:9 only, flagged in the ruling's words; (2) G17a's quiet before
 154 | +    the hook's first word is SOFT (a measured shortfall only), flagged 'The opening clip may start abruptly.'"""
 155 | +    TICKER = {"kind": "ticker", "text": "S&P 500 Nasdaq Bitcoin", "whole_in_16x9": True, "in_9x16": "cut",
 156 | +              "covers_speaker": False}
 157 | +    QUIET = "70 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame)"
 158 | +
 159 | +    def rec(self, **kw):
 160 | +        import visual_pin as VP
 161 | +        r = {"version": VP.VERSION, "measured": True, "flags": [], "burned_in": [dict(self.TICKER)],
 162 | +             "third_person": {"shown": False, "how": "none", "words_negative": False}}
 163 | +        return dict(r, **kw)
 164 | +
 165 | +    def test_the_shows_own_graphics_and_what_stays_hard(self):
 166 | +        import visual_pin as VP
 167 | +        self.assertEqual(VP.graphics_only(self.rec()), ["ticker"])
 168 | +        for bad in (self.rec(measured=False), self.rec(version="old"), self.rec(burned_in=None), self.rec(burned_in=[])):
 169 | +            self.assertIsNone(VP.graphics_only(bad))
 170 | +        with mock.patch.object(VP, "hook_block", lambda r: "a third person"):
 171 | +            self.assertIsNone(VP.graphics_only(self.rec()))              # ruling 70's third person: not graphics
 172 | +        m = {"moment_id": "x", "visual": self.rec()}
 173 | +        self.assertTrue(PK.soft_graphics(m))
 174 | +        self.assertEqual((m["visual"]["formats"], m["visual"]["graphics_16x9"]), (["16x9"], ["ticker"]))
 175 | +        self.assertFalse(PK.soft_graphics({"moment_id": "y", "visual": self.rec(burned_in=[])}))
 176 | +
 177 | +    def rig(self, ms, never_empty, **kw):
 178 | +        import test_medley as TM
 179 | +        r = TM.Rig(ms, [m["moment_id"] for m in ms], [(True, [], None, TM.Rig.LINE)], [None], **kw)
 180 | +        r.build_kw = {"never_empty": never_empty}
 181 | +        return r
 182 | +
 183 | +    def test_a_clip_with_the_shows_ticker_seals_16x9_only_flagged(self):
 184 | +        from test_moments import pm
 185 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 186 | +        import test_medley as TM
 187 | +        clean = self.rig(ms, False, visuals={"x": {"burned_in": [dict(self.TICKER)]}}).run()
 188 | +        self.assertIsNone(clean["package"])
 189 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 190 | +                   visuals={"x": {"burned_in": [dict(self.TICKER)]}},
 191 | +                   follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})   # the clean pass reached its line-up
 192 | +        r.build_kw = {"never_empty": True}
 193 | +        pk = r.run()["package"]
 194 | +        self.assertEqual(PP.formats_of(pk["segments"]), ["16x9"])
 195 | +        ch = next(s["channel"] for s in pk["segments"] if s["moment_id"] == "x")
 196 | +        self.assertEqual((pk["gates"]["graphics"]["status"], pk["gates"]["graphics"]["flags"]), (
 197 | +            "FLAGGED", [f"The clip ({ch}) shows the show's own ticker; this package is 16:9 only."]))
 198 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 199 | +
 200 | +    def test_a_hook_with_a_quiet_shortfall_opens_flagged(self):
 201 | +        from test_moments import pm
 202 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 203 | +        quiet = self.QUIET
 204 | +
 205 | +        def make(ne):
 206 | +            r = self.rig(ms, ne)
 207 | +            base = r.onset
 208 | +            r.onset = lambda m, *a, **k: ({"pass": False, "measured": True, "lead_ms": 70, "why": quiet}
 209 | +                                          if m["moment_id"] == "h" else base(m, *a, **k))
 210 | +            return r
 211 | +        self.assertIsNone(make(False).run()["package"])
 212 | +        pk = make(True).run()["package"]
 213 | +        self.assertEqual(pk["segments"][0]["moment_id"], "h")
 214 | +        self.assertEqual((pk["gates"]["hook_onset"]["status"], pk["gates"]["hook_onset"]["flags"]),
 215 | +                         ("FLAGGED", ["The opening clip may start abruptly."]))
 216 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 217 | +
 218 | +    def test_an_unmeasured_or_other_onset_failure_stays_hard(self):
 219 | +        from test_moments import pm
 220 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 221 | +        for rec in ({"pass": False, "measured": False, "why": "not measured"},
 222 | +                    {"pass": False, "measured": True, "why": "the cut lands inside a word"}):
 223 | +            r = self.rig(ms, True)
 224 | +            base = r.onset
 225 | +            r.onset = lambda m, *a, _rec=rec, **k: dict(_rec) if m["moment_id"] == "h" else base(m, *a, **k)
 226 | +            out = r.run()
 227 | +            self.assertTrue(out["package"] is None or out["package"]["segments"][0]["moment_id"] != "h", rec)
 228 | +
 229 | +
 230 |  class TestTheDayCount(unittest.TestCase):
 231 |      def test_counted_per_day_ledger(self):
 232 |          with tempfile.TemporaryDirectory() as d:
 233 | 
```

---

pp-selectid: RULING 146 (1) + (2) (orchestrator 07:55 ET Nov 18), in the NEVER-EMPTY pass only (package.build runs it
only when the clean pass sealed nothing). The approved HARD list keeps: OUR crop cutting burned text or a face, a cut
mid-word. RULED SOFT: (1) the source's OWN on-screen graphics (a ticker crawl, a 'LIVE' lower third, a channel bug) in a
package sealed 16:9 ONLY, where nothing is cut ("Ruling 93's 'a ticker is never allowed' is withdrawn for 16:9-only
packages; in 9:16 the crop rule stands"), flag "The clip (X) shows the show's own ticker / lower third; this package is
16:9 only."; (2) G17a, the quiet before the hook's first word, flag "The opening clip may start abruptly." The
integrator's render re-asks neither the ticker nor the lower third (vertical_layout's 9:16 crop only; a pin sealed
formats ['16x9'] renders and releases 16:9 only, release_auth.release_formats). It holds G17a HARD in its lock / cut
table and is making those flags (its own lockstep); its render pads room tone, so its check is the more lenient and
decides through the build's own lock pre-check. Files: pipeline/visual_pin.py, pipeline/package.py,
pipeline/package_pin.py, tests/package/test_ruling_137.py.

THE CHANGE:
(a) visual_pin.graphics_only(rec): the kinds of the burned items burned_block refuses, when a measured, current record has
    no third person (ruling 70's hook_block) and the render can pass a 16:9-only pin; else None.
(b) package.soft_graphics(m): marks the pass's own copy of the clip's visual record formats ['16x9'] (package_pin.
    formats_of then seals the WHOLE package 16:9 only, as ruling 123's hook already did) and graphics_16x9. It is used
    only when soft: at the hook stage (a hook refused only by the graphics opens), and in both clip refusals (vbad, the
    main line-up and the no-voice order). Our 9:16 crop is never made: no 9:16 version exists.
(c) G17a: in the soft pass, a hook_onset record MEASURED and failed by the quiet shortfall (its why matches "ms of genuine
    quiet before the hook's first onset <") becomes {..., soft: True}; _can_open accepts pass OR soft. Unmeasured, or any
    other failure (a cut mid-word), stays HARD.
(d) inventory: hook_onset row FLAGGED with the ruling's sentence when soft and the hook is soft; a new optional "graphics"
    row FLAGGED, one sentence per such clip with its channel. package_pin.SOFT_GATES adds hook_onset and graphics.

TESTS (4): graphics_only and soft_graphics (a third person, unmeasured, older, empty stay hard); END TO END through the
Rig: a clip whose only problem is the show's ticker seals 16:9 only with the exact sentence (the clean pass seals
nothing); a hook with a 70 ms quiet shortfall opens flagged (the clean pass seals nothing); an unmeasured or other onset
failure never opens. Mutations: 7 of 8 killed (F7, "graphics" in SOFT_GATES, is equivalent: gate_problems checks only
required rows and graphics is optional).

PLEASE CHECK: (1) can a 9:16 version ever carry a clip whose burned text our crop cuts? (2) can a third person, an
unmeasured record or a mid-word cut pass? (3) the clean pass unchanged; (4) the tests.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
