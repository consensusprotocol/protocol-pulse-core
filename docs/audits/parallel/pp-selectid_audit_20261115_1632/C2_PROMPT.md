# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1632
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 61 s finish=stop usage in 18110 / out 959 usd_reported=0.041576 usd~0.115 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1632 (RULING 117 join-table + search)**

**Summary of compliance**
- The change implements exactly the verbatim order in the orchestrator ruling (build join table once per angle on cleared/CUTTABLE moments, Grok-only via "coherence_verdict:joins", cached by text+JOINS_VERSION, 25-pair batches, strict contract parse, search over all qualifying permutations with lineup_ok + at-most-1-flagged, ratings-aware ordering, hook-first, fallback to existing lineup_for when table absent or search empty, verdict still decides, agreement stats recorded).
- JOIN_QUESTION is identical to the clips-alone verdict's join sentence (verified in test); MEDLEY_PROMPT itself is untouched → calibration, version hash, and "one bridge" law are preserved.
- All governing laws are respected: SELECTION_LOCK / SNAP_LIMIT / NEIGHBOUR / ONSET/TAIL / L-b / L-c / L-e / L-g / L-h / L-i / L-j / L-k / L-l / M12 / LAW-20 / LAW-22 are either upstream of this selection stage or untouched. No cut points are recomputed, no edge-word fidelity gates are relaxed, no model is allowed to decide sentence boundaries, fail-closed behavior is maintained on parse errors / provider errors / empty tables / out-of-contract replies, canon.py route is used for text_sha, v2f reference is protected via proof JOIN_CACHE that forces old writer-order behavior on reference inputs.
- No new renderer, compositor, TTS, lip-sync, or publishing path. GPU0-only constraint is irrelevant here. Every new DB-adjacent structure (cache) follows existing _load_cache/_cache_put pattern.
- Tests (TestRuling117JoinSearch + updates to proof_ledger / Rig) are thorough: 12 cases cover once-per-ordered-pair, hook-never-B, batching, cache filtering by today's joins list, out-of-contract chunks, unanswered pairs counted as flagged, ratings bias, dropped clips after low verdict, fallback when table empty, agreement recording, mutation coverage 14/14. Suite passes, must-fail/must-pass cases for other L-* laws unaffected.

**Findings**

[P1] Violates "no new selector (M1)" and "Smallest diff". search_lineups + join_table constitute a new combinatorial selector (permutations + multi-criteria sort over join table) and add >100 LOC of new control flow inside build(). While it implements ruling 117 and falls back to lineup_for, the governing laws explicitly prohibit new selectors. The intent (better joins to address D6 abrupt changes) is sound, but the implementation breaches the "M1" line that every other law references as immutable.

[P2] itertools.permutations is used in search_lineups but the diff does not add an import (nor "from itertools import permutations"). If the module top-level does not already contain it, this is a runtime NameError on first angle. (Tests import indirectly via PK but production path is exposed.)

[P2] join_table builds the full join table for up to 8 moments (49 pairs) on every angle before any lineup is judged. With MAX_ANGLES and lineups=8 this can be 300–400 model calls per package in worst-case fresh builds. The ruling says "DO NOT LOOSEN" but does not address the new spend / latency budget; existing spend() callback is not charged for these calls.

[P3] Cache key uses only text_sha(a['text']) + JOINS_VERSION. Per L-k / L-h a canon-normalized spoken form is used, but any future change to speaker name, channel alias, or metadata that the prompt includes but the key ignores will produce spurious cache hits. Existing caches (step_a_cache, hook_cache) have the same pattern, but this new one amplifies it.

[P3] Long embedded ruling text and docstrings duplicate the orchestrator comments already present in model_providers.json and the commit message. Increases diff size with no functional gain (style is consistent with rest of codebase but still violates "Smallest diff").

[P3] In build(), a_ratings and dropped are updated only on measured clips-alone failures. A coherence-only failure that still returns clip ratings is ignored for search pruning; the ruling does not specify this corner case.

**Conclusion**
The implementation is careful, well-tested, fail-closed where required, and preserves every editorial law and reference render. The only blocking issues are the explicit M1 prohibition on new selectors and the missing import. After those two fixes the change would be mergeable under the governing laws.

P1_OR_WORSE: 3

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 48 s finish=stop usage in 20029 / out 3358 usd_reported=0.003326 usd~0.110 (upper-bound price)

I will begin by analyzing the provided code diff against the "Governing Laws" and the specific instructions for RULING 117.

### Analysis of `pipeline/package.py`

**1. `join_table` Function (Lines 73-138)**
*   **Law L-l (Model Reply Counts Only Whole):** The `parse` function (lines 118-125) strictly validates the JSON structure. It checks that the top-level key is `pairs`, that the set of keys matches the expected `want` (the pairs in the current chunk), and that each value is a dict with exactly `followable` (bool) and `why` (str). If any check fails, it raises `ValueError`. This is caught in the `except` block (line 130), which records an error and continues to the next chunk. This complies with L-l: an out-of-contract reply is treated as a failure, not a pass.
*   **Law M12 (Fail Closed):** If `router.chain` fails or returns an empty list, `listed` becomes `set()`. The cache lookup (line 101) requires `name in listed`. If `listed` is empty, no cached entries are used, and new calls are made. If the call fails, `err` is set. The function returns `out` (which may be partial) and `err`. The caller (`build`) handles `err` by logging it. If the table is empty or partial, the search logic handles missing pairs as "flagged" (see below). This is fail-closed.
*   **Caching:** The cache key is `text_sha(a['text']):text_sha(b['text']):JOINS_VERSION`. This ensures that if the text of a clip changes, the old cache entry is not used. The `JOINS_VERSION` is a hash of the prompt, ensuring that if the prompt changes, the cache is invalidated. This is robust.
*   **Concurrency:** The function uses `ThreadPoolExecutor`? No, it iterates sequentially over chunks. This is fine for correctness, though potentially slow. However, the prompt says "batched in one call where the contract allows". The code batches 25 pairs per call. This is acceptable.

**2. `search_lineups` Function (Lines 141-173)**
*   **Law L-m (One Bridge):** The function enforces `LY_MAX_BRIDGES`. The prompt states "at most one flagged join". The code checks `if nf > LY_MAX_BRIDGES`. I need to verify `LY_MAX_BRIDGES` is 1. The diff doesn't show the definition, but the test `test_the_search_every_order_the_rules_and_at_most_one_flagged_join` asserts that lineups with 2 flagged joins are not offered. The logic `flagged = lambda a, b: (a, b) in bad_pairs or (table.get((a, b)) or {}).get("followable") is not True` correctly identifies a join as flagged if:
    1.  It was flagged by a previous verdict (`bad_pairs`).
    2.  The table says it is *not* followable (`followable` is `False`).
    3.  The table has *no answer* for it (`table.get((a, b))` is `None`, so `.get("followable")` is `None`, which is `not True`).
    This complies with the instruction: "a join is flagged when the table finds it unfollowable, when the table has no answer for it, or when a verdict of this build flagged it".
*   **Search Space:** It iterates over permutations of `others` of length `n` where `n` is in `range(LY_CLIPS[0], LY_CLIPS[1] + 1)`. The prompt says "2-4 clips". Assuming `LY_CLIPS` is `(2, 4)`, this is correct.
*   **Constraints:** It checks `lineup_ok(segs, repeat_ok=repeat_ok)[0]`. This ensures the standard rules (channel, duration, etc.) are applied.
*   **Sorting:** It sorts by `(nf, -min(rs), -sum(rs) / len(rs), moves)`.
    *   `nf`: Fewest flagged joins (primary).
    *   `-min(rs)`: Highest minimum rating (secondary). The prompt says "highest clip ratings first". Using the minimum rating as the primary sort key for quality is a conservative approach (bottleneck).
    *   `-sum(rs) / len(rs)`: Highest mean rating (tertiary).
    *   `moves`: Fewest moves from writer's order (quaternary).
    This ordering seems reasonable and aligns with "Best first: the fewest flagged joins, then the highest clip ratings... then the writer's play order kept".

**3. `build` Function Integration (Lines 200-280)**
*   **Table Construction:** The table is built *before* the lineup selection loop. `jms` is constructed from `cleared` moments. `cleared` is defined in the prompt as "moments that passed step A... and CUTTABLE". The code uses `cleared[m]`. This matches.
*   **Fallback Logic:**
    *   If `jt` (join table) is empty or `search_lineups` returns nothing, it falls back to `lineup_for` (the old behavior).
    *   Code: `if swapped is None and segs is None: ... segs, exception = lineup_for(...)`.
    *   This complies with "With no table... or no line-up left in the search, the line-up is chosen as before".
*   **Verdict Handling:**
    *   After a verdict, if `not ok_m` (failed), it updates `a_ratings` and `dropped`.
    *   It then calls `search_lineups` again to find the next best lineup.
    *   If found, it sets `swapped` and `continue`s the loop.
    *   This complies with "after a failed verdict, the search's next line-up is asked".
*   **Agreement Re

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1632 (RULING 117 (2)+(3): the join table and the search)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of tokens (finish=length, no answer), so Grok
was asked (P1_OR_WORSE: 3, one finding tagged P1, two P2 it calls blocking). Cycle 1: $0.0490 vendor-reported.

GROK'S BLOCKING POINTS, each checked against the code:
1. [P1] "A new selector, against M1 (no new renderer / compositor / selector)". NOT A DEFECT: the search is the
   orchestrator's own order (ruling 117 (2): "choose the order BY SEARCH over the table ... No model call in the
   search"). It lives INSIDE the existing line-up stage of package.build, beside lineup_for, reorder (ruling 63) and
   swap_lineup (ruling 41), and replaces the trial-and-error reordering ruling 63 did with paid verdicts; it adds no
   pipeline stage, no module, no render path, and the clips-alone and coherence verdicts still decide every line-up.
2. [P2, "blocking"] "itertools.permutations without an import". REFUTED: pipeline/package.py:54 `import itertools`
   (module top; reorder() has used itertools.permutations since ruling 63).
3. [P2] "300-400 model calls per package". REFUTED by arithmetic: at most 8 moments an angle = 49 ordered pairs (the
   hook never second), 25 pairs a call = 2 calls an angle, MAX_ANGLES 3 = at most 6 calls a build, and every answer is
   cached by the two texts for every later build. "Not charged": every call goes through the build's own router,
   whose spend ledger is the batch ledger (tests/package/proof_ledger.py:217-221, spend_path=PL.SPEND), read by the
   build's budget guards (over_budget, ruling 41's per-build cap).

P3s noted: the cache key carries the two texts and the question's version, not the on-screen names (the hook cache's
rule too; a channel renamed would need a new key); the docstrings; a coherence-only failure does not prune the search
(the ruling names the clips-alone verdict's joins; coherence has no joins).

CHANGED AFTER CYCLE 1 (in this cycle 2's diff): the order's set for the table is "the hook and the clips that passed
step A from both vendors, the second pass and CUTTABLE; cap 8 moments an angle", which is the CLEARED POOL, not only
the writer's own 3-4 picks. build() now asks the table of the angle's hook, its writer's other moments, then the rest
of the cleared pool by rank score, at most 8 (ext = the angle with those moments; the search keeps the writer's order
first by its fewest-moves rule). New test: the table's moments are the hook, the writer's picks, then the pool, capped
at 8. 13 tests in TestRuling117JoinSearch; all 40 suite files pass.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1632/C2_STEP.diff (554 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index c071828..57c2e64 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -372,6 +372,9 @@
   6 |     "coherence_verdict:hook": [
   7 |      "xai:grok-4.20-0309-reasoning"
   8 |     ],
   9 | +   "coherence_verdict:joins": [
  10 | +    "xai:grok-4.20-0309-reasoning"
  11 | +   ],
  12 |     "coherence_verdict:clips_alone": [
  13 |      "xai:grok-4.20-0309-reasoning",
  14 |      "google:gemini-2.5-pro"
  15 | @@ -393,6 +396,9 @@
  16 |     "coherence_verdict:hook": [
  17 |      "xai:grok-4.20-0309-reasoning"
  18 |     ],
  19 | +   "coherence_verdict:joins": [
  20 | +    "xai:grok-4.20-0309-reasoning"
  21 | +   ],
  22 |     "coherence_verdict": [
  23 |      "xai:grok-4.20-0309-reasoning",
  24 |      "google:gemini-2.5-pro",
  25 | @@ -460,9 +466,13 @@
  26 |     ],
  27 |     "coherence_verdict:hook": [
  28 |      "xai:grok-4.20-0309-reasoning"
  29 | +   ],
  30 | +   "coherence_verdict:joins": [
  31 | +    "xai:grok-4.20-0309-reasoning"
  32 |     ]
  33 |    },
  34 |    "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first.",
  35 | +  "ruling_117": "RULING 117 (orchestrator 16:24 ET Nov 15): the JOIN TABLE (package.join_table: the clips-alone verdict's join question once per ordered pair of an angle's moments) is asked of GROK alone, the calibrated rater, in every routing (no other model fills it; a pair with no answer counts as flagged in the search).",
  36 |    "ruling_115": "RULING 115 (orchestrator 13:24 ET Nov 15), amending 85 / 88 / 96 for the HOOK only: the hook job is asked ALONE (one candidate a call) at production's seed by GROK, and Grok alone, in every routing (heimdall_first, today, plan_b): the calibrated floors (pipeline/hook_calibration.json, hook_bar.py) are Grok's, so no other model may decide a hook while Grok is out (no rating = no hook, law L-m). qwen answers every hook in SHADOW (recorded, never deciding; proof_ledger: shadow 'coherence_verdict:hook'). A hook passes when each of scroll / alone / setup is at least its floor.",
  37 |    "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
  38 |    "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged.",
  39 | diff --git a/pipeline/package.py b/pipeline/package.py
  40 | index 6be44e4..7a058ff 100644
  41 | --- a/pipeline/package.py
  42 | +++ b/pipeline/package.py
  43 | @@ -1015,6 +1015,25 @@ MEDLEY_VERSION = hashlib.sha256(MEDLEY_PROMPT.encode()).hexdigest()[:12]
  44 |  COHERENCE_VERSION = hashlib.sha256(COHERENCE_PROMPT.encode()).hexdigest()[:12]   # valid for exactly these questions
  45 |  STANDARD_LINEUP = {"clips_alone": {"clip": COHERENCE_MIN}, "coherence": {"clip": COHERENCE_MIN,
  46 |                                                                           "vo_point": COHERENCE_MIN}}
  47 | +JOIN_QUESTION = ("could a viewer follow the jump with no narration, i.e. is the next clip's subject or referent clear "
  48 | +                 "coming from the previous clip's ending?")   # RULING 117: the clips-alone verdict's own join question
  49 | +JOINS_PROMPT = """You judge JOINS between clips of 60-second videos made of other channels' own words (each clip is a
  50 | +person's own words from a show; the shows were not in one conversation). In each PAIR, clip A plays and clip B follows
  51 | +it at once, with NO narration between them. Judge each pair ALONE: the pairs are not one video, and nothing else plays
  52 | +before or between A and B.
  53 | +
  54 | +THE CLIPS:
  55 | +{clips}
  56 | +
  57 | +THE PAIRS (A -> B):
  58 | +{pairs}
  59 | +
  60 | +For EACH pair, the join question (the previous clip is A, the next clip is B): """ + JOIN_QUESTION + """ Answer
  61 | +"followable": true or false, and "why": a few words.
  62 | +Return ONLY this JSON object: {{"pairs": {{{keys}}}}}"""
  63 | +JOINS_VERSION = hashlib.sha256(JOINS_PROMPT.encode()).hexdigest()[:12]   # a cached join is for exactly this question
  64 | +JOIN_MOMENTS_MAX = 8                 # ruling 117: the hook and its angle's other moments, at most 8 an angle
  65 | +JOIN_PAIRS_PER_CALL = 25             # pairs a call (one item a pair)
  66 |  #   the standard bar: every verdict not given by the calibrated rater, and every verdict while the file is invalid
  67 |  
  68 |  
  69 | @@ -1917,6 +1936,109 @@ def reorder(segs, bad_pairs, judged, repeat_ok=False):
  70 |      return best[1] if best else None
  71 |  
  72 |  
  73 | +def join_table(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
  74 | +    """RULING 117 (2): the JOIN TABLE. The clips-alone verdict's own join question (JOIN_QUESTION) asked ONCE per ordered
  75 | +    pair of `ms` (the angle's hook first, then its other moments; at most JOIN_MOMENTS_MAX; the hook is never B), one
  76 | +    pair an item, JOIN_PAIRS_PER_CALL pairs a call, on coherence_verdict's "joins" list (Grok, the calibrated rater),
  77 | +    never the writers' vendor or family. Cached (`cache`, shared by every build) by the two texts and JOINS_VERSION;
  78 | +    only a back-end on today's joins list answers from it. A reply out of contract moves on (providers.call_parsed).
  79 | +    -> ({(a id, b id): {"followable", "why", "backend", "cached"}}, the first error or None). A pair no call answered has
  80 | +    no entry: the search counts it as flagged (law L-m)."""
  81 | +    import providers as P
  82 | +    ms = list(ms)[:JOIN_MOMENTS_MAX]
  83 | +    if len(ms) < 2:
  84 | +        return {}, None
  85 | +    wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
  86 | +    off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
  87 | +    try:
  88 | +        listed = set(router.chain("coherence_verdict", "joins"))
  89 | +    except AttributeError:                       # a stand-in router without chain(): any back-end off the writers
  90 | +        listed = None
  91 | +    except P.ProviderError:                      # no joins list: no cached join answers (fail closed)
  92 | +        listed = set()
  93 | +    key = lambda a, b: f"{text_sha(a['text'])}:{text_sha(b['text'])}:{JOINS_VERSION}"
  94 | +    cdb, out, todo = _load_cache(cache), {}, []
  95 | +    for a in ms:
  96 | +        for b in ms[1:]:
  97 | +            if a is b:
  98 | +                continue
  99 | +            rec = next((x for name, x in sorted((cdb.get(key(a, b)) or {}).items())
 100 | +                        if isinstance(x, dict) and off(name) and x.get("backend") == name and
 101 | +                        (listed is None or name in listed) and type(x.get("followable")) is bool), None)
 102 | +            if rec is not None:
 103 | +                out[(a["moment_id"], b["moment_id"])] = dict(rec, cached=True)
 104 | +            else:
 105 | +                todo.append((a, b))
 106 | +    new, err = {}, None
 107 | +    for i in range(0, len(todo), JOIN_PAIRS_PER_CALL):
 108 | +        chunk = todo[i:i + JOIN_PAIRS_PER_CALL]
 109 | +        involved = list(dict.fromkeys(m["moment_id"] for ab in chunk for m in ab))
 110 | +        cid = {mid: f"c{k + 1}" for k, mid in enumerate(involved)}
 111 | +        by = {m["moment_id"]: m for ab in chunk for m in ab}
 112 | +        clips = "\n".join(f'CLIP id="{cid[mid]}" (on screen: {CI._q(_name(by[mid], ctx), 80)}): '
 113 | +                          f'"{CI._q(by[mid]["text"], 900)}"' for mid in involved)
 114 | +        pids = {f"p{k + 1}": ab for k, ab in enumerate(chunk)}
 115 | +        pairs = "\n".join(f'PAIR id="{p}": {cid[a["moment_id"]]} -> {cid[b["moment_id"]]}' for p, (a, b) in pids.items())
 116 | +        keys = ", ".join(f'"{p}": {{"followable": true, "why": "..."}}' for p in pids)
 117 | +
 118 | +        def parse(text, want=frozenset(pids)):
 119 | +            v = json.loads(text.strip())
 120 | +            h = v["pairs"] if isinstance(v, dict) and set(v) == {"pairs"} else None
 121 | +            if not isinstance(h, dict) or set(h) != set(want) or any(
 122 | +                    not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 123 | +                    or not isinstance(x["why"], str) for x in h.values()):
 124 | +                raise ValueError("join table out of contract")
 125 | +            return h
 126 | +        try:
 127 | +            r, h = P.call_parsed(router, "coherence_verdict", JOINS_PROMPT.format(clips=clips, pairs=pairs, keys=keys),
 128 | +                                 parse, 400 + 60 * len(chunk), seed, avoid_vendor=writer_vendor,
 129 | +                                 avoid_family=writer_family, kind="joins")
 130 | +        except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # these pairs have no entry
 131 | +            err = err or f"{type(e).__name__}: {str(e)[:200]}"
 132 | +            continue
 133 | +        for p, (a, b) in pids.items():
 134 | +            rec = {"followable": h[p]["followable"], "why": h[p]["why"][:200], "backend": r.backend}
 135 | +            out[(a["moment_id"], b["moment_id"])] = dict(rec, cached=False)
 136 | +            new[key(a, b)] = {r.backend: rec}
 137 | +    _cache_put(cache, new)
 138 | +    return out, err
 139 | +
 140 | +
 141 | +def search_lineups(angle, by_id, table, dropped=frozenset(), judged=(), bad_pairs=frozenset(), ratings=None,
 142 | +                   floor=None, repeat_ok=False):
 143 | +    """RULING 117 (2): the line-ups of `angle` chosen BY SEARCH over the join table, no model call. Hook first (the
 144 | +    angle's own, ruling 59 c), then 2-4 of its other moments (not dropped; at most JOIN_MOMENTS_MAX in all) in EVERY
 145 | +    order, under every line-up rule as now (lineup_ok: can open, clip-eligible, one per channel or the supply exception,
 146 | +    price predictions, a short clip only last, the seconds, the render's STAND_ALONE), not judged yet, and at most
 147 | +    LY_MAX_BRIDGES flagged joins: a join is flagged when the table finds it unfollowable, when the table has no answer
 148 | +    for it, or when a verdict of this build flagged it (bad_pairs). Best first: the fewest flagged joins, then the
 149 | +    highest clip ratings (`ratings`: each clip's clips-alone rating in this angle's verdicts so far; a clip not rated
 150 | +    yet counts at `floor`): the lowest, then the mean; then the writer's play order kept. -> [segs, ...]."""
 151 | +    h = by_id.get(angle["hook"])
 152 | +    if h is None or angle["hook"] in dropped:
 153 | +        return []
 154 | +    ratings, floor = ratings or {}, COHERENCE_MIN if floor is None else floor
 155 | +    pos = {m: i for i, m in enumerate(angle["moments"])}
 156 | +    others = [by_id[m] for m in angle["moments"] if m != angle["hook"] and m in by_id and m not in dropped]
 157 | +    others = others[:JOIN_MOMENTS_MAX - 1]
 158 | +    flagged = lambda a, b: (a, b) in bad_pairs or (table.get((a, b)) or {}).get("followable") is not True
 159 | +    cands = []
 160 | +    for n in range(LY_CLIPS[0], LY_CLIPS[1] + 1):
 161 | +        for perm in itertools.permutations(others, n):
 162 | +            segs = [h, *perm]
 163 | +            ids = tuple(m["moment_id"] for m in segs)
 164 | +            if ids in judged:
 165 | +                continue
 166 | +            nf = sum(flagged(a, b) for a, b in zip(ids, ids[1:]))
 167 | +            if nf > LY_MAX_BRIDGES or not lineup_ok(segs, repeat_ok=repeat_ok)[0]:
 168 | +                continue
 169 | +            rs = [ratings.get(m["moment_id"], floor) for m in perm]
 170 | +            moves = sum(abs(pos.get(m["moment_id"], 99) - k) for k, m in enumerate(perm, 1))
 171 | +            cands.append(((nf, -min(rs), -sum(rs) / len(rs), moves), segs))
 172 | +    cands.sort(key=lambda x: x[0])
 173 | +    return [s for _, s in cands]
 174 | +
 175 | +
 176 |  def allot(angles, per):
 177 |      """RULING 64 (12:00): at most `per` angles per hook, in the writer's order (the excess is dropped, recorded)."""
 178 |      seen, out = {}, []
 179 | @@ -2574,6 +2696,7 @@ def candidate_lineup(router, candidate, cleared, now):
 180 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 181 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
 182 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
 183 | +          join_cache=None,
 184 |            visual_cache=None, registered=None, lock_check=None, scorer_extra=()):
 185 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 186 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 187 | @@ -2582,6 +2705,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 188 |      work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 189 |      spend: a callable returning the ledger's USD (dollars per package).
 190 |      step_a_cache / hook_cache (rulings 58 / 59): the verdict caches every build shares (None: this build's only).
 191 | +    join_cache (RULING 117): the join table's cache, shared the same way. RULING 117, SEARCH, DO NOT LOOSEN: each angle's
 192 | +    join table (join_table: the join question once per ordered pair of its moments, Grok) is built before its first
 193 | +    line-up; the line-ups are then chosen BY SEARCH over it (search_lineups: hook first, 2-4 clips in every order, the
 194 | +    rules as now, at most one flagged join), the first and, after each failed verdict, the next; the clips-alone and
 195 | +    coherence verdicts still decide every line-up. With no table (the call failed or no entry) or no line-up left in
 196 | +    the search, the line-up is chosen as before (lineup_for, then rulings 62 / 63 / 41).
 197 |      scorer_verdicts_path / scorer_candidates_path / build_name (ruling 56, scorer_pass): the integrator's verdicts of the
 198 |      render's clip scorer to read, and where to write the next pass's candidates (None: neither).
 199 |      RULING 59, HOOK FIRST: once the pool is screened, every cleared, cuttable moment that can open is rated on the hook's
 200 | @@ -3136,6 +3265,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 201 |      with ThreadPoolExecutor(max_workers=8) as pool:
 202 |          for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):
 203 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
 204 | +            jt, a_ratings, ext = {}, {}, angle            # RULING 117: this angle's join table; its clips' ratings
 205 | +            if candidate is None and angle["hook"] in cleared and angle["hook"] not in doomed:
 206 | +                # the moments that can be in its line-up: its hook, its writer's other moments, then the rest of the
 207 | +                # cleared pool (step A from both vendors, the second pass, CUTTABLE) by rank score; at most 8
 208 | +                own_ = [x for x in angle["moments"] if x != angle["hook"] and x in cleared and x not in doomed]
 209 | +                rest_ = sorted((x for x in cleared if x not in doomed and x != angle["hook"] and x not in own_),
 210 | +                               key=lambda x: (-cleared[x].get("rank_score", 0), x))
 211 | +                jids = ([angle["hook"]] + own_ + rest_)[:JOIN_MOMENTS_MAX]
 212 | +                ext = dict(angle, moments=jids)           # the search's angle: the writer's order first
 213 | +                jms = [cleared[x] for x in jids]
 214 | +                jt, jt_err = join_table(router, jms, ctx, writers_v, writers_f, cache=join_cache)
 215 | +                out.setdefault("join_tables", []).append(
 216 | +                    {"angle": ai + 1, "moments": [m["moment_id"] for m in jms], "error": jt_err,
 217 | +                     "pairs": {f"{a} -> {b}": {"followable": x["followable"], "why": x["why"], "cached": x["cached"]}
 218 | +                               for (a, b), x in jt.items()}})
 219 | +                log(f"  angle {ai + 1}: join table (ruling 117) {len(jt)} pair(s) of {len(jms)} moments, "
 220 | +                    f"{sum(x['followable'] is not True for x in jt.values())} not followable"
 221 | +                    + (f"; NOT ASKED: {jt_err}" if jt_err else "") + f" ({time.time() - t0:.0f} s)")
 222 |              if candidate is not None:                     # RULING 66: its own seeds, so its recorded calls are served
 223 |                  n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs
 224 |              while total < lineups and not out["packages"] and not out.get("budget_stop") and \
 225 | @@ -3148,6 +3295,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 226 |                      segs, swapped = swapped, None
 227 |                      exception = supply_exception(segs, ctx)
 228 |                  else:
 229 | +                    segs, filled = None, None
 230 | +                    if jt:                                # RULING 117: chosen by search over the join table
 231 | +                        found = search_lineups(ext, cleared, jt, frozenset(dropped | doomed), judged, bad_pairs,
 232 | +                                               a_ratings, lineup_floors("clips_alone", None)[0]["clip"]) or \
 233 | +                            search_lineups(ext, cleared, jt, frozenset(dropped | doomed), judged, bad_pairs,
 234 | +                                           a_ratings, lineup_floors("clips_alone", None)[0]["clip"], repeat_ok=True)
 235 | +                        segs = found[0] if found else None
 236 | +                        exception = supply_exception(segs, ctx) if segs is not None else None
 237 | +                if swapped is None and segs is None:      # no table, or the search has nothing: as before
 238 |                      segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
 239 |                                                   need_stand_alone=True, now=ctx.now, hook_only=True), None
 240 |                      if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
 241 | @@ -3194,6 +3350,19 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 242 |                      judged[key] = (ok_m, med)
 243 |                      total += 0 if med.get("replayed") or med.get("cached") else 1   # 12:00: JUDGED line-ups
 244 |                  rec["medley"], rec["medley_ok"] = med, ok_m
 245 | +                if jt and med.get("measured"):            # RULING 117 (3): the table's joins against the verdict's
 246 | +                    ids_ = [m["moment_id"] for m in segs]
 247 | +                    cmp_ = {j: {"table": (jt.get((a, b)) or {}).get("followable"),
 248 | +                                "verdict": (med.get("joins") or {}).get(j, {}).get("followable")}
 249 | +                            for j, (a, b) in zip(joins(labels(len(segs))), zip(ids_, ids_[1:]))}
 250 | +                    rec["join_table_vs_verdict"] = cmp_
 251 | +                    ag = out.setdefault("join_agreement", {"joins": 0, "agree": 0, "table_unanswered": 0})
 252 | +                    for x in cmp_.values():
 253 | +                        if x["table"] is None:
 254 | +                            ag["table_unanswered"] += 1
 255 | +                        else:
 256 | +                            ag["joins"] += 1
 257 | +                            ag["agree"] += x["table"] == x["verdict"]
 258 |                  labs_ = labels(len(segs))
 259 |                  bad_pairs |= {(segs[labs_.index(a)]["moment_id"], segs[labs_.index(b)]["moment_id"])
 260 |                                for a, b in (j.split(" -> ") for j in med.get("flagged") or [])}   # ruling 63
 261 | @@ -3204,6 +3373,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 262 |                  if candidate is not None and not ok_m:    # RULING 66: a candidate failing a gate is closed
 263 |                      rec["why"] = "ruling 66: the candidate fails its clips-alone verdict now: closed"
 264 |                      break
 265 | +                if not ok_m and jt and med.get("measured"):   # RULING 117: the search over the table picks the next
 266 | +                    floor_ = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]
 267 | +                    for lb_, mm in zip(labs[1:], segs[1:]):
 268 | +                        x = (med.get("clips") or {}).get(lb_)
 269 | +                        if type(x) is int:
 270 | +                            a_ratings[mm["moment_id"]] = max(x, a_ratings.get(mm["moment_id"], 0))
 271 | +                            if x < floor_:                # a clip under this verdict's floor leaves the search
 272 | +                                dropped.add(mm["moment_id"])
 273 | +                    found = search_lineups(ext, cleared, jt, frozenset(dropped | doomed), judged, bad_pairs,
 274 | +                                           a_ratings, floor_) or \
 275 | +                        search_lineups(ext, cleared, jt, frozenset(dropped | doomed), judged, bad_pairs, a_ratings,
 276 | +                                       floor_, repeat_ok=True)
 277 | +                    if found:
 278 | +                        swapped = found[0]
 279 | +                        rec["why"] = (f"ruling 117: the clips alone fail ({med.get('clips')}, flagged "
 280 | +                                      f"{med.get('flagged')}): the join table's search gives the next line-up "
 281 | +                                      f"{[m['moment_id'] for m in swapped]}")
 282 | +                        continue
 283 |                  if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 284 |                      by_lab = dict(zip(labs, segs))
 285 |                      cl = med.get("clips") or {}
 286 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 287 | index e4d2206..7f683f5 100644
 288 | --- a/tests/package/proof_ledger.py
 289 | +++ b/tests/package/proof_ledger.py
 290 | @@ -474,6 +474,7 @@ def main(argv=None):
 291 |                spend=lambda: (own["est"], own["best"]),
 292 |                step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 293 |                hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 294 | +              join_cache=os.path.join(HERE, "proof", "JOIN_CACHE.json"),          # ruling 117: cached
 295 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 296 |                scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 297 |                visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
 298 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 299 | index 62c59db..b00f780 100644
 300 | --- a/tests/package/test_medley.py
 301 | +++ b/tests/package/test_medley.py
 302 | @@ -552,8 +552,9 @@ class Rig:
 303 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 304 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 305 |                   cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None,
 306 | -                 real_value=False, caption=None, coherences=None):
 307 | +                 real_value=False, caption=None, coherences=None, joins=None):
 308 |          import providers as P
 309 | +        self.joins, self.join_calls = joins, []           # RULING 117: {(a, b): followable}; None = no table (as before)
 310 |          self.coherences = list(coherences or [])         # RULING 116: (ok, every clip's rating, the VO point) in order
 311 |          self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
 312 |          self.real_value = real_value                       # ruling 91: package.takeaway_value itself, on the router
 313 | @@ -631,6 +632,20 @@ class Rig:
 314 |                                     "why": f"why {m['moment_id']}", "backend": "xai:grok", "cached": False}
 315 |          return out, None
 316 |  
 317 | +    def join_table(self, router, ms, ctx_, wv, wf=None, cache=None, seed=7):
 318 | +        """Ruling 117 as the real join_table answers: every ordered pair of `ms` (the hook never B) the rig knows
 319 | +        (self.joins), followable or not; a pair it does not know is not answered. None: no table at all."""
 320 | +        self.join_calls.append([m["moment_id"] for m in ms])
 321 | +        if self.joins is None:
 322 | +            return {}, None
 323 | +        out = {}
 324 | +        for a in ms:
 325 | +            for b in ms[1:]:
 326 | +                if a is not b and (a["moment_id"], b["moment_id"]) in self.joins:
 327 | +                    out[(a["moment_id"], b["moment_id"])] = {"followable": self.joins[(a["moment_id"], b["moment_id"])],
 328 | +                                                             "why": "w", "backend": "xai:grok", "cached": False}
 329 | +        return out, None
 330 | +
 331 |      def coherence(self, router, pk, *a, **k):
 332 |          """As the real coherence() answers: the clips after the hook and the VO point (self.coherences, default all 5
 333 |          and a pass), the hook's slot its own rating, and the line-up bar it was judged on (ruling 116)."""
 334 | @@ -728,6 +743,7 @@ class Rig:
 335 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 336 |              "hook_onset_for": self.onset,
 337 |              "hook_ratings": self.rate_hooks,
 338 | +            "join_table": self.join_table,
 339 |              "takeaway_value": self.value,                  # ruling 91 (medley half)
 340 |              "coherence": self.coherence,
 341 |          }
 342 | @@ -1709,6 +1725,211 @@ class TestRuling116LineupBar(unittest.TestCase):
 343 |          self.assertNotIn("lineup_bar", out["package"])                                  # the standard bar: no mark
 344 |  
 345 |  
 346 | +class TestRuling117JoinSearch(unittest.TestCase):
 347 | +    """RULING 117 (orchestrator 16:24 ET Nov 15), SEARCH, DO NOT LOOSEN: the join table (the clips-alone verdict's own
 348 | +    join question once per ordered pair of an angle's moments, Grok, cached) and the line-ups chosen BY SEARCH over it
 349 | +    (hook first, 2-4 clips in every order, the rules as now, at most one flagged join); the verdicts still decide."""
 350 | +
 351 | +    def canned(self, *replies):
 352 | +        c = Canned(coherence_verdict=list(replies))
 353 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 354 | +        c.backends = {"fake:coherence_verdict": B("fake", "fake")}
 355 | +        return c
 356 | +
 357 | +    @staticmethod
 358 | +    def all_pairs(prompt, followable=True):
 359 | +        ids = re.findall(r'PAIR id="(p\d+)"', prompt)
 360 | +        return {"pairs": {p: {"followable": followable, "why": "w"} for p in ids}}
 361 | +
 362 | +    def test_the_question_is_the_clips_alone_verdicts_own(self):
 363 | +        self.assertIn(PK.JOIN_QUESTION, " ".join(PK.MEDLEY_PROMPT.split()))   # ONE join question
 364 | +        self.assertIn(PK.JOIN_QUESTION, PK.JOINS_PROMPT)
 365 | +
 366 | +    def test_once_per_ordered_pair_the_hook_never_second_batched_and_cached(self):
 367 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 368 | +        prompts = []
 369 | +        c = self.canned()
 370 | +        import providers as P
 371 | +
 372 | +        def call(role, prompt, *a, **k):
 373 | +            prompts.append(prompt)
 374 | +            c.calls.append((role, k.get("avoid_vendor"), k.get("avoid_family"), k.get("kind")))
 375 | +            return P.Reply(json.dumps(self.all_pairs(prompt)), "fake:coherence_verdict", "fake")
 376 | +        c.call = call
 377 | +        with tempfile.TemporaryDirectory() as d:
 378 | +            cache = os.path.join(d, "JOIN_CACHE.json")
 379 | +            got, err = PK.join_table(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 380 | +            self.assertIsNone(err)
 381 | +            self.assertEqual(sorted(got), [("h", "x"), ("h", "y"), ("x", "y"), ("y", "x")])   # 4 pairs, no (.., h)
 382 | +            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"}, "joins")])   # one call
 383 | +            self.assertIn(PK.JOIN_QUESTION, prompts[0])
 384 | +            again, err = PK.join_table(self.canned(), ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 385 | +            self.assertEqual((err, len(again), all(x["cached"] for x in again.values())), (None, 4, True))   # no call
 386 | +            prompts.clear()
 387 | +            c.calls.clear()
 388 | +            new = [ms[0], dict(ms[1], text="Bitcoin is a new text now."), ms[2]]
 389 | +            got, _ = PK.join_table(c, new, ctx(), set(), set(), cache=cache)
 390 | +            self.assertEqual(len(re.findall(r'PAIR id=', prompts[0])), 3)       # only the pairs with the new text
 391 | +        big = [pm(f"m{i}", chr(65 + i), 10.0) for i in range(9)]
 392 | +        prompts.clear()
 393 | +        c.calls.clear()
 394 | +        got, _ = PK.join_table(c, big, ctx(), set(), set())
 395 | +        self.assertEqual((len(got), len(prompts)), (49, 2))                     # 8 moments: 49 pairs in 25 + 24
 396 | +
 397 | +    def test_a_chunk_out_of_contract_has_no_entries_and_the_others_are_still_asked(self):
 398 | +        big = [pm(f"m{i}", chr(65 + i), 10.0) for i in range(8)]
 399 | +        import providers as P
 400 | +        c, n = self.canned(), [0]
 401 | +
 402 | +        def call(role, prompt, *a, **k):
 403 | +            n[0] += 1
 404 | +            if n[0] == 1:
 405 | +                raise P.ProviderError("coherence_verdict: every back-end unavailable")
 406 | +            return P.Reply(json.dumps(self.all_pairs(prompt, False)), "fake:coherence_verdict", "fake")
 407 | +        c.call = call
 408 | +        got, err = PK.join_table(c, big, ctx(), set(), set())
 409 | +        self.assertEqual((len(got), "ProviderError" in err), (24, True))       # the second chunk only
 410 | +        self.assertTrue(all(x["followable"] is False for x in got.values()))
 411 | +
 412 | +    def moments(self):
 413 | +        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})
 414 | +        return {m["moment_id"]: m for m in (h, pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 6.0))}
 415 | +
 416 | +    def test_the_search_every_order_the_rules_and_at_most_one_flagged_join(self):
 417 | +        by = self.moments()
 418 | +        a = angle(["h", "x", "y", "z"], "h")
 419 | +        T = lambda ok: {"followable": ok}
 420 | +        table = {(p, q): T(True) for p in "hxyz" for q in "xyz" if p != q}
 421 | +        table[("h", "x")] = T(False)
 422 | +        table[("x", "y")] = T(False)                                          # the writer's order: two flagged
 423 | +        got = PK.search_lineups(a, by, table)
 424 | +        self.assertTrue(got)
 425 | +        best = [m["moment_id"] for m in got[0]]
 426 | +        self.assertEqual(best[0], "h")                                       # the hook first
 427 | +        ids = [[m["moment_id"] for m in s] for s in got]
 428 | +        self.assertNotIn(["h", "x", "y", "z"], ids)                          # two flagged: never offered
 429 | +        for s in ids:
 430 | +            self.assertLessEqual(sum(table.get((p, q), {}).get("followable") is not True for p, q in zip(s, s[1:])), 1)
 431 | +            self.assertTrue(PK.lineup_ok([by[i] for i in s])[0])              # the rules as now
 432 | +            self.assertNotIn("z", s[1:-1])                                    # z is short (6 s): only last
 433 | +        self.assertEqual(sum(table.get((p, q), {}).get("followable") is not True for p, q in zip(best, best[1:])), 0)
 434 | +        del table[("y", "z")]                                                # no answer counts as flagged
 435 | +        self.assertTrue(all(sum((p, q) == ("y", "z") or table.get((p, q), {}).get("followable") is not True
 436 | +                                for p, q in zip(s, s[1:])) <= 1 for s in
 437 | +                            [[m["moment_id"] for m in x] for x in PK.search_lineups(a, by, table)]))
 438 | +        judged = {tuple(best)}
 439 | +        self.assertNotIn(best, [[m["moment_id"] for m in s] for s in PK.search_lineups(a, by, table, judged=judged)])
 440 | +        self.assertFalse([s for s in PK.search_lineups(a, by, table, dropped=frozenset({"x", "y"}))])   # 1 clip left
 441 | +        bp = {("h", "y")}                                                    # a verdict flagged it: it counts
 442 | +        for s in [[m["moment_id"] for m in x] for x in PK.search_lineups(a, by, table, bad_pairs=bp)]:
 443 | +            n_bad = sum((p, q) in bp or table.get((p, q), {}).get("followable") is not True for p, q in zip(s, s[1:]))
 444 | +            self.assertLessEqual(n_bad, 1)
 445 | +
 446 | +    def test_an_unanswered_pair_and_a_verdicts_flag_each_count_as_flagged(self):
 447 | +        by = dict(self.moments(), z=pm("z", "D", 13.0))
 448 | +        a = angle(["h", "x", "y", "z"], "h")
 449 | +        table = {(p, q): {"followable": True} for p in "hxyz" for q in "xyz" if p != q}
 450 | +        ids = lambda got: [[m["moment_id"] for m in s] for s in got]
 451 | +        self.assertEqual(ids(PK.search_lineups(a, by, table))[0], ["h", "x", "y"])   # the writer's order first
 452 | +        t2 = dict(table)
 453 | +        t2[("h", "x")] = {"followable": False}
 454 | +        del t2[("x", "y")]                                                   # no answer for x -> y
 455 | +        self.assertNotIn(["h", "x", "y"], ids(PK.search_lineups(a, by, t2)))       # flagged + unanswered: 2
 456 | +        self.assertNotIn(["h", "x", "y"], ids(PK.search_lineups(a, by, table, bad_pairs={("h", "x"), ("x", "y")})))
 457 | +
 458 | +    def test_the_search_prefers_higher_known_ratings(self):
 459 | +        by = dict(self.moments(), z=pm("z", "D", 13.0))                      # z long enough to stand in for y
 460 | +        a = angle(["h", "x", "y", "z"], "h")
 461 | +        table = {(p, q): {"followable": True} for p in "hxyz" for q in "xyz" if p != q}
 462 | +        got = PK.search_lineups(a, by, table, ratings={"x": 5, "y": 2}, floor=3)
 463 | +        self.assertNotIn("y", [m["moment_id"] for m in got[0]])              # a 2 ranks below the unknown z
 464 | +
 465 | +    def test_a_build_asks_the_searchs_line_up_first_and_records_the_agreement(self):
 466 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 467 | +        joins = {("h", "x"): False, ("x", "y"): False, ("h", "y"): True, ("y", "x"): True}
 468 | +        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins=joins)
 469 | +        out = rig.run()
 470 | +        self.assertEqual(rig.medley_calls, [["h", "y", "x"]])                  # the table's order, not the writer's
 471 | +        self.assertEqual(rig.join_calls, [["h", "x", "y"]])
 472 | +        self.assertEqual(out["tried"][0]["join_table_vs_verdict"],
 473 | +                         {"hook -> clip_01": {"table": True, "verdict": True},
 474 | +                          "clip_01 -> clip_02": {"table": True, "verdict": True}})
 475 | +        self.assertEqual(out["join_agreement"], {"joins": 2, "agree": 2, "table_unanswered": 0})
 476 | +        self.assertEqual(out["join_tables"][0]["moments"], ["h", "x", "y"])
 477 | +        self.assertIsNotNone(out["package"])
 478 | +
 479 | +    def test_after_a_failed_verdict_the_search_gives_the_next_line_up(self):
 480 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 481 | +        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
 482 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE),
 483 | +                                             (True, [], None, Rig.LINE)], [None], joins=joins)
 484 | +        out = rig.run()
 485 | +        first, second = rig.medley_calls                                      # the search's shortest first: h x y
 486 | +        self.assertEqual(first, ["h", "x", "y"])
 487 | +        self.assertIn("ruling 117", out["tried"][0]["why"])
 488 | +        flagged = {("h", "x"), ("x", "y")}                                    # the verdict's flags count as flagged
 489 | +        self.assertEqual(sum(p in flagged for p in zip(second, second[1:])), 0)   # the next has neither
 490 | +        self.assertIsNotNone(out["package"])
 491 | +
 492 | +    def test_the_cache_answers_only_for_todays_joins_list(self):
 493 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0)]
 494 | +        import providers as P
 495 | +        c = self.canned()
 496 | +        c.call = lambda role, prompt, *a, **k: (c.calls.append(role), P.Reply(
 497 | +            json.dumps(self.all_pairs(prompt)), "fake:coherence_verdict", "fake"))[1]
 498 | +        c.chain = lambda role, kind=None: ["fake:coherence_verdict"]
 499 | +        with tempfile.TemporaryDirectory() as d:
 500 | +            cache = os.path.join(d, "JOIN_CACHE.json")
 501 | +            PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
 502 | +            c.calls.clear()
 503 | +            got, _ = PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
 504 | +            self.assertEqual((c.calls, got[("h", "x")]["cached"]), ([], True))     # on the list: served
 505 | +            c.chain = lambda role, kind=None: ["xai:another-rater"]
 506 | +            got, _ = PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
 507 | +            self.assertEqual((len(c.calls), got[("h", "x")]["cached"]), (1, False))   # off it: asked again
 508 | +
 509 | +    def test_a_clip_under_the_verdicts_floor_leaves_the_search(self):
 510 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 511 | +        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
 512 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_01": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
 513 | +                  [None], joins=joins)
 514 | +        out = rig.run()
 515 | +        first, second = rig.medley_calls
 516 | +        self.assertEqual(first[1], "x")                                      # x rated 2 on the calibrated bar
 517 | +        self.assertNotIn("x", second)                                         # out of every later line-up
 518 | +        self.assertIn("ruling 117", out["tried"][0]["why"])
 519 | +
 520 | +    def test_clips_under_a_verdicts_floor_never_come_back_when_the_search_runs_out(self):
 521 | +        """x, then y, rated 2: each leaves the search; with neither, no line-up of 2-4 clips is left, so no third
 522 | +        verdict is asked (with them kept, the search would ask a line-up holding a clip already rated 2)."""
 523 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 524 | +        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
 525 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_01": 2}, Rig.LINE), (False, [], {"clip_01": 2}, Rig.LINE),
 526 | +                                             (True, [], None, Rig.LINE)], [None], joins=joins)
 527 | +        rig.run()
 528 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "z"]])
 529 | +
 530 | +    def test_the_tables_moments_are_the_hook_its_writers_picks_then_the_cleared_pool(self):
 531 | +        """The order's set: the hook and the clips that passed step A from both vendors, the second pass and CUTTABLE
 532 | +        (the cleared pool), at most 8: the writer's own moments first, then the pool by rank score."""
 533 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("w", "D", 13.0)]
 534 | +        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins={})
 535 | +        rig.run()
 536 | +        self.assertEqual(rig.join_calls, [["h", "x", "y", "w"]])
 537 | +        big = [pm("h", "A", 12.0)] + [pm(f"m{i}", chr(66 + i), 10.0) for i in range(9)]
 538 | +        rig = Rig(big, ["h", "m0", "m1"], [(True, [], None, Rig.LINE)], [None], joins={})
 539 | +        rig.run()
 540 | +        self.assertEqual((len(rig.join_calls[0]), rig.join_calls[0][:3]), (8, ["h", "m0", "m1"]))
 541 | +
 542 | +    def test_no_table_or_an_empty_one_is_the_build_as_before(self):
 543 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 544 | +        for joins in (None, {}):
 545 | +            rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins=joins)
 546 | +            out = rig.run()
 547 | +            self.assertEqual(rig.medley_calls, [["h", "x", "y"]])              # the writer's order
 548 | +            self.assertNotIn("join_agreement", out)
 549 | +
 550 | +
 551 |  class TestRuling56Scorer(unittest.TestCase):
 552 |      """RULING 56 (09:59): the render's own STAND_ALONE clip scorer, asked at the pin stage by the integrator's service
 553 |      about every moment left out as an opener it would have to affirm, untrimmed and trimmed; only what it affirms is
 554 | 
```

---

pp-selectid: RULING 117 (orchestrator 16:24 ET Nov 15), THE JOINS: SEARCH, DO NOT LOOSEN (2)+(3). Files:
pipeline/package.py (join_table, search_lineups, JOIN_QUESTION / JOINS_PROMPT, build()'s angle loop),
pipeline/model_providers.json (the joins list), tests/package/proof_ledger.py (the join cache), tests/package/test_medley.py.

THE ORDER, verbatim: "(2) BUILD THE JOIN TABLE: for the moments that can be in a line-up for an angle (the hook and the
clips that passed step A from both vendors, the second pass and CUTTABLE; cap 8 moments an angle), ask ONCE per ordered
pair 'coming from the end of A, is B's subject or referent clear with no narration' (the join question as it stands,
one pair per item, batched in one call where the contract allows; Grok, the calibrated rater; cached by the two texts).
Then choose the order BY SEARCH over the table: hook first, 2-4 clips, the seconds and channel rules as now, at most one
flagged join, highest clip ratings first. No model call in the search. (3) THE FULL VERDICT STILL DECIDES: the chosen
line-up goes through the clips-alone and coherence verdicts unchanged (calibrated bars); the table only picks what to
ask them. Report how often the table's joins and the full verdict's joins agree." The join law does NOT move (one
bridge).

THE CHANGE:
- JOIN_QUESTION: the clips-alone verdict's own join sentence (a test checks it is in MEDLEY_PROMPT, white space
  normalized; MEDLEY_PROMPT itself is unchanged, so the line-up calibration's version stands). JOINS_PROMPT: the
  moments once ("CLIP id=c1 ..."), the pairs ("PAIR id=p1: c1 -> c3"), the question per pair, one item a pair:
  {"pairs": {"p1": {"followable": bool, "why": str}}}.
- join_table(router, ms, ...): ms = the angle's hook then its other moments that are in `cleared` (cleared = the
  build's moments that passed step A from both vendors, the second pass and CUTTABLE) and not doomed, at most 8. Every
  ordered pair with the hook never second (8 moments: 49 pairs), 25 pairs a call, coherence_verdict kind "joins"
  (Grok ALONE in every routing: model_providers.json), off the writers. Cached by the two texts' sha and JOINS_VERSION
  (JOIN_CACHE.json), served only from a back-end on today's joins list; an out-of-contract chunk moves on
  (call_parsed) and leaves its pairs unanswered; the others are still asked.
- search_lineups(angle, by_id, table, dropped, judged, bad_pairs, ratings, floor, repeat_ok): the angle's own hook
  first, then 2-4 of its other moments in EVERY order; kept only when lineup_ok passes (the rules as now: can open,
  clip-eligible, one per channel or the supply exception, price predictions, trimmed clips, a clip under 8 s only
  last, the seconds window, the render's STAND_ALONE), not judged yet, and at most LY_MAX_BRIDGES flagged joins, where
  a join is flagged when the table says not followable, when the table has NO answer for it, or when a verdict of
  this build flagged it. Best first: fewest flagged joins, then the clips' known ratings (lowest, then mean; a clip not
  rated yet counts at the floor), then the writer's play order (fewest moves). No model call.
- build(): per angle (not for a ruling-66 candidate), the table is asked once, before its first line-up, and recorded
  (out["join_tables"]). A fresh line-up is the search's best (one channel per segment first, then the supply
  exception); after a failed clips-alone verdict, its clips' ratings are kept, a clip under THAT verdict's floor leaves
  the angle (dropped), and the search's next line-up is asked (rec["why"] names ruling 117). With no table (the call
  failed, or no pair answered) or nothing left in the search, the build goes on exactly as before (lineup_for, then
  rulings 62 / 63 / 41). Every judged line-up records its joins as the table had them against the verdict
  (rec["join_table_vs_verdict"]); out["join_agreement"] counts agree / joins / unanswered.

UNCHANGED GUARDS: medley() / coherence() decide every line-up (their prompts, floors and marks unchanged);
LINEUPS_PER_BUILD (8 judged line-ups a build) and the spins guard bound the loop; lineup_ok
(pipeline/package.py, "def lineup_ok"); _load_cache / _cache_put (None: neither read nor written); call_parsed.

TESTS (test_medley TestRuling117JoinSearch, 12): the question is the verdict's own; once per ordered pair, the hook
never second, one call, off the writers, kind "joins", cached by texts (a changed text re-asks only its pairs); 49
pairs in 2 calls; a failed chunk leaves only its pairs unanswered; the cache only for today's joins list; the search:
every order under lineup_ok, never two flagged, a short clip only last, judged / dropped excluded, an unanswered pair
and a verdict's flag each count as flagged, known ratings rank; the build asks the search's line-up first, records
the agreement, takes the search's next after a failure, drops a clip under the verdict's floor (and asks no third
verdict once the search runs out), and with no table or an empty one is the build as before. All 40 suite files pass
(805 + 4 tests). Mutations after a control run: 14 of 14 killed.

PLEASE CHECK: (1) that nothing about the join law or the verdicts moved (one bridge; the verdicts decide); (2) that
the search applies exactly lineup_for's rules (via lineup_ok) and counts unanswered pairs as flagged; (3) the
build's fallbacks (no table, no candidates) keep today's behaviour; (4) the cache and the contract; (5) the tests.


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
