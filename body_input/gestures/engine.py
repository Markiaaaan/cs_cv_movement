"""Runs every gesture on one frame and says which actions are wanted.

Input: pose landmarks (or None), a list of hands, the time. Output: which
actions to hold right now, which to tap once, and a mouse move. No input
code here; actions.ActionMapper turns this into key presses.

Gesture map (justified in the README):
  step in place ............ forward (W), slow steps also Shift
  step + hands on hips ..... back (S)
  lean left / right ........ strafe (A / D)
  squat .................... crouch (Ctrl)
  both arms above head ..... jump (Space)
  turn / tilt head ......... camera (mouse)
  right fist at chest ...... fire (left mouse)
  left hand raised + sign .. 1-4 weapons, thumb = last weapon, fist = reload,
                             open palm = scope (right mouse)
  right open palm raised ... use (E)
  both open palms raised, below head, held ... buy menu (B)
"""
from dataclasses import dataclass, field

from .. import features as F
from .body import EdgeTrigger, Lean, Level, WalkInPlace
from .hands import Debounce, SignTrigger, classify, split_hands
from .look import HeadLook


@dataclass
class Output:
    holds: set = field(default_factory=set)
    taps: list = field(default_factory=list)
    move: tuple = (0.0, 0.0)
    labels: list = field(default_factory=list)  # what the HUD shows


class GestureEngine:
    def __init__(self, rest, cfg):
        self.rest, self.c = rest, cfg
        c = cfg
        self.walk = WalkInPlace(c.STEP_ON, c.STEP_OFF, c.WALK_STOP_S, c.WALK_SLOW_INTERVAL_S)
        self.lean = Lean(c.LEAN_ON, c.LEAN_OFF)
        self.crouch = Level(c.CROUCH_ON, c.CROUCH_OFF)
        self.hips = Level(c.HIPS_ELBOW_SPAN_ON, c.HIPS_ELBOW_SPAN_OFF)
        self.jump = EdgeTrigger(c.JUMP_ON, c.JUMP_OFF, c.JUMP_COOLDOWN_S)
        self.look = HeadLook(c.LOOK_YAW_DEADZONE, c.LOOK_PITCH_DEADZONE,
                             c.LOOK_YAW_SPEED, c.LOOK_PITCH_SPEED, c.LOOK_CURVE,
                             c.LOOK_MAX_DT, c.LOOK_INVERT_PITCH,
                             (c.ONE_EURO_MIN_CUTOFF, c.ONE_EURO_BETA, c.ONE_EURO_D_CUTOFF))
        self.fire = Debounce(c.FIRE_ON_FRAMES, c.FIRE_OFF_FRAMES)
        self.left_sign = SignTrigger(c.SIGN_HOLD_S)
        self.right_sign = SignTrigger(c.SIGN_HOLD_S)
        self.buy = SignTrigger(c.BUY_HOLD_S)

    def _vis(self, lm, *idxs):
        return lm is not None and F.all_visible(lm, idxs, self.c.LANDMARK_MIN_VISIBILITY)

    def update(self, lm, hands, t):
        c, r, out = self.c, self.rest, Output()
        body = self._vis(lm, F.L_SHOULDER, F.R_SHOULDER, F.L_HIP, F.R_HIP)
        knees = body and self._vis(lm, F.L_KNEE, F.R_KNEE)
        head = body and self._vis(lm, F.NOSE, F.L_EAR, F.R_EAR)
        arms = body and self._vis(lm, F.L_WRIST, F.R_WRIST, F.L_ELBOW, F.R_ELBOW, F.NOSE)

        # Legs and torso.
        walk = self.walk.update(F.knee_diff(lm) - r["knee_diff"] if knees else None, t)
        backward = self.hips.update(F.hands_on_hips(lm, c.HIPS_WRIST_MAX) if arms else None)
        if walk.walking:
            out.holds.add("back" if backward else "forward")
            out.labels.append("walk back" if backward else "walk")
            if walk.slow:
                out.holds.add("walk")
                out.labels.append("quiet")
        side = self.lean.update(F.lean(lm) - r["lean"] if body else None)
        if side:
            out.holds.add("right" if side > 0 else "left")
            out.labels.append("strafe " + ("right" if side > 0 else "left"))
        if self.crouch.update(F.hip_drop(lm, r["hip_y"], r["torso_length"]) if body else None):
            out.holds.add("crouch")
            out.labels.append("crouch")
        if self.jump.update(F.arms_up(lm) if arms else None, t):
            out.taps.append("jump")
            out.labels.append("JUMP")

        # Head.
        if head:
            out.move = self.look.update(F.head_yaw(lm) - r["head_yaw"],
                                        F.head_pitch(lm) - r["head_pitch"], t)
        else:
            out.move = self.look.update(None, None, t)

        self._hands(lm if body else None, hands, t, out)
        return out

    def _hands(self, lm, hands, t, out):
        c = self.c
        left = right = None
        if lm is not None:
            shoulder = F.midpoint(lm, F.L_SHOULDER, F.R_SHOULDER)
            hip_y = F.midpoint(lm, F.L_HIP, F.R_HIP)[1]
            left, right = split_hands(hands, shoulder[0])
        ratios = (c.FINGER_EXT_RATIO, c.THUMB_EXT_RATIO)
        l_sign, r_sign = classify(left, *ratios), classify(right, *ratios)
        l_up = left is not None and left[0, 1] < shoulder[1]
        r_up = right is not None and right[0, 1] < shoulder[1]

        fire_pose = (r_sign == "fist" and not r_up
                     and right[0, 1] < hip_y - c.FIRE_MIN_RAISE * self.rest["torso_length"])
        if self.fire.update(fire_pose):
            out.holds.add("fire")
            out.labels.append("FIRE")

        # Both hands up: only "buy" counts, so single-hand signs cannot misfire.
        buy_pose = (l_up and r_up and l_sign == "palm" and r_sign == "palm"
                    and min(left[0, 1], right[0, 1]) > lm[F.NOSE, 1])
        if self.buy.update("buy" if buy_pose else None, t):
            out.taps.append("buy")
            out.labels.append("BUY")

        l_label = l_sign if (l_up and not r_up) else None
        fired = self.left_sign.update(l_label, t)
        if fired in c.LEFT_SIGNS:
            out.taps.append(c.LEFT_SIGNS[fired])
            out.labels.append(c.LEFT_SIGNS[fired].upper())

        r_label = r_sign if (r_up and not l_up) else None
        fired = self.right_sign.update(r_label, t)
        if fired in c.RIGHT_RAISED_SIGNS:
            out.taps.append(c.RIGHT_RAISED_SIGNS[fired])
            out.labels.append(c.RIGHT_RAISED_SIGNS[fired].upper())
