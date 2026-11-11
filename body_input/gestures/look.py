"""Camera turning by head turn, used like a joystick.

Turning the head past a dead zone turns the camera at a speed that grows with
how far you turn. Inside the dead zone nothing moves, so there is no drift
while you stand still. Compared with the other options:
- shoulder twist: hard to see from the front with one camera (it is depth);
- hand touchpad: precise, but it ties up a hand that we need for shooting;
- head turn: cheap (nose + ears), keeps both hands free, small turns only.
"""
import math

from ..features import OneEuroFilter


class HeadLook:
    def __init__(self, yaw_dead, pitch_dead, yaw_speed, pitch_speed, curve,
                 max_dt, invert_pitch=False, filter_args=(1.0, 0.05, 1.0)):
        self.yaw_dead, self.pitch_dead = yaw_dead, pitch_dead
        self.yaw_speed, self.pitch_speed = yaw_speed, pitch_speed
        self.curve, self.max_dt = curve, max_dt
        self.pitch_sign = -1.0 if invert_pitch else 1.0
        self._fy, self._fp = OneEuroFilter(*filter_args), OneEuroFilter(*filter_args)
        self._last_t = None

    def _axis(self, v, dead, speed):
        excess = abs(v) - dead
        if excess <= 0:
            return 0.0
        return math.copysign(speed * excess ** self.curve, v)

    def update(self, yaw, pitch, t):
        """yaw/pitch are offsets from rest (or None). Returns mouse (dx, dy)."""
        if yaw is None or pitch is None:
            self._fy.reset()
            self._fp.reset()
            self._last_t = None
            return 0.0, 0.0
        y, p = self._fy(yaw, t), self._fp(pitch, t)
        dt = 0.0 if self._last_t is None else min(t - self._last_t, self.max_dt)
        self._last_t = t
        dx = self._axis(y, self.yaw_dead, self.yaw_speed) * dt
        dy = self._axis(p, self.pitch_dead, self.pitch_speed) * dt * self.pitch_sign
        return dx, dy
