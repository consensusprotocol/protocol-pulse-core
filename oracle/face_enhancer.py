"""
FACE ENHANCER — Post-process Wav2Lip frames with face restoration.
Upgrades blurry 96x96 mouth to sharp, detailed output.
Industry approach: Wav2Lip (sync) + GFPGAN/CodeFormer (quality).
"""
import os
import sys
import cv2
import numpy as np
import logging
import threading

logger = logging.getLogger("face_enhancer")

_enhancer = None
_enhancer_lock = threading.Lock()
_enhancer_type = None  # 'codeformer', 'gfpgan', or None


def _load_enhancer():
    """Load best available face restorer. CodeFormer > GFPGAN > None."""
    global _enhancer, _enhancer_type

    # Try CodeFormer first (better on lower face/mouth)
    try:
        codeformer_dir = os.path.expanduser('~/CodeFormer')
        if codeformer_dir not in sys.path:
            sys.path.insert(0, codeformer_dir)

        import torch
        from basicsr.utils.registry import ARCH_REGISTRY

        # Check if weights exist
        weight_path = os.path.join(codeformer_dir, 'weights/CodeFormer/codeformer.pth')
        if not os.path.exists(weight_path):
            alt_path = os.path.expanduser('~/.cache/CodeFormer/weights/CodeFormer/codeformer.pth')
            if os.path.exists(alt_path):
                weight_path = alt_path
            else:
                raise FileNotFoundError("CodeFormer weights not found")

        # Load CodeFormer network
        net = ARCH_REGISTRY.get('CodeFormer')(
            dim_embd=512, codebook_size=1024, n_head=8, n_layers=9,
            connect_list=['32', '64', '128', '256']
        ).to('cuda:1')

        ckpt = torch.load(weight_path, map_location='cuda:1')['params_ema']
        net.load_state_dict(ckpt)
        net.eval()

        _enhancer = net
        _enhancer_type = 'codeformer'
        logger.info("CodeFormer loaded on GPU 1")
        return
    except Exception as e:
        logger.warning(f"CodeFormer unavailable: {e}")

    # Try GFPGAN
    try:
        from gfpgan import GFPGANer

        # Try multiple weight paths
        weight_paths = [
            os.path.expanduser('~/SadTalker/gfpgan/weights/GFPGANv1.4.pth'),
            os.path.expanduser('~/gfpgan/weights/GFPGANv1.4.pth'),
        ]
        model_path = None
        for p in weight_paths:
            if os.path.exists(p):
                model_path = p
                break
        if model_path is None:
            # Let it download automatically
            model_path = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth'

        _enhancer = GFPGANer(
            model_path=model_path,
            upscale=1,  # No upscale — just enhance quality at same resolution
            arch='clean',
            channel_multiplier=2,
            bg_upsampler=None,
            device='cuda:1'
        )
        _enhancer_type = 'gfpgan'
        logger.info("GFPGAN loaded on GPU 1")
        return
    except Exception as e:
        logger.warning(f"GFPGAN unavailable: {e}")

    _enhancer_type = None
    logger.warning("No face enhancer available — running without enhancement")


def get_enhancer():
    """Get or initialize the face enhancer singleton."""
    global _enhancer, _enhancer_type
    with _enhancer_lock:
        if _enhancer is None and _enhancer_type is None:
            _load_enhancer()
    return _enhancer, _enhancer_type


def enhance_frames_batch(frames, face_coords, batch_size=16):
    """
    Enhance face region in a batch of frames using GFPGAN or CodeFormer.

    This is the #1 visual quality upgrade: fixes Wav2Lip's blurry 96x96 upscaled mouth.

    Args:
        frames: list of BGR numpy arrays
        face_coords: (y1, y2, x1, x2) face region coordinates
        batch_size: frames to process at once

    Returns:
        list of enhanced BGR numpy arrays
    """
    enhancer, etype = get_enhancer()
    if enhancer is None:
        return frames  # No enhancer available — return as-is

    y1, y2, x1, x2 = face_coords
    enhanced_frames = []

    if etype == 'gfpgan':
        for i, frame in enumerate(frames):
            try:
                # Crop the face region with slight padding for better context
                pad = 20
                py1 = max(0, y1 - pad)
                py2 = min(frame.shape[0], y2 + pad)
                px1 = max(0, x1 - pad)
                px2 = min(frame.shape[1], x2 + pad)

                face_crop = frame[py1:py2, px1:px2].copy()

                # Run GFPGAN on face crop
                _, _, restored = enhancer.enhance(
                    face_crop,
                    has_aligned=False,
                    only_center_face=True,
                    paste_back=True
                )

                if restored is not None and restored.shape == face_crop.shape:
                    # Blend restored region back (95% enhanced, 5% original for edge smoothing)
                    result = frame.copy()
                    result[py1:py2, px1:px2] = (
                        restored * 0.95 + face_crop * 0.05
                    ).astype(np.uint8)
                    enhanced_frames.append(result)
                else:
                    enhanced_frames.append(frame)

            except Exception as e:
                if i == 0:
                    logger.warning(f"GFPGAN enhance error: {e}")
                enhanced_frames.append(frame)

    elif etype == 'codeformer':
        import torch
        from basicsr.utils import img2tensor, tensor2img
        from torchvision.transforms.functional import normalize as tv_normalize
        try:
            from facelib.utils.face_restoration_helper import FaceRestoreHelper
            helper = FaceRestoreHelper(
                upscale_factor=1, face_size=512, crop_ratio=(1,1),
                det_model='retinaface_resnet50', save_ext='png',
                use_parse=True, device='cuda:1'
            )
            for i, frame in enumerate(frames):
                try:
                    helper.clean_all()
                    helper.read_image(frame)
                    helper.get_face_landmarks_5(only_center_face=True, resize=640)
                    helper.align_warp_face()
                    if not helper.cropped_faces:
                        enhanced_frames.append(frame)
                        continue
                    face_t = img2tensor(helper.cropped_faces[0]/255., bgr2rgb=True, float32=True)
                    tv_normalize(face_t, (0.5,0.5,0.5), (0.5,0.5,0.5), inplace=True)
                    face_t = face_t.unsqueeze(0).to('cuda:1')
                    with torch.no_grad():
                        out = enhancer(face_t, w=0.7, adain=True)[0]
                    restored = tensor2img(out, rgb2bgr=True, min_max=(-1,1)).astype('uint8')
                    helper.add_restored_face(restored)
                    helper.paste_faces_to_input_image()
                    result = helper.output
                    enhanced_frames.append(result if result is not None and result.shape==frame.shape else frame)
                except Exception as e:
                    if i==0: logger.warning(f"CodeFormer frame error: {e}")
                    enhanced_frames.append(frame)
        except Exception as e:
            logger.warning(f"CodeFormer batch setup error: {e}")
            enhanced_frames = list(frames)
    else:
        # Unknown enhancer type — return as-is
        enhanced_frames = list(frames)

    return enhanced_frames



def enhance_frames_fast(frames, face_coords):
    """
    Fast per-frame enhancement using GFPGAN.
    Optimized: only enhance mouth/lower-face subregion (faster than full face).
    """
    enhancer, etype = get_enhancer()
    if enhancer is None:
        return frames

    y1, y2, x1, x2 = face_coords
    # Only enhance lower 60% of face (mouth region) — faster, targets the Wav2Lip artifact
    mouth_y1 = y1 + int((y2 - y1) * 0.35)

    enhanced = []
    for frame in frames:
        try:
            # Extract slightly-expanded mouth region
            pad = 15
            ry1 = max(0, mouth_y1 - pad)
            ry2 = min(frame.shape[0], y2 + pad)
            rx1 = max(0, x1 - pad)
            rx2 = min(frame.shape[1], x2 + pad)

            region = frame[ry1:ry2, rx1:rx2].copy()

            if etype == 'gfpgan':
                _, _, restored = enhancer.enhance(
                    region, has_aligned=False, only_center_face=True, paste_back=True
                )
                if restored is not None and restored.shape == region.shape:
                    result = frame.copy()
                    result[ry1:ry2, rx1:rx2] = restored
                    enhanced.append(result)
                    continue
        except Exception:
            pass
        enhanced.append(frame)

    return enhanced


def sharpen_mouth_region(frames, face_coords):
    import cv2, numpy as np
    y1, y2, x1, x2 = face_coords
    mouth_y1 = y1 + int((y2 - y1) * 0.45)
    kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]], dtype=np.float32)
    out = []
    for frame in frames:
        try:
            region = frame[mouth_y1:y2, x1:x2].copy()
            smooth = cv2.bilateralFilter(region, d=5, sigmaColor=40, sigmaSpace=5)
            sharpened = cv2.filter2D(smooth, -1, kernel)
            blended = cv2.addWeighted(sharpened, 0.65, smooth, 0.35, 0)
            result = frame.copy()
            result[mouth_y1:y2, x1:x2] = blended
            out.append(result)
        except Exception:
            out.append(frame)
    return out
