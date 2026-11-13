# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0123
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 301 s finish=stop usage in 16616 / out 8307 usd~0.174 (upper-bound price)

# Audit: pp-selectid — WINDOW records into the ledger build

Scope note: I can only see the diff. Functions referenced but not shown (`window()`, `mark()`, `E._time`, `E.spoken`, `E.sentence_ready`, `S.tokens_from_record`, `ts.segments_sha256`, `ts.sentences_from_words`, `M.exclusion_verdict`, `row()`, `tokens()` in the test helper, `CONTEXT_BEFORE_S/AFTER_S` values) are assumed to behave as their names and prior usage suggest; where a finding depends on them I say so.

## P0

**P0-1. `caption_source()` can return a *different* record than the one the ledger mined — the segments-sha match is not unique, and the loop takes the first (alphabetically) match.** `ledger_build.py:217-240` (new `caption_source`). It scans `sorted(os.listdir(d))` for any `transcript.*.json` whose `transcript_sha256 == row["transcript_sha256"]` **and** whose own `segments` hash to the same value, and returns the first. Failure scenario: the store legitimately holds two records with identical segment *hashes* but different provenance/method — e.g. `transcript.whisper_words_punct.json` (full-video, punctuated) and a re-encode/copy `transcript.yt_auto.json` whose `segments` were copied verbatim (same start/end/text triples → same `segments_sha256`, since the fixture at `test_ledger_build.py:451-454` shows the caption record's sha is just `ts.segments_sha256(lines)` with no method binding). Then `caption_source` returns whichever sorts first (`transcript.whisper...` < `transcript.yt_auto...`), and the window clip's L-s context is built from the wrong record's *words* — different tokenization/timing than the mined record. Concrete wrong result: `caption_parts` (`context_integrity.py:25-29`) selects context words by time from the wrong token stream; the exclusion prompt (`package.py:332`) and `_window_text` carry text the ledger never mined. Whether this happens in practice depends on whether the store guarantees one record per segments-sha — not verifiable from the diff. Also note: the returned record's *method* is whatever the file says (`rec.get("transcript_method")`), and `caption_parts` never checks it — the contract says "CAPTION record", but nothing enforces `yt_auto`/caption-ness. A `whisper_words` full-video record whose segments happen to match would silently serve as "the caption record". I flag this as P0-conditional: if the store can hold two records with the same segments sha, the wrong one is used; if it cannot, this collapses to P2. (Uncertain: I cannot see the store's uniqueness guarantees.)

**P0-2. `caption_parts` time-window selection can yield less than the 90 s/60 s context and still pass — the "or to the media's edge" clause is implemented as "any overlap", not "clipped to the edge".** `context_integrity.py:28-29`:
```python
pre = [tok for tok, a, b in timed if b > t0 - before and a < t0]
post = [tok for tok, a, b in timed if t1 < a <= t1 + after]
```
`pre` keeps caption words *overlapping* the 90 s window; `post` keeps words *starting* within 60 s. Two concrete shortfalls, both producing a context shorter than the law's minimum while `caption_parts` returns a non-None result (so `exclusion_for` proceeds to a real verdict, `package.py:336-338`, and `_window_text` returns a marked string — nothing records the shortfall):

1. **Caption gaps.** Auto-captions routinely have dead stretches (no words for 30+ s: music, silence, non-speech). If the caption record has no words in, say, `[t0-90, t0-40]`, the `pre` list's earliest token starts at `t0-40` — the context actually judged is 40 s, not ≥90 s. Nothing in the diff measures or reports the achieved context span; `caption_parts` returns `(from_s, to_s)` = the *requested* window (`round(t0 - before, 3), round(t1 + after, 3)`, line 31), not the achieved one — the returned window is the requested bounds, so a caller cannot even detect the shortfall from it. L-s says "judged ... from >= 90 s before to >= 60 s after"; this returns a pass (a real exclusion verdict, `measured: True` implicitly via `M.exclusion_verdict`'s return) with less. Whether the *caller* checks the achieved span is not visible in the diff — `package.exclusion_for` just passes `before`/`after` strings into `M.exclusion_verdict`, whose internals I cannot see. If `exclusion_verdict` does not itself measure the achieved span, this is a silent L-s shortfall: **fail-open where the law says the context is the judged thing.** Flag as P0-conditional → P1 if `M.exclusion_verdict` measures; I cannot verify.

2. **`post` uses `a <= t1 + after` (start-in-window) but `pre` uses overlap.** Asymmetric by design, but note a caption word that *starts* just before `t1` and runs past `t1+60` is counted in neither list (it fails `a < t0`? no — it fails `pre`'s `a < t0` only if it starts after `t0`... actually a word starting in `[t0, t1]` — inside the selection — is in neither `pre` nor `post`), which is correct (it

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 61 s finish=stop usage in 16404 / out 677 usd~0.099 (upper-bound price)

**Findings (verified only from diff):**
- **No P0/P1/P2.** All (a-e) pass per code+tests.
  - (a) No. word_pass_index (ledger_build.py:154) keeps only sentence_ready+record_sha256 rows; window_source (ledger_build.py:178-212) rejects on sha256 mismatch, bad structure, segments/words_sha mismatch, words_off_segments, !youtube clock, still_unpunctuated=True, span outside tol=0.01, channel mismatch or !sentence_ready. TestWindowRecords.test_a_window_record_is_used_only_when_every_claim_checks_out (test_ledger_build.py:493-509) tampers each field and asserts exact error strings; no Source/moment produced.
  - (b) No. caption_parts (context_integrity.py:23) returns None,None on no cs/missing times; context_around (context_integrity.py:39) propagates it; exclusion_for (package.py:333) then hard-codes verdict="exclude", measured=False, no model call. TestWindowRecords.test_a_window_without_its_caption_record_has_no_context_and_fails_closed (test_ledger_build.py:544-552) asserts exactly this (no_caption_context report, _window_text=(None,None), exclusion measured=False). Uses before=CONTEXT_BEFORE_S/after=CONTEXT_AFTER_S (or edge); never passes L-s on missing context.
  - (c) Yes. caption_source (ledger_build.py:230) matches row["transcript_sha256"] against stored record's transcript_sha256 + recomputed segments_sha256; takes first sorted name match. window_source sets it from the mined row (ledger_build.py:296). Test (test_ledger_build.py:546) without matching caption asserts "no record in the store matches the row's transcript_sha256"; wrong sha cannot match.
  - (d) Yes. context_around/_window_text (context_integrity.py:37,57) and exclusion_for (package.py:332) guard with `if getattr(src, "window", None) is not None`; else path is original window()/E.spoken() calls. build_inputs (ledger_build.py:304) only sets .window for the new path; full-video records unchanged (byte-identical contexts/prompts).
  - (e) Yes. TestWindowRecords methods each name one defect and assert the concrete failure: index counts failed/not_ready/unreadable (test_ledger_build.py:478), tamper cases produce exact why strings ("words_sha256", "still unpunctuated", "YouTube clock", "not inside the window", record_sha256, path), no-caption produces no_caption_context+exclude measured=False, window from start sets file_head=True, build with mixed rows keeps only anchored window moment and caption context lines. Updated no_word_record_why tests (test_ledger_build.py:403,413) match new messages. proof_ledger.py passes --word-pass and writes it.

No diff violates listed standing laws (L-j/L-m fail-closed on missing context/data, sentence-ready only, L-s contract for caption context on windows, no acceptance change for full records, L-e punctuation check, L-p delivered spans untouched). All new paths tested with fixtures exactly matching worker output.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 57 s finish=stop usage in 18314 / out 3757 usd~0.111 (upper-bound price)

I’ll analyze the diff against the specific questions (a)–(e) and the governing laws, focusing on what is verifiable from the provided code.

## Analysis

### (a) Can a tampered or non-sentence-ready window record reach a moment?

**Verification of `window_source()` checks:**
1.  **Path Integrity:** `os.path.dirname(path) != base` ensures the file is in `transcripts/<vid>/windows/`.
2.  **File Hash:** `hashlib.sha256(raw).hexdigest() != wp["record_sha256"]` ensures the file on disk matches the hash in `word_pass.jsonl`.
3.  **Method:** `rec.get("transcript_method") != "whisper_words_punct"` rejects non-punctuated methods.
4.  **Segments Hash:** `rec.get("transcript_sha256") != sha` (where `sha` is computed from `rec["segments"]`) ensures internal consistency.
5.  **Words Hash:** `rec.get("words_sha256") != wsha` (where `wsha` is computed from `rec["words"]`) ensures internal consistency.
6.  **Words vs Segments:** `words_off_segments(rec)` ensures words spell the segments.
7.  **Clock:** `win.get("clock") != "youtube"` rejects non-YouTube clocks.
8.  **Punctuation:** `(rec.get("punctuation") or {}).get("still_unpunctuated") is not False` rejects unpunctuated stretches.
9.  **Span Containment:** `t0 < w0 - WINDOW_TOL_S or t1 > w1 + WINDOW_TOL_S` ensures the ledger row's time span is inside the window.
10. **Channel:** `rec.get("channel_id") != row.get("channel_id")` rejects channel mismatches.
11. **Sentence Ready:** `E.sentence_ready(src)` is called on the constructed Source.

**Potential Gap:**
The check `E.sentence_ready(src)` relies on the `eligibility` module (imported as `E`). The diff does not show the implementation of `E.sentence_ready`. However, the law L-e states: "transcript_store.acquire(prefer_words) returns only a sentence_ready record... editorial_select's word pass treats any other record as failed."
In `window_source`, the record is explicitly checked for `still_unpunctuated is False`. If `E.sentence_ready` also checks for this (or similar conditions), it is redundant but safe. If `E.sentence_ready` checks something else (e.g., minimum word count, valid timing), it adds safety.
Crucially, the `word_pass_index` function filters for `r.get("sentence_ready") is not True` -> `not_ready`. So only rows marked `sentence_ready: true` in the JSONL are passed to `window_source`.
`window_source` then re-verifies the file content.
**Conclusion:** It is very difficult for a tampered or non-ready record to pass. The multi-layered hash and content checks are robust.

### (b) Can a window clip be judged for L-s with LESS than 90s/60s context, or pass when missing?

**Verification of `caption_parts()`:**
-   `before=CONTEXT_BEFORE_S` (90s) and `after=CONTEXT_AFTER_S` (60s) are default arguments.
-   `pre = [tok for tok, a, b in timed if b > t0 - before and a < t0]`
-   `post = [tok for tok, a, b in timed if t1 < a <= t1 + after]`
-   If `cs` (context source) is `None`, or `t0`/`t1` are `None`, or `cs.tokens` is empty, it returns `(None, None)`.
-   If any token in `cs.tokens` has missing start/end times, it returns `(None, None)`.

**Verification of `exclusion_for()` in `package.py`:**
-   `before, after = CI.context_around(...)`
-   `if before is None: cache[key] = {"verdict": "exclude", ... "measured": False}`
-   This implements **Fail Closed** (L-j/M12). If context is missing, the moment is excluded, not passed.

**Verification of `caption_source()`:**
-   It looks for a record in `transcripts/<vid>/` where `rec.get("transcript_sha256") == want` (the row's `transcript_sha256`).
-   It also checks `ts.segments_sha256(rec.get("segments") or []) != want`.
-   If no such record is found, it returns `(None, "no record...")`.
-   In `build_inputs`, if `src.context_source` is `None`, it logs `no_caption_context` and sets `src.context_source = None`.
-   Later, `caption_parts` will see `cs is None` and return `(None, None)`, leading to exclusion.

**Potential Gap:**
Does `caption_parts` guarantee *at least* 90s/60s of context?
The code selects *all* tokens within the window. If the video is short, or the caption record doesn't cover that time, the context will be shorter.
However, the law says: "CONTEXT INTEGRITY (L-s): every clip is judged inside its source's transcript from >= 90 s before to >= 60 s after".
If the context is *less* than 90s/60s because the video ends or the caption is missing, does it fail?
The code does **not** explicitly check if `len(pre)` or `len(post)` covers the full 90s/60s duration. It just takes what is there.
If the caption record is the "full-video" record (as stated in the docstring: "a caption record is the whole video"), then for a moment in the middle, it should have 90s/60s.
But what if the moment is near the start or end of the video?
The docstring for `caption_parts` says: "or to the media's edge". This implies that if the video is shorter than 90s before the start, it u

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of the window-record wiring (ruling 2): cycle 1 consensus (synthesis by the pp-selectid session, 01:32 ET Nov 13)

**Run.** C1_STEP.diff is 35,703 bytes; the prompt is 58,992 bytes.
- grok-4.20-0309-reasoning (xAI): no findings. "SHIP: yes".
- qwen/qwen3.8-27b (Heimdall, effort none): the context length is not enforced (P1 -> P2); some P2s. SHIP yes with
  conditions.
- z-ai/glm-5.3-flash (Heimdall, effort none): three "P0"s, of which one is conditional and two do not hold; five P1s;
  eleven P2s. SHIP yes with conditions.

The integrator answered the open question out of band: their render path never looks a pin segment's record up by
sha. It decodes its own window and checks approved_text by token ratio, failing closed before any render. So a window
clip needs nothing more in the pin.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | a window clip's L-s context can be SHORTER than 90 s / 60 s with nothing to show it: the code takes whatever caption words exist, so a caption record that stops early (an incomplete ingest) passes silently (qwen P1, glm P0-2 / P1-2) | IMPLEMENTED: the coverage is MEASURED. The caption must reach 90 s before the selection or begin within EDGE_TOL_S (30 s) of the media's start. It must reach 60 s after or end within 30 s of the video's duration (the caption record's own "duration" field, from meta.json). Otherwise caption_parts gives (None, None) and L-s fails closed. "Or to the media's edge" is the existing law's own form (window(): "or to the transcript's edge"). The window returned is the coverage achieved, no longer the bound asked for (glm P2-1). Test: test_the_caption_coverage_is_measured_never_assumed (stops at 650 s: unavailable; the same with duration 660 s: available; starts at 560 s: unavailable) |
| K2 | the caption record might not be the one the ledger mined: segments-sha matches are not proven unique, and the first one sorted wins (glm P0-1, conditional; qwen P2) | IMPLEMENTED: two or more records matching the row's transcript_sha256 is ambiguous, so there is no context (fail closed, with why). Only the full-video slots transcripts/<vid>/transcript.*.json are scanned, never a window. Test: test_two_records_matching_the_rows_sha_are_ambiguous_and_give_no_context |

## Unique findings, implemented (each verified first)

- **glm P2-10:** a caption word starting exactly at the selection's end was dropped. post now takes words with start
  >= t1.
- **glm P2-2:** context_around no longer raises StopIteration on an empty selection; it gives (None, None).
- **glm P2-3 / P2-6:** branches that were never tested now have tamper cases: the segments sha, the method, a channel
  contradiction, and segment edges off their words.
- **glm P2-7:** the exclusion verdict's normal path is tested: a canned verdict, measured, whose prompt carries the
  caption's words.
- **glm P1-4 wording:** "one window per video: the best-ranked row whose window record passes every check". A 

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0123/C2_STEP.diff (665 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index 0c4bf2f9..59db4a4f 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -30,6 +30,8 @@ CONTEXT_BEFORE_S = 90.0
   6 |  CONTEXT_MAX_BEFORE_S = 180.0
   7 |  CONTEXT_AFTER_S = 60.0
   8 |  EXCERPT_MAX = 12000                # characters of one escaped window; a longer one is CONTEXT_TOO_LONG (never cut)
   9 | +EDGE_TOL_S = 30.0                  # a caption record's first / last word this close to the media's start / end
  10 | +                                   # (its duration) counts as reaching that edge: intros and outros are often wordless
  11 |  A_KEYS = ("label", "speaker_changes_inside", "view", "referents", "conditions", "retraction", "time_ok", "proposition",
  12 |            "certainty", "speaker_is", "speaker_evidence")
  13 |  VIEWS = ("own_sincere", "attributed", "hypothetical", "conditional", "sarcastic", "question", "reading_aloud",
  14 | @@ -83,9 +85,73 @@ def mark(parts):
  15 |      return " ".join(out)
  16 |  
  17 |  
  18 | +def caption_parts(src, k0, k1, w0=None, w1=None, before=CONTEXT_BEFORE_S, after=CONTEXT_AFTER_S):
  19 | +    """A moment on a WINDOW word record (the integrator's word-pass worker: about +-45 s of words around one moment,
  20 | +    on the YouTube clock). Under the contract agreed with the integrator, its L-s context comes from the full-video
  21 | +    CAPTION record the ledger mined it from (src.context_source). The selection is the window record's own words, and
  22 | +    the context is the caption's words by TIME: every caption word overlapping the >= `before` s before the selection,
  23 | +    and every caption word starting in the `after` s after it, or to the media's edge (a caption record is the whole
  24 | +    video). YouTube's automatic captions carry no punctuation, so the window is cut by time, never by sentences, and
  25 | +    the pull-back to a question (which needs a '?') does not apply.
  26 | +    The coverage is MEASURED, never assumed (audit 0123 C1: qwen, glm). The caption must reach `before` s ahead of the
  27 | +    selection, or begin within EDGE_TOL_S of the media's start. It must reach `after` s past the selection, or end
  28 | +    within EDGE_TOL_S of the video's duration (cs.duration_s). A caption record that stops short, or an unknown
  29 | +    duration where the end would need it, leaves the context unavailable.
  30 | +    -> ([(text, selected?)], (from_s, to_s) actually covered), or (None, None) when there is no caption record, a
  31 | +    time is missing, or the coverage falls short: the context is unavailable and L-s fails closed."""
  32 | +    cs = getattr(src, "context_source", None)
  33 | +    S, T = src.sentences, src.tokens
  34 | +    lo, hi = (w0, w1) if w0 is not None and w1 is not None else (S[k0][0], S[k1][1])
  35 | +    t0, t1 = E._time(T[lo], "start"), E._time(T[hi], "end")
  36 | +    if cs is None or t0 is None or t1 is None or not cs.tokens:
  37 | +        return None, None
  38 | +    timed = [(tok, E._time(tok, "start"), E._time(tok, "end")) for tok in cs.tokens]
  39 | +    if any(a is None or b is None for _, a, b in timed):
  40 | +        return None, None                            # an unclocked caption record: no measurable window
  41 | +    first, last = min(a for _, a, _ in timed), max(b for _, _, b in timed)
  42 | +    dur = getattr(cs, "duration_s", None)
  43 | +    if not (first <= t0 - before or first <= EDGE_TOL_S):
  44 | +        return None, None                            # the caption starts too late to show what came before
  45 | +    if not (last >= t1 + after or (isinstance(dur, (int, float)) and last >= float(dur) - EDGE_TOL_S)):
  46 | +        return None, None                            # it stops short of what comes after, and short of the end
  47 | +    pre = [tok for tok, a, b in timed if b > t0 - before and a < t0]
  48 | +    post = [tok for tok, a, b in timed if t1 <= a <= t1 + after]
  49 | +    sel = E.spoken(T[lo:hi + 1])
  50 | +    if not sel.strip():
  51 | +        return None, None
  52 | +    parts = [(E.spoken(pre), False), (sel, True), (E.spoken(post), False)]
  53 | +    covered = (round(min([E._time(x, "start") for x in pre] or [t0]), 3),
  54 | +               round(max([E._time(x, "end") for x in post] or [t1]), 3))
  55 | +    return [(t, s_) for t, s_ in parts if t.strip()], covered
  56 | +
  57 | +
  58 | +def context_around(src, k0, k1, w0=None, w1=None):
  59 | +    """(the context before the selection, the context after it) as text, for any Source: a window record's from its
  60 | +    caption record (caption_parts), every other record's from its own window(). (None, None) when unavailable."""
  61 | +    if getattr(src, "window", None) is not None:
  62 | +        parts, win = caption_parts(src, k0, k1, w0, w1)
  63 | +        if parts is None:
  64 | +            return None, None
  65 | +        i = next((n for n, (_, sel) in enumerate(parts) if sel), None)
  66 | +        if i is None:                                # no selection (never from caption_parts; checked anyway)
  67 | +            return None, None
  68 | +        return " ".join(t for t, _ in parts[:i]), " ".join(t for t, _ in parts[i + 1:])
  69 | +    win = window(src, k0, k1)
  70 | +    if win is None:
  71 | +        return None, None
  72 | +    a, b = win
  73 | +    S, T = src.sentences, src.tokens
  74 | +    lo, hi = (w0, w1) if w0 is not None and w1 is not None else (S[k0][0], S[k1][1])
  75 | +    return E.spoken(T[S[a][0]:lo]), E.spoken(T[hi + 1:S[b][1] + 1])
  76 | +
  77 | +
  78 |  def _window_text(src, k0, k1, w0=None, w1=None):
  79 |      """The window's text with the selection marked. With word indices w0..w1 the selection is marked by WORDS (a
  80 | -    moment cut inside a store sentence, ruling 7 / orchestrator 06:45), else by sentences k0..k1."""
  81 | +    moment cut inside a store sentence, ruling 7 / orchestrator 06:45), else by sentences k0..k1. A moment on a WINDOW
  82 | +    word record takes its context from its caption record (caption_parts)."""
  83 | +    if getattr(src, "window", None) is not None:
  84 | +        parts, win = caption_parts(src, k0, k1, w0, w1)
  85 | +        return (mark(parts), win) if parts is not None else (None, None)
  86 |      win = window(src, k0, k1)
  87 |      if win is None:
  88 |          return None, None
  89 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
  90 | index 847d60a3..c469e5e6 100644
  91 | --- a/pipeline/ledger_build.py
  92 | +++ b/pipeline/ledger_build.py
  93 | @@ -7,11 +7,21 @@ FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call h
  94 |    interpreter, from the pp-ingest worktree, until the integrator merges it.
  95 |  - READY: a row is packageable only on a sentence-ready WORD record (law L-e). Today that is the store's full-video slot
  96 |    (transcripts/<vid>/transcript.whisper_words_punct.json, then transcript.whisper_words.json: WORD_RECORDS, in that
  97 | -  order). Its segments sha is checked, and its words must spell those segments exactly (words_off_segments). Window records from
  98 | -  the word-pass worker (the integrator's contract: transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json,
  99 | -  youtube clock, listed in moments/word_pass.jsonl) need their L-s context from the CAPTION record. That is not wired
 100 | -  yet: a row whose video has only a window record counts as waiting for a word record (report.no_word_record, "no
 101 | -  word record in the store") and is not used. No window record exists yet (none in the store at 23:36 ET Nov 12).
 102 | +  order). Its segments sha is checked, and its words must spell those segments exactly (words_off_segments).
 103 | +- WINDOW records: a video with no such full-video record may have WINDOW records from the integrator's word-pass
 104 | +  worker (pipeline/word_pass_worker.py on branch word-pass, 514dd704).
 105 | +  - Each is transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json: about +-45 s of words around one ledger
 106 | +    moment, on the YouTube clock, with words_sha256.
 107 | +  - Each is listed in moments/word_pass.jsonl as {moment_id, video_id, window_record, record_sha256, sentence_ready,
 108 | +    window, at}.
 109 | +  - word_pass_index() reads that list. window_source() checks every claim before use: the file's sha256 is the row's
 110 | +    record_sha256, the segments sha, words_sha256, the words spell the segments, the YouTube clock, nothing still
 111 | +    unpunctuated, and the ledger row's span inside the window.
 112 | +  - One window per video: the best-ranked row whose window record passes every check (a row whose own record fails
 113 | +    is passed over with why). The video's other rows re-anchor in it, or are counted out.
 114 | +  - L-s context comes from the caption record the ledger mined the moment from (caption_source(): its segments sha
 115 | +    is the row's transcript_sha256), cut by time (context_integrity.caption_parts). Without one, the context is
 116 | +    unavailable and L-s fails closed.
 117 |  - RE-ANCHOR: sentence_law.anchor, the sentence law's own text locator, finds the row's TEXT in the word record. The
 118 |    row's caption-clock times only narrow the search. The span then snaps to that record's WHOLE sentences when at most
 119 |    SNAP_WORDS words lie outside the anchored text at either edge; otherwise the row is dropped, and why is recorded.
 120 | @@ -20,6 +30,7 @@ FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call h
 121 |    row's scores, risks, topics, reason and mining provenance are kept (mined.ledger_moment_id).
 122 |  -> build_inputs(...) = (moments, sources, report).
 123 |  """
 124 | +import hashlib
 125 |  import json
 126 |  import os
 127 |  import sys
 128 | @@ -47,6 +58,9 @@ INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest
 129 |  MAIN = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")
 130 |  STORE = os.path.join(MAIN, "data", "editorial")
 131 |  WORD_RECORDS = ("transcript.whisper_words_punct.json", "transcript.whisper_words.json")
 132 | +WORD_PASS = os.path.join(STORE, "moments", "word_pass.jsonl")     # the word-pass worker's rows (the integrator's)
 133 | +WINDOW_TOL_S = 0.01      # the ledger row's span must lie inside its window record's [start_s, end_s] (the worker cut
 134 | +                         # the window around that very span; this is only the 3-decimal rounding)
 135 |                            # the store's two word-record slots (transcript_store._store: transcript.<method>.json), read
 136 |                            # in this order: a total order, never the file system's (glm C3 P1-2)
 137 |  
 138 | @@ -129,6 +143,143 @@ def words_off_segments(rec, tol=0.001):
 139 |      return None
 140 |  
 141 |  
 142 | +def _num(x):
 143 | +    try:
 144 | +        v = float(x)
 145 | +    except (TypeError, ValueError):
 146 | +        return None
 147 | +    return v if v == v and v not in (float("inf"), float("-inf")) else None
 148 | +
 149 | +
 150 | +def word_pass_index(path=WORD_PASS):
 151 | +    """The word-pass worker's rows -> ({moment_id: the LAST row of that moment, when it is sentence_ready with a
 152 | +    window_record and a record_sha256}, report). A failed moment's row has neither, and the worker never retries it.
 153 | +    No file yet = no window record yet: ({}, report). A file that exists but cannot be read raises: it is never read
 154 | +    as an empty word pass (law L-j)."""
 155 | +    rep = {"rows": 0, "unreadable": 0, "ready": 0, "not_ready": 0, "failed": 0, "file": path}
 156 | +    try:
 157 | +        f = open(path)
 158 | +    except FileNotFoundError:
 159 | +        return {}, dict(rep, file="none yet: " + path)
 160 | +    last = {}
 161 | +    with f:
 162 | +        for line in f:
 163 | +            if not line.strip():
 164 | +                continue
 165 | +            rep["rows"] += 1
 166 | +            try:
 167 | +                r = json.loads(line)
 168 | +            except ValueError:
 169 | +                rep["unreadable"] += 1
 170 | +                continue
 171 | +            if not isinstance(r, dict) or not isinstance(r.get("moment_id"), str):
 172 | +                rep["unreadable"] += 1
 173 | +                continue
 174 | +            last[r["moment_id"]] = r
 175 | +    out = {}
 176 | +    for mid, r in last.items():
 177 | +        if r.get("error") or r.get("window_record") is None:
 178 | +            rep["failed"] += 1
 179 | +        elif r.get("sentence_ready") is not True:
 180 | +            rep["not_ready"] += 1
 181 | +        elif isinstance(r.get("window_record"), str) and isinstance(r.get("record_sha256"), str):
 182 | +            out[mid] = r
 183 | +            rep["ready"] += 1
 184 | +        else:
 185 | +            rep["unreadable"] += 1
 186 | +    return out, rep
 187 | +
 188 | +
 189 | +def window_source(row, wp, ctx, store=STORE):
 190 | +    """The moment's sentence-ready WINDOW record (its word_pass.jsonl row `wp`) as an eligibility Source, every claim
 191 | +    checked -> (Source, path, None) or (None, None, why). The Source carries .window = {start_s, end_s, record,
 192 | +    words_sha256, record_sha256}; file_head only when the window starts at the media's first second."""
 193 | +    vid, rel = row["video_id"], wp["window_record"]
 194 | +    name = os.path.basename(rel)
 195 | +    base = os.path.join(os.path.realpath(store), "transcripts", vid, "windows")
 196 | +    path = os.path.realpath(os.path.join(store, rel))
 197 | +    if wp.get("video_id") != vid or os.path.dirname(path) != base:
 198 | +        return None, None, f"{name}: not this video's window record (transcripts/{vid}/windows/)"
 199 | +    try:
 200 | +        with open(path, "rb") as f:
 201 | +            raw = f.read()
 202 | +        rec = json.loads(raw)
 203 | +    except (OSError, ValueError):
 204 | +        return None, None, f"{name}: cannot be read"
 205 | +    if hashlib.sha256(raw).hexdigest() != wp["record_sha256"]:
 206 | +        return None, None, f"{name}: the file is not the one word_pass.jsonl names (record_sha256)"
 207 | +    if not isinstance(rec, dict) or rec.get("video_id") != vid or rec.get("transcript_method") != "whisper_words_punct":
 208 | +        return None, None, f"{name}: not a punctuated word record of this video"
 209 | +    try:
 210 | +        sha = ts.segments_sha256(rec.get("segments") or [])
 211 | +        wsha = hashlib.sha256(json.dumps([[w["word"], w["start"], w["end"]] for w in rec["words"]],
 212 | +                                         ensure_ascii=False).encode()).hexdigest()
 213 | +    except (KeyError, TypeError, ValueError, AttributeError):
 214 | +        return None, None, f"{name}: its segments or words cannot be hashed"
 215 | +    if rec.get("transcript_sha256") != sha:
 216 | +        return None, None, f"{name}: its segments do not match its transcript_sha256"
 217 | +    if rec.get("words_sha256") != wsha:
 218 | +        return None, None, f"{name}: its words do not match its words_sha256"
 219 | +    off = words_off_segments(rec)
 220 | +    if off:
 221 | +        return None, None, f"{name}: its words do not spell its sha-checked segments ({off})"
 222 | +    win = rec.get("window") if isinstance(rec.get("window"), dict) else {}
 223 | +    w0, w1 = _num(win.get("start_s")), _num(win.get("end_s"))
 224 | +    if w0 is None or w1 is None or win.get("clock") != "youtube":
 225 | +        return None, None, f"{name}: no window on the YouTube clock"
 226 | +    if (rec.get("punctuation") or {}).get("still_unpunctuated") is not False:
 227 | +        return None, None, f"{name}: a stretch is still unpunctuated (law L-e)"
 228 | +    t0, t1 = _num(row.get("start")), _num(row.get("end"))
 229 | +    if t0 is None or t1 is None or t0 < w0 - WINDOW_TOL_S or t1 > w1 + WINDOW_TOL_S:
 230 | +        return None, None, f"{name}: the row's span {t0}-{t1} is not inside the window {w0}-{w1}"
 231 | +    if rec.get("channel_id") and rec.get("channel_id") != row.get("channel_id"):
 232 | +        return None, None, f"{name}: it names channel {rec.get('channel_id')}, the ledger row {row.get('channel_id')}"
 233 | +    timing, toks = S.tokens_from_record(rec)
 234 | +    reg = ctx.channel(row.get("channel_id")) or {}
 235 | +    src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
 236 | +                   row.get("published_at"), sha, "whisper_words_punct", toks, timing=timing,
 237 | +                   title=row.get("title") or "", file_head=(w0 == 0.0), vod=True)
 238 | +    if not E.sentence_ready(src):
 239 | +        return None, None, f"{name}: not sentence-ready (law L-e)"
 240 | +    src.window = {"start_s": w0, "end_s": w1, "record": rel, "words_sha256": wsha, "record_sha256": wp["record_sha256"]}
 241 | +    return src, path, None
 242 | +
 243 | +
 244 | +def caption_source(row, ctx, store=STORE):
 245 | +    """The full-video record the ledger row was MINED from: the one whose segments sha is the row's transcript_sha256
 246 | +    (the full-video slots transcripts/<vid>/transcript.*.json only; never a window). It is a window record's L-s
 247 | +    context (the contract) -> (Source with .duration_s, file name) or (None, why). Two records matching is ambiguous:
 248 | +    no context (audit 0123 C1, glm P0-1)."""
 249 | +    vid, want = row["video_id"], row.get("transcript_sha256")
 250 | +    d = os.path.join(store, "transcripts", vid)
 251 | +    try:
 252 | +        names = sorted(n for n in os.listdir(d) if n.startswith("transcript.") and n.endswith(".json"))
 253 | +    except OSError:
 254 | +        return None, "no transcript directory for the video"
 255 | +    found = []
 256 | +    for n in names:
 257 | +        try:
 258 | +            with open(os.path.join(d, n)) as f:
 259 | +                rec = json.load(f)
 260 | +            if not isinstance(rec, dict) or not want or rec.get("transcript_sha256") != want or \
 261 | +                    ts.segments_sha256(rec.get("segments") or []) != want:
 262 | +                continue
 263 | +            found.append((n, rec, S.tokens_from_record(rec)))
 264 | +        except (OSError, ValueError, KeyError, TypeError, AttributeError):
 265 | +            continue
 266 | +    if not found:
 267 | +        return None, "no record in the store matches the row's transcript_sha256"
 268 | +    if len(found) > 1:
 269 | +        return None, f"{len(found)} records match the row's transcript_sha256 ({[n for n, _, _ in found]}): ambiguous"
 270 | +    n, rec, (timing, toks) = found[0]
 271 | +    reg = ctx.channel(row.get("channel_id")) or {}
 272 | +    src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
 273 | +                   row.get("published_at"), want, rec.get("transcript_method"), toks, timing=timing,
 274 | +                   title=row.get("title") or "", file_head=True, vod=True)
 275 | +    src.duration_s = _num(rec.get("duration"))          # the media's end, for the coverage check (caption_parts)
 276 | +    return src, n
 277 | +
 278 | +
 279 |  def word_source(row, ctx, store=STORE):
 280 |      """The video's sentence-ready word record from the store's full-video slot (punctuated first, its segments sha
 281 |      checked), as an eligibility Source with the row's identity -> (Source, path, passed_over), or (None, None,
 282 | @@ -222,11 +373,14 @@ def reanchor(row, src):
 283 |      return sp, info
 284 |  
 285 |  
 286 | -def build_inputs(rows, ctx, store=STORE, log=print):
 287 | -    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). Rows on a video with no sentence-
 288 | -    ready word record, rows whose text does not re-anchor on whole sentences, and duplicates of one span are dropped,
 289 | -    each counted with why."""
 290 | +def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None):
 291 | +    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). word_pass: word_pass_index()'s
 292 | +    {moment_id: row} (None = no window records). Rows on a video with neither a sentence-ready full-video word record
 293 | +    nor a sentence-ready window record, rows whose text does not re-anchor on whole sentences, and duplicates of one
 294 | +    span are dropped, each counted with why."""
 295 | +    word_pass = word_pass or {}
 296 |      report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "no_word_record_videos": {},
 297 | +              "window_records": {}, "window_passed_over": {}, "no_caption_context": {},
 298 |                "fallbacks": {},
 299 |                "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "duplicates_of": {},
 300 |                "moments": 0, "videos": 0,
 301 | @@ -249,15 +403,35 @@ def build_inputs(rows, ctx, store=STORE, log=print):
 302 |              report["channel_conflict"][vid] = {"rows": len(rs), "channel_ids": channels}
 303 |              continue
 304 |          src, path, passed_over = word_source(rs[0], ctx, store)
 305 | -        if src is None:
 306 | -            why = "; ".join(passed_over)
 307 | -            report["no_word_record"] += len(rs)
 308 | -            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 309 | -            report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 310 | -            continue
 311 | -        if passed_over:
 312 | +        if src is None:                         # the WINDOW path: the best-ranked row of this video with a
 313 | +            wrow, why_w = None, []              # sentence-ready window record (rows arrive best first)
 314 | +            for i, r in irs:
 315 | +                wp = word_pass.get(r["moment_id"])
 316 | +                if wp is None:
 317 | +                    continue
 318 | +                cand, cpath, why = window_source(r, wp, ctx, store)
 319 | +                if cand is not None:
 320 | +                    src, path, wrow = cand, cpath, r
 321 | +                    break
 322 | +                why_w.append(f"{r['moment_id']}: {why}")
 323 | +            if why_w:
 324 | +                report["window_passed_over"][vid] = why_w
 325 | +            if src is None:
 326 | +                why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
 327 | +                                               ["no sentence-ready window record"]))
 328 | +                report["no_word_record"] += len(rs)
 329 | +                report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 330 | +                report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 331 | +                continue
 332 | +            src.context_source, cwhy = caption_source(wrow, ctx, store)
 333 | +            if src.context_source is None:
 334 | +                src.context_source = None
 335 | +                report["no_caption_context"][vid] = cwhy          # L-s fails closed for this video's clips
 336 | +            report["window_records"][vid] = os.path.relpath(path, os.path.realpath(store))
 337 | +        elif passed_over:
 338 |              report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
 339 | -        report["word_records"][vid] = os.path.relpath(path, store)        # read; whether a moment came of it: moments
 340 | +        if getattr(src, "window", None) is None:
 341 | +            report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
 342 |          for i, r in irs:
 343 |              sp, info = reanchor(r, src)
 344 |              if sp is None:
 345 | @@ -273,6 +447,9 @@ def build_inputs(rows, ctx, store=STORE, log=print):
 346 |                       "reason": r.get("reason") or ""}
 347 |                  mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 348 |                               ledger_text=r.get("text"))
 349 | +                if getattr(src, "window", None) is not None:      # provenance: the window record it was cut from
 350 | +                    mined["window"] = dict(src.window, context_record=(getattr(src.context_source, "transcript_method",
 351 | +                                                                                None)))
 352 |                  rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
 353 |                  rec["rank_score"] = M.rank_score(rec)
 354 |              except (KeyError, TypeError, ValueError) as e:     # counted, never a crash (glm C1 P1-8)
 355 | @@ -286,6 +463,7 @@ def build_inputs(rows, ctx, store=STORE, log=print):
 356 |          f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
 357 |          f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
 358 |          f"{len(report['channel_conflict'])} video(s) name more than one channel, "
 359 | -        f"{len(report['fallbacks'])} read from a fallback record")
 360 | +        f"{len(report['fallbacks'])} read from a fallback record; {len(report['window_records'])} window record(s) "
 361 | +        f"used ({len(report['no_caption_context'])} without a caption record for L-s)")
 362 |      moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
 363 |      return moments, sources, report
 364 | diff --git a/pipeline/package.py b/pipeline/package.py
 365 | index 95b12b09..aaae8f37 100644
 366 | --- a/pipeline/package.py
 367 | +++ b/pipeline/package.py
 368 | @@ -858,12 +858,13 @@ def exclusion_for(router, m, sources, cache, seed=7):
 369 |      if key not in cache:
 370 |          import moments as M
 371 |          src = sources[m["video_id"]]
 372 | -        a, b = CI.window(src, m["sentences"][0], m["sentences"][1])
 373 | -        w0, w1 = m["words"]
 374 | -        cache[key] = M.exclusion_verdict(
 375 | -            router, m["text"], E.spoken(src.tokens[src.sentences[a][0]:w0]),
 376 | -            E.spoken(src.tokens[w1 + 1:src.sentences[b][1] + 1]), seed=seed,
 377 | -            avoid_model=(m.get("mined") or {}).get("by"))
 378 | +        before, after = CI.context_around(src, m["sentences"][0], m["sentences"][1], *m["words"])
 379 | +        if before is None:                                    # no context to judge in (a window record without its
 380 | +            cache[key] = {"verdict": "exclude", "why": "no context: the moment's context is unavailable",   # caption
 381 | +                          "risks": [], "backend": None, "measured": False, "replayed": False}            # record)
 382 | +        else:
 383 | +            cache[key] = M.exclusion_verdict(router, m["text"], before, after, seed=seed,
 384 | +                                             avoid_model=(m.get("mined") or {}).get("by"))
 385 |      return cache[key]
 386 |  
 387 |  
 388 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 389 | index 5d344003..37091176 100644
 390 | --- a/tests/package/proof_ledger.py
 391 | +++ b/tests/package/proof_ledger.py
 392 | @@ -2,7 +2,9 @@
 393 |  """ORCHESTRATOR 22:40 ruling 2: build the medley from the INGEST LEDGER and seal a pin.
 394 |  
 395 |  - The rows are pp-ingest's adapter (best_unused_moments), read-only.
 396 | -- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py).
 397 | +- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py). That
 398 | +  is the store's full-video record, or else the integrator's word-pass WINDOW record (moments/word_pass.jsonl,
 399 | +  --word-pass), whose L-s context comes from the caption record the ledger mined.
 400 |  - "now" is the RENDER clock (ruling 1): L-v 3 and currency are judged against tonight, not against a universe snapshot.
 401 |  - Novelty (L-p): every clip span of the pins already delivered (--delivered, required; tonight: the 37c5b5f5 review,
 402 |    run 165629, and the 41f29b1f medley) is passed to package.usable as delivered. usable drops ANY moment that overlaps
 403 | @@ -80,6 +82,7 @@ def main(argv=None):
 404 |      ap.add_argument("--since", help="ISO time with a zone; default: the newest delivered pin's approved_at")
 405 |      ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
 406 |      ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 407 | +    ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 408 |      a = ap.parse_args(argv)
 409 |      now = datetime.now(timezone.utc)
 410 |      try:                                                 # read before anything is written (glm C2 N-4)
 411 | @@ -108,7 +111,10 @@ def main(argv=None):
 412 |          f"{len(delivered)} clip spans out")
 413 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
 414 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 415 | -    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say)
 416 | +    wp, wp_rep = LB.word_pass_index(a.word_pass)
 417 | +    say(f"  word pass: {json.dumps(wp_rep)}")
 418 | +    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp)
 419 | +    inputs["word_pass"] = wp_rep
 420 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 421 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 422 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 423 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 424 | index 696b7d11..f75c86d1 100644
 425 | --- a/tests/package/test_ledger_build.py
 426 | +++ b/tests/package/test_ledger_build.py
 427 | @@ -4,6 +4,7 @@
 428 |  - reading the store's word record (its sha checked, sentence-ready only);
 429 |  - turning rows into the packager's moments (counted drops, no duplicate spans);
 430 |  - the adapter's failures are raised, never read as an empty ledger."""
 431 | +import hashlib
 432 |  import io
 433 |  import json
 434 |  import os
 435 | @@ -19,7 +20,7 @@ sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 436 |  import eligibility as E  # noqa: E402
 437 |  import ledger_build as LB  # noqa: E402
 438 |  import transcript_store as ts  # noqa: E402
 439 | -from test_eligibility import NOW, REG, source  # noqa: E402
 440 | +from test_eligibility import NOW, REG, source, tokens  # noqa: E402
 441 |  
 442 |  SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settling a payment.",
 443 |           "That is the whole design and it works every day.", "Bitcoin does not ask for permission.",
 444 | @@ -241,7 +242,8 @@ class TestWordSourceAndInputs(unittest.TestCase):
 445 |              self.assertEqual(ms, [])
 446 |              self.assertEqual(rep["no_word_record_why"],
 447 |                               {"transcript.whisper_words_punct.json: its segments do not match its transcript_sha256; "
 448 | -                              "transcript.whisper_words.json: not sentence-ready (law L-e)": 1})
 449 | +                              "transcript.whisper_words.json: not sentence-ready (law L-e); "
 450 | +                              "no sentence-ready window record": 1})
 451 |              self.store_with(d, "vidA", SENTS, method="whisper_words")           # a verbatim record that IS ready
 452 |              ms, _, rep = LB.build_inputs([row(SENTS[0])], ctx, d, log=lambda s: None)
 453 |              self.assertEqual(len(ms), 1)
 454 | @@ -271,7 +273,8 @@ class TestWordSourceAndInputs(unittest.TestCase):
 455 |              self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["L1"])
 456 |              self.assertEqual(sorted(rep["malformed"]), ["L2", "row 2", "row 3", "row 4"])
 457 |              ms, _, rep = LB.build_inputs([row(SENTS[0], vid="vidZ")], ctx, d, log=lambda s: None)
 458 | -            self.assertEqual(rep["no_word_record_videos"], {"vidZ": {"rows": 1, "why": "no word record in the store"}})
 459 | +            self.assertEqual(rep["no_word_record_videos"], {"vidZ": {"rows": 1, "why": "no word record in the store; "
 460 | +                                                                                 "no sentence-ready window record"}})
 461 |  
 462 |      def test_rows_become_the_packagers_moments_with_every_drop_counted(self):
 463 |          ctx = E.Context(NOW, REG)
 464 | @@ -328,6 +331,200 @@ class TestAdapter(unittest.TestCase):
 465 |              self.assertEqual((rows, rep["excluded"]), ([], {"delivered in the previous 24 h": 3}))
 466 |  
 467 |  
 468 | +SENTS_W = ["So we were talking about money before the break.", "Bitcoin is a global free market.",
 469 | +           "Nobody can stop Bitcoin from settling a payment.", "That is the whole design and it works every day.",
 470 | +           "Anyway, let us move on to the next question."]
 471 | +
 472 | +
 473 | +def window_fixture(d, vid="vidW", w0=600.0, still=False, clock="youtube", caption=True, cap_from=0, cap_to=900,
 474 | +                   duration=900.0):
 475 | +    """A window record exactly as the word-pass worker's make_record writes it (words on the YouTube clock, segments
 476 | +    from sentences_from_words, words_sha256, window, punctuation), its word_pass.jsonl row, and the full-video caption
 477 | +    record the ledger mined from (unpunctuated lines over the whole video)."""
 478 | +    words = [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in tokens(SENTS_W, t0=w0 + 1.0)]
 479 | +    segs = [{"start": round(x["start"], 3), "end": round(x["end"], 3), "text": x["text"].strip()}
 480 | +            for x in ts.sentences_from_words(words)]
 481 | +    w1 = round(words[-1]["end"] + 1.0, 3)
 482 | +    rec = {"video_id": vid, "transcript_method": "whisper_words_punct", "segments": segs,
 483 | +           "transcript_sha256": ts.segments_sha256(segs), "words": words,
 484 | +           "words_sha256": hashlib.sha256(json.dumps([[w["word"], w["start"], w["end"]] for w in words],
 485 | +                                                     ensure_ascii=False).encode()).hexdigest(),
 486 | +           "punctuation": {"still_unpunctuated": still},
 487 | +           "window": {"start_s": w0, "end_s": w1, "clock": clock, "offset_s": w0}}
 488 | +    rel = f"transcripts/{vid}/windows/{w0:.3f}-{w1:.3f}.whisper_words_punct.json"
 489 | +    os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
 490 | +    with open(os.path.join(d, rel), "w") as f:
 491 | +        json.dump(rec, f)
 492 | +    with open(os.path.join(d, rel), "rb") as f:
 493 | +        sha = hashlib.sha256(f.read()).hexdigest()
 494 | +    wp = {"moment_id": "W1", "video_id": vid, "window_record": rel, "record_sha256": sha, "sentence_ready": not still,
 495 | +          "window": [w0, w1], "at": "2026-11-13T06:00:00+00:00"}
 496 | +    cap = None
 497 | +    if caption:
 498 | +        lines = [{"start": float(t), "end": float(t + 5), "text": f"caption line {t} about money"}
 499 | +                 for t in range(cap_from, cap_to, 5)]
 500 | +        cap = ts.segments_sha256(lines)
 501 | +        with open(os.path.join(d, "transcripts", vid, "transcript.yt_auto.json"), "w") as f:
 502 | +            json.dump({"video_id": vid, "transcript_method": "yt_auto", "segments": lines, "transcript_sha256": cap,
 503 | +                       "duration": duration}, f)
 504 | +    k = [i for i, t in enumerate(words) if t["word"] == "Nobody"][0]
 505 | +    n = len(SENTS_W[2].split())
 506 | +    r = dict(row(SENTS_W[2], start=words[k]["start"], end=words[k + n - 1]["end"], mid="W1", vid=vid),
 507 | +             transcript_sha256=cap)
 508 | +    return rel, wp, r, words
 509 | +
 510 | +
 511 | +class TestWindowRecords(unittest.TestCase):
 512 | +    """The integrator's word-pass worker (word-pass 514dd704): window records listed in moments/word_pass.jsonl."""
 513 | +
 514 | +    def test_the_word_pass_index_reads_each_moments_last_ready_row_and_counts_the_rest(self):
 515 | +        with tempfile.TemporaryDirectory() as d:
 516 | +            p = os.path.join(d, "word_pass.jsonl")
 517 | +            self.assertEqual(LB.word_pass_index(p)[0], {})                          # no file yet: no window record
 518 | +            rows = [{"moment_id": "A", "window_record": None, "record_sha256": None, "sentence_ready": False,
 519 | +                     "error": "word pass: boom"},
 520 | +                    {"moment_id": "B", "window_record": "x", "record_sha256": "s", "sentence_ready": False},
 521 | +                    {"moment_id": "C", "window_record": "x", "record_sha256": "s1", "sentence_ready": True},
 522 | +                    {"moment_id": "C", "window_record": "y", "record_sha256": "s2", "sentence_ready": True,
 523 | +                     "reused": True}]
 524 | +            with open(p, "w") as f:
 525 | +                f.write("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
 526 | +            idx, rep = LB.word_pass_index(p)
 527 | +            self.assertEqual(list(idx), ["C"])
 528 | +            self.assertEqual(idx["C"]["record_sha256"], "s2")                       # the last row of a moment wins
 529 | +            self.assertEqual((rep["failed"], rep["not_ready"], rep["ready"], rep["unreadable"]), (1, 1, 1, 1))
 530 | +
 531 | +    def test_a_window_record_is_used_only_when_every_claim_checks_out(self):
 532 | +        ctx = E.Context(NOW, REG)
 533 | +        with tempfile.TemporaryDirectory() as d:
 534 | +            rel, wp, r, words = window_fixture(d)
 535 | +            src, path, why = LB.window_source(r, wp, ctx, d)
 536 | +            self.assertIsNone(why)
 537 | +            self.assertEqual((src.timing, src.file_head, src.window["start_s"]), ("word", False, 600.0))
 538 | +            p = os.path.join(d, rel)
 539 | +            with open(p) as f:
 540 | +                good = json.load(f)
 541 | +
 542 | +            def tampered(rec, **row_change):
 543 | +                with open(p, "w") as f:
 544 | +                    json.dump(rec, f)
 545 | +                with open(p, "rb") as f:
 546 | +                    sha = hashlib.sha256(f.read()).hexdigest()
 547 | +                return LB.window_source(dict(r, **row_change.get("row", {})), dict(wp, record_sha256=sha), ctx, d)[2]
 548 | +            w = [dict(x) for x in good["words"]]
 549 | +            w[3]["start"] += 0.05                                     # an INTERIOR word's time: only words_sha256 sees it
 550 | +            self.assertIn("words_sha256", tampered(dict(good, words=w)))
 551 | +            self.assertIn("still unpunctuated", tampered(dict(good, punctuation={"still_unpunctuated": True})))
 552 | +            self.assertIn("YouTube clock", tampered(dict(good, window=dict(good["window"], clock="window"))))
 553 | +            self.assertIn("not inside the window", tampered(good, row={"start": 10.0, "end": 20.0}))
 554 | +            self.assertIn("transcript_sha256", tampered(dict(good, transcript_sha256="0" * 64)))
 555 | +            self.assertIn("not a punctuated word record", tampered(dict(good, transcript_method="whisper_words")))
 556 | +            self.assertIn("names channel UCother", tampered(dict(good, channel_id="UCother")))
 557 | +            segs = [dict(x) for x in good["segments"]]
 558 | +            segs[1]["start"] = segs[1]["start"] + 0.5                     # a segment edge off its first word's time
 559 | +            self.assertIn("do not spell", tampered(dict(good, segments=segs, transcript_sha256=ts.segments_sha256(segs))))
 560 | +            with open(p, "w") as f:
 561 | +                json.dump(good, f)
 562 | +            self.assertIn("record_sha256", LB.window_source(r, dict(wp, record_sha256="0" * 64), ctx, d)[2])
 563 | +            self.assertIn("not this video's window record",
 564 | +                          LB.window_source(r, dict(wp, window_record="transcripts/vidW/x.json"), ctx, d)[2])
 565 | +
 566 | +    def test_a_window_from_the_media_start_is_file_head(self):
 567 | +        with tempfile.TemporaryDirectory() as d:
 568 | +            rel, wp, r, words = window_fixture(d, w0=0.0)
 569 | +            self.assertTrue(LB.window_source(r, wp, E.Context(NOW, REG), d)[0].file_head)
 570 | +
 571 | +    def test_a_video_without_a_full_record_is_built_from_its_window_with_caption_context(self):
 572 | +        import context_integrity as CI
 573 | +        ctx = E.Context(NOW, REG)
 574 | +        with tempfile.TemporaryDirectory() as d:
 575 | +            rel, wp, r, words = window_fixture(d)
 576 | +            far = dict(row("Bitcoin started as a quiet experiment.", start=100.0, end=104.0, mid="W2", vid="vidW"),
 577 | +                       transcript_sha256=r["transcript_sha256"])               # outside the window: it cannot anchor
 578 | +            ms, srcs, rep = LB.build_inputs([r, far], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 579 | +            self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["W1"])
 580 | +            self.assertEqual(ms[0]["text"], SENTS_W[2])
 581 | +            self.assertEqual(list(rep["not_anchored"]), ["W2"])
 582 | +            self.assertEqual(rep["window_records"], {"vidW": rel})
 583 | +            src = srcs["vidW"]
 584 | +            self.assertEqual(src.context_source.transcript_method, "yt_auto")
 585 | +            text, win = CI._window_text(src, ms[0]["sentences"][0], ms[0]["sentences"][1], *ms[0]["words"])
 586 | +            t0 = words[[w["word"] for w in words].index("Nobody")]["start"]
 587 | +            self.assertLessEqual(win[0], t0 - CI.CONTEXT_BEFORE_S)                  # at least 90 s covered before
 588 | +            self.assertGreater(win[0], t0 - CI.CONTEXT_BEFORE_S - 5.0)                  # (one caption line over)
 589 | +            self.assertEqual(ms[0]["mined"]["window"]["record"], rel)                    # provenance in the moment
 590 | +            self.assertEqual(ms[0]["mined"]["window"]["context_record"], "yt_auto")
 591 | +            self.assertIn(f"caption line {int(t0 - 85) // 5 * 5} about money", text)   # the caption, 85 s before
 592 | +            self.assertIn("<selected>" + SENTS_W[2] + "</selected>", text)            # the window's own words
 593 | +            before, after = CI.context_around(src, ms[0]["sentences"][0], ms[0]["sentences"][1], *ms[0]["words"])
 594 | +            self.assertIn("caption line", before)
 595 | +            self.assertIn("caption line", after)
 596 | +
 597 | +    def test_the_caption_coverage_is_measured_never_assumed(self):
 598 | +        """Audit 0123 C1 (qwen, glm): a caption that stops short of 60 s after the clip (and short of the media's end),
 599 | +        or starts after the 90 s before it (and not near the media's start), leaves the context unavailable."""
 600 | +        import context_integrity as CI
 601 | +        ctx = E.Context(NOW, REG)
 602 | +        for kw, ok in (({"cap_to": 650}, False),                         # stops at 650 s; the clip ends ~616 s
 603 | +                       ({"cap_to": 650, "duration": 660.0}, True),        # ... but 650 s is the media's end, nearly
 604 | +                       ({"cap_from": 560}, False),                        # starts 560 s; 90 s before is ~526 s
 605 | +                       ({}, True)):
 606 | +            with tempfile.TemporaryDirectory() as d:
 607 | +                rel, wp, r, words = window_fixture(d, **kw)
 608 | +                ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 609 | +                m = ms[0]
 610 | +                text, win = CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"])
 611 | +                self.assertEqual(text is not None, ok, kw)
 612 | +
 613 | +    def test_two_records_matching_the_rows_sha_are_ambiguous_and_give_no_context(self):
 614 | +        with tempfile.TemporaryDirectory() as d:
 615 | +            rel, wp, r, words = window_fixture(d)
 616 | +            src = os.path.join(d, "transcripts", "vidW", "transcript.yt_auto.json")
 617 | +            with open(src) as f, open(os.path.join(d, "transcripts", "vidW", "transcript.yt_manual.json"), "w") as g:
 618 | +                g.write(f.read())
 619 | +            cs, why = LB.caption_source(r, E.Context(NOW, REG), d)
 620 | +            self.assertIsNone(cs)
 621 | +            self.assertIn("ambiguous", why)
 622 | +
 623 | +    def test_the_exclusion_verdict_reads_the_caption_context(self):
 624 | +        """glm C1 P2-7: the normal path, measured: the verdict's prompt carries the caption's words around the clip."""
 625 | +        import package as PK
 626 | +
 627 | +        class Canned:
 628 | +            def __init__(self):
 629 | +                self.prompts = []
 630 | +
 631 | +            def call(self, role, prompt, max_tokens=2000, seed=7, **k):
 632 | +                self.prompts.append(prompt)
 633 | +                return type("R", (), {"text": json.dumps({"risks": [], "about_bitcoin": "yes", "why": "ok"}),
 634 | +                                      "backend": "xai:grok", "replayed": False})()
 635 | +
 636 | +            def reject(self, r):
 637 | +                pass
 638 | +        with tempfile.TemporaryDirectory() as d:
 639 | +            rel, wp, r, words = window_fixture(d)
 640 | +            ms, srcs, rep = LB.build_inputs([r], E.Context(NOW, REG), d, log=lambda s: None, word_pass={"W1": wp})
 641 | +            router = Canned()
 642 | +            ex = PK.exclusion_for(router, ms[0], srcs, {})
 643 | +            self.assertEqual((ex["verdict"], ex["measured"]), ("keep", True))
 644 | +            self.assertIn("caption line", router.prompts[0])
 645 | +
 646 | +    def test_a_window_without_its_caption_record_has_no_context_and_fails_closed(self):
 647 | +        import context_integrity as CI
 648 | +        import package as PK
 649 | +        ctx = E.Context(NOW, REG)
 650 | +        with tempfile.TemporaryDirectory() as d:
 651 | +            rel, wp, r, words = window_fixture(d, caption=False)
 652 | +            ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 653 | +            self.assertEqual(rep["no_caption_context"], {"vidW": "no record in the store matches the row's "
 654 | +                                                                  "transcript_sha256"})
 655 | +            m = ms[0]
 656 | +            self.assertEqual(CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"]),
 657 | +                             (None, None))                                 # step A: unavailable, never cleared
 658 | +            ex = PK.exclusion_for(None, m, srcs, {})                       # no model call is made
 659 | +            self.assertEqual((ex["verdict"], ex["measured"]), ("exclude", False))
 660 | +
 661 | +
 662 |  class TestDriverRefuses(unittest.TestCase):
 663 |      def test_the_driver_reads_the_delivered_pins_before_writing_and_refuses_a_bad_one(self):
 664 |          """Audit 2315 C2 (grok, qwen, glm): no hard-coded delivered pins; a pin that cannot be read, has no clip or no
 665 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
It wires WINDOW word records into the ledger build path (orchestrator ruling 2, 22:40 ET Nov 12: "when [ingest ledger]
rows turn sentence-ready, build from the ledger and seal a pin; that is the first FRESH medley"). The integrator's
word-pass worker (branch word-pass, 514dd704) writes the window records.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- clips are verbatim WHOLE sentences of a sentence-ready, word-timed record (L-o 1, L-e);
- CONTEXT INTEGRITY (L-s): every clip is judged inside its source's transcript from >= 90 s before to >= 60 s after;
- no delivered span is used again (L-p).

The worker's contract, as built:
- A window record is transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json in the store: about +-45 s of words
  around one ledger moment, clipped to the video. It holds:
  - words on the YouTube clock;
  - segments from those words, plus transcript_sha256 (the segments sha);
  - words_sha256 = sha256(json.dumps([[word, start, end], ...], ensure_ascii=False));
  - punctuation.still_unpunctuated;
  - window = {start_s, end_s, clock: "youtube", offset_s}.
- A row in moments/word_pass.jsonl is {moment_id, video_id, window_record (relative to the store), record_sha256 (the
  file's sha256), sentence_ready, window, at}. It may also carry "reused"; a failed moment's row has an error and
  window_record null, and is never retried.
- L-s context for a window clip comes from the full-video CAPTION record the ledger mined the moment from (the
  contract): a window holds only +-45 s, and L-s needs 90 s / 60 s.

The files:
1. pipeline/ledger_build.py:
   - word_pass_index(): the last row per moment_id; only sentence_ready rows with a record count.
   - window_source(): every claim checked before use: the path is under transcripts/<vid>/windows/; the file sha256
     is the row's record_sha256; the method; the segments sha; words_sha256; the words spell the segments; the
     YouTube clock; nothing still unpunctuated; the ledger row's span inside the window; the channel;
     sentence_ready. file_head is True only when the window starts at 0.
   - caption_source(): the full-video record whose segments sha is the ledger row's transcript_sha256.
   - build_inputs(): a video with no full-video word record uses the best-ranked row's window record (one per video;
     the video's other rows re-anchor in it or are counted out), with .context_source = the caption record.
2. pipeline/context_integrity.py:
   - caption_parts(): for a window Source, the selection is the window's own words and the context is the caption's
     words by TIME (>= 90 s before, 60 s after, or to the media's edge), because auto captions carry no punctuation.
     No caption record, or a missing time, gives (None, None).
   - context_around(): the same for the exclusion verdict.
   - _window_text() routes window Sources through caption_parts.
3. pipeline/package.py exclusion_for(): takes its context from context_around(). With no context, it returns exclude
   with measured false.
4. tests/package/proof_ledger.py: passes the word-pass index (--word-pass).
5. tests/package/test_ledger_build.py: fixtures built exactly as the worker's make_record, plus tamper cases.

Check, concretely:
(a) Can a window record that is tampered with, or not sentence-ready, reach a moment (file, segments, words, clock,
    punctuation, path)?
(b) Can a window clip be judged for L-s with LESS than its 90 s / 60 s context, or pass when the context is missing?
(c) Is the caption record the one the ledger mined, and can a wrong one be used?
(d) Does anything change for the full-video records path (byte-identical contexts and exclusion prompts)?
(e) Do the tests fail on the defect each one names?

Output:
- Findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
- Only state what you can verify from the diff provided. If uncertain, say so; do not guess.
- End with a verdict line: "SHIP: yes | yes with conditions | no".


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
