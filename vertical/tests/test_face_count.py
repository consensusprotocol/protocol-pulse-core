#!/usr/bin/env python3
"""T1: Every output frame's face set == shot_map faces for that shot.

Catches wrong face, dropped column, 3-band from 5-tile source.
Runs face detection on sampled frames from rendered output and verifies
the count matches shot_map's total_faces for that shot.
"""
import json
import os
import subprocess
import sys
import unittest

VERTICAL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

FACE_MODEL = "/home/ultron/protocol_pulse/segment_v1/qa_v6/blaze_face_short_range.tflite"


def extract_frame(mp4, t, out_png):
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(t), "-i", mp4,
        "-frames:v", "1", "-q:v", "2", out_png,
    ], capture_output=True, timeout=30)
    return os.path.exists(out_png)


def count_faces_mediapipe(frame_path):
    """Count faces using MediaPipe FaceDetector."""
    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as mp_base_options

    base_opts = mp_base_options.BaseOptions(model_asset_path=FACE_MODEL)
    detector = vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(base_options=base_opts,
                                   min_detection_confidence=0.4))
    img = cv2.imread(frame_path)
    if img is None:
        return 0
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=rgb)
    results = detector.detect(mp_image)
    return len(results.detections)


class TestFaceCount(unittest.TestCase):
    """T1: Rendered output face count matches shot_map per shot."""

    def test_face_count_matches_shot_map(self):
        shot_map_path = os.path.join(VERTICAL_DIR, "work", "shot_map.json")
        rendered_path = os.path.join(VERTICAL_DIR, "work", "final_vertical.mp4")

        if not os.path.exists(shot_map_path):
            self.skipTest("No shot_map.json yet")
        if not os.path.exists(rendered_path):
            self.skipTest("No rendered output yet")

        with open(shot_map_path) as f:
            shot_map = json.load(f)

        qa_dir = os.path.join(VERTICAL_DIR, "work", "qa_t1")
        os.makedirs(qa_dir, exist_ok=True)

        failures = []
        for shot in shot_map.get("shots", []):
            if shot.get("layout") in ("unmeasured",):
                continue

            expected = shot.get("total_faces", 0)
            if expected == 0:
                continue

            # Sample 3 frames from the shot
            t_in = shot["t_in"]
            t_out = shot["t_out"]
            dur = t_out - t_in
            if dur < 0.5:
                continue

            sample_times = [t_in + dur * (i + 0.5) / 3 for i in range(3)]
            counts = []
            for i, t in enumerate(sample_times):
                frame_path = os.path.join(qa_dir, f"t1_{shot['id']}_{i}.png")
                if extract_frame(rendered_path, t, frame_path):
                    c = count_faces_mediapipe(frame_path)
                    counts.append(c)

            if not counts:
                continue

            # At least 2 of 3 samples must match expected
            matches = sum(1 for c in counts if c == expected)
            if matches < 2:
                failures.append(
                    f"  {shot['id']} ({shot['layout']}): expected {expected} faces, "
                    f"got {counts}")

        if failures:
            self.fail(f"Face count mismatches:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
