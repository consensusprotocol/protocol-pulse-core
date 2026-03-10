"""
BLINK ENGINE — Natural eye blinks using MediaPipe face mesh.
Replaces the disabled apply_blink() that caused black oval artifacts.

Approach: detect exact eye landmark positions -> apply gradient eyelid overlay
instead of warpAffine (which caused the artifacts).
"""
import cv2
import numpy as np
import math
import random
import logging

logger = logging.getLogger("blink_engine")

# MediaPipe face mesh eye landmark indices
# Upper eyelid: 159, 145 (left eye), 386, 374 (right eye)
# Eye corners: 33, 133 (left), 362, 263 (right)
LEFT_EYE_UPPER = [159, 158, 157, 173, 133]
LEFT_EYE_LOWER = [145, 144, 163, 7, 33]
RIGHT_EYE_UPPER = [386, 385, 384, 398, 362]
RIGHT_EYE_LOWER = [374, 373, 390, 249, 263]

_mp_face_mesh = None
_mp_loaded = False


def _load_mediapipe():
    global _mp_face_mesh, _mp_loaded
    try:
        import mediapipe as mp
        _mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        _mp_loaded = True
        logger.info("MediaPipe FaceMesh loaded")
    except Exception as e:
        logger.warning(f"MediaPipe unavailable: {e} — using fallback blink")
        _mp_loaded = False


def detect_eye_landmarks(frame):
    """Return eye polygon points from MediaPipe, or None if unavailable."""
    global _mp_face_mesh, _mp_loaded
    if not _mp_loaded:
        _load_mediapipe()
    if not _mp_loaded:
        return None

    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = _mp_face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return None

        lm = results.multi_face_landmarks[0].landmark
        h, w = frame.shape[:2]

        def get_pts(indices):
            return [(int(lm[i].x * w), int(lm[i].y * h)) for i in indices]

        return {
            'left_upper': get_pts(LEFT_EYE_UPPER),
            'left_lower': get_pts(LEFT_EYE_LOWER),
            'right_upper': get_pts(RIGHT_EYE_UPPER),
            'right_lower': get_pts(RIGHT_EYE_LOWER),
        }
    except Exception:
        return None


def apply_blink_gradient(frame, intensity, eye_landmarks=None, face_coords=None):
    """
    Apply eye blink using gradient eyelid overlay — NO warpAffine artifacts.

    intensity: 0.0 (eyes open) to 1.0 (eyes fully closed)
    eye_landmarks: from detect_eye_landmarks() or None (uses face_coords fallback)
    """
    if intensity <= 0.02:
        return frame

    result = frame.copy()

    if eye_landmarks is not None:
        # MediaPipe path: draw filled polygon over upper eyelid area
        h, w = frame.shape[:2]

        for side in ['left', 'right']:
            upper = eye_landmarks[f'{side}_upper']
            lower = eye_landmarks[f'{side}_lower']

            if not upper or not lower:
                continue

            # Build eyelid polygon (upper portion closes down)
            upper_arr = np.array(upper, dtype=np.float32)
            lower_arr = np.array(lower, dtype=np.float32)

            # Interpolate: at intensity=1.0, upper points move to lower points
            closed_upper = (upper_arr * (1 - intensity) + lower_arr * intensity).astype(np.int32)

            # Full polygon: closed upper + lower (creates filled eye shape)
            poly = np.concatenate([closed_upper, lower_arr.astype(np.int32)[::-1]])

            # Sample skin color near forehead
            forehead_y = max(0, min(int(upper_arr[:, 1].min()) - 15, h - 1))
            forehead_x = int(np.mean(upper_arr[:, 0]))
            forehead_x = max(0, min(forehead_x, w - 1))
            skin_color = frame[forehead_y, forehead_x].astype(np.float32)

            # Create mask for smooth blend
            mask = np.zeros((h, w), dtype=np.float32)
            cv2.fillPoly(mask, [poly], 1.0)

            # Feather the mask edges
            mask = cv2.GaussianBlur(mask, (5, 5), 2)

            # Apply skin color over eye region
            for c in range(3):
                result[:, :, c] = (
                    result[:, :, c] * (1 - mask * intensity * 0.9) +
                    skin_color[c] * (mask * intensity * 0.9)
                ).astype(np.uint8)

    else:
        # Fallback: use face_coords to estimate eye positions
        if face_coords is None:
            return frame

        y1, y2, x1, x2 = face_coords
        face_h = y2 - y1
        face_w = x2 - x1

        # Eyes are roughly at 35-45% face height, left/right thirds
        eye_y_center = y1 + int(face_h * 0.40)
        eye_h = int(face_h * 0.10)

        for eye_x_center in [x1 + int(face_w * 0.28), x1 + int(face_w * 0.72)]:
            eye_w = int(face_w * 0.22)

            # Sample skin color from near eyebrow
            brow_y = max(0, eye_y_center - eye_h - 5)
            brow_x = max(0, min(eye_x_center, frame.shape[1] - 1))
            skin_color = frame[brow_y, brow_x].astype(np.float32)

            # Eyelid rectangle that closes from top
            lid_top = eye_y_center - eye_h
            lid_bottom = int(eye_y_center - eye_h + (eye_h * 2 * intensity))
            lid_left = eye_x_center - eye_w // 2
            lid_right = eye_x_center + eye_w // 2

            if lid_bottom > lid_top:
                # Gradient blend
                for row in range(max(0, lid_top), min(result.shape[0], lid_bottom)):
                    row_intensity = intensity * min(1.0, (row - lid_top + 1) / max(1, lid_bottom - lid_top))
                    c_left = max(0, lid_left)
                    c_right = min(result.shape[1], lid_right)
                    result[row, c_left:c_right] = (
                        result[row, c_left:c_right] * (1 - row_intensity) +
                        skin_color * row_intensity
                    ).astype(np.uint8)

    return result


def generate_blink_schedule(num_frames, fps, interval_min=2.5, interval_max=5.0, duration=0.22):
    """Generate randomized blink timing schedule."""
    blink_frames = {}
    duration_sec = num_frames / fps
    t = random.uniform(interval_min, interval_max)

    while t < duration_sec - duration:
        center_frame = int(t * fps)
        half_frames = int((duration / 2) * fps)

        for offset in range(-half_frames, half_frames + 1):
            frame_idx = center_frame + offset
            if 0 <= frame_idx < num_frames:
                progress = abs(offset) / max(half_frames, 1)
                # Cosine curve: peaks at center of blink
                intensity = 0.5 * (1 + math.cos(math.pi * progress))
                blink_frames[frame_idx] = max(blink_frames.get(frame_idx, 0), intensity)

        t += duration + random.uniform(interval_min, interval_max)

    return blink_frames


def apply_blink(frame, intensity=0.0, face_coords=None):
    """LAW 2: Permanently disabled — black oval artifact prevention.
    Body is return frame per gospel. Do not re-enable.
    """
    return frame
