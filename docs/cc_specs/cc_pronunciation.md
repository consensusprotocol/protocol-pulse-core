TASK: Restart oracle avatar server to pick up new pronunciation dict, then verify

The oracle_dialogue_engine.py was updated with new pronunciations for:
Satomi (Sah-TOH-mee), exahash (EX-ah-hash), Marty (MAR-tee), Pompliano, $2B

Steps:
1. Check current pronunciation dict: grep -n "Satomi\|exahash\|Marty" ~/protocol_pulse/oracle/oracle_dialogue_engine.py
2. Verify the new entries are there
3. Restart oracle server:
   fuser -k 8200/tcp 2>/dev/null; sleep 3
   cd ~/protocol_pulse/oracle && python3 avatar_server.py >> logs/avatar_server.log 2>&1 &
   sleep 20 && curl -s http://localhost:8200/health | python3 -m json.tool | grep uptime
4. Verify normalize_pronunciation is working by testing it directly:
   python3 -c "
   import sys; sys.path.insert(0,'oracle')
   from oracle.oracle_dialogue_engine import normalize_pronunciation
   tests = ['Satomi', 'exahash', '5 EH/s', 'Marty Bent', '$2B', '$500M']
   for t in tests: print(f'{t!r} -> {normalize_pronunciation(t)!r}')
   "
5. If any pronunciation is wrong, fix it in oracle_dialogue_engine.py
6. Also check the GREETING text in oracle_dialogue_engine.py - find where the opening line is defined
   and ensure it says "Sah-TOH-mee" (phonetic) not "Satomi" for the TTS
7. git add oracle/oracle_dialogue_engine.py && git commit -m "fix(oracle): pronunciation verified and server restarted" && git push
