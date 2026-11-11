#!/usr/bin/env python3
"""pipeline/credit_rings.py — DEC-11 (orchestrator 2026-11-11 13:15 ET): G12 / G15 measure the credits ring by
what the renderer draws, not by a generic circle search over the avatar artwork (OD-1: the capital N of
"Natalie Brunell" passed the old size filter as a "squished ring").

The renderer (segment_v1/scene_shoutout.render_shoutout) draws each channel's ring as a brand-red (#FF1A1A)
outline of radius avatar_diam // 2 + ring_gap around a node at a position fixed by the card layout. A ring
here is the brand-red mask (G12's rule, unchanged: R > 100, R > G + 40, R > B + 40) taken as ONE external
contour: its outer boundary is the ring (plus its glow) whatever avatar artwork sits inside, and the ellipse
is fitted to that boundary, never to a circle assumed in advance. A contour is a ring when its bounding box
has a ring's size (from the layout scale); G15's aspect tolerance (>= 0.95) and G12's count rule (== the
channels in the EDL) are unchanged. G12 also requires each ring at its layout position for that count."""
import functools

import cv2
import numpy as np

ASPECT_MIN = 0.95             # G15's tolerance, unchanged (aspect < 0.95 = squished)
AVATAR_R_MIN = 0.90           # the disc inside ring i correlates with channel i's registered avatar (grey,
                              # inner 118 px radius): measured 0.999-1.000 on every node of the v2f and Nov 11
                              # cards (both formats); yesterday's squashed video thumbnails 0.297 / -0.030 / -0.142.
                              # Yesterday's RINGS are round (0.999-1.000): the D4 defect was the content inside.
SIZE_RANGE = (0.80, 1.30)     # ring bbox side / expected outer diameter (core ring + glow); a warped ring
                              # keeps its long axis, so this filters glyphs and rays, not warps
POS_TOL = 0.25                # a ring sits at its layout position: centre within 0.25 ring radii (35 px)


def card_layout(w, h, n):
    """The node centres and ring radius scene_shoutout.render_shoutout uses for n channels (its lines 141-206)."""
    scale = min(w, h) / 1080.0
    avatar_diam = int(260 * scale)
    ring_r = avatar_diam // 2 + int(8 * scale)
    if h > w:                                      # 9:16: stacked in the middle
        node_h = avatar_diam + 10 + int(46 * scale) + 5 + int(32 * scale)
        sp = int(80 * scale)
        y0 = (h - (n * node_h + (n - 1) * sp)) // 2
        pos = [(w // 2, y0 + i * (node_h + sp) + avatar_diam // 2) for i in range(n)]
    else:                                          # 16:9: one row
        gap = int(200 * scale)
        x0 = (w - (n * avatar_diam + (n - 1) * gap)) // 2 + avatar_diam // 2
        pos = [(x0 + i * (avatar_diam + gap), h // 2 - int(30 * scale)) for i in range(n)]
    return {"ring_r": ring_r, "outer_d": 2 * (ring_r + int(12 * scale)), "positions": pos}


def red_mask(img_bgr):
    b, g, r = (c.astype(np.int16) for c in cv2.split(img_bgr))
    return ((r > 100) & (r > g + 40) & (r > b + 40)).astype(np.uint8) * 255


def find_rings(img_bgr):
    """Every ring-sized brand-red contour: centre, bbox, fitted ellipse axes, aspect."""
    h, w = img_bgr.shape[:2]
    exp_d = card_layout(w, h, 1)["outer_d"]
    contours, _ = cv2.findContours(red_mask(img_bgr), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    rings = []
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        if not (SIZE_RANGE[0] * exp_d <= max(bw, bh) <= SIZE_RANGE[1] * exp_d) or len(c) < 20:
            continue
        (cx, cy), (a1, a2), ang = cv2.fitEllipse(c)
        lo, hi = min(a1, a2), max(a1, a2)
        rings.append({"cx": round(cx, 1), "cy": round(cy, 1), "bbox": [x, y, bw, bh],
                      "axes": [round(lo, 1), round(hi, 1)], "aspect": round(lo / hi, 3) if hi else 0.0})
    return sorted(rings, key=lambda r: (r["cy"], r["cx"]))


def credit_channels(edl):
    """The credited channels in card order, as pipeline/shoutout.build_shoutout builds them: the hook's
    channel first, then each clip's in EDL order, each once."""
    out = []
    for seg in [edl.get("hook") or {}] + list(edl.get("clips") or []):
        ch = seg.get("channel", "")
        if ch and ch not in out:
            out.append(ch)
    return out


@functools.lru_cache(maxsize=1)
def _registry():
    import json
    import os
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")) as f:
        return tuple(json.load(f))


def registered_avatar(channel):
    """The channel's avatar from pipeline/channels.json (the only avatars the renderer may draw). Paths come
    from that internal registry only, never from user input."""
    import os
    entry = next((e for e in _registry() if e.get("display_name") == channel), None)
    path = (entry or {}).get("avatar_path", "")
    return path if path and os.path.exists(path) else None


def disc_matches(img_bgr, channels):
    """Correlation of the disc the renderer drew at node i with channel i's registered avatar, resized and
    masked the way render_shoutout draws it. None for a channel with no registered avatar (= no match)."""
    from PIL import Image
    if not channels:                               # the caller fails closed on an empty result
        return []
    h, w = img_bgr.shape[:2]
    scale = min(w, h) / 1080.0
    lay = card_layout(w, h, len(channels))
    r_av = lay["ring_r"] - int(8 * scale)
    r_in = r_av - int(12 * scale)
    yy, xx = np.mgrid[0:2 * r_av, 0:2 * r_av]
    m = (yy - r_av + 0.5) ** 2 + (xx - r_av + 0.5) ** 2 <= r_in ** 2
    out = []
    for (cx, cy), ch in zip(lay["positions"], channels):
        path = registered_avatar(ch)
        crop = img_bgr[cy - r_av:cy + r_av, cx - r_av:cx + r_av]
        if path is None or crop.shape[:2] != (2 * r_av, 2 * r_av):
            out.append({"channel": ch, "r": None})
            continue
        ref = Image.open(path).convert("RGB").resize((2 * r_av, 2 * r_av), Image.LANCZOS)
        a = cv2.cvtColor(np.array(ref), cv2.COLOR_RGB2GRAY).astype(float)[m]
        b = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(float)[m]
        r = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else 0.0
        out.append({"channel": ch, "r": round(r, 3)})
    return out


def check_card(img_bgr, n_expected=None):
    """Returns (count, aspect_ok, at_layout, rings). at_layout: every layout node for n_expected has one
    ring within POS_TOL ring radii (None when n_expected is not given)."""
    rings = find_rings(img_bgr)
    aspect_ok = bool(rings) and all(r["aspect"] >= ASPECT_MIN for r in rings)
    at_layout = None
    if n_expected:
        h, w = img_bgr.shape[:2]
        lay = card_layout(w, h, n_expected)
        tol = POS_TOL * lay["ring_r"]
        at_layout = all(any(np.hypot(r["cx"] - px, r["cy"] - py) <= tol for r in rings)
                        for px, py in lay["positions"])
    return len(rings), aspect_ok, at_layout, rings
