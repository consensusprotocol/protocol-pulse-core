#!/usr/bin/env python3
# Vendored from boomers_pipeline/overlays/adaptive_gfx/shotmap.py (EP22), extended for Protocol Pulse vertical module.
"""vertical.shotmap - measure what is actually on screen, shot by shot, from the master.

Every placement decision in this module starts here. The EP22 sprint showed that assumed geometry
fails: the 3-up seams move between shots (x=633/1292 in most, 619/1299 in S1/H05), two cards straddled
hard cuts by 1 and 8 frames, and no list existed of where the full-frame shots were.

Method
  1. Every-frame pass (not samples). The master is decoded once at 192x108 grey. For each frame we keep
     the mean absolute difference to the previous frame (MAD), a 32-bin histogram distance and the
     column-mean profile. A hard cut is a MAD spike far above its local median that is also large in
     absolute terms (MAD >= 30 or histogram distance >= 0.10); smaller spikes are frame jumps (a Riverside
     tile freezing or skipping), listed separately and not treated as shot boundaries. The thresholds are
     recorded in the output. Cache: <out>/work/framediff.npz.
  2. Keyframe pass: every keyframe (about 1 per second; x264 also places one on each scene cut) is decoded
     at full resolution with -skip_frame nokey. Seams and the logo are measured on each. Per shot, the
     consensus over its keyframes gives:
       seams     columns where |dI| > 18 persists over >= 55% of rows 120-900, clustered within 4 px
                 (Riverside gutters show two edges). Seam x0 = first gutter pixel, the convention behind
                 the sprint's 633/1292. A seam counts if it is present in >= 80% of the shot's keyframes.
       layout    '3up' (2 seams), '2up' (1 seam), 'single' (0 seams), '4up' (3 seams), '5up' (4 seams), etc.
                 Every tile must be >= MIN_TILE_FRAC * W; otherwise the shot is flagged low-confidence.
       tiles     [x0, x1) per tile, with the host per tile taken from the episode config's left-to-right
                 order. Single shots get host=null here (the speaker layer names them).
       stability fraction of the shot's keyframes whose seams match the consensus. A run of >= 2 keyframes
                 with different seams splits the shot (a layout change without a hard cut); the split frame is
                 refined from the every-frame column profile.
       logo_ncc  normalised correlation of the configured logo box against the config reference keyframe.
     Faces are measured per tile via MediaPipe FaceDetector when in config-free mode.
  3. Burned-in regions (logo, name band) come from the episode config and are verified per shot.
     Skipped when running config-free (no logo verification, auto-detect hosts from face counting).

Extensions over the EP22 original:
  - Config-free entry: build(master_path, out_dir, stage='all') without requiring a config file.
  - Screen-share detection per keyframe (large bright rectangles >35% of frame area).
  - 4+ tile recognition: '4up', '5up', etc. as first-class layouts (up to 10 seams).
  - MediaPipe face counting per tile (median across 3-5 sampled keyframes).

Writes <out>/shot_map.json and <out>/shot_map_contact.png. Read-only on the master.
Usage:
  Config-free:  python3 shotmap.py --master /path/to/master.mp4 --out /path/to/out [--stage ...]
  With config:  python3 shotmap.py --episode /path/to/episode.json [--stage ...]
"""
import argparse, hashlib, json, pathlib, subprocess, time, statistics
import numpy as np

LW, LH = 192, 108                 # every-frame pass resolution
SEAM_ROWS = (120, 900)            # rows used for seam persistence (clear of logo and name band)
SEAM_STEP = 18                    # |dI| between adjacent columns that counts as a step
SEAM_PERSIST = 0.55               # fraction of rows that must step (validated on EP22 in the sprint)
SEAM_CLUSTER_PX = 4               # gutter edges closer than this are one seam
SEAM_MATCH_PX = 3                 # same seam across keyframes
SEAM_PRESENT = 0.8                # share of a shot's keyframes a seam must appear in
MIN_TILE_FRAC = 0.22              # narrowest plausible tile
CUT_K, CUT_ABS, CUT_WIN = 4.0, 6.0, 12   # MAD >= CUT_ABS and >= CUT_K x local median (+/- CUT_WIN frames)
CUT_HARD_MAD, CUT_HARD_HIST = 30.0, 0.10  # below both, a spike is a frame jump (Riverside freeze/skip), not a cut.
                                          # EP22: real cuts MAD 48-83 / hist 0.21-0.45; jumps MAD 6.5-11 / hist <= 0.034
FAMILY_MIN_SHARE = 0.02           # a multi-seam signature in >= 2% of keyframes is one of the episode's layouts
FAMILY_SEAM_MIN = 0.40            # relaxed per-seam persistence that classifies a keyframe into a known layout
                                  # (EP22: true seams 0.51-0.89, non-seam columns <= 0.35, single shots <= 0.08)
SCHEMA = 'vertical.shot_map/0.2'
FACE_MODEL = "/home/ultron/protocol_pulse/segment_v1/qa_v6/blaze_face_short_range.tflite"

# Screen-share detection thresholds
SS_AREA_FRAC = 0.35               # contour must cover > 35% of frame area
SS_BRIGHT_THRESH = 140            # grey brightness threshold for binary mask
SS_ASPECT_LO = 1.2                # minimum aspect ratio (landscape)
SS_ASPECT_HI = 3.0                # maximum aspect ratio

# Face counting
FACE_SAMPLE_COUNT = 5             # keyframes to sample per shot for face counting
FACE_MIN_CONFIDENCE = 0.4         # MediaPipe detection threshold


def sha16(path, n=16 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read(n))
    return h.hexdigest()


def probe(master):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height,r_frame_rate,nb_frames,start_time:format=duration', '-of', 'json',
                        str(master)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    s = j['streams'][0]
    num, den = map(int, s['r_frame_rate'].split('/'))
    return dict(width=int(s['width']), height=int(s['height']), fps=num / den,
                nb_frames=int(s.get('nb_frames') or 0), start_time=float(s.get('start_time') or 0.0),
                duration_s=float(j['format']['duration']))


# ---------------------------------------------------------------- 1. every-frame pass

def frame_pass(master, cache, threads=16):
    """MAD, histogram distance and column profile for every frame (cached)."""
    if cache.exists():
        z = np.load(cache)
        return z['mad'], z['hd'], z['colp']
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-threads', str(threads),
           '-i', str(master), '-an', '-vf', f'scale={LW}:{LH}:flags=area,format=gray', '-f', 'rawvideo', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1 << 22)
    fs = LW * LH
    mad, hd, colp = [], [], []
    prev = prevh = None
    t0 = time.time()
    while True:
        buf = p.stdout.read(fs)
        if len(buf) < fs:
            break
        f = np.frombuffer(buf, np.uint8).reshape(LH, LW)
        fi = f.astype(np.int16)
        h = np.bincount((f >> 3).ravel(), minlength=32) / fs
        if prev is None:
            mad.append(0.0)
            hd.append(0.0)
        else:
            mad.append(float(np.abs(fi - prev).mean()))
            hd.append(float(0.5 * np.abs(h - prevh).sum()))
        colp.append(f.mean(axis=0))
        prev, prevh = fi, h
        if len(mad) % 4800 == 0:
            print(f'  frame pass: {len(mad)} frames in {time.time() - t0:.0f} s', flush=True)
    if p.wait() != 0:
        raise RuntimeError('ffmpeg frame pass failed')
    mad, hd, colp = np.array(mad, np.float32), np.array(hd, np.float32), np.array(colp, np.float16)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, mad=mad, hd=hd, colp=colp)
    return mad, hd, colp


def find_cuts(mad, hd, k=CUT_K, mad_abs=CUT_ABS, win=CUT_WIN):
    """Hard cuts = first frame of a new shot. Adjacent spikes (flash frames) collapse to the larger."""
    n = len(mad)
    raw = []
    for i in range(1, n):
        lo, hi = max(1, i - win), min(n, i + win + 1)
        neigh = np.concatenate([mad[lo:max(lo, i - 1)], mad[min(i + 2, hi):hi]])
        base = float(np.median(neigh)) if len(neigh) else 0.0
        if mad[i] >= mad_abs and mad[i] >= k * max(base, 0.5):
            raw.append(dict(frame=i, mad=round(float(mad[i]), 2), local_median=round(base, 2),
                            hist_dist=round(float(hd[i]), 3)))
    cuts = []
    for c in raw:
        if cuts and c['frame'] - cuts[-1]['frame'] <= 2:
            if c['mad'] > cuts[-1]['mad']:
                c['merged_with'] = cuts[-1]['frame']
                cuts[-1] = c
            else:
                cuts[-1]['merged_with'] = c['frame']
            continue
        cuts.append(c)
    for c in cuts:
        c['kind'] = 'cut' if (c['mad'] >= CUT_HARD_MAD or c['hist_dist'] >= CUT_HARD_HIST) else 'jump'
    return cuts


# ---------------------------------------------------------------- 2. keyframe pass (full resolution)

def keyframe_list(master, fps):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'packet=pts_time,flags',
                        '-of', 'csv=p=0', str(master)], capture_output=True, text=True, check=True)
    ts = sorted(float(a) for a, _, fl in (ln.partition(',') for ln in r.stdout.splitlines()) if 'K' in fl and a)
    return [int(round(t * fps)) for t in ts]


def persistence(g):
    """Per column x: share of rows 120-900 where |I[x+1] - I[x]| > SEAM_STEP (len W-1)."""
    band = g[SEAM_ROWS[0]:SEAM_ROWS[1]].astype(np.int16)
    return (np.abs(np.diff(band, axis=1)) > SEAM_STEP).mean(axis=0)


def seams_in(g, persist=None):
    """Vertical tile seams in one full-res grey frame: list of dict(x0, x1, persist, gutter_std)."""
    band = g[SEAM_ROWS[0]:SEAM_ROWS[1]].astype(np.int16)
    if persist is None:
        persist = persistence(g)
    W = g.shape[1]
    cols = [int(c) for c in np.where(persist > SEAM_PERSIST)[0] if 8 < c < W - 9]
    groups = []
    for c in cols:
        if groups and c - groups[-1][-1] <= SEAM_CLUSTER_PX:
            groups[-1].append(c)
        else:
            groups.append([c])
    out = []
    for g_ in groups:
        x0, x1 = g_[0] + 1, g_[-1] + 1
        gutter = band[:, x0:x1]
        out.append(dict(x0=x0, x1=x1, persist=round(float(persist[g_].max()), 3),
                        gutter_std=round(float(gutter.std()), 1) if x1 > x0 else None))
    return out


def grey(rgb):
    return (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114).astype(np.uint8)


def ncc(a, b):
    a = a.astype(np.float64).ravel() - a.mean()
    b = b.astype(np.float64).ravel() - b.mean()
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / d) if d else 0.0


# ---------------------------------------------------------------- 2a. screen-share detection

def detect_screenshare(frame_bgr):
    """Detect large bright rectangles in a full-resolution BGR frame.
    Returns (has_screenshare: bool, rect: dict or None).
    rect is {x, y, w, h} of the largest qualifying contour."""
    import cv2
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, SS_BRIGHT_THRESH, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H, W = frame_bgr.shape[:2]
    frame_area = W * H
    best_area = 0
    best_rect = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > frame_area * SS_AREA_FRAC:
            x, y, cw, ch = cv2.boundingRect(cnt)
            aspect = cw / max(ch, 1)
            if SS_ASPECT_LO < aspect < SS_ASPECT_HI:
                if area > best_area:
                    best_area = area
                    best_rect = dict(x=int(x), y=int(y), w=int(cw), h=int(ch))
    return (best_rect is not None), best_rect


# ---------------------------------------------------------------- 2b. keyframe chunk (config-aware)

def _keyframe_chunk(master, W, H, fps, lg, chunk):
    """Decode one run of consecutive keyframes (-ss on the first, -t past the last) and measure each.
    lg is the logo rect dict (config mode) or None (config-free mode)."""
    t0, t1 = chunk[0] / fps, (chunk[-1] + 0.5) / fps
    # In config-free mode, decode as BGR (rgb24) so we can run screen-share detection on color frames.
    # In config mode, decode as gray for logo NCC.
    config_free = lg is None
    pix_fmt = 'rgb24' if config_free else 'gray'
    bpp = 3 if config_free else 1
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-skip_frame', 'nokey', '-threads', '2',
           '-ss', f'{t0:.4f}', '-i', str(master), '-t', f'{t1 - t0:.4f}', '-an', '-vsync', '0',
           '-f', 'rawvideo', '-pix_fmt', pix_fmt, '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1 << 24)
    rows, thumbs, logos, profs, ss_results = [], [], [], [], []
    for fr in chunk:
        buf = p.stdout.read(W * H * bpp)
        if len(buf) < W * H * bpp:
            break
        if config_free:
            rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            g = grey(rgb)
            # Screen-share detection on full-res colour frame (convert RGB->BGR for cv2 convention)
            bgr = rgb[..., ::-1].copy()
            ss_hit, ss_rect = detect_screenshare(bgr)
            ss_results.append(dict(screen_share=ss_hit, screen_share_rect=ss_rect))
        else:
            g = np.frombuffer(buf, np.uint8).reshape(H, W)
            ss_results.append(dict(screen_share=False, screen_share_rect=None))
        pr = persistence(g)
        if lg is not None:
            logos.append(g[lg['y']:lg['y'] + lg['h'], lg['x']:lg['x'] + lg['w']].copy())
        rows.append(dict(frame=fr, seams=seams_in(g, pr)))
        thumbs.append(g[::8, ::8].copy())
        profs.append(np.round(pr * 255).astype(np.uint8))
    extra = len(p.stdout.read()) // (W * H * bpp)
    p.wait()
    if len(rows) != len(chunk) or extra:
        raise RuntimeError(f'chunk {chunk[0]}..{chunk[-1]}: decoded {len(rows)} (+{extra}) frames for {len(chunk)} keyframes')
    return rows, thumbs, logos, profs, ss_results


def keyframe_pass(master, info, cfg, cache_json, cache_thumbs, jobs=16):
    """Seams + logo NCC on every keyframe at full resolution, decoded in parallel time chunks (cached).
    Chunk starts are keyframe times, so each ffmpeg seek lands exactly on its first keyframe; every chunk
    must return exactly its keyframes (checked), which keeps frame indices exact.
    cfg may be None for config-free mode (no logo verification)."""
    if cache_json.exists() and cache_thumbs.exists():
        z = np.load(cache_thumbs)
        if 'persist' in z.files:
            data = json.loads(cache_json.read_text())
            return data, z['thumbs'], z['persist']
    from concurrent.futures import ThreadPoolExecutor
    W, H, fps = info['width'], info['height'], info['fps']
    kfs = keyframe_list(master, fps)
    config_free = cfg is None
    lg = None if config_free else cfg['burned_in']['logo']
    ref_idx = None
    if not config_free:
        ref_idx = min(range(len(kfs)), key=lambda i: abs(kfs[i] - cfg['logo_reference_frame']))
    per = -(-len(kfs) // jobs)
    chunks = [kfs[i:i + per] for i in range(0, len(kfs), per)]
    print(f'  keyframes: {len(kfs)} in {len(chunks)} parallel chunks', flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(len(chunks)) as ex:
        parts = list(ex.map(lambda ch: _keyframe_chunk(master, W, H, fps, lg, ch), chunks))
    rows = [r for p_ in parts for r in p_[0]]
    thumbs = [t for p_ in parts for t in p_[1]]
    logos = [l_ for p_ in parts for l_ in p_[2]]
    profs = np.array([q for p_ in parts for q in p_[3]], np.uint8)
    ss_all = [s for p_ in parts for s in p_[4]]
    print(f'  keyframe pass: {len(rows)} keyframes in {time.time() - t0:.0f} s', flush=True)
    # Attach screen-share results to each keyframe row
    for r, ss in zip(rows, ss_all):
        r['screen_share'] = ss['screen_share']
        r['screen_share_rect'] = ss['screen_share_rect']
    if not config_free and logos:
        ref = logos[ref_idx]
        for r, crop in zip(rows, logos):
            r['logo_ncc'] = round(ncc(crop, ref), 3)
    res = dict(keyframes=rows)
    if not config_free:
        res['logo_reference_keyframe'] = kfs[ref_idx]
    cache_json.parent.mkdir(parents=True, exist_ok=True)
    cache_json.write_text(json.dumps(res))
    np.savez_compressed(cache_thumbs, thumbs=np.array(thumbs, np.uint8), persist=profs)
    return res, np.array(thumbs, np.uint8), profs


def consensus_seams(kf_rows):
    """Seams present in >= SEAM_PRESENT of the keyframes (matched within SEAM_MATCH_PX), median edges."""
    if not kf_rows:
        return []
    clusters = []
    for r in kf_rows:
        for s in r['seams']:
            for c in clusters:
                if abs(np.median([m['x0'] for m in c]) - s['x0']) <= SEAM_MATCH_PX:
                    c.append(s)
                    break
            else:
                clusters.append([s])
    need = SEAM_PRESENT * len(kf_rows)
    out = [dict(x0=int(np.median([m['x0'] for m in c])), x1=int(np.median([m['x1'] for m in c])),
                present=round(len(c) / len(kf_rows), 2), persist_min=min(m['persist'] for m in c))
           for c in clusters if len(c) >= need]
    return sorted(out, key=lambda s: s['x0'])


def seam_signature(seams):
    return tuple(s['x0'] for s in seams)


def same_sig(a, b):
    return len(a) == len(b) and all(abs(x - y) <= SEAM_MATCH_PX for x, y in zip(a, b))


def describe(seams, W, hosts):
    """Produce layout name, tile list and plausibility flag. Supports up to 10 seams (11 tiles).
    Layouts: 'single' (0 seams), '2up' (1), '3up' (2), '4up' (3), '5up' (4), ..., '11up' (10).
    Plausible when all tiles >= MIN_TILE_FRAC * W and seam count <= 10."""
    edges = [0] + [x for s in seams for x in (s['x0'], s['x1'])] + [W]
    tiles = [dict(x0=edges[i], x1=edges[i + 1]) for i in range(0, len(edges), 2)]
    n_seams = len(seams)
    layout = {0: 'single', 1: '2up', 2: '3up'}.get(n_seams, f'{n_seams + 1}up')
    plausible = all(t['x1'] - t['x0'] >= MIN_TILE_FRAC * W for t in tiles) and n_seams <= 10
    for i, t in enumerate(tiles):
        if hosts is not None and n_seams + 1 == len(hosts):
            t['host'] = hosts[i]
        elif hosts is not None and layout == '3up' and len(hosts) == 3:
            t['host'] = hosts[i]
        else:
            t['host'] = None
    return layout, tiles, plausible


def learn_families(kf_rows):
    """The episode's recurring tiled layouts: multi-seam signatures from strict detections, merged within
    SEAM_MATCH_PX, kept when they cover >= FAMILY_MIN_SHARE of keyframes. Learned from the data, not assumed."""
    fams = []
    for r in kf_rows:
        sg = r['seams']
        if len(sg) < 2:
            continue
        for f in fams:
            if same_sig(f['sig'], seam_signature(sg)):
                f['members'].append(sg)
                break
        else:
            fams.append(dict(sig=seam_signature(sg), members=[sg]))
    out = []
    for f in sorted(fams, key=lambda f: -len(f['members'])):
        if len(f['members']) >= FAMILY_MIN_SHARE * len(kf_rows):
            k = len(f['members'][0])
            seams = [dict(x0=int(np.median([m[i]['x0'] for m in f['members']])),
                          x1=int(np.median([m[i]['x1'] for m in f['members']]))) for i in range(k)]
            out.append(dict(id=f'L{len(out) + 1}', seams=seams, strict_keyframes=len(f['members'])))
    return out


def classify_family(prof, fams):
    """(family, score): score = weakest seam's persistence within +/-SEAM_MATCH_PX of the family's seam."""
    best, score = None, 0.0
    for f in fams:
        sc = min(float(prof[max(0, sm['x0'] - 1 - SEAM_MATCH_PX):sm['x0'] + SEAM_MATCH_PX].max()) for sm in f['seams'])
        if sc > score:
            best, score = f, sc
    return (best if score >= FAMILY_SEAM_MIN else None), round(score, 3)


def effective_row(r, prof, fams):
    """A keyframe's layout: a learned family when its seams are all present (relaxed), else strict seams."""
    f, sc = classify_family(prof, fams)
    if f:
        seams = [dict(x0=sm['x0'], x1=sm['x1'], persist=sc) for sm in f['seams']]
    else:
        seams = r['seams']
    row = dict(frame=r['frame'], seams=seams, family=f['id'] if f else None, family_score=sc,
               strict=[sm['x0'] for sm in r['seams']], logo_ncc=r.get('logo_ncc'),
               screen_share=r.get('screen_share', False),
               screen_share_rect=r.get('screen_share_rect'))
    return row


def split_runs(kf_rows):
    """Runs of consecutive keyframes with the same seam signature; runs of 1 are noise, not layouts."""
    runs = []
    for r in kf_rows:
        sig = seam_signature(r['seams'])
        if runs and same_sig(runs[-1]['sig'], sig):
            runs[-1]['rows'].append(r)
        else:
            runs.append(dict(sig=sig, rows=[r]))
    merged = []
    for run in runs:
        if merged and (len(run['rows']) < 2 or same_sig(merged[-1]['sig'], run['sig'])):
            merged[-1]['rows'].extend(run['rows'])
        else:
            merged.append(run)
    if len(merged) > 1 and len(merged[0]['rows']) < 2:
        merged[1]['rows'] = merged[0]['rows'] + merged[1]['rows']
        merged.pop(0)
    return merged


def refine_split(colp, f_a, f_b):
    """First frame between keyframes f_a < f_b whose low-res column profile is closer to f_b's."""
    pa, pb = colp[f_a].astype(np.float32), colp[f_b].astype(np.float32)
    for f in range(f_a + 1, f_b + 1):
        p = colp[f].astype(np.float32)
        if np.abs(p - pb).mean() < np.abs(p - pa).mean():
            return f
    return f_b


# ---------------------------------------------------------------- 2c. MediaPipe face counting per tile

_FACE_DETECTOR = None


def _get_face_detector():
    """Lazy-init singleton MediaPipe FaceDetector."""
    global _FACE_DETECTOR
    if _FACE_DETECTOR is None:
        import mediapipe as mp_lib
        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.core import base_options as mp_base_options
        base_opts = mp_base_options.BaseOptions(model_asset_path=FACE_MODEL)
        _FACE_DETECTOR = vision.FaceDetector.create_from_options(
            vision.FaceDetectorOptions(base_options=base_opts, min_detection_confidence=FACE_MIN_CONFIDENCE))
    return _FACE_DETECTOR


def count_faces_in_crop(rgb_crop):
    """Run MediaPipe FaceDetector on an RGB numpy array, return face count."""
    import mediapipe as mp_lib
    if rgb_crop.size == 0 or rgb_crop.shape[0] < 10 or rgb_crop.shape[1] < 10:
        return 0
    detector = _get_face_detector()
    mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=np.ascontiguousarray(rgb_crop))
    results = detector.detect(mp_image)
    return len(results.detections)


def face_count_tiles(master, tiles, kf_frames, fps, W, H):
    """For a shot's tiles, sample 3-5 keyframes at full resolution, crop each tile rect, count faces.
    Returns updated tiles list (with face_count per tile) and total_faces (median across samples)."""
    import cv2
    n_samples = min(FACE_SAMPLE_COUNT, len(kf_frames))
    if n_samples == 0:
        for t in tiles:
            t['face_count'] = 0
        return tiles, 0
    # Pick evenly spaced keyframes
    if n_samples >= len(kf_frames):
        sample_frames = list(kf_frames)
    else:
        step = len(kf_frames) / n_samples
        sample_frames = [kf_frames[int(i * step)] for i in range(n_samples)]
    # Collect face counts per tile across samples
    tile_counts = [[] for _ in tiles]
    total_per_sample = []
    cap = cv2.VideoCapture(str(master))
    for fr in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fr)
        ok, bgr = cap.read()
        if not ok:
            continue
        rgb = bgr[..., ::-1].copy()
        sample_total = 0
        for ti, t in enumerate(tiles):
            x0 = max(0, t['x0'])
            x1 = min(W, t['x1'])
            crop = rgb[:, x0:x1, :]
            fc = count_faces_in_crop(crop)
            tile_counts[ti].append(fc)
            sample_total += fc
        total_per_sample.append(sample_total)
    cap.release()
    # Median face count per tile
    for ti, t in enumerate(tiles):
        if tile_counts[ti]:
            t['face_count'] = int(statistics.median(tile_counts[ti]))
        else:
            t['face_count'] = 0
    total_faces = int(statistics.median(total_per_sample)) if total_per_sample else 0
    return tiles, total_faces


# ---------------------------------------------------------------- 3. contact sheet

def contact_sheet(shots, thumbs_by_shot, out_png, W_full=1920):
    from PIL import Image, ImageDraw, ImageFont
    tw, th, cols = 384, 216, 6
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows * (th + 22)), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(pathlib.Path(__file__).resolve().parents[1] / 'fonts' / 'PlexMono-Bold.ttf'), 13)
    except OSError:
        try:
            font = ImageFont.truetype(str(pathlib.Path('/home/ultron/boomers_pipeline/overlays/fonts/PlexMono-Bold.ttf')), 13)
        except OSError:
            font = ImageFont.load_default()
    sx = tw / W_full
    for i, (s, im) in enumerate(zip(shots, thumbs_by_shot)):
        x, y = (i % cols) * tw, (i // cols) * (th + 22)
        if im is not None:
            sheet.paste(Image.fromarray(im).convert('RGB').resize((tw, th)), (x, y))
        for sm in s['seams']:
            d.line([(x + sm['x0'] * sx, y), (x + sm['x0'] * sx, y + th)], fill=(255, 40, 40), width=1)
        ss_tag = ' SS' if s.get('screen_share') else ''
        fc_tag = f' f={s["total_faces"]}' if 'total_faces' in s else ''
        lab = f"{s['id']} {s['t_in']:.2f}-{s['t_out']:.2f} {s['layout']} {[sm['x0'] for sm in s['seams']]} {s['confidence'][0]}{ss_tag}{fc_tag}"
        d.text((x + 4, y + th + 3), lab, fill=(255, 205, 60), font=font)
    sheet.save(out_png)


# ---------------------------------------------------------------- build

def build(master_path_or_cfg, out_dir=None, stage='all'):
    """Build shot map from a master video.

    Signatures:
      build(cfg_path, stage='all')                         -- original config-based mode
      build(master_path, out_dir, stage='all')             -- config-free mode

    Config-free mode skips logo verification and burned_in measurements. Hosts are auto-detected
    from face counting per tile. Screen-share detection and MediaPipe face counting are always active
    in config-free mode.
    """
    master_path_or_cfg = str(master_path_or_cfg)

    # Determine mode: config-based or config-free
    config_free = False
    cfg = None
    if master_path_or_cfg.endswith('.json'):
        # Config-based mode (original behaviour)
        cfg = json.loads(pathlib.Path(master_path_or_cfg).read_text())
        master = pathlib.Path(cfg['master'])
        out = pathlib.Path(master_path_or_cfg).parent
        if out_dir is not None:
            out = pathlib.Path(out_dir)
        hosts = cfg['hosts_left_to_right']
    else:
        # Config-free mode
        config_free = True
        master = pathlib.Path(master_path_or_cfg)
        if out_dir is None:
            out = master.parent / 'shotmap_out'
        else:
            out = pathlib.Path(out_dir)
        hosts = None  # will be auto-detected from face counting

    work = out / 'work'
    work.mkdir(parents=True, exist_ok=True)
    info = probe(master)
    W, H, fps = info['width'], info['height'], info['fps']
    t0 = time.time()
    print(f'probe: {info}', flush=True)

    if stage in ('cuts', 'all'):
        frame_pass(master, work / 'framediff.npz')
        print(f'frame pass cached ({time.time() - t0:.0f} s)', flush=True)

    if stage in ('keyframes', 'all'):
        keyframe_pass(master, info, cfg, work / 'keyframes.json', work / 'keyframe_thumbs.npz')
        print(f'keyframe pass cached ({time.time() - t0:.0f} s)', flush=True)

    if stage not in ('build', 'all'):
        return None

    mad, hd, colp = frame_pass(master, work / 'framediff.npz')
    kf, thumbs, prof = keyframe_pass(master, info, cfg, work / 'keyframes.json', work / 'keyframe_thumbs.npz')
    n = len(mad)
    spikes = find_cuts(mad, hd)
    cuts = [c for c in spikes if c['kind'] == 'cut']
    jumps = [c for c in spikes if c['kind'] == 'jump']
    fams = learn_families(kf['keyframes'])
    kf_rows = [effective_row(r, prof[i].astype(np.float32) / 255.0, fams) for i, r in enumerate(kf['keyframes'])]
    print(f'layout families: {[(f["id"], [sm["x0"] for sm in f["seams"]], f["strict_keyframes"]) for f in fams]}; '
          f'{sum(1 for r in kf_rows if r["family"])} keyframes classified into a family, '
          f'{sum(1 for r in kf_rows if r["family"] and len(r["strict"]) != len(r["seams"]))} of them rescued from a weak seam', flush=True)

    reader = None
    kf_frames = [r['frame'] for r in kf_rows]
    on_kf = sum(1 for c in cuts if c['frame'] in set(kf_frames))
    bounds = [0] + [c['frame'] for c in cuts] + [n]
    shots, sheet_thumbs, soft = [], [], []

    for i in range(len(bounds) - 1):
        f_in, f_out = bounds[i], bounds[i + 1]
        idx = [j for j, f in enumerate(kf_frames) if f_in <= f < f_out]
        rows = [kf_rows[j] for j in idx]
        if not rows:                       # shot without a keyframe: measure its middle frame directly
            reader = reader or Reader(master)
            mid_f = (f_in + f_out) // 2
            g = grey(reader.rgb(mid_f))
            pr = persistence(g)
            raw_row = dict(frame=mid_f, seams=seams_in(g, pr), screen_share=False, screen_share_rect=None)
            rows = [effective_row(raw_row, pr, fams)]
        pieces = []
        runs = split_runs(rows) if len(rows) >= 4 else [dict(sig=None, rows=rows)]
        start = f_in
        for k, run in enumerate(runs):
            end = f_out if k == len(runs) - 1 else refine_split(colp, run['rows'][-1]['frame'], runs[k + 1]['rows'][0]['frame'])
            pieces.append((start, end, run['rows']))
            if k < len(runs) - 1:
                soft.append(dict(frame=end, t=round(end / fps, 3), between_keyframes=[run['rows'][-1]['frame'], runs[k + 1]['rows'][0]['frame']]))
            start = end

        for (a, b, rws) in pieces:
            seams = consensus_seams(rws)
            layout, tiles, plausible = describe(seams, W, hosts)
            sig = seam_signature(seams)
            stab = round(sum(same_sig(seam_signature(r['seams']), sig) for r in rws) / len(rws), 2) if rws else None
            conf = 'none' if not rws else ('low' if not plausible else ('high' if stab >= 0.8 else 'medium'))
            fam_ids = [r['family'] for r in rws if r['family']]

            # Screen-share: consensus across keyframes in this piece (majority vote)
            ss_votes = [r.get('screen_share', False) for r in rws]
            shot_ss = sum(ss_votes) > len(ss_votes) / 2

            # Screen-share rect: take from the first keyframe that has one
            shot_ss_rect = None
            if shot_ss:
                for r in rws:
                    if r.get('screen_share_rect'):
                        shot_ss_rect = r['screen_share_rect']
                        break

            # Face counting per tile (config-free mode always; config mode skips)
            shot_kf_frames = [r['frame'] for r in rws]
            total_faces = None
            if config_free:
                tiles, total_faces = face_count_tiles(master, tiles, shot_kf_frames, fps, W, H)

            s = dict(id=f'sh{len(shots) + 1:03d}', frame_in=a, frame_out=b, t_in=round(a / fps, 3), t_out=round(b / fps, 3),
                     dur_s=round((b - a) / fps, 3), start=('cut' if a in bounds else ('soft' if a > 0 else 'start')),
                     layout=layout if rws else 'unmeasured', confidence=conf, seams=seams, tiles=tiles,
                     family=max(set(fam_ids), key=fam_ids.count) if fam_ids else None,
                     keyframes=len(rws), stability=stab,
                     screen_share=shot_ss, screen_share_rect=shot_ss_rect)

            if total_faces is not None:
                s['total_faces'] = total_faces

            if not config_free:
                s['logo_ncc_min'] = min((r['logo_ncc'] for r in rws if r.get('logo_ncc') is not None), default=None)

            shots.append(s)
            mid = idx[len(idx) // 2] if idx else None
            sheet_thumbs.append(thumbs[mid] if mid is not None else None)

    # Summary: screen-share stats
    ss_count = sum(1 for s in shots if s.get('screen_share'))
    ss_dur = round(sum(s['dur_s'] for s in shots if s.get('screen_share')), 1)

    episode_name = cfg.get('episode', master.stem) if cfg else master.stem
    res = dict(schema=SCHEMA, episode=episode_name, generated_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               master=str(master), master_sha256_first16MB=sha16(master), video=info, frames_analysed=n,
               keyframes_analysed=len(kf_rows), cuts_on_keyframes=f'{on_kf}/{len(cuts)}',
               config_free=config_free,
               params=dict(lowres=[LW, LH], seam_rows=SEAM_ROWS, seam_step=SEAM_STEP, seam_persist=SEAM_PERSIST,
                           seam_cluster_px=SEAM_CLUSTER_PX, seam_present=SEAM_PRESENT, min_tile_frac=MIN_TILE_FRAC,
                           cut_k=CUT_K, cut_abs=CUT_ABS, cut_win=CUT_WIN, cut_hard_mad=CUT_HARD_MAD,
                           cut_hard_hist=CUT_HARD_HIST, family_min_share=FAMILY_MIN_SHARE,
                           family_seam_min=FAMILY_SEAM_MIN,
                           ss_area_frac=SS_AREA_FRAC, ss_bright_thresh=SS_BRIGHT_THRESH,
                           ss_aspect_lo=SS_ASPECT_LO, ss_aspect_hi=SS_ASPECT_HI,
                           face_model=FACE_MODEL if config_free else None,
                           face_min_confidence=FACE_MIN_CONFIDENCE if config_free else None))

    if not config_free:
        res['burned_in'] = cfg['burned_in']
        res['hosts_left_to_right'] = hosts

    res.update(dict(
        layout_families=fams, cuts=[dict(c, t=round(c['frame'] / fps, 3)) for c in cuts],
        frame_jumps=[dict(c, t=round(c['frame'] / fps, 3)) for c in jumps], soft_layout_changes=soft, shots=shots,
        layout_seconds={lay: round(sum(s['dur_s'] for s in shots if s['layout'] == lay), 1)
                        for lay in sorted({s['layout'] for s in shots})},
        screen_share_shots=ss_count, screen_share_seconds=ss_dur))

    out.mkdir(parents=True, exist_ok=True)
    (out / 'shot_map.json').write_text(json.dumps(res, indent=1))
    contact_sheet(shots, sheet_thumbs, out / 'shot_map_contact.png', W_full=W)

    for s in shots:
        ss_tag = ' SS' if s.get('screen_share') else ''
        fc_tag = f' faces={s["total_faces"]}' if 'total_faces' in s else ''
        logo_tag = f' logo={s["logo_ncc_min"]}' if 'logo_ncc_min' in s else ''
        print(f"  {s['id']} {s['t_in']:9.3f}-{s['t_out']:9.3f} [{s['start']:5s}] {s['layout']:6s} seams={[x['x0'] for x in s['seams']]} "
              f"kf={s['keyframes']} stab={s['stability']} conf={s['confidence']}{logo_tag}{fc_tag}{ss_tag}", flush=True)
    print(f'wrote {out / "shot_map.json"}: {len(cuts)} cuts ({on_kf} on keyframes), {len(jumps)} frame jumps, {len(soft)} soft changes, '
          f'{len(shots)} shots, layouts {res["layout_seconds"]}, screen-share: {ss_count} shots / {ss_dur}s', flush=True)
    return res


class Reader:
    """In-process frame access (OpenCV FFmpeg backend). Reads forward when the target is close, seeks
    otherwise, and checks that every seek landed on the requested frame index."""

    def __init__(self, master):
        import cv2
        self.cv2, self.cap, self.pos = cv2, cv2.VideoCapture(str(master)), -1

    def rgb(self, frame):
        cv2 = self.cv2
        if not 0 <= frame - self.pos - 1 <= 36:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            self.pos = frame - 1
        bgr = None
        while self.pos < frame:
            ok, bgr = self.cap.read()
            if not ok:
                raise RuntimeError(f'cannot read frame {frame}')
            self.pos += 1
        got = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        if got != frame:
            raise RuntimeError(f'reader is at frame {got}, wanted {frame}')
        return bgr[..., ::-1].copy()


_CASC = {}


def _cascade(name):
    import cv2
    if name not in _CASC:
        _CASC[name] = cv2.CascadeClassifier(cv2.data.haarcascades + f'haarcascade_{name}.xml')
    return _CASC[name]


def faces_in(rgb):
    """Haar faces at half resolution, boxes in full-res pixels, de-duplicated (IoU > 0.3)."""
    import cv2
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    small = cv2.equalizeHist(cv2.resize(g, (g.shape[1] // 2, g.shape[0] // 2), interpolation=cv2.INTER_AREA))
    found = []
    for name, flip in (('frontalface_default', False), ('profileface', False), ('profileface', True)):
        img = cv2.flip(small, 1) if flip else small
        for (x, y, w, h) in _cascade(name).detectMultiScale(img, scaleFactor=1.1, minNeighbors=6, minSize=(36, 36)):
            if flip:
                x = img.shape[1] - x - w
            found.append(dict(x=2 * int(x), y=2 * int(y), w=2 * int(w), h=2 * int(h), kind=name + ('_r' if flip else '')))
    found.sort(key=lambda b: -b['w'] * b['h'])
    keep = []
    for b in found:
        if all(iou(b, k) <= 0.3 for k in keep):
            keep.append(b)
    return keep


def iou(a, b):
    ix = max(0, min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x']))
    iy = max(0, min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y']))
    inter = ix * iy
    return inter / float(a['w'] * a['h'] + b['w'] * b['h'] - inter or 1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--episode', default=None, help='episode.json (its folder is the output folder) -- config mode')
    ap.add_argument('--master', default=None, help='master video path -- config-free mode')
    ap.add_argument('--out', default=None, help='output directory (config-free mode; defaults to master_dir/shotmap_out)')
    ap.add_argument('--stage', default='all', choices=['cuts', 'keyframes', 'build', 'all'])
    a = ap.parse_args()
    if a.episode:
        build(a.episode, stage=a.stage)
    elif a.master:
        build(a.master, a.out, stage=a.stage)
    else:
        ap.error('either --episode or --master is required')
