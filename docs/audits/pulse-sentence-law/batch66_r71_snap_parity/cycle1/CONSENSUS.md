# Batch 66 cycle 1: no consensus findings
glm F1 [medium], single vote: "the 9:16 scene-score regex drops the last frame's score, so a punch-in on the final frame
can never be snapped in the 9:16 path". Disproved by measurement. The hook clip has 407 frames (0-406), and its LAST frame
is the punch-in. scene_changes_9x16 on it returned [(71, 0.4876), (127, 0.3139), (155, 0.3170), (245, 0.5714),
(306, 0.7131), (336, 1.0), (406, 0.3172)]: frame 406's score is read. The GPU0 must-fail test snaps exactly that frame.
No change.
