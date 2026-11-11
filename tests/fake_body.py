"""Make fake MediaPipe landmarks so gestures can be tested without a camera.

Body: torso length = 0.25 * scale, shoulder width = 0.15 * scale.
"""
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
        F.L_EAR: (cx + 0.035 * scale, top - 0.01 * scale),
        F.R_EAR: (cx - 0.035 * scale, top - 0.01 * scale),
        F.L_SHOULDER: (cx + sw / 2, top + 0.08 * scale),
        F.R_SHOULDER: (cx - sw / 2, top + 0.08 * scale),
        F.L_HIP: (cx + sw / 3, top + 0.33 * scale),
        F.R_HIP: (cx - sw / 3, top + 0.33 * scale),
        F.L_KNEE: (cx + sw / 3, top + 0.50 * scale),
        F.R_KNEE: (cx - sw / 3, top + 0.50 * scale),
        F.L_ANKLE: (cx + sw / 3, top + 0.67 * scale),
        F.R_ANKLE: (cx - sw / 3, top + 0.67 * scale),
        F.L_ELBOW: (cx + sw * 0.6, top + 0.20 * scale),
        F.R_ELBOW: (cx - sw * 0.6, top + 0.20 * scale),
        F.L_WRIST: (cx + sw * 0.7, top + 0.33 * scale),
        F.R_WRIST: (cx - sw * 0.7, top + 0.33 * scale),
    }
    for i, (x, y) in pts.items():
        lm[i, :2] = (x, y)
    return lm


def torso(lm):
    return F.torso_length(lm)


def lift_knee(lm, side, amount):
    """Raise the left (side=+1) or right (side=-1) knee by `amount` torso lengths."""
    out = lm.copy()
    idx = F.L_KNEE if side > 0 else F.R_KNEE
    out[idx, 1] -= amount * torso(lm)
    return out


def lean_body(lm, amount):
    """Shift the shoulders and head sideways by `amount` shoulder widths."""
    out = lm.copy()
    dx = amount * F.shoulder_width(lm)
    for i in (F.NOSE, F.L_EAR, F.R_EAR, F.L_SHOULDER, F.R_SHOULDER):
        out[i, 0] += dx
    return out


def squat(lm, amount):
    """Lower everything above the knees by `amount` torso lengths."""
    out = lm.copy()
    dy = amount * torso(lm)
    for i in (F.NOSE, F.L_EAR, F.R_EAR, F.L_SHOULDER, F.R_SHOULDER,
              F.L_HIP, F.R_HIP, F.L_WRIST, F.R_WRIST):
        out[i, 1] += dy
    return out


def raise_arms(lm, above_nose):
    """Put both wrists `above_nose` torso lengths above the nose."""
    out = lm.copy()
    y = lm[F.NOSE, 1] - above_nose * torso(lm)
    out[F.L_WRIST, 1] = out[F.R_WRIST, 1] = y
    return out


def hands_on_hips(lm):
    out = lm.copy()
    out[F.L_WRIST, :2] = lm[F.L_HIP, :2] + (0.02, 0.0)
    out[F.R_WRIST, :2] = lm[F.R_HIP, :2] - (0.02, 0.0)
    sw = F.shoulder_width(lm)
    out[F.L_ELBOW, 0] = lm[F.L_SHOULDER, 0] + 0.5 * sw
    out[F.R_ELBOW, 0] = lm[F.R_SHOULDER, 0] - 0.5 * sw
    return out


def turn_head(lm, yaw=0.0, pitch=0.0):
    """Move the nose by yaw / pitch ear distances (like turning the head)."""
    out = lm.copy()
    ear = float(np.linalg.norm(lm[F.L_EAR, :2] - lm[F.R_EAR, :2]))
    out[F.NOSE, 0] += yaw * ear
    out[F.NOSE, 1] += pitch * ear
    return out


def noisy(lm, sigma, rng):
    out = lm.copy()
    out[:, :2] += rng.normal(0, sigma, size=(33, 2)).astype(np.float32)
    return out
