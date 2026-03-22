Read ~/protocol_pulse/PIPELINE_LAWS.md first.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY AUDIT-FIRST LAW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DO NOT write any code until the cross-LLM audit completes.
The audit fires Gemini + GPT-4o + Grok in parallel on the actual files.
Their consensus determines what gets built and how.
This is non-negotiable — skipping the audit is what caused every regression tonight.

TASK: Fix social segment ("WHAT BITCOIN IS SAYING") and space tap segment.
Both have been absent from every production render. Root cause identified.

FILES IN SCOPE:
- video_pipeline_v3/daily_producer.py
- video_pipeline_v3/script_writer.py
- video_pipeline_v3/utils/social_fetcher.py
DO NOT touch: assembler.py, tts_engine.py, overnight_render_loop.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — CROSS-LLM AUDIT (Cycle 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/protocol_pulse
python3 utils/cross_llm_audit.py --feature fix-social-spacetap
Save the output path from cycle 1.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — CROSS-LLM AUDIT (Cycle 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 utils/cross_llm_audit.py --feature fix-social-spacetap --cycle 2 --cycle1-results [C1_OUTPUT]
Read the full consensus. Note every P0 finding.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — IMPLEMENT BASED ON AUDIT CONSENSUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Known root cause: social_posts is fetched AFTER generate_from_clips() runs.
Claude generates the script without seeing tweet data → no social segment in output.

Fix in daily_producer.py:
1. Move get_todays_social_posts() call to BEFORE generate_from_clips()
2. Pass social_posts into generate_from_clips() as a parameter
3. Verify generate_from_clips() signature accepts social_posts
4. Verify {social_posts} is passed to the prompt template in script_writer.py

For space tap: verify selections.json has space_tap_clips populated.
If x_spaces_scraper is not producing clips, log the issue and add fallback
so the segment is simply skipped cleanly rather than breaking the render.

Apply any additional P0 findings from the audit consensus.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — VERIFY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/protocol_pulse/video_pipeline_v3
python3 daily_producer.py --skip-scan --test 2>&1 | grep -E "SOCIAL|social|space_tap|STEP" | tail -20
cat output/$(date +%Y-%m-%d)/script.json | python3 -m json.tool | grep -E "social_segment|space_tap" | head -10
Confirm social_segment entries exist in script.json.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh  # must show 0 FAILs
git add video_pipeline_v3/daily_producer.py video_pipeline_v3/script_writer.py
git commit -m "fix(pipeline): social_posts passed before script generation — social segment now fires every render; space tap hardened"
git push