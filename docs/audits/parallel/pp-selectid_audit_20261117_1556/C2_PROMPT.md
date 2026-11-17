# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1556
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 207 s finish=stop usage in 11390 / out 3647 usd_reported=0.000805 usd~0.089 (upper-bound price)

The code implements a robust fallback mechanism for fetching media from YouTube "post_live" streams, which are known to return empty files when using `yt-dlp --download-sections`. By downloading the whole stream once and cutting locally via `ffmpeg`, it ensures that QA gates (word checks and frame sheets) have the necessary data to operate without violating the "fail closed" principle.

### Analysis

1.  **Fail-Closed Integrity**: The implementation strictly adheres to the requirement that missing or corrupt media must not result in a "PASS". Both `audio_window` and `visual_pin.fetch` verify the duration of the resulting file against `MIN_SECTION_SHARE` (50% of the expected window). If the file is too short, it is deleted and an `OSError` is raised, which the pipeline interprets as a failure to measure.
2.  **Efficiency and Caching**: 
    *   It prioritizes the integrator's read-only cache (`POST_LIVE_CACHE`), reducing redundant downloads.
    *   It downloads the whole stream only once per video/tag per run, reusing the local file for subsequent windows.
    *   In `visual_pin.fetch`, it checks for the existence and validity of a previously created `.cut.mp4` before attempting a new whole-stream download.
3.  **Technical Correctness**:
    *   **FFmpeg**: The use of `-ss` before `-i` in `audio_window` ensures fast seeking on large files. The video scaling `scale=-2:'min(480,ih)'` correctly ensures the height is capped at 480p and the width remains even (required for `libx264`).
    *   **yt-dlp**: The format selection for audio (`bestaudio[acodec^=mp4a]/bestaudio`) is appropriate for the target `.m4a` extension.
    *   **Concurrency**: Since `out_dir` is typically unique per run in this pipeline, the local caching of whole streams is safe. The global `POST_LIVE_CACHE` is read-only.
4.  **Test Coverage**: The new test suite `test_ruling_142_post_live.py` is comprehensive. It stubs the external binaries and verifies all critical paths: empty sections triggering whole-stream downloads, cache priority, normal section preservation, and the deletion of invalid cuts.

### Findings

No [P0], [P1], or [P2] defects were found. The logic is sound and complies with all governing laws.

[P3] **Inline Import**: In `visual_pin.py`, `import transcript_truth as TT` is performed inside the `fetch` function. While this avoids potential circular dependencies and is functional, it is generally preferred to place imports at the top of the file. Given the architecture, this is a minor stylistic point.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 520 s finish=stop usage in 10615 / out 22846 usd_reported=0.016783 usd~0.375 (upper-bound price)



# Code Audit — pp-selectid / RULING 142 (3) post_live stream handling

## Scope reviewed
`pipeline/transcript_truth.py` (new `media_seconds`, `whole_stream`, modified `audio_window`), `pipeline/visual_pin.py` (modified `fetch`), `tests/package/test_ruling_142_post_live.py` (new, 8 tests).

---

## Findings

### [P1] `visual_pin.fetch` — early return skips duration validation of `.cut.mp4`

```python
cut = os.path.join(d, stem + ".cut.mp4")
if not have and os.path.exists(cut):
    return cut          # ← no media_seconds check
```

If a prior run's ffmpeg cut was interrupted (SIGKILL, OOM, disk full), a 0-byte or partially-written `.cut.mp4` remains on disk. The next call for the same span finds `have` empty (the section was also empty) and returns the corrupt file **without** the `TT.media_seconds(cut) >= TT.MIN_SECTION_SHARE * (end - start)` guard that the later code path applies. Downstream frame-sheet extraction reads garbage; the visual gate may pass on black/tear frames or fail in a way that is not attributable to the real cause.

The `import transcript_truth as TT` sits *after* this early return, so the fix requires hoisting the import (or the check) above it:

```python
import transcript_truth as TT   # move here (or to module level)
...
if not have and os.path.exists(cut) \
        and TT.media_seconds(cut) >= TT.MIN_SECTION_SHARE * (end - start):
    return cut
```

The test `test_an_empty_section_is_cut_from_the_whole_stream_and_kept` exercises the happy-path reuse (second call, no new subprocess) but never plants a 0-byte `.cut.mp4` before the first call, so the defect is untested.

---

### [P2] `whole_stream` — partial file from a failed yt-dlp download is silently reused

```python
if not find():
    subprocess.run(["yt-dlp", ...], check=True, timeout=1800, capture_output=True)
have = find()
```

If yt-dlp is killed mid-download (timeout, network drop, `check=True` → `CalledProcessError`), a partial file with the correct stem is left in `out_dir`. The **next** call to `whole_stream` for the same `video_id`/`tag` finds it via `find()` and returns it. The caller's `MIN_SECTION_SHARE` check catches windows that fall beyond the partial file's duration, but a window *within* the partial file's range produces a cut that passes the duration gate yet contains missing or corrupt DASH segments.

Suggested fix: write to a temp name and `os.rename` on success, or `try/except` around the yt-dlp call and `os.remove` the partial file on failure.

---

### [P2] `whole_stream` — no concurrency guard on the download

Two pipeline workers (or a retry) calling `whole_stream` for the same `video_id`/`tag` simultaneously both see `find()` empty, both launch yt-dlp, and both write to the same output path. The second write corrupts the first. The 30-minute timeout makes the window for collision realistic on a 2-GPU box running parallel story builds.

Suggested fix: a lock file (`<stem>.lock`) with `O_CREAT | O_EXCL`, or the temp-file + atomic-rename pattern above.

---

### [P3] `import transcript_truth as TT` inside `visual_pin.fetch`

The import is placed mid-function, after the early-return block. This is what makes the P1 fix awkward and is inconsistent with the rest of the module (which uses top-level imports). Move it to module level.

---

### [P3] `WHOLE` dict is incomplete / misleading

```python
WHOLE = {"audio": ("audio.m4a", "bestaudio[acodec^=mp4a]/bestaudio")}
```

Only the `"audio"` key exists, yet `whole_stream` is also called with `tag="video"` (from `visual_pin.fetch`, which passes its own `FORMAT` constant). The integrator-cache filename mapping for video is a separate hard-coded dict inside `whole_stream`. Consolidating both entries into `WHOLE` would make the single source of truth explicit and prevent a future edit from diverging the two.

---

### [P3] `media_seconds` timeout of 60 s

`ffprobe` on a local file reads the container header and returns in < 1 s. A 60 s timeout is a safety net against a hung NFS mount or a pathological file, but it also means a stuck probe blocks the pipeline for a full minute before the `except` fires. 10 s is ample and keeps the fail-closed path snappy.

---

## Items checked and found sound

| Question from the diff header | Verdict |
|---|---|
| (1) Can an empty or wrong window be returned as measured? | `audio_window` always re-cuts (no stale-wav path); the `MIN_SECTION_SHARE` guard on both the section and the whole-stream cut, plus `os.remove` + `OSError` on failure, closes the loop. **Exception:** the `visual_pin.fetch` early return (P1 above). |
| (2) Is a normal (non-post_live) video unaffected? | Yes. A section whose duration ≥ 50 % of the window takes the original `ffmpeg -i src → wav` / direct-return path. No new code runs. |
| (3) Cache and download paths (concurrent builds, partial downloads) | Integrator cache is read-on

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1556, the post_live fetch fallback on the builder's side)

SEATS ANSWERED: 2 of 3. gemma-4-31b-it: P0/P1 none. qwen3.8-27b: ONE P1, ACCEPTED AND FIXED. gpt-oss-20b: no answer.

## qwen [P1]: visual_pin.fetch's early return took a .cut.mp4 with no duration check (a cut interrupted by SIGKILL / OOM
## / a full disk would be returned partial) - FIXED, the only change from cycle 1 to cycle 2:
- Both cuts are now ATOMIC: ffmpeg writes <stem>.tmp.wav / <stem>.cut.tmp.mp4, and the file is renamed into place
  (os.replace) only after its duration passes MIN_SECTION_SHARE; an interrupted or empty cut never takes the final name.
- visual_pin.fetch's reuse path checks the cut's duration too (whole_cut: exists AND >= half the span), with the
  transcript_truth import hoisted above it.
- New test: a 0-second .cut.mp4 planted before the first call is never returned; the span is cut again, whole. The test
  stub follows renames. Mutation P10 (the reuse check reverted to a bare exists) is killed.
Suites after the fix: test_ruling_142_post_live 9, test_angles + test_visual_pin with it 50 passed; mutations 9 of 9.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1556/C2_STEP.diff (276 lines)
```
   1 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
   2 | index 02f1207..f7c7fe3 100644
   3 | --- a/pipeline/transcript_truth.py
   4 | +++ b/pipeline/transcript_truth.py
   5 | @@ -29,6 +29,41 @@ PAUSE_MIN_S = 0.700          # ruling 38: a measured pause this long with no rec
   6 |  CANON_RUN = 6                # recogniser words read together at an edge, so a spoken number is one canonical token
   7 |  
   8 |  
   9 | +MIN_SECTION_SHARE = 0.5   # RULING 142 (3) on this side: a fetched section under half its window's length is empty
  10 | +POST_LIVE_CACHE = "/home/ultron/protocol_pulse/data/post_live_cache"   # the integrator's whole streams (batch 111;
  11 | +#   read only): <video_id>/audio.m4a (format 140) and video.mp4 (137), used first when they hold media
  12 | +WHOLE = {"audio": ("audio.m4a", "bestaudio[acodec^=mp4a]/bestaudio")}   # the integrator's audio format (15:5x ET)
  13 | +
  14 | +
  15 | +def media_seconds(path):
  16 | +    """A media file's duration in seconds (ffprobe); 0.0 when it has none or cannot be read (a post_live stream's section
  17 | +    download gives a file of 0 s: MeC8YEmUx_w, 15:5x ET Nov 17, 258 bytes)."""
  18 | +    try:
  19 | +        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
  20 | +                             capture_output=True, text=True, timeout=60).stdout.strip()
  21 | +        return float(out or 0.0)
  22 | +    except (OSError, ValueError, subprocess.SubprocessError):
  23 | +        return 0.0
  24 | +
  25 | +
  26 | +def whole_stream(video_id, fmt, out_dir, tag):
  27 | +    """RULING 142 (3) on this side (the integrator's batch 111 does the same for the render): a post_live YouTube stream
  28 | +    (DASH segments only) gives an EMPTY section download, so its whole stream in `fmt` is fetched ONCE per video and tag,
  29 | +    kept in out_dir as <video_id>.whole-<tag>.<ext>, and every window is cut from it locally. -> the file's path."""
  30 | +    theirs = os.path.join(POST_LIVE_CACHE, video_id, {"audio": "audio.m4a", "video": "video.mp4"}.get(tag, "-"))
  31 | +    if os.path.isfile(theirs) and media_seconds(theirs) > 0:   # the integrator's copy of the same stream: read only
  32 | +        return theirs
  33 | +    stem = f"{video_id}.whole-{tag}"
  34 | +    find = lambda: [f for f in sorted(os.listdir(out_dir)) if os.path.splitext(f)[0] == stem]
  35 | +    if not find():
  36 | +        subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", fmt, "-o", os.path.join(out_dir, stem + ".%(ext)s"),
  37 | +                        f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=1800, capture_output=True)
  38 | +    have = find()
  39 | +    if not have:
  40 | +        raise OSError(f"the whole stream of {video_id} ({fmt}) was not fetched")
  41 | +    return os.path.join(out_dir, have[0])
  42 | +
  43 | +
  44 |  def audio_window(video_id, start, end, out_dir, pad=PAD_S, pad_before=PAD_BEFORE_S):
  45 |      """WAV (16 kHz mono) of [start - pad_before, end + pad] (clamped at the video head), fetched with yt-dlp's
  46 |      download sections -> (path, the window's real start in video seconds)."""
  47 | @@ -42,8 +77,19 @@ def audio_window(video_id, start, end, out_dir, pad=PAD_S, pad_before=PAD_BEFORE
  48 |      subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", "bestaudio", "--download-sections", f"*{a:.2f}-{b:.2f}",
  49 |                      "--force-keyframes-at-cuts", "-o", base + ".%(ext)s", f"https://www.youtube.com/watch?v={video_id}"],
  50 |                     check=True, timeout=300, capture_output=True)
  51 | -    src = next(os.path.join(out_dir, f) for f in sorted(os.listdir(out_dir))
  52 | -               if os.path.splitext(f)[0] == stem and not f.endswith(".wav"))       # exact stem: never a longer id
  53 | +    src = next((os.path.join(out_dir, f) for f in sorted(os.listdir(out_dir))
  54 | +                if os.path.splitext(f)[0] == stem and not f.endswith(".wav")), None)   # exact stem: never a longer id
  55 | +    if src is None or media_seconds(src) < MIN_SECTION_SHARE * (b - a):   # RULING 142 (3): a post_live stream's empty
  56 | +        whole = whole_stream(video_id, WHOLE["audio"][1], out_dir, "audio")   # (or absent) section: the whole audio
  57 | +        #   stream once, the window cut here
  58 | +        tmp = base + ".tmp.wav"                       # renamed into place only whole: an interrupted cut is never cached
  59 | +        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a:.3f}", "-i", whole, "-t", f"{b - a:.3f}",
  60 | +                        "-ac", "1", "-ar", "16000", tmp], check=True, timeout=300)
  61 | +        if media_seconds(tmp) < MIN_SECTION_SHARE * (b - a):            # still empty: never cached, never a pass
  62 | +            os.remove(tmp)
  63 | +            raise OSError(f"{video_id} {a:.2f}-{b:.2f}: no audio in the section or the whole stream")
  64 | +        os.replace(tmp, wav)
  65 | +        return wav, a
  66 |      subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True,
  67 |                     timeout=120)
  68 |      return wav, a
  69 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
  70 | index 24ed7a1..3153ca7 100644
  71 | --- a/pipeline/visual_pin.py
  72 | +++ b/pipeline/visual_pin.py
  73 | @@ -149,14 +149,32 @@ def fetch(video_id, start, end, work_dir):
  74 |      os.makedirs(d, exist_ok=True)
  75 |      stem = f"{video_id}_{int(start * 1000)}_{int(end * 1000)}"
  76 |      have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
  77 | +    import transcript_truth as TT
  78 | +    cut = os.path.join(d, stem + ".cut.mp4")                    # RULING 142 (3): a post_live span cut before, whole
  79 | +    whole_cut = lambda: os.path.exists(cut) and TT.media_seconds(cut) >= TT.MIN_SECTION_SHARE * (end - start)
  80 | +    if not have and whole_cut():                                # (audit 20261117_1556 C1 qwen: never a partial one)
  81 | +        return cut
  82 |      if not have:
  83 |          subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", FORMAT, "--download-sections",
  84 |                          f"*{start:.2f}-{end:.2f}", "--force-keyframes-at-cuts", "-o", os.path.join(d, stem + ".%(ext)s"),
  85 |                          f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=300, capture_output=True)
  86 |          have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
  87 | -    if not have:
  88 | -        raise OSError(f"no video fetched for {stem}")
  89 | -    return os.path.join(d, have[0])
  90 | +    path = os.path.join(d, have[0]) if have else None
  91 | +    if path is not None and TT.media_seconds(path) >= TT.MIN_SECTION_SHARE * (end - start):
  92 | +        return path
  93 | +    #   RULING 142 (3): a post_live stream's empty (or absent) section: the whole
  94 | +    if not whole_cut():                                                # stream once (<= 480p), the span cut here
  95 | +        whole = TT.whole_stream(video_id, FORMAT, d, "video")
  96 | +        tmp = os.path.join(d, stem + ".cut.tmp.mp4")                  # renamed into place only whole
  97 | +        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", whole, "-t",
  98 | +                        f"{end - start:.3f}", "-an", "-vf", "scale=-2:'min(480,ih)'", "-c:v", "libx264", "-preset",
  99 | +                        "veryfast", "-crf", "28", tmp],
 100 | +                       check=True, timeout=300)
 101 | +        if TT.media_seconds(tmp) < TT.MIN_SECTION_SHARE * (end - start):
 102 | +            os.remove(tmp)
 103 | +            raise OSError(f"no video in the section or the whole stream for {stem}")
 104 | +        os.replace(tmp, cut)
 105 | +    return cut
 106 |  
 107 |  
 108 |  def sheet(video, start, end, work_dir):
 109 | diff --git a/tests/package/test_ruling_142_post_live.py b/tests/package/test_ruling_142_post_live.py
 110 | new file mode 100644
 111 | index 0000000..211f40d
 112 | --- /dev/null
 113 | +++ b/tests/package/test_ruling_142_post_live.py
 114 | @@ -0,0 +1,161 @@
 115 | +#!/usr/bin/env python3
 116 | +"""RULING 142 (3) on the builder's side (orchestrator 14:32 ET Nov 17): a post_live YouTube stream (DASH segments only)
 117 | +gives an EMPTY section download (MeC8YEmUx_w, 15:5x ET: 258 bytes, 0 s), so this side's word check
 118 | +(transcript_truth.audio_window) and frame sheet (visual_pin.fetch) would fail closed on every clip of it. They now fetch
 119 | +the whole stream once per video (the integrator's read-only cache first, batch 111), cut the window locally, and still
 120 | +fail closed when even that holds no media. Offline: yt-dlp, ffmpeg and the duration probe are stubbed."""
 121 | +import os
 122 | +import sys
 123 | +import tempfile
 124 | +import unittest
 125 | +from unittest import mock
 126 | +
 127 | +HERE = os.path.dirname(os.path.abspath(__file__))
 128 | +REPO = os.path.dirname(os.path.dirname(HERE))
 129 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 130 | +import transcript_truth as TT  # noqa: E402
 131 | +import visual_pin as VP  # noqa: E402
 132 | +
 133 | +REAL_REPLACE = os.replace
 134 | +
 135 | +
 136 | +class Media:
 137 | +    """yt-dlp / ffmpeg stand-ins that write the files they would, and a duration table for media_seconds."""
 138 | +
 139 | +    def __init__(self, section_s=0.0, cut_s=None, write_section=True):
 140 | +        self.calls, self.section_s, self.cut_s, self.write_section = [], section_s, cut_s, write_section
 141 | +        self.seconds = {}
 142 | +
 143 | +    def run(self, cmd, **kw):
 144 | +        self.calls.append(list(cmd))
 145 | +        if cmd[0] == "yt-dlp":
 146 | +            out = cmd[cmd.index("-o") + 1].replace("%(ext)s", "m4a" if "bestaudio" in cmd[cmd.index("-f") + 1]
 147 | +                                                   else "mp4")
 148 | +            if "--download-sections" in cmd:
 149 | +                if self.write_section:
 150 | +                    open(out, "w").write("x")
 151 | +                    self.seconds[out] = self.section_s
 152 | +            else:
 153 | +                open(out, "w").write("whole")
 154 | +                self.seconds[out] = 5700.0
 155 | +        elif cmd[0] == "ffmpeg":
 156 | +            out = cmd[-1]
 157 | +            open(out, "w").write("cut")
 158 | +            if "-ss" in cmd:                          # a cut from a whole stream
 159 | +                self.seconds[out] = float(cmd[cmd.index("-t") + 1]) if self.cut_s is None else self.cut_s
 160 | +            else:
 161 | +                self.seconds[out] = 15.0
 162 | +        return mock.Mock(returncode=0, stdout="", stderr="")
 163 | +
 164 | +    def secs(self, path):
 165 | +        return self.seconds.get(path, 0.0)
 166 | +
 167 | +    def replace(self, src, dst):                       # a cut renamed into place keeps its duration
 168 | +        REAL_REPLACE(src, dst)
 169 | +        self.seconds[dst] = self.seconds.pop(src, 0.0)
 170 | +
 171 | +    def wholes(self):
 172 | +        return [c for c in self.calls if c[0] == "yt-dlp" and "--download-sections" not in c]
 173 | +
 174 | +
 175 | +class Base(unittest.TestCase):
 176 | +    def setUp(self):
 177 | +        self.tmp = tempfile.TemporaryDirectory()
 178 | +        self.d, self.cache = os.path.join(self.tmp.name, "w"), os.path.join(self.tmp.name, "theirs")
 179 | +        os.makedirs(self.d)
 180 | +
 181 | +    def tearDown(self):
 182 | +        self.tmp.cleanup()
 183 | +
 184 | +    def patched(self, m):
 185 | +        return [mock.patch.object(TT.subprocess, "run", m.run), mock.patch.object(TT, "media_seconds", m.secs),
 186 | +                mock.patch.object(TT, "POST_LIVE_CACHE", self.cache), mock.patch.object(os, "replace", m.replace)]
 187 | +
 188 | +    def go(self, m, fn):
 189 | +        ps = self.patched(m)
 190 | +        for p in ps:
 191 | +            p.start()
 192 | +        try:
 193 | +            return fn()
 194 | +        finally:
 195 | +            for p in ps:
 196 | +                p.stop()
 197 | +
 198 | +
 199 | +class TestTheWordChecksWindow(Base):
 200 | +    def test_an_empty_section_is_cut_from_the_whole_stream_fetched_once(self):
 201 | +        m = Media(section_s=0.0)
 202 | +        wav, a = self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 203 | +        self.assertEqual((a, m.secs(wav) > 0), (96.0, True))
 204 | +        self.assertEqual(len(m.wholes()), 1)
 205 | +        cut = [c for c in m.calls if c[0] == "ffmpeg"][-1]
 206 | +        self.assertEqual((cut[cut.index("-ss") + 1], cut[cut.index("-t") + 1]), ("96.000", "15.500"))
 207 | +        self.go(m, lambda: TT.audio_window("vid", 200.0, 210.0, self.d))         # another window: the same stream
 208 | +        self.assertEqual(len(m.wholes()), 1)
 209 | +
 210 | +    def test_the_integrators_cached_stream_is_read_first(self):
 211 | +        os.makedirs(os.path.join(self.cache, "vid"))
 212 | +        theirs = os.path.join(self.cache, "vid", "audio.m4a")
 213 | +        open(theirs, "w").write("whole")
 214 | +        m = Media(section_s=0.0)
 215 | +        m.seconds[theirs] = 5700.0
 216 | +        self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 217 | +        self.assertEqual(m.wholes(), [])                                           # no download of our own
 218 | +        self.assertIn(theirs, [c for c in m.calls if c[0] == "ffmpeg"][-1])
 219 | +
 220 | +    def test_no_section_file_at_all_takes_the_whole_stream_too(self):
 221 | +        m = Media(write_section=False)
 222 | +        wav, _ = self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 223 | +        self.assertTrue(m.secs(wav) > 0)
 224 | +        self.assertEqual(len(m.wholes()), 1)
 225 | +
 226 | +    def test_a_normal_section_is_used_as_before(self):
 227 | +        m = Media(section_s=15.5)
 228 | +        self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 229 | +        self.assertEqual(m.wholes(), [])
 230 | +        self.assertNotIn("-ss", [c for c in m.calls if c[0] == "ffmpeg"][-1])
 231 | +
 232 | +    def test_a_cut_with_no_audio_fails_closed_and_is_never_kept(self):
 233 | +        m = Media(section_s=0.0, cut_s=0.0)
 234 | +        with self.assertRaises(OSError):
 235 | +            self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
 236 | +        self.assertFalse([f for f in os.listdir(self.d) if f.endswith(".wav")])
 237 | +
 238 | +
 239 | +class TestTheFrameSheetsVideo(Base):
 240 | +    def test_an_empty_section_is_cut_from_the_whole_stream_and_kept(self):
 241 | +        m = Media(section_s=0.0)
 242 | +        v = self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
 243 | +        self.assertTrue(v.endswith(".cut.mp4") and m.secs(v) > 0, v)
 244 | +        cut = [c for c in m.calls if c[0] == "ffmpeg"][-1]
 245 | +        self.assertEqual((cut[cut.index("-ss") + 1], cut[cut.index("-t") + 1]), ("100.000", "10.000"))
 246 | +        self.assertIn("scale=-2:'min(480,ih)'", cut)                               # the sheet's <= 480p
 247 | +        n = len(m.calls)
 248 | +        self.assertEqual(self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d)), v)   # cut once, then kept
 249 | +        self.assertEqual(len(m.calls), n)
 250 | +
 251 | +    def test_a_partial_cut_left_behind_is_never_returned(self):
 252 | +        """Audit 20261117_1556 C1 (qwen): an interrupted earlier cut must not stand for the span."""
 253 | +        os.makedirs(os.path.join(self.d, "visual"))
 254 | +        bad = os.path.join(self.d, "visual", "vid_100000_110000.cut.mp4")
 255 | +        open(bad, "w").write("partial")                                  # 0 s by the duration table
 256 | +        m = Media(section_s=0.0)
 257 | +        v = self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
 258 | +        self.assertEqual((v, m.secs(v)), (bad, 10.0))                        # re-cut, whole
 259 | +        self.assertTrue([c for c in m.calls if c[0] == "ffmpeg"])
 260 | +
 261 | +    def test_a_normal_section_is_returned_as_before(self):
 262 | +        m = Media(section_s=10.0)
 263 | +        v = self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
 264 | +        self.assertTrue(v.endswith("vid_100000_110000.mp4"), v)
 265 | +        self.assertEqual(m.wholes(), [])
 266 | +
 267 | +    def test_a_cut_with_no_picture_fails_closed_and_is_never_kept(self):
 268 | +        m = Media(section_s=0.0, cut_s=0.0)
 269 | +        with self.assertRaises(OSError):
 270 | +            self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
 271 | +        self.assertFalse(os.path.exists(os.path.join(self.d, "visual", "vid_100000_110000.cut.mp4")))
 272 | +
 273 | +
 274 | +if __name__ == "__main__":
 275 | +    unittest.main()
 276 | 
```

---

pp-selectid: RULING 142 (3) (orchestrator 14:32 ET Nov 17: post_live streams, "do not wait for YouTube") ON THE BUILDER'S
SIDE. The integrator's batch 111 made the render and its lock pre-check fetch a post_live stream whole and cut locally
(its read-only cache /home/ultron/protocol_pulse/data/post_live_cache/<video>/audio.m4a, video.mp4). This side's two
fetchers still used yt-dlp --download-sections, which on the post_live stream MeC8YEmUx_w gives an EMPTY file (tested
15:5x ET: 258 bytes, 0 s): the word check (transcript_truth.audio_window, L-v 2 + CUTTABLE, HARD) and the frame sheet
(visual_pin.fetch, the visual check, HARD) would fail closed on every clip of it, and every 3-channel story today needs
one. Files: pipeline/transcript_truth.py, pipeline/visual_pin.py, tests/package/test_ruling_142_post_live.py (new).

THE CHANGE:
(a) transcript_truth: media_seconds(path) (ffprobe; 0.0 when unreadable); whole_stream(video_id, fmt, out_dir, tag):
    the integrator's cached whole stream first when it holds media (read only), else ONE yt-dlp download of the whole
    stream per video and tag into out_dir, reused after. audio_window: when the section file is ABSENT or shorter than
    MIN_SECTION_SHARE (0.5) of its window, the window is cut from the whole audio stream (ffmpeg -ss <start> -i whole -t
    <len>, 16 kHz mono); a cut that still holds under half the window raises OSError and leaves no wav (fail closed: the
    word check reads it as not measured). A normal section takes the unchanged path.
(b) visual_pin.fetch: the same for the <= 480p frame clip: an absent or empty section is replaced by a cut from the
    whole video stream (re-encoded, scaled to at most 480 lines, no audio), kept as <stem>.cut.mp4 and reused; an empty
    cut raises and is removed. A normal section is returned as before.
    No offset check of our own: the integrator cuts audio and video from the same DASH stream timestamps, and its HARD
    offset guard checks the audio clock; a shift here makes the word check fail closed (its words would not match).

EVIDENCE: a real run (free) on MeC8YEmUx_w 5409.96-5420.32 from the integrator's cache: the word check's window 15.86 s,
the frame clip 10.38 s. TESTS (8, offline, yt-dlp / ffmpeg / ffprobe stubbed): an empty section cut from the whole
stream fetched once; the integrator's cache read first; no section file at all; a normal section unchanged; an empty
audio cut fails closed and is not kept; the video cut is kept and reused, scaled to 480; a normal video section
unchanged; an empty video cut fails closed and is removed. Mutations: 8 of 8 killed.

PLEASE CHECK: (1) can an empty or wrong window ever be returned as measured? (2) is a normal (non post_live) video
unaffected? (3) the cache and download paths (concurrent builds, partial downloads); (4) the tests.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
