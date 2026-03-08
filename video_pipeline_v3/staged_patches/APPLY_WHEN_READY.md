# Staged Patches — X Spaces Integration

These patches integrate X Spaces segments into the video render pipeline.
They modify assembler.py and daily_run.py which are render-path files.

## IMPORTANT: Do NOT apply during an active render session.

Wait for the apex2 render to complete. Then:

```bash
cd ~/protocol_pulse/video_pipeline_v3
patch -p1 < staged_patches/01_daily_run_spaces_injection.py.patch
patch -p1 < staged_patches/02_assembler_spaces_type.py.patch
bash regression_test.sh
```

## What these patches do:

### 01_daily_run_spaces_injection.py.patch
- Imports `get_latest_spaces_segment` from spaces_pipeline
- After script segments are collected, checks for fresh X Spaces data
- Injects the segment before the outro if available

### 02_assembler_spaces_type.py.patch
- Handles `"x_spaces"` segment type in the assembler
- Maps to `data_segment` scene with appropriate eyebrow/tag
- Supports `context_only_segment` flag for different labeling
