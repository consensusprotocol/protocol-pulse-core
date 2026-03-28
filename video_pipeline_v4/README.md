# Video Pipeline V4 — Remotion-Based Parallel Pipeline

A/B testing infrastructure. V4 runs alongside V3. **V3 is never modified.**

## Architecture

- V4 replaces `assembler.py` ONLY — everything else (TTS, script gen, grading, content fetching) stays in V3
- Remotion composition engine renders the same episode spec JSON that V3 reads
- Output: 1920x1080, 30fps CFR, h264, CRF-17, AAC 48kHz stereo (per PIPELINE_LAWS)

## Quick Start

### Render V4 only

```bash
python3 video_pipeline_v4/producer_v4.py <episode_spec.json>
```

Output: `video_pipeline_v4/output/YYYY-MM-DD/pulse_check_v4_YYYYMMDD.mp4`

### Run A/B test

```bash
python3 ab_test.py <episode_spec.json>
```

This renders V4 and tells you where both V3 and V4 outputs are for comparison.

### Grade

```bash
# Grade V3
python3 video_pipeline_v3/gemini_grade.py <v3_output.mp4>

# Grade V4 (uses same grader)
python3 video_pipeline_v4/grade_v4.py <v4_output.mp4>
```

### Preview in browser

```bash
cd video_pipeline_v4/remotion
npx remotion studio
```

## Promotion to Production

1. Achieve 10 consecutive Grade A renders with V4
2. Update overnight loop to call `producer_v4.py` instead of V3 assembler
3. V3 remains as rollback target — never delete it

## Rollback

The overnight loop calls V3 by default. To rollback:
- Simply stop calling `producer_v4.py`
- V3 is untouched and always available

## Scene Components

| Scene | File | Duration |
|-------|------|----------|
| Cold Open | `scenes/ColdOpen.tsx` | 4s (120 frames) |
| PIP | `scenes/PipScene.tsx` | Variable |
| Intelligence | `scenes/IntelligenceScene.tsx` | 30-45s |
| Social Post | `scenes/SocialPostScene.tsx` | 8-15s |
| X Spaces | `scenes/XSpacesScene.tsx` | Up to 45s |
| Narration | `scenes/NarrationScene.tsx` | Variable |
| Outro | `scenes/OutroScene.tsx` | Matches outro.mp4 |

## Transitions

- **GlitchCut**: 6 frames (0.2s), red scan lines + whoosh SFX, dedup within 60 frames
- **FadeToBlack**: 15 frames (0.5s), cold open entry only

## Brand Colors (PIPELINE_LAWS Section 10)

- Primary Red: `#CC0000`
- Black: `#0A0A0A`
- White: `#FFFFFF`
- **Blue/cyan/purple are PERMANENTLY BANNED**
