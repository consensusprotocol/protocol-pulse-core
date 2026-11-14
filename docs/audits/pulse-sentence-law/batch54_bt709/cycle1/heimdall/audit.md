# Heimdall audit

**Question:** Batch 54 = RULING 30 (orchestrator 2026-11-13 '01:55'), verbatim: "G9 tail with a BT.601 source in both formats: this is the measured cause ruling 26 waited for. Fix at prepare: convert BT.601 sources to BT.709 with correct matrix and tag so the tail measures the same as a 709 source. Add a test with this hook as the fixture. The G9 floor stays."
Measured facts (ruling 26):
- pin #1's and the medley's untagged finals both trace to one BT.601 source, Sjb6lUiL0m4: tv / smpte170m MATRIX / bt709 primaries and transfer;
- their luma plane equals that of the 709 sources;
- G9 reads through RGB (ffmpeg PNG with its default decode, then OpenCV gray), so the tag and the chroma moved its number.
The change, run_fresh.to_bt709(run_dir, video_ids), called at the start of stage_prepare before any clip is prepared (run_isolated.prerender_clips is a protected file and is unchanged):
- a source whose color_space is smpte170m or bt470bg is re-encoded with the colorspace filter:
  - output space / primaries / trc bt709, range tv;
  - input ispace from the source; iprimaries / itrc from the source when declared, else the matrix's own;
- lossless libx264 qp 0, -vsync 0 (every frame timestamp passed through; ffmpeg 4.4 has no -fps_mode), audio copied;
- output tags -colorspace / -color_primaries / -color_trc bt709, -color_range tv;
- the original is kept as run_dir/sources_bt601/<vid>.mp4. It is outside sources/ because record_assets lists every file in sources/ as a video;
- both sha256 values and the filter go to PROVENANCE["bt709_conversion"];
- a failed encode raises Hold and leaves the source as it was;
- 709 and untagged sources are never touched.
Measured on a 4 s span of the real hook, original against converted:
- the same 97 frames and duration; the same sorted frame times; byte-identical audio;
- RGB with each file decoded by its own matrix: mean abs diff 0.30;
- G9's decode path: 99.49 / 99.54.
Tests: 3 (that fixture; 709 and untagged untouched; a failed conversion holds).
FIND:
- a wrong matrix / primaries / transfer mapping (e.g. bt470bg's input options; a source whose primaries are not declared);
- a frame dropped, duplicated or retimed (VFR sources with -vsync 0);
- the cut times no longer matching the converted source;
- the lossless claim false (qp 0 with yuv420p);
- the original lost on failure;
- a later stage reading the wrong file;
- tests that do not test what they claim.
Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0023
## Consensus findings (majority of panel agrees)
- **[low] pipeline/test_bt709.py:96** the failure test's fake ffmpeg also intercepts the ffprobe call? No — it passes non-ffmpeg commands through, but it returns CompletedProcess(cmd,1,'',stderr) with 4 positional args while subprocess.run normally returns 5 fields (returncode, args, stdout, stderr, others); the code only reads .returncode and .stderr, so it works; however the mock also replaces the *setup* ffmpeg? No, setup runs before the patch. The test does not exercise the os.replace/keep path, so 'leaves the source as it was' is only checked for the untouched original, not that sources_bt601/ is not half-created — acceptable since the failure happens before any replace.
  - evidence: `if r.returncode != 0 or not os.path.exists(tmp): ... raise Hold(...)`
  - fix: none required
  - raised by glm:F2; agree: qwen27b, glm
- **[low] pipeline/run_fresh.py:762** to_bt709 runs before prerender_clips as ruled, but if a later re-run of stage_prepare happens on the same run_dir the already-converted (now bt709-tagged) source is skipped, so PROVENANCE['bt709_conversion'] is overwritten with {} and the provenance of the first conversion is lost on resume.
  - evidence: `run.prov["bt709_conversion"] = to_bt709(run.dir, [c["video_id"] for c in cuts])`
  - fix: merge: run.prov["bt709_conversion"] = {**run.prov.get("bt709_conversion", {}), **to_bt709(...)}
  - raised by glm:F3; agree: qwen27b, glm

## Raised but not agreed
- qwen27b:F1 [high] Incorrect input transfer characteristics (itrc) mapping for BT.601 sources. The code defaults `itrc` to the `color_space` (e.g., 'smpte170m' or 'bt470bg') if `color_transfer` is not declared. However, 'smpte170m' and 'bt470bg' are matrix coefficients, not valid transfer characteristics (TRC) for the ffmpeg `colorspace` filter. The correct default TRC for BT.601 is 'bt601'. Passing an invalid TRC will cause the ffmpeg conversion to fail or produce incorrect results, violating the requirement to convert with the correct matrix and tag. (agree: 1)
- qwen27b:F2 [medium] Incorrect input primaries (iprimaries) mapping. The code defaults `ip` to the `color_space` if `color_primaries` is not declared. 'smpte170m' and 'bt470bg' are not valid primary color spaces (e.g., 'bt709', 'bt470m', 'smpte170m' is sometimes used as a primary alias in some contexts but strictly it's a matrix; however, ffmpeg's colorspace filter expects valid primaries like 'bt470m' or 'smpte170m' is actually a valid primary name in ffmpeg? No, 'smpte170m' is a matrix. The primary for BT.601 is typically 'bt470m' or 'smpte170m' is accepted as a primary in some ffmpeg versions? Let's check. FFmpeg `colorspace` filter `iprimaries` accepts 'bt709', 'smpte170m', 'smpte240m', 'bt470m', 'bt2020', etc. Actually, 'smpte170m' IS a valid primary name in ffmpeg (it refers to the SMPTE 170M primaries). So this might be okay. BUT, the issue is that if the source is `bt470bg`, the primary is `bt470m`. The code sets `ip` to `bt470bg` which is NOT a valid primary name in ffmpeg (it's a matrix). This will cause a failure for `bt470bg` sources. (agree: 1)
- glm:F1 [low] bt470bg sources get their input primaries/trc defaulted to the matrix name, but bt470bg's own primaries are bt470bg while its transfer is bt470bg too in ffmpeg's naming — actually ffmpeg's colorspace filter accepts these names, so the mapping is valid; the residual risk is only that a source declaring primaries but not transfer (or vice versa) mixes declared and matrix-defaulted values, which the ruling permits ('iprimaries / itrc from the source when declared, else the matrix's own'). (agree: 1)

## Added in cross-examination (not voted on)
- glm: [low] irange=tv is hardcoded; a BT.601 source tagged pc (full range) is converted with wrong input range, shifting the picture
