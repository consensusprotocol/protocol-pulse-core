"""
vertical/debug.py -- Debug drawing module for vertical (9:16) reframing.

ALL debug/diagnostic drawing (cv2.rectangle, cv2.putText, cv2.circle,
PIL ImageDraw) lives ONLY in this file.

Neither compositor.py nor reframe.py may import from this module at runtime
in the render path. This module is for offline diagnostics and QA only.
"""

import math
import logging
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

logger = logging.getLogger("vertical.debug")

# ── Constants ────────────────────────────────────────────────────────────────

_SEAM_COLOR   = (0, 0, 255)    # BGR red for seam lines
_TILE_COLOR   = (0, 255, 0)    # BGR green for tile rects
_FACE_COLOR   = (255, 255, 0)  # BGR cyan for face boxes
_LABEL_COLOR  = (255, 255, 255)
_LABEL_BG     = (40, 40, 40)
_BAND_COLOR   = (255, 100, 0)  # PIL RGB orange-blue for band boundaries
_CENTROID_R   = 6
_LINE_THICK   = 2
_FONT_SCALE   = 0.5
_FONT_THICK   = 1

_THUMB_W_16_9 = 240
_THUMB_H_16_9 = 135
_THUMB_W_9_16 = 135
_THUMB_H_9_16 = 240
_GRID_COLS_SHOT  = 4
_GRID_COLS_COMP  = 6
_GRID_PAD        = 4
_BG_GRAY         = 30


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_cv2():
    if cv2 is None:
        raise ImportError("cv2 (opencv-python) is required for debug drawing")


def _ensure_pil():
    if Image is None:
        raise ImportError("PIL (Pillow) is required for debug drawing")


def _put_label(img, text, x, y):
    """Draw a text label with dark background at (x, y) on a BGR image."""
    _ensure_cv2()
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX,
                                         _FONT_SCALE, _FONT_THICK)
    cv2.rectangle(img, (x, y - th - 4), (x + tw + 6, y + baseline + 2),
                  _LABEL_BG, cv2.FILLED)
    cv2.putText(img, text, (x + 3, y), cv2.FONT_HERSHEY_SIMPLEX,
                _FONT_SCALE, _LABEL_COLOR, _FONT_THICK, cv2.LINE_AA)


# ── Public API ───────────────────────────────────────────────────────────────

def draw_shot_debug(frame_bgr, shot: dict) -> np.ndarray:
    """Draw seam lines (red), tile rects (green), face boxes (cyan),
    layout label on a frame copy. Returns new array.

    Expected shot keys (all optional, drawn if present):
      seams:     list of int (y-coordinates of horizontal seam lines)
      tiles:     list of dict with 'x','y','w','h'
      faces:     list of dict with 'x','y','w','h'
      layout:    str  e.g. '2-up', '3-up', 'solo', 'full+col'
      shot_id:   str
    """
    _ensure_cv2()
    out = frame_bgr.copy()
    h, w = out.shape[:2]

    # Seam lines (red horizontal)
    for sy in shot.get("seams", []):
        sy = int(sy)
        if 0 <= sy < h:
            cv2.line(out, (0, sy), (w - 1, sy), _SEAM_COLOR, _LINE_THICK)

    # Tile rectangles (green)
    for tile in shot.get("tiles", []):
        tx, ty = int(tile.get("x", 0)), int(tile.get("y", 0))
        tw, th = int(tile.get("w", 0)), int(tile.get("h", 0))
        cv2.rectangle(out, (tx, ty), (tx + tw, ty + th), _TILE_COLOR,
                      _LINE_THICK)

    # Face boxes (cyan)
    for face in shot.get("faces", []):
        fx, fy = int(face.get("x", 0)), int(face.get("y", 0))
        fw, fh = int(face.get("w", 0)), int(face.get("h", 0))
        cv2.rectangle(out, (fx, fy), (fx + fw, fy + fh), _FACE_COLOR,
                      _LINE_THICK)
        # Cross-hair at center
        cx, cy = fx + fw // 2, fy + fh // 2
        cv2.drawMarker(out, (cx, cy), _FACE_COLOR, cv2.MARKER_CROSS, 10, 1)

    # Layout label top-left
    label_parts = []
    if shot.get("shot_id"):
        label_parts.append(shot["shot_id"])
    if shot.get("layout"):
        label_parts.append(shot["layout"])
    tile_count = len(shot.get("tiles", []))
    face_count = len(shot.get("faces", []))
    label_parts.append(f"tiles={tile_count} faces={face_count}")
    label = " | ".join(label_parts)
    _put_label(out, label, 8, 20)

    return out


def draw_composition_debug(canvas_pil, shot: dict,
                           band_rects: list) -> "Image.Image":
    """Draw band boundaries, face centroids, crop regions on a 9:16 canvas
    copy. Returns new Image.

    Args:
        canvas_pil: PIL Image (1080x1920 or any 9:16).
        shot:       dict with optional keys: faces, crop_regions, layout,
                    shot_id.
        band_rects: list of dict with 'x','y','w','h' (band positions on
                    the composed canvas).
    """
    _ensure_pil()
    out = canvas_pil.copy()
    draw = ImageDraw.Draw(out)

    # Band boundaries (orange dashed-style lines at top/bottom of each band)
    for band in band_rects:
        bx = int(band.get("x", 0))
        by = int(band.get("y", 0))
        bw = int(band.get("w", out.width))
        bh = int(band.get("h", 0))
        # Top edge
        draw.line([(bx, by), (bx + bw, by)], fill=(255, 140, 0), width=2)
        # Bottom edge
        draw.line([(bx, by + bh), (bx + bw, by + bh)],
                  fill=(255, 140, 0), width=2)

    # Face centroids (cyan circles)
    for face in shot.get("faces", []):
        fx = int(face.get("x", 0))
        fy = int(face.get("y", 0))
        fw = int(face.get("w", 0))
        fh = int(face.get("h", 0))
        cx = fx + fw // 2
        cy = fy + fh // 2
        r = _CENTROID_R
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                     outline=(0, 255, 255), width=2)
        draw.line([(cx - r, cy), (cx + r, cy)], fill=(0, 255, 255), width=1)
        draw.line([(cx, cy - r), (cx, cy + r)], fill=(0, 255, 255), width=1)

    # Crop regions (green rectangles)
    for crop in shot.get("crop_regions", []):
        cx = int(crop.get("x", 0))
        cy = int(crop.get("y", 0))
        cw = int(crop.get("w", 0))
        ch = int(crop.get("h", 0))
        draw.rectangle([(cx, cy), (cx + cw, cy + ch)],
                       outline=(0, 255, 0), width=2)

    # Label at top
    label_parts = []
    if shot.get("shot_id"):
        label_parts.append(shot["shot_id"])
    if shot.get("layout"):
        label_parts.append(shot["layout"])
    if label_parts:
        label = " | ".join(label_parts)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/"
                                      "DejaVuSansMono.ttf", 16)
        except (OSError, IOError):
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.rectangle([(4, 4), (tw + 12, th + 12)], fill=(30, 30, 30))
        draw.text((8, 6), label, fill=(255, 255, 255), font=font)

    return out


def save_debug_sheet(shots: list, debug_frames: list, out_png: str):
    """Grid of debug-annotated frames, one per shot.
    4 columns, 240x135 per thumb.

    Args:
        shots:        list of shot dicts (for labels).
        debug_frames: list of np.ndarray (BGR) -- already annotated via
                      draw_shot_debug.
        out_png:      output path for the grid PNG.
    """
    _ensure_cv2()
    n = len(debug_frames)
    if n == 0:
        logger.warning("[DEBUG] No frames to build debug sheet")
        return

    cols = _GRID_COLS_SHOT
    rows = math.ceil(n / cols)
    tw, th = _THUMB_W_16_9, _THUMB_H_16_9
    pad = _GRID_PAD

    canvas_w = cols * (tw + pad) + pad
    canvas_h = rows * (th + pad) + pad
    canvas = np.full((canvas_h, canvas_w, 3), _BG_GRAY, dtype=np.uint8)

    for idx, frame in enumerate(debug_frames):
        if frame is None:
            continue
        r = idx // cols
        c = idx % cols
        x = pad + c * (tw + pad)
        y = pad + r * (th + pad)

        thumb = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
        canvas[y:y + th, x:x + tw] = thumb

        # Shot label below thumb
        shot = shots[idx] if idx < len(shots) else {}
        sid = shot.get("shot_id", f"s{idx:02d}")
        layout = shot.get("layout", "?")
        label = f"{sid} [{layout}]"
        _put_label(canvas, label, x, y + th - 4)

    cv2.imwrite(out_png, canvas)
    logger.info(f"[DEBUG] Shot debug sheet saved: {out_png} "
                f"({rows}x{cols}, {n} shots)")


def save_debug_contact(shots: list, composed_frames: list, out_png: str):
    """Contact sheet of composed 9:16 frames.
    6 columns, 135x240 per thumb.

    Args:
        shots:           list of shot dicts (for labels).
        composed_frames: list of PIL.Image (9:16 composed frames) or
                         np.ndarray (BGR).
        out_png:         output path for the contact sheet PNG.
    """
    _ensure_cv2()
    _ensure_pil()
    n = len(composed_frames)
    if n == 0:
        logger.warning("[DEBUG] No frames to build contact sheet")
        return

    cols = _GRID_COLS_COMP
    rows = math.ceil(n / cols)
    tw, th = _THUMB_W_9_16, _THUMB_H_9_16
    pad = _GRID_PAD

    canvas_w = cols * (tw + pad) + pad
    canvas_h = rows * (th + pad) + pad
    canvas = np.full((canvas_h, canvas_w, 3), _BG_GRAY, dtype=np.uint8)

    for idx, frame in enumerate(composed_frames):
        if frame is None:
            continue
        r = idx // cols
        c = idx % cols
        x = pad + c * (tw + pad)
        y = pad + r * (th + pad)

        # Convert PIL to BGR numpy if needed
        if isinstance(frame, np.ndarray):
            bgr = frame
        else:
            bgr = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)

        thumb = cv2.resize(bgr, (tw, th), interpolation=cv2.INTER_AREA)
        canvas[y:y + th, x:x + tw] = thumb

        # Shot label
        shot = shots[idx] if idx < len(shots) else {}
        sid = shot.get("shot_id", f"s{idx:02d}")
        layout = shot.get("layout", "?")
        label = f"{sid} [{layout}]"
        _put_label(canvas, label, x, y + th - 8)

    cv2.imwrite(out_png, canvas)
    logger.info(f"[DEBUG] Composition contact sheet saved: {out_png} "
                f"({rows}x{cols}, {n} shots)")
