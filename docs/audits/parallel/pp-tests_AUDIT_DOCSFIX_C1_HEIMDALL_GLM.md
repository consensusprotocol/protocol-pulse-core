<!-- z-ai/glm-5.3-flash, 35 s, finish stop, $0.0005 (vendor usage.cost) -->

# FORENSIC REVIEW — pp-tests_docsfix (docs-only diff, 202 lines)

Scope note: this diff touches only `docs/audits/parallel/pp-tests_{BIBLE_ADDITIONS,REQUESTS,STATE}.md`. Sections 3–5 (security/backend) are therefore N/A beyond what the docs claim; I flag where the docs assert unverified things.

---

## SECTION 1: CORRECTNESS

Walking the claims against the Facts:

1. **R-29 correction (lines 45–48, 57–65, 161–164, 192):** consistent. Old text said the stale-title cases "pass whatever the gate would say"; corrected to "gate rejected them on their dated sign-off." Matches the Facts (builder measured NOT passed; sign-off "Pulse Check for 2026-11-12." trips NUMBER). ✔
2. **PP-E28 correction (lines 11–13):** "An omission shows what is NOT judged, not what the verdict will be" — consistent with the Facts and with PP-E33. ✔
3. **PP-E33 (lines 22–33):** bad_line i → slot "<slot>_i", bad_title → "title", "HOLE HIDDEN BY ANOTHER LINE" — matches the Facts verbatim. ✔
4. **R-30 (lines 67–92):** 92 cases / 30 dated sign-offs / 16 must-pass + 14 must-fail — matches Facts. "NOT a request: a decision for the orchestrator" and the withdrawn first draft (line 77) satisfy the R-19 precedent. ✔
5. **PRICE_NOW decision (lines 100–109):** $76,000 vs $73,500 = 3.4 %, 5 % tolerance — matches Facts. ✔
6. **Universe news ages (lines 64, 106):** 38.6/43.0/45.1/7.3 h, 7.3 h item states no Bitcoin level → levels [] → PRICE_NOW fails by ABSENCE. Matches Facts. ✔

**Minor discrepancies / overstatements:**

- **Line 63 vs 65 (internal tension, not a contradiction):** line 63 says both stale-title cases now fail "ON THEIR TITLE (NEEDS_SOURCE, NUMBER, PRICE_NOW)" — but line 65 says PRICE_NOW fails *by absence* because the 7.3 h item states no level, i.e. the price trap is NOT exercised. Line 106–107 admits this ("the exam cannot exercise the tolerance"). A careful reader gets the right answer, but line 63's "ON THEIR TITLE" reads stronger than the mechanism. Also: the Facts say the *builder* measured the old-adapter rejection on the sign-off; line 63's parenthetical (NEEDS_SOURCE, NUMBER, PRICE_NOW) is attributed to the *fixed* adapter — the Facts do not confirm those three violation codes. **Uncertain; say so.** (The Facts only confirm the old-adapter sign-off rejection and the 3.4 %/5 % arithmetic.)
- **Line 51:** "the gate never saw" (was: "never sees") — tense now correct post-fix. ✔
- **Line 82:** "Under the order of 05:25 ET Nov 12 (class C: production lines must match the manifest)" — this order/class-C reference is not in the Facts. Cannot verify from the diff. Flag as unverified.
- **Line 130:** "entry 10:02" in the DoD — not verifiable from the diff; the Facts say the integrator merged at d1ccdfc7 but give no DoD entry time. Minor.
- **Line 126 vs 200:** "382 passed, 40 xfailed, 3 skipped, 0 failed" — consistent with line 200's earlier count. ✔
- **Line 131–132 vs 170–171:** the exam-approval conditions (heimdall_first, $5.00, hard stop $4.00, free replay) are stated twice, identically. ✔ But note: the Facts say the *sign-off caveat and PRICE_NOW decision* are in the DoD — line 130 says exactly that. ✔

No logic errors, no contradictions. One unverified detail (class C / 05:25 order) and one overstated violation list (line 63).

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|---|---|---|
| Tests only (tests/adversarial/, docs/audits/parallel/pp-tests_*) | **COMPLIANT** | Diff touches exactly 3 docs files (lines 1, 34, 114). "No test changed" (line 195) is true. |
| Never change what a check accepts | **COMPLIANT** | R-30 explicitly withdrawn the change-request; "NOT a request: a decision" (line 67), "My first draft asked the builder for that change; it is withdrawn" (line 77). |
| R-19 precedent: loosening is the orchestrator's ruling | **COMPLIANT** | Lines 75–76, 148–149. |
| L-m: nothing measured is never a pass | **COMPLIANT** | Every load-bearing claim cites a measurement ("read and confirmed", lines 57, 147, 161; "measured by the builder", line 68). |
| Only report what you can verify; if uncertain, say so | **PARTIAL** | Lines 82 (class C / 05:25 order) and 63 (the NEEDS_SOURCE/NUMBER/PRICE_NOW triple) assert specifics not in the Facts. Line 52's "not measured" honesty (dropping `after`) is exemplary, though — the discipline is mostly there. |

---

## SECTION 3: SECURITY
N/A — docs only. No secrets, no routes, no queries introduced. (Verified: the diff contains no code.)

---

## SECTION 4: FRONTEND QUALITY
N/A — markdown. Formatting is consistent; the STATE newest-first ordering (lines 190–201) is maintained correctly (11:00 above 10:00 above 10:20 — note 10:20 appears *below* 10:00 at line 198, which breaks strict newest-first, but 10:20 is the *earlier* 12c7e48d entry being re-dated; slightly confusing, cosmetic only).

---

## SECTION 5: BACKEND QUALITY
N/A — no code. The docs' *process* quality (hashes cited: 91d37100, d1ccdfc7, 12c7e48d, a55e4dcf; ET timestamps; "read and confirmed") is genuinely good provenance discipline.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

- **Excellent:** the correction discipline. PP-E28's "an omission shows what is NOT judged" (line 13) and PP-E33's trap-location scoring (lines 28–33) are real, transferable insights, not filler. The R-30 "decision, not request" framing with the withdrawn first draft preserved (line 77) is exactly how an audit trail should work.
- **Missing, material:** the 14 must-fail cases' *trap-level* outcome under the fixed adapter is not stated. Facts confirm the old-adapter sign-off rejection; line 63 hints at the new violations but nobody states whether, post-91d37100, the 14 must-fail cases are now caught *on their own bad line* or still "hidden by another line" (the sign-off). That single number decides whether the exam is worth $5. Line 167's "reads up to 14 too high" acknowledges the risk but the diff never resolves it — even though the fixed adapter's behavior was measured (line 63).
- **Missing, minor:** R-30's "The corpus follows the ruling" (line 80) has no acceptance criterion for the YES branch (what exactly gets re-reviewed if the ruling is YES? Only the 16 must-pass "lost yield" items?).

---

## SECTION 7: SCORES

- Backend logic: 88/100 (docs; one overstated violation list, one unverified class-C reference)
- Frontend/UI: 85/100 (clean markdown; minor chronological wobble at line 198)
- Error handling: 90/100 (uncertainty flagged at line 52; "not measured" honesty)
- Security: N/A → 90/100 (nothing to break)
- Performance: N/A → 90/100
- Law compliance: 92/100 (two unverifiable specifics; otherwise exemplary)
- World-class gap: 82/100 (the 14-case trap-level outcome is the missing headline number)
- **OVERALL: 88/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P1 HIGH | State the post-fix trap-level outcome for the 14 must-fail dated-sign-off cases (caught on their own bad line, or "hole hidden"?) | pp-tests_REQUESTS.md:86–90 | It determines whether the $5 exam measures anything; currently the reader must infer it.
P2 MEDIUM | Cite the source for "order of 05:25 ET Nov 12 (class C)" | pp-tests_REQUESTS.md:82 | Unverifiable from the Facts; the orchestrator ruling on R-30 depends on the labels' provenance.
P2 MEDIUM | Qualify line 63's "(NEEDS_SOURCE, NUMBER, PRICE_NOW)" as builder-reported, or list which of the three sits on the title | pp-tests_REQUESTS.md:63 | PRICE_NOW fails by absence (line 65), so "ON THEIR TITLE" overstates what the title-trap exercise shows.
P3 LOW | Add the YES-branch acceptance criterion to R-30 ("corpus follows the ruling") | pp-tests_REQUESTS.md:80 | Only the NO branch (lines 84–85) has a concrete follow-up.
P3 LOW | Fix newest-first ordering: the 10:20/12c7e48d entry (line 198) sits below the 10:00 merge (line 196) | pp-tests_STATE.md:196–198 | Cosmetic; breaks the stated convention.

---

## SECTION 9: THE ONE THING

State, in one measured sentence, whether the 14 must-fail cases are now rejected *on their own trap* under 91d37100 — because that number, not the R-30 ruling, is what tells the orchestrator whether the paid exam measures the gate or the sign-off.

---

## SECTION 10: FINAL VERDICT

Ready to merge as-is: it is a docs-only correction, internally consistent with the Facts, and it correctly honors the R-19 precedent by converting R-30 into an orchestrator decision with the original request withdrawn. Before the orchestrator rules, add the post-fix trap-level outcome for the 14 must-fail cases and cite the provenance of the 05:25 class-C order — those are the only two claims a reviewer cannot verify from the material given.