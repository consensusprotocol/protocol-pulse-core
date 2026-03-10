# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: session1-terminal
# Branch: feature/session1-terminal
# Generated: 2026-03-10 04:05 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

**AUDITOR'S NOTE:** This review is based on the provided project specifications, as the code package explicitly states: `(No code files found — run after Claude Code session completes)`. A forensic code review is impossible without code. Therefore, this report serves as a **pre-emptive audit and checklist** of critical considerations that the development team must address. The scores reflect the current state of the provided package, which is unauditable.

---

### SECTION 1: CORRECTNESS
**Status: UNVERIFIABLE**

Without any code, it is impossible to verify correctness. However, based on the technology stack and feature description, the following areas will be critical points of failure and must be rigorously tested:

1.  **State Management:** For a "terminal" feature, session state is paramount. If a user's session involves multiple steps (e.g., text input -> TTS -> avatar generation -> lip-sync), the atomicity of this workflow is crucial. A failure at the lip-sync stage must not result in orphaned TTS audio files or charges from HeyGen for an unused avatar. The system must be able to gracefully handle and roll back failed multi-step operations.
2.  **Concurrency:** With an expected peak of ~1000 concurrent users, any shared resources or stateful operations are at high risk for race conditions. For example, if temporary files are generated for lip-syncing (e.g., audio and video clips), ensure they use universally unique identifiers (UUIDs) to prevent one user's process from overwriting another's.
3.  **Edge Cases:** The following edge cases must be handled without crashing or producing unexpected behavior:
    *   **Empty Input:** User submits an empty string to the terminal.
    *   **Extremely Long Input:** User submits a very large block of text. This could lead to high costs at ElevenLabs and long processing times. Input should be validated and likely truncated.
    *   **API Failures:** Any of the external services (ElevenLabs, HeyGen, Wav2Lip) could time out, return an error, or be temporarily unavailable. The user flow must not hang indefinitely.
    *   **Database Contention:** With 1000 concurrent users, writes to any frequently accessed table could cause locking. Ensure transactions are short-lived and database indexing is comprehensive.

### SECTION 2: LAW COMPLIANCE
**Status: UNVERIFIABLE**

The "GOVERNING LAWS" section of the specification is empty. This is a critical oversight.

*   **VIOLATION:** The specification is incomplete. Development cannot be compliant with laws that have not been defined. Depending on the nature of the user data being processed (e.g., voice from text, user-provided text that might contain PII), laws such as GDPR, CCPA, or others may apply. This must be clarified before any code is written that handles user data.

### SECTION 3: SECURITY
**Status: UNVERIFIABLE**

A security audit requires source code. However, the specified tech stack (Python/Flask/SQLAlchemy) has common vulnerability patterns that must be avoided.

1.  **SQL Injection:** While SQLAlchemy ORM provides strong protection, developers must not use string formatting to build queries (e.g., `filter("username = '%s'" % user_input)`). All user-provided input must be passed as parameters to methods like `filter_by()` or `filter()`.
2.  **Authentication Bypasses:** All routes that handle session data, trigger paid API calls, or access user-specific information must be protected by a robust authentication and authorization decorator (e.g., `@login_required`).
3.  **Rate Limiting Gaps:** This is a major financial risk. The external APIs (ElevenLabs, HeyGen) are expensive. A single user in a loop could exhaust the monthly budget in minutes. Strict rate limiting must be applied on a per-user basis to every endpoint that triggers these external calls.
4.  **Secrets in Code:** API keys for ElevenLabs and HeyGen must not be hardcoded. They must be loaded from environment variables or a dedicated secrets management service (like HashiCorp Vault or AWS Secrets Manager).
5.  **Unvalidated User Input:** Any text input from the user must be sanitized before it is passed to external services or stored in the database to prevent cross-site scripting (XSS) if that data is ever displayed back to a user.

### SECTION 4: FRONTEND QUALITY
**Status: UNVERIFIABLE**

The frontend cannot be reviewed. The following are critical for meeting the "world-class" standard:

1.  **Asynchronous Operation States:** Every action that triggers a backend process (especially the multi-step AI pipeline) *must* have clear and distinct UI states for:
    *   **Loading:** An immediate visual confirmation that the request was received (e.g., a subtle loading spinner, a progress indicator for the multi-step process).
    *   **Error:** A clear, user-friendly error message if any part of the chain fails (e.g., "We couldn't generate the avatar. Please try again."). This must include a way to retry the action.
    *   **Empty:** If the terminal session is new, what does the initial state look like? It should be inviting and intuitive, not a blank white box.
2.  **Animation Compliance:** The "CSS/SVG only" constraint is strict. Developers must ensure all animations are performant and do not cause layout thrashing, especially on mobile devices.
3.  **Mobile Viewport:** A "terminal" interface can be difficult to implement on a small screen. The layout must be fully responsive and usable on a standard mobile viewport without horizontal scrolling or overlapping elements.
4.  **Aesthetics:** For a premium product, the UI must feel polished and professional. Font choices, spacing, color palette, and the smoothness of animations are non-negotiable. It must look like Bloomberg, not a hobby project.

### SECTION 5: BACKEND QUALITY
**Status: UNVERIFIABLE**

Based on the specifications, the backend requires high reliability.

1.  **Database Transactions:** Every database write operation (create, update, delete) must be wrapped in a `try/except` block. Upon any exception, a `db.session.rollback()` must be called to prevent partial or corrupt data from being committed to the database.
2.  **External API Calls:** All calls to external services must be implemented with:
    *   **Timeouts:** A reasonable timeout (e.g., 10-15 seconds) must be set to prevent a slow external API from holding a request handler hostage.
    *   **Retries:** Implement an exponential backoff retry mechanism (e.g., using the `tenacity` library) for transient network errors or 5xx-level API responses.
    *   **Graceful Degradation:** If an API call fails after retries, the system must degrade gracefully. For instance, if HeyGen fails, can the system fall back to a static image or just TTS audio instead of crashing the entire user flow?
3.  **Logging:** Error logging must be comprehensive. A log entry for a failed request should include a unique request/trace ID, the user ID, the endpoint being hit, the function where the error occurred, and the full exception traceback. This is non-negotiable for debugging production issues with 1000 concurrent users.
4.  **Scalability:** The choice of Wav2Lip GPU lip-sync implies a potential bottleneck. Is there a job queue (e.g., Celery with Redis/RabbitMQ) to manage these GPU-intensive tasks? Processing these synchronously within a Flask request handler will not scale to 1000 concurrent users and will lead to request timeouts.

### SECTION 6: WORLD-CLASS GAP ANALYSIS
The current specification describes a feature, but a world-class *terminal* implies much more.

1.  **Keyboard-First Interface:** A professional terminal is operated almost entirely by keyboard. The feature should include extensive keyboard shortcuts for all common actions, command history (up/down arrows), and perhaps a command palette (Ctrl/Cmd+K) for discovering functionality.
2.  **Real-Time Data Streams:** The current spec implies a request-response model. A premium terminal would use WebSockets or Server-Sent Events (SSE) to push real-time data to the client, making the experience feel live and responsive, akin to a real trading terminal.
3.  **Customization & Personalization:** Professionals expect to tailor their tools. Allowing users to customize the terminal's appearance (themes, colors, font sizes), save command aliases, or create simple scripts/macros would be a significant differentiator.
4.  **Composability:** Can the output of one command be piped into another? For a "terminal" this is a core expectation. A user might want to get market data, feed it into an analysis command, and then use the result to generate a spoken summary via the AI pipeline. This transforms it from a novelty into a powerful tool.
5.  **Context-Awareness:** The terminal should maintain context. If a user is analyzing BTC, subsequent commands should default to that context unless specified otherwise. This reduces repetitive typing and makes the workflow smoother.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    0/100
- Frontend/UI:      0/100
- Error handling:   0/100
- Security:         0/100
- Performance:      0/100
- Law compliance:   0/100
- World-class gap:  20/100 (The concept has potential, but the spec is missing key professional features.)
- **OVERALL:          3/100**

*(Scores are based on the provided package. An unauditable package with an incomplete specification cannot be rated higher.)*

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact.

P0 CRITICAL | **Provide full source code for the `feature/session1-terminal` branch.** | `N/A` | An audit is impossible without code. This is a complete blocker for the quality gate.
P0 CRITICAL | **Define and document the "Governing Laws" for compliance.** | `SPEC.md` | Development cannot proceed without knowing the legal constraints (e.g., GDPR, CCPA) for handling user data and generated content.
P1 HIGH     | **Design and document the asynchronous task queue for GPU jobs.** | `ARCHITECTURE.md` | Synchronous GPU processing in web requests will not scale and will cause constant timeouts in production.
P1 HIGH     | **Implement per-user rate limiting on all external API endpoints.** | `(TBD)` | To prevent catastrophic budget overruns and denial-of-service from a single malicious or buggy client.
P1 HIGH     | **Ensure all DB writes are atomic with `try/except/rollback` blocks.** | `(TBD)` | To guarantee data integrity under load and during partial system failures.
P2 MEDIUM   | **Implement a robust keyboard-first navigation and command system.** | `(TBD)` | This is a core expectation for a "terminal" product and is essential for a professional user experience.
P3 LOW      | **Scope out a plan for user customization (themes, aliases).** | `(TBD)` | Enhances user retention and elevates the product from a tool to a personalized workspace.

### SECTION 9: THE ONE THING
Before writing another line, architect a robust job queue system for all external AI/GPU tasks, as this is the single greatest point of failure for both performance and user experience at scale.

### SECTION 10: FINAL VERDICT
This feature is **not ready for production**. It is not even ready for a meaningful review. The provided package lacks the fundamental component—source code—and the specification is missing critical legal and architectural details. The team must provide the code and address the architectural concerns, particularly the handling of long-running, expensive API calls, before this can be considered for a merge.