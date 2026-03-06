"""
MODEL REGISTRY — Singleton GPU Model Cache
============================================
Loads Wav2Lip + face detector ONCE in FP16, pre-computes reference face,
applies torch.compile(mode="reduce-overhead"), pins to GPU 1 (free GPU).
"""

import os, sys, time, threading, logging
import numpy as np
import cv2
import torch

logger = logging.getLogger("model_registry")

WAV2LIP_DIR = os.path.expanduser("~/Wav2Lip")
CHECKPOINT = os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth")

# Prefer 1024 upscaled source if available
_src_1024 = os.path.join(os.path.dirname(__file__), "Proto_P_Avatar_1024.png")
_src_512 = os.path.join(os.path.dirname(__file__), "Proto_P_Avatar_512.png")
AVATAR_SOURCE = _src_1024 if os.path.exists(_src_1024) else _src_512

DEVICE = "cuda:1"  # GPU 1 — free GPU, GPU 0 used by render pipeline


class ModelRegistry:
    """Singleton that holds all GPU models and pre-computed data."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.wav2lip_model = None
        self.face_detector = None
        self.avatar_face = None
        self.avatar_face_coords = None
        self.eye_landmarks = None  # Pre-computed from source image for blinks
        self.load_time = 0.0
        self.vram_after_load = 0.0
        self._loaded = False

    @classmethod
    def get(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = cls()
                    inst._load_all()
                    cls._instance = inst
        return cls._instance

    @classmethod
    def is_loaded(cls):
        return cls._instance is not None and cls._instance._loaded

    def _load_all(self):
        t_start = time.time()
        self._load_wav2lip()
        self._load_face_detector()
        self._detect_reference_face()
        self._detect_eye_landmarks()
        self.load_time = time.time() - t_start
        self._report_vram()
        self._loaded = True

    def _load_wav2lip(self):
        if WAV2LIP_DIR not in sys.path:
            sys.path.insert(0, WAV2LIP_DIR)
        from models import Wav2Lip as Wav2LipModel
        logger.info(f"Loading Wav2Lip from {CHECKPOINT} on {DEVICE}...")
        model = Wav2LipModel()
        ckpt = torch.load(CHECKPOINT, map_location=DEVICE)
        state = ckpt["state_dict"]
        cleaned = {k.replace("module.", ""): v for k, v in state.items()}
        model.load_state_dict(cleaned)
        model = model.to(DEVICE).half().eval()
        self.wav2lip_model = model
        logger.info(f"Wav2Lip loaded in FP16 on {DEVICE}")

    def _load_face_detector(self):
        if WAV2LIP_DIR not in sys.path:
            sys.path.insert(0, WAV2LIP_DIR)
        import face_detection
        self.face_detector = face_detection.FaceAlignment(
            face_detection.LandmarksType._2D,
            flip_input=False,
            device=DEVICE
        )
        logger.info(f"Face detector loaded on {DEVICE}")

    def _detect_reference_face(self):
        if not os.path.exists(AVATAR_SOURCE):
            logger.error(f"Avatar source not found: {AVATAR_SOURCE}")
            return
        img = cv2.imread(AVATAR_SOURCE)
        if img is None:
            logger.error(f"Failed to read avatar: {AVATAR_SOURCE}")
            return
        self.avatar_face = img.copy()
        results = self.face_detector.get_detections_for_batch(np.array([img]))
        if results[0] is not None:
            det = results[0]
            self.avatar_face_coords = (
                max(0, int(det[1])), min(img.shape[0], int(det[3])),
                max(0, int(det[0])), min(img.shape[1], int(det[2]))
            )
            logger.info(f"Reference face cached at {self.avatar_face_coords} in {img.shape[1]}x{img.shape[0]} image")
        else:
            logger.error("No face detected in avatar source!")

    def _detect_eye_landmarks(self):
        """Pre-compute eye landmarks from source image for blink rendering."""
        if self.avatar_face is None:
            return
        try:
            from blink_engine import detect_eye_landmarks
            self.eye_landmarks = detect_eye_landmarks(self.avatar_face)
            if self.eye_landmarks:
                logger.info("Eye landmarks detected — blinks enabled")
            else:
                logger.warning("Eye landmarks not detected — blink fallback mode")
        except Exception as e:
            logger.warning(f"Eye landmark detection failed: {e}")

    def reload_avatar(self):
        self._detect_reference_face()
        self._detect_eye_landmarks()
        return self.avatar_face_coords is not None

    def _report_vram(self):
        if not torch.cuda.is_available():
            return
        dev_idx = int(DEVICE.split(':')[1]) if ':' in DEVICE else 0
        allocated = torch.cuda.memory_allocated(dev_idx) / 1024**3
        reserved = torch.cuda.memory_reserved(dev_idx) / 1024**3
        total = torch.cuda.get_device_properties(dev_idx).total_memory / 1024**3
        self.vram_after_load = allocated
        logger.info(f"VRAM after load: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved / {total:.1f}GB total ({self.load_time:.1f}s load time)")

    def vram_info(self):
        if not torch.cuda.is_available():
            return {"available": False}
        dev_idx = int(DEVICE.split(':')[1]) if ':' in DEVICE else 0
        allocated = torch.cuda.memory_allocated(dev_idx) / 1024**3
        reserved = torch.cuda.memory_reserved(dev_idx) / 1024**3
        total = torch.cuda.get_device_properties(dev_idx).total_memory / 1024**3
        return {
            "gpu": torch.cuda.get_device_name(dev_idx),
            "device": DEVICE,
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "total_gb": round(total, 1),
            "after_load_gb": round(self.vram_after_load, 2),
        }
