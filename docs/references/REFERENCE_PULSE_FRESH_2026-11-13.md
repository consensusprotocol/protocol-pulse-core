# REFERENCE: the first full pass, 2026-11-13 (PBX approved; published as a YouTube Short; orchestrator order '18:20' 1)

Pin 0c68b589 (the builder's ruling-67 re-seal of 61fd55d0). Run pinned_20261113_211048, on HEAD 3395c61f. Every
release gate passed in both formats: run_fresh exit 0, attestation ALL_PASS. The run was delivered on the pass path
at 17:12 ET (Telegram 67844-67848).
PBX at 18:10 ET, verbatim as the orchestrator relayed it: "I just reviewed the video that passed at 5 o'clock and I'm
genuinely impressed! Excellent work! ... Go ahead and publish that ... throw it up on YouTube".
The orchestrator published the 9:16 at 18:10:52 ET: https://www.youtube.com/watch?v=9Sj7PpFNeCA, 'No CEO. No
Compromise. No Committee.' (references/pulse_fresh_2026-11-13/YT_POST.json).

This is the fifth protected reference, after:
- the frozen v2f;
- the approved preview;
- the review video;
- the L-y medley.

It is the first one built end to end by the pipeline from fresh moments, and the first published.

## What it is a reference for
- THE FIRST FULL PASS: every release gate PASS, both formats, no waivers. The code paths of the day are in it:
  - ruling 17 and its attested re-seal (ruling 67);
  - the 9:16 colour tags (G9);
  - ruling 71's two-format shot snap (the hook's frame 406 held on 405, G19).
- SHAPE (law L-y): hook -> clip -> clip, ONE closing line after the last clip, the shout-out, the outro. Both concat
  manifests (seconds):

  | Segment | From | To |
  |---|---|---|
  | hook (Simply Bitcoin) | 0.000 | 16.958 |
  | clip_01 (CNBC Television) | 16.958 | 31.375 |
  | clip_02 (Scott Melker) | 31.375 | 40.708 |
  | the closing line (vo_bridge_01, after clip 2) | 40.708 | 49.375 |
  | shout-out | 49.375 | 58.500 |
  | outro | 58.500 | 62.958 |

## Its three spans are DELIVERED (orchestrator order '18:20' 2; ruling 76 b): no build uses them again
| Role | Channel | Video | Span (source seconds) |
|---|---|---|---|
| hook | Simply Bitcoin | DcUbBkyeh9M | 236.688-253.308 |
| clip | CNBC Television | GXWj2JO9bz8 | 124.157-138.097 |
| clip | Scott Melker | mKNAcOFMYD4 | 755.454-764.214 |

## The 12-hour rule
PBX published this video as an exception: it "would have missed a window" and is still relevant. Going forward the
12 h rule (rulings 76 / 77) stands, and PBX wants the next render from the next 5-10 hour window.

## How it is protected (pipeline/regression.sh step 9, as step 8 for the medley)
- Every file is exactly as SHA256SUMS: 430 files, the media included (pipeline/check_reference_manifest.py).
- The tracked files equal tag ref-pulse-fresh-2026-11-13.
- Its decisions reproduce with the current code (pipeline/check_medley_reference.py on this directory): the shape
  from its PIN, the selection locks from its frozen transcripts, the cuts within one 10 ms hop, the flow and junctions,
  and the 9:16 shot layout. Measured at 18:16 ET: REPRODUCED. clip_01's OUT recomputes 29.50 against the recorded 29.51,
  within the one-hop tolerance; that offset existed before this reference.
- The reproduction writes nothing: the manifest is checked again after it.
