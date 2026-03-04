# VIDEO PIPELINE REGRESSION TEST — MANDATORY BEFORE EVERY COMMIT

## RULE: NO COMMIT UNTIL ALL CHECKS PASS
Run this checklist after EVERY change to assembler.py, script_writer.py, tts_engine.py, clip_extractor.py, or daily_producer.py. If ANY check fails, fix it before committing. Do NOT commit partial work that regresses existing features.

## HOW TO RUN
```bash
cd ~/protocol_pulse/video_pipeline_v3
python3 daily_producer.py --test --skip-scan 2>&1 | tee /tmp/pipeline_test.log
```
Then run verification:
```bash
bash ~/protocol_pulse/video_pipeline_v3/regression_test.sh
```

---

## AUTOMATED CHECKS (regression_test.sh runs these)

### 1. OUTPUT EXISTS
```bash
LATEST=$(ls -td output/test_* | head -1)
[ -f "$LATEST/pulse_check_*.mp4" ] || echo "FAIL: No final video"
[ -f "$LATEST/script.json" ] || echo "FAIL: No script"
[ -d "$LATEST/work" ] || echo "FAIL: No work directory"
```

### 2. VIDEO SPECS
```bash
FINAL="$LATEST/pulse_check_*.mp4"
# Resolution must be 1920x1080
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 $FINAL | grep -q "1920,1080" || echo "FAIL: Not 1920x1080"
# Pixel format must be yuv420p
ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt -of csv=p=0 $FINAL | grep -q "yuv420p" || echo "FAIL: Not yuv420p"
# Has audio
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 $FINAL | grep -q "aac" || echo "FAIL: No AAC audio"
# Duration > 30s (even test mode should produce 30s+)
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $FINAL | cut -d. -f1)
[ "$DUR" -gt 30 ] || echo "FAIL: Duration too short ($DUR s)"
```

### 3. PARTS STRUCTURE — ALL REQUIRED PARTS PRESENT
```bash
WORK="$LATEST/work"
# Cold open MUST exist
ls $WORK/part_*cold_open* >/dev/null 2>&1 || echo "FAIL: No cold open part"
# At least 1 clip
ls $WORK/part_*clip* >/dev/null 2>&1 || echo "FAIL: No clip parts"
# At least 1 setup (narrator intro before clip)
ls $WORK/part_*setup* >/dev/null 2>&1 || echo "FAIL: No setup parts"
# At least 1 react (narrator after clip)
ls $WORK/part_*react* >/dev/null 2>&1 || echo "FAIL: No react parts"
# Glitch transitions
ls $WORK/part_*glitch* >/dev/null 2>&1 || echo "FAIL: No glitch transitions"
# Wrap (closing line)
ls $WORK/part_*wrap* >/dev/null 2>&1 || echo "FAIL: No wrap part"
# Outro
ls $WORK/part_*outro* >/dev/null 2>&1 || echo "FAIL: No outro part"
```

### 4. NO BLACK FRAMES — VERIFY VISUAL CONTENT
```bash
# Check each part has real video (file size > 100KB minimum)
for f in $WORK/part_*.mp4; do
    SZ=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
    if [ "$SZ" -lt 100000 ]; then
        echo "FAIL: $f is only ${SZ} bytes — likely black/empty"
    fi
done

# Intro specifically — must not be black
INTRO=$(ls $WORK/part_000* 2>/dev/null | head -1)
if [ -n "$INTRO" ]; then
    INTRO_SZ=$(stat -c%s "$INTRO" 2>/dev/null || stat -f%z "$INTRO" 2>/dev/null)
    [ "$INTRO_SZ" -gt 500000 ] || echo "FAIL: Intro too small — likely black screen"
fi
```

### 5. THUMBNAIL OVERLAYS — VERIFY THUMBNAILS FETCHED
```bash
# Check that YouTube thumbnails were downloaded for clips
THUMB_COUNT=$(ls /tmp/thumb_*.jpg 2>/dev/null | wc -l)
CLIP_COUNT=$(ls $WORK/part_*clip* 2>/dev/null | wc -l)
[ "$THUMB_COUNT" -ge "$CLIP_COUNT" ] || echo "FAIL: Only $THUMB_COUNT thumbnails for $CLIP_COUNT clips — thumbnails missing from narrator segments"
```

### 6. AUDIO SYNC — CLIPS HAVE MATCHING AUDIO
```bash
# Each clip part must have audio stream
for f in $WORK/part_*clip*.mp4; do
    HAS_AUD=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$f" 2>/dev/null)
    [ "$HAS_AUD" = "audio" ] || echo "FAIL: $f has no audio — clip will be silent"
done
```

### 7. VOICE VERIFICATION — CORRECT VOICE IDS
```bash
# Check tts_engine.py has the right voice IDs (American English, not British)
grep -q "XB0fDUnXU5powFXDhCwa\|VeCVR24o7g2y1IxLJzZs\|FyrYFW3P9GUxA348YGWu" tts_engine.py && echo "WARN: Verify voice is American English — Charlotte/Deborah/Madison"
# Check voice_settings has stability set
grep -q "stability" tts_engine.py || echo "FAIL: No voice_settings with stability — moaning artifact risk"
```

### 8. SCRIPT QUALITY — VERIFY TONE AND STRUCTURE
```bash
SCRIPT="$LATEST/script.json"
# Must have cold_open
python3 -c "import json; d=json.load(open('$SCRIPT')); assert d.get('cold_open'), 'No cold_open'" 2>&1 || echo "FAIL: No cold_open in script"
# Must have dialogue array
python3 -c "import json; d=json.load(open('$SCRIPT')); assert len(d.get('dialogue',[])) > 5, 'Too few dialogue entries'" 2>&1 || echo "FAIL: Dialogue too short"
# Must have CLIP entries
python3 -c "import json; d=json.load(open('$SCRIPT')); clips=[e for e in d.get('dialogue',[]) if e.get('host')=='CLIP']; assert len(clips) >= 1, f'Only {len(clips)} clips'" 2>&1 || echo "FAIL: No CLIP entries in dialogue"
# Setup lines should be short (< 200 chars each)
python3 -c "
import json
d=json.load(open('$SCRIPT'))
for e in d.get('dialogue',[]):
    if e.get('type') == 'setup' and len(e.get('text','')) > 200:
        print(f\"WARN: Setup line too long ({len(e['text'])} chars): {e['text'][:60]}...\")
" 2>&1
# React lines should be short (< 200 chars each)
python3 -c "
import json
d=json.load(open('$SCRIPT'))
for e in d.get('dialogue',[]):
    if e.get('type') == 'react' and len(e.get('text','')) > 200:
        print(f\"WARN: React line too long ({len(e['text'])} chars): {e['text'][:60]}...\")
" 2>&1
# Check for banned generic phrases
python3 -c "
import json
d=json.load(open('$SCRIPT'))
banned = ['let us dive in', 'without further ado', 'buckle up', 'game changer', 'really interesting', 'really impactful', 'great stuff']
for e in d.get('dialogue',[]):
    text = e.get('text','').lower()
    for b in banned:
        if b in text:
            print(f\"FAIL: Banned phrase '{b}' in: {e['text'][:60]}...\")
" 2>&1
```

### 9. NARRATOR DOES NOT OVERLAP CLIPS
```bash
# Verify no host audio parts directly adjacent to clip parts without a transition
python3 -c "
import os, glob
work = '$WORK'
parts = sorted(glob.glob(os.path.join(work, 'part_*.mp4')))
for i in range(len(parts)-1):
    curr = os.path.basename(parts[i])
    nxt = os.path.basename(parts[i+1])
    # Clip followed immediately by react (no glitch between) is OK
    # But setup followed immediately by clip with no glitch = missing transition
    if 'setup' in curr and 'clip' in nxt and 'glitch' not in nxt:
        print(f'WARN: {curr} -> {nxt} — no glitch transition between setup and clip')
" 2>&1
```

### 10. BACKGROUND MUSIC PRESENT
```bash
# Verify background music file exists and is referenced
[ -f "assets/music/pp_background.mp3" ] || echo "FAIL: Background music missing"
[ -f "assets/music/pp_intro.mp3" ] || echo "FAIL: Intro music missing"
[ -f "assets/music/pp_outro.mp3" ] || echo "FAIL: Outro music missing"
# Check assembler references music
grep -q "pp_background" assembler.py || echo "FAIL: assembler.py doesn't reference background music"
grep -q "pp_intro" assembler.py || echo "FAIL: assembler.py doesn't reference intro music"
```

### 11. GLITCH TRANSITION HAS AUDIO
```bash
GLITCH=$(ls $WORK/part_*glitch* 2>/dev/null | head -1)
if [ -n "$GLITCH" ]; then
    HAS_AUD=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$GLITCH" 2>/dev/null)
    [ "$HAS_AUD" = "audio" ] || echo "FAIL: Glitch transition has no audio — woosh missing"
    # Check volume is audible (not silent)
    VOL=$(ffmpeg -i "$GLITCH" -af "volumedetect" -f null - 2>&1 | grep mean_volume | grep -oP '[-0-9.]+')
    if [ -n "$VOL" ]; then
        VOLINT=$(echo "$VOL" | cut -d. -f1 | tr -d -)
        [ "$VOLINT" -lt 50 ] || echo "FAIL: Glitch audio mean_volume=$VOL — too quiet"
    fi
fi
```

---

## MANUAL CHECKS (human must verify after watching)
After downloading and watching the video, confirm:

- [ ] Intro: Music plays, strong vocal hook opens the video
- [ ] Cold open is 1 explosive sentence, not a paragraph
- [ ] Host narration has animated background (NOT plain dark card)
- [ ] YouTube thumbnails visible during setup/react segments
- [ ] Glitch woosh is AUDIBLE between segments
- [ ] Clips play FULL SCREEN with ORIGINAL audio
- [ ] Clips are NOT cut off mid-sentence at start or end
- [ ] Narrator does NOT talk over clip audio (no overlap)
- [ ] Narrator tone is MMA-gossip, not generic news anchor
- [ ] Both voices are AMERICAN ENGLISH (no British accent)
- [ ] Background music audible but quiet under narration
- [ ] Outro plays with fade, video ends cleanly (no hard cut, no black)
- [ ] No black frames or dead air anywhere in the video
- [ ] Social segment present (tweets/Nostr posts) — at minimum placeholder
- [ ] BTC price ticker visible during host segments

---

## HOW TO USE THIS

### For Claude Code sessions:
Paste at the END of every fix prompt:
```
BEFORE COMMITTING: Run ~/protocol_pulse/video_pipeline_v3/regression_test.sh
and paste the full output. Fix ANY failures before git commit.
Do NOT commit if any check says FAIL.
```

### For the human (PBX):
After downloading every test render, go through the MANUAL CHECKS section.
If anything fails, report it with the specific check name so the fix is targeted.

### Git commit rule:
```bash
# ONLY after regression_test.sh passes with zero FAILs:
git add -A && git commit -m "feat: [description] — regression test PASSED" && git push origin main
```

---

## VERSION HISTORY
- v1.0 (2026-03-04): Initial checklist after V7→V8 regression (thumbnails dropped, waveform missing)
- Covers: video specs, parts structure, thumbnails, audio sync, voice, script quality, narrator overlap, music, transitions
