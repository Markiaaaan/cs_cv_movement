"""Preview window: skeleton, state, FPS, model time and the keys held now."""
import cv2

# Pairs of pose landmark indices to draw as bones (upper body + legs).
BONES = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28),
]
WINDOW = "CS 1.6 body input"


def draw_skeleton(frame, lm, min_vis):
    h, w = frame.shape[:2]
    for a, b in BONES:
        if lm[a, 3] >= min_vis and lm[b, 3] >= min_vis:
            pa = (int(lm[a, 0] * w), int(lm[a, 1] * h))
            pb = (int(lm[b, 0] * w), int(lm[b, 1] * h))
            cv2.line(frame, pa, pb, (0, 255, 0), 2)
    for x, y, _, v in lm:
        if v >= min_vis:
            cv2.circle(frame, (int(x * w), int(y * h)), 3, (0, 200, 255), -1)


def draw_text(frame, lines):
    y = 22
    for text, color in lines:
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        y += 24


def show(frame):
    cv2.imshow(WINDOW, frame)
    try:  # keep the preview above the game window (Windows builds of OpenCV)
        cv2.setWindowProperty(WINDOW, cv2.WND_PROP_TOPMOST, 1)
    except cv2.error:
        pass
