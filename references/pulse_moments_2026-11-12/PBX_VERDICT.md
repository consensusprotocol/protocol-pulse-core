# PBX's verdict on the Pulse Check review video of 2026-11-12

Relayed by the orchestrator, order 2026-11-12 '20:30' ET, verbatim:

> "the output was actually good. I was very pleased. You did a great job! The only thing that I need to comment is
> that you added too much voiceover and though it wasn't terrible, it was too interruptive most of the time it wasn't
> necessary at the very end, it was appreciated. We keep it that we only have one input at the end unless you deem it
> necessary to stick together other content, but honestly, all that content work together beautifully as a medley
> without my voice."

## What this reference is for

A reference for **clip choice, cuts, layout and the closing line**. It is **NOT** a reference for the amount of
voiceover: PBX found the VO too much and too interruptive, and law L-y VOICEOVER IS MINIMAL (same order) makes the
default shape hook -> clip -> clip (-> clip) back to back, then one takeaway line at the end and the sign-off. This
video's intro and its bridge after clip 1 are exactly what L-y removes; its closing line ("No ruler. Just rules nobody
gets to bend. That's the idea, and it's the part most people still miss when they look at Bitcoin.") is the line PBX
appreciated.

## The video

- Sent to PBX's Telegram approval chat by telegram.review_drop as **REVIEW ONLY - NOT A PASS** on 2026-11-12 at 13:33 ET:
  message 67806 (16:9), 67807 (9:16), 67808 (the review note). No release authorisation exists for this run.
- Run runs/pinned_20261112_165629, code 59068f44 (tree clean at launch); sealed pin 37c5b5f5
  (data/moments_pins/MOMENTS_PIN_115548.json, sha256 fe29a10f5312ee5bbe93d98ea52886985813ff89d0e2aa7f994b0bf506cd4f3d,
  copied here as PIN.json).
- Final sha256 (the bytes sent): 16:9 out/segment.mp4 5fb53826d8f45b083bd696abc483a22346cf80fbdcdd8bc418441923b7358265,
  9:16 out/segment_vertical.mp4 1b864cd809a70c485dd1a6bae335de2421a2f6496343ef531a3add3b9f7b1d63. 61.000 s in both.
- Line-up (locked word spans): hook Saifedean Ammous 8.54 s, clip 1 What Bitcoin Did 10.34 s, clip 2 Natalie Brunell
  3.64 s (a 9:16 stack of two speakers). In the final (concat manifest): hook 0.00-8.62, VO intro 8.62-14.79 (6.17 s),
  clip 1 14.79-25.79, bridge 25.79-32.62 (6.83 s), clip 2 32.62-37.29, takeaway 37.29-46.29 (9.00 s), shout-out naming
  all three channels 46.29-56.54, outro 56.54-61.00. VO 22.0 s of 61.0 s.
- Three REQUIRED rows were not PASS when it was sent, each named in the review note with its measured reason:
  G3c_acoustic_tail (clip_02's tail under the music bed; ruling 21 since measures the prepared clip),
  G18_word_for_word (the final's decode omitted clip_01's soft aside "it's not, you know,"; ruling 22 since decides
  that by the audio), V1_visual_checklist 9:16 (the two vision models split on clip_02's stack; ruling 23 since asks a
  stack per panel).

## Protection

Read-only copy; SHA256SUMS covers every file; tag ref-pulse-moments-2026-11-12; pipeline/regression.sh verifies the
manifest (any changed, missing or added file fails). Doc: docs/references/REFERENCE_PULSE_MOMENTS_2026-11-12.md.
