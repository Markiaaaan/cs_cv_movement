import numpy as np
import pytest

from body_input.safety import Calibrator, PresenceWatchdog
from tests.fake_body import noisy, standing

FPS = 30


def test_watchdog_tolerates_short_dropouts():
    w = PresenceWatchdog(0.3)
    assert w.update(True, 0.0)
    assert w.update(False, 0.1)   # 3 lost frames: still present
    assert w.update(False, 0.3)
    assert not w.update(False, 0.35)
    assert w.update(True, 0.4)    # comes back


def test_watchdog_absent_before_anyone_is_seen():
    assert not PresenceWatchdog(0.3).update(False, 0.0)


def calib():
    return Calibrator(seconds=2.0, max_jitter=0.08, min_vis=0.5)


def test_calibration_measures_still_person_with_noise():
    rng = np.random.default_rng(1)
    c, body = calib(), standing(scale=0.8)
    for i in range(2 * FPS + 2):
        c.update(noisy(body, 0.002, rng), i / FPS)
    assert c.done
    assert c.result["shoulder_width"] == pytest.approx(0.15 * 0.8, rel=0.05)


def test_calibration_restarts_when_person_moves():
    c = calib()
    for i in range(FPS):
        c.update(standing(cx=0.5), i / FPS)
    c.update(standing(cx=0.7), 1.0)  # walked sideways
    assert c.progress(1.0) == 0.0
    assert not c.done


def test_calibration_restarts_on_tracking_loss():
    c = calib()
    for i in range(FPS):
        c.update(standing(), i / FPS)
    c.update(None, 1.0)
    assert c.progress(1.0) == 0.0


def test_calibration_ignores_low_visibility():
    c = calib()
    for i in range(3 * FPS):
        c.update(standing(vis=0.2), i / FPS)
    assert not c.done


def test_person_walking_past_never_calibrates():
    c = calib()
    for i in range(3 * FPS):
        c.update(standing(cx=0.1 + i * 0.01), i / FPS)
    assert not c.done
