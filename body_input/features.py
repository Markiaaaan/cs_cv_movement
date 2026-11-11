"""Turn raw landmarks into body-relative numbers, plus small reusable helpers.

Landmarks are a numpy array of shape (33, 4): x, y, z, visibility, with x and y
in 0..1 image units (y grows downward). Dividing distances by shoulder width
makes them the same whether you stand 1.5 m or 3 m from the camera.
"""
import math

import numpy as np

# MediaPipe Pose landmark indices we use.
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
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
