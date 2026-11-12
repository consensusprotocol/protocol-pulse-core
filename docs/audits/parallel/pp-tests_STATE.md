# pp-tests STATE — session pipeline_pp_tests (worktree /home/ultron/worktrees/pp-tests, branch pp-tests)

## LIVE STATE (newest first; times ET, 2026-11-12)

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
