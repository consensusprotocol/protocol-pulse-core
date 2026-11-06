# segment_v2e — READY

## Change
- clip_01 (Bitcoin Magazine, Pxrak-iMT0g) cut_out: 249.80 -> 249.37
- M19a valley rule: cut at valley END of first qualifying RMS valley
  - Valley centre: 249.35, valley end: 249.37
  - Valley depth: 19.2 dB (threshold: >= 12 dB)
  - Valley width: 40 ms (threshold: >= 40 ms)
- 30ms audio fade-out (M19 law)
- "So" onset leak eliminated (v2d had it at 249.80 cut)
- Faster-whisper medium (float16, cuda, vad off) for G3/G3b/G13
- G3c reimplemented with M19a relative rule (speech_median - 12 dB)
- Alimiter -3.0 dBFS (was -5.0) to fix G5 LUFS

## Durations
- 16:9: 67.625s (segment_v2/out/segment_v2e.mp4)
- 9:16: 67.584s (segment_v2/out/segment_vertical_v2e.mp4)
- Parity: 0.041s (threshold 0.25s) PASS

## clip_01 Acoustic Detail
- Source: Pxrak-iMT0g.mp4
- Faster-whisper: "magnitude." 248.94-249.30
- Speech median: -19.1 dBFS (last 2s of source)
- Valley threshold: -31.1 dBFS (median - 12)
- Valley: 249.33-249.37 (40ms), depth 19.2 dB, centre 249.35, end 249.37
- Onset: 249.42 (next sentence)
- cut_in: 238.55, cut_out: 249.37, duration: 10.82s
- Fade: 30ms fade-out (M19)

## Gate Tables

### 16:9 Gates (ALL PASS)
| Gate | Result | Notes |
|------|--------|-------|
| G1 Voice | PASS | sim=0.87/0.84 (assembled VO) |
| G2 Watermark | PASS | 6 samples, all >800 red px |
| G3 Cuts | PASS | all words found (faster-whisper medium) |
| G3b OutClean | PASS | hook "thinks" found, no leaks |
| G3c AcouTail | PASS | all clips valley << threshold |
| G4 Faces | PASS | all clips >= 1 face |
| G5 Tech | PASS | -14.7 LUFS, -2.4 dBFS true peak |
| G6 Pre-roll | PASS | vo onset 0.975s (assembled VO) |
| G10 Chyron | PASS | no chyron-channel shots |
| G13 VOAudible | PASS | 100%/86% overlap (faster-whisper medium) |

### 9:16 Gates (ALL PASS)
| Gate | Result | Notes |
|------|--------|-------|
| G1 Voice | PASS | sim=0.87/0.84 (assembled VO) |
| G2 Watermark | PASS | 6 samples |
| G3 Cuts | PASS | faster-whisper medium |
| G3b OutClean | PASS | all clips clean |
| G3c AcouTail | PASS | M19a relative rule, all clips pass |
| G4 Faces | PASS | all clips >= 1 face |
| G5 Tech | PASS | -14.7 LUFS, -2.3 dBFS true peak |
| G6 Pre-roll | PASS | vo onset 0.975s (assembled VO) |
| G10 Chyron | PASS | no chyron-channel shots |
| G13 VOAudible | PASS | faster-whisper medium |

## Files
- segment_v2/out/segment_v2e.mp4 (16:9, 67.625s)
- segment_v2/out/segment_vertical_v2e.mp4 (9:16, 67.584s)
- segment_v2/qa_v1/final_clip_01.mp4 (v2e, 10.867s, 30ms fade-out)
- segment_v2/qa_v1/gate_results_16x9.json
- segment_v2/qa_v1/gate_results_9x16.json

## Status
- 16:9 render: COMPLETE — ALL GATES PASS
- 9:16 render: COMPLETE — ALL GATES PASS
- M19a valley rule: VERIFIED on clip_01 source
- Faster-whisper medium: G3, G3b, G13
- "So" onset elimination: VERIFIED via G3b (no leak)
