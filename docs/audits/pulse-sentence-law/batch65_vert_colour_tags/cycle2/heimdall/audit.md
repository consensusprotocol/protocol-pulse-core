# Heimdall audit

**Question:** Batch 65 CYCLE 2 (cycle 1: no consensus findings; the diff is unchanged) = the 9:16 colour-tag fix (law Section 2 format lock; ruling 26 (a) "tag every final explicitly", which ruling 30 left out because it took the BT.601 source to be the only cause). G9 (the tail luma gate) measures through RGB, so a final's colour tags enter its number. Its floor and its measure are NOT changed here.
Measured (Nov 13, four runs, ffprobe of every 9:16 part): every 9:16 part is made by render_vertical.reframe_auto (layout 'auto' in all four runs). A part whose shot plan includes a stack2 shot (split, crop, scale, vstack, pad) comes out with all four tags unknown (range, space, transfer, primaries). A single-crop part keeps its source's tags. A safe-frame part already re-declares its matrix (the Nov 11 fix). The 9:16 final takes its FIRST part's tags:
- run 191409: the hook opens on stack2, the final is untagged, G9 9:16 13.6 vs 14.73 FAIL, with every source BT.709 tv;
- run 031328 (the medley): the hook opens on stack2, untagged, 13.6 FAIL;
- run 165629: the hook is single (bt709), the final bt709, 14.8 PASS (although its clip_02 part was untagged);
- run 054035: the hook was BT.601 (smpte170m), 14.5 FAIL (ruling 30's case, converted at prepare now).
The change: _input_matrix (colorspace only) becomes _input_colour. It probes the input's color_range, color_primaries, color_transfer and color_space, keeps only whitelisted values, and returns setparams options. reframe_auto appends ",setparams=<those>" after EVERY shot (it did so only after the safe frame, and only for colorspace). Metadata only: setparams rewrites frame properties, not pixels.
Tests: test_safe_frame_colour.py. The NVENC class gains test_a_part_opening_on_a_stack2_keeps_bt709_and_its_range (run on GPU0 under the lease: must fail on the old code, pass on the new). New CPU tests: every shot's chain ends on the input's colour, and the probe keeps known values only.
FIND: a pixel change (anything but tag metadata); a wrong or untruthful tag (a declared colour the pixels are not in); a filtergraph that breaks for any shot class (single, stack2, stack3, screen / safe frame) or for several shots in one part; a tag still lost on some 9:16 path the final can open on; a change to G9 or its floor; a test that does not test what it claims. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 4 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0020
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [medium] The GPU test's mock of subprocess.run swallows the real encode, so the test does not test what it claims (a part opening on a stack2 keeps bt709 and its range through a real render); it only checks the filtergraph string. The class docstring says 'run on GPU0 under the lease: must fail on the old code, pass on the new', but the mocked run never encodes, so the old code would also pass this test (the old code's graph also ends each shot's chain with setsar=1:1, just without the setparams, and the assertion only checks the new code's expected substring). (agree: 1)
- glm:F2 [low] The probe test's second case asserts primaries=bt470bg and colorspace=smpte170m survive, but the third case (all-unknown) returns '' and the first case's expected string orders range first; the dict-iteration order of _KNOWN (Python 3.7+ insertion order) makes the output order deterministic, but the test hard-codes that order, coupling the test to _KNOWN's declaration order rather than to the documented contract ('known values only'). (agree: 1)

## Added in cross-examination (not voted on)
- glm: [low] _input_colour parses ffprobe output by whitespace-splitting lines; a value containing a space or an unexpected extra key would corrupt the dict, and any ffprobe failure (nonzero returncode) is silently treated as no colour, so the part renders untagged with no warning — the very failure mode this fix targets can recur silently.
