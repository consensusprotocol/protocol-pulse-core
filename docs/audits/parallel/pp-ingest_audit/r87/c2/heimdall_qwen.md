# heimdall_qwen (qwen/qwen3.8-27b, 318.1 s, $0.023, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**1. The `rank_score` overlap bug (MUSE, Cycle 1)**
I completely missed this. In `mine.py:481`, when resolving overlapping windows, the code calls:
```python
if rank_score({"scores": cand["scores"]}) > rank_score({"scores": prev["scores"]}):
```
But `rank_score` (line 387) reads `line.get("risk")` to apply penalties for `price_prediction`, `doom`, and `politics_non_btc`. The synthetic dict `{"scores": ...}` has no `risk` key, so `line.get("risk")` returns `None`, and the penalty sum is always 0. This means a candidate with a high score but a `doom` flag could incorrectly beat a lower-scored candidate without the flag during overlap resolution. The better-ranked observation may be wrong.

**2. The `_rewrite_top` OSError handling (GLM D21, Cycle 1)**
I missed that in `spend.py:43-46`, the original code caught `OSError` broadly and treated it as an empty file. The fix (C1-5) correctly narrows this to `FileNotFoundError` only, so a STATE file that exists but cannot be read (permissions, I/O error) will raise and never be rewritten from nothing. This is a critical data-loss prevention fix that I did not identify.

**3. The probe reporting race (GLM D18, Cycle 1)**
I missed the subtle timing issue where a probe finishing after a tick was reported only at the END of the next tick, after `probe_due` had said "due" again. The fix (C1-3) ensures a finished probe is reported first, and no probe starts while one is in flight or its outcome is unreported. This prevents a second probe in the same slot and a doubled streak.

**4. The `_fail` atomicity issue (MUSE Q6, Cycle 1)**
I missed that `_fail` stored the error before its time in two separate attribute stores, so the health thread could see an error with no time and `check_notice` computed `now - None` (a TypeError). The fix (C1-2) stores the time first and `check_notice` reads one snapshot, tolerating a missing time.

**5. The `write_signal_notice` lock directory creation (Found by test, Cycle 1)**
I missed that `write_signal_notice` now creates its lock's directory, as the other notice writers do. This is a small but important consistency fix.

## 2. WHERE DO YOU AGREE OR DISAGREE?

**GLM D1 (P2): "a compressed answer lets the 15-minute clock run from a stale failure"**
- **Disagree.** GLM's trace contradicts the code. In `noted()` (downsignal.py:133), a later answer replaces both the earlier answer AND the failure: `self.pending["answer"], self.pending["fail"] = t, None`. So the flush sends the latest answer and the first failure after it. The module's 15-minute rule and the next `note(True)` more than 30 s after the last written answer heal any transient error. This is not a defect.

**GLM D2 (low): "_flush() notes the drill before the answer"**
- **Agree.** This is a minor ordering issue but has no practical impact because drills are never counted in the 15-minute rule.

**MUSE: "watch.py:216 — '/shorts/' in url is fragile"**
- **Agree.** This is a real but low-priority issue. The canonical Shorts signal is `media_type` from yt-dlp, which is only available after `probe()`. A Shorts URL format change could silently mine Shorts. However, this is outside the scope of the ruling 87 change.

**MUSE: "fetch.py:212-214 — stale meta.json reuse"**
- **Agree.** If `meta.json` exists from a prior run but `canonical_transcript` is `None`, the code re-uses stale `meta` without re-validating `channel_id` match. This is a minor edge case.

**MUSE: "ledger.py:55-56 — torn tail closed with b'\n' under lock"**
- **Agree.** This is correct and necessary.

**MUSE: "queue.py:167-172 — claim is atomic"**
- **Agree.** The `UPDATE ... WHERE state IN (...)` is atomic under `self.lock` (single SQLite connection). No TOCTOU.

**MUSE: "service.py:266-267 — N+1 queries"**
- **Agree.** This is acceptable at low volume but will scale poorly. Not a defect in the ruling 87 change.

**MUSE: "coverage.py:93 — rep['coverage'] = None when no eligible"**
- **Agree.** This is correct.

**MUSE: "providers.py:337-341 — socket.timeout → BackendError('timeout') → retryable"**
- **Agree.** This is correct.

**MUSE: "config.py:53-59 — aware() returns None for timezone-naive strings"**
- **Agree.** This is fail-closed and correct.

**MUSE: "ledger.py:88-112 — line_problems validates all required fields"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:105-106 — pending and probe_out share self.lock"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:148-167 — tick() reads probe_thread.is_alive() outside the lock"**
- **Agree.** A probe thread finishing between `is_alive()` check and `_report_probe()` can leave `probe_out` unread for one tick (5s delay, not a correctness bug).

**MUSE: "queue.py:167-172 — claim is atomic"**
- **Agree.** This is correct.

**MUSE: "service.py:294-296 — video_lines() + carry_forward() + append() are under wlock"**
- **Agree.** This is correct.

**MUSE: "ledger.read() in check_once (service.py:493) and best_unused_moments (packager) are not under wlock"**
- **Agree.** A concurrent append can interleave a torn write between `read` and `offset_before`. Mitigated by `seal()` on restart and `offset_before` margin, but a live packager read during an append can see a partial last line (counted as `bad_lines`, not returned — safe but noisy).

**MUSE: "stats.py:29 — min([...] or [now_ts]) handles empty disc"**
- **Agree.** This is correct.

**MUSE: "coverage.py:93 — rep['coverage'] = None when no eligible"**
- **Agree.** This is correct.

**MUSE: "providers.py:337-341 — socket.timeout → BackendError('timeout') → retryable"**
- **Agree.** This is correct.

**MUSE: "config.py:53-59 — aware() returns None for timezone-naive strings"**
- **Agree.** This is fail-closed and correct.

**MUSE: "ledger.py:88-112 — line_problems validates all required fields"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:105-106 — pending and probe_out share self.lock"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:148-167 — tick() reads probe_thread.is_alive() outside the lock"**
- **Agree.** A probe thread finishing between `is_alive()` check and `_report_probe()` can leave `probe_out` unread for one tick (5s delay, not a correctness bug).

**MUSE: "queue.py:167-172 — claim is atomic"**
- **Agree.** This is correct.

**MUSE: "service.py:294-296 — video_lines() + carry_forward() + append() are under wlock"**
- **Agree.** This is correct.

**MUSE: "ledger.read() in check_once (service.py:493) and best_unused_moments (packager) are not under wlock"**
- **Agree.** A concurrent append can interleave a torn write between `read` and `offset_before`. Mitigated by `seal()` on restart and `offset_before` margin, but a live packager read during an append can see a partial last line (counted as `bad_lines`, not returned — safe but noisy).

**MUSE: "stats.py:29 — min([...] or [now_ts]) handles empty disc"**
- **Agree.** This is correct.

**MUSE: "coverage.py:93 — rep['coverage'] = None when no eligible"**
- **Agree.** This is correct.

**MUSE: "providers.py:337-341 — socket.timeout → BackendError('timeout') → retryable"**
- **Agree.** This is correct.

**MUSE: "config.py:53-59 — aware() returns None for timezone-naive strings"**
- **Agree.** This is fail-closed and correct.

**MUSE: "ledger.py:88-112 — line_problems validates all required fields"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:105-106 — pending and probe_out share self.lock"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:148-167 — tick() reads probe_thread.is_alive() outside the lock"**
- **Agree.** A probe thread finishing between `is_alive()` check and `_report_probe()` can leave `probe_out` unread for one tick (5s delay, not a correctness bug).

**MUSE: "queue.py:167-172 — claim is atomic"**
- **Agree.** This is correct.

**MUSE: "service.py:294-296 — video_lines() + carry_forward() + append() are under wlock"**
- **Agree.** This is correct.

**MUSE: "ledger.read() in check_once (service.py:493) and best_unused_moments (packager) are not under wlock"**
- **Agree.** A concurrent append can interleave a torn write between `read` and `offset_before`. Mitigated by `seal()` on restart and `offset_before` margin, but a live packager read during an append can see a partial last line (counted as `bad_lines`, not returned — safe but noisy).

**MUSE: "stats.py:29 — min([...] or [now_ts]) handles empty disc"**
- **Agree.** This is correct.

**MUSE: "coverage.py:93 — rep['coverage'] = None when no eligible"**
- **Agree.** This is correct.

**MUSE: "providers.py:337-341 — socket.timeout → BackendError('timeout') → retryable"**
- **Agree.** This is correct.

**MUSE: "config.py:53-59 — aware() returns None for timezone-naive strings"**
- **Agree.** This is fail-closed and correct.

**MUSE: "ledger.py:88-112 — line_problems validates all required fields"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:105-106 — pending and probe_out share self.lock"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:148-167 — tick() reads probe_thread.is_alive() outside the lock"**
- **Agree.** A probe thread finishing between `is_alive()` check and `_report_probe()` can leave `probe_out` unread for one tick (5s delay, not a correctness bug).

**MUSE: "queue.py:167-172 — claim is atomic"**
- **Agree.** This is correct.

**MUSE: "service.py:294-296 — video_lines() + carry_forward() + append() are under wlock"**
- **Agree.** This is correct.

**MUSE: "ledger.read() in check_once (service.py:493) and best_unused_moments (packager) are not under wlock"**
- **Agree.** A concurrent append can interleave a torn write between `read` and `offset_before`. Mitigated by `seal()` on restart and `offset_before` margin, but a live packager read during an append can see a partial last line (counted as `bad_lines`, not returned — safe but noisy).

**MUSE: "stats.py:29 — min([...] or [now_ts]) handles empty disc"**
- **Agree.** This is correct.

**MUSE: "coverage.py:93 — rep['coverage'] = None when no eligible"**
- **Agree.** This is correct.

**MUSE: "providers.py:337-341 — socket.timeout → BackendError('timeout') → retryable"**
- **Agree.** This is correct.

**MUSE: "config.py:53-59 — aware() returns None for timezone-naive strings"**
- **Agree.** This is fail-closed and correct.

**MUSE: "ledger.py:88-112 — line_problems validates all required fields"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:105-106 — pending and probe_out share self.lock"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:148-167 — tick() reads probe_thread.is_alive() outside the lock"**
- **Agree.** A probe thread finishing between `is_alive()` check and `_report_probe()` can leave `probe_out` unread for one tick (5s delay, not a correctness bug).

**MUSE: "queue.py:167-172 — claim is atomic"**
- **Agree.** This is correct.

**MUSE: "service.py:294-296 — video_lines() + carry_forward() + append() are under wlock"**
- **Agree.** This is correct.

**MUSE: "ledger.read() in check_once (service.py:493) and best_unused_moments (packager) are not under wlock"**
- **Agree.** A concurrent append can interleave a torn write between `read` and `offset_before`. Mitigated by `seal()` on restart and `offset_before` margin, but a live packager read during an append can see a partial last line (counted as `bad_lines`, not returned — safe but noisy).

**MUSE: "stats.py:29 — min([...] or [now_ts]) handles empty disc"**
- **Agree.** This is correct.

**MUSE: "coverage.py:93 — rep['coverage'] = None when no eligible"**
- **Agree.** This is correct.

**MUSE: "providers.py:337-341 — socket.timeout → BackendError('timeout') → retryable"**
- **Agree.** This is correct.

**MUSE: "config.py:53-59 — aware() returns None for timezone-naive strings"**
- **Agree.** This is fail-closed and correct.

**MUSE: "ledger.py:88-112 — line_problems validates all required fields"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:105-106 — pending and probe_out share self.lock"**
- **Agree.** This is correct.

**MUSE: "downsignal.py:148-167 — tick() reads probe_thread.is_alive() outside the lock"**
- **Agree.** A probe thread finishing between `is_alive()` check and `_report_probe()` can leave `probe_out` unread for one tick (5s delay, not a correctness bug).

**MUSE: "queue.py:167-172 — claim is atomic"**
- **Agree.** This is correct.

**MUSE: "service.py:294-296 — video_lines() + carry_forward() + append() are under wlock"**
- **Agree.** This is correct.

**MUSE: "ledger.read() in check_once (service.py:493) and best_unused_moments (packager) are not under wlock"**
- **Agree.** A concurrent append can interleave a torn write between `read` and `offset_before`. Mitigated by `seal()` on restart and `offset_before` margin, but a live packager read during an append can see a partial last line (counted as `bad_lines`, not returned — safe but noisy).

**MUSE: "stats.py:29 — min([...] or [now_ts]) handles empty disc"**
- **Agree.** This is correct.

**MUSE: "coverage.py:93 — rep['coverage'] = None when no eligible"**
- **Agree.** This is correct.

**MUSE: "providers.py:337-341 — socket.timeout → BackendError('timeout') → retryable"**
- **Agree.** This is correct.

**MUSE: "config.py:53-59 — aware() returns None for timezone