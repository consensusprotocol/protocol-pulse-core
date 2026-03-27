Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 1066-1160 (make_pip_preview).
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 4840-4970 (main assembly loop, wrap/outro).
Read ~/protocol_pulse/video_pipeline_v3/script_writer.py lines 40-80 and 175-215 (wrap, stay sovereign).
Read ~/protocol_pulse/core/routes.py lines 813-830 (nostr route).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4 TARGETED VIDEO + NOSTR FIXES
Human review of the C(76) render identified these specific issues.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NO CROSS-LLM AUDIT NEEDED — all 4 are targeted, low-risk fixes
with clear root causes from code inspection.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 1 — PiP WINDOW BLACK AT 3:31 AND 5:39
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Root cause: make_pip_preview() CFR pre-process fails for some
clips (wrong codec, b-frames). It falls back to the original
clip. Then the PiP filtergraph in the main assembler receives
a VFR clip and ffmpeg silently outputs black frames.

In make_pip_preview() (around line 1105), after the CFR step:
If CFR fails AND the original clip has codec issues (vfr),
force-generate a dark placeholder instead of passing bad clip.

Add explicit black-frame detection after pip render:
  After the pip ffmpeg call completes and writes output_path,
  run: ffprobe -f lavfi -i movie={output_path},blackdetect=d=0.1:pix_th=0.10 -an -t 3
  If >50% of first 3s is black → discard and use dark placeholder

Also: in make_pip_preview, change -preset medium to -preset ultrafast
(same regression fix as oracle — was 4-8s slower than necessary).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 2 — PARTNER CLIP SENTENCES CUT OFF TOO EARLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Root cause: clip extractor trims to the quote duration exactly.
The speaker is still finishing when it cuts.

In assembler.py, find where partner clip duration is set.
Search for: clip_dur = ffprobe_duration(clip_path)
And where the clip is trimmed for assembly.

Add 1.5 seconds of tail padding to all partner clip segments:
  clip_display_dur = clip_dur + 1.5
This gives the speaker 1.5s to finish their sentence before cut.
Cap at clip total duration to avoid black frames at end.

Also check clip_extractor.py — find where --end-time is calculated:
  If quote_end is calculated from quote timestamps, add 1.5s buffer
  grep -n "end_time\|quote_end\|trim_end" video_pipeline_v3/clip_extractor.py | head -20

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 3 — EPISODE ENDS ABRUPTLY, NO "STAY SOVEREIGN" CLOSING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Root cause: script_writer.py line 183 generates:
  {"host": 2, "text": "Final wrap. Stay sovereign.", "type": "wrap"}
This is only 5 words. It gets TTS rendered as a very short
clip that sounds abrupt. The outro video plays immediately after.

Fix in script_writer.py — update the wrap fallback to a proper
closing statement. When the LLM generates the wrap segment,
ensure it ends with a full closing phrase. Add to the system
prompt's wrap instruction (around line 71):
  "The wrap segment must be at least 2-3 sentences. End with
  'Stay sovereign.' as the final words. Give the audience a
  proper send-off — summarize the key takeaway, then close."

Also in assembler.py, after the wrap TTS segment is created:
  Check if wrap_audio duration < 4s → log warning, this is too short

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 4 — NOSTR FEED SHOWING SPAM/EXPLICIT CONTENT [CRITICAL]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The Stage signal feed is showing explicit spam from unfiltered
Nostr relays. This is publicly visible on the live site.
This must be fixed immediately.

Find where Nostr posts are fetched and rendered in stage.html:
  grep -n "nostr\|relay\|fetch.*notes\|notes.*fetch" templates/stage.html | head -20
  grep -n "nostr\|relay" core/routes.py | head -20

Add content filter to ALL Nostr post fetching:

BLOCKLIST to filter out (apply to post content before display):
  - Any post containing: "incest", "sex", "porn", "xxx", "nude", "naked",
    "onlyfans", "#solana", "#memecoin", "ETHBTC", "PAXGBTC", "altcoin" 
    when combined with financial pump language
  - Any post where the content is >80% hashtags
  - Any post from npubs not in a curated whitelist (if whitelist exists)

In the route that serves Nostr content:
  posts = fetch_nostr_posts(relay_url)
  posts = [p for p in posts if not is_spam(p['content'])]

Add is_spam() function:
  def is_spam(content):
      content_lower = content.lower()
      spam_terms = ['incest', 'onlyfans', 'nude', 'xxx', 'porn']
      if any(t in content_lower for t in spam_terms):
          return True
      # Filter posts that are mostly hashtags
      words = content.split()
      hashtag_ratio = sum(1 for w in words if w.startswith('#')) / max(len(words), 1)
      if hashtag_ratio > 0.6:
          return True
      return False

Apply same filter in stage.html JS if posts are fetched client-side.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST 1 - Nostr filter (EXTERNAL):
  curl -s https://protocolpulse.io/api/nostr/latest/SOME_PUBKEY | python3 -m json.tool | grep -i "incest\|onlyfans\|xxx"
  EXPECTED: 0 results

TEST 2 - Wrap duration:
  Find the wrap TTS audio file from today's render and check duration:
  find ~/protocol_pulse/video_pipeline_v3 -name "*wrap*" -newer /tmp -exec ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 {} \;
  EXPECTED: >4s

TEST 3 - regression_test.sh 0 FAILs

COMMIT:
git add video_pipeline_v3/assembler.py video_pipeline_v3/script_writer.py \
  video_pipeline_v3/clip_extractor.py core/routes.py templates/stage.html
git commit -m "fix(video+nostr): PiP black frames + clip tail padding + stay sovereign closing + nostr spam filter
- PiP: blackdetect validation after render, discard if >50% black first 3s
- PiP: ultrafast preset (was medium, 4-8s slower)
- Partner clips: +1.5s tail padding so speaker finishes sentence
- Wrap segment: require 2-3 sentences minimum, enforce Stay sovereign closing
- Nostr: is_spam() filter blocks explicit content, altcoin spam, hashtag farms"
git push
