# Batch 54 cycle 1: consensus and what was done

- C2 [low], a re-run of stage_prepare overwrote the conversion record with {}: implemented, the records now merge.
- C1 [low], the failure test does not exercise the replace path: no fix needed. The failure happens before any os.replace, and the test asserts that the source is byte-identical and that nothing else was written.
- glm, cross-examination, irange hard-coded to tv: implemented. A full-range (pc) source converts with irange=pc, and the output is tv.
- qwen F1 / F2 [1 vote], "smpte170m / bt470bg are not valid trc / primaries names": rejected by a REAL conversion. ffmpeg 4.4's colorspace filter accepts both as iprimaries and itrc; for an undeclared transfer they are the matrix's own BT.601-525 / -625 values. Test: test_a_source_declaring_only_its_bt601_matrix_converts_with_the_matrix_defaults (smpte170m tv, bt470bg tv, smpte170m pc: each converts and tags bt709).
