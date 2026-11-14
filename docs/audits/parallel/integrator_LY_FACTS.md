# Integrator facts for pp-selectid: law L-y on the render side (order 2026-11-12 '20:30')

What the render path checks and does with a moments pin under L-y VOICEOVER IS MINIMAL. Code on branch ly-shape
(edl_rules R11), merged to the release branch once its audit closes; the DoD carries the status.

## The EDL contract a moments package must meet (edl_rules R11, run in stage_validate before any cut)
Agreed with pp-selectid's shape (their message, 21:00 ET):
- DEFAULT `{"intro": null, "bridges": [{"text": <takeaway>, "after_clip": <the LAST clip index>}]}` passes; so does a
  package with no VO line.
- THE ONE L-y 2 EXCEPTION may sit in EITHER slot: `edl_vo.intro` (the hook -> clip_01 join: the only line the renderer
  plays there) or a bridge with after_clip = k < last. It passes only with the package's record
  `moments_package.bridge` (pinned.build_edl copies it into the EDL as `moments_bridge`):
  - `text`: exactly that line (compared after strip);
  - `why`: non-empty text;
  - `confirmed_by`: a non-empty string, list or dict (the blind clips-alone check);
  - the line itself: at most 20 words (BRIDGE_WORD_CAP) in either slot.
  R11 binds the record by its text and does not read after / after_clip / join.
- FAILS: an intro or a between-clips line without a matching record; two or more lines before the takeaway (even with
  a record); more than one line after the last clip; a record with no bridge line; a line whose after_clip is not a
  clip index; any intro that is not null or "" without its record (whitespace included: vo.py and the renderer would
  voice it); malformed vo / bridges / clip indexes.
- Every other moments check is unchanged: both gate verdicts exactly true, every `*_ok` check exactly true, title and
  caption, sources_30s_before per segment, hook_first_words.

## Length (R4-moments, unchanged)
- No minimum VO share; the 45 % cap stays an upper bound (unreachable with one takeaway).
- The estimated runtime stays inside 60-70 s: hook + clips + VO (words / 2.5 + 1.0 s per line) + 14.30 s tail.
  With one 24-word takeaway (10.6 s) the hook + clips must total 35.1-45.1 s; with no VO line, 45.7-55.7 s.
  The measured final is accepted at 58-72 s (G5, ruling 12).
- The editorial law gate (LAW 2) keys its VO judgments per line as before: the intro slot is `intro`, the
  bridges `bridge_1`, `bridge_2`, ... in list order, so a lone takeaway is `bridge_1`.

## What the renderer does with that shape (measured on a reshaped copy of run 165629, 20:31-21:00 ET)
hook -> clip_01 -> clip_02 -> takeaway VO card -> shout-out -> outro. DEC-4 crossfades join two clips of different
channels only where both sides have measured non-speech (here clip_01 -> clip_02: 6 frames; hook -> clip_01: a hard
cut, the hook's tail is 0.01 s). The render stage drops from 45.5 min (three VO cards) to about 28 min (one).
