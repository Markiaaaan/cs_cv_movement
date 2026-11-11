"""Make fake MediaPipe pose landmarks so gestures can be tested without a camera."""
import numpy as np

from body_input import features as F


def standing(cx=0.5, scale=1.0, vis=0.99):
    """A person standing straight, facing the camera. scale ~ 1/distance."""
    lm = np.zeros((33, 4), dtype=np.float32)
    lm[:, 3] = vis
    sw = 0.15 * scale  # shoulder width in image units
    top = 0.5 - 0.35 * scale
    pts = {
        F.NOSE: (cx, top),
        F.L_SHOULDER: (cx + sw / 2, top + 0.08 * scale),
        F.R_SHOULDER: (cx - sw / 2, top + 0.08 * scale),
        F.L_HIP: (cx + sw / 3, top + 0.33 * scale),
        F.R_HIP: (cx - sw / 3, top + 0.33 * scale),
        F.L_KNEE: (cx + sw / 3, top + 0.50 * scale),
        F.R_KNEE: (cx - sw / 3, top + 0.50 * scale),
        F.L_ANKLE: (cx + sw / 3, top + 0.67 * scale),
        F.R_ANKLE: (cx - sw / 3, top + 0.67 * scale),
        F.L_WRIST: (cx + sw * 0.7, top + 0.33 * scale),
        F.R_WRIST: (cx - sw * 0.7, top + 0.33 * scale),
    }
    for i, (x, y) in pts.items():
        lm[i, :2] = (x, y)
    return lm


def noisy(lm, sigma, rng):
    out = lm.copy()
    out[:, :2] += rng.normal(0, sigma, size=(33, 2)).astype(np.float32)
    return out
