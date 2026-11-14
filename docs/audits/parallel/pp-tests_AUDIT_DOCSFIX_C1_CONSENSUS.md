# pp-tests_docsfix — CYCLE 1 CONSENSUS (written by the session; 2026-11-14)

Why the session writes it: the repo tool's consensus step (claude-sonnet-4-6) cannot run, because Anthropic is out of
credit. Rule (pp-ingest's): consensus = the same finding from >= 2 reviewers, or one reviewer's finding verified against
the text. Refutations carry their evidence.

Reviewers (the same AUDIT_PACKAGE.md, 27,107 chars, built by the repo tool from the brief and the docs diff):
- gemini-2.5-pro: 100, "no fixes or improvements are required".
- Heimdall qwen3.8-27b: 95, one P1, one P2 and one P3.
- Heimdall glm-5.3-flash: 88, one P1, two P2 and two P3.

## Dispositions (all text edits; no test changed)
1. qwen P2 and glm P3, both branches of R-30 spelled out. CONSENSUS (two reviewers). DONE:
   - YES: the builder changes NUMBER (with its audit) and the corpus stays. Acceptance: no "lost yield: the dated
     sign-off" row.
   - NO: the gate stays, and pp-tests rewrites the 30 sign-offs and re-reviews them. Acceptance: no line of the corpus
     carries a date's digits.
2. glm P1, "the trap-level outcome of the 14 must-fail cases". ACCEPTED as a statement of what is known: it is NOT
   measured yet; the builder's report gives it per case. Until then, must-fail recall on those 14 is unknown.
3. glm P2, "cite the source of the class-C rule". DONE: the orchestrator's order of 2026-11-12 05:25 ET, quoted in
   pp-tests_AUDIT_INTEG_BRIEF.md ("Order 2").
4. glm P2, "'ON THEIR TITLE (NEEDS_SOURCE, NUMBER, PRICE_NOW)' overstates". ACCEPTED: the text now says the builder
   REPORTS it, names NEEDS_SOURCE and NUMBER as title figures in no clip, and says PRICE_NOW fails by absence here.
5. glm P3, "the live state is not newest-first". VERIFIED, and the root cause was worse: STATE carried hand-typed
   "~" times, and the cycle-3 entry said "~10:20" though 12c7e48d was committed at 09:52, before the 10:02 merge. All
   times on 2026-11-14 are now the git commit times (08:06, 08:51, 09:24, 09:52, 10:02; the builder's 91d37100 09:48),
   and the list is newest-first.
6. qwen P1, "add a CI run ID proving 91d37100 fixed R-29". PARTLY: there is no CI here, and the commit hash is the
   immutable reference. DONE: R-29 now says the fix is on origin/pp-selectid, NOT yet on the release line, and names
   the builder's own audit record (docs/audits/parallel/pp-selectid_audit_0915 on that branch).
7. qwen P3, "say whether the PRICE_NOW question is independent of R-30". DONE: independent (a date in a production
   line vs a price).

No P0. No text asks for a check to be loosened (Gemini, qwen and glm agree on B). Cycle 2 reviews the updated diff.
