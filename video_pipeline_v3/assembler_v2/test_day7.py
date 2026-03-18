#!/usr/bin/env python3
"""Day 7 self-test for assembler_v2 X Spaces segment."""
import sys, tempfile, logging, os
from pathlib import Path
from unittest.mock import patch, MagicMock
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, '/home/ultron/protocol_pulse/video_pipeline_v3')
os.chdir(Path('/home/ultron/protocol_pulse/video_pipeline_v3'))

from assembler_v2.episode import EpisodeRunner, EpisodeReport, SEGMENT_MAP
from assembler_v2.manifest import EpisodeManifest, SegmentSpec, RenderedSegment
from assembler_v2.state import EpisodeContext
from assembler_v2.segments.x_spaces_segment import XSpacesSegment

results = []

def test(name, fn):
    try:
        fn()
        results.append(('PASS', name))
        print(f'  PASS  {name}')
    except Exception as e:
        results.append(('FAIL', name, str(e)))
        print(f'  FAIL  {name}: {e}')


# Test 1: XSpacesSegment returns filler when spec.body is empty
def t1():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        spec = SegmentSpec(segment_type='x_spaces', body='', headline='X SPACES')
        out = ctx.segment_dir() / 'x_spaces_empty.mp4'
        seg = XSpacesSegment()
        result = seg.render(spec, ctx, out, 0)
        assert isinstance(result, RenderedSegment)
        assert result.degraded is True, f'degraded={result.degraded}'
        assert 'no_x_spaces_content' in result.error, f'error={result.error}'
test('XSpacesSegment filler on empty body', t1)


# Test 2: XSpacesSegment returns filler when spec.body is None
def t2():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        spec = SegmentSpec(segment_type='x_spaces', headline='X SPACES')
        # spec.body defaults to "" which is falsy
        out = ctx.segment_dir() / 'x_spaces_none.mp4'
        seg = XSpacesSegment()
        result = seg.render(spec, ctx, out, 0)
        assert isinstance(result, RenderedSegment)
        assert result.degraded is True
test('XSpacesSegment filler on None body', t2)


# Test 3: XSpacesSegment render() never raises
def t3():
    with tempfile.TemporaryDirectory() as d:
        ctx = EpisodeContext.create('20260318', Path(d))
        spec = SegmentSpec(segment_type='x_spaces', body='Test content', headline='X SPACES')
        out = ctx.segment_dir() / 'x_spaces_nocrash.mp4'
        seg = XSpacesSegment()
        try:
            result = seg.render(spec, ctx, out, 0)
            assert isinstance(result, RenderedSegment)
        except Exception as e:
            raise AssertionError(f'render() raised: {e}')
test('XSpacesSegment render() never raises', t3)


# Test 4: x_spaces in SEGMENT_MAP
def t4():
    assert 'x_spaces' in SEGMENT_MAP, f'x_spaces not in SEGMENT_MAP: {list(SEGMENT_MAP.keys())}'
    assert SEGMENT_MAP['x_spaces'] is XSpacesSegment
test('x_spaces in SEGMENT_MAP', t4)


# Test 5: EpisodeRunner dispatches x_spaces to XSpacesSegment
def t5():
    with tempfile.TemporaryDirectory() as d:
        m = EpisodeManifest(date_str='20260318', title='Test')
        m.segments.append(SegmentSpec(
            segment_type='x_spaces',
            body='Bitcoin discussion on X Spaces',
            headline='LIVE X SPACES SIGNAL',
        ))
        mock_result = RenderedSegment(
            spec=m.segments[0], path=None, duration=10.0,
            contract_passed=True, degraded=False,
        )
        with patch.object(XSpacesSegment, 'render', return_value=mock_result) as mock_render:
            with patch('assembler_v2.episode.run_preflight', return_value={'passed': True, 'critical_failures': [], 'warnings': [], 'checks': {}}):
                report = EpisodeRunner().run(m, Path(d))
        mock_render.assert_called_once()
        assert report.segment_reports[0] is mock_result
test('EpisodeRunner dispatches x_spaces to XSpacesSegment', t5)


# Test 6: XSpacesSegment uses safe_text — no raw escaping
def t6():
    seg_file = Path('/home/ultron/protocol_pulse/video_pipeline_v3/assembler_v2/segments/x_spaces_segment.py')
    code = seg_file.read_text()
    assert 'safe_text' in code, 'safe_text not found in x_spaces_segment.py'
    # Ensure no manual escaping bypasses (no chr(39) or _safe patterns)
    assert 'chr(39)' not in code, 'chr(39) found — must use safe_text() only'
    assert '_safe(' not in code, '_safe( found — must use safe_text() from helpers'
test('XSpacesSegment uses safe_text (no manual escaping)', t6)


passes = sum(1 for r in results if r[0] == 'PASS')
fails = sum(1 for r in results if r[0] == 'FAIL')
print(f'\nDay 7: {passes}/{len(results)} PASSED')
if fails:
    for r in results:
        if r[0] == 'FAIL':
            print(f'  FAIL: {r[1]} - {r[2]}')
    sys.exit(1)
else:
    print('ALL TESTS PASSED - Day 7 X Spaces segment solid.')
