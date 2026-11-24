# Findings checked against the code (01:10 ET Nov 24)
Seats: qwen27b and gemma answered (effort high, 65,536 tokens); gpt-oss stops at the gateway's 32,768-token cap at
effort high with no content.

1. qwen F1 [high] "build() enables lx_soft without checking never_empty, so a clean pass can activate stand-in
   judges": REFUTED. pipeline/package.py build(): `out = _build(*args, **kw)` (the clean pass) runs first, then
   `if not never_empty or out.get("package") or flagged_today >= FLAGGED_DAY_MAX: return out` returns BEFORE any
   lx_mark; lx_mark(True) is set only around `soft = _build(*args, soft=True, **kw)` and restored in `finally`. The
   hunk shown began after that return. Tests: TestRuling154StandInJudge (the router refuses with lx_soft unset) and
   TestRuling154UnratedOpener (the clean pass seals nothing).
2. qwen F2 [high] "coherence_by_panel catches P.SpendLimit as a miss": NOT A DEFECT HERE. The except clause is the
   panel's code since ruling 130 (4) (unchanged by this diff), and every panel seat is a Heimdall model: Heimdall is
   an `uncapped` vendor (tests/package/proof_ly.py UNCAPPED, ruling 118 (b); providers.Router never reserves or caps
   it), so a seat cannot spend outside money and a SpendLimit there stops nothing that costs.
3. qwen F3 [medium] "the extra seat's one-model list is keyed by family; two seats of one family collide": FIXED.
   Keyed by the model now (`coherence_panel:seat_<model>`, kind `seat_<model>`). Each Heimdall family has one model
   today, so no build was affected.

Cycle 2 (qwen and gemma voted; both agreed F1-F3, see above for the code that refutes F1 and F2). qwen's two notes
"missed" in cycle 2 (not voted):
4. "if every stand-in step fails, Router.call re-raises the original error, so 'every back-end unavailable ... same
   vendor' can still occur": when no model at all answers there is no verdict to have (law L-m: never a pass). FIXED
   so it is never silent: the error now reads "NO JUDGE ANSWERED, the stand-in judges included (ruling 154 (1)): no
   verdict ..." with its own list's reasons and each stand-in step's (test: TestRuling154StandInJudge).
5. "a stale family-keyed one-model list can make a later seat ask a different backend": closed by F3's fix (keyed by
   the model: a stale list names the same model).
