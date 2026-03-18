import sys,tempfile,logging
from pathlib import Path
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0,"/home/ultron/protocol_pulse/video_pipeline_v3")
from assembler_v2.segments.partner_clip import PartnerClipSegment
from assembler_v2.helpers import safe_text
from assembler_v2.segments.data_segment import DataSegment
from assembler_v2.manifest import SegmentSpec
from assembler_v2.state import EpisodeContext
from assembler_v2.helpers import ffprobe_duration,ffprobe_contract,run_ffmpeg
from assembler_v2.constants import AUDIO_SAMPLE_RATE
results=[]
def test(name,fn):
    try:
        fn()
        results.append(("PASS",name))
        print("  PASS  "+name)
    except Exception as e:
        results.append(("FAIL",name,str(e)))
        print("  FAIL  "+name+": "+str(e))
def mclip(d,dur=5,audio=True):
    p=Path(d)/"c.mp4"
    a=["-f","lavfi","-i","testsrc=size=1280x720:rate=30:duration="+str(dur)]
    if audio: a+=["-f","lavfi","-i","sine=frequency=440:duration="+str(dur),"-c:v","libx264","-crf","30","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-ar",str(AUDIO_SAMPLE_RATE),"-b:a","128k","-ac","1",str(p)]
    else: a+=["-c:v","libx264","-crf","30","-preset","veryfast","-pix_fmt","yuv420p","-an",str(p)]
    run_ffmpeg(a,"c",30); return p
def mtts(d,dur=3):
    p=Path(d)/"t.m4a"
    run_ffmpeg(["-f","lavfi","-i","sine=frequency=440:duration="+str(dur),"-c:a","aac","-ar",str(AUDIO_SAMPLE_RATE),"-b:a","128k","-ac","1",str(p)],"t",30)
    return p
def t1():
    assert PartnerClipSegment.criticality=="required"
    assert DataSegment.criticality=="optional"
test("imports and criticality",t1)
def t2():
    with tempfile.TemporaryDirectory() as d:
        ctx=EpisodeContext.create("20260318",Path(d))
        r=PartnerClipSegment().render(SegmentSpec(segment_type="partner_clip",clip_rank=1),ctx,ctx.segment_dir()/"x.mp4",0)
        assert r is not None; print("    degraded="+str(r.degraded))
test("PartnerClip no-crash missing clip",t2)
def t3():
    with tempfile.TemporaryDirectory() as d:
        ctx=EpisodeContext.create("20260318",Path(d))
        c=mclip(d)
        spec=SegmentSpec(segment_type="partner_clip",clip_rank=1,headline="Simply Bitcoin",clip_path=str(c))
        r=PartnerClipSegment().render(spec,ctx,ctx.segment_dir()/"p.mp4",0)
        assert r.path,"no output: "+str(r.error)
        ok,s=ffprobe_contract(Path(r.path))
        assert ok,"contract: "+str(s.get("issues"))
        assert s["width"]==1920; print("    1920x1080 contract=PASS dur="+str(round(ffprobe_duration(Path(r.path)),1))+"s")
test("PartnerClip renders 1920x1080",t3)
def t4():
    with tempfile.TemporaryDirectory() as d:
        ctx=EpisodeContext.create("20260318",Path(d))
        c=mclip(d,5,False)
        spec=SegmentSpec(segment_type="partner_clip",clip_rank=1,headline="test",clip_path=str(c))
        r=PartnerClipSegment().render(spec,ctx,ctx.segment_dir()/"p.mp4",0)
        assert r.path; ok,s=ffprobe_contract(Path(r.path))
        assert ok,"contract: "+str(s.get("issues")); print("    silence_added contract=PASS")
test("PartnerClip adds silence for audio-less clip",t4)
def t5():
    with tempfile.TemporaryDirectory() as d:
        ctx=EpisodeContext.create("20260318",Path(d))
        r=DataSegment().render(SegmentSpec(segment_type="data",headline="Price"),ctx,ctx.segment_dir()/"x.mp4",0)
        assert r is not None; print("    degraded="+str(r.degraded))
test("DataSegment no-crash missing TTS",t5)
def t6():
    with tempfile.TemporaryDirectory() as d:
        ctx=EpisodeContext.create("20260318",Path(d))
        tts=mtts(d)
        spec=SegmentSpec(segment_type="data",headline="BTC hashrate ATH",body="miners printing",chart_keyword="hashrate",tts_path=str(tts),duration_hint=ffprobe_duration(tts))
        r=DataSegment().render(spec,ctx,ctx.segment_dir()/"ds.mp4",0)
        assert r.path,"no output: "+str(r.error)
        ok,s=ffprobe_contract(Path(r.path))
        assert ok,"contract: "+str(s.get("issues"))
        print("    dur="+str(round(ffprobe_duration(Path(r.path)),1))+"s contract=PASS")
test("DataSegment renders contract-compliant",t6)
def t7():
    # safe_text escapes ' as '\'' for FFmpeg drawtext
    assert "'\\''" in safe_text("It's alive",40)
    assert chr(92)+chr(58) in safe_text("time: 5pm",40)
    assert len(safe_text("a"*100,40))<=40
test("safe_text sanitizes (consolidated from _safe_label)",t7)
p=sum(1 for r in results if r[0]=="PASS")
f=sum(1 for r in results if r[0]=="FAIL")
print("Day 4: "+str(p)+"/"+str(len(results))+" PASSED")
if f: [print("  FAIL: "+r[1]+" - "+r[2]) for r in results if r[0]=="FAIL"]; import sys; sys.exit(1)
else: print("ALL TESTS PASSED - Day 4 solid.")
