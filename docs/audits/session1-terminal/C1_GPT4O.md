I can’t perform the requested forensic audit because the package contains no code to review:

> **“THE CODE (every new and modified file) — No code files found”**

Without source files, diffs, templates, models, routes, migrations, or tests, I cannot truthfully validate correctness, security, performance, frontend quality, or law compliance, and I cannot cite line numbers.

## SECTION 1: CORRECTNESS
**Blocked — no code provided.**

I cannot walk the main user flow, verify logic, inspect race conditions, detect N+1 queries, or identify production edge cases without the implementation.

## SECTION 2: LAW COMPLIANCE
Because the **governing laws section is empty** and **no code is present**, compliance cannot be established.

- Governing laws provided: **None visible**
- Code provided: **None**

Status:
- **Overall law compliance: NOT ASSESSABLE**

## SECTION 3: SECURITY
**Blocked — no code provided.**

Cannot assess:
- SQL injection risk
- auth/authz gaps
- rate limiting
- secret leakage
- unsafe filesystem/shell usage
- CSRF/XSS/session handling

## SECTION 4: FRONTEND QUALITY
**Blocked — no code provided.**

Cannot assess:
- layout/spec fidelity
- mobile behavior
- JS/runtime errors
- loading/error/empty states
- visual quality

## SECTION 5: BACKEND QUALITY
**Blocked — no code provided.**

Cannot assess:
- transaction handling / rollback
- timeout/retry behavior for ElevenLabs / HeyGen / Wav2Lip
- cron resilience
- memory lifecycle
- logging quality
- DB indexing on sort/filter columns

## SECTION 6: WORLD-CLASS GAP ANALYSIS
Given the absence of code, the material gap is straightforward:

1. **There is no auditable implementation in this package.** A premium pre-merge gate is ineffective if the review artifact omits the actual diff.
2. **No evidence of production-grade safeguards.** For a “Bloomberg Terminal”-level product, I would expect to see:
   - explicit DB indexes for all sortable/filterable fields
   - request timeouts/retries/circuit breaking for paid external APIs
   - background job isolation for GPU/video/TTS workloads
   - rate limiting and quota enforcement
   - robust observability: structured logs, trace IDs, failure metrics
   - tests covering core session-terminal flows and failure modes

Nothing can be credited as “already excellent” because nothing is available to inspect.

## SECTION 7: SCORES (0-100 each)
These scores reflect **auditability/readiness of the submitted package**, not the unseen codebase.

- Backend logic:    **0/100**
- Frontend/UI:      **0/100**
- Error handling:   **0/100**
- Security:         **0/100**
- Performance:      **0/100**
- Law compliance:   **0/100**
- World-class gap:  **0/100**
- OVERALL:          **0/100**

## SECTION 8: PRIORITY ACTION PLAN
P0 CRITICAL | Include the actual changed files or git diff in the audit package | audit package:THE CODE section | No review can be performed; merging without inspectable code defeats the quality gate

P0 CRITICAL | Include the governing laws/spec text instead of an empty placeholder | audit package:GOVERNING LAWS section | Compliance cannot be determined against missing requirements

P1 HIGH     | Provide schema/models/migrations for any new sort/filter fields | models/migrations:unknown | Index compliance cannot be verified and performance regressions may ship unnoticed

P1 HIGH     | Provide route handlers, templates, JS/CSS, and background job code for session1-terminal | app/routes/templates/static/jobs:unknown | Core correctness, security, and frontend behavior cannot be validated

P1 HIGH     | Provide tests and representative failure-path coverage | tests/:unknown | No evidence the feature survives API timeouts, empty states, or concurrent usage

P2 MEDIUM   | Attach a file manifest with commit SHA and line-stable diff | audit package:metadata | Enables precise line-cited review across multiple reviewers

P2 MEDIUM   | Include environment/config handling examples with secrets redacted | config/.env.example:unknown | Needed to assess secret management and deployment safety

P3 LOW      | Add screenshots or recordings for key UI states | docs/review-assets:unknown | Helps validate polish, responsiveness, and async state handling

## SECTION 9: THE ONE THING
**Do not ask for a production-readiness audit without attaching the actual diff—an empty review package is itself a release-process failure.**

## SECTION 10: FINAL VERDICT
No, this is **not ready for production review**, let alone production deployment, because there is **no code to inspect** and no governing laws to validate against. The first thing that must change is the review package itself: include the full diff, relevant files, and the actual spec so a real audit can occur.