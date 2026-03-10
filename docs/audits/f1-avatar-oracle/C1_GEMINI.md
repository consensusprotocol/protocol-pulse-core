Here is a forensic code review for the `f1-avatar-oracle` feature.

### SECTION 1: CORRECTNESS

The provided code package has significant correctness issues, the most critical being that the core implementation files for the `f1-avatar-oracle` feature are missing. The review is therefore limited to the surrounding and auxiliary files.

*   **Critical Omission**: The files `oracle/avatar_server.py`, `oracle_routes.py`, and the `oracle.html` template are not included in this audit package. As `avatar_server.py` is defined by LAW 5 as the "authoritative file," its absence makes it impossible to audit the primary feature. This is a catastrophic process failure.

*   **Logic Error in `media_unified.js`**: The `run_mu_audit.py` script correctly identifies that the "SIGNAL GAUGE" is broken. The root cause is in `media_unified.js`.
    *   **File**: `media_reforge/static/js/media_unified.js:916-941`
    *   **Bug**: The function `updateSignalStrength()` calculates a composite score but does not update the correct HTML elements for the gauge itself. It writes to `#signal-fill` and `#telem-signal`, which are part of the telemetry ribbon. The HTML spec in `run_mu_audit.py` (lines 27-32) clearly states the gauge uses IDs `#sig-composite`, `#sig-sentiment`, and `#sig-spaces`. The JavaScript never writes to these, leaving the gauge permanently in its initial state.

*   **Performance Anti-Pattern**: In `app.py`, the `inject_ads` template filter performs a live database query every time it is called.
    *   **File**: `app.py:167-190`
    *   **Bug**: `models.Advertisement.query.filter_by(is_active=True).all()` is executed inside a template filter. If this filter is used on multiple content blocks on a single page, it will run N queries. This is a classic N+1 query problem that will severely degrade page load times under load. The active ads should be fetched once per request (e.g., in a `before_request` hook and stored on `g`) or cached aggressively.

*   **Risky Startup Logic**: The application startup logic in `app.py` has two notable issues.
    *   **File**: `app.py:245`
    *   **Issue 1**: `db.create_all()` is run on startup. While convenient for development, this is dangerous in production environments that use a migration tool (like Flask-Migrate, which is present). It can lead to conflicts with the migration history or accidental data loss if the models diverge from the schema. This should be disabled in production.
    *   **File**: `app.py:234-236`
    *   **Issue 2**: The `sys.modules["app"] = sys.modules["__main__"]` hack is a code smell that indicates a project structure problem, likely related to circular dependencies between `app.py` and `routes.py`. This makes the codebase harder to reason about and maintain.

### SECTION 2: LAW COMPLIANCE

Compliance with the governing laws is largely unverifiable due to the missing `avatar_server.py` file.

*   **LAW 1: Wav2Lip is the ONLY approved lip-sync engine**: **UNVERIFIABLE**. The implementation is in the missing `avatar_server.py`.
*   **LAW 2: apply_blink() is permanently disabled**: **UNVERIFIABLE**. The `apply_blink()` function is in the missing `avatar_server.py`.
*   **LAW 3: Voice = Jessica only**: **UNVERIFIABLE**. The ElevenLabs integration code is not provided.
*   **LAW 4: No Three.js, no VR, no DAO, no WebGL shaders**: **PARTIAL**. The provided `media_unified.js` is compliant and uses only standard DOM/Canvas for its sparklines. However, the `oracle.html` UI file is missing, so full compliance for the new feature cannot be confirmed.
*   **LAW 5: avatar_server.py is the authoritative file**: **VIOLATION**. The file is not included in the audit package, which is a direct violation of the audit process itself.
*   **LAW 6: Proto-P avatar asset**: **UNVERIFIABLE**. The code that loads and uses the avatar asset is missing.

### SECTION 3: SECURITY

The codebase contains several moderate-to-high security risks.

*   **Hardcoded Fallback Secret Key**: A default, non-random secret key is present in the code.
    *   **File**: `app.py:46`
    *   **Vulnerability**: `app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_protocol_pulse_2026")`. If the `SESSION_SECRET` environment variable is not set, the application falls back to a predictable, hardcoded key. This allows an attacker to forge session cookies, bypassing authentication and gaining unauthorized access. This fallback MUST be removed before production.

*   **Insecure Development Process**: The feature launch script uses a dangerous flag and an insecure pattern.
    *   **File**: `launch_all_features.sh:81`
    *   **Vulnerability**: The command `claude --dangerously-skip-permissions` is used. This explicitly disables security checks in the AI development tool. While this is a dev script, it fosters a culture of ignoring security warnings and could have unintended consequences. The entire script, which automates coding via LLM, is a novel attack surface that requires extreme caution.

*   **Unvalidated Database Writes (Potential)**: The provided code doesn't show direct user input reaching the DB, but the pattern of local imports inside functions (`app.py:169`, `app.py:224`) obscures the data flow and makes auditing difficult. Any user input used in ORM filters without explicit validation or parameterization is a potential injection vector.

*   **Rate Limiting Gaps**: The rate limiter in `app.py:96` is applied globally (`default_limits=["200 per day"]`). This is a good start, but expensive, resource-intensive routes (like any that would trigger the Oracle's GPU-based lip-sync) should have much stricter, specific limits to prevent resource exhaustion and denial-of-service attacks.

### SECTION 4: FRONTEND QUALITY

The frontend code quality in `media_unified.js` is that of a legacy prototype, not a world-class product.

*   **Monolithic "God File"**: `media_reforge/static/js/media_unified.js` is a 1200+ line file with no modularization. This is extremely difficult to maintain, debug, and test. It mixes API logic, state management, and DOM manipulation for dozens of components.
*   **Outdated Practices**: The code exclusively uses `var` instead of modern `let` and `const`, which can lead to scope-related bugs. The heavy use of `prototype` suggests an older JS style.
*   **Inadequate State Handling**:
    *   **Error States**: Error handling is minimal. `fetch` calls often have an empty `.catch(function() {})` (`media_unified.js:374`, `media_unified.js:622`), which means API failures will silently break components with no feedback to the user.
    *   **Loading States**: The primary loading state is to show a skeleton and then remove it (`media_unified.js:540`). There is no handling for what happens if the data never arrives, leaving the skeleton on screen indefinitely. This is not robust.
*   **Direct DOM Manipulation**: The code is a cascade of `document.getElementById` and `.innerHTML` updates. This is inefficient and prone to errors. While a full framework isn't required by the laws, a more structured approach (e.g., creating components as classes or functions that manage their own state and element) would dramatically improve quality.
*   **Appearance**: The UI described by the JS file appears functional but not "world-class." The reliance on `splitFlap` for every numerical update suggests a busy, potentially distracting interface. The combination of so many disparate data feeds into one view is ambitious but likely cluttered without extremely careful design, which is not evident from the code.

### SECTION 5: BACKEND QUALITY

The backend code in `app.py` shows signs of being cobbled together and contains performance and maintainability issues.

*   **No Transactional Integrity**: The `inject_ads` filter reads from the database, but there are no examples of database writes. The spec requires that "Every DB write: rollback." Without seeing the routes, I cannot confirm this, but the lack of structure in `app.py` is concerning. Any route performing multiple database operations must wrap them in a `try/except` block with `db.session.rollback()` in the exception handler.
*   **Missing API Timeouts**: The spec requires "Every API call: timeout + fallback." The `fetch` calls in `media_unified.js` do not specify a timeout. On the backend (which is not provided), Python `requests` or `httpx` calls must *always* include a `timeout` parameter to prevent requests from hanging indefinitely and tying up worker threads.
*   **Poor Logging**: Logging is configured, but critical failures like the `except Exception as e` in `inject_ads` (`app.py:188`) only log a warning (`logging.warning`). A database query failing in a request should be an `ERROR` with a full stack trace to be investigated. Context, such as the request path or user ID, is also missing.
*   **Circular Dependency "Hack"**: As mentioned in Correctness, the code at `app.py:234-236` is a workaround, not a solution. A proper Flask application structure (e.g., using an application factory pattern) would resolve this without resorting to manipulating `sys.modules`.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

Protocol Pulse aims to be a premium product, but the audited code falls short of that standard.

*   **Frontend Architecture is Subpar**: A Bloomberg Terminal or Coinbase Advanced front-end would not be built using a single 1200-line jQuery-style vanilla JS file. It would use a modern, modular architecture (ES Modules, Webpack/Vite) and likely a lightweight framework (like Preact or Svelte) or a well-structured component-based vanilla JS system for maintainability and performance. The current approach is brittle and unscalable.
*   **Real-Time is Not Real-Time**: The entire `media_unified.js` dashboard is built on polling (`setInterval`). A world-class intelligence platform would use WebSockets or Server-Sent Events to push data from the server the moment it's available. This provides true real-time updates, reduces unnecessary network traffic, and feels far more responsive and professional. The Oracle Avatar, in particular, would benefit from this for streaming video chunks.
*   **Configuration Management**: Configuration is scattered and handled by direct `os.environ.get()` calls. A world-class application would use a dedicated configuration object (e.g., populated from a file, environment variables, and defaults) to centralize and validate settings, especially for different environments (dev, staging, prod).
*   **Missing Personalization/Context**: The dashboard appears to be one-size-fits-all. A premium product would allow users to configure the layout, filter sources, set alerts, and save workspaces. The current implementation is a static display of information.
*   **Backend API Design**: While the v2 API is registered, the older API endpoints appear to be serving full HTML fragments or data blobs designed for one specific UI. A professional backend would provide a clean, RESTful or GraphQL API that is UI-agnostic, versioned, and well-documented (e.g., with OpenAPI/Swagger).

### SECTION 7: SCORES (0-100 each)

*   Backend logic:    **50/100** (Fundamental anti-patterns like DB queries in filters and structural hacks exist.)
*   Frontend/UI:      **35/100** (Monolithic, outdated, poor state handling, and not the feature under review.)
*   Error handling:   **20/100** (Mostly non-existent. Silent failures are common.)
*   Security:         **40/100** (A hardcoded secret key is a critical flaw. The dev process is questionable.)
*   Performance:      **45/100** (The N+1 query in the ad filter is a major bottleneck. Polling is inefficient.)
*   Law compliance:   **10/100** (Almost entirely unverifiable due to missing files. A direct violation of the process.)
*   World-class gap:  **25/100** (The architecture and feature set are far from a premium, professional product.)
*   **OVERALL**:          **32/100**

### SECTION 8: PRIORITY ACTION PLAN

**P0 CRITICAL | Provide the complete code for the f1-avatar-oracle feature | All Files | An audit is impossible without the code for `avatar_server.py`, `oracle_routes.py`, and `oracle.html`. This entire process is blocked.**
**P0 CRITICAL | Remove hardcoded fallback session secret | app.py:46 | Exposing a static secret key allows trivial session forgery and full account takeover in environments where the ENV var is not set.**
**P1 HIGH     | Refactor ad injection to avoid DB queries in a template filter | app.py:167-190 | This is a severe performance bottleneck (N+1 query problem) that will slow down every page render where it's used.**
**P1 HIGH     | Fix Signal Gauge JavaScript logic | media_reforge/static/js/media_unified.js:916 | The JS writes to the wrong element IDs, causing a key UI feature to be permanently broken.**
**P1 HIGH     | Implement proper error handling and user feedback | media_reforge/static/js/media_unified.js | Silent failures on API calls leave the UI in a broken or perpetually loading state, making the product seem unreliable.**
**P2 MEDIUM   | Refactor monolithic JavaScript into modern modules | media_reforge/static/js/media_unified.js | The entire file is unmaintainable. Breaking it into components is essential for future development.**
**P2 MEDIUM   | Remove `db.create_all()` from production startup | app.py:245 | This conflicts with migration tools and poses a risk to database integrity in production.**
**P2 MEDIUM   | Replace polling with WebSockets for real-time data | media_reforge/static/js/media_unified.js | Polling is inefficient and not truly "live". WebSockets are the professional standard for intelligence dashboards.**
**P3 LOW      | Resolve the circular dependency causing the `sys.modules` hack | app.py:234-236 | This indicates a structural problem that should be fixed with an app factory pattern for long-term maintainability.**

### SECTION 9: THE ONE THING

The core code for the feature supposedly under review, `f1-avatar-oracle`, is entirely missing, making a meaningful audit of its implementation and law compliance impossible.

### SECTION 10: FINAL VERDICT

This code is absolutely not ready for production. The audit process has failed by omitting the primary feature's implementation files. Furthermore, the provided supporting code contains critical security vulnerabilities (hardcoded secret key), severe performance anti-patterns (N+1 queries), and clear frontend bugs. The entire package must be rejected until the feature code is provided and the identified P0/P1 issues are resolved.