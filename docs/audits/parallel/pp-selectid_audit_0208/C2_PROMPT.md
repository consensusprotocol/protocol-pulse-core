# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0208
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 246 s finish=stop usage in 12457 / out 5371 usd~0.118 (upper-bound price)

# Audit: pp-selectid — one window record per moment

Scope note: I can only see the diff hunks provided. I have not seen `word_source`, `window_source`, `caption_source`, `reanchor`, `M.record`, `M.rank_score`, the full `prescreen`, the pin/render/novelty code, or the fixtures (`window_fixture`, `row`, `SENTS_W`). Statements below are limited to what the hunks show; where a conclusion depends on unseen code I say so.

## (a) Can a lookup still reach the wrong window/Source?

**P1 — `prescreen`'s `fails`/`contexts` are keyed by `moment_id` only, but two window moments of one video can now share the same speech... actually no — they can't (dedup). But two *different* moments of the same video can now have *different* Sources, and every downstream consumer that keys by `video_id` alone is a latent wrong-Source site.** Verified consumers in the diff:

- `package.py:872` `exclusion_for` — fixed to `src_of`. ✔
- `package.py:929` `hook_onset_for` — fixed to `src_of`. ✔
- `package.py:396-397` prescreen step A — fixed to `src_of`. ✔
- `speakers.py:264` `attribute_package` — fixed to `sources.get(s.get("source_key") or s["video_id"])`. ✔
- `context_integrity.py:298` `contexts_from_sources` — fixed. ✔

**P1 — `speakers.py:265` uses `sources.get(...)` (returns `None` on miss) while `package.src_of` uses `sources[...]` (raises).** If a segment carries a `source_key` that is not in `sources` (e.g. a package round-tripped through JSON where the sources dict was rebuilt, or a segment whose moment was later dropped), `attribute_package` silently produces a speaker record from `attribute(router, s, None, meta)`; whether that fails closed depends on `attribute()` (not in the diff — uncertain). By contrast `src_of` would raise a `KeyError`, which is the fail-closed behavior the laws demand. Inconsistent lookup semantics between the two helpers is a real, if conditional, divergence. Also note `src_of` is defined in `package.py` but `speakers.py` and `context_integrity.py` do not use it — they inline the same expression. Three copies of the lookup rule; the test `TestSites` (L-k) fails ad-hoc normalisers outside `canon.py`, but there is no such single-home for the source-lookup rule. If the rule changes again, one of the three copies will be missed.

**P2 — `package.py:207` `**({"source_key": ...} if m.get("source_key") else {})`** — a moment whose `source_key` is an empty string or `None` silently falls back to `video_id` lookup. That is the intended fallback, but note the *inverse* hazard: a full-video moment (no `source_key`) whose video ALSO has a window-Source keyed `vid@...` in `sources` is fine (keyed by `vid`), and a window moment's `video_id` key is never in `sources` (only `vid@...` keys are, per the window branch — verified: the window branch only does `sources[key] = wsrc`, never `sources[vid] = ...`). So the fallback in `src_of`/`contexts_from_sources`/`attribute_package` can only hit the full-video case. That is consistent. No defect found here — stated for completeness.

**P2 — `ledger_build.py:166` key format `f"{vid}@{wsrc.window['start_s']:.3f}-{wsrc.window['end_s']:.3f}"`** — two moments of one video whose windows have identical `start_s`/`end_s` to 3 dp share a key and therefore a Source. Is that correct? If the word-pass worker writes one window per moment, two moments with the same window bounds would be the same record; the dedup by overlapping span (line 143) would likely have caught it first if the spans also overlap. But two *non-overlapping* spans inside one identical window (possible if the worker writes one window covering two nearby moments — the diff's docstring says "ONE WINDOW PER MOMENT", so this should not happen, but nothing in the diff enforces it) would share a Source legitimately. Uncertain whether the worker guarantees uniqueness; the diff does not. If it does not, the shared Source is still the *correct* record (same window = same words), so this is benign. No failure scenario found.

## (b) Same speech twice / span crossing a window edge

**P1 — the time-overlap dedup (line 143) compares only within one video's window branch, which is correct, but it uses `kept` which is NOT cleared... wait, it is: `kept` is initialized inside the per-video loop (line 101: `caps, why_w, waiting, windows, kept = {}, [], 0, 0, []`), so it resets per video. ✔** Verified: the `for i, r in irs` window loop is inside the `for` over videos (the `by_vid` grouping at lines 66-71), and `kept` is re-created per video. Cross-video duplicates are correctly not deduped (different videos = different speech, even identical words — L-p "no delivered span is used again" is per-source). ✔

**P2 — the overlap test `a < sp.end and sp.start < b` (line 143) is strict, so two moments whose spans merely TOUCH (one ends exactly where the next begins, `sp1.end == sp2.start`) are NOT duplicates.** Whether that is right de

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 428 s finish=stop usage in 12428 / out 316 usd~0.070 (upper-bound price)

**Findings:**
- No P0/P1/P2 findings verifiable from diff. No concrete inputs -> wrong result scenarios (a)-(e) can be constructed from the provided code alone.
- (a) No: all shown lookups (context_integrity.py:10, package.py:216+229+234+243+252, speakers.py:265) use `.get("source_key") or video_id` / `src_of`; full-video path never injects source_key.
- (b) No: ledger_build.py:143 (`dup = next((mid for a, b, mid in kept if a < sp.end and sp.start < b)`) + 167 (`rec["source_key"] = key`) + per-`wsrc` reanchor (line 138) + test at 310-324 prevent same-speech or cross-edge clips.
- (c) No: full-video `if src is not None:` block (ledger_build.py:75-100) retains exact prior reanchor/seen/(vid,k0,k1) logic and `sources[vid]`.
- (d) Uncertain (downstream pin/render/novelty/dedup not present in diff).
- (e) No: all tests updated to assert new per-moment window + dedup + src_of behavior (e.g. test at 296-325, 333/351 now use `m["source_key"]`); they would pass the diff and fail the pre-change 63/74-row loss.

**Verdict**  
SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 47 s finish=stop usage in 13628 / out 3242 usd~0.090 (upper-bound price)

I’ll audit the diff strictly against the five questions, using only what is visible in the provided patch.

## Findings

### P1 — `speakers.attribute_package` may pass `None` as the Source for window moments (fail-open risk)
**File:** `pipeline/speakers.py` (diff line 265)

```python
src, meta = sources.get(s.get("source_key") or s["video_id"]), meta_for(s["video_id"])
```

**Scenario:**
1. A window moment is packaged with `source_key = "vidW@600.000-645.000"`.
2. `sources` is keyed by that `source_key` (per `ledger_build.py` line 174: `sources[key] = wsrc`).
3. If the package segment **lacks** the `source_key` field (e.g., an older package, a serialization bug, or a code path that drops it), the lookup falls back to `s["video_id"]` → `"vidW"`.
4. `sources.get("vidW")` returns `None` because the window path **never** inserts a `video_id`-keyed Source (only the full-video path does, at line 99).
5. `attribute(router, s, None, meta)` is called with `src=None`.

**Why this matters:** The diff does not show `attribute()`’s body. If it dereferences `src` (e.g., `src.words`, `src.window`), this is a crash. If it treats `None` as “no source” and returns a default/empty speaker record, it **silently produces an unmeasured speaker attribution**, violating L-m (“nothing measured is never a pass”) and L-j (fail closed). The full-video path is safe because `sources[vid]` is always set. The window path has no such guarantee for the fallback key.

**Contrast with other call sites:** `package.py`’s `src_of()` (line 218) uses `sources[x.get("source_key") or x["video_id"]]` with **direct indexing** (`[]`), which raises `KeyError` if the key is missing — fail-closed. `speakers.py` uses `.get()` — fail-open. This inconsistency is a defect.

**Fix:** Use `src_of(s, sources)` (which raises) or explicitly check for `None` and mark the segment as unmeasured/failed.

---

### P1 — `context_integrity.contexts_from_sources` uses direct indexing but the fallback key may not exist
**File:** `pipeline/context_integrity.py` (diff line 10)

```python
src = sources[seg.get("source_key") or seg["video_id"]]
```

**Scenario:**
1. A window segment has `source_key = "vidW@600.000-645.000"`.
2. `sources` is keyed by that `source_key`.
3. If `source_key` is present, the lookup succeeds.
4. If `source_key` is **absent** (serialization loss, older package), the fallback is `seg["video_id"]` → `"vidW"`.
5. `sources["vidW"]` raises `KeyError` because the window path never inserts a `video_id`-keyed Source.

**Why this is P1, not P0:** The `KeyError` is fail-closed (it crashes, it does not silently pass). However, it means that **any** window segment that loses its `source_key` in transit will crash the context-integrity gate rather than being cleanly rejected with a diagnostic. The `speakers.py` case is worse because it may not crash. This is a robustness gap: the two lookup sites disagree on failure mode.

**Note:** The diff shows `_package` (line 207) conditionally includes `source_key`:
```python
**({"source_key": m["source_key"]} if m.get("source_key") else {})
```
So a moment **without** a `source_key` (full-video path) will not have the field in the segment. That is correct for full-video moments (keyed by `video_id`). But if a **window** moment somehow loses its `source_key` before packaging, the segment will fall back to `video_id` and crash here. The risk is low if `source_key` is always set for window moments (which the diff shows it is, line 167), but the failure mode is a crash, not a clean rejection.

---

### P2 — `window_records` report structure change may break downstream consumers
**File:** `pipeline/ledger_build.py` (diff line 137)

```python
report["window_records"].setdefault(vid, []).append(os.path.relpath(wpath, os.path.realpath(store)))
```

**Before:** `report["window_records"]` was `{video_id: path}` (a single path per video).
**After:** `report["window_records"]` is `{video_id: [path1, path2, ...]}` (a list of paths per video).

**Scenario:**
1. Any downstream code that reads `report["window_records"][vid]` expecting a string will now receive a list.
2. If that code does `os.path.basename(report["window_records"][vid])`, it will crash or produce garbage.
3. The diff does not show any downstream consumers of `report["window_records"]`, so I cannot verify whether this breaks anything.

**Why P2:** The diff is self-contained in the files shown. If no other code reads `window_records`, this is a non-issue. But the change in data structure is a breaking change for any external consumer. The log line (line 195) correctly uses `sum(len(v) for v in report["window_records"].values())`, so the internal logging is updated.

---

### P2 — `sources` count in report may be misleading
**File:** `pipeline/ledger_build.py` (diff line 185)

```python
report["moments"], report["sources"] = len(moments), len(sources)
```

**Scenario:**


## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of one window per moment: cycle 1 consensus (synthesis by the pp-selectid session, 02:17 ET Nov 13)

**Run.** C1_STEP.diff covers ledger_build.py, package.py, context_integrity.py, speakers.py and test_ledger_build.py.
No P0.
- grok-4.20-0309-reasoning (xAI): no findings, "SHIP: yes".
- qwen/qwen3.8-27b (Heimdall, effort none): two P1s on the lookups; "SHIP: no".
- z-ai/glm-5.3-flash (Heimdall, effort none): P1s on the lookups, the report schema, and consumers outside the diff.
  SHIP yes with conditions.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | the Source lookup existed in three copies with different failure modes: package.src_of raised KeyError on a missing key, while speakers.attribute_package used .get() and passed None (qwen P1 x2, glm P1) | IMPLEMENTED: ONE rule, context_integrity.source_for(x, sources) = sources[x.get("source_key") or x["video_id"]], which raises KeyError (fail closed). package.src_of and contexts_from_sources use it. speakers.attribute_package catches the KeyError, so the speaker is "unknown", not measured, with no call made; it never claims a name and never takes another Source. Test: a segment whose source_key is not in sources makes the gate's context check raise, and gives an unknown, unmeasured speaker |

## Unique findings: answered or kept (each verified)

- **glm P1 (coverage: consumers outside the diff may still look up by video id):** ANSWERED. A grep of every
  `sources[` / `sources.get(` in pipeline/ and the drivers finds the medley path's lookups only in source_for (via
  package.src_of, contexts_from_sources) and speakers. The other hits belong to other dictionaries that never see
  these Sources:
  - select_by_id.py: the older selector's own universe sources;
  - rank.py: a list named sources;
  - select_passages.py: the render's acquisition file paths.
  package_pin and the pin never read Sources. The render (the integrator's) uses each pin segment's video_id and
  times, and decodes its own window.
- **glm P1 (the report schema: window_records becomes a list, plus new counts):** KEPT. The report is read only by the
  driver's log line and saved in inputs.json as proof; no code consumes it.
- **qwen ("unmeasured speaker attribution violates L-m"):** KEPT, as disposed in audit 0007 K2. "unknown" with
  measured false claims no name; L-m governs gates, and this record is not one.

## Verification

- 11 offline suites, 234 tests OK; regression_test.sh 26 PASS | 0 FAIL | 5 WARN (run before this fix).
- test_ledger_build, test_medley, test_speakers and test_gates are re-run after the fix: OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0208/C2_STEP.diff (379 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index 55202f0b..487cacb9 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -291,11 +291,18 @@ def _strict(raw, top, item_keys):
   6 |      return obj
   7 |  
   8 |  
   9 | +def source_for(x, sources):
  10 | +    """THE lookup of a moment's (or a package segment's) own Source, in one place (audit 0208 C1: glm, qwen): a WINDOW
  11 | +    moment's by its source_key (one window record per moment; ledger_build.build_inputs), every other one's by its video
  12 | +    id. A key missing from `sources` raises KeyError: fail closed, never another Source."""
  13 | +    return sources[x.get("source_key") or x["video_id"]]
  14 | +
  15 | +
  16 |  def contexts_from_sources(package, sources, now=None):
  17 |      """{label: {"text": the window with <selected> marks, "title", "channel", "published", "show_date", "window"}}."""
  18 |      out = {}
  19 |      for seg in package["segments"]:
  20 | -        src = sources[seg["video_id"]]
  21 | +        src = source_for(seg, sources)                              # a window segment's own Source (one per moment)
  22 |          w = seg.get("words") or (None, None)
  23 |          text, win = _window_text(src, seg["k0"], seg["k1"], w[0], w[1])
  24 |          if text is None:
  25 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
  26 | index b45f33b5..d3a7ce26 100644
  27 | --- a/pipeline/ledger_build.py
  28 | +++ b/pipeline/ledger_build.py
  29 | @@ -385,21 +385,44 @@ def reanchor(row, src):
  30 |  
  31 |  
  32 |  def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store=None):
  33 | -    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). word_pass: word_pass_index()'s
  34 | -    {moment_id: row} (None = no window records). Rows on a video with neither a sentence-ready full-video word record
  35 | -    nor a sentence-ready window record, rows whose text does not re-anchor on whole sentences, and duplicates of one
  36 | -    span are dropped, each counted with why."""
  37 | +    """Ledger rows -> (moments in the packager's form, {key: Source}, report). word_pass: word_pass_index()'s
  38 | +    {moment_id: row} (None = no window records).
  39 | +    - A video with a sentence-ready full-video word record: every row re-anchors in it (key: the video id).
  40 | +    - Otherwise ONE WINDOW PER MOMENT, the word-pass worker writing one around each moment. A row with its own
  41 | +      sentence-ready window record re-anchors in THAT window, and its moment carries source_key =
  42 | +      "<video>@<w0>-<w1>", its Source's key (the packager looks every moment up by source_key, else by video_id). The
  43 | +      first FRESH build kept one window per video and lost 63 of 74 rows. Two window moments of one video whose spans
  44 | +      overlap in time are one moment: the better-ranked row (rows arrive best first) keeps it.
  45 | +    Rows with no word record, rows that do not re-anchor on whole sentences, and duplicates are dropped, each counted
  46 | +    with why."""
  47 |      word_pass = word_pass or {}
  48 |      report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "no_word_record_videos": {},
  49 | -              "window_records": {}, "window_passed_over": {}, "no_caption_context": {},
  50 | +              "window_records": {}, "window_waiting": 0, "window_passed_over": {}, "no_caption_context": {},
  51 |                "fallbacks": {},
  52 |                "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "duplicates_of": {},
  53 | -              "moments": 0, "videos": 0,
  54 | +              "moments": 0, "videos": 0, "sources": 0,
  55 |                "word_records": {}}
  56 |      def malformed(i, r, why):                     # counted under a key no other row can take (qwen C3, glm C3 P1-4)
  57 |          mid = r.get("moment_id") if isinstance(r, dict) else None
  58 |          report["malformed"][mid if isinstance(mid, str) and mid and mid not in report["malformed"] else f"row {i}"] = why
  59 |  
  60 | +    def make(i, r, sp, info, src):
  61 | +        try:
  62 | +            m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
  63 | +                 "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
  64 | +                 "reason": r.get("reason") or ""}
  65 | +            mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
  66 | +                         ledger_text=r.get("text"))
  67 | +            if getattr(src, "window", None) is not None:          # provenance: the window record it was cut from
  68 | +                mined["window"] = dict(src.window, context_record=(getattr(src.context_source, "transcript_method",
  69 | +                                                                            None)))
  70 | +            rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
  71 | +            rec["rank_score"] = M.rank_score(rec)
  72 | +            return rec
  73 | +        except (KeyError, TypeError, ValueError) as e:         # counted, never a crash (glm C1 P1-8)
  74 | +            malformed(i, r, f"{type(e).__name__}: {str(e)[:120]}")
  75 | +            return None
  76 | +
  77 |      by_vid = {}
  78 |      for i, r in enumerate(rows):
  79 |          if not (isinstance(r, dict) and all(isinstance(r.get(k), str) and r.get(k) for k in ("moment_id", "video_id"))):
  80 | @@ -414,67 +437,80 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
  81 |              report["channel_conflict"][vid] = {"rows": len(rs), "channel_ids": channels}
  82 |              continue
  83 |          src, path, passed_over = word_source(rs[0], ctx, store)
  84 | -        if src is None:                         # the WINDOW path: the best-ranked row of this video with a
  85 | -            wrow, why_w = None, []              # sentence-ready window record (rows arrive best first)
  86 | +        if src is not None:                          # the video's full-video word record: every row re-anchors in it
  87 | +            if passed_over:
  88 | +                report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
  89 | +            report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
  90 |              for i, r in irs:
  91 | -                wp = word_pass.get(r["moment_id"])
  92 | -                if wp is None:
  93 | +                sp, info = reanchor(r, src)
  94 | +                if sp is None:
  95 | +                    report["not_anchored"][r["moment_id"]] = info
  96 | +                    continue
  97 | +                if (vid, sp.k0, sp.k1) in seen:
  98 | +                    report["duplicates"] += 1
  99 | +                    report["duplicates_of"][r["moment_id"]] = seen[(vid, sp.k0, sp.k1)]   # named (glm C4 P2-5)
 100 | +                    continue
 101 | +                rec = make(i, r, sp, info, src)
 102 | +                if rec is None:
 103 |                      continue
 104 | -                cand, cpath, why = window_source(r, wp, ctx, store)
 105 | -                if cand is not None:
 106 | -                    src, path, wrow = cand, cpath, r
 107 | -                    break
 108 | +                seen[(vid, sp.k0, sp.k1)] = r["moment_id"]
 109 | +                moments.append(rec)
 110 | +                sources[vid] = src
 111 | +            continue
 112 | +        caps, why_w, waiting, windows, kept = {}, [], 0, 0, []     # kept: (start, end, moment id) of window moments
 113 | +        for i, r in irs:                             # ONE WINDOW PER MOMENT
 114 | +            wp = word_pass.get(r["moment_id"])
 115 | +            if wp is None:
 116 | +                waiting += 1
 117 | +                continue
 118 | +            wsrc, wpath, why = window_source(r, wp, ctx, store)
 119 | +            if wsrc is None:
 120 |                  why_w.append(f"{r['moment_id']}: {why}")
 121 | -            if why_w:
 122 | -                report["window_passed_over"][vid] = why_w
 123 | -            if src is None:
 124 | -                why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
 125 | -                                               ["no sentence-ready window record"]))
 126 | -                report["no_word_record"] += len(rs)
 127 | -                report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 128 | -                report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 129 |                  continue
 130 | -            src.context_source, cwhy = caption_source(wrow, ctx, store, ledger_store)
 131 | -            if src.context_source is None:
 132 | -                src.context_source = None
 133 | -                report["no_caption_context"][vid] = cwhy          # L-s fails closed for this video's clips
 134 | -            report["window_records"][vid] = os.path.relpath(path, os.path.realpath(store))
 135 | -        elif passed_over:
 136 | -            report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
 137 | -        if getattr(src, "window", None) is None:
 138 | -            report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
 139 | -        for i, r in irs:
 140 | -            sp, info = reanchor(r, src)
 141 | +            windows += 1
 142 | +            sha = r.get("transcript_sha256")
 143 | +            if sha not in caps:                      # the caption record the row was mined from, once per sha
 144 | +                caps[sha] = caption_source(r, ctx, store, ledger_store)
 145 | +            wsrc.context_source, cwhy = caps[sha]
 146 | +            if wsrc.context_source is None:
 147 | +                report["no_caption_context"][vid] = cwhy               # L-s fails closed for these clips
 148 | +            report["window_records"].setdefault(vid, []).append(os.path.relpath(wpath, os.path.realpath(store)))
 149 | +            sp, info = reanchor(r, wsrc)
 150 |              if sp is None:
 151 |                  report["not_anchored"][r["moment_id"]] = info
 152 |                  continue
 153 | -            if (vid, sp.k0, sp.k1) in seen:
 154 | +            dup = next((mid for a, b, mid in kept if a < sp.end and sp.start < b), None)
 155 | +            if dup is not None:                      # the same speech, cut from another of the video's windows
 156 |                  report["duplicates"] += 1
 157 | -                report["duplicates_of"][r["moment_id"]] = seen[(vid, sp.k0, sp.k1)]       # named (glm C4 P2-5)
 158 | +                report["duplicates_of"][r["moment_id"]] = dup
 159 |                  continue
 160 | -            try:
 161 | -                m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
 162 | -                     "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
 163 | -                     "reason": r.get("reason") or ""}
 164 | -                mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 165 | -                             ledger_text=r.get("text"))
 166 | -                if getattr(src, "window", None) is not None:      # provenance: the window record it was cut from
 167 | -                    mined["window"] = dict(src.window, context_record=(getattr(src.context_source, "transcript_method",
 168 | -                                                                                None)))
 169 | -                rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
 170 | -                rec["rank_score"] = M.rank_score(rec)
 171 | -            except (KeyError, TypeError, ValueError) as e:     # counted, never a crash (glm C1 P1-8)
 172 | -                malformed(i, r, f"{type(e).__name__}: {str(e)[:120]}")
 173 | +            rec = make(i, r, sp, info, wsrc)
 174 | +            if rec is None:
 175 |                  continue
 176 | -            seen[(vid, sp.k0, sp.k1)] = r["moment_id"]
 177 | +            key = f"{vid}@{wsrc.window['start_s']:.3f}-{wsrc.window['end_s']:.3f}"
 178 | +            rec["source_key"] = key
 179 | +            kept.append((sp.start, sp.end, r["moment_id"]))
 180 |              moments.append(rec)
 181 | -            sources[vid] = src
 182 | -    report["moments"], report["videos"] = len(moments), len(sources)
 183 | -    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} word records; "
 184 | -        f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
 185 | +            sources[key] = wsrc
 186 | +        if why_w:
 187 | +            report["window_passed_over"][vid] = why_w
 188 | +        if not windows:
 189 | +            why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
 190 | +                                           ["no sentence-ready window record"]))
 191 | +            report["no_word_record"] += len(rs)
 192 | +            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 193 | +            report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 194 | +        else:
 195 | +            report["window_waiting"] += waiting      # rows of a window video with no window record of their own
 196 | +    report["moments"], report["sources"] = len(moments), len(sources)
 197 | +    report["videos"] = len({m["video_id"] for m in moments})
 198 | +    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} videos "
 199 | +        f"({report['sources']} word records); {report['no_word_record']} rows wait for a word record, "
 200 | +        f"{report['window_waiting']} wait for their own window, {len(report['not_anchored'])} do not re-anchor, "
 201 |          f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
 202 |          f"{len(report['channel_conflict'])} video(s) name more than one channel, "
 203 | -        f"{len(report['fallbacks'])} read from a fallback record; {len(report['window_records'])} window record(s) "
 204 | -        f"used ({len(report['no_caption_context'])} without a caption record for L-s)")
 205 | +        f"{len(report['fallbacks'])} read from a fallback record; "
 206 | +        f"{sum(len(v) for v in report['window_records'].values())} window record(s) used "
 207 | +        f"({len(report['no_caption_context'])} video(s) without a caption record for L-s)")
 208 |      moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
 209 |      return moments, sources, report
 210 | diff --git a/pipeline/package.py b/pipeline/package.py
 211 | index 8d8ae6a4..74ea177c 100644
 212 | --- a/pipeline/package.py
 213 | +++ b/pipeline/package.py
 214 | @@ -283,6 +283,7 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
 215 |      pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
 216 |            "vo_kind": vo_kind, "style": fields.get("style"),
 217 |            "segments": [{"label": lb, "moment_id": m["moment_id"],
 218 | +                        **({"source_key": m["source_key"]} if m.get("source_key") else {}),   # a window moment's
 219 |                          "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
 220 |                          "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 221 |                          "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 222 | @@ -358,6 +359,11 @@ def _load_store(store):
 223 |          return json.load(f)
 224 |  
 225 |  
 226 | +def src_of(x, sources):
 227 | +    """A moment's (or a package segment's) own Source: context_integrity.source_for, the one lookup rule."""
 228 | +    return CI.source_for(x, sources)
 229 | +
 230 | +
 231 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 232 |                store=None, log=print):
 233 |      """Step A (context only, package-independent by law L-s) on the best n usable moments, distinct channels first:
 234 | @@ -389,11 +395,11 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 235 |          chunk = todo[i:i + batch]
 236 |          contexts = {}
 237 |          for m in chunk:
 238 | -            text, win = CI._window_text(sources[m["video_id"]], m["sentences"][0], m["sentences"][1], *m["words"])
 239 | +            text, win = CI._window_text(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])
 240 |              if text is None:        # no L-s context (a window record without its caption record, short coverage, an
 241 |                  fails[m["moment_id"]] = ["CONTEXT_UNAVAILABLE: no L-s context for this moment (law L-s)"]   # unclocked
 242 |                  continue            # moment): THIS moment is not cleared; it never poisons its batch's call
 243 | -            contexts[m["moment_id"]] = {"text": text, "title": sources[m["video_id"]].title or "",
 244 | +            contexts[m["moment_id"]] = {"text": text, "title": src_of(m, sources).title or "",
 245 |                                          "channel": _name(m, ctx), "window": win,
 246 |                                          "published": str(m.get("published_at") or "")[:16],
 247 |                                          "show_date": ctx.now.strftime("%Y-%m-%d")}
 248 | @@ -865,7 +871,7 @@ def exclusion_for(router, m, sources, cache, seed=7):
 249 |      key = m["moment_id"] if seed == 7 else (m["moment_id"], seed)
 250 |      if key not in cache:
 251 |          import moments as M
 252 | -        src = sources[m["video_id"]]
 253 | +        src = src_of(m, sources)
 254 |          before, after = CI.context_around(src, m["sentences"][0], m["sentences"][1], *m["words"])
 255 |          if before is None:                                    # no context to judge in (a window record without its
 256 |              cache[key] = {"verdict": "exclude", "why": "no context: the moment's context is unavailable",   # caption
 257 | @@ -922,7 +928,7 @@ def hook_onset_for(m, sources, work_dir, cache):
 258 |      if m["moment_id"] not in cache:
 259 |          import hook_onset as HO
 260 |          try:
 261 | -            cache[m["moment_id"]] = HO.measure(sources[m["video_id"]], m["words"][0], m["words"][1], m["video_id"],
 262 | +            cache[m["moment_id"]] = HO.measure(src_of(m, sources), m["words"][0], m["words"][1], m["video_id"],
 263 |                                                 float(m["start"]), float(m["end"]), work_dir)
 264 |          except Exception as e:
 265 |              cache[m["moment_id"]] = {"pass": False, "measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 266 | diff --git a/pipeline/speakers.py b/pipeline/speakers.py
 267 | index 155fd48c..40fa33b4 100644
 268 | --- a/pipeline/speakers.py
 269 | +++ b/pipeline/speakers.py
 270 | @@ -182,7 +182,12 @@ def attribute(router, seg, src, meta, seed=7):
 271 |  def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
 272 |      """Every segment of a package gets its speaker record, in place (before the pin is sealed)."""
 273 |      for i, s in enumerate(pk["segments"]):
 274 | -        src, meta = sources.get(s["video_id"]), meta_for(s["video_id"])
 275 | +        import context_integrity as CI
 276 | +        try:
 277 | +            src = CI.source_for(s, sources)                   # the one lookup rule (audit 0208 C1: glm, qwen)
 278 | +        except KeyError:
 279 | +            src = None                                        # -> "unknown", not measured: never a name
 280 | +        meta = meta_for(s["video_id"])
 281 |          sp = attribute(router, s, src, meta)
 282 |          if not sp["measured"] and sp["why"].startswith("not measured"):      # once more, a new sample (C1 K2)
 283 |              sp = attribute(router, s, src, meta, seed=8)
 284 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 285 | index 4417ea1e..b99d2ddc 100644
 286 | --- a/tests/package/test_ledger_build.py
 287 | +++ b/tests/package/test_ledger_build.py
 288 | @@ -440,13 +440,14 @@ class TestWindowRecords(unittest.TestCase):
 289 |          with tempfile.TemporaryDirectory() as d:
 290 |              rel, wp, r, words = window_fixture(d)
 291 |              far = dict(row("Bitcoin started as a quiet experiment.", start=100.0, end=104.0, mid="W2", vid="vidW"),
 292 | -                       transcript_sha256=r["transcript_sha256"])               # outside the window: it cannot anchor
 293 | +                       transcript_sha256=r["transcript_sha256"])               # no window record of its own
 294 |              ms, srcs, rep = LB.build_inputs([r, far], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 295 |              self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["W1"])
 296 |              self.assertEqual(ms[0]["text"], SENTS_W[2])
 297 | -            self.assertEqual(list(rep["not_anchored"]), ["W2"])
 298 | -            self.assertEqual(rep["window_records"], {"vidW": rel})
 299 | -            src = srcs["vidW"]
 300 | +            self.assertEqual((list(rep["not_anchored"]), rep["window_waiting"]), ([], 1))   # it waits for its own
 301 | +            self.assertEqual(rep["window_records"], {"vidW": [rel]})
 302 | +            self.assertEqual(ms[0]["source_key"], f"vidW@600.000-{wp['window'][1]:.3f}")   # one window per moment
 303 | +            src = srcs[ms[0]["source_key"]]
 304 |              self.assertEqual(src.context_source.transcript_method, "yt_auto")
 305 |              text, win = CI._window_text(src, ms[0]["sentences"][0], ms[0]["sentences"][1], *ms[0]["words"])
 306 |              t0 = words[[w["word"] for w in words].index("Nobody")]["start"]
 307 | @@ -460,6 +461,44 @@ class TestWindowRecords(unittest.TestCase):
 308 |              self.assertIn("caption line", before)
 309 |              self.assertIn("caption line", after)
 310 |  
 311 | +    def test_each_moment_reads_its_own_window_and_the_same_speech_twice_is_one_moment(self):
 312 | +        """The 02:01 FRESH build kept ONE window per video and lost 63 of 74 rows. The worker writes a window around
 313 | +        every moment, so each moment re-anchors in its OWN window (its source_key); two windows holding the same
 314 | +        speech give one moment (the better-ranked row keeps it)."""
 315 | +        ctx = E.Context(NOW, REG)
 316 | +        with tempfile.TemporaryDirectory() as d:
 317 | +            rel1, wp1, r1, words1 = window_fixture(d, w0=600.0)               # W1: "Nobody can stop Bitcoin ..."
 318 | +            rel2, wp2, r2, words2 = window_fixture(d, w0=640.0)               # W2: the same sentences, 40 s later
 319 | +            k = [w["word"] for w in words2].index("That")
 320 | +            n = len(SENTS_W[3].split())
 321 | +            r2 = dict(row(SENTS_W[3], start=words2[k]["start"], end=words2[k + n - 1]["end"], mid="W2", vid="vidW"),
 322 | +                      transcript_sha256=r1["transcript_sha256"])
 323 | +            wp2 = dict(wp2, moment_id="W2")
 324 | +            r3 = dict(r1, moment_id="W3")                                    # W1's speech again (W1's window record)
 325 | +            ms, srcs, rep = LB.build_inputs([r1, r2, r3], ctx, d, log=lambda s: None,
 326 | +                                            word_pass={"W1": wp1, "W2": wp2, "W3": dict(wp1, moment_id="W3")})
 327 | +            self.assertEqual(sorted(m["mined"]["ledger_moment_id"] for m in ms), ["W1", "W2"])
 328 | +            keys = {m["mined"]["ledger_moment_id"]: m["source_key"] for m in ms}
 329 | +            self.assertNotEqual(keys["W1"], keys["W2"])                       # two windows, two Sources
 330 | +            self.assertEqual(set(srcs), set(keys.values()))
 331 | +            self.assertEqual(rep["duplicates_of"], {"W3": "W1"})              # the same speech: one moment
 332 | +            self.assertEqual((rep["videos"], rep["sources"]), (1, 2))
 333 | +            import context_integrity as CI                                     # the gate reads each segment's own
 334 | +            m2 = next(m for m in ms if m["mined"]["ledger_moment_id"] == "W2")  # window (package.src_of's key)
 335 | +            seg = {"label": "clip_01", "video_id": "vidW", "source_key": m2["source_key"], "k0": m2["sentences"][0],
 336 | +                   "k1": m2["sentences"][1], "words": m2["words"], "channel": "DataDash"}
 337 | +            got = CI.contexts_from_sources({"segments": [seg]}, srcs)
 338 | +            self.assertIn("<selected>" + SENTS_W[3] + "</selected>", got["clip_01"]["text"])
 339 | +            self.assertIn("caption line", got["clip_01"]["text"])
 340 | +            lost = dict(seg, source_key="vidW@1.000-2.000")                   # a key that is not in sources: the
 341 | +            with self.assertRaises(KeyError):                                 # gate fails closed (one lookup rule,
 342 | +                CI.contexts_from_sources({"segments": [lost]}, srcs)         # audit 0208 C1: glm, qwen) ...
 343 | +            import speakers as SP                                             # ... and the speaker is "unknown",
 344 | +            pk = {"segments": [dict(lost)]}                                   # not measured, with no call made
 345 | +            SP.attribute_package(None, pk, srcs, meta_for=lambda v: {"exact_title": "t"}, log=lambda s: None)
 346 | +            self.assertEqual((pk["segments"][0]["speaker"]["name"], pk["segments"][0]["speaker"]["measured"]),
 347 | +                             ("unknown", False))
 348 | +
 349 |      def test_the_caption_coverage_is_measured_never_assumed(self):
 350 |          """Audit 0123 C1 (qwen, glm): a caption that stops short of 60 s after the clip (and short of the media's end),
 351 |          or starts after the 90 s before it (and not near the media's start), leaves the context unavailable."""
 352 | @@ -473,7 +512,7 @@ class TestWindowRecords(unittest.TestCase):
 353 |                  rel, wp, r, words = window_fixture(d, **kw)
 354 |                  ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 355 |                  m = ms[0]
 356 | -                text, win = CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"])
 357 | +                text, win = CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"])
 358 |                  self.assertEqual(text is not None, ok, kw)
 359 |  
 360 |      def test_a_wordless_stretch_inside_the_window_is_bridged_to_reach_the_marks(self):
 361 | @@ -486,7 +525,7 @@ class TestWindowRecords(unittest.TestCase):
 362 |              ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 363 |              m = ms[0]
 364 |              t0 = words[[w["word"] for w in words].index("Nobody")]["start"]
 365 | -            text, win = CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"])
 366 | +            text, win = CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"])
 367 |              self.assertLessEqual(win[0], t0 - CI.CONTEXT_BEFORE_S)          # it reaches past the gap
 368 |              self.assertLess(win[0], 515.0)                                     # a word from before the gap ...
 369 |              self.assertTrue(text.startswith("money caption line 585"))        # ... ("money", the last word of line 510)
 370 | @@ -585,7 +624,7 @@ class TestWindowRecords(unittest.TestCase):
 371 |              self.assertEqual(rep["no_caption_context"], {"vidW": "no record in the store matches the row's "
 372 |                                                                    "transcript_sha256"})
 373 |              m = ms[0]
 374 | -            self.assertEqual(CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"]),
 375 | +            self.assertEqual(CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"]),
 376 |                               (None, None))                                 # step A: unavailable, never cleared
 377 |              ex = PK.exclusion_for(None, m, srcs, {})                       # no model call is made
 378 |              self.assertEqual((ex["verdict"], ex["measured"]), ("exclude", False))
 379 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
It moves the ledger build from ONE window record per video to ONE WINDOW RECORD PER MOMENT.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: the integrator's word-pass worker writes a sentence-ready window record (about +-45 s of words) around EACH
ledger moment. The FRESH build at 02:01 ET used one window per video (the best-ranked row's). 63 of 74 fresh rows
therefore could not re-anchor, which left 11 moments and no package.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- clips are verbatim WHOLE sentences of a sentence-ready, word-timed record (L-o 1, L-e);
- L-s context (>= 90 s before, 60 s after) for a window clip comes from the caption record the ledger mined, by time;
- no delivered span is used again (L-p).

The change:
1. pipeline/ledger_build.py build_inputs():
   - A video WITH a sentence-ready full-video word record: unchanged. Every row re-anchors in it, with the
     (vid, k0, k1) dedup, and the Source is keyed by the video id.
   - Otherwise each row with its OWN sentence-ready window record (window_source(): every claim checked) re-anchors
     in THAT window. Its moment carries source_key = "<video>@<w0>-<w1>", the key of its Source in the returned
     sources.
   - The caption record for L-s is looked up once per mined sha.
   - Two window moments of one video whose spans overlap in TIME are one moment: the better-ranked row (rows arrive
     best first) keeps it, and the other is counted in duplicates_of.
   - Rows of a window video without their own window record are counted in window_waiting.
   - The report adds sources and videos counts, and window_records becomes {video: [records]}.
2. pipeline/package.py:
   - src_of(x, sources) = sources[x.get("source_key") or x["video_id"]], used by prescreen (step A), exclusion_for
     and hook_onset_for.
   - _package's segment rows carry source_key when the moment has one.
3. pipeline/context_integrity.py contexts_from_sources() and pipeline/speakers.py attribute_package(): look the
   segment's Source up by source_key, else video_id.
4. tests/package/test_ledger_build.py:
   - two windows of one video give two moments with two Sources;
   - the same speech in two windows is one moment;
   - the gate's context check reads the segment's own window;
   - the existing window tests use each moment's source_key.

Check, concretely:
(a) Can any lookup still reach the WRONG window or Source for a moment or segment, e.g. one keyed by video_id when a
    source_key exists?
(b) Can the same speech enter two clips through two overlapping windows, or a span cross a window's edge?
(c) Is anything in the full-video path changed?
(d) Does anything downstream (pin, render, novelty, dedup, speakers) still assume one Source per video?
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
