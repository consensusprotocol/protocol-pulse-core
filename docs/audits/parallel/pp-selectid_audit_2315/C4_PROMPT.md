# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2315
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 335 s finish=stop usage in 17625 / out 9785 usd~0.200 (upper-bound price)

# Audit — pp-selectid, ROUND 2 (final diff), C3_STEP

Scope: only the three files in the diff. I cannot see `sentence_law.anchor`, `eligibility.Span/Source/sentence_ready`, `moments.judge/record/rank_score`, `package.build/usable`, `transcript_store.segments_sha256`, or the pp-ingest adapter, so anything that depends on their internals is marked as unverifiable from this diff.

## P0

None found. (Conditional — see P1-1.)

## P1

**P1-1. `since` default can read too few lines — the newest delivered pin's `approved_at` is not the same instant as "since the last delivered video" when mining happens after delivery.**
`tests/package/proof_ledger.py:233-234, 304` — the default `since` = `max(approved_at of delivered pins)`. The adapter's contract (stated in the task) returns "lines mined at or after `since` **or** published inside the 72 h window", so a line *mined* after the last delivery but *published* before it is only returned if it falls in the 72 h publish window. That part is fine. The risk is the other direction: a line mined **before** the last delivery, published inside the window, but excluded as "delivered" only by `delivered_ids` — and `delivered_ids` is never passed. `LB.rows()` is called at `proof_ledger.py:322` as `LB.rows(since, now, horizon_h=a.hours)`; the `delivered` parameter defaults to `()` and the clip spans (`delivered`, line 303) are passed only to `PK.build(..., delivered=delivered, ...)` at line 333. So the ledger adapter's own "delivered" exclusion never sees the delivered pins. Whether that is a defect depends on the adapter's semantics (does `best_unused_moments`'s `delivered_ids` mean *delivered moments* or *delivered videos*?), which I cannot verify from this diff. If it means delivered moment/line ids, then: inputs → a ledger line whose moment was already packaged in the 41f29b1f medley, not excluded by the adapter, re-anchored to the same span → duplicate span caught only if `(vid, k0, k1)` collides exactly (line 194); a *different* span from the same already-delivered moment text would slip through as "fresh". Flag: the L-p overlap check in `package.usable` may cover this — unverifiable here. **Concrete scenario if `delivered_ids` is moment-ids:** row L1 delivered in the prior pin; adapter (with `delivered=()`) returns L1 again; `reanchor` yields the same `(vid, k0, k1)` → caught by `seen` (line 194) — but only if the snap lands identically; a one-word-different snap (e.g. after the store's record was re-anchored differently) yields a new span, counted as a new moment, and the L-p overlap check is the only remaining guard. Recommend: pass `delivered` (or the pin moment-ids) into `LB.rows` — one-line change.

**P1-2. `word_source`'s glob+sort can silently prefer a *newer* punctuated record over the one the row was mined from, and the sort key is not total.**
`pipeline/ledger_build.py:103-104` — `sorted(glob(...transcript.whisper_words*.json), key=lambda p: "punct" not in p)`. Two issues: (i) the key is boolean, so all `punct` files tie and all non-punct files tie; ties are broken by glob order, which is filesystem-dependent (Python's `glob` does not sort). With two punctuated variants (the contract's `transcript.whisper_words*.json` allows e.g. `transcript.whisper_words_punct_v2.json`), which one wins is unspecified. (ii) There is no tie-break by recency or by the row's mining provenance. Failure: store holds `transcript.whisper_words_punct.json` (the one the ledger's text was mined against) and `transcript.whisper_words_punct_v2.json` (a later re-transcription); glob returns v2 first; the row's text anchors against v2's words — possibly a different wording → `not_anchored` drop, counted but *wrong* (the row was perfectly good against the record it was mined from). Severity: P1, because the report does name which record was used (`report["word_records"][vid]`, line 188) and the drop is counted, so it is diagnosable, not silent. Fix: sort by `("punct" not in p, -mtime, p)` or by an explicit version key; or better, prefer the record whose `transcript_sha256` matches the row's mined provenance if the ledger carries one (unverifiable whether it does).

**P1-3. `reanchor`'s `SEARCH_PAD_S` narrowing can silently change which occurrence of a repeated phrase is chosen, and the failure mode of a *wrong* hit is not counted.**
`pipeline/ledger_build.py:45-48, 138-140` — the comment says the pad exists so "the window only keeps a phrase said again elsewhere in the video from anchoring", i.e. the pad is what *prevents* a far-away duplicate. But the converse: if the caption clock is off by more than 30 s (the comment itself says "a caption cue starts or ends a few seconds off the words" — a few, but nothing bounds it), the correct occurrence is outside `[t0-30, t1+30]` and either (a) no hit → counted drop (`not_anchored`), or (b) the *wrong* occurrence inside the window is hit → a

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 198 s finish=stop usage in 17328 / out 627 usd~0.102 (upper-bound price)

**Findings (verifiable from diff only):**

P2: tests/package/proof_ledger.py:322  
Call `LB.rows(since, now, horizon_h=a.hours)` supplies no `delivered_ids` (defaults to `()`), even though `delivered_pins()` read the full list at line 303, `rows()` forwards it to the adapter's `best_unused_moments(..., a["delivered"], ...)`, and the driver docstring cites L-p novelty. Concrete failure: supply two overlapping pins as `--delivered`, a ledger row mined after the newest `approved_at` but overlapping an earlier pin's span → adapter returns the row (no `delivered_ids` filter), `build_inputs` accepts it (only intra-run duplicate check on `(vid, k0, k1)`), `PK.build(..., delivered=delivered)` receives it. (Uncertain whether `package.usable` perfectly blocks; only this diff visible.)

P2: pipeline/ledger_build.py:176  
`channels = sorted({str(r.get("channel_id")) for r in rs}); if len(channels) > 1: report["channel_conflict"]...; continue` drops the video but only after `by_vid` grouping. Concrete failure: two rows for same `video_id`, one with `channel_id=123` (int), one with `"123"` (str) → treated as conflict even though identical after `str()`. Test at line 528-531 only exercises distinct strings.

No P0/P1. All cycle-2 fixes (K4 `passed_over` + fallbacks reporting, K5 channel_conflict, K6 required `--delivered` + pre-write refusal + exit 2, apostrophe normalization in SNAP_GUARD, no-sha test, SEARCH_PAD_S doc) are present and exercised by the added tests. (a) Non-whole-sentence clips refused by `reanchor` (SNAP_WORDS guard + `Span(k0,k1)` on `src.sentences`, lines 150-153); non-sentence-ready / sha-broken records refused by `word_source` + `E.sentence_ready` (lines 124, 117) with explicit counts; delivered spans at least reach `PK.build(delivered=...)`. (b) No silent drops—every case (`no_word_record_why`, `not_anchored`, `malformed`, `duplicates`, `channel_conflict`, `fallbacks`) recorded. (c) `since` defaults to newest pin `approved_at` (lines 304, 318) and is passed to adapter; empty ledger allowed with report (test lines 580-584). (d-e) All listed cycle-2 items and named defect tests (negation snap, bad sha, driver refusal before mkdir, punctuated-first ordering, malformed exception→count) match the code and would fail their asserts if the defect were reintroduced.

**SHIP: yes with conditions** (the delivered_ids omission must be confirmed harmless by the unmodified `package.build` / ingest adapter).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 57 s finish=stop usage in 19399 / out 3845 usd~0.116 (upper-bound price)

I’ll verify the claims strictly against the provided diff. I will not assume the behavior of `sentence_law.anchor`, `eligibility.Source`, `moments.judge/record`, `package.build`, or the ingest adapter beyond what the diff shows.

## Findings

### P0 — None found in the provided diff
I could not construct a concrete failure from the diff alone where a non-whole-sentence clip, a non-word-timed moment, an unverified record, or a delivered span is accepted. The code paths that would allow those are not visible in the diff (e.g., `SL.anchor`, `E.sentence_ready`, `M.judge`, `PK.build`), so I cannot verify a P0 from the provided text.

### P1 — `since` default may read too few lines (c)

**File:** `tests/package/proof_ledger.py:304`  
**Code:**
```python
since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
```
where `last` is the newest delivered pin’s `approved_at`.

**Ruling 2 wording:** “best_unused_moments since the last delivered video.”

**Problem:** The adapter contract says it returns “lines mined at or after `since` **or** published inside the 72 h window.” If a ledger row was mined *before* the last delivered pin’s `approved_at` but published within the 72 h window, it is included. But if a row was mined *before* `approved_at` and published *outside* the 72 h window, it is excluded. The question is whether “since the last delivered video” means “since the last delivered video was *approved*” or “since the last delivered video was *rendered/published*.” The diff uses `approved_at`, which is the pin’s approval time, not necessarily the video’s publish time. If a video was published at 10:00 and approved at 14:00, rows mined between 10:00 and 14:00 are excluded by the `since` default, even though they postdate the video’s publication. This could read too few lines.

**Concrete failure scenario:**
- Last delivered pin: published 2026-11-12T10:00:00Z, approved 2026-11-12T14:00:00Z.
- Ledger row: mined 2026-11-12T12:00:00Z, published 2026-11-12T11:00:00Z.
- `since` default = 2026-11-12T14:00:00Z.
- Row is mined before `since` and published outside the 72 h window (if `now` is 2026-11-12T15:00:00Z, the 72 h window starts 2026-11-09T15:00:00Z, so the row *is* inside the window). Wait — the row *is* inside the 72 h window, so it is included. Let me re-examine.

Actually, the adapter returns rows mined at or after `since` **OR** published inside the 72 h window. So a row mined before `since` but published inside the 72 h window is included. The only rows excluded are those mined before `since` AND published outside the 72 h window. If the 72 h window is wide enough, this is unlikely to be a problem. But if a row was published 73 h ago and mined before `since`, it is excluded. Is that correct? Ruling 2 says “since the last delivered video,” which is ambiguous. The diff’s choice is defensible but not clearly correct. I’ll downgrade this to P2.

### P2 — `since` default is ambiguous (c)

**File:** `tests/package/proof_ledger.py:304`

**Issue:** The default `since` is the newest delivered pin’s `approved_at`. Ruling 2 says “since the last delivered video.” It is unclear whether “last delivered video” means the video’s publish time, render time, or approval time. The diff uses `approved_at`, which is the pin’s approval time. If the intent was the video’s publish time, this could read too few or too many lines. The diff does not document this choice.

**Concrete failure scenario:**
- Last delivered pin: published 2026-11-12T10:00:00Z, approved 2026-11-12T14:00:00Z.
- Ledger row: mined 2026-11-12T12:00:00Z, published 2026-11-12T11:00:00Z.
- `since` default = 2026-11-12T14:00:00Z.
- Row is mined before `since` but published inside the 72 h window, so it is included. No failure.
- Ledger row: mined 2026-11-12T12:00:00Z, published 2026-11-10T12:00:00Z (72 h ago).
- `since` default = 2026-11-12T14:00:00Z.
- Row is mined before `since` and published at the edge of the 72 h window. If the adapter’s window is inclusive, it is included; if exclusive, it is excluded. The diff does not specify.

This is a minor ambiguity, not a clear defect.

### P2 — `SNAP_GUARD` may not catch all negations (d)

**File:** `pipeline/ledger_build.py:39-41`
```python
SNAP_GUARD = __import__("re").compile(r"^(not|no|never|none|nobody|nothing|neither|nor|cannot|can't|won't|don't|"
                                      r"doesn't|didn't|isn't|aren't|wasn't|weren't|shouldn't|wouldn't|couldn't|"
                                      r"\w+n't)$|\d", __import__("re").I)
```

**Issue:** The guard catches a fixed list of negations and any word with a digit. It does not catch negations like “hardly,” “scarcely,” “barely,” “rarely,” “seldom,” “infrequently,” “un-” prefixes, or “non-” prefixes. If a snap adds one of these, it could flip or add a claim the ledger never judged.

**Concrete failure scenario:**
- Word record sente

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of the ledger build path, ROUND 2: cycle 3 consensus (synthesis by the pp-selectid session, 23:47 ET Nov 12)

**Run.** Cycle 3 is a fresh review of the final diff after cycles 1 and 2 (C3_STEP.diff, 38,967 bytes; prompt 62,400
bytes; the question is QUESTION_R2.txt). No reviewer raised a P0.
- grok-4.20-0309-reasoning (xAI), 198 s: two P2s. SHIP yes with conditions.
- qwen/qwen3.8-27b (Heimdall, effort none), 57 s: P2s only. "SHIP: no", on a missing video_id crashing the build.
- z-ai/glm-5.3-flash (Heimdall, effort none), 335 s: four P1s and six P2s, plus one open question: does the sha cover
  the words? SHIP yes with conditions.

**Spend:** about $0.42 at the config's upper-bound prices.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K7 | the adapter's delivered_ids stay empty, so L-p rests on package.usable (grok P2, glm P1-1; condition: pass ids, or state that usable's any-overlap check alone carries L-p) | ANSWERED with evidence, and now stated and tested. usable drops ANY moment that overlaps a delivered span of the same video (package.py:96-97: d.start < m.end and m.start < d.end), whatever the pin's age; the driver passes every delivered pin's spans. The live run dropped 2 moments this way. The adapter's delivered_ids are ledger moment ids for the previous 24 h; tonight's pins carry no ledger id, and an overlap check is stricter than an id check. The driver's docstring says so. Test: test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age (a pin from Oct 1; two overlapping spans out, two touching spans in) |
| K8 | a row without video_id crashes build_inputs, and two rows without moment_id share one report key (qwen P2 x2, glm P1-4) | IMPLEMENTED: a row whose moment_id or video_id is not a non-empty string (or that is not an object) is counted in report.malformed. It is keyed by its moment_id, or by "row <i>" when that id is missing or already taken, and it never crashes the build. Test: test_a_row_without_an_id_is_counted_never_a_crash |

## Unique findings, implemented (each verified first)

- **glm (a): the sha does not cover the words.** CONFIRMED: segments_sha256 hashes each segment's [start, end, text]
  only (transcript_store.py:86-89), and S.tokens_from_record reads the clip's words from rec["words"]. The store's
  own reader checks the same thing (transcript_records). Fix in word_source: words_off_segments requires the word
  list to spell the sha-checked segments exactly, in order, with each segment's start and end equal to its first and
  last word's times (1 ms). Measured on the store:
  - all 66 word records (35,697 segments) agree to the ms;
  - word_source over all 57 videos refuses none for this reason (28 are read; 29 are verbatim records that are not
    sentence-ready).
  Test: test_a_record_whose_words_do_not_spell_its_segments_is_never_read (an edited word, a shifted boundary time, an
  added word). Word times inside a segment stay outside the sha; inclu

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_2315/C4_STEP.diff (781 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | new file mode 100644
   3 | index 00000000..7cb5300b
   4 | --- /dev/null
   5 | +++ b/pipeline/ledger_build.py
   6 | @@ -0,0 +1,266 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/ledger_build.py — ORCHESTRATOR 22:40 ruling 2: the medley built from the INGEST LEDGER, the path to the first
   9 | +FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call here (package.build makes those).
  10 | +
  11 | +- rows(): pp-ingest's own adapter, pipeline.ingest.ledger.best_unused_moments, with its exclusions applied: delivered,
  12 | +  opted out, hard flags, altcoin or not about Bitcoin, a speaker change, re-uploads. It runs read-only in its own
  13 | +  interpreter, from the pp-ingest worktree, until the integrator merges it.
  14 | +- READY: a row is packageable only on a sentence-ready WORD record (law L-e). Today that is the store's full-video slot
  15 | +  (transcripts/<vid>/transcript.whisper_words_punct.json, then transcript.whisper_words.json: WORD_RECORDS, in that
  16 | +  order). Its segments sha is checked, and its words must spell those segments exactly (words_off_segments). Window records from
  17 | +  the word-pass worker (the integrator's contract: transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json,
  18 | +  youtube clock, listed in moments/word_pass.jsonl) need their L-s context from the CAPTION record. That is not wired
  19 | +  yet: a row whose video has only a window record counts as waiting for a word record (report.no_word_record, "no
  20 | +  word record in the store") and is not used. No window record exists yet (none in the store at 23:36 ET Nov 12).
  21 | +- RE-ANCHOR: sentence_law.anchor, the sentence law's own text locator, finds the row's TEXT in the word record. The
  22 | +  row's caption-clock times only narrow the search. The span then snaps to that record's WHOLE sentences when at most
  23 | +  SNAP_WORDS words lie outside the anchored text at either edge; otherwise the row is dropped, and why is recorded.
  24 | +  The moment's text becomes the word record's own words, verbatim, the words the render locks on.
  25 | +- RECORD: the miner's own moments.judge() and moments.record(): eligibility on word timing (on_screen_ok). The ledger
  26 | +  row's scores, risks, topics, reason and mining provenance are kept (mined.ledger_moment_id).
  27 | +-> build_inputs(...) = (moments, sources, report).
  28 | +"""
  29 | +import json
  30 | +import os
  31 | +import sys
  32 | +
  33 | +import eligibility as E
  34 | +import moments as M
  35 | +import select_by_id as S
  36 | +import sentence_law as SL
  37 | +import transcript_store as ts
  38 | +
  39 | +SNAP_WORDS = 3            # words of a word-record sentence the anchored text may leave out at either edge
  40 | +SNAP_GUARD = __import__("re").compile(r"^(not|no|never|none|nobody|nothing|neither|nor|cannot|can't|won't|don't|"
  41 | +                                      r"hardly|scarcely|barely|rarely|seldom|"
  42 | +                                      r"doesn't|didn't|isn't|aren't|wasn't|weren't|shouldn't|wouldn't|couldn't|"
  43 | +                                      r"\w+n't)$|\d", __import__("re").I)
  44 | +                          # a word the snap would ADD may not be a negation or carry a digit: it could flip or add a
  45 | +                          # claim the ledger's scores and risks never saw (audit 2315 C1: grok P1, glm P1-1; the
  46 | +                          # near-negations "hardly" ... "seldom": qwen C3)
  47 | +APOSTROPHES = {"\u2019": "'", "\u2018": "'", "\u02bc": "'"}   # a typographic apostrophe is read as ' by the guard
  48 | +SEARCH_PAD_S = 30.0       # the row's caption times narrow the anchor's search to [start - pad, end + pad]. Captions
  49 | +                          # and word records share the full-video clock, and a caption cue starts or ends a few
  50 | +                          # seconds off the words; the window only keeps a phrase said again elsewhere in the video
  51 | +                          # from anchoring. A row the window misses is a counted, named drop.
  52 | +INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
  53 | +MAIN = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")
  54 | +STORE = os.path.join(MAIN, "data", "editorial")
  55 | +WORD_RECORDS = ("transcript.whisper_words_punct.json", "transcript.whisper_words.json")
  56 | +                          # the store's two word-record slots (transcript_store._store: transcript.<method>.json), read
  57 | +                          # in this order: a total order, never the file system's (glm C3 P1-2)
  58 | +
  59 | +
  60 | +_ROWS = """
  61 | +import json, sys
  62 | +from datetime import datetime
  63 | +sys.path.insert(0, sys.argv[1])
  64 | +from pipeline.ingest import ledger as IL
  65 | +a = json.loads(sys.stdin.read())
  66 | +rows, rep = IL.best_unused_moments(a["path"], datetime.fromisoformat(a["since"]), datetime.fromisoformat(a["now"]),
  67 | +                                   a["delivered"], store_root=a["store_root"], horizon_h=a["horizon_h"])
  68 | +sys.stdout.write(json.dumps({"rows": rows, "report": rep}, default=str))
  69 | +"""
  70 | +
  71 | +
  72 | +def rows(since, now, delivered_ids=(), ingest_root=INGEST_ROOT, horizon_h=72, timeout=300):
  73 | +    """pp-ingest's adapter, best_unused_moments, run read-only in its OWN interpreter, from its worktree until the
  74 | +    integrator merges it. Its store guard refuses a process in which another transcript_store was imported first, so
  75 | +    the two never share modules. -> (rows, report). Raises RuntimeError when the adapter FAILS or REFUSES (fail
  76 | +    closed: a failure is never read as an empty ledger). An empty successful read is a real result: no row passes the
  77 | +    ledger's own exclusions, and the report's counts say why."""
  78 | +    import subprocess
  79 | +    args = {"path": os.path.join(ingest_root, "data", "editorial", "moments", "moment_ledger.jsonl"),
  80 | +            "since": since.isoformat(), "now": now.isoformat(), "delivered": list(delivered_ids),
  81 | +            "store_root": os.path.join(ingest_root, "data", "editorial"), "horizon_h": horizon_h}
  82 | +    env = dict(os.environ, PP_SELECTID_PIPELINE=os.path.dirname(os.path.abspath(__file__)))
  83 | +    try:
  84 | +        p = subprocess.run([sys.executable, "-c", _ROWS, ingest_root], input=json.dumps(args), capture_output=True,
  85 | +                           text=True, cwd=ingest_root, env=env, timeout=timeout)
  86 | +    except subprocess.TimeoutExpired:                   # a failure like any other: RuntimeError (glm C2 N-5)
  87 | +        raise RuntimeError(f"the ledger adapter did not answer in {timeout} s") from None
  88 | +    if p.returncode != 0:
  89 | +        raise RuntimeError(f"the ledger adapter failed: {p.stderr.strip()[-400:]}")
  90 | +    try:
  91 | +        out = json.loads(p.stdout)
  92 | +        got, report = out["rows"], out["report"] or {}
  93 | +        if not isinstance(got, list) or not isinstance(report, dict):
  94 | +            raise TypeError("'rows' is not a list or 'report' is not an object")
  95 | +    except (ValueError, KeyError, TypeError) as e:
  96 | +        raise RuntimeError(f"the ledger adapter's answer cannot be read ({type(e).__name__}: {str(e)[:160]})") from None
  97 | +    if report.get("contract"):
  98 | +        raise RuntimeError(f"the ledger adapter refused: {report['contract']}")
  99 | +    return got, report
 100 | +
 101 | +
 102 | +def words_off_segments(rec, tol=0.001):
 103 | +    """None when the record's word list spells its segments exactly, in order (whitespace aside), and every segment
 104 | +    starts at its first word's start and ends at its last word's end (to the ms the segments are rounded to); else
 105 | +    why. segments_sha256 covers the segments only, and the clip is cut from the WORDS (S.tokens_from_record reads
 106 | +    rec["words"]), so this is what ties those words to the sha (glm C3 (a)). The store writes its segments from the
 107 | +    words: all 66 word records (35,697 segments) agree to the ms (measured by 23:44 ET Nov 12). Word times inside a
 108 | +    segment stay outside the sha: that is the store's to close (words in the hash), flagged to the integrator."""
 109 | +    ws = [w for w in (rec.get("words") or []) if isinstance(w, dict) and str(w.get("word") or "").strip()]
 110 | +    if not ws:
 111 | +        return "no words"
 112 | +    k = 0
 113 | +    for i, sg in enumerate(rec.get("segments") or []):
 114 | +        need, got, first = "".join(str(sg.get("text") or "").split()), "", k
 115 | +        if not need:
 116 | +            return f"segment {i} is empty"
 117 | +        while k < len(ws) and len(got) < len(need):
 118 | +            got += "".join(str(ws[k]["word"]).split())
 119 | +            k += 1
 120 | +        if got != need:
 121 | +            return f"segment {i}: the words spell {got[:40]!r}, the segment {need[:40]!r}"
 122 | +        try:
 123 | +            if (abs(float(ws[first]["start"]) - float(sg["start"])) > tol or
 124 | +                    abs(float(ws[k - 1]["end"]) - float(sg["end"])) > tol):
 125 | +                return f"segment {i}: its times are not its words' times"
 126 | +        except (KeyError, TypeError, ValueError):
 127 | +            return f"segment {i}: a word or the segment has no readable time"
 128 | +    if k != len(ws):
 129 | +        return f"{len(ws) - k} word(s) after the last segment"
 130 | +    return None
 131 | +
 132 | +
 133 | +def word_source(row, ctx, store=STORE):
 134 | +    """The video's sentence-ready word record from the store's full-video slot (punctuated first, its segments sha
 135 | +    checked), as an eligibility Source with the row's identity -> (Source, path, passed_over), or (None, None,
 136 | +    passed_over). passed_over names every record read and not used, in reading order, each with why ("<file>: <why>";
 137 | +    "no word record in the store" when there is none). A Source that comes with a non-empty passed_over is a fallback
 138 | +    from the punctuated record, and is visible as one (audit 2315 C2: all three reviewers)."""
 139 | +    vid = row["video_id"]
 140 | +    paths = [p for p in (os.path.join(store, "transcripts", vid, n) for n in WORD_RECORDS) if os.path.exists(p)]
 141 | +    if not paths:
 142 | +        return None, None, ["no word record in the store"]
 143 | +    reg = ctx.channel(row.get("channel_id")) or {}
 144 | +    passed_over = []
 145 | +    for p in paths:
 146 | +        name = os.path.basename(p)
 147 | +        try:
 148 | +            with open(p) as f:
 149 | +                rec = json.load(f)
 150 | +        except (OSError, ValueError):
 151 | +            passed_over.append(f"{name}: cannot be read")
 152 | +            continue
 153 | +        if rec.get("transcript_sha256") != ts.segments_sha256(rec.get("segments") or []):
 154 | +            passed_over.append(f"{name}: its segments do not match its transcript_sha256")
 155 | +            continue
 156 | +        off = words_off_segments(rec)
 157 | +        if off:
 158 | +            passed_over.append(f"{name}: its words do not spell its sha-checked segments ({off})")
 159 | +            continue
 160 | +        timing, toks = S.tokens_from_record(rec)
 161 | +        src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
 162 | +                       row.get("published_at"), rec.get("transcript_sha256"), rec.get("transcript_method"), toks,
 163 | +                       timing=timing, title=row.get("title") or "", file_head=True, vod=True)
 164 | +        if E.sentence_ready(src):
 165 | +            return src, p, passed_over
 166 | +        passed_over.append(f"{name}: not sentence-ready (law L-e)")
 167 | +    return None, None, passed_over
 168 | +
 169 | +
 170 | +def reanchor(row, src):
 171 | +    """The row's TEXT located in the word record and snapped to its whole sentences -> (E.Span, info) or (None, why)."""
 172 | +    def num(x):
 173 | +        try:
 174 | +            return float(x)
 175 | +        except (TypeError, ValueError):
 176 | +            return None                                 # an unreadable time only widens the search (glm C1 P1-9)
 177 | +    t0, t1 = num(row.get("start")), num(row.get("end"))
 178 | +    hit = SL.anchor(src.tokens, row.get("text") or "",
 179 | +                    t0=(t0 - SEARCH_PAD_S) if t0 is not None else None,
 180 | +                    t1=(t1 + SEARCH_PAD_S) if t1 is not None else None)
 181 | +    if hit is None:
 182 | +        return None, (f"the row's text does not anchor in the word record (sentence_law.anchor"
 183 | +                      + (f", searched {t0 - SEARCH_PAD_S:.0f}-{t1 + SEARCH_PAD_S:.0f} s)" if t0 is not None and
 184 | +                         t1 is not None else ")"))
 185 | +    i0, i1, ratio = hit
 186 | +    k0 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i0 <= b), None)
 187 | +    k1 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i1 <= b), None)
 188 | +    if k0 is None or k1 is None:
 189 | +        return None, "the anchored words fall outside the record's sentences"
 190 | +    left, right = i0 - src.sentences[k0][0], src.sentences[k1][1] - i1
 191 | +    if left > SNAP_WORDS or right > SNAP_WORDS:
 192 | +        return None, (f"the anchored text is not whole sentences of the word record ({left} word(s) before it and "
 193 | +                      f"{right} after it inside its edge sentences; at most {SNAP_WORDS})")
 194 | +    added = ["".join(APOSTROPHES.get(c, c) for c in t["word"]).strip(".,!?;:\"'()\u201c\u201d\u2014\u2026")
 195 | +             for t in list(src.tokens[src.sentences[k0][0]:i0]) + list(src.tokens[i1 + 1:src.sentences[k1][1] + 1])]
 196 | +    # a typographic apostrophe reads as ' here (glm C2 N-3; none of the store's 66 word records holds one today)
 197 | +    risky = [w for w in added if SNAP_GUARD.search(w)]
 198 | +    if risky:
 199 | +        return None, f"snapping to whole sentences would add {risky}: a negation or a number the ledger never judged"
 200 | +    sp = E.Span(src, k0, k1)
 201 | +    info = {"anchor_ratio": round(ratio, 3), "snapped_words": [left, right], "sentences": [k0, k1]}
 202 | +    a, b = num(src.tokens[i0].get("start")), num(src.tokens[i1].get("end"))
 203 | +    if None not in (t0, t1, a, b):      # the hit against the row's own caption times: a phrase said twice inside the
 204 | +        info["offset_s"] = [round(a - t0, 2), round(b - t1, 2)]          # window shows here (glm C3 P1-3)
 205 | +    return sp, info
 206 | +
 207 | +
 208 | +def build_inputs(rows, ctx, store=STORE, log=print):
 209 | +    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). Rows on a video with no sentence-
 210 | +    ready word record, rows whose text does not re-anchor on whole sentences, and duplicates of one span are dropped,
 211 | +    each counted with why."""
 212 | +    report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "no_word_record_videos": {},
 213 | +              "fallbacks": {},
 214 | +              "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "moments": 0, "videos": 0,
 215 | +              "word_records": {}}
 216 | +    def malformed(i, r, why):                     # counted under a key no other row can take (qwen C3, glm C3 P1-4)
 217 | +        mid = r.get("moment_id") if isinstance(r, dict) else None
 218 | +        report["malformed"][mid if isinstance(mid, str) and mid and mid not in report["malformed"] else f"row {i}"] = why
 219 | +
 220 | +    by_vid = {}
 221 | +    for i, r in enumerate(rows):
 222 | +        if not (isinstance(r, dict) and all(isinstance(r.get(k), str) and r.get(k) for k in ("moment_id", "video_id"))):
 223 | +            malformed(i, r, "no moment_id or video_id")
 224 | +            continue
 225 | +        by_vid.setdefault(r["video_id"], []).append((i, r))
 226 | +    moments, sources, seen = [], {}, set()
 227 | +    for vid, irs in by_vid.items():
 228 | +        rs = [r for _, r in irs]
 229 | +        channels = sorted({str(r.get("channel_id")) for r in rs})
 230 | +        if len(channels) > 1:       # one uploader per video, checked, not assumed (audit 2315 C2: qwen P1, glm P1)
 231 | +            report["channel_conflict"][vid] = {"rows": len(rs), "channel_ids": channels}
 232 | +            continue
 233 | +        src, path, passed_over = word_source(rs[0], ctx, store)
 234 | +        if src is None:
 235 | +            why = "; ".join(passed_over)
 236 | +            report["no_word_record"] += len(rs)
 237 | +            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 238 | +            report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 239 | +            continue
 240 | +        if passed_over:
 241 | +            report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
 242 | +        report["word_records"][vid] = os.path.relpath(path, store)        # read; whether a moment came of it: moments
 243 | +        for i, r in irs:
 244 | +            sp, info = reanchor(r, src)
 245 | +            if sp is None:
 246 | +                report["not_anchored"][r["moment_id"]] = info
 247 | +                continue
 248 | +            if (vid, sp.k0, sp.k1) in seen:
 249 | +                report["duplicates"] += 1
 250 | +                continue
 251 | +            try:
 252 | +                m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
 253 | +                     "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
 254 | +                     "reason": r.get("reason") or ""}
 255 | +                mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 256 | +                             ledger_text=r.get("text"))
 257 | +                rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
 258 | +                rec["rank_score"] = M.rank_score(rec)
 259 | +            except (KeyError, TypeError, ValueError) as e:     # counted, never a crash (glm C1 P1-8)
 260 | +                malformed(i, r, f"{type(e).__name__}: {str(e)[:120]}")
 261 | +                continue
 262 | +            seen.add((vid, sp.k0, sp.k1))
 263 | +            moments.append(rec)
 264 | +            sources[vid] = src
 265 | +    report["moments"], report["videos"] = len(moments), len(sources)
 266 | +    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} word records; "
 267 | +        f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
 268 | +        f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
 269 | +        f"{len(report['channel_conflict'])} video(s) name more than one channel, "
 270 | +        f"{len(report['fallbacks'])} read from a fallback record")
 271 | +    moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
 272 | +    return moments, sources, report
 273 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 274 | new file mode 100644
 275 | index 00000000..e574a0ad
 276 | --- /dev/null
 277 | +++ b/tests/package/proof_ledger.py
 278 | @@ -0,0 +1,145 @@
 279 | +#!/usr/bin/env python3
 280 | +"""ORCHESTRATOR 22:40 ruling 2: build the medley from the INGEST LEDGER and seal a pin.
 281 | +
 282 | +- The rows are pp-ingest's adapter (best_unused_moments), read-only.
 283 | +- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py).
 284 | +- "now" is the RENDER clock (ruling 1): L-v 3 and currency are judged against tonight, not against a universe snapshot.
 285 | +- Novelty (L-p): every clip span of the pins already delivered (--delivered, required; tonight: the 37c5b5f5 review,
 286 | +  run 165629, and the 41f29b1f medley) is passed to package.usable as delivered. usable drops ANY moment that overlaps
 287 | +  a delivered span of the same video, whatever the pin's age, and that check alone carries L-p here. The adapter's
 288 | +  delivered_ids (ledger moment ids, previous 24 h) stay empty: the delivered pins carry no ledger moment id, and an
 289 | +  overlap check is stricter than an id check (audit 2315 C3 K7: grok, glm).
 290 | +- "since": ruling 2's words are "best_unused_moments since the last delivered video". The default is the newest
 291 | +  delivered pin's approved_at: a line mined after the last delivered package was sealed cannot be in it. --hours is
 292 | +  the adapter's publish window. The pins are read BEFORE anything is written; a missing or broken pin, or a pin with
 293 | +  no clip or no zoned approved_at, refuses the run (exit 2) with why (audit 2315 C2: grok, qwen, glm).
 294 | +- The same legs, ledger and meters as proof_ly.py: Heimdall writes, xAI judges, scribe_v1 is the second recogniser.
 295 | +  Writer calls have ruling 5's deadline; the budget is ruling 5's.
 296 | +Writes tests/package/proof/ledger_<UTC stamp, to the second>/ (a run never writes into an existing one): inputs.json,
 297 | +package.json, package.log, step_a.json and, on a package, MOMENTS_PIN_LEDGER.json.
 298 | +
 299 | +Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since ISO] [--hours 72]
 300 | +  tonight: --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json \\
 301 | +                       tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json
 302 | +"""
 303 | +import argparse
 304 | +import json
 305 | +import os
 306 | +import sys
 307 | +import time
 308 | +from datetime import datetime, timezone
 309 | +
 310 | +HERE = os.path.dirname(os.path.abspath(__file__))
 311 | +REPO = os.path.dirname(os.path.dirname(HERE))
 312 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 313 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 314 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 315 | +sys.path.insert(0, HERE)
 316 | +import eligibility as E  # noqa: E402
 317 | +import ledger_build as LB  # noqa: E402
 318 | +import moments as M  # noqa: E402
 319 | +import package as PK  # noqa: E402
 320 | +import package_pin  # noqa: E402
 321 | +import proof_ly as PL  # noqa: E402
 322 | +import proof_saved_runs as PS  # noqa: E402
 323 | +import providers as P  # noqa: E402
 324 | +
 325 | +def delivered_pins(paths):
 326 | +    """The pins already delivered -> (every clip span {video_id, start, end, pin} for package.usable's overlap check,
 327 | +    the newest approved_at, [{path, story_id, approved_at, clips}]). Raises ValueError (or OSError / KeyError /
 328 | +    TypeError) on a pin that cannot be read, has no clip, or has no zoned approved_at: never a partial delivered set."""
 329 | +    if not paths:
 330 | +        raise ValueError("no delivered pin named")
 331 | +    spans, newest, pins = [], None, []
 332 | +    for p in paths:
 333 | +        try:
 334 | +            with open(p) as f:
 335 | +                pin = json.load(f)
 336 | +            at = datetime.fromisoformat(str(pin["approved_at"]).replace("Z", "+00:00"))
 337 | +            if at.tzinfo is None:
 338 | +                raise ValueError("approved_at has no time zone")
 339 | +            segs = pin["segments"]
 340 | +            if not isinstance(segs, list) or not segs:
 341 | +                raise ValueError("no clip")
 342 | +            spans += [{"video_id": str(s["video_id"]), "start": float(s["start"]), "end": float(s["end"]),
 343 | +                       "pin": pin["story_id"]} for s in segs]
 344 | +            pins.append({"path": os.path.relpath(os.path.abspath(p), REPO), "story_id": pin["story_id"],
 345 | +                         "approved_at": at.isoformat(), "clips": len(segs)})
 346 | +        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:       # which pin (glm C3 P2-3)
 347 | +            raise ValueError(f"{p}: {type(e).__name__}: {e}") from None
 348 | +        newest = at if newest is None or at > newest else newest
 349 | +    return spans, newest, pins
 350 | +
 351 | +
 352 | +def main(argv=None):
 353 | +    ap = argparse.ArgumentParser()
 354 | +    ap.add_argument("--delivered", nargs="+", required=True, metavar="PIN",
 355 | +                    help="every pin already delivered: their clip spans are out (L-p), and 'since' defaults to the "
 356 | +                         "newest one's approved_at")
 357 | +    ap.add_argument("--since", help="ISO time with a zone; default: the newest delivered pin's approved_at")
 358 | +    ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
 359 | +    ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 360 | +    a = ap.parse_args(argv)
 361 | +    now = datetime.now(timezone.utc)
 362 | +    try:                                                 # read before anything is written (glm C2 N-4)
 363 | +        delivered, last, pins = delivered_pins(a.delivered)
 364 | +        since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
 365 | +        if since.tzinfo is None:
 366 | +            raise ValueError("--since has no time zone")
 367 | +        if since > now:
 368 | +            raise ValueError(f"since {since.isoformat()} is after now")
 369 | +    except (OSError, ValueError, KeyError, TypeError) as e:
 370 | +        print(f"REFUSED: the delivered pins or 'since' cannot be read ({type(e).__name__}: {e})", file=sys.stderr)
 371 | +        return 2
 372 | +    out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M%S')}")
 373 | +    try:
 374 | +        os.makedirs(out_dir)                     # never into an earlier run's evidence (glm C3 P2-1)
 375 | +    except FileExistsError:
 376 | +        print(f"REFUSED: {out_dir} exists", file=sys.stderr)
 377 | +        return 2
 378 | +    logf = open(os.path.join(out_dir, "package.log"), "a")
 379 | +    say = lambda s: (print(s, flush=True), logf.write(s + "\n"), logf.flush())
 380 | +    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
 381 | +    say(f"=== {time.strftime('%H:%M:%S %Z')} LEDGER medley build, code {PL.code_sha()}, now (render clock) "
 382 | +        f"{now.isoformat(timespec='seconds')}, since {since.isoformat(timespec='seconds')} "
 383 | +        f"({'--since' if a.since else 'the newest delivered pin'}), publish window {a.hours} h")
 384 | +    say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
 385 | +        f"{len(delivered)} clip spans out")
 386 | +    rows, rep = LB.rows(since, now, horizon_h=a.hours)
 387 | +    say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 388 | +    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say)
 389 | +    with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 390 | +        json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 391 | +                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 392 | +                  f, indent=1, default=str)
 393 | +    router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 394 | +                      chains=PL.chains())
 395 | +    own, used = PL.meter(router), PL.reply_meter(router)
 396 | +    t0 = time.time()
 397 | +    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 398 | +                   work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 399 | +                   spend=lambda: (own["est"], own["best"]))
 400 | +    res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 401 | +               full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 402 | +               since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 403 | +    if res["package"]:
 404 | +        try:
 405 | +            path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 406 | +                                              name="MOMENTS_PIN_LEDGER.json")
 407 | +            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 408 | +                          "package_sha256": pin["moments_package"]["package_sha256"]}
 409 | +            say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known) "
 410 | +                f"pin {path}")
 411 | +        except package_pin.PinRefused as e:
 412 | +            res["pin_refused"] = str(e)
 413 | +            say(f"PIN REFUSED: {e}")
 414 | +    else:
 415 | +        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 416 | +    with open(os.path.join(out_dir, "package.json"), "w") as f:
 417 | +        json.dump(res, f, indent=1, default=str)
 418 | +    logf.close()
 419 | +    return 0
 420 | +
 421 | +
 422 | +if __name__ == "__main__":
 423 | +    sys.exit(main())
 424 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 425 | new file mode 100644
 426 | index 00000000..777f2434
 427 | --- /dev/null
 428 | +++ b/tests/package/test_ledger_build.py
 429 | @@ -0,0 +1,351 @@
 430 | +#!/usr/bin/env python3
 431 | +"""pipeline/ledger_build.py (ORCHESTRATOR 22:40 ruling 2): the medley built from the ingest ledger. Offline:
 432 | +- re-anchoring a ledger row's TEXT in a word record and snapping it to that record's whole sentences;
 433 | +- reading the store's word record (its sha checked, sentence-ready only);
 434 | +- turning rows into the packager's moments (counted drops, no duplicate spans);
 435 | +- the adapter's failures are raised, never read as an empty ledger."""
 436 | +import io
 437 | +import json
 438 | +import os
 439 | +import sys
 440 | +import tempfile
 441 | +import unittest
 442 | +from unittest import mock
 443 | +
 444 | +HERE = os.path.dirname(os.path.abspath(__file__))
 445 | +REPO = os.path.dirname(os.path.dirname(HERE))
 446 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 447 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 448 | +import eligibility as E  # noqa: E402
 449 | +import ledger_build as LB  # noqa: E402
 450 | +import transcript_store as ts  # noqa: E402
 451 | +from test_eligibility import NOW, REG, source  # noqa: E402
 452 | +
 453 | +SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settling a payment.",
 454 | +         "That is the whole design and it works every day.", "Bitcoin does not ask for permission.",
 455 | +         "In 2009 Bitcoin started as a quiet experiment."]
 456 | +
 457 | +
 458 | +def row(text, start=None, end=None, mid="L1", vid="vidA"):
 459 | +    return {"moment_id": mid, "video_id": vid, "channel_id": "UCdd", "channel_name": "DataDash", "text": text,
 460 | +            "start": start, "end": end, "published_at": NOW.isoformat(), "title": "t",
 461 | +            "scores": {"contempt_outrage": 0, "hook_first_2s": 3, "quotable": 3, "stakes": 3, "stance": 3,
 462 | +                       "stands_alone": 4, "surprising_fact": 2},
 463 | +            "risk": [], "topics": [], "reason": "r", "names_person": False,
 464 | +            "mined": {"by": "qwen/qwen3.8-27b@heimdall_qwen27b", "at": NOW.isoformat()}}
 465 | +
 466 | +
 467 | +class TestReanchor(unittest.TestCase):
 468 | +    def setUp(self):
 469 | +        self.src = source(SENTS)
 470 | +
 471 | +    def test_whole_sentences_anchor_exactly(self):
 472 | +        sp, info = LB.reanchor(row(SENTS[1] + " " + SENTS[2]), self.src)
 473 | +        self.assertEqual((sp.k0, sp.k1), (1, 2))
 474 | +        self.assertEqual(info["snapped_words"], [0, 0])
 475 | +        self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words
 476 | +
 477 | +    def test_a_caption_text_snaps_to_the_records_whole_sentences_within_the_limit(self):
 478 | +        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short: snaps
 479 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((0, 0), [1, 0]))
 480 | +        sp, info = LB.reanchor(row("whole design and it works every day."), self.src)  # exactly 3 words: snaps
 481 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [3, 0]))
 482 | +        sp, why = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused
 483 | +        self.assertIsNone(sp)
 484 | +        self.assertIn("not whole sentences", why)
 485 | +
 486 | +    def test_a_snap_never_adds_a_negation_or_a_number(self):
 487 | +        """Audit 2315 C1 (grok P1, glm P1-1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin' flips the
 488 | +        claim the ledger scored; '... started as a quiet experiment' snapped to 'In 2009 ...' adds a number."""
 489 | +        for text, word in (("can stop Bitcoin from settling a payment.", "Nobody"),
 490 | +                           ("Bitcoin started as a quiet experiment.", "2009")):
 491 | +            sp, why = LB.reanchor(row(text), self.src)
 492 | +            self.assertIsNone(sp, text)
 493 | +            self.assertIn(word, why)
 494 | +
 495 | +    def test_a_snap_never_adds_a_near_negation(self):
 496 | +        """qwen C3: 'Hardly anyone can stop Bitcoin' flips 'anyone can stop Bitcoin'."""
 497 | +        for word in ("Hardly", "Scarcely", "Barely", "Rarely", "Seldom"):
 498 | +            src = source([f"{word} anyone can stop Bitcoin from settling a payment.", "That is the plan."])
 499 | +            sp, why = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
 500 | +            self.assertIsNone(sp, word)
 501 | +            self.assertIn(word, why)
 502 | +
 503 | +    def test_the_hit_is_measured_against_the_rows_own_caption_times(self):
 504 | +        """glm C3 P1-3: a phrase said twice inside the search window would anchor on the earliest longest match; the
 505 | +        offset of the hit from the row's caption times is recorded, so such a hit is visible."""
 506 | +        a, b = self.src.sentences[1]
 507 | +        t0, t1 = self.src.tokens[a]["start"], self.src.tokens[b]["end"]
 508 | +        sp, info = LB.reanchor(row(SENTS[1], start=t0 + 2.0, end=t1 - 1.0), self.src)
 509 | +        self.assertEqual(info["offset_s"], [-2.0, 1.0])
 510 | +        self.assertNotIn("offset_s", LB.reanchor(row(SENTS[1]), self.src)[1])    # no caption times: nothing measured
 511 | +
 512 | +    def test_a_typographic_apostrophe_does_not_hide_a_negation(self):
 513 | +        """glm C2 N-3: 'Don\u2019t' (U+2019) is the negation 'Don't' to the guard."""
 514 | +        for apostrophe in ("\u2019", "'"):
 515 | +            src = source([f"Don{apostrophe}t sell your Bitcoin to anyone today.", "That is the plan."])
 516 | +            sp, why = LB.reanchor(row("sell your Bitcoin to anyone today."), src)
 517 | +            self.assertIsNone(sp, apostrophe)
 518 | +            self.assertIn("negation", why)
 519 | +
 520 | +    def test_text_that_is_not_whole_sentences_or_not_there_is_dropped_with_why(self):
 521 | +        sp, why = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
 522 | +        self.assertIsNone(sp)
 523 | +        self.assertIn("not whole sentences", why)
 524 | +        sp, why = LB.reanchor(row("Ethereum is a world computer for everyone."), self.src)
 525 | +        self.assertIsNone(sp)
 526 | +        self.assertIn("does not anchor", why)
 527 | +
 528 | +
 529 | +class TestWordSourceAndInputs(unittest.TestCase):
 530 | +    def store_with(self, d, vid, sentences, break_sha=False, method="whisper_words_punct", no_sha=False):
 531 | +        src = source(sentences, vid=vid, method=method)
 532 | +        segs = [{"start": src.tokens[a]["start"], "end": src.tokens[b]["end"],
 533 | +                 "text": E.spoken(src.tokens[a:b + 1]),
 534 | +                 "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens[a:b + 1]]}
 535 | +                for a, b in src.sentences]
 536 | +        rec = {"segments": segs, "transcript_method": method, "video_id": vid,                     # the store's word
 537 | +               "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens]}  # record shape
 538 | +        if not no_sha:
 539 | +            rec["transcript_sha256"] = "x" * 64 if break_sha else ts.segments_sha256(segs)
 540 | +        os.makedirs(os.path.join(d, "transcripts", vid), exist_ok=True)
 541 | +        with open(os.path.join(d, "transcripts", vid, f"transcript.{method}.json"), "w") as f:
 542 | +            json.dump(rec, f)
 543 | +        return src
 544 | +
 545 | +    def test_a_record_whose_sha_does_not_match_its_segments_is_never_read(self):
 546 | +        ctx = E.Context(NOW, REG)
 547 | +        with tempfile.TemporaryDirectory() as d:
 548 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d), (None, None, ["no word record in the store"]))
 549 | +            self.store_with(d, "vidA", SENTS, break_sha=True)
 550 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d),
 551 | +                             (None, None, ["transcript.whisper_words_punct.json: its segments do not match its "
 552 | +                                           "transcript_sha256"]))
 553 | +            self.store_with(d, "vidA", SENTS, no_sha=True)                      # glm C2: no sha at all is no match
 554 | +            self.assertIsNone(LB.word_source(row(SENTS[0]), ctx, d)[0])
 555 | +            self.store_with(d, "vidA", SENTS)
 556 | +            src, path, passed_over = LB.word_source(row(SENTS[0]), ctx, d)
 557 | +            self.assertIsNotNone(src)
 558 | +            self.assertEqual((src.timing, passed_over), ("word", []))
 559 | +            p = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
 560 | +            with open(p) as f:                             # glm C1 P2-10: a segment edited AFTER its sha was taken
 561 | +                rec = json.load(f)
 562 | +            rec["segments"][1]["text"] = "Somebody can stop Bitcoin from settling a payment."
 563 | +            with open(p, "w") as f:
 564 | +                json.dump(rec, f)
 565 | +            self.assertIsNone(LB.word_source(row(SENTS[0]), ctx, d)[0])
 566 | +
 567 | +    def test_a_record_whose_words_do_not_spell_its_segments_is_never_read(self):
 568 | +        """glm C3 (a): segments_sha256 covers the segments only, and the clip is cut from rec["words"]. A word list
 569 | +        edited after the sha (text, or a segment's first or last word's time) is never read."""
 570 | +        ctx = E.Context(NOW, REG)
 571 | +        p = None
 572 | +        for edit in ("text", "time", "extra"):
 573 | +            with tempfile.TemporaryDirectory() as d:
 574 | +                self.store_with(d, "vidA", SENTS)
 575 | +                p = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
 576 | +                self.assertIsNotNone(LB.word_source(row(SENTS[0]), ctx, d)[0])           # intact: read
 577 | +                with open(p) as f:
 578 | +                    rec = json.load(f)
 579 | +                w = rec["words"][len(SENTS[0].split()) + 1]                              # "can", in sentence 1
 580 | +                if edit == "text":
 581 | +                    w["word"] = "cannot"                                                 # the claim flips
 582 | +                elif edit == "time":
 583 | +                    rec["words"][len(SENTS[0].split())]["start"] += 0.5                  # sentence 1's first word
 584 | +                else:
 585 | +                    rec["words"].append({"word": "really.", "start": 99.0, "end": 99.4})
 586 | +                with open(p, "w") as f:
 587 | +                    json.dump(rec, f)
 588 | +                src, path, passed_over = LB.word_source(row(SENTS[0]), ctx, d)
 589 | +                self.assertIsNone(src, edit)
 590 | +                self.assertIn("do not spell its sha-checked segments", passed_over[0])
 591 | +
 592 | +    def test_only_the_stores_two_word_record_slots_are_read_in_a_fixed_order(self):
 593 | +        """glm C3 P1-2: the order is total (punctuated, then verbatim), never the file system's; another name is no
 594 | +        slot of the store's."""
 595 | +        ctx = E.Context(NOW, REG)
 596 | +        with tempfile.TemporaryDirectory() as d:
 597 | +            self.store_with(d, "vidA", SENTS)
 598 | +            os.rename(os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json"),
 599 | +                      os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct_v2.json"))
 600 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d), (None, None, ["no word record in the store"]))
 601 | +        self.assertEqual(LB.WORD_RECORDS, ("transcript.whisper_words_punct.json", "transcript.whisper_words.json"))
 602 | +
 603 | +    def test_the_punctuated_record_is_read_first(self):
 604 | +        """qwen C1 P0-1 / glm C1 P0-2: "punct" sorts first (key False < True); the verbatim record only as a fallback."""
 605 | +        ctx = E.Context(NOW, REG)
 606 | +        with tempfile.TemporaryDirectory() as d:
 607 | +            self.store_with(d, "vidA", SENTS)                                   # transcript.whisper_words_punct.json
 608 | +            punct = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
 609 | +            plain = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words.json")
 610 | +            import shutil
 611 | +            shutil.copy(punct, plain)                                           # both valid, both sentence-ready
 612 | +            self.assertTrue(LB.word_source(row(SENTS[0]), ctx, d)[1].endswith("transcript.whisper_words_punct.json"))
 613 | +            os.remove(punct)
 614 | +            self.assertTrue(LB.word_source(row(SENTS[0]), ctx, d)[1].endswith("transcript.whisper_words.json"))
 615 | +
 616 | +    def test_every_record_passed_over_is_named_and_a_fallback_shows(self):
 617 | +        """Audit 2315 C2 (grok, qwen, glm): the reason was the LAST failure only, and a punctuated record rejected
 618 | +        before a verbatim one was used left no trace."""
 619 | +        ctx = E.Context(NOW, REG)
 620 | +        unpunctuated = [" ".join(["bitcoin moves when the market moves"] * 12)]   # 72 words, no stop: not ready
 621 | +        self.assertFalse(E.sentence_ready(source(unpunctuated, vid="vidA", method="whisper_words")))
 622 | +        with tempfile.TemporaryDirectory() as d:
 623 | +            self.store_with(d, "vidA", SENTS, break_sha=True)
 624 | +            self.store_with(d, "vidA", unpunctuated, method="whisper_words")
 625 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d)[2],
 626 | +                             ["transcript.whisper_words_punct.json: its segments do not match its transcript_sha256",
 627 | +                              "transcript.whisper_words.json: not sentence-ready (law L-e)"])
 628 | +            ms, _, rep = LB.build_inputs([row(SENTS[0])], ctx, d, log=lambda s: None)
 629 | +            self.assertEqual(ms, [])
 630 | +            self.assertEqual(rep["no_word_record_why"],
 631 | +                             {"transcript.whisper_words_punct.json: its segments do not match its transcript_sha256; "
 632 | +                              "transcript.whisper_words.json: not sentence-ready (law L-e)": 1})
 633 | +            self.store_with(d, "vidA", SENTS, method="whisper_words")           # a verbatim record that IS ready
 634 | +            ms, _, rep = LB.build_inputs([row(SENTS[0])], ctx, d, log=lambda s: None)
 635 | +            self.assertEqual(len(ms), 1)
 636 | +            self.assertEqual(rep["fallbacks"], {"vidA": {
 637 | +                "used": "transcript.whisper_words.json",
 638 | +                "passed_over": ["transcript.whisper_words_punct.json: its segments do not match its transcript_sha256"]}})
 639 | +
 640 | +    def test_a_video_whose_rows_name_two_channels_is_dropped_whole(self):
 641 | +        """Audit 2315 C2 (qwen P1, glm P1): one uploader per video is checked, never taken from the first row."""
 642 | +        ctx = E.Context(NOW, REG)
 643 | +        with tempfile.TemporaryDirectory() as d:
 644 | +            self.store_with(d, "vidA", SENTS)
 645 | +            other = dict(row(SENTS[2], mid="L2"), channel_id="UCother")
 646 | +            ms, _, rep = LB.build_inputs([row(SENTS[0], mid="L1"), other], ctx, d, log=lambda s: None)
 647 | +            self.assertEqual(ms, [])
 648 | +            self.assertEqual(rep["channel_conflict"], {"vidA": {"rows": 2, "channel_ids": ["UCdd", "UCother"]}})
 649 | +
 650 | +    def test_a_row_without_an_id_is_counted_never_a_crash(self):
 651 | +        """qwen C3, glm C3 P1-4: a row without video_id crashed the grouping; two rows without moment_id took one key."""
 652 | +        ctx = E.Context(NOW, REG)
 653 | +        with tempfile.TemporaryDirectory() as d:
 654 | +            self.store_with(d, "vidA", SENTS)
 655 | +            rows = [row(SENTS[0], mid="L1"), {k: v for k, v in row(SENTS[1], mid="L2").items() if k != "video_id"},
 656 | +                    {k: v for k, v in row(SENTS[2]).items() if k != "moment_id"},
 657 | +                    {k: v for k, v in row(SENTS[3]).items() if k != "moment_id"}, "not a row"]
 658 | +            ms, _, rep = LB.build_inputs(rows, ctx, d, log=lambda s: None)
 659 | +            self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["L1"])
 660 | +            self.assertEqual(sorted(rep["malformed"]), ["L2", "row 2", "row 3", "row 4"])
 661 | +            ms, _, rep = LB.build_inputs([row(SENTS[0], vid="vidZ")], ctx, d, log=lambda s: None)
 662 | +            self.assertEqual(rep["no_word_record_videos"], {"vidZ": {"rows": 1, "why": "no word record in the store"}})
 663 | +
 664 | +    def test_rows_become_the_packagers_moments_with_every_drop_counted(self):
 665 | +        ctx = E.Context(NOW, REG)
 666 | +        with tempfile.TemporaryDirectory() as d:
 667 | +            self.store_with(d, "vidA", SENTS)
 668 | +            rows = [row(SENTS[0], mid="L1"), row(SENTS[0], mid="L2"),               # the same span twice
 669 | +                    row("Ethereum is a world computer for everyone.", mid="L3"),  # does not anchor
 670 | +                    row(SENTS[0], mid="L4", vid="vidZ"),                            # no word record for vidZ
 671 | +                    {k: v for k, v in row(SENTS[3], mid="L5").items() if k != "scores"}]   # malformed: counted
 672 | +            ms, srcs, rep = LB.build_inputs(rows, ctx, d, log=lambda s: None)
 673 | +            self.assertEqual((rep["moments"], rep["duplicates"], rep["no_word_record"]), (1, 1, 1))
 674 | +            self.assertEqual(list(rep["not_anchored"]), ["L3"])
 675 | +            self.assertEqual(list(rep["malformed"]), ["L5"])                   # glm C1 P1-8: never a crash
 676 | +            m = ms[0]
 677 | +            self.assertEqual(m["mined"]["ledger_moment_id"], "L1")
 678 | +            self.assertEqual(m["scores"], rows[0]["scores"])                  # the ledger's judgment kept (glm P2-6)
 679 | +            self.assertEqual(m["text"], SENTS[0])
 680 | +            self.assertEqual(m["timing"], "word")
 681 | +            self.assertIn("rank_score", m)
 682 | +            self.assertEqual(set(srcs), {"vidA"})
 683 | +
 684 | +
 685 | +class TestAdapter(unittest.TestCase):
 686 | +    def test_a_failing_or_refusing_adapter_raises_never_an_empty_ledger(self):
 687 | +        from datetime import timedelta
 688 | +        fail = mock.Mock(returncode=1, stderr="Traceback ... boom", stdout="")
 689 | +        with mock.patch("subprocess.run", return_value=fail):
 690 | +            with self.assertRaises(RuntimeError):
 691 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 692 | +        refused = mock.Mock(returncode=0, stderr="", stdout=json.dumps(
 693 | +            {"rows": [], "report": {"contract": "unavailable: StoreGuard"}}))
 694 | +        with mock.patch("subprocess.run", return_value=refused):
 695 | +            with self.assertRaises(RuntimeError) as cm:
 696 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 697 | +            self.assertIn("refused", str(cm.exception))
 698 | +        ok = mock.Mock(returncode=0, stderr="", stdout=json.dumps({"rows": [{"moment_id": "x"}], "report": {}}))
 699 | +        with mock.patch("subprocess.run", return_value=ok):
 700 | +            self.assertEqual(LB.rows(NOW - timedelta(hours=72), NOW)[0], [{"moment_id": "x"}])
 701 | +        import subprocess                                                    # glm C2 N-5: every failure is RuntimeError
 702 | +        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("python3", 300)):
 703 | +            with self.assertRaises(RuntimeError) as cm:
 704 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 705 | +            self.assertIn("did not answer", str(cm.exception))
 706 | +        for stdout in ("", "not json", "[]", json.dumps({"rows": {}, "report": {}}), json.dumps({"report": {}})):
 707 | +            with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0, stderr="", stdout=stdout)):
 708 | +                with self.assertRaises(RuntimeError, msg=stdout) as cm:
 709 | +                    LB.rows(NOW - timedelta(hours=72), NOW)
 710 | +                self.assertIn("cannot be read", str(cm.exception))
 711 | +        empty = mock.Mock(returncode=0, stderr="", stdout=json.dumps(       # grok C1 P0 (reframed): a real empty read
 712 | +            {"rows": [], "report": {"excluded": {"delivered in the previous 24 h": 3}}}))
 713 | +        with mock.patch("subprocess.run", return_value=empty):
 714 | +            rows, rep = LB.rows(NOW - timedelta(hours=72), NOW)
 715 | +            self.assertEqual((rows, rep["excluded"]), ([], {"delivered in the previous 24 h": 3}))
 716 | +
 717 | +
 718 | +class TestDriverRefuses(unittest.TestCase):
 719 | +    def test_the_driver_reads_the_delivered_pins_before_writing_and_refuses_a_bad_one(self):
 720 | +        """Audit 2315 C2 (grok, qwen, glm): no hard-coded delivered pins; a pin that cannot be read, has no clip or no
 721 | +        zoned approved_at refuses the run (exit 2) before any proof dir exists; 'since' defaults to the newest
 722 | +        delivered pin's approved_at (ruling 2: "best_unused_moments since the last delivered video")."""
 723 | +        sys.path.insert(0, HERE)
 724 | +        import proof_ledger as PLG
 725 | +        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 726 | +                                                                                 "MOMENTS_PIN_LY.json")]
 727 | +        spans, newest, info = PLG.delivered_pins(pins)
 728 | +        self.assertEqual(newest.isoformat(), "2026-11-13T03:01:09+00:00")              # the 41f29b1f medley
 729 | +        self.assertEqual(len(spans), sum(i["clips"] for i in info))
 730 | +        proof = os.path.join(HERE, "proof")
 731 | +        before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_"))
 732 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()):
 733 | +            with open(pins[1]) as f:
 734 | +                pin = json.load(f)
 735 | +            for name, bad in (("naive.json", dict(pin, approved_at="2026-11-13T03:01:09")),
 736 | +                              ("empty.json", dict(pin, segments=[]))):
 737 | +                with open(os.path.join(d, name), "w") as f:
 738 | +                    json.dump(bad, f)
 739 | +            for argv in (["--delivered", os.path.join(d, "missing.json")],
 740 | +                         ["--delivered", os.path.join(d, "naive.json")],
 741 | +                         ["--delivered", os.path.join(d, "empty.json")],
 742 | +                         ["--delivered", *pins, "--since", "2099-01-01T00:00:00+00:00"],
 743 | +                         ["--delivered", *pins, "--since", "2026-11-13T03:01:09"]):
 744 | +                self.assertEqual(PLG.main(argv), 2, argv)
 745 | +            with self.assertRaises(SystemExit):
 746 | +                PLG.main([])                                                            # --delivered is required
 747 | +            nostart = dict(pin, segments=[{k: v for k, v in pin["segments"][0].items() if k != "start"}])
 748 | +            with open(os.path.join(d, "nostart.json"), "w") as f:
 749 | +                json.dump(nostart, f)
 750 | +            with self.assertRaises(ValueError) as cm:                                   # glm C3 P2-3: which pin
 751 | +                PLG.delivered_pins([pins[0], os.path.join(d, "nostart.json")])
 752 | +            self.assertIn("nostart.json", str(cm.exception))
 753 | +        self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_")), before)
 754 | +
 755 | +    def test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age(self):
 756 | +        """Audit 2315 C3 K7 (grok, glm): the adapter's delivered_ids (ledger moment ids, 24 h) stay empty: tonight's
 757 | +        pins carry no ledger id. L-p is carried by package.usable, which drops any moment that overlaps a delivered
 758 | +        span of the same video, and the driver passes every delivered pin's spans, whatever the pin's age."""
 759 | +        sys.path.insert(0, HERE)
 760 | +        import package as PK
 761 | +        import proof_ledger as PLG
 762 | +        with open(os.path.join(HERE, "proof", "fresh_20261112_050611", "MOMENTS_PIN_LY.json")) as f:
 763 | +            pin = json.load(f)
 764 | +        old = dict(pin, approved_at="2026-10-01T00:00:00+00:00",
 765 | +                   segments=[dict(pin["segments"][0], video_id="vidA", start=15.0, end=25.0)])
 766 | +        with tempfile.TemporaryDirectory() as d:
 767 | +            with open(os.path.join(d, "old.json"), "w") as f:
 768 | +                json.dump(old, f)
 769 | +            spans, _, _ = PLG.delivered_pins([os.path.join(d, "old.json")])
 770 | +        m = {"moment_id": "m1", "video_id": "vidA", "channel_id": "UCdd", "on_screen_ok": True, "duration_s": 8.0,
 771 | +             "published_at": NOW.isoformat(), "text": SENTS[0]}
 772 | +        for start, end, out in ((20.0, 28.0, True), (10.0, 16.0, True), (25.0, 33.0, False), (5.0, 15.0, False)):
 773 | +            ok, why = PK.usable([dict(m, start=start, end=end)], E.Context(NOW, REG), delivered=spans)
 774 | +            self.assertEqual("m1" in why, out, (start, end))
 775 | +            if out:
 776 | +                self.assertIn("overlaps a delivered moment", why["m1"])
 777 | +
 778 | +
 779 | +if __name__ == "__main__":
 780 | +    unittest.main()
 781 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse, moments-first packaging under law L-y, the
MEDLEY). ROUND 2: this is the FINAL diff after two audit cycles. Check that every fix below is right and complete, and
look for anything new. Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

The task (orchestrator ruling 2, 22:40 ET Nov 12): "when [ingest ledger] rows turn sentence-ready, build from the
ledger (best_unused_moments since the last delivered video) and seal a pin; that is the first FRESH medley".
Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- clips are verbatim WHOLE sentences of the sentence-locked word transcript (L-o 1);
- a moment is on screen only on a word-timed, sentence-ready record (L-e);
- time-sensitive words only from a source <= 24 h old, judged on the RENDER clock (L-v 3, ruling 1);
- no clip span already delivered is used again (L-p).

The contract agreed with the integrator, who owns the word-pass worker:
- word records: the store's full-video slot (transcripts/<vid>/transcript.whisper_words*.json, write-once, full-video
  clock), or LATER window records the worker lists in moments/word_pass.jsonl (not wired yet; counted, unused).
- the ingest adapter, best_unused_moments(path, since, now, delivered_ids, ...), returns "lines mined at or after
  `since` or published inside the 72 h window", minus its own exclusions. Ledger rows carry the CAPTION clock.

The files:
1. pipeline/ledger_build.py:
   - rows(): the adapter in its own interpreter, read-only.
   - word_source(): the punctuated record first, sha-checked, sentence-ready only.
   - reanchor(): sentence_law.anchor plus a snap of at most 3 words per edge, guarded against an added negation or
     number.
   - build_inputs(): the miner's own judge/record; every drop is counted.
2. tests/package/proof_ledger.py: the driver (render clock, delivered spans out, the medley build, the pin).
3. tests/package/test_ledger_build.py.

Fixed after cycle 1 (C1_CONSENSUS):
- the snap may not add a negation or a digit (SNAP_GUARD);
- the delivered pins became an argument;
- malformed rows are counted;
- the drop reason is recorded;
- the horizon is a float;
- tests: punctuated-first, a segment edited after its sha.

Fixed after cycle 2 (C2_DISPOSITIONS):
- K4: word_source returns (Source, path, passed_over). Every record read and not used is named with why, in reading
  order; a fallback from the punctuated record is listed in report.fallbacks.
- K5: a video whose rows name more than one channel_id is dropped whole and counted (report.channel_conflict).
- K6: --delivered is REQUIRED (no hard-coded default). The pins are read before anything is written; a pin that
  cannot be read, has no clip or no zoned approved_at refuses the run (exit 2).
- rows(): a timeout or an unreadable answer raises RuntimeError.
- SNAP_GUARD reads a typographic apostrophe (U+2019 and others) as '.
- tested: a record with no sha; SEARCH_PAD_S's reason is documented.
- NOT a reviewer finding (check it against ruling 2's words): `since` now defaults to the newest delivered pin's
  approved_at, overridable with --since. Before, it was now - 72 h; --hours is now the publish window only.

Check, concretely:
(a) Can a non-whole-sentence clip, a non-word-timed moment, a moment from an unverified record, or a delivered span
    get through?
(b) Is any drop silent?
(c) Does the `since` default match "best_unused_moments since the last delivered video", and can it read too few or
    too many lines?
(d) Is each cycle-2 fix complete?
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
