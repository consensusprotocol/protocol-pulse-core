# Heimdall audit

**Question:** Commit 1d makes selection propose sentence-aligned windows: abbreviation-aware sentence splitting (sentence_law.is_terminal), windows of one to three whole sentences (interjection-only sentences transparent per PBX D4a), clip budget 12-20 s, the editor's hook/clip slots honoured, and a window the sentence law rejects replaced by the next-ranked legal candidate of the same kind (score floor, budget, overlap, per-channel and per-video caps) instead of moving a cut. Find defects: a path that can pick an illegal/overlapping window, a cap or floor bypass, wrong window bookkeeping, a fallback that can loop or silently drop the hook. (this chunk: pipeline/select_passages.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0193
## Consensus findings (majority of panel agrees)
- **[critical] pipeline/select_passages.py:0** The first candidate (the editor's hook or clip) bypasses _eligible entirely, so it can violate the score floor, duration budget, overlap, per-channel cap, and per-video cap.
  - evidence: `if p is None or (p is not first and not _eligible(p, kind)): continue`
  - fix: Apply _eligible to the first candidate as well, or validate the first candidate before calling _fill.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[critical] pipeline/select_passages.py:0** A fallback can select a later clip that is still in the clips list; that clip is then processed again as first in the outer loop, bypassing _eligible and tried, causing a duplicate/overlapping window and cap/floor bypass.
  - evidence: `for clip in clips:
                seg = _fill(clip, f"clip_{len(clip_segs) + 1:02d}", "clip") ... if p is None or (p is not first and not _eligible(p, kind)): continue`
  - fix: Remove fallback-selected candidates from clips, or check tried/used for the first candidate, or mark fallback-selected clips so they are not processed again.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[medium] pipeline/select_passages.py:0** After _build_segment returns None, the code still writes to boundary_report[-1], which can raise IndexError if no report entry exists or mutate the wrong entry.
  - evidence: `seg = _build_segment(p, label)
            boundary_report[-1]["fallback"] = p is not first`
  - fix: Only set fallback when seg is not None and a boundary_report entry was appended for this candidate.
  - raised by deepseek:F3; agree: deepseek, qwen27b
- **[medium] pipeline/select_passages.py:0** If the hook cannot be filled, hook_seg is None and the guard skips all clips, silently dropping the hook and every clip slot.
  - evidence: `hook_seg = _fill(hook, "hook", "hook") ... if hook_seg is not None:`
  - fix: Handle hook failure explicitly or still attempt clip slots when the hook is unavailable.
  - raised by deepseek:F4; agree: deepseek, qwen27b
- **[low] pipeline/select_passages.py:0** _source_for skips the downloaded-window boundary check when span is 0 or None, allowing a window outside the downloaded source.
  - evidence: `if span and not (offsets[vid] + 1.0 <= p["start"] and p["end"] <= offsets[vid] + span - 1.0):`
  - fix: Require a valid span and always enforce the boundary check.
  - raised by deepseek:F5; agree: deepseek, qwen27b
- **[critical] pipeline/select_passages.py:310** boundary_report[-1] raises IndexError when the list is empty, or silently mutates a stale entry from a prior _source_for failure. When _source_for succeeds (returns None) nothing is appended, so on the very first successful candidate the list may be empty (crash) or the last element belongs to an earlier rejected candidate (wrong bookkeeping).
  - evidence: `seg = _build_segment(p, label)
            boundary_report[-1]["fallback"] = p is not first`
  - fix: Append a new boundary_report entry for the successful candidate before setting its 'fallback' field, e.g. entry = {"segment": label, "video_id": p["video_id"], "channel": p["channel"], "window_full_video_s": [p["start"], p["end"]], "result": "accepted", "fallback": p is not first}; boundary_report.append(entry).
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[high] pipeline/select_passages.py:303** The editor's first candidate (p is first) bypasses every _eligible check: score floor, duration budget (12-20 s), overlap with already-used windows, per-video cap, and per-channel cap. A window that overlaps the hook or exceeds the clip budget can therefore be selected and sealed into the EDL.
  - evidence: `if p is None or (p is not first and not _eligible(p, kind)):
            continue`
  - fix: Apply _eligible to the first candidate as well, or at minimum check overlap and duration budget for the first candidate before calling _build_segment. If the first candidate fails those checks, treat it as rejected and proceed to the sorted fallback list.
  - raised by qwen27b:F2; agree: deepseek, qwen27b
- **[high] pipeline/select_passages.py:290** _source_for caches the downloaded window per video_id. If the hook already downloaded video X for window [10,20], a fallback clip from the same video at [50,60] finds vid in sources, skips the download, and then fails the bounds check (offsets[vid]+1.0 <= 50 is false). The fallback is permanently blocked for any same-video passage outside the originally downloaded window.
  - evidence: `if vid not in sources:
            res = _download_window(vid, p["start"], p["end"], run_dir)
            if not res or not res[0]:
                return "download failed"
            sources[vid], o`
  - fix: Before the bounds check, verify that p's window is actually contained in the already-downloaded span. If it is not, re-download (or extend) the window for that video_id and update sources/offsets/transcripts accordingly, rather than returning 'outside the downloaded window'.
  - raised by qwen27b:F3; agree: deepseek, qwen27b
- **[medium] pipeline/select_passages.py:311** When _build_segment returns None (sentence law rejects the window) no entry is appended to boundary_report. The rejection is invisible in the audit trail, and the loop simply continues to the next candidate. If all candidates are rejected by the sentence law, _fill returns None and the slot is silently dropped with no diagnostic record.
  - evidence: `seg = _build_segment(p, label)
            boundary_report[-1]["fallback"] = p is not first
            if seg is not None:
                used.append(p)
                return seg`
  - fix: When seg is None, append a boundary_report entry recording the sentence-law rejection (segment label, video_id, channel, window, result='rejected: sentence law', fallback flag) before continuing the loop.
  - raised by qwen27b:F4; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- deepseek: [high] If _whisper_transcribe fails, _source_for returns 'transcription failed' after already setting sources[vid] and offsets[vid] but before setting transcripts[vid]. A later candidate from the same video then skips the download/transcribe block and crashes with KeyError on transcripts[vid].
- qwen27b: [high] KeyError on transcripts[vid] when transcription fails but download succeeded: sources[vid] and offsets[vid] are set before the transcription check, so a subsequent _source_for call for the same video_id skips the download block (vid in sources is True) and then executes `transcripts[vid].get("duration")` on a key that was never assigned, raising an unhandled KeyError that crashes the entire selection pass.
