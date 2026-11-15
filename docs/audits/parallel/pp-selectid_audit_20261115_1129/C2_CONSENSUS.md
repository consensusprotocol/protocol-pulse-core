# C2 CONSENSUS — pp-selectid audit 20261115_1129 (ruling 112's diagnosis driver, tests/package/hook112.py)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0; the findings it tags P1 in its text it settles there) and glm-5.3-flash
(P1_OR_WORSE: 1). They disagree on a P1, so Grok was asked: grok-4.20-0309-reasoning (P1_OR_WORSE: 0, all P2/P3).
AUDIT TOTAL: $0.0527 vendor-reported (cap $1.00).

glm's P1 (F12): "the calibration's record_dir (proof/hook112/replies) is never created; if providers.Router does not
mkdir it, the first paid call dies". NOT A DEFECT. providers.Router._record (pipeline/providers.py:1286-1288, UNCHANGED)
does `os.makedirs(os.path.dirname(path), exist_ok=True)` before every recording. The path is
record_dir/<key[:2]>/<key>.json, so the first call creates record_dir and its subfolder. No real defect was found, so
there is no third cycle (ruling 107 (2)). THE CODE LANDED IS THE CODE AUDITED (FINAL.diff = C2_STEP.diff).

ACCEPTED, RECORDED FOR THE NEXT CHANGE TO THIS DRIVER. None changes a stage count, so the run's numbers stand:
1. glm F15 / Grok: reason_class's pattern order (the topic rule before the opener rule) deserves an assertion. Grok:
   its "STAND_ALONE with the clip scorer|" alternative is dead, because "STAND_ALONE" alone matches. It affects
   labels only.
2. glm F7: a test for the ledger-id fallback (a moment with no mined.ledger_moment_id resolves to its build id).
3. glm F4: spotlight_trace keeps `>` on a same-stage tie between pool.out and a folded span; funnel uses `>=`. Only
   the reason label of a tie can differ, never the stage.
4. Grok: a test for a spotlight rating with no cache record (rater None); a comment citing the spotlight.build lines
   that write "step A: ..." (the text the trace matches).
5. glm P3s: comments (the held-back predicates; the first event's call window is the video's whole history, which is
   the right attribution; went_on; the per-seed stop under the router's hard cap). The report prints hook_rows as a
   dict.

AGREED BY ALL: both cycle-1 P1 items are resolved (qwen's withdrawn: "may open" is can_open; glm's fixed, failures
before the rating). The calibration is Heimdall only (the hook list filtered on "heimdall/<family>"; hook_ratings makes
only that one kind of call), uses no cache, gets no shadow, uses its own ledger and stays under the router's $0.30.
Every read of pp-ingest's queue is mode=ro, and its ledger is only read.
