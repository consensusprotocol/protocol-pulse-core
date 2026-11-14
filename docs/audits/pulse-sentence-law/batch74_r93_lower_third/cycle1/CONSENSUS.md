# Batch 74 cycle 1: ONE consensus finding, implemented (panel qwen27b, glm; Grok alongside)
- [high; qwen27b F1 + glm F2, both agree; Grok F1 the same] single_crop on a 'single' shot with no face samples: np.median([]) raises.
  The case is not reachable through classify: a 'single' run always holds at least one sample originally labelled single, which has a face; the pre-existing face_cx median above it would raise first. The guard is cheap.
  FIX: single_crop returns (None, {"why": "no face samples"}); render_vertical ignores a non-int crop_x and keeps its face-centred x. Test: test_no_face_samples_gives_no_x_and_the_renderer_keeps_its_own.
Raised, not agreed, checked:
- glm F1 "a face-unsafe crop after clamping": clamping only shrinks [lo, hi], and any x inside it satisfies x + cw >= right + margin and x <= left - margin. No change.
- glm F3 "the range can invert when the face box is wider than the crop": then nothing is clear and today's x stays, which the ruling allows (no clear crop exists). No change.
- Grok F2 "with no clear x, today's x can violate the margin": today's x is the existing face-centred crop; the ruling changes the crop only where a clear one exists. No change.
