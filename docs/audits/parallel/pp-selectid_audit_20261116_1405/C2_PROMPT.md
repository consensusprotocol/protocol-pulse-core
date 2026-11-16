# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1405
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 438 s finish=stop usage in 9322 / out 4812 usd_reported=0.000886 usd~0.100 (upper-bound price)

The code implements RULING 123 (2) to allow a hook to open a package as 16:9-only if its only refusal is the 9:16 crop. However, there is a critical logic contradiction between the selection seal and the validation check.

### [P0] Logic Contradiction: Seal Disables Exception
The feature is designed to seal a package as 16:9-only and then excuse that hook from the final layout block. However, the implementation of the excuse is disabled by the seal itself.

1.  **The Seal**: In `pipeline/package.py` (line 32), when a 16:9-only hook is identified, the code seals the record: `m["visual"] = dict(m["visual"], formats=["16x9"])`.
2.  **The Excuse**: Later in `build()`, the layout check (lines 54 and 64) calls `opens_16x9(m)` to determine if the hook should be excused from Ruling 93.
3.  **The Failure**: `opens_16x9(m)` (line 15) requires `bool(VP.crop_only(v))` to be `True`.
4.  **The Block**: In `pipeline/visual_pin.py` (line 84), `crop_only(rec)` explicitly returns `None` if the record already has formats assigned: `if ... or (formats(rec) and not RENDER_16X9_ONLY): return None`.

**Result**: Because the record is sealed with `formats=["16x9"]` at line 32, `VP.crop_only` will always return `None` during the final layout check. This makes `opens_16x9` return `False`, which causes the layout check to see the Ruling 93 refusal and return `None` for the entire `build()` call. The feature will not work; any package attempting to use a 16:9-only hook will fail the final quality gate and produce no output.

### [P2] Redundant Check in `opens_16x9`
In `pipeline/package.py` (line 15), `opens_16x9` checks `v.get("formats") == ["16x9"]`. This is redundant because the `sixteen_nine_only` flag is only set in `build()` at the exact same time the `formats` list is set to `["16x9"]`. While not a bug, it adds unnecessary complexity to a critical path.

### [P3] Test Coverage Gap
The tests in `tests/package/test_medley.py` may pass if the `Rig` mock does not fully execute the final `vbad` layout check in `package.build()` or if it uses a different version of `visual_pin.py`. The test `test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only` should be verified against the actual `pipeline/package.py` logic to ensure it catches the [P0] failure.

P1_OR_WORSE: 1

## MIMO-V2.6-FLASH-RL — CYCLE 1 OUTPUT
# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 418 s finish=stop usage in 8688 / out 30570 usd_reported=0.003031 usd~0.485 (upper-bound price)

# Code Audit: pp-selectid — RULING 123 (2) A 16:9-Only Hook

## Review of the Four Requested Checks

**(1) Exception fires only when no both-format hook exists** — The guard `if rated_open and not [m for m in rated_open if not m.get("visual_hook_block")]` correctly requires that *every* rated opener carries a `visual_hook_block`. If any rated opener lacks one (i.e., a both-format hook exists), the list comprehension is non-empty, `not [...]` is `False`, and the exception block is skipped entirely. ✅ Correct.

**(2) Only the hook is excused, and only for the 9:16 crop** — Both per-segment layout checks gate the skip on `m is order[0]` / `m is segs[0]` **and** `opens_16x9(m)`. `opens_16x9` requires the `sixteen_nine_only` flag, `formats == ["16x9"]`, and `crop_only` still naming the record — so only the first segment (the hook) and only for ruling 93's crop are excused. As a clip, `opens_16x9` is never consulted for non-first segments. ✅ Correct.

**(3) The seal says 16:9 only** — `m["visual"] = dict(m["visual"], formats=["16x9"])` writes the sealed formats; the test asserts `package_pin.formats_of(...) == ["16x9"]`. ✅ Correct.

**(4) The tests** — Four tests cover: crop_only qualification (ticker / covers_speaker / whole_in_16x9=False / nothing refused / older version / unmeasured / third-person all return None), the happy path (package built, sealed 16:9), a both-format hook winning (exception doesn't fire), and the moment refused as a clip. Coverage is solid. ✅ Correct.

---

## Findings

**[P2] `crop_only` guard may return `None` after the record is sealed, breaking `opens_16x9` in the per-segment checks.**
`crop_only` contains the guard `(formats(rec) and not RENDER_16X9_ONLY)`. The build sequence is:
1. `build()` calls `crop_only` on the **unsealed** record → returns truthy → unblocks and seals with `formats=["16x9"]`.
2. Later, the per-segment layout check calls `opens_16x9(m)` → which calls `crop_only(v)` on the **now-sealed** record.

If `formats(rec)` reads `rec.get("formats")` (returning `["16x9"]`, truthy) and `RENDER_16X9_ONLY` is `False` (the normal both-format render mode), the guard fires and `crop_only` returns `None`. `opens_16x9` then returns `False`, the per-segment check does **not** skip ruling 93 for the hook, and the package is rejected — the exact opposite of the ruling's intent.

The test `test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only` asserts `assertIsNotNone(out["package"])`, which would catch this if the guard fires. So either the guard does not fire (because `formats()` returns falsy for `["16x9"]`, or `RENDER_16X9_ONLY` is `True` in this context), or the test fails. Since neither `formats()` nor `RENDER_16X9_ONLY` is visible in this diff, the interaction cannot be confirmed safe. **Recommend explicitly verifying that `crop_only` still returns truthy on a sealed `formats=["16x9"]` record**, or restructuring `opens_16x9` to not re-call `crop_only` after sealing (e.g., cache the crop_only result alongside `sixteen_nine_only`).

**[P3] Redundant local import in `opens_16x9`.**
`import visual_pin as VP` inside `opens_16x9` is unnecessary — `VP` is already used unqualified throughout `build()` (lines 28, 52 of the diff), confirming it is imported at module scope. The local import shadows the module-level name for no benefit.

---

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 85 s finish=stop usage in 8853 / out 7052 usd_reported=0.005440 usd~0.132 (upper-bound price)

I will analyze the provided code diff against the "Governing Laws" and the specific "RULING 123 (2)" requirements.

### Context Analysis
The feature implements **RULING 123 (2)**: If no hook passes for both 16:9 and 9:16 formats, a hook that is *only* refused because the 9:16 crop would cut a lower-third/bug (Ruling 93 violation) may open a package sealed as `["16x9"]` only. This hook is exempted from the 9:16 layout check *only* when it is the first segment (the hook). As a clip, it remains blocked.

### Code Review

**1. `pipeline/visual_pin.py` - `crop_only(rec)`**
*   **Logic**: Checks if `rec` is measured, current version, and has no `hook_block` (Ruling 70). It iterates `burned_in` items. It identifies items that cause a block (`burned_block`). It verifies that *all* blocking items are:
    *   Kind in `RUNNING` (lower third/bug) or `CAPTION`? Wait, the docstring says "lower third or bug". The code checks `x["kind"] in RUNNING`. Let's assume `RUNNING` contains lower thirds/bugs.
    *   `whole_in_16x9` is True.
    *   `in_9x16` is "cut".
    *   `covers_speaker` is False.
*   **Potential Issue**: The code returns `None` if `formats(rec) and not RENDER_16X9_ONLY`. This seems to be a guard against records that are already explicitly formatted for 16:9 only? Or perhaps it's checking if the record *claims* to be 16:9 only already? The logic `if ... (formats(rec) and not RENDER_16X9_ONLY): return None` is slightly ambiguous without seeing `RENDER_16X9_ONLY` definition, but likely ensures we don't double-process or apply this to records that are already restricted.
*   **Law Compliance**:
    *   **SENTENCE LAW**: Not directly applicable to visual pins, but the hook selection relies on valid clips.
    *   **LAW 20 / M2**: Thresholds are constants. The logic is deterministic.
    *   **M12 FAIL CLOSED**: If `rec` is not measured or version mismatch, it returns `None` (fails closed, i.e., doesn't qualify for the exception).

**2. `pipeline/package.py` - `build()`**
*   **Logic**:
    ```python
    sixteen = {}
    if rated_open and not [m for m in rated_open if not m.get("visual_hook_block")]:
        # Condition: There are rated openers, AND NONE of them are unblocked (i.e., all are blocked).
        for m in rated_open:
            why_c = VP.crop_only(m.get("visual"))
            if why_c:
                m.pop("visual_hook_block", None)
                blocked.pop(m["moment_id"], None)
                m["visual"] = dict(m["visual"], formats=["16x9"])
                m["sixteen_nine_only"] = sixteen[m["moment_id"]] = why_c
    ```
*   **Critical Check 1: "Exception fires only when no both-format hook exists"**:
    The condition `not [m for m in rated_open if not m.get("visual_hook_block")]` translates to: "There is no moment in `rated_open` that does *not* have a `visual_hook_block`." In other words, *every* moment in `rated_open` has a `visual_hook_block`.
    *   If a hook passes for both formats, it would *not* have `visual_hook_block` (or it would be cleared earlier).
    *   If a hook is blocked by Ruling 70 (third person), it has `visual_hook_block`. `crop_only` returns `None` for these (because `hook_block(rec) is not None`). So they won't be unblocked.
    *   If a hook is blocked by Ruling 93 (crop), it has `visual_hook_block`. `crop_only` returns the reason. It *will* be unblocked.
    *   **Scenario**: What if there are two hooks? Hook A is blocked by Ruling 70. Hook B is blocked by Ruling 93.
        *   `rated_open` contains A and B.
        *   Both have `visual_hook_block`.
        *   The condition `not [m for m in rated_open if not m.get("visual_hook_block")]` is True (list is empty).
        *   Loop runs.
        *   A: `crop_only` returns `None` (Ruling 70). A remains blocked.
        *   B: `crop_only` returns reason. B is unblocked, marked `sixteen_nine_only`.
        *   Result: B becomes the hook.
        *   **Is this correct?** The order says: "when no hook passes for both formats... a hook whose only refusal is ruling 93's 9:16 crop may open".
        *   If Hook A was blocked by Ruling 70, it does *not* pass for both formats (it fails the "third person" check which applies to both). Hook B fails 9:16 crop. So *no* hook passes for both formats. The exception should apply to B.
        *   **However**, what if Hook A was blocked by *something else* that isn't Ruling 70 or 93? `crop_only` handles specific cases.
        *   **What if there is a hook that passes both formats?**
            *   If Hook C passes both, it does *not* have `visual_hook_block`.
            *   The list `[m for m in rated_open if not m.get("visual_hook_block")]` would contain C.
            *   The condition `not [...]` would be False.
            *   The exception block is skipped.
            *   Hook C remains the valid hook.
            *   **This satisfies "A both-format h

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_1405 (RULING 123 (2): a 16:9-only hook)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: mimo 0,
gemma 1 (a P0), qwen 1. Cycle 1 $0.0094 of Heimdall, not capped.

gemma's P0 ("the seal disables the exception: crop_only returns None once the record has formats assigned"): NOT SO.
visual_pin.formats(rec) (visual_pin.py:268, unchanged) never reads the record's "formats" key: it answers ["16x9"] only
for a burned CAPTION the 9:16 crop cuts (rec["burned_in"] items of kind "caption"); and RENDER_16X9_ONLY is True
(visual_pin.py:48: the integrator's format-aware release landed, c396c3c8). Sealing formats ["16x9"] on the hook's
record therefore changes nothing crop_only reads. The tests run the real build through the final per-segment check:
test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only gets a PACKAGE whose segment 0 is the 16:9-only hook
(the line-up check excused it), and mutations W2 / W4 die on exactly that path (gemma's P3 answered).
qwen's P1 ("with RENDER_16X9_ONLY False, crop_only returns None"): that is the intent, and it is now said directly:
CHANGED (in cycle 2's diff) the guard to "not RENDER_16X9_ONLY": the exception makes a 16:9-only pin, so it fires only
when the render can pass one; equal today (the flag is True), stricter if it ever is not.
gemma's P2 (opens_16x9 also checks the record's formats): kept on purpose: the excuse holds only while the sealed record
still says 16:9 only (a record seen again without it is not excused).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_1405/C2_STEP.diff (166 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 52c1dfe..038c3c9 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1552,6 +1552,15 @@ def hook_own(m):
   6 |                  rule=HOOK_OWN_RULE)
   7 |  
   8 |  
   9 | +def opens_16x9(m):
  10 | +    """RULING 123 (2): this moment opens a package sealed formats ['16x9']: the build found no hook for both formats
  11 | +    and its own frames are refused only by ruling 93's 9:16 crop (visual_pin.crop_only), still so on its sealed record.
  12 | +    Only as the HOOK: as a clip its ruling-93 refusal stands."""
  13 | +    import visual_pin as VP
  14 | +    v = m.get("visual") or {}
  15 | +    return bool(m.get("sixteen_nine_only")) and v.get("formats") == ["16x9"] and bool(VP.crop_only(v))
  16 | +
  17 | +
  18 |  def can_open(m):
  19 |      if m.get("visual_hook_block"):                       # RULING 70: its picture may not open the medley
  20 |          return False
  21 | @@ -3088,6 +3097,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  22 |          #   ruling 93: its own frames, per clip; both reasons when both hold (audit 0003 C1, glm)
  23 |          if why_v:
  24 |              m["visual_hook_block"] = blocked[m["moment_id"]] = why_v
  25 | +    sixteen = {}
  26 | +    if rated_open and not [m for m in rated_open if not m.get("visual_hook_block")]:   # RULING 123 (2): no hook opens
  27 | +        for m in rated_open:                                                          # both formats: one refused ONLY
  28 | +            why_c = VP.crop_only(m.get("visual"))                                     # by ruling 93's 9:16 crop opens
  29 | +            if why_c:                                                                 # a package sealed 16:9 only
  30 | +                m.pop("visual_hook_block", None)
  31 | +                blocked.pop(m["moment_id"], None)
  32 | +                m["visual"] = dict(m["visual"], formats=["16x9"])                     # sealed: package_pin.formats
  33 | +                m["sixteen_nine_only"] = sixteen[m["moment_id"]] = why_c
  34 |      out["visual"] = out_visual
  35 |      if rated_open:
  36 |          log(f"  visual (ruling 70): {len(rated_open)} hook(s) seen, {len(blocked)} may not open"
  37 | @@ -3101,7 +3119,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  38 |                          "bar_invalid": live_why,
  39 |                          "ratings": {mid: rated[mid] for mid in sorted(rated)}, "best": best,
  40 |                          "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])],
  41 | -                        "visual_blocked": blocked}
  42 | +                        "visual_blocked": blocked,
  43 | +                        **({"sixteen_nine_only": {"hooks": sixteen, "note": "no hook passes for both formats: a hook "
  44 | +                            "refused only by ruling 93's 9:16 crop opens a package sealed formats ['16x9'] (ruling "
  45 | +                            "123 (2))"}} if sixteen else {})}
  46 |      log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} pass "
  47 |          f"{HB.text(live)}" + (f" [{live_why}]" if live_why else "") + (f"; NOT RATED: {hook_err}" if hook_err else "")
  48 |          + f" ({time.time() - t0:.0f} s)")
  49 | @@ -3386,7 +3407,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  50 |                                    if value is not None else {})}}
  51 |          see(order)                                        # RULING 70: the added clip is seen too
  52 |          vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
  53 | -                if VP.layout_block(m.get("visual"))}                                 # included, law L-m)
  54 | +                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}   # included, law L-m)
  55 |          if vbad:
  56 |              note["why_not"] = ("rulings 70 / 93: " + "; ".join(f"{k}: {v}" for k, v in vbad.items()))[:400]
  57 |              return None
  58 | @@ -3652,7 +3673,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  59 |                  see(segs)                                   # RULING 70: every clip seen before any write is paid
  60 |                  vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  61 |                              "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip (L-m
  62 | -                        for m in segs if VP.layout_block(m.get("visual"))}                 # included); the cause named
  63 | +                        for m in segs if VP.layout_block(m.get("visual"))                  # included); the cause named
  64 | +                        and not (m is segs[0] and opens_16x9(m))}          # ruling 123 (2): the 16:9-only HOOK only
  65 |                  if vbad or segs[0].get("visual_hook_block"):
  66 |                      vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  67 |                      dropped |= set(vbad)
  68 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
  69 | index a3d31e6..24ed7a1 100644
  70 | --- a/pipeline/visual_pin.py
  71 | +++ b/pipeline/visual_pin.py
  72 | @@ -309,6 +309,24 @@ def layout_block(rec):
  73 |      return (f"ruling 93 ({len(why)} item(s)): " + "; ".join(why))[:600] if why else None   # (audit 0003 C2)
  74 |  
  75 |  
  76 | +def crop_only(rec):
  77 | +    """RULING 123 (2) (orchestrator 14:05 ET Nov 16): the reason a measured record's ONLY refusal is ruling 93's 9:16 crop
  78 | +    (a lower third or bug wholly inside the 16:9, not over the speaker, that the 9:16 crop would cut through mid-word),
  79 | +    or None. Such a clip shows whole in 16:9: as a HOOK, when no hook passes for both formats, it may open a package
  80 | +    sealed formats ['16x9'] (package.build). A ticker or crawl, a part outside the 16:9, a speaker covered, a third
  81 | +    person (ruling 70) or an unmeasured or older record: None."""
  82 | +    if not ((rec or {}).get("measured") is True and rec.get("version") == VERSION and
  83 | +            isinstance(rec.get("burned_in"), list)) or hook_block(rec) is not None or \
  84 | +            not RENDER_16X9_ONLY:                # the exception makes a 16:9-only pin: only when the render can pass one
  85 | +        return None
  86 | +    why = [burned_block(x) for x in rec["burned_in"]]
  87 | +    cut = [x for x, w in zip(rec["burned_in"], why) if w]
  88 | +    if not cut or any(x["kind"] in RUNNING or x["kind"] == CAPTION or not x["whole_in_16x9"] or x["in_9x16"] != "cut"
  89 | +                      or x["covers_speaker"] for x in cut):
  90 | +        return None
  91 | +    return "; ".join(w for w in why if w)
  92 | +
  93 | +
  94 |  def hook_block(rec):
  95 |      """Why this clip may not be the HOOK (ruling 70), or None."""
  96 |      if not (rec or {}).get("measured"):
  97 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  98 | index 4e1f1b8..c7d52b5 100644
  99 | --- a/tests/package/test_medley.py
 100 | +++ b/tests/package/test_medley.py
 101 | @@ -4672,5 +4672,64 @@ class TestRuling118StoryFirst(unittest.TestCase):
 102 |              PK.load_candidate(rec)
 103 |  
 104 |  
 105 | +class TestRuling123SixteenNineHook(unittest.TestCase):
 106 | +    """RULING 123 (2) (orchestrator 14:05 ET Nov 16): when no hook passes for both formats, a hook whose ONLY refusal is
 107 | +    ruling 93's 9:16 crop (a lower third the crop would cut mid-word) opens a package sealed formats ['16x9']; a
 108 | +    both-format hook always wins; as a clip its refusal stands."""
 109 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 110 | +    CUT = {"burned_in": [{"kind": "lower_third", "text": "IN THIS EPISODE...", "whole_in_16x9": True, "in_9x16": "cut",
 111 | +                          "covers_speaker": False}]}
 112 | +
 113 | +    def rec(self, **kw):
 114 | +        base = {"version": VP.VERSION, "measured": True, "flags": [], "burned_in": self.CUT["burned_in"]}
 115 | +        return dict(base, **kw)
 116 | +
 117 | +    def test_only_a_crop_refusal_qualifies(self):
 118 | +        lt = self.CUT["burned_in"][0]
 119 | +        self.assertTrue(VP.crop_only(self.rec()).startswith("a lower_third the 9:16 crop would cut through mid-word"))
 120 | +        for bad in (dict(lt, kind="ticker"), dict(lt, covers_speaker=True), dict(lt, whole_in_16x9=False)):
 121 | +            self.assertIsNone(VP.crop_only(self.rec(burned_in=[bad])), bad)
 122 | +        self.assertIsNone(VP.crop_only(self.rec(burned_in=[dict(lt, in_9x16="whole")])))    # nothing refused at all
 123 | +        self.assertIsNone(VP.crop_only(self.rec(version="visual-2")))
 124 | +        self.assertIsNone(VP.crop_only(self.rec(measured=False)))
 125 | +        tp = {"kind": "third_person", "text": "a still of a CEO", "why": "w"}
 126 | +        self.assertIsNone(VP.crop_only(self.rec(flags=[tp])))                                # ruling 70 still refuses
 127 | +
 128 | +    def test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only(self):
 129 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"h": self.CUT}).run()
 130 | +        self.assertIn("h", out["hook_pool"]["sixteen_nine_only"]["hooks"])
 131 | +        self.assertEqual(out["hook_pool"]["passing"], ["h"])
 132 | +        self.assertIsNotNone(out["package"])
 133 | +        self.assertEqual(out["package"]["segments"][0]["moment_id"], "h")
 134 | +        import package_pin
 135 | +        self.assertEqual(package_pin.formats_of(out["package"]["segments"]), ["16x9"])        # sealed 16:9 only
 136 | +
 137 | +    def test_a_both_format_hook_always_wins(self):
 138 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"h": self.CUT},
 139 | +                  hooks={"x": (5, 5, 5)}).run()
 140 | +        self.assertNotIn("sixteen_nine_only", out["hook_pool"])
 141 | +        self.assertEqual(out["hook_pool"]["passing"], ["x"])
 142 | +        self.assertIn("h", out["hook_pool"]["visual_blocked"])
 143 | +
 144 | +    def test_a_second_16x9_only_opener_is_still_refused_as_a_clip(self):
 145 | +        """Two hooks refused only by the crop and none for both formats: both may open, but in a line-up the one that
 146 | +        plays as a CLIP keeps its ruling-93 refusal (only the hook is excused)."""
 147 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)] * 4, [None, None],
 148 | +                  visuals={"h": self.CUT, "x": self.CUT}, hooks={"x": (5, 5, 5)})
 149 | +        out = rig.run()
 150 | +        self.assertEqual(set(out["hook_pool"]["sixteen_nine_only"]["hooks"]), {"h", "x"})
 151 | +        self.assertTrue(any("x: ruling 93" in (r.get("why") or "") for r in out["tried"]), out["tried"])
 152 | +        for lu in rig.write_calls:                                    # nothing is written for a line-up with x as a clip
 153 | +            self.assertNotIn("x", lu[0][1:])
 154 | +        self.assertTrue(out["package"] is None or "x" not in [s["moment_id"] for s in out["package"]["segments"][1:]])
 155 | +
 156 | +    def test_as_a_clip_its_refusal_stands(self):
 157 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)] * 3, [None, None],
 158 | +                  visuals={"y": self.CUT}).run()
 159 | +        self.assertNotIn("sixteen_nine_only", out["hook_pool"])
 160 | +        self.assertTrue(out["package"] is None or "y" not in [s["moment_id"] for s in out["package"]["segments"]])
 161 | +        self.assertTrue(any("y: ruling 93" in (r.get("why") or "") for r in out["tried"]), out["tried"])
 162 | +
 163 | +
 164 |  if __name__ == "__main__":
 165 |      unittest.main()
 166 | 
```

---

pp-selectid: RULING 123 (2) (orchestrator 14:05 ET Nov 16), A 16:9-ONLY HOOK. Files: pipeline/visual_pin.py (crop_only),
pipeline/package.py (the hook pool's exception; opens_16x9; the two per-segment layout checks), tests/package/test_medley.py.

THE ORDER, verbatim: "(2) THE HOOK YOU ALREADY HAVE: What Bitcoin Did 44a6d503 passes the calibrated bar and is refused as
an opener only because the 9:16 crop would cut a lower third. Ruling 93 as amended already lets a clip with burned-in text
go 16:9-ONLY. Apply the same to a hook: when no hook passes for both formats, a hook whose only refusal is ruling 93's 9:16
crop may open a package sealed formats ['16x9'], marked, exactly as the Blockware spotlight was (PBX posted that one in
16:9 and was content). A both-format hook always wins over a 16:9-only one. If this needs code, audit-first."
WHY CODE: ruling 93 as amended makes a burned CAPTION cut by the 9:16 16:9-only (visual_pin.formats, unchanged); a lower
third or bug the 9:16 crop would cut is still a refusal in any role (visual_pin.burned_block, layout_block, unchanged).
The integrator confirms a pin sealed formats ["16x9"] renders 16:9 only through its existing path (batch 86, the
Blockware spotlight) and needs nothing new.

THE CHANGE:
- visual_pin.crop_only(rec): the reason when a measured, current-version record's ONLY refusal is ruling 93's 9:16 crop
  (every refusing burned-in item a lower third or bug wholly inside the 16:9, not over the speaker, cut by the 9:16), no
  ruling-70 third person (hook_block None), else None.
- build(): after the rated openers' frames are judged, ONLY when none of them may open (every one has
  visual_hook_block), each whose refusal crop_only names loses its block, its record gains formats ["16x9"] (so
  package_pin.formats_of seals the pin ["16x9"], unchanged) and sixteen_nine_only; hook_pool records them with a note.
- opens_16x9(m): that flag, the record's ["16x9"], and crop_only still naming it. The two per-segment layout checks
  (the no-voice order's and the line-up's, before any write) skip ruling 93 for that moment ONLY as the hook (order[0],
  segs[0]); as a clip its refusal stands.

UNCHANGED GUARDS: the hook bar, G17a, the opener rule (can_open); hook_block (ruling 70) still refuses; the visual gate
row (inventory: every clip measured); package_pin.formats_of; the render's own checks.

TESTS: crop_only (a crop-cut lower third qualifies; a ticker, a speaker covered, a part outside the 16:9, nothing refused,
an older or unmeasured record, a third person: none); a build with no both-format hook opens on the 16:9-only hook and
seals ["16x9"]; a both-format hook wins (the other stays refused); as a clip the moment is still refused. Mutations
W1-W6 after a control run.

PLEASE CHECK: (1) that the exception fires only when no both-format hook exists; (2) that only the hook is excused, and
only for the 9:16 crop; (3) that the seal says 16:9 only; (4) the tests.


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
