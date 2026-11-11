"""Whole-body gestures. Each class gets one number per frame and returns a state.

No camera, OpenCV or input code here, so tests can feed fake numbers.
A value of None means "not visible this frame".
"""
from collections import deque
from dataclasses import dataclass

from ..features import Hysteresis


@dataclass
class WalkState:
    walking: bool = False
    slow: bool = False   # stepping slowly -> walk quietly (Shift)


class WalkInPlace:
    """Stepping in place = alternating knee lifts.

    Fed the knee height difference (minus its calibrated rest value). A lift of
    either knee starts walking at once (fast start). Walking stops
    `stop_s` after the last moment any knee was up (fast stop). The gap
    between steps decides walk vs run.
    """

    def __init__(self, on, off, stop_s, slow_interval_s):
        self._up = {+1: Hysteresis(on, off), -1: Hysteresis(on, off)}
        self.stop_s, self.slow_interval_s = stop_s, slow_interval_s
        self._last_up_t = None
        self._steps = deque(maxlen=3)

    def update(self, diff, t):
        for side, h in self._up.items():
            was = h.state
            now = h.update(side * diff) if diff is not None else h.update(-1e9)
            if now and not was:
                self._steps.append(t)
            if now:
                self._last_up_t = t
        walking = self._last_up_t is not None and t - self._last_up_t <= self.stop_s
        if not walking:
            self._steps.clear()
        slow = len(self._steps) >= 2 and self._steps[-1] - self._steps[-2] > self.slow_interval_s
        return WalkState(walking, walking and slow)


class Lean:
    """Sideways lean -> -1 (left), 0, +1 (right)."""

    def __init__(self, on, off):
        self._right, self._left = Hysteresis(on, off), Hysteresis(on, off)

    def update(self, value):
        if value is None:
            self._right.reset()
            self._left.reset()
            return 0
        r, l = self._right.update(value), self._left.update(-value)
        return 1 if r and not l else -1 if l and not r else 0


class Level:
    """A held pose with hysteresis (crouch, hands on hips). None -> off."""

    def __init__(self, on, off, invert=False):
        # invert: the pose is ON when the value is SMALL (e.g. distance).
        self.invert = invert
        self._h = Hysteresis(-on, -off) if invert else Hysteresis(on, off)

    def update(self, value):
        if value is None:
            self._h.reset()
            return False
        return self._h.update(-value if self.invert else value)


class EdgeTrigger:
    """Fires once when a value crosses `on`; re-arms below `off`; has a cooldown."""

    def __init__(self, on, off, cooldown_s):
        self._h = Hysteresis(on, off)
        self.cooldown_s = cooldown_s
        self._last = None

    def update(self, value, t):
        was = self._h.state
        now = self._h.update(value if value is not None else -1e9)
        if now and not was and (self._last is None or t - self._last >= self.cooldown_s):
            self._last = t
            return True
        return False
