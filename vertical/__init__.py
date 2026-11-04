"""vertical — Standalone vertical (9:16) reframing module for Protocol Pulse.

Replaces render_v*_vertical.py with a shotmap-driven, per-shot composition engine.
GPU 0 only. Debug drawing isolated in debug.py.
"""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

VERSION = "vertical_v1"
BASE = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(BASE, "work")
VERT_W, VERT_H = 1080, 1920
FPS = 24
ACCENT_COLOR = (247, 147, 26)  # Bitcoin orange #F7931A
DIVIDER_H = 4
GUTTER_H = 12
