Read ~/protocol_pulse/services/stage_brief_pipeline.py lines 480-530 (_generate_tts_chatterbox function).
Read ~/protocol_pulse/oracle/avatar_server.py lines 655-670 (normalize_pronunciation usage).
Read ~/protocol_pulse/oracle/oracle_dialogue_engine.py — find normalize_pronunciation function.
Read ~/protocol_pulse/templates/stage.html — grep for "Oracle" in nameplate and greeting text.
Read ~/protocol_pulse/core/routes.py — grep for "Oracle" in any stage/oracle page context strings.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SATOMI RENAME + NUMBER NORMALIZATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1 — RENAME ORACLE → SATOMI across Stage avatar

The Oracle avatar is being renamed to "Satomi" (sah-TOH-mee).
Japanese name meaning "wise truth". Fits the anime/cyberpunk aesthetic perfectly.

In stage.html find ALL references to "Oracle" in:
  - The nameplate: "Oracle — Protocol Pulse" → "Satomi — Protocol Pulse"  
  - Any greeting/intro text referencing "Oracle"
  - Button labels or status text saying "Oracle"
  - The title attribute on mic button: "Tap to interrupt Oracle" → "Tap to interrupt Satomi"

In stage_brief_pipeline.py find the greeting/intro script where the 
avatar introduces herself. Change any "I'm the Oracle" or "Oracle here" 
to "I'm Satomi" or "Satomi here".

In stage_broadcast_service.py find any GREETING script or intro text:
  grep -n "Oracle\|greeting\|intro\|I am\|I'm" services/stage_broadcast_service.py | head -20
Update any self-introduction to use "Satomi".

NOTE: Do NOT rename the oracle_live.html page or /oracle-live route.
That is a separate page. Only rename the Stage avatar persona name.
The nameplate in stage.html specifically says "Oracle — Protocol Pulse" — change that.

FIX 2 — PRONUNCIATION: ensure Chatterbox says "Satomi" correctly

Chatterbox uses normalize_pronunciation in oracle_dialogue_engine.py.
Add "Satomi" to the pronunciation dictionary with phonetic spelling:
  "Satomi": "Sah-TOH-mee"

In oracle_dialogue_engine.py find the pronunciation dictionary/map.
Add: "Satomi": "Sah-TOH-mee"
This ensures when the name is spoken it sounds natural, not "SAT-oh-my".

FIX 3 — NUMBER NORMALIZATION for Stage TTS

Root cause: _generate_tts_chatterbox() in stage_brief_pipeline.py 
sends text to /oracle/voice WITHOUT calling normalize_pronunciation first.
The avatar server's /oracle/voice endpoint already has normalize_pronunciation
but it's called AFTER the text arrives. The stage pipeline needs to 
normalize BEFORE sending.

In stage_brief_pipeline.py in _generate_tts_chatterbox():
  Find where `text` is sent to the /oracle/voice endpoint.
  Before the requests.post() call, add:
    try:
        sys.path.insert(0, os.path.join(BASE, 'oracle'))
        from oracle_dialogue_engine import normalize_pronunciation
        text = normalize_pronunciation(text)
    except Exception as e:
        logger.warning(f"normalize_pronunciation unavailable: {e}")
  
This converts: "$70,534" → "seventy thousand five hundred thirty-four dollars"
And: "78%" → "seventy-eight percent"
And: "978 EH/s" → "nine hundred seventy-eight exahash per second"

Also verify normalize_pronunciation handles these cases. In oracle_dialogue_engine.py:
  grep -n "EH\|exahash\|per second\|hashrate" oracle/oracle_dialogue_engine.py | head -5
If "EH/s" is not handled, add it:
  text = re.sub(r'(\d+(?:\.\d+)?)\s*EH/s', 
    lambda m: num2words(float(m.group(1))) + ' exahash per second', text)

FIX 4 — GREETING SCRIPT update for Satomi intro

In stage_broadcast_service.py find where the GREETING script is generated.
The intro script likely says something like "Hey, I'm the Oracle..."
Update the Claude Haiku prompt/template for GREETING type to:
  "You are Satomi, Protocol Pulse's live Bitcoin intelligence anchor.
   Your intro should start: 'I'm Satomi, your Protocol Pulse signal anchor...'
   or similar. Never say 'Oracle' — always 'Satomi'."

VERIFICATION:
  grep -r "Oracle" ~/protocol_pulse/templates/stage.html | grep -v "oracle-live\|oracle_live\|oracle_widget\|/oracle" | head -5
  # Should return 0 nameplate/greeting references (route refs OK to keep)
  grep "Satomi" ~/protocol_pulse/templates/stage.html | head -5
  # Should show nameplate with Satomi
  grep "Satomi\|Sah-TOH" ~/protocol_pulse/oracle/oracle_dialogue_engine.py | head -3
  # Should show pronunciation entry

COMMIT:
  git add templates/stage.html services/stage_brief_pipeline.py services/stage_broadcast_service.py oracle/oracle_dialogue_engine.py
  git commit -m "feat(satomi): rename Stage Oracle→Satomi + number normalization for Chatterbox TTS + pronunciation dict"
  git push
