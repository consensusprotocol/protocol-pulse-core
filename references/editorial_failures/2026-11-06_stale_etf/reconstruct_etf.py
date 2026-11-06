"""Post-run forensic reconstruction of the stale-ETF emergent candidate from
runs/fresh_20261106_174439 (read-only use of pipeline modules; no code changes).
Universe = transcripts acquired before run start (17:44:39 UTC) and published within 72 h of it."""
import glob, json, os, sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '/home/ultron/protocol_pulse/pipeline')
import numpy as np
import transcript_store as ts, story_semantics as sm, editorial_select as es
RUN_START = datetime(2026, 11, 6, 17, 44, 39, tzinfo=timezone.utc)
OUT = '/home/ultron/protocol_pulse/references/editorial_failures/2026-11-06_stale_etf'
os.makedirs(OUT, exist_ok=True)
reg = {c['channel_id']: c for c in json.load(open(es.CHANNELS_PATH)) if c.get('channel_id')}
recs = []
for d in sorted(glob.glob(ts.TRANSCRIPTS_DIR + '/*')):
    vid = os.path.basename(d)
    if vid in es.V2F_VIDEO_IDS:
        continue
    files = [f for f in glob.glob(d + '/transcript.*.json') if 'whisper_words' not in f]
    cands = []
    for f in files:
        r = json.load(open(f))
        if datetime.fromisoformat(r['acquired_at']) < RUN_START:
            cands.append(r)
    if not cands:
        continue
    r = max(cands, key=lambda r: ts.METHOD_RANK.get(r['transcript_method'].split(':')[0], 0))
    pub = datetime.fromisoformat(r['published_at'].replace('Z', '+00:00')) if r.get('published_at') else None
    if pub is None or not (timedelta(0) <= RUN_START - pub <= timedelta(hours=72)):
        continue
    r['_age_h'] = round((RUN_START - pub).total_seconds() / 3600, 1)
    recs.append(r)
print('reconstructed universe transcripts:', len(recs), '(run reported 105)')
E = sm.Embedder()
chunks, vecs = [], []
for r in recs:
    cs = ts.chunks(r)
    _, vv = E.chunk_vectors(r, cs)
    for c in cs:
        c['age_h'] = r['_age_h']
        c['layout_eligible'] = es.layout_eligible(reg.get(r['channel_id'], {}))
    chunks += cs; vecs.append(vv)
vecs = np.vstack(vecs)
print('chunks:', len(chunks), '(run reported 4908)')
L = sm.LocalLLM().start()
today = RUN_START.strftime('%Y-%m-%d')
groups = sm.emergent_clusters(chunks, vecs)
labels = []
etf = None
for g in groups:
    lab = sm.label_cluster(L, chunks, vecs, g, today)
    labels.append({'channels': g['channels'], 'n_chunks': len(g['chunk_idx']), 'label': lab})
    print('cluster', len(g['channels']), 'ch', len(g['chunk_idx']), 'chunks ->', lab.get('is_specific_event'), lab.get('headline'))
    if etf is None and 'etf' in (lab.get('headline') or '').lower() and 'approv' in (lab.get('headline') or '').lower():
        etf = (g, lab)
json.dump(labels, open(OUT + '/emergent_clusters_reconstructed.json', 'w'), indent=1)
if not etf:
    print('ETF approval label NOT reproduced; see emergent_clusters_reconstructed.json')
    L.stop(); sys.exit(0)
g, lab = etf
member = [chunks[i] for i in g['chunk_idx']]
cand = {'origin': 'transcript_cluster', 'headline': lab['headline'], 'summary': lab.get('summary', ''),
        'source_domain': 'transcript cluster'}
q = sm.derive_story_query(L, cand, today)
qv = E.encode(sm.query_texts(q), query=True)
sims = (vecs @ qv.T).max(axis=1)
pats = sm.alias_patterns(q)
per = {}
for i, ch in enumerate(chunks):
    hits = sum(1 for p in pats if p.search(ch['text']))
    if sims[i] >= es.RETRIEVAL_MIN_SIM or hits >= 2:
        per.setdefault(ch['video_id'], []).append((float(sims[i]) + 0.03 * min(hits, 3), i))
ranked = sorted(per.items(), key=lambda kv: -max(s for s, _ in kv[1]))
picked, seen = [], set()
for vid, lst in ranked:
    c0 = chunks[lst[0][1]]['channel_id']
    if c0 not in seen:
        picked.append((vid, lst)); seen.add(c0)
for vid, lst in ranked:
    if len(picked) >= es.MAX_ADJUDICATE_PER_STORY: break
    if (vid, lst) not in picked: picked.append((vid, lst))
picked = picked[:es.MAX_ADJUDICATE_PER_STORY]
verdicts = []
for vid, lst in picked:
    idx = [i for _, i in sorted(lst, reverse=True)[:4]]
    ex = [chunks[i] for i in sorted(idx, key=lambda i: chunks[i]['start'])]
    v = sm.adjudicate(L, q, {'title': ex[0]['exact_title'], 'channel': ex[0]['channel_name']}, ex)
    v.update(video_id=vid, channel=ex[0]['channel_name'], title=ex[0]['exact_title'], canonical_url=ex[0]['canonical_url'],
             layout_eligible=ex[0]['layout_eligible'], published_at=ex[0]['published_at'], age_h=ex[0]['age_h'],
             transcript_sha256=ex[0]['transcript_sha256'], transcript_method=ex[0]['transcript_method'],
             excerpts=[{'chunk_id': x['chunk_id'], 'start': x['start'], 'end': x['end'], 'text': x['text']} for x in ex])
    verdicts.append(v)
    print('  ', v['verdict'], v['counted_as_same_event'], v['channel'], '|', v['title'][:60], '|', (v['evidence_quote'] or '')[:120])
L.stop(); E.close()
fixture = {'what': 'Real failure mode: current spot-ETF flow discussion clustered across channels and was labelled by gemma3:27b '
                   'as the January 2024 SEC spot Bitcoin ETF approval, then promoted to the top current-story candidate.',
           'run': 'runs/fresh_20261106_174439 @ 27049908', 'run_start_utc': RUN_START.isoformat(),
           'reconstruction': 'offline, same cached transcripts (acquired before run start), same embeddings/clustering/prompts, '
                             'temperature 0 seed 7; the run itself crashed before writing TOPIC_SELECTION.json',
           'cluster': {'channels': g['channels'], 'n_chunks': len(g['chunk_idx']), 'label': lab,
                       'member_chunks': [{k: c[k] for k in ('chunk_id', 'video_id', 'channel_name', 'exact_title', 'canonical_url',
                                                            'published_at', 'transcript_sha256', 'start', 'end', 'text')} for c in member]},
           'derived_query': q, 'adjudications': verdicts}
json.dump(fixture, open(OUT + '/stale_etf_fixture.json', 'w'), indent=1, ensure_ascii=False)
print('wrote', OUT + '/stale_etf_fixture.json')
