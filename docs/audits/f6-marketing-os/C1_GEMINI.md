An independent audit of feature `f6-marketing-os` follows.

### SECTION 1: CORRECTNESS

The most critical finding of this audit is that **the core feature is not present in the submitted code.** The GOSPEL and LAWS describe a "Marketing OS" with a `MilestoneService`, database models (`performance_metrics`, `milestone_fired`), a cron job, and a `/api/launch-gate` endpoint. None of this implementation exists in the provided Python files. The submission consists primarily of documentation, audit-runner scripts, and unrelated modifications to a large JavaScript file.

Therefore, a correctness audit of the main user flow is impossible. The feature, as specified, does not exist.

**Analysis of Submitted (Unrelated) Code:**

*   **`media_reforge/static/js/media_unified.js`**:
    *   **Logic Error / Silent Failure:** In `NostrFeed.prototype.connect` (line 386), the `onclose` handler schedules a reconnection. However, `onerror` (line 427) simply calls `ws.close()`, which then triggers the `onclose` reconnection logic. This means a persistent error (e.g., invalid relay URL, network block) will cause an infinite, tight loop of connection attempts, potentially DDOSing the client's own network or the relay. The reconnection delay backoff helps but doesn't solve the underlying issue of retrying on unrecoverable errors.
    *   **Potential Race Condition:** The `updateSignalStrength` function (line 916) reads from shared state (`state.nostrNotes`, `state.chainData`, `state.fngData`) which is written to by multiple independent, asynchronous `fetch` calls. While JavaScript's single-threaded nature prevents true race conditions on reads/writes, it's possible for the signal score to be calculated using a mix of fresh and stale data (e.g., new Nostr data but old FNG data), leading to a temporarily inaccurate composite score.
    *   **Hardcoded Values:** `NOSTR_RELAYS` (line 10), `POLL_INTERVALS` (line 18), and `SPACES_ACCOUNTS` (line 26) are all hardcoded. This makes configuration changes require a code deployment. These should be fetched from a configuration endpoint.

### SECTION 2: LAW COMPLIANCE

The code is in **VIOLATION** of all specified laws due to a complete lack of implementation.

*   **LAW 1: Launch gate — 9 items must ALL be ✓ before milestone campaigns fire**
    *   **Status:** VIOLATION
    *   **Reason:** The required `/api/launch-gate` endpoint is not implemented anywhere in the provided Flask app (`app.py`, `routes.py`, etc.). There is no code to check any ofthe 9 conditions.

*   **LAW 2: Price milestone triggers (fire ONCE per milestone, never repeat)**
    *   **Status:** VIOLATION
    *   **Reason:** The `MilestoneService` specified in `GOSPEL.md` is missing. The `milestone_fired` database table/model is not defined or migrated. The core logic for checking the price against milestones and ensuring it fires only once does not exist.

*   **LAW 3: What each milestone trigger fires**
    *   **Status:** VIOLATION
    *   **Reason:** No code exists to perform any of the 5 required actions (generate video, post Nostr note, send newsletter, activate banner, update Oracle). The frontend banner component mentioned in the GOSPEL prompt is also missing from the provided JS and HTML context.

*   **LAW 4: Performance metrics schema**
    *   **Status:** VIOLATION
    *   **Reason:** The `performance_metrics` table is defined in the GOSPEL, but no corresponding SQLAlchemy model or database migration file was provided. The `db.create_all()` in `app.py` (line 245) will not create this table as the model is not defined and imported.

### SECTION 3: SECURITY

*   **Secrets in Code:**
    *   **`app.py:46`**: A fallback `app.secret_key` is present. While this is noted as a "fallback for local dev," it's a security risk. If the `SESSION_SECRET` environment variable is ever unset in production, the app will fall back to this known, hardcoded secret, making all user sessions vulnerable to trivial hijacking. The application should fail to start if the production secret is missing.

*   **Unvalidated User Input:**
    *   **`app.py:178`**: The `inject_ads` template filter builds HTML with f-strings. Data like `ad.image_url` and `ad.name` are injected directly. If an admin interface allows setting these ad properties, and that interface does not properly sanitize input, a malicious user with access could inject arbitrary HTML/JS into pages, leading to a stored Cross-Site Scripting (XSS) vulnerability.

*   **Dangerous Execution Practices:**
    *   **`launch_all_features.sh:81`**: The script runs `claude --dangerously-skip-permissions`. This is an extremely high-risk practice. It indicates the process is bypassing security sandboxing and safety checks built into the `claude` CLI tool. Whatever this script does, it's doing it with elevated and unchecked permissions, which could have severe consequences if the build process is compromised or generates malicious code.

*   **Information Leakage:**
    *   **`launch_all_features.sh:43`**: The script writes a temporary prompt file to a predictable location in `/tmp/`. On a multi-user system, this could allow other users to read the contents of the prompts, which may contain sensitive details about the application's architecture or upcoming features.

### SECTION 4: FRONTEND QUALITY

The required frontend component for this feature—the homepage banner—is missing.

**Analysis of Submitted (Unrelated) Frontend Code:**

*   **`media_reforge/static/js/media_unified.js`**:
    *   **Loading/Error States:** The file shows a pattern of removing `.mu-skeleton` elements on successful data load (e.g., line 540, 628). However, the `.catch()` blocks for most `fetch` calls are empty or just call `setHealth` (e.g., line 294, 622). There is no user-visible error state. If an API fails, the section will simply remain in its initial skeleton/loading state indefinitely with no indication to the user that something is wrong.
    *   **Mobile Breakage:** The code does not contain any explicit logic for handling different viewports. While the layout may be responsive via CSS (not provided), the fixed-width canvas elements for sparklines (`SparklineRenderer`) and the sentiment gauge (`drawGauge`) will likely render poorly or become unreadable on small screens without responsive resizing logic.
    *   **Maintainability:** The `media_unified.js` file is a 1200+ line monolithic script. It mixes concerns (data fetching, state management, rendering for multiple distinct components, utility functions). This makes it extremely difficult to debug, maintain, or modify without risking side effects. It is prototype-quality in its structure.

### SECTION 5: BACKEND QUALITY

The required backend code for this feature is missing.

**Analysis of Submitted (Unrelated) Backend Code:**

*   **`app.py`**:
    *   **Error Handling:** The `inject_ads` filter at `app.py:188` uses a bare `except Exception as e:`. This is a poor practice as it catches *all* exceptions (including `SystemExit` or `KeyboardInterrupt`) and can mask underlying bugs. The logging is a `warning`, which might not be severe enough for a failing component.
    *   **Database Management:** The application relies on `db.create_all()` at startup (`app.py:245`) if an environment variable is set. This is not a substitute for a proper migration tool like Alembic (which is installed via `flask_migrate`). Relying on `create_all` can lead to schema drift and is not suitable for production environments where schema changes must be managed carefully.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

The most significant gap is that **the feature wasn't built.**

Assuming it were built according to the spec, here are the world-class gaps:

1.  **Trigger Mechanism is Brittle:** A 5-minute cron job is a simple but fragile way to handle price triggers. A world-class system would use a dedicated, high-throughput price-streaming service (e.g., a WebSocket feed from a major exchange or aggregator like Kaiko). The check wouldn't be "every 5 minutes" but "every time the price ticks." This ensures immediate firing on a milestone cross, which is crucial for market-sensitive events.

2.  **Execution is Not Fault-Tolerant:** The spec implies `fire_milestone` is a single, synchronous function. Video generation (LAW 3, item 1) is a long-running, resource-intensive, and failure-prone process. Tying it directly to the trigger means a video pipeline failure could prevent the other, faster actions (Nostr post, newsletter) from happening. A Bloomberg-level system would use a robust job queue (e.g., RabbitMQ, Redis Queue). The price trigger would publish a single "MilestoneHit" event. Separate, independent worker processes would subscribe to this event to generate the video, send the newsletter, etc. This decouples the components, allows for retries on failure, and ensures the system is resilient.

3.  **No Manual Override or "Circuit Breaker":** The system is fully automated. What happens if a flash crash/spike incorrectly triggers a milestone due to a faulty price feed? There is no mention of a human-in-the-loop confirmation step, a kill switch to halt campaigns, or a dashboard to monitor the status of the launch-gate checklist. Professional marketing and trading systems always have manual overrides for automated strategies.

4.  **Process Automation is Immature:** The use of `tmux` and shell scripts (`launch_all_features.sh`) for building and auditing features is a sign of a development process that is not yet mature. A world-class team would use a dedicated CI/CD platform (GitHub Actions, GitLab CI, etc.) to automate these workflows. This provides better logging, artifact management, security scanning, parallel execution, and a clear audit trail of builds and deployments.

The multi-LLM audit concept itself is world-class and innovative. The implementation, however, is not.

### SECTION 7: SCORES (0-100)

*   **Backend logic:** 0/100 (The feature's backend is entirely missing.)
*   **Frontend/UI:** 0/100 (The feature's frontend is entirely missing.)
*   **Error handling:** 40/100 (Based on provided unrelated code, error states are not communicated to the user on the frontend, and backend error handling is overly broad.)
*   **Security:** 50/100 (Fallback secrets, a potential stored XSS vector, and extremely dangerous shell script execution flags are significant issues.)
*   **Performance:** N/A (Cannot be assessed without the implementation.)
*   **Law compliance:** 0/100 (Every law is violated by omission.)
*   **World-class gap:** 10/100 (The concept is sound, but the specified architecture is brittle and the development process is immature. The core deliverable is missing.)
*   **OVERALL:** **5/100**

### SECTION 8: PRIORITY ACTION PLAN

| Priority    | Change                                                                      | File:Line                                | Reason                                                                                                 |
|-------------|-----------------------------------------------------------------------------|------------------------------------------|--------------------------------------------------------------------------------------------------------|
| **P0 CRITICAL** | **Implement the entire f6-marketing-os feature.**                           | (all missing files)                      | The core feature described in the GOSPEL was not implemented or submitted. The current code does nothing.      |
| **P0 CRITICAL** | Remove `--dangerously-skip-permissions` from Claude CLI calls.              | `launch_all_features.sh:81`              | This flag disables critical security sandboxing and exposes the entire system to unacceptable risk.       |
| **P0 CRITICAL** | Application must crash on startup if `SESSION_SECRET` is not set.           | `app.py:46`                              | Using a hardcoded fallback secret key in production is a critical vulnerability that compromises all sessions. |
| **P1 HIGH**     | Properly sanitize all database-driven content used in the `inject_ads` filter. | `app.py:178`                             | The current implementation is vulnerable to stored XSS if ad content can be manipulated.                   |
| **P1 HIGH**     | Implement user-visible error states for all failed API calls on the frontend. | `media_reforge/static/js/media_unified.js` | The UI currently fails silently, leaving users with a perpetually loading interface and no feedback.       |
| **P2 MEDIUM**   | Refactor the milestone trigger logic to use a job queue (e.g., RQ, Celery). | (missing `milestone_service.py`)         | Decouples long-running tasks (video) from the trigger, improving reliability and fault tolerance.       |
| **P2 MEDIUM**   | Refactor monolithic `media_unified.js` into smaller, manageable modules.    | `media_reforge/static/js/media_unified.js` | The current 1200-line file is difficult to maintain and debug.                                         |
| **P3 LOW**      | Move hardcoded configurations out of JS and into a backend API endpoint.    | `media_reforge/static/js/media_unified.js:10` | Allows for configuration changes without requiring a full frontend deployment.                         |

### SECTION 9: THE ONE THING

The submitted code contains detailed specifications and development process scripts but **entirely omits the feature's actual implementation**, making it completely non-functional and non-compliant with all governing laws.

### SECTION 10: FINAL VERDICT

This code is **categorically not ready for production.** It is not even ready for a proper code review, as the central feature is missing. The developer has submitted documentation and unrelated changes instead of the required implementation. Before this can proceed, the entire feature—including backend services, database models, API endpoints, and frontend components as specified in the GOSPEL—must be built.