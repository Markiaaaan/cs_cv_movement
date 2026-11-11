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

# --- Walk in place (knee lifts) -------------------------------------------
# Units: torso lengths of knee height difference between the two knees.
STEP_ON = 0.15        # a knee counts as lifted above this
STEP_OFF = 0.07       # ...and as down again below this (hysteresis)
WALK_STOP_S = 0.35    # release W this long after the last lifted knee
WALK_SLOW_INTERVAL_S = 0.75  # steps slower than this hold Shift (quiet walk)

# --- Posture ----------------------------------------------------------------
LEAN_ON = 0.30        # sideways lean (shoulder widths) that starts strafing
LEAN_OFF = 0.18
CROUCH_ON = 0.20      # hip drop (torso lengths) that starts crouching
CROUCH_OFF = 0.12
JUMP_ON = 0.15        # lower wrist above the nose (torso lengths) = jump
JUMP_OFF = 0.0        # arms must come back down below the nose to re-arm
JUMP_COOLDOWN_S = 0.4
# Hands on hips = walk backward while stepping. Both wrists within
# HIPS_WRIST_MAX shoulder widths of a hip AND elbows spread wide.
HIPS_WRIST_MAX = 0.5
HIPS_ELBOW_SPAN_ON = 1.6   # elbow-to-elbow, in shoulder widths
HIPS_ELBOW_SPAN_OFF = 1.4

# --- Camera look (head turn, joystick style) -------------------------------
# Units: ear distances of nose offset from the calibrated rest position.
LOOK_YAW_DEADZONE = 0.10
LOOK_PITCH_DEADZONE = 0.10
LOOK_YAW_SPEED = 2500.0    # mouse counts per second at 1.0 past the dead zone
LOOK_PITCH_SPEED = 1200.0
LOOK_CURVE = 1.5           # >1 = finer control near the dead zone
LOOK_MAX_DT = 0.1          # cap frame gaps so a stall cannot cause a big jump
LOOK_INVERT_PITCH = False

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
