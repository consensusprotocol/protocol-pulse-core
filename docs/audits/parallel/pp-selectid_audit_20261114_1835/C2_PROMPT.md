# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1835
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 778 s finish=length usage in 10985 / out 24000 usd~0.393 (upper-bound price)

<critical>None found.</critical>

<high>None found.</high>

<medium>H1 — proof_ledger.py:131-132 (directives): a row whose "why" key is missing or non-string is silently dropped, but "why" is documented as optional in tail_variant.py:68 (`d.get('why') or ''`), so the reader is stricter than the consumer. A directive written without "why" (a perfectly valid directive per the builder's own writer) yields no directive at all — the rules stand, fail-closed, so this is only a consistency wart, not a break. Same for a row where "parent" is a str but duplicated: the later row silently wins (dict comprehension, last-write-wins); no error, no note. If the builder ever writes two rows for one parent (e.g. a corrected directive), the first is discarded without trace. Fail-closed, but silent.

<medium>H2 — tail_variant.py:66-67 (directive_variant): `got[-len(want):] == want` — if `len(got) < len(want)`, the slice yields the whole of `got` and the comparison fails correctly, so no bug; but if `want` is longer than the parent's entire token span the loop scans all k and returns the "no earlier sentence boundary" note — correct. However: the loop range is `range(k1-1, k0-1, -1)` — it never considers k = k0 itself... wait, it does: k0-1 exclusive, so k0 is included. Correct. But note the variant at k = k1-1 is the parent's own full span (sentences [k0, k1-1] vs parent's [k0, k1-1]... actually the parent's sentences field is [k0, k1] and the variant's is [k0, k1-1]) — the variant ending at the LAST sentence boundary (k1-1) is the parent minus its final sentence, not the parent's own end. The test at test_ruling_104.py:212-213 asserts `"...by 45."` (the parent's own end) yields None — consistent: the directive path only makes EARLIER boundaries, the parent's own end is not a variant. Correct per ruling 104 ("ends at an earlier sentence boundary"). No bug.

<medium>H3 — proof_ledger.py:140-142 (spot_place): when `again is None` (unreadable record) it returns the combined message "ruling 90: this channel already has a spotlight today, or the record cannot be read" — the same string the old code appended, so the pin-time message is unchanged. But note the asymmetry: `alt` is returned even when the check fails, and record_spotlit (proof_ledger.py:172-177) records `alternative_to: alt` even when... no — record_spotlit only runs after the pin succeeds (the raise happens first at :168-169), so `alt` is only recorded on success. Correct.

<medium>H4 — proof_ledger.py:177: `**({"alternative_to": alt} if alt else {})` — if `alt` is the empty string, the key is omitted; if a directive's alternative_to were "" the directives() reader requires isinstance(str) so "" passes, day_taken would compare `r.get("story_id") == ""` which never matches a real story_id, so the variant would be refused at the pool (day_taken returns True → why[mid] set → continue) — wait, no: day_taken(day, "A", today, "") — the record's story_id is "moments-x-3f481fH5a", not "", so the exception clause never fires and the channel reads as taken → the variant is refused at the pool despite a valid directive. Fail-closed, consistent with "an alternative to another story... admits no one". No break, but a directive with alternative_to="" is accepted by the reader and then silently behaves as no-alternative. Silent, fail-closed.

<medium>H5 — tail_variant.py:95-98: the directive branch adds the variant to `out` and `have` and marks the parent replaced, but does NOT check the variant against the 35 s ceiling (`ceil_s` parameter is accepted and ignored in this branch — the pre-check path at :102+ applies it). The docstring says "whatever its pre-check says", and the test at :218-221 uses a 35.0 ceiling with a 15.28 s variant so it passes anyway, but a directive variant over 35 s would enter the pool over the ceiling. Whether that's intended ("whatever its pre-check says" — the ceiling is part of the pre-check) or a gap depends on ruling 104's wording: the ceiling is one of the triggers, and the docstring of for_pool says the variant faces "a current lock pre-check hold on the parent's span, a cut the render cannot make, the seconds ceiling" — the directive branch skips all three. If the orchestrator's directive names a parent whose variant exceeds 35 s, it enters the pool over the ceiling. Whether the later gates (the medley's own ceiling check) catch it is not verifiable from the diff. Not verifiable from the diff whether downstream gates re-check the ceiling.

<medium>H6 — proof_ledger.py:141: `pk["segments"][0]["channel_id"]` — if the package's segments list were empty this raises IndexError inside the try at :159-169, caught by `except (PinRefused, ValueError, OSError)` — IndexError is NOT in that tuple, so an empty-segments package crashes the ledger build rather than failing closed with a note. Not new in this diff (the old code at :162-164 had the same

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 99 s finish=stop usage in 11021 / out 527 usd~0.068 (upper-bound price)

<medium> pipeline/tail_variant.py:85-101 (for_pool: if mid in directives): a well-formed directive row (validated by proof_ledger.directives:131) but with "ends" that matches no earlier sentence boundary (e.g. parent's own end "...by 45." or mid-sentence "" or "...I sold every stock" per test_ruling_104.py:212) hits `if v is None: notes[mid]=...; continue` (no fallback to add original m to out, replaced.add only after successful v); concrete sequence: DIRECTIVES.json names the Blockware parent from the case (pre-check="no_difference", passes holds), for_pool returns neither parent nor variant (out excludes it, replaced includes it, notes records "no variant, no earlier sentence boundary..."), violating "the rules stand" / "no directive (the rules stand)" when ends mismatches. Un-tested in new test_ruling_104.py:215-240.

<medium> tests/package/proof_ledger.py:146 (with_variants:153) + tail_variant.py:74: directive path bypasses all normal hold/ceiling logic for a named parent even on pass pre-check (as in case 13:51/18:17 Scribe reads); if directive present but invalid, parent silently dropped rather than normal pool inclusion per ruling-104 docstring ("whatever its pre-check says" only documented for successful case).

No verifiable breaks for (a) second/non-named/third spotlight (day_taken:13 + spot_place:141 + test:249-260 requires exact story_id match on the *one* exempted record; malformed/absent DIRECTIVES:129 returns {} so normal ruling 90), (b) gates/skipping/mid-sentence (unchanged facts + directive_variant:65 loops only sentence k boundaries + canon match + every gate on pool variant per background; test:212 rejects parent's end/mid), (c) both full+variant without directive (replaced.add + out only gets variant when directive succeeds; without directives={} normal path drops variant by ruling 90 per test:254), (d) unintended trigger changes (only adds directive path; ruling 90 exception only on derived_from.alternative_to from that path), or (e) sealing without builder-written directive (requires matching row in DIRECTIVES or pre-crafted moment with exact derived_from; both fail-closed on absent/malformed per 129+234).

SHIP: yes with conditions (fix parent-drop on bad directive ends; add test for for_pool with matching parent + non-matching directive row)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 12083 / out 3051 usd~0.082 (upper-bound price)

I have reviewed the diff against the governing laws and the specific attack vectors. Here are the findings.

### Findings

**<critical> L-k Violation: Ad-hoc Normalization in `directive_variant`**
*   **File:** `pipeline/tail_variant.py` (lines 62-67 in diff)
*   **Issue:** The function `directive_variant` uses `C.canon_tokens` to normalize the directive's `ends` string and the source tokens. However, it performs a raw string slice `src.tokens[src.sentences[k0][0]:src.sentences[k][1] + 1]` and then passes it to `E.spoken` before `C.canon_tokens`.
*   **Law Violation:** **L-k (ONE CANONICAL FORM)** states: *"every text comparison in the pipeline uses pipeline/canon.py... TestSites fails any ad-hoc normaliser outside canon.py."*
*   **Concrete Sequence:** If `E.spoken` performs any transformation (e.g., expanding abbreviations, handling punctuation) that is not idempotent with `C.canon_tokens`, or if the directive's `ends` string contains characters that `C.canon_tokens` handles differently than the processed source tokens, the comparison `got[-len(want):] == want` may fail to match a valid boundary or, worse, match an invalid one if the normalization is inconsistent. More critically, the law requires that *all* text comparisons use `canon.py`. While `canon_tokens` is used, the intermediate step `E.spoken` is an external transformation. If `E.spoken` is not part of the canonical read path defined by L-k (which specifies `transcript_store.read_text` and `story_semantics._norm`), this is a violation. The diff does not show `E.spoken` being routed through `canon.py`'s specific entity/token joining rules (L-h). If `E.spoken` returns raw ASR tokens with entities like `&amp;` or split numbers like `$81 ,000`, `C.canon_tokens` might not fix them if it expects pre-processed text, or if `E.spoken` introduces its own normalization that conflicts with `canon.py`.
*   **Impact:** A directive might be rejected because the "ends" string doesn't match the canonically normalized source, or a wrong boundary might be accepted if the normalization is flawed.

**<high> L-l Violation: Directive Fields Not Validated Against Enumerated Values/Ranges**
*   **File:** `tests/package/proof_ledger.py` (lines 122-132 in diff)
*   **Issue:** The `directives` function reads the JSON file and filters rows based on type checks (`isinstance(d.get("parent"), str)`, etc.). However, it does not validate the *content* of these fields against the rules of **L-l (A MODEL REPLY COUNTS ONLY WHOLE)** or the specific constraints of Ruling 104.
*   **Law Violation:** **L-l** states: *"a local-model reply feeds a decision only when every field that decision reads is present, of its exact type, inside its enumerated values and ranges... anything else is a failed call."* While this is a builder-written file, not a model reply, the principle of **M12 (FAIL CLOSED)** and **LAW 20** applies. The code accepts any string for `ends`, `alternative_to`, and `by`.
*   **Concrete Sequence:**
    1.  Builder writes `RULING_104_DIRECTIVES.json` with `{"parent": "valid_id", "ends": "garbage text that matches no boundary", "alternative_to": "invalid_story_id", "by": "orchestrator", "why": "test"}`.
    2.  `directives()` returns this row because all types are correct.
    3.  `directive_variant` is called. It iterates through boundaries. If no boundary matches `ends`, it returns `(None, "no earlier sentence boundary...")`. This is safe.
    4.  **However**, if `ends` *does* match a boundary, but `alternative_to` points to a story that does not exist or is not the one the channel is currently holding, the `day_taken` logic in `spotlight.py` (line 13-14) checks `r.get("story_id") == alternative_to`. If `alternative_to` is wrong, `day_taken` returns `True` (channel is taken), and the variant is rejected in the pool. This is safe.
    5.  **The Risk:** What if `alternative_to` is correct, but the directive is for a *different* parent than the one currently holding the spotlight? The `for_pool` function (line 85) checks `if mid in (directives or {})`. It only applies the directive to the specific parent ID. This seems safe.
    6.  **Re-evaluating L-l:** The law is about *model* replies. This is a *builder* file. The builder is trusted to write valid JSON. The code fails closed if the file is malformed. The main risk is if the builder writes a directive that *looks* valid but is logically inconsistent (e.g., `ends` matches a boundary, but the resulting variant violates other laws like SENTENCE LAW). The variant *does* face all gates (per background: "Every gate... runs on every pool moment, the variant included"). So, if the variant is illegal, the gates will catch it.
    7.  **Correction:** This is not a critical L-l violation because it's not a model reply. It is a builder input. The system relies on the gates to validate the *result*.

**<medium> Potential Bypass of

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 20261114_1835 (ruling 104's directive path: the orchestrator-ordered alternative variant), cycle 1: consensus

Reviewers:
- grok-4.20: yes with conditions. Two <medium>.
- qwen3.8-27b: yes with conditions. One <critical> (L-k), one <high> (field validation), one <medium>.
- glm-5.3-flash (778 s, finish=length): no <critical> or <high>; yes with four conditions.

## Taken (the diff as it stands now)

- **grok, a directive whose ending matches no boundary.** The parent did stay in the pool (with_variants keeps every
  moment that is not replaced). But the branch's `continue` also skipped that parent's OWN triggers (a current hold,
  the ceiling), which is not "the rules stand".
  - Now a miss is noted and the normal triggers run.
  - Test: a non-matching directive leaves the parent in the pool, and with a current hold the hold's variant is made,
    both notes kept. Mutation D11 is killed.
- **qwen <critical> (L-k, a normaliser outside canon).** directive_variant stripped a leading "..." itself before
  canon. canon.canon_tokens already drops it (checked: "...I still don't use my Roth IRA." and "…I still ..."
  both give ['i', 'still', "don't", 'use', 'my', 'roth', 'ira']). The strip is removed; the comparison is canon's alone.
  The span's text is E.spoken, the canonical read of the record's words (law L-h).
- **qwen <high>, the directive's fields checked by type only.** This is a builder-written file, not a model reply, so
  L-l does not govern it, but fail-closed does. directives() now also requires:
  - parent: a moment id (20 hex);
  - alternative_to: a pin's story id (moments-<run>-<8 hex>);
  - ends and by: non-blank.
  Mutations D5 and D5b are killed.
- **glm (1), a crash.** {"directives": 5} raised a TypeError outside the try and would have stopped a build. A
  non-list value now gives no directive (mutation D12; tests for 5, null, a list file and a null file).
- **glm (3), a silent ignore.** A directive on a one-sentence parent is now noted ("no earlier boundary"), mutation
  D13.

## Documented, no change

- **glm (2)/(4), the directive variant and the 35 s ceiling.** The directive branch makes the variant the orchestrator
  named. Every pool moment, the variant included, still faces spotlight.pool's usable(seg_max=35 s) and every later
  gate. The variant here is 15.28 s.
- **qwen <medium>, two records for the channel that day.** By design, the alternative takes the named story's place
  and records it ("alternative_to"). day_taken admits ONE alternative: a third moment naming the same story is
  refused, because the alternative's own record now takes the day (test).

Verification: 14 of 14 mutations killed. test_ruling_104, test_spotlight and test_ledger_build, 98 passed.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_1835/C2_STEP.diff (330 lines)
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
 133 | index b646c26..f455c18 100644
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
 144 | @@ -132,13 +133,44 @@ def applied(router):
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
 161 | +    story = re.compile(r"^moments-[A-Za-z0-9_]+-[0-9a-f]{8}$")      # the pins' own story id form (package_pin.to_pin)
 162 | +    return {d["parent"]: d for d in rows if isinstance(d, dict) and isinstance(d.get("parent"), str) and
 163 | +            re.fullmatch(r"[0-9a-f]{20}", d["parent"]) and isinstance(d.get("ends"), str) and d["ends"].strip() and
 164 | +            isinstance(d.get("alternative_to"), str) and story.match(d["alternative_to"]) and
 165 | +            isinstance(d.get("by"), str) and d["by"].strip()}
 166 | +
 167 | +
 168 | +def spot_place(pk, again, now):
 169 | +    """RULING 90 at the pin, read again: the spotlight's channel must have no spotlight on this ET day, unless the
 170 | +    package is ruling 104's ALTERNATIVE (the orchestrator's directive) to that day's named story (spotlight.day_taken).
 171 | +    again: the spotlights record, None when it cannot be read (then no pin). -> (why it cannot take the place or None,
 172 | +    the story it is the alternative to or None)."""
 173 | +    alt = ((pk.get("spotlight") or {}).get("derived_from") or {}).get("alternative_to")
 174 | +    if again is None or SPOT.day_taken(again, pk["segments"][0]["channel_id"], SPOT.et_day(now), alt):
 175 | +        return "ruling 90: this channel already has a spotlight today, or the record cannot be read", alt
 176 | +    return None, alt
 177 | +
 178 | +
 179 | +def with_variants(moments, sources, ctx, inputs, say, results_dir=None, directives_path=None):
 180 |      """RULING 104 (14:12 Nov 14): the build's pool with the tail-side variants (tail_variant.for_pool: a current lock
 181 |      pre-check hold on the parent's span, a cut the render cannot make, the spotlight's seconds ceiling), so every gate
 182 |      judges them from the start, the clip scorer included (its pool is made from these moments). A parent whose current
 183 |      hold is final is replaced by its variant; a parent over the ceiling stays beside it. inputs["ruling_104"] records
 184 |      them, the replaced parents, and why each parent has a variant or none. -> the new list of moments."""
 185 | -    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1])
 186 | +    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1],
 187 | +                                            directives=directives(directives_path))
 188 |      inputs["ruling_104"] = {"variants": [v["moment_id"] for v in variants], "replaced": sorted(replaced),
 189 |                              "notes": notes}
 190 |      say(f"  RULING 104 (the tail-side twin): {len(variants)} variant(s) in the pool, {len(replaced)} held parent(s) "
 191 | @@ -397,9 +429,9 @@ def main(argv=None):
 192 |          try:
 193 |              lock = LP.pin_problems(sp["package"]) + package_pin.window_problems(sp["package"]["segments"])
 194 |              again = SPOT.load_spotlit(SPOTLIGHTS)        # one per channel per day, read again at the pin
 195 | -            if again is None or any(r["channel_id"] == sp["package"]["segments"][0]["channel_id"] and
 196 | -                                    r.get("day_et") == SPOT.et_day(now) for r in again):
 197 | -                lock.append("ruling 90: this channel already has a spotlight today, or the record cannot be read")
 198 | +            why_place, alt = spot_place(sp["package"], again, now)
 199 | +            if why_place:
 200 | +                lock.append(why_place)
 201 |              if lock:
 202 |                  raise package_pin.PinRefused("; ".join(lock))
 203 |              path, pin = package_pin.write_pin(sp["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 204 | @@ -414,7 +446,8 @@ def main(argv=None):
 205 |              SPOT.record_spotlit(SPOTLIGHTS, {"channel_id": sg["channel_id"], "channel": sg["channel"],
 206 |                                               "day_et": SPOT.et_day(now), "story_id": pin["story_id"],
 207 |                                               "package_sha256": pin["moments_package"]["package_sha256"],
 208 | -                                             "at": now.isoformat(timespec="seconds"), "build": name})
 209 | +                                             "at": now.isoformat(timespec="seconds"), "build": name,
 210 | +                                             **({"alternative_to": alt} if alt else {})})    # ruling 104
 211 |              say(f"SPOTLIGHT PIN {path} ({sg['channel']}, {sg['duration_s']} s, closing line "
 212 |                  f"{sp['package']['vo']['closing']!r})")
 213 |          except (package_pin.PinRefused, ValueError, OSError) as e:
 214 | diff --git a/tests/package/test_ruling_104.py b/tests/package/test_ruling_104.py
 215 | index 728f40a..3626f7b 100644
 216 | --- a/tests/package/test_ruling_104.py
 217 | +++ b/tests/package/test_ruling_104.py
 218 | @@ -260,3 +260,111 @@ class TestTheSpotlight(unittest.TestCase):
 219 |  
 220 |  if __name__ == "__main__":
 221 |      unittest.main()
 222 | +
 223 | +
 224 | +DIRECTIVE = {"parent": None, "ends": "...I still don't use my Roth IRA.", "alternative_to": "moments-x-3f481f5a",
 225 | +             "by": "orchestrator 18:4x ET Nov 14", "why": "two of three readings of the token say 401"}
 226 | +
 227 | +
 228 | +class TestTheDirective(unittest.TestCase):
 229 | +    """RULING 104 on the orchestrator's written directive: a NAMED parent's variant ending as the directive says, as
 230 | +    the ALTERNATIVE to a named sealed spotlight; nothing without a directive."""
 231 | +
 232 | +    def setUp(self):
 233 | +        self.d = tempfile.TemporaryDirectory()
 234 | +        self.addCleanup(self.d.cleanup)
 235 | +
 236 | +    def test_the_directive_names_the_ending_and_the_variant_records_it(self):
 237 | +        src, m = blockware()
 238 | +        d = dict(DIRECTIVE, parent=m["moment_id"])
 239 | +        v, why = TV.directive_variant(m, src, CTX, d)
 240 | +        self.assertIsNone(why)
 241 | +        self.assertEqual(v["text"], " ".join(SENTENCES[:3]))
 242 | +        self.assertEqual((v["derived_from"]["directive"], v["derived_from"]["alternative_to"]),
 243 | +                         ("orchestrator 18:4x ET Nov 14", "moments-x-3f481f5a"))
 244 | +        self.assertEqual(v["mined"]["derived_from"]["alternative_to"], "moments-x-3f481f5a")   # in its mined record
 245 | +        for ends in ("...by 45.", "...I sold every stock", ""):                # the parent's own end; mid-sentence;
 246 | +            self.assertIsNone(TV.directive_variant(m, src, CTX, dict(d, ends=ends))[0], ends)   # nothing named
 247 | +
 248 | +    def test_a_named_parent_is_replaced_whatever_its_pre_check_says(self):
 249 | +        src, m = blockware()
 250 | +        put(self.d.name, m, [hold(m, outcome="no_difference")])                 # its current answer: a pass
 251 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0,
 252 | +                                          directives={m["moment_id"]: dict(DIRECTIVE, parent=m["moment_id"])})
 253 | +        self.assertEqual(([v["sentences"] for v in vs], replaced), ([[0, 2]], {m["moment_id"]}))
 254 | +        self.assertIn("the alternative to moments-x-3f481f5a", notes[m["moment_id"]])
 255 | +        self.assertEqual(TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0), ([], {}, set()))   # none
 256 | +        one = parent(src, 2, 2)                                                    # a one-sentence parent: noted
 257 | +        vs, notes, _ = TV.for_pool([one], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0,
 258 | +                                   directives={one["moment_id"]: dict(DIRECTIVE, parent=one["moment_id"])})
 259 | +        self.assertEqual((vs, notes), ([], {one["moment_id"]: "the directive: no variant, the parent is one sentence "
 260 | +                                                             "(no earlier boundary)"}))
 261 | +
 262 | +    def test_a_directive_that_matches_nothing_leaves_the_rules_standing(self):
 263 | +        """grok, audit 1835 C1: a directive whose ending is no boundary changes nothing: the parent stays in the pool,
 264 | +        and its own hold still gives the hold's variant."""
 265 | +        src, m = blockware()
 266 | +        bad = {m["moment_id"]: dict(DIRECTIVE, parent=m["moment_id"], ends="...by 45.")}
 267 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0, directives=bad)
 268 | +        self.assertEqual((vs, replaced), ([], set()))
 269 | +        self.assertIn("the directive: no variant", notes[m["moment_id"]])
 270 | +        out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, {}, lambda s: None, results_dir=self.d.name)
 271 | +        self.assertEqual([x["moment_id"] for x in out], [m["moment_id"]])         # the parent stays
 272 | +        put(self.d.name, m, [hold(m)])                                             # and a current hold still works
 273 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0, directives=bad)
 274 | +        self.assertEqual(([v["sentences"] for v in vs], replaced), ([[0, 2]], {m["moment_id"]}))
 275 | +        self.assertIn("the directive: no variant", notes[m["moment_id"]])
 276 | +        self.assertIn("variant", notes[m["moment_id"]].split("; ")[1])
 277 | +
 278 | +    def test_the_directives_file_is_read_and_never_guessed_at(self):
 279 | +        p = os.path.join(self.d.name, "D.json")
 280 | +        self.assertEqual(PLG.directives(p), {})                                  # absent: none
 281 | +        with open(p, "w") as f:
 282 | +            f.write("{ broken")
 283 | +        self.assertEqual(PLG.directives(p), {})
 284 | +        for odd in ({"directives": 5}, {"directives": None}, [1, 2], None):     # never a crash, never a guess
 285 | +            with open(p, "w") as f:
 286 | +                json.dump(odd, f)
 287 | +            self.assertEqual(PLG.directives(p), {}, odd)
 288 | +        good = dict(DIRECTIVE, parent="06d34e155feae654ee56", alternative_to="moments-ledger_x-3f481f5a")
 289 | +        with open(p, "w") as f:
 290 | +            json.dump({"directives": [good, dict(good, parent="b", by=None), dict(good, parent="c", ends=7), "x",
 291 | +                                      dict(good, parent=5), dict(good, parent="d", alternative_to=None),
 292 | +                                      dict(good, parent="0" * 20, alternative_to="not-a-story"),   # not a story id
 293 | +                                      dict(good, parent="1" * 20, ends="  "), dict(good, parent="Z" * 20)]}, f)
 294 | +        self.assertEqual(PLG.directives(p), {"06d34e155feae654ee56": good})       # malformed rows dropped
 295 | +        src, m = blockware()
 296 | +        with open(p, "w") as f:
 297 | +            json.dump({"directives": [dict(DIRECTIVE, parent=m["moment_id"])]}, f)
 298 | +        out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, {}, lambda s: None, results_dir=self.d.name,
 299 | +                                directives_path=p)
 300 | +        self.assertEqual([x["sentences"] for x in out], [[0, 2]])                # in the parent's place
 301 | +
 302 | +    def test_the_alternative_takes_the_day_s_place_only_beside_its_named_story(self):
 303 | +        ctx = E.Context(NOW, REG)
 304 | +        a, b = TS.moment(mid="a", channel="A"), TS.moment(mid="b", channel="B", text=TS.TEXT.replace("money", "asset"))
 305 | +        caps = lambda vid: (None, None)
 306 | +        day = [{"channel_id": "A", "day_et": SPOT.et_day(NOW), "story_id": "moments-x-3f481f5a"}]
 307 | +        alt = dict(a, derived_from={"ruling": 104, "from": "p", "alternative_to": "moments-x-3f481f5a"})
 308 | +        got, why = SPOT.pool([alt, b], {}, ctx, spotlit=day, captions_for=caps)
 309 | +        self.assertEqual(sorted(m["moment_id"] for m in got), ["a", "b"])        # the alternative is admitted
 310 | +        other = dict(a, derived_from={"ruling": 104, "from": "p", "alternative_to": "moments-x-another"})
 311 | +        got, why = SPOT.pool([other, b], {}, ctx, spotlit=day, captions_for=caps)
 312 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # another story's: refused
 313 | +        self.assertIn("already has a spotlight", why["a"])
 314 | +        got, why = SPOT.pool([a, b], {}, ctx, spotlit=day, captions_for=caps)
 315 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # no directive: refused, as before
 316 | +        today = SPOT.et_day(NOW)                                                  # the one rule, as the pin reads it
 317 | +        self.assertFalse(SPOT.day_taken(day, "A", today, "moments-x-3f481f5a"))
 318 | +        self.assertTrue(SPOT.day_taken(day, "A", today, None))
 319 | +        self.assertTrue(SPOT.day_taken(day + [{"channel_id": "A", "day_et": today, "story_id": "moments-alt"}], "A",
 320 | +                                       today, "moments-x-3f481f5a"))             # one alternative, not two
 321 | +        self.assertFalse(SPOT.day_taken(day, "A", "2026-11-15", None))           # another day
 322 | +        pk = {"segments": [{"channel_id": "A"}],
 323 | +              "spotlight": {"derived_from": {"ruling": 104, "alternative_to": "moments-x-3f481f5a"}}}
 324 | +        self.assertEqual(PLG.spot_place(pk, day, NOW), (None, "moments-x-3f481f5a"))     # at the pin: admitted
 325 | +        self.assertTrue(PLG.spot_place({"segments": [{"channel_id": "A"}]}, day, NOW)[0])  # no directive: refused
 326 | +        self.assertTrue(PLG.spot_place(pk, None, NOW)[0])                                  # unreadable: refused
 327 | +        no_id = [{"channel_id": "A", "day_et": SPOT.et_day(NOW)}]                 # a record without a story id
 328 | +        got, _ = SPOT.pool([a, alt, b], {}, ctx, spotlit=no_id, captions_for=caps)
 329 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # admits no one
 330 | 
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
