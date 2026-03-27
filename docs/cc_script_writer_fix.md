Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Full audit and clean rewrite of generate_from_clips() in script_writer.py.
This function has caused KeyError: 'Name' crashes throughout the day despite multiple patch attempts.
Root cause: .format() is fragile when user content contains {curly braces}.
The relay-based fix using chr() encoding is functional but ugly and fragile.
Rewrite it cleanly so it is readable, maintainable, and permanently safe.

FILE: ~/protocol_pulse/video_pipeline_v3/script_writer.py

STEP 1 — AUDIT
Read the ENTIRE generate_from_clips() function.
Identify every place user content (tweets, clip quotes, transcripts, space tap text)
is inserted into strings. Note every .format() call.
Run regression_test.sh. Note current state.

STEP 2 — FIND ALL .format() CALLS THAT TOUCH USER CONTENT
Find every line matching: .format( that is NOT inside logger/log/print/f-string context.
These are all potential KeyError sources.

STEP 3 — CLEAN REWRITE
Replace the prompt assembly block with a clean Template approach:

from string import Template as _Template

# Build prompt using Template — $variable syntax, immune to {curly braces}
_t = _Template(SCRIPT_PROMPT_TEMPLATE)  # rename SCRIPT_PROMPT to use $clips_info etc
prompt = _t.safe_substitute(
    clips_info=str(clips_info),
    btc_price=str(btc_price),
    social_posts=str(social_posts),
    live_context=str(_live),
)

OR if Template approach requires changing SCRIPT_PROMPT too, use the simpler approach:
prompt = SCRIPT_PROMPT
prompt = prompt.replace('{clips_info}', str(clips_info))
prompt = prompt.replace('{btc_price}', str(btc_price))
prompt = prompt.replace('{social_posts}', str(social_posts))
prompt = prompt.replace('{live_context}', str(live_block+morning_block+engagement_block+memory_block+space_tap_block))

The .replace() approach is already in the file via chr() encoding. 
CLEAN IT UP — replace the chr() encoded strings with their actual string values directly.
chr(123) = { and chr(125) = } — just write the strings literally using different quoting.

STEP 4 — VERIFY WITH ADVERSARIAL TEST
After rewriting, test with content that has been causing crashes:
python3 -c "
import sys
sys.path.insert(0, 'video_pipeline_v3')
from script_writer import generate_from_clips

# Adversarial test - content with curly braces that caused crashes
test_selections = {
    'clips': [{
        'rank': 1, 'video_id': 'test', 'channel': 'Test',
        'video_title': 'Test {Name} Video',
        'quote': 'Iran sells {oil} priced in {yuan}',
        'why': 'Test {reason}',
        'host_setup': 'Setup with {Name} and {likes}',
        'host_react': 'React to {topic}',
        'score': 80,
        'start_seconds': 0, 'end_seconds': 30,
        'timestamped_text': 'transcript with {curly} {braces}',
        'clip_path': '/tmp/test.mp4'
    }],
    'social_posts': [{'text': 'Tweet with {Name} and {topic}', 'likes': 100}]
}
try:
    # Don't actually call Claude - just test prompt assembly
    import unittest.mock as mock
    with mock.patch('script_writer.call_llm', return_value=None):
        result = generate_from_clips(test_selections, btc_price='70000')
    print('ADVERSARIAL TEST PASSED')
except KeyError as e:
    print(f'STILL FAILING: {e}')
except Exception as e:
    print(f'OTHER ERROR: {e}')
"

STEP 5 — REGRESSION + COMMIT
bash regression_test.sh  # must show 0 FAILs
git add video_pipeline_v3/script_writer.py
git commit -m "fix(script): clean rewrite of prompt assembly — readable .replace() instead of chr() encoding, permanently KeyError-immune"
git push

DO NOT touch: assembler.py, tts_engine.py, overnight_render_loop.py, daily_producer.py
DO NOT restart the render loop — it is running and must not be interrupted
