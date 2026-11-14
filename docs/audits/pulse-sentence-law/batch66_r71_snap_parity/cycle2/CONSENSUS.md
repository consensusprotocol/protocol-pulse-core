# Batch 66 cycle 2: one consensus finding, fixed
glm F1 [medium], agreed by qwen27b and glm: scene_changes_9x16 built the 9:16 graph without the input's colour, while
reframe_auto passes render_vertical._input_colour(seg_path), so prepare did not score literally the renderer's graph.
setparams is metadata only and the scene filter reads pixels, so the scores were not affected. But the ruling is
"one code path", so it is fixed.
FIX: scene_changes_9x16 passes render_vertical._input_colour(clip) to auto_graph, the call reframe_auto makes.
Re-run on the fix: the CPU tests 4 passed; the GPU0 must-fail on 0c68b589's held hook 1 passed (16:06 ET).
