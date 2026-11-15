# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_0951
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 89 s finish=stop usage in 12074 / out 2434 usd_reported=0.000676 usd~0.073 (upper-bound price)

# Audit: pp-selectid — the word pass's refused moments, counted apart from the waiting

Scope: 5 files (ledger_build.py, spotlight.py, funnel.py, proof_ledger.py, 3 test files). Reporting-only change; I checked it against the stated claim "no gate, verdict or selection changes; no moment enters or leaves a build."

## Findings

**[P1] `word_pass_index`'s "refused" can disagree with what the worker will actually re-work — the last-row rule is asserted, not proven.** The docstring and the finding both state the worker "never works a moment again once it has a row (its passed_ids)". The refused set is computed as `set(last) - set(out)`, i.e. *every* moment that has a row but no ready record. But the worker's passed_ids semantics are not in this diff. If the worker's passed_ids are only the moments it *succeeded* on (a common worker pattern: record failures in a separate failures file, retry failures next pass), then a failed/not-ready moment **will** be re-worked, and "refused: never re-worked" is a wrong report — exactly the class of error this change exists to fix. The test `test_the_refused_are_the_moments_whose_last_row_gives_no_window` only tests the index function against a hand-built fixture; nothing in this diff pins the index's classification to the worker's actual passed_ids. If the worker lives elsewhere (it does — it's not in this diff), there should be a test (or a cross-reference in the docstring naming the worker's file/constant) that the two agree. As written, the invariant "refused == never re-worked" rests on the integrator's 09:37 statement alone. Fix: either add the worker's passed_ids/row-writing code path to the tested surface, or cite it precisely and add a guard test that fails if the worker's row-writing semantics change. (Severity: it's a reporting-only change, so no wrong verdict — but the report is the product here, and its one new fact is unverified. P1 is defensible; if the worker's semantics are documented elsewhere and you're confident, call it P2.)

**[P2] `build_inputs`: a moment in `refused` whose row IS in `word_pass` but fails `window_source` is counted neither refused nor waiting — it silently becomes `window_failed`/`window_passed_over`, which is correct, but the refused count in the report can then exceed the rows the video actually lost.** Trace: `wp = word_pass.get(mid)`; if `wp is not None` the row never reaches the `n_ref` branch, so a moment that is in `refused` (per the report) *and* has a ready row (per the index) is counted as... neither. That's actually consistent (it's ready), but note the index's `refused` and its `out` are disjoint by construction, so this can't happen — *unless* the caller passes a stale `word_pass` map with a fresher `refused` list (proof_ledger.py:162-169 reads both from one call, so it's safe there; the driver test passes `wp_rep` while the stubbed `word_pass_index` returns `({}, dict(wp_rep))` — also consistent). Fine as wired, but the function's contract doesn't say the two arguments must come from the same `word_pass_index` call. One docstring sentence would prevent a future caller from splitting them. P2/P3.

**[P2] `next_attempt`: `word_pass_waiting = len(rs) - ready - n_ref` can go negative.** `n_ref` counts rows where `mid in refused and mid not in word_pass`; `ready` counts rows where `word_pass.get(mid, {}).get("sentence_ready")`. These are disjoint *given* the guard `mid not in word_pass`, so waiting = rows − ready − refused ≥ 0... but only if `refused` and the keys of `word_pass` are disjoint, which is the same cross-argument invariant as above. With a stale/mismatched pair, `waiting` goes negative and the ruling-95 log line prints a negative count. The test only exercises the consistent case. Cheap fix: `max(0, ...)` or an assert. P2.

**[P2] The no-window branch's `len(rs) > n_ref` condition changes behavior for the all-refused video in a way the log line doesn't explain.** When every row of a video is refused, the video now produces *no* `no_word_record_videos` entry at all. The funnel script (tests/package/funnel.py) sums `no_word_record_why` and `window_waiting`/`window_refused` into supply lines; a video that vanished from `no_word_record_videos` is invisible in the per-video report, and its rows appear only in the aggregate `window_refused`. For a reporting change whose stated purpose is "the STATE line says the watcher would build when they land: they never will", the all-refused video is precisely the case that most needs a per-video line, and it's the one case that now has none. Consider: when `n_ref == len(rs)` and no windows, still emit a `no_word_record_videos[vid] = {"rows": 0, "why": "all rows refused by the word pass"}` (or a parallel `refused_videos` map). P2.

**[P3] `rep["refused"] = sorted(mid for mid in last if mid not in out)` — `last` maps moment_id → last row; the comprehen

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 38 s finish=stop usage in 12097 / out 760 usd_reported=0.027769 usd~0.079 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_0951 (C1_STEP.diff)**

**Summary**  
The diff is a narrowly-scoped reporting-only change. It adds `report["refused"]` (moments whose *last* row is non-ready/failed/unreadable) in `word_pass_index`, threads that list into `build_inputs` and `spotlight.next_attempt`, updates the derived counts (`window_refused`, `word_pass_refused`), adjusts the no-word-record path so an all-refused video is not counted as “waiting for a record it will never receive,” and updates logs/tests accordingly. No selection, anchoring, sentence-law, punctuation, gate, EDL, render, release-auth, or byte-producing path is touched. The original mis-count (refused moments appearing as “waiting”) is fixed exactly as described by the integrator note. All governing laws are satisfied: the change is purely diagnostic, cannot alter which moments enter a build, cannot cause a gate to pass what it must refuse, preserves L-j/L-k/L-l fail-closed behavior, leaves v2f and the protected preview untouched, and uses only canonical forms for strings. Tests (including the new ones) pass, 12/14 mutations killed; the two survivors are in unreachable driver-after-router and non-CI report-script paths.

**Findings**  
[P3] `word_pass_index` docstring update is accurate but could explicitly state “last row per `moment_id` wins for both the ready index *and* the refused list” to match the test name and integrator comment.  
[P3] `spotlight.next_attempt` line `r.get("moment_id") not in word_pass` is defensive (refused list is already disjoint) and harmless, but adds a tiny amount of redundant work on every call.  
[P3] `build_inputs` `if not windows and len(rs) > n_ref` branch correctly subtracts refused rows from `no_word_record*` counters and per-video dicts; the all-refused video exclusion is intentional and documented in the new comment, but the control-flow (n_ref incremented in the None-wp path, added after the per-video loop) is subtle and merits a one-line inline comment at the `report["window_refused"] += n_ref` site.  
[P2] The two surviving mutations (driver ruling-95 path when router is mocked out, and `funnel.py` report script) are acceptable given current test coverage, but a future change that exercised the full driver past the router or ran funnel in CI would make them live. Recommend a trivial follow-up test that forces the “no refused= argument” code path in the driver (already partially covered) to reach 14/14.  
[P3] Log string and JSON keys now expose “refused” count/ids; this is useful debugging data and stays inside the audit pack (inputs.json, package.log). No PII or secret material added.  
[P3] All new test assertions match the described semantics (last-row-wins, no double-counting, backward-compat when refused= omitted, vidY/vidZ/vidX cases). Test coverage for the no-window branch is adequate.

No violations of SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, LAW 20/M2, M12 FAIL CLOSED, or the protected-preview reference. No new model calls, no renderer changes, GPU0-only, smallest diff. The fix prevents misleading “4 wait for their own window … when they land” messages for permanently refused Scott Melker moments.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 77 s finish=stop usage in 13224 / out 6999 usd_reported=0.005605 usd~0.145 (upper-bound price)

To perform this audit, I will analyze the provided diff against the "Governing Laws" and the specific "PLEASE CHECK" criteria.

### Analysis of the Code Change

**Context:** The change introduces a `refused` status for moments in the word-pass pipeline. Previously, moments that were not `sentence_ready` (either because they failed or were just not ready yet) were lumped into `waiting`. The integrator clarified that the worker *never* re-works a moment once it has a row. Therefore, a moment with a row that is not `sentence_ready` is permanently `refused`, not `waiting`.

**1. `pipeline/ledger_build.py` - `word_pass_index`**
*   **Change:** Adds `rep["refused"] = sorted(mid for mid in last if mid not in out)`.
*   **Logic Check:** `last` contains the moment IDs of the *last* row for each moment. `out` contains the moment IDs that are `sentence_ready` and have a valid `window_record` and `record_sha256`.
*   **Law Compliance (M12 Fail Closed):** If a row is unreadable or malformed, it won't be in `out`. If it's the last row, it will be in `last`. Thus, it goes into `refused`. This is correct. A failed moment is final.
*   **Check (1):** "The refused set is exactly what the worker will never re-work."
    *   The docstring states: "The worker never works a moment again once it has a row... so these are final, never 'waiting'."
    *   The code identifies moments where the *last* row is not in the `out` (ready) set. This aligns with the "last row wins" logic used for `out`.
    *   **Verdict:** Correct.

**2. `pipeline/ledger_build.py` - `build_inputs`**
*   **Change:** Accepts `word_pass_refused`.
*   **Logic Check:**
    *   `refused = set(word_pass_refused or ())`.
    *   Inside the loop for rows `irs` of a video `vid`:
        *   `wp = word_pass.get(r["moment_id"])`.
        *   If `wp is None`:
            *   If `r["moment_id"] in refused`: `n_ref += 1`.
            *   Else: `waiting += 1`.
    *   **Check (2):** "No row can be counted twice."
        *   A row either has a `wp` (window pass record) or it doesn't.
        *   If it has a `wp`, it goes through `window_source`. If that fails, it's `window_failed` or passed over. It is *not* counted in `n_ref` or `waiting` in the `wp is None` branch.
        *   If it has *no* `wp`, it is either in `refused` or `waiting`. These are mutually exclusive sets for a given moment ID in this context (a moment is either in the `refused` list or it isn't).
        *   **Verdict:** Correct.
    *   **Check (3):** "The no-window branch: no_word_record, its why counts and its per-video rows."
        *   Code:
            ```python
            if not windows and len(rs) > n_ref:
                # ...
                report["no_word_record"] += len(rs) - n_ref
                report["no_word_record_why"][why] = ... + len(rs) - n_ref
                report["no_word_record_videos"][vid] = {"rows": len(rs) - n_ref, "why": why}
            elif windows:
                report["window_waiting"] += waiting
            ```
        *   **Scenario A: Video has NO windows (`windows` is empty/0).**
            *   If `len(rs) > n_ref` (there are some rows that are *not* refused, i.e., they are waiting):
                *   `no_word_record` increases by `len(rs) - n_ref`.
                *   `no_word_record_videos` records `len(rs) - n_ref`.
                *   This is correct. The refused rows are accounted for in `report["window_refused"] += n_ref` (line 77).
            *   If `len(rs) == n_ref` (ALL rows are refused):
                *   The `if` condition `len(rs) > n_ref` is False.
                *   The `elif windows` is False (windows is 0).
                *   So, `no_word_record` is NOT incremented. `no_word_record_videos` is NOT updated.
                *   `report["window_refused"]` IS incremented by `n_ref`.
                *   **Verdict:** Correct. A video where all rows are refused should not appear in `no_word_record_videos` as "waiting for a word record" because it isn't waiting; it's dead.
        *   **Scenario B: Video HAS windows (`windows` > 0).**
            *   `report["window_refused"] += n_ref` (line 77).
            *   `report["window_waiting"] += waiting` (line 89).
            *   `no_word_record` is NOT touched.
            *   **Verdict:** Correct. Refused and waiting are distinct counts.

**3. `pipeline/spotlight.py` - `next_attempt`**
*   **Change:** Accepts `refused`.
*   **Logic Check:**
    *   `n_ref = sum(1 for r in rs if r.get("moment_id") in refused and r.get("moment_id") not in word_pass)`
    *   `word_pass_waiting = len(rs) - ready - n_ref`
    *   **Check (2):** "No row can be counted twice."
        *   `ready` counts rows where `word_pass.get(mid)` exists and is `sentence_ready`.
        *   `n_ref` counts rows where `mid` is in `refused` AND `mid` is NOT in `word_pass`.
        *   Can a row be both `ready

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_0951 (the word pass's refused moments, counted apart)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0; every finding it tagged P1 in its text it settles there as safe or correct)
and glm-5.3-flash (P1_OR_WORSE: 1). They disagree on a P1, so Grok was asked: grok-4.20-0309-reasoning
(P1_OR_WORSE: 0). Cycle 1: $0.0340 vendor-reported.

1. glm [P1] "refused == never re-worked rests on the integrator's word; cite the worker or test it". REAL, AND IT FOUND
   A DEFECT. I read the worker: its passed_ids (the integrator's pipeline/word_pass_worker.py:121-133, release branch
   b22a5e56) counts EVERY row as worked EXCEPT an acquisition failure in YouTube's sign-in wording (BLOCK, :68) without
   control_ok. That failure is the platform's, and the moment is picked again. Cycle 1's refused set (every moment
   whose LAST row gives no window) would have called such a moment refused while the worker retries it.
   FIXED:
   - ledger_build.worked_by_worker(row) mirrors passed_ids' rule, with WORKER_BLOCK mirroring BLOCK. Both cite file,
     lines and commit. They cannot be imported: the worker is not on this branch, and it loads the main tree's
     transcript_store, which rows()'s store guard refuses in one process.
   - refused = worked - ready. A moment counts as worked when ANY of its rows counts, as passed_ids does, not only
     its last row.
   Tests:
   - B (a sign-in failure without control_ok) is NOT refused: it waits.
   - C (the same failure with control_ok) is refused.
   - E (worked earlier, then a sign-in failure) is refused.
   Mutations killed: R15 (block failures counted as worked), R16 (control_ok ignored), R17 (the last row alone
   decides). A test against the worker's own code is not possible from this branch. If the integrator changes
   passed_ids, the mirror must change with it; the integrator is told.
2. glm [P2] "word_pass and word_pass_refused must come from one call". DONE: build_inputs' docstring says so. The
   driver takes both from one word_pass_index() call (tests/package/proof_ledger.py:405-411). It is the only caller.
3. glm [P2] "word_pass_waiting can go negative with a mismatched pair". NO CHANGE: it cannot.
   - n_ref counts only rows whose moment is NOT in word_pass.
   - ready counts only rows whose moment IS in word_pass (and sentence-ready).
   So ready + n_ref <= rows for any inputs, matched or not.
4. glm [P2] "an all-refused video vanishes from the per-video report". FIXED: report["window_refused_videos"]
   {video: refused rows}, tested ({vidW: 1, vidX: 2, vidZ: 1}; mutation R18 killed).
5. glm [P3] "unreadable counts lines, refused counts moments". Pre-existing; noted. The report keeps both.
6. glm [P3] (a) "confirm the driver's ruling-95 call site was updated". tests/package/proof_ledger.py IS the build
   driver. Its call (:510) passes refused=refused, and no other caller of next_attempt exists (grep). The survivor R11
   is that one keyword: no test reaches the driver past 

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_0951/C2_STEP.diff (360 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | index 88a255b..185ba4c 100644
   3 | --- a/pipeline/ledger_build.py
   4 | +++ b/pipeline/ledger_build.py
   5 | @@ -34,6 +34,7 @@ FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call h
   6 |  import hashlib
   7 |  import json
   8 |  import os
   9 | +import re
  10 |  import sys
  11 |  
  12 |  import eligibility as E
  13 | @@ -157,12 +158,32 @@ def _num(x):
  14 |      return v if v == v and v not in (float("inf"), float("-inf")) else None
  15 |  
  16 |  
  17 | +WORKER_BLOCK = re.compile(r"Sign in to confirm|--cookies for the authentication", re.I)
  18 | +# the word-pass worker's own BLOCK (the integrator's pipeline/word_pass_worker.py:68, release branch b22a5e56):
  19 | +# YouTube's sign-in wording. It is mirrored, not imported: the worker loads the main tree's transcript_store, which
  20 | +# this process may not (rows()'s store guard).
  21 | +
  22 | +
  23 | +def worked_by_worker(row):
  24 | +    """True when the word-pass worker counts this row as its moment WORKED, so it never picks the moment again: its
  25 | +    passed_ids (the integrator's pipeline/word_pass_worker.py:121-133, b22a5e56) counts every row (ready, not ready or
  26 | +    failed) except an acquisition failure in YouTube's sign-in wording without control_ok, which is the platform's, not
  27 | +    the moment's (that moment is picked again)."""
  28 | +    why = row.get("error")
  29 | +    blocked = isinstance(why, str) and why.startswith("acquisition:") and bool(WORKER_BLOCK.search(why))
  30 | +    return not (blocked and not row.get("control_ok"))
  31 | +
  32 | +
  33 |  def word_pass_index(path=WORD_PASS):
  34 |      """The word-pass worker's rows -> ({moment_id: the LAST row of that moment, when it is sentence_ready with a
  35 | -    window_record and a record_sha256}, report). A failed moment's row has neither, and the worker never retries it.
  36 | -    No file yet = no window record yet: ({}, report). A file that exists but cannot be read raises: it is never read
  37 | -    as an empty word pass (law L-j)."""
  38 | -    rep = {"rows": 0, "unreadable": 0, "ready": 0, "not_ready": 0, "failed": 0, "file": path}
  39 | +    window_record and a record_sha256}, report). A failed moment's row has neither.
  40 | +    report["refused"], sorted: every moment the worker has WORKED (worked_by_worker) and no usable window record came
  41 | +    of: it is final, never "waiting", because the worker never works a moment again (the integrator, 09:37 ET Nov 15).
  42 | +    A moment whose only rows are retried block failures is not refused: the worker picks it again. No file yet = no
  43 | +    window record yet: ({}, report). A file that exists but cannot be read raises: it is never read as an empty word
  44 | +    pass (law L-j)."""
  45 | +    rep = {"rows": 0, "unreadable": 0, "ready": 0, "not_ready": 0, "failed": 0, "file": path, "refused": []}
  46 | +    worked = set()
  47 |      try:
  48 |          f = open(path)
  49 |      except FileNotFoundError:
  50 | @@ -182,6 +203,8 @@ def word_pass_index(path=WORD_PASS):
  51 |                  rep["unreadable"] += 1
  52 |                  continue
  53 |              last[r["moment_id"]] = r
  54 | +            if worked_by_worker(r):
  55 | +                worked.add(r["moment_id"])
  56 |      out = {}
  57 |      for mid, r in last.items():
  58 |          if r.get("error") or r.get("window_record") is None:
  59 | @@ -193,6 +216,7 @@ def word_pass_index(path=WORD_PASS):
  60 |              rep["ready"] += 1
  61 |          else:
  62 |              rep["unreadable"] += 1
  63 | +    rep["refused"] = sorted(worked - set(out))
  64 |      return out, rep
  65 |  
  66 |  
  67 | @@ -420,9 +444,13 @@ def reanchor(row, src, cap=None):
  68 |      return sp, info
  69 |  
  70 |  
  71 | -def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store=None):
  72 | +def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store=None, word_pass_refused=()):
  73 |      """Ledger rows -> (moments in the packager's form, {key: Source}, report). word_pass: word_pass_index()'s
  74 | -    {moment_id: row} (None = no window records).
  75 | +    {moment_id: row} (None = no window records). word_pass_refused: the "refused" ids of the SAME word_pass_index()
  76 | +    call's report (the two are disjoint by construction). A row with neither a sentence-ready window record nor a
  77 | +    full-video record is counted as REFUSED when the word pass refused it (final: never re-worked), else as waiting (no
  78 | +    row yet): report "window_refused" (and per video, "window_refused_videos") apart from "window_waiting" and
  79 | +    "no_word_record".
  80 |      - A video with a sentence-ready full-video word record: every row re-anchors in it (key: the video id).
  81 |      - Otherwise ONE WINDOW PER MOMENT, the word-pass worker writing one around each moment. A row with its own
  82 |        sentence-ready window record re-anchors in THAT window, and its moment carries source_key =
  83 | @@ -434,9 +462,10 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
  84 |      Rows with no word record, rows that do not re-anchor on whole sentences, and duplicates are dropped, each counted
  85 |      with why. report: "videos" counts the videos that gave moments and "sources" their records (one per window
  86 |      moment); window_records is {video: [records]} (audit 0208 C2, glm N2 / N4)."""
  87 | -    word_pass = word_pass or {}
  88 | +    word_pass, refused = word_pass or {}, set(word_pass_refused or ())
  89 |      report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "no_word_record_videos": {},
  90 | -              "window_records": {}, "window_waiting": 0, "window_failed": 0, "window_passed_over": {},
  91 | +              "window_records": {}, "window_waiting": 0, "window_refused": 0, "window_refused_videos": {},
  92 | +              "window_failed": 0, "window_passed_over": {},
  93 |                "no_caption_context": {},
  94 |                "fallbacks": {},
  95 |                "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "duplicates_of": {},
  96 | @@ -502,10 +531,14 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
  97 |                  sources[vid] = src
  98 |              continue
  99 |          caps, why_w, waiting, windows, kept = {}, [], 0, 0, []     # kept: (start, end, moment id) of window moments
 100 | +        n_ref = 0                                    # rows the word pass refused: final, never waiting
 101 |          for i, r in irs:                             # ONE WINDOW PER MOMENT
 102 |              wp = word_pass.get(r["moment_id"])
 103 |              if wp is None:
 104 | -                waiting += 1
 105 | +                if r["moment_id"] in refused:
 106 | +                    n_ref += 1
 107 | +                else:
 108 | +                    waiting += 1
 109 |                  continue
 110 |              wsrc, wpath, why = window_source(r, wp, ctx, store)
 111 |              if wsrc is None:
 112 | @@ -539,19 +572,23 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
 113 |              sources[key] = wsrc
 114 |          if why_w:
 115 |              report["window_passed_over"][vid] = why_w
 116 | -        if not windows:
 117 | +        report["window_refused"] += n_ref            # this video's refused rows (counted in its loop above), whether
 118 | +        if n_ref:                                    # or not it has windows; never in the waiting counts below
 119 | +            report["window_refused_videos"][vid] = n_ref
 120 | +        if not windows and len(rs) > n_ref:          # rows that still wait (a video the word pass refused whole: none)
 121 |              why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
 122 |                                             ["no sentence-ready window record"]))
 123 | -            report["no_word_record"] += len(rs)
 124 | -            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 125 | -            report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 126 | -        else:
 127 | +            report["no_word_record"] += len(rs) - n_ref
 128 | +            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs) - n_ref
 129 | +            report["no_word_record_videos"][vid] = {"rows": len(rs) - n_ref, "why": why}   # which (glm C3 P2-2)
 130 | +        elif windows:
 131 |              report["window_waiting"] += waiting      # rows of a window video with no window record of their own
 132 |      report["moments"], report["sources"] = len(moments), len(sources)
 133 |      report["videos"] = len({m["video_id"] for m in moments})
 134 |      log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} videos "
 135 |          f"({report['sources']} word records); {report['no_word_record']} rows wait for a word record, "
 136 | -        f"{report['window_waiting']} wait for their own window, {len(report['not_anchored'])} do not re-anchor, "
 137 | +        f"{report['window_waiting']} wait for their own window, {report['window_refused']} refused by the word pass "
 138 | +        f"(not sentence-ready or failed: never re-worked), {len(report['not_anchored'])} do not re-anchor, "
 139 |          f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
 140 |          f"{len(report['channel_conflict'])} video(s) name more than one channel, "
 141 |          f"{len(report['fallbacks'])} read from a fallback record; "
 142 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 143 | index f2290d0..c945ced 100644
 144 | --- a/pipeline/spotlight.py
 145 | +++ b/pipeline/spotlight.py
 146 | @@ -342,16 +342,18 @@ def source_test(evidence, layout):
 147 |      return True, f"layout '{lay}'; the captions' evidence: {evidence_text(evidence)}"
 148 |  
 149 |  
 150 | -def next_attempt(rows, word_pass, now, captions_for=None):
 151 | +def next_attempt(rows, word_pass, now, captions_for=None, refused=()):
 152 |      """RULING 95 (00:40 ET Nov 14): when a build ends with no medley and no spotlight, when the next qualifying episode
 153 |      could arrive. The NEWEST upload among the adapter's rows whose captions do not refuse it (RULING 92 AMENDED, 09:03
 154 |      Nov 14: unmarked, or marked with at least one speaker change; the layout decides per clip), its caption turns from
 155 |      pp-ingest's `episode` (mine-hook/2 rows), else episode_turns(): an episode marked with zero turns is the one
 156 | -    excluded. Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready or still
 157 | -    waiting (word_pass: ledger_build.word_pass_index's {moment_id: row}). -> {"conversation": {...} or None,
 158 | +    excluded. Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready, refused
 159 | +    (refused: word_pass_index's report["refused"], final: the worker never re-works them) or still waiting (no row yet)
 160 | +    (word_pass: ledger_build.word_pass_index's {moment_id: row}). -> {"conversation": {...} or None,
 161 |      "newest_upload": {...} or None}."""
 162 |      from datetime import datetime, timedelta, timezone
 163 |      import package_pin as PPN
 164 | +    refused = set(refused or ())
 165 |      by_vid = {}
 166 |      for r in rows or ():
 167 |          if isinstance(r, dict) and r.get("video_id"):
 168 | @@ -370,13 +372,14 @@ def next_attempt(rows, word_pass, now, captions_for=None):
 169 |              k = f"{(r.get('mined') or {}).get('pass')}/{(r.get('mined') or {}).get('prompt_version')}"
 170 |              passes[k] = passes.get(k, 0) + 1
 171 |          ready = sum(1 for r in rs if (word_pass.get(r.get("moment_id")) or {}).get("sentence_ready"))
 172 | +        n_ref = sum(1 for r in rs if r.get("moment_id") in refused and r.get("moment_id") not in word_pass)
 173 |          exp = (datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) +
 174 |                 timedelta(hours=PPN.WINDOW_H)).strftime("%Y-%m-%dT%H:%M:%SZ") if pub else None
 175 |          age = E.age_hours(rs[0].get("published_at"), now)
 176 |          return {"video_id": vid, "channel": rs[0].get("channel_name"), "published_at": pub, "expires_at": exp,
 177 |                  "age_h": round(age, 1) if age is not None else None,
 178 |                  "turns_per_min": tpm, "unmarked": unmarked, "turns_from": frm, "rows": len(rs), "passes": passes,
 179 | -                "word_pass_ready": ready, "word_pass_waiting": len(rs) - ready}
 180 | +                "word_pass_ready": ready, "word_pass_refused": n_ref, "word_pass_waiting": len(rs) - ready - n_ref}
 181 |      sts = sorted((state(v, rs) for v, rs in by_vid.items()), key=lambda x: x["published_at"] or "", reverse=True)
 182 |      conv = [x for x in sts if x["unmarked"] or not (isinstance(x["turns_per_min"], (int, float)) and
 183 |                                                      x["turns_per_min"] <= 0)]       # only MARKED with zero turns is out
 184 | diff --git a/tests/package/funnel.py b/tests/package/funnel.py
 185 | index 044385c..71d7f95 100644
 186 | --- a/tests/package/funnel.py
 187 | +++ b/tests/package/funnel.py
 188 | @@ -100,6 +100,8 @@ for why, n in (rep.get("no_word_record_why") or {}).items():
 189 |      s0 += [(f"SUPPLY: no word record yet ({why})", None)] * int(n)
 190 |  s0 += [("SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row)", None)] * \
 191 |      int(rep.get("window_waiting") or 0)
 192 | +s0 += [("refused by the word pass (its row is not sentence-ready or failed; never re-worked)", None)] * \
 193 | +    int(rep.get("window_refused") or 0)
 194 |  s0 += [("its window record failed a check", None)] * int(rep.get("window_failed") or 0)
 195 |  na = rep.get("not_anchored") or {}
 196 |  ws_rows = {}
 197 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 198 | index 0e36ebd..63860a3 100644
 199 | --- a/tests/package/proof_ledger.py
 200 | +++ b/tests/package/proof_ledger.py
 201 | @@ -403,9 +403,11 @@ def main(argv=None):
 202 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
 203 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 204 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
 205 | -    say(f"  word pass: {json.dumps(wp_rep)}")
 206 | +    refused = wp_rep.get("refused") or []                # final: the worker never re-works them (the inputs keep ids)
 207 | +    say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(refused)))}")
 208 |      moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
 209 | -                                               ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"))
 210 | +                                               ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"),
 211 | +                                               word_pass_refused=refused)
 212 |      inputs["word_pass"] = wp_rep
 213 |      moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
 214 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 215 | @@ -505,7 +507,7 @@ def main(argv=None):
 216 |      res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
 217 |                                                  "scorer_waited_s", "lock_stop", "scorer")}
 218 |      try:                                                 # RULING 95: when the next qualifying episode could arrive
 219 | -        res["next_attempt"] = SPOT.next_attempt(rows, wp, now)
 220 | +        res["next_attempt"] = SPOT.next_attempt(rows, wp, now, refused=refused)
 221 |      except Exception as e:                               # noqa: BLE001  a report, never the build
 222 |          res["next_attempt"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
 223 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 224 | @@ -569,7 +571,8 @@ def main(argv=None):
 225 |          say(f"  RULING 95: the newest conversation upload: {na.get('channel')} {na.get('video_id')} published "
 226 |              f"{na.get('published_at')} (expires {na.get('expires_at')}), {na.get('turns_per_min')} turns a minute, "
 227 |              f"rows {na.get('passes')}, word pass {na.get('word_pass_ready')} ready / {na.get('word_pass_waiting')} "
 228 | -            f"waiting" if na else "  RULING 95: no conversation upload in the window")
 229 | +            f"waiting / {na.get('word_pass_refused')} refused (never re-worked)" if na else
 230 | +            "  RULING 95: no conversation upload in the window")
 231 |          say(f"no spotlight ({sp.get('why_none')})" + "".join(
 232 |              f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
 233 |              f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
 234 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 235 | index cc9b1e8..5a109eb 100644
 236 | --- a/tests/package/test_ledger_build.py
 237 | +++ b/tests/package/test_ledger_build.py
 238 | @@ -462,6 +462,49 @@ class TestWindowRecords(unittest.TestCase):
 239 |              self.assertEqual(idx["C"]["record_sha256"], "s2")                       # the last row of a moment wins
 240 |              self.assertEqual((rep["failed"], rep["not_ready"], rep["ready"], rep["unreadable"]), (1, 1, 1, 1))
 241 |  
 242 | +    def test_the_refused_are_the_moments_the_worker_worked_with_no_window_from_it(self):
 243 | +        """The integrator, 09:37 ET Nov 15: the worker never works a moment again once a row counts as worked (its
 244 | +        passed_ids, pipeline/word_pass_worker.py:121-133): every row but an acquisition failure in YouTube's sign-in
 245 | +        wording without control_ok. A worked moment with no usable window record is refused, never waiting."""
 246 | +        with tempfile.TemporaryDirectory() as d:
 247 | +            p = os.path.join(d, "word_pass.jsonl")
 248 | +            self.assertEqual(LB.word_pass_index(p)[1]["refused"], [])               # no file yet: none refused
 249 | +            ok = {"window_record": "x", "record_sha256": "s", "sentence_ready": True}
 250 | +            boom = {"window_record": None, "record_sha256": None, "sentence_ready": False, "error": "boom"}
 251 | +            signin = dict(boom, error="acquisition: ERROR: [youtube] abc: Sign in to confirm you're not a bot")
 252 | +            rows = [dict(ok, moment_id="R"), dict(boom, moment_id="F"),
 253 | +                    dict(ok, moment_id="N", sentence_ready=False), dict(ok, moment_id="U", record_sha256=None),
 254 | +                    dict(boom, moment_id="L"), dict(ok, moment_id="L"),                # the last row wins, both ways
 255 | +                    dict(ok, moment_id="T"), dict(ok, moment_id="T", sentence_ready=False),
 256 | +                    dict(signin, moment_id="B"),                     # the platform's block: picked again, it waits
 257 | +                    dict(signin, moment_id="C", control_ok=True),    # the control downloaded: the video's, refused
 258 | +                    dict(ok, moment_id="E", sentence_ready=False), dict(signin, moment_id="E")]   # worked before
 259 | +            with open(p, "w") as f:
 260 | +                f.write("\n".join(json.dumps(r) for r in rows) + "\n")
 261 | +            idx, rep = LB.word_pass_index(p)
 262 | +            self.assertEqual((sorted(idx), rep["refused"]), (["L", "R"], ["C", "E", "F", "N", "T", "U"]))
 263 | +
 264 | +    def test_a_row_the_word_pass_refused_is_counted_apart_from_the_waiting(self):
 265 | +        ctx = E.Context(NOW, REG)
 266 | +        with tempfile.TemporaryDirectory() as d:
 267 | +            rel, wp, r, words = window_fixture(d)
 268 | +            mk = lambda mid, vid, t: dict(row("Bitcoin started as a quiet experiment.", start=t, end=t + 4.0, mid=mid,
 269 | +                                              vid=vid), transcript_sha256=r["transcript_sha256"])
 270 | +            rows = [r, mk("W2", "vidW", 100.0), mk("W3", "vidW", 200.0),      # vidW: W1 ready, W2 refused, W3 waits
 271 | +                    mk("X1", "vidX", 10.0), mk("X2", "vidX", 20.0),           # vidX: every row refused
 272 | +                    mk("Y1", "vidY", 10.0),                                    # vidY: no row yet
 273 | +                    mk("Z1", "vidZ", 10.0), mk("Z2", "vidZ", 20.0)]           # vidZ: no window; Z1 refused, Z2 waits
 274 | +            go = lambda **k: LB.build_inputs(rows, ctx, d, log=lambda s: None, word_pass={"W1": wp}, **k)
 275 | +            ms, _, rep = go(word_pass_refused=["W2", "X1", "X2", "Z1"])
 276 | +            self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["W1"])
 277 | +            self.assertEqual((rep["window_waiting"], rep["window_refused"], rep["no_word_record"]), (1, 4, 2))
 278 | +            self.assertEqual({v: x["rows"] for v, x in rep["no_word_record_videos"].items()},
 279 | +                             {"vidY": 1, "vidZ": 1})                             # vidX waits for nothing
 280 | +            self.assertEqual(rep["window_refused_videos"], {"vidW": 1, "vidX": 2, "vidZ": 1})   # named per video
 281 | +            self.assertEqual(sum(rep["no_word_record_why"].values()), 2)         # the why counts agree
 282 | +            _, _, old = go()                                                     # no refused ids given: as before
 283 | +            self.assertEqual((old["window_waiting"], old["window_refused"], old["no_word_record"]), (2, 0, 5))
 284 | +
 285 |      def test_a_window_record_is_used_only_when_every_claim_checks_out(self):
 286 |          ctx = E.Context(NOW, REG)
 287 |          with tempfile.TemporaryDirectory() as d:
 288 | diff --git a/tests/package/test_ruling_107_guard.py b/tests/package/test_ruling_107_guard.py
 289 | index ce0eade..c1b3e31 100644
 290 | --- a/tests/package/test_ruling_107_guard.py
 291 | +++ b/tests/package/test_ruling_107_guard.py
 292 | @@ -161,7 +161,8 @@ class TestTheDriverAsksNoModel(Paths):
 293 |      PIN_PATHS = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 294 |                                                                                    "MOMENTS_PIN_LY.json")]
 295 |  
 296 | -    def run_driver(self, left):
 297 | +    def run_driver(self, left, wp_rep=None, seen=None):
 298 | +        """wp_rep: the word pass's report the stubbed index gives; seen: filled with build_inputs' keyword arguments."""
 299 |          proof = os.path.join(self.tmp.name, "drv", "proof")
 300 |          os.makedirs(proof)
 301 |          delivered, last, pins = PLG.delivered_pins(self.PIN_PATHS)
 302 | @@ -177,12 +178,16 @@ class TestTheDriverAsksNoModel(Paths):
 303 |  
 304 |          def no_router(*a, **k):
 305 |              raise Built("a router was built")
 306 | +
 307 | +        def inputs(*a, **k):
 308 | +            (seen if seen is not None else {}).update(k)
 309 | +            return copy.deepcopy(POOL), {}, {}
 310 |          stubs = [mock.patch.object(PLG, "HERE", os.path.join(self.tmp.name, "drv")),
 311 |                   mock.patch.object(PLG, "REGISTRY", os.path.join(proof, "CANDIDATES.json")),
 312 |                   mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []),
 313 |                   mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})),
 314 | -                 mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, {"rows": 0})),
 315 | -                 mock.patch.object(PLG.LB, "build_inputs", lambda *a, **k: (copy.deepcopy(POOL), {}, {})),
 316 | +                 mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, dict(wp_rep or {"rows": 0}))),
 317 | +                 mock.patch.object(PLG.LB, "build_inputs", inputs),
 318 |                   mock.patch.object(PLG, "with_variants", lambda moments, *a, **k: moments),
 319 |                   mock.patch.object(PLG, "build_router", no_router),
 320 |                   mock.patch("sys.stdout", new=io.StringIO())]
 321 | @@ -208,6 +213,16 @@ class TestTheDriverAsksNoModel(Paths):
 322 |          self.assertIn("NOTHING NEW (ruling 107 (1))", open(os.path.join(runs[0], "package.log")).read())
 323 |          self.assertFalse(os.path.exists(os.path.join(runs[0], PLG.FINGERPRINT)))   # a skip never stands for a build
 324 |  
 325 | +    def test_the_word_pass_refused_reach_the_inputs_and_the_log_gives_their_count(self):
 326 | +        seen = {}
 327 | +        rc, runs = self.run_driver(left=0, wp_rep={"rows": 2, "ready": 0, "refused": ["Xa1", "Yb2"]}, seen=seen)
 328 | +        self.assertEqual((rc, seen.get("word_pass_refused")), (0, ["Xa1", "Yb2"]))
 329 | +        log = open(os.path.join(runs[0], "package.log")).read()
 330 | +        self.assertIn('"refused": 2', log)                                   # the count; the ids stay in inputs.json
 331 | +        self.assertNotIn("Xa1", log)
 332 | +        self.assertEqual(json.load(open(os.path.join(runs[0], "inputs.json")))["inputs"]["word_pass"]["refused"],
 333 | +                         ["Xa1", "Yb2"])
 334 | +
 335 |      def test_work_left_undone_goes_on_to_the_router(self):
 336 |          rc, runs = self.run_driver(left=1)
 337 |          self.assertEqual(rc, "router")
 338 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 339 | index c99d420..64517b8 100644
 340 | --- a/tests/package/test_spotlight.py
 341 | +++ b/tests/package/test_spotlight.py
 342 | @@ -538,6 +538,17 @@ class TestRuling94And95(unittest.TestCase):
 343 |          self.assertIn("ruling 94 (a): the trimmed cut is not clean: it bleeds", out["moments"]["a~trim"]["out"])
 344 |          self.assertNotIn("package_for", calls)
 345 |  
 346 | +    def test_ruling_95_a_moment_the_word_pass_refused_is_not_waiting(self):
 347 | +        rows = [{"video_id": "mid", "channel_name": "Panel", "published_at": "2026-11-13T20:00:00+00:00",
 348 | +                 "moment_id": m, "episode": {"turns_per_min": 1.5}, "mined": {"pass": "moment",
 349 | +                                                                             "prompt_version": "mine/2"}}
 350 | +                for m in ("m1", "m2", "m3")]
 351 | +        c = SPOT.next_attempt(rows, {"m1": {"sentence_ready": True}}, NOW, refused=["m2", "zz"])["conversation"]
 352 | +        self.assertEqual((c["rows"], c["word_pass_ready"], c["word_pass_refused"], c["word_pass_waiting"]),
 353 | +                         (3, 1, 1, 1))                                       # zz is no row of this upload
 354 | +        c = SPOT.next_attempt(rows, {"m1": {"sentence_ready": True}}, NOW)["conversation"]   # none named: as before
 355 | +        self.assertEqual((c["word_pass_refused"], c["word_pass_waiting"]), (0, 2))
 356 | +
 357 |      def test_ruling_95_the_newest_conversation_upload_and_its_mining_state(self):
 358 |          rows = [{"video_id": "old", "channel_name": "Talk", "published_at": "2026-11-13T18:00:00+00:00",
 359 |                   "moment_id": "o1", "episode": {"turns_per_min": 2.0}, "mined": {"pass": "hook",
 360 | 
```

---

pp-selectid: THE WORD PASS'S REFUSED MOMENTS, COUNTED APART FROM THE WAITING. Reporting only: no gate, verdict or
selection changes; no moment enters or leaves a build because of this change.

THE FINDING (the integrator, 09:37 ET Nov 15). The word-pass worker never works a moment again once it has a row
(ready, not ready or failed: its passed_ids). ledger_build.word_pass_index returns only the sentence-ready rows, so
build_inputs counted a moment whose row is NOT sentence-ready the same as a moment with no row yet: "N wait for their
own window" (pipeline/ledger_build.py:504-509 and :549 in the base). This morning two builds said "4 wait for their own
window" for 4 Scott Melker moments the word pass had refused at 09:05, and my STATE line said the watcher would build
"when they land": they never will. spotlight.next_attempt (ruling 95, pipeline/spotlight.py:345) counted them "waiting"
the same way.

THE CHANGE:
1. word_pass_index: report["refused"] = the sorted moment ids whose LAST row gives no window record (failed, not
   sentence-ready, or unreadable): set(last) - set(out). Its index and its other counts are unchanged. A line that is
   not JSON or has no moment_id is attributable to no moment, so it refuses none (as before, it is counted unreadable).
2. build_inputs(..., word_pass_refused=()): a row with no sentence-ready window record of its own is counted
   "window_refused" when its moment is in word_pass_refused, else exactly as before: "window_waiting" in a video that
   has windows, "no_word_record" (with its why and per-video rows) in a video that has none. A video whose rows are ALL
   refused gets no no_word_record entry: it waits for nothing. The log line gives the refused count. With no refused
   ids given, every count is as before (tested).
3. spotlight.next_attempt(..., refused=()): "word_pass_refused" apart; "word_pass_waiting" = rows - ready - refused.
4. tests/package/proof_ledger.py: passes the report's refused ids to build_inputs and to next_attempt; logs the
   word-pass report with the refused COUNT (the ids stay in inputs.json); ruling 95's line reads
   "ready / waiting / refused".
5. tests/package/funnel.py (a report script over a build's inputs.json): one supply line for the refused.

TESTS:
- test_ledger_build: the index's refused set (the last row decides, both ways), and build_inputs' counts over four
  videos (windows with one refused and one waiting row; all rows refused; no row yet; no window with one refused and
  one waiting row), then the same rows with no refused ids: as before.
- test_spotlight: ruling 95's counts.
- test_ruling_107_guard: the driver passes the ids to build_inputs and logs only their count. Its harness gains two
  optional arguments; the existing tests call it as before.
MUTATIONS: 12 of 14 killed, after a control run (the unmutated copy passes all 93 tests). The 2 that survive:
- the driver's ruling-95 call without refused=: no test reaches the driver past its router (the existing harness stops
  there);
- the funnel script's line: no test runs funnel.py.
SUITES: tests/package, moments, select_by_id and providers: 684 pass.

PLEASE CHECK: (1) that the refused set is exactly what the worker will never re-work (the last row decides, as
word_pass_index's own classification does); (2) that no row can be counted twice (refused and waiting, or refused and
ready), and that every count is as before when no ids are given; (3) the no-window branch: no_word_record, its why
counts and its per-video rows; (4) the driver's wiring, and that the log carries counts, not ids; (5) whether either
surviving mutation matters.


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
