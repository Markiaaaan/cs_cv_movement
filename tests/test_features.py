import numpy as np
import pytest

from body_input import features as F
from body_input.features import Hysteresis, OneEuroFilter
from tests.fake_body import standing


def test_body_units_do_not_depend_on_distance():
    near, far = standing(scale=1.2), standing(scale=0.6)
    r_near = F.torso_length(near) / F.shoulder_width(near)
    r_far = F.torso_length(far) / F.shoulder_width(far)
    assert r_near == pytest.approx(r_far, rel=1e-5)


def test_one_euro_smooths_noise_when_still():
    rng = np.random.default_rng(0)
    f = OneEuroFilter(min_cutoff=1.0, beta=0.0)
    raw = 0.5 + rng.normal(0, 0.01, 300)
    out = [f(x, i / 30) for i, x in enumerate(raw)]
    assert np.std(out[30:]) < np.std(raw[30:]) / 2


def test_one_euro_follows_a_step_with_beta():
    f = OneEuroFilter(min_cutoff=1.0, beta=5.0)
    for i in range(30):
        f(0.0, i / 30)
    for i in range(30, 45):
        y = f(1.0, i / 30)
    assert y > 0.9  # within half a second


def test_one_euro_ignores_non_increasing_time():
    f = OneEuroFilter()
    f(1.0, 1.0)
    assert f(5.0, 1.0) == 5.0  # resets instead of dividing by zero


def test_hysteresis_does_not_flicker_between_thresholds():
    h = Hysteresis(on_at=0.6, off_at=0.4)
    seq = [0.5, 0.61, 0.55, 0.45, 0.59, 0.41, 0.39, 0.5]
    states = [h.update(v) for v in seq]
    assert states == [False, True, True, True, True, True, False, False]


def test_hysteresis_rejects_bad_thresholds():
    with pytest.raises(ValueError):
        Hysteresis(on_at=0.4, off_at=0.6)
