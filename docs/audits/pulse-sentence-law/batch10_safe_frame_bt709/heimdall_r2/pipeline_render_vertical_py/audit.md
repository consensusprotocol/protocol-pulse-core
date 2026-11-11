# Heimdall audit

**Question:** Second pass after batch 10 (deepseek F1: a hard bt709 tag could mislabel a non-709 source). Now reframe_auto probes its input's color_space once; when a shot uses the safe-frame filter (LETTERBOX_VF, colorlevels in RGB drops the matrix tag in ffmpeg 4.4 while keeping the YUV values) and the input declares a known matrix, it appends setparams=colorspace=<that matrix>; an untagged input stays untagged; no pixel changes; other shot classes unchanged. Report only real defects you can quote.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0063
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
