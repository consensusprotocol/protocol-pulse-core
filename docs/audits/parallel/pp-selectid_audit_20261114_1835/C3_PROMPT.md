# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1835
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 136 s finish=stop usage in 13149 / out 3691 usd~0.095 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-20261114_1835, ruling 104's directive path)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **glm's H1 (crash on `{"directives": 5}`)** — I missed this. `json.load(f).get("directives")` returns `5`, then the dict comprehension iterates it → TypeError outside the try at proof_ledger.py:154-157, which kills the whole ledger build, not just the directive. That's the strongest finding of Cycle 1: a one-key typo in a builder-written file stops a build. Now fixed (proof_ledger.py:158-159, `if not isinstance(rows, list): return {}`), and the test at test_ruling_104.py:284-287 covers `5`, `None`, a bare list, and bare `null`. Killed properly.
- **glm's silent-ignore on the one-sentence parent** — I missed that the `continue` at tail_variant.py:87 (one-sentence parent) silently swallowed a named directive. Now noted at :85-86 before the `continue`. Correct fix, correct placement (the note is written *before* the continue, so it survives).
- **grok's "parent dropped on bad directive ends"** — I missed the interaction: the old code's `continue` after a failed directive_variant also skipped the parent's own hold/ceiling triggers, so a miss didn't just fail to add a variant, it *removed* the parent's own ruling-104 rights. The fix (no `continue` on miss; the note is prepended and the triggers below still run) is the right shape, and the note-merging at :117-119 and :128-129 (`notes[mid] + "; " if mid in notes else ""`) is what makes the combined note possible. Test at :262-276 covers it, including the hold-variant case.
- **qwen's L-k (ad-hoc "..." strip)** — I missed that directive_variant stripped the leading "..." itself. The fix (delete the strip, rely on canon) is verified in their consensus note: both `"...I still don't use my Roth IRA."` and `"…I still ..."` canon to the same tokens. Agree it's the right fix; the comment at :62 now documents it.

## 2. AGREE / DISAGREE ON THEIR KEY FINDINGS

- **grok (parent dropped on miss): AGREE, and the fix is correct.** Verified in the diff: the miss path at :96-97 sets the note and *falls through* to the hold/ceiling triggers. The test at :272-276 proves the hold's variant is still made with the miss note kept. One subtlety they didn't note: the miss path also falls through when the directive's *source* is missing (`continue` at :94) — that one still skips the triggers, but there the parent can't be variant-built anyway (no word record), so the skip is harmless. No finding.
- **qwen <critical> L-k: PARTIALLY AGREE.** The original strip was a real wart, but calling it <critical> was generous — the comparison was still canon-vs-canon on both sides, so the failure mode was a missed match, not a wrong one, and it was fail-closed. The fix is right; the severity was not. Their <high> (field validation) they themselves walked back to "not a model reply, so L-l doesn't govern" mid-finding — I agree with their own correction: it's a fail-closed builder input, and the added type/shape checks (20-hex parent, `moments-<run>-<8hex>` story id, non-blank ends/by) are good hygiene, not a law repair. The regex at :161-165 is anchored (`re.fullmatch` for the parent, `story.match` + the `$` in the pattern for the story id) — verified.
- **glm H5 (directive variant skips the 35 s ceiling): AGREE, documented, correctly.** The consensus note says every pool moment still faces `spotlight.pool`'s `usable(seg_max=35 s)` and every later gate. I can't see spotlight.pool in this diff, but the background states it as an unchanged fact ("Every gate ... runs on every pool moment, the variant included"), so I take it as given. Their "not verifiable from the diff" hedge was the right call, and the consensus resolution (downstream gate catches it) is consistent with the stated background. No change needed.
- **glm H4 (alternative_to="" behaves as no-alternative): MOOT.** The new validation at :164 requires `story.match(d["alternative_to"])`, and the regex requires the `moments-` prefix, so `""` is now dropped at read time. Their finding is fixed as a side effect of qwen's <high> fix. Nobody noted this convergence; it's worth stating.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (medium) — proof_ledger.py:173-175, `spot_place` reads `pk["segments"][0]` and `pk["spotlight"]["derived_from"]["alternative_to"]` with unchecked indexing.** Concrete sequence: a package whose `segments` is `[]` raises IndexError at :174; IndexError is not in the `except (package_pin.PinRefused, ValueError, OSError)` tuple at :213, so the ledger build dies instead of noting. Same for a package whose `spotlight` lacks `derived_from` — no, that one is guarded (`(pk.get("spotlight") or {}).get("derived_from") or {}`), verified. So the exposure is exactly: empty `segments` → IndexError → build crash. glm flagged this in Cycle 1 (their H6, truncated m

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 23 s finish=stop usage in 13090 / out 1079 usd~0.092 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
Grok caught the exact `continue` after `if v is None` in `tail_variant.py:96` (pre-fix) that dropped the parent entirely on a non-matching `ends` (no fallback to normal hold/ceiling triggers, violating “the rules stand”). I had only flagged the duplicate-parent dict-comprehension loss.  
Qwen caught the pre-canon `E.spoken` + manual slice + implicit “...” strip in the original `directive_variant` (lines 62-67 pre-fix), a potential L-k violation. I had reviewed the canon call but missed that the strip was outside the single canonical form.  
GLM caught the non-list `{"directives": 5}` TypeError outside the try (proof_ledger.py:155 pre-fix) and the one-sentence parent silent-ignore. These were outside my Cycle-1 scope.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- Grok’s medium on bad-ends parent drop: fully agree; the fixed `if v is None: notes…` (no `continue`) + later `notes[mid] = (notes.get… + "; " …)` merge now lets normal triggers run and keeps both notes. Mutation D11 killed.  
- Qwen’s L-k critical on ad-hoc normalization: agree on the original risk; disagree it was still critical post-fix—the strip is gone, `C.canon_tokens(E.spoken(...))` is now the sole path, and test_ruling_104.py:245-246 confirms canon drops “...” idempotently.  
- GLM H1/H4 (silent drops, alternative_to=""): agree these were consistency warts; the new strict `directives()` regex + type + non-blank checks (lines 162-165) plus test with malformed rows (lines 284-294) close them.  
- GLM H5 (ceiling bypass): partially agree—the `continue` after adding directive variant still skips *for_pool’s* local ceiling check, but background + test with 35 s ceiling + later `pool.usable` on every returned moment (including variants) makes it non-breaking.  
- GLM H6 (IndexError on empty segments): agree it exists but is unchanged by this diff; not introduced here.

**3. NEW FINDINGS FROM THIS REVIEW**  
<medium> pipeline/tail_variant.py:174 (spot_place call site) + proof_ledger.py:174: `pk["segments"][0]["channel_id"]` remains; a package with `"segments": []` (possible from upstream malformation) raises IndexError inside the ledger `try` but is *not* in the `except (PinRefused, ValueError, OSError)` tuple, crashing the build instead of recording a refusal note. Concrete sequence: malformed package reaches `main()`, `spot_place` line 174 → uncaught IndexError → ledger build aborts. (Not new to this diff, but surfaced by the added `spot_place` extraction.)  
No other breaks verifiable from diff + background. All 14 mutations remain killed; directive path cannot reach pin without a validated builder-written row; variant still faces every gate; ruling 90 one-per-day rule is identical for non-alternatives.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1     | Cycle 2     | Why changed |
|------------------------|-------------|-------------|-------------|
| directive_variant path | <medium>    | none        | Bad-ends `continue` removed; canon path cleaned; one-sentence note added |
| directives() reader    | <medium>    | none        | Strict 20-hex, story-id regex, non-blank, non-list handling per GLM/Qwen |
| day_taken / spot_place | <medium>    | none        | Unified rule, explicit alt return, tests for second-alternative and unreadable record |
| ceiling / gate bypass  | <medium>    | <medium>    | Still skips local ceiling but downstream gates confirmed by background + test |
| segments[0] indexing   | not scored  | <medium>    | Newly visible after extraction to spot_place |

**5. FINAL PRIORITY LIST**  
P2 MEDIUM — pipeline/tail_variant.py:174 (and proof_ledger.py:174): add explicit check `if not pk.get("segments"):` before `[0]`, return refusal note (kill the IndexError path).  
No P0 or P1.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Unifying ruling-90 into `day_taken(..., alternative_to)` and having both pool and pin call it, so the single exception for a named alternative is explicit, testable, and cannot be bypassed without a validated directive row.

**7. PRODUCTION READY?**  
Yes with conditions: (1) address the remaining `pk["segments"][0]` IndexError with an explicit guard and test (P2 above); (2) add one test case passing a >35 s directive variant to confirm `pool.usable(seg_max=35)` still refuses it downstream. Once those two lines/tests land, the feature is ship-ready. All Cycle-1 findings are resolved.

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 75 s finish=stop usage in 14386 / out 2548 usd~0.081 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1835

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I identified the `IndexError` risk in `spot_place` (H6) and the silent drop of directives without `why` (H1). I missed the following:

1.  **The "Silent Parent Drop" on Directive Mismatch (Grok's Key Finding):** In Cycle 1, I analyzed the `for_pool` logic but failed to trace the control flow when `directive_variant` returns `None` (no boundary match). I assumed the `continue` statement at the end of the directive block (which was present in the *original* pre-fix code or implied by the "in its place" logic) would skip the parent's normal trigger checks. Grok correctly identified that if a directive is present but invalid (e.g., `ends` doesn't match any boundary), the parent was being silently excluded from the pool without its normal hold/ceiling triggers running. This violated "the rules stand." The fix in the current diff (lines 96-97) addresses this by *not* continuing, allowing the normal triggers to run. I missed this specific control-flow defect in the pre-fix state and its resolution.
2.  **The `IndexError` in `spot_place` (My H6, but I under-weighted it):** I flagged it as a "crash" but didn't explicitly verify if it was caught. Looking at `proof_ledger.py:174`, `pk["segments"][0]` is accessed *outside* the `try` block that wraps the pin logic in `main` (lines 192-213). Wait, looking closer at the diff: `spot_place` is called at line 198. The `try` block starts at line 192. `spot_place` is *inside* the try. However, `spot_place` itself does not have a try/except for `IndexError`. If `pk["segments"]` is empty, `spot_place` raises `IndexError`. The `except` clause at line 213 catches `(package_pin.PinRefused, ValueError, OSError)`. `IndexError` is **not** caught. This would crash the build. I flagged this in Cycle 1 (H6) but the consensus marked it as "Taken" (fixed) or "Documented"? The consensus says "glm (1), a crash... A non-list value now gives no directive". It does *not* say the `IndexError` in `spot_place` was fixed. Let me re-read the diff.
    *   `spot_place` (line 168-176) accesses `pk["segments"][0]`.
    *   `main` (line 198) calls `spot_place`.
    *   `main`'s `except` (line 213) does NOT catch `IndexError`.
    *   **This is still a live bug.** If a package has no segments, the build crashes with an unhandled `IndexError` instead of failing closed with a note.

3.  **Qwen's L-k "Critical" was a False Positive:** Qwen flagged `E.spoken` as a violation of L-k (One Canonical Form). I agree with the consensus that this is not a violation because `E.spoken` is the canonical read path for ASR tokens, and `C.canon_tokens` is applied to the result. The comparison is canonical. I missed the nuance that `E.spoken` is *part* of the canonical pipeline, not an ad-hoc normalizer.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok (Parent Drop on Bad Directive):** **Agree.** This was the most significant logic error in the pre-fix code. The current diff fixes it by removing the `continue` on directive failure, allowing normal triggers to run.
*   **Qwen (L-k Critical):** **Disagree.** `E.spoken` is the standard way to get text from tokens in this codebase. It is not an ad-hoc normalizer. The use of `C.canon_tokens` on the result satisfies L-k.
*   **Qwen (L-l High):** **Disagree.** `directives()` is a builder input, not a model reply. L-l applies to model replies. However, the fail-closed validation added (20-hex parent, story id format) is good practice and addresses the spirit of M12.
*   **GLM (IndexError in spot_place):** **Agree.** This is a real crash risk. The `except` block in `main` does not catch `IndexError`.
*   **GLM (Silent Drop of `why`):** **Agree.** The `directives()` function now requires `by` to be non-blank, but `why` is still optional. This is consistent with the builder's writer, so it's a minor consistency wart, not a break.

## 3. NEW FINDINGS FROM THIS REVIEW

**<high> H1 — `proof_ledger.py:174` (spot_place): Unhandled `IndexError` on empty segments.**
*   **File:** `tests/package/proof_ledger.py`
*   **Issue:** `spot_place` accesses `pk["segments"][0]["channel_id"]`. If `pk["segments"]` is an empty list, this raises `IndexError`.
*   **Concrete Sequence:**
    1.  A package is created with no segments (malformed or edge case).
    2.  `main` calls `spot_place(sp["package"], again, now)` at line 198.
    3.  `spot_place` raises `IndexError`.
    4.  The `except` block at line 213 catches `(package_pin.PinRefused, ValueError, OSError)`. `IndexError` is not caught.
    5.  The build crashes with a traceback instead of failing closed with a note.
*   **Fix:** Add `IndexError` to the `except` tuple in `main`, or add a check in `spot_place` for empty segments.

**<medium> H2 — `tail_variant.py:66` (directive_variant): Potential `IndexError` if `

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 20261114_1835 (ruling 104's directive path), cycle 2: consensus

- grok-4.20: yes with conditions. No P0 or P1.
- qwen3.8-27b: yes with conditions. No P0. One <high>: the IndexError on an empty package.
- glm-5.3-flash: yes with conditions. No P0 or P1. It notes that the cycle-1 <critical> and <high> were, on inspection,
  a wart and a hygiene item, both fixed.

## Taken (cycle 3 reviews these)

- **All three: spot_place read pk["segments"][0] unguarded.** An empty or odd package would raise an IndexError
  outside the pin's except, and stop the build instead of refusing the pin. The inline check this replaced had the same
  exposure. spot_place now refuses ("a spotlight without its segment has no channel to place") for an empty, missing or
  non-object segment list. Tests cover [], None and ["x"]; mutation D14 is killed.
- **qwen P2 / glm (2), the story id.** `$` lets a trailing newline through. The match is now re.fullmatch on the pins'
  own form (moments-<run>-<8 hex>), tested against to_pin's real id "moments-ledger_20261114_230148-3f481f5a" and
  against a trailing "\n". Mutation D15 is killed.
- **grok (2), the ceiling.** A test now gives a 36 s alternative to spotlight.pool: refused by usable's 35 s ceiling,
  directive or not.

## Documented, no change

- **qwen P2, directive_variant on a source with no sentences.** The parent's own sentences [k0, k1] index the same
  source; for_pool reaches directive_variant only for a parent with k1 > k0, whose source has those sentences.
- **glm (2), the count of dropped directive rows.** The builder writes the file. The build's RULING 104 line names
  each named parent's outcome, and a parent whose row was dropped has no directive note, which is visible there.
- **glm (3), the colliding id in "already in the pool".** The note names the variant's id, and it is in the pool beside
  it.

Verification: 16 of 16 mutations killed. test_ruling_104, test_spotlight and test_ledger_build, 98 passed.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_1835/C3_STEP.diff (343 lines)
```
   1 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
   2 | index 370390e..5f7daa3 100644
   3 | --- a/pipeline/spotlight.py
   4 | +++ b/pipeline/spotlight.py
   5 | @@ -189,6 +189,14 @@ def snap(m, sources, ctx, captions_for=None, target=SNAP_TO_S):
   6 |      return rec, None
   7 |  
   8 |  
   9 | +def day_taken(spotlit, channel_id, day, alternative_to=None):
  10 | +    """RULING 90: the channel already has a spotlight on this ET day. RULING 104 on the orchestrator's directive: a
  11 | +    variant that is the ALTERNATIVE to a named sealed spotlight takes that story's place, and only that one (any other
  12 | +    record of the channel that day still takes it). One rule for the pool and for the pin. -> bool."""
  13 | +    return any(r.get("channel_id") == channel_id and r.get("day_et") == day and
  14 | +               not (isinstance(alternative_to, str) and r.get("story_id") == alternative_to) for r in spotlit)
  15 | +
  16 | +
  17 |  def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), captions_for=None):
  18 |      """Stage 1, FREE (no vendor call) -> (the moments that may be a spotlight, {moment id: why not}): package.usable
  19 |      with ruling 90's 35 s ceiling (inside 12 h on the render clock, never a delivered span or the same speech, no hard
  20 | @@ -204,11 +212,11 @@ def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), ca
  21 |                                      "record cannot be read)" for m in ms})
  22 |          return [], why
  23 |      day = et_day(ctx.now)
  24 | -    taken = {r["channel_id"] for r in spotlit if r.get("day_et") == day}
  25 | +
  26 |      out, seen = [], set()
  27 |      for m in ms:
  28 |          mid = m["moment_id"]
  29 | -        if m["channel_id"] in taken:
  30 | +        if day_taken(spotlit, m["channel_id"], day, (m.get("derived_from") or {}).get("alternative_to")):
  31 |              why[mid] = f"ruling 90: this channel already has a spotlight on {day} (ET)"
  32 |              continue
  33 |          v, target = m, SNAP_TO_S + (TRIM_MARGIN_S if P.hook_trim(m) else 0.0)
  34 | diff --git a/pipeline/tail_variant.py b/pipeline/tail_variant.py
  35 | index ce29936..36973ce 100644
  36 | --- a/pipeline/tail_variant.py
  37 | +++ b/pipeline/tail_variant.py
  38 | @@ -19,7 +19,10 @@ a variant that drops the speaker's own condition or conclusion fails there."
  39 |    A parent with a current hold is REPLACED by its variant ("the hold is final and the clip may only be saved by a
  40 |    variant that leaves the token out", ruling 103): the two never compete for a line-up or a finalist's place. A parent
  41 |    over the ceiling stays beside its variant (the medley may still use it).
  42 | -A variant is never snapped outward (spotlight.snap): that would put back the words it leaves out."""
  43 | +A variant is never snapped outward (spotlight.snap): that would put back the words it leaves out.
  44 | +- directive_variant(): ONLY on the orchestrator's written directive (proof_ledger.DIRECTIVES, written by the builder
  45 | +  quoting the ruling), the variant of a NAMED parent ending as the directive says, as the ALTERNATIVE to a named sealed
  46 | +  spotlight (ruling 90's one place per channel per day then admits it beside that story, and nothing else)."""
  47 |  import attest as AT
  48 |  import canon as C
  49 |  import eligibility as E
  50 | @@ -90,9 +93,27 @@ def held_word(m, src, entry):
  51 |      return None
  52 |  
  53 |  
  54 | -def for_pool(moments, sources, ctx, results_dir, ceil_s):
  55 | -    """The ruling-104 variants for this build's pool. -> (variants, {parent id: why it has none / which it got},
  56 | -    {the ids of the parents a current hold makes final: replaced by their variants})."""
  57 | +def directive_variant(m, src, ctx, d):
  58 | +    """The orchestrator's directive `d` ({"parent", "ends", "alternative_to", "by", "why"}) on the parent `m`: its variant
  59 | +    ending at the longest earlier sentence boundary whose words END as d["ends"] (canon tokens), recorded with the
  60 | +    directive and the spotlight it is the alternative to. -> (variant, None) or (None, why there is none)."""
  61 | +    k0, k1 = m["sentences"]
  62 | +    want = C.canon_tokens(str(d.get("ends") or ""))      # canon drops a leading "..." itself (L-k: one form)
  63 | +    if not want:
  64 | +        return None, "the directive names no ending"
  65 | +    for k in range(k1 - 1, k0 - 1, -1):
  66 | +        got = C.canon_tokens(E.spoken(src.tokens[src.sentences[k0][0]:src.sentences[k][1] + 1]))
  67 | +        if got[-len(want):] == want:
  68 | +            v = variant(m, src, k, ctx, f"the orchestrator's directive ({d.get('by')}): {d.get('why') or ''}".strip())
  69 | +            v["derived_from"].update(directive=d.get("by"), alternative_to=d.get("alternative_to"))
  70 | +            return v, None
  71 | +    return None, f"no earlier sentence boundary of the parent ends {d.get('ends')!r}"
  72 | +
  73 | +
  74 | +def for_pool(moments, sources, ctx, results_dir, ceil_s, directives=None):
  75 | +    """The ruling-104 variants for this build's pool. directives: {parent id: the orchestrator's directive} (a parent
  76 | +    named there gets the directive's variant, in its place, whatever its pre-check says). -> (variants, {parent id: why
  77 | +    it has none / which it got}, {the ids of the parents replaced by their variants})."""
  78 |      import context_integrity as CI
  79 |      have = {m["moment_id"] for m in moments}
  80 |      out, notes, replaced = [], {}, set()
  81 | @@ -100,8 +121,29 @@ def for_pool(moments, sources, ctx, results_dir, ceil_s):
  82 |          mid = m["moment_id"]
  83 |          k0, k1 = m.get("sentences") or (None, None)
  84 |          if not (isinstance(k0, int) and isinstance(k1, int) and k1 > k0):
  85 | +            if mid in (directives or {}):                # glm, audit 1835 C1: never a silent ignore
  86 | +                notes[mid] = "the directive: no variant, the parent is one sentence (no earlier boundary)"
  87 |              continue                                     # one sentence: no earlier boundary
  88 |          wanted = []
  89 | +        if mid in (directives or {}):                    # the orchestrator's directive: this variant, in its place
  90 | +            try:
  91 | +                src = CI.source_for(m, sources)
  92 | +            except KeyError:
  93 | +                notes[mid] = "the directive: no variant, its word record is not in this build"
  94 | +                continue
  95 | +            v, why = directive_variant(m, src, ctx, directives[mid])
  96 | +            if v is None:                                # the rules stand: the triggers below still apply to it
  97 | +                notes[mid] = f"the directive: no variant, {why}"
  98 | +            elif v["moment_id"] in have:
  99 | +                notes[mid] = f"the directive: its variant {v['moment_id']} is already in the pool"
 100 | +            else:
 101 | +                have.add(v["moment_id"])
 102 | +                out.append(v)
 103 | +                replaced.add(mid)
 104 | +                notes[mid] = (f"the directive's variant {v['moment_id']} ({v['duration_s']} s, ends "
 105 | +                              f"{v['text'][-60:]!r}), in its place, the alternative to "
 106 | +                              f"{v['derived_from'].get('alternative_to')}")
 107 | +                continue
 108 |          e = holds(m, results_dir)
 109 |          try:
 110 |              src = CI.source_for(m, sources)
 111 | @@ -120,8 +162,9 @@ def for_pool(moments, sources, ctx, results_dir, ceil_s):
 112 |                                             f"{src.tokens[i].get('start')} s (the lock pre-check's hold, "
 113 |                                             f"{e.get('request_id')})"))
 114 |                  else:                                    # no variant can leave the held word out: none at all,
 115 | -                    notes[mid] = ("no variant: the held word cannot be placed" if i is None else   # not even the
 116 | -                                  "no variant: the held word is in its first sentence")             # ceiling's (qwen,
 117 | +                    notes[mid] = (notes[mid] + "; " if mid in notes else "") + (            # not even the
 118 | +                        "no variant: the held word cannot be placed" if i is None else          # ceiling's (qwen,
 119 | +                        "no variant: the held word is in its first sentence")
 120 |                      continue                                                                         # audit 1441 C2)
 121 |          if float(m.get("duration_s") or 0) > ceil_s:
 122 |              t0 = float(m["start"])
 123 | @@ -141,6 +184,7 @@ def for_pool(moments, sources, ctx, results_dir, ceil_s):
 124 |              continue
 125 |          have.add(v["moment_id"])
 126 |          out.append(v)
 127 | -        notes[mid] = (f"variant {v['moment_id']} ({v['duration_s']} s, ends {v['text'][-60:]!r})"
 128 | +        notes[mid] = (notes[mid] + "; " if mid in notes else "") + (
 129 | +                      f"variant {v['moment_id']} ({v['duration_s']} s, ends {v['text'][-60:]!r})"
 130 |                        + (", in its place" if mid in replaced else ", beside it"))
 131 |      return out, notes, replaced
 132 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 133 | index b646c26..9eeb541 100644
 134 | --- a/tests/package/proof_ledger.py
 135 | +++ b/tests/package/proof_ledger.py
 136 | @@ -74,6 +74,7 @@ import tail_variant as TV  # noqa: E402
 137 |  
 138 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 139 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
 140 | +DIRECTIVES = os.path.join(HERE, "proof", "RULING_104_DIRECTIVES.json")   # ruling 104: the orchestrator's directives
 141 |  STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1
 142 |  
 143 |  
 144 | @@ -132,13 +133,47 @@ def applied(router):
 145 |      return applies
 146 |  
 147 |  
 148 | -def with_variants(moments, sources, ctx, inputs, say, results_dir=None):
 149 | +def directives(path=None):
 150 | +    """RULING 104: the orchestrator's directives ({"directives": [{"parent", "ends", "alternative_to", "by", "why"}]}),
 151 | +    written by the builder only on the orchestrator's written yes, quoting it. -> {parent id: directive}; none when the
 152 | +    file is absent; an unreadable file or a malformed row is never guessed at: no directive (the rules stand)."""
 153 | +    try:
 154 | +        with open(path or DIRECTIVES) as f:
 155 | +            rows = json.load(f).get("directives") or []
 156 | +    except (OSError, ValueError, AttributeError):
 157 | +        return {}
 158 | +    if not isinstance(rows, list):                       # glm, audit 1835 C1: {"directives": 5} is no directive
 159 | +        return {}
 160 | +    import re
 161 | +    story = re.compile(r"moments-[A-Za-z0-9_]+-[0-9a-f]{8}")         # the pins' own story id form (package_pin.to_pin)
 162 | +    return {d["parent"]: d for d in rows if isinstance(d, dict) and isinstance(d.get("parent"), str) and
 163 | +            re.fullmatch(r"[0-9a-f]{20}", d["parent"]) and isinstance(d.get("ends"), str) and d["ends"].strip() and
 164 | +            isinstance(d.get("alternative_to"), str) and story.fullmatch(d["alternative_to"]) and
 165 | +            isinstance(d.get("by"), str) and d["by"].strip()}
 166 | +
 167 | +
 168 | +def spot_place(pk, again, now):
 169 | +    """RULING 90 at the pin, read again: the spotlight's channel must have no spotlight on this ET day, unless the
 170 | +    package is ruling 104's ALTERNATIVE (the orchestrator's directive) to that day's named story (spotlight.day_taken).
 171 | +    again: the spotlights record, None when it cannot be read (then no pin). -> (why it cannot take the place or None,
 172 | +    the story it is the alternative to or None)."""
 173 | +    alt = ((pk.get("spotlight") or {}).get("derived_from") or {}).get("alternative_to")
 174 | +    segs = pk.get("segments") or []
 175 | +    if not segs or not isinstance(segs[0], dict):            # cycle 2 (all three): never a crash, never a pin
 176 | +        return "ruling 90: a spotlight without its segment has no channel to place", alt
 177 | +    if again is None or SPOT.day_taken(again, segs[0].get("channel_id"), SPOT.et_day(now), alt):
 178 | +        return "ruling 90: this channel already has a spotlight today, or the record cannot be read", alt
 179 | +    return None, alt
 180 | +
 181 | +
 182 | +def with_variants(moments, sources, ctx, inputs, say, results_dir=None, directives_path=None):
 183 |      """RULING 104 (14:12 Nov 14): the build's pool with the tail-side variants (tail_variant.for_pool: a current lock
 184 |      pre-check hold on the parent's span, a cut the render cannot make, the spotlight's seconds ceiling), so every gate
 185 |      judges them from the start, the clip scorer included (its pool is made from these moments). A parent whose current
 186 |      hold is final is replaced by its variant; a parent over the ceiling stays beside it. inputs["ruling_104"] records
 187 |      them, the replaced parents, and why each parent has a variant or none. -> the new list of moments."""
 188 | -    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1])
 189 | +    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1],
 190 | +                                            directives=directives(directives_path))
 191 |      inputs["ruling_104"] = {"variants": [v["moment_id"] for v in variants], "replaced": sorted(replaced),
 192 |                              "notes": notes}
 193 |      say(f"  RULING 104 (the tail-side twin): {len(variants)} variant(s) in the pool, {len(replaced)} held parent(s) "
 194 | @@ -397,9 +432,9 @@ def main(argv=None):
 195 |          try:
 196 |              lock = LP.pin_problems(sp["package"]) + package_pin.window_problems(sp["package"]["segments"])
 197 |              again = SPOT.load_spotlit(SPOTLIGHTS)        # one per channel per day, read again at the pin
 198 | -            if again is None or any(r["channel_id"] == sp["package"]["segments"][0]["channel_id"] and
 199 | -                                    r.get("day_et") == SPOT.et_day(now) for r in again):
 200 | -                lock.append("ruling 90: this channel already has a spotlight today, or the record cannot be read")
 201 | +            why_place, alt = spot_place(sp["package"], again, now)
 202 | +            if why_place:
 203 | +                lock.append(why_place)
 204 |              if lock:
 205 |                  raise package_pin.PinRefused("; ".join(lock))
 206 |              path, pin = package_pin.write_pin(sp["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 207 | @@ -414,7 +449,8 @@ def main(argv=None):
 208 |              SPOT.record_spotlit(SPOTLIGHTS, {"channel_id": sg["channel_id"], "channel": sg["channel"],
 209 |                                               "day_et": SPOT.et_day(now), "story_id": pin["story_id"],
 210 |                                               "package_sha256": pin["moments_package"]["package_sha256"],
 211 | -                                             "at": now.isoformat(timespec="seconds"), "build": name})
 212 | +                                             "at": now.isoformat(timespec="seconds"), "build": name,
 213 | +                                             **({"alternative_to": alt} if alt else {})})    # ruling 104
 214 |              say(f"SPOTLIGHT PIN {path} ({sg['channel']}, {sg['duration_s']} s, closing line "
 215 |                  f"{sp['package']['vo']['closing']!r})")
 216 |          except (package_pin.PinRefused, ValueError, OSError) as e:
 217 | diff --git a/tests/package/test_ruling_104.py b/tests/package/test_ruling_104.py
 218 | index 728f40a..585955a 100644
 219 | --- a/tests/package/test_ruling_104.py
 220 | +++ b/tests/package/test_ruling_104.py
 221 | @@ -260,3 +260,121 @@ class TestTheSpotlight(unittest.TestCase):
 222 |  
 223 |  if __name__ == "__main__":
 224 |      unittest.main()
 225 | +
 226 | +
 227 | +DIRECTIVE = {"parent": None, "ends": "...I still don't use my Roth IRA.", "alternative_to": "moments-x-3f481f5a",
 228 | +             "by": "orchestrator 18:4x ET Nov 14", "why": "two of three readings of the token say 401"}
 229 | +
 230 | +
 231 | +class TestTheDirective(unittest.TestCase):
 232 | +    """RULING 104 on the orchestrator's written directive: a NAMED parent's variant ending as the directive says, as
 233 | +    the ALTERNATIVE to a named sealed spotlight; nothing without a directive."""
 234 | +
 235 | +    def setUp(self):
 236 | +        self.d = tempfile.TemporaryDirectory()
 237 | +        self.addCleanup(self.d.cleanup)
 238 | +
 239 | +    def test_the_directive_names_the_ending_and_the_variant_records_it(self):
 240 | +        src, m = blockware()
 241 | +        d = dict(DIRECTIVE, parent=m["moment_id"])
 242 | +        v, why = TV.directive_variant(m, src, CTX, d)
 243 | +        self.assertIsNone(why)
 244 | +        self.assertEqual(v["text"], " ".join(SENTENCES[:3]))
 245 | +        self.assertEqual((v["derived_from"]["directive"], v["derived_from"]["alternative_to"]),
 246 | +                         ("orchestrator 18:4x ET Nov 14", "moments-x-3f481f5a"))
 247 | +        self.assertEqual(v["mined"]["derived_from"]["alternative_to"], "moments-x-3f481f5a")   # in its mined record
 248 | +        for ends in ("...by 45.", "...I sold every stock", ""):                # the parent's own end; mid-sentence;
 249 | +            self.assertIsNone(TV.directive_variant(m, src, CTX, dict(d, ends=ends))[0], ends)   # nothing named
 250 | +
 251 | +    def test_a_named_parent_is_replaced_whatever_its_pre_check_says(self):
 252 | +        src, m = blockware()
 253 | +        put(self.d.name, m, [hold(m, outcome="no_difference")])                 # its current answer: a pass
 254 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0,
 255 | +                                          directives={m["moment_id"]: dict(DIRECTIVE, parent=m["moment_id"])})
 256 | +        self.assertEqual(([v["sentences"] for v in vs], replaced), ([[0, 2]], {m["moment_id"]}))
 257 | +        self.assertIn("the alternative to moments-x-3f481f5a", notes[m["moment_id"]])
 258 | +        self.assertEqual(TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0), ([], {}, set()))   # none
 259 | +        one = parent(src, 2, 2)                                                    # a one-sentence parent: noted
 260 | +        vs, notes, _ = TV.for_pool([one], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0,
 261 | +                                   directives={one["moment_id"]: dict(DIRECTIVE, parent=one["moment_id"])})
 262 | +        self.assertEqual((vs, notes), ([], {one["moment_id"]: "the directive: no variant, the parent is one sentence "
 263 | +                                                             "(no earlier boundary)"}))
 264 | +
 265 | +    def test_a_directive_that_matches_nothing_leaves_the_rules_standing(self):
 266 | +        """grok, audit 1835 C1: a directive whose ending is no boundary changes nothing: the parent stays in the pool,
 267 | +        and its own hold still gives the hold's variant."""
 268 | +        src, m = blockware()
 269 | +        bad = {m["moment_id"]: dict(DIRECTIVE, parent=m["moment_id"], ends="...by 45.")}
 270 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0, directives=bad)
 271 | +        self.assertEqual((vs, replaced), ([], set()))
 272 | +        self.assertIn("the directive: no variant", notes[m["moment_id"]])
 273 | +        out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, {}, lambda s: None, results_dir=self.d.name)
 274 | +        self.assertEqual([x["moment_id"] for x in out], [m["moment_id"]])         # the parent stays
 275 | +        put(self.d.name, m, [hold(m)])                                             # and a current hold still works
 276 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0, directives=bad)
 277 | +        self.assertEqual(([v["sentences"] for v in vs], replaced), ([[0, 2]], {m["moment_id"]}))
 278 | +        self.assertIn("the directive: no variant", notes[m["moment_id"]])
 279 | +        self.assertIn("variant", notes[m["moment_id"]].split("; ")[1])
 280 | +
 281 | +    def test_the_directives_file_is_read_and_never_guessed_at(self):
 282 | +        p = os.path.join(self.d.name, "D.json")
 283 | +        self.assertEqual(PLG.directives(p), {})                                  # absent: none
 284 | +        with open(p, "w") as f:
 285 | +            f.write("{ broken")
 286 | +        self.assertEqual(PLG.directives(p), {})
 287 | +        for odd in ({"directives": 5}, {"directives": None}, [1, 2], None):     # never a crash, never a guess
 288 | +            with open(p, "w") as f:
 289 | +                json.dump(odd, f)
 290 | +            self.assertEqual(PLG.directives(p), {}, odd)
 291 | +        good = dict(DIRECTIVE, parent="06d34e155feae654ee56", alternative_to="moments-ledger_x-3f481f5a")
 292 | +        with open(p, "w") as f:
 293 | +            json.dump({"directives": [good, dict(good, parent="b", by=None), dict(good, parent="c", ends=7), "x",
 294 | +                                      dict(good, parent=5), dict(good, parent="d", alternative_to=None),
 295 | +                                      dict(good, parent="0" * 20, alternative_to="not-a-story"),   # not a story id
 296 | +                                      dict(good, parent="2" * 20, alternative_to="moments-x-3f481f5a\n"),
 297 | +                                      dict(good, parent="1" * 20, ends="  "), dict(good, parent="Z" * 20)]}, f)
 298 | +        self.assertEqual(PLG.directives(p), {"06d34e155feae654ee56": good})       # malformed rows dropped
 299 | +        real = dict(good, alternative_to="moments-ledger_20261114_230148-3f481f5a")   # to_pin's real story id
 300 | +        with open(p, "w") as f:
 301 | +            json.dump({"directives": [real]}, f)
 302 | +        self.assertEqual(PLG.directives(p), {"06d34e155feae654ee56": real})
 303 | +        src, m = blockware()
 304 | +        with open(p, "w") as f:
 305 | +            json.dump({"directives": [dict(DIRECTIVE, parent=m["moment_id"])]}, f)
 306 | +        out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, {}, lambda s: None, results_dir=self.d.name,
 307 | +                                directives_path=p)
 308 | +        self.assertEqual([x["sentences"] for x in out], [[0, 2]])                # in the parent's place
 309 | +
 310 | +    def test_the_alternative_takes_the_day_s_place_only_beside_its_named_story(self):
 311 | +        ctx = E.Context(NOW, REG)
 312 | +        a, b = TS.moment(mid="a", channel="A"), TS.moment(mid="b", channel="B", text=TS.TEXT.replace("money", "asset"))
 313 | +        caps = lambda vid: (None, None)
 314 | +        day = [{"channel_id": "A", "day_et": SPOT.et_day(NOW), "story_id": "moments-x-3f481f5a"}]
 315 | +        alt = dict(a, derived_from={"ruling": 104, "from": "p", "alternative_to": "moments-x-3f481f5a"})
 316 | +        got, why = SPOT.pool([alt, b], {}, ctx, spotlit=day, captions_for=caps)
 317 | +        self.assertEqual(sorted(m["moment_id"] for m in got), ["a", "b"])        # the alternative is admitted
 318 | +        other = dict(a, derived_from={"ruling": 104, "from": "p", "alternative_to": "moments-x-another"})
 319 | +        got, why = SPOT.pool([other, b], {}, ctx, spotlit=day, captions_for=caps)
 320 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # another story's: refused
 321 | +        self.assertIn("already has a spotlight", why["a"])
 322 | +        got, why = SPOT.pool([a, b], {}, ctx, spotlit=day, captions_for=caps)
 323 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # no directive: refused, as before
 324 | +        today = SPOT.et_day(NOW)                                                  # the one rule, as the pin reads it
 325 | +        self.assertFalse(SPOT.day_taken(day, "A", today, "moments-x-3f481f5a"))
 326 | +        self.assertTrue(SPOT.day_taken(day, "A", today, None))
 327 | +        self.assertTrue(SPOT.day_taken(day + [{"channel_id": "A", "day_et": today, "story_id": "moments-alt"}], "A",
 328 | +                                       today, "moments-x-3f481f5a"))             # one alternative, not two
 329 | +        self.assertFalse(SPOT.day_taken(day, "A", "2026-11-15", None))           # another day
 330 | +        pk = {"segments": [{"channel_id": "A"}],
 331 | +              "spotlight": {"derived_from": {"ruling": 104, "alternative_to": "moments-x-3f481f5a"}}}
 332 | +        self.assertEqual(PLG.spot_place(pk, day, NOW), (None, "moments-x-3f481f5a"))     # at the pin: admitted
 333 | +        self.assertTrue(PLG.spot_place({"segments": [{"channel_id": "A"}]}, day, NOW)[0])  # no directive: refused
 334 | +        self.assertTrue(PLG.spot_place(pk, None, NOW)[0])                                  # unreadable: refused
 335 | +        for bad in (dict(pk, segments=[]), dict(pk, segments=None), dict(pk, segments=["x"])):   # never a crash
 336 | +            self.assertIn("without its segment", PLG.spot_place(bad, day, NOW)[0])
 337 | +        long_ = dict(alt, duration_s=36.0)                                       # the alternative still faces the
 338 | +        got, why = SPOT.pool([long_], {}, ctx, spotlit=day, captions_for=caps)   # 35 s ceiling (usable)
 339 | +        self.assertEqual(got, [])
 340 | +        no_id = [{"channel_id": "A", "day_et": SPOT.et_day(NOW)}]                 # a record without a story id
 341 | +        got, _ = SPOT.pool([a, alt, b], {}, ctx, spotlit=no_id, captions_for=caps)
 342 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # admits no one
 343 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- RULING 104 (the orchestrator, 14:12 ET Nov 14), already implemented and committed (5aad59b5): "a spotlight (and a
  medley hook or clip) may be sealed as a variant that ENDS at an earlier sentence boundary of the mined moment, when
  that is what keeps it lawful (a held word after the boundary, a tail the cut cannot make, the seconds ceiling). It
  is a new span: it faces every gate again from the start ..., and the variant is recorded as derived from its parent
  row."
  - pipeline/tail_variant.py makes such variants at pool time when the parent's CURRENT lock pre-check answer HOLDS
    (or ruling 73's cut hold, or the 35 s ceiling). A parent with a current hold is REPLACED by its variant.
- RULING 90: at most one spotlight per channel per ET day (tests/package/proof/SPOTLIGHTS.json records each sealed
  spotlight: channel_id, day_et, story_id, ...). spotlight.pool refuses a taken channel's moments. The ledger build
  reads the record again at the pin and refuses there too.
- THE CASE (now): the spotlight pin 3f481f5a, Blockware Solutions 06d34e15, the FULL 22.94 s clip, sealed at 18:23 ET.
  - The integrator's pre-check answered "no_difference" (the second recogniser read "401k" this time).
  - The integrator froze it but has not launched it. Scribe read the token three times today: "401" (13:51, long),
    "401" (14:16, ruling 103's short re-listen, recorded as final) and "401k" (18:17, long).
  - It asks the orchestrator whether the full clip may go. It also asks the builder to have the ruling-104 VARIANT
    (0.000-15.280, ending "...I still don't use my Roth IRA.") ready so the orchestrator can choose before 00:00 ET,
    when the source expires.
  - The builder put the question on STATE line 1. Two of the orchestrator's rules stand in the way of that variant:
    its current pre-check answer is a pass, and ruling 90 gives Blockware's channel to 3f481f5a today. The variant is
    built ONLY on the orchestrator's written yes.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff):
- tail_variant.variant(m, src, k, ctx, why) builds the variant by moments.record over eligibility.Span(src, k0, k):
  eligibility judged afresh, its own id, derived_from on the record and in its mined record (the same dict).
- Every gate (step A both families, CUTTABLE, opener rating, visual, ALONE, exclusion, the lock pre-check, the writes)
  runs on every pool moment, the variant included. spotlight.snap never snaps a ruling-104 variant outward.
- package_pin seals segments; pk["spotlight"] (with derived_from) rides on the pin outside the seal.

THE CHANGE (the diff follows): the builder's path for the orchestrator's DIRECTIVE.
1. tests/package/proof_ledger.py:
   - DIRECTIVES = tests/package/proof/RULING_104_DIRECTIVES.json, written by the builder ONLY on the orchestrator's
     written yes, quoting it.
   - directives(path) reads {"directives": [{"parent", "ends", "alternative_to", "by", "why"}]}. An absent or
     unreadable file, or a malformed row, gives no directive (the rules stand).
   - with_variants passes them to for_pool.
   - spot_place(pk, again, now) is the pin-time ruling-90 check through spotlight.day_taken. It also returns the story
     the package is the alternative to, which record_spotlit then records.
2. pipeline/tail_variant.py:
   - directive_variant(m, src, ctx, d): the variant ending at the longest earlier sentence boundary whose words END as
     d["ends"] (canon tokens), recorded with derived_from.directive and derived_from.alternative_to.
   - for_pool(..., directives): a NAMED parent gets the directive's variant, in its place, whatever its pre-check says.
     No variant when no boundary matches (noted).
3. pipeline/spotlight.py: day_taken(spotlit, channel_id, day, alternative_to) is the ONE rule for the pool and the pin.
   A channel's day is taken by any record of it that day, except the one story the moment is the named alternative to.
   An alternative to another story, a moment with no directive, or a record without a story_id admits no one.
4. Tests in test_ruling_104.py (+4) and 10 mutations, each killed.

ATTACK:
(a) Can anything be sealed through this path WITHOUT a directive file the builder wrote (absent, unreadable, malformed,
    another parent)? Can a directive admit a second spotlight that is NOT the named alternative, or a third one?
(b) Does the directive's variant still face every gate (nothing skipped or inherited from the full clip)? Can it end
    mid-sentence, at the parent's own end, or anywhere other than the named ending?
(c) Can the full clip 3f481f5a and its alternative both reach a render without the orchestrator choosing? (The builder
    seals; the integrator launches.)
(d) Any change to ruling 104's hold, cut or ceiling triggers, or to ruling 90 for every moment without a directive?
(e) Anything else that could seal a wrong pin or spend without a directive.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

CHANGED AFTER CYCLE 1 (review the diff as it stands): a directive whose ending matches no boundary now lets the parent's
own triggers run (no `continue`); the leading-"..." strip is gone (canon drops it); directives() requires a 20-hex parent
id, a pin story id for alternative_to, non-blank ends and by, and returns none for a non-list value; a directive on a
one-sentence parent is noted.

CHANGED AFTER CYCLE 2 (cycle 3 reviews only this): spot_place refuses a package without a usable first segment instead
of indexing it; directives() matches alternative_to with re.fullmatch on the pins' story id form; tests for both and for a
36 s alternative refused by the pool's 35 s ceiling.
CYCLE 3 ATTACK: (f) can any path still raise out of the pin's try or the pool? (g) did either change alter a decision for
a well-formed directive or for any moment without one?


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
