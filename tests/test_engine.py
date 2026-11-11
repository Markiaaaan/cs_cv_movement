"""Whole pipeline on fake people: engine -> mapper -> dry-run input."""
import numpy as np

from body_input import config as C
from body_input import features as F
from body_input.actions import ActionMapper
from body_input.gestures.engine import GestureEngine
from body_input.input_layer import DryRunBackend, InputController
from tests import fake_body as fb
from tests.fake_hand import hand

FPS = 30


class Rig:
    def __init__(self, body=None):
        self.body = fb.standing() if body is None else body
        self.engine = GestureEngine(F.rest_values(self.body), C)
        self.backend = DryRunBackend()
        self.ctl = InputController(self.backend)
        self.mapper = ActionMapper(self.ctl, C.KEYS)
        self.t = 0.0

    def frames(self, n, lm=None, hands=()):
        outs = []
        for _ in range(n):
            out = self.engine.update(self.body if lm is None else lm, list(hands), self.t)
            self.mapper.apply(out)
            outs.append(out)
            self.t += 1 / FPS
        return outs

    def taps(self):
        downs = [e[1] for e in self.backend.events if e[2:] == ("down",)]
        ups = [e[1] for e in self.backend.events if e[2:] == ("up",)]
        return downs, ups


def wrist_y(rig, where):
    lm = rig.body
    sh = F.midpoint(lm, F.L_SHOULDER, F.R_SHOULDER)[1]
    if where == "raised":
        return sh - 0.05
    return sh + 0.06  # chest height: above the hips by > FIRE_MIN_RAISE


def test_standing_still_sends_nothing():
    rng = np.random.default_rng(5)
    rig = Rig()
    for _ in range(5 * FPS):
        rig.frames(1, lm=fb.noisy(rig.body, 0.001, rng))
    assert rig.backend.events == [] and not rig.ctl.held


def test_walking_holds_w_and_stopping_releases_it():
    rig = Rig()
    for i in range(2 * FPS):
        side = 1 if (i // 8) % 2 == 0 else -1
        rig.frames(1, lm=fb.lift_knee(rig.body, side, 0.3 if i % 8 < 5 else 0.0))
    assert "w" in rig.ctl.held
    rig.frames(FPS // 2)
    assert "w" not in rig.ctl.held


def test_walking_with_hands_on_hips_goes_back():
    rig = Rig()
    hips = fb.hands_on_hips(rig.body)
    rig.frames(5, lm=fb.lift_knee(hips, 1, 0.3))
    assert "s" in rig.ctl.held and "w" not in rig.ctl.held


def test_lean_squat_and_jump():
    rig = Rig()
    rig.frames(3, lm=fb.lean_body(rig.body, -0.5))
    assert "a" in rig.ctl.held
    rig.frames(3, lm=fb.squat(rig.body, 0.3))
    assert "ctrl" in rig.ctl.held and "a" not in rig.ctl.held
    rig.frames(3, lm=fb.raise_arms(rig.body, 0.3))
    downs, _ = rig.taps()
    assert downs.count("space") == 1


def test_right_fist_at_chest_fires_until_opened():
    rig = Rig()
    x = rig.body[F.R_SHOULDER, 0] + 0.3  # image right = person's right hand
    fist = hand(x, wrist_y(rig, "chest"), "fist")
    rig.frames(3, hands=[fist])
    assert "mouse_left" in rig.ctl.held
    rig.frames(1, hands=[])  # one lost frame: keep firing
    assert "mouse_left" in rig.ctl.held
    rig.frames(3, hands=[hand(x, wrist_y(rig, "chest"), "palm")])
    assert "mouse_left" not in rig.ctl.held


def test_relaxed_fist_at_the_hips_does_not_fire():
    rig = Rig()
    hip_y = F.midpoint(rig.body, F.L_HIP, F.R_HIP)[1]
    rig.frames(10, hands=[hand(0.9, hip_y, "fist")])
    assert "mouse_left" not in rig.ctl.held


def test_left_hand_signs_switch_weapons_reload_and_scope():
    rig = Rig()
    y = wrist_y(rig, "raised")
    for sign, key in [("one", "1"), ("two", "2"), ("three", "3"), ("four", "4"),
                      ("thumb", "q"), ("fist", "r"), ("palm", "mouse_right")]:
        rig.frames(10, hands=[hand(0.1, y, sign)])
        rig.frames(3)  # lower the hand
        downs, _ = rig.taps()
        assert downs[-1] == key, sign
    assert not rig.ctl.held


def test_holding_a_sign_taps_only_once():
    rig = Rig()
    rig.frames(60, hands=[hand(0.1, wrist_y(rig, "raised"), "fist")])
    downs, _ = rig.taps()
    assert downs.count("r") == 1


def test_right_palm_raised_is_use_and_both_palms_is_buy():
    rig = Rig()
    y = wrist_y(rig, "raised")
    rig.frames(10, hands=[hand(0.9, y, "palm")])
    rig.frames(3)
    rig.frames(20, hands=[hand(0.1, y, "palm"), hand(0.9, y, "palm")])
    downs, _ = rig.taps()
    assert downs == ["e", "b"]  # no scope from the left palm while both are up


def test_person_lost_releases_everything():
    rig = Rig()
    rig.frames(3, lm=fb.squat(rig.body, 0.3))
    assert rig.ctl.held
    for _ in range(3):
        rig.mapper.apply(rig.engine.update(None, [], rig.t))
        rig.t += 1 / FPS
    assert not rig.ctl.held


def test_someone_walking_past_does_nothing_lasting():
    rig = Rig()
    for i in range(3 * FPS):
        rig.frames(1, lm=fb.standing(cx=0.05 + i * 0.01))
    rig.frames(FPS)
    assert not rig.ctl.held
