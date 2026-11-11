"""Every threshold, key binding and sensitivity lives here.

Tune the game feel by editing this file only; the logic files read from it.
"""

# --- Camera -----------------------------------------------------------------
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
MIRROR = True  # mirror the image so moving right looks like moving right

# --- Models -----------------------------------------------------------------
# "lite" is the fastest pose model; switch to "full" only if lite is too noisy.
POSE_MODEL_PATH = "models/pose_landmarker_lite.task"
HAND_MODEL_PATH = "models/hand_landmarker.task"
POSE_MIN_DETECTION_CONFIDENCE = 0.5
POSE_MIN_TRACKING_CONFIDENCE = 0.5
LANDMARK_MIN_VISIBILITY = 0.5  # below this a landmark counts as "not seen"

# --- Safety -----------------------------------------------------------------
# Release every key if no person is seen for this long (seconds).
PERSON_LOST_RELEASE_S = 0.3
# Windows virtual-key codes for the global hotkeys (work while the game has focus).
KILL_SWITCH_VK = 0x7B    # F12: release everything and quit
TOGGLE_ACTIVE_VK = 0x7A  # F11: start / pause control
HOTKEY_POLL_S = 0.02

# --- Calibration ------------------------------------------------------------
CALIBRATION_SECONDS = 2.0     # stand still in the neutral pose this long
CALIBRATION_MAX_JITTER = 0.08  # max allowed movement, in shoulder widths

# --- Smoothing (One Euro filter) -------------------------------------------
# min_cutoff: lower = smoother when still. beta: higher = less lag when moving.
ONE_EURO_MIN_CUTOFF = 1.0
ONE_EURO_BETA = 0.05
ONE_EURO_D_CUTOFF = 1.0

# --- Mouse ------------------------------------------------------------------
MOUSE_SENSITIVITY = 1.0  # multiplies every relative mouse move

# --- CS 1.6 key bindings (names must exist in input_layer.SCAN_CODES) ------
KEYS = {
    "forward": "w",
    "back": "s",
    "left": "a",
    "right": "d",
    "walk": "shift",
    "jump": "space",
    "crouch": "ctrl",
    "reload": "r",
    "use": "e",
    "buy": "b",
    "last_weapon": "q",
    "slot1": "1",
    "slot2": "2",
    "slot3": "3",
    "slot4": "4",
    "slot5": "5",
    "fire": "mouse_left",
    "scope": "mouse_right",
}
