import cv2, numpy as np, logging, os
logger = logging.getLogger(__name__)
_gfpgan_enhancer = None
_gfpgan_loaded = False
GFPGAN_WEIGHT = os.path.expanduser("~/SadTalker/gfpgan/weights/GFPGANv1.4.pth")

def _load_gfpgan():
    global _gfpgan_enhancer, _gfpgan_loaded
    if _gfpgan_loaded: return _gfpgan_enhancer
    try:
        from gfpgan import GFPGANer
        _gfpgan_enhancer = GFPGANer(model_path=GFPGAN_WEIGHT, upscale=1, arch="clean",
            channel_multiplier=2, bg_upsampler=None, device="cuda:1")
        logger.info("GFPGAN loaded OK")
    except Exception as e:
        logger.warning("GFPGAN load failed: %s", e)
        _gfpgan_enhancer = None
    _gfpgan_loaded = True
    return _gfpgan_enhancer

def enhance_frames_batch(frames, face_coords, batch_size=16):
    """Enhance frames using GFPGAN. Processes every 3rd frame and copies result
    to adjacent frames (face doesn't change much frame-to-frame in lip-sync).
    Uses has_aligned=True to skip GFPGAN's internal face detection (~10x faster)."""
    if not frames: return frames
    enhancer = _load_gfpgan()
    y1, y2, x1, x2 = face_coords
    if enhancer is not None:
        try:
            out = list(frames)  # shallow copy
            step = 3  # enhance every 3rd frame, copy to neighbors
            enhanced_count = 0
            for i in range(0, len(frames), step):
                try:
                    face_crop = frames[i][y1:y2, x1:x2]
                    face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                    # has_aligned=True: skip face detection, treat input as aligned face
                    _, _, restored = enhancer.enhance(face_rgb, has_aligned=True,
                        only_center_face=True, paste_back=False)
                    if restored is not None:
                        restored_bgr = cv2.resize(
                            cv2.cvtColor(restored, cv2.COLOR_RGB2BGR), (x2-x1, y2-y1))
                        # Apply to this frame and up to step-1 neighbors
                        for j in range(i, min(i + step, len(frames))):
                            result = frames[j].copy()
                            result[y1:y2, x1:x2] = restored_bgr
                            out[j] = result
                        enhanced_count += 1
                except Exception:
                    pass
            logger.info("GFPGAN enhanced %d keyframes (%d total frames)", enhanced_count, len(out))
            return out
        except Exception as e:
            logger.warning("GFPGAN batch failed: %s", e)
    return sharpen_mouth_region(frames, face_coords)

def sharpen_mouth_region(frames, face_coords):
    y1, y2, x1, x2 = face_coords
    mouth_y1 = y1 + int((y2 - y1) * 0.45)
    kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]], dtype=np.float32)
    out = []
    for frame in frames:
        try:
            region = frame[mouth_y1:y2, x1:x2].copy()
            smooth = cv2.bilateralFilter(region, d=5, sigmaColor=40, sigmaSpace=5)
            blended = cv2.addWeighted(cv2.filter2D(smooth,-1,kernel), 0.65, smooth, 0.35, 0)
            result = frame.copy(); result[mouth_y1:y2, x1:x2] = blended
            out.append(result)
        except Exception: out.append(frame)
    return out
