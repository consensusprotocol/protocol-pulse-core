"""
Generate placeholder viseme + blink frames for testing the JS avatar pipeline.
Uses OpenCV/Pillow overlays on the base avatar image.
Run: python3 generate_placeholder_frames.py
"""
import os
import cv2
import numpy as np

AVATAR_SOURCE = os.path.expanduser("~/protocol_pulse/oracle/Proto_P_Avatar_1024.png")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "assets", "frames")

VISEME_NAMES = {
    0: "SIL", 1: "PP", 2: "FF", 3: "TH", 4: "DD", 5: "KK",
    6: "CH", 7: "SS", 8: "HH", 9: "RR", 10: "AA", 11: "EE",
    12: "IH", 13: "OH", 14: "OU", 15: "AW", 16: "WIDE-E", 17: "SMILE",
}

# Mouth region approximate coords (relative to 1024px image)
MOUTH_CENTER_X = 512
MOUTH_CENTER_Y = 680
MOUTH_RADIUS_X = 80
MOUTH_RADIUS_Y = 50

# Colors for each viseme category (BGR)
VISEME_COLORS = {
    0: (40, 40, 40),       # Silence — dark
    1: (60, 40, 100),      # Bilabial — purple
    2: (60, 80, 120),      # Labiodental — blue
    3: (80, 80, 80),       # Dental — gray
    4: (80, 100, 60),      # Alveolar — green
    5: (60, 120, 80),      # Velar — teal
    6: (100, 80, 60),      # Palato — brown
    7: (120, 100, 40),     # Sibilant — gold
    8: (80, 60, 100),      # Nasal — purple
    9: (60, 60, 140),      # Rhotic — red
    10: (40, 40, 200),     # Open vowel — bright red
    11: (40, 120, 200),    # Mid-front — orange
    12: (40, 160, 180),    # High-front — yellow
    13: (120, 80, 40),     # Mid-back — teal
    14: (140, 60, 60),     # High-back — blue
    15: (60, 100, 180),    # Half-open — warm
    16: (40, 180, 200),    # Wide-E — bright
    17: (100, 100, 100),   # Smile — neutral
}

# Mouth opening sizes (width_pct, height_pct) per viseme
MOUTH_SHAPES = {
    0: (0.3, 0.1),    # Closed
    1: (0.2, 0.05),   # Bilabial — lips together
    2: (0.4, 0.2),    # Labiodental
    3: (0.5, 0.2),    # Dental
    4: (0.5, 0.3),    # Alveolar
    5: (0.4, 0.35),   # Velar
    6: (0.6, 0.4),    # Palato
    7: (0.4, 0.25),   # Sibilant
    8: (0.35, 0.3),   # Nasal
    9: (0.5, 0.4),    # Rhotic
    10: (0.9, 0.8),   # Open vowel — wide open
    11: (0.8, 0.6),   # Mid-front
    12: (0.6, 0.4),   # High-front
    13: (0.5, 0.7),   # Mid-back rounded
    14: (0.4, 0.6),   # High-back rounded
    15: (0.7, 0.5),   # Half-open
    16: (0.9, 0.5),   # Wide-E
    17: (0.5, 0.2),   # Smile
}


def generate_viseme_frame(base_img, viseme_id):
    """Overlay a colored mouth shape on the base image for a given viseme."""
    frame = base_img.copy()
    h, w = frame.shape[:2]

    color = VISEME_COLORS.get(viseme_id, (80, 80, 80))
    shape = MOUTH_SHAPES.get(viseme_id, (0.5, 0.3))

    rx = int(MOUTH_RADIUS_X * shape[0])
    ry = int(MOUTH_RADIUS_Y * shape[1])

    # Draw semi-transparent ellipse
    overlay = frame.copy()
    cv2.ellipse(overlay, (MOUTH_CENTER_X, MOUTH_CENTER_Y), (rx, ry), 0, 0, 360, color, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Border
    cv2.ellipse(frame, (MOUTH_CENTER_X, MOUTH_CENTER_Y), (rx, ry), 0, 0, 360, (200, 200, 200), 1)

    # Label
    label = f"V{viseme_id}: {VISEME_NAMES.get(viseme_id, '?')}"
    cv2.putText(frame, label, (MOUTH_CENTER_X - 60, MOUTH_CENTER_Y + ry + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    return frame


def generate_blink_frame(base_img, state):
    """Generate a blink overlay frame."""
    frame = base_img.copy()
    h, w = frame.shape[:2]

    # Eye positions (approximate for 1024px)
    left_eye = (380, 480)
    right_eye = (644, 480)
    eye_w, eye_h = 50, 20

    if state == 'open':
        # Just the base — eyes are open
        pass
    elif state == 'half':
        for (ex, ey) in [left_eye, right_eye]:
            overlay = frame.copy()
            cv2.ellipse(overlay, (ex, ey - 5), (eye_w, eye_h // 2), 0, 0, 360, (30, 30, 30), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    elif state == 'closed':
        for (ex, ey) in [left_eye, right_eye]:
            cv2.ellipse(frame, (ex, ey), (eye_w, eye_h), 0, 0, 360, (30, 30, 30), -1)

    # Label
    cv2.putText(frame, f"BLINK: {state}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    return frame


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(AVATAR_SOURCE):
        print(f"Avatar source not found: {AVATAR_SOURCE}")
        # Create a blank 1024x1024 placeholder
        base = np.zeros((1024, 1024, 3), dtype=np.uint8)
        base[:] = (20, 20, 20)
        cv2.circle(base, (512, 420), 280, (40, 40, 40), -1)
        cv2.circle(base, (512, 420), 280, (80, 0, 0), 2)
        print("Using blank placeholder base")
    else:
        base = cv2.imread(AVATAR_SOURCE)
        print(f"Loaded avatar: {base.shape[1]}x{base.shape[0]}")

    # Generate base frame
    cv2.imwrite(os.path.join(OUTPUT_DIR, "base.png"), base)
    print("Generated: base.png")

    # Generate 18 viseme frames
    for i in range(18):
        frame = generate_viseme_frame(base, i)
        path = os.path.join(OUTPUT_DIR, f"viseme_{i}.png")
        cv2.imwrite(path, frame)
        print(f"Generated: viseme_{i}.png ({VISEME_NAMES.get(i, '?')})")

    # Generate 3 blink frames
    for state in ['open', 'half', 'closed']:
        frame = generate_blink_frame(base, state)
        path = os.path.join(OUTPUT_DIR, f"blink_{state}.png")
        cv2.imwrite(path, frame)
        print(f"Generated: blink_{state}.png")

    print(f"\nDone! {18 + 3 + 1} frames saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
