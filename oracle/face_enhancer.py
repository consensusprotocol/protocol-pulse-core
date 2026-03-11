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
    if not frames: return frames
    enhancer = _load_gfpgan()
    y1, y2, x1, x2 = face_coords
    if enhancer is not None:
        try:
            out = []
            for frame in frames:
                try:
                    face_rgb = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2RGB)
                    _, _, restored = enhancer.enhance(face_rgb, has_aligned=False,
                        only_center_face=True, paste_back=True)
                    if restored is not None:
                        result = frame.copy()
                        result[y1:y2, x1:x2] = cv2.resize(
                            cv2.cvtColor(restored, cv2.COLOR_RGB2BGR), (x2-x1, y2-y1))
                        out.append(result)
                    else:
                        out.append(frame)
                except Exception: out.append(frame)
            logger.info("GFPGAN enhanced %d frames", len(out))
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
