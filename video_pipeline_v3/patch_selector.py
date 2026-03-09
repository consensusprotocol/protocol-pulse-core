#!/usr/bin/env python3
"""Patch clip_selector.py with dedup rules."""
path = '/home/ultron/protocol_pulse/video_pipeline_v3/clip_selector.py'
with open(path) as f:
    txt = f.read()

old = """RULES:
- Pick from DIFFERENT channels when possible (variety matters)
- Each clip should be 20-40 seconds long. The best moment, not the full segment.
- Rank 1 = most dramatic/important (this becomes the cold open teaser)
- The timestamps in the transcripts are approximate — pick ranges that capture complete thoughts
- Avoid dead air, filler words, or mid-sentence cuts"""

new = """RULES:
- Pick from DIFFERENT channels when possible (variety matters)
- NEVER select more than 1 clip from the same YouTube video (unique video_id per clip)
- NEVER select 2 clips from the same channel back-to-back — vary the source
- If forced to use the same channel twice, clips must be different videos on different topics
- Each clip should be 20-40 seconds long (the best moment, not the full segment)
- Rank 1 = most dramatic/important (this becomes the cold open teaser)
- The timestamps in the transcripts are approximate — pick ranges that capture complete thoughts
- Avoid dead air, filler words, or mid-sentence cuts
- Sort clips to maximize channel variety: no same channel appearing consecutively"""

if old in txt:
    txt = txt.replace(old, new, 1)
    print('SUCCESS: Dedup rules added to SELECTION_PROMPT')
else:
    # Try with different dash character
    old2 = old.replace('\u2014', '--')
    if old2 in txt:
        txt = txt.replace(old2, new, 1)
        print('SUCCESS: Dedup rules added (dash variant)')
    else:
        print('WARNING: RULES block not found exactly. Trying line-by-line...')
        if 'Pick from DIFFERENT channels when possible' in txt:
            # Find the RULES: line and add after it
            lines = txt.split('\n')
            new_lines = []
            for line in lines:
                new_lines.append(line)
                if '- Avoid dead air, filler words, or mid-sentence cuts' in line:
                    new_lines.append("- NEVER select more than 1 clip from the same YouTube video (unique video_id per clip)")
                    new_lines.append("- NEVER select 2 clips from the same channel back-to-back — vary the source")
                    new_lines.append("- Sort clips to maximize channel variety: no same channel appearing consecutively")
                    print('SUCCESS: Dedup rules appended after existing rules')
            txt = '\n'.join(new_lines)
        else:
            print('ERROR: Could not find insertion point')

with open(path, 'w') as f:
    f.write(txt)
print('clip_selector.py saved')
