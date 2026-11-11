"""Turn raw landmarks into body-relative numbers, plus small reusable helpers.

Landmarks are a numpy array of shape (33, 4): x, y, z, visibility, with x and y
in 0..1 image units (y grows downward). Dividing distances by shoulder width
makes them the same whether you stand 1.5 m or 3 m from the camera.
"""
import math

import numpy as np

# MediaPipe Pose landmark indices we use.
NOSE = 0
L_EAR, R_EAR = 7, 8
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28


def visible(lm, idx, min_vis):
    return lm[idx, 3] >= min_vis


def midpoint(lm, a, b):
    return (lm[a, :2] + lm[b, :2]) / 2.0


def shoulder_width(lm):
    return float(np.linalg.norm(lm[L_SHOULDER, :2] - lm[R_SHOULDER, :2]))


def torso_length(lm):
    """Shoulder midpoint to hip midpoint."""
    return float(np.linalg.norm(midpoint(lm, L_SHOULDER, R_SHOULDER) - midpoint(lm, L_HIP, R_HIP)))


# --- Per-frame body measures ------------------------------------------------
# None of these use MediaPipe's left/right labels for direction, because on a
# mirrored image those labels are easy to get backwards. They use image
# positions or symmetric pairs instead.

def all_visible(lm, idxs, min_vis):
    return all(lm[i, 3] >= min_vis for i in idxs)


def knee_diff(lm):
    """Height difference between the two knees, in torso lengths.

    Lifting one knee makes this swing to + or -. A squat moves both knees the
    same way, so it barely changes this number (that is why we use it).
    """
    return float((lm[R_KNEE, 1] - lm[L_KNEE, 1]) / torso_length(lm))


def lean(lm):
    """Sideways torso lean: shoulder centre vs hip centre, in shoulder widths.

    + means leaning toward image right, which is your right on a mirrored image.
    """
    sx = midpoint(lm, L_SHOULDER, R_SHOULDER)[0]
    hx = midpoint(lm, L_HIP, R_HIP)[0]
    return float((sx - hx) / shoulder_width(lm))


def hip_drop(lm, rest_hip_y, rest_torso):
    """How far the hips are below their calibrated height, in torso lengths."""
    return float((midpoint(lm, L_HIP, R_HIP)[1] - rest_hip_y) / rest_torso)


def arms_up(lm):
    """How far the LOWER wrist is above the nose, in torso lengths (+ = above)."""
    lowest_wrist = max(lm[L_WRIST, 1], lm[R_WRIST, 1])
    return float((lm[NOSE, 1] - lowest_wrist) / torso_length(lm))


def hands_on_hips(lm, wrist_max):
    """Elbow span in shoulder widths when both wrists are near the hips, else 0.

    Relaxed hanging arms also put the wrists near the hips, so the elbows
    sticking out sideways is what really tells "hands on hips" apart.
    """
    sw = shoulder_width(lm)
    hips = lm[[L_HIP, R_HIP], :2]
    for w in (L_WRIST, R_WRIST):
        if np.min(np.linalg.norm(hips - lm[w, :2], axis=1)) / sw > wrist_max:
            return 0.0
    return float(abs(lm[L_ELBOW, 0] - lm[R_ELBOW, 0]) / sw)


def head_yaw(lm):
    """Nose left/right of the ear centre, in ear distances (+ = turned to image right)."""
    ear_mid = midpoint(lm, L_EAR, R_EAR)
    ear_dist = float(np.linalg.norm(lm[L_EAR, :2] - lm[R_EAR, :2]))
    return float((lm[NOSE, 0] - ear_mid[0]) / ear_dist)


def head_pitch(lm):
    """Nose below the ear line, in ear distances (+ = looking down)."""
    ear_mid = midpoint(lm, L_EAR, R_EAR)
    ear_dist = float(np.linalg.norm(lm[L_EAR, :2] - lm[R_EAR, :2]))
    return float((lm[NOSE, 1] - ear_mid[1]) / ear_dist)


def rest_values(lm):
    """Neutral-pose values that the gestures measure against."""
    return {
        "shoulder_width": shoulder_width(lm),
        "torso_length": torso_length(lm),
        "hip_y": float(midpoint(lm, L_HIP, R_HIP)[1]),
        "shoulder_mid": tuple(float(v) for v in midpoint(lm, L_SHOULDER, R_SHOULDER)),
        "knee_diff": knee_diff(lm),
        "lean": lean(lm),
        "head_yaw": head_yaw(lm),
        "head_pitch": head_pitch(lm),
    }


class OneEuroFilter:
    """Adaptive low-pass filter: smooth when still, responsive when moving.

    Casiez et al., 2012. Works on floats or numpy arrays.
    """

    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self._x = None
        self._dx = 0.0
        self._t = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def reset(self):
        self._x, self._dx, self._t = None, 0.0, None

    def __call__(self, x, t):
        if self._x is None or t <= self._t:
            self._x, self._t = x, t
            return x
        dt = t - self._t
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * np.abs(self._dx)
        a = self._alpha(cutoff, dt)
        self._x = a * x + (1 - a) * self._x
        self._t = t
        return self._x


class Hysteresis:
    """A boolean with two thresholds, so a value near the edge does not flicker.

    Turns on when value >= on_at, turns off only when value <= off_at.
    """

    def __init__(self, on_at, off_at):
        if off_at > on_at:
            raise ValueError("off_at must be <= on_at")
        self.on_at, self.off_at = on_at, off_at
        self.state = False

    def update(self, value):
        if not self.state and value >= self.on_at:
            self.state = True
        elif self.state and value <= self.off_at:
            self.state = False
        return self.state

    def reset(self):
        self.state = False
