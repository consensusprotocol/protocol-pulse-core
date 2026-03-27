Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 4578-4615 (should_insert_transition).
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 2798-2860 (make_signal_active_scene).
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 319-360 (_ken_burns_motion).
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 1068-1300 (make_pip_preview and placeholders).
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 1540-1600 (tweet card metrics).
Read ~/protocol_pulse/core/routes.py lines 817-845 (_is_nostr_spam).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VIDEO PIPELINE FIXES — 7 ISSUES FROM HUMAN REVIEW OF B-GRADE RENDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1 — MISSING TRANSITIONS (P0)
At minute 5:45 partner channel → Today's Intelligence: no transition/whoosh.
At minute 7:19 Today's Intelligence → What Bitcoin Is Saying: no transition.
The same glitch+whoosh transitions that exist between intel graph slides
at 6:33 must also fire between ALL major segment boundaries.

In should_insert_transition(), add these missing cases:
  # Transition out of partner/clip into data/intelligence
  if prev_part in ("clip", "react", "partner", "space_tap") and next_part in ("data", "social_segment"):
      return True
  # Transition out of data/intelligence into social/tweet segments
  if prev_part == "data" and next_part in ("social_segment", "signal_active"):
      return True
  # Transition out of social into signal_active
  if prev_part == "social_segment" and next_part == "signal_active":
      return True

Also check what segment types are used for "partner channel" and "Today's Intelligence"
by searching for entries with type "clip" or "partner" followed by "data":
  grep -n "partner\|space_tap\|data.*segment" assembler.py | head -20

FIX 2 — TWEET CARD 0 LIKES / 0 RETWEETS (P0)
At line ~2372, tweet cards render score/likes from card data.
At line 3414 and 3751, likes field is read from post data.
The tweet card drawtext renders "0" because the social_posts_raw
from script_writer.py are not passing through actual X API metrics.

In assembler.py find where tweet cards render the likes/retweets numbers.
Look for drawtext patterns near "likes" or "❤" or "retweets".
If the value is 0, fall back to showing the screenshot image of the tweet
(which contains real metrics) rather than fake "0 likes 0 retweets" text.
The logic: if likes == 0 AND retweets == 0, suppress the metrics line
or replace with a subtle "📊 Real-time metrics loading" placeholder.
Do NOT show "0 likes 0 retweets" — it looks broken.

FIX 3 — NARRATOR CUT OFF AT SEGMENT END (P0)
At minute 7:19 the social segment narrator is cut off abruptly when
SIGNAL ACTIVE begins. Root cause: audio duration mismatch between
the social segment's TTS audio and the video render duration.

In the assembly loop where should_insert_transition() is checked
before signal_active: add a 0.5s audio tail pad to the social segment
BEFORE inserting the transition. Find where social_card parts are
appended to `parts` and after the last card, add:
  # Ensure audio tail — prevent narrator cutoff at segment boundary
  # The last social segment audio needs +0.5s of silence padded
This prevents the transition from cutting narration mid-word.

Technically: in _bv2_encode or the final encode of social segments,
add afade=t=out:st={audio_dur-0.5}:d=0.5 to the audio chain so
narration fades rather than hard-cuts.

FIX 4 — NOSTR SPAM SHOWING ON SIGNAL ACTIVE (P0 CRITICAL)
The _is_nostr_spam() function exists in core/routes.py at line 817.
BUT it is NOT applied when signal_content["nostr_posts"] is populated
for the video pipeline. The spam posts from npub1a1c6869a...50514b
(known spam npub) are rendering in the video.

In assembler.py, in make_signal_active_scene() or wherever
signal_content["nostr_posts"] is used:
  1. Copy the _is_nostr_spam logic directly into assembler.py as
     a local function (since routes.py can't be imported from assembler):
     
     SPAM_TERMS = ['incest', 'onlyfans', 'nude', 'xxx', 'porn', 'naked', 
                   'sex tape', 'teenage', 'teenagegirls', '#nolimit',
                   'FolloFFFFvh', 'RssazZZZ', 'altcoin', 'memecoin',
                   '#solana', '#ethereum', '#eth ', '#nft', 'airdrop',
                   'shitcoin', 'presale', 'pump it']
     SPAM_NPUBS = ['npub1a1c6869a', '50514b']  # known spam accounts
     
     def _is_nostr_spam_assembler(post: dict) -> bool:
         content = post.get('content', post.get('text', '')).lower()
         npub = post.get('npub', post.get('author', ''))
         if any(t in content for t in SPAM_TERMS):
             return True
         if any(n in npub for n in SPAM_NPUBS):
             return True
         return False
  
  2. In make_signal_active_scene(), filter nostr_posts BEFORE rendering:
     nostr = [p for p in signal_content.get("nostr_posts", [])[:5]
              if not _is_nostr_spam_assembler(p)][:3]
  
  3. In the main assembly loop at ~line 5200 where signal_content is
     built, also filter there:
     if "nostr_posts" in signal_content:
         signal_content["nostr_posts"] = [
             p for p in signal_content["nostr_posts"]
             if not _is_nostr_spam_assembler(p)
         ]

FIX 5 — NOSTR TEXT WORD WRAP / CUT OFF (P1)
In make_signal_active_scene(), the nostr card text is rendered with
fixed drawtext. Text gets cut off because drawtext has no word wrap.

Replace the current drawtext approach for nostr card body text with
a word-wrapped version:
  def _wrap_text(text: str, max_chars: int = 55) -> list:
      """Wrap text to max_chars per line, return list of lines."""
      words = text.split()
      lines, current = [], ''
      for word in words:
          if len(current) + len(word) + 1 <= max_chars:
              current = (current + ' ' + word).strip()
          else:
              if current:
                  lines.append(current)
              current = word
      if current:
          lines.append(current)
      return lines[:4]  # max 4 lines per card

Then in the nostr card ffmpeg filtergraph, render each line with
separate drawtext at y positions: card_y+40, card_y+60, card_y+80,
card_y+100 (20px line spacing at fontsize 16).

Truncate display text to 220 characters before wrapping to prevent
overflow beyond card height.

FIX 6 — PiP BROKEN "SIGNAL" BOX AT 7:49 (P0)
At minute 7:49, the PiP window shows a broken "SIGNAL" placeholder
instead of the clip. The dark placeholder at line 1133 has no visual —
just black. When cfr-fail or blackdetect triggers, we fall back to
a plain dark box, but the filtergraph still tries to overlay text
labels on it that look broken.

In make_pip_preview(), when the cfr-fail placeholder or dark placeholder
is used, set a flag `pip_is_placeholder = True` and pass this to the
caller. In the caller (make_host_visual or wherever PiP is composited),
if pip_is_placeholder is True, simply DO NOT render the PiP overlay
at all — run the scene as a full-panel narrator scene without PiP.
A clean full-panel narrator is far better than a broken "SIGNAL" box.

Also investigate WHY cfr-fail is triggering for this specific clip.
The clip at position ~7:49 is likely a Suno music track or a
non-standard FPS clip. Check what PIP_PLACEHOLDER is and whether
_ensure_pip_placeholder() is producing a valid file.

FIX 7 — KEN BURNS JITTER / SUBTLE SHAKE (P1)
The _ken_burns_motion function uses continuous accumulation:
  crop=1920:1080:'20*t/{dur:.2f}':'11*t/{dur:.2f}'
This causes drift that accumulates nonlinearly and creates wobble
on long segments or when multiple Ken Burns segments are concatenated.

Fix: cap the motion at a very small range and use smooth easing:
  # Max pan distance: 8px horizontal, 4px vertical (was 20px, 11px)
  # Use smooth ease-in-out: sin curve instead of linear
  crop=1920:1080:'8*sin(PI*t/{dur:.2f}/2)':'4*sin(PI*t/{dur:.2f}/2)'

This creates a gentle, smooth drift that starts and ends at center,
never accumulates, and cannot cause perceived shake.

Also add setpts=PTS-STARTPTS after each crop to reset timestamps:
  f"[{label_in}]scale=1960:1102:flags=lanczos,"
  f"crop=1920:1080:'8*sin(PI*t/{dur:.2f}/2)':'4*sin(PI*t/{dur:.2f}/2)',"
  f"setpts=PTS-STARTPTS,setsar=1,format=yuv420p[{label_out}];\n"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After all fixes:
  python3 -c "import assembler; print('assembler imports OK')"
  grep -c "_is_nostr_spam_assembler" video_pipeline_v3/assembler.py
  # Should be > 0
  grep "sin(PI" video_pipeline_v3/assembler.py | head -2
  # Should show new Ken Burns formula
  bash regression_test.sh
  # Must show ZERO FAILs before commit

COMMIT:
  git add video_pipeline_v3/assembler.py
  git commit -m "fix(video+nostr): PiP black frames + clip tail padding + stay sovereign closing + nostr spam filter"
  git push
