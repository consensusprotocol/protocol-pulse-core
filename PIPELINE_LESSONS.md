# Pipeline Lessons Learned


## Iteration 1 — 2026-03-12 06:33 — Grade F (34/100)

### Failures:
- TTS service for host 'Eryn' is non-functional (HTTP 404, voice_id not found), resulting in silent audio for all her line
- The TTS fallback system also failed, leading to a complete inability to generate audio for one of two hosts.
- The final video contains 12 multi-second freeze frames, a catastrophic visual error.
- The audio mix is clipping (True Peak at 0.4 dBTP), a violation of broadcast audio standards.
- Multiple long silence gaps are present, destroying the episode's pacing and watchability.
- Audio clipping: true peak 999dBTP (limit -1.0)
- Silent gaps: 2 gaps >2s detected
- Low bitrate: 2.77Mbps (min 3.0)

### Fixes applied:
- CC fix session iter1 applied

### Key insight:
Carry forward: TTS service for host 'Eryn' is non-functional (HTTP 404, voice_id not found), resulting in silent audio for all her line; The TTS fallback system also failed, leading to a complete inability to generate audio for one of two hosts.

---

## Iteration 2 — 2026-03-12 07:01 — Grade F (57/100)

### Failures:
- CRITICAL FAILURE: True peak at +0.4 dBTP exceeds the 0 dBFS limit, causing audio
- CRITICAL FAILURE: 12 freeze frames detected. The video is unwatchable.
- CRITICAL FAILURE: Host Eryn's voice failed to render, replaced by long silences.
- CRITICAL FAILURE: The 12 freeze frames are severe visual artifacts that make the
- CRITICAL FAILURE: Catastrophic failure of the TTS system for one host results in
- TTS system failed for host 'Eryn', replacing all her lines with long silences.
- 12 freeze frames (>1s) detected, rendering the video unwatchable.
- Audio is clipping with a true peak of +0.4 dBTP, which is above the 0 dBFS limit.

### Fixes applied:
- CC fix session iter2 applied

### Key insight:
Carry forward: CRITICAL FAILURE: True peak at +0.4 dBTP exceeds the 0 dBFS limit, causing audio; CRITICAL FAILURE: 12 freeze frames detected. The video is unwatchable.

---

## Iteration 3 — 2026-03-12 07:29 — Grade F (38/100)

### Failures:
- CRITICAL FAILURE: True peak is at 0.4 dBFS according to the render log QC. This
- CRITICAL FAILURE: 12 freeze frames detected. This is an unacceptably high number
- CRITICAL FAILURE: The render log shows a complete failure to generate audio for
- CRITICAL FAILURE: The video is riddled with artifacts, including 12 freeze frame
- CRITICAL FAILURE: One host's entire audio track is missing and replaced with sil
- true_peak_check: Audio is clipping at +0.4 dBFS.
- freeze_check: 12 video freeze frames detected, making the video unwatchable.
- host_authenticity: Host 'Eryn' has no audio; all lines were replaced with silence due to a TTS API failure.

### Fixes applied:
- CC fix session iter3 applied

### Key insight:
Carry forward: CRITICAL FAILURE: True peak is at 0.4 dBFS according to the render log QC. This; CRITICAL FAILURE: 12 freeze frames detected. This is an unacceptably high number

---

## Iteration 4 — 2026-03-12 07:58 — Grade F (41/100)

### Failures:
- CRITICAL FAILURE: Loudness analysis returned 'None LUFS'. This indicates a catas
- CRITICAL FAILURE: True Peak analysis returned 'None dBFS'. This confirms a funda
- CRITICAL FAILURE: 12 freeze frames were detected. This is an unacceptable number
- CRITICAL FAILURE: One host is entirely missing. There is no banter or interactio
- CRITICAL FAILURE: The presence of 12 freeze frames is a severe visual artifactin
- CRITICAL FAILURE: The audio is fundamentally broken. One host's voice is missing
- Host 'Eryn' TTS generation failed completely due to a 'voice_not_found' API error, resulting in her lines being replaced
- 12 video freeze frames (>1s) were detected, rendering the visual experience unacceptable.

### Fixes applied:
- CC fix session iter4 applied

### Key insight:
Carry forward: CRITICAL FAILURE: Loudness analysis returned 'None LUFS'. This indicates a catas; CRITICAL FAILURE: True Peak analysis returned 'None dBFS'. This confirms a funda

---

## Iteration 5 — 2026-03-12 09:10 — Grade F (48/100)

### Failures:
- CRITICAL FAILURE. Post-render QC log shows a true peak of 0.4 dBTP, which is ove
- CRITICAL FAILURE. 12 freeze frames detected. This is an unwatchable number of er
- CRITICAL FAILURE. One of the two hosts is entirely silent. The core format of th
- CRITICAL FAILURE. The 12 freeze frames are severe visual artifacts that make the
- CRITICAL FAILURE. Half of the narration is missing and replaced with silence. Th
- true_peak_check: Audio is clipping at +0.4 dBTP, which is unacceptable.
- freeze_check: 12 freeze frames render the video unwatchable.
- audio_quality: Catastrophic TTS failure resulted in one host being completely silent.

### Fixes applied:
- CC fix session iter5 applied

### Key insight:
Carry forward: CRITICAL FAILURE. Post-render QC log shows a true peak of 0.4 dBTP, which is ove; CRITICAL FAILURE. 12 freeze frames detected. This is an unwatchable number of er

---

## Iteration 6 — 2026-03-12 10:56 — Grade F (34/100)

### Failures:
- Catastrophic TTS failure for host 'Eryn' due to an invalid ElevenLabs voice_id, resulting in all her lines being replace
- TTS fallback mechanism failed because the 'pyttsx3' module is not installed, indicating a severe system configuration er
- 15 freeze frames detected, rendering the video visually unwatchable.
- Audio is clipping, with a true peak of +0.4 dBTP, which is a broadcast-critical error.
- Multiple long silence gaps (5 reported >2.0s) are present due to the TTS failure, destroying the episode's pacing.
- Audio clipping: true peak 999dBTP (limit -1.0)
- Silent gaps: 1 gaps >2s detected
- Duration out of range: 652s (target 400-550s)

### Fixes applied:
- CC fix session iter6 applied

### Key insight:
Carry forward: Catastrophic TTS failure for host 'Eryn' due to an invalid ElevenLabs voice_id, resulting in all her lines being replace; TTS fallback mechanism failed because the 'pyttsx3' module is not installed, indicating a severe system configuration er

---

## Iteration 7 — 2026-03-12 12:29 — Grade F (38/100)

### Failures:
- CRITICAL FAILURE: Forensic data shows no LUFS value calculated, indicating a mea
- CRITICAL FAILURE: The QC log shows a true peak of +0.4 dBTP. Any value over 0 dB
- CRITICAL FAILURE: 11 freeze frames detected. This is an unacceptable number of v
- CRITICAL FAILURE: The render logs show a complete failure to generate audio for
- CRITICAL FAILURE: The video is riddled with artifacts, specifically the 11 freez
- CRITICAL FAILURE: Half of the narration is missing entirely. This is a total fai
- TTS Failure: All lines for host 'Eryn' failed to render, resulting in long, unwatchable gaps of silence.
- Freeze Frames: 11 instances of frozen video were detected, making the viewing experience impossible.

### Fixes applied:
- CC fix session iter7 applied

### Key insight:
Carry forward: CRITICAL FAILURE: Forensic data shows no LUFS value calculated, indicating a mea; CRITICAL FAILURE: The QC log shows a true peak of +0.4 dBTP. Any value over 0 dB

---
