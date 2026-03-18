import sys, tempfile, json, logging
from pathlib import Path
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, '/home/ultron/protocol_pulse/video_pipeline_v3')
from assembler_v2.segments.social import SocialSegment
from assembler_v2.segments.signal_active import SignalActiveSegment
from assembler_v2.manifest import SegmentSpec
from assembler_v2.state import EpisodeContext
from assembler_v2.helpers import ffprobe_duration, ffprobe_contract, run_ffmpeg
from assembler_v2.constants import AUDIO_SAMPLE_RATE

results = []
def test(name, fn):
    try:
        fn()
        results.append(('PASS', name))
        print(f'  PASS  {name}')
    except Exception as e:
        results.append(('FAIL', name, str(e)))
        print(f'  FAIL  {name}: {e}')

def make_tts(tmpdir, dur=3.0):
    p = Path(tmpdir) / 'tts.m4a'
    run_ffmpeg(['-f', 'lavfi', '-i', f'sine=frequency=440:duration={dur}',
                '-c:a', 'aac', '-ar', str(AUDIO_SAMPLE_RATE), '-b:a', '128k', '-ac', '1',
                str(p)], 'test tts', 30)
    return p

POSTS_3 = [
    {'account': '@satoshi', 'text': 'Bitcoin fixes this', 'timestamp': '2h ago', 'likes': 100, 'retweets': 50},
    {'account': '@hal', 'text': 'Running bitcoin', 'timestamp': '4h ago', 'likes': 200, 'retweets': 80},
    {'account': '@adam', 'text': 'Hashcash to Bitcoin', 'timestamp': '6h ago', 'likes': 150, 'retweets': 60},
]

SIGNAL_DATA = {
    'nostr_posts': [{
        'text': 'Bitcoin mining with renewable energy is the future',
        'display_name': 'npub1test',
        'score': 90,
        'relay': 'wss://relay.damus.io',
        'created_at': 1773826716,
        'pubkey': 'abc123',
        'has_zap': False,
    }]
}

# Test 1: SocialSegment renders 3 posts successfully (account/retweets keys)
def t1():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        tts = make_tts(d, 5.0)
        spec = SegmentSpec(segment_type='social', social_posts=POSTS_3,
                           tts_path=str(tts), duration_hint=ffprobe_duration(tts))
        r = SocialSegment().render(spec, ctx, ctx.segment_dir() / 'social3.mp4', 0)
        assert r.path, f'no output: {r.error}'
        ok, s = ffprobe_contract(Path(r.path))
        assert ok, f'contract: {s.get("issues")}'
        assert s['width'] == 1920
        print(f'    dur={round(ffprobe_duration(Path(r.path)), 1)}s contract=PASS 3posts')
test('SocialSegment renders 3 posts (account/retweets keys)', t1)

# Test 2: SocialSegment returns filler on empty social_posts
def t2():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        spec = SegmentSpec(segment_type='social', social_posts=[])
        r = SocialSegment().render(spec, ctx, ctx.segment_dir() / 'empty.mp4', 0)
        assert r is not None
        assert r.degraded, 'should be degraded for empty posts'
        assert 'no_social_posts' in r.error
        print(f'    degraded={r.degraded} error={r.error}')
test('SocialSegment filler on empty social_posts', t2)

# Test 3: SocialSegment returns filler on None social_posts
def t3():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        spec = SegmentSpec(segment_type='social', social_posts=None)
        r = SocialSegment().render(spec, ctx, ctx.segment_dir() / 'none.mp4', 0)
        assert r is not None
        assert r.degraded
        print(f'    degraded={r.degraded}')
test('SocialSegment filler on None social_posts', t3)

# Test 4: SocialSegment handles 1 post without crashing
def t4():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        tts = make_tts(d, 3.0)
        spec = SegmentSpec(segment_type='social', social_posts=[POSTS_3[0]],
                           tts_path=str(tts), duration_hint=ffprobe_duration(tts))
        r = SocialSegment().render(spec, ctx, ctx.segment_dir() / 'social1.mp4', 0)
        assert r.path, f'no output: {r.error}'
        ok, s = ffprobe_contract(Path(r.path))
        assert ok, f'contract: {s.get("issues")}'
        print(f'    dur={round(ffprobe_duration(Path(r.path)), 1)}s 1post contract=PASS')
test('SocialSegment renders 1 post without crashing', t4)

# Test 5: SignalActiveSegment renders with valid nostr_posts[0] + sponsor always present
def t5():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        tts = make_tts(d, 5.0)
        spec = SegmentSpec(segment_type='signal_active', signal_content=SIGNAL_DATA,
                           tts_path=str(tts), duration_hint=ffprobe_duration(tts))
        r = SignalActiveSegment().render(spec, ctx, ctx.segment_dir() / 'sig.mp4', 0)
        assert r.path, f'no output: {r.error}'
        ok, s = ffprobe_contract(Path(r.path))
        assert ok, f'contract: {s.get("issues")}'
        print(f'    dur={round(ffprobe_duration(Path(r.path)), 1)}s signal+sponsor contract=PASS')
test('SignalActiveSegment renders signal + sponsor', t5)

# Test 6: SignalActiveSegment NO SIGNAL + sponsor on missing/empty cache
def t6():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        tts = make_tts(d, 5.0)
        spec = SegmentSpec(segment_type='signal_active', signal_content={'nostr_posts': []},
                           tts_path=str(tts), duration_hint=ffprobe_duration(tts))
        r = SignalActiveSegment().render(spec, ctx, ctx.segment_dir() / 'sig_empty.mp4', 0)
        assert r.path, f'no output: {r.error}'
        ok, s = ffprobe_contract(Path(r.path))
        assert ok, f'contract: {s.get("issues")}'
        print(f'    dur={round(ffprobe_duration(Path(r.path)), 1)}s NO_SIGNAL+sponsor contract=PASS')
test('SignalActiveSegment NO SIGNAL + sponsor on empty cache', t6)

# Test 7: SignalActiveSegment returns filler on render failure, not exception
def t7():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        spec = SegmentSpec(segment_type='signal_active')
        r = SignalActiveSegment().render(spec, ctx, ctx.segment_dir() / 'sig_law1.mp4', 0)
        assert r is not None, 'render returned None (Law 1 violation)'
        print(f'    degraded={r.degraded} path={r.path is not None}')
test('SignalActiveSegment never raises (Law 1)', t7)

passes = sum(1 for r in results if r[0] == 'PASS')
fails = sum(1 for r in results if r[0] == 'FAIL')
print(f'\nDay 5: {passes}/{len(results)} PASSED')
if fails:
    for r in results:
        if r[0] == 'FAIL':
            print(f'  FAIL: {r[1]} - {r[2]}')
    sys.exit(1)
else:
    print('ALL TESTS PASSED - Day 5 social + signal_active solid.')
