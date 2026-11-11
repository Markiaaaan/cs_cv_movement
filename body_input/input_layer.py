"""The ONLY place that sends keyboard and mouse input.

InputController remembers every key and button it holds, so release_all()
can always undo them. A stuck W or a stuck fire button is the worst failure,
so every exit path in the app ends in release_all().

Backends do the actual sending:
- DryRunBackend records what would be sent (any OS, used by tests too).
- SendInputBackend sends hardware scan codes through Windows SendInput,
  which old engines like GoldSrc (CS 1.6) accept. pyautogui's virtual-key
  events are often ignored by such games, and its moveTo() cannot turn a
  first-person camera, so we use relative MOUSEEVENTF_MOVE instead.
"""
import ctypes
import sys
import threading

# Set-1 keyboard scan codes. "extended" keys would need KEYEVENTF_EXTENDEDKEY;
# none of the keys below are extended (left Ctrl / left Shift are not).
SCAN_CODES = {
    "esc": 0x01, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06,
    "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13,
    "a": 0x1E, "s": 0x1F, "d": 0x20, "b": 0x30,
    "ctrl": 0x1D, "shift": 0x2A, "space": 0x39,
}
MOUSE_BUTTONS = ("mouse_left", "mouse_right")


class DryRunBackend:
    """Records events instead of sending them. Prints them if verbose."""

    def __init__(self, verbose=False):
        self.events = []
        self.verbose = verbose

    def _log(self, event):
        self.events.append(event)
        if self.verbose:
            print("[dry-run]", *event)

    def key(self, name, down):
        self._log(("key", name, "down" if down else "up"))

    def button(self, name, down):
        self._log(("button", name, "down" if down else "up"))

    def move(self, dx, dy):
        self._log(("move", dx, dy))


class SendInputBackend:
    """Windows SendInput with scan codes and relative mouse moves."""

    INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
    KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 0x0002, 0x0008
    MOUSEEVENTF_MOVE = 0x0001
    MOUSE_FLAGS = {  # (down flag, up flag)
        "mouse_left": (0x0002, 0x0004),
        "mouse_right": (0x0008, 0x0010),
    }

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("SendInputBackend only works on Windows; use --dry-run")
        self._user32 = ctypes.windll.user32
        self._INPUT, self._MOUSEINPUT, self._KEYBDINPUT = _input_structs()

    def _send(self, inp):
        sent = self._user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        if sent != 1:  # e.g. blocked by UIPI when the game runs as admin and we don't
            raise OSError(f"SendInput failed (error {ctypes.get_last_error()})")

    def key(self, name, down):
        flags = self.KEYEVENTF_SCANCODE | (0 if down else self.KEYEVENTF_KEYUP)
        ki = self._KEYBDINPUT(0, SCAN_CODES[name], flags, 0, 0)
        inp = self._INPUT(self.INPUT_KEYBOARD)
        inp.u.ki = ki
        self._send(inp)

    def button(self, name, down):
        flag = self.MOUSE_FLAGS[name][0 if down else 1]
        self._mouse(0, 0, flag)

    def move(self, dx, dy):
        self._mouse(dx, dy, self.MOUSEEVENTF_MOVE)

    def _mouse(self, dx, dy, flags):
        inp = self._INPUT(self.INPUT_MOUSE)
        inp.u.mi = self._MOUSEINPUT(dx, dy, 0, flags, 0, 0)
        self._send(inp)


def _input_structs():
    """The Win32 INPUT structure, built with fixed-size ctypes types."""
    WORD, DWORD, LONG = ctypes.c_uint16, ctypes.c_uint32, ctypes.c_int32
    ULONG_PTR = ctypes.c_size_t

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", LONG), ("dy", LONG), ("mouseData", DWORD),
                    ("dwFlags", DWORD), ("time", DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", WORD), ("wScan", WORD), ("dwFlags", DWORD),
                    ("time", DWORD), ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", DWORD), ("wParamL", WORD), ("wParamH", WORD)]

    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", DWORD), ("u", _U)]

    return INPUT, MOUSEINPUT, KEYBDINPUT


class InputController:
    """Owns all key/button state. Thread-safe so the kill switch can call it."""

    def __init__(self, backend, sensitivity=1.0):
        self.backend = backend
        self.sensitivity = sensitivity
        self.held = set()
        self._lock = threading.Lock()
        self._rem_x = 0.0  # sub-pixel leftovers, so slow turns don't vanish
        self._rem_y = 0.0

    def _press(self, name, down):
        if name in MOUSE_BUTTONS:
            self.backend.button(name, down)
        elif name in SCAN_CODES:
            self.backend.key(name, down)
        else:
            raise KeyError(f"unknown key {name!r}")

    def hold(self, name):
        with self._lock:
            if name not in self.held:  # never send a second "down"
                self._press(name, True)
                self.held.add(name)

    def release(self, name):
        with self._lock:
            if name in self.held:
                self.held.discard(name)
                self._press(name, False)

    def tap(self, name):
        """Press and release. Does nothing if the key is already held."""
        with self._lock:
            if name in self.held:
                return
            self._press(name, True)
            self._press(name, False)

    def move_mouse(self, dx, dy):
        with self._lock:
            fx = dx * self.sensitivity + self._rem_x
            fy = dy * self.sensitivity + self._rem_y
            ix, iy = int(round(fx)), int(round(fy))
            self._rem_x, self._rem_y = fx - ix, fy - iy
            if ix or iy:
                self.backend.move(ix, iy)

    def release_all(self):
        """Release everything. Keeps going even if one release fails."""
        with self._lock:
            errors = []
            for name in sorted(self.held):
                try:
                    self._press(name, False)
                except Exception as exc:  # still try the other keys
                    errors.append(exc)
            self.held.clear()
            self._rem_x = self._rem_y = 0.0
        if errors:
            raise errors[0]
