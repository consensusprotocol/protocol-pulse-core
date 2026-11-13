# Batch 53 cycle 1: no consensus findings. The single votes were checked on pin #1's REAL finals.

- glm F1 [high, 1 vote], duration growth and AV drift from the audio re-encode. Measured on copies of pin #1's real
  finals after the correction: video 1549 frames, 64.5417 s; audio 3022 frames, 64.448 s; both identical before and
  after, in both formats. check_av_sync is -0.021333 before and after. On the synthetic pair the audio duration
  moved 10 ms (12.010 -> 12.000 s; padding), less than one AAC frame, with every frame kept. Tested:
  test_the_correction_keeps_every_frame_count_and_duration.
- The same real run found a defect no reviewer named, now fixed. A linear +1.21 dB was predicted to give -2.08 dBTP,
  but re-measured -1.64 dBTP after the AAC encode. The re-measure check correctly KEPT the rendered finals. Pass 2 now
  aims CODEC_TP_MARGIN = 0.5 dB under the ceiling (TP -2.5). On pin #1's real finals the result is: corrected,
  normalization "dynamic", -14.13 LUFS and -2.31 dBTP in both formats; ebur128 (G5's measure) I -14.1 LUFS, peak
  -2.3.
- glm F2 [medium, 1 vote], the regex: loudnorm prints exactly one JSON object per run, and the regex requires input_i
  inside it. normalization_type stays a string by design (measure() converts every other key to float).
- glm F3 [medium, 1 vote], the in-tolerance test re-ran on a corrected pair: rewritten. The pair now measures in
  tolerance, and pass 2 raises if it is called. The files stay byte-identical.
