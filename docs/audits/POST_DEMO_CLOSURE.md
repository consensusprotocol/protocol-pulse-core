# POST-DEMO CLOSURE LIST (PBX, 2026-11-06 07:07 ET). Frozen until after the demo: no production changes before the meeting.
Reference: docs/references/REFERENCE_v2f.md. Every item: test that fails on the old code, regression run against the v2f reference pair (must stay byte-identical or visually/aurally equivalent with evidence), one commit each.
1. Wire G14 and G15 into the normal production gate runner (both aspects). No manual-only required gates.
2. Fix the generic cutter regressions: internal energy dip != word boundary. Must-fail fixtures: 'thinks' (hook, cutter gave 9.13 inside the word), 'themselves' (clip_03 in, 997.25 mid-word), 'magnitude' (249.37 inside the 't' closure). Combine acoustic valleys with word/phoneme boundaries.
3. Renderer fails closed on wrong final duration, resolution, fps, audio format or timeline contract (the 05:23 run reported COMPLETE on a 27.29 s 1280x720 file).
4. Intermediate clip contract enforced before expensive rendering: 1920x1080, 24 fps, 48 kHz stereo, exact intended duration/cuts, expected 30 ms out / 20 ms in fades.
5. M12 no silent fallback: any vertical crop/layout failure STOPS ("reframe failed ... using original" must be impossible).
6. Do NOT change the approved 9:16 layout behavior from the v2f reference unless a future regression test proves a real defect.
7. Resolve QA-rule conflicts without weakening gates, PBX approval required for any threshold/rule change: G8 sharpness relative to source-camera sharpness; G9 tail rule that allows the approved new outro ending on black (asset-identity check, not a brightness floor).
8. Preserve the new outro behavior exactly in both formats.
9. Pulse Studio becomes only a control surface for ONE canonical production orchestrator (today it launches python3 -m pipeline.run --keyword, not the hardened path). No separate Studio/Claude/demo pipelines.
10. Performance: shout-out/plate generation used ~1 CPU core with GPU0 idle. After correctness is frozen, profile; cache/pre-render reusable assets or move frame/compositing work to FFmpeg/GPU. No visual change without regression coverage.
11. GPU1 stays quarantined; production on CUDA_VISIBLE_DEVICES=0 until GPU1 is separately proven healthy.
12. Both v2f outputs are the approved demo/reference pair.
13. Repeatability: one reference episode does not prove arbitrary topics. After the demo, run fresh unrelated topics through the same canonical path with no code edits between runs.
