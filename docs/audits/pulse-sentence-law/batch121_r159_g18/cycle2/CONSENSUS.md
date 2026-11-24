# Batch 121, cycle 2 (the strongest case against the change)
Seats: qwen27b (high): PASS (0.85), no findings. gemma (medium): PASS. gpt-oss (medium): FAIL, 2 findings, "mock and W
are not imported in test_word_diff.py": DISPROVED, an artefact of the hunk view: the file imports both at its top
(`from unittest import mock`, `import word_diff as W`), and the suite runs green (19 tests, its 4 GPU-only errors as on
the live code). No change.
