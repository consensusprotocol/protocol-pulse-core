# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0332
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 185 s finish=stop usage in 17241 / out 5463 usd~0.134 (upper-bound price)

# Audit: pp-selectid — Ruling 32 (snap outward to whole sentences)

Scope: I verified only what the diff shows. `E.Span`, `E.spoken`, `caption_source`, `vo_fidelity.price_mentions`, `moments.exclusion_verdict`, `context_integrity` and `transcript_truth` are outside the diff; where I rely on their behaviour I say so.

---

## P0

None found.

---

## P1

**P1-1 — `snap_risk` only fires when the miner's risk list is a list; a `None` risk silently becomes `[]`-equivalent, but a non-list (e.g. dict) raises.** `ledger_build.py:72-80` (diff lines 72–80) and call site at diff line 128. `snap_risk` does `out = list(risk or [])`. If `r.get("risk")` is a non-iterable truthy value (a dict, a string), `list(...)` either copies keys or splits into characters, and the `"price_prediction" not in out` check then compares against the wrong thing. Previously `build_inputs` did `list(r.get("risk") or [])` too, so this is pre-existing behaviour, not a regression — but the new function now *adds* to that list, so a string risk like `"price_prediction"` (one flag as a string, not a list) would become `['p','r','i',...]` and the flag would be re-added, producing a duplicate `"price_prediction"` entry. Downstream, `exclusion_verdict` screens "the MOMENT TEXT for every L-u hard risk" — whether a duplicated flag breaks it depends on code outside the diff; I cannot verify. Severity: P1 (low likelihood, unverifiable blast radius), not P0.

**P1-2 — the marker window is asymmetric at the edges and the 1.0 s exclusion is unmeasured, but this is declared, not hidden.** `marker_inside`, diff lines 60–69: the condition is `a + MARKER_EDGE_S < float(s) < b - MARKER_EDGE_S`. A marker at exactly `a + 1.0` or `b - 1.0` is *not* inside (strict inequality), and the test at diff line 518 (`cap(a + 0.5), cap(b - 0.5)`) only exercises 0.5 s, not the 1.0 s boundary itself. The docstring and the change description both declare "a marker within 1.0 s of an edge ... is not a measurement at this stage; L-v 2 decides on the audio", so the design intent is consistent and L-v 2 (outside the diff, stated to measure "exactly one speaker measured inside") is the backstop. However: `MARKER_EDGE_S`'s rationale ("caption token times may be interpolated across a cue") is a comment, not a measurement, and the ruling says the snap must keep "the same single speaker" — a marker 0.9 s inside the span is accepted with no measurement at this stage. This is fail-open *by declaration* only if L-v 2 actually fails such a span; I cannot verify L-v 2's behaviour from this diff. If L-v 2's speaker check is a MONITORING (non-blocking) gate, a snapped span with a mid-span speaker change at 0.9 s would pass with no measurement anywhere — that would violate L-m. Flag as P1: the safety of the 1.0 s window rests entirely on L-v 2 being a hard gate, which the diff does not prove.

**P1-3 — `caps_v` caches by `transcript_sha256` but `caption_source`'s failure returns are not checked.** Diff lines 138–143: `caps_v[sha] = caption_source(r, ctx, store, ledger_store)[0]`. From the module docstring (diff lines 13–15): "Without one, the context is unavailable and L-s fails closed" — so `caption_source` can return `None` (or a record without `.tokens`). `marker_inside` handles `None` via `getattr(cap, "tokens", None) or []` → returns `None` → "no caption record is not a measurement". That is consistent with the declared design (L-v 2 decides). But note the *cache key*: two rows sharing a `transcript_sha256` share one `caption_source` lookup — correct if `caption_source` is a pure function of the record's sha; the diff's docstring says "the caption record the ledger mined the moment from (caption_source(): its segments sha is the row's transcript_sha256)", which supports the key. OK, but: if `caption_source` returns a *different* record than the one the row was mined from (e.g. the store's copy changed between the ledger build and now), the marker times read are not the ones the row's caption times came from. Not verifiable from the diff; noted as a question, not a finding.

**P1-4 — the 20 s limit is measured on the snapped span's word times, but `usable()`'s 20 s limit (L-u, `package.SEG_MAX_S`) is measured... on what?** Diff lines 110–114: `a, b = num(src.tokens[s0].get("start")), num(src.tokens[s1].get("end"))` — the snapped span's own word-clock. The ruling says the snap stays inside "the clip length limits" (plural, "limits" — L-u). If `package.usable()` measures duration differently (e.g. including lead-in/lead-out pads, the 80 ms hook lead, or the L-b fades), a span of exactly 20.00 s here could exceed the limit downstream. The diff's own test (diff line 501) asserts `src.tokens[b]["end"] - src.tokens[a]["start"] > LB.SNAP_MAX_S` — the test measures the same quantity the gate measures, so it cannot catch a divergence between the two definitions. Since `SNAP_MAX_S = 20.0` i

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 20 s finish=stop usage in 17038 / out 720 usd~0.103 (upper-bound price)

**P0: None verifiable from diff.**  
**P1: ledger_build.py:114 (reanchor):** `b - a > SNAP_MAX_S` (20.0) rejects with explicit ruling-32 message; `a`/`b` taken from sentence token `start`/`end` only after `k0`/`k1` sentence lookup succeeds. Matches "at most 20 s per clip (L-u)" and "nothing measured is never a pass (L-m)".  
**P1: ledger_build.py:115-117 (`marker_inside` call):** Only a token whose `start` satisfies `a + 1.0 < s < b - 1.0` and `startswith` one of `SPEAKER_MARKERS` triggers rejection; edge/no-marker/no-cap cases explicitly fall through to L-v2 audio measurement (comment at 62). Exact per ruling.  
**P1: ledger_build.py:78 (`snap_risk`):** `out = list(risk or [])`; only *appends* `"price_prediction"` when `info["snapped_words"]` non-empty *and* `vo_fidelity.price_mentions` sees a future price on the *full* `sp.text`. Cannot remove any flag; satisfies L-u per-video cap and "snap_risk cannot remove a flag".  
**P1: ledger_build.py:144-146 (`build_inputs`):** Non-anchoring rows (`sp is None`) still recorded under `report["not_anchored"]` and skipped; `reanchor` early return at 92-93 when `k0`/`k1` missing. Preserves "a row whose text does not anchor at all stays out".  
**P1: ledger_build.py:118-119:** `sp = E.Span(src, k0, k1)` *after* snap checks; `info["added"]` records spoken before/after only on actual snap. Later tests (test_ledger_build.py:478,552) confirm `sp.text == E.spoken(src.tokens[sp.w0:sp.w1+1])` — verbatim word-record sentences.  
**P2: ledger_build.py:31-50:** SNAP_WORDS/SNAP_GUARD/APOSTROPHES removed; replaced by SNAP_MAX_S/MARKER_EDGE_S logic exactly as described in orchestrator ruling restated at top of diff. No other behavioral change to window path, deduplication-by-time-overlap, or usable() call sites visible.  
**P2: tests/package/test_ledger_build.py:480-529:** Old SNAP_GUARD tests rewritten to assert snaps *now succeed*, added words are recorded, 20 s limit fires, caption-marker-inside vs edge vs absent cases match L-v2 deferral, and `snap_risk` only augments. New tests stay inside the diff; no core pipeline dependence.  
**P2: funnel*.py:** Pure offline read-only analysis tools (recorded Router replay=True, no network, no mutation). Do not alter ledger_build, selection lock, or any gate.

All observable changes stay inside Ruling 32 bounds, preserve verbatim whole-sentence word-record clips, selection lock on recorded text, fail-closed behavior, downstream L-s / exclusion / L-v2 / usable() judgment of the full snapped span, and "never change what a check accepts merely to make a render pass" (the ruling itself is the change). No violation of listed governing laws detectable in the supplied diff.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 89 s finish=stop usage in 18936 / out 3019 usd~0.102 (upper-bound price)

# Audit: pp-selectid-0332 (Ruling 32 — Snap Outward)

## P0 Findings
None. The core logic correctly implements Ruling 32: it snaps outward to whole sentences, enforces the 20s limit, checks for speaker markers, and records added words. It does not violate the "fail closed" or "verbatim whole sentences" laws.

## P1 Findings

**1. `pipeline/ledger_build.py` (approx. line 115 in diff): `marker_inside` uses `startswith` on a tuple of strings.**
*   **Scenario:** The code `str(t.get("word") or "").lstrip().startswith(SPEAKER_MARKERS)` relies on `str.startswith` accepting a tuple. While valid in Python, it is brittle if `SPEAKER_MARKERS` is ever modified to include non-string elements or if the logic is refactored. More importantly, `lstrip()` removes *all* leading whitespace, but `startswith` checks the beginning. If a token is `"  >>"`, `lstrip` makes it `">>"`, which matches. This is correct. However, if a token is `">> something"`, it matches. This is likely intended.
    *   *Correction:* This is actually fine. `str.startswith(tuple)` is standard. No P1 here.

**2. `pipeline/ledger_build.py` (approx. line 110-114 in diff): Edge time measurement for `SNAP_MAX_S`.**
*   **Scenario:** The code calculates `a` and `b` as:
    ```python
    a, b = num(src.tokens[s0].get("start")), num(src.tokens[s1].get("end"))
    ```
    It checks `if a is None or b is None: return None, ...`.
    It then checks `if b - a > SNAP_MAX_S`.
    *   **Risk:** `s0` is the start index of the *first* sentence in the snapped span, and `s1` is the end index of the *last* sentence. `src.tokens[s0]` is the first word of the first sentence. `src.tokens[s1]` is the last word of the last sentence.
    *   **Verification:** This correctly measures the duration of the *entire* snapped span (from the start of the first added/kept word to the end of the last added/kept word). This aligns with "the snapped span runs more than 20 s".
    *   **Potential Issue:** Does `SNAP_MAX_S` (20.0) match `package.SEG_MAX_S`? The comment says `= package.SEG_MAX_S`. If `package.SEG_MAX_S` is defined as 20.0, this is consistent. If it changes, this constant is hardcoded. This is a minor maintainability issue, not a logic bug, unless the law requires dynamic lookup. The prompt says "at most 20 s per clip (L-u, package.SEG_MAX_S)". Hardcoding 20.0 is acceptable if it matches the constant, but referencing the constant would be safer. I will flag this as P2.

**3. `pipeline/ledger_build.py` (approx. line 115 in diff): `marker_inside` logic.**
*   **Scenario:** `marker_inside` checks if a marker is *strictly* inside `[a, b]` with a margin of `MARKER_EDGE_S` (1.0s).
    ```python
    if isinstance(s, (int, float)) and a + MARKER_EDGE_S < float(s) < b - MARKER_EDGE_S:
    ```
    *   **Risk:** If a speaker change happens *exactly* at the boundary of the snapped span (e.g., the last word of the previous sentence is spoken by Speaker A, and the first word of the snapped span is Speaker B), the marker might be at time `a` (start of snapped span). The condition `a + 1.0 < s` would be false if `s == a`. Thus, it would *not* reject the snap.
    *   **Law Check:** The prompt says: "A marker within 1.0 s of an edge... is not a measurement at this stage; L-v 2 decides on the audio."
    *   **Conclusion:** This behavior is **correct** per the prompt's description. The code intentionally ignores markers near the edges, deferring to L-v 2.

**4. `pipeline/ledger_build.py` (approx. line 118 in diff): `info["added"]` calculation.**
    ```python
    info["added"] = {"before": E.spoken(src.tokens[s0:i0]), "after": E.spoken(src.tokens[i1 + 1:s1 + 1])}
    ```
    *   **Scenario:** `i0` and `i1` are the indices of the first and last words of the *anchored* text (the row's text). `s0` and `s1` are the indices of the first and last words of the *snapped* span (whole sentences).
    *   **Verification:**
        *   `before`: Words from `s0` to `i0-1`. These are the words added *before* the anchored text. Correct.
        *   `after`: Words from `i1+1` to `s1`. These are the words added *after* the anchored text. Correct.
    *   **Edge Case:** If `i0 == s0`, `src.tokens[s0:i0]` is empty. `E.spoken([])` should return `""`. The test `test_a_caption_text_snaps_outward...` asserts `info["added"] == {"before": "Bitcoin", "after": ""}`. This implies `E.spoken` handles empty lists correctly.

**5. `pipeline/ledger_build.py` (approx. line 128 in diff): `snap_risk` usage.**
    ```python
    "risk": snap_risk(sp.text, info, r.get("risk")),
    ```
    *   **Scenario:** `sp.text` is the text of the *snapped* span (whole sentences). `info` contains `snapped_words`. `r.get("risk")` is the original risk from the ledger row.
    *   **Logic:** `snap_risk` adds `"price_prediction"` if `info["snapped_words"]` is non-empty AND `sp.text` contains a future price mention.
    *   **Risk:** Does `sp.te

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0332 (ruling 32: snap outward to whole sentences): cycle 1 consensus

Synthesis by the pp-selectid session, 03:33 ET Nov 13, written before cycle 2.

**Run.** C1_STEP.diff covers ledger_build.py, test_ledger_build.py, funnel.py and funnel_pre_edge.py. No P0.
Verdicts:
- grok: no P0, "SHIP: yes";
- qwen: "yes with conditions", P2 only;
- glm: "yes with conditions".

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | SNAP_MAX_S = 20.0 is a copy of package.SEG_MAX_S and can drift (qwen P2-1, glm P1-4 and its condition 1) | IMPLEMENTED: test_the_snap_limit_is_the_packagers_clip_limit asserts LB.SNAP_MAX_S == PK.SEG_MAX_S. ledger_build does not import package; it is the lighter module, and package imports the verdict stack. Both limits are measured the same way: a span's first word start to last word end on its word record (the moment's duration_s, which usable() compares with SEG_MAX_S). |
| K2 | The funnel tools hard-code their paths (qwen P2-2 / P2-3, glm P2-3) | IMPLEMENTED: the ledger path comes from ledger_build.INGEST_ROOT (env PP_INGEST_ROOT), and the WAV dir is proof_ly.SCRATCH/lv2, the build's own default --work-dir. |
| K3 | The 1.0 s marker margin leaves edge-adjacent speaker changes unmeasured at the snap. Is L-v 2's single-speaker rule a REQUIRED, blocking gate (glm P1-2, its condition 2)? | VERIFIED, outside the diff. transcript_truth.verify_segment: `ok = cmp_["ok"] and turns["turn_change_inside"] is False`, so an unmeasured speaker (None) is not ok. package.build: a moment is cleared only when cut_ok (t["ok"] and CUTTABLE). The pin's "second_pass" row needs every segment's ok, and "second_pass" is in package_pin.REQUIRED_GATES. No snapped span reaches a pin without one speaker measured. |
| K4 | snap_risk mangles a non-list risk through list() (glm P1-1, condition 3) | IMPLEMENTED: a risk that is not a list raises TypeError, which make() counts as malformed. Tested. (It was pre-existing behaviour of make(), `list(r.get("risk") or [])`.) |

## Answered or kept

- **SNAP_GUARD's retirement (the audit question):** all three reviewers find no risk class that no downstream gate judges.
  - glm: the moment text is the word record's snapped sentences, so every text-reading gate reads the added words.
  - The exclusion verdict screens every L-u hard risk on the moment text.
  - About-Bitcoin can only gain, since the row's text is a substring.
  - The miner's scores stay the row's, which is ranking only.
- **glm P1-3 (the caption lookup's failure):** answered. caption_source returns (None, why). marker_inside treats None as no measurement, and L-v 2 decides (K3).
- **glm P1-4b (the anchor-time measurement):** unchanged code (offset_s), covered by the existing test_the_hit_is_measured_against_the_rows_own_caption_times.
- **glm P2-1 (">>>" also counts as a marker):** KEPT. It fails closed: a run of three is still a speaker marker in caption text.
- **glm P2-2 (lazy vo_fidelity import):** KEPT. vo_fi

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0332/C2_STEP.diff (569 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | index 1b97ff09..374cb227 100644
   3 | --- a/pipeline/ledger_build.py
   4 | +++ b/pipeline/ledger_build.py
   5 | @@ -17,15 +17,16 @@ FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call h
   6 |    - word_pass_index() reads that list. window_source() checks every claim before use: the file's sha256 is the row's
   7 |      record_sha256, the segments sha, words_sha256, the words spell the segments, the YouTube clock, nothing still
   8 |      unpunctuated, and the ledger row's span inside the window.
   9 | -  - One window per video: the best-ranked row whose window record passes every check (a row whose own record fails
  10 | -    is passed over with why). The video's other rows re-anchor in it, or are counted out.
  11 | +  - One window per MOMENT (audit 0208): each row re-anchors in its own window record when that record passes every
  12 | +    check (a row whose record fails is counted with why); the same speech in two windows is one moment.
  13 |    - L-s context comes from the caption record the ledger mined the moment from (caption_source(): its segments sha
  14 |      is the row's transcript_sha256), cut by time (context_integrity.caption_parts). Without one, the context is
  15 |      unavailable and L-s fails closed.
  16 |  - RE-ANCHOR: sentence_law.anchor, the sentence law's own text locator, finds the row's TEXT in the word record. The
  17 | -  row's caption-clock times only narrow the search. The span then snaps to that record's WHOLE sentences when at most
  18 | -  SNAP_WORDS words lie outside the anchored text at either edge; otherwise the row is dropped, and why is recorded.
  19 | -  The moment's text becomes the word record's own words, verbatim, the words the render locks on.
  20 | +  row's caption-clock times only narrow the search. The span then snaps OUTWARD to that record's WHOLE sentences
  21 | +  (ruling 32), when the snapped span is at most SNAP_MAX_S long and holds no caption speaker marker. Otherwise the row
  22 | +  is dropped, and why is recorded; a row whose text does not anchor at all stays out. The moment's text becomes the
  23 | +  word record's own words, verbatim, the words the render locks on.
  24 |  - RECORD: the miner's own moments.judge() and moments.record(): eligibility on word timing (on_screen_ok). The ledger
  25 |    row's scores, risks, topics, reason and mining provenance are kept (mined.ledger_moment_id).
  26 |  -> build_inputs(...) = (moments, sources, report).
  27 | @@ -41,15 +42,17 @@ import select_by_id as S
  28 |  import sentence_law as SL
  29 |  import transcript_store as ts
  30 |  
  31 | -SNAP_WORDS = 3            # words of a word-record sentence the anchored text may leave out at either edge
  32 | -SNAP_GUARD = __import__("re").compile(r"^(not|no|never|none|nobody|nothing|neither|nor|cannot|can't|won't|don't|"
  33 | -                                      r"hardly|scarcely|barely|rarely|seldom|"
  34 | -                                      r"doesn't|didn't|isn't|aren't|wasn't|weren't|shouldn't|wouldn't|couldn't|"
  35 | -                                      r"\w+n't)$|\d", __import__("re").I)
  36 | -                          # a word the snap would ADD may not be a negation or carry a digit: it could flip or add a
  37 | -                          # claim the ledger's scores and risks never saw (audit 2315 C1: grok P1, glm P1-1; the
  38 | -                          # near-negations "hardly" ... "seldom": qwen C3)
  39 | -APOSTROPHES = {"\u2019": "'", "\u2018": "'", "\u02bc": "'"}   # a typographic apostrophe is read as ' by the guard
  40 | +SNAP_MAX_S = 20.0         # RULING 32 (orchestrator 02:45 ET Nov 13): a row whose anchored text is not whole sentences
  41 | +                          # is SNAPPED OUTWARD to the word record's whole sentences, instead of dropped, when the
  42 | +                          # snapped span stays inside the clip length limit (= package.SEG_MAX_S, L-u) and shows no
  43 | +                          # speaker change. The added words are the speaker's own, so nothing is changed by omission;
  44 | +                          # the snapped span is judged as usual: step A (L-s), the exclusion verdict (every L-u risk),
  45 | +                          # L-v 2 (every number and negation both ways, exactly one speaker measured) and usable() (time
  46 | +                          # words). It replaces SNAP_WORDS = 3 and SNAP_GUARD (audit 2315 C1), whose concern was words
  47 | +                          # the ledger never judged: those gates judge them. Its price predictions: snap_risk().
  48 | +SPEAKER_MARKERS = (">>", "&gt;&gt;")   # a caption speaker change (pp-ingest contract.SPEAKER_MARKERS)
  49 | +MARKER_EDGE_S = 1.0       # caption token times may be interpolated across a cue: a marker this close to a snapped edge
  50 | +                          # is not placed inside it here, and L-v 2 measures the speaker on the audio
  51 |  SEARCH_PAD_S = 30.0       # the row's caption times narrow the anchor's search to [start - pad, end + pad]. Captions
  52 |                            # and word records share the full-video clock, and a caption cue starts or ends a few
  53 |                            # seconds off the words; the window only keeps a phrase said again elsewhere in the video
  54 | @@ -343,8 +346,35 @@ def word_source(row, ctx, store=STORE):
  55 |      return None, None, passed_over
  56 |  
  57 |  
  58 | -def reanchor(row, src):
  59 | -    """The row's TEXT located in the word record and snapped to its whole sentences -> (E.Span, info) or (None, why)."""
  60 | +def marker_inside(cap, a, b):
  61 | +    """The time of a caption speaker marker ('>>', stored '&gt;&gt;') more than MARKER_EDGE_S inside [a, b] (seconds on
  62 | +    the media clock): a MEASURED speaker change. None otherwise: no marker, or no caption record, is not a measurement
  63 | +    (L-m), and L-v 2 measures the speaker on the audio before the moment can be used."""
  64 | +    for t in (getattr(cap, "tokens", None) or []):
  65 | +        if str(t.get("word") or "").lstrip().startswith(SPEAKER_MARKERS):
  66 | +            s = t.get("start")
  67 | +            if isinstance(s, (int, float)) and a + MARKER_EDGE_S < float(s) < b - MARKER_EDGE_S:
  68 | +                return float(s)
  69 | +    return None
  70 | +
  71 | +
  72 | +def snap_risk(text, info, risk):
  73 | +    """Ruling 32: the miner flagged price predictions on the ROW's text, so a SNAPPED moment's are counted on its
  74 | +    snapped text (a future price per vo_fidelity.price_mentions), for the per-video cap (L-u). -> a new risk list."""
  75 | +    import vo_fidelity as VF
  76 | +    if risk is not None and not isinstance(risk, list):        # never mangled by list() (audit 0332 C1, glm P1-1);
  77 | +        raise TypeError(f"the row's risk is a {type(risk).__name__}, not a list")   # make() counts it as malformed
  78 | +    out = list(risk or [])
  79 | +    if any((info or {}).get("snapped_words") or []) and "price_prediction" not in out and \
  80 | +            any(kind == "future" for _, kind in VF.price_mentions(text or "")):
  81 | +        out.append("price_prediction")
  82 | +    return out
  83 | +
  84 | +
  85 | +def reanchor(row, src, cap=None):
  86 | +    """The row's TEXT located in the word record and SNAPPED OUTWARD to its whole sentences (ruling 32) -> (E.Span,
  87 | +    info) or (None, why). cap: the caption record the row was mined from, read for its speaker markers (default: a
  88 | +    window Source's context_source)."""
  89 |      def num(x):
  90 |          try:
  91 |              return float(x)
  92 | @@ -363,18 +393,21 @@ def reanchor(row, src):
  93 |      k1 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i1 <= b), None)
  94 |      if k0 is None or k1 is None:
  95 |          return None, "the anchored words fall outside the record's sentences"
  96 | -    left, right = i0 - src.sentences[k0][0], src.sentences[k1][1] - i1
  97 | -    if left > SNAP_WORDS or right > SNAP_WORDS:
  98 | -        return None, (f"the anchored text is not whole sentences of the word record ({left} word(s) before it and "
  99 | -                      f"{right} after it inside its edge sentences; at most {SNAP_WORDS})")
 100 | -    added = ["".join(APOSTROPHES.get(c, c) for c in t["word"]).strip(".,!?;:\"'()\u201c\u201d\u2014\u2026")
 101 | -             for t in list(src.tokens[src.sentences[k0][0]:i0]) + list(src.tokens[i1 + 1:src.sentences[k1][1] + 1])]
 102 | -    # a typographic apostrophe reads as ' here (glm C2 N-3; none of the store's 66 word records holds one today)
 103 | -    risky = [w for w in added if SNAP_GUARD.search(w)]
 104 | -    if risky:
 105 | -        return None, f"snapping to whole sentences would add {risky}: a negation or a number the ledger never judged"
 106 | -    sp = E.Span(src, k0, k1)
 107 | +    (s0, _), (_, s1) = src.sentences[k0], src.sentences[k1]
 108 | +    left, right = i0 - s0, s1 - i1
 109 |      info = {"anchor_ratio": round(ratio, 3), "snapped_words": [left, right], "sentences": [k0, k1]}
 110 | +    if left or right:
 111 | +        snap = f"snapped outward to whole sentences ({left} word(s) before the anchored text, {right} after)"
 112 | +        a, b = num(src.tokens[s0].get("start")), num(src.tokens[s1].get("end"))
 113 | +        if a is None or b is None:
 114 | +            return None, f"{snap}, its length is not measured (a word time is missing)"
 115 | +        if b - a > SNAP_MAX_S:
 116 | +            return None, f"{snap} it runs {b - a:.2f} s > {SNAP_MAX_S:.0f} s (ruling 32: the clip length limit)"
 117 | +        t = marker_inside(cap if cap is not None else getattr(src, "context_source", None), a, b)
 118 | +        if t is not None:
 119 | +            return None, f"{snap} it holds a caption speaker marker at {t:.2f} s: a measured speaker change (ruling 32)"
 120 | +        info["added"] = {"before": E.spoken(src.tokens[s0:i0]), "after": E.spoken(src.tokens[i1 + 1:s1 + 1])}
 121 | +    sp = E.Span(src, k0, k1)
 122 |      a, b = num(src.tokens[i0].get("start")), num(src.tokens[i1].get("end"))
 123 |      # the hit against the row's own caption times: a phrase said twice inside the window shows here (glm C3 P1-3);
 124 |      # when it cannot be measured, it says so (glm C4 P2-8)
 125 | @@ -413,7 +446,7 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
 126 |      def make(i, r, sp, info, src):
 127 |          try:
 128 |              m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
 129 | -                 "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
 130 | +                 "risk": snap_risk(sp.text, info, r.get("risk")), "topics": list(r.get("topics") or []),
 131 |                   "reason": r.get("reason") or ""}
 132 |              mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 133 |                           ledger_text=r.get("text"))
 134 | @@ -445,8 +478,12 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
 135 |              if passed_over:
 136 |                  report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
 137 |              report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
 138 | -            for i, r in irs:
 139 | -                sp, info = reanchor(r, src)
 140 | +            caps_v = {}                              # the caption record a row was mined from, once per sha: its
 141 | +            for i, r in irs:                         # speaker markers for a snapped span (ruling 32)
 142 | +                sha = r.get("transcript_sha256")
 143 | +                if sha not in caps_v:
 144 | +                    caps_v[sha] = caption_source(r, ctx, store, ledger_store)[0]
 145 | +                sp, info = reanchor(r, src, cap=caps_v[sha])
 146 |                  if sp is None:
 147 |                      report["not_anchored"][r["moment_id"]] = info
 148 |                      continue
 149 | diff --git a/tests/package/funnel.py b/tests/package/funnel.py
 150 | new file mode 100644
 151 | index 00000000..45ccfe8c
 152 | --- /dev/null
 153 | +++ b/tests/package/funnel.py
 154 | @@ -0,0 +1,250 @@
 155 | +#!/usr/bin/env python3
 156 | +"""The FUNNEL TABLE of one ledger build record (orchestrator 02:45 item 1): per stage, the moments lost per exact
 157 | +reason, with one example moment text per reason. No vendor call: it reads the record (inputs.json, package.json,
 158 | +step_a.json, package.log), the ledger for row texts, and recomputes the CUTTABLE edges from the RECORDED scribe replies
 159 | +(Router replay=True: a reply not recorded raises, it is never fetched).
 160 | +usage: tests/package/funnel.py <build dir>"""
 161 | +import collections
 162 | +import json
 163 | +import os
 164 | +import re
 165 | +import sys
 166 | +
 167 | +D = sys.argv[1]
 168 | +REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 169 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 170 | +sys.path.insert(0, os.path.join(REPO, "tests", "package"))
 171 | +import ledger_build as LB  # noqa: E402  (the build's own roots: PP_INGEST_ROOT, audit 0332 C1 qwen P2-2)
 172 | +import proof_ly as PL  # noqa: E402
 173 | +LEDGER = os.path.join(LB.INGEST_ROOT, "data", "editorial", "moments", "moment_ledger.jsonl")
 174 | +REPLIES = os.path.join(REPO, "tests", "package", "fixtures", "replies")
 175 | +LV2 = os.path.join(PL.SCRATCH, "lv2")                 # the build's default L-v 2 work dir (proof_ledger --work-dir)
 176 | +inp = json.load(open(os.path.join(D, "inputs.json")))
 177 | +pk = json.load(open(os.path.join(D, "package.json")))
 178 | +sa = json.load(open(os.path.join(D, "step_a.json"))) if os.path.exists(os.path.join(D, "step_a.json")) else {}
 179 | +rep, moments = inp["inputs"], inp["moments"]
 180 | +by = {m["moment_id"]: m for m in moments}
 181 | +texts = {}
 182 | +for line in open(LEDGER):
 183 | +    try:
 184 | +        r = json.loads(line)
 185 | +    except ValueError:
 186 | +        continue
 187 | +    if isinstance(r, dict) and r.get("moment_id"):
 188 | +        texts[r["moment_id"]] = r.get("text") or ""
 189 | +
 190 | +
 191 | +def q(t, n=140):
 192 | +    t = " ".join(str(t or "").split()).replace("|", "/")
 193 | +    return t if len(t) <= n else t[:n - 1] + "…"
 194 | +
 195 | +
 196 | +def tx(mid):
 197 | +    return by.get(mid, {}).get("text") or texts.get(mid) or ""
 198 | +
 199 | +
 200 | +def emit(title, rows, head=("lost", "exact reason", "one example (moment text)")):
 201 | +    print(f"\n**{title}**\n")
 202 | +    print("| " + " | ".join(head) + " |")
 203 | +    print("|" + "---|" * len(head))
 204 | +    for r in rows:
 205 | +        print("| " + " | ".join(str(c) for c in r) + " |")
 206 | +
 207 | +
 208 | +def grouped(items):
 209 | +    """items: [(reason, mid)] -> rows [count, reason, example] by count, the example the first moment of the reason."""
 210 | +    g = collections.OrderedDict()
 211 | +    for why, mid in items:
 212 | +        g.setdefault(why, []).append(mid)
 213 | +    return [[len(ms), why, f'"{q(tx(ms[0]))}"' if ms[0] else "n/a"] for why, ms in
 214 | +            sorted(g.items(), key=lambda kv: -len(kv[1]))]
 215 | +
 216 | +
 217 | +def flags_rows(per_moment, describe, example_note=None):
 218 | +    """per_moment: {mid: [flag, ...]} -> rows [moments carrying it, of them it ALONE keeps out, flag, example]."""
 219 | +    carry, alone = collections.Counter(), collections.Counter()
 220 | +    ex = {}
 221 | +    for mid, fl in per_moment.items():
 222 | +        for f in fl:
 223 | +            carry[f] += 1
 224 | +            ex.setdefault(f, mid)
 225 | +            if len(set(fl)) == 1:
 226 | +                alone[f] += 1
 227 | +                ex[f] = ex[f] if len(set(per_moment[ex[f]])) == 1 else mid      # prefer an example it alone rejects
 228 | +    rows = []
 229 | +    for f, n in carry.most_common():
 230 | +        note = (example_note(ex[f], f) if example_note else "")
 231 | +        rows.append([n, alone[f], f"`{f}`: {describe(f)}", f'"{q(tx(ex[f]))}"' + (f" ({note})" if note else "")])
 232 | +    return rows
 233 | +
 234 | +
 235 | +print(f"Build `{os.path.basename(D)}`: code {pk.get('code')}, render clock {pk.get('now')}.")
 236 | +ar = inp.get("adapter_report") or {}
 237 | +print(f"Adapter (pp-ingest, before the ledger rows): excluded {json.dumps(ar.get('excluded'))}.")
 238 | +
 239 | +# ---- stage 0: ledger rows -> moments
 240 | +s0 = []
 241 | +for why, n in (rep.get("no_word_record_why") or {}).items():
 242 | +    s0 += [(f"SUPPLY: no word record yet ({why})", None)] * int(n)
 243 | +s0 += [("SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row)", None)] * \
 244 | +    int(rep.get("window_waiting") or 0)
 245 | +s0 += [("its window record failed a check", None)] * int(rep.get("window_failed") or 0)
 246 | +na = rep.get("not_anchored") or {}
 247 | +ws_rows = {}
 248 | +for mid, why in na.items():
 249 | +    m = re.search(r"\((\d+) word\(s\) before (?:it|the anchored text),? and (\d+) after", why)
 250 | +    if m:
 251 | +        ws_rows[mid] = (int(m.group(1)), int(m.group(2)), why)
 252 | +    s0.append(("does not re-anchor: " + re.sub(r"\d+(\.\d+)?", "N", re.sub(r"searched [\d.]+-[\d.]+ s",
 253 | +                                                                       "searched around the row's time", why)), mid))
 254 | +s0 += [("duplicate: the same speech as a kept moment (time overlap in the same video)", mid)
 255 | +       for mid in (rep.get("duplicates_of") or {})]
 256 | +s0 += [(f"malformed: {why}", mid) for mid, why in (rep.get("malformed") or {}).items()]
 257 | +s0 += [("its video's rows name two channels", None) for _ in (rep.get("channel_conflict") or {})]
 258 | +emit(f"Stage 0: {rep.get('rows')} ledger rows -> {len(moments)} moments ({len(s0)} not moments)", grouped(s0))
 259 | +if ws_rows:
 260 | +    print("\nThe rows that are not whole sentences of the word record, exactly (words of the edge sentences outside "
 261 | +          "the anchored text, before / after, and why each stays out):")
 262 | +    for mid, (l, r, why) in sorted(ws_rows.items(), key=lambda kv: kv[1][0] + kv[1][1]):
 263 | +        print(f"- {l} before / {r} after: \"{q(texts.get(mid), 90)}\" (why: {q(why, 140)})")
 264 | +
 265 | +# ---- stage 1: moments -> usable
 266 | +DESC = {"opener": "opens on a pronoun or reply word that needs what came before (stand_alone.opener)",
 267 | +        "no_bitcoin": "does not name Bitcoin: regex `\\b(bitcoins?|btcs?)\\b` (T11, the old story selector's subject "
 268 | +                      "screen; 'Bitcoiners', 'sats', 'Satoshi' do not count)",
 269 | +        "too_many_sentences": "more than 3 sentences (T9, the old selector's MAX_WINDOW_SENTENCES = 3)",
 270 | +        "layout_ineligible": "the channel has a burned-in chyron (registry has_chyron, DEC-12d)",
 271 | +        "not_statement": "ends on a question",
 272 | +        "hook_lead": "hook only: transcript gap before the first word < 80 ms",
 273 | +        "start_case": "starts lower-case", "fragment": "not a sentence start / end", "too_short": "< 5 words",
 274 | +        "no_content": "interjections only", "unpunctuated": "boundary in an unpunctuated stretch",
 275 | +        "duration": "no word timestamps", "not_sentence_ready": "no sentence-ready word record"}
 276 | +un = pk.get("unusable") or {}
 277 | +clipflags, other = {}, []
 278 | +for mid, why in un.items():
 279 | +    m = re.match(r"not eligible on screen: (.*)$", why)
 280 | +    if m:
 281 | +        roles = dict(p.split(": ", 1) for p in m.group(1).split("; ") if ": " in p)
 282 | +        clipflags[mid] = [f.strip() for f in roles.get("clip", "").split(",") if f.strip()]
 283 | +    else:
 284 | +        other.append((re.sub(r"^[\d.]+ s:", "N s:", why), mid))
 285 | +print(f"\n**Stage 1: {len(moments)} moments -> {pk.get('usable')} usable** (package.usable; {len(un)} lost)")
 286 | +print("\nA moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the "
 287 | +      "binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).")
 288 | +emit(f"Stage 1a: not eligible on screen ({len(clipflags)} moments)",
 289 | +     flags_rows(clipflags, lambda f: DESC.get(f, f)), head=("moments", "alone", "exact reason (clip role)",
 290 | +                                                             "one example"))
 291 | +if other:
 292 | +    emit(f"Stage 1b: the other usable() reasons ({len(other)} moments)", grouped(other))
 293 | +
 294 | +# ---- stage 2: usable -> cleared step A
 295 | +pre = pk.get("prescreen") or {}
 296 | +failed = pre.get("failed") or {}
 297 | +sa_by = {}
 298 | +for k, v in sa.items():
 299 | +    if isinstance(v, dict):
 300 | +        sa_by[k.split(":")[0]] = v
 301 | +
 302 | +
 303 | +def a_note(mid, rule):
 304 | +    a = next((v for lb, v in sa_by.items() if mid.startswith(lb)), None)
 305 | +    if not a:
 306 | +        return ""
 307 | +    if rule == "REFERENT_OUTSIDE":
 308 | +        rs = [r for r in a.get("referents") or [] if isinstance(r, dict) and r.get("inside") is not True]
 309 | +        return "; ".join(f"'{r.get('word')}' -> '{q(r.get('refers_to'), 50)}', changes the assertion: "
 310 | +                         f"{r.get('changes_assertion')}" for r in rs[:2])
 311 | +    if rule == "NOT_OWN_SINCERE":
 312 | +        return f"view: {a.get('view')}"
 313 | +    if rule == "STALE_TIME":
 314 | +        return f"time_ok: {a.get('time_ok')}"
 315 | +    if rule == "CONDITION_OUTSIDE":
 316 | +        return "; ".join(f"'{q((c or {}).get('text'), 60)}'" for c in a.get("conditions") or [])
 317 | +    if rule == "SPEAKER_CHANGE":
 318 | +        return f"speaker_changes_inside: {a.get('speaker_changes_inside')}"
 319 | +    if rule == "UNCERTAIN":
 320 | +        return f"certainty: {a.get('certainty')}"
 321 | +    if rule == "RETRACTION":
 322 | +        return f"retraction: {q(a.get('retraction'), 60)}"
 323 | +    return ""
 324 | +
 325 | +
 326 | +SDESC = {"REFERENT_OUTSIDE": "a word refers to something outside the clip AND resolving it could change the assertion "
 327 | +                             "(anything but an explicit 'no' fails, L-m)",
 328 | +         "NOT_OWN_SINCERE": "not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...)",
 329 | +         "STALE_TIME": "time words stale on the show date (L-v 3)", "CONDITION_OUTSIDE": "a condition outside the clip",
 330 | +         "SPEAKER_CHANGE": "a speaker change inside", "RETRACTION": "retracted or corrected later",
 331 | +         "UNCERTAIN": "the judge is not certain", "CONTEXT_UNAVAILABLE": "no source context to judge"}
 332 | +print(f"\n**Stage 2: {pk.get('usable')} usable -> {pre.get('cleared')} cleared step A** (L-s on the moment's own "
 333 | +      f"context; {pre.get('screened')} screened, {len(failed)} failed)")
 334 | +emit(f"Stage 2: step A rules ({len(failed)} moments)",
 335 | +     flags_rows(failed, lambda f: SDESC.get(f, f), a_note), head=("moments", "alone", "exact reason", "one example"))
 336 | +
 337 | +# ---- stage 3: cleared -> L-v 2 + CUTTABLE (edges recomputed from the recorded scribe replies, offline)
 338 | +sp = pre.get("second_pass") or {}
 339 | +lost3 = [mid for mid, v in sp.items() if v != "PASS"]
 340 | +detail = {}
 341 | +try:
 342 | +    import providers as P
 343 | +    import transcript_truth as TT
 344 | +    rt = P.Router(record_dir=REPLIES, replay=True)
 345 | +    for mid in lost3:
 346 | +        m = by[mid]
 347 | +        try:
 348 | +            t = TT.verify_segment(rt, m["video_id"], float(m["start"]), float(m["end"]), m["text"], LV2)
 349 | +            e = t.get("edges") or {}
 350 | +            if not t.get("ok"):
 351 | +                bits = []
 352 | +                if not t.get("transcript_ok"):
 353 | +                    bits.append(f"the two recognisers disagree on {json.dumps(t.get('disagree'))[:160]}")
 354 | +                if t["speakers"].get("turn_change_inside") is not False:
 355 | +                    bits.append(f"speakers measured inside: {t['speakers'].get('labels')}")
 356 | +                detail[mid] = ("L-v 2 FAIL", "; ".join(bits))
 357 | +            else:
 358 | +                bad = [f"{k.upper()}: {e[k].get('why')}" for k in ("in", "out") if not (e.get(k) or {}).get("ok")]
 359 | +                detail[mid] = ("not CUTTABLE: " + " + ".join(b.split(":")[0] for b in bad) + " edge", "; ".join(bad))
 360 | +        except Exception as ex:                              # noqa: BLE001
 361 | +            detail[mid] = (sp[mid], f"(edge detail not recomputed offline: {type(ex).__name__}: {str(ex)[:120]})")
 362 | +except Exception as ex:                                      # noqa: BLE001
 363 | +    print(f"(stage-3 detail not recomputed: {type(ex).__name__}: {ex})")
 364 | +rows3 = []
 365 | +g3 = collections.OrderedDict()
 366 | +for mid in lost3:
 367 | +    k = detail.get(mid, (sp[mid], ""))[0]
 368 | +    g3.setdefault(k, []).append(mid)
 369 | +for k, ms in sorted(g3.items(), key=lambda kv: -len(kv[1])):
 370 | +    rows3.append([len(ms), k, f'"{q(tx(ms[0]))}" ({q(detail.get(ms[0], ("", ""))[1], 200)})'])
 371 | +emit(f"Stage 3: {pre.get('cleared')} cleared -> {pre.get('cuttable')} pass L-v 2 + CUTTABLE ({len(lost3)} lost)", rows3)
 372 | +if len(lost3) > 1:
 373 | +    print("\nEvery stage-3 loss, exactly:")
 374 | +    for mid in lost3:
 375 | +        k, d = detail.get(mid, (sp[mid], ""))
 376 | +        print(f"- {by[mid].get('channel_name')}: {k}: {q(d, 260)}")
 377 | +
 378 | +# ---- stage 4: cuttable -> can open
 379 | +ho = pre.get("hook_onset") or {}
 380 | +lost4 = [(v, mid) for mid, v in ho.items() if v != "PASS"]
 381 | +emit(f"Stage 4: {pre.get('cuttable')} cuttable -> {sum(v == 'PASS' for v in ho.values())} can open a medley (G17a; "
 382 | +     f"the others stay in play as non-hook clips)", grouped(lost4) or [[0, "-", "-"]])
 383 | +
 384 | +# ---- stage 5: -> angle -> line-ups
 385 | +print(f"\n**Stage 5: the angle step and the line-ups.** why_none: {pk.get('why_none')!r}; angles: "
 386 | +      f"{len(pk.get('angles') or [])} from {pk.get('angle_backend')}")
 387 | +cl = [mid for mid, v in sp.items() if v == "PASS"]
 388 | +print("\nThe moments offered to the angle step:")
 389 | +for mid in cl:
 390 | +    m = by.get(mid, {})
 391 | +    print(f"- {m.get('channel_name')} ({m.get('video_id')}), {m.get('duration_s')} s, can open: "
 392 | +          f"{ho.get(mid) == 'PASS'}: \"{q(m.get('text'), 150)}\"")
 393 | +print(f"\nTogether {round(sum(float(by[m]['duration_s']) for m in cl if m in by), 2)} s from "
 394 | +      f"{len({by[m]['channel_id'] for m in cl if m in by})} channels.")
 395 | +for a in pk.get("angles") or []:
 396 | +    print(f"- angle: \"{q(a.get('angle'), 200)}\" moments {len(a.get('moments') or [])}")
 397 | +log = open(os.path.join(D, "package.log")).read().splitlines()
 398 | +k = next((i for i, l in enumerate(log) if re.search(r"angles? from|no readable angles|readable angle", l)), None)
 399 | +if k is not None:
 400 | +    print("\nThe build's own log from the angle step on:")
 401 | +    print("```")
 402 | +    for l in log[k:]:
 403 | +        print(l.rstrip()[:240])
 404 | +    print("```")
 405 | diff --git a/tests/package/funnel_pre_edge.py b/tests/package/funnel_pre_edge.py
 406 | new file mode 100644
 407 | index 00000000..bf4e5806
 408 | --- /dev/null
 409 | +++ b/tests/package/funnel_pre_edge.py
 410 | @@ -0,0 +1,37 @@
 411 | +"""For each stage-3 'no word before it' loss in a build: what is in the audio before the clip? Offline (recorded scribe
 412 | +replies, replay=True) + the cached L-v 2 WAV, CPU only. usage: tests/package/funnel_pre_edge.py <build dir>"""
 413 | +import json, os, sys, wave
 414 | +import numpy as np
 415 | +REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 416 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 417 | +import providers as P, transcript_truth as TT
 418 | +D = sys.argv[1]
 419 | +sys.path.insert(0, os.path.join(REPO, "tests", "package"))
 420 | +import proof_ly as PL  # noqa: E402
 421 | +LV2 = os.path.join(PL.SCRATCH, "lv2")                 # the build's default L-v 2 work dir (proof_ledger --work-dir)
 422 | +inp = json.load(open(os.path.join(D, "inputs.json"))); pk = json.load(open(os.path.join(D, "package.json")))
 423 | +by = {m["moment_id"]: m for m in inp["moments"]}
 424 | +rt = P.Router(record_dir=os.path.join(REPO, "tests/package/fixtures/replies"), replay=True)
 425 | +for mid, v in (pk["prescreen"].get("second_pass") or {}).items():
 426 | +    if v == "PASS":
 427 | +        continue
 428 | +    m = by[mid]; s, e = float(m["start"]), float(m["end"])
 429 | +    wav, a = TT.audio_window(m["video_id"], s, e, LV2)
 430 | +    sec, _ = TT.second_pass(rt, wav)
 431 | +    edg = TT.edges(sec, a, s, e, m["text"])
 432 | +    w = wave.open(wav); n = w.getnframes(); sr = w.getframerate()
 433 | +    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
 434 | +    off = s - a
 435 | +    fr = int(0.05 * sr)
 436 | +    def db(seg):
 437 | +        r = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
 438 | +        return -120.0 if r <= 0 else 20 * np.log10(r)
 439 | +    pre = [round(db(x[i:i + fr]), 1) for i in range(0, int(off * sr), fr)]
 440 | +    words = [(round(float(w_["start"]), 2), w_.get("text"), w_.get("speaker")) for w_ in sec.get("words") or []
 441 | +             if w_.get("start") is not None][:6]
 442 | +    print(f"\n{m['channel_name']} {m['video_id']} clip {s:.2f}-{e:.2f}, window from {a:.2f} (pad {off:.2f} s); "
 443 | +          f"IN: {edg['in'].get('why')} | OUT: {edg['out'].get('why')}")
 444 | +    print("  recogniser's first words (s into the window, text, speaker):", words)
 445 | +    print("  pre-clip RMS dBFS per 50 ms:", pre)
 446 | +    print("  clip's first 0.5 s RMS dBFS per 50 ms:", [round(db(x[i:i + fr]), 1) for i in range(int(off * sr), int((off + 0.5) * sr), fr)])
 447 | +    print("  primary (store) text starts:", repr(m["text"][:70]))
 448 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 449 | index b99d2ddc..c18f81e6 100644
 450 | --- a/tests/package/test_ledger_build.py
 451 | +++ b/tests/package/test_ledger_build.py
 452 | @@ -46,31 +46,70 @@ class TestReanchor(unittest.TestCase):
 453 |          self.assertEqual(info["snapped_words"], [0, 0])
 454 |          self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words
 455 |  
 456 | -    def test_a_caption_text_snaps_to_the_records_whole_sentences_within_the_limit(self):
 457 | -        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short: snaps
 458 | +    def test_a_caption_text_snaps_outward_to_the_records_whole_sentences(self):
 459 | +        """Ruling 32 (02:45 ET Nov 13): any number of the speaker's own words is added, within 20 s, no speaker
 460 | +        change; the added words are recorded."""
 461 | +        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short
 462 |          self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((0, 0), [1, 0]))
 463 | -        sp, info = LB.reanchor(row("whole design and it works every day."), self.src)  # exactly 3 words: snaps
 464 | -        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [3, 0]))
 465 | -        sp, why = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused
 466 | -        self.assertIsNone(sp)
 467 | -        self.assertIn("not whole sentences", why)
 468 | -
 469 | -    def test_a_snap_never_adds_a_negation_or_a_number(self):
 470 | -        """Audit 2315 C1 (grok P1, glm P1-1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin' flips the
 471 | -        claim the ledger scored; '... started as a quiet experiment' snapped to 'In 2009 ...' adds a number."""
 472 | -        for text, word in (("can stop Bitcoin from settling a payment.", "Nobody"),
 473 | -                           ("Bitcoin started as a quiet experiment.", "2009")):
 474 | -            sp, why = LB.reanchor(row(text), self.src)
 475 | -            self.assertIsNone(sp, text)
 476 | -            self.assertIn(word, why)
 477 | -
 478 | -    def test_a_snap_never_adds_a_near_negation(self):
 479 | -        """qwen C3: 'Hardly anyone can stop Bitcoin' flips 'anyone can stop Bitcoin'."""
 480 | -        for word in ("Hardly", "Scarcely", "Barely", "Rarely", "Seldom"):
 481 | +        self.assertEqual(info["added"], {"before": "Bitcoin", "after": ""})
 482 | +        sp, info = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused before 32
 483 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [4, 0]))
 484 | +        self.assertEqual(info["added"]["before"], "That is the whole")
 485 | +        self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words
 486 | +
 487 | +    def test_a_snap_adds_the_speakers_own_negation_or_number_and_records_it(self):
 488 | +        """Ruling 32 retires SNAP_GUARD (audit 2315 C1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin'
 489 | +        restores what the speaker said. Step A, the exclusion verdict and L-v 2 judge the snapped span; the added
 490 | +        words are on the record."""
 491 | +        for text, before in (("can stop Bitcoin from settling a payment.", "Nobody"),
 492 | +                             ("Bitcoin started as a quiet experiment.", "In 2009")):
 493 | +            sp, info = LB.reanchor(row(text), self.src)
 494 | +            self.assertIsNotNone(sp, text)
 495 | +            self.assertEqual(info["added"]["before"], before)
 496 | +        for word in ("Hardly", "Don\u2019t"):
 497 |              src = source([f"{word} anyone can stop Bitcoin from settling a payment.", "That is the plan."])
 498 | -            sp, why = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
 499 | -            self.assertIsNone(sp, word)
 500 | -            self.assertIn(word, why)
 501 | +            sp, info = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
 502 | +            self.assertEqual(info["added"]["before"], word)
 503 | +
 504 | +    def test_the_snap_limit_is_the_packagers_clip_limit(self):                 # audit 0332 C1, qwen P2-1
 505 | +        import package as PK
 506 | +        self.assertEqual(LB.SNAP_MAX_S, PK.SEG_MAX_S)
 507 | +
 508 | +    def test_a_snap_longer_than_20_s_stays_out(self):
 509 | +        long_ = "Bitcoin " + " ".join(["keeps"] * 72) + " settling payments."             # 75 words, 0.3 s each
 510 | +        src = source([long_, "That is the plan."])
 511 | +        a, b = src.sentences[0]
 512 | +        self.assertGreater(src.tokens[b]["end"] - src.tokens[a]["start"], LB.SNAP_MAX_S)
 513 | +        sp, why = LB.reanchor(row(" ".join(["keeps"] * 8) + " settling payments."), src)
 514 | +        self.assertIsNone(sp)
 515 | +        self.assertIn("> 20 s (ruling 32", why)
 516 | +        sp, info = LB.reanchor(row(long_), src)                       # whole sentences: no snap, usable() measures it
 517 | +        self.assertEqual(info["snapped_words"], [0, 0])
 518 | +
 519 | +    def test_a_caption_speaker_marker_inside_the_snapped_span_keeps_the_row_out(self):
 520 | +        a = self.src.tokens[self.src.sentences[1][0]]["start"]
 521 | +        b = self.src.tokens[self.src.sentences[1][1]]["end"]
 522 | +        cap = lambda *ts: type("Cap", (), {"tokens": [{"word": "&gt;&gt;", "start": x} for x in ts]})()
 523 | +        text = "can stop Bitcoin from settling a payment."
 524 | +        sp, why = LB.reanchor(row(text), self.src, cap=cap((a + b) / 2))
 525 | +        self.assertIsNone(sp)
 526 | +        self.assertIn("caption speaker marker", why)
 527 | +        self.assertIsNone(LB.reanchor(row(text), self.src, cap=type("C", (), {"tokens": [
 528 | +            {"word": ">>", "start": (a + b) / 2}]})())[0])                                # the raw form too
 529 | +        for c in (cap(a + 0.5), cap(b - 0.5), None, cap()):        # at an edge, no record, no marker: L-v 2 decides
 530 | +            self.assertIsNotNone(LB.reanchor(row(text), self.src, cap=c)[0])
 531 | +        self.assertIsNotNone(LB.reanchor(row(SENTS[1]), self.src, cap=cap((a + b) / 2))[0])   # no snap: no read
 532 | +
 533 | +    def test_a_snapped_moment_counts_its_own_price_prediction(self):
 534 | +        info = {"snapped_words": [4, 0]}
 535 | +        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030. It is coming.", info, []),
 536 | +                         ["price_prediction"])
 537 | +        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030.", {"snapped_words": [0, 0]}, []), [])
 538 | +        self.assertEqual(LB.snap_risk("Bitcoin is at 70,000 today.", info, ["time_sensitive"]), ["time_sensitive"])
 539 | +        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030.", info, ["price_prediction"]),
 540 | +                         ["price_prediction"])
 541 | +        with self.assertRaises(TypeError):                                     # a malformed row, never mangled
 542 | +            LB.snap_risk("Bitcoin will hit 250,000 by 2030.", info, "price_prediction")
 543 |  
 544 |      def test_the_hit_is_measured_against_the_rows_own_caption_times(self):
 545 |          """glm C3 P1-3: a phrase said twice inside the search window would anchor on the earliest longest match; the
 546 | @@ -82,18 +121,10 @@ class TestReanchor(unittest.TestCase):
 547 |          self.assertEqual(LB.reanchor(row(SENTS[1]), self.src)[1]["offset_s"],      # glm C4 P2-8: said, not absent
 548 |                           "unmeasured: the row has no readable caption times")
 549 |  
 550 | -    def test_a_typographic_apostrophe_does_not_hide_a_negation(self):
 551 | -        """glm C2 N-3: 'Don\u2019t' (U+2019) is the negation 'Don't' to the guard."""
 552 | -        for apostrophe in ("\u2019", "'"):
 553 | -            src = source([f"Don{apostrophe}t sell your Bitcoin to anyone today.", "That is the plan."])
 554 | -            sp, why = LB.reanchor(row("sell your Bitcoin to anyone today."), src)
 555 | -            self.assertIsNone(sp, apostrophe)
 556 | -            self.assertIn("negation", why)
 557 | -
 558 | -    def test_text_that_is_not_whole_sentences_or_not_there_is_dropped_with_why(self):
 559 | -        sp, why = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
 560 | -        self.assertIsNone(sp)
 561 | -        self.assertIn("not whole sentences", why)
 562 | +    def test_text_cut_at_both_edges_snaps_and_text_that_is_not_there_is_dropped_with_why(self):
 563 | +        sp, info = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
 564 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((1, 2), [4, 5]))
 565 | +        self.assertEqual(info["added"], {"before": "Nobody can stop Bitcoin", "after": "and it works every day."})
 566 |          sp, why = LB.reanchor(row("Ethereum is a world computer for everyone."), self.src)
 567 |          self.assertIsNone(sp)
 568 |          self.assertIn("does not anchor", why)
 569 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
pipeline/ledger_build.py turns the moment LEDGER's rows into moments:
- a row is a moment the miner found in a caption record: its text, its caption times, its risk flags, its scores;
- the row's TEXT is located (re-anchored) in a sentence-ready, word-timed WORD record of the same video;
- the moment becomes that record's own whole sentences, verbatim.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR RULING 32 (02:45 ET Nov 13, restated at 03:12: "32 stands as written; the 20 s limit decides the
long snaps"): "a moment whose anchored text is not whole sentences is SNAPPED OUTWARD to the whole sentences of the
word record instead of dropped, when the snapped span is still inside the clip length limits and the same single
speaker. ... Snapping outward adds the speaker's own words, so it cannot change meaning by omission; step A / L-s
then judge the snapped span as usual. Rows where the text does not anchor at all stay out."
- Before: up to SNAP_WORDS = 3 words could be added at either edge, and SNAP_GUARD refused a snap that ADDED a negation
  or a digit (audit 2315 C1: "it could flip or add a claim the ledger's scores and risks never saw").
- The 02:37 build lost 12 rows this way (0/6, 0/9, 9/0, 0/11, 0/11, 2/12, 16/0, 0/32, 0/39, 0/47, 0/47, 0/57 words
  before / after).

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. This change is the orchestrator's own ruling;
  check that it does exactly that and no more;
- clips are verbatim whole sentences of a word-timed record;
- at most 20 s per clip (L-u, package.SEG_MAX_S);
- at most one price prediction per video (L-u), counted from the moment's risk flags.

What judges a snapped span downstream (unchanged, outside this diff):
- package.usable(): the 20 s limit, and time-sensitive words in the moment's text;
- step A (L-s, context_integrity): the moment's own view, its referents and conditions, a speaker change inside;
- the exclusion verdict (moments.exclusion_verdict, a hard gate in every pin): it screens the MOMENT TEXT for every
  L-u hard risk (accusation, partner_attack, imperative, guaranteed_return, single_source_breaking, ad_read,
  third_party_media) and for about-Bitcoin;
- L-v 2 (transcript_truth.verify_segment): every number and negation both ways against an independent recogniser, and
  exactly one speaker measured inside.

The change:
1. pipeline/ledger_build.py:
   - SNAP_WORDS, SNAP_GUARD and APOSTROPHES are removed. SNAP_MAX_S = 20.0.
   - reanchor(row, src, cap=None): a hit that is not whole sentences snaps outward to sentences k0..k1. It stays out
     when:
     (a) a word time at the snapped span's edges is missing (its length is not measured);
     (b) the snapped span runs more than 20 s;
     (c) marker_inside(cap, a, b) finds a caption speaker marker (">>" or "&gt;&gt;") on a caption token whose time is
         more than MARKER_EDGE_S = 1.0 s inside the span. cap is the caption record the row was mined from (default:
         the window Source's context_source).
     A marker within 1.0 s of an edge, no marker, or no caption record is not a measurement at this stage; L-v 2
     decides on the audio. The added words are recorded in info["added"].
   - snap_risk(text, info, risk): for a SNAPPED moment, "price_prediction" is added to its risk when its text holds a
     future price (vo_fidelity.price_mentions), because the miner flagged only the row's text.
   - build_inputs: the full-video path now looks up the row's caption record (caption_source, once per sha) and passes
     it to reanchor. The window path already attached it.
   - The docstrings are updated, including a stale "one window per video" line (it is one per moment since audit
     0208).
2. tests/package/test_ledger_build.py:
   - the old SNAP_GUARD tests now assert that the snap restores the speaker's own words and records them;
   - new: the 20 s limit; a caption marker inside the span vs at an edge vs none vs no record; snap_risk.
3. tests/package/funnel.py and tests/package/funnel_pre_edge.py: the offline funnel tools behind the 02:45 FUNNEL
   TABLE.
   - They read a build record.
   - They recompute the edges from RECORDED recogniser replies (Router replay=True: a miss raises and nothing is
     fetched).
   - Stage 0 groups reasons with their numbers taken out.
   - No pipeline code depends on them.

Check in particular:
- whether removing SNAP_GUARD leaves any risk that NO downstream gate judges, for words the ledger never saw;
- the edge times a / b and the marker window;
- that a row whose text does not anchor still stays out;
- that a snapped moment's text, start, end and words come from the word record;
- that the dedup and the window path are unchanged;
- that snap_risk cannot remove a flag.

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
