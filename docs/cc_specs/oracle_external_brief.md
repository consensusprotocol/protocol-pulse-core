# ORACLE AVATAR — COMPLETE SITUATION BRIEF FOR EXTERNAL LLM AUDIT
# Date: March 25, 2026 — 9PM ET
# Status: BLOCKING Friday demo. User has been awake 24+ hours.

## THE SYSTEM
- Protocol Pulse: Bitcoin intelligence platform
- Oracle: AI avatar (Satomi) — Wav2Lip lip sync on 4x RTX 4090, Kokoro TTS
- Stack: Flask + Python backend, iOS Safari frontend
- Server: avatar_server.py port 8200, Cloudflare tunnel to protocolpulse.io

## CONFIRMED WORKING (server logs prove this)
- Wav2Lip renders correctly: 345 frames, 11.4s video, 8-15s render time
- Job 50e52c3577c8403e: audio 200, stream 200, video 200 — all perfect
- Greeting cache: 646KB served correctly every time
- Server NEVER fails — every issue is 100% frontend JavaScript

## CURRENT BUG (just discovered, 9PM)
Gate screen "Activate Microphone" button is permanently disabled (opacity:.4, not clickable).

ROOT CAUSE: requestMic() is DEFINED TWICE in oracle_live.html
- First definition at line ~991
- Second definition immediately after (duplicate)
- Also: gBtn.disabled=true at start of requestMic() is never reset if JS crashes

## HISTORY OF BUGS FIXED TODAY (in order)
1. vid.muted=true in playVid() — greeting played silent (fix: unconditional unmute)
2. setBusy(false) never re-enabled mic (fix: else{mic.disabled=false})  
3. recognition.abort() on iOS kills recognition permanently (fix: fresh instance per startRec)
4. onresult broken by duplicate for-loop injection (fix: clean single loop)
5. dual-track TTS+video: audio_first:true played TTS, video arrived after audio ended, 
   _audioFinished guard discarded lip sync video (fix: audio_first:false, video-only poll)
6. requestMic() duplicate definition + gBtn.disabled never reset (CURRENT BUG)

## THE COMPLETE oracle_live.html ARCHITECTURE
- Gate screen: user taps "Activate Microphone" → requestMic() → getUserMedia → go()
- go(): hides gate, shows stage, calls initSR() + playIntent('GREETING')
- initSR(): creates window._SR = SpeechRecognition constructor (not an instance)
- playIntent('GREETING'): fetches greeting blob from /oracle/speak, calls playVid()
- playVid(): pause+removeAttribute+load, muted=false, sets src, plays
- After greeting: startRec() creates fresh recognition instance, starts listening
- User speaks → onresult sets pending/transcript → onend auto-submits → process(text)
- process(): calls /oracle/chat with audio_first:false, polls /oracle/job/{id} every 2s
- When video blob arrives: playVid() → video plays with baked audio + lip sync
- After playVid() resolves: setBusy(false) + startRec() → loop continues

## WHAT NEEDS TO BE FIXED RIGHT NOW

FIX 1 (IMMEDIATE): Remove the duplicate requestMic() function definition
FIX 2: Add gBtn.disabled=false to the catch block in requestMic() 
FIX 3: Verify gBtn.disabled is reset after any error path

## THE QUESTION FOR EXTERNAL LLMS
Given the complete context above:
1. Are there any other duplicate function definitions in a 2401-line template that has had 
   20+ surgical patches applied in 8 hours that could cause similar issues?
2. Is the video-only polling approach (audio_first:false, 2s poll) going to work reliably 
   on iOS Safari given the 8-15s render time? What's the risk of iOS killing the page?
3. After all these patches, is there a clean architectural approach that avoids all these 
   failure modes without a full rewrite?
4. What is the minimum viable oracle that WILL work on iOS Safari for Friday demo?

## RECENT COMMITS (oracle_live.html changes today)
de34773a - iOS-safe SR rewrite: fresh instance per session
5e0711be - setBusy(false) re-enables mic
4d41cb85 - unconditional unmute in playVid
84a8817a - clean onresult handler
c60412cd - stop audio bleed, recovering escape
7cbd6955 - forensic audit: iOS video reset
e68846a7 - replace dual-track with video-first poll (LATEST)
