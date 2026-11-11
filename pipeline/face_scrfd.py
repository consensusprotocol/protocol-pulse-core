#!/usr/bin/env python3
"""pipeline/face_scrfd.py — SCRFD-10G face detector (insightface buffalo_l det_10g.onnx) via
onnxruntime (CPU). Used to MEASURE faces for the vertical layout class (DEC-2/DEC-5): the
BlazeFace short-range model misses medium/small faces (Yahoo Finance's standing host, 2026-11-11) and
the Haar cascade over-counts (2-4 'faces' on a single talking head). Detection measures; the layout
rules in vertical_layout.py decide, deterministically."""
import os

import cv2
import numpy as np

MODEL = os.path.expanduser("~/.insightface/models/buffalo_l/det_10g.onnx")
MODEL_SHA256 = "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91"   # pinned 2026-11-11
INPUT = 640
SCORE_MIN = 0.5
NMS_IOU = 0.4
_SESSION = None


def _session():
    global _SESSION
    if _SESSION is None:
        import hashlib
        import onnxruntime as ort
        # the layout classes are only reproducible with this exact model: fail closed on any other
        if not os.path.exists(MODEL):
            raise FileNotFoundError(f"STOP: SCRFD model missing: {MODEL}")
        with open(MODEL, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest != MODEL_SHA256:
            raise RuntimeError(f"STOP: SCRFD model sha256 {digest[:12]}... is not the pinned {MODEL_SHA256[:12]}...")
        # CPU on purpose: this host's onnxruntime CUDA provider lacks cuDNN 8, and ~12 frames per clip
        # need no GPU (GPU1 must never be touched; GPU0 stays free for whisper/NVENC)
        _SESSION = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    return _SESSION


def _nms(boxes, scores):
    order, keep = scores.argsort()[::-1], []
    while order.size:
        i = order[0]
        keep.append(i)
        xx1, yy1 = np.maximum(boxes[i, 0], boxes[order[1:], 0]), np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2, yy2 = np.minimum(boxes[i, 2], boxes[order[1:], 2]), np.minimum(boxes[i, 3], boxes[order[1:], 3])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        area = lambda b: (b[..., 2] - b[..., 0]) * (b[..., 3] - b[..., 1])
        iou = inter / (area(boxes[i]) + area(boxes[order[1:]]) - inter + 1e-9)
        order = order[1:][iou <= NMS_IOU]
    return keep


def detect(bgr):
    """Faces in a BGR frame as [(x0, y0, x1, y1, score)] in frame pixels, largest first."""
    h, w = bgr.shape[:2]
    scale = INPUT / max(h, w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    canvas = np.zeros((INPUT, INPUT, 3), np.uint8)
    canvas[:nh, :nw] = cv2.resize(bgr, (nw, nh))
    blob = cv2.dnn.blobFromImage(canvas, 1.0 / 128, (INPUT, INPUT), (127.5, 127.5, 127.5), swapRB=True)
    sess = _session()
    outs = sess.run(None, {sess.get_inputs()[0].name: blob})
    boxes, scores = [], []
    for idx, stride in enumerate((8, 16, 32)):
        sc, bb = outs[idx].reshape(-1), outs[idx + 3].reshape(-1, 4) * stride
        g = INPUT // stride
        centers = (np.stack(np.mgrid[:g, :g][::-1], axis=-1).reshape(-1, 2) * stride).astype(np.float32)
        centers = np.repeat(centers, 2, axis=0)                     # two anchors per location
        keep = sc >= SCORE_MIN
        c, d = centers[keep], bb[keep]
        boxes.append(np.stack([c[:, 0] - d[:, 0], c[:, 1] - d[:, 1], c[:, 0] + d[:, 2], c[:, 1] + d[:, 3]], 1))
        scores.append(sc[keep])
    boxes, scores = np.concatenate(boxes) / scale, np.concatenate(scores)
    if not len(scores):
        return []
    out = [(*boxes[i].tolist(), float(scores[i])) for i in _nms(boxes, scores)]
    return sorted(out, key=lambda f: -(f[2] - f[0]) * (f[3] - f[1]))
