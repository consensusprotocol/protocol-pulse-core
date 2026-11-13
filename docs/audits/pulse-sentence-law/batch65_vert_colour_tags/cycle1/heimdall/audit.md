# Heimdall audit

**Question:** Batch 65 = the 9:16 colour-tag fix (law Section 2 format lock; ruling 26 (a) "tag every final explicitly", which ruling 30 left out because it took the BT.601 source to be the only cause). G9 (the tail luma gate) measures through RGB, so a final's colour tags enter its number. Its floor and its measure are NOT changed here.
Measured (Nov 13, four runs, ffprobe of every 9:16 part): every 9:16 part is made by render_vertical.reframe_auto (layout 'auto' in all four runs). A part whose shot plan includes a stack2 shot (split, crop, scale, vstack, pad) comes out with all four tags unknown (range, space, transfer, primaries). A single-crop part keeps its source's tags. A safe-frame part already re-declares its matrix (the Nov 11 fix). The 9:16 final takes its FIRST part's tags:
- run 191409: the hook opens on stack2, the final is untagged, G9 9:16 13.6 vs 14.73 FAIL, with every source BT.709 tv;
- run 031328 (the medley): the hook opens on stack2, untagged, 13.6 FAIL;
- run 165629: the hook is single (bt709), the final bt709, 14.8 PASS (although its clip_02 part was untagged);
- run 054035: the hook was BT.601 (smpte170m), 14.5 FAIL (ruling 30's case, converted at prepare now).
The change: _input_matrix (colorspace only) becomes _input_colour. It probes the input's color_range, color_primaries, color_transfer and color_space, keeps only whitelisted values, and returns setparams options. reframe_auto appends ",setparams=<those>" after EVERY shot (it did so only after the safe frame, and only for colorspace). Metadata only: setparams rewrites frame properties, not pixels.
Tests: test_safe_frame_colour.py. The NVENC class gains test_a_part_opening_on_a_stack2_keeps_bt709_and_its_range (run on GPU0 under the lease: must fail on the old code, pass on the new). New CPU tests: every shot's chain ends on the input's colour, and the probe keeps known values only.
FIND: a pixel change (anything but tag metadata); a wrong or untruthful tag (a declared colour the pixels are not in); a filtergraph that breaks for any shot class (single, stack2, stack3, screen / safe frame) or for several shots in one part; a tag still lost on some 9:16 path the final can open on; a change to G9 or its floor; a test that does not test what it claims. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 4 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0022
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] The stack2 GPU test's 'must fail on the old code' claim is not enforced: it only asserts the new behaviour, so it cannot itself prove the old code failed (no regression check against the old path). (agree: 1)
- glm:F2 [low] The CPU graph test mocks subprocess.run globally, so the ffprobe call inside _input_colour is also mocked via the _input_colour patch — fine — but the encode/ffmpeg command's returncode Mock(returncode=0) means the test would pass even if the real filtergraph were rejected by ffmpeg; it only checks the graph string, not that ffmpeg accepts it. (agree: 1)

## Added in cross-examination (not voted on)
- none
