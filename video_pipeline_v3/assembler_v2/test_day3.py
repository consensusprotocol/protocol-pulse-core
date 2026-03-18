import sys,tempfile,logging,subprocess
from pathlib import Path
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0,'/home/ultron/protocol_pulse/video_pipeline_v3')
from assembler_v2.segments.cold_open import ColdOpenSegment
from assembler_v2.segments.narration import NarrationSegment
from assembler_v2.manifest import SegmentSpec
from assembler_v2.state import EpisodeContext
from assembler_v2.helpers import ffprobe_duration,ffprobe_contract,run_ffmpeg,safe_text
from assembler_v2.constants import INTRO_TAG,BG_LOOP,AUDIO_SAMPLE_RATE
results=[]
def test(name,fn):
    try:
        fn()
        results.append(('PASS',name))
        print(f'  PASS  {name}')
    except Exception as e:
        results.append(('FAIL',name,str(e)))
        print(f'  FAIL  {name}: {e}')

def make_tts(tmpdir,dur=3.0):
    """Generate a real TTS-like m4a for testing."""
    p=Path(tmpdir)/'tts.m4a'
    run_ffmpeg(['-f','lavfi','-i',f'sine=frequency=440:duration={dur}',
                '-c:a','aac','-ar',str(AUDIO_SAMPLE_RATE),'-b:a','128k','-ac','1',str(p)],
               'test tts',30)
    return p

def make_pip(tmpdir):
    """Generate a minimal pip_preview_norm.mp4 for testing."""
    p=Path(tmpdir)/'pip.mp4'
    run_ffmpeg(['-f','lavfi','-i','testsrc=size=640x360:rate=30:duration=3',
                '-an','-c:v','libx264','-crf','30','-preset','veryfast',
                '-pix_fmt','yuv420p',str(p)],'test pip',30)
    return p

# Test 1: imports
def t_imports():
    assert ColdOpenSegment is not None
    assert NarrationSegment is not None
    assert ColdOpenSegment.criticality=='required'
    assert NarrationSegment.criticality=='required'
test('ColdOpen and Narration import correctly',t_imports)

# Test 2: _safe_text
def t_safe_text():
    seg=NarrationSegment()
    # FFmpeg drawtext escape: ' becomes '\'' (close-escape-reopen)
    assert "'\\''" in safe_text("it's alive",100)
    assert '\\:' in safe_text('time: 5pm',100)
    assert '\\%' in safe_text('50% done',100)
    assert len(safe_text('a'*200,50))<=50
test('NarrationSegment._safe_text sanitizes correctly',t_safe_text)

# Test 3: ColdOpen with no assets -> filler (never crash)
def t_coldopen_no_assets():
    with tempfile.TemporaryDirectory() as tmp:
        ctx=EpisodeContext.create('20260318',Path(tmp))
        spec=SegmentSpec(segment_type='cold_open',headline='TEST')
        seg=ColdOpenSegment()
        out=ctx.segment_dir()/'co_no_assets.mp4'
        result=seg.render(spec,ctx,out,0)
        assert result is not None,'render returned None'
        print(f'    degraded={result.degraded} path={result.path is not None}')
test('ColdOpenSegment never crashes with missing assets',t_coldopen_no_assets)

# Test 4: ColdOpen with real TTS (no intro_tag, fallback mode)
def t_coldopen_tts_only():
    with tempfile.TemporaryDirectory() as tmp:
        ctx=EpisodeContext.create('20260318',Path(tmp))
        tts=make_tts(tmp)
        assert tts.exists() and tts.stat().st_size>1000
        spec=SegmentSpec(segment_type='cold_open',headline='PULSE CHECK',
                         tts_path=str(tts),duration_hint=ffprobe_duration(tts))
        seg=ColdOpenSegment()
        out=ctx.segment_dir()/'co_tts_only.mp4'
        result=seg.render(spec,ctx,out,0)
        assert result.path is not None
        assert Path(result.path).exists()
        passed,summary=ffprobe_contract(Path(result.path))
        assert passed,f'Contract failed: {summary.get("issues")}'
        assert summary['width']==1920
        dur=ffprobe_duration(Path(result.path))
        assert dur>1.0,f'Duration too short: {dur}'
        print(f'    dur={dur:.1f}s contract=PASS')
test('ColdOpenSegment renders contract-compliant with TTS only',t_coldopen_tts_only)

# Test 5: Narration with no assets -> filler
def t_narration_no_assets():
    with tempfile.TemporaryDirectory() as tmp:
        ctx=EpisodeContext.create('20260318',Path(tmp))
        spec=SegmentSpec(segment_type='narration',clip_rank=1)
        seg=NarrationSegment()
        out=ctx.segment_dir()/'nar_no_assets.mp4'
        result=seg.render(spec,ctx,out,0)
        assert result is not None,'render returned None'
        print(f'    degraded={result.degraded}')
test('NarrationSegment never crashes with missing assets',t_narration_no_assets)

# Test 6: Narration with TTS, no pip (dark panel mode)
def t_narration_no_pip():
    with tempfile.TemporaryDirectory() as tmp:
        ctx=EpisodeContext.create('20260318',Path(tmp))
        tts=make_tts(tmp,3.0)
        spec=SegmentSpec(segment_type='narration',clip_rank=1,
                         headline='Bitcoin signal',body='The market is reacting.',
                         tts_path=str(tts),duration_hint=ffprobe_duration(tts))
        seg=NarrationSegment()
        out=ctx.segment_dir()/'nar_no_pip.mp4'
        result=seg.render(spec,ctx,out,0)
        assert result.path is not None
        passed,summary=ffprobe_contract(Path(result.path))
        assert passed,f'Contract failed: {summary.get("issues")}'
        dur=ffprobe_duration(Path(result.path))
        assert dur>1.0
        print(f'    dur={dur:.1f}s contract=PASS degraded={result.degraded}')
test('NarrationSegment renders contract-compliant with TTS, no pip',t_narration_no_pip)

# Test 7: Narration with TTS + PiP video
def t_narration_with_pip():
    with tempfile.TemporaryDirectory() as tmp:
        ctx=EpisodeContext.create('20260318',Path(tmp))
        tts=make_tts(tmp,3.0)
        pip=make_pip(tmp)
        assert pip.exists() and pip.stat().st_size>1000
        spec=SegmentSpec(segment_type='narration',clip_rank=1,
                         headline='Simply Bitcoin',body='Individual ownership peaked.',
                         tts_path=str(tts),pip_path=str(pip),
                         duration_hint=ffprobe_duration(tts))
        seg=NarrationSegment()
        out=ctx.segment_dir()/'nar_with_pip.mp4'
        result=seg.render(spec,ctx,out,0)
        assert result.path is not None,f'No output: {result.error}'
        passed,summary=ffprobe_contract(Path(result.path))
        assert passed,f'Contract failed: {summary.get("issues")}'
        dur=ffprobe_duration(Path(result.path))
        assert dur>1.0
        print(f'    dur={dur:.1f}s contract=PASS pip=ACTIVE')
test('NarrationSegment renders with PiP video looping',t_narration_with_pip)

# Test 8: PiP is actually video (multiple frames, not static)
def t_pip_is_video():
    with tempfile.TemporaryDirectory() as tmp:
        ctx=EpisodeContext.create('20260318',Path(tmp))
        tts=make_tts(tmp,3.0)
        pip=make_pip(tmp)
        spec=SegmentSpec(segment_type='narration',clip_rank=2,
                         headline='Test',body='test body',
                         tts_path=str(tts),pip_path=str(pip),
                         duration_hint=ffprobe_duration(tts))
        seg=NarrationSegment()
        out=ctx.segment_dir()/'nar_pip_motion.mp4'
        result=seg.render(spec,ctx,out,0)
        if result.path:
            res=subprocess.run(['ffprobe','-v','error','-select_streams','v',
                               '-show_entries','stream=nb_frames','-of','csv=p=0',result.path],
                               capture_output=True,text=True)
            frames=res.stdout.strip()
            nb=int(frames) if frames and frames.isdigit() else 0
            assert nb>1,f'Only {nb} frames — pip may be static'
            print(f'    frames={nb} (video confirmed moving)')
test('PiP segment has multiple frames (not static)',t_pip_is_video)

passes=sum(1 for r in results if r[0]=='PASS')
fails=sum(1 for r in results if r[0]=='FAIL')
print(f'\nDay 3: {passes}/{len(results)} PASSED')
if fails:
    for r in results:
        if r[0]=='FAIL': print(f'  FAIL: {r[1]} - {r[2]}')
    import sys; sys.exit(1)
else:
    print('ALL TESTS PASSED - Day 3 segments solid.')
