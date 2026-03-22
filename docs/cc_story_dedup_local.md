Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Migrate story_dedup.py from gpt-4o-mini to local Qwen3-Coder:30b.
This is a pure classification task — yes/no duplicate detection on article headlines.
Zero quality risk. Significant cost saving (~$0.0001/call but fires constantly).

FILE: ~/protocol_pulse/services/story_dedup.py
LOCAL LLM: http://localhost:11435, model qwen3-coder:30b
FALLBACK: gpt-4o-mini (existing path, keep intact)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVESTIGATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read ~/protocol_pulse/services/story_dedup.py in full.
Find is_same_story_gpt() function (line ~73).
Understand the exact prompt and expected output format.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGE REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add a new function is_same_story_local() that:
1. Calls http://localhost:11435/api/chat with qwen3-coder:30b
2. Uses the SAME prompt as the GPT version
3. Parses response for yes/no/maybe
4. Returns same format as is_same_story_gpt()
5. Timeout: 15 seconds

Modify is_same_story_gpt() to:
- Try local Ollama FIRST via is_same_story_local()
- Fall back to gpt-4o-mini only if local fails
- Log which path was used: logger.debug("dedup: local|gpt path")

IMPORTANT: is_same_story_gpt() is called is_semantic_duplicate (aliased at line 121).
Do not change the function signature or return format.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 -c "
from services.story_dedup import is_semantic_duplicate
# Same story
r1 = is_semantic_duplicate('Bitcoin Price Hits All Time High Above 100K', ['Bitcoin Surges Past 100000 Dollar Mark'])
print('SAME:', r1)
# Different story
r2 = is_semantic_duplicate('Bitcoin Mining Difficulty Hits Record', ['Iran Sanctions Hit Oil Markets'])
print('DIFF:', r2)
"
Both should return quickly. SAME should be True/similar, DIFF should be False.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add services/story_dedup.py
git commit -m "feat(dedup): local Qwen3 semantic duplicate detection, gpt-4o-mini fallback"
git push

DO NOT touch: article_automation.py, routes.py, assembler.py, tts_engine.py