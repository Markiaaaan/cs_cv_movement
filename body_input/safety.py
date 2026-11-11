"""Safety pieces: person-lost watchdog, calibration, and global hotkeys.

PresenceWatchdog and Calibrator are fed one frame at a time and touch no
camera or input code, so they are unit-tested with fake landmarks.
"""
import sys
import threading
import time

import numpy as np

from . import features as F


class PresenceWatchdog:
    """Says when nobody has been seen for longer than `timeout` seconds."""

    def __init__(self, timeout):
        self.timeout = timeout
        self._last_seen = None

    def update(self, person_seen, t):
        """Returns True while the person counts as present."""
        if person_seen:
            self._last_seen = t
            return True
        return self._last_seen is not None and (t - self._last_seen) <= self.timeout


class Calibrator:
    """Collect frames of the neutral pose and measure the body.

    Restarts if the person moves too much, so the resting values are clean.
    Result: dict with shoulder_width, torso_length, hip_y, shoulder_mid (x, y).
    """

    KEY_POINTS = (F.L_SHOULDER, F.R_SHOULDER, F.L_HIP, F.R_HIP)

    def __init__(self, seconds, max_jitter, min_vis):
        self.seconds, self.max_jitter, self.min_vis = seconds, max_jitter, min_vis
        self.result = None
        self.restart()

    def restart(self):
        self._frames = []
        self._t0 = None
        self.result = None

    @property
    def done(self):
        return self.result is not None

    def progress(self, t):
        if self.done:
            return 1.0
        if self._t0 is None:
            return 0.0
        return min(1.0, (t - self._t0) / self.seconds)

    def update(self, lm, t):
        if self.done:
            return self.result
        if lm is None or not all(F.visible(lm, i, self.min_vis) for i in self.KEY_POINTS):
            self.restart()
            return None
        if self._frames:
            sw = F.shoulder_width(self._frames[0])
            moved = np.abs(lm[list(self.KEY_POINTS), :2] - self._frames[0][list(self.KEY_POINTS), :2]).max()
            if sw <= 0 or moved / sw > self.max_jitter:
                self.restart()
        if self._t0 is None:
            self._t0 = t
        self._frames.append(lm.copy())
        if t - self._t0 >= self.seconds and len(self._frames) >= 5:
            mean = np.mean(self._frames, axis=0)
            self.result = {
                "shoulder_width": F.shoulder_width(mean),
                "torso_length": F.torso_length(mean),
                "hip_y": float(F.midpoint(mean, F.L_HIP, F.R_HIP)[1]),
                "shoulder_mid": tuple(F.midpoint(mean, F.L_SHOULDER, F.R_SHOULDER)),
            }
        return self.result


class GlobalHotkeys:
    """Polls F12 (kill) and F11 (toggle) in a background thread.

    GetAsyncKeyState sees keys even while CS 1.6 has focus. On non-Windows
    systems this does nothing, so the app and tests still run.
    """

    def __init__(self, kill_vk, toggle_vk, on_kill, on_toggle, poll_s=0.02):
        self.kill_vk, self.toggle_vk = kill_vk, toggle_vk
        self.on_kill, self.on_toggle = on_kill, on_toggle
        self.poll_s = poll_s
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if sys.platform != "win32":
            return False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()

    def _run(self):
        import ctypes
        get = ctypes.windll.user32.GetAsyncKeyState
        was_toggle = False
        while not self._stop.is_set():
            if get(self.kill_vk) & 0x8000:
                self.on_kill()
                return
            down = bool(get(self.toggle_vk) & 0x8000)
            if down and not was_toggle:  # act on the press edge only
                self.on_toggle()
            was_toggle = down
            time.sleep(self.poll_s)
