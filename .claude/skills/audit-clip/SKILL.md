---
name: audit-clip
description: Technical audit on a rendered video. Checks AV sync, loudness, true peak, black frames, bitrate.
invocation: user
---
# Video Audit Skill
Run on $ARGUMENTS (video path):
1. FFprobe: codec, resolution, fps, bitrate, duration
2. Loudness: ffmpeg loudnorm (target -14 LUFS)
3. True peak: must be below -1.5 dBTP
4. Black frames: ffmpeg blackdetect
5. AV sync: packet-level offset
6. Report: pass/fail table
