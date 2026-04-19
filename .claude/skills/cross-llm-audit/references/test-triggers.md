# Test Triggers for cross-llm-audit Skill

## Positive Triggers (MUST activate the skill)

These prompts touch pipeline code and MUST cause Claude to load
the cross-llm-audit skill before implementing any changes.

### 1. AV Sync Fix
> "Fix the AV sync drift in clip_extractor.py -- clips are 40ms out of sync"

Why it triggers: clip_extractor.py is in video_pipeline_v3/,
which is explicitly listed in the skill description.

### 2. Assembler Refactor
> "Refactor render_narrator.py to reduce duplicate filter graphs"

Why it triggers: render_narrator is explicitly named in the skill
description as a trigger file. Any refactor of pipeline modules
requires the audit.

### 3. TTS Pronunciation
> "Patch the TTS pronunciation map in tts_engine.py to fix 'Satoshi' mispronunciation"

Why it triggers: tts_engine is explicitly named in the skill
description. Any patch to pipeline code triggers the audit.

## Negative Triggers (MUST NOT activate the skill)

These prompts do NOT touch pipeline code and must NOT load the skill.

### 1. Homepage Content
> "Update the homepage hero copy to say 'Bitcoin Intelligence, Delivered'"

Why it does NOT trigger: website content writes are explicitly
excluded in the skill description ("Do NOT use for website route
edits, content writes, doc updates, or pure git ops").

### 2. Blog Post
> "Write a blog post about node monitoring best practices"

Why it does NOT trigger: doc/content creation is explicitly
excluded. No pipeline code is touched.

## Verification Procedure

To verify the skill is registered correctly and will trigger
on the right prompts:

1. Ask Claude: "When would you use the cross-llm-audit skill?"
2. Compare the echoed description to the registered one in SKILL.md
3. The response should mention:
   - video_pipeline_v3/ directory
   - oracle/, services/, core/ directories
   - Specific files: daily_producer, assembler, clip_selector, etc.
   - The exclusions: website routes, content writes, doc updates, git ops
4. Test with each positive prompt above -- skill should load
5. Test with each negative prompt above -- skill should NOT load

## Edge Cases

| Prompt | Should Trigger? | Why |
|--------|----------------|-----|
| "Add a new route to core/routes_api.py" | NO | Website route edit |
| "Fix a bug in services/tweet_machine.py" | YES | services/ is in scope |
| "Update PIPELINE_LAWS.md" | NO | Doc update only |
| "Optimize clip_selector.py query" | YES | Pipeline code |
| "Change the git commit message format" | NO | Pure git ops |
| "Add a new skill definition" | YES | Skill definitions in scope |
