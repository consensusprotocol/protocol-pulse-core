"""
vertical/speaker_eval.py -- Lip-activity speaker evaluation using
MediaPipe FaceLandmarker.

Evaluation only -- not shipped into the render path.

Method per tile per shot (2-up and 3-up only):
  - Extract frames at ~5 fps
  - Run FaceLandmarker, get 478 landmarks
  - Mouth Aspect Ratio = dist(lm13, lm14) / dist(lm10, lm152)
  - lip_active = MAR > threshold
  - Per tile per 1-second window: fraction of frames with lip_active
  - Winner = tile with highest activity fraction
  - Margin = winner_pct - runner_up_pct

Model: /home/ultron/protocol_pulse/oracle/assets/face_landmarker.task
"""

import os
import math
import json
import logging
import numpy as np

logger = logging.getLogger("vertical.speaker_eval")

_MODEL_PATH = "/home/ultron/protocol_pulse/oracle/assets/face_landmarker.task"
_DEFAULT_MAR_THRESHOLD = 0.04
_SAMPLE_FPS = 5

# MediaPipe landmark indices for mouth aspect ratio
_LM_UPPER_LIP = 13   # upper lip center (inner)
_LM_LOWER_LIP = 14   # lower lip center (inner)
_LM_NOSE_TIP  = 10   # nose tip (used as top reference)
_LM_CHIN      = 152  # chin (bottom reference)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _dist(a, b):
    """Euclidean distance between two (x, y) or (x, y, z) points."""
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def _extract_tile_region(frame, tile: dict):
    """Crop a tile region from a full 16:9 source frame.

    Args:
        frame: np.ndarray (H, W, 3) BGR.
        tile:  dict with 'x', 'y', 'w', 'h' in source pixel coords.

    Returns:
        np.ndarray cropped tile or None if out of bounds.
    """
    h, w = frame.shape[:2]
    tx = max(0, int(tile.get("x", 0)))
    ty = max(0, int(tile.get("y", 0)))
    tw = int(tile.get("w", 0))
    th = int(tile.get("h", 0))
    tx2 = min(w, tx + tw)
    ty2 = min(h, ty + th)
    if tx2 <= tx or ty2 <= ty:
        return None
    return frame[ty:ty2, tx:tx2]


def _create_landmarker():
    """Create a MediaPipe FaceLandmarker instance (IMAGE mode)."""
    import mediapipe as mp
    from mediapipe.tasks.python.vision import (
        FaceLandmarker, FaceLandmarkerOptions, RunningMode
    )

    if not os.path.exists(_MODEL_PATH):
        raise FileNotFoundError(
            f"FaceLandmarker model not found: {_MODEL_PATH}")

    opts = FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=_MODEL_PATH),
        running_mode=RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.3,
        min_face_presence_confidence=0.3,
    )
    return FaceLandmarker.create_from_options(opts)


def _compute_mar(landmarks) -> float:
    """Compute Mouth Aspect Ratio from 478 MediaPipe face landmarks.

    MAR = dist(landmark 13, landmark 14) / dist(landmark 10, landmark 152)

    A higher MAR indicates the mouth is more open (speaking).
    """
    lm13 = (landmarks[_LM_UPPER_LIP].x, landmarks[_LM_UPPER_LIP].y)
    lm14 = (landmarks[_LM_LOWER_LIP].x, landmarks[_LM_LOWER_LIP].y)
    lm10 = (landmarks[_LM_NOSE_TIP].x, landmarks[_LM_NOSE_TIP].y)
    lm152 = (landmarks[_LM_CHIN].x, landmarks[_LM_CHIN].y)

    mouth_open = _dist(lm13, lm14)
    face_height = _dist(lm10, lm152)

    if face_height < 1e-6:
        return 0.0
    return mouth_open / face_height


def _get_frame_indices(total_frames: int, source_fps: float) -> list:
    """Compute frame indices to sample at _SAMPLE_FPS from the source."""
    if source_fps <= 0 or total_frames <= 0:
        return []
    step = max(1, int(round(source_fps / _SAMPLE_FPS)))
    return list(range(0, total_frames, step))


# ── Core evaluation ──────────────────────────────────────────────────────────

def _evaluate_tile_activity(cap, tile: dict, frame_indices: list,
                            landmarker, threshold: float) -> list:
    """Run lip-activity detection on one tile across sampled frames.

    Returns list of (frame_idx, mar, is_active) tuples.
    """
    import cv2
    import mediapipe as mp

    results = []
    for fidx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
        ret, frame = cap.read()
        if not ret:
            continue

        crop = _extract_tile_region(frame, tile)
        if crop is None or crop.size == 0:
            results.append((fidx, 0.0, False))
            continue

        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        try:
            det = landmarker.detect(mp_image)
        except Exception:
            results.append((fidx, 0.0, False))
            continue

        if not det.face_landmarks:
            results.append((fidx, 0.0, False))
            continue

        mar = _compute_mar(det.face_landmarks[0])
        active = mar > threshold
        results.append((fidx, mar, active))

    return results


def _build_windows(tile_results: list, source_fps: float) -> list:
    """Group frame-level results into 1-second windows.
    Returns list of {t_start, t_end, active_frac, n_frames}."""
    if not tile_results or source_fps <= 0:
        return []

    windows = []
    win_start_frame = tile_results[0][0]
    win_frames = []
    window_size_frames = source_fps  # 1 second

    for fidx, mar, active in tile_results:
        # Check if this frame belongs to the current window
        if fidx - win_start_frame >= window_size_frames and win_frames:
            n = len(win_frames)
            active_count = sum(1 for _, _, a in win_frames if a)
            windows.append({
                "t_start": round(win_start_frame / source_fps, 2),
                "t_end": round(fidx / source_fps, 2),
                "active_frac": round(active_count / n, 4) if n else 0.0,
                "n_frames": n,
            })
            win_start_frame = fidx
            win_frames = []

        win_frames.append((fidx, mar, active))

    # Final window
    if win_frames:
        n = len(win_frames)
        active_count = sum(1 for _, _, a in win_frames if a)
        last_fidx = win_frames[-1][0]
        windows.append({
            "t_start": round(win_start_frame / source_fps, 2),
            "t_end": round((last_fidx + 1) / source_fps, 2),
            "active_frac": round(active_count / n, 4) if n else 0.0,
            "n_frames": n,
        })

    return windows


def _pick_winner(tile_windows: dict) -> list:
    """Given per-tile window lists, pick per-window winner.

    Args:
        tile_windows: {tile_idx: [windows...]}

    Returns:
        list of {t, winner_tile, margin, tiles: {idx: pct}}
        aligned by window index.
    """
    # Determine the max number of windows across tiles
    max_wins = max((len(w) for w in tile_windows.values()), default=0)
    results = []

    for wi in range(max_wins):
        tile_pcts = {}
        for tidx, wins in tile_windows.items():
            if wi < len(wins):
                tile_pcts[tidx] = wins[wi]["active_frac"]
            else:
                tile_pcts[tidx] = 0.0

        # Determine time from any tile that has this window
        t = 0.0
        for wins in tile_windows.values():
            if wi < len(wins):
                t = wins[wi]["t_start"]
                break

        if not tile_pcts:
            continue

        sorted_tiles = sorted(tile_pcts.items(), key=lambda x: x[1],
                              reverse=True)
        winner = sorted_tiles[0][0]
        winner_pct = sorted_tiles[0][1]
        runner_pct = sorted_tiles[1][1] if len(sorted_tiles) > 1 else 0.0
        margin = round(winner_pct - runner_pct, 4)

        results.append({
            "t": t,
            "winner_tile": winner,
            "margin": margin,
            "tiles": {str(k): round(v, 4) for k, v in tile_pcts.items()},
        })

    return results


# ── Public API ───────────────────────────────────────────────────────────────

def evaluate_speakers(master_path: str, shot_map: dict,
                      work_dir: str,
                      mar_threshold: float = _DEFAULT_MAR_THRESHOLD) -> dict:
    """Per-shot speaker evaluation using lip activity.

    Only evaluates 2-up and 3-up layouts (multi-tile shots where speaker
    identification is meaningful).

    Args:
        master_path: path to the source 16:9 master video.
        shot_map:    dict with 'shots' key containing list of shot dicts.
                     Each shot has: shot_id, layout, tiles (list with
                     x/y/w/h), start_frame, end_frame.
        work_dir:    directory for temporary files.
        mar_threshold: MAR threshold for lip-active detection.

    Returns:
        {shots: [{shot_id, windows: [{t, winner_tile, margin,
                  tiles: {0: pct, 1: pct, ...}}], ...}]}
    """
    import cv2

    os.makedirs(work_dir, exist_ok=True)

    cap = cv2.VideoCapture(master_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {master_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    landmarker = _create_landmarker()
    shot_results = []

    shots = shot_map.get("shots", shot_map.get("shot_map", []))
    if isinstance(shots, dict):
        shots = list(shots.values())

    for shot in shots:
        shot_id = shot.get("shot_id", "unknown")
        layout = shot.get("layout", "")
        tiles = shot.get("tiles", [])

        # Only evaluate multi-tile layouts
        if layout not in ("2-up", "3-up") or len(tiles) < 2:
            logger.debug(f"[SPEAKER] Skipping {shot_id} "
                         f"(layout={layout}, tiles={len(tiles)})")
            continue

        start_f = int(shot.get("start_frame", 0))
        end_f = int(shot.get("end_frame", total_frames))
        end_f = min(end_f, total_frames)

        # Frame indices to sample within this shot's range
        all_indices = _get_frame_indices(end_f - start_f, source_fps)
        frame_indices = [start_f + i for i in all_indices if start_f + i < end_f]

        if not frame_indices:
            logger.warning(f"[SPEAKER] No frames to sample for {shot_id}")
            continue

        # Evaluate each tile
        tile_windows = {}
        for tidx, tile in enumerate(tiles):
            activity = _evaluate_tile_activity(
                cap, tile, frame_indices, landmarker, mar_threshold)
            windows = _build_windows(activity, source_fps)
            tile_windows[tidx] = windows

        # Pick per-window winner
        windows = _pick_winner(tile_windows)

        shot_results.append({
            "shot_id": shot_id,
            "layout": layout,
            "n_tiles": len(tiles),
            "windows": windows,
        })
        logger.info(f"[SPEAKER] {shot_id}: {len(windows)} windows evaluated, "
                    f"{len(tiles)} tiles")

    cap.release()
    landmarker.close()

    logger.info(f"[SPEAKER] Evaluation complete: "
                f"{len(shot_results)} shots processed")

    return {"shots": shot_results}


def compare_with_truth(eval_results: dict, truth_path: str) -> dict:
    """Compare evaluation results with human-labeled ground truth.

    Args:
        eval_results: output of evaluate_speakers().
        truth_path:   path to JSON file with ground truth, structured as:
                      {shots: [{shot_id, windows: [{t, speaker_tile}]}]}

    Returns:
        {precision, recall, accuracy, total_windows, per_window: [...]}
    """
    with open(truth_path) as f:
        truth = json.load(f)

    # Index truth by (shot_id, window_t)
    truth_index = {}
    truth_shots = truth.get("shots", [])
    for ts in truth_shots:
        sid = ts.get("shot_id", "")
        for tw in ts.get("windows", []):
            key = (sid, tw.get("t", 0.0))
            truth_index[key] = tw.get("speaker_tile")

    # Compare
    per_window = []
    tp = 0  # true positives (correct winner)
    fp = 0  # false positives (wrong winner)
    fn = 0  # false negatives (truth exists, no eval)
    total = 0

    for shot in eval_results.get("shots", []):
        sid = shot.get("shot_id", "")
        for win in shot.get("windows", []):
            t = win.get("t", 0.0)
            predicted = win.get("winner_tile")
            key = (sid, t)
            actual = truth_index.pop(key, None)

            if actual is None:
                # No truth for this window, skip
                per_window.append({
                    "shot_id": sid, "t": t,
                    "predicted": predicted, "actual": None,
                    "match": None,
                })
                continue

            total += 1
            match = (predicted == actual)
            if match:
                tp += 1
            else:
                fp += 1

            per_window.append({
                "shot_id": sid, "t": t,
                "predicted": predicted, "actual": actual,
                "match": match,
            })

    # Remaining truth entries with no prediction
    for key, actual in truth_index.items():
        fn += 1
        total += 1
        per_window.append({
            "shot_id": key[0], "t": key[1],
            "predicted": None, "actual": actual,
            "match": False,
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    accuracy = tp / total if total > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "accuracy": round(accuracy, 4),
        "total_windows": total,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "per_window": per_window,
    }
