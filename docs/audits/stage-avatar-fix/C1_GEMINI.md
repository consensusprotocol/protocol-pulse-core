# PROTOCOL PULSE — CODE AUDIT REPORT
**Feature:** stage-avatar-fix
**Branch:** main
**Reviewer:** Gemini 2.5 Pro

This forensic code review assesses correctness, security, quality, and production readiness. The findings are detailed below.

---

### SECTION 1: CORRECTNESS

The code largely implements the described features, but contains several logic errors and edge cases that will cause production failures.

-   **Silent API Failures:** In `routes.py`, multiple `try...except Exception: pass` blocks (lines 8912, 8917, 8951) exist within the `/api/stage/transcript` route. If the underlying JSON data files are corrupt, empty, or have schema changes, the exceptions will be caught and ignored. The API will silently return an empty response, making the frontend appear broken with no corresponding error log, rendering debugging nearly impossible.
-   **`ZeroDivisionError` Crash:** The sentiment statistics calculation in `routes.py` (line 8938) will crash the entire route with an unhandled `ZeroDivisionError` if the `entries` list is empty after loading from the data files. This is a likely edge case.
-   **JavaScript Memory Leak:** In `templates/stage.html`, the `handleStageCameraUpload` function (line 1767) creates a blob URL at line 1839. If the subsequent `audio.play()` call is rejected (common on mobile browsers), the `catch` block at line 1858 handles the error but fails to call `URL.revokeObjectURL()`. This will cause a memory leak on every failed photo-question attempt.
-   **Inefficient DB Query:** In `services/stage_broadcast_service.py`, the `check_article_teaser` function uses an `ORDER BY RANDOM() LIMIT 1` query (line 506). On SQLite, this query becomes extremely slow as the table size increases, as it can require a full table scan and sort. This will eventually cause the cron job to slow down or time out.

---

### SECTION 2: LAW COMPLIANCE

The "GOVERNING LAWS" section of the specification is empty.

-   **ALL LAWS:** COMPLIANT

---

### SECTION 3: SECURITY

The code demonstrates good security practices in some areas but has a notable gap in rate limiting.

-   **Rate Limiting Gap:** The `/api/stage/transcript` route in `routes.py` (line 8879) is missing a rate-limiting decorator, unlike all other `/api/stage/*` routes. As this route performs disk I/O, it is vulnerable to resource exhaustion from a simple, high-frequency request attack.
-   **Secrets Management:** **(GOOD)** The `_get_anthropic_key` function in `services/stage_broadcast_service.py` (line 65) correctly loads API keys from environment variables or a `.env` file, avoiding hardcoded secrets.
-   **Cross-Site Scripting (XSS):** **(GOOD)** The frontend JavaScript in `templates/stage.html` correctly uses `element.textContent` (line 984) for plain text and `DOMPurify` (line 991) for sanitized HTML, providing strong protection against XSS vulnerabilities.

---

### SECTION 4: FRONTEND QUALITY

The UI is visually striking and feature-rich, consistent with a premium product. However, the underlying code quality is poor, posing significant maintenance and reliability risks.

-   **Monolithic JavaScript:** The entire frontend logic is contained in a single, 1400-line inline `<script>` block in `templates/stage.html` (lines 968-2346). This is extremely difficult to maintain, debug, and test. The lack of modularity and use of global-like variables will inevitably lead to bugs.
-   **Inconsistent Error Handling:** User-facing error handling is inconsistent. While the `setStatus` function exists, many `catch` blocks for failed `fetch` calls only log to the console (e.g., line 1387), leaving the user with a non-responsive UI and no feedback.
-   **Excessive Inline Styles:** The HTML is littered with inline `style` attributes (e.g., lines 771-776, 782, 791-805). This violates the separation of concerns, makes the code difficult to read, and complicates future styling changes or theming. All styles should be in CSS classes.
-   **Accessibility Issue:** The code explicitly prevents pinch-to-zoom on mobile (lines 2342-2343). This is a standard accessibility feature, and disabling it can be highly frustrating for users. This should be removed unless it fixes a specific, critical rendering bug.

---

### SECTION 5: BACKEND QUALITY

The backend service is more robust than the web routes but suffers from a fragile, file-based architecture and potential concurrency issues.

-   **Brittle Architecture:** The entire broadcast system relies on a single `broadcast_queue.json` file on the filesystem, protected by `fcntl`. This is not a scalable or robust solution for a system with ~1000 concurrent users. A proper message queue (like Redis) or a transactional database table should be used to manage state between the web server and the background service.
-   **Cron Job Concurrency:** The `stage_broadcast_service.py` script is intended to run every 5 minutes but lacks a mechanism to prevent concurrent execution. If a single run takes longer than 5 minutes (e.g., due to a slow LLM API response), another instance will start, leading to race conditions and unpredictable behavior. A PID file or a similar locking mechanism at the script level is required.
-   **Insufficient Logging in Routes:** `routes.py` has almost no logging. The silent `except: pass` blocks are a critical failure; they should log the full exception with a traceback to enable debugging of production issues.
-   **Robust Service Design:** **(GOOD)** The `stage_broadcast_service.py` itself is well-designed to be resilient. Wrapping each data-source check in a `try/except` block (e.g., line 767) prevents the entire job from failing if one source is down. The fallback from a local LLM to a cloud API is an excellent design choice for cost and reliability.

---

### SECTION 6: WORLD-CLASS GAP ANALYSIS

While visually polished, the application's architecture is not on par with leading financial intelligence platforms.

1.  **Shift from Polling to Real-Time:** A top-tier "live" platform would not rely on 30-second polling (`setInterval` at line 2276). With 1000 users, this creates significant unnecessary server load. The system should use **WebSockets** to push data from the server to all connected clients the moment it becomes available, providing a genuinely live experience.
2.  **Adopt a Modern Frontend Framework:** The monolithic, inline JavaScript is a prototype-level implementation. A professional product would use a modern framework (e.g., React, Vue) or, at minimum, structure the code into **ES6 modules**. This would dramatically improve maintainability, testability, and developer velocity.
3.  **Decouple Services with a Message Queue:** The use of a shared JSON file as a queue is the system's biggest architectural flaw. A robust solution would use a dedicated service like **Redis Streams or RabbitMQ**. This decouples the broadcast service from the web server, improves scalability, and provides better tools for introspection and management of the broadcast queue.
4.  **Introduce Structured Logging and Metrics:** For a system this complex (multiple external APIs, LLM calls, background jobs), observability is key. The current logging is basic. A world-class implementation would use **structured logging** (e.g., JSON-formatted logs) and export key metrics (queue depth, API latencies, error rates) to a system like Prometheus for real-time monitoring and alerting.

---

### SECTION 7: SCORES (0-100 each)

-   Backend logic:    **65/100** (Service logic is decent, but routes are flawed. File-based architecture is a major liability.)
-   Frontend/UI:      **70/100** (Looks great, but the underlying JS architecture is fragile and unmaintainable.)
-   Error handling:   **45/100** (Excellent in the cron job, dangerously poor in the API routes and frontend.)
-   Security:         **80/100** (Mostly strong, but the missing rate limit is a notable and easily fixed vulnerability.)
-   Performance:      **60/100** (Polling at scale and inefficient DB queries are significant concerns. Video pre-rendering is a highlight.)
-   Law compliance:   **100/100** (Compliant with the empty spec.)
-   World-class gap:  **40/100** (The core architecture is that of a prototype, not a scalable, professional-grade product.)
-   **OVERALL:          66/100**

---

### SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Fix silent API failures | `routes.py:8912, 8917, 8951` | Silent failures will make production outages impossible to debug. Replace `pass` with `logging.exception(...)` and return a 500 error response.
P0 CRITICAL | Prevent cron job race conditions | `services/stage_broadcast_service.py` | If the job runs long, multiple instances will corrupt the queue. Implement a file-based lock at the start of the script to enforce a singleton pattern.
P0 CRITICAL | Fix API crash on empty data | `routes.py:8938` | An empty transcript file will cause a `ZeroDivisionError`, taking down the API route. Add a check for `if total > 0` before division.
P1 HIGH     | Add rate limiting to transcript API | `routes.py:8879` | An unprotected, I/O-intensive endpoint is a prime vector for a denial-of-service attack. Apply the same `@limiter` decorator as other stage routes.
P1 HIGH     | Replace file-based queue | `services/stage_broadcast_service.py`, `routes.py` | The core architecture is not robust. This should be migrated to a proper message queue (Redis) or a transactional DB table to ensure data integrity and scalability.
P1 HIGH     | Refactor monolithic JavaScript | `templates/stage.html:968-2346` | The current JS is a "ball of mud" that is a liability. It must be broken down into smaller, manageable ES6 modules.
P2 MEDIUM   | Replace `ORDER BY RANDOM()` | `services/stage_broadcast_service.py:506` | This query will become a performance bottleneck. Fetch the N most recent articles and select one randomly in the Python code.
P2 MEDIUM   | Implement WebSockets for real-time data | `templates/stage.html`, `routes.py` | Constant polling is inefficient and doesn't feel truly "live." WebSockets are the correct technology for this use case.
P2 MEDIUM   | Remove all inline styles from HTML | `templates/stage.html` | Co-locating styles in HTML makes maintenance painful. Move all styling to CSS classes in the `<style>` block.
P3 LOW      | Fix minor JS memory leak | `templates/stage.html:1858` | In `handleStageCameraUpload`, call `URL.revokeObjectURL()` in the `play().catch()` block to prevent a leak on mobile devices.

---

### SECTION 9: THE ONE THING

The entire system's reliability rests on a fragile architecture using shared JSON files for state management; this must be re-architected around a proper database and message queue before it can handle production traffic reliably.

---

### SECTION 10: FINAL VERDICT

This feature is a visually impressive and functionally complex prototype, but it is **NOT ready for production**. The backend's reliance on a file-based queue is brittle and unsafe under concurrent load, and critical API routes contain silent error-handling bugs that will cause production outages. The P0 and P1 issues in the action plan, particularly the architectural shift away from flat files and the fixing of silent error handling, must be addressed before this code is merged.