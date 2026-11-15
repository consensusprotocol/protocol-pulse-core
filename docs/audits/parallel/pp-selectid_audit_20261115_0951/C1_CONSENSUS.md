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
   is that one keyword: no test reaches the driver past its router.
7. Grok [P3] "an inline comment at the window_refused site; the docstring on which row decides". Both done. The
   docstring now states the any-worked-row rule.
8. Grok [P2] / glm [P3] the two surviving mutations. They stay, disclosed: the driver past its router (R11) and the
   funnel report script (R12). Neither changes a build.

THE CODE NOW: pipeline/ledger_build.py adds WORKER_BLOCK and worked_by_worker(), refused = worked - ready, and
window_refused_videos. The tests add B / C / E and the per-video assertion. Mutations: 16 of 18 killed after a control
run (the unmutated copy passes all 93 tests); R11 and R12 survive as stated. Suites: 684 pass.
