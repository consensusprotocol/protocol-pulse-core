# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 39 s finish=stop usage in 5999 / out 922 usd_reported=0.022594 usd~0.053 (upper-bound price)

**CODE AUDIT REPORT — pp-selectid-20261114_2214 (spotlight.py + test)**

**Summary of review against all governing laws (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, LAW 20/M2, M12 FAIL CLOSED, LAW 22, L-d protected preview, smallest-diff rule, exact gate inventory, fail-closed on missing data, canon.py as sole text comparator, model reply validation, no reclassification of failing gates, byte-identical v2f re-renders, etc.):**

The diff implements Ruling 109 by moving the known ALONE < ALONE_MIN check immediately after P.with_verdict() and before any paid prescreen/step A. Low-scoring moments are stopped with a dedicated reason, filtered from the ms list, counted in out["ruling_109"], and cause an early why_none return if nothing remains. Unscored moments (None) continue. Tests updated to match new stop reasons and to assert which moments reach prescreen.

**Findings:**

[P1] Early stop on already-known ALONE score (before prescreen, before any span snapping or refinement) can permanently drop a moment that could still seal. A low initial ALONE on the pre-filter candidate text does not preclude a later snapped span (per SNAP LIMIT + SENTENCE LAW boundary rules) from receiving ALONE >= ALONE_MIN on the final locked selection. Stage 7 only re-checks the *current* text; the early filter therefore introduces false-negative rejections that the later guard cannot recover. This changes effective selection criteria, violates SELECTION LOCK (words fixed at selection time, no later recomputation), L-c (dissent treated as right until final-byte acoustic proof), L-f cluster-to-model flow, and the "smallest diff / no change to what a check accepts" rule (LAW 20/M2). The commit message itself flags this exact risk in "PLEASE CHECK (1)"; the implementation does not mitigate it. Must be fixed before merge.

[P2] New out["ruling_109"] key and mutated stop-reason strings alter the shape of build() output and per-moment "out" entries. While the supplied tests cover the new paths, there is no verification that release_auth.py (L-j), ATTESTATION.json, telegram delivery, or gate-inventory exact-match logic will treat the new fields as non-blocking. Any divergence from "every REQUIRED gate ran, on exactly the bytes that are sent" is a release-authorisation hazard.

[P2] No regression test exercising a moment whose ALONE score changes *after* the new early-check point (e.g. scorer updates, snapped span, or text mutated by step A) to confirm it is not erroneously filtered. The "waits for the alone scorer" test only covers the None case, not a low-then-later-high transition on a refinable candidate.

[P3] Updated test expectations now expect "ruling 109" instead of prior opener-rule or "ALONE scorer: no rating" strings; this reclassifies the failure mode without acoustic or final-byte proof (touches L-c, L-g, L-k canon rules).

[P3] Nit: long test name test_ruling_109_a_known_low_alone_never_reaches_a_paid_verdict mixes implementation detail with ruling number; also, inline comments repeat the orchestrator timestamp instead of citing the specific laws (SENTENCE LAW, SELECTION LOCK, L-c, L-j, M12) the change must obey.

[P3] Diff claims "no sealed pin lost" and references a cost-audit-pack section 10 that is not provided in the review package, preventing independent verification of replay integrity (LAW 22, L-d protected preview).

No P0 findings: no gate is shown passing what must be refused, no data loss, no violation of fail-closed on missing data/model errors (M12), no unpunctuated transcript paths opened (L-e), no model-reply partial fields accepted (L-l), canon.py usage untouched, v2f byte-identical render path unaffected, and ALONE_MIN remains a constant.

The change is small, touches only spotlight path, runs no new models/renderers, and correctly preserves the "if score is None, proceed" case. However, the core logic flaw in (P1) means it does not comply with the governing laws as written.

P1_OR_WORSE: 1