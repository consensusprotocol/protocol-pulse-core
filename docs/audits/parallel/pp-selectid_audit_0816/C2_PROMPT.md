# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0816
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 152 s finish=stop usage in 8696 / out 3937 usd~0.085 (upper-bound price)

# Audit: pp-selectid — Ruling 53 de-duplication (reposted_once)

Scope note: I only have the diff. I have not seen `canon.canon_tokens`, `usable()`, the step-A/L-v2 screens, the angle writer, or the sign-off credit path, so several conclusions below are conditional on the stated behavior of those functions.

## P0

None. I can't construct a scenario from the diff alone where the ruling's outcome (original kept, copy recorded, copy never offered) fails.

## P1

**P1-1. Tie-break "lower moment id" is not actually implemented — the kept moment is chosen by *input order* of the `min`, not by id.** `package.py:67` (`keep = {min(g, key=at)["moment_id"] for g in groups.values()}`). `min` with `key=at` returns the *first* element of the group in iteration order when the `at()` keys tie. `at()` returns `(0, timestamp, moment_id)` for readable times — so for two readable, equal timestamps, the tie is broken by the *lexicographically smaller moment_id* only if that moment happens to come first in the group list; otherwise the first-encountered wins. Wait — actually, since the third tuple element is `moment_id`, `min` does compare the third element on a timestamp tie, so equal readable timestamps DO resolve to the lower id. The real gap: the ruling says "a tie goes to the lower moment id", but the ruling's tie presumably means equal *published_at*; that is handled. However, if `published_at` strings differ in format but denote the same instant (e.g. `+00:00` vs `Z`), both parse to the same timestamp and the id tie-break applies — fine. So the residual risk is narrower: **a moment whose `published_at` parses but is naive (no tz) is treated as "no readable time"** (`package.py:30-31`: `if t is None or t.tzinfo is None: return (1, 0.0, mid)`), even though `datetime.fromisoformat` succeeded. A naive-but-parseable time (e.g. `"2026-11-12T20:55:00"` with no offset) is arguably readable, and the ruling says "earliest published_at" without restricting to tz-aware. Scenario: the 07:14 build's CNBC moment carries a naive timestamp while Strategy's is UTC-aware; the copy (Strategy) would be kept and credited, violating "credit the original". I cannot verify from the diff whether the moments' `published_at` is always tz-aware; the test helper `pm()` uses `NOW - timedelta(...)` — if `NOW` is a naive datetime, all test times are naive and this branch is exercised only via the `None` case in the tests. **Concrete ask: confirm the provenance of `published_at` (tz-aware or not) in production moments.**

**P1-2. `same()` returns `None` when either token list is empty, and an empty-text moment is then never grouped — but it also can never be a copy, which is correct; the subtler issue is the multiset pre-check's interaction with `autojunk=False`... actually the pre-check is sound.** Let me instead flag what I *can*: **`difflib.SequenceMatcher`'s matching blocks are not guaranteed maximal-coverage** — `get_matching_blocks()` returns a maximal *set of* blocks via its greedy longest-matching-block recursion, but it does not guarantee the maximum total aligned coverage. Scenario: two 20-word speeches where the greedy choice of one long common block prevents a better overall alignment, dropping the aligned count below 80 % while a true optimal alignment (e.g. via edit-distance alignment) would reach it. This is a known property of SequenceMatcher (it's not a Needleman-Wunsch optimum). Concrete: moment A = `a b c ... x` (20 words), moment B = same 20 words with one word inserted early and one deleted late; the greedy recursion can, in contrived cases, lock onto a shorter block. Practical risk is low for near-identical re-posts (the 07:14 case: 38/38), but the ruling's "80 % of the words" is implemented as "SequenceMatcher's alignment", which is *a* reading (K1), not obviously *the* reading. Flag as a documented-reading risk, not a bug.

**P1-3. Transitive grouping can keep a moment that is not the earliest *within its own pairwise-identical* subgroup.** Because grouping is transitive via union-find, a chain A—B—C (A≈B, B≈C, but A!≈C) forms one group, and the kept moment is the earliest in the *whole group*. That matches "the same speech ... is ONE moment" only if the ruling intends the transitive closure; the ruling's wording ("Equal text after 80 %...") defines a pairwise relation, and the diff's union-find takes its transitive closure. Scenario: CNBC's 13.9 s, Strategy's near-identical, and a third channel's 80 %-aligned-to-Strategy-but-72 %-to-CNBC variant published earliest of all — the third channel's moment is kept and credited even though it is not 80 %-aligned to... it *is* in the group, so it's consistent with the closure reading. This is a reading question, not a defect; state it: **the ruling's pairwise definition vs. the implemented transitive closure is a stated-reading gap (K1-adjacent) that the ruling text does not sett

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 55 s finish=stop usage in 8788 / out 407 usd~0.054 (upper-bound price)

**P2: pipeline/package.py:41** (concrete scenario: pair with bag-of-words overlap of exactly 79% of shorter length). The Counter-based pre-filter correctly rejects before difflib.SequenceMatcher because multiset intersection is a strict upper bound on possible in-order hit; no false-negative matches are possible (verifiable from the comment and the 80% test cases that follow).

**P2: pipeline/package.py:74** (concrete scenario: three moments A-B-C where A matches B and B matches C on different channels, earliest publish time is A). The union-find + root_of path compression + final min-per-group correctly collapses the transitive group and keeps only the earliest readable published_at (tie broken by moment_id); the "aligned through another copy" fallback reason is emitted for the indirect duplicate.

**P2: tests/package/test_medley.py:168** (concrete scenario: moment with published_at=None vs one with valid ISO time). The at() helper treats missing/unparseable time as (1, 0.0, id) so it is never selected as original; same-channel pairs are excluded from reposted (matches K3 exactly, verifiable in both the loop guard and the unit test that asserts dup=={}).

**P2: pipeline/package.py:91** (post-usable, pre-STAND_ALONE/trim/step-A). Placement matches the ruling's "before the angle step" and "keep the ORIGINAL publisher's … credit the original" verbatim; n_usable is captured before filtering so out["usable"] semantics are preserved (explicit comment references audit 0310).

No P0 or P1 findings. All governing laws verifiable in the diff (L-k canonical form via canon.canon_tokens, L-j exact bytes/attestation untouched, no renderer/selector change, fail-closed on unreadable times, etc.) are respected. The 308-moment real run (2.3 s) and full test suite pass are stated in the diff.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 9481 / out 2453 usd~0.065 (upper-bound price)

**P0 Findings**

1.  **`pipeline/package.py:41` (Logic Error in Pre-check):** The multiset overlap pre-check uses `collections.Counter` intersection, which counts shared words regardless of order. The actual match requires *in-order* alignment via `difflib`.
    *   *Scenario:* Moment A: "Bitcoin is the future of money." (6 words). Moment B: "money of future the is Bitcoin." (6 words).
    *   *Pre-check:* Counter intersection is 6. `6 >= 0.8 * 6` is True. Proceeds to `difflib`.
    *   *Difflib:* `SequenceMatcher` on reversed lists finds 0 matching blocks (or very few if single words match, but "Bitcoin" is at index 0 in A and 5 in B; "money" is 5 in A and 0 in B). The in-order alignment will fail.
    *   *Result:* The pair is correctly rejected by `difflib`. **However**, the pre-check is described in the diff comments as an "upper bound" to *skip* pairs. If the pre-check fails, it skips. If it passes, it runs difflib. The logic `if sum(...) < REPOST_ALIGN_MIN * short: return None` is correct for *skipping* non-matches.
    *   *Wait, let's re-read the code:*
        ```python
        if sum((collections.Counter(ta) & collections.Counter(tb)).values()) < REPOST_ALIGN_MIN * short:
            return None                           # the shared words bound the aligned ones: 80 % is out of reach
        ```
        This is a valid *necessary* condition. If the multiset overlap is < 80%, the in-order overlap MUST be < 80%. So this is **not** a P0 logic error for correctness, but it is a **P1 performance/efficiency** issue if the pre-check is too loose (it is, as shown above, but it doesn't cause false positives, only false negatives in the *skip* step, meaning it runs difflib unnecessarily).
    *   *Correction:* There is no P0 here. The pre-check is safe.

2.  **`pipeline/package.py:43` (False Positive Risk with `difflib`):** `difflib.SequenceMatcher` with `autojunk=False` finds the longest contiguous matching blocks. It does **not** require the *entire* sequence to be aligned, just that the sum of matching block sizes is >= 80% of the shorter length.
    *   *Scenario:* Moment A: "The Bitcoin market is volatile today." (7 words). Moment B: "The Bitcoin market is volatile today and tomorrow." (9 words).
    *   *Shorter:* A (7 words). 80% of 7 = 5.6.
    *   *Difflib:* Matches "The Bitcoin market is volatile today" (7 words). 7 >= 5.6. **Match.**
    *   *Is this a re-post?* Yes, B contains A plus extra words. This is likely a valid re-post (e.g., a clip that includes the full sentence plus a tag).
    *   *Scenario 2:* Moment A: "Bitcoin is up. The market is green." (7 words). Moment B: "Bitcoin is down. The market is red." (7 words).
    *   *Difflib:* Matches "Bitcoin is" (2) and "The market is" (3). Total 5. 5 < 5.6. **No Match.** Correct.
    *   *Scenario 3:* Moment A: "I like Bitcoin. It is good." (6 words). Moment B: "I like Ethereum. It is good." (6 words).
    *   *Difflib:* Matches "I like" (2) and "It is good" (3). Total 5. 5 < 4.8 (80% of 6). **No Match.** Correct.
    *   *Scenario 4:* Moment A: "The Fed raised rates. Bitcoin fell." (6 words). Moment B: "The Fed raised rates. Gold fell." (6 words).
    *   *Difflib:* Matches "The Fed raised rates" (4). 4 < 4.8. **No Match.** Correct.
    *   *Scenario 5:* Moment A: "Bitcoin is the new gold. It is digital." (8 words). Moment B: "Bitcoin is the new silver. It is digital." (8 words).
    *   *Difflib:* Matches "Bitcoin is the new" (4) and "It is digital" (3). Total 7. 7 >= 6.4. **MATCH.**
    *   *Verdict:* These are **different speeches** (gold vs silver). The rule merges them. This violates the intent of "same speech". The 80% threshold is too low for short sentences where a single word change (gold/silver) leaves 7/8 words identical.
    *   *Severity:* **P0**. The rule fails to distinguish between a re-post and a similar but distinct statement when the difference is a single key noun/verb in a short clip. The "original publisher" logic will then arbitrarily credit the first one, potentially misattributing the "silver" comment to the "gold" channel or vice versa, and removing the other from the pool.

3.  **`pipeline/package.py:27` (Timezone Handling):** `datetime.fromisoformat` in Python 3.11+ handles 'Z' correctly, but the code explicitly replaces 'Z' with '+00:00'. This is fine. However, `m.get("published_at")` might be a string without timezone info (naive).
    *   *Code:* `if t is None or t.tzinfo is None: return (1, 0.0, m["moment_id"])`.
    *   *Scenario:* If `published_at` is a naive datetime string (e.g., "2026-11-13T08:00:00"), `t.tzinfo` is None. The moment is treated as "no readable time" and **never preferred**.
    *   *Impact:* If the original publisher has a naive timestamp and the re-poster has a UTC timestamp, the re-poster (with valid tz) will be preferred over the original (naive), violating "keep the ORIGINAL publisher

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0816 (RULING 53: a speech re-posted by a second channel is one moment): cycle 1 consensus

**Run.** Verdicts:
- grok: "SHIP: yes";
- glm: "yes with conditions" (no P0);
- qwen: "SHIP: NO", on one P0 that holds.

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | qwen P0: text-only alignment merges two DIFFERENT short statements that differ in one key word ("Bitcoin is the new gold. It is digital." vs "...silver...": 7 of 8 words align in order) | The match is now what ruling 53 says: "time-aligned overlap of 80 % of the words". A word counts only when it matches in order (difflib's blocks) AND its start time keeps the one clock offset of the pair: within REPOST_TIME_TOL_S (0.3 s) of the median start difference. A re-post is the same audio, so every matched word keeps its spacing; two speakers saying similar words do not. My K1 reading had dropped the "time" part; it is restored. Without a word record with timings, only EQUAL text merges, so nothing merges on a guess. Tested: the gold / silver pair at two rhythms is not merged; a re-post with 3 extra words at a 97.5 s offset is merged (15 of 15 time-aligned). Measured on the 07:14 inputs: the same 2 CNBC / Strategy copies (39 of 39 words time-aligned; one equal text). |
| F2 | qwen P1: a published_at with no zone was "never preferred", so a naive original could lose to an aware copy | A time with no zone is read as UTC, the pipeline's own clock. An unreadable time is never preferred (tested both ways). |

## Refuted or recorded

| # | claim | the code |
|---|---|---|
| R1 | glm P1-1: the tie-break "lower moment id" is not implemented; min keeps input order | at() returns (0, timestamp, moment_id): on equal times the tuple's third element decides, so the lower id wins whatever the input order. |
| R2 | glm P1-3 / qwen P1-2: union-find merges a chain A~B, B~C even when A and C do not match | Intended: one speech re-posted twice is one group, and its earliest publisher is kept. qwen marks it "Correct". |
| R3 | glm P1-5 / qwen P1: O(n^2) pairs | The same-channel skip and the multiset pre-check (an upper bound on the aligned words) prune most pairs. Measured 2.3 s on 308 moments, about 1 s on the ~170 usable ones a build passes. Recorded; no change. |
| R4 | glm P1-4: STAND_ALONE and the trims run on the de-duplicated moments | Intended (K2): a copy makes no trimmed variant either. out["usable"] keeps its pre-duplicate count, as tested. |

## Verification

- test_medley 86 OK (the ruling-53 tests rewritten for the time-aligned rule); every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0816/C2_STEP.diff (239 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5b7a168..8940e48 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -711,6 +711,115 @@ def trim_variant(m, sources):
   6 |      return v
   7 |  
   8 |  
   9 | +REPOST_ALIGN_MIN = 0.80          # ruling 53: the share of the shorter moment's words that are TIME-aligned
  10 | +REPOST_TIME_TOL_S = 0.30         # a re-post is the same audio: its matched words keep their spacing within this
  11 | +
  12 | +
  13 | +def _timed_words(m, sources):
  14 | +    """[(the word's canonical form, its start s)] for a moment's own words, from its word record; None without one."""
  15 | +    import canon
  16 | +    try:
  17 | +        toks = src_of(m, sources).tokens
  18 | +        w0, w1 = m["words"]
  19 | +    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
  20 | +        return None
  21 | +    out = []
  22 | +    for t in toks[w0:w1 + 1]:
  23 | +        key, st = " ".join(canon.canon_tokens(t.get("word") or "")), t.get("start")
  24 | +        if key and isinstance(st, (int, float)) and not isinstance(st, bool):
  25 | +            out.append((key, float(st)))
  26 | +    return out or None
  27 | +
  28 | +
  29 | +def _time_aligned(ta, tb):
  30 | +    """How many words of two timed word lists match IN ORDER (difflib's matching blocks) AND keep one clock offset:
  31 | +    each matched pair's start-time difference lies within REPOST_TIME_TOL_S of the median difference. Two uploads of
  32 | +    one audio share the spacing of every word; two speakers saying similar words do not."""
  33 | +    import difflib
  34 | +    import statistics
  35 | +    sm = difflib.SequenceMatcher(None, [w for w, _ in ta], [w for w, _ in tb], autojunk=False)
  36 | +    pairs = [(ta[x.a + k][1], tb[x.b + k][1]) for x in sm.get_matching_blocks() for k in range(x.size)]
  37 | +    if not pairs:
  38 | +        return 0
  39 | +    off = statistics.median(y - x for x, y in pairs)
  40 | +    return sum(abs((y - x) - off) <= REPOST_TIME_TOL_S for x, y in pairs)
  41 | +
  42 | +
  43 | +def reposted_once(ms, sources):
  44 | +    """RULING 53 (08:06 Nov 13): the same speech re-posted by a SECOND channel is ONE moment. Two moments on different
  45 | +    channels are the same speech when their texts are equal after normalisation (canon.canon_tokens, the one normal
  46 | +    form), or when at least REPOST_ALIGN_MIN of the shorter one's words are TIME-ALIGNED: the same words in order, at
  47 | +    one clock offset (each within REPOST_TIME_TOL_S; _time_aligned). Without a word record with timings only equal
  48 | +    text merges, so two moments are never merged on a guess. Of each such group the ORIGINAL publisher's moment is kept:
  49 | +    the earliest published_at (a time with no zone is read as UTC, the pipeline's own; an unreadable one is never
  50 | +    preferred; a tie goes to the lower moment id). Only it plays, so its channel is the one credited.
  51 | +    -> (the moments kept, in their order, {copy's moment id: why})."""
  52 | +    import collections
  53 | +    from datetime import datetime, timezone
  54 | +    import canon
  55 | +    text = {m["moment_id"]: canon.canon_tokens(m.get("text") or "") for m in ms}
  56 | +    timed = {m["moment_id"]: _timed_words(m, sources) for m in ms}
  57 | +
  58 | +    def at(m):                                    # the earliest readable publish time first; none is never first
  59 | +        try:
  60 | +            t = datetime.fromisoformat(str(m.get("published_at") or "").replace("Z", "+00:00"))
  61 | +        except ValueError:
  62 | +            return (1, 0.0, m["moment_id"])
  63 | +        t = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
  64 | +        return (0, t.astimezone(timezone.utc).timestamp(), m["moment_id"])
  65 | +
  66 | +    def same(a, b):
  67 | +        if text[a["moment_id"]] and text[a["moment_id"]] == text[b["moment_id"]]:
  68 | +            return "equal text after normalisation"
  69 | +        ta, tb = timed[a["moment_id"]], timed[b["moment_id"]]
  70 | +        if not ta or not tb:
  71 | +            return None                           # no timings: only equal text merges
  72 | +        short = min(len(ta), len(tb))
  73 | +        shared = collections.Counter(w for w, _ in ta) & collections.Counter(w for w, _ in tb)
  74 | +        if sum(shared.values()) < REPOST_ALIGN_MIN * short:
  75 | +            return None                           # the shared words bound the aligned ones: 80 % is out of reach
  76 | +        hit = _time_aligned(ta, tb)
  77 | +        return (f"{hit} of the shorter's {short} words time-aligned (the same words in order, one clock offset within "
  78 | +                f"{REPOST_TIME_TOL_S:.1f} s)") if hit >= REPOST_ALIGN_MIN * short else None
  79 | +    parent = {m["moment_id"]: m["moment_id"] for m in ms}
  80 | +
  81 | +    def root_of(x):
  82 | +        while parent[x] != x:
  83 | +            parent[x] = parent[parent[x]]
  84 | +            x = parent[x]
  85 | +        return x
  86 | +    how = {}
  87 | +    for i, a in enumerate(ms):
  88 | +        for b in ms[i + 1:]:
  89 | +            if a["channel_id"] == b["channel_id"]:
  90 | +                continue                                  # the rule is about a SECOND channel
  91 | +            w = same(a, b)
  92 | +            if w:
  93 | +                ra, rb = root_of(a["moment_id"]), root_of(b["moment_id"])
  94 | +                if ra != rb:
  95 | +                    parent[rb] = ra
  96 | +                how[(a["moment_id"], b["moment_id"])] = how[(b["moment_id"], a["moment_id"])] = w
  97 | +    groups = {}
  98 | +    for m in ms:
  99 | +        groups.setdefault(root_of(m["moment_id"]), []).append(m)
 100 | +    keep = {min(g, key=at)["moment_id"] for g in groups.values()}
 101 | +    by = {m["moment_id"]: m for m in ms}
 102 | +    out, dup = [], {}
 103 | +    for m in ms:
 104 | +        mid = m["moment_id"]
 105 | +        if mid in keep:
 106 | +            out.append(m)
 107 | +            continue
 108 | +        k = next(x for x in keep if root_of(x) == root_of(mid))
 109 | +        o = by[k]
 110 | +        dup[mid] = (f"the same speech as {k} ({o.get('channel_name') or o['channel_id']}, published "
 111 | +                    f"{o.get('published_at')}), re-posted by a second channel "
 112 | +                    f"({m.get('channel_name') or m['channel_id']}, published {m.get('published_at')}): "
 113 | +                    f"{how.get((k, mid)) or 'matched through another copy'} (ruling 53: the original publisher's is "
 114 | +                    f"kept and credited)")
 115 | +    return out, dup
 116 | +
 117 | +
 118 |  def no_topic(m):
 119 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
 120 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
 121 | @@ -1269,6 +1378,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 122 |      usd0 = _spent(spend)
 123 |      ms, why = usable(moments, ctx, delivered, optout)
 124 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
 125 | +    ms, reposted = reposted_once(ms, sources)          # ruling 53: a speech re-posted by a second channel is ONE
 126 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
 127 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
 128 |      trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}
 129 | @@ -1281,10 +1391,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 130 |      levels = current_levels(sources.values(), ctx)
 131 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 132 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
 133 | +           "reposted": reposted,
 134 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 135 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 136 |             "package": None}
 137 | -    log(f"  {n_usable} usable, {len(no_role)} of them left out by the render's STAND_ALONE (an opener the clip scorer "
 138 | +    log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
 139 | +        f"the original publisher's kept), {len(no_role)} left out by the render's STAND_ALONE (an opener the clip scorer "
 140 |          f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
 141 |          f"variants with ONE leading word trimmed, ruling 33 part 2), {len(ad_read)} on an ad-read "
 142 |          f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 143 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
 144 | index 7a41a3a..c8814db 100644
 145 | --- a/tests/moments/test_moments.py
 146 | +++ b/tests/moments/test_moments.py
 147 | @@ -93,7 +93,7 @@ def pm(mid, channel, dur, rank=10.0, hook=True, clip=True, risk=(), topics=("pri
 148 |              "duration_s": dur, "rank_score": rank, "scores": dict(SCORES), "risk": list(risk), "topics": list(topics),
 149 |              "eligibility": {"hook": {"ok": hook}, "clip": {"ok": clip}}, "on_screen_ok": True, "excluded": [],
 150 |              "published_at": (NOW - timedelta(hours=6)).isoformat(), "speaker": {"turn_change_inside": None},
 151 | -            "text": "Bitcoin x.", "sentences": [0, 0], "words": [0, 1], "start": 0.0, "end": dur,
 152 | +            "text": f"Bitcoin {mid} x.", "sentences": [0, 0], "words": [0, 1], "start": 0.0, "end": dur,
 153 |              "transcript_sha256": "s"}
 154 |  
 155 |  
 156 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 157 | index 062acfe..9aa23ca 100644
 158 | --- a/tests/package/test_medley.py
 159 | +++ b/tests/package/test_medley.py
 160 | @@ -14,6 +14,7 @@ import json
 161 |  import os
 162 |  import sys
 163 |  import unittest
 164 | +from datetime import timedelta
 165 |  
 166 |  HERE = os.path.dirname(os.path.abspath(__file__))
 167 |  REPO = os.path.dirname(os.path.dirname(HERE))
 168 | @@ -1059,6 +1060,70 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 169 |          self.assertTrue(fail["z"][0].startswith("STEP_A_SAME_VENDOR"))
 170 |  
 171 |  
 172 | +class TestRuling53Reposted(unittest.TestCase):
 173 | +    """RULING 53 (08:06): the same speech re-posted by a second channel is ONE moment, the original publisher's kept and
 174 | +    credited: equal text after normalisation, or 80 % of the words TIME-aligned (the same words in order at one clock
 175 | +    offset). The 07:14 build's pair: CNBC Television (20:55 UTC Nov 12) and Strategy (MicroStrategy) (02:57 UTC Nov
 176 | +    13), the same 13.9 s. Audit 0816 C1 (qwen P0): two speakers saying near-identical words are never merged."""
 177 | +    SPEECH = "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin is about markets."
 178 | +
 179 | +    def m(self, mid, ch, text, hours_ago, vid=None):
 180 | +        return dict(pm(mid, ch, 13.0, vid=vid), text=text, words=[0, len(text.split()) - 1],
 181 | +                    published_at=(NOW - timedelta(hours=hours_ago)).isoformat())
 182 | +
 183 | +    def timed(self, vid, words, t0, gaps):
 184 | +        t, toks = t0, []
 185 | +        for w, g in zip(words, gaps):
 186 | +            toks.append({"word": w, "start": round(t, 3), "end": round(t + g * 0.8, 3)})
 187 | +            t += g
 188 | +        return E.Source(vid, "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", tuple(toks),
 189 | +                        timing="word", file_head=False, vod=True)
 190 | +
 191 | +    def test_the_original_publishers_moment_is_kept_and_the_copy_recorded(self):
 192 | +        orig, copy = self.m("o", "CNBC", self.SPEECH, 10), self.m("c", "STRATEGY", self.SPEECH.upper(), 4)
 193 | +        kept, dup = PK.reposted_once([copy, orig, pm("z", "Z", 9.0)], {})
 194 | +        self.assertEqual([m["moment_id"] for m in kept], ["o", "z"])        # the earliest published, order kept
 195 | +        self.assertIn("the same speech as o (CNBC", dup["c"])
 196 | +        self.assertIn("equal text after normalisation", dup["c"])
 197 | +
 198 | +    def test_a_re_post_aligns_in_time_and_two_speakers_never_merge(self):
 199 | +        words = self.SPEECH.split()                                        # 15 words
 200 | +        rhythm = [0.31, 0.22, 0.4, 0.28, 0.35, 0.3, 0.45, 0.26, 0.33, 0.5, 0.29, 0.37, 0.24, 0.41, 0.3, 0.3, 0.3]
 201 | +        src = {"vA": self.timed("vA", words, 100.0, rhythm),
 202 | +               "vB": self.timed("vB", words + ["and", "more", "after"], 2.5, rhythm)}   # the same audio, +3 words
 203 | +        a = self.m("a", "A", self.SPEECH, 9, vid="vA")
 204 | +        b = dict(self.m("b", "B", self.SPEECH + " and more after", 3, vid="vB"), words=[0, 16])
 205 | +        kept, dup = PK.reposted_once([a, b], src)
 206 | +        self.assertEqual((list(dup), [m["moment_id"] for m in kept]), (["b"], ["a"]))
 207 | +        self.assertIn("15 of the shorter's 15 words time-aligned", dup["b"])
 208 | +        gold, silver = "Bitcoin is the new gold. It is digital.", "Bitcoin is the new silver. It is digital."
 209 | +        src2 = {"vG": self.timed("vG", gold.split(), 5.0, [0.4] * 8),            # qwen's P0: 7 of 8 words equal,
 210 | +                "vS": self.timed("vS", silver.split(), 5.0, [0.25] * 8)}         # another speaker's rhythm
 211 | +        kept, dup = PK.reposted_once([self.m("g", "A", gold, 9, vid="vG"), self.m("s", "B", silver, 3, vid="vS")], src2)
 212 | +        self.assertEqual(dup, {})
 213 | +        kept, dup = PK.reposted_once([self.m("g", "A", gold, 9), self.m("s", "B", silver, 3)], {})
 214 | +        self.assertEqual(dup, {})                                          # no timings: only equal text merges
 215 | +
 216 | +    def test_only_a_second_channel_and_a_readable_time_first(self):
 217 | +        kept, dup = PK.reposted_once([self.m("a", "A", self.SPEECH, 9), self.m("b", "A", self.SPEECH, 3)], {})
 218 | +        self.assertEqual(dup, {})                                          # one channel twice: not this rule
 219 | +        nodate = dict(self.m("u", "B", self.SPEECH, 0), published_at=None)
 220 | +        kept, dup = PK.reposted_once([nodate, self.m("d", "A", self.SPEECH, 2)], {})
 221 | +        self.assertEqual(list(dup), ["u"])                                 # no readable time is never preferred
 222 | +        naive = dict(self.m("n", "B", self.SPEECH, 0), published_at="2026-11-01T00:00:00")
 223 | +        kept, dup = PK.reposted_once([self.m("d", "A", self.SPEECH, 2), naive], {})
 224 | +        self.assertEqual(list(dup), ["d"])                                 # no zone: read as UTC (the earliest)
 225 | +
 226 | +    def test_the_build_never_offers_the_copy_and_records_it(self):
 227 | +        ms = [pm("h", "A", 12.0), self.m("x", "B", self.SPEECH, 10), pm("y", "C", 13.0), pm("z", "D", 13.0),
 228 | +              self.m("w", "E", self.SPEECH, 2)]
 229 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 230 | +        out = rig.run()
 231 | +        self.assertEqual(list(out["reposted"]), ["w"])
 232 | +        self.assertNotIn("id=w ", next(p for r, p in rig.prompts if r == "angle_write"))
 233 | +        self.assertEqual(out["usable"], 5)                                 # usable keeps its meaning
 234 | +
 235 | +
 236 |  class TestRuling41Search(unittest.TestCase):
 237 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 238 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 239 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips
from several YouTube channels). Your role: a strict reviewer of a de-duplication rule.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- build() takes the usable moments (each with moment_id, channel_id, channel_name, video_id, text, published_at),
  screens them (step A, L-v 2, CUTTABLE, ...), and offers the survivors to an angle writer, which proposes line-ups.
  The sign-off credits the channel of every clip that plays.
- The 07:14 build: Strategy (MicroStrategy) re-posted CNBC Television's interview six hours later. The same 13.9 s
  speech appeared as two moments, and the angle writer built every angle on both copies.

The order this diff implements (ORCHESTRATOR RULING 53, 08:06 ET Nov 13, verbatim): "PROPOSAL 2: YES. The same speech
re-posted by a second channel is ONE moment before the angle step; keep the ORIGINAL publisher's (earliest
published_at), credit the original, and record the copy as a duplicate with its reason. Equal text after
normalisation, or time-aligned overlap of 80 % of the words."

The change:
1. pipeline/package.py:
   - reposted_once(ms) -> (kept, {copy id: why}). Two moments on DIFFERENT channels are the same speech when:
     - their canonical tokens (canon.canon_tokens, the pipeline's one normal form) are equal; or
     - an in-order alignment (difflib.SequenceMatcher matching blocks, autojunk off) covers at least 80 %
       (REPOST_ALIGN_MIN) of the SHORTER moment's words.
     A multiset-overlap pre-check skips a pair whose shared words cannot reach 80 %. It is an upper bound, so no
     match is lost.
   - Groups are merged transitively (union-find). Per group the kept moment is the earliest READABLE published_at;
     a moment with no readable time is never preferred; a tie goes to the lower moment id.
   - Each copy's reason names the original (id, channel, time), the copy's channel and time, and the match.
   - build() applies it right after usable(), before the STAND_ALONE screens, the trimmed variants and step A.
     out["reposted"] records the copies; out["usable"] keeps its count from before (its meaning since audit 0310);
     the log line counts the copies.
   - "Credit the original": only the kept moment plays, so the sign-off credits the original's channel.
2. tests/moments/test_moments.py: the shared test helper pm() gave EVERY test moment the same text "Bitcoin x.". Under
   this rule those would all be one speech on many channels, so the default text is now distinct per moment
   ("Bitcoin <id> x.").
3. tests/package/test_medley.py (+ `from datetime import timedelta`):
   - the original is kept and the copy is recorded, with the order kept;
   - 2 extra words still align (a duplicate); 7 of 12 words do not;
   - one channel twice is not this rule;
   - a moment with no readable time is never preferred;
   - the build never offers the copy, records it, and keeps usable's count.
- Measured on the 07:14 build's real 308 moments: 2 copies found, both Strategy re-posts of CNBC Television, one with
  equal text and one with 38 of 38 words aligned. 2.3 s.
- test_medley 86 OK; every other suite OK.

Stated readings (say so if you read the ruling differently):
- K1: "time-aligned overlap of 80 % of the words" is read as an in-order alignment of the two word sequences covering
  80 % of the shorter moment's words. Two re-posts have different clocks, so the alignment is by the words.
- K2: the rule runs on the usable moments, before step A, not only on the cleared pool just before the angle. That
  keeps the original even when a copy would survive a later gate the original fails, as "keep the ORIGINAL
  publisher's, credit the original" asks, and it saves the copy's step-A and L-v 2 calls.
- K3: only DIFFERENT channels ("a second channel"). The same speech twice from one channel is out of this rule; the
  package's duplicate check still covers it.

Check in particular: the match never merges two different speeches that merely share words (the 80 % bound, the
pre-check); the original is chosen by publish time and not by order; no copy can reach the angle step; the recorded
reason; and anything that could be slow on 300 moments.

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
