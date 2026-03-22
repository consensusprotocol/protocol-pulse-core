## SECTION 1: CORRECTNESS

### Main user flow for the actual feature
The feature spec is **V22 multi-format output engine**: after a 12-minute episode is fully rendered and QC-passed, a parallel subprocess should generate shorts, podcast, article, tweet thread, and Nostr post.

**That implementation is not present in the provided code.**  
There is no `video_pipeline_v3/format_multiplier.py`, no wiring into `daily_producer.py`, no article adapter, no tweet-thread generator, and no Nostr publisher using `NOSTR_PRIVATE_KEY`. So the main user flow for the feature cannot be walked end-to-end because the feature appears **not implemented** in this diff.

### What is actually in the diff
Most of the code shown is:
- audit protocol docs/scripts,
- app bootstrap,
- a launcher shell script,
- unrelated media dashboard JS.

So from a correctness standpoint, this package fails the feature claim before deeper review.

### Concrete correctness issues

#### 1) Feature missing / wrong scope
- **GOSPEL.md:21-27** defines six output formats.
- **GOSPEL.md:31-40** defines expected architecture in `format_multiplier.py`.
- No such implementation is included anywhere in the code package.
- **Result:** the feature does not do what it claims.

#### 2) Audit runner points at wrong files / wrong domains
- **docs/audits/run_mu_audit.py:9** reads `protocol_pulse/static/js/media_unified_v4.js`
- Provided JS file is `media_reforge/static/js/media_unified.js`
- This script likely fails immediately with `FileNotFoundError` in many environments.
- Also this script audits unrelated media dashboard JS, not the V22 multi-format pipeline.

#### 3) “Multi-LLM audit” script is pre-build, contradicting protocol
- **AUDIT_PROTOCOL.md:15** says “Build code first. Audit code second.”
- **docs/intel/run_multi_llm_audit.py:16** explicitly says “This is a PRE-BUILD AUDIT.”
- That is a direct protocol contradiction and means the tooling itself is inconsistent.

#### 4) `launch_all_features.sh` likely creates invalid git worktree branch names
- **launch_all_features.sh:16-25** stores branch names like `feature/v22-multi-format`
- **launch_all_features.sh:36** runs `git worktree add $WORKTREE -b $BRANCH`
- `git worktree add -b` expects a branch name, but using a slash path-like branch is valid in git; however the fallback logic is brittle and suppresses stderr. If branch creation fails for another reason, the script silently retries with a different command and may attach wrong state.
- More importantly, this launcher is not feature-specific and does not verify the target branch contains the expected implementation before audit.

#### 5) Shell injection / breakage risk via unquoted variables
- **launch_all_features.sh:13, 34, 36, 39, 96, 106** use many unquoted variables.
- If paths or names ever contain spaces/shell metacharacters, behavior breaks.
- Today names are controlled, but this is still brittle automation.

#### 6) Frontend JS violates stated stack constraints
- Tech constraints say **no Canvas**.
- **media_reforge/static/js/media_unified.js:169-199** uses canvas for sparklines.
- **media_reforge/static/js/media_unified.js:760-806** uses canvas for gauge rendering.
- This is a direct mismatch with the stated platform rules.

#### 7) Timestamp updater logic is broken
- **media_reforge/static/js/media_unified.js:1175-1178** expects `.intel-card-time` elements to have `data-ts`.
- But rendered cards set visible text only:
  - Nostr notes: **556**
  - Combined feed cards: **721**
- No `data-ts` attribute is written, so periodic time refresh silently does nothing.

#### 8) Signal gauge implementation does not match expected DOM contract
- Audit facts in **docs/audits/run_mu_audit.py:27-34** say signal gauge uses IDs:
  - `sig-composite`
  - `sig-sentiment`
  - `sig-spaces`
- But **media_reforge/static/js/media_unified.js:932-940** writes only to:
  - `#signal-fill`
  - `#telem-signal`
- So if this JS is intended for that HTML, the gauge will remain stale.

#### 9) Nostr relay status bar likely never updates per relay
- Audit facts in **docs/audits/run_mu_audit.py:16-24** define relay status bar items.
- In JS, Nostr connection updates only global health dots:
  - **397-398**, **428-433**
- No code updates `.mu-relay-status` or `.mu-relay-count` per relay item.
- So “all relays show OFFLINE, 0 notes” is consistent with the code.

#### 10) Many async failures are swallowed silently
Examples:
- **media_reforge/static/js/media_unified.js:374, 416, 454, 494, 622, 757**
- Empty catches make production debugging difficult and create silent broken states.

#### 11) App startup uses insecure default secret
- **app.py:46** falls back to `dev_secret_key_protocol_pulse_2026`
- In production, if env is missing, sessions become forgeable/predictable.

#### 12) Rate limiter default is too coarse and likely wrong for real load
- **app.py:96** sets only `200 per day` globally by IP.
- For a site serving ~1000 concurrent users, this is both too restrictive for legitimate users and too weak for protecting expensive endpoints because it is not route-specific.

#### 13) Potential N+1 / expensive query in template filter
- **app.py:171** queries all active ads inside a template filter.
- If the filter is used repeatedly in a page render, this becomes repeated DB work.
- Also no visible index evidence on `Advertisement.is_active`, though model file is not provided.

---

## SECTION 2: LAW COMPLIANCE

### LAW 1: Only runs AFTER the 12-min episode is fully rendered and QC-passed
**VIOLATION**

- The required post-render implementation is absent.
- No code in the package shows gating on “fully rendered and QC-passed.”
- **GOSPEL.md:15**
- No corresponding implementation file exists.

### LAW 2: Never adds latency to the main episode render — runs in parallel subprocess
**VIOLATION**

- The required subprocess implementation is only described in spec:
  - **GOSPEL.md:31-40**
- No actual implementation is present.
- Therefore compliance cannot be demonstrated, and the feature is effectively missing.

### LAW 3: Article adapter MUST rewrite for reading (strip TTS language)
**VIOLATION**

- No article adapter implementation is included.
- No rewrite logic exists in provided code.
- **GOSPEL.md:17, 25**

### LAW 4: Tweet thread max 8 tweets, each under 280 chars, no em dashes
**VIOLATION**

- No tweet thread generator or validator is included.
- No enforcement logic exists in provided code.
- **GOSPEL.md:18, 26**

### LAW 5: Nostr publish uses PP keypair (NOSTR_PRIVATE_KEY in .env)
**VIOLATION**

- No Nostr publishing implementation is included.
- No code references `NOSTR_PRIVATE_KEY`.
- **GOSPEL.md:19**

---

## SECTION 3: SECURITY

### Secrets / credentials
- **app.py:46** hardcodes a fallback session secret. This is a security flaw in any environment that accidentally boots without `SESSION_SECRET`.
- **launch_all_features.sh:81** runs `claude --dangerously-skip-permissions`; not a direct app vuln, but dangerous operationally.
- No API keys are hardcoded in plaintext in the provided files, which is good.

### Authentication / authorization
- No route code is provided for the V22 feature, so auth posture cannot be validated.
- In `app.py`, blueprints are registered broadly with no visible auth enforcement. This is not proof of bypass, but there is no evidence of protection for sensitive routes.

### Rate limiting
- **app.py:96-97** only sets a blanket `200 per day` by remote IP.
- This is inadequate for protecting expensive API-backed routes and may also punish NAT’d users.
- No per-route limits for audit runners, media APIs, or external-service-triggering endpoints are shown.

### Input validation / shell safety
- **launch_all_features.sh** uses unquoted variables in shell commands throughout, especially:
  - **13, 34, 36, 39, 81, 96, 106**
- Since feature names/branches are internally defined, exploitability is limited, but this is still unsafe scripting practice.
- No direct SQL injection vectors are visible in the provided Python because there are no raw SQL snippets shown.

### XSS
- The JS generally escapes user content before insertion:
  - `escapeHtml()` at **127-132**
  - used in note/card rendering.
- `linkify(escapeHtml(...))` is reasonably safe in this pattern.
- One caveat: inline `onerror` HTML attributes in generated strings (**345**, **703**, **841**) are brittle and should be avoided, though not directly user-controlled here.

### CSRF
- **app.py:115-126** injects a CSRF token into templates, but there is no evidence of server-side CSRF validation. Token generation alone is not protection.

---

## SECTION 4: FRONTEND QUALITY

### Does it match the spec?
For the actual V22 feature: **no frontend implementation is shown at all**, so there is nothing to validate against the multi-format output spec.

For the included media dashboard JS:
- It looks feature-rich, but it does **not** match the stated stack constraints because it uses Canvas.
- It also appears partially mismatched to the HTML contract described in the audit script.

### Hardcoded values
- **media_reforge/static/js/media_unified.js:26-31** hardcoded Spaces accounts.
- **10-16** hardcoded relay list and meta relay.
- **45-109** hardcoded series/episodes.
- These may be acceptable content defaults, but they are not dynamic and reduce maintainability.

### Mobile / responsive risk
- Only JS is shown, not CSS/templates, so mobile cannot be fully verified.
- However, the amount of dense card content and command palette behavior suggests likely viewport issues unless CSS is very strong.

### JS errors / broken behavior
- Canvas usage may fail if expected elements are absent, though code checks for null canvas.
- More serious are DOM contract mismatches:
  - signal gauge IDs mismatch,
  - timestamp updater expects `data-ts` that is never rendered,
  - relay status bar not updated.
- These cause silent non-functioning UI rather than hard crashes.

### Loading / error / empty states
This is mixed:
- Loading skeletons exist for feeds: **1218-1223**
- Empty state exists for combined feed: **630-633**
- Keywords empty state exists: **813-816**
- But error states are weak:
  - many fetches just `.catch(function() {})`
  - no user-visible retry/error messaging for several async flows.
- So this is **not world-class**; it feels like a polished prototype with hidden failure modes.

### World-class feel
- The JS has ambition and some polish.
- But silent failures, hardcoded sources, and DOM mismatches make it feel **prototype-grade under the hood**.

---

## SECTION 5: BACKEND QUALITY

### For the actual V22 backend
There is effectively **no backend implementation provided** for the feature. So:
- no DB writes to review,
- no external API integrations for article/X/Nostr/podcast to review,
- no subprocess orchestration to review.

That alone is a release blocker.

### App bootstrap quality
- **app.py** is serviceable but has several production concerns:
  - **243-247** `db.create_all()` at runtime is risky in managed environments.
  - **96** limiter defaults are not production-tuned.
  - **111** `cors_allowed_origins="*"` for SocketIO is broad.
  - **129-163** caches `/api/` responses publicly for 60 seconds by default, which may be wrong for user-specific or sensitive APIs.

### DB operations / rollback
- No write-path code for this feature is shown.
- Therefore the requirement “all DB operations wrapped in try/except with rollback” cannot be validated and is not demonstrated.

### External API calls
- In the included JS, external browser fetches have no timeout/retry wrappers.
- In backend scripts:
  - `run_mu_audit.py` and `run_multi_llm_audit.py` call external LLM APIs with no explicit timeout handling.
  - Thread joins in **run_mu_audit.py:128** use timeout, but the underlying API calls may still hang or continue.
- Graceful degradation is partial at best.

### Cron / background jobs
- **app.py:293-299** scheduler init is wrapped in try/except, which is good.
- But no V22 cron/post-render job implementation is shown.

### Memory / resource issues
- `run_mu_audit.py` loads a large JS file into memory at startup (**9**) and embeds up to 16k chars in prompt. Fine for a script.
- `media_unified.js` keeps growing arrays bounded to 24/100 items, which is good.
- WebSocket reconnect loops are unbounded but expected.

### Logging
- Logging in `app.py` is acceptable.
- Logging in JS is poor due to swallowed exceptions.
- Audit scripts print basic status but not enough structured context for production debugging.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

1. **The actual feature is missing.**  
   The biggest gap is not polish; it is absence. A premium product cannot ship a “multi-format output engine” PR that contains docs, audit tooling, and unrelated dashboard JS but not the pipeline implementation.

2. **No observable job orchestration or status model.**  
   A Bloomberg/Blockworks-grade system would have:
   - a persisted job record per episode,
   - per-format status (`queued/running/succeeded/failed`),
   - retries,
   - duration metrics,
   - operator visibility,
   - idempotency keys to prevent duplicate posts.

3. **No compliance guardrails for output formats.**  
   World-class implementation would include deterministic validators:
   - article rewrite quality checks,
   - tweet count/length/em-dash validator,
   - Nostr signing verification with the correct key,
   - post-publish receipts/URLs stored.

4. **No failure isolation architecture shown.**  
   The spec says “parallel subprocess”; a professional implementation would isolate each format task so one failure cannot poison the rest, with structured logs and dead-letter handling.

5. **Frontend/dashboard code is over-ambitious but under-instrumented.**  
   The media JS has good product instincts, but a professional-grade terminal would not rely on silent catches and DOM assumptions. It would have explicit health telemetry, typed contracts, and test coverage for rendering/state transitions.

What is already good:
- The audit protocol concept is strong.
- Bounding in-memory arrays in the JS is good.
- Escaping user content before HTML insertion is mostly handled correctly.

---

## SECTION 7: SCORES

- Backend logic: **18/100**
- Frontend/UI: **52/100**
- Error handling: **28/100**
- Security: **41/100**
- Performance: **55/100**
- Law compliance: **0/100**
- World-class gap: **15/100**
- OVERALL: **26/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Implement the actual V22 multi-format pipeline (`format_multiplier.py`, secondary format functions, and post-render wiring) | GOSPEL.md:21-40 | The claimed feature is not present, so this PR cannot satisfy its purpose

P0 CRITICAL | Add hard gating so multi-format jobs only start after render completion and QC pass | GOSPEL.md:15 / missing implementation | LAW 1 is currently unimplemented and therefore violated

P0 CRITICAL | Run secondary outputs in isolated parallel subprocesses with failure isolation and no blocking of main render | GOSPEL.md:16,31-40 / missing implementation | LAW 2 is unimplemented; without this, the core pipeline contract is broken

P0 CRITICAL | Implement article rewrite adapter that strips TTS language and rewrites for reading before POSTing article | GOSPEL.md:17,25 / missing implementation | LAW 3 is unimplemented; article output would be noncompliant or absent

P0 CRITICAL | Implement tweet-thread generator with enforced max 8 tweets, each <280 chars, and explicit em-dash rejection/rewrite | GOSPEL.md:18,26 / missing implementation | LAW 4 is unimplemented; output can violate platform/spec constraints

P0 CRITICAL | Implement Nostr publishing signed with `NOSTR_PRIVATE_KEY` from env and verify correct PP keypair usage | GOSPEL.md:19,27 / missing implementation | LAW 5 is unimplemented; publishing would be wrong or impossible

P1 HIGH     | Remove insecure fallback session secret and fail closed in non-dev environments | app.py:46 | Predictable session secret is a production security risk

P1 HIGH     | Replace blanket `200 per day` limiter with route-specific limits for expensive endpoints and automation triggers | app.py:96-97 | Current rate limiting is both too weak for abuse prevention and too restrictive for normal traffic

P1 HIGH     | Stop publicly caching all `/api/` responses by default | app.py:153-157 | This can leak stale or inappropriate API responses and is unsafe as a blanket policy

P1 HIGH     | Fix audit tooling to point at real files and the actual feature under review | docs/audits/run_mu_audit.py:9 / docs/intel/run_multi_llm_audit.py:16 | Current audit scripts are mis-scoped and can fail or review the wrong thing

P1 HIGH     | Remove Canvas-based rendering or update constraints/spec because current JS violates “no Canvas” | media_reforge/static/js/media_unified.js:169-199,760-806 | This directly violates stated platform constraints

P1 HIGH     | Fix signal gauge DOM contract mismatch so updates target actual expected IDs | docs/audits/run_mu_audit.py:27-34,57 / media_reforge/static/js/media_unified.js:932-940 | Current implementation leaves gauge stale/broken

P1 HIGH     | Add visible error states and logging instead of swallowing async failures | media_reforge/static/js/media_unified.js:374,416,454,494,622,757 | Silent failures make production breakage invisible and hard to debug

P2 MEDIUM   | Add `data-ts` attributes when rendering timestamps so periodic refresh works | media_reforge/static/js/media_unified.js:556,721,1175-1178 | Relative times currently do not update after initial render

P2 MEDIUM   | Update per-relay Nostr status/count UI instead of only global health dots | media_reforge/static/js/media_unified.js:395-429 | Relay bar appears broken and undermines trust in live data

P2 MEDIUM   | Quote shell variables in launcher and harden worktree/branch creation logic | launch_all_features.sh:13,34,36,39,81,96,106 | Current automation is brittle and can break unexpectedly

P2 MEDIUM   | Avoid querying ads inside a template filter or cache the result per request | app.py:167-190 | Repeated DB access in template rendering can become inefficient

P3 LOW      | Replace inline HTML event handlers in generated avatar markup with bound listeners | media_reforge/static/js/media_unified.js:345,703,841 | Cleaner and more maintainable frontend code

P3 LOW      | Align protocol docs so all audit tooling consistently describes post-build review only | AUDIT_PROTOCOL.md:15-24 / docs/intel/run_multi_llm_audit.py:16 | Reduces process confusion and audit drift

---

## SECTION 9: THE ONE THING

Ship the actual post-render multi-format job system with hard law-enforcing validators before spending another minute on audit orchestration or unrelated dashboard polish.

---

## SECTION 10: FINAL VERDICT

This code is **not ready for production**. The core V22 feature is effectively missing, and all five governing laws are currently violated because there is no implementation proving compliance. The first thing that must change is to build the real post-render multi-format pipeline with explicit gating, subprocess isolation, and per-format validators; only then does a meaningful audit become possible.