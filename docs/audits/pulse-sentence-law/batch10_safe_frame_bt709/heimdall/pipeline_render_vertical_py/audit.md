# Heimdall audit

**Question:** Render fix: the 9:16 safe-frame filter (LETTERBOX_VF, used by reframe_auto for screen / uncertain shots) runs colorlevels in RGB; ffmpeg 4.4 converts the background YUV->RGB->YUV with the same BT.601 matrix both ways (values kept) but the overlay output loses the colour-matrix tag, so a 9:16 part opening on a safe frame - and the concatenated final, which inherits the first part's tags - came out color_space=unknown (Nov 11 recut; v2f's parts are all bt709); decoders then read the whole video as BT.601 (G9 measured 14.47 instead of 14.74). Fix: append setparams=colorspace=bt709 to LETTERBOX_VF (frame metadata only, no pixel change; parts not opening on a safe frame keep the tag their first frame already carries). Test: reframe_auto on a bt709 clip keeps bt709 when opening on a screen shot (fails on the old filter) and when opening on a speaker crop. Find real defects only: wrong matrix on any pixels, a path still dropping the tag, Law 22 (the frozen v2f re-render must stay byte-identical; v2f's 9:16 parts never open on a safe frame). (this chunk: pipeline/render_vertical.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0057
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- deepseek:F1 [high] Unconditionally forces BT.709 colorspace on all LETTERBOX_VF outputs, even when the source is not BT.709 (e.g., BT.601). This mislabels the pixels, causing decoders to apply the wrong matrix and produce incorrect colors. (agree: 1)

## Added in cross-examination (not voted on)
- none
