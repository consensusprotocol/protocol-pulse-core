#!/usr/bin/env python3
"""Day 6 self-test for assembler_v2 episode runner."""
import sys, tempfile, logging, os
from pathlib import Path
from unittest.mock import patch
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, '/home/ultron/protocol_pulse/video_pipeline_v3')
os.chdir(Path('/home/ultron/protocol_pulse/video_pipeline_v3'))

from assembler_v2.episode import EpisodeRunner, EpisodeReport, SEGMENT_MAP
from assembler_v2.manifest import EpisodeManifest, SegmentSpec, RenderedSegment
from assembler_v2.state import EpisodeContext
from assembler_v2.helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract
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

def _mock_preflight(*a, **kw):
    return {'passed': True, 'critical_failures': [], 'warnings': [], 'checks': {}}

def make_minimal_manifest(tmpdir):
    """Build a minimal valid manifest with a cold_open segment + TTS."""
    tts = make_tts(tmpdir, 3.0)
    m = EpisodeManifest(date_str='20260318', title='Test Episode', btc_price='$74,000')
    m.segments.append(SegmentSpec(
        segment_type='cold_open', headline='Test Cold Open',
        tts_path=str(tts), duration_hint=3.0,
    ))
    return m


# Test 1: EpisodeRunner.run() returns EpisodeReport with output_path on valid manifest
def t1():
    with tempfile.TemporaryDirectory() as d:
        m = make_minimal_manifest(d)
        with patch('assembler_v2.episode.run_preflight', _mock_preflight):
            report = EpisodeRunner().run(m, Path(d))
        assert isinstance(report, EpisodeReport), f'wrong type: {type(report)}'
        assert report.output_path is not None, f'no output: {report.error}'
        assert report.output_path.exists(), f'output missing: {report.output_path}'
        assert report.output_path.stat().st_size > 1000
        print(f'    output={report.output_path.name} verdict={report.verdict}')
test('EpisodeRunner returns EpisodeReport with output_path', t1)


# Test 2: EpisodeRunner returns verdict=HOLD (not raise) when preflight fails
def t2():
    with tempfile.TemporaryDirectory() as d:
        m = EpisodeManifest(date_str='20260318', title='Test')
        m.segments.append(SegmentSpec(
            segment_type='cold_open',
            tts_path='/nonexistent/fake_tts.m4a',
            duration_hint=5.0,
        ))
        report = EpisodeRunner().run(m, Path(d))
        assert isinstance(report, EpisodeReport)
        assert report.verdict == 'HOLD', f'verdict={report.verdict}'
        assert report.error, 'error should be populated'
        print(f'    verdict={report.verdict} error={report.error[:80]}')
test('EpisodeRunner HOLD on preflight failure (no raise)', t2)


# Test 3: EpisodeRunner.run() never raises — catch all exceptions, return HOLD
def t3():
    with tempfile.TemporaryDirectory() as d:
        m = make_minimal_manifest(d)
        with patch.object(EpisodeRunner, '_run', side_effect=RuntimeError('catastrophic')):
            report = EpisodeRunner().run(m, Path(d))
        assert isinstance(report, EpisodeReport)
        assert report.verdict == 'HOLD'
        assert 'catastrophic' in report.error
        print(f'    verdict={report.verdict} error={report.error}')
test('EpisodeRunner never raises — catch all, return HOLD', t3)


# Test 4: Unknown segment_type produces filler + marks degraded, no crash
def t4():
    with tempfile.TemporaryDirectory() as d:
        tts = make_tts(d, 3.0)
        m = EpisodeManifest(date_str='20260318', title='Test')
        m.segments.append(SegmentSpec(
            segment_type='cold_open', headline='Intro',
            tts_path=str(tts), duration_hint=3.0,
        ))
        m.segments.append(SegmentSpec(
            segment_type='mystery_segment',
        ))
        with patch('assembler_v2.episode.run_preflight', _mock_preflight):
            report = EpisodeRunner().run(m, Path(d))
        assert isinstance(report, EpisodeReport)
        assert report.degraded_count >= 1, f'degraded_count={report.degraded_count}'
        degraded_segs = [r for r in report.segment_reports if r.degraded]
        assert len(degraded_segs) >= 1
        assert 'unknown' in degraded_segs[-1].error.lower()
        print(f'    degraded_count={report.degraded_count} segs={len(report.segment_reports)}')
test('Unknown segment_type produces filler + degraded (no crash)', t4)


# Test 5: EpisodeReport.contract_passed reflects ffprobe_contract result
def t5():
    with tempfile.TemporaryDirectory() as d:
        m = make_minimal_manifest(d)
        with patch('assembler_v2.episode.run_preflight', _mock_preflight):
            report = EpisodeRunner().run(m, Path(d))
        assert isinstance(report, EpisodeReport)
        if report.output_path and report.output_path.exists():
            ok, _ = ffprobe_contract(report.output_path)
            assert report.contract_passed == ok, \
                f'contract_passed={report.contract_passed} but ffprobe says {ok}'
        print(f'    contract_passed={report.contract_passed}')
test('EpisodeReport.contract_passed reflects ffprobe_contract', t5)


# Test 6: Manifest with all 8 segment types dispatches each to correct class
def t6():
    all_types = ['cold_open', 'narration', 'partner_clip', 'transition',
                 'data', 'social', 'signal_active', 'wrap']
    for st in all_types:
        assert st in SEGMENT_MAP, f'{st} not in SEGMENT_MAP'
    assert len(SEGMENT_MAP) == 8, f'SEGMENT_MAP has {len(SEGMENT_MAP)} entries, expected 8'
    print(f'    all 8 types mapped: {sorted(SEGMENT_MAP.keys())}')
test('All 8 segment types in SEGMENT_MAP', t6)


# Test 7: EpisodeReport.elapsed_seconds is populated and > 0
def t7():
    with tempfile.TemporaryDirectory() as d:
        m = make_minimal_manifest(d)
        with patch('assembler_v2.episode.run_preflight', _mock_preflight):
            report = EpisodeRunner().run(m, Path(d))
        assert report.elapsed_seconds > 0, f'elapsed={report.elapsed_seconds}'
        print(f'    elapsed_seconds={report.elapsed_seconds:.3f}')
test('EpisodeReport.elapsed_seconds populated and > 0', t7)


# Test 8: Concat output path follows naming convention: date_str + episode_id + _episode.mp4
def t8():
    with tempfile.TemporaryDirectory() as d:
        m = make_minimal_manifest(d)
        with patch('assembler_v2.episode.run_preflight', _mock_preflight):
            report = EpisodeRunner().run(m, Path(d))
        assert report.output_path is not None, f'no output: {report.error}'
        name = report.output_path.name
        assert name.startswith('20260318_'), f'name does not start with date: {name}'
        assert name.endswith('_episode.mp4'), f'name does not end with _episode.mp4: {name}'
        assert report.episode_id in name, f'episode_id not in name: {name}'
        print(f'    filename={name}')
test('Concat output follows naming convention', t8)


passes = sum(1 for r in results if r[0] == 'PASS')
fails = sum(1 for r in results if r[0] == 'FAIL')
print(f'\nDay 6: {passes}/{len(results)} PASSED')
if fails:
    for r in results:
        if r[0] == 'FAIL':
            print(f'  FAIL: {r[1]} - {r[2]}')
    sys.exit(1)
else:
    print('ALL TESTS PASSED - Day 6 episode runner solid.')
