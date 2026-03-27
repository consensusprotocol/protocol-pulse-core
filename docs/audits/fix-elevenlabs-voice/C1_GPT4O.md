I can’t perform the requested forensic review because the audit package contains no code:

> **“THE CODE (every new and modified file) — No code files found”**

Without source files, I also can’t cite line numbers, verify behavior, assess compliance, or score implementation quality in a meaningful way. The only honest review is that the package is incomplete and fails the quality gate by default.

## SECTION 1: CORRECTNESS
**Blocked.** No code provided, so the main user flow cannot be traced.
- Cannot verify ElevenLabs voice fix behavior
- Cannot inspect for logic errors, silent failures, race conditions, N+1 queries, or production edge cases

## SECTION 2: LAW COMPLIANCE
Because no implementation is present, compliance cannot be demonstrated.

- **Technology stack constraints:** **PARTIAL / UNVERIFIABLE**
  - Python/Flask/SQLAlchemy usage: unverified
  - No Three.js/WebGL/Canvas: unverified
  - Route scalability for ~1000 concurrent users: unverified
  - DB indexes on sort/filter columns: unverified

- **Governing laws section:** **UNVERIFIABLE**
  - The package says “see gospel” / laws omitted, so there is no actual law text to evaluate against.

## SECTION 3: SECURITY
**Blocked.** No code to inspect for:
- SQL injection
- auth bypass
- rate limiting gaps
- hardcoded secrets
- unsafe input reaching DB/filesystem/shell

## SECTION 4: FRONTEND QUALITY
**Blocked.** No templates, CSS, or JS provided.
- Cannot verify layout, responsiveness, async states, or polish

## SECTION 5: BACKEND QUALITY
**Blocked.** No backend code provided.
- Cannot verify transaction handling, rollback discipline, timeout/retry behavior, cron resilience, memory usage, or logging quality

## SECTION 6: WORLD-CLASS GAP ANALYSIS
Material issue: **the review artifact itself is not production-grade**. A premium engineering workflow should never open a merge gate with an empty diff package. Bloomberg/Coinbase-grade teams would require:
- complete changed-file bundle
- tests for the fix
- reproducible steps
- API contract changes, if any
- migration/index notes, if any
- observability impact

## SECTION 7: SCORES
Given the absence of code, these scores reflect **reviewability and merge readiness**, not implementation quality.

- Backend logic:    **0/100**
- Frontend/UI:      **0/100**
- Error handling:   **0/100**
- Security:         **0/100**
- Performance:      **0/100**
- Law compliance:   **0/100**
- World-class gap:  **0/100**
- OVERALL:          **0/100**

## SECTION 8: PRIORITY ACTION PLAN
P0 CRITICAL | Attach all new and modified files for feature `fix-elevenlabs-voice` | audit package:THE CODE | No review can be performed; merge would be blind and unsafe  
P0 CRITICAL | Include the actual governing laws/spec text (“gospel”) in the package | audit package:GOVERNING LAWS | Compliance cannot be evaluated against missing requirements  
P1 HIGH     | Include tests covering the ElevenLabs voice fix and failure modes | tests:missing | Without tests, regressions and API-edge failures will reach production  
P1 HIGH     | Include schema/index changes for any new sort/filter paths | models/migrations:missing | Missing indexes will degrade under ~1000 concurrent users  
P2 MEDIUM   | Include request/response examples and reproduction steps | audit package:missing docs | Reviewers cannot validate intended behavior versus implementation  
P3 LOW      | Include commit diff summary and touched routes/services | audit package:missing metadata | Improves audit speed and reduces missed issues

## SECTION 9: THE ONE THING
**Do not ask for a production merge review with an empty code bundle—make the audit artifact complete, or every downstream quality signal is meaningless.**

## SECTION 10: FINAL VERDICT
No, this is **not ready for production review**, let alone production deployment. The first thing that must change is to provide the actual modified code, tests, and governing spec text; until then, any approval would be negligent.