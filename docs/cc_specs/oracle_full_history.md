# ORACLE AVATAR — COMPLETE HISTORY OF BUGS AND FIXES
# This is the full picture for forensic LLM analysis.
# Read every word before touching any code.

## WHAT WORKS RIGHT NOW (confirmed by user test, 8:22 PM)
- Oracle page loads correctly
- Thinking loop animation plays (vid.muted=true, streaming 206)
- Greeting VIDEO is served correctly: POST /oracle/speak → 200 → 646KB video/mp4
- Greeting AUDIO plays (user hears Satomi's voice)
- Mic activates after greeting

## WHAT IS BROKEN RIGHT NOW (user screenshot at 8:22 PM)
- Greeting plays with NO LIP SYNC — avatar face is FROZEN/STATIC while audio plays
- After greeting, user speaks, text transcribes correctly (onresult working)
- But auto-submit doesn't fire — user has to tap "tap to send"
- After tapping send: status shows "Satomi is thinking" (good)
- Then: response audio plays with NO LIP SYNC (frozen face again)
- Halfway through: response STARTS OVER (double audio)
- Third attempt: dead, no response

## ROOT CAUSE IDENTIFIED IN CODE (do not patch around — fix the actual root)

### BUG 1: GREETING HAS NO LIP SYNC
The playVid() function (line 1504) does this:
  vid.pause();
  vid.removeAttribute('src');
  vid.load();
  vid.loop=false;
  vid.muted=true;  ← STARTS MUTED
  vid.src=url;
  ... then waits for 'canplay' event to unmute:
  vid.addEventListener('canplay', function() {
    if(!window._chatAudioPlaying) {  ← THIS GUARD IS THE BUG
      vid.muted=false;
    }
  });

THE PROBLEM: For the GREETING, the greeting blob is the ONLY audio source.
There is no separate TTS audio. window._chatAudioPlaying is either:
(a) Still true from a previous session/state, OR  
(b) The condition is wrong — greeting should ALWAYS unmute regardless

The video plays (you can see lip movement briefly in older working versions)
but vid.muted=true is never cleared because the canplay guard blocks it.

SIMPLE FIX: In playVid(), unmute unconditionally right before vid.play():
  vid.muted=false;  // Always unmute — the video IS the audio source
  var p = vid.play();

Remove the canplay unmute logic entirely for the greeting path.
OR: remove the `if(!window._chatAudioPlaying)` guard from canplay.

### BUG 2: AUTO-SUBMIT NOT FIRING  
recognition.onresult fires and sets pending correctly.
recognition.onend fires but doesn't call process().
Most likely: busy=true is stuck from a previous state.
The onend check `if(_sub&&!busy)` fails because busy=true.
FIX: In onend, if we have text, call process() regardless of busy state.
Or better: call setBusy(false) at the start of onend before checking.

### BUG 3: DOUBLE AUDIO ON RESPONSE
Two code paths both call playVid():
Path A: SSE EventSource 'video_ready' event → _handleVideoReady() → playVid()
Path B: polling setInterval → _startPollFallback() → playVid()
When SSE fires AND polling is still running, both trigger.
FIX: When SSE fires video_ready, immediately clearInterval(pollVideo).
The _videoHandled flag exists but there's a race — SSE and poll both check it
and both can pass before either sets it to true.
FIX: Set _videoHandled=true SYNCHRONOUSLY before any async fetch.

### BUG 4: GREETING AUDIO BLEEDS INTO RESPONSE
When process() is called, the greeting video is still playing.
My earlier fix added vid.pause() at process() start which was correct.
But vid.muted=true in process() then gets applied to the response video too.
The response video starts with muted=true and never gets unmuted.
FIX: Don't set vid.muted=true in process(). Just vid.pause(). Let playVid handle muting.

## COMMIT HISTORY (every oracle change, most recent first)
84a8817a - fix onresult (broken by double for-loop), auto-submit onend
c60412cd - stop audio bleed, double audio fix, iOS interim, recovering escape  
7cbd6955 - forensic audit: iOS video reset, _handleVideoReady race
823a08cf - unmute playVid, onend state, API timeouts
d4e0c270 - video before audioFinished, Seh-toe-mee pronunciation
53e9828b - iOS onended race, 7 fixes from cross-LLM audit
280429d2 - auto-submit on silence, persistent avatar underlay
3fc8658d - stopRec isRec flag race

## THE SINGLE CORRECT FIX (do exactly this, nothing else)

In playVid() function around line 1516:
REMOVE: vid.muted=true;
REMOVE: the canplay listener that conditionally unmutes
ADD: vid.muted=false; immediately before var p=vid.play();

In process() function around line 1172:
REMOVE: vid.muted=true from the try{vid.pause();vid.muted=true;...} line
KEEP: vid.pause(); vid.loop=false;

In _handleVideoReady():
ADD: _videoHandled=true; as the FIRST LINE before the async fetch
This prevents the race between SSE and polling

In recognition.onend:
ADD: busy=false; as first line before checking _sub
This unblocks auto-submit if busy got stuck

These 4 surgical changes fix all bugs.
Verify after each: curl test the greeting endpoint, check no muted flags.
Commit only when all 4 are in and verified.
