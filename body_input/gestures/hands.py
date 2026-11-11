"""Hand signs from the 21 Hand Landmarker points, and triggers for them.

A hand is a (21, 3) array of x, y, z in image units. Every test is a ratio
of distances inside the hand, so hand size and distance do not matter.
"""
import numpy as np

WRIST = 0
THUMB_MCP, THUMB_TIP = 2, 4
# (PIP joint, tip) for index, middle, ring, pinky.
FINGERS = ((6, 8), (10, 12), (14, 16), (18, 20))
PINKY_MCP = 17


def _d(h, a, b):
    return float(np.linalg.norm(h[a, :2] - h[b, :2]))


def extended(h, finger_ratio, thumb_ratio):
    """Which fingers are straight: (thumb, index, middle, ring, pinky)."""
    thumb = _d(h, THUMB_TIP, PINKY_MCP) > thumb_ratio * _d(h, THUMB_MCP, PINKY_MCP)
    others = tuple(_d(h, WRIST, tip) > finger_ratio * _d(h, WRIST, pip) for pip, tip in FINGERS)
    return (thumb,) + others


SIGNS = {
    (False, False, False, False, False): "fist",
    (True, True, True, True, True): "palm",
    (True, False, False, False, False): "thumb",
    (False, True, False, False, False): "one",
    (False, True, True, False, False): "two",
    (False, True, True, True, False): "three",
    (False, True, True, True, True): "four",
}


def classify(h, finger_ratio, thumb_ratio):
    """Returns a sign name, or None for anything we do not use."""
    if h is None:
        return None
    return SIGNS.get(extended(h, finger_ratio, thumb_ratio))


def split_hands(hands, body_mid_x):
    """Return (left, right) hand of the person, or None for each.

    The image is mirrored, so the person's right hand is on the image right.
    We use image position, not MediaPipe's handedness label, which is easy to
    get backwards on a mirrored image.
    """
    if not hands:
        return None, None
    if len(hands) == 1:
        h = hands[0]
        return (None, h) if h[WRIST, 0] > body_mid_x else (h, None)
    a, b = sorted(hands[:2], key=lambda h: h[WRIST, 0])
    return a, b


class Debounce:
    """A bool that needs `on_n` true frames to turn on and `off_n` false to turn off."""

    def __init__(self, on_n, off_n):
        self.on_n, self.off_n = on_n, off_n
        self.state = False
        self._count = 0

    def update(self, value):
        if bool(value) != self.state:
            self._count += 1
            if self._count >= (self.on_n if value else self.off_n):
                self.state, self._count = bool(value), 0
        else:
            self._count = 0
        return self.state


class SignTrigger:
    """Emit a label once after it has been held `hold_s`; re-arm when it changes.

    Changing to another sign, or lowering the hand (None), re-arms, so a quick
    "fist, down, fist" reloads twice but holding a fist reloads only once.
    """

    def __init__(self, hold_s):
        self.hold_s = hold_s
        self._label, self._since, self._fired = None, None, False

    def update(self, label, t):
        if label != self._label:
            self._label, self._since, self._fired = label, t, False
        if label is None or self._fired or t - self._since < self.hold_s:
            return None
        self._fired = True
        return label
