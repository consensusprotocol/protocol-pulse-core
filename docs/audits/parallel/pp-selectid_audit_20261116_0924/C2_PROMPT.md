# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_0924
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 327 s finish=stop usage in 20836 / out 3973 usd_reported=0.001139 usd~0.122 (upper-bound price)

The code implements **RULING 118 (4): STORY-FIRST LINE-UPS** as requested. It introduces a mechanism to prioritize angles derived from a pre-grouped stories file while maintaining all existing quality gates and the "writer-centric" build flow.

### Audit Analysis

**1. Story Angle Restriction (Inside the Story)**
The implementation ensures that story angles are strictly contained within their respective stories across all potential modification paths in the `build()` loop:
- **Join Table:** `join_moments` is called with `sel` (the restricted pool), ensuring the join table only contains moments from the same story.
- **Pool Fill:** `pool_fill` is called with `sel`, preventing the line-up from being filled by moments outside the story.
- **Swaps:** Both `swap_lineup` calls (for weak clips and re-screen failures) use `sel`, ensuring any replacement clip is also from the same story.
- **Selection:** `story_pool` correctly filters the `cleared` pool based on the `story_id` if the angle is a story angle.

**2. Fallback and Candidate Behavior**
- **No File/Invalid Shape:** `read_stories` implements a strict "all-or-nothing" validation. If the file is missing, unreadable, or any single story is malformed, it returns an empty list and a record of the failure, allowing the build to proceed as before.
- **Candidate Exclusion:** The code correctly prevents story angles from becoming candidates. `candidates.seed` and `load_candidate` both use the `story(t)` lambda to skip story-based line-ups, ensuring they are not cached as candidates for future builds.
- **Candidate Builds:** In `build()`, the `if candidate is None and stories_path:` block ensures that when a specific candidate is being re-processed, the story-first logic is bypassed.

**3. Gate Integrity and Ordering**
- **Ordering:** `angles = sorted(s_angles, key=order) + sorted(angles, key=order)` correctly places story angles ahead of the writer's angles while maintaining the rank/freshness sorting key.
- **Gates:** The loop `for ai, angle in enumerate(angles):` processes story angles through the exact same pipeline (medley, fidelity, context, coherence, value) as writer angles. No gates were bypassed or modified.
- **Writer Gateway:** The check `if not angles: return out` (where `angles` are the writer's results) ensures that if the writer fails to produce any angles, the build stops, preserving the ruling that the writer's gateway controls the build's progression.

**4. Law L-x (Writer Avoidance)**
- `story_writers` extracts the vendors and families of the models used for grouping.
- These are merged into `writers_v` and `writers_f` in `build()`, which are then used to populate `writer_avoid`. This ensures that the models that created the story grouping cannot judge the resulting line-ups.

**5. Test Coverage**
The `TestRuling118StoryFirst` suite is comprehensive, covering:
- The "all-or-nothing" file reader.
- The angle contract (3+ channels, passing hook, 3-8 moments).
- The priority of new channels over rank score in `story_angles`.
- The restriction of joins, fills, and swaps to the story pool.
- The exclusion of story angles from the candidate registry.
- The correct attribution of the angle source in the package.

### Findings

No defects found. The implementation is precise and adheres to all governing laws and the specific ruling.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 174 s finish=stop usage in 19556 / out 12967 usd_reported=0.010155 usd~0.253 (upper-bound price)



# Code Audit — pp-selectid / RULING 118 (4) STORY-FIRST LINE-UPS

## Scope

Reviewed the 519-line diff across `pipeline/candidates.py`, `pipeline/package.py`, `tests/package/proof_ledger.py`, `tests/package/test_medley.py`, and `tests/package/test_candidates.py`. Checked against the five requested items and all governing laws.

---

## Findings

### [P3] `read_stories` does not reject an empty-string `moment_id`

```python
all(isinstance(m, dict) and isinstance(m.get("moment_id"), str) for m in ms)
```

A moment with `"moment_id": ""` passes validation. In practice this is harmless (an empty string will never be a key in `cleared`, so it is filtered by `if x in cleared`), but the shape check is one `and m["moment_id"]` away from being airtight. The test suite exercises `{"moment_id": 3}` (wrong type) but not `{"moment_id": ""}`.

**Risk:** none in the current pipeline; a future change that allows empty-string keys in `cleared` would silently include a phantom moment.

---

### [P3] `out["stories"]["angles"]` is a misnomer

The field stores the **per-story diagnostic records** (each with `why`, `cleared`, `channels`, and optionally `angle`/`hook`/`moments`), not the angle objects themselves. The actual angles live in `out["angles"]` (the combined list) and in the local `s_angles`. A reader of the JSON output could reasonably expect `stories.angles` to be the angle dicts.

**Risk:** none functional; purely a readability / future-maintenance concern.

---

### [P3] `story` lambda in `load_candidate` re-reads `record.get("angles")` on every call

```python
story = lambda t: 0 < t["angle"] <= len(record.get("angles") or []) and \
    bool(((record.get("angles") or [])[t["angle"] - 1] or {}).get("story"))
```

`record.get("angles") or []` is evaluated twice per call (once for `len`, once for indexing). With a small `tried` list this is negligible, but hoisting to a local `angles = record.get("angles") or []` (as `candidates.py` does) would be marginally cleaner and avoid a subtle inconsistency if the record were mutated between the two reads (it isn't, but the pattern is fragile).

---

## Verification of the five requested checks

### (1) A story angle can never take a hook or clip from outside its story

**Confirmed.** Every path that could introduce a new moment is routed through `sel = story_pool(angle, cleared, by_story)`:

| Path | Uses `sel`? |
|---|---|
| `join_moments(angle, sel, doomed)` → join table | ✓ |
| `pool_fill(angle, sel, …, hook_only=True)` → first fill | ✓ |
| `swap_lineup(segs, weak, sel, …)` → weak-clip swap | ✓ |
| `swap_lineup(segs, set(bad), sel, …)` → re-screen swap | ✓ |
| `lineup_for` / `search_lineups` (unchanged) | Choose only from the angle's own moments ∪ join-table moments, both ⊆ story | ✓ |

The angle's own moments are built in `story_angles` from `ids = [x for x in s["moment_ids"] if x in cleared]` — strictly the story's cleared moments. The hook is selected from `hook_ids ∩ ids`. No path reaches outside `sel`.

The test `test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it` explicitly verifies that a 3-moment story (28 s of clips) produces no line-up and never pulls `z` or `q` from the wider pool.

### (2) Nothing changes when there is no file, no 3-channel story, or a candidate

**Confirmed.**

- **No file / unreadable / wrong shape:** `read_stories` returns `([], rec)`. `story_angles([], …)` returns `([], [])`. `s_angles` is empty → `s_writers` stays `(set(), set())` → `writers_v`/`writers_f` are just the angle writer's. `by_story` is `{}`. The combined `angles` list is just the writer's. `out["stories"]["read"]` is `False`. The per-angle loop uses `story_pool` which returns `cleared` (full pool) for non-story angles. Identical to pre-change behaviour.
- **No story of ≥ 3 channels:** `check_angles` raises → `row["why"]` is set → no angle produced. Same as no file.
- **Candidate build:** `if candidate is None and stories_path:` guards the entire stories block. `load_candidate` refuses story angles (both the auto-pick and the explicit-index path). `candidates.seed` skips them. Test `test_a_candidates_build_reads_no_stories` confirms `out` has no `"stories"` key.

### (3) Every gate is unchanged

**Confirmed.** The diff touches no gate code. The clips-alone verdict, coherence, fidelity, step-A re-screens, hook bar, and render-stage `STAND_ALONE` are all called with the same signatures and thresholds. The only change is the **source pool** for moment selection (`sel` vs `cleared`), not the **judgment** of any moment. `check_angles` (the angle contract) is the same function the writer's angles pass through.

### (4) L-x compliance

**Confirmed.** `story_writers` extracts the grouping model IDs from the file's `models.group` field, finds the router back-ends running those models, and returns their vendors and families. These are unio

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_0924 (RULING 118 (4): story-first line-ups)

FIRST ATTEMPT (kept as C1first_*): SEATS ANSWERED 1 of 3: qwen at effort none looped to its 16,000-token cap; mimo was cut
off at 32,000. gemma's one P1 ("check_angles(..., cleared, 1, ...): the third argument is min_moments; 1 lets a 1-2 moment
angle through") MISREADS the unchanged guard: its signature is check_angles(obj, by_id, k=MAX_ANGLES, hooks=None)
(package.py:1058), k being how many angles the object may hold ("exactly {'angles': [1-k items]}"); the 3-8 moments rule
is inside it, unconditionally (package.py:1073: "if not 3 <= len(ms) <= 8"). Not a defect. A test now pins it: a story with
two cleared moments gives no angle, "not an angle: angle 1: 3-8 distinct offered ids" (in cycle 2's diff).

CYCLE 1 RE-ASKED on the same diff plus that test, with qwen at effort medium and gpt-oss-20b at medium in mimo's seat (as
the integrator's audits answer): SEATS ANSWERED 2 of 3 (gpt-oss cut off at 24,000 with no answer). P1_OR_WORSE: qwen 0,
gemma 0. Cycle 1, both attempts: $0.0325 of Heimdall, not capped.

P3 noted, not changed (qwen): an empty-string moment_id is read (it can never be in the cleared pool, so it can never
enter a line-up); out["stories"]["angles"] holds one row a story, with the angle it gave or why not (a record name);
load_candidate's story lambda re-reads the record's angles list (a few items, once a record).

Suites: 40 files, 828 tests. Mutations S1-S18 after a control run: 18 of 18 killed.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_0924/C2_STEP.diff (519 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | index 4e1c4e2..bc834c0 100644
   3 | --- a/pipeline/candidates.py
   4 | +++ b/pipeline/candidates.py
   5 | @@ -62,16 +62,22 @@ def seed(reg, record, source):
   6 |      """Seed the registry from one build record, once per record (reg["records"]). Every tried line-up that passed the
   7 |      clips-alone verdict and is not itself a candidate's try becomes a candidate (one per line-up, the earliest record
   8 |      that passed it). A line-up the record packaged is closed. A record written before the registry existed applies
   9 | -    the outcome of the candidate it tried (its out["candidate"]). -> the keys added."""
  10 | +    the outcome of the candidate it tried (its out["candidate"]). A story angle's line-up (ruling 118 (4)) is never
  11 | +    a candidate: its angle has no writer back-end (law L-x), and a later build reads the story again. -> the keys
  12 | +    added."""
  13 |      if source in reg["records"]:
  14 |          return []
  15 |      reg["records"].append(source)
  16 |      added, at = [], record.get("now")
  17 |      pk = record.get("package") or {}
  18 |      packaged = [s.get("moment_id") for s in pk.get("segments") or []]
  19 | +    angles = record.get("angles") or []
  20 | +    story = lambda t: type(t.get("angle")) is int and 0 < t["angle"] <= len(angles) and \
  21 | +        bool((angles[t["angle"] - 1] or {}).get("story"))                 # RULING 118 (4)
  22 |      for i, t in enumerate(record.get("tried") or []):
  23 |          lu = t.get("lineup")
  24 | -        if t.get("medley_ok") is not True or not isinstance(lu, list) or not lu or t.get("candidate") is not None:
  25 | +        if t.get("medley_ok") is not True or not isinstance(lu, list) or not lu or t.get("candidate") is not None \
  26 | +                or story(t):
  27 |              continue
  28 |          k = key(lu)
  29 |          if k not in reg["candidates"]:
  30 | diff --git a/pipeline/package.py b/pipeline/package.py
  31 | index fc9cd76..8493f7b 100644
  32 | --- a/pipeline/package.py
  33 | +++ b/pipeline/package.py
  34 | @@ -103,6 +103,8 @@ TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: t
  35 |  # only with the scorer's affirmation of its trimmed text, and package_pin refuses scorer_pending. RULING 60 (11:01): for
  36 |  # a moments pin the scorer judges stand-alone only, and the affirmation is the score alone (stand_alone.affirmed with
  37 |  # moments=True), as the render's validate reads it.
  38 | +STORIES = "/home/ultron/pulse_intel/stories/latest.json"   # RULING 118 (4): the receipts session's stories
  39 | +#   (pipeline_pi_receipts; read only), refreshed every 15 minutes: the story-first angles (read_stories)
  40 |  SCORER_VERDICTS = "/home/ultron/protocol_pulse/data/stand_alone_scorer/verdicts/latest.json"   # ruling 56: the
  41 |  SCORER_KIND = "moments"            # integrator's verdicts (read only); ruling 60: kind "moments", no event
  42 |  RENDER_SCORER_CODE = tuple(f"/home/ultron/protocol_pulse/pipeline/{f}" for f in ("stand_alone.py", "story_semantics.py"))
  43 | @@ -1960,6 +1962,101 @@ def join_moments(angle, cleared, doomed=frozenset()):
  44 |      return ([h] + own + first + then)[:JOIN_MOMENTS_MAX]
  45 |  
  46 |  
  47 | +def read_stories(path):
  48 | +    """RULING 118 (4): the receipts session's stories file (pipeline_pi_receipts, /home/ultron/pulse_intel; read only), in
  49 | +    its writer's documented shape (stories.py): {"generated_at", ..., "models", "stories": [{"story_id", "headline",
  50 | +    "channels", "n_claims", "moments": [{"moment_id", "video_id", "channel_name", "published_at", "claims"}]}]}.
  51 | +    -> (stories, record): each story {"story_id", "headline", "moment_ids"}, in the file's order (the most claims
  52 | +    first). No path, no file, or a file out of that shape: no stories (the build goes on as before) and the record says
  53 | +    why. Its age is recorded, not judged: only the moments this build's own pool still holds can be used."""
  54 | +    rec = {"path": path, "read": False}
  55 | +    if not path:
  56 | +        return [], dict(rec, why="no stories file named")
  57 | +    try:
  58 | +        with open(path) as f:
  59 | +            d = json.load(f)
  60 | +    except FileNotFoundError:
  61 | +        return [], dict(rec, why="no file")
  62 | +    except (OSError, ValueError) as e:
  63 | +        return [], dict(rec, why=f"unreadable ({type(e).__name__})")
  64 | +    st = d.get("stories") if isinstance(d, dict) else None
  65 | +    if not isinstance(st, list):
  66 | +        return [], dict(rec, why="no 'stories' list")
  67 | +    out = []
  68 | +    for i, s in enumerate(st):
  69 | +        ms = s.get("moments") if isinstance(s, dict) else None
  70 | +        if not (isinstance(ms, list) and isinstance(s.get("story_id"), str) and s["story_id"] and
  71 | +                isinstance(s.get("headline"), str) and s["headline"].strip() and
  72 | +                all(isinstance(m, dict) and isinstance(m.get("moment_id"), str) for m in ms)):
  73 | +            return [], dict(rec, why=f"story {i + 1} is out of the file's shape")
  74 | +        out.append({"story_id": s["story_id"], "headline": " ".join(s["headline"].split()),
  75 | +                    "moment_ids": list(dict.fromkeys(m["moment_id"] for m in ms))})
  76 | +    return out, dict(rec, read=True, generated_at=d.get("generated_at"), prompt_version=d.get("prompt_version"),
  77 | +                     models=d.get("models"), stories=len(out))
  78 | +
  79 | +
  80 | +def story_angles(stories, cleared, hooks, k=MAX_ANGLES):
  81 | +    """RULING 118 (4), STORY-FIRST LINE-UPS: angles built INSIDE ONE STORY (its hook and every clip from the same story),
  82 | +    tried ahead of the angle writer's; every gate unchanged. For each story in the file's order, the best of `hooks`
  83 | +    (the build's passing hooks, best first) among the story's cleared moments; the angle's moments are that hook, then
  84 | +    the story's other cleared moments, one of each channel not yet in first, then by rank score (at most 8); its
  85 | +    sentence is the story's headline. It must hold the angle contract (check_angles: 3-8 distinct moments from >= 3
  86 | +    channels, the hook one of them and a passing hook) or the story gives no angle. At most k angles.
  87 | +    -> (angles, record): each angle {"angle", "moments", "hook", "story": story_id}; the record, one row a story."""
  88 | +    hook_ids = [m["moment_id"] for m in hooks]
  89 | +    angles, rec = [], []
  90 | +    for s in stories:
  91 | +        ids = [x for x in s["moment_ids"] if x in cleared]
  92 | +        row = {"story_id": s["story_id"], "cleared": len(ids),
  93 | +               "channels": len({cleared[x]["channel_id"] for x in ids})}
  94 | +        rec.append(row)
  95 | +        if len(angles) >= k:
  96 | +            row["why"] = f"{k} story angle(s) already"
  97 | +            continue
  98 | +        h = next((x for x in hook_ids if x in ids), None)
  99 | +        if h is None:
 100 | +            row["why"] = "no passing hook among its cleared moments"
 101 | +            continue
 102 | +        chans, first, then = {cleared[h]["channel_id"]}, [], []
 103 | +        for x in sorted((x for x in ids if x != h), key=lambda x: (-cleared[x].get("rank_score", 0), x)):
 104 | +            (then if cleared[x]["channel_id"] in chans else first).append(x)
 105 | +            chans.add(cleared[x]["channel_id"])
 106 | +        ms = ([h] + first + then)[:8]
 107 | +        a = {"angle": s["headline"], "moments": ms, "hook": h, "support": {x: s["story_id"] for x in ms}}
 108 | +        try:
 109 | +            check_angles({"angles": [a]}, cleared, 1, hooks=set(hook_ids))
 110 | +        except ValueError as e:
 111 | +            row["why"] = f"not an angle: {e}"
 112 | +            continue
 113 | +        angles.append({"angle": a["angle"], "moments": ms, "hook": h, "story": s["story_id"]})
 114 | +        row.update(angle=len(angles), hook=h, moments=ms)
 115 | +    return angles, rec
 116 | +
 117 | +
 118 | +def story_pool(angle, cleared, by_story):
 119 | +    """RULING 118 (4): the pool a line-up for `angle` takes moments from beyond its own (its join table, the fill, every swap):
 120 | +    a story's angle ONLY its story's cleared moments (`by_story`: story id -> moment ids; a story it does not hold gives
 121 | +    none); any other angle the whole cleared pool, as before."""
 122 | +    if angle.get("story") is None:
 123 | +        return cleared
 124 | +    return {x: cleared[x] for x in by_story.get(angle["story"]) or () if x in cleared}
 125 | +
 126 | +
 127 | +def story_writers(router, models):
 128 | +    """Law L-x for the story angles: the stories file's grouping models chose each story's moments (one of them wrote its
 129 | +    headline), so the back-ends of the router that run those models give their vendors and families to the writers'
 130 | +    sets the verdicts avoid. A model no back-end runs can judge nothing here. -> (vendors, families)."""
 131 | +    ms = {m for m in ((models or {}).get("group") or []) if isinstance(m, str)} if isinstance(models, dict) else set()
 132 | +    bs = [b for b in router.backends.values() if getattr(b, "model", None) in ms]
 133 | +    return {b.vendor for b in bs}, {b.family for b in bs}
 134 | +
 135 | +
 136 | +def angle_source(angle, reply):
 137 | +    """The package's record of who made its angle: the angle writer's back-end, or for a story angle (ruling 118 (4))
 138 | +    the story of the receipts session's stories file it was built inside."""
 139 | +    return f"story {angle['story']} (the stories file)" if angle.get("story") else reply.backend
 140 | +
 141 | +
 142 |  def join_table(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
 143 |      """RULING 117 (2): the JOIN TABLE. The clips-alone verdict's own join question (JOIN_QUESTION) asked ONCE per ordered
 144 |      pair of `ms` (the angle's hook first, then its other moments; at most JOIN_MOMENTS_MAX; the hook is never B), one
 145 | @@ -2668,8 +2765,11 @@ def load_candidate(record, index=None, source=""):
 146 |      tried = record.get("tried") or []
 147 |      ids_ok = lambda t: isinstance(t.get("lineup"), list) and bool(t["lineup"]) and \
 148 |          all(isinstance(x, str) for x in t["lineup"]) and type(t.get("angle")) is int    # audit 1330 C2: the shape
 149 | -    if index is None:
 150 | -        index = next((i for i, t in enumerate(tried) if t.get("medley_ok") is True and ids_ok(t)), None)
 151 | +    story = lambda t: 0 < t["angle"] <= len(record.get("angles") or []) and \
 152 | +        bool(((record.get("angles") or [])[t["angle"] - 1] or {}).get("story"))   # RULING 118 (4)
 153 | +    if index is None:                                  # (a story angle's line-up is never kept: see below)
 154 | +        index = next((i for i, t in enumerate(tried) if t.get("medley_ok") is True and ids_ok(t) and not story(t)),
 155 | +                     None)
 156 |          if index is None:
 157 |              raise ValueError("no line-up in this record passed the clips-alone verdict")
 158 |      if not 0 <= index < len(tried):
 159 | @@ -2683,6 +2783,9 @@ def load_candidate(record, index=None, source=""):
 160 |      ai, angles = int(t["angle"]) - 1, record.get("angles") or []
 161 |      if not 0 <= ai < len(angles) or angles[ai].get("angle") != t.get("text"):
 162 |          raise ValueError(f"tried[{index}]'s angle is not the record's angle {ai + 1}")
 163 | +    if angles[ai].get("story"):                       # RULING 118 (4): its moments were chosen by the stories file's
 164 | +        raise ValueError(f"tried[{index}] is story {angles[ai]['story']!r}'s line-up (ruling 118 (4)): not kept, "
 165 | +                         f"its angle has no writer back-end for law L-x; a later build reads the story again")
 166 |      a = {k: angles[ai][k] for k in ("angle", "moments", "hook")}
 167 |      if a["hook"] != t["lineup"][0]:
 168 |          raise ValueError(f"tried[{index}] does not open on its angle's hook (ruling 59 c)")
 169 | @@ -2721,7 +2824,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 170 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
 171 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
 172 |            join_cache=None,
 173 | -          visual_cache=None, registered=None, lock_check=None, scorer_extra=()):
 174 | +          visual_cache=None, registered=None, lock_check=None, scorer_extra=(), stories_path=None):
 175 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 176 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 177 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 178 | @@ -3002,6 +3105,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 179 |      lo, hi = medley_content_range()
 180 |      angles, angle_reply, errs = None, None, []
 181 |      cand_segs = None
 182 | +    stories, s_angles, s_writers = [], [], (set(), set())
 183 | +    if candidate is None and stories_path:           # RULING 118 (4): STORY-FIRST LINE-UPS, ahead of the angle writer
 184 | +        stories, out["stories"] = read_stories(stories_path)
 185 | +        s_angles, out["stories"]["angles"] = story_angles(stories, cleared, passing, max_angles)
 186 | +        if s_angles:                                  # law L-x: the grouping models chose the story's moments
 187 | +            s_writers = story_writers(router, out["stories"].get("models"))
 188 | +        log(f"  RULING 118 (4): {len(stories)} story(ies) read, {len(s_angles)} story angle(s)"
 189 | +            + ("" if out["stories"]["read"] else f" (no stories: {out['stories']['why']})"))
 190 | +    by_story = {s["story_id"]: s["moment_ids"] for s in stories}
 191 |      if candidate is not None:                         # RULING 66 (13:18): A PASSED LINE-UP IS KEPT: its own angle and
 192 |          cand_segs, why_c = candidate_lineup(router, candidate, cleared, ctx.now)   # line-up; no angle is asked for
 193 |          out["candidate"] = {"source": candidate.get("source"), "index": candidate.get("index"),
 194 | @@ -3035,8 +3147,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 195 |                  router.reject(r)
 196 |              errs.append(f"{type(e).__name__}: {str(e)[:200]}")       # every reason, the first one too
 197 |              out["why_none"] = "no readable angles: " + "; then ".join(errs)
 198 | -    if not angles:
 199 | -        return out
 200 | +    if not angles:                                    # RULING 118 (4): the story angles go with the writer's only:
 201 | +        return out                                    # its back-end keeps every write on its gateway (ruling 85)
 202 |      out.pop("why_none", None)
 203 |      missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}] if candidate is None else []
 204 |      if missing and len(angles) < max_angles:            # RULING 64: a passing hook left without an angle is asked
 205 | @@ -3061,11 +3173,17 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 206 |          return bool(segs) and fresh_key(segs, ctx.now)[0]                                              # old go first
 207 |      hrank = {m["moment_id"]: (-hook_own(m)["rating"], -sum(m["hook_rating"].get(k) or 0 for k in HOOK_PARTS))
 208 |               for m in passing}                            # ruling 59 (c): the best hook first, then ruling 57's
 209 | -    angles = sorted(angles, key=lambda a: (hrank[a["hook"]], not first_fresh(a)))   # freshness; stable: the writer's
 210 | +    order = lambda a: (hrank[a["hook"]], not first_fresh(a))
 211 | +    angles = sorted(s_angles, key=order) + sorted(angles, key=order)   # RULING 118 (4): the story angles first; then
 212 | +    # ruling 57's freshness; stable: the writer's
 213 |      # order within each
 214 | -    out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
 215 | +    out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"],
 216 | +                      **({"story": a["story"]} if a.get("story") else {})} for a in angles]
 217 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
 218 | -    writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 219 | +    writers_v = {angle_reply.vendor} | s_writers[0]   # RULING 118 (4): and the stories file's grouping models (L-x)
 220 | +    writers_f = {angle_reply.family} | s_writers[1]
 221 | +    if s_angles:
 222 | +        out["stories"]["writers"] = {"vendors": sorted(s_writers[0]), "families": sorted(s_writers[1])}
 223 |  
 224 |      def pin_last_resort(pk):
 225 |          """RULING 102: the pin's record of the local judge's step-A verdicts on its clips (either screen's), by label."""
 226 | @@ -3089,7 +3207,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 227 |      writer_avoid = {P.gateway(router.backends[n]) for n in router.chain("angle_write") if n in router.backends} - \
 228 |          {P.gateway(ab) if ab is not None else angle_reply.vendor}   # heimdall_first a family is its own maker, and
 229 |      # a write may still fail over deepseek -> qwen as today); the verdicts avoid every writer's maker and family
 230 | -    log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)" if candidate is None else
 231 | +    log(f"  {len(angles)} angles from {angle_reply.backend}"
 232 | +        + (f", the first {len(s_angles)} from the stories file (ruling 118 (4))" if s_angles else "")
 233 | +        + f" ({time.time() - t0:.0f} s)" if candidate is None else
 234 |          f"  ruling 66: the candidate {candidate.get('source')} tried[{candidate.get('index')}] (angle "
 235 |          f"{candidate['ai'] + 1} line-up {candidate['n_lineup']}), as judged: its angle from {angle_reply.backend}, "
 236 |          f"no angle asked ({time.time() - t0:.0f} s)")
 237 | @@ -3264,7 +3384,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 238 |          if problems:
 239 |              note["why_not"] = f"a required gate is not exactly PASS: {problems}"
 240 |              return None
 241 | -        pk["models"] = {"angle": angle_reply.backend,
 242 | +        pk["models"] = {"angle": angle_source(angle, angle_reply),
 243 |                          "writer": "the latest write's title and caption" if fixed is None else
 244 |                                    "the latest write's title; the caption is code's fixed line (07:30 (C), ruling 65 b)",
 245 |                          "medley": nv_med.get("backend"), "fidelity_verdict": fid.get("backend"),
 246 | @@ -3289,9 +3409,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 247 |      with ThreadPoolExecutor(max_workers=8) as pool:
 248 |          for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):
 249 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
 250 | +            sel = story_pool(angle, cleared, by_story)    # RULING 118 (4): a story's angle chooses inside its story
 251 | +            #   (its join table, the fill, every swap; lineup_for and the search choose only among the angle's own and
 252 | +            #   its join table's moments, so the story holds there by construction)
 253 |              jt, a_ratings, ext = {}, {}, angle            # RULING 117: this angle's join table; its clips' ratings
 254 |              if candidate is None and angle["hook"] in cleared and angle["hook"] not in doomed:
 255 | -                jids = join_moments(angle, cleared, doomed)  # the moments that CAN be in its line-up
 256 | +                jids = join_moments(angle, sel, doomed)  # the moments that CAN be in its line-up
 257 |                  ext = dict(angle, moments=jids)           # the search's angle: the writer's order first
 258 |                  jms = [cleared[x] for x in jids]
 259 |                  jt, jt_err = join_table(router, jms, ctx, writers_v, writers_f, cache=join_cache)
 260 | @@ -3332,7 +3455,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 261 |                              exception = supply_exception(segs, ctx)
 262 |                      filled = None
 263 |                      if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
 264 | -                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed), ctx.now,
 265 | +                        segs, filled = pool_fill(angle, sel, frozenset(dropped | doomed), ctx.now,
 266 |                                                   hook_only=True)   # FIRST: the
 267 |                          # pool completes it. A re-line after a drop moves on to the next angle, as before
 268 |                          exception = supply_exception(segs, ctx) if segs is not None else None
 269 | @@ -3443,7 +3566,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 270 |                                        "the clips alone have no through-line a viewer can state (or it was not measured)")
 271 |                          break
 272 |                      dropped |= weak
 273 | -                    swapped, swaps = swap_lineup(segs, weak, cleared, frozenset(dropped | doomed), keep_hook=True)
 274 | +                    swapped, swaps = swap_lineup(segs, weak, sel, frozenset(dropped | doomed), keep_hook=True)
 275 |                      rec["why"] = (f"the clips alone fail (ratings / joins): swapped {swaps}, re-judged (ruling 41)"
 276 |                                    if swapped is not None else
 277 |                                    f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the "
 278 | @@ -3572,7 +3695,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 279 |                              dropped |= set(bad)                # with their reason; the next-best cuttable clip takes
 280 |                              doomed |= set(bad)                 # each place (ruling 41's swap); the clips-alone verdict
 281 |                              out["prescreen"].setdefault("rescreen_failed", {}).update(bad)     # re-judges the line-up
 282 | -                            swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed),
 283 | +                            swapped, swaps = swap_lineup(segs, set(bad), sel, frozenset(dropped | doomed),
 284 |                                                           keep_hook=True)
 285 |                              held = sorted(k for k, v in bad.items() if is_held(v))    # ruling 102: no answer
 286 |                              rec["why"] = (f"step A, re-screened off the writer's vendor, fails "
 287 | @@ -3764,7 +3887,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 288 |                          rec["why"] = f"a required gate is not exactly PASS: {problems}: next angle"
 289 |                          w_used = writes
 290 |                          break
 291 | -                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend, "medley": med.get("backend"),
 292 | +                    pk["models"] = {"angle": angle_source(angle, angle_reply), "writer": wr.backend, "medley": med.get("backend"),
 293 |                                      "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
 294 |                                      "coherence": coh.get("backend"), "value": val.get("backend")}
 295 |                      pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med, "value": val}
 296 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 297 | index a5cae35..ed044d9 100644
 298 | --- a/tests/package/proof_ledger.py
 299 | +++ b/tests/package/proof_ledger.py
 300 | @@ -481,6 +481,7 @@ def main(argv=None):
 301 |                join_cache=os.path.join(HERE, "proof", "JOIN_CACHE.json"),          # ruling 117: cached
 302 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 303 |                scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 304 | +              stories_path=PK.STORIES,                                             # ruling 118 (4): read only
 305 |                visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
 306 |                lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
 307 |                    segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
 308 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
 309 | index 7ab18d0..a110a21 100644
 310 | --- a/tests/package/test_candidates.py
 311 | +++ b/tests/package/test_candidates.py
 312 | @@ -173,5 +173,13 @@ class TestRegistry(unittest.TestCase):
 313 |          self.assertTrue(reg["candidates"]["a+b+c"]["history"][-1]["fresh"])
 314 |  
 315 |  
 316 | +    def test_a_story_angles_line_up_is_never_a_candidate(self):
 317 | +        """RULING 118 (4): its angle has no writer back-end (law L-x); a later build reads the story again."""
 318 | +        rec = record(T0, [dict(t(["a", "b", "c"]), angle=1), dict(t(["a", "b", "d"]), angle=2)])
 319 | +        rec["angles"] = [{"angle": "S", "moments": ["a", "b", "c"], "hook": "a", "story": "S-1"},
 320 | +                         {"angle": "W", "moments": ["a", "b", "d"], "hook": "a"}]
 321 | +        self.assertEqual(CA.seed(CA.new_registry(), rec, "r1"), ["a+b+d"])
 322 | +
 323 | +
 324 |  if __name__ == "__main__":
 325 |      unittest.main()
 326 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 327 | index 1adf4a6..48fe738 100644
 328 | --- a/tests/package/test_medley.py
 329 | +++ b/tests/package/test_medley.py
 330 | @@ -754,6 +754,8 @@ class Rig:
 331 |              kw["registered"] = self.registered
 332 |          if self.lock_check is not None:
 333 |              kw["lock_check"] = self.lock_check
 334 | +        if getattr(self, "stories_path", None):            # RULING 118 (4): the stories file (default: none read)
 335 | +            kw["stories_path"] = self.stories_path
 336 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 337 |              import tempfile
 338 |              fd, path = tempfile.mkstemp(suffix=".json")
 339 | @@ -4401,5 +4403,179 @@ class TestRuling109Channels(unittest.TestCase):
 340 |          self.assertNotIn("ruling_109", out)
 341 |  
 342 |  
 343 | +class TestRuling118StoryFirst(unittest.TestCase):
 344 | +    """RULING 118 (4) (orchestrator 05:40 ET Nov 16), STORY-FIRST LINE-UPS: an angle source that builds a line-up INSIDE
 345 | +    ONE STORY (the hook and every clip from the same story, 3 channels), ahead of the angle writer, every gate unchanged;
 346 | +    the receipts session's stories file is read only; no file: the build as before."""
 347 | +    GROUP = {"group": ["deepseek/deepseek-v4.1-flash", "minimax/minimax-m3.1-flash"]}
 348 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
 349 | +    STORY = [("S-1", "Bitcoin's own story", ["h", "x", "y", "gone"])]
 350 | +
 351 | +    def file(self, stories, models=GROUP):
 352 | +        d = tempfile.mkdtemp()
 353 | +        self.addCleanup(lambda: [os.remove(os.path.join(d, f)) for f in os.listdir(d)] and None or os.rmdir(d))
 354 | +        p = os.path.join(d, "latest.json")
 355 | +        with open(p, "w") as f:
 356 | +            json.dump({"generated_at": "2026-11-16T13:43:27Z", "prompt_version": "st1-x", "models": models,
 357 | +                       "stories": [{"story_id": sid, "headline": hl, "channels": 3, "n_claims": 6,
 358 | +                                    "moments": [{"moment_id": m, "video_id": "v" + m, "channel_name": "c",
 359 | +                                                 "published_at": "2026-11-16T10:00:00Z", "claims": []} for m in ms]}
 360 | +                                   for sid, hl, ms in stories]}, f)
 361 | +        return p
 362 | +
 363 | +    def rig(self, ms, writer, stories, **kw):
 364 | +        rig = Rig(ms, writer, [(False, [], None, "none")] * 20, [], **kw)
 365 | +        rig.stories_path = self.file(stories) if stories is not None else "/nonexistent/stories/latest.json"
 366 | +        return rig
 367 | +
 368 | +    def test_every_swap_of_a_story_line_up_stays_inside_its_story(self):
 369 | +        ms = self.MS + [pm("w", "F", 13.0, rank=5.0)]                     # in the story, ranked under the pool's z, q
 370 | +        story = [("S-1", "Bitcoin's own story", ["h", "x", "y", "w"])]
 371 | +        rig = self.rig(ms, ["h", "x", "y", "z", "q"], story)               # a weak clip: swapped inside the story
 372 | +        rig.medleys = [(False, [], {"clip_02": 2}, Rig.LINE)] + [(False, [], None, "none")] * 6
 373 | +        out = rig.run()
 374 | +        mine = [lu for r in out["tried"] if r["angle"] == 1 for lu in [r["lineup"]] if lu]
 375 | +        self.assertEqual(mine[:2], [["h", "x", "y"], ["h", "x", "w"]], out["tried"])
 376 | +        rig = self.rig(ms, ["h", "x", "y", "z", "q"], story, angle_from=("xai:grok", "xai", "grok"),
 377 | +                       a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]})    # a clip failing its re-screen: the same
 378 | +        rig.medleys, rig.writes = [(True, [], None, Rig.LINE)] * 2, [None, None]
 379 | +        out = rig.run()
 380 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "w"]])
 381 | +        self.assertIn("swapped {'y': 'w'}", out["tried"][0]["why"])
 382 | +        self.assertEqual(out["package"]["models"]["angle"], "story S-1 (the stories file)")   # who made its angle
 383 | +
 384 | +    def test_a_candidates_build_reads_no_stories(self):
 385 | +        med = {"through_line": "Nobody controls the rules.", "clips": {"hook": 4, "clip_01": 4, "clip_02": 4},
 386 | +               "flagged": [], "measured": True, "replayed": False, "backend": "xai:grok"}
 387 | +        c = PK.load_candidate({"tried": [{"angle": 1, "text": "W", "lineup": ["h", "z", "q"], "supply_exception": None,
 388 | +                                          "medley": med, "medley_ok": True}],
 389 | +                               "angles": [{"angle": "W", "moments": ["h", "x", "y", "z", "q"], "hook": "h"}],
 390 | +                               "angle_backend": "heimdall:deepseek", "angle_tried": []}, source="proof/ledger_x")
 391 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY, candidate=c)
 392 | +        out = rig.run()
 393 | +        self.assertNotIn("stories", out)
 394 | +        self.assertEqual((rig.medley_calls[0], out["tried"][0]["text"]), (["h", "z", "q"], "W"))   # its own, as judged
 395 | +
 396 | +    def test_the_file_is_read_in_its_writers_shape_or_not_at_all(self):
 397 | +        self.assertEqual(PK.read_stories(None), ([], {"path": None, "read": False, "why": "no stories file named"}))
 398 | +        st, rec = PK.read_stories("/nonexistent/stories/latest.json")
 399 | +        self.assertEqual((st, rec["read"], rec["why"]), ([], False, "no file"))
 400 | +        p = self.file([("S-1", "  Bitcoin   falls ", ["a", "b", "a"])])
 401 | +        st, rec = PK.read_stories(p)
 402 | +        self.assertEqual(st, [{"story_id": "S-1", "headline": "Bitcoin falls", "moment_ids": ["a", "b"]}])
 403 | +        self.assertEqual((rec["read"], rec["generated_at"], rec["models"], rec["stories"]),
 404 | +                         (True, "2026-11-16T13:43:27Z", self.GROUP, 1))
 405 | +        for bad in ([], {"stories": {}}, {"stories": [{"story_id": "S-1", "headline": "h", "moments": "a"}]},
 406 | +                    {"stories": [{"story_id": "S-1", "headline": " ", "moments": []}]},
 407 | +                    {"stories": [{"story_id": "", "headline": "h", "moments": []}]},
 408 | +                    {"stories": [{"story_id": "S-1", "headline": "h", "moments": [{"moment_id": 3}]}]},
 409 | +                    {"stories": [{"story_id": "S-1", "headline": "h", "moments": []}, "S-2"]}):
 410 | +            with open(p, "w") as f:
 411 | +                json.dump(bad, f)
 412 | +            st, rec = PK.read_stories(p)
 413 | +            self.assertEqual((st, rec["read"]), ([], False), bad)          # the whole file, never part of it
 414 | +        with open(p, "w") as f:
 415 | +            f.write("{")
 416 | +        self.assertEqual(PK.read_stories(p)[1]["why"], "unreadable (JSONDecodeError)")
 417 | +
 418 | +    def test_one_angle_a_story_on_its_best_passing_hook_new_channels_first_and_the_angle_contract(self):
 419 | +        pool = {m["moment_id"]: m for m in [pm("h", "A", 12.0), pm("x", "B", 14.0, rank=5.0), pm("y", "C", 13.0, rank=6.0),
 420 | +                                            pm("w", "A", 11.0, rank=9.0), pm("z", "D", 13.0)]}
 421 | +        st = [{"story_id": "S-1", "headline": "One", "moment_ids": ["h", "w", "x", "y", "gone"]},
 422 | +              {"story_id": "S-2", "headline": "Two", "moment_ids": ["h", "w", "z"]},          # two channels
 423 | +              {"story_id": "S-3", "headline": "Three", "moment_ids": ["y", "w", "z"]},        # no passing hook
 424 | +              {"story_id": "S-6", "headline": "Six", "moment_ids": ["x", "z", "gone"]},       # two cleared moments
 425 | +              {"story_id": "S-4", "headline": "Four", "moment_ids": ["h", "y", "z"]},
 426 | +              {"story_id": "S-5", "headline": "Five", "moment_ids": ["h", "y", "z"]}]         # over k
 427 | +        angles, rec = PK.story_angles(st, pool, [pool["x"], pool["h"]], k=2)               # the passing hooks, best first
 428 | +        self.assertEqual(angles, [{"angle": "One", "moments": ["x", "h", "y", "w"], "hook": "x", "story": "S-1"},
 429 | +                                  {"angle": "Four", "moments": ["h", "z", "y"], "hook": "h", "story": "S-4"}])
 430 | +        self.assertEqual((rec[0]["cleared"], rec[0]["channels"]), (4, 3))                  # "gone" is not in the pool
 431 | +        self.assertTrue(rec[1]["why"].startswith("not an angle: angle 1: >= 3 channels"), rec[1])
 432 | +        self.assertEqual(rec[2]["why"], "no passing hook among its cleared moments")
 433 | +        self.assertEqual(rec[3]["why"], "not an angle: angle 1: 3-8 distinct offered ids")     # the contract's 3
 434 | +        self.assertEqual(rec[5]["why"], "2 story angle(s) already")
 435 | +        for a in angles:                                                                  # the writer's own contract
 436 | +            PK.check_angles({"angles": [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"],
 437 | +                                         "support": {m: "s" for m in a["moments"]}}]}, pool, 1, hooks={"x", "h"})
 438 | +
 439 | +    def test_a_story_angle_chooses_only_inside_its_story(self):
 440 | +        pool = {m["moment_id"]: m for m in self.MS}
 441 | +        by = {"S-1": ["h", "x", "gone"]}
 442 | +        self.assertEqual(set(PK.story_pool({"story": "S-1"}, pool, by)), {"h", "x"})
 443 | +        self.assertEqual(PK.story_pool({"story": "S-9"}, pool, by), {})                  # a story it does not hold
 444 | +        self.assertIs(PK.story_pool({"angle": "w", "hook": "h"}, pool, by), pool)         # the writer's: as before
 445 | +
 446 | +    def test_the_story_angle_is_tried_first_and_its_line_ups_stay_inside_its_story(self):
 447 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
 448 | +        out = rig.run()
 449 | +        self.assertEqual(out["angles"][0], {"angle": "Bitcoin's own story", "moments": ["h", "x", "y"], "hook": "h",
 450 | +                                            "story": "S-1"})
 451 | +        self.assertNotIn("story", out["angles"][1])                                      # the writer's, after it
 452 | +        self.assertEqual((out["stories"]["read"], out["stories"]["angles"][0]["angle"]), (True, 1))
 453 | +        self.assertEqual(out["tried"][0]["angle"], 1)
 454 | +        mine = [r["lineup"] for r in out["tried"] if r["angle"] == 1 and r["lineup"]]
 455 | +        self.assertTrue(mine and all(set(lu) <= {"h", "x", "y"} for lu in mine), out["tried"])
 456 | +        self.assertEqual(rig.medley_calls[0], mine[0])                                    # judged first, as any line-up
 457 | +
 458 | +    def test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it(self):
 459 | +        ms = [pm("h", "A", 10.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
 460 | +        out = self.rig(ms, ["h", "z", "q", "x"], [("S-1", "A short story", ["h", "x", "y"])]).run()
 461 | +        self.assertEqual(out["angles"][0]["story"], "S-1")
 462 | +        mine = [r for r in out["tried"] if r["angle"] == 1]
 463 | +        self.assertTrue(mine)
 464 | +        for r in mine:                                    # 28 s of its own clips: no line-up, never the pool's z or q
 465 | +            self.assertIsNone(r["lineup"], r)
 466 | +            self.assertNotIn("pool_filled", r)
 467 | +
 468 | +    def test_the_join_table_of_a_story_angle_is_asked_only_of_its_story(self):
 469 | +        ids = [m["moment_id"] for m in self.MS]
 470 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY,
 471 | +                       joins={(a, b): True for a in ids for b in ids if a != b})
 472 | +        out = rig.run()
 473 | +        self.assertEqual(rig.join_calls[0], ["h", "x", "y"])                             # the story angle's: its story
 474 | +        self.assertEqual(set(rig.join_calls[1]), set(ids))                               # the writer's: the pool
 475 | +        self.assertTrue(all(set(r["lineup"]) <= {"h", "x", "y"} for r in out["tried"] if r["angle"] == 1 and r["lineup"]))
 476 | +
 477 | +    def test_the_stories_grouping_models_never_judge_its_line_ups(self):
 478 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
 479 | +        rig.router.backends["heimdall:qwen"].model = "minimax/minimax-m3.1-flash"        # a back-end running one of them
 480 | +        seen, jt = [], rig.join_table
 481 | +        rig.join_table = lambda router, ms_, c, wv, wf=None, **k: (seen.append((set(wv), set(wf or ()))),
 482 | +                                                                   jt(router, ms_, c, wv, wf, **k))[1]
 483 | +        out = rig.run()
 484 | +        self.assertEqual(out["stories"]["writers"], {"vendors": ["heimdall"], "families": ["qwen"]})
 485 | +        self.assertTrue(seen and all("heimdall" in wv and "qwen" in wf for wv, wf in seen), seen)
 486 | +
 487 | +    def test_no_file_no_story_of_three_channels_or_no_writer_builds_as_before(self):
 488 | +        out = self.rig(self.MS, ["h", "x", "y", "z", "q"], None).run()
 489 | +        self.assertEqual((out["stories"]["read"], out["stories"]["why"]), (False, "no file"))
 490 | +        self.assertTrue(all("story" not in a for a in out["angles"]))
 491 | +        ms = self.MS + [pm("w", "A", 11.0)]
 492 | +        out = self.rig(ms, ["h", "x", "y", "z", "q"], [("S-2", "Two channels", ["h", "w", "x"])]).run()
 493 | +        self.assertTrue(out["stories"]["angles"][0]["why"].startswith("not an angle"))
 494 | +        self.assertTrue(all("story" not in a for a in out["angles"]))
 495 | +        self.assertNotIn("stories", Rig(self.MS, ["h", "x", "y", "z", "q"], [(False, [], None, "none")] * 4, []).run())
 496 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
 497 | +        rig.router.answers["angle_write"] = ["{", "{"]                               # the writer gives no angle:
 498 | +        out = rig.run()                                                              # the build stops, as before
 499 | +        self.assertTrue(out["why_none"].startswith("no readable angles"))
 500 | +        self.assertEqual((out["angles"], rig.medley_calls), ([], []))
 501 | +
 502 | +    def test_a_story_angles_line_up_is_never_kept_as_a_candidate(self):
 503 | +        med = {"measured": True, "replayed": False}
 504 | +        rec = {"angle_backend": "heimdall:deepseek",
 505 | +               "angles": [{"angle": "S", "moments": ["h", "x", "y"], "hook": "h", "story": "S-1"},
 506 | +                          {"angle": "W", "moments": ["h", "x", "y", "z"], "hook": "h"}],
 507 | +               "tried": [{"angle": 1, "text": "S", "lineup": ["h", "x", "y"], "medley_ok": True, "medley": med},
 508 | +                         {"angle": 2, "text": "W", "lineup": ["h", "x", "z"], "medley_ok": True, "medley": med}]}
 509 | +        self.assertEqual(PK.load_candidate(rec)["index"], 1)                             # the writer's line-up
 510 | +        with self.assertRaisesRegex(ValueError, "story 'S-1'"):
 511 | +            PK.load_candidate(rec, 0)
 512 | +        rec["angles"][1]["story"] = "S-2"
 513 | +        with self.assertRaisesRegex(ValueError, "no line-up in this record passed"):
 514 | +            PK.load_candidate(rec)
 515 | +
 516 | +
 517 |  if __name__ == "__main__":
 518 |      unittest.main()
 519 | 
```

---

pp-selectid: RULING 118 (4) (orchestrator 05:40 ET Nov 16), STORY-FIRST LINE-UPS. Files: pipeline/package.py (read_stories,
story_angles, story_pool, story_writers, angle_source; build(); load_candidate), pipeline/candidates.py (seed),
tests/package/proof_ledger.py (the builds pass the stories file), tests/package/test_medley.py, tests/package/test_candidates.py.

THE ORDER, verbatim: "(4) STORY-FIRST LINE-UPS (the supply fix that costs nothing): what killed every line-up yesterday was
joins and no through-line, because angles were assembled from moments that only share a topic word. The receipts session
(pipeline_pi_receipts, /home/ultron/pulse_intel) now reads every moment into claims and groups the day's claims across
channels into STORIES. It will write, read-only for you, /home/ultron/pulse_intel/stories/latest.json: stories with their
moment_ids, channels and one-line headline, refreshed as moments arrive. Add an angle source that builds a line-up INSIDE
ONE STORY (hook and clips all from the same story, 3 channels), ahead of the angle writer; every gate unchanged. Until that
file exists, build as now."
THE FILE (its writer's docstring, /home/ultron/pulse_intel/stories.py): {"generated_at", "grouped_at", "window", "prompt_version",
"models": {"group": [two model ids]}, "counts", "note", "stories": [{"story_id", "headline", "channels", "n_claims",
"moments": [{"moment_id", "video_id", "channel_name", "published_at", "claims": [...]}]}]}; replaced in one step (temp file
+ rename); a moment sits in at most one story; a story is written only with claims from >= 2 channels; every 15 minutes.

THE CHANGE:
- read_stories(path): the file in that shape or not at all (no file / unreadable / any story out of shape: no stories, the
  record says why; the build goes on as before). Each story -> {story_id, headline (whitespace normalised), moment_ids}.
- story_angles(stories, cleared, passing hooks, k=MAX_ANGLES): per story (file order), its best PASSING hook among its
  cleared moments; moments = that hook, then the story's other cleared moments, a new channel first, then by rank (<= 8);
  sentence = the headline; it must pass the writer's own angle contract (check_angles, package.py:1058: 3-8 distinct
  moments, >= 3 channels, the hook one of them and a passing hook) or the story gives no angle (recorded). At most k.
- build(): only when there is no candidate (ruling 66) and a stories path: the story angles go AHEAD of the writer's angles
  (each list sorted by ruling 59/57's key as before). The writer is still asked exactly as before (its follow-up only for
  its own angles); when it gives no angle the build stops as before (the writes stay on the writer's gateway, ruling 85:
  package.py:3207). In the per-angle loop, sel = story_pool(angle, cleared, ...): a story angle's join table
  (join_moments), its fill (pool_fill) and both swaps (swap_lineup: a weak clip; a clip failing its re-screen) take
  moments ONLY from its story's cleared moments; any other angle the whole pool as before. lineup_for (package.py:1730)
  and search_lineups (package.py:2143) choose only among the angle's own moments / its join table's moments, so the story
  holds there by construction (unchanged).
- Law L-x: story_writers(): the router back-ends running the file's grouping models give their vendors and families to
  the writers' sets every verdict avoids (with the angle writer's, as before).
- angle_source(): a story angle's package records "story <id> (the stories file)" as its angle's maker (models.angle).
- A story angle's line-up is never a ruling-66 candidate (candidates.seed skips it; load_candidate refuses it and its
  first pick skips it): its angle has no writer back-end for L-x; a later build reads the story again.
- proof_ledger passes stories_path=PK.STORIES to the builds (a candidate's build ignores it).

UNCHANGED GUARDS (not in the diff): every verdict and gate after the line-up (clips-alone, coherence, fidelity, step A
re-screens, the hook bar, the render's STAND_ALONE at the pin stage package.py:1085); the loop stops at the first package
that passes every gate; the candidate loop takes angles[0] only on a candidate's build (package.py:3410).

TESTS (test_medley TestRuling118StoryFirst, 11; test_candidates, 1): the reader (shape or nothing); the angles (best
passing hook, new channels first, 2 channels refused, no passing hook, k); story_pool; the build: the story angle first and
its line-ups inside its story; a story too short is never filled from outside it; its join table asked only of its story;
both swaps inside it, and its package names the story; L-x; no file / no 3-channel story / no writer: as before; a
candidate's build reads no stories; never a candidate. Mutations S1-S18 after a control run: 18 of 18 killed.

PLEASE CHECK: (1) that a story angle can never take a hook or clip from outside its story, in any path of the loop;
(2) that nothing changes when there is no file, no story of 3 channels, or a candidate; (3) that every gate is unchanged;
(4) L-x; (5) the tests.


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
