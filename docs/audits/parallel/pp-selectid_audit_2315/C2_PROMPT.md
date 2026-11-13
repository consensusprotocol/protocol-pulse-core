# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2315
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 824 s finish=length usage in 12070 / out 24000 usd~0.396 (upper-bound price)

# Audit: pp-selectid — ledger_build / proof_ledger / test_ledger_build

Scope note: I can only see the 3 new files in the diff. Everything below is what I can verify from them plus the contracts stated in the prompt; where I depend on an unseen function (`sentence_law.anchor`, `E.sentence_ready`, `M.judge`, `package.build`, `ts.segments_sha256`), I say so.

---

## P0 findings

**P0-1. `word_source()` silently accepts a record whose `transcript_sha256` field is *absent* — the sha check can pass vacuously.**
`ledger_build.py:89`:
```python
if rec.get("transcript_sha256") != ts.segments_sha256(rec.get("segments") or []):
    continue
```
If a record has no `transcript_sha256` key, `rec.get(...)` is `None`, and the record is skipped only if `segments_sha256(...)` returns something non-None. I cannot see `segments_sha256`'s body, so I cannot prove it never returns `None` for an empty/absent segments list. But the failure scenario is concrete: a record `{"segments": []}` (or `{"segments": null}`) where `segments_sha256([]) is None` would compare `None != None` → False → **not skipped**, then `S.tokens_from_record(rec)` runs on an empty record. Whether that yields a usable Source or a crash depends on unseen code. The test at `test_ledger_build.py:346-355` only covers a *wrong* sha (`"x"*64`), never a *missing* sha or empty segments — so this path is unproven either way. Given the standing law "nothing measured is never a pass" (L-m) and fail-closed (L-j), an unverified record reaching the render would be a P0; as written I can only call it "unproven, likely P0 if `segments_sha256` can return None". Recommend: the test adds a missing-sha and empty-segments case, or `word_source` requires the key explicitly.

**P0-2. `word_source()` globs `transcript.whisper_words*.json` and sorts by "punctuated first", but a *non-punctuated* record that happens to be sentence-ready can win over a punctuated one — and the punctuated record's sha failure falls through silently to the unpunctuated one.**
`ledger_build.py:81-82`:
```python
paths = sorted(glob(...), key=lambda p: "punct" not in p)
```
The sort key `"punct" not in p` is a bool; `False < True`, so punctuated sorts first — that part is correct. But the loop `continue`s on *any* failure (sha mismatch, `E.sentence_ready` false) and falls through to the next candidate. Combined with the contract "write-once, one per video", this is fine for the store's invariant, but the *contract* says the full-video slot is one record per video; the glob+sort+fallthrough implies the author expects multiple. If the store ever holds both `transcript.whisper_words.json` (verbatim, unpunctuated) and `transcript.whisper_words_punct.json`, and the punctuated one has a stale sha (e.g. written before a segments fix), the code silently uses the *verbatim* record — which under L-e must not be read for sentences unless it is itself sentence-ready. That is actually the correct behavior *if* `E.sentence_ready` is strict, but the drop of the punctuated record is counted nowhere: `report["word_records"][vid]` records only the winner (`ledger_build.py:137`), and no counter tracks "punctuated record present but rejected". Silent, uncounted degradation of the *preferred* source. P1/P0 boundary; I'll call it P1 since the outcome (a sentence-ready record) is still law-compliant — but the "why" is invisible in the report, which the diff's own header promises ("every drop counted").

---

## P1 findings

**P1-1. `reanchor()`'s snap can change the meaning of a moment, and the 3-word budget is counted per edge, not total — the diff's own question "can a snap change the meaning (3 words)?" is answered "yes, silently, up to 6 words total, and the ledger's scores/risks/topics are kept verbatim for a *different* span".**
`ledger_build.py:114-119`:
```python
left, right = i0 - src.sentences[k0][0], src.sentences[k1][1] - i1
if left > SNAP_WORDS or right > SNAP_WORDS:  # per-edge, not total
    return None, ...
sp = E.Span(src, k0, k1)
```
Concrete scenario: the ledger row's text is the *middle* 2 sentences of a 5-sentence stretch, but its caption-clock `start`/`end` (±30 s pad) cause `SL.anchor` to hit words inside sentence 0 and sentence 4. Then `left=4, right=4` → dropped (fine). But if the anchor hits 3 words into sentence 0 and 3 words into sentence 4, the span becomes 5 sentences where the ledger's `scores`/`risks`/`topics`/`reason` (kept verbatim at `ledger_build.py:147-148`) were judged on 2. The moment's `rank_score` (`ledger_build.py:152`) is then computed from scores that describe different words than the clip. The `mined.reanchored` info records `snapped_words: [left, right]` — good — but nothing re-derives or even flags that the ledger's editorial metadata now describes a different (larger) span. Whether this is a *meaning* change depends on `M.judge`/`M.record` (unseen), but the scores prove

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 77 s finish=stop usage in 12007 / out 618 usd~0.075 (upper-bound price)

**P0: pipeline/ledger_build.py:69**
Adapter success with zero rows is treated quietly. Concrete inputs: ledger containing only already-delivered moments or only non-Bitcoin/opted-out rows → `best_unused_moments` returns `{"rows": [], "report": {"excluded": {"delivered": 12, "horizon": 5}}}` (no `"contract"` key, returncode=0) → `rows()` returns `([], report)` instead of raising → `build_inputs` produces 0 moments → `package.build` can emit a pin with `why_none` that downstream treats as a valid (empty) medley. Violates explicit docstring contract ("no rows is never read as a quiet ledger"), M12 FAIL CLOSED, and L-j release authorisation (missing data must reject).

**P1: pipeline/ledger_build.py:139 (reanchor call inside build_inputs)**
Snap logic silently enlarges the selected span. Concrete inputs: ledger row with `text="Bitcoin is sound money"` that `sentence_law.anchor` matches to tokens[7:11] inside a 10-word sentence (left overhang=3 words: "Despite critics claiming otherwise,") with `SNAP_WORDS=3` → `sp = E.Span(..., k0=0, k1=0)` → `M.record` and `M.judge` run on the full sentence, `rec["text"]` becomes the word-record full sentence, `mined["ledger_text"]` retains the original shorter string → moment passed downstream with words that were never in the mined ledger row. Violates SELECTION LOCK (words must be fixed at selection time) and "the moment's text becomes the word record's own words" claim when the snap materially changes semantic content. (Test at test_ledger_build.py:319 only exercises a 1-word snap; 3-word case untested.)

**P2: tests/package/test_ledger_build.py:378**
Test suite does not exercise the empty-rows path that the production code accepts. Concrete inputs: mocked adapter returning `{"rows": [], "report": {"excluded": {...}}}` (no `"contract"`) → only the `returncode!=0` and `"contract"` branches are asserted; the quiet-empty case that reaches `build_inputs` and `package.json` with `usable=0` is untested. Therefore the P0 behaviour above is not regression-protected. (Also, `proof_ledger.py:234` passes `delivered_spans()` but never asserts that an overlapping ledger row is dropped per the novelty comment.)

**Verdict:** SHIP: yes with conditions  
(The empty-ledger raise must be added and tested; snap acceptance must either tighten to ratio >=0.9 or document why altering the mined text is legal under SELECTION LOCK / L-o. All other laws (L-e punctuated records, sha check, fail-closed adapter, counted drops, render-clock `now`, whole-sentence enforcement) are satisfied by the diff.)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 71 s finish=stop usage in 13298 / out 2466 usd~0.077 (upper-bound price)

# Code Audit: pp-selectid-2315 (C1_STEP.diff)

## P0 Findings

### P0-1: `word_source` returns the first *any* matching record, not necessarily the punctuated one
**File:** `pipeline/ledger_build.py:81-96`

The glob sorts with `key=lambda p: "punct" not in p`, which places files *without* "punct" in the name first (False=0 < True=1). The loop then returns the **first** record that passes the SHA check and `E.sentence_ready()`. If a non-punctuated `transcript.whisper_words.json` exists alongside `transcript.whisper_words_punct.json` and both have valid SHAs, the non-punctuated record is returned first.

**Failure scenario:** A video has both `transcript.whisper_words.json` (verbatim, unpunctuated) and `transcript.whisper_words_punct.json`. The verbatim record's segments SHA is valid. `E.sentence_ready()` may pass if the verbatim record happens to have sentence boundaries from a prior pass. The builder uses the verbatim record, violating **Law L-e** ("Every word transcript the sentence law reads… has its sentence punctuation restored from a prompted second decode… before any sentence is read"). The docstring explicitly states "punctuated first" but the sort order is inverted.

**Fix:** `key=lambda p: "punct" in p` (True=1 sorts first) or explicitly prefer the punct file.

---

### P0-2: `reanchor` does not verify the snapped span is sentence-ready
**File:** `pipeline/ledger_build.py:100-119`

`reanchor` snaps the anchored word range to `src.sentences[k0]` and `src.sentences[k1]`, then constructs `E.Span(src, k0, k1)`. It never calls `E.sentence_ready()` on the resulting span. The `word_source` function checks `E.sentence_ready(src)` on the *Source*, but the Source-level check may not guarantee that the specific sentence range `[k0, k1]` is sentence-ready (e.g., if the record has a mix of punctuated and unpunctuated stretches, or if `sentence_ready` is a per-record flag that doesn't validate every sentence boundary).

**Failure scenario:** A word record is marked sentence-ready at the record level, but sentence `k1` ends without terminal punctuation (an unpunctuated stretch at the tail). The snap extends to include that sentence. The clip's last word is not the last word of a sentence, violating the **SENTENCE LAW**. The gate would catch it at render time, but the builder should fail closed at selection time.

**Note:** If `E.sentence_ready(src)` is a per-record boolean that guarantees *all* sentences are punctuated, this is not a bug. I cannot verify this from the diff alone. Flagging as P0 pending confirmation.

---

## P1 Findings

### P1-1: `build_inputs` uses `rs[0]` for `word_source` but iterates all rows for re-anchoring
**File:** `pipeline/ledger_build.py:132-133`

```python
for vid, rs in by_vid.items():
    src, path = word_source(rs[0], ctx, store)
```

`word_source` is called with `rs[0]` (the first row for that video). If `rs[0]` has a `channel_id` that differs from other rows in `rs` (e.g., a re-upload or a multi-channel video), the `Source` is constructed with `rs[0]`'s channel identity. The other rows in `rs` are re-anchored against this Source, but their own `channel_id` is not used.

**Failure scenario:** A video has two ledger rows: one from channel "DataDash" and one from "Coin Bureau" (e.g., a compilation video). `rs[0]` is the DataDash row. The Source is built with DataDash's identity. The Coin Bureau row is re-anchored and recorded with DataDash's channel in the Source, but the moment's `mined.ledger_moment_id` preserves the original row. The credits card (Law CREDITS) would show DataDash for a clip that is actually Coin Bureau's statement.

**Mitigation:** This may be impossible if the ledger guarantees one channel per video. Flagging as P1 pending confirmation.

---

### P1-2: `SEARCH_PAD_S = 30.0` may be insufficient for long captions
**File:** `pipeline/ledger_build.py:39, 104-106`

The anchor search window is `[t0 - 30, t1 + 30]`. If a ledger row's caption times are significantly off (e.g., the caption clock is 40 seconds ahead of the word record's clock due to a different timebase), the anchor will fail and the row is dropped.

**Failure scenario:** A video's caption track has a 35-second offset from the audio. The row's `start` is 100s, `end` is 110s. The search window is [70, 140]. The actual words in the word record are at 135-145s. The anchor fails. The row is dropped with "does not anchor." This is fail-closed (correct behavior), but it may silently drop valid moments if the offset exceeds 30s. The report counts these as `not_anchored`, so they are not *silently* dropped, but the 30s pad is a magic number with no documented rationale.

**Severity:** P1 because it is fail-closed and counted, but the pad may be too small for real-world caption drift.

---

### P1-3: `proof_ledger.py` hardcodes `DELIVERED_PINS` paths
**File:** `tests/package/proof_ledger.py:204-205`

```pyth

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of the ledger build path (ruling 2, 22:40): cycle 1 consensus (synthesis by the pp-selectid session; written after cycle 1 closed, time from `date` in the commit)

**Run.** C1_STEP.diff is 21,663 bytes; the prompt is 42,836 bytes. Reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions.
- qwen/qwen3.8-27b (Heimdall, effort none): two P0s, both refuted below.
- z-ai/glm-5.3-flash (Heimdall, effort none): "P0: none provable".

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | the punctuated record is not read first; a broken punctuated record falls through to the verbatim one (qwen P0-1, glm P0-2) | REFUTED on the sort, and now tested. `key=lambda p: "punct" not in p` gives the punctuated file False, which sorts BEFORE True: the punctuated record is read first. The fall-through to a verbatim record that is itself sentence-ready is law L-e's own rule (E.sentence_ready: punctuation restored OR no stretch that needs restoring), as in the selector. Test: test_the_punctuated_record_is_read_first |
| K2 | the snap can change the meaning (up to 3 words per edge) while the ledger's scores and risks are kept (grok P1, glm P1-1) | IMPLEMENTED: a word the snap would ADD may not be a negation (not, no, never, nobody, ... n't) or carry a digit (SNAP_GUARD); such a row is dropped with why. Those are the words that flip or add a claim the ledger's judgment never saw. The rest of the snap (at most 3 words of the record's own sentence) stays: the ledger row is discovery, and the word record's whole sentences are what every gate judges (step A, exclusion, fidelity, context) and what the pin locks. Tests: test_a_snap_never_adds_a_negation_or_a_number ("can stop Bitcoin" would gain "Nobody"; "Bitcoin started ..." would gain "In 2009"), and the exact 3-word boundary (3 snaps, 4 refused) |
| K3 | the delivered pins are hard-coded in the driver (qwen P1-3, glm P1-4 / P2-8) | IMPLEMENTED: --delivered PIN ... (default: tonight's two delivered pins); a missing or broken pin file stops the run (fail closed) |

## Unique findings, evaluated

| finding | disposition |
|---|---|
| grok P0: an empty successful read is "quiet" | REFRAMED, docstring corrected. A FAILURE or a REFUSAL raises (tested). An empty successful read is a real result: no row passes the ledger's own exclusions, the report's counts say why, and no pin can come of it. Test: the empty-read case returns ([], report) |
| glm P0-1: a record with no transcript_sha256 passes vacuously | REFUTED: None != segments_sha256(...), so it is skipped. A segment edited after its sha was taken is caught too (new test) |
| qwen P0-2: the snapped span may not be sentence-ready | REFUTED: sentence readiness is a property of the RECORD (E.sentence_ready), and the Span is whole sentences k0..k1 of that record by construction |
| glm P1-2: the report cannot tell "no record" from "sha-broken / not sentence-ready" | IMPLEMENTED: word_source returns why, and the report counts

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_2315/C2_STEP.diff (465 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | new file mode 100644
   3 | index 00000000..fe639c32
   4 | --- /dev/null
   5 | +++ b/pipeline/ledger_build.py
   6 | @@ -0,0 +1,181 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/ledger_build.py — ORCHESTRATOR 22:40 ruling 2: the medley built from the INGEST LEDGER, the path to the first
   9 | +FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call here (package.build makes those).
  10 | +
  11 | +- rows(): pp-ingest's own adapter, pipeline.ingest.ledger.best_unused_moments, with its exclusions applied: delivered,
  12 | +  opted out, hard flags, altcoin or not about Bitcoin, a speaker change, re-uploads. It runs read-only in its own
  13 | +  interpreter, from the pp-ingest worktree, until the integrator merges it.
  14 | +- READY: a row is packageable only on a sentence-ready WORD record (law L-e). Today that is the store's full-video slot
  15 | +  (transcripts/<vid>/transcript.whisper_words*.json, punctuated first, its segments sha checked). Window records from
  16 | +  the word-pass worker (the integrator's contract: transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json,
  17 | +  youtube clock, listed in moments/word_pass.jsonl) need their L-s context from the CAPTION record. That is not wired
  18 | +  yet: such rows are counted in the report and not used.
  19 | +- RE-ANCHOR: sentence_law.anchor, the sentence law's own text locator, finds the row's TEXT in the word record. The
  20 | +  row's caption-clock times only narrow the search. The span then snaps to that record's WHOLE sentences when at most
  21 | +  SNAP_WORDS words lie outside the anchored text at either edge; otherwise the row is dropped, and why is recorded.
  22 | +  The moment's text becomes the word record's own words, verbatim, the words the render locks on.
  23 | +- RECORD: the miner's own moments.judge() and moments.record(): eligibility on word timing (on_screen_ok). The ledger
  24 | +  row's scores, risks, topics, reason and mining provenance are kept (mined.ledger_moment_id).
  25 | +-> build_inputs(...) = (moments, sources, report).
  26 | +"""
  27 | +import glob
  28 | +import json
  29 | +import os
  30 | +import sys
  31 | +
  32 | +import eligibility as E
  33 | +import moments as M
  34 | +import select_by_id as S
  35 | +import sentence_law as SL
  36 | +import transcript_store as ts
  37 | +
  38 | +SNAP_WORDS = 3            # words of a word-record sentence the anchored text may leave out at either edge
  39 | +SNAP_GUARD = __import__("re").compile(r"^(not|no|never|none|nobody|nothing|neither|nor|cannot|can't|won't|don't|"
  40 | +                                      r"doesn't|didn't|isn't|aren't|wasn't|weren't|shouldn't|wouldn't|couldn't|"
  41 | +                                      r"\w+n't)$|\d", __import__("re").I)
  42 | +                          # a word the snap would ADD may not be a negation or carry a digit: it could flip or add a
  43 | +                          # claim the ledger's scores and risks never saw (audit 2315 C1: grok P1, glm P1-1)
  44 | +SEARCH_PAD_S = 30.0       # the row's caption times narrow the anchor's search to [start - pad, end + pad]
  45 | +INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
  46 | +MAIN = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")
  47 | +STORE = os.path.join(MAIN, "data", "editorial")
  48 | +
  49 | +
  50 | +_ROWS = """
  51 | +import json, sys
  52 | +from datetime import datetime
  53 | +sys.path.insert(0, sys.argv[1])
  54 | +from pipeline.ingest import ledger as IL
  55 | +a = json.loads(sys.stdin.read())
  56 | +rows, rep = IL.best_unused_moments(a["path"], datetime.fromisoformat(a["since"]), datetime.fromisoformat(a["now"]),
  57 | +                                   a["delivered"], store_root=a["store_root"], horizon_h=a["horizon_h"])
  58 | +sys.stdout.write(json.dumps({"rows": rows, "report": rep}, default=str))
  59 | +"""
  60 | +
  61 | +
  62 | +def rows(since, now, delivered_ids=(), ingest_root=INGEST_ROOT, horizon_h=72, timeout=300):
  63 | +    """pp-ingest's adapter, best_unused_moments, run read-only in its OWN interpreter, from its worktree until the
  64 | +    integrator merges it. Its store guard refuses a process in which another transcript_store was imported first, so
  65 | +    the two never share modules. -> (rows, report). Raises RuntimeError when the adapter FAILS or REFUSES (fail
  66 | +    closed: a failure is never read as an empty ledger). An empty successful read is a real result: no row passes the
  67 | +    ledger's own exclusions, and the report's counts say why."""
  68 | +    import subprocess
  69 | +    args = {"path": os.path.join(ingest_root, "data", "editorial", "moments", "moment_ledger.jsonl"),
  70 | +            "since": since.isoformat(), "now": now.isoformat(), "delivered": list(delivered_ids),
  71 | +            "store_root": os.path.join(ingest_root, "data", "editorial"), "horizon_h": horizon_h}
  72 | +    env = dict(os.environ, PP_SELECTID_PIPELINE=os.path.dirname(os.path.abspath(__file__)))
  73 | +    p = subprocess.run([sys.executable, "-c", _ROWS, ingest_root], input=json.dumps(args), capture_output=True,
  74 | +                       text=True, cwd=ingest_root, env=env, timeout=timeout)
  75 | +    if p.returncode != 0:
  76 | +        raise RuntimeError(f"the ledger adapter failed: {p.stderr.strip()[-400:]}")
  77 | +    out = json.loads(p.stdout)
  78 | +    if (out["report"] or {}).get("contract"):
  79 | +        raise RuntimeError(f"the ledger adapter refused: {out['report']['contract']}")
  80 | +    return out["rows"], out["report"]
  81 | +
  82 | +
  83 | +def word_source(row, ctx, store=STORE):
  84 | +    """The video's sentence-ready word record from the store's full-video slot (punctuated first, its segments sha
  85 | +    checked), as an eligibility Source with the row's identity -> (Source, path), or (None, why)."""
  86 | +    vid = row["video_id"]
  87 | +    paths = sorted(glob.glob(os.path.join(store, "transcripts", vid, "transcript.whisper_words*.json")),
  88 | +                   key=lambda p: "punct" not in p)
  89 | +    reg = ctx.channel(row.get("channel_id")) or {}
  90 | +    why = "no word record in the store" if not paths else None
  91 | +    for p in paths:
  92 | +        try:
  93 | +            rec = json.load(open(p))
  94 | +        except (OSError, ValueError):
  95 | +            why = why or "a word record that cannot be read"
  96 | +            continue
  97 | +        if rec.get("transcript_sha256") != ts.segments_sha256(rec.get("segments") or []):
  98 | +            why = "a word record whose segments do not match its transcript_sha256"
  99 | +            continue
 100 | +        timing, toks = S.tokens_from_record(rec)
 101 | +        src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
 102 | +                       row.get("published_at"), rec.get("transcript_sha256"), rec.get("transcript_method"), toks,
 103 | +                       timing=timing, title=row.get("title") or "", file_head=True, vod=True)
 104 | +        if E.sentence_ready(src):
 105 | +            return src, p
 106 | +        why = "a word record that is not sentence-ready (law L-e)"
 107 | +    return None, why
 108 | +
 109 | +
 110 | +def reanchor(row, src):
 111 | +    """The row's TEXT located in the word record and snapped to its whole sentences -> (E.Span, info) or (None, why)."""
 112 | +    def num(x):
 113 | +        try:
 114 | +            return float(x)
 115 | +        except (TypeError, ValueError):
 116 | +            return None                                 # an unreadable time only widens the search (glm C1 P1-9)
 117 | +    t0, t1 = num(row.get("start")), num(row.get("end"))
 118 | +    hit = SL.anchor(src.tokens, row.get("text") or "",
 119 | +                    t0=(t0 - SEARCH_PAD_S) if t0 is not None else None,
 120 | +                    t1=(t1 + SEARCH_PAD_S) if t1 is not None else None)
 121 | +    if hit is None:
 122 | +        return None, (f"the row's text does not anchor in the word record (sentence_law.anchor"
 123 | +                      + (f", searched {t0 - SEARCH_PAD_S:.0f}-{t1 + SEARCH_PAD_S:.0f} s)" if t0 is not None and
 124 | +                         t1 is not None else ")"))
 125 | +    i0, i1, ratio = hit
 126 | +    k0 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i0 <= b), None)
 127 | +    k1 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i1 <= b), None)
 128 | +    if k0 is None or k1 is None:
 129 | +        return None, "the anchored words fall outside the record's sentences"
 130 | +    left, right = i0 - src.sentences[k0][0], src.sentences[k1][1] - i1
 131 | +    if left > SNAP_WORDS or right > SNAP_WORDS:
 132 | +        return None, (f"the anchored text is not whole sentences of the word record ({left} word(s) before it and "
 133 | +                      f"{right} after it inside its edge sentences; at most {SNAP_WORDS})")
 134 | +    added = [t["word"].strip(".,!?;:\"'()") for t in list(src.tokens[src.sentences[k0][0]:i0]) +
 135 | +             list(src.tokens[i1 + 1:src.sentences[k1][1] + 1])]
 136 | +    risky = [w for w in added if SNAP_GUARD.search(w)]
 137 | +    if risky:
 138 | +        return None, f"snapping to whole sentences would add {risky}: a negation or a number the ledger never judged"
 139 | +    sp = E.Span(src, k0, k1)
 140 | +    return sp, {"anchor_ratio": round(ratio, 3), "snapped_words": [left, right], "sentences": [k0, k1]}
 141 | +
 142 | +
 143 | +def build_inputs(rows, ctx, store=STORE, log=print):
 144 | +    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). Rows on a video with no sentence-
 145 | +    ready word record, rows whose text does not re-anchor on whole sentences, and duplicates of one span are dropped,
 146 | +    each counted with why."""
 147 | +    report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "not_anchored": {}, "malformed": {},
 148 | +              "duplicates": 0, "moments": 0, "videos": 0, "word_records": {}}
 149 | +    by_vid = {}
 150 | +    for r in rows:
 151 | +        by_vid.setdefault(r["video_id"], []).append(r)
 152 | +    moments, sources, seen = [], {}, set()
 153 | +    for vid, rs in by_vid.items():
 154 | +        src, path = word_source(rs[0], ctx, store)
 155 | +        if src is None:
 156 | +            report["no_word_record"] += len(rs)
 157 | +            report["no_word_record_why"][path] = report["no_word_record_why"].get(path, 0) + len(rs)
 158 | +            continue
 159 | +        report["word_records"][vid] = os.path.relpath(path, store)
 160 | +        for r in rs:
 161 | +            sp, info = reanchor(r, src)
 162 | +            if sp is None:
 163 | +                report["not_anchored"][r["moment_id"]] = info
 164 | +                continue
 165 | +            if (vid, sp.k0, sp.k1) in seen:
 166 | +                report["duplicates"] += 1
 167 | +                continue
 168 | +            try:
 169 | +                m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
 170 | +                     "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
 171 | +                     "reason": r.get("reason") or ""}
 172 | +                mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 173 | +                             ledger_text=r.get("text"))
 174 | +                rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
 175 | +                rec["rank_score"] = M.rank_score(rec)
 176 | +            except (KeyError, TypeError, ValueError) as e:     # counted, never a crash (glm C1 P1-8)
 177 | +                report["malformed"][r.get("moment_id")] = f"{type(e).__name__}: {str(e)[:120]}"
 178 | +                continue
 179 | +            seen.add((vid, sp.k0, sp.k1))
 180 | +            moments.append(rec)
 181 | +            sources[vid] = src
 182 | +    report["moments"], report["videos"] = len(moments), len(sources)
 183 | +    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} word records; "
 184 | +        f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
 185 | +        f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates")
 186 | +    moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
 187 | +    return moments, sources, report
 188 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 189 | new file mode 100644
 190 | index 00000000..4596c688
 191 | --- /dev/null
 192 | +++ b/tests/package/proof_ledger.py
 193 | @@ -0,0 +1,102 @@
 194 | +#!/usr/bin/env python3
 195 | +"""ORCHESTRATOR 22:40 ruling 2: build the medley from the INGEST LEDGER and seal a pin.
 196 | +
 197 | +- The rows are pp-ingest's adapter (best_unused_moments), read-only.
 198 | +- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py).
 199 | +- "now" is the RENDER clock (ruling 1): L-v 3 and currency are judged against tonight, not against a universe snapshot.
 200 | +- Novelty (L-p): every clip span of the pins already delivered (the 37c5b5f5 review, run 165629; the 41f29b1f medley)
 201 | +  is passed to package.usable as delivered, so an overlapping moment is out.
 202 | +- The same legs, ledger and meters as proof_ly.py: Heimdall writes, xAI judges, scribe_v1 is the second recogniser.
 203 | +  Writer calls have ruling 5's deadline; the budget is ruling 5's.
 204 | +Writes tests/package/proof/ledger_<UTC stamp>/: inputs.json, package.json, package.log, step_a.json and, on a
 205 | +package, MOMENTS_PIN_LEDGER.json.
 206 | +
 207 | +Usage: python3 tests/package/proof_ledger.py [--hours 72]
 208 | +"""
 209 | +import argparse
 210 | +import json
 211 | +import os
 212 | +import sys
 213 | +import time
 214 | +from datetime import datetime, timedelta, timezone
 215 | +
 216 | +HERE = os.path.dirname(os.path.abspath(__file__))
 217 | +REPO = os.path.dirname(os.path.dirname(HERE))
 218 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 219 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 220 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 221 | +sys.path.insert(0, HERE)
 222 | +import eligibility as E  # noqa: E402
 223 | +import ledger_build as LB  # noqa: E402
 224 | +import moments as M  # noqa: E402
 225 | +import package as PK  # noqa: E402
 226 | +import package_pin  # noqa: E402
 227 | +import proof_ly as PL  # noqa: E402
 228 | +import proof_saved_runs as PS  # noqa: E402
 229 | +import providers as P  # noqa: E402
 230 | +
 231 | +DELIVERED_PINS = (os.path.join(HERE, "proof", "fresh_20261112_050611", "MOMENTS_PIN.json"),       # 37c5b5f5 (165629)
 232 | +                  os.path.join(HERE, "proof", "fresh_20261112_050611", "MOMENTS_PIN_LY.json"))    # 41f29b1f
 233 | +
 234 | +
 235 | +def delivered_spans(paths=DELIVERED_PINS):
 236 | +    """Every clip span of the pins already delivered: {video_id, start, end} (package.usable reads overlaps)."""
 237 | +    out = []
 238 | +    for p in paths:
 239 | +        pin = json.load(open(p))
 240 | +        out += [{"video_id": s["video_id"], "start": s["start"], "end": s["end"], "pin": pin["story_id"]}
 241 | +                for s in pin["segments"]]
 242 | +    return out
 243 | +
 244 | +
 245 | +def main(argv=None):
 246 | +    ap = argparse.ArgumentParser()
 247 | +    ap.add_argument("--hours", type=float, default=72.0, help="the adapter's horizon (and 'since' = now - hours)")
 248 | +    ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 249 | +    ap.add_argument("--delivered", nargs="*", default=list(DELIVERED_PINS),
 250 | +                    help="the pins already delivered (their clip spans are out, L-p); the default is tonight's two")
 251 | +    a = ap.parse_args(argv)
 252 | +    now = datetime.now(timezone.utc)
 253 | +    out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M')}")
 254 | +    os.makedirs(out_dir, exist_ok=True)
 255 | +    logf = open(os.path.join(out_dir, "package.log"), "a")
 256 | +    say = lambda s: (print(s, flush=True), logf.write(s + "\n"), logf.flush())
 257 | +    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
 258 | +    say(f"=== {time.strftime('%H:%M:%S %Z')} LEDGER medley build, code {PL.code_sha()}, now (render clock) "
 259 | +        f"{now.isoformat(timespec='seconds')}")
 260 | +    rows, rep = LB.rows(now - timedelta(hours=a.hours), now, horizon_h=a.hours)
 261 | +    say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 262 | +    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say)
 263 | +    delivered = delivered_spans(a.delivered)
 264 | +    json.dump({"adapter_report": rep, "inputs": inputs, "delivered": delivered,
 265 | +               "moments": moments}, open(os.path.join(out_dir, "inputs.json"), "w"), indent=1, default=str)
 266 | +    router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 267 | +                      chains=PL.chains())
 268 | +    own, used = PL.meter(router), PL.reply_meter(router)
 269 | +    t0 = time.time()
 270 | +    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 271 | +                   work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 272 | +                   spend=lambda: (own["est"], own["best"]))
 273 | +    res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 274 | +               full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 275 | +               chains=router.chains, inputs=inputs)
 276 | +    if res["package"]:
 277 | +        try:
 278 | +            path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M')}", out_dir,
 279 | +                                              name="MOMENTS_PIN_LEDGER.json")
 280 | +            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 281 | +                          "package_sha256": pin["moments_package"]["package_sha256"]}
 282 | +            say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known) "
 283 | +                f"pin {path}")
 284 | +        except package_pin.PinRefused as e:
 285 | +            res["pin_refused"] = str(e)
 286 | +            say(f"PIN REFUSED: {e}")
 287 | +    else:
 288 | +        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 289 | +    json.dump(res, open(os.path.join(out_dir, "package.json"), "w"), indent=1, default=str)
 290 | +    logf.close()
 291 | +    return 0
 292 | +
 293 | +
 294 | +if __name__ == "__main__":
 295 | +    sys.exit(main())
 296 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 297 | new file mode 100644
 298 | index 00000000..5c51619b
 299 | --- /dev/null
 300 | +++ b/tests/package/test_ledger_build.py
 301 | @@ -0,0 +1,163 @@
 302 | +#!/usr/bin/env python3
 303 | +"""pipeline/ledger_build.py (ORCHESTRATOR 22:40 ruling 2): the medley built from the ingest ledger. Offline:
 304 | +- re-anchoring a ledger row's TEXT in a word record and snapping it to that record's whole sentences;
 305 | +- reading the store's word record (its sha checked, sentence-ready only);
 306 | +- turning rows into the packager's moments (counted drops, no duplicate spans);
 307 | +- the adapter's failures are raised, never read as an empty ledger."""
 308 | +import json
 309 | +import os
 310 | +import sys
 311 | +import tempfile
 312 | +import unittest
 313 | +from unittest import mock
 314 | +
 315 | +HERE = os.path.dirname(os.path.abspath(__file__))
 316 | +REPO = os.path.dirname(os.path.dirname(HERE))
 317 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 318 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 319 | +import eligibility as E  # noqa: E402
 320 | +import ledger_build as LB  # noqa: E402
 321 | +import transcript_store as ts  # noqa: E402
 322 | +from test_eligibility import NOW, REG, source  # noqa: E402
 323 | +
 324 | +SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settling a payment.",
 325 | +         "That is the whole design and it works every day.", "Bitcoin does not ask for permission.",
 326 | +         "In 2009 Bitcoin started as a quiet experiment."]
 327 | +
 328 | +
 329 | +def row(text, start=None, end=None, mid="L1", vid="vidA"):
 330 | +    return {"moment_id": mid, "video_id": vid, "channel_id": "UCdd", "channel_name": "DataDash", "text": text,
 331 | +            "start": start, "end": end, "published_at": NOW.isoformat(), "title": "t",
 332 | +            "scores": {"contempt_outrage": 0, "hook_first_2s": 3, "quotable": 3, "stakes": 3, "stance": 3,
 333 | +                       "stands_alone": 4, "surprising_fact": 2},
 334 | +            "risk": [], "topics": [], "reason": "r", "names_person": False,
 335 | +            "mined": {"by": "qwen/qwen3.8-27b@heimdall_qwen27b", "at": NOW.isoformat()}}
 336 | +
 337 | +
 338 | +class TestReanchor(unittest.TestCase):
 339 | +    def setUp(self):
 340 | +        self.src = source(SENTS)
 341 | +
 342 | +    def test_whole_sentences_anchor_exactly(self):
 343 | +        sp, info = LB.reanchor(row(SENTS[1] + " " + SENTS[2]), self.src)
 344 | +        self.assertEqual((sp.k0, sp.k1), (1, 2))
 345 | +        self.assertEqual(info["snapped_words"], [0, 0])
 346 | +        self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words
 347 | +
 348 | +    def test_a_caption_text_snaps_to_the_records_whole_sentences_within_the_limit(self):
 349 | +        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short: snaps
 350 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((0, 0), [1, 0]))
 351 | +        sp, info = LB.reanchor(row("whole design and it works every day."), self.src)  # exactly 3 words: snaps
 352 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [3, 0]))
 353 | +        sp, why = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused
 354 | +        self.assertIsNone(sp)
 355 | +        self.assertIn("not whole sentences", why)
 356 | +
 357 | +    def test_a_snap_never_adds_a_negation_or_a_number(self):
 358 | +        """Audit 2315 C1 (grok P1, glm P1-1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin' flips the
 359 | +        claim the ledger scored; '... started as a quiet experiment' snapped to 'In 2009 ...' adds a number."""
 360 | +        for text, word in (("can stop Bitcoin from settling a payment.", "Nobody"),
 361 | +                           ("Bitcoin started as a quiet experiment.", "2009")):
 362 | +            sp, why = LB.reanchor(row(text), self.src)
 363 | +            self.assertIsNone(sp, text)
 364 | +            self.assertIn(word, why)
 365 | +
 366 | +    def test_text_that_is_not_whole_sentences_or_not_there_is_dropped_with_why(self):
 367 | +        sp, why = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
 368 | +        self.assertIsNone(sp)
 369 | +        self.assertIn("not whole sentences", why)
 370 | +        sp, why = LB.reanchor(row("Ethereum is a world computer for everyone."), self.src)
 371 | +        self.assertIsNone(sp)
 372 | +        self.assertIn("does not anchor", why)
 373 | +
 374 | +
 375 | +class TestWordSourceAndInputs(unittest.TestCase):
 376 | +    def store_with(self, d, vid, sentences, break_sha=False):
 377 | +        src = source(sentences, vid=vid)
 378 | +        segs = [{"start": src.tokens[a]["start"], "end": src.tokens[b]["end"],
 379 | +                 "text": E.spoken(src.tokens[a:b + 1]),
 380 | +                 "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens[a:b + 1]]}
 381 | +                for a, b in src.sentences]
 382 | +        rec = {"segments": segs, "transcript_method": "whisper_words_punct", "video_id": vid,     # the store's word
 383 | +               "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens]}  # record shape
 384 | +        rec["transcript_sha256"] = "x" * 64 if break_sha else ts.segments_sha256(segs)
 385 | +        os.makedirs(os.path.join(d, "transcripts", vid), exist_ok=True)
 386 | +        json.dump(rec, open(os.path.join(d, "transcripts", vid, "transcript.whisper_words_punct.json"), "w"))
 387 | +        return src
 388 | +
 389 | +    def test_a_record_whose_sha_does_not_match_its_segments_is_never_read(self):
 390 | +        ctx = E.Context(NOW, REG)
 391 | +        with tempfile.TemporaryDirectory() as d:
 392 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d), (None, "no word record in the store"))
 393 | +            self.store_with(d, "vidA", SENTS, break_sha=True)
 394 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d)[1],
 395 | +                             "a word record whose segments do not match its transcript_sha256")
 396 | +            self.store_with(d, "vidA", SENTS)
 397 | +            src, path = LB.word_source(row(SENTS[0]), ctx, d)
 398 | +            self.assertIsNotNone(src)
 399 | +            self.assertEqual(src.timing, "word")
 400 | +            p = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
 401 | +            rec = json.load(open(p))                       # glm C1 P2-10: a segment edited AFTER its sha was taken
 402 | +            rec["segments"][1]["text"] = "Somebody can stop Bitcoin from settling a payment."
 403 | +            json.dump(rec, open(p, "w"))
 404 | +            self.assertIsNone(LB.word_source(row(SENTS[0]), ctx, d)[0])
 405 | +
 406 | +    def test_the_punctuated_record_is_read_first(self):
 407 | +        """qwen C1 P0-1 / glm C1 P0-2: "punct" sorts first (key False < True); the verbatim record only as a fallback."""
 408 | +        ctx = E.Context(NOW, REG)
 409 | +        with tempfile.TemporaryDirectory() as d:
 410 | +            self.store_with(d, "vidA", SENTS)                                   # transcript.whisper_words_punct.json
 411 | +            punct = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
 412 | +            plain = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words.json")
 413 | +            import shutil
 414 | +            shutil.copy(punct, plain)                                           # both valid, both sentence-ready
 415 | +            self.assertTrue(LB.word_source(row(SENTS[0]), ctx, d)[1].endswith("transcript.whisper_words_punct.json"))
 416 | +            os.remove(punct)
 417 | +            self.assertTrue(LB.word_source(row(SENTS[0]), ctx, d)[1].endswith("transcript.whisper_words.json"))
 418 | +
 419 | +    def test_rows_become_the_packagers_moments_with_every_drop_counted(self):
 420 | +        ctx = E.Context(NOW, REG)
 421 | +        with tempfile.TemporaryDirectory() as d:
 422 | +            self.store_with(d, "vidA", SENTS)
 423 | +            rows = [row(SENTS[0], mid="L1"), row(SENTS[0], mid="L2"),               # the same span twice
 424 | +                    row("Ethereum is a world computer for everyone.", mid="L3"),  # does not anchor
 425 | +                    row(SENTS[0], mid="L4", vid="vidZ"),                            # no word record for vidZ
 426 | +                    {k: v for k, v in row(SENTS[3], mid="L5").items() if k != "scores"}]   # malformed: counted
 427 | +            ms, srcs, rep = LB.build_inputs(rows, ctx, d, log=lambda s: None)
 428 | +            self.assertEqual((rep["moments"], rep["duplicates"], rep["no_word_record"]), (1, 1, 1))
 429 | +            self.assertEqual(list(rep["not_anchored"]), ["L3"])
 430 | +            self.assertEqual(list(rep["malformed"]), ["L5"])                   # glm C1 P1-8: never a crash
 431 | +            m = ms[0]
 432 | +            self.assertEqual(m["mined"]["ledger_moment_id"], "L1")
 433 | +            self.assertEqual(m["scores"], rows[0]["scores"])                  # the ledger's judgment kept (glm P2-6)
 434 | +            self.assertEqual(m["text"], SENTS[0])
 435 | +            self.assertEqual(m["timing"], "word")
 436 | +            self.assertIn("rank_score", m)
 437 | +            self.assertEqual(set(srcs), {"vidA"})
 438 | +
 439 | +
 440 | +class TestAdapter(unittest.TestCase):
 441 | +    def test_a_failing_or_refusing_adapter_raises_never_an_empty_ledger(self):
 442 | +        from datetime import timedelta
 443 | +        fail = mock.Mock(returncode=1, stderr="Traceback ... boom", stdout="")
 444 | +        with mock.patch("subprocess.run", return_value=fail):
 445 | +            with self.assertRaises(RuntimeError):
 446 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 447 | +        refused = mock.Mock(returncode=0, stderr="", stdout=json.dumps(
 448 | +            {"rows": [], "report": {"contract": "unavailable: StoreGuard"}}))
 449 | +        with mock.patch("subprocess.run", return_value=refused):
 450 | +            with self.assertRaises(RuntimeError) as cm:
 451 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 452 | +            self.assertIn("refused", str(cm.exception))
 453 | +        ok = mock.Mock(returncode=0, stderr="", stdout=json.dumps({"rows": [{"moment_id": "x"}], "report": {}}))
 454 | +        with mock.patch("subprocess.run", return_value=ok):
 455 | +            self.assertEqual(LB.rows(NOW - timedelta(hours=72), NOW)[0], [{"moment_id": "x"}])
 456 | +        empty = mock.Mock(returncode=0, stderr="", stdout=json.dumps(       # grok C1 P0 (reframed): a real empty read
 457 | +            {"rows": [], "report": {"excluded": {"delivered in the previous 24 h": 3}}}))
 458 | +        with mock.patch("subprocess.run", return_value=empty):
 459 | +            rows, rep = LB.rows(NOW - timedelta(hours=72), NOW)
 460 | +            self.assertEqual((rows, rep["excluded"]), ([], {"delivered in the previous 24 h": 3}))
 461 | +
 462 | +
 463 | +if __name__ == "__main__":
 464 | +    unittest.main()
 465 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse, moments-first packaging under law L-y, the
MEDLEY). It implements the builder's part of the orchestrator's ruling 2 (22:40 ET Nov 12): "when [ingest ledger]
rows turn sentence-ready, build from the ledger (best_unused_moments since the last delivered video) and seal a pin;
that is the first FRESH medley". Standing laws: nothing measured is never a pass (L-m); fail closed (L-j); never change
what a check accepts in order to make something pass; clips are verbatim WHOLE sentences of the sentence-locked word
transcript (L-o 1); a moment is on screen only on a word-timed, sentence-ready record (L-e); time-sensitive words only
from a source <= 24 h old, now judged on the RENDER clock (L-v 3, ruling 1).

The contract agreed with the integrator, who owns the word-pass worker:
- word records: the store's full-video slot (transcripts/<vid>/transcript.whisper_words*.json, write-once, one per
  video, full-video clock), or LATER window records under transcripts/<vid>/windows/ that the worker lists in
  moments/word_pass.jsonl. The ledger rows are never rewritten and carry the CAPTION clock.
- each moment is re-anchored by its TEXT in the word record (sentence_law.anchor); L-s context comes from the caption
  record for a window record (not wired yet: only full-video records are used today).

What changed, and what to check:
1. pipeline/ledger_build.py (new):
   - rows(): pp-ingest's adapter run read-only in its OWN interpreter (subprocess), because its store guard refuses a
     process in which another transcript_store was imported first. A failure or a refusal raises RuntimeError; it is
     never read as an empty ledger.
   - word_source(): the punctuated record first; its segments sha must match its transcript_sha256; only a
     sentence-ready record (E.sentence_ready) is used.
   - reanchor(): sentence_law.anchor with the row's caption times +- 30 s as a search window. The span snaps to the
     record's whole sentences only if at most SNAP_WORDS (3) words of an edge sentence lie outside the anchored text;
     otherwise the row is dropped with why. The moment's text is the WORD RECORD's own words.
   - build_inputs(): M.judge / M.record (the miner's own eligibility and record), the ledger's scores / risks / topics
     / reason kept, mined.ledger_moment_id kept, duplicate spans dropped, every drop counted.
   Can a non-whole-sentence clip, a non-word-timed moment, a stale time-sensitive moment, or a moment from an
   unverified record get through? Can a snap change the meaning (3 words)? Is anything silently dropped?
2. tests/package/proof_ledger.py (new): the driver. It sets ctx.now to the RENDER clock, passes every clip span of
   the two pins already delivered as `delivered` (package.usable drops overlaps), uses the medley build (package.build)
   with the same legs and meters as proof_ly.py, and writes the pin.
3. tests/package/test_ledger_build.py (new): the re-anchor and snap rules, the sha check, the counted drops, and the
   adapter's raises.

Output: findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
Only state what you can verify from the diff provided. If uncertain, say so; do not guess. End with a verdict line:
"SHIP: yes | yes with conditions | no".


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
