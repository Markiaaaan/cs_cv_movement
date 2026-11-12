"""Pure pose -> Minecraft intent logic (no camera, no OS input; fully testable).

Coordinates are MediaPipe-normalised image coordinates (x right, y down) of a
*mirrored* frame, so leaning to your left moves the landmarks left on screen.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

# MediaPipe pose landmark indices
NOSE, L_SHOULDER, R_SHOULDER, L_HIP, R_HIP = 0, 11, 12, 23, 24
# MediaPipe hand landmark indices
WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_MCP = 0, 4, 8, 9


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Baseline:
    """Neutral standing posture captured during calibration."""
    shoulder_width: float
    mid_x: float
    shoulder_y: float
    hip_y: float
    nose_dx: float  # nose x offset from shoulder midpoint, in shoulder widths
    nose_dy: float  # nose y offset from shoulder midpoint, in shoulder widths


@dataclass(frozen=True)
class Tuning:
    lean_forward: float = 0.12   # relative growth in shoulder width -> W
    lean_back: float = 0.12      # relative shrink -> S
    strafe: float = 0.35         # shoulder-widths of sideways lean -> A/D
    jump: float = 0.30           # hips rise (shoulder-widths) -> space
    sneak: float = 0.25          # shoulders drop (shoulder-widths) -> shift
    look_deadzone: float = 0.10  # head offset (shoulder-widths) ignored
    look_gain: float = 60.0      # pixels/frame per shoulder-width beyond deadzone
    pinch: float = 0.35          # thumb-index gap / hand size below which = pinch


@dataclass(frozen=True)
class Intent:
    forward: bool = False
    back: bool = False
    left: bool = False
    right: bool = False
    jump: bool = False
    sneak: bool = False
    look_dx: float = 0.0
    look_dy: float = 0.0
    attack: bool = False   # left mouse (mine / hit)
    use: bool = False      # right mouse (place / use)


def _mid(a: Point, b: Point) -> Point:
    return Point((a.x + b.x) / 2, (a.y + b.y) / 2)


def _dist(a: Point, b: Point) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def calibrate(pose: Sequence[Point]) -> Baseline:
    ls, rs, lh, rh = pose[L_SHOULDER], pose[R_SHOULDER], pose[L_HIP], pose[R_HIP]
    width = _dist(ls, rs)
    if width <= 1e-6:
        raise ValueError("shoulders not resolvable; stand facing the camera")
    sm, hm = _mid(ls, rs), _mid(lh, rh)
    return Baseline(
        shoulder_width=width,
        mid_x=sm.x,
        shoulder_y=sm.y,
        hip_y=hm.y,
        nose_dx=(pose[NOSE].x - sm.x) / width,
        nose_dy=(pose[NOSE].y - sm.y) / width,
    )


def _axis(value: float, deadzone: float, gain: float) -> float:
    if abs(value) <= deadzone:
        return 0.0
    return (abs(value) - deadzone) * gain * (1 if value > 0 else -1)


def is_pinch(hand: Sequence[Point], threshold: float) -> bool:
    size = _dist(hand[WRIST], hand[MIDDLE_MCP])
    if size <= 1e-6:
        return False
    return _dist(hand[THUMB_TIP], hand[INDEX_TIP]) / size < threshold


def compute_intent(
    pose: Sequence[Point],
    base: Baseline,
    right_hand: Sequence[Point] | None = None,
    left_hand: Sequence[Point] | None = None,
    tuning: Tuning = Tuning(),
) -> Intent:
    """Map the current pose (and optional hands) to Minecraft controls.

    Lean forward/back = W/S, lean sideways = A/D, hop = jump, crouch = sneak,
    head offset = mouse look, right-hand pinch = attack, left-hand pinch = use.
    """
    ls, rs, lh, rh = pose[L_SHOULDER], pose[R_SHOULDER], pose[L_HIP], pose[R_HIP]
    width = _dist(ls, rs)
    if width <= 1e-6:
        return Intent()
    sm, hm = _mid(ls, rs), _mid(lh, rh)
    w = base.shoulder_width

    scale = width / w - 1.0  # >0 closer to camera (leaning in)
    forward = scale > tuning.lean_forward
    back = scale < -tuning.lean_back

    side = (sm.x - base.mid_x) / w
    left = side < -tuning.strafe
    right = side > tuning.strafe

    jump = (base.hip_y - hm.y) / w > tuning.jump
    sneak = (sm.y - base.shoulder_y) / w > tuning.sneak

    dx = (pose[NOSE].x - sm.x) / width - base.nose_dx
    dy = (pose[NOSE].y - sm.y) / width - base.nose_dy
    look_dx = _axis(dx, tuning.look_deadzone, tuning.look_gain)
    look_dy = _axis(dy, tuning.look_deadzone, tuning.look_gain)

    return Intent(
        forward=forward and not back,
        back=back and not forward,
        left=left and not right,
        right=right and not left,
        jump=jump,
        sneak=sneak,
        look_dx=look_dx,
        look_dy=look_dy,
        attack=bool(right_hand) and is_pinch(right_hand, tuning.pinch),
        use=bool(left_hand) and is_pinch(left_hand, tuning.pinch),
    )
