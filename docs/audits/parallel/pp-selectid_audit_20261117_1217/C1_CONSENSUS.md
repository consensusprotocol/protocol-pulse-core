# Cycle 1 consensus (pp-selectid_audit_20261117_1217, stage 2a)

SEATS ANSWERED: 2 of 3. qwen3.8-27b: P0/P1 none, a traced review. gpt-oss-20b: 6 P0/P1 claimed, every one refuted below
from the code. gemma-4-31b-it: its 24,000-token cap ran out with no answer.

## gpt-oss's claims, checked against the code (the unchanged lines below were outside cycle 1's diff hunks)
1. [P0] "soft_second never mutates cleared": REFUTED. soft_second (package.py:528) calls add_flags(m, c) (:536), and
   add_flags (:522) sets m["step_a_flags"] on the moment object held in cleared. The test asserts
   cleared["b"]["step_a_flags"] == ["REFERENT_OUTSIDE"], and mutation E4 (add_flags removed) is killed.
2. [P0] "context_a's status uses the cuttable expression": REFUTED. context_a is row(bool(a_rows) and (not a_codes or
   soft_a), ...). The expression quoted belongs to the separate "cuttable" row.
3-6. [P1 x4] "inventory's a_by is keyed by moment id, so lab_codes, who and seg_flags miss": REFUTED. Both call sites
   pass a_by = a_lab, built UNCHANGED as {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]} (package.py:3685
   and :4173): keyed by LABEL, like who and seg_flags. Only truth and exc are keyed by moment id, which is why the
   cuttable flags map through mids. The tests feed a_by={"clip_01": ...}, as the pipeline does.
7. [P2] "soft_step_a is never used in _build": REFUTED. cleared_pool calls it (:556), and _build calls cleared_pool
   (:3227). Stage 1, live.
8. [P2] "fails may be None": DECLINED. prescreen (:649) always returns a dict of failures.
9. [P2] "soft_step_a's copy drops the moment's keys": REFUTED. dict(m, step_a_flags=c) keeps every key of m.
10. [P2] "soft_edges needs ok True": BY DESIGN. A missing ok is an unmeasured word check, and unmeasured is never a
   pass (law L-m), so it stays hard.

## No change from cycle 1 to cycle 2.
