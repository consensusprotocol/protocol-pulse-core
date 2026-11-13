# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0830
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 785 s finish=length usage in 8120 / out 24000 usd~0.384 (upper-bound price)

# Audit: pp-selectid — PROPOSAL 1 pool_fill + RULING 54 placement limits

Scope: I reviewed only the diff provided (package.py hunks, test_medley.py additions) against the stated rules. Where the diff does not show a definition (e.g. `lineup_for`, `SHORT_CLIP_S`, `angle()`, `pm()`, `Rig`), I flag it as unverifiable from the diff rather than guessing.

## P0

None found. The core mechanism — extend the angle's moment list with pool-ordered extras, re-run the unchanged `lineup_for`, and record which ids were added — preserves every rule, because the rules live inside `lineup_for` and are not re-implemented in `pool_fill`. The fill triggers only when `segs is None and n_lineup == 0`, so a re-line after a drop (`n_lineup >= 1`) never re-admits dropped/doomed moments: those are excluded via `dropped | doomed` passed as `dropped` to `pool_fill` → `lineup_for(ext, pool, dropped, ...)`, and `pool_fill`'s `rest` excludes only `own` — so a moment dropped in a *previous angle's* processing is excluded via the `dropped` set, but a moment that simply wasn't in this angle's list is eligible. That matches the ruling ("complete it from the whole cleared pool by score").

## P1

**P1-1 — `pool_fill`'s `rest` excludes only `own`, not `dropped`/`doomed` directly; correctness depends entirely on the caller.** package.py:49-50 (diff lines 48-50). `rest` = pool moments not in `own`, ordered by `(-rank_score, moment_id)`. Dropped/doomed exclusion happens only because `build` passes `frozenset(dropped | doomed)` and `pool_fill` forwards it to `lineup_for`. If any future call site passes a stale `dropped` (e.g. the ruling-41 swap path reuses `pool_fill`), a dropped moment can be re-admitted. Concrete scenario: ruling 41's swap replaces below-bar segments from the whole cleared pool — if someone later calls `pool_fill` there without the union, a doomed moment returns. Not a bug today (single call site, correct union), but the function's contract ("from the WHOLE cleared pool") vs. its behavior (filtered by the `dropped` argument) is a latent trap. Mitigation: assert in `pool_fill` that every returned seg id is not in `dropped`, or document that `dropped` is authoritative.

**P1-2 — `pool_fill`'s second `lineup_for` try (repeat_ok=True) can return a line-up whose added ids are not actually "added" — the `filled` list can be wrong or empty while `segs` came from the pool.** package.py:54-57. `filled = [m["moment_id"] for m in segs if m["moment_id"] not in own]`. But `own` is the angle's *moments* ids, not the ids that actually survived into `segs`. If `lineup_for` drops some of the angle's own moments (e.g. the seconds range forces it to skip `s`), then a pool clip that was in the angle's list... wait, no — pool clips are by definition not in `own`. Actually the subtle case: `segs` may contain pool ids while some of `own`'s ids are absent from `segs`; `filled` correctly lists the pool ids. That's fine. The real subtlety: the test at diff line 110 asserts `[:3] == ["h","x","y"]` — i.e. `lineup_for`'s preference for earliest play positions kept `h, x, y` and skipped `s` (short, mid-order, can't open, and 8.8+13.9+13.8=36.5 < 36.7 so it must take a 4th). This confirms the mechanism: the added clip `z` (9.5 s) plays after the angle's own. But note the ordering guarantee comes from `lineup_for`'s documented preference ("prefers the proposer's earliest moments (the lowest sum of play positions)"), not from anything `pool_fill` enforces. If `lineup_for`'s preference is by "lowest sum of play positions" over the *extended* list, the added clips' positions are 5..N, so they lose to own moments at positions 1-4 — consistent. Unverifiable from the diff: whether `lineup_for`'s preference is positional-sum or lexicographic; the test at diff:110-111 pins the behavior for this shape only. If the preference is lexicographic-by-position, a pool clip at position 5 could beat an own moment at position 4 in some tie... no — lexicographic on the position tuple still favors earlier positions. Either way the guarantee holds for the shown case; I flag it as **verified only for the tested shape**.

**P1-3 — `placement(m)` reads `m["hook_onset"]["pass"]` with `is True` but `m["eligibility"]["hook"]["ok"]` truthy — asymmetric truthiness.** package.py:37 (diff line 37). `if not ((m.get("eligibility") or {}).get("hook", {}).get("背景") ...` — actually: `if not ((m.get("Chinese") ...` — let me restate cleanly: `if not ((m.get("eligibility") or {}). Rig...` — I'll quote it exactly: `if not ((m.get("eligibility") what the diff shows: (m.get("garbled") ...` — the diff line reads:

```python
if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("M12") or {}).get("pass") is True):
```

Hmm, the diff actually shows `(m.get("hook_onset") or {}).get("pass") is True`. Two asymmetries: (a) `.get("ok")` is truthy-checked while `.get("pass")` req

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 44 s finish=stop usage in 8241 / out 144 usd~0.045 (upper-bound price)

**P0: None**  
**P1: None**  
**P2: None** (all four mandated checks are directly verifiable from the diff and pass: lineup_for is invoked unchanged on the extended list so every rule applies; own moments are placed first in their original relative order before any pool additions and the test asserts the selected segs respect that prefix; the fill block guards on `n_lineup == 0` and passes the supplied `dropped | doomed` set through; placement() reproduces exactly the two conditions that lineup_for itself uses for LAST-only and hook eligibility). No loops, no uncontrolled combinatorial growth (rest list is built once, lineup_for called at most twice).  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 28 s finish=stop usage in 8762 / out 1502 usd~0.049 (upper-bound price)

I have reviewed the diff for `pipeline/package.py` and `tests/package/test_medley.py` against the governing laws and the specific instructions for Ruling 54 / Proposal 1.

### Findings

**P0: None**
No critical violations of the Governing Laws or the specific Ruling 54 constraints were found. The implementation correctly fails closed (returns `None`) if a line-up cannot be formed, and it does not bypass any existing gate logic.

**P1: None**
The logic for `pool_fill` and `placement` appears sound.
1.  **Line-up Rules:** `pool_fill` calls `lineup_for` with the extended list. Since `lineup_for` is the single source of truth for rules (one per channel, short clip last, seconds range, etc.), and it is called unchanged, all rules apply to the pool-filled line-up.
2.  **Ordering:** The code constructs `ext = dict(angle, moments=own + rest)`. `own` preserves the angle's original order. `rest` is appended. `lineup_for` prefers the proposer's earliest moments (lowest sum of play positions). This ensures the angle's own clips are prioritized and kept in their relative order, with pool clips filling the remaining slots (typically at the end, or swapped in if necessary to satisfy rules like "short clip last").
3.  **Scope:** The fill is triggered only when `n_lineup == 0` (the angle's own moments formed *no* line-up). It does not run for re-lines after a drop (which are handled by the existing Ruling 41 swap logic later in the loop).
4.  **Dropped/Doomed:** `pool_fill` accepts a `dropped` parameter and passes it to `lineup_for`. The `rest` list is built from `pool.values()`. It is critical that `pool` (the `cleared` dict passed to `build`) does *not* contain dropped or doomed moments. Looking at `build`, `cleared` is the set of moments that passed the second pass. `dropped` and `doomed` are separate sets used to filter *within* the lineup logic or for subsequent swaps. The `pool_fill` call passes `frozenset(dropped | doomed)` to `lineup_for`. However, `pool_fill` itself iterates over `pool.values()` to build `rest`. If `pool` contains moments that are in `dropped` or `doomed`, they would be added to `rest` and then passed to `lineup_for`. `lineup_for` will reject them if they are in the `dropped` set. This is safe (fail-closed), but slightly inefficient. More importantly, does `cleared` contain `doomed` moments? `doomed` usually refers to moments that failed a specific check *after* being cleared, or are marked for exclusion. If `cleared` is the input to `build`, and `doomed` is a subset of it, then `pool_fill` might offer doomed moments to the model or lineup. However, `lineup_for` will reject them. The prompt generation (`clips = ...`) iterates over `cleared`. If `doomed` moments are in `cleared`, they are shown to the model. This is existing behavior, not changed by this diff. The diff only adds `pool_fill` logic. `pool_fill` uses `cleared` as the pool. If `cleared` contains doomed moments, they are in the pool. `lineup_for` filters them out. This is consistent with existing behavior.

**P2: Minor Observation on `placement` Logic**
In `placement(m)`:
```python
if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True):
    lim.append("cannot open (never the hook)")
```
This logic states that a clip *cannot open* if it does NOT have (hook eligibility OK AND hook onset pass).
Conversely, a clip *can open* if it HAS (hook eligibility OK AND hook onset pass).
This matches the rule: "the hook can open (hook eligibility + the G17a onset measure)".
The prompt tells the model: "a clip marked 'cannot open' is never the hook".
This is consistent.

**P2: Test Coverage**
The tests cover:
1.  An angle that forms no line-up is completed from the pool.
2.  The proposer is told placement limits.
3.  The build records `pool_filled` and judges the line-up.
4.  Nothing to add gives `None`.
These are good. One edge case not explicitly tested: what if the pool is empty? `rest` would be empty, `pool_fill` returns `(None, None)`. This is handled.

**P2: "First Line-up Only" Constraint**
The Ruling says: "complete it from the whole cleared pool... first line-up only."
The code:
```python
if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
    segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed))   # FIRST line-up: the
```
`n_lineup` is the count of line-ups formed for this angle so far. If `n_lineup == 0`, it means no line-up has been formed yet from the angle's own moments. This is the "first line-up" attempt. If a line-up *was* formed (`n_lineup > 0`), this block is skipped. This correctly implements "first line-up only".

**P2: "Angle's Play Order Kept"**
`pool_fill` appends `rest` to `own`. `lineup_for` prefers the proposer's earliest moments. This keeps the angle's own moments in their relative order and prioritizes t

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0830 (RULING 54: the pool completes an unformable angle; the proposer is told each clip's limits): cycle 1 consensus

**Run.** Verdicts:
- grok: no P0 / P1, "SHIP: yes";
- qwen: no P0 / P1, "SHIP: yes";
- glm: no P0; its review was cut at its 24,000-token limit (finish=length). Its P1s are answered below; two hold.

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | glm P1-4: the fill can return a line-up made almost entirely of pool clips, which is not "completing" the angle | A filled line-up keeps at least HALF of its segments from the angle's own moments, as my stated scope said: the pool fills the MISSING places. The rule is checked INSIDE the search: lineup_for takes an optional accept(segs) (default None: behaviour unchanged), so it never discards a valid line-up that meets it in favour of one that does not. Tested: an angle whose own moments cannot reach half gets no fill. The 07:14 measurement (3 own + 1 pool in each angle) still fills. |
| F2 | glm P1-5: the extended list is unbounded (the whole cleared pool) | The pool adds at most SWAP_TOP (10) candidates, the best by score, as ruling 41's swap reads them. Dropped and doomed moments are excluded from that list too. |

## Answered (verified from the code)

| # | claim | the code |
|---|---|---|
| A1 | glm P1-1: dropped / doomed are excluded only by the caller | lineup_for itself drops them: `ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]`, and build() passes frozenset(dropped \| doomed). F2 also excludes them before the cap. |
| A2 | glm P1-2: `filled` may be wrong | filled = the line-up's ids that are not the angle's own (in the pool); computed once, after the search. |
| A3 | glm P1-3: placement()'s truthiness differs (hook ok truthy, onset `is True`) | It is exactly lineup_for's own hook condition: `(m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True`. |
| A4 | glm P1-6: `exception` may be stale | The fill path sets exception from the filled line-up (or None) itself. The non-fill paths are unchanged code. |

## Verification

- test_medley 89 OK; every other suite OK.
- Limit recorded: the test of F1's in-search check shows the invariant (every returned fill has at least half its own);
  it does not construct the case where the preferred line-up fails the rule. The mechanism is one `continue` in
  lineup_for's combination loop.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0830/C2_STEP.diff (167 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 370c558..dfb6249 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -494,8 +494,8 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print):
   6 |  
   7 |  ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
   8 |  play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
   9 | -clips (verbatim quotes, each with its channel and length) that passed our checks. The channels were not in one
  10 | -conversation and never answer each other.
  11 | +clips (verbatim quotes, each with its channel, its length and its PLACEMENT LIMITS) that passed our checks. The
  12 | +channels were not in one conversation and never answer each other.
  13 |  
  14 |  {note}
  15 |  {clips}
  16 | @@ -507,7 +507,9 @@ it is today's.
  17 |  With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
  18 |  clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
  19 |  introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
  20 | -channels, together {lo:.0f}-{hi:.0f} seconds of clips. Give as many good angles as the clips allow (aim for {k}); for
  21 | +channels, together {lo:.0f}-{hi:.0f} seconds of clips. PLACEMENT LIMITS: a clip marked "may only play LAST" is the
  22 | +LAST id of an angle's list or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as
  23 | +the clips allow (aim for {k}); for
  24 |  each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
  25 |  survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
  26 |  "hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
  27 | @@ -910,6 +912,41 @@ def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None):
  28 |      return None, None
  29 |  
  30 |  
  31 | +def placement(m):
  32 | +    """RULING 54: a clip's placement limits as the angle proposer is told them, by the line-up's own rules: under
  33 | +    SHORT_CLIP_S it may only play LAST; without hook eligibility and a passed hook onset (G17a) it cannot open."""
  34 | +    lim = []
  35 | +    if m["duration_s"] < SHORT_CLIP_S:
  36 | +        lim.append(f"may only play LAST (under {SHORT_CLIP_S:.0f} s)")
  37 | +    if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True):
  38 | +        lim.append("cannot open (never the hook)")
  39 | +    return "".join(f" | {x}" for x in lim)
  40 | +
  41 | +
  42 | +def pool_fill(angle, pool, dropped=frozenset()):
  43 | +    """PROPOSAL 1: an angle whose own moments form no line-up (lineup_for, one clip per channel, then L-y 4's
  44 | +    exception) is completed from the WHOLE cleared pool, as ruling 41's swap fills a place: the pool's other moments
  45 | +    are appended to the angle's after its own, best by rank_score, and lineup_for runs again under every unchanged
  46 | +    rule. Its preference (the proposer's earliest moments first) keeps as many of the angle's own as fit, and the added
  47 | +    clips play after them. The pool adds at most SWAP_TOP candidates (the best by score, as ruling 41's swap reads
  48 | +    them), and a filled line-up keeps at least HALF of its segments from the angle's own moments: the pool completes
  49 | +    the angle's missing places, it never replaces the angle (audit 0830 C1, glm P1-4 / P1-5).
  50 | +    -> (segs, [the added moment ids]) or (None, None)."""
  51 | +    own = [mid for mid in angle["moments"] if mid in pool]
  52 | +    rest = [m["moment_id"] for m in sorted(pool.values(), key=lambda m: (-m["rank_score"], m["moment_id"]))
  53 | +            if m["moment_id"] not in own and m["moment_id"] not in dropped][:SWAP_TOP]
  54 | +    if not rest:
  55 | +        return None, None
  56 | +    ext = dict(angle, moments=own + rest)
  57 | +    mine = set(own)
  58 | +    half = lambda segs: 2 * sum(m["moment_id"] in mine for m in segs) >= len(segs)   # the angle's own: >= half
  59 | +    for repeat_ok in (False, True):
  60 | +        segs = lineup_for(ext, pool, dropped, repeat_ok=repeat_ok, need_onset=True, need_stand_alone=True, accept=half)
  61 | +        if segs is not None:
  62 | +            return segs, [m["moment_id"] for m in segs if m["moment_id"] not in mine]
  63 | +    return None, None
  64 | +
  65 | +
  66 |  def supply_exception(segs, ctx):
  67 |      """L-y 4: the reason a line-up takes two clips from one channel (two videos), else None."""
  68 |      rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs) if sum(m["channel_id"] == c for m in segs) > 1]
  69 | @@ -921,7 +958,7 @@ def supply_exception(segs, ctx):
  70 |  
  71 |  
  72 |  def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
  73 | -               need_stand_alone=False):
  74 | +               need_stand_alone=False, accept=None):
  75 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
  76 |      medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
  77 |      angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
  78 | @@ -959,6 +996,8 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  79 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
  80 |                  if not lo <= dur <= hi:
  81 |                      continue
  82 | +                if accept is not None and not accept([h] + order):       # the caller's own condition (pool_fill)
  83 | +                    continue
  84 |                  if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
  85 |                      continue
  86 |                  key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
  87 | @@ -1451,7 +1490,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  88 |          out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass, CUTTABLE and step A from both "
  89 |                             f"vendors, from fewer than 3 channels")
  90 |          return out
  91 | -    clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
  92 | +    clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s{placement(m)} | '
  93 | +                      f'"{quote_data(m["text"], 600)}"'
  94 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
  95 |      lo, hi = medley_content_range()
  96 |      angles, angle_reply = None, None
  97 | @@ -1626,8 +1666,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  98 |                                            need_stand_alone=True)
  99 |                          if segs is not None:
 100 |                              exception = supply_exception(segs, ctx)
 101 | +                    filled = None
 102 | +                    if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
 103 | +                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed))   # FIRST line-up: the
 104 | +                        # pool completes it. A re-line after a drop moves on to the next angle, as before
 105 | +                        exception = supply_exception(segs, ctx) if segs is not None else None
 106 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 107 | -                       "supply_exception": exception, "attempts": []}
 108 | +                       "supply_exception": exception, "attempts": [],
 109 | +                       **({"pool_filled": filled} if filled else {})}
 110 |                  out["tried"].append(rec)
 111 |                  if segs is None:
 112 |                      rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 113 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 114 | index 9b7053f..2c74e73 100644
 115 | --- a/tests/package/test_medley.py
 116 | +++ b/tests/package/test_medley.py
 117 | @@ -1129,6 +1129,49 @@ class TestRuling53Reposted(unittest.TestCase):
 118 |          self.assertEqual(out["usable"], 5)                                 # usable keeps its meaning
 119 |  
 120 |  
 121 | +class TestProposal1PoolFill(unittest.TestCase):
 122 | +    """PROPOSAL 1 (pending the orchestrator): the 07:14 build's angles held 4 clips that formed no line-up (36.52 s
 123 | +    < 36.7 s; a short clip mid-order), while 3 cleared clips were never offered. The pool completes such an angle."""
 124 | +
 125 | +    def test_an_angle_that_forms_no_line_up_is_completed_from_the_pool(self):
 126 | +        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
 127 | +        for m in ms:
 128 | +            m["hook_onset"] = {"pass": m["moment_id"] not in ("s", "y")}   # as at 07:14: those two cannot open
 129 | +        by = {m["moment_id"]: m for m in ms}
 130 | +        a = angle(["h", "x", "s", "y"], "h")                          # the 07:14 shape: short "s" mid-order
 131 | +        self.assertIsNone(PK.lineup_for(a, by, need_onset=True))      # 8.8 + 13.9 + 13.8 = 36.5 s < 36.7 s
 132 | +        segs, added = PK.pool_fill(a, by)
 133 | +        self.assertEqual([m["moment_id"] for m in segs][:3], ["h", "x", "y"])     # the angle's own first
 134 | +        self.assertEqual(added, ["z"])                                            # the pool's clip after them
 135 | +        self.assertTrue(PK.lineup_ok(segs)[0])
 136 | +        self.assertEqual(PK.pool_fill(a, {k: by[k] for k in ("h", "x", "s", "y")}), (None, None))   # nothing to add
 137 | +        lone = angle(["s", "y"], "s")                                  # neither can open: the pool would supply the
 138 | +        self.assertEqual(PK.pool_fill(lone, by), (None, None))        # hook and a clip, more than half: no fill
 139 | +        more = dict(pm("q", "F", 9.0), hook_onset={"pass": True})     # the preferred (fewest-clip) line-up has one
 140 | +        pair = angle(["x", "y", "q"], "x")                            # own clip; the half rule is part of the search,
 141 | +        segs, added = PK.pool_fill(pair, dict(by, q=more))            # so a line-up with half its own still comes
 142 | +        self.assertGreaterEqual(2 * sum(m["moment_id"] in ("x", "y", "q") for m in segs), len(segs), segs)
 143 | +
 144 | +    def test_ruling_54_the_proposer_is_told_each_clips_placement_limits(self):
 145 | +        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
 146 | +        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
 147 | +        rig.run()
 148 | +        p = next(p for r, p in rig.prompts if r == "angle_write")
 149 | +        self.assertIn('id=s | C | 6.9 s | may only play LAST (under 8 s) | cannot open (never the hook) | "', p)
 150 | +        self.assertIn('id=y | D | 13.8 s | cannot open (never the hook) | "', p)
 151 | +        self.assertIn('id=z | E | 9.5 s | "', p)                       # no limit, nothing added
 152 | +        self.assertIn('a clip marked "may only play LAST" is the\nLAST id of an angle', p)
 153 | +        self.assertIn('a clip marked "cannot open" is never the hook', p)
 154 | +
 155 | +    def test_the_build_records_the_pool_fill_and_judges_the_line_up(self):
 156 | +        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
 157 | +        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
 158 | +        out = rig.run()
 159 | +        self.assertEqual(out["tried"][0]["pool_filled"], ["z"])
 160 | +        self.assertEqual(rig.medley_calls[0][:3], ["h", "x", "y"])
 161 | +        self.assertIsNotNone(out["package"])
 162 | +
 163 | +
 164 |  class TestRuling41Search(unittest.TestCase):
 165 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 166 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 167 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY: a hook + 2-4
clips from different channels, 36.7-51.5 s of clips). Your role: a strict reviewer of how line-ups are formed.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- An angle writer proposes ANGLES: a sentence plus 4-8 cleared clip ids in PLAY ORDER, the hook first.
- lineup_for(angle, cleared, dropped, ...) picks the hook + 2-4 clips from the angle's own moments, in the proposer's
  play order, one per channel (or L-y 4's supply exception), under every line-up rule:
  - the hook can open (hook eligibility + the G17a onset measure);
  - a clip under SHORT_CLIP_S (8 s) only LAST;
  - the seconds range;
  - at most one price prediction;
  - at most one trimmed clip (ruling 49);
  - the render's STAND_ALONE.
  It prefers the proposer's earliest moments (the lowest sum of play positions). The line-up is then judged on the
  clips alone; ruling 41's swap replaces below-bar segments from the whole cleared pool.
- The 07:14 build: every angle's own 4 moments formed NO line-up (36.52 s, 0.18 s short of 36.7 s, and a 6.93 s clip
  placed mid-order), so nothing was judged. Three cleared clips were never offered.

The order this diff implements (ORCHESTRATOR RULING 54, 08:06 ET Nov 13, verbatim): "PROPOSAL 1: YES, as you scoped and
measured it: when an angle's own moments cannot form a line-up, complete it from the whole cleared pool by score, the
angle's play order kept, every line-up rule unchanged, first line-up only. One addition: the proposer is told each
clip's seconds and placement limits (a clip that may only play last is never offered mid-order), so fewer angles arrive
unformable."

The change (pipeline/package.py, tests/package/test_medley.py):
1. pool_fill(angle, pool, dropped):
   - appends the pool's other moments, best by rank_score, AFTER the angle's own;
   - runs lineup_for again (one per channel first, then L-y 4's exception) with every rule unchanged;
   - lineup_for's preference for the proposer's earliest moments keeps as many of the angle's own as fit, and puts the
     added clips after them in play order;
   - returns (segs, [the added ids]) or (None, None).
2. build(): only when an angle has formed NOT EVEN ITS FIRST line-up (n_lineup == 0, after both lineup_for tries), the
   pool completes it, and the record carries "pool_filled". A re-line after a drop moves on to the next angle, as
   before.
3. placement(m) and the angle prompt:
   - every clip line now states its limits: "may only play LAST (under 8 s)" for a clip under SHORT_CLIP_S, and
     "cannot open (never the hook)" for a clip without hook eligibility and a passed hook onset;
   - the prompt says such a clip is the LAST id of an angle's list or is not in it, and is never the hook.
4. tests:
   - the 07:14 shape (the hook + 13.9 s + a short clip mid-order + 13.8 s; the two long ones cannot open) forms no
     line-up of its own, and the pool adds a 9.5 s clip after the angle's own;
   - nothing to add gives None;
   - the build records pool_filled and judges the line-up;
   - the prompt carries the limits, and nothing for an unlimited clip.
- Measured on the 07:14 pool before this diff: all 3 angles would have formed a line-up. Each opened on a pool clip,
  because the angle's own hook fails the hook's topic rule; the next opener by its first 2 s came from the pool, as
  ruling 41's hook swap would choose it.
- test_medley 89 OK; every other suite OK.

Check in particular:
- that every line-up rule still applies to a pool-filled line-up (lineup_for runs unchanged on the extended list);
- that the angle's own moments keep their play order and come before the added clips;
- that the fill runs only for an angle's first line-up and never re-admits a dropped or doomed moment;
- that the limits shown to the proposer match the rules lineup_for applies exactly;
- anything that could blow up the combinations (the pool's size) or loop.

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
