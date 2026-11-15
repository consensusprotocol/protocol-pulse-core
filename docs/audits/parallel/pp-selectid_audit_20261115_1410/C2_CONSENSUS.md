# C2 CONSENSUS — pp-selectid audit 20261115_1410 (ruling 115 (1)+(2), the calibrated hook bar)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 1), glm-5.3-flash (0); they disagree on a P1, so Grok was asked (0). Cycle 2:
$0.0716; the audit $0.1473 vendor-reported. No third cycle: cycle 2 found no real defect.

THE ONE P1 (qwen): the reading of "nothing else about the hook path changes" (the hook's slot in the clips-alone and
coherence verdicts and in ruling 62 is judged by the calibrated bar; the clips after it keep COHERENCE_MIN). qwen:
"a semantic change; ensure PBX approved this reading". glm and Grok: the only reading under which a scroll-3 floor
can open a medley (a hook at its floors has rating 3 < COHERENCE_MIN 4); not a defect. It goes to the orchestrator
on STATE line 1 as the reading taken (a question in CAPITALS, ruling 106), with "keep" recommended.

Every cycle-1 fix was checked and agreed by all three (the future / naive measured_at, the rater-change cache, the
seed in the version, the spotlight pin's mark, the minute in the bar's cache key).

ACTED ON IN THIS PASS (glm's new P2s):
1. glm "the cache's fallback when the router has no hook list silently serves any cached rating". FIXED: a stand-in
   router WITHOUT chain() keeps the old behaviour (tests' routers); a router whose hook list is MISSING
   (ProviderError) serves NO cached rating (fail closed: every hook is asked, and with no list the ask fails too, no
   rating, law L-m). New test leg; mutation P16 killed.
2. glm "the mark made at seal time can disagree with the bar the gates were judged on (the minute cache)". FIXED: the
   medley's mark is made from the bar its build captured at the hook stage (the one hook_pool names), and the
   spotlight's from the bar captured right after its openers were rated (hook_bar_mark(live)). New tests switch the
   live bar to another valid one after the hook stage (at the write / at package_for): the mark still names the
   judged bar. Mutations P17 / S5 (a fresh read at seal time) killed.

NOT CHANGED:
3. Grok [P2] "a calibration missing its floors gets the generic message": the message ("no readable measured_at or
   floors") is accurate and the file is fail-closed either way.
4. glm [P2] "hook112.build_router defaults to the Heimdall list": deliberate (production's list is Grok alone now;
   the driver is Heimdall-only by its order); the startup line prints the list used.
5. Grok's condition "(c) a calibration run with the new HOOK_VERSION bytes": the version is a LABEL of the asking (the
   prompt bytes sent, alone, seed 7). Adding the seed to the label did not change one byte sent to the model, so the
   measured floors stand; the relabel is noted in the file. The daily re-run (VALID_H 24 h) measures it afresh by
   18:07 UTC Nov 16.

TESTS: all 37 suite files of the handoff pass, one process each (768 tests). Mutations: 41 (the cycle-1 38 + P16 /
P17 / S5), each killed after a control run; the full set's final run is in the commit message.
