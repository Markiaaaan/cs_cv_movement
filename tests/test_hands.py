import numpy as np
import pytest

from body_input import config as C
from body_input.gestures.hands import Debounce, SignTrigger, classify, split_hands
from tests.fake_hand import SIGNS, hand

FPS = 30


def cls(h):
    return classify(h, C.FINGER_EXT_RATIO, C.THUMB_EXT_RATIO)


@pytest.mark.parametrize("sign", ["fist", "palm", "thumb", "one", "two", "three", "four"])
def test_every_sign_is_recognised(sign):
    assert cls(hand(0.5, 0.5, sign)) == sign


@pytest.mark.parametrize("size", [0.04, 0.1, 0.25])
def test_hand_size_does_not_matter(size):
    assert cls(hand(0.3, 0.6, "two", s=size)) == "two"


def test_unknown_sign_and_missing_hand_give_none():
    assert cls(hand(0.5, 0.5, "rock")) is None
    assert cls(None) is None


def test_signs_survive_small_noise():
    rng = np.random.default_rng(4)
    for sign in SIGNS:
        if sign == "rock":
            continue
        hits = sum(cls(hand(0.5, 0.5, sign) + rng.normal(0, 0.003, (21, 3))) == sign
                   for _ in range(50))
        assert hits >= 45, sign


def test_split_hands_by_image_side():
    left, right = hand(0.3, 0.5, "fist"), hand(0.7, 0.5, "palm")
    assert split_hands([right, left], 0.5) == (left, right)
    one_left = split_hands([left], 0.5)
    assert one_left[0] is left and one_left[1] is None
    assert split_hands([], 0.5) == (None, None)


def test_debounce_ignores_single_frame_flicker():
    d = Debounce(on_n=2, off_n=3)
    seq = [1, 0, 1, 1, 0, 1, 0, 0, 0]
    out = [d.update(v) for v in seq]
    assert out == [False, False, False, True, True, True, True, True, False]


def test_sign_trigger_fires_once_per_hold():
    s = SignTrigger(C.SIGN_HOLD_S)
    fired = [s.update("fist", i / FPS) for i in range(30)]
    assert [f for f in fired if f] == ["fist"]
    assert fired.index("fist") / FPS >= C.SIGN_HOLD_S


def test_sign_trigger_rapid_repeat_after_lowering_hand():
    s = SignTrigger(C.SIGN_HOLD_S)
    labels = ["fist"] * 8 + [None] * 3 + ["fist"] * 8
    fired = [s.update(lab, i / FPS) for i, lab in enumerate(labels)]
    assert sum(f == "fist" for f in fired) == 2


def test_sign_trigger_ignores_passing_signs():
    s = SignTrigger(C.SIGN_HOLD_S)
    # Opening a fist goes one -> two -> three -> palm quickly: nothing fires
    labels = ["one", "one", "two", "two", "three", "three", None]
    assert not any(s.update(lab, i / FPS) for i, lab in enumerate(labels))
