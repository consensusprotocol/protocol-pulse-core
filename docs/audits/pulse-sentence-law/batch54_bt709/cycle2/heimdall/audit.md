# Heimdall audit

**Question:** Batch 54 cycle 2 (verification). Cycle 1 implemented: the provenance merges on a re-run; irange follows the source (pc / tv); the matrix-default names proven by real conversions (see CONSENSUS.md).

Batch 54 = RULING 30 (orchestrator 2026-11-13 '01:55'), verbatim: "G9 tail with a BT.601 source in both formats: this is the measured cause ruling 26 waited for. Fix at prepare: convert BT.601 sources to BT.709 with correct matrix and tag so the tail measures the same as a 709 source. Add a test with this hook as the fixture. The G9 floor stays."
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
FIND: anything still open; a wrong mapping; a frame retimed; the original lost; a later stage reading the wrong file; a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0016
## Consensus findings (majority of panel agrees)
- **[low] pipeline/test_bt709.py:0** The failed-conversion test's fail_ffmpeg also breaks the ffprobe call inside to_bt709? No — it only fails ffmpeg, but it also fails the *setup* ffmpeg? No, setup runs before the patch; however the mock returns CompletedProcess(cmd,1,...) for the *conversion* ffmpeg only, and the test then asserts the source is unchanged — but to_bt709 raises Hold before os.replace, so the assertion passes trivially; the test never verifies sources_bt601/ was not created
  - evidence: `self.assertEqual([n for n in os.listdir(os.path.join(self.run, "sources")) if n != "v601.mp4"], [])`
  - fix: Also assert not os.path.exists(os.path.join(self.run, 'sources_bt601'))
  - raised by glm:F3; agree: qwen27b, glm

## Raised but not agreed
- glm:F1 [low] On a re-run, the provenance record's 'from' tags are overwritten with the converted file's tags, so the original BT.601 matrix is lost from PROVENANCE['bt709_conversion'] (agree: 1)

## Added in cross-examination (not voted on)
- glm: [low] media_tags returns {} on ffprobe failure or a stream with no tags, and to_bt709 then treats the source as untagged and skips it — but if the stream exists yet ffprobe fails transiently, a 601 source silently skips conversion with no provenance note
