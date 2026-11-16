# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1325
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 166 s finish=stop usage in 9436 / out 1767 usd_reported=0.000512 usd~0.055 (upper-bound price)

The code implements a fix for a defect where the `stories` file (using Ledger IDs) failed to match the current build's moments (using Build IDs).

### Analysis

1.  **Mapping Logic (`in_pool_ids`)**:
    *   The function correctly builds an index of `ledger_moment_id` $\rightarrow$ `build_id`.
    *   It handles **trimmed variants** by allowing multiple build IDs to map to a single ledger ID (`idx.setdefault(lid, []).append(mid)`).
    *   It handles **duplicates** via the `aliases` (duplicates_of) map: `idx.get(lid) or idx.get((aliases or {}).get(lid)) or []`. This ensures that if a ledger row was dropped as a duplicate, the kept row's build ID is used.
    *   It preserves the original file IDs in `ledger_ids` for auditing and ensures `moment_ids` contains only valid build IDs present in the current `cleared` pool.

2.  **Integration**:
    *   The `build` function now accepts `ledger_aliases` and applies the translation immediately after reading the stories file. This ensures that subsequent calls to `story_angles` and `story_pool` operate on the correct internal IDs.
    *   The addition of `out["stories"]["matched"]` provides the necessary telemetry to verify how many moments from the stories file were actually found in the current build.

3.  **Test Verification**:
    *   `test_the_files_ledger_ids_become_this_builds_ids` is a high-quality test. It explicitly verifies:
        *   Standard mapping.
        *   Trimmed variants (one ledger ID $\rightarrow$ multiple build IDs).
        *   Alias resolution (duplicate ledger ID $\rightarrow$ kept ledger ID $\rightarrow$ build ID).
        *   Fail-closed behavior for IDs not in the pool.
        *   The specific failure case: verifying that providing build IDs in the stories file (instead of ledger IDs) results in no match, confirming the translation is mandatory and functioning.
    *   Existing story-first tests were updated with the `ledgered()` helper to reflect the real-world data structure (`mined.ledger_moment_id`).

4.  **Governing Laws**:
    *   The change is a targeted fix for ID resolution and does not modify the Sentence Law, Selection Lock, or any rendering/QA gates.
    *   It adheres to the "Smallest diff" principle.

### Findings

No defects found. The implementation correctly resolves the ID mismatch between the receipts session and the build process.

P1_OR_WORSE: 0

## MIMO-V2.6-FLASH-RL — CYCLE 1 OUTPUT
# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 227 s finish=stop usage in 8777 / out 15016 usd_reported=0.001684 usd~0.252 (upper-bound price)

# CODE AUDIT — pp-selectid (RULING 118 (4) id translation)

Scope reviewed: `in_pool_ids` mapping semantics, the `build()` call site, the `ledger_aliases` plumbing, and the test changes. I traced the id flow described in the defect note (ledger_build.make → `mined.ledger_moment_id`, `duplicates_of` → aliases, stories file names ledger ids) against the implementation and the assertions.

---

## FINDINGS

### [P1] Nothing fails closed when a non-empty stories file translates to ZERO matches — the exact silent-death defect this ticket repairs can recur invisibly

`pipeline/package.py`, `in_pool_ids` (diff 9–29) and the call site (diff 49–51).

Every unmatched file id is dropped silently (`idx.get(lid) or idx.get(alias) or []` → `[]`), and the only signal is the new informational record `out["stories"]["matched"]` (diff 50–51), which nothing reads, asserts, or HOLDs on. Consequences:

- If `cleared` moments ever stop carrying `mined.ledger_moment_id` (a moment not re-anchored by `ledger_build.make`, a stripped `mined` dict, a schema drift), **every** story translates to `moment_ids=[]`, `story_angles` builds nothing, and the pipeline proceeds exactly as builds 41–57 did — for as long as it takes a human to notice. That is the precise failure mode this branch exists to fix, and the fix does not close it.
- Same for a future/other stories file that names *build* ids: the new test (diff 118–120) asserts `cleared: 0` as *desired* behaviour, i.e. the code is deliberately built to match nothing in that case, with no stop.
- Per M12 ("missing data … never produces a pass") and the defect history, a non-empty, successfully-read stories file whose total match count is 0 is missing data and should HOLD (or at minimum hard-fail the story-first source), not fall through to the angle writer. `matched` already carries the numbers needed for the check; the gate is simply absent.

Suggested shape: after `in_pool_ids`, if `out["stories"]["read"]` and `stories` non-empty and `sum(len(s["moment_ids"]) for s in stories) == 0` → HOLD with the `matched` record as evidence. (Partial matches are normal — moments that did not clear — so gate on the file-wide zero, not per story.)

---

### [P2] A parent moment and its trimmed variant are both indexed under the same ledger id, so one story line-up can contain two clips of the same speech

`in_pool_ids` (diff 16–20): `idx.setdefault(lid, []).append(mid)` collects **every** build id carrying the ledger id, and the docstring says "every match … each once". The test locks this in: `L1 → ["b1", "b1~trim"]` (diff 116–117).

`ledger_build` keeps a trimmed variant alive with its parent's ledger id (only *ledger rows* are deduped via `duplicates_of` — that alias path handles rows, not variants). So a story naming `L1` now yields both variants as candidate moments, and nothing in this diff (or in `story_angles`/`story_pool`, which are unchanged) shows a same-speech dedup between them. If both clear, a STORY-FIRST line-up can ship two clips of one utterance — an editorial error of the same family PBX caught by hand on 2026-11-10.

Please confirm one of: (a) downstream medley/gates reject two moments sharing a `ledger_moment_id`, or (b) only one variant is ever in `cleared` at a time, or (c) index one preferred variant (e.g. the parent) per ledger id. If none holds, this is the wrong index shape.

---

### [P2] The alias half of the fix is silently disabled for any `build()` caller that omits `ledger_aliases`

`build()` gains `ledger_aliases=None` (diff 40–41); only `tests/package/proof_ledger.py` passes it (diff 63). With the default, `in_pool_ids` still runs but `(aliases or {})` is empty, so a stories file whose ids are all *dropped duplicates* (`duplicates_of` targets) matches nothing — again silently, and again only visible in the informational `matched` record.

Since `stories_path` and `ledger_aliases` are set together or not at all, make the mismatch loud: when `stories_path` is truthy and `ledger_aliases is None`, HOLD (or at least record `aliases: "not supplied"` in `matched`). Also confirm `proof_ledger` is the *only* production caller of `build()` with `stories_path` — no other caller appears in the diff, and I cannot verify from the package that none exists.

---

### [P3] `inputs.get("duplicates_of")` will raise if `inputs` is `None`

`tests/package/proof_ledger.py` (diff 63). Every other argument in that call block is a module constant; this is the only one dereferencing `inputs`. If the harness can run with `inputs = None`, this crashes before `build()` — fail-closed, but an avoidable hard crash. Use `(inputs or {}).get("duplicates_of") or {}`.

---

### [P3] Test helper `ledgered()` replaces `mined` instead of merging into it

`tests/package/test_medley.py` (diff 75–78): `dict(m, mined={"ledger_moment_id": "L" + m["moment_id"]})` discard

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 69 s finish=stop usage in 8938 / out 2564 usd_reported=0.003123 usd~0.065 (upper-bound price)

I have reviewed the diff for `pp-selectid` against the provided context, governing laws, and the specific defect description.

### Analysis

**1. The Defect and Fix Logic**
The core issue is an ID mismatch: the `stories` file uses **Ledger IDs** (stable, from the ledger build), while the `build` pool uses **Build Moment IDs** (ephemeral, generated per build). The previous code compared them directly, resulting in zero matches.
The fix introduces `in_pool_ids`, which maps Ledger IDs to Build Moment IDs using the `mined.ledger_moment_id` field present in the pool moments. It also handles `aliases` (duplicates) where a dropped ledger row points to a kept one.

**2. Code Review: `pipeline/package.py`**

*   **`in_pool_ids` Function:**
    *   **Indexing:** `idx.setdefault(lid, []).append(mid)` correctly builds a map of `ledger_id -> [build_id, ...]`. This handles the case where multiple build moments (e.g., a parent and a trimmed variant) might share the same ledger ID.
    *   **Resolution Loop:**
        ```python
        for lid in s["moment_ids"]:
            for mid in idx.get(lid) or idx.get((aliases or {}).get(lid)) or []:
                if mid not in ids:
                    ids.append(mid)
        ```
        *   It iterates through the story's ledger IDs.
        *   It checks `idx.get(lid)` first. If the ledger ID exists directly in the pool, it uses those build IDs.
        *   If not, it checks `aliases.get(lid)`. If the ledger ID is a duplicate that was dropped, it resolves to the *kept* ledger ID and looks that up in `idx`.
        *   **Potential Issue (P2):** The logic `idx.get(lid) or idx.get((aliases or {}).get(lid))` relies on `idx.get(lid)` returning a truthy value (non-empty list) to short-circuit. If a ledger ID exists in the index but maps to an empty list (which shouldn't happen given `append`, but theoretically possible if data is malformed), it would fall through to the alias check. However, since `idx` is built by appending, values are always non-empty lists if the key exists. This is safe.
        *   **Deduplication:** `if mid not in ids` ensures unique build IDs in the output. This is correct because a single ledger ID might map to multiple build moments (e.g., original + trim), and we want all of them, but we don't want duplicates if the story lists the same ledger ID twice (unlikely, but safe) or if two different ledger IDs alias to the same kept ID which maps to the same build moment.
    *   **Output:** `dict(s, moment_ids=ids, ledger_ids=list(s["moment_ids"]))`. It preserves the original ledger IDs in `ledger_ids` for auditing/reporting (`stories.matched`) and replaces `moment_ids` with the resolved build IDs for downstream processing (`story_angles`). This is correct.

*   **`build` Function Integration:**
    *   `stories = in_pool_ids(stories, cleared, ledger_aliases)` is called immediately after `read_stories`.
    *   `cleared` is the pool of moments. The function signature `in_pool_ids(stories, pool, aliases)` matches.
    *   `out["stories"]["matched"]` is populated with diagnostic info: `ledger_ids` (count of original IDs) and `cleared` (count of resolved build IDs). This is useful for debugging the "matched nothing" issue.
    *   `story_angles(stories, cleared, passing, max_angles)` is called with the *translated* stories. This is the critical fix.

*   **`ledger_aliases` Parameter:**
    *   Added to `build` signature.
    *   Passed from `proof_ledger.py` as `inputs.get("duplicates_of") or {}`. This correctly sources the alias map from the ledger build report.

**3. Code Review: `tests/package/proof_ledger.py`**
*   Passes `ledger_aliases=inputs.get("duplicates_of") or {}`. This is correct. The `duplicates_of` map in the ledger report is exactly the `aliases` needed.

**4. Code Review: `tests/package/test_medley.py`**
*   **`ledgered` Helper:** Creates moments with `mined.ledger_moment_id` set to `"L" + moment_id`. This simulates the real-world scenario where build IDs differ from ledger IDs.
*   **Test Updates:**
    *   `MS` and `STORY` are updated to use `ledgered` moments and ledger IDs (`"Lh"`, etc.) in the story file.
    *   `test_the_files_ledger_ids_become_this_builds_ids`:
        *   Constructs a pool with explicit `ledger_moment_id` values (`"L1"`, `"L2"`).
        *   Includes a duplicate scenario: `"Ldup"` aliases to `"L2"`.
        *   Story has `moment_ids: ["L3", "Ldup", "L1", "L2"]`.
        *   Expected `moment_ids` in output: `["b2", "b1", "b1~trim"]`.
            *   `"L3"`: Not in pool, not in aliases. Resolves to `[]`.
            *   `"Ldup"`: Not in pool. Alias to `"L2"`. `"L2"` is in pool (`"b2"`). Resolves to `["b2"]`.
            *   `"L1"`: In pool (`"b1"`, `"b1~trim"`). Resolves to `["b1", "b1~trim"]`.
            *   `"L2"`: In pool (`"b2"`). Resolves to `["b2"]`.
            *   Combined & Deduped: `["b2",

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_1325 (the story-first id defect)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0,
gemma 0, mimo 1. Cycle 1 $0.0053 of Heimdall, not capped.

mimo's P1 ("a read stories file that translates to ZERO matches is silent again"): RIGHT ABOUT THE SILENCE, and taken in a
loud form, not a HOLD. A file-wide zero of CLEARED matches is normal (story moments held at step A, refused, not
cuttable: today's S-533ed7f7 has Fox not cuttable and What Bitcoin Did held), and story-first is an extra angle source
beside the writer's: a HOLD would stop builds the file has nothing to do with. What signals an id mismatch is a zero in
the WHOLE POOL. CHANGED (in cycle 2's diff): stories.matched gives each story's ids found in this build's pool at all
(in_pool, through mined.ledger_moment_id or the duplicates alias) beside those cleared; when a read file with stories has
in_pool 0 for every story, stories.warning says "NO ID OF THE STORIES FILE NAMES A MOMENT OF THIS BUILD'S POOL: an id
mismatch? story-first cannot fire" and the build log prints it (builds 41-57 would have said so at 09:59). Tests: a file
naming build ids: warning, in_pool 0; the file's ledger ids: in_pool 3, cleared 3, no warning. Mutation T4 (the warning
silent).
mimo's P2 (a parent and its trimmed variant share a ledger id; both indexed): both may be in a story's pool, never in one
line-up: every segment needs its own video (lineup_for, package.py:1764, unchanged: len of the video ids == clips + 1), and a
variant shares its parent's video. Not changed.
mimo's P2 (ledger_aliases omitted by a caller): proof_ledger is the only caller that passes stories_path; the record now
says stories.aliases = how many, or "not supplied" (tested). mimo's P3 (inputs None): build_inputs returns its report
dict always (ledger_build.py:598); not changed. qwen's P2 (order): file order, then the pool's insertion order:
deterministic; not changed.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_1325/C2_STEP.diff (161 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5ae1e1b..52c1dfe 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -2017,6 +2017,29 @@ def read_stories(path):
   6 |                       models=d.get("models"), stories=len(out))
   7 |  
   8 |  
   9 | +def in_pool_ids(stories, pool, aliases=None):
  10 | +    """RULING 118 (4), the ids: the stories file names each moment by the LEDGER's id (the receipts session reads the
  11 | +    ledger), and this build's moments carry that id as mined.ledger_moment_id (ledger_build: each moment gets its own
  12 | +    id; a trimmed variant keeps its parent's ledger id). A ledger row the ledger build dropped as the same speech as
  13 | +    another (ledger_build's duplicates_of: its id -> the kept row's id, `aliases`) stands for the kept one. -> the
  14 | +    stories with moment_ids in this build's own ids (every match, in the file's order, each once) and the file's own
  15 | +    ids kept as ledger_ids. Builds 41-57 matched nothing: they compared the two kinds of id directly."""
  16 | +    idx = {}
  17 | +    for mid, m in pool.items():
  18 | +        lid = (m.get("mined") or {}).get("ledger_moment_id")
  19 | +        if lid:
  20 | +            idx.setdefault(lid, []).append(mid)
  21 | +    out = []
  22 | +    for s in stories:
  23 | +        ids = []
  24 | +        for lid in s["moment_ids"]:
  25 | +            for mid in idx.get(lid) or idx.get((aliases or {}).get(lid)) or []:
  26 | +                if mid not in ids:
  27 | +                    ids.append(mid)
  28 | +        out.append(dict(s, moment_ids=ids, ledger_ids=list(s["moment_ids"])))
  29 | +    return out
  30 | +
  31 | +
  32 |  def story_angles(stories, cleared, hooks, k=MAX_ANGLES):
  33 |      """RULING 118 (4), STORY-FIRST LINE-UPS: angles built INSIDE ONE STORY (its hook and every clip from the same story),
  34 |      tried ahead of the angle writer's; every gate unchanged. For each story in the file's order, the best of `hooks`
  35 | @@ -2846,7 +2869,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  36 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  37 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  38 |            join_cache=None,
  39 | -          visual_cache=None, registered=None, lock_check=None, scorer_extra=(), stories_path=None):
  40 | +          visual_cache=None, registered=None, lock_check=None, scorer_extra=(), stories_path=None,
  41 | +          ledger_aliases=None):
  42 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  43 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  44 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  45 | @@ -3137,6 +3161,18 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  46 |      stories, s_angles, s_writers = [], [], (set(), set())
  47 |      if candidate is None and stories_path:           # RULING 118 (4): STORY-FIRST LINE-UPS, ahead of the angle writer
  48 |          stories, out["stories"] = read_stories(stories_path)
  49 | +        stories = in_pool_ids(stories, cleared, ledger_aliases)   # the file's ledger ids -> this build's ids
  50 | +        pool_lids = {(m.get("mined") or {}).get("ledger_moment_id") for m in moments} - {None}
  51 | +        alias = ledger_aliases or {}
  52 | +        out["stories"]["matched"] = [{"story_id": s["story_id"], "ledger_ids": len(s["ledger_ids"]),
  53 | +                                      "in_pool": sum(1 for x in s["ledger_ids"] if x in pool_lids or
  54 | +                                                     alias.get(x) in pool_lids),
  55 | +                                      "cleared": len(s["moment_ids"])} for s in stories]
  56 | +        out["stories"]["aliases"] = len(alias) if ledger_aliases is not None else "not supplied"
  57 | +        if stories and not any(r["in_pool"] for r in out["stories"]["matched"]):     # audit 1325 C1 (mimo): never
  58 | +            out["stories"]["warning"] = ("NO ID OF THE STORIES FILE NAMES A MOMENT OF THIS BUILD'S POOL: an id "  # silent
  59 | +                                         "mismatch? story-first cannot fire")
  60 | +            log(f"  RULING 118 (4): {out['stories']['warning']}")
  61 |          s_angles, out["stories"]["angles"] = story_angles(stories, cleared, passing, max_angles)
  62 |          if s_angles:                                  # law L-x: the grouping models chose the story's moments
  63 |              s_writers = story_writers(router, out["stories"].get("models"))
  64 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  65 | index ed044d9..ec6d16f 100644
  66 | --- a/tests/package/proof_ledger.py
  67 | +++ b/tests/package/proof_ledger.py
  68 | @@ -482,6 +482,7 @@ def main(argv=None):
  69 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
  70 |                scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
  71 |                stories_path=PK.STORIES,                                             # ruling 118 (4): read only
  72 | +              ledger_aliases=inputs.get("duplicates_of") or {},    # its ledger ids: a dropped duplicate -> the kept row
  73 |                visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
  74 |                lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
  75 |                    segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
  76 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  77 | index abf864c..4e1f1b8 100644
  78 | --- a/tests/package/test_medley.py
  79 | +++ b/tests/package/test_medley.py
  80 | @@ -4473,13 +4473,19 @@ class TestRuling109Channels(unittest.TestCase):
  81 |          self.assertNotIn("ruling_109", out)
  82 |  
  83 |  
  84 | +def ledgered(*ms):
  85 | +    """The pool's moments as ledger_build makes them: each with its own id and the LEDGER's id kept as
  86 | +    mined.ledger_moment_id ("L" + its id here), the id the stories file names (ruling 118 (4))."""
  87 | +    return [dict(m, mined={"ledger_moment_id": "L" + m["moment_id"]}) for m in ms]
  88 | +
  89 | +
  90 |  class TestRuling118StoryFirst(unittest.TestCase):
  91 |      """RULING 118 (4) (orchestrator 05:40 ET Nov 16), STORY-FIRST LINE-UPS: an angle source that builds a line-up INSIDE
  92 |      ONE STORY (the hook and every clip from the same story, 3 channels), ahead of the angle writer, every gate unchanged;
  93 |      the receipts session's stories file is read only; no file: the build as before."""
  94 |      GROUP = {"group": ["deepseek/deepseek-v4.1-flash", "minimax/minimax-m3.1-flash"]}
  95 | -    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
  96 | -    STORY = [("S-1", "Bitcoin's own story", ["h", "x", "y", "gone"])]
  97 | +    MS = ledgered(pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0))
  98 | +    STORY = [("S-1", "Bitcoin's own story", ["Lh", "Lx", "Ly", "Lgone"])]     # the file names LEDGER ids
  99 |  
 100 |      def file(self, stories, models=GROUP):
 101 |          d = tempfile.mkdtemp()
 102 | @@ -4499,8 +4505,8 @@ class TestRuling118StoryFirst(unittest.TestCase):
 103 |          return rig
 104 |  
 105 |      def test_every_swap_of_a_story_line_up_stays_inside_its_story(self):
 106 | -        ms = self.MS + [pm("w", "F", 13.0, rank=5.0)]                     # in the story, ranked under the pool's z, q
 107 | -        story = [("S-1", "Bitcoin's own story", ["h", "x", "y", "w"])]
 108 | +        ms = self.MS + ledgered(pm("w", "F", 13.0, rank=5.0))             # in the story, ranked under the pool's z, q
 109 | +        story = [("S-1", "Bitcoin's own story", ["Lh", "Lx", "Ly", "Lw"])]
 110 |          rig = self.rig(ms, ["h", "x", "y", "z", "q"], story)               # a weak clip: swapped inside the story
 111 |          rig.medleys = [(False, [], {"clip_02": 2}, Rig.LINE)] + [(False, [], None, "none")] * 6
 112 |          out = rig.run()
 113 | @@ -4526,6 +4532,25 @@ class TestRuling118StoryFirst(unittest.TestCase):
 114 |          self.assertNotIn("stories", out)
 115 |          self.assertEqual((rig.medley_calls[0], out["tried"][0]["text"]), (["h", "z", "q"], "W"))   # its own, as judged
 116 |  
 117 | +    def test_the_files_ledger_ids_become_this_builds_ids(self):
 118 | +        """The receipts session names the LEDGER's ids; this build's moments carry them as mined.ledger_moment_id (a
 119 | +        trimmed variant its parent's), and a ledger row dropped as a duplicate of a kept one stands for the kept one.
 120 | +        Builds 41-57 compared the two kinds of id directly and matched nothing."""
 121 | +        pool = {"b1": {"mined": {"ledger_moment_id": "L1"}}, "b1~trim": {"mined": {"ledger_moment_id": "L1"}},
 122 | +                "b2": {"mined": {"ledger_moment_id": "L2"}}, "b4": {}}
 123 | +        st = PK.in_pool_ids([{"story_id": "S", "headline": "h", "moment_ids": ["L3", "Ldup", "L1", "L2"]}], pool,
 124 | +                            {"Ldup": "L2"})
 125 | +        self.assertEqual(st, [{"story_id": "S", "headline": "h", "moment_ids": ["b2", "b1", "b1~trim"],
 126 | +                               "ledger_ids": ["L3", "Ldup", "L1", "L2"]}])
 127 | +        out = self.rig(self.MS, ["h", "x", "y", "z", "q"], [("S-1", "By build ids", ["h", "x", "y"])]).run()
 128 | +        self.assertEqual(out["stories"]["matched"], [{"story_id": "S-1", "ledger_ids": 3, "in_pool": 0, "cleared": 0}])
 129 | +        self.assertTrue(all("story" not in a for a in out["angles"]))          # build ids are not the file's ids
 130 | +        self.assertIn("NO ID OF THE STORIES FILE NAMES A MOMENT OF THIS BUILD'S POOL", out["stories"]["warning"])
 131 | +        self.assertEqual(out["stories"]["aliases"], "not supplied")              # the rig passes no ledger_aliases
 132 | +        out = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY).run()     # the file's ledger ids: matched,
 133 | +        self.assertEqual(out["stories"]["matched"], [{"story_id": "S-1", "ledger_ids": 4, "in_pool": 3, "cleared": 3}])
 134 | +        self.assertNotIn("warning", out["stories"])                               # no warning
 135 | +
 136 |      def test_the_file_is_read_in_its_writers_shape_or_not_at_all(self):
 137 |          self.assertEqual(PK.read_stories(None), ([], {"path": None, "read": False, "why": "no stories file named"}))
 138 |          st, rec = PK.read_stories("/nonexistent/stories/latest.json")
 139 | @@ -4589,8 +4614,8 @@ class TestRuling118StoryFirst(unittest.TestCase):
 140 |          self.assertEqual(rig.medley_calls[0], mine[0])                                    # judged first, as any line-up
 141 |  
 142 |      def test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it(self):
 143 | -        ms = [pm("h", "A", 10.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
 144 | -        out = self.rig(ms, ["h", "z", "q", "x"], [("S-1", "A short story", ["h", "x", "y"])]).run()
 145 | +        ms = ledgered(pm("h", "A", 10.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 13.0), pm("q", "E", 13.0))
 146 | +        out = self.rig(ms, ["h", "z", "q", "x"], [("S-1", "A short story", ["Lh", "Lx", "Ly"])]).run()
 147 |          self.assertEqual(out["angles"][0]["story"], "S-1")
 148 |          mine = [r for r in out["tried"] if r["angle"] == 1]
 149 |          self.assertTrue(mine)
 150 | @@ -4621,8 +4646,8 @@ class TestRuling118StoryFirst(unittest.TestCase):
 151 |          out = self.rig(self.MS, ["h", "x", "y", "z", "q"], None).run()
 152 |          self.assertEqual((out["stories"]["read"], out["stories"]["why"]), (False, "no file"))
 153 |          self.assertTrue(all("story" not in a for a in out["angles"]))
 154 | -        ms = self.MS + [pm("w", "A", 11.0)]
 155 | -        out = self.rig(ms, ["h", "x", "y", "z", "q"], [("S-2", "Two channels", ["h", "w", "x"])]).run()
 156 | +        ms = self.MS + ledgered(pm("w", "A", 11.0))
 157 | +        out = self.rig(ms, ["h", "x", "y", "z", "q"], [("S-2", "Two channels", ["Lh", "Lw", "Lx"])]).run()
 158 |          self.assertTrue(out["stories"]["angles"][0]["why"].startswith("not an angle"))
 159 |          self.assertTrue(all("story" not in a for a in out["angles"]))
 160 |          self.assertNotIn("stories", Rig(self.MS, ["h", "x", "y", "z", "q"], [(False, [], None, "none")] * 4, []).run())
 161 | 
```

---

pp-selectid: A DEFECT IN RULING 118 (4)'S STORY-FIRST SOURCE (live since 1571b7b9, 09:59 ET Nov 16), found at 13:25 ET when
the first 3-channel story appeared. Files: pipeline/package.py (in_pool_ids; build() translates the file's ids;
build()'s new kwarg ledger_aliases), tests/package/proof_ledger.py (passes the ledger build's duplicates_of),
tests/package/test_medley.py.

THE DEFECT: the receipts session's stories file (/home/ultron/pulse_intel/stories/latest.json) names each moment by the
LEDGER's id; this build's moments have their OWN ids (ledger_build.build_inputs: make() gives each re-anchored moment a
new moment_id and keeps the ledger's as mined.ledger_moment_id, pipeline/ledger_build.py:483; a row dropped as the same
speech as a kept row is named in the report's duplicates_of: its ledger id -> the kept row's ledger id,
ledger_build.py:524 and :563). story_angles matched the file's ids against cleared[moment_id] directly: never a match,
so no story angle could ever be built. Seen on build 57's record: the story S-533ed7f7 (3 channels) names ledger ids
533ed7f7..., 917df8e9..., 74f60d1a...: no build moment has them as moment_id; moments[134] carries 533ed7f7 as
mined.ledger_moment_id. The tests had used one id for both.

THE FIX: in_pool_ids(stories, pool, aliases): an index ledger id -> every build id carrying it (mined.ledger_moment_id; a
trimmed variant keeps its parent's), a dropped duplicate's ledger id standing for the kept one (aliases =
duplicates_of); each story's moment_ids become this build's ids (file order, each once), its own kept as ledger_ids.
build() applies it to the stories read, right after read_stories, on `cleared`; the record gains stories.matched (per
story: the file's ids, how many are cleared here). story_angles, story_pool and every gate are unchanged.
proof_ledger passes ledger_aliases=inputs["duplicates_of"] (the report build_inputs returns).

TESTS: in_pool_ids (variants, duplicates, unknown ids, order); every story-first build test now gives its moments
ledger ids distinct from their own and names the ledger ids in the stories file; a file naming build ids matches
nothing. Mutations T1-T3 (no translation; aliases ignored; one build id a ledger id) beside S1-S18, after a control run.

PLEASE CHECK: (1) the mapping (variants, duplicates, ids not in the pool); (2) that nothing else changed; (3) the tests.


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
