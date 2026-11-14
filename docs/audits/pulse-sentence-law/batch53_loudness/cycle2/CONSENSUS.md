# Batch 53 cycle 2: consensus and what was done

- C1 [high], "frames() crashes: int() on the duration". Rejected with evidence. ffprobe prints the stream fields in its own order, codec_type,duration,nb_frames: the earlier failure output reads "audio,12.010000,564". The parse t, d, n gives (int(n), float(d)) = (frames, duration), and the test passes (8 passed).
- C2 [medium], the 9:16 audio is not verified as the corrected 16:9 audio: implemented. audio_md5 (framemd5 over the audio packets) of both temp files must be equal before anything is replaced; otherwise the rendered finals are kept. Test: test_a_vertical_whose_audio_is_not_the_corrected_audio_is_never_promoted. On pin #1's real finals the two are identical.
- qwen F2 (1 vote), an OSError between the two replaces: implemented. _replace_pair keeps the originals as hard links and puts BOTH back if either move fails; OSError is caught. Test: test_a_failed_second_replace_puts_both_originals_back.
- glm F3 (1 vote): the off-target test now asserts that no temp file is left.
- glm F2 (1 vote), dynamic normalization not enforced as linear: the ruling asks for a two-pass correction to target, and dynamic is recorded when ffmpeg needs it. On pin #1 every frame count and duration is unchanged.
