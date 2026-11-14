# heimdall_qwen (qwen/qwen3.8-27b, 366.6 s, $0.010, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the logic of `_quiet` and the race conditions, but I missed several critical structural and data-integrity issues that the other models (specifically GLM and Muse) identified:

1.  **The "Vanish" Bug (GLM P0):** I noted that `compose` returns `None` if `out` is empty and `quiet` is empty, and I called this "correct." I failed to realize that if a cycle runs but finds *no new uploads* (n=0), `out` remains empty. If *no* video in the window has a Bitcoin term (so `quiet` is also empty/None), the function returns `None`. This causes `write_cycles_notice(None)` to **delete** the line. The orchestrator's order is to report *after each cycle*. If a cycle runs and finds nothing, the line should say "Cycle ran, found nothing," not disappear. GLM correctly identified that the line vanishes when it should persist with a "nothing found" status.
2.  **Multi-line Reasons (GLM P0):** I assumed `reason` fields were clean. GLM pointed out that `yt-dlp` errors can contain newlines. `write_cycles_notice` explicitly rejects lines with `"\n"`. If a video's `reason` contains a newline, `compose` produces a multi-line string, `write_cycles_notice` raises `ValueError`, and the line is never written (or removed if it was previously valid). This is a hard failure mode I missed.
3.  **Count Mismatch (Muse P1):** I noted the N+1 query issue but missed the logical flaw in how `n` (from the event) is compared to `vids` (derived from time windows). If the event says "3 new" but the time-window heuristic only captures 2 discovery events (due to clock skew or delayed writes), the line says "3 new" but lists 2. This is a data integrity error.
4.  **Stale "Newest with One" (GLM P1):** I analyzed the `_quiet` logic but missed that the `tail` lookup for "the newest upload with one" searches the *entire* `videos` table, not just the 3-hour window. On a quiet Saturday, this could point to a video from days ago, which is misleading in a "last 3 hours" context.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM (P0s):** **Agree.** The "vanish" bug and the multi-line reason bug are critical. The code fails to meet the "report after each cycle" requirement when cycles are empty, and it crashes on dirty data.
*   **Muse (P1s):** **Agree.** The count mismatch is a real risk. The N+1 query is a performance issue but less critical than the correctness bugs.
*   **My Cycle 1 (Race Conditions):** **Disagree with severity.** I flagged race conditions as a potential issue. GLM and Muse correctly identified that SQLite WAL mode + `RLock` makes the reads safe enough for this low-frequency reporting task. The "stale" data is corrected on the next 60s health loop. This is not a bug, just a characteristic of the polling design.
*   **My Cycle 1 (Time Zones):** **Agree.** The `ZoneInfo` usage is correct. No issues here.

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **`_quiet` Logic Flaw with `MINED_PARTIAL`:**
    In `_quiet`, `known` includes `Q.MINED_PARTIAL`. The check `if any((r["windows"] or 0) > (r["windows_screened"] or 0) for r in known)` determines if a Bitcoin term was found.
    *   If a video is `MINED_PARTIAL` because *some* windows failed (outage) but the *successful* windows had no Bitcoin terms, `windows` (total) > `windows_screened` (screened out) might be false if the failed windows were never "screened" (they were just failed).
    *   Actually, `windows_screened` counts windows *sent to the model*. If a window failed, it wasn't sent. So `windows` (total) > `windows_screened` (sent) would be True.
    *   Wait, the logic is: `windows` is the total number of windows. `windows_screened` is the number of windows that *passed* the Bitcoin screen (i.e., were sent to the model).
    *   If `windows > windows_screened`, it means some windows were *not* sent to the model. This implies they were screened out (no Bitcoin term).
    *   The condition `if any(... > ...)` returns `""` (no quiet note) if *any* video has windows that were *not* screened out? No, that's backwards.
    *   Let's re-read: `windows` = total windows. `windows_screened` = windows sent to model.
    *   If `windows > windows_screened`, it means some windows were *not* sent to the model. Why? Because they were screened out (no Bitcoin term).
    *   So, if `windows > windows_screened`, it means the video *did* have windows with no Bitcoin term.
    *   The code says: `if any((r["windows"] or 0) > (r["windows_screened"] or 0) for r in known): return ""`.
    *   This returns `""` (no "Nothing Bitcoin" note) if *any* video has windows that were screened out.
    *   This is **incorrect**. If a video has 10 windows, and 5 were screened out (no Bitcoin), and 5 were sent to the model (had Bitcoin), then `windows (10) > windows_screened (5)` is True. The code returns `""`, suppressing the "Nothing Bitcoin" note. This is correct *if* the model found moments. But if the model found *no* moments (0 moments), the video is `MINED` with 0 moments.
    *   The "Nothing Bitcoin" note should appear if *no* video in the window had a Bitcoin term *in any window that was sent to the model*.
    *   The current logic checks if *any* window was screened out. This is the wrong condition. It should check if *any* window was sent to the model *and* resulted in a moment? No, the note is "Nothing Bitcoin in the last 3h". It should appear if *no* video had a Bitcoin term.
    *   If a video has a Bitcoin term, it is sent to the model. `windows_screened` increases.
    *   If *no* video has a Bitcoin term, `windows_screened` is 0 for all. `windows > 0` is True. The code returns `""`. **BUG.**
    *   If *no* video has a Bitcoin term, the code *suppresses* the "Nothing Bitcoin" note. It should *print* it.
    *   The logic is inverted. It should be: `if any((r["windows_screened"] or 0) > 0 for r in known): return ""`. (If any video had a window sent to the model, don't say "Nothing Bitcoin").

2.  **`_videos` Query Injection Risk (Low):**
    `_videos` uses `f"SELECT * FROM videos WHERE video_id IN ({','.join('?' * len(chunk))})"`. This is safe because it uses placeholders. However, if `ids` is empty, `chunk` is empty, and the SQL becomes `IN ()`, which is a syntax error in SQLite.
    *   `compose` calls `_videos(q, {e["video_id"] for e in disc})`. If `disc` is empty, `ids` is empty.
    *   `for i in range(0, 0, 500)` does not run. `out` is `[]`. Returns `{}`.
    *   So it's safe.

3.  **`newest` Calculation in `compose`:**
    `newest = max(newest or ts, ts)`.
    If `newest` is `None`, `newest or ts` is `ts`. `max(ts, ts)` is `ts`.
    If `newest` is set, `max(newest, ts)`.
    This is correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 6/10 | 4/10 | Discovered the inverted logic in `_quiet` (P0) and the "vanish" bug (P0). |
| **Robustness** | 7/10 | 5/10 | Multi-line reasons cause hard failures (P0). |
| **Performance** | 8/10 | 7/10 | N+1 queries are acceptable but not optimal. |
| **Maintainability** | 8/10 | 8/10 | Code is clear, but the logic in `_quiet` is confusing. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
1.  **`cycles.py` `_quiet` logic is inverted.**
    *   Current: `if any((r["windows"] or 0) > (r["windows_screened"] or 0) for r in known): return ""`
    *   Fix: `if any((r["windows_screened"] or 0) > 0 for r in known): return ""`
    *   Reason: If *any* video had a window sent to the model (i.e., had a Bitcoin term), we should *not* print "Nothing Bitcoin". The current code prints "Nothing Bitcoin" only if *no* video had any windows screened out, which is impossible if there are any videos. It effectively suppresses the note whenever there are any videos with windows.

2.  **`cycles.py` `compose` returns `None` when cycles ran but found nothing.**
    *   Current: `if not out and not quiet: return None`
    *   Fix: If `cycles` is not empty, but `out` is empty (no new uploads), and `quiet` is empty (no Bitcoin note), return a line saying "Cycles ran, no new uploads found."
    *   Reason: The line should not vanish. It should report the status of the cycles.

3.  **`cycles.py` `video_entry` / `compose` does not sanitize `reason` for newlines.**
    *   Current: `why = _one(v["reason"], 120)`
    *   Fix: `_one` already collapses whitespace. `return " ".join(str(s or "").split())`. This *does* handle newlines.
    *   Wait, `_one` is defined as:
        ```python
        def _one(s, n=None):
            t = " ".join(str(s or "").split())
            return t if n is None or len(t) <= n else t[:n - 3] + "..."
        ```
    *   This *does* remove newlines. So GLM's P0 about multi-line reasons is **invalid** for the current code. `_one` handles it.
    *   **Correction:** I agree with GLM that it's a risk, but the code *already* mitigates it via `_one`. However, `_one` is only applied to `reason` in `video_entry`. Is it applied to the whole line?
    *   `compose` returns `_one(head + body + tail)`.
    *   So the final line is sanitized. **This is not a bug.**

**P1 HIGH**
1.  **`cycles.py` `compose` count mismatch.**
    *   `n` from event vs `len(evs)` from time window.
    *   Fix: Use `n` for the count, but if `len(evs) != n`, add a note "(M found in events)". The code *already* does this: `found = "" if len(evs) == n else f" ({len(evs)} found in its events)"`.
    *   So this is **already handled**.

2.  **`cycles.py` `_quiet` "newest with one" is not windowed.**
    *   Fix: Add `AND discovered_ts >= ?` to the `last` query in `_quiet`.

**P2 MEDIUM**
1.  **N+1 queries in `compose`.**
    *   Fix: Use `_videos` (already done).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the inverted logic in `_quiet` so that the "Nothing Bitcoin" note is actually printed when no videos had Bitcoin terms.**

## 7. PRODUCTION READY?

**No.**

**Conditions:**
1.  Fix the `_quiet` logic (P0).
2.  Fix the `compose` return value when cycles ran but found nothing (P0).
3.  Add a test for the "Nothing Bitcoin" note appearing when no videos have Bitcoin terms.
4.  Add a test for the line persisting when cycles run but find no new uploads.