Read PIPELINE_LAWS.md. Then read the ENTIRE templates/oracle_live.html (all 2401 lines).
Then run cross_llm_audit.py on templates/oracle_live.html with these 8 forensic questions.

CONFIRMED FACTS FROM SERVER LOGS:
- Server receives POST /oracle/speak → returns video/mp4 (646KB greeting cache) → 200 OK
- Server receives GET /oracle/thinking → 206 (thinking loop served)
- Server receives POST /oracle/chat → 200 with job_id
- Server renders Wav2Lip correctly (frames, audio, encoding all confirmed working)
- ALL server-side is working perfectly

THE BUGS (user-confirmed, reproducible every time):
BUG 1: Greeting video plays with NO lip sync — Satomi avatar is static/frozen while audio plays
BUG 2: After greeting, any user speech goes to "Recovering" mode and never produces output
BUG 3: Both bugs persist across multiple fix attempts (7+ commits today)

FORENSIC AUDIT QUESTIONS for Gemini + GPT-4o + Grok:

1. The thinking loop video plays first (vid.muted=true, vid.loop=true, vid.src=/oracle/thinking).
   When the greeting blob arrives, playVid() sets vid.muted=false, vid.loop=false, vid.src=blobURL.
   On iOS Safari: does changing video.src while a video is actively playing require a user gesture?
   Could iOS suppress the src change or show a frozen frame from the previous video?

2. The greeting is served as a direct video/mp4 response from /oracle/speak (not via job polling).
   The frontend checks content-type 'video' and calls r.blob().then(blobURL).
   Is there any scenario where the blob URL is created but the video element shows a static frame
   instead of playing the lip-sync animation?

3. After the greeting plays (or appears to play), _greeted=true is set and startRec() is called.
   recognition.start() fires. User speaks. recognition.onresult fires and sets pending.
   Then recognition.onend fires. process(pending) is called.
   process() calls /oracle/chat → gets job_id → polls /oracle/job/{id}/audio → plays audio.
   WHERE exactly does "Recovering" state appear and what triggers it?
   Map every state transition that could lead to RECOVERING without ever resolving.

4. The oracle server logs show the interactive request received and processed successfully
   (job rendered, audio ready, video ready). But the frontend shows "Recovering".
   This means the frontend either: (a) never receives the job response, (b) receives it but
   fails silently, or (c) the setOracleState('RECOVERING') is called somewhere and never cleared.
   Find every place setOracleState('RECOVERING') is called and what conditions lead there.

5. Look at the audio polling flow: fetch /oracle/job/{id}/audio with polling retry.
   If this returns 202 (audio not ready), it retries. If it returns 200, it plays audio.
   Is there a race condition where audio 200 is received but the EventSource for video_ready
   fires before audio.onended, causing the state machine to deadlock?

6. The video element has a settled guard (_settled flag). If _settled=true from the thinking
   loop's safety timeout, could it prevent the greeting video from ever triggering _finish()?

7. On iOS Safari specifically: does fetch() with a blob response work correctly for video/mp4
   of 646KB? Are there any known iOS issues with MediaSource, blob URLs, or video element
   src swapping that would cause the video to render as a static image?

8. Is there a timing issue where vid.muted=true is set AFTER playVid() already set it to false?
   Trace every place vid.muted is set in the entire template and identify if any async callback
   could re-mute the video after playVid() unmutes it.

AFTER AUDIT - IMPLEMENT THE HIGHEST CONFIDENCE FIXES:

The fix must be surgical and complete. Do NOT patch around the issue — fix the root cause.

Key areas to fix based on audit findings:
- If thinking loop src-swap issue on iOS: add vid.pause() + vid.removeAttribute('src') + vid.load() before setting new src in playVid()
- If RECOVERING state deadlock: find every setOracleState('RECOVERING') call and add a recovery timeout that clears it after 30s
- If settled guard issue: reset _settled=false at the start of each new playVid() call
- If audio/video race: ensure audio playback doesn't gate video rendering
- If blob URL issue on iOS: try using URL.createObjectURL on a new Blob explicitly

After implementing:
1. Test by curling the greeting endpoint: curl -X POST http://localhost:8200/oracle/speak -H "Content-Type: application/json" -d '{"intent":"GREETING"}' -o /tmp/test_greeting.mp4 && file /tmp/test_greeting.mp4 && ffprobe /tmp/test_greeting.mp4 2>&1 | grep -E "Duration|Video|Audio"
2. Verify the template logic with a dry-run trace through the JS
3. git add templates/oracle_live.html && git commit -m "fix(oracle): forensic audit — fix greeting lip sync + Recovering loop" && git push

This is BLOCKING Friday demo. Make it work.
