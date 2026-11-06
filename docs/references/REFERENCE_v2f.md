# PROTECTED PRODUCTION REFERENCE: v2f (approved by PBX 2026-11-06 07:07 ET)

Status: APPROVED, BOTH FORMATS. Do not modify. PBX's direct review supersedes the earlier "9:16 not demo-ready" label: the 9:16 is approved.
Frozen copy (read-only): references/v2f_2026-11-06/ (run, brand assets, code snapshot, run log, toolchain, pip freeze, SHA256SUMS). Original run dir runs/v2f_20261106_111034 is also read-only.

## Reproduce
- Revision: 7465f0d625861e1060dde70c25c59e4ebdd97087 (tag ref-v2f-2026-11-06)
- Command: cd ~/protocol_pulse/pipeline && CUDA_VISIBLE_DEVICES=0 python3 run_isolated.py --clip1-out 249.63 --allow-clip1-gap-ms 20
- GPU: RTX 4090 GPU0 only (GPU1 quarantined). Encoder h264_nvenc.
- Acoustic cutter NOT used: cuts pinned (references/v2f_2026-11-06/run/CUTS_PINNED.md).

## Pinned cut table (source seconds)
| clip | source | channel | cut_in | cut_out |
|---|---|---|---|---|
| hook | RBFN4CB60To | The Bitcoin Layer | 0.00 | 9.52 |
| clip_01 | Pxrak-iMT0g | Bitcoin Magazine | 238.55 | 249.63 |
| clip_02 | RBFN4CB60To | The Bitcoin Layer | 624.63 | 636.72 |
| clip_03 | QCgW8RlTu5Q | BTC Sessions | 998.00 | 1011.80 |
clip_01 out 249.63: no silence before "So" (onset ~249.65-249.67); one-time 20 ms acceptance by PBX/GPT/Grok listening A/B (249.67 carries the "S"). The 60 ms rule is unchanged.

## Input hashes (sha256)
- RBFN4CB60To.mp4 cfb2c57aebbfd9d41fb98694fa8adbfa5011bf880c9364ababd9dd49b2125460
- Pxrak-iMT0g.mp4 57ba9c51544bbbe0449c3914c95b83448886db6d35cf400bf55ecce7d0f1354a
- QCgW8RlTu5Q.mp4 a1f760077bf02cf1725f9bf68ef1ee7f23dfa192868a71b1cd73fdedb5b65bd4
- vo_intro_pp2_v1.wav ce576ec2373bbea0efaf0c96e0916cca3feec3153a0f1411a4808de3c6a95290
- vo_bridge_01_pp2_v1.wav 6721610b1b69f20425e59df79bac3f96dfa167b8e08b5805935e9bbcec7d29a3
- vo_signoff_pp2_v1.wav 8796e840c666c0e74e8d31a9d3d61c540ba3c8d183f8832cc94b3209a9462b78
- PBX outro 16:9 master 7c2cc7ae6efa9b276144f51b33290b190120470a36541e977f52c25b1e614e58 (conformed b8a402947c42017e7f448fba05306cad2dc052eb5c9097415582c1624d9fefc6)
- PBX outro 9:16 master 48d114daab327aa9695cdebf25fec3ca5186113322fd29feedbcb035f2e421f9 (conformed 1af99ca7c21a72fc085ea66f99a264fb2360b72f250b68c88b1a4caef0042883, -8.7 dB)
All other files: references/v2f_2026-11-06/SHA256SUMS.

## Approved outputs
- 16:9 segment.mp4 sha256 472938134157b649626c19d6e1d6e4b4221323ade3003c1487e8e3d03207cefd (Telegram msg 67222)
- 9:16 segment_vertical.mp4 sha256 5545a261feedd8c1bb402a99691331fe7e588e7dcde1a34381458be44a5d6c57 (Telegram msg 67223)

## Measured facts (orchestrator, on these exact files)
- Both timelines 67.542 s (G14c parity 0 ms). 1920x1080 / 1080x1920, 24 fps, 48 kHz stereo.
- G14: 29 sampled points, A/V offset 0 ms at every point, frame_sim 0.957-1.000; joins at 13.96 / 28.21 / 40.33 / 54.17 s in both formats.
- "magnitude." complete, no "So"; hook ends "thinks." (no "today"); clip 3 starts "a prison", ends "have." (no "It's").
- Bridge (25.4-28.2) uses the blur + gold waveform plate; Bitcoin Layer chart arrives with its audio at 28.21.
- Credits: one continuous card per format, rings aspect 0.99-1.00 (G15 PASS both), single exit, then the new PBX outro (107 frames) ending on the held logo.
- 16:9 -14.6 LUFS, sample peak -2.2 dB. 9:16 -14.6 LUFS, peak -1.3 dB (approved as reviewed).
- Gate flags at render time, all reviewed: G8 sharpness (absolute floor vs soft source cameras; policy pending), G9 tail luma 14.8 (new outro ends on black; policy conflict), G3c hook (false positive: output fades to -87 dB at 9.52, source "today" onset 9.60), 9:16 G5 true peak.
- G14/G15 were run by the orchestrator manually; they are not yet in the production gate runner (closure item 1).

## Fixtures
Positive: this pair (supersedes v12/v17 as the mechanical reference; v12/v17 remain creative references). Negative: segment_v2/out/segment_v2e.mp4 (20eacd78...) and segment_vertical_v2e.mp4 (a43305d8...).
