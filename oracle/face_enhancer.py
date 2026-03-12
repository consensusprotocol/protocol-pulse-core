"""
FACE ENHANCER — CV2 sharpen-only (GFPGAN fully removed 2026-03-12)
===================================================================
GFPGAN was adding 60s+ per generation and loading 500MB+ into VRAM.
Replaced with bilateral filter + sharpen kernel — instant, zero ML deps.
"""
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def enhance_frames_batch(frames, face_coords, batch_size=16):
    """No-op passthrough. GFPGAN removed — use sharpen_mouth_region() instead."""
    return frames


def sharpen_mouth_region(frames, face_coords):
    """CV2 bilateral filter + sharpen kernel on mouth region. Instant, no ML."""
    y1, y2, x1, x2 = face_coords
    mouth_y1 = y1 + int((y2 - y1) * 0.45)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
    out = []
    for frame in frames:
        try:
            region = frame[mouth_y1:y2, x1:x2].copy()
            smooth = cv2.bilateralFilter(region, d=5, sigmaColor=40, sigmaSpace=5)
            blended = cv2.addWeighted(cv2.filter2D(smooth, -1, kernel), 0.65, smooth, 0.35, 0)
            result = frame.copy()
            result[mouth_y1:y2, x1:x2] = blended
            out.append(result)
        except Exception:
            out.append(frame)
    return out
