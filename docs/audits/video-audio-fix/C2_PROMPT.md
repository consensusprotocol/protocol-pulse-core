# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: video-audio-fix
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### SECTION 1: CORRECTNESS
I’ve reviewed the provided codebase for the `video-audio-fix` feature, focusing on the main user flow related to video and audio processing as described in the governing laws and pipeline documentation. The primary intent of this feature appears to be addressing audio-visual synchronization, loudness normalization, and other rendering issues in a video production pipeline. Below is a step-by-step analysis of correctness issues:

- **Main User Flow (Video Pipeline Rendering)**:
  1. **Input Processing**: The codebase does not include explicit files for video rendering logic (e.g., `smart_render_loop.py` or specific rendering scripts), but references in `cc_watchdog.py` and `PIPELINE_LESSONS.md` suggest a rendering loop (`smart_loop`) is central to the feature. Without the core rendering code, I cannot verify if input processing (e.g., raw clip handling for AV sync) is correct.
  2. **AV Sync Diagnosis**: The governing law mandates checking raw clips before touching the assembler, but there’s no evidence in the provided files (e.g., `PIPELINE_LAWS.md` or `PIPELINE_LESSONS.md`) that this step is implemented. `PIPELINE_LESSONS.md` repeatedly flags issues like freeze frames and TTS failures, indicating persistent AV sync problems (e.g., Iteration 1, Line 9: "12 multi-second freeze frames").
  3. **Audio Normalization**: The target of -14 LUFS and -1 dBTP ceiling is defined in `PIPELINE_LAWS.md` (Lines 22-23), but `PIPELINE_LESSONS.md` shows consistent failures (e.g., Line 10: "true peak at 0.4 dBTP"). There’s no code to verify if normalization logic is applied correctly.
  4. **Output and Forensics**: The law requires running `ffprobe`, `blackdetect`, `silencedetect`, and `ebur128` post-render, but no code or logs in the provided files confirm this is implemented. `PIPELINE_LESSONS.md` mentions silent gaps and clipping without forensic output (e.g., Line 114: "Multiple long silence gaps").

- **Logic Errors**:
  - In `cc_watchdog.py` (Line 121), the restart command for Python sessions logs output to a file, but there’s no error handling if the log directory doesn’t exist or is unwritable. This could silently fail.
  - In `app.py` (Line 258), `db.create_all()` is called without checking if the database connection is valid, risking silent failures if `DATABASE_URL` is misconfigured.

- **Race Conditions**:
  - `cc_watchdog.py` (Lines 184-222) monitors and restarts sessions, but multiple watchdog instances could conflict when restarting the same session (e.g., `smart_loop`). There’s no locking mechanism to prevent concurrent restarts.
  - In `app.py` (Lines 127-128), CSRF token generation in `inject_csrf()` could face race conditions under high concurrency if session storage isn’t thread-safe.

- **N+1 Query Problems**:
  - In `core/blueprints/affiliates.py` (Lines 176-180), the admin dashboard executes multiple raw SQL queries without batching, potentially leading to N+1 issues when fetching related data for each partner. This could scale poorly with more partners or clicks.

- **Edge Cases**:
  - **Empty DB**: In `core/blueprints/briefings.py` (Lines 65-67), querying `MarketBriefing` assumes rows exist, with no handling for empty results beyond an empty list. UI rendering (Line 102) doesn’t account for a fully empty state across DB and filesystem.
  - **API Timeout**: No evidence of timeout handling for external services (e.g., ElevenLabs TTS mentioned in `PIPELINE_LAWS.md`, Line 30) in any file, risking hanging renders as seen in `PIPELINE_LESSONS.md` (Line 107: "TTS failure").
  - **Bad Input**: In `app.py` (Lines 417-438), asset serving routes (`/a/<path:fn>` and `/v3/<path:fn>`) don’t sanitize `fn`, potentially allowing path traversal if input isn’t validated elsewhere.

### SECTION 2: LAW COMPLIANCE
Reviewing compliance with the governing laws from `PIPELINE_LAWS.md` as specified:

- **Law 1: Always run auto-forensic after render: ffprobe, blackdetect, silencedetect, ebur128**
  - **VIOLATION**: No code or log evidence in any file (e.g., `PIPELINE_LESSONS.md` or `cc_watchdog.py`) shows these forensic tools being executed post-render. `PIPELINE_LESSONS.md` flags issues like silent gaps (Line 114) without forensic data, suggesting non-compliance.

- **Law 2: Never skip regression_test.sh — zero FAILs before commit**
  - **PARTIAL**: `GOSPEL.md` (Line 49) and `BUILD_COMPLETE.md` (Line 54) mention regression tests with zero FAILs, but `MERGE_NOTES.md` (Line 35) excludes `feature/video-audio-fix` from merging, implying tests may not have been run or passed for this branch. No direct evidence of test execution in logs.

- **Law 3: AV sync diagnosis first: check raw clips before touching assembler**
  - **VIOLATION**: No code or documentation in provided files (e.g., `PIPELINE_LAWS.md` or `PIPELINE_LESSONS.md`) indicates raw clip checks before assembler processing. Persistent freeze frame issues (e.g., `PIPELINE_LESSONS.md`, Line 109: "15 freeze frames") suggest this step is missing.

- *

## GEMINI — CYCLE 1 OUTPUT
Here is a forensic code review of the `feature/video-audio-fix` branch.

### OVERALL ASSESSMENT

This audit package is deeply flawed. The feature is named `video-audio-fix`, yet **not a single line of video or audio processing code has been provided for review**. The included files primarily relate to a large-scale refactoring of the Flask application into a blueprint architecture, along with documentation for other features.

The most critical context comes from `PIPELINE_LESSONS.md`, which details repeated, catastrophic failures in the video pipeline this branch is meant to fix: TTS failures, audio clipping, and video freeze frames. The code provided does nothing to address these issues.

Furthermore, the codebase exhibits a critical structural flaw: two conflicting application entry points (`app.py` and `core/app.py`). This indicates a messy, incomplete refactoring that will lead to unpredictable behavior, configuration drift, and security vulnerabilities. This audit will focus on the code that *was* provided, but the primary conclusion is that the core purpose of the branch has not been met.

---

### SECTION 1: CORRECTNESS

The code contains significant structural and logical errors that will prevent it from running reliably.

*   **CRITICAL FLAW: Dual Application Entry Points.** There are two application factory files, `app.py` and `core/app.py`. They are similar but have critical differences in configuration, security, and initialization.
    *   `app.py` has safer secret key handling (line 46), better logging configuration (line 28), and more robust database URL parsing (line 63).
    *   `core/app.py` has a hardcoded development secret key (line 39), enables `DEBUG` level logging for production (line 25), and uses a bug-prone method of adding `charset=utf8mb4` to SQLite URLs (line 46), which is explicitly removed in the other `app.py`.
    *   This dual-entrypoint problem will cause chaos. Depending on how the WSGI server is configured (`app:app` vs `core.app:app`), the application will behave differently, load different blueprints, and have different security postures. This is a recipe for production failure.

*   **Logic Error: N+1 Query in Ad Injection.** The `inject_ads` filter in `core/app.py:97` re-queries the database for all active ads on *every single request* that uses the filter. The version in the root `app.py:181` correctly caches this result within the request context (`g` object), but the `core` version does not. This will degrade performance under load.

*   **Logic Error: Fragile Filesystem Parsing.** In `core/blueprints/briefings.py:35`, the code `mp4.stem.split("_")` assumes a strict `briefing_TYPE_TIME.mp4` naming convention. If a file is named `briefing.mp4`, this will cause an `IndexError` when accessing `parts[1]`. The code does not handle this edge case.

*   **Silent Failure: Ad Injection Fails Silently.** The `inject_ads` filter in both `app.py` and `core/app.py` uses a broad `except Exception` block (e.g., `app.py:201`) that logs a warning and returns the original content. While this prevents a crash, it can hide underlying database or logic issues, leading to ads silently disappearing from the site.

*   **Race Condition: Unsafe File Appending.** In `cc_watchdog.py:147`, the function `append_to_lessons` opens `PIPELINE_LESSONS.md` in append mode. While the script is likely single-threaded, if two instances were ever run concurrently, this could lead to interleaved writes and file corruption. A file lock would be safer.

---

### SECTION 2: LAW COMPLIANCE

*   **Law: Always run auto-forensic after render: ffprobe, blackdetect, silencedetect, ebur128**
    *   **STATUS: VIOLATION (based on evidence).**
    *   The provided code does not contain the render pipeline. However, `PIPELINE_LESSONS.md` provides extensive evidence that the rendered output is **failing** the quality checks mandated by this law. For example, `PIPELINE_LESSONS.md:10` reports "The audio mix is clipping (True Peak at 0.4 dBTP)", and line 9 reports "12 multi-second freeze frames". While the *checks* may be running, the pipeline is not producing compliant output.

*   **Law: Never skip regression_test.sh — zero FAILs before commit**
    *   **STATUS: UNVERIFIABLE.**
    *   Cannot be verified from the code provided. The documentation states this is a requirement.

*   **Law: AV sync diagnosis first: check raw clips before touching assembler**
    *   **STATUS: UNVERIFIABLE.**
    *   Cannot be verified from the code provided.

*   **Law: Audio target: -14 LUFS integrated, -1 dBTP ceiling, music at -14 LUFS with sidechain**
    *   **STATUS: VIOLATION.**
    *   `PIPELINE_LESSONS.md` is a catalog of this law being violated.
    *   **Violation:** `PIPELINE_LESSONS.md:10`, `PIPELINE_LESSONS.md:34`, etc. all report a true peak of `+0.4 dBTP`, violating the `-1 dBTP` ceiling.
    *   **Violation:** `PIPELINE_LESSONS.md:73` and `PIPELINE_LESSONS.md:341` report failures of the TTS system, leading to long silen

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — VIDEO-AUDIO-FIX — CYCLE 1
Generated: 2026-03-12 20:56
Models: grok, gemini (+1 failed — GPT-4o quota exceeded)

---

## SCORES

> **Note:** Neither model produced explicit numerical scores. Scores below are synthesized from severity language, violation counts, and confidence signals in each output. GPT-4o failed; scores are interpolated as N/A.

| Subsystem         | Gemini | GPT-4o | Grok | Consensus |
|-------------------|--------|--------|------|-----------|
| Correctness       | 3/10   | N/A    | 4/10 | **3/10**  |
| Law Compliance    | 2/10   | N/A    | 2/10 | **2/10**  |
| Security          | 5/10   | N/A    | 5/10 | **5/10**  |
| Frontend Quality  | N/A    | N/A    | 3/10 | **N/A**   |
| Backend Quality   | 4/10   | N/A    | 4/10 | **4/10**  |
| **Overall**       | **3/10** | N/A  | **4/10** | **3/10** |

*Scoring key: 1=catastrophic, 5=mediocre, 10=world-class. Low scores reflect missing core feature code and persistent pipeline law violations.*

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### 1. Core Feature Code Is Entirely Absent
**What:** The `video-audio-fix` branch contains zero video/audio processing logic. No render pipeline, no AV sync checker, no loudness normalization code. The files provided are Flask blueprint refactoring code unrelated to the feature's stated purpose.
**Files:** All submitted files — `app.py`, `core/app.py`, `core/blueprints/`, `cc_watchdog.py`
**What to change:** Provide and review the actual render pipeline code (`smart_render_loop.py` or equivalent). This branch cannot be considered feature-complete without it. Every other finding below is secondary to this.

### 2. Pipeline Law Violations — Audio Clipping (True Peak)
**What:** Both models independently identified `PIPELINE_LESSONS.md` as documenting repeated violations of the `-1 dBTP` ceiling law. The pipeline consistently renders audio at `+0.4 dBTP`.
**Files:** `PIPELINE_LESSONS.md` lines 10, 34, and throughout; the render pipeline (not provided)
**What to change:** The audio normalization stage must apply a true peak limiter with a ceiling of `-1 dBTP` before final output. This is non-negotiable per `PIPELINE_LAWS.md` Law 4.

### 3. Pipeline Law Violations — Freeze Frames and AV Sync Failures
**What:** Both models flagged `PIPELINE_LESSONS.md` documenting 12–15 multi-second freeze frames per render iteration. Law 3 requires raw clip diagnosis before touching the assembler; neither model found evidence this check exists in any code.
**Files:** `PIPELINE_LESSONS.md` lines 9, 109; render pipeline (not provided)
**What to change:** Implement a pre-assembly raw clip validation step that runs `ffprobe` on each source clip, verifies audio/video stream alignment, and halts assembly if sync drift exceeds threshold (e.g., >100ms).

### 4. Dual Application Entry Points (Critical Structural Flaw)
**What:** Two conflicting application factory files — `app.py` (root) and `core/app.py` — with meaningfully differe

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: .gitignore (33 lines)
```
   1 | *.mp4
   2 | *.wav
   3 | *.pyc
   4 | __pycache__/
   5 | logs/
   6 | night_prompts/
   7 | *.log
   8 | instance/
   9 | test_*
  10 | /tmp/
  11 | .env
  12 | venv/
  13 | data/episodes/
  14 | *.mp3
  15 | uploads/*.png
  16 | uploads/*.jpg
  17 | /tmp/*.png
  18 | /tmp/*.jpg
  19 | attached_assets/*.png
  20 | attached_assets/*.jpg
  21 | # Allow fallback cover images (Law 1)
  22 | !static/images/default-covers/*.jpg
  23 | node_modules/
  24 | *.part
  25 | x_spaces_scraper/cache/
  26 | video_pipeline_v3/remotion/node_modules/
  27 | x_spaces_scraper/cache/
  28 | gfpgan/weights/
  29 | oracle/gfpgan/weights/
  30 | *.pth
  31 | video_pipeline_v3/tts_cache/
  32 | gunicorn.pid
  33 | 
```

### File: AUDIT_PROTOCOL.md (273 lines)
```
   1 | # MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
   2 | # Sequence: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
   3 | # ------------------------------------------------------------
   4 | 
   5 | # PROTOCOL PULSE — POST-BUILD LLM AUDIT PROTOCOL
   6 | # Status: GOSPEL. This runs AFTER every Claude Code feature session.
   7 | # The audit target is ACTUAL PRODUCTION CODE, not specs.
   8 | # Created: 2026-03-09
   9 | # Trigger: After every feature branch produces its first complete build
  10 | 
  11 | ---
  12 | 
  13 | ## THE RULE
  14 | 
  15 | **Build code first. Audit code second. Never audit specs.**
  16 | 
  17 | The sequence is:
  18 | 1. Gospel doc defines what to build (done)
  19 | 2. Claude Code session builds full working frontend + backend (one session per feature)
  20 | 3. THIS PROTOCOL runs on the resulting code
  21 | 4. Gemini + Grok + ChatGPT review the actual code
  22 | 5. Claude synthesizes consensus
  23 | 6. Second Claude Code pass incorporates improvements
  24 | 7. Branch is PR-ready
  25 | 
  26 | This protocol is NOT optional. Every feature gets it before merging to main.
  27 | 
  28 | ---
  29 | 
  30 | ## PHASE 1: GENERATE THE CODE AUDIT PACKAGE
  31 | 
  32 | After a Claude Code session completes, Claude (in this chat) runs:
  33 | 
  34 | ```bash
  35 | # Pull all new/modified files from the feature branch
  36 | cd ~/protocol_pulse
  37 | git diff main..feature/BRANCH_NAME --name-only
  38 | ```
  39 | 
  40 | Then for each file, pull the full content via relay. Assemble into a single
  41 | audit package document with this structure:
  42 | 
  43 | ---
  44 | 
  45 | ### AUDIT PACKAGE TEMPLATE
  46 | 
  47 | ```markdown
  48 | # PROTOCOL PULSE — CODE AUDIT PACKAGE
  49 | # Feature: [Feature Name]
  50 | # Branch: feature/[branch-name]
  51 | # Build date: [date]
  52 | # Auditors: You are [Gemini / Grok / ChatGPT] — other models will also review this
  53 | # Purpose: Pre-merge quality gate. Find everything wrong before this ships.
  54 | 
  55 | ---
  56 | 
  57 | ## WHAT THIS FEATURE DOES
  58 | [2-paragraph description of what was built, what problem it solves,
  59 | and what the user experience looks like end-to-end]
  60 | 
  61 | ## THE LAWS THIS CODE MUST OBEY
  62 | [Paste the full LAWS section from the gospel doc]
  63 | The code MUST comply with every law above. Flag any violation.
  64 | 
  65 | ## TECHNOLOGY CONSTRAINTS
  66 | - Python 3.12, Flask, SQLite (SQLAlchemy ORM)
  67 | - Ubuntu 24.04 on Ultron (2x RTX 4090, 93GB RAM)
  68 | - All CSS animations only — NO Three.js, no WebGL
  69 | - FFmpeg for video, ElevenLabs for TTS, Wav2Lip for lip sync (F1 only)
  70 | - The site serves ~1000 concurrent users at peak
  71 | - Every DB query must have an index on the sort/filter column
  72 | 
  73 | ## THE CODE
  74 | 
  75 | ### File: [filename] ([N] lines)
  76 | [complete file contents with line numbers]
  77 | 
  78 | ### File: [next file]
  79 | [complete contents]
  80 | 
  81 | [...every new/modified file...]
  82 | 
  83 | ## WHAT WE NEED FROM YOU
  84 | 
  85 | You are performing a forensic code review. Be brutally honest.
  86 | Other top AI models are reviewing this same code — we'll compare your outputs.
  87 | The developer who wrote this will not be present. There is no ego to protect.
  88 | Only quality matters.
  89 | 
  90 | ### 1. CORRECTNESS AUDIT
  91 | Does the code do what it claims to do?
  92 | - Walk through the main user flow step by step
  93 | - Find logic errors, off-by-one errors, wrong variable names
  94 | - Find places where the code will silently fail without error
  95 | - Find race conditions (multiple requests hitting same resource)
  96 | - Find N+1 query problems (DB queries inside loops)
  97 | 
  98 | ### 2. LAW COMPLIANCE AUDIT
  99 | Check every LAW from the governing spec above.
 100 | For each law: COMPLIANT / VIOLATION / PARTIALLY COMPLIANT + explanation.
 101 | Be specific — cite line numbers.
 102 | 
 103 | ### 3. SECURITY AUDIT
 104 | - SQL injection vectors (even with ORM — check raw queries)
 105 | - Authentication bypasses
 106 | - Rate limiting gaps (can a single user exhaust API limits?)
 107 | - Secret exposure (are any API keys, tokens, or passwords in the code?)
 108 | - Input validation gaps (user-supplied data that hits DB or shell)
 109 | 
 110 | ### 4. FRONTEND QUALITY AUDIT
 111 | - Does the UI match the spec layout?
 112 | - Are there any hardcoded values that should be dynamic?
 113 | - Will it break on mobile viewport?
 114 | - Are there any JS errors that would prevent the page from functioning?
 115 | - Is the loading/error/empty state handled for every async operation?
 116 | 
 117 | ### 5. BACKEND QUALITY AUDIT
 118 | - Are all DB operations wrapped in try/except with proper rollback?
 119 | - Are all external API calls (ElevenLabs, HeyGen, EDGAR, Bitnodes) 
 120 |   handled with timeout, retry, and graceful degradation?
 121 | - Does the cron job handle failure without crashing the service?
 122 | - Are there memory leaks (large objects created per request, not freed)?
 123 | 
 124 | ### 6. WORLD-CLASS GAP ANALYSIS
 125 | This code needs to be the best Bitcoin intelligence product on the internet.
 126 | What would Bloomberg Terminal, Coinbase, or a top-5 crypto media product do
 127 | differently here? What's missing that would make this genuinely impressive?
 128 | Do not pad this section — only include changes that would materially elevate
 129 | the product. If the code is already excellent in a given area, say so.
 130 | 
 131 | ### 7. SCORING
 132 | Rate each subsystem 0-100:
 133 | - Backend logic: X/100
 134 | - Frontend/UI: X/100  
 135 | - Error handling: X/100
 136 | - Security: X/100
 137 | - Performance: X/100
 138 | - Law compliance: X/100
 139 | - Overall: X/100
 140 | 
 141 | ### 8. PRIORITY ACTION PLAN
 142 | List every fix, improvement, and addition — sorted by impact:
 143 | | Priority | Change | File:Line | Reason | Impact |
 144 | |----------|--------|-----------|--------|--------|
 145 | | P0 CRITICAL | ... | ... | Will break in prod | Fix immediately |
 146 | | P1 HIGH | ... | ... | Degrades quality | Fix before merge |
 147 | | P2 MEDIUM | ... | ... | Enhancement | Fix in second pass |
 148 | | P3 LOW | ... | ... | Polish | Nice to have |
 149 | 
 150 | ### 9. ONE THING
 151 | If you could only tell the developer one thing to make this dramatically better,
 152 | what would it be?
 153 | ```
 154 | 
 155 | ---
 156 | 
 157 | ## PHASE 2: DISTRIBUTE TO 3 LLMs
 158 | 
 159 | PBX pastes the full audit package into:
 160 | 1. **Gemini 2.5 Pro** (Google AI Studio — free) — strongest at architecture
 161 | 2. **Grok** (grok.com) — strongest at API verification + current info
 162 | 3. **ChatGPT o3** (chatgpt.com) — strongest at frontend + UX critique
 163 | 
 164 | Each model gets the IDENTICAL package. Do not modify between models.
 165 | Tell them nothing about what the other models said until Phase 3.
 166 | 
 167 | ---
 168 | 
 169 | ## PHASE 3: CONSENSUS SYNTHESIS (Claude does this)
 170 | 
 171 | PBX pastes all 3 outputs back. Claude produces:
 172 | 
 173 | ```markdown
 174 | # CONSENSUS REPORT — [Feature Name]
 175 | # Models: Gemini 2.5 Pro + Grok + ChatGPT o3
 176 | 
 177 | ## UNANIMOUS FINDINGS (all 3 agree — highest confidence)
 178 | [Items every model flagged — fix these unconditionally]
 179 | 
 180 | ## MAJORITY FINDINGS (2 of 3 agree)
 181 | [Fix these unless there's a strong reason not to]
 182 | 
 183 | ## UNIQUE INSIGHTS (only 1 model caught this)
 184 | [Often the most valuable — evaluate case by case]
 185 | 
 186 | ## SCORE CONSENSUS
 187 | | Subsystem | Gemini | Grok | GPT | Average |
 188 | |-----------|--------|------|-----|---------|
 189 | | ...       |  X/100 | X/100| X/100| X/100 |
 190 | 
 191 | ## CONFLICTS (models disagree)
 192 | [Claude provides tiebreaker with reasoning]
 193 | 
 194 | ## VALIDATED (all models agree this is already excellent — do NOT change)
 195 | [These are strengths to preserve]
 196 | 
 197 | ## FINAL ACTION PLAN (sorted by consensus priority)
 198 | [Only includes items with 2+ model agreement, plus unique high-impact items]
 199 | ```
 200 | 
 201 | ---
 202 | 
 203 | ## PHASE 4: SECOND CLAUDE CODE PASS
 204 | 
 205 | Claude drafts the execution prompt for the second build pass:
 206 | 
 207 | ```
 208 | Read ~/protocol_pulse/docs/gospels/[FEATURE]_GOSPEL.md.
 209 | Read ~/protocol_pulse/docs/audits/[FEATURE]_CONSENSUS.md.
 210 | 
 211 | This is the SECOND PASS for feature [X].
 212 | The first build was reviewed by 3 independent AI models.
 213 | Below is the consensus action plan. Implement every P0 and P1 item.
 214 | For P2 items, use your judgment — only implement if it clearly
 215 | improves the product without adding complexity.
 216 | 
 217 | CONSENSUS ACTION PLAN:
 218 | [paste the prioritized list]
 219 | 
 220 | VALIDATED (do not touch these — all models confirmed they're excellent):
 221 | [paste the validated list]
 222 | 
 223 | After implementing: run regression_test.sh — zero FAILs required.
 224 | git add -A && git commit -m "feat([feature]): post-audit second pass — [N] consensus improvements"
 225 | git push origin feature/[branch]
 226 | ```
 227 | 
 228 | ---
 229 | 
 230 | ## PHASE 5: PR REVIEW + MERGE
 231 | 
 232 | After second pass:
 233 | - Claude reviews the final diff one more time
 234 | - If clean: `git merge feature/[branch] → main`
 235 | - If issues remain: targeted third pass (rare)
 236 | 
 237 | ---
 238 | 
 239 | ## AUDIT TRACKING
 240 | 
 241 | Every completed audit gets stored at:
 242 | `~/protocol_pulse/docs/audits/[FEATURE]_AUDIT_PACKAGE.md` — the package sent to LLMs
 243 | `~/protocol_pulse/docs/audits/[FEATURE]_GEMINI.md` — Gemini's raw response
 244 | `~/protocol_pulse/docs/audits/[FEATURE]_GROK.md` — Grok's raw response  
 245 | `~/protocol_pulse/docs/audits/[FEATURE]_GPT.md` — ChatGPT's raw response
 246 | `~/protocol_pulse/docs/audits/[FEATURE]_CONSENSUS.md` — Claude's synthesis
 247 | 
 248 | This creates a permanent audit trail for every feature.
 249 | 
 250 | ---
 251 | 
 252 | ## ACCELERATED PATH (when you need speed)
 253 | 
 254 | For lower-stakes features (B1 Newsletter, F5 Node Watch):
 255 | - Single LLM audit (Gemini only) instead of 3
 256 | - Skip Phase 4 second pass if score > 85/100 across the board
 257 | - Still store the audit doc
 258 | 
 259 | For high-stakes features (F1 Avatar, V30 Terminal API, V22 Pipeline):
 260 | - Full 3-model audit, mandatory
 261 | - Phase 4 second pass always runs
 262 | - No shortcuts
 263 | 
 264 | ---
 265 | 
 266 | ## THE GOLDEN RULE
 267 | 
 268 | **A feature is not "done" when Claude Code finishes.**
 269 | **A feature is done when 2+ external models have reviewed the code**
 270 | **and the consensus improvements have been implemented.**
 271 | 
 272 | This is what separates a rushed internal tool from a world-class product.
 273 | 
```

### File: BUILD_COMPLETE.md (64 lines)
```
   1 | # BUILD COMPLETE — V22: MULTI-FORMAT VIDEO DISTRIBUTION
   2 | Feature ID: v22-multi-format
   3 | Branch: feature/v22-multi-format
   4 | Completed: 2026-03-09
   5 | Commit: 36901e4 (post-audit second pass — consensus improvements)
   6 | 
   7 | ---
   8 | 
   9 | ## WHAT WAS BUILT
  10 | 
  11 | ### Format Multiplier (video_pipeline_v3/format_multiplier.py — 851 lines)
  12 | - Takes a completed Pulse Check episode and generates platform-specific formats
  13 | - YouTube: 16:9 full-length with chapters
  14 | - X/Twitter: 60s clip with caption overlay
  15 | - Nostr: 90s clip with zap-friendly description
  16 | - Newsletter: thumbnail + transcript excerpt
  17 | - FFmpeg-native: no Remotion, no external render services
  18 | 
  19 | ### Distribution Engine (services/video_engine/distribution_engine.py — 608 lines)
  20 | - YouTube Data API v3 upload (title, description, tags, thumbnail)
  21 | - X/Twitter API v2 media upload + tweet
  22 | - Nostr NIP-94 media event publish
  23 | - Newsletter embed generation
  24 | 
  25 | ### Distribution Manager (services/distribution_manager.py — 431 lines)
  26 | - Orchestrates format_multiplier → distribution_engine pipeline
  27 | - Per-platform success/failure tracking
  28 | - `distribution_state.json` for idempotency (skip already-distributed formats)
  29 | - Retry logic: 3x on transient failures
  30 | 
  31 | ### Routes
  32 | - `GET /admin/distribution` — distribution status dashboard
  33 | - `POST /api/distribution/run` — manual trigger for an episode
  34 | - `GET /api/distribution/status/<episode_id>` — per-episode status
  35 | 
  36 | ---
  37 | 
  38 | ## AUDIT SUMMARY
  39 | 
  40 | ### Audit Grade (Cycle 2 — 1/10 before second pass)
  41 | - Feature was present but distribution pipeline had critical integration bugs
  42 | - Post-audit second pass fixed consensus improvements
  43 | 
  44 | ### Key Findings Fixed
  45 | 1. YouTube API auth: OAuth2 scope corrected (was using wrong scope)
  46 | 2. X media upload: file size check before upload (Twitter 512MB limit)
  47 | 3. Nostr publish: NIP-94 URL hash computed correctly
  48 | 4. `distribution_state.json` race condition: atomic write with temp file + rename
  49 | 5. Missing error propagation from format step to distribution step
  50 | 
  51 | ---
  52 | 
  53 | ## REGRESSION TEST
  54 | - Result: 29 PASS | 0 FAIL | 1 WARN
  55 | 
  56 | ---
  57 | 
  58 | ## PBX ACTIONS REQUIRED
  59 | 1. **YOUTUBE_CLIENT_ID** + **YOUTUBE_CLIENT_SECRET** + OAuth2 refresh token for YouTube upload
  60 | 2. **X_API_KEY** + **X_API_SECRET** + **X_ACCESS_TOKEN** + **X_ACCESS_SECRET** for X/Twitter upload
  61 | 3. **NOSTR_PRIVATE_KEY** (shared with f4-nostr) for Nostr publish
  62 | 4. YouTube: must complete OAuth2 consent flow once to get refresh_token
  63 | 5. Test run: `python3 -c "from services.distribution_manager import run_distribution; run_distribution('TEST_EPISODE_ID', dry_run=True)"`
  64 | 
```

### File: GOSPEL.md (65 lines)
```
   1 | # MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
   2 | # Sequence: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
   3 | # ------------------------------------------------------------
   4 | 
   5 | # PROTOCOL PULSE — GOSPEL: V22 MULTI-FORMAT OUTPUT ENGINE
   6 | # Branch: feature/v22-multi-format | Created: 2026-03-09
   7 | # BLOCKING: Requires video pipeline stable first (clean daily renders)
   8 | ---
   9 | 
  10 | ## WHAT THIS IS
  11 | One pipeline run → six distribution formats simultaneously. This is the
  12 | multiplier that makes the expensive daily pipeline 6x more valuable.
  13 | 
  14 | ## THE LAWS
  15 | ### LAW 1: Only runs AFTER the 12-min episode is fully rendered and QC-passed
  16 | ### LAW 2: Never adds latency to the main episode render — runs in parallel subprocess
  17 | ### LAW 3: Article adapter MUST rewrite for reading (strip TTS language)
  18 | ### LAW 4: Tweet thread max 8 tweets, each under 280 chars, no em dashes
  19 | ### LAW 5: Nostr publish uses PP keypair (NOSTR_PRIVATE_KEY in .env)
  20 | 
  21 | ## SIX OUTPUT FORMATS
  22 | 1. **12-min YouTube** — existing pipeline (no change)
  23 | 2. **3-5 YouTube Shorts** — shorts_cutter.py (enhanced clip selection)
  24 | 3. **Podcast MP3** — strip visual segments, push to Fountain RSS
  25 | 4. **Written article** — script → article rewrite → POST to /api/v2/articles
  26 | 5. **Tweet thread** — 8 tweets, hook + story + link to episode
  27 | 6. **Nostr long-form** — NIP-23 post via relay
  28 | 
  29 | ## ARCHITECTURE
  30 | ```python
  31 | # format_multiplier.py — runs as subprocess after main render
  32 | def run_all_formats(manifest, episode_mp4, script_text):
  33 |     pool = multiprocessing.Pool(processes=4)
  34 |     pool.apply_async(cut_shorts, [manifest, episode_mp4])
  35 |     pool.apply_async(create_podcast, [episode_mp4, script_text])
  36 |     pool.apply_async(publish_article, [script_text, manifest])
  37 |     pool.apply_async(post_tweet_thread, [script_text, manifest])
  38 |     pool.apply_async(post_nostr, [script_text, manifest])
  39 |     pool.close()
  40 |     pool.join()
  41 | ```
  42 | 
  43 | ## VERIFICATION
  44 | - [ ] All 6 formats produce outputs in single pipeline run
  45 | - [ ] Article appears on site within 5 min of render
  46 | - [ ] Tweet thread posts (verify X API key in .env)
  47 | - [ ] Podcast episode in RSS feed
  48 | - [ ] No added latency to main episode
  49 | - [ ] regression_test.sh: zero FAILs
  50 | 
  51 | ## CLAUDE CODE PROMPT
  52 | ```
  53 | Read ~/protocol_pulse/docs/gospels/V22_MULTI_FORMAT_GOSPEL.md.
  54 | Read ~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md.
  55 | Branch: feature/v22-multi-format.
  56 | PREREQUISITE: Only build this if daily pipeline is producing clean renders.
  57 | 1. Create video_pipeline_v3/format_multiplier.py
  58 | 2. Implement all 5 secondary format functions
  59 | 3. Wire into daily_producer.py as post-render step
  60 | 4. Add X API integration (TWITTER_BEARER_TOKEN in .env)
  61 | 5. Test each format individually, then full run
  62 | 6. regression_test.sh: zero FAILs → commit + push feature/v22-multi-format
  63 | ```
  64 | 
  65 | 
```

### File: MERGE_NOTES.md (36 lines)
```
   1 | # SESSION 0 MERGE NOTES — 2026-03-09
   2 | 
   3 | ## Overview
   4 | Merged 15 feature branches into main. All conflicts resolved. No merges skipped.
   5 | 
   6 | ## Merge Order & Conflicts
   7 | 
   8 | | # | Branch | Conflicts | Resolution |
   9 | |---|--------|-----------|------------|
  10 | | 1 | feature/v30-terminal-api | app.py | Kept main's try/except pattern (safer fallback) |
  11 | | 2 | feature/p3-charts | BUILD_COMPLETE.md | Took feature's version |
  12 | | 3 | feature/p3-sentiment-intel | PHASE0_ADDENDUM.md | Took feature's version |
  13 | | 4 | feature/p3-mining-intel | core/routes.py, BUILD_COMPLETE.md, PHASE0_ADDENDUM.md | Kept BOTH route sections (p3-charts + p3-mining) |
  14 | | 5 | feature/p3-media-unified | dual_host_tts.py, tts_engine.py, BUILD_COMPLETE.md, GOSPEL.md, PHASE0_ADDENDUM.md | Took feature's video pipeline improvements (better defaults) |
  15 | | 6 | feature/p3-premium-stripe | core/models.py, BUILD_COMPLETE.md, GOSPEL.md, PHASE0_ADDENDUM.md | Kept BOTH model sections (PriceAlert + ApiSubscriber) |
  16 | | 7 | feature/p3-affiliates | core/routes.py, BUILD_COMPLETE.md, GOSPEL.md, PHASE0_ADDENDUM.md | Kept BOTH route sections |
  17 | | 8 | feature/b1-newsletter | core/models.py, models.py, BUILD_COMPLETE.md | Kept BOTH model sections (adding NewsletterSubscriber/NewsletterSend) |
  18 | | 9 | feature/f1-avatar-oracle | routes.py, models.py, media_reforge/static/js/media_unified.js, BUILD_COMPLETE.md | Kept BOTH sides |
  19 | | 10 | feature/f2-briefing-room | core/routes.py, models.py, BUILD_COMPLETE.md | Kept BOTH sides |
  20 | | 11 | feature/f3-schiff-bot | core/models.py, core/routes.py, BUILD_COMPLETE.md | Kept BOTH sides |
  21 | | 12 | feature/f4-nostr | BUILD_COMPLETE.md only | Took feature's version |
  22 | | 13 | feature/f5-node-watch | core/models.py (2 conflicts), core/routes.py, BUILD_COMPLETE.md | Kept BOTH sides |
  23 | | 14 | feature/f6-marketing-os | models.py, routes.py, BUILD_COMPLETE.md, GOSPEL.md | Kept BOTH sides |
  24 | | 15 | feature/v22-multi-format | BUILD_COMPLETE.md, GOSPEL.md | Took feature's version |
  25 | 
  26 | ## Conflict Resolution Strategy
  27 | - **routes.py / core/routes.py**: Always kept BOTH sides — feature additions appended after HEAD content
  28 | - **models.py / core/models.py**: Always kept BOTH sides — new model classes from feature appended
  29 | - **app.py**: Kept main's version (try/except pattern is safer than hard-fail)
  30 | - **BUILD_COMPLETE.md, GOSPEL.md, PHASE0_ADDENDUM.md**: Always took feature branch version (most recent)
  31 | - **Video pipeline files (dual_host_tts.py, tts_engine.py)**: Took feature branch (better defaults)
  32 | 
  33 | ## NOT Merged (per directive)
  34 | - feature/p3-sponsor-agent
  35 | - feature/video-audio-fix
  36 | 
```

### File: PHASE0_ADDENDUM.md (73 lines)
```
   1 | # PHASE 0 ADDENDUM — p3-affiliates
   2 | # Created: 2026-03-09
   3 | # Source: C0_SYNTHESIS.md + C0_GEMINI.md + C0_GROK.md
   4 | 
   5 | ## TOP PHASE 0 SUGGESTIONS TO IMPLEMENT
   6 | 
   7 | ### 1. Thompson Sampling MAB (Multi-Armed Bandit) — IMPLEMENTING
   8 | **What:** Replace static 50/50 split with adaptive traffic allocation after sufficient data
   9 | **How:**
  10 | - `p3_affiliate_ab_results` table stores alpha/beta params for Thompson Sampling
  11 | - Variant selection: deterministic hash of (IP+date+salt) maps into MAB-weighted bucket
  12 | - After 100 clicks per partner: Thompson Sampling weights update automatically
  13 | - Starts 50/50, converges to winner over time
  14 | - "Declare winner" button freezes allocation permanently
  15 | - `_get_ab_variant(partner, user_hash)` in affiliate_injector.py implements this
  16 | 
  17 | ### 2. Client-Side Behavioral Intent Scoring — IMPLEMENTING (lightweight JS, no TF.js)
  18 | **What:** Track scroll depth + time-on-page to score user intent before showing CTA
  19 | **How:**
  20 | - Pure vanilla JS in article_detail.html
  21 | - Tracks: scroll depth (0-100%), time on page (seconds), mouse movement
  22 | - Generates intent score 0-100: (scroll_depth * 0.6 + min(time_secs/120, 1)*40)
  23 | - CTA only injects via JS reveal when intent_score >= 40 (configurable threshold)
  24 | - No TF.js / no external ML - privacy-safe, pure math
  25 | - Falls back to showing CTA at page load if JS disabled
  26 | 
  27 | ### 3. navigator.sendBeacon for Impressions — IMPLEMENTING
  28 | **What:** Non-blocking async impression tracking that doesn't delay page transitions
  29 | **How:**
  30 | - `window.addEventListener('beforeunload', ...)` fires sendBeacon to /api/affiliates/impression
  31 | - Also fires on CTA visibility (IntersectionObserver)
  32 | - Server endpoint handles beacon asynchronously
  33 | 
  34 | ### 4. Statistical Significance Display — IMPLEMENTING
  35 | **What:** Admin dashboard shows p-value and confidence interval for A/B tests
  36 | **How:**
  37 | - Python: scipy-style z-test for two proportions (manual math, no scipy dep)
  38 | - Formula: z = (p1-p2) / sqrt(pooled*(1-pooled)*(1/n1+1/n2))
  39 | - p-value approximated via error function
  40 | - Shows: "95% confidence: Variant A wins" or "Need more data (N=47/200)"
  41 | 
  42 | ### 5. Content-to-Conversion Intelligence in Admin — IMPLEMENTING
  43 | **What:** Show which articles drive most conversions with per-article revenue estimates
  44 | **How:**
  45 | - Admin dashboard: "Top referrer pages" table with clicks + estimated revenue
  46 | - Meanwhile: $150 average commission per funded policy (conservative)
  47 | - RNS.ID: $300 per referral (stated in gospel)
  48 | - Shows: estimated earnings per article, per day
  49 | 
  50 | ### 6. Sovereignty Score Widget on Landing Pages — IMPLEMENTING
  51 | **What:** Visual trust score showing why Protocol Pulse endorses each partner
  52 | **How:**
  53 | - Static widget with 5 criteria: Privacy, Non-custodial, BTC-native, Regulatory, Transparency
  54 | - Score 0-5 bars, gold fill, visible on both landing pages
  55 | - Reinforces trust with cypherpunk audience
  56 | 
  57 | ### 7. k-Anonymity Constraint on Analytics — IMPLEMENTING
  58 | **What:** Never display analytics for fewer than k=10 distinct user hashes
  59 | **How:**
  60 | - All admin analytics queries check count(distinct user_hash) >= 10 before returning
  61 | - For small counts: show "< 10 users — aggregating for privacy" placeholder
  62 | - Implemented in /api/affiliates/metrics endpoint
  63 | 
  64 | ## NOT IMPLEMENTING (over-engineered for this Flask/SQLite env):
  65 | - WebSocket live dashboard → SSE (simpler, same effect, no Redis needed)
  66 | - Edge computing / Cloudflare Workers → not applicable to this Flask stack
  67 | - Redis for MAB storage → SQLite handles MAB state fine at this scale
  68 | - TensorFlow.js behavioral ML → simple scroll/time math is sufficient
  69 | - Blockchain referral tracking → misaligned with simplicity requirement
  70 | - WebXR experiences → banned by GOSPEL (CSS animations only, no 3D)
  71 | - LangChain agent swarms → overkill, Claude Haiku API call is sufficient
  72 | - Voice-activated CTAs → novelty without conversion value
  73 | 
```

### File: PIPELINE_LAWS.md (74 lines)
```
   1 | # PROTOCOL PULSE — PIPELINE LAWS
   2 | ## Status: ACTIVE (being refined via 10-cycle gauntlet)
   3 | 
   4 | ---
   5 | 
   6 | ## PIXEL ZONES (confirmed spec)
   7 | - Background: full 1920×1080, color #0A0A0F (never pure black #000000)
   8 | - Text zone (narration): x=40-960, y=80-760 (left half only)
   9 | - PiP zone: x=960-1880, y=0-540 (top right)
  10 | - Subtitle band: y=778-885, full width (1920px), dark glass rgba(0,0,0,0.75), 4px red left bar
  11 | - Info rail (gold): bottom, y≈1032-1080, full width, #F8C15C text
  12 | - Title card: full canvas, no thumbnail bleed
  13 | 
  14 | ## COLOR PALETTE (locked)
  15 | - Background: #0A0A0F (VDS dark navy)
  16 | - Accent / border: #FF3333 (red, 2px borders)
  17 | - Gold info text: #F8C15C
  18 | - Primary text: #FFFFFF
  19 | - Subtitle band bg: rgba(0,0,0,0.75) + blur
  20 | 
  21 | ## AUDIO TARGETS (locked)
  22 | - Integrated LUFS: -14 ±2
  23 | - True peak: ≤ -2.0dBTP
  24 | - LRA: 7 LU
  25 | - Single loudnorm: only in concatenate_parts() — no per-segment loudnorm
  26 | - Sample rate: 48000 Hz
  27 | - Bitrate: 192k (audio)
  28 | 
  29 | ## TTS (locked)
  30 | - Host 1 (Eryn): ID kdnRe2koJdOK4Ovxn2DI at 1.12x speed — sharp female setup/bridge host
  31 | - Host 2 (Mark): ID 1SM7GgM6IMuvQlz2BwM3 at 1.10x speed — male contrarian/react host
  32 | - DUAL HOST RESTORED 2026-03-10: both voices MUST render in every episode
  33 | - Speed param: top-level body param, NOT inside voice_settings
  34 | - Fallback chain: ElevenLabs → pyttsx3 → gTTS → silence
  35 | - TTS cache: tts_cache/ SHA256(voice_id:segment_type:text)[:16].m4a
  36 | 
  37 | ## FFMPEG TIMEOUTS (locked)
  38 | - Default run_ffmpeg_filtergraph() timeout: 300s (was 120s)
  39 | - Heavy filtergraphs (make_intro_coldopen, PiP): 300s minimum
  40 | - concatenate_parts(): 600s
  41 | 
  42 | ## TIMING SPEC
  43 | - Title card: 2.0s exactly
  44 | - Cold open: 10-14s
  45 | - Narration segments: 15-35s each
  46 | - Clip segments: natural duration
  47 | - Tweet cards: 8-12s
  48 | - Outro: 10-15s
  49 | - Total: 8-15 minutes
  50 | 
  51 | ## PRODUCTION RULES
  52 | - debug_mode = False in all production renders
  53 | - No debug overlays ("ORACLE NARRATION ACTIVE" etc.) — instant F grade if visible
  54 | - Cold open: NO logos, bars, watermarks — pure dramatic clip
  55 | - Clip segments: full-screen 1920×1080, NO narration overlays bleeding through
  56 | - Continuous BGM: music mixed ONCE in concatenate_parts(), not per-segment
  57 | - AV sync: nuclear PTS in fix_av_sync() + concatenate_parts()
  58 | 
  59 | ## PRESERVED ELEMENTS (never touch)
  60 | - Gold bottom bar text color #F8C15C
  61 | - Red border thickness 2px where intentionally present
  62 | - Watermark: "PROTOCOL PULSE" white, lower-right, opacity 0.5
  63 | - PiP position: top-right, no text overlap
  64 | 
  65 | ---
  66 | 
  67 | ## CYCLE LEARNINGS
  68 | 
  69 | ### PRE-GAUNTLET (cycles 1-3 on feature/video-audio-fix)
  70 | - Fixed: ElevenLabs fallback chain (gTTS added), AV sync, gold rail in make_host_visual, subtitle band in make_host_visual, per-segment loudnorm removed, bg color 0x0A0A0F, ffmpeg timeout raised to 300s
  71 | - Locked: Single loudnorm in concatenate_parts()
  72 | - Open: Subtitle band inconsistency (~50% of frames missing it), LUFS low (-17.7) due to cached silence audio
  73 | 
  74 | 
```

### File: PIPELINE_LESSONS.md (360 lines)
```
   1 | # Pipeline Lessons Learned
   2 | 
   3 | 
   4 | ## Iteration 1 — 2026-03-12 06:33 — Grade F (34/100)
   5 | 
   6 | ### Failures:
   7 | - TTS service for host 'Eryn' is non-functional (HTTP 404, voice_id not found), resulting in silent audio for all her line
   8 | - The TTS fallback system also failed, leading to a complete inability to generate audio for one of two hosts.
   9 | - The final video contains 12 multi-second freeze frames, a catastrophic visual error.
  10 | - The audio mix is clipping (True Peak at 0.4 dBTP), a violation of broadcast audio standards.
  11 | - Multiple long silence gaps are present, destroying the episode's pacing and watchability.
  12 | - Audio clipping: true peak 999dBTP (limit -1.0)
  13 | - Silent gaps: 2 gaps >2s detected
  14 | - Low bitrate: 2.77Mbps (min 3.0)
  15 | 
  16 | ### Fixes applied:
  17 | - CC fix session iter1 applied
  18 | 
  19 | ### Key insight:
  20 | Carry forward: TTS service for host 'Eryn' is non-functional (HTTP 404, voice_id not found), resulting in silent audio for all her line; The TTS fallback system also failed, leading to a complete inability to generate audio for one of two hosts.
  21 | 
  22 | ---
  23 | 
  24 | ## Iteration 2 — 2026-03-12 07:01 — Grade F (57/100)
  25 | 
  26 | ### Failures:
  27 | - CRITICAL FAILURE: True peak at +0.4 dBTP exceeds the 0 dBFS limit, causing audio
  28 | - CRITICAL FAILURE: 12 freeze frames detected. The video is unwatchable.
  29 | - CRITICAL FAILURE: Host Eryn's voice failed to render, replaced by long silences.
  30 | - CRITICAL FAILURE: The 12 freeze frames are severe visual artifacts that make the
  31 | - CRITICAL FAILURE: Catastrophic failure of the TTS system for one host results in
  32 | - TTS system failed for host 'Eryn', replacing all her lines with long silences.
  33 | - 12 freeze frames (>1s) detected, rendering the video unwatchable.
  34 | - Audio is clipping with a true peak of +0.4 dBTP, which is above the 0 dBFS limit.
  35 | 
  36 | ### Fixes applied:
  37 | - CC fix session iter2 applied
  38 | 
  39 | ### Key insight:
  40 | Carry forward: CRITICAL FAILURE: True peak at +0.4 dBTP exceeds the 0 dBFS limit, causing audio; CRITICAL FAILURE: 12 freeze frames detected. The video is unwatchable.
  41 | 
  42 | ---
  43 | 
  44 | ## Iteration 3 — 2026-03-12 07:29 — Grade F (38/100)
  45 | 
  46 | ### Failures:
  47 | - CRITICAL FAILURE: True peak is at 0.4 dBFS according to the render log QC. This
  48 | - CRITICAL FAILURE: 12 freeze frames detected. This is an unacceptably high number
  49 | - CRITICAL FAILURE: The render log shows a complete failure to generate audio for
  50 | - CRITICAL FAILURE: The video is riddled with artifacts, including 12 freeze frame
  51 | - CRITICAL FAILURE: One host's entire audio track is missing and replaced with sil
  52 | - true_peak_check: Audio is clipping at +0.4 dBFS.
  53 | - freeze_check: 12 video freeze frames detected, making the video unwatchable.
  54 | - host_authenticity: Host 'Eryn' has no audio; all lines were replaced with silence due to a TTS API failure.
  55 | 
  56 | ### Fixes applied:
  57 | - CC fix session iter3 applied
  58 | 
  59 | ### Key insight:
  60 | Carry forward: CRITICAL FAILURE: True peak is at 0.4 dBFS according to the render log QC. This; CRITICAL FAILURE: 12 freeze frames detected. This is an unacceptably high number
  61 | 
  62 | ---
  63 | 
  64 | ## Iteration 4 — 2026-03-12 07:58 — Grade F (41/100)
  65 | 
  66 | ### Failures:
  67 | - CRITICAL FAILURE: Loudness analysis returned 'None LUFS'. This indicates a catas
  68 | - CRITICAL FAILURE: True Peak analysis returned 'None dBFS'. This confirms a funda
  69 | - CRITICAL FAILURE: 12 freeze frames were detected. This is an unacceptable number
  70 | - CRITICAL FAILURE: One host is entirely missing. There is no banter or interactio
  71 | - CRITICAL FAILURE: The presence of 12 freeze frames is a severe visual artifactin
  72 | - CRITICAL FAILURE: The audio is fundamentally broken. One host's voice is missing
  73 | - Host 'Eryn' TTS generation failed completely due to a 'voice_not_found' API error, resulting in her lines being replaced
  74 | - 12 video freeze frames (>1s) were detected, rendering the visual experience unacceptable.
  75 | 
  76 | ### Fixes applied:
  77 | - CC fix session iter4 applied
  78 | 
  79 | ### Key insight:
  80 | Carry forward: CRITICAL FAILURE: Loudness analysis returned 'None LUFS'. This indicates a catas; CRITICAL FAILURE: True Peak analysis returned 'None dBFS'. This confirms a funda
  81 | 
  82 | ---
  83 | 
  84 | ## Iteration 5 — 2026-03-12 09:10 — Grade F (48/100)
  85 | 
  86 | ### Failures:
  87 | - CRITICAL FAILURE. Post-render QC log shows a true peak of 0.4 dBTP, which is ove
  88 | - CRITICAL FAILURE. 12 freeze frames detected. This is an unwatchable number of er
  89 | - CRITICAL FAILURE. One of the two hosts is entirely silent. The core format of th
  90 | - CRITICAL FAILURE. The 12 freeze frames are severe visual artifacts that make the
  91 | - CRITICAL FAILURE. Half of the narration is missing and replaced with silence. Th
  92 | - true_peak_check: Audio is clipping at +0.4 dBTP, which is unacceptable.
  93 | - freeze_check: 12 freeze frames render the video unwatchable.
  94 | - audio_quality: Catastrophic TTS failure resulted in one host being completely silent.
  95 | 
  96 | ### Fixes applied:
  97 | - CC fix session iter5 applied
  98 | 
  99 | ### Key insight:
 100 | Carry forward: CRITICAL FAILURE. Post-render QC log shows a true peak of 0.4 dBTP, which is ove; CRITICAL FAILURE. 12 freeze frames detected. This is an unwatchable number of er
 101 | 
 102 | ---
 103 | 
 104 | ## Iteration 6 — 2026-03-12 10:56 — Grade F (34/100)
 105 | 
 106 | ### Failures:
 107 | - Catastrophic TTS failure for host 'Eryn' due to an invalid ElevenLabs voice_id, resulting in all her lines being replace
 108 | - TTS fallback mechanism failed because the 'pyttsx3' module is not installed, indicating a severe system configuration er
 109 | - 15 freeze frames detected, rendering the video visually unwatchable.
 110 | - Audio is clipping, with a true peak of +0.4 dBTP, which is a broadcast-critical error.
 111 | - Multiple long silence gaps (5 reported >2.0s) are present due to the TTS failure, destroying the episode's pacing.
 112 | - Audio clipping: true peak 999dBTP (limit -1.0)
 113 | - Silent gaps: 1 gaps >2s detected
 114 | - Duration out of range: 652s (target 400-550s)
 115 | 
 116 | ### Fixes applied:
 117 | - CC fix session iter6 applied
 118 | 
 119 | ### Key insight:
 120 | Carry forward: Catastrophic TTS failure for host 'Eryn' due to an invalid ElevenLabs voice_id, resulting in all her lines being replace; TTS fallback mechanism failed because the 'pyttsx3' module is not installed, indicating a severe system configuration er
 121 | 
 122 | ---
 123 | 
 124 | ## Iteration 7 — 2026-03-12 12:29 — Grade F (38/100)
 125 | 
 126 | ### Failures:
 127 | - CRITICAL FAILURE: Forensic data shows no LUFS value calculated, indicating a mea
 128 | - CRITICAL FAILURE: The QC log shows a true peak of +0.4 dBTP. Any value over 0 dB
 129 | - CRITICAL FAILURE: 11 freeze frames detected. This is an unacceptable number of v
 130 | - CRITICAL FAILURE: The render logs show a complete failure to generate audio for
 131 | - CRITICAL FAILURE: The video is riddled with artifacts, specifically the 11 freez
 132 | - CRITICAL FAILURE: Half of the narration is missing entirely. This is a total fai
 133 | - TTS Failure: All lines for host 'Eryn' failed to render, resulting in long, unwatchable gaps of silence.
 134 | - Freeze Frames: 11 instances of frozen video were detected, making the viewing experience impossible.
 135 | 
 136 | ### Fixes applied:
 137 | - CC fix session iter7 applied
 138 | 
 139 | ### Key insight:
 140 | Carry forward: CRITICAL FAILURE: Forensic data shows no LUFS value calculated, indicating a mea; CRITICAL FAILURE: The QC log shows a true peak of +0.4 dBTP. Any value over 0 dB
 141 | 
 142 | ---
 143 | 
 144 | ## Iteration 1 — 2026-03-12 17:50 — Grade F (38/100)
 145 | 
 146 | ### Failures:
 147 | - CRITICAL FAILURE: True peak is 0.4 dBTP, which is over 0 dBFS. This constitutes
 148 | - CRITICAL FAILURE: 11 freeze frames detected. The rubric specifies 2+ is a critic
 149 | - CRITICAL FAILURE: Host Eryn has no voice. The two-host dynamic is non-existent,
 150 | - CRITICAL FAILURE: The video is riddled with severe artifacts, primarily the nume
 151 | - CRITICAL FAILURE: The audio is unusable. One host is entirely silent, and the ov
 152 | - TTS Failure: Host 'Eryn' has no voice; all her lines were replaced with silence due to a recurring API 404 error for her
 153 | - Audio Clipping: True peak at +0.4 dBFS is a critical audio failure and will sound distorted.
 154 | - Visual Collapse: 11 freeze frames and a mid-video black segment make the video unwatchable.
 155 | 
 156 | ### Fixes applied:
 157 | - CC fix session iter1 applied and verified
 158 | 
 159 | ### Key insight:
 160 | Carry forward: CRITICAL FAILURE: True peak is 0.4 dBTP, which is over 0 dBFS. This constitutes; CRITICAL FAILURE: 11 freeze frames detected. The rubric specifies 2+ is a critic
 161 | 
 162 | ---
 163 | 
 164 | ### WATCHDOG [2026-03-12 17:55] RENDER-HEARTBEAT - smart_loop
 165 | Progress: [17:50:08] ITERATION 2/8 — 0.1h elapsed | [17:47:50] GRADE: F (38/100)
 166 | 
 167 | ### WATCHDOG [2026-03-12 18:01] RENDER-HEARTBEAT - smart_loop
 168 | Progress: [17:50:08] ITERATION 2/8 — 0.1h elapsed | [17:58:22] GRADE: F (49/100)
 169 | 
 170 | ### WATCHDOG [2026-03-12 18:06] RENDER-HEARTBEAT - smart_loop
 171 | Progress: [17:50:08] ITERATION 2/8 — 0.1h elapsed | [17:58:22] GRADE: F (49/100)
 172 | 
 173 | ### WATCHDOG [2026-03-12 18:11] RENDER-HEARTBEAT - smart_loop
 174 | Progress: [17:50:08] ITERATION 2/8 — 0.1h elapsed | [17:58:22] GRADE: F (49/100)
 175 | 
 176 | ## Iteration 2 — 2026-03-12 18:11 — Grade F (49/100)
 177 | 
 178 | ### Failures:
 179 | - CRITICAL FAILURE: True peak is at +0.4 dBTP according to the render log. Any val
 180 | - CRITICAL FAILURE: 11 freeze frames were detected. This makes the video unwatchab
 181 | - CRITICAL FAILURE: Host Eryn is completely silent due to a TTS API failure. There
 182 | - CRITICAL FAILURE: The presence of 11 freeze frames is a complete failure on this
 183 | - CRITICAL FAILURE: One host is entirely missing. The remaining audio is clipping.
 184 | - Catastrophic TTS failure: Host 'Eryn' has no voice, replaced by long silent gaps throughout the episode. The logs confir
 185 | - Multiple (11) freeze frames detected, rendering the video unwatchable in parts.
 186 | - Audio clipping: True Peak at +0.4 dBFS exceeds the 0 dBFS limit.
 187 | 
 188 | ### Fixes applied:
 189 | - CC fix session iter2 applied and verified
 190 | 
 191 | ### Key insight:
 192 | Carry forward: CRITICAL FAILURE: True peak is at +0.4 dBTP according to the render log. Any val; CRITICAL FAILURE: 11 freeze frames were detected. This makes the video unwatchab
 193 | 
 194 | ---
 195 | 
 196 | ### WATCHDOG [2026-03-12 18:16] RENDER-HEARTBEAT - smart_loop
 197 | Progress: [18:11:41] ITERATION 3/8 — 0.5h elapsed | [17:58:22] GRADE: F (49/100)
 198 | 
 199 | ### WATCHDOG [2026-03-12 18:21] RENDER-HEARTBEAT - smart_loop
 200 | Progress: [18:17:35] ITERATION 1/8 — 0.0h elapsed | no grade yet
 201 | 
 202 | ### WATCHDOG [2026-03-12 18:26] RENDER-HEARTBEAT - smart_loop
 203 | Progress: [18:17:35] ITERATION 1/8 — 0.0h elapsed | [18:23:41] GRADE: F (38/100)
 204 | 
 205 | ### WATCHDOG [2026-03-12 18:31] RENDER-HEARTBEAT - smart_loop
 206 | Progress: [18:17:35] ITERATION 1/8 — 0.0h elapsed | [18:23:41] GRADE: F (38/100)
 207 | 
 208 | ### WATCHDOG [2026-03-12 18:36] RENDER-HEARTBEAT - smart_loop
 209 | Progress: [18:17:35] ITERATION 1/8 — 0.0h elapsed | [18:23:41] GRADE: F (38/100)
 210 | 
 211 | ### WATCHDOG [2026-03-12 18:41] RENDER-HEARTBEAT - smart_loop
 212 | Progress: [18:17:35] ITERATION 1/8 — 0.0h elapsed | [18:23:41] GRADE: F (38/100)
 213 | 
 214 | ### WATCHDOG [2026-03-12 18:46] RENDER-HEARTBEAT - smart_loop
 215 | Progress: [18:17:35] ITERATION 1/8 — 0.0h elapsed | [18:23:41] GRADE: F (38/100)
 216 | 
 217 | ### WATCHDOG [2026-03-12 18:51] RENDER-HEARTBEAT - smart_loop
 218 | Progress: [18:17:35] ITERATION 1/8 — 0.0h elapsed | [18:23:41] GRADE: F (38/100)
 219 | 
 220 | ## Iteration 1 — 2026-03-12 18:54 — Grade F (38/100)
 221 | 
 222 | ### Failures:
 223 | - TTS API Failure: All of host Eryn's lines were replaced with long silence gaps due to a recurring HTTP 404 error for her
 224 | - Multiple Freeze Frames: 11 freeze frames detected, making the video technically unwatchable.
 225 | - Audio Clipping: True peak at +0.4 dBFS exceeds the 0 dBFS limit, resulting in distorted audio.
 226 | - Multiple Silence Gaps: 3+ long silence gaps detected, ruining the episode's pacing and flow.
 227 | - Mid-video Black Frame: A black frame segment was detected mid-episode, a critical visual error.
 228 | - Audio clipping: true peak 999dBTP (limit -1.0)
 229 | - Silent gaps: 3 gaps >2s detected
 230 | - Duration out of range: 603s (target 400-550s)
 231 | 
 232 | ### Fixes applied:
 233 | - CC fix session iter1 applied and verified
 234 | 
 235 | ### Key insight:
 236 | Carry forward: TTS API Failure: All of host Eryn's lines were replaced with long silence gaps due to a recurring HTTP 404 error for her; Multiple Freeze Frames: 11 freeze frames detected, making the video technically unwatchable.
 237 | 
 238 | ---
 239 | 
 240 | ### WATCHDOG [2026-03-12 18:56] RENDER-HEARTBEAT - smart_loop
 241 | Progress: [18:54:00] ITERATION 2/8 — 0.6h elapsed | [18:23:41] GRADE: F (38/100)
 242 | 
 243 | ### WATCHDOG [2026-03-12 19:01] RENDER-HEARTBEAT - smart_loop
 244 | Progress: [18:54:00] ITERATION 2/8 — 0.6h elapsed | [18:23:41] GRADE: F (38/100)
 245 | 
 246 | ### WATCHDOG [2026-03-12 19:06] RENDER-HEARTBEAT - smart_loop
 247 | Progress: [18:54:00] ITERATION 2/8 — 0.6h elapsed | [19:02:10] GRADE: F (41/100)
 248 | 
 249 | ### WATCHDOG [2026-03-12 19:11] RENDER-HEARTBEAT - smart_loop
 250 | Progress: [18:54:00] ITERATION 2/8 — 0.6h elapsed | [19:02:10] GRADE: F (41/100)
 251 | 
 252 | ### WATCHDOG [2026-03-12 19:16] RENDER-HEARTBEAT - smart_loop
 253 | Progress: [18:54:00] ITERATION 2/8 — 0.6h elapsed | [19:02:10] GRADE: F (41/100)
 254 | 
 255 | ### WATCHDOG [2026-03-12 19:21] RENDER-HEARTBEAT - smart_loop
 256 | Progress: [18:54:00] ITERATION 2/8 — 0.6h elapsed | [19:02:10] GRADE: F (41/100)
 257 | 
 258 | ### WATCHDOG [2026-03-12 19:26] RENDER-HEARTBEAT - smart_loop
 259 | Progress: [18:54:00] ITERATION 2/8 — 0.6h elapsed | [19:02:10] GRADE: F (41/100)
 260 | 
 261 | ## Iteration 2 — 2026-03-12 19:30 — Grade F (41/100)
 262 | 
 263 | ### Failures:
 264 | - CRITICAL FAILURE. Render log QC reports a true peak of 0.4 dBTP, which is over t
 265 | - CRITICAL FAILURE. 11 freeze frames detected. This is an unacceptable number of v
 266 | - CRITICAL FAILURE. The TTS service failed to generate audio for host 'Eryn' on al
 267 | - CRITICAL FAILURE. The 11 detected freeze frames are a catastrophic visual artifa
 268 | - CRITICAL FAILURE. Half of the narration is missing, and the remaining audio is c
 269 | - Total TTS failure for host 'Eryn' due to a 'voice_not_found' error, resulting in her lines being replaced by long silenc
 270 | - 11 freeze frames detected, rendering the video visually unwatchable.
 271 | - Audio true peak exceeds 0 dBFS, causing audible clipping.
 272 | 
 273 | ### Fixes applied:
 274 | - CC fix session iter2 applied and verified
 275 | 
 276 | ### Key insight:
 277 | Carry forward: CRITICAL FAILURE. Render log QC reports a true peak of 0.4 dBTP, which is over t; CRITICAL FAILURE. 11 freeze frames detected. This is an unacceptable number of v
 278 | 
 279 | ---
 280 | 
 281 | ### WATCHDOG [2026-03-12 19:31] RENDER-HEARTBEAT - smart_loop
 282 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 283 | 
 284 | ### WATCHDOG [2026-03-12 19:36] RENDER-HEARTBEAT - smart_loop
 285 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 286 | 
 287 | ### WATCHDOG [2026-03-12 19:41] RENDER-HEARTBEAT - smart_loop
 288 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 289 | 
 290 | ### WATCHDOG [2026-03-12 19:46] RENDER-HEARTBEAT - smart_loop
 291 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 292 | 
 293 | ### WATCHDOG [2026-03-12 19:51] RENDER-HEARTBEAT - smart_loop
 294 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 295 | 
 296 | ### WATCHDOG [2026-03-12 19:56] RENDER-HEARTBEAT - smart_loop
 297 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 298 | 
 299 | ### WATCHDOG [2026-03-12 20:01] RENDER-HEARTBEAT - smart_loop
 300 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 301 | 
 302 | ### WATCHDOG [2026-03-12 20:06] RENDER-HEARTBEAT - smart_loop
 303 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 304 | 
 305 | ## Iteration 1 — 2026-03-12 20:09 — Grade F (34/100)
 306 | 
 307 | ### Failures:
 308 | - TTS API for host 'Eryn' failed repeatedly, replacing all her lines with silence and breaking the episode.
 309 | - 11 freeze frames detected, making the video visually unwatchable.
 310 | - Audio true peak is 0.4 dBTP, exceeding the 0 dBFS limit and causing clipping.
 311 | - The render log filename (20260311) does not match the graded file (20260312), indicating a severe pipeline integrity fai
 312 | - The automated Quality Gate reported a 'PASS' with a 94/100 score, directly contradicting its own internal QC 'FAIL' stat
 313 | - Audio clipping: true peak 999dBTP (limit -1.0)
 314 | - Silent gaps: 3 gaps >2s detected
 315 | - Duration out of range: 603s (target 400-550s)
 316 | 
 317 | ### Fixes applied:
 318 | - CC fix session iter1 applied and verified
 319 | 
 320 | ### Key insight:
 321 | Carry forward: TTS API for host 'Eryn' failed repeatedly, replacing all her lines with silence and breaking the episode.; 11 freeze frames detected, making the video visually unwatchable.
 322 | 
 323 | ---
 324 | 
 325 | ### WATCHDOG [2026-03-12 20:11] RENDER-HEARTBEAT - smart_loop
 326 | Progress: [19:30:29] ITERATION 3/8 — 1.2h elapsed | [19:02:10] GRADE: F (41/100)
 327 | 
 328 | ### WATCHDOG [2026-03-12 20:16] RENDER-HEARTBEAT - smart_loop
 329 | Progress: [20:14:50] ITERATION 1/8 — 0.0h elapsed | no grade yet
 330 | 
 331 | ### WATCHDOG [2026-03-12 20:21] RENDER-HEARTBEAT - smart_loop
 332 | Progress: [20:20:54] ITERATION 1/8 — 0.0h elapsed | no grade yet
 333 | 
 334 | ### WATCHDOG [2026-03-12 20:26] RENDER-HEARTBEAT - smart_loop
 335 | Progress: [20:20:54] ITERATION 1/8 — 0.0h elapsed | no grade yet
 336 | 
 337 | ### WATCHDOG [2026-03-12 20:31] RENDER-HEARTBEAT - smart_loop
 338 | Progress: [20:20:54] ITERATION 1/8 — 0.0h elapsed | no grade yet
 339 | 
 340 | ### Run4 Iter1 Grade:F Score:34
 341 | - TTS generation for host 'Eryn' failed completely, resulting in massive silence gaps where her dialogue should be.
 342 | - 11 freeze frames detected, rendering the video unwatchable.
 343 | - Audio true peak is at 0.4 dBTP, causing clipping and distortion.
 344 | - Loudness metadata is missing from the final file, a sign of a corrupt render.
 345 | - Audio clipping: true peak 999dBTP (limit -1.0)
 346 | - Silent gaps: 3 gaps >2s detected
 347 | - Duration out of range: 603s (target 400-550s)
 348 | 
 349 | ### WATCHDOG [2026-03-12 20:36] RENDER-HEARTBEAT - smart_loop
 350 | Progress: [20:20:54] ITERATION 1/8 — 0.0h elapsed | no grade yet
 351 | 
 352 | ### WATCHDOG [2026-03-12 20:41] RENDER-HEARTBEAT - smart_loop
 353 | Progress: [20:20:54] ITERATION 1/8 — 0.0h elapsed | no grade yet
 354 | 
 355 | ### WATCHDOG [2026-03-12 20:46] RENDER-HEARTBEAT - smart_loop
 356 | Progress: [20:20:54] ITERATION 1/8 — 0.0h elapsed | no grade yet
 357 | 
 358 | ### WATCHDOG [2026-03-12 20:51] RENDER-HEARTBEAT - smart_loop
 359 | Progress: [20:20:54] ITERATION 1/8 — 0.0h elapsed | no grade yet
 360 | 
```

### File: STRIPE_SETUP.md (124 lines)
```
   1 | # STRIPE SETUP FOR PBX — Terminal API Commander Tier
   2 | # Created: 2026-03-09
   3 | 
   4 | ---
   5 | 
   6 | ## STEP 1: Create Stripe Account
   7 | - Go to https://dashboard.stripe.com
   8 | - Create account if needed (or log in)
   9 | - Stay in TEST MODE first (toggle in top-left: "Test mode")
  10 | 
  11 | ## STEP 2: Create the Commander Product
  12 | 1. Go to **Products** → **+ Add product**
  13 | 2. Name: `Protocol Pulse Commander API`
  14 | 3. Description: `Terminal API — 1,000 req/hr · SSE Stream · Webhook Delivery`
  15 | 4. Pricing model: **Recurring**
  16 | 5. Amount: **$49.00 USD** per **month**
  17 | 6. Click **Save product**
  18 | 7. On the product page, copy the **Price ID** → starts with `price_...`
  19 |    → This is your `STRIPE_COMMANDER_PRICE_ID`
  20 | 
  21 | ## STEP 3: Get API Keys
  22 | 1. Go to **Developers** → **API keys**
  23 | 2. Copy **Secret key** (starts with `sk_test_...` for test mode)
  24 |    → This is your `STRIPE_SECRET_KEY`
  25 | 3. (Do NOT use the publishable key — only the secret key)
  26 | 
  27 | ## STEP 4: Create Webhook Endpoint
  28 | 1. Go to **Developers** → **Webhooks** → **+ Add endpoint**
  29 | 2. Endpoint URL: `https://protocolpulse.io/webhook/stripe/terminal`
  30 |    (For local testing: use Stripe CLI or ngrok)
  31 | 3. Select events to listen to:
  32 |    - `checkout.session.completed`
  33 |    - `customer.subscription.deleted`
  34 |    - `customer.subscription.updated`
  35 |    - `invoice.payment_failed`
  36 | 4. Click **Add endpoint**
  37 | 5. On the webhook page, click **Reveal** on "Signing secret"
  38 |    → Copy the value starting with `whsec_...`
  39 |    → This is your `STRIPE_WEBHOOK_SECRET`
  40 | 
  41 | ## STEP 5: Add Keys to Ultron .env
  42 | SSH to Ultron and add to `~/protocol_pulse/.env`:
  43 | 
  44 | ```bash
  45 | STRIPE_SECRET_KEY=sk_test_...        # from Step 3
  46 | STRIPE_WEBHOOK_SECRET=whsec_...      # from Step 4
  47 | STRIPE_COMMANDER_PRICE_ID=price_...  # from Step 2
  48 | ```
  49 | 
  50 | ## STEP 6: Restart Flask
  51 | ```bash
  52 | # Find the gunicorn/flask process
  53 | tmux list-sessions
  54 | tmux attach -t flask_main
  55 | 
  56 | # Or restart via systemd if configured:
  57 | sudo systemctl restart protocol-pulse
  58 | ```
  59 | 
  60 | ## STEP 7: Test with Test Card
  61 | 1. Go to https://protocolpulse.io/premium
  62 | 2. Enter your email, click "JOIN THE INTEL FEED →"
  63 | 3. On Stripe checkout page:
  64 |    - Card: `4242 4242 4242 4242`
  65 |    - Expiry: Any future date (e.g., `12/28`)
  66 |    - CVC: Any 3 digits (e.g., `123`)
  67 |    - ZIP: Any 5 digits (e.g., `90210`)
  68 | 4. Click "Subscribe"
  69 | 5. You should be redirected to `/subscribe/terminal/success` with your API key
  70 | 6. Check that welcome email was sent (if RESEND_API_KEY is configured)
  71 | 
  72 | ## STEP 8: Verify API Key Works
  73 | ```bash
  74 | # Replace with your actual key from the success page
  75 | curl https://protocolpulse.io/api/v2/terminal/topics \
  76 |   -H "X-API-Key: pp_cmd_your_key_here"
  77 | ```
  78 | Should return: `{"data": [...], "meta": {"tier": "commander", ...}}`
  79 | 
  80 | ## STEP 9: Go Live (when ready)
  81 | 1. Toggle Stripe dashboard from **Test mode** to **Live mode**
  82 | 2. Repeat Steps 2-4 with live keys (they start with `sk_live_`, `price_live_`, `whsec_live_`)
  83 | 3. Update `.env` on Ultron with live keys
  84 | 4. Restart Flask
  85 | 
  86 | ---
  87 | 
  88 | ## VERIFICATION CHECKLIST
  89 | - [ ] GET /premium → HTTP 200, Terminal API section visible
  90 | - [ ] POST /api/v2/terminal/subscribe → Stripe redirect (with STRIPE keys in .env)
  91 | - [ ] GET /api/v2/terminal/topics with valid api_key → 200 with data
  92 | - [ ] GET /api/v2/terminal/topics with bad key → 401
  93 | - [ ] 21st request with demo key → 429 with Retry-After header
  94 | - [ ] Stripe webhook processes checkout.session.completed → creates api_key in DB
  95 | - [ ] Welcome email sent via Resend on subscription
  96 | - [ ] GET /api/playground → playground renders, demo key works
  97 | - [ ] GET /api/dashboard → unauthenticated state shown
  98 | - [ ] GET /api/dashboard?key=pp_cmd_... → subscriber state shown
  99 | 
 100 | ---
 101 | 
 102 | ## TROUBLESHOOTING
 103 | 
 104 | **"Stripe not configured" error on checkout:**
 105 | → STRIPE_SECRET_KEY not in .env. Add it and restart Flask.
 106 | 
 107 | **Webhook not firing / subscriber not created:**
 108 | → Check webhook endpoint URL is correct.
 109 | → Check STRIPE_WEBHOOK_SECRET matches the whsec_ from Stripe dashboard.
 110 | → Check Flask logs: `tail -f logs/app.log`
 111 | 
 112 | **API key not in success page after checkout:**
 113 | → Webhook may not have fired yet. Wait 30s and go to /api/dashboard.
 114 | → Enter your email in the key lookup to find your key.
 115 | → If still missing, check webhook logs in Stripe dashboard.
 116 | 
 117 | **Demo key not working in playground:**
 118 | → Run: `curl http://localhost:5000/api/v2/terminal/topics -H "X-API-Key: pp_demo_00000000000000000000000000000001"`
 119 | → If 401: demo key not provisioned. Restart Flask to trigger provision_demo_key().
 120 | 
 121 | ---
 122 | 
 123 | *Questions: support@protocolpulse.io*
 124 | 
```

### File: STRIPE_TERMINAL_SETUP.md (68 lines)
```
   1 | # STRIPE + TERMINAL API SETUP — PBX Instructions
   2 | 
   3 | ## 1. Create Stripe Account
   4 | - Go to https://dashboard.stripe.com
   5 | - Create account if needed
   6 | - Start in **test mode** (toggle top-right)
   7 | 
   8 | ## 2. Create Product
   9 | - Go to **Products** → **Add product**
  10 | - Name: `Protocol Pulse Commander`
  11 | - Price: `$49.00 / month` (recurring)
  12 | - Click **Save product**
  13 | - Copy the **Price ID** (starts with `price_...`)
  14 | 
  15 | ## 3. Get API Keys
  16 | - Go to **Developers** → **API keys**
  17 | - Copy the **Secret key** (starts with `sk_test_...` in test mode)
  18 | 
  19 | ## 4. Set Up Webhook
  20 | - Go to **Developers** → **Webhooks** → **Add endpoint**
  21 | - Endpoint URL: `https://protocolpulse.io/webhook/stripe/terminal`
  22 | - Events to listen for:
  23 |   - `checkout.session.completed`
  24 |   - `customer.subscription.deleted`
  25 | - Click **Add endpoint**
  26 | - Copy the **Signing secret** (starts with `whsec_...`)
  27 | 
  28 | ## 5. Add to Ultron .env
  29 | SSH to Ultron and add these to `~/protocol_pulse/.env`:
  30 | ```
  31 | STRIPE_SECRET_KEY=sk_test_...
  32 | STRIPE_WEBHOOK_SECRET=whsec_...
  33 | STRIPE_COMMANDER_PRICE_ID=price_...
  34 | ```
  35 | 
  36 | ## 6. Restart Flask
  37 | ```bash
  38 | tmux send-keys -t flask_main C-c
  39 | tmux send-keys -t flask_main "cd ~/protocol_pulse && python3 app.py" Enter
  40 | ```
  41 | 
  42 | ## 7. Test with Stripe Test Card
  43 | - Card number: `4242 4242 4242 4242`
  44 | - Expiry: any future date (e.g., `12/30`)
  45 | - CVC: any 3 digits (e.g., `123`)
  46 | - ZIP: any 5 digits (e.g., `10001`)
  47 | 
  48 | ## 8. Test Endpoints
  49 | ```bash
  50 | # Status (no auth)
  51 | curl http://localhost:5000/api/v2/terminal/status
  52 | 
  53 | # With demo key
  54 | curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/sentiment
  55 | curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/topics
  56 | curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/entities
  57 | curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/breaking
  58 | curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/network
  59 | ```
  60 | 
  61 | ## 9. Go Live
  62 | When ready for production:
  63 | 1. Toggle Stripe to **live mode**
  64 | 2. Replace `sk_test_` with `sk_live_` key
  65 | 3. Create a new webhook with the production URL
  66 | 4. Update `.env` with live keys
  67 | 5. Restart Flask
  68 | 
```

### File: app.py (440 lines)
```
   1 | import os
   2 | from pathlib import Path
   3 | from dotenv import load_dotenv
   4 | # Load .env from the same directory as this file (core/) so it works from any cwd
   5 | load_dotenv(Path(__file__).resolve().parent / ".env")
   6 | 
   7 | import logging
   8 | import json
   9 | import random
  10 | from flask import Flask, session
  11 | from flask_sqlalchemy import SQLAlchemy
  12 | from flask_migrate import Migrate
  13 | from sqlalchemy.orm import DeclarativeBase
  14 | from flask_login import LoginManager
  15 | from flask_limiter import Limiter
  16 | from flask_limiter.util import get_remote_address
  17 | try:
  18 |     from flask_socketio import SocketIO
  19 | except ImportError:
  20 |     SocketIO = None
  21 | try:
  22 |     from flask_caching import Cache
  23 |     _cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
  24 | except ImportError:
  25 |     _cache = None
  26 | 
  27 | # Configure logging (default info; keep noisy transport libs quiet).
  28 | logging.basicConfig(level=logging.INFO)
  29 | logging.getLogger("urllib3").setLevel(logging.WARNING)
  30 | logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
  31 | logging.getLogger("requests").setLevel(logging.WARNING)
  32 | logging.getLogger("werkzeug").setLevel(logging.INFO)
  33 | 
  34 | class Base(DeclarativeBase):
  35 |     pass
  36 | 
  37 | # 1. Initialize DB WITHOUT app first to prevent circular loops
  38 | db = SQLAlchemy(model_class=Base)
  39 | 
  40 | # 2. Create the app instance — use absolute paths so templates/static are always found
  41 | #    whether run as "app:app" from core/ or "core.app:app" from project root
  42 | _core_dir = Path(__file__).resolve().parent
  43 | app = Flask(__name__, template_folder=str(_core_dir / "templates"), static_folder=str(_core_dir / "static"))
  44 | 
  45 | # Security: SECRET must be set in environment — no silent insecure fallback
  46 | _session_secret = os.environ.get("SESSION_SECRET", "")
  47 | if not _session_secret:
  48 |     logging.critical("SESSION_SECRET not set — using ephemeral key. Set SESSION_SECRET in environment for production.")
  49 |     import secrets as _secrets_mod
  50 |     _session_secret = _secrets_mod.token_hex(32)
  51 | app.secret_key = _session_secret
  52 | 
  53 | # Public network endpoints (local by default, cloudflared-ready when set in .env)
  54 | app.config["PUBLIC_HUB_URL"] = os.environ.get("PUBLIC_HUB_URL", "http://127.0.0.1:5000").rstrip("/")
  55 | app.config["PUBLIC_AI_URL"] = os.environ.get("PUBLIC_AI_URL", "http://127.0.0.1:11434").rstrip("/")
  56 | app.config["PUBLIC_SSH_HOST"] = os.environ.get("PUBLIC_SSH_HOST", "").strip()
  57 | app.config["USE_DOUBLE_PIPE"] = os.environ.get("USE_DOUBLE_PIPE", "false").strip().lower() in {
  58 |     "1", "true", "yes", "on"
  59 | }
  60 | 
  61 | # Configure the database
  62 | database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
  63 | # Replit (and some Heroku-style hosts) emit postgres:// — SQLAlchemy 1.4+ requires postgresql://
  64 | if database_url.startswith("postgres://"):
  65 |     database_url = database_url.replace("postgres://", "postgresql://", 1)
  66 | if database_url.startswith("sqlite:"):
  67 |     # SQLite: remove unsupported charset param added by older code
  68 |     if "charset=utf8mb4" in database_url:
  69 |         database_url = database_url.replace("?charset=utf8mb4", "").replace("&charset=utf8mb4", "")
  70 | 
  71 | app.config["SQLALCHEMY_DATABASE_URI"] = database_url
  72 | app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
  73 |     "pool_recycle": 300,
  74 |     "pool_pre_ping": True,
  75 | }
  76 | 
  77 | # Startup env diagnostics.
  78 | # Required vars: missing → log CRITICAL (feature is broken without these).
  79 | # Recommended vars: missing → log INFO (integration degrades gracefully).
  80 | _required_env = ["SESSION_SECRET", "DATABASE_URL", "RESEND_API_KEY"]
  81 | _recommended_env = [
  82 |     "TWITTER_API_KEY",
  83 |     "TWITTER_API_SECRET",
  84 |     "TWITTER_ACCESS_TOKEN",
  85 |     "TWITTER_ACCESS_TOKEN_SECRET",
  86 | ]
  87 | for _name in _required_env:
  88 |     if not os.environ.get(_name):
  89 |         logging.critical(
  90 |             "REQUIRED env var %s is missing — dependent features will fail.", _name
  91 |         )
  92 | for _name in _recommended_env:
  93 |     if not os.environ.get(_name):
  94 |         logging.info("%s not configured (related integration stays degraded/off).", _name)
  95 | 
  96 | app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 1 day default for send_file
  97 | 
  98 | # 3. Initialize extensions
  99 | db.init_app(app)
 100 | migrate = Migrate(app, db)
 101 | login_manager = LoginManager()
 102 | login_manager.init_app(app)
 103 | login_manager.login_view = "login"
 104 | 
 105 | limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day"])
 106 | limiter.init_app(app)
 107 | 
 108 | if _cache is not None:
 109 |     _cache.init_app(app)
 110 |     cache = _cache
 111 | else:
 112 |     class _NullCache:
 113 |         def init_app(self, app): pass
 114 |         def cached(self, timeout=None, key_prefix=None):
 115 |             def decorator(f): return f
 116 |             return decorator
 117 |     cache = _NullCache()
 118 | 
 119 | if SocketIO is not None:
 120 |     socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
 121 | else:
 122 |     socketio = None
 123 | 
 124 | @app.context_processor
 125 | def inject_csrf():
 126 |     """Inject CSRF token for forms. Generate once per session."""
 127 |     if "csrf_token" not in session:
 128 |         session["csrf_token"] = os.urandom(32).hex()
 129 |     return {
 130 |         "csrf_token": session.get("csrf_token"),
 131 |         "public_hub_url": app.config.get("PUBLIC_HUB_URL"),
 132 |         "public_ai_url": app.config.get("PUBLIC_AI_URL"),
 133 |         "public_ssh_host": app.config.get("PUBLIC_SSH_HOST"),
 134 |         "use_double_pipe": app.config.get("USE_DOUBLE_PIPE", False),
 135 |     }
 136 | 
 137 | 
 138 | @app.after_request
 139 | def add_headers(response):
 140 |     """Add cache, security, and performance headers to every response."""
 141 |     from flask import request
 142 | 
 143 |     # ── Security headers ──
 144 |     response.headers["X-Content-Type-Options"] = "nosniff"
 145 |     response.headers["X-Frame-Options"] = "SAMEORIGIN"
 146 |     response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
 147 |     response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
 148 |     response.headers["X-XSS-Protection"] = "1; mode=block"
 149 | 
 150 |     # ── Cache strategy ──
 151 |     if request.path.startswith("/static/"):
 152 |         # Versioned assets (?v=X) get long cache; images get 1 week; CSS/JS get 1 day
 153 |         if any(request.path.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico')):
 154 |             response.cache_control.max_age = 604800  # 1 week
 155 |             response.cache_control.public = True
 156 |         elif any(request.path.endswith(ext) for ext in ('.css', '.js')):
 157 |             response.cache_control.max_age = 86400  # 1 day
 158 |             response.cache_control.public = True
 159 |         else:
 160 |             response.cache_control.max_age = 86400
 161 |             response.cache_control.public = True
 162 |     elif request.path.startswith("/api/"):
 163 |         # P1-3: API endpoints default to private/no-store — prevents user-specific
 164 |         # data leaking through shared caches. Individual routes may opt into caching.
 165 |         if "Cache-Control" not in response.headers:
 166 |             response.headers["Cache-Control"] = "private, no-store"
 167 |     else:
 168 |         # HTML pages: no-cache but allow revalidation
 169 |         if "Cache-Control" not in response.headers:
 170 |             response.headers["Cache-Control"] = "public, no-cache, must-revalidate"
 171 | 
 172 |     return response
 173 | 
 174 | 
 175 | # 4. Define Template Filters
 176 | @app.template_filter('inject_ads')
 177 | def inject_ads(content):
 178 |     import models
 179 |     from flask import g
 180 |     try:
 181 |         if not hasattr(g, '_active_ads'):
 182 |             g._active_ads = models.Advertisement.query.filter_by(is_active=True).all()
 183 |         active_ads = g._active_ads
 184 |         if not active_ads:
 185 |             return content
 186 |         ad = random.choice(active_ads)
 187 |         from markupsafe import escape as _esc
 188 |         ad_html = f'''
 189 |         <div class="native-ad-unit my-4 p-3 border-start border-danger bg-dark rounded">
 190 |             <small class="text-muted d-block mb-2 text-uppercase" style="letter-spacing: 1px; font-size: 0.7rem;">Protocol Partner</small>
 191 |             <a href="/ads/go/{ad.id}" rel="noopener" class="text-decoration-none">
 192 |                 <img src="{_esc(ad.image_url or '')}" class="img-fluid mb-2 rounded" style="max-height: 150px;" alt="{_esc(ad.name or '')}">
 193 |                 <p class="mb-0 text-white fw-bold">{_esc(ad.name or '')}</p>
 194 |             </a>
 195 |         </div>
 196 |         '''
 197 |         parts = content.split('</p>', 2)
 198 |         if len(parts) > 2:
 199 |             return parts[0] + '</p>' + parts[1] + '</p>' + ad_html + parts[2]
 200 |         return content + ad_html
 201 |     except Exception as e:
 202 |         logging.warning(f"Ad injection failed: {e}")
 203 |         return content
 204 | 
 205 | @app.template_filter('basename')
 206 | def basename_filter(path):
 207 |     """Return the basename of a path for use in templates (e.g. clip filename)."""
 208 |     if not path:
 209 |         return ""
 210 |     return os.path.basename(str(path).strip())
 211 | 
 212 | @app.template_filter('from_json')
 213 | def from_json_filter(value):
 214 |     if not value:
 215 |         return []
 216 |     try:
 217 |         return json.loads(value)
 218 |     except (json.JSONDecodeError, TypeError):
 219 |         return []
 220 | 
 221 | # Distinct header image per article: when stored URL is missing or the old single default, use pool by title
 222 | _OLD_SINGLE_DEFAULT_HEADER = "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200"
 223 | 
 224 | @app.template_filter('article_header_display')
 225 | def article_header_display_filter(article):
 226 |     """Return a distinct header image URL for this article (avoids same image on every card)."""
 227 |     if article is None:
 228 |         return _OLD_SINGLE_DEFAULT_HEADER
 229 |     stored = (getattr(article, "header_image_url", None) or "").strip()
 230 |     if stored and stored != _OLD_SINGLE_DEFAULT_HEADER:
 231 |         return stored
 232 |     return "/static/images/default-header.png"
 233 | 
 234 | # 5. User loader for Flask-Login
 235 | @login_manager.user_loader
 236 | def load_user(user_id):
 237 |     import models
 238 |     try:
 239 |         return models.User.query.get(int(user_id))
 240 |     except (ValueError, TypeError):
 241 |         return None
 242 | 
 243 | # =====================================
 244 | # THE IGNITION ZONE (CRITICAL ORDER)
 245 | # =====================================
 246 | # When we run as python app.py, __name__ is "__main__". Later, "import routes" does
 247 | # "from app import app", which loads this file again as module "app" (a second Flask
 248 | # app). Routes then register on that second app, but we call app.run() on this one → 404.
 249 | # So make "app" resolve to this same module when we are the main script.
 250 | if __name__ == "__main__":
 251 |     import sys
 252 |     sys.modules["app"] = sys.modules["__main__"]
 253 | 
 254 | with app.app_context():
 255 |     # 1. Load the models into memory first
 256 |     import models
 257 |     # Create any missing tables at startup (idempotent — safe to always run).
 258 |     # Set ENABLE_RUNTIME_DB_CREATE_ALL=false to suppress on managed migration envs.
 259 |     if os.environ.get("ENABLE_RUNTIME_DB_CREATE_ALL", "true").strip().lower() not in {"0", "false", "no", "off"}:
 260 |         try:
 261 |             db.create_all()
 262 |         except Exception as _dbe:
 263 |             logging.warning("db.create_all() failed (non-fatal): %s", _dbe)
 264 | 
 265 |     # p3-sentiment-intel: migration-safe column/table additions
 266 |     try:
 267 |         from utils.db_migrate_sentiment import run_migrations
 268 |         run_migrations(db)
 269 |     except Exception as _mige:
 270 |         logging.warning("db_migrate_sentiment failed (non-fatal): %s", _mige)
 271 | 
 272 | def _run_dev_server():
 273 |     port = 5000
 274 |     host = "0.0.0.0"
 275 |     print(f"Starting Protocol Pulse -> http://127.0.0.1:{port}/ (debug routes: http://127.0.0.1:{port}/debug-routes)")
 276 |     # Disable reloader so the process that binds the port is the same one that loaded routes (avoids 404 from reloader child)
 277 |     if socketio is not None:
 278 |         socketio.run(app, host=host, port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
 279 |     else:
 280 |         app.run(host=host, port=port, debug=False, use_reloader=False)
 281 | 
 282 | # Keep routes import near the very bottom so the app object and extensions are fully initialized first.
 283 | import routes
 284 | from routes_api_v2 import api_v2
 285 | try:
 286 |     from routes_api_terminal import terminal_bp, provision_demo_key
 287 |     app.register_blueprint(terminal_bp)
 288 |     with app.app_context():
 289 |         provision_demo_key()
 290 | except Exception as e:
 291 |     logging.critical("Terminal API blueprint failed to load: %s", e)
 292 | try:
 293 |     from routes_commander import commander_bp, commander_pages_bp
 294 |     app.register_blueprint(commander_bp)
 295 |     app.register_blueprint(commander_pages_bp)
 296 |     logging.info("Commander API blueprint registered at /api/v1")
 297 | except Exception as _e:
 298 |     logging.warning("Commander blueprint not loaded: %s", _e)
 299 | try:
 300 |     from routes_newsletter_trigger import newsletter_trigger_bp
 301 |     app.register_blueprint(newsletter_trigger_bp)
 302 | except Exception as e:
 303 |     logging.critical("Newsletter trigger blueprint failed to load: %s", e)
 304 | 
 305 | # B1 Newsletter Engine — hard fail if feature is active
 306 | from routes_newsletter_b1 import newsletter_b1_bp
 307 | app.register_blueprint(newsletter_b1_bp)
 308 | logging.info("B1 Newsletter blueprint registered")
 309 | app.register_blueprint(api_v2)
 310 | from onboarding_routes import onboarding_bp
 311 | app.register_blueprint(onboarding_bp)
 312 | 
 313 | from oracle_routes import oracle_bp
 314 | app.register_blueprint(oracle_bp)
 315 | 
 316 | # SESSION 2: Blueprint Architecture — Newsletter main routes
 317 | try:
 318 |     from core.blueprints.newsletter import newsletter_bp
 319 |     app.register_blueprint(newsletter_bp)
 320 |     logging.info("Newsletter main blueprint registered (/newsletter)")
 321 | except Exception as _e:
 322 |     logging.warning("Newsletter main blueprint not loaded: %s", _e)
 323 | 
 324 | # SESSION 10 — Article Rebuild: new /api/v2/articles endpoint
 325 | try:
 326 |     from routes_articles import articles_api_bp
 327 |     app.register_blueprint(articles_api_bp)
 328 |     logging.info("Articles API blueprint registered (/api/v2/articles)")
 329 | except Exception as _e:
 330 |     logging.warning("Articles API blueprint not loaded: %s", _e)
 331 | 
 332 | # SESSION 8 — Nostr Feed
 333 | try:
 334 |     from routes_nostr import nostr_bp
 335 |     app.register_blueprint(nostr_bp)
 336 |     logging.info("Nostr Feed blueprint registered (/nostr)")
 337 | except Exception as _e:
 338 |     logging.warning("Nostr Feed blueprint not loaded: %s", _e)
 339 | 
 340 | # SESSION 5 — Mining Intel Blueprint
 341 | try:
 342 |     from core.blueprints.mining import mining_bp
 343 |     app.register_blueprint(mining_bp)
 344 |     logging.info("Mining Intel blueprint registered at /mining-intel")
 345 | except Exception as _e:
 346 |     logging.warning("Mining Intel blueprint not loaded: %s", _e)
 347 | 
 348 | # SESSION 6 — Schiff Bot Blueprint
 349 | try:
 350 |     from core.blueprints.schiff import schiff_bp
 351 |     app.register_blueprint(schiff_bp)
 352 |     logging.info("Schiff Bot blueprint registered (/schiff, /api/schiff/*)")
 353 | except Exception as _e:
 354 |     logging.warning("Schiff Bot blueprint not loaded: %s", _e)
 355 | 
 356 | 
 357 | # CURATED MINING — White-glove service landing page
 358 | try:
 359 |     from core.blueprints.curated_mining import curated_mining_bp
 360 |     app.register_blueprint(curated_mining_bp)
 361 |     logging.info("Curated Mining blueprint registered at /curated-mining")
 362 | except Exception as _e:
 363 |     logging.warning("Curated Mining blueprint not loaded: %s", _e)
 364 | # SESSION 7 — Oracle Avatar Blueprint
 365 | try:
 366 |     from core.blueprints.oracle_avatar import oracle_avatar_bp
 367 |     app.register_blueprint(oracle_avatar_bp)
 368 |     logging.info("Oracle Avatar blueprint registered (/oracle-live, /api/oracle/*)")
 369 | except Exception as _e:
 370 |     logging.warning("Oracle Avatar blueprint not loaded: %s", _e)
 371 | 
 372 | try:
 373 |     from services.video_engine.dashboard.app import dashboard_bp
 374 |     app.register_blueprint(dashboard_bp)
 375 |     logging.info("Dashboard blueprint registered at /dashboard/")
 376 | except ImportError as _e:
 377 |     logging.warning("Dashboard blueprint not loaded: %s", _e)
 378 | 
 379 | # SPONSOR AGENT V2 — Outreach pipeline
 380 | try:
 381 |     from core.blueprints.sponsor import sponsor_bp
 382 |     app.register_blueprint(sponsor_bp)
 383 |     logging.info("Sponsor Agent blueprint registered at /sponsor-agent")
 384 | except Exception as _e:
 385 |     logging.warning("Sponsor Agent blueprint not loaded: %s", _e)
 386 | 
 387 | # F4/F7 — Briefings Blueprint (public /briefings page)
 388 | try:
 389 |     from core.blueprints.briefings import briefings_bp
 390 |     app.register_blueprint(briefings_bp)
 391 |     logging.info("Briefings blueprint registered at /briefings")
 392 | except Exception as _e:
 393 |     logging.warning("Briefings blueprint not loaded: %s", _e)
 394 | 
 395 | # Start background APScheduler only when explicitly enabled for this process.
 396 | if os.environ.get("ENABLE_APSCHEDULER", "false").strip().lower() in {"1", "true", "yes", "on"}:
 397 |     try:
 398 |         from services.scheduler import initialize_scheduler
 399 |         _sch = initialize_scheduler()
 400 |         logging.info("Scheduler initialized: %s", _sch)
 401 |     except Exception as _e:
 402 |         logging.warning("Scheduler init skipped: %s", _e)
 403 | 
 404 | # Diagnose after routes import so startup logs reflect the real routing table.
 405 | try:
 406 |     rules = [r.rule for r in app.url_map.iter_rules()]
 407 |     has_root = "/" in rules
 408 |     logging.info("Routes registered: %s ... (/) present: %s", len(rules), has_root)
 409 |     if not has_root:
 410 |         logging.warning("Missing '/' route! Sample rules: %s", rules[:20])
 411 | except Exception as e:
 412 |     logging.warning("Could not list routes: %s", e)
 413 | 
 414 | if __name__ == "__main__":
 415 |     _run_dev_server()
 416 | @app.route('/a/<path:fn>')
 417 | def _serve_asset(fn):
 418 |     from flask import make_response, abort
 419 |     import mimetypes, os as _o
 420 |     p = _o.path.join('/home/ultron/protocol_pulse/static', fn)
 421 |     if not _o.path.exists(p): abort(404)
 422 |     data = open(p,'rb').read()
 423 |     resp = make_response(data)
 424 |     resp.headers['Content-Type'] = mimetypes.guess_type(p)[0] or 'text/plain'
 425 |     resp.headers['Cache-Control'] = 'public, max-age=3600'
 426 |     return resp
 427 | 
 428 | @app.route('/v3/<path:fn>')
 429 | def _serve_v3(fn):
 430 |     from flask import make_response, abort
 431 |     import mimetypes, os as _o
 432 |     p = _o.path.join('/home/ultron/protocol_pulse/static', fn)
 433 |     if not _o.path.exists(p): abort(404)
 434 |     data = open(p,'rb').read()
 435 |     resp = make_response(data)
 436 |     resp.headers['Content-Type'] = mimetypes.guess_type(p)[0] or 'text/plain'
 437 |     resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
 438 |     resp.headers['Pragma'] = 'no-cache'
 439 |     return resp
 440 | 
```

### File: blueprints/curated_mining.py (7 lines)
```
   1 | from flask import Blueprint, render_template
   2 | curated_mining_bp = Blueprint('curated_mining', __name__)
   3 | 
   4 | @curated_mining_bp.route('/curated-mining')
   5 | def curated_mining():
   6 |     return render_template('curated_mining.html')
   7 | 
```

### File: cc_watchdog.py (226 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | cc_watchdog.py — Universal CC Session Watchdog
   4 | Monitors all active CC sessions every 60s.
   5 | Detects stalls, restarts them, logs everything.
   6 | Runs as a persistent daemon in tmux:watchdog
   7 | """
   8 | import subprocess, time, os, json, re
   9 | from datetime import datetime
  10 | 
  11 | BASE = '/home/ultron/protocol_pulse'
  12 | LOG = f'{BASE}/logs/watchdog.log'
  13 | DISCORD_WEBHOOK = None  # add later if wanted
  14 | 
  15 | # Sessions to monitor: name → prompt file (for restart)
  16 | WATCHED = {
  17 |     'smart_loop':       {'type': 'python',  'cmd': 'python3 smart_render_loop.py', 'log': 'video_pipeline_v3/logs/smart_loop_run3.log', 'critical': True},
  18 |     'sovereignty_stack':{'type': 'cc',      'prompt': 'docs/cc_sovereignty_stack.md', 'critical': False},
  19 |     'flask_main':       {'type': 'service', 'cmd': 'bash run_flask.sh',             'critical': True},
  20 |     'video_server':     {'type': 'service', 'cmd': 'python3 video_file_server.py',  'critical': True},
  21 | }
  22 | 
  23 | # Stall detection: if pane output hasn't changed in N seconds, it's stalled
  24 | STALL_TIMEOUT = {
  25 |     'cc':      600,   # 10 min — CC can think for a while, but not 10 min silently
  26 |     'python':  300,   # 5 min  — render loop should be logging regularly
  27 |     'service': 120,   # 2 min  — services should respond
  28 | }
  29 | 
  30 | os.makedirs(f'{BASE}/logs', exist_ok=True)
  31 | pane_snapshots = {}   # session_name → (last_content, last_change_time)
  32 | restart_counts = {}   # session_name → count
  33 | MAX_RESTARTS = 3
  34 | 
  35 | def log(msg):
  36 |     ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  37 |     line = f'[{ts}] {msg}'
  38 |     print(line, flush=True)
  39 |     with open(LOG, 'a') as f:
  40 |         f.write(line + '\n')
  41 | 
  42 | def session_alive(name):
  43 |     return subprocess.run(f'tmux has-session -t {name} 2>/dev/null',
  44 |                          shell=True).returncode == 0
  45 | 
  46 | def get_pane(name):
  47 |     r = subprocess.run(f'tmux capture-pane -t {name} -p 2>/dev/null',
  48 |                       shell=True, capture_output=True, text=True)
  49 |     # Strip blank lines and ANSI codes
  50 |     lines = [re.sub(r'\x1b\[[0-9;]*m', '', l) for l in r.stdout.split('\n') if l.strip()]
  51 |     return '\n'.join(lines[-15:])  # last 15 non-empty lines
  52 | 
  53 | def is_stalled(name, stype):
  54 |     content = get_pane(name)
  55 |     now = time.time()
  56 |     timeout = STALL_TIMEOUT.get(stype, 300)
  57 |     
  58 |     prev_content, prev_time = pane_snapshots.get(name, (None, now))
  59 |     
  60 |     if content != prev_content:
  61 |         pane_snapshots[name] = (content, now)
  62 |         return False  # actively changing
  63 |     
  64 |     elapsed = now - prev_time
  65 |     if elapsed > timeout:
  66 |         return True, elapsed
  67 |     return False
  68 | 
  69 | def detect_cc_stuck(name):
  70 |     """CC-specific stall patterns"""
  71 |     content = get_pane(name)
  72 |     stuck_patterns = [
  73 |         'bypass permissions on',  # sitting at prompt, not working
  74 |         'ctrl+g to edit in Vim',  # waiting for input
  75 |         'Pasted text #1',         # got paste but didn't process it
  76 |     ]
  77 |     # If ONLY these patterns and nothing else in last 5 lines — it's stuck
  78 |     last_lines = content.split('\n')[-5:]
  79 |     last_text = ' '.join(last_lines)
  80 |     has_work = any(x in last_text for x in ['Reading', 'Writing', 'Bash', 'Creating', '✓', '⎽', 'TokenCount'])
  81 |     is_idle = any(p in last_text for p in stuck_patterns)
  82 |     return is_idle and not has_work
  83 | 
  84 | def restart_cc_session(name, config):
  85 |     count = restart_counts.get(name, 0) + 1
  86 |     restart_counts[name] = count
  87 |     if count > MAX_RESTARTS:
  88 |         log(f'WATCHDOG: {name} hit max restarts ({MAX_RESTARTS}) — NOT restarting. Manual intervention needed.')
  89 |         return False
  90 |     
  91 |     log(f'WATCHDOG: Restarting stalled CC session {name} (restart #{count})')
  92 |     subprocess.run(f'tmux kill-session -t {name} 2>/dev/null', shell=True)
  93 |     time.sleep(3)
  94 |     
  95 |     prompt_file = config.get('prompt')
  96 |     if prompt_file and os.path.exists(f'{BASE}/{prompt_file}'):
  97 |         subprocess.run(
  98 |             f'tmux new-session -d -s {name} "cd {BASE} && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions"',
  99 |             shell=True
 100 |         )
 101 |         time.sleep(12)
 102 |         # Send as a proper Claude instruction, not a paste
 103 |         subprocess.run(
 104 |             f'tmux send-keys -t {name} "Execute the build task defined in {prompt_file}. Read that file first using the Read tool, then complete every step." Enter',
 105 |             shell=True
 106 |         )
 107 |         log(f'WATCHDOG: {name} restarted with prompt from {prompt_file}')
 108 |         return True
 109 |     return False
 110 | 
 111 | def restart_python_session(name, config):
 112 |     count = restart_counts.get(name, 0) + 1
 113 |     restart_counts[name] = count
 114 |     if count > MAX_RESTARTS:
 115 |         log(f'WATCHDOG: {name} hit max restarts — NOT restarting.')
 116 |         return False
 117 |     log(f'WATCHDOG: Restarting stalled python session {name} (restart #{count})')
 118 |     subprocess.run(f'tmux kill-session -t {name} 2>/dev/null', shell=True)
 119 |     time.sleep(3)
 120 |     cmd = config['cmd']
 121 |     log_file = config.get('log', f'logs/{name}.log')
 122 |     subprocess.run(
 123 |         f'tmux new-session -d -s {name} "cd {BASE} && {cmd} 2>&1 | tee {log_file}"',
 124 |         shell=True
 125 |     )
 126 |     log(f'WATCHDOG: {name} restarted')
 127 |     return True
 128 | 
 129 | def check_render_progress():
 130 |     """Special check: is the render loop making actual progress?"""
 131 |     log_file = f'{BASE}/video_pipeline_v3/logs/smart_loop_run3.log'
 132 |     if not os.path.exists(log_file):
 133 |         return 'no log yet'
 134 |     lines = open(log_file).readlines()
 135 |     # Find last grade
 136 |     grades = [l.strip() for l in lines if 'GRADE:' in l]
 137 |     iterations = [l.strip() for l in lines if 'ITERATION' in l and '/8' in l]
 138 |     last_grade = grades[-1] if grades else 'no grade yet'
 139 |     current_iter = iterations[-1] if iterations else 'iteration 1 running'
 140 |     return f'{current_iter} | {last_grade}'
 141 | 
 142 | 
 143 | def append_to_lessons(event_type, session, detail):
 144 |     ts = datetime.now().strftime("%Y-%m-%d %H:%M")
 145 |     line = "\n### WATCHDOG [" + ts + "] " + event_type + " - " + session + "\n" + str(detail) + "\n"
 146 |     try:
 147 |         with open(BASE + "/PIPELINE_LESSONS.md", "a") as fh:
 148 |             fh.write(line)
 149 |     except Exception as ex:
 150 |         log("LESSONS write error: " + str(ex))
 151 | 
 152 | 
 153 | def write_status_file():
 154 |     status = {
 155 |         'timestamp': datetime.now().isoformat(),
 156 |         'sessions': {},
 157 |         'render_progress': check_render_progress(),
 158 |     }
 159 |     for name in WATCHED:
 160 |         alive = session_alive(name)
 161 |         status['sessions'][name] = {
 162 |             'alive': alive,
 163 |             'restarts': restart_counts.get(name, 0),
 164 |         }
 165 |     with open(f'{BASE}/logs/watchdog_status.json', 'w') as f:
 166 |         json.dump(status, f, indent=2)
 167 | 
 168 | def main():
 169 |     log('=' * 60)
 170 |     log('CC WATCHDOG STARTED — monitoring all active sessions')
 171 |     log('Sessions: ' + ', '.join(WATCHED.keys()))
 172 |     log('=' * 60)
 173 |     
 174 |     # Initial snapshot
 175 |     for name in WATCHED:
 176 |         if session_alive(name):
 177 |             pane_snapshots[name] = (get_pane(name), time.time())
 178 |     
 179 |     check_interval = 60  # seconds between checks
 180 |     status_interval = 300  # write status file every 5 min
 181 |     last_status = time.time()
 182 |     
 183 |     while True:
 184 |         time.sleep(check_interval)
 185 |         now = time.time()
 186 |         
 187 |         for name, config in WATCHED.items():
 188 |             stype = config['type']
 189 |             
 190 |             if not session_alive(name):
 191 |                 if config.get('critical'):
 192 |                     log(f'WATCHDOG: CRITICAL session {name} is DEAD')
 193 |                     if stype == 'python':
 194 |                         restart_python_session(name, config)
 195 |                     elif stype == 'cc':
 196 |                         restart_cc_session(name, config)
 197 |                 continue
 198 |             
 199 |             # Check for stall
 200 |             stall = is_stalled(name, stype)
 201 |             if stall:
 202 |                 elapsed = time.time() - pane_snapshots.get(name, (None, now))[1]
 203 |                 log(f'WATCHDOG: {name} stalled for {elapsed:.0f}s')
 204 |                 if stype == 'cc' and detect_cc_stuck(name):
 205 |                     log(f'WATCHDOG: CC-specific stall detected in {name} — restarting')
 206 |                     restart_cc_session(name, config)
 207 |                 elif stype == 'python' and config.get('critical'):
 208 |                     restart_python_session(name, config)
 209 |             
 210 |             # Log a heartbeat every 5 min
 211 |             if now - last_status >= status_interval:
 212 |                 content = get_pane(name)
 213 |                 last_line = [l for l in content.split('\n') if l.strip()]
 214 |                 last_line = last_line[-1] if last_line else '(empty)'
 215 |                 log(f'HEARTBEAT {name}: {last_line[:80]}')
 216 |         
 217 |         if now - last_status >= status_interval:
 218 |             write_status_file()
 219 |             progress = check_render_progress()
 220 |             log(f'RENDER PROGRESS: {progress}')
 221 |             append_to_lessons('RENDER-HEARTBEAT', 'smart_loop', f'Progress: {progress}')
 222 |             last_status = now
 223 | 
 224 | if __name__ == '__main__':
 225 |     main()
 226 | 
```

### File: core/app.py (201 lines)
```
   1 | import os
   2 | from blueprints.curated_mining import curated_mining_bp
   3 | from pathlib import Path
   4 | from dotenv import load_dotenv
   5 | # Load .env from the same directory as this file (core/) so it works from any cwd
   6 | load_dotenv(Path(__file__).resolve().parent / ".env")
   7 | 
   8 | import logging
   9 | import json
  10 | import random
  11 | from flask import Flask, session
  12 | from flask_sqlalchemy import SQLAlchemy
  13 | from flask_migrate import Migrate
  14 | from sqlalchemy.orm import DeclarativeBase
  15 | from flask_login import LoginManager
  16 | from flask_limiter import Limiter
  17 | from flask_limiter.util import get_remote_address
  18 | try:
  19 |     from flask_caching import Cache
  20 |     _cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
  21 | except ImportError:
  22 |     _cache = None
  23 | 
  24 | # Configure logging
  25 | logging.basicConfig(level=logging.DEBUG)
  26 | 
  27 | class Base(DeclarativeBase):
  28 |     pass
  29 | 
  30 | # 1. Initialize DB WITHOUT app first to prevent circular loops
  31 | db = SQLAlchemy(model_class=Base)
  32 | 
  33 | # 2. Create the app instance — use absolute paths so templates/static are always found
  34 | #    whether run as "app:app" from core/ or "core.app:app" from project root
  35 | _core_dir = Path(__file__).resolve().parent
  36 | app = Flask(__name__, template_folder=str(_core_dir / "templates"), static_folder=str(_core_dir / "static"))
  37 | 
  38 | # Security: Uses .env secret, but provides a fallback for local dev
  39 | app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_protocol_pulse_2026")
  40 | 
  41 | # Configure the database
  42 | database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
  43 | if database_url.startswith("sqlite:"):
  44 |     # Ensure UTF-8 support for Bitcoin symbols
  45 |     if "?" not in database_url:
  46 |         database_url += "?charset=utf8mb4"
  47 | 
  48 | app.config["SQLALCHEMY_DATABASE_URI"] = database_url
  49 | app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
  50 |     "pool_recycle": 300,
  51 |     "pool_pre_ping": True,
  52 | }
  53 | 
  54 | # 3. Initialize extensions
  55 | db.init_app(app)
  56 | migrate = Migrate(app, db)
  57 | login_manager = LoginManager()
  58 | login_manager.init_app(app)
  59 | login_manager.login_view = "login"
  60 | 
  61 | limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day"])
  62 | limiter.init_app(app)
  63 | 
  64 | if _cache is not None:
  65 |     _cache.init_app(app)
  66 |     cache = _cache
  67 | else:
  68 |     class _NullCache:
  69 |         def init_app(self, app): pass
  70 |         def cached(self, timeout=None, key_prefix=None):
  71 |             def decorator(f): return f
  72 |             return decorator
  73 |     cache = _NullCache()
  74 | 
  75 | @app.context_processor
  76 | def inject_csrf():
  77 |     """Inject CSRF token for forms. Generate once per session."""
  78 |     if "csrf_token" not in session:
  79 |         session["csrf_token"] = os.urandom(32).hex()
  80 |     return {"csrf_token": session.get("csrf_token")}
  81 | 
  82 | 
  83 | @app.after_request
  84 | def add_static_cache_headers(response):
  85 |     """Allow browsers to cache static assets for 1 day."""
  86 |     from flask import request
  87 |     if request.path.startswith("/static/"):
  88 |         response.cache_control.max_age = 86400
  89 |         response.cache_control.public = True
  90 |     return response
  91 | 
  92 | 
  93 | # 4. Define Template Filters
  94 | @app.template_filter('inject_ads')
  95 | def inject_ads(content):
  96 |     import models
  97 |     try:
  98 |         active_ads = models.Advertisement.query.filter_by(is_active=True).all()
  99 |         if not active_ads:
 100 |             return content
 101 |         ad = random.choice(active_ads)
 102 |         ad_html = f'''
 103 |         <div class="native-ad-unit my-4 p-3 border-start border-danger bg-dark rounded">
 104 |             <small class="text-muted d-block mb-2 text-uppercase" style="letter-spacing: 1px; font-size: 0.7rem;">Protocol Partner</small>
 105 |             <a href="{ad.target_url}" target="_blank" rel="noopener" class="text-decoration-none">
 106 |                 <img src="{ad.image_url}" class="img-fluid mb-2 rounded" style="max-height: 150px;" alt="{ad.name}">
 107 |                 <p class="mb-0 text-white fw-bold">{ad.name}</p>
 108 |             </a>
 109 |         </div>
 110 |         '''
 111 |         parts = content.split('</p>', 2)
 112 |         if len(parts) > 2:
 113 |             return parts[0] + '</p>' + parts[1] + '</p>' + ad_html + parts[2]
 114 |         return content + ad_html
 115 |     except Exception as e:
 116 |         logging.warning(f"Ad injection failed: {e}")
 117 |         return content
 118 | 
 119 | @app.template_filter('from_json')
 120 | def from_json_filter(value):
 121 |     if not value:
 122 |         return []
 123 |     try:
 124 |         return json.loads(value)
 125 |     except (json.JSONDecodeError, TypeError):
 126 |         return []
 127 | 
 128 | # 5. User loader for Flask-Login
 129 | @login_manager.user_loader
 130 | def load_user(user_id):
 131 |     import models
 132 |     return models.User.query.get(int(user_id))
 133 | 
 134 | # =====================================
 135 | # THE IGNITION ZONE (CRITICAL ORDER)
 136 | # =====================================
 137 | # When we run as python app.py, __name__ is "__main__". Later, "import routes" does
 138 | # "from app import app", which loads this file again as module "app" (a second Flask
 139 | # app). Routes then register on that second app, but we call app.run() on this one → 404.
 140 | # So make "app" resolve to this same module when we are the main script.
 141 | if __name__ == "__main__":
 142 |     import sys
 143 |     sys.modules["app"] = sys.modules["__main__"]
 144 | 
 145 | with app.app_context():
 146 |     # 1. Load the models into memory first
 147 |     import models
 148 |     # 2. Create the tables (migration-safe: adds new columns/tables without dropping existing)
 149 |     db.create_all()
 150 |     # 2b. SESSION 12 — Run sentiment intelligence migrations (adds article sentiment columns + tables)
 151 |     try:
 152 |         from utils.db_migrate_sentiment import run_migrations
 153 |         run_migrations(db)
 154 |         logging.info("SESSION 12: sentiment-intel migrations applied")
 155 |     except Exception as _e:
 156 |         logging.warning("SESSION 12: db_migrate_sentiment failed: %s", _e)
 157 |     # 3. ONLY NOW load the routes
 158 |     import routes
 159 |     # 4. Register Terminal API blueprint
 160 |     try:
 161 |         from routes_premium_api import premium_api
 162 |         app.register_blueprint(premium_api)
 163 |         logging.info("Terminal API blueprint registered")
 164 |         # 5. Provision demo API key for playground
 165 |         from services.api_key_service import provision_demo_key
 166 |         provision_demo_key(db, models)
 167 |     except Exception as e:
 168 |         logging.warning("Terminal API blueprint not loaded: %s", e)
 169 |     # 6. Initialize FTS5 search index (SESSION 17 — GLOBAL SEARCH)
 170 |     try:
 171 |         import importlib.util as _ilu
 172 |         import os as _os
 173 |         _svc_path = _os.path.join(_os.path.dirname(__file__), 'services', 'search_service.py')
 174 |         _spec = _ilu.spec_from_file_location('search_service', _svc_path)
 175 |         _search_svc = _ilu.module_from_spec(_spec)
 176 |         _spec.loader.exec_module(_search_svc)
 177 |         _search_svc.init_fts_index(db)
 178 |         _search_svc.populate_fts_index(db)
 179 |         logging.info("FTS5 search index initialized")
 180 |     except Exception as _fts_init_err:
 181 |         logging.warning("FTS5 search index init failed (non-fatal): %s", _fts_init_err)
 182 | 
 183 | app.register_blueprint(curated_mining_bp)
 184 | 
 185 | # Diagnose: confirm / and /debug-routes are registered (debug 404)
 186 | try:
 187 |     rules = [r.rule for r in app.url_map.iter_rules()]
 188 |     has_root = "/" in rules
 189 |     logging.info("Routes registered: %s ... (/) present: %s", len(rules), has_root)
 190 |     if not has_root:
 191 |         logging.warning("Missing '/' route! Sample rules: %s", rules[:20])
 192 | except Exception as e:
 193 |     logging.warning("Could not list routes: %s", e)
 194 | 
 195 | if __name__ == "__main__":
 196 |     port = int(os.environ.get("PORT", 5000))
 197 |     print(f"Starting Protocol Pulse → http://127.0.0.1:{port}/ (debug routes: http://127.0.0.1:{port}/debug-routes)")
 198 |     # Disable reloader so the process that binds the port is the same one that loaded routes (avoids 404 from reloader child)
 199 |     app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
 200 | 
 201 | 
```

### File: core/blueprints/__init__.py (3 lines)
```
   1 | # core/blueprints — Protocol Pulse Blueprint Architecture
   2 | # Each module exposes a Flask Blueprint. Register them all in app.py.
   3 | 
```

### File: core/blueprints/affiliates.py (237 lines)
```
   1 | """
   2 | core/blueprints/affiliates.py
   3 | Protocol Pulse SESSION 13 — Affiliate Revenue Engine Blueprint
   4 | 
   5 | Routes:
   6 |   GET  /bitcoin-insurance          — Meanwhile landing page
   7 |   GET  /digital-residency          — RNS.ID landing page (alias)
   8 |   GET  /go/meanwhile               — Click redirect → Meanwhile
   9 |   GET  /go/rns                     — Click redirect → RNS.ID
  10 |   GET  /api/affiliate/click        — Click tracking + redirect
  11 |   GET  /admin/affiliates           — Admin dashboard
  12 | """
  13 | 
  14 | import hashlib
  15 | import logging
  16 | import os
  17 | from datetime import datetime
  18 | 
  19 | from flask import (
  20 |     Blueprint,
  21 |     redirect,
  22 |     render_template,
  23 |     request,
  24 |     jsonify,
  25 |     url_for,
  26 | )
  27 | from flask_login import login_required
  28 | 
  29 | logger = logging.getLogger(__name__)
  30 | 
  31 | affiliates_bp = Blueprint(
  32 |     "affiliates",
  33 |     __name__,
  34 |     url_prefix="",
  35 | )
  36 | 
  37 | # Affiliate destination URLs
  38 | AFFILIATE_URLS = {
  39 |     "meanwhile": "https://meanwhile.app?ref=KKM73K",
  40 |     "rns": "https://rns.id?ref=protocol-pulse",
  41 | }
  42 | 
  43 | 
  44 | # ────────────────────────────────────────────────────────────
  45 | # Helpers
  46 | # ────────────────────────────────────────────────────────────
  47 | def _get_user_hash(ip: str) -> str:
  48 |     """SHA256(ip + date.today() + TRACKING_SALT)[:16] — daily rotating."""
  49 |     from services.affiliate_injector import hash_user
  50 |     return hash_user(ip)
  51 | 
  52 | 
  53 | def _get_client_ip() -> str:
  54 |     return (
  55 |         request.headers.get("X-Forwarded-For", request.remote_addr or "")
  56 |         .split(",")[0]
  57 |         .strip()
  58 |     )
  59 | 
  60 | 
  61 | def _get_ab_variant(user_hash: str) -> str:
  62 |     """50/50 A/B split based on last nibble of user_hash."""
  63 |     return "A" if int(user_hash[-1], 16) < 8 else "B"
  64 | 
  65 | 
  66 | def _record_click_db(partner: str, article_id: str, user_hash: str, variant: str):
  67 |     """Write click to affiliate_clicks table (lazy import to avoid circular deps)."""
  68 |     try:
  69 |         from app import db
  70 |         from services.affiliate_injector import record_click
  71 |         record_click(db, partner, article_id, user_hash, variant)
  72 |     except Exception as exc:
  73 |         logger.warning("_record_click_db failed: %s", exc)
  74 | 
  75 | 
  76 | # ────────────────────────────────────────────────────────────
  77 | # Landing Pages
  78 | # ────────────────────────────────────────────────────────────
  79 | @affiliates_bp.route("/bitcoin-insurance")
  80 | def bitcoin_insurance():
  81 |     """Meanwhile Bitcoin Life Insurance landing page — SESSION 13."""
  82 |     return render_template("bitcoin_insurance.html")
  83 | 
  84 | 
  85 | # ────────────────────────────────────────────────────────────
  86 | # GET /api/affiliate/click  — Click tracking + redirect
  87 | # ────────────────────────────────────────────────────────────
  88 | @affiliates_bp.route("/api/affiliate/click")
  89 | def affiliate_click():
  90 |     """
  91 |     Track affiliate click and redirect to partner URL.
  92 | 
  93 |     Query params:
  94 |       partner    — 'meanwhile' | 'rns'
  95 |       article_id — source article (optional, defaults to 'direct')
  96 | 
  97 |     LAW: TRACKING_SALT MUST be set — raises RuntimeError if missing.
  98 |     LAW: Never store raw IP — always SHA256 hash.
  99 |     LAW: 50/50 A/B via user_hash last nibble.
 100 |     """
 101 |     partner = request.args.get("partner", "").strip().lower()
 102 |     article_id = request.args.get("article_id", "direct")
 103 | 
 104 |     if partner not in AFFILIATE_URLS:
 105 |         return redirect("/", code=302)
 106 | 
 107 |     ip = _get_client_ip()
 108 | 
 109 |     # TRACKING_SALT hard-fail — raises RuntimeError if not set (per LAW)
 110 |     user_hash = _get_user_hash(ip)
 111 | 
 112 |     # A/B variant: 50/50 deterministic from user_hash
 113 |     variant = _get_ab_variant(user_hash)
 114 | 
 115 |     # Record click asynchronously (fire-and-forget; don't block redirect)
 116 |     _record_click_db(partner, str(article_id), user_hash, variant)
 117 | 
 118 |     # Redirect to affiliate URL
 119 |     dest = AFFILIATE_URLS[partner]
 120 |     resp = redirect(dest, code=302)
 121 |     resp.headers["Cache-Control"] = "no-store, no-cache"
 122 |     return resp
 123 | 
 124 | 
 125 | # ────────────────────────────────────────────────────────────
 126 | # Short redirect aliases (/go/*)
 127 | # ────────────────────────────────────────────────────────────
 128 | @affiliates_bp.route("/go/meanwhile-s13")
 129 | def go_meanwhile_s13():
 130 |     """Session 13 short link for Meanwhile."""
 131 |     ip = _get_client_ip()
 132 |     user_hash = _get_user_hash(ip)
 133 |     variant = _get_ab_variant(user_hash)
 134 |     referrer = request.args.get("ref", request.referrer or "direct")
 135 |     _record_click_db("meanwhile", referrer[:200], user_hash, variant)
 136 |     resp = redirect(AFFILIATE_URLS["meanwhile"], code=302)
 137 |     resp.headers["Cache-Control"] = "no-store, no-cache"
 138 |     return resp
 139 | 
 140 | 
 141 | @affiliates_bp.route("/go/rns-s13")
 142 | def go_rns_s13():
 143 |     """Session 13 short link for RNS.ID."""
 144 |     ip = _get_client_ip()
 145 |     user_hash = _get_user_hash(ip)
 146 |     variant = _get_ab_variant(user_hash)
 147 |     referrer = request.args.get("ref", request.referrer or "direct")
 148 |     _record_click_db("rns", referrer[:200], user_hash, variant)
 149 |     resp = redirect(AFFILIATE_URLS["rns"], code=302)
 150 |     resp.headers["Cache-Control"] = "no-store, no-cache"
 151 |     return resp
 152 | 
 153 | 
 154 | # ────────────────────────────────────────────────────────────
 155 | # Admin Dashboard
 156 | # ────────────────────────────────────────────────────────────
 157 | @affiliates_bp.route("/admin/affiliates-s13")
 158 | @login_required
 159 | def admin_affiliates_s13():
 160 |     """
 161 |     Admin affiliate analytics dashboard (SESSION 13).
 162 |     Shows click counts per partner, A/B performance, recent clicks.
 163 |     """
 164 |     try:
 165 |         from app import db
 166 |         from sqlalchemy import text
 167 |         from services.affiliate_injector import (
 168 |             _init_affiliate_clicks_table,
 169 |             compute_ab_stats,
 170 |             PARTNER_CONFIG,
 171 |         )
 172 | 
 173 |         _init_affiliate_clicks_table(db)
 174 | 
 175 |         # Totals per partner
 176 |         totals = db.session.execute(text(
 177 |             "SELECT partner, COUNT(*) as total "
 178 |             "FROM affiliate_clicks "
 179 |             "WHERE clicked_at >= date('now', '-30 days') "
 180 |             "GROUP BY partner"
 181 |         )).fetchall()
 182 |         totals_map = {r[0]: r[1] for r in totals}
 183 | 
 184 |         # Daily clicks last 30 days
 185 |         daily = db.session.execute(text(
 186 |             "SELECT partner, date(clicked_at) as day, COUNT(*) as cnt "
 187 |             "FROM affiliate_clicks "
 188 |             "WHERE clicked_at >= date('now', '-30 days') "
 189 |             "GROUP BY partner, day ORDER BY day DESC"
 190 |         )).fetchall()
 191 |         daily_by_partner = {}
 192 |         for r in daily:
 193 |             daily_by_partner.setdefault(r[0], []).append({"date": r[1], "clicks": r[2]})
 194 | 
 195 |         # Recent clicks (last 20, k-anon: show truncated hash only)
 196 |         recent = db.session.execute(text(
 197 |             "SELECT partner, article_id, substr(user_hash,1,8) as hash_prefix, "
 198 |             "variant, clicked_at "
 199 |             "FROM affiliate_clicks "
 200 |             "ORDER BY clicked_at DESC LIMIT 20"
 201 |         )).fetchall()
 202 | 
 203 |         # A/B stats
 204 |         ab_stats = {
 205 |             "meanwhile": compute_ab_stats("meanwhile", db),
 206 |             "rns": compute_ab_stats("rns", db),
 207 |         }
 208 | 
 209 |         # Estimated earnings (conservative 2% conversion)
 210 |         earnings = {}
 211 |         for partner_key, cfg in PARTNER_CONFIG.items():
 212 |             t = totals_map.get(partner_key, 0)
 213 |             earnings[partner_key] = round(t * 0.02 * cfg["estimated_commission"], 2)
 214 | 
 215 |         return render_template(
 216 |             "admin/affiliates_s13.html",
 217 |             totals_map=totals_map,
 218 |             daily_by_partner=daily_by_partner,
 219 |             recent=recent,
 220 |             ab_stats=ab_stats,
 221 |             earnings=earnings,
 222 |             partner_cfg=PARTNER_CONFIG,
 223 |         )
 224 | 
 225 |     except Exception as exc:
 226 |         logger.error("admin_affiliates_s13 error: %s", exc)
 227 |         return render_template(
 228 |             "admin/affiliates_s13.html",
 229 |             totals_map={},
 230 |             daily_by_partner={},
 231 |             recent=[],
 232 |             ab_stats={},
 233 |             earnings={},
 234 |             partner_cfg={},
 235 |             error=str(exc),
 236 |         )
 237 | 
```

### File: core/blueprints/api.py (24 lines)
```
   1 | """
   2 | API BLUEPRINT — Protocol Pulse
   3 | ================================
   4 | Owns: /api/* (non-terminal, non-charts, non-mining)
   5 | Status: Core API routes in routes_api_v2.py (api_v2). Additional in routes.py.
   6 | TODO: Extract remaining /api/* routes from routes.py here (future session).
   7 | """
   8 | from flask import Blueprint
   9 | 
  10 | api_bp = Blueprint("api_main", __name__)
  11 | 
  12 | # Routes already in routes_api_v2.api_v2 (keep there):
  13 | #   /api/v2/* — V2 API endpoints
  14 | 
  15 | # Routes to migrate from routes.py:
  16 | #   GET  /api/sentiment        — sentiment summary
  17 | #   GET  /api/articles         — articles list
  18 | #   GET  /api/price            — BTC price proxy
  19 | #   GET  /api/mempool          — mempool stats proxy
  20 | #   GET  /api/fear-greed       — fear & greed index
  21 | #   GET  /api/search           — article search
  22 | #   POST /api/affiliates/impression — affiliate impression beacon
  23 | #   POST /api/affiliates/click      — affiliate click beacon
  24 | 
```

### File: core/blueprints/articles.py (23 lines)
```
   1 | """
   2 | ARTICLES BLUEPRINT — Protocol Pulse
   3 | =====================================
   4 | Owns: /articles, /article/<id>, /category/*
   5 | Status: Routes currently live in routes.py.
   6 | TODO: Extract article routes from routes.py into this blueprint (future session).
   7 | """
   8 | from flask import Blueprint
   9 | 
  10 | articles_bp = Blueprint("articles_main", __name__)
  11 | 
  12 | # Routes to migrate from routes.py:
  13 | #   GET  /articles             — articles listing
  14 | #   GET  /article/<id>         — article detail
  15 | #   GET  /articles/<category>  — category listing
  16 | #   GET  /bitcoin              — Bitcoin category
  17 | #   GET  /defi                 — DeFi category
  18 | #   GET  /regulation           — Regulation category
  19 | #   GET  /privacy              — Privacy category
  20 | #   GET  /innovation           — Innovation category
  21 | #   POST /admin/generate       — Article generation (admin)
  22 | #   POST /admin/publish/<id>   — Publish article (admin)
  23 | 
```

### File: core/blueprints/briefings.py (119 lines)
```
   1 | """
   2 | BRIEFINGS BLUEPRINT — Protocol Pulse
   3 | ======================================
   4 | GET /briefings — Public page showing last 7 days of HeyGen Sarah briefings.
   5 | Pulls from market_briefings table + oracle_briefing/output/ filesystem.
   6 | """
   7 | import os
   8 | from datetime import datetime, timedelta
   9 | from pathlib import Path
  10 | from flask import Blueprint, render_template, jsonify
  11 | 
  12 | briefings_bp = Blueprint("briefings", __name__)
  13 | 
  14 | 
  15 | def _get_fs_briefings(days: int = 7) -> list[dict]:
  16 |     """Scan oracle_briefing/output/ for briefing videos."""
  17 |     base = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "oracle_briefing" / "output"
  18 |     briefings = []
  19 |     cutoff = datetime.now() - timedelta(days=days)
  20 | 
  21 |     if not base.exists():
  22 |         return briefings
  23 | 
  24 |     for date_dir in sorted(base.iterdir(), reverse=True):
  25 |         if not date_dir.is_dir():
  26 |             continue
  27 |         try:
  28 |             dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
  29 |             if dir_date < cutoff:
  30 |                 break
  31 |         except ValueError:
  32 |             continue
  33 | 
  34 |         for mp4 in sorted(date_dir.glob("briefing_*.mp4"), reverse=True):
  35 |             parts = mp4.stem.split("_")
  36 |             btype = parts[1] if len(parts) > 1 else "unknown"
  37 |             btime = parts[2] if len(parts) > 2 else "0000"
  38 |             size_mb = round(mp4.stat().st_size / 1024 / 1024, 1)
  39 | 
  40 |             # Check for matching script
  41 |             script_path = mp4.with_suffix(".txt")
  42 |             script_text = ""
  43 |             if script_path.exists():
  44 |                 script_text = script_path.read_text()[:500]
  45 | 
  46 |             briefings.append({
  47 |                 "date": date_dir.name,
  48 |                 "type": btype,
  49 |                 "time": f"{btime[:2]}:{btime[2:]}" if len(btime) == 4 else btime,
  50 |                 "file": str(mp4),
  51 |                 "filename": mp4.name,
  52 |                 "size_mb": size_mb,
  53 |                 "script_preview": script_text,
  54 |                 "video_url": f"/briefings/video/{date_dir.name}/{mp4.name}",
  55 |             })
  56 | 
  57 |     return briefings
  58 | 
  59 | 
  60 | def _get_db_briefings(days: int = 7) -> list[dict]:
  61 |     """Pull briefings from MarketBriefing DB table."""
  62 |     try:
  63 |         from models import MarketBriefing
  64 |         cutoff = datetime.now() - timedelta(days=days)
  65 |         rows = MarketBriefing.query.filter(
  66 |             MarketBriefing.generated_at >= cutoff,
  67 |             MarketBriefing.status == "completed",
  68 |         ).order_by(MarketBriefing.generated_at.desc()).all()
  69 | 
  70 |         return [{
  71 |             "date": r.scheduled_date or r.generated_at.strftime("%Y-%m-%d"),
  72 |             "type": r.briefing_type,
  73 |             "time": r.generated_at.strftime("%H:%M") if r.generated_at else "",
  74 |             "title": r.title,
  75 |             "script_preview": (r.script_text or "")[:500],
  76 |             "video_url": r.video_url or "",
  77 |             "duration": r.duration_seconds,
  78 |             "btc_price": r.btc_price_at_generation,
  79 |             "source": "db",
  80 |         } for r in rows]
  81 |     except Exception:
  82 |         return []
  83 | 
  84 | 
  85 | @briefings_bp.route("/briefings")
  86 | def briefings_page():
  87 |     """Public page: last 7 days of Oracle Briefings."""
  88 |     fs_briefings = _get_fs_briefings(days=7)
  89 |     db_briefings = _get_db_briefings(days=7)
  90 | 
  91 |     # Merge: prefer DB entries, supplement with filesystem
  92 |     all_briefings = db_briefings + fs_briefings
  93 | 
  94 |     # Group by date
  95 |     by_date = {}
  96 |     for b in all_briefings:
  97 |         date = b["date"]
  98 |         if date not in by_date:
  99 |             by_date[date] = []
 100 |         by_date[date].append(b)
 101 | 
 102 |     return render_template("briefings.html", briefings_by_date=by_date)
 103 | 
 104 | 
 105 | @briefings_bp.route("/api/briefings")
 106 | def briefings_api():
 107 |     """JSON API: last 7 days of briefings."""
 108 |     fs_briefings = _get_fs_briefings(days=7)
 109 |     db_briefings = _get_db_briefings(days=7)
 110 |     return jsonify({"briefings": db_briefings + fs_briefings})
 111 | 
 112 | 
 113 | @briefings_bp.route("/briefings/video/<date>/<filename>")
 114 | def briefing_video(date, filename):
 115 |     """Serve briefing video files."""
 116 |     from flask import send_from_directory
 117 |     video_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "oracle_briefing" / "output" / date
 118 |     return send_from_directory(str(video_dir), filename)
 119 | 
```

### File: core/blueprints/charts.py (24 lines)
```
   1 | """
   2 | CHARTS BLUEPRINT — Protocol Pulse
   3 | ===================================
   4 | Owns: /charts, /charts/*, /api/charts/*
   5 | Status: Routes currently live in routes.py (p3-charts session).
   6 | TODO: Extract chart routes from routes.py into this blueprint (future session).
   7 | """
   8 | from flask import Blueprint
   9 | 
  10 | charts_bp = Blueprint("charts_main", __name__)
  11 | 
  12 | # Routes to migrate from routes.py:
  13 | #   GET  /charts                         — charts.html (9 sections)
  14 | #   GET  /charts/embed/<chart_id>        — embeddable chart widget
  15 | #   GET  /api/charts/price-history       — proxy CoinGecko
  16 | #   GET  /api/charts/mempool-data        — proxy mempool.space
  17 | #   GET  /api/charts/hashrate-history    — proxy blockchair
  18 | #   GET  /api/charts/pool-distribution   — mining pool donut
  19 | #   GET  /api/charts/fee-history         — mempool fees
  20 | #   GET  /api/charts/lightning           — lightning stats
  21 | #   GET  /api/charts/fear-greed          — F&G index
  22 | #   POST /api/charts/price-alert         — set price alert
  23 | #   POST /api/charts/ai-explain          — Claude Haiku chart analysis
  24 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
