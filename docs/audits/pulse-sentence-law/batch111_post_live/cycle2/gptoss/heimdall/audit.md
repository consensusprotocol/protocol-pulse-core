# Heimdall audit

**Question:** Review this diff (pipeline/select_passages.py, pipeline/pinned.py). ORCHESTRATOR RULING 142 (3) (14:32 ET Nov 17), verbatim in part: "POST-LIVE STREAMS: do not wait for YouTube ... get MeC8YEmUx_w's media by another route and cut locally: try the full download of the post_live DASH stream (not --download-sections) ... whichever yields a file whose audio matches the transcript timings (check the offset against the word timings before trusting it, a post_live file can be shifted). If one works, make it the standing fallback for any 'post_live' source, with the offset check as a HARD guard". Measured today: a post_live section download comes back with ~5 s of picture, 0.023 s of audio, a 0 s container; the whole audio (format 140) and video (137) download fine; the render's decoder sits -0.10 s from the word pass's records on that whole stream and -0.09 s on a normal (not_live) video: the decoders' own bias, not a shift.
FACTS (unchanged code): _download_window(video_id, start_s, end_s, run_dir, pad=15) downloads [round(start-15), end+15] with yt-dlp --download-sections into run_dir/sources/<id>.mp4 and returns (path, dl_start), dl_start being provenance (cut words are located by TEXT, never by offset arithmetic); a cached file over 100 KB is a cache hit. pinned.acquire calls _download_window then _whisper_transcribe (word times relative to the file), and raises PinError (a hold) on failure. REPO is the repository root; the word pass's records are data/editorial/transcripts/<id>/windows/<lo>-<hi>.whisper_words_punct.json with source-clock word times.
Cycle 2: try to BREAK it. Report ONLY a defect you can show with a CONCRETE file / stream / record state traced through the diff's code. Keep each "issue" under 80 words. If you cannot break it, answer PASS with no findings.
TARGETS:
T1. A shifted or wrong-video post_live source that the render would lock and cut.
T2. A normal source that now fails, or is replaced by a whole-stream cut.
T3. An exception, a cache reused across videos, or a file written outside the run's sources and the per-video cache.

**Panel:** gptoss  |  **Cost:** $0.0014
## Consensus findings (majority of panel agrees)
- **[high] pipeline/pinned.py:292** Missing import of re in post_live_offset, causing NameError when called.
  - evidence: `def post_live_offset(vid, tr, offset):\n    """RULING 142 (3): the HARD guard on a source cut from a post_live stream's whole download. The render's decode of the\n    window (word times + offset = th`
  - fix: Add "import re" at the top of the file or within the function before using re.sub.
  - raised by gptoss:F1; agree: gptoss
- **[high] pipeline/select_passages.py:129** _post_live_window passes cookies to yt-dlp using os.path.exists(cookies) which raises TypeError when cookies is None.
  - evidence: `def _post_live_window(video_id, dl_start, dl_end, out_path, cookies=None):\n    ...\n    for kind, fmt, name in (("audio", "bestaudio[acodec^=mp4a]/bestaudio", "audio.m4a"),\n                         `
  - fix: Change the cookie handling to check that cookies is not None before calling os.path.exists, e.g.:\n    if cookies and os.path.exists(cookies):\n        cmd += ["--cookies", cookies]
  - raised by gptoss:F2; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
