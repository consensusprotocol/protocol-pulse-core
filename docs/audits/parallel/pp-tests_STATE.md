# pp-tests STATE — session pipeline_pp_tests (worktree /home/ultron/worktrees/pp-tests, branch pp-tests)

> **FOR THE BUILDER (pipeline_pp_selectid): the moments-first EXAM lives at**
> **`/home/ultron/worktrees/pp-tests/tests/adversarial/corpora/`** (`context_integrity/`, `vo_fidelity/`, `exclusions/`;
> branch `pp-tests`); the harness is `tests/adversarial/test_moments_gates.py`. Format and adapter protocol: the
> section "PHASE 2 — CORPORA FORMAT v1" just below. Code your adapter against it; do not read the expected verdicts.

## PHASE 2 LIVE STATE (newest first; times ET, 2026-11-12)

- 05:05 FINAL: corpus frozen at 136 cases, audited (two cycles of the repo tool on code and corpus, an independent
  claude-opus-5-5 review of each, then a verification round), final blind baseline run; committing and pushing (the
  hash goes in the line below once pushed). `python3 -m pytest tests/adversarial/test_moments_gates.py -q`: 31 passed,
  3 skipped (the real gates are absent from this branch: skip-with-reason, never pass). Whole wall
  `python3 -m pytest tests/adversarial -q`: 365 passed, 3 skipped, 38 xfailed (Phase 1's 38 strict xfails unchanged);
  regression_test.sh 26 PASS / 0 FAIL.
- 04:17 first audit fixes; 03:29 first corpus (135 cases, superseded); 02:57 FORMAT v1 published (below).

### Counts per class (REAL vs CONSTRUCTED)

| corpus | expected | class | REAL | CONSTRUCTED |
|---|---|---|---|---|
| context_integrity | fail | steelman 3, quoting_opponent 3, sarcasm 3, hypothetical 3, conditional_split 2, unresolved_referent 4, some_people_say 3, answer_without_question 3, later_retraction 2 (1 of them stratum beyond_window, reported apart), reading_aloud 3, wrong_speaker 3, stale_time_reference 3, false_dialogue 3, title_adds_thesis 3 | 41 | 0 |
| context_integrity | pass | clean_assertion 16, clean_conjunction_opener (opens on And / So / But) 6 | 22 | 0 |
| vo_fidelity | fail | stance_flip, could_to_will, number_swapped, number_rounded, invented_agreement, fact_not_in_clips, absent_name, banned_framing, financial_imperative (3 each) | 27 | 0 |
| vo_fidelity | pass | faithful_paraphrase 6, manifest_language 7 | 13 | 0 |
| exclusions | exclude | accusation 3, ad_read 5, altcoin 3, imperative 2, single_source_breaking 2, third_party_media 2 | 17 | 0 |
| exclusions | exclude | partner_attack 2, guaranteed_return 2 | 0 | 4 |
| exclusions | keep | policy_criticism 4, framed_prediction 4, neutral_company 4 | 12 | 0 |

136 cases from 42 store videos on 21 channels. What REAL means: every window / moment / context / adjacent sentence is
a store record's own sentence (record path + sha256 in the case; `test_every_case_rebuilds_verbatim_from_the_store`
re-extracts all 136; `test_sentence_ids_match_pp_selectid_at_the_named_commit` re-splits all referenced records with
pp-selectid's own code at d809a1f8). For false_dialogue and title_adds_thesis the clips are real and clean and the
trap is the package (bridge, sequence, title). The VO lines and every package are authored stimulus. CONSTRUCTED: 4
exclusion cases, because the store holds no partner-on-partner attack (none in any partner record, none in the
39,999 statements of the oracle exports) and no guaranteed-return claim to the viewer; the searches are in each case;
the moments are opinion-level, the context around them is neutral filler, the guaranteed-return shows are fictional.

Must-pass make-up: 13 single-narrator clips (Swan Bitcoin 5, Coin Bureau 6, Simply Bitcoin 1, Yahoo Finance 1) and
9 one-sentence interview clips; every must-pass package credits the SHOW (a channel named after a person is "<name>'s
show"); the one person named (Swan Bitcoin's Cory Klippsten) is verified by the source description and by his own
words in the window; every hedge is kept; an And / So / But opener goes first; two channels per package; intro /
bridge / sign-off / order come from the same pool as the must-fail packages.

### Blind frontier baseline (how hard the exam is before the real gates sit it)

Adapter `tests/adversarial/baselines/frontier_blind.py` through the same runner: one call per blinded case, the laws'
own wording only (v2), shuffled order, salted ids. Spend guard $15 across all runs: ledger $14.66 billed by usage
(`baselines/SPEND.jsonl`; 11 calls OpenAI refused with HTTP 429 after its credits ran out were not billed and their
reservations are released in the ledger, `release_refused`).

**v2, the FINAL corpus (136 cases), law-text-only prompt** (`results/v2_FINAL_*.json`; final INDEX hashes in
`results/final_corpus_INDEX/`):

| model (vendor) | corpus | must-reject rejected | missed | must-accept false-rejected | errors | thresholds |
|---|---|---|---|---|---|---|
| claude-opus-5-5 (Anthropic), effort medium | context_integrity | 40/40 | 0 | 0/22 = 0.0% | 0 | MEETS |
| same | (beyond_window stratum, apart) | 0/1 | 1 | | | the correction is 74 s after; inside 60 s it cannot be seen (R-24) |
| same | vo_fidelity | 27/27 | 0 | 0/13 = 0.0% | 0 | MEETS |
| same | exclusions | 21/21 | 0 | 2/12 = 16.7% | 0 | MISSES (both 'uncertain': a company's purchase and a bank charter read as possibly single-source news) |
| gemini-3.1-pro-preview (Google) | context_integrity, must-pass only | | | 0/22 = 0.0% | 0 | budget allowed the false-reject side only |
| same | vo_fidelity / exclusions, must-accept | | | not run | 20 | refused by the $15 guard (spent $14.9 + estimate) |

**v1, the previous corpus versions (label-informing: their disagreements led to corrections, so not blind to the
corpus's design)**: gemini-3.1-pro-preview, full run on version 6 (139 cases): context 42/42 rejected, 1/22 false
rejects; VO 27/27, 0/13; exclusions 22/23 (missed the sarcastic imperative, since removed), 0/12. claude-opus-5-5 on
version 4 plus re-runs of every changed case: context 42/42, VO 27/27, exclusions 23/23; its context false rejects
(a paraphrase-adjacent clip, a host-named intro) led to corrections. gpt-6.1-sol (OpenAI) on version 4: context
42/42 rejected, 4/22 false rejects (two host-named intros, a title that dropped 'in the buildout', a clip after a
reported-speech lead-in: all four fixed), 1 error; its VO and exclusion legs did not run: the OpenAI account ran out
of credits during that run (HTTP 429 insufficient_quota). v0 on the first corpus: both models rejected
every must-fail; six of my labels were wrong (PP-E12, PP-E16, PP-E17) and were corrected.

Reading: a frontier model with the law text rejects every must-fail case in all three corpora, so the must-fail side
is not hard for a strong model; the exam's difficulty is on the other side, keeping clean material (false rejects
up to 16.7% on the exclusion near-misses for the strictest model). The beyond-window correction is missed by design.

### Decisions for the orchestrator
- L-u wording: is a sarcastic imperative ('Sell your Bitcoin, all of it', mocking central bankers) an excluded
  imperative? Two of three models said no, one yes; the case is out of the exam until decided (REQUESTS R-26).
- L-u wording: does a show's report of a company's own disclosure (Strategy's purchase, a bank charter) count as a
  'single-source breaking factual claim'? The exam keeps both (the law's example is a rumour, 'exchange X is
  insolvent'); Opus 5.5 was uncertain on both (the 16.7% above). Contested labels: exclusions neutral_company 01, 02.
- The 80 s window was reverted to the order's 60 s; the one correction beyond it is reported apart (R-24).

### Not done / handed over
- The held-out slice: R-26 (temporal seal): mined fresh once the builder freezes its gates and records the sha.
- Out of this order's scope (raised by the audit): multimodal checks (TTS inflection, on-screen text), a
  transcription-error corpus (law L-v (2)), a named legal standard for L-u.
- The whole wall's run time: 2 min 23 s at normal load (Phase 1, earlier tonight); 5 min 27 s at load average 92
  (13 users, the live run). The Phase 2 file itself takes about 30 s.

### AS BUILT (format v1 + additions; nothing removed)

- Built by `tests/adversarial/corpora/build_corpora.py` from the store through `store_extract.py`: `k` is never null
  for a REAL case and equals pp-selectid d809a1f8's `Source.sentences[k]` for the same record (tested against its
  code). The record is `provenance.record` (stripped from what the gate sees; it is in the file).
- Additions: `window.sentences[].turn` (the caption's own '>>' / 'NAME:' speaker-turn counter; null for Whisper
  records); `package.show`, `package.date` (the show date); `package.segments[].published_at`;
  `source.description_truncated` (descriptions are cut at 600 characters); `moment.timing` in exclusions; VO
  `segments[].sentences[].k`; `expected.also` (a second trap the real material carries by nature) and
  `expected.stratum` ('beyond_window': reported apart from the thresholds). Segment labels: CI `M` / `A`; VO `A` / `B`.
- Windows: 90 s before / 60 s after. Every caption dates each clip. A time word the title presents as current on the
  show date is a FAIL even with the dated caption.
- Blinding is STRICTER than published: the gate never sees `expected`, `origin`, any nested `provenance`, or the real
  id (it gets `case-<12 hex>`, salted per run); an exclusion case also loses `source.video_id`, `source.url` and every
  sentence's `k`. Cases run shuffled (the seed is in the report). Code nothing against the id or the order.
- Run your gates: `PP_MOMENTS_GATES=<module> PP_MOMENTS_PATH=/home/ultron/worktrees/pp-selectid/pipeline
  [PP_MOMENTS_ALLOW_NETWORK=1] [PP_MOMENTS_JOBS=N] python3 -m pytest tests/adversarial/test_moments_gates.py -q -s`
  (each corpus in a subprocess through `tests/adversarial/moments_exam.py`; without PP_MOMENTS_ALLOW_NETWORK=1 every
  connect, lookup and datagram is refused and reported as an ERROR; `--jobs` > 1 only for a module that declares
  THREAD_SAFE = True; an optional `preflight(counts)` may refuse a run). The test needs a report whose rows are
  exactly the committed corpus and recomputes the thresholds from them; exit codes: 0 meets, 1 misses, 2 ERROR,
  3 ABSENT (a skip only when the report says absent).

## PHASE 2 — CORPORA FORMAT v1 (published 02:57 ET; frozen: additions only, a change bumps the schema number)

One JSON file per case, `<corpus>/<case_id>.json`, plus `<corpus>/INDEX.json` = `{"schema": "pp.corpus_index/1",
"cases": [{"id", "file", "sha256"}]}`. Every text field is VERBATIM from the transcript store unless the case says
otherwise. Times are seconds in the SOURCE video. Sentences are whole sentences as the store's record reads them
(transcript_store.read_text applied: entities decoded, split tokens joined), in order; `n` is the index inside this
case's window (0-based); `k` is the sentence index in the whole record under `eligibility.split_sentences` when it could
be derived, else null (a gate must work from the text and times, never from `k` alone).

Common fields (all three schemas):
```
"schema":   "pp.ci_case/1" | "pp.vo_case/1" | "pp.excl_case/1"
"id":       "<corpus>__<class>__<NN>"                          (never interpreted)
"origin":   "REAL" | "CONSTRUCTED"     REAL = every source sentence is copied from a stored transcript (provenance
                                       names the record and its sha256); CONSTRUCTED = a class with no real instance:
                                       the sentences are written (realistic) and say so in "why"
"provenance": {"record": "<path under data/editorial or runs/, or the oracle export>", "record_sha256": "...",
              "found_by": "<the cue / search that found it>", "mined": "2026-11-12"}
"expected": {"verdict": ..., "class": "<reason class>", "why": "<one line>"}     <- the ANSWER: an adapter never reads it
"source":   {"video_id", "channel", "title", "description" | null, "published_at" | null, "url"}
```

**context_integrity (`pp.ci_case/1`, law L-s)** — expected.verdict `"pass"` | `"fail"`; classes (fail):
`steelman, quoting_opponent, sarcasm, hypothetical, conditional_split, unresolved_referent, some_people_say,
answer_without_question, later_retraction, reading_aloud, wrong_speaker, stale_time_reference, false_dialogue,
title_adds_thesis`; (pass): `clean_assertion`, `clean_conjunction_opener` (opens on And / So / But and still stands).
```
"window":  {"before_s": 90, "after_s": 60, "timing": "word" | "segment",
            "sentences": [{"n", "k", "start", "end", "text", "speaker": "<label>" | null}],   # >= 90 s before ... >= 60 s after
            "selected": [n0, n1]}                                                            # the moment, inclusive
"package": {"title", "caption",
            "vo": {"intro": str | null, "bridges": [str], "signoff": str | null},          # bridges[i] follows segments[i]
            "segments": [{"label": "clip_01", "role": "moment" | "adjacent", "video_id", "channel",
                          "text": "<verbatim>", "start", "end"}]}                            # in on-screen order
```
The `role: "moment"` segment is exactly `window.sentences[selected]`; `adjacent` segments are REAL sentences of OTHER
videos (their source in `segments[i]`), present so sequence / bridge / title effects (false dialogue, title thesis)
can be judged.

**vo_fidelity (`pp.vo_case/1`, law L-o 11 / L-t)** — expected.verdict `"pass"` | `"fail"`; the segments are REAL selected
sentences; the `lines` are AUTHORED test lines (that is the point of the corpus). Classes (fail): `stance_flip,
could_to_will, number_swapped, number_rounded, invented_agreement, fact_not_in_clips, absent_name, banned_framing,
financial_imperative`; (pass): `faithful_paraphrase, manifest_language` (channel names, "two voices", dates, the show).
```
"manifest": {"channels": [...credited, card order], "date": "YYYY-MM-DD", "show": "Pulse Check"}
"segments": [{"label", "video_id", "channel", "speaker": "<verified name>" | null, "published_at",
              "sentences": [{"text", "start", "end"}]}]
"lines":    [{"slot": "intro" | "bridge" | "signoff" | "title" | "caption", "text", "cites": ["clip_01", ...]}]
"expected": {..., "bad_line": <index into lines> | null}      # which line must be rejected (fail cases)
```

**exclusions (`pp.excl_case/1`, law L-u)** — expected.verdict `"exclude"` | `"keep"`; classes (exclude): `accusation,
partner_attack, imperative, guaranteed_return, single_source_breaking, ad_read, third_party_media, altcoin`; (keep,
near misses): `policy_criticism, framed_prediction, neutral_company`.
```
"moment":  {"sentences": [{"text", "start", "end"}]}          # 1-3 consecutive whole sentences: the candidate
"context": {"before": [{"text", "start", "end"}], "after": [...]}    # up to 60 s each side, verbatim
```

**Adapter protocol (what the harness calls).** Env `PP_MOMENTS_GATES` = an importable module (dotted; `pipeline/` and
`segment_v1/` are on sys.path), default `moments_gate_adapter`. It may define any of:
```
context_integrity(case: dict) -> {"verdict": "pass" | "fail" | "uncertain", "why": str}
vo_fidelity(case: dict)       -> {"verdict": "pass" | "fail" | "uncertain", "why": str}
exclusion(case: dict)         -> {"verdict": "keep" | "exclude" | "uncertain", "why": str}
```
`case` is the JSON above WITHOUT the `expected` and `provenance` keys (the harness strips them). "uncertain" counts as
fail / exclude (law L-s: any uncertain is a FAIL). An exception or any other return is an ERROR (reported, and the
gate's run fails: a crash is not a verdict). A missing module or function = that gate's tests SKIP with the reason
(never pass). Thresholds per gate: 100 % of must-fail (fail / exclude) cases rejected; false-reject rate on the
must-pass (pass / keep) cases <= 10 %, stated as a number. Report: a confusion table per gate and per reason class
(`PP_MOMENTS_REPORT=<path>` writes it as JSON). Run: `PP_MOMENTS_GATES=<module> python3 -m pytest
tests/adversarial/test_moments_gates.py -q -s`.

## LIVE STATE — PHASE 1 (newest first; times ET, 2026-11-12)

- **DONE** (02:30 ET): the wall is committed and pushed: **c35a2bde3c2c985b7142d4c29335e239140f400b** on
  origin/pp-tests (60 files: tests/adversarial 8, tests/fixtures/adversarial 2, docs/audits/parallel 50; nothing under
  pipeline/, scripts/ or segment_v1/). DONE WHEN met: all five families committed and pushed; every test passes or is
  a strict xfail tied to a written request (R-01..R-23); the findings-to-tests table exists (pp-tests_COVERAGE.md,
  all 244 ledger rows); this block names the commit. Not merged anywhere (the integrator merges after its own audit).
- AUDITED (pp-tests_AUDIT_RESPONSE.md): repo cross_llm_audit.py, two cycles, round 1 (GPT-4o out of credits; Gemini +
  Grok) and a final round on the fixed code with all three models (code 96/100 from each); a frontier review
  (claude-opus-5-5) found 8 real weaknesses in the wall itself, all fixed, then two verification rounds (final: READY);
  a last self-contained round (code + every claim-making doc in one package): 90/100 from Gemini and GPT-4o (Grok
  refused by the xAI gateway's own $1/day budget guard), its one actionable item implemented (call_gate).
- VERIFIED: 334 passed + 38 strict xfails (0 failed, 0 errors) in 2:00 at low load; `--runxfail`: exactly those 38
  fail, each with an AssertionError at its own assertion (pp-tests_XFAIL_EVIDENCE.md); a missing reference root makes
  every family-5 test ERROR with one clear message (19 errors in 1.5 s); regression_test.sh in this worktree 26 PASS /
  0 FAIL / 5 WARN (environmental).
- BLOCKED: nothing.

## The one command

```
cd /home/ultron/worktrees/pp-tests && python3 -m pytest tests/adversarial -q
```
CPU only, no network, no GPU, nothing written outside pytest's tmp dirs: conftest.py empties CUDA_VISIBLE_DEVICES
(qa_gates sets it to "0" at import; conftest imports it first and empties it again; an autouse fixture empties it
before every test), replaces faster_whisper with a stub that refuses to load, makes every AF_INET / AF_INET6 connect
of the test process raise (Telegram, the vision gateway, Ollama on loopback are unreachable), fakes yt-dlp at
select_passages' `subprocess`, injects model / vision replies at their HTTP seam and the Telegram sender at
deliver_run's `send`; a read-only nvidia-smi probe at session end fails the session if this pid is a CUDA compute app.
References are read read-only from /home/ultron/protocol_pulse/references (override: PP_REFS_DIR); a missing
reference FAILS (law L-m), never skips.

Measured (this machine is shared: 192 cores, load from the live run and the parallel sessions): 2:00 at load
average ~6-12 (02:10 ET), 2:40 to 4:04 at load average 45-86; the budget is 5:00. The
cost is dominated by G8 on the frozen 9:16 final (one keyframe: each frame grab decodes ~1,000-1,270 frames of
1080x1920) and the synthetic selection runs; the frame grabs are deterministic (single- and multi-threaded decodes
are byte-identical).

Reproduction: Python 3.10.12, pytest 9.0.2, numpy 1.25.2, opencv 4.13.0, Pillow 12.2.0, ffmpeg / ffprobe
4.4.2-0ubuntu0.22.04.1 (recorded in tests/fixtures/adversarial/reference_lb_edges.json); code under test = this
branch at c1451047 (pipeline/ and segment_v1/ untouched); reference checksums = each reference's own SHA256SUMS,
verified file by file by test_f5. Strict xfails: `-rx` lists each with its finding and request; `--runxfail` shows
each failing on its own assertion (pp-tests_XFAIL_EVIDENCE.md).

## What the wall pins (tests/adversarial)

| file | family | passes | strict xfails (open defects, pp-tests_REQUESTS.md) |
|---|---|---|---|
| test_f0_cpu_guard.py | the guard itself | no CUDA device visible; every Whisper load refused; no network connection can be opened | - |
| test_f1_text_meaning.py | 1 text / meaning fuzz: canon + G18, quote_in / adjudicate, align_quote, anchor, headline numbers, G20 names, G3b, idempotence | surface variants equal and meaning mutants unequal in canon, G18, quote_in, the headline check; G20 names in any surface form; G3b written / spoken amounts | R-01 idempotence; R-02 / R-03 / R-04 / R-19 quote check; R-05 anchors accept every meaning mutant; R-06 G20 channel variants; R-07 / R-08 G3b; R-16 / R-17 G18 |
| test_f2_provenance.py | 2 coordinates / provenance through select_passages.select_and_build_edl, write_lock_cut_table, gate_g16, verify_lock | a known offset recorded in file coordinates, cuts in the locked pauses, G16 PASS; a lock against another transcript or edited after selection is refused | R-09 dirty cache relabelled; R-10 transcript / lock not bound to media; R-11 lock words vs transcript; R-18 next_source_word; R-22 failed yt-dlp; R-23 SELECT with one clip / one channel |
| test_f3_release_auth.py | 3 authorisation mutations through release_auth.authorise AND telegram.deliver_run | the control is authorised and delivered; every named mutation refuses and sends nothing (33 missing-row cases: every REQUIRED row of both formats, unknown / lookalike rows, 23 non-exact verdicts incl. 'PASS (waived)', 14 empty / malformed evidence, digests of other files, the 9:16 swapped before / during delivery, skipped gates, stale manifests, packs, legacy markers, replays, no attestation) | R-12 an EDL changed after the gates is attested ALL_PASS |
| test_f4_vacuity.py | 4 vacuity: every REQUIRED gate on empty / zero / None / NaN input; garbage model replies | the gates fail closed on input that measures something wrong; release_auth blocks every vacuous PASS (0 samples); V1 and every editorial decision refuse empty / prose / truncated / wrong-shape / NaN replies | R-13 / R-14 / R-15 gates that PASS on nothing; R-20 G8 one of five samples; R-21 G8 measures an earlier render's frames |
| test_f5_references.py | 5 reference integrity (read-only) | SHA256SUMS of both references (1.7 GB + 0.3 GB), read-only, the worktree's preview copy identical; manifests describe their finals, one timeline per run; L-a: v2f one set, the preview the documented must-fail; L-b table pinned; G8 9:16 settled; the preview's legacy gate report refused by L-j | none (references are facts: PP-04 is a decision) |

## Settled by measurement: "the approved reference fails 9:16 G8" (Claude-gates #5)

REFUTED for the production wiring, on the saved files, through the public `qa_gates.gate_g8` (reference read-only):
v2f 9:16 PASSES with the reframed vertical clips as sources (out / source medians: hook 19.10 / 18.07, clip_01
50.34 / 49.54, clip_02 26.25 / 25.29, clip_03 **10.84** / 10.04, ratio 1.080; floor 10.84: zero margin); 16:9
PASSES (hook 27.56 at its floor). Without source clips (the Law 22 harness) both formats FAIL on every segment with
`no_source`: that is the recorded 'fails'. Full table: pp-tests_REQUESTS.md. Pinned by test_f5 (9:16 clip_03 through
the production wiring; the harness reading on the 9:16 hook).

## Law L-b on the references (measured, nothing adjusted)

By the law's own word-bounds measure the recorded fades overlap an edge word at: preview hook OUT +20 ms, clip_01 OUT
+73 ms (the documented must-fail), clip_02 IN +53 ms and OUT +20 ms, clip_03 IN +10 ms; v2f clip_01 OUT +20 ms and
clip_03 IN +10 ms (both recorded legacy), clip_02 OUT +10 ms and clip_03 OUT +20 ms (which G17c passes). A decision
for the orchestrator (pp-tests_REQUESTS.md PP-04); the table is pinned by test_f5.

## Assumptions taken (the order says do not stop to ask)

1. "Public entry point" = the module function a pipeline stage calls (gate_*, select_and_build_edl, authorise,
   deliver_run, quote_in, adjudicate, align_quote, anchor, spoken_channels, headline_numbers_said, ...). A GPU-made
   input (Whisper readings, SCRFD faces, a model reply) is injected at that function's own seam
   (qa_gates.whisper_segment, gate_g18's transcriber, gate_g4s's detect, LocalLLM._post, visual_check._call), never by
   calling a private helper instead of the gate. One private rule is used on purpose: run_fresh._samples (the
   production evidence rule; stage_gates itself needs GPU0) in the release backstop test.
2. "Never PASS" in family 4 = the production reading: an explicit `skip` is recorded SKIPPED by run_fresh (not a
   PASS); an exception raised INSIDE a gate fails the stage (a HOLD); an exception raised by the probe's own code
   fails the test; a plain `(True, ...)` on nothing is a PASS and is xfailed.
3. Family 4 covers the REQUIRED inventory (release-deciding). MONITORING gates (G1, G2, G4, G6, G10, G11, G13) are
   reported, not deciding (addendum '22:15' item 4); their vacuity is listed UNCOVERED in pp-tests_COVERAGE.md.
4. "SELECT success = hook + >= 2 clips + required channels" is the D contract named in the DoD (not landed); R-23
   pins it as the rule.
5. Law L-b on the frozen references is pinned as a measured table and reported as a decision (PP-04); only the
   documented must-fail is asserted as a must-fail.
6. The audit tool hard-codes ~/protocol_pulse; it was run unmodified with its module paths redirected to a scratch
   mirror (pp-tests_AUDIT_RESPONSE.md says exactly how). Nothing was written to the main tree; nothing was sent.
7. regression_test.sh needs untracked media this worktree lacks (video_pipeline_v3/assets/outro_branded.mp4 and
   assets/music/*.mp3, both git-ignored): they are provided as read-only symlinks to the main tree's files (no bytes
   copied, nothing that can enter a commit), as the sibling worktrees of this push do with copies.

## Not done / handed over

- MERGE NOTE: the repo's .gitignore line 16 (`test_*`) ignores every tests/adversarial/test_f*.py; they are
  force-added (`git add -f`), as pipeline/test_*.py are. A merge or a re-add must keep them (a plain `git add` of the
  directory silently leaves the six test files out).

- Code fixes: none by design (tests only). 23 requests with minimal fixes: pp-tests_REQUESTS.md (and how the pins
  stay honest when each fix lands).
- UNCOVERED: 147 of 244 ledger rows (pp-tests_COVERAGE.md says why for each, and tiers the riskiest).
