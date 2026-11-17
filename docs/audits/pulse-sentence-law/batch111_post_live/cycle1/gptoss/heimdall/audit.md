# Heimdall audit

**Question:** Review this diff (pipeline/select_passages.py, pipeline/pinned.py). ORCHESTRATOR RULING 142 (3) (14:32 ET Nov 17), verbatim in part: "POST-LIVE STREAMS: do not wait for YouTube ... get MeC8YEmUx_w's media by another route and cut locally: try the full download of the post_live DASH stream (not --download-sections) ... whichever yields a file whose audio matches the transcript timings (check the offset against the word timings before trusting it, a post_live file can be shifted). If one works, make it the standing fallback for any 'post_live' source, with the offset check as a HARD guard". Measured today: a post_live section download comes back with ~5 s of picture, 0.023 s of audio, a 0 s container; the whole audio (format 140) and video (137) download fine; the render's decoder sits -0.10 s from the word pass's records on that whole stream and -0.09 s on a normal (not_live) video: the decoders' own bias, not a shift.
FACTS (unchanged code): _download_window(video_id, start_s, end_s, run_dir, pad=15) downloads [round(start-15), end+15] with yt-dlp --download-sections into run_dir/sources/<id>.mp4 and returns (path, dl_start), dl_start being provenance (cut words are located by TEXT, never by offset arithmetic); a cached file over 100 KB is a cache hit. pinned.acquire calls _download_window then _whisper_transcribe (word times relative to the file), and raises PinError (a hold) on failure. REPO is the repository root; the word pass's records are data/editorial/transcripts/<id>/windows/<lo>-<hi>.whisper_words_punct.json with source-clock word times.
Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.
CHECKS:
H1. Can a post_live source reach a lock WITHOUT the offset check, or pass it while shifted (median over 0.35 s) or on fewer than 10 aligned words or with no record?
H2. Can a NORMAL (not post_live) window change behaviour: a cache hit, a section with media, a failed download?
H3. Is the local cut placed at dl_start for both streams and dl_end - dl_start long; is the whole stream reused per video, never another video's?
H4. Can any input raise uncaught (ffprobe output, a malformed record file, a missing word time) in _has_media, _post_live_window, post_live_offset or acquire?

**Panel:** gptoss  |  **Cost:** $0.0009
## Consensus findings (majority of panel agrees)
- **[high] pipeline/pinned.py:0** post_live_offset uses re.sub and json.load without importing re or json, causing NameError. Also REPO is referenced but not defined in this file.
  - evidence: `def post_live_offset(vid, tr, offset):
    import glob
    import statistics
    from difflib import SequenceMatcher

    def norm(w):
        return re.sub(r"[^a-z0-9']", "", str(w).lower())
    mine`
  - fix: Add "import re" and "import json" at the top of the file (or within the function). Ensure REPO is defined globally or passed into the function. This will prevent NameError and allow the function to access the transcript files correctly.
  - raised by gptoss:F1; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
