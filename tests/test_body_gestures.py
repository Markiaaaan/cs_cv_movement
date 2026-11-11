"""Walk, lean, crouch, jump, hands-on-hips fed with fake body measures."""
import numpy as np

from body_input import config as C
from body_input import features as F
from body_input.gestures.body import EdgeTrigger, Lean, Level, WalkInPlace
from tests import fake_body as fb

FPS = 30


def walker():
    return WalkInPlace(C.STEP_ON, C.STEP_OFF, C.WALK_STOP_S, C.WALK_SLOW_INTERVAL_S)


def knee_wave(step_hz, seconds, amp=0.3, t0=0.0):
    """Alternating knee lifts: sine wave of knee difference."""
    n = int(seconds * FPS)
    ts = t0 + np.arange(n) / FPS
    return ts, amp * np.sin(2 * np.pi * (step_hz / 2) * (ts - t0))


def run(w, ts, vals):
    return [w.update(v, t) for t, v in zip(ts, vals)]


def test_walk_starts_within_a_quarter_second():
    w = walker()
    ts, vals = knee_wave(step_hz=2.0, seconds=1.0)
    states = run(w, ts, vals)
    first = next(i for i, s in enumerate(states) if s.walking)
    assert ts[first] <= 0.25


def test_walk_stops_within_half_a_second():
    w = walker()
    ts, vals = knee_wave(step_hz=2.0, seconds=2.0)
    run(w, ts, vals)
    # Stop: knees go back to level from the last frame on.
    still_ts = ts[-1] + np.arange(1, FPS) / FPS
    states = run(w, still_ts, [0.0] * len(still_ts))
    stopped = next(t for t, s in zip(still_ts, states) if not s.walking)
    assert stopped - ts[-1] <= 0.5


def test_walk_stays_on_between_steps():
    w = walker()
    ts, vals = knee_wave(step_hz=2.0, seconds=3.0)
    states = run(w, ts, vals)
    first = next(i for i, s in enumerate(states) if s.walking)
    assert all(s.walking for s in states[first:])


def test_slow_steps_mean_quiet_walk_fast_steps_run():
    slow = run(walker(), *knee_wave(step_hz=1.0, seconds=3.0))
    fast = run(walker(), *knee_wave(step_hz=2.5, seconds=3.0))
    assert slow[-1].slow and not fast[-1].slow


def test_standing_still_with_noise_never_walks():
    rng = np.random.default_rng(2)
    w = walker()
    states = [w.update(rng.normal(0, 0.02), i / FPS) for i in range(10 * FPS)]
    assert not any(s.walking for s in states)


def test_squat_does_not_walk():
    body = fb.standing()
    rest = F.knee_diff(body)
    w = walker()
    for i in range(FPS):
        lm = fb.squat(body, 0.4 * i / FPS)
        assert not w.update(F.knee_diff(lm) - rest, i / FPS).walking


def test_tracking_dropout_mid_walk_keeps_walking_briefly_then_stops():
    w = walker()
    ts, vals = knee_wave(step_hz=2.0, seconds=1.0)
    vals = list(vals)
    vals[20:23] = [None] * 3  # 3 lost frames
    states = run(w, ts, vals)
    assert states[23].walking
    lost_ts = ts[-1] + np.arange(1, FPS) / FPS
    assert not run(w, lost_ts, [None] * len(lost_ts))[-1].walking


def test_knee_diff_from_fake_body_matches_lift():
    body = fb.standing(scale=0.7)
    lifted = fb.lift_knee(body, +1, 0.3)
    assert F.knee_diff(lifted) - F.knee_diff(body) > C.STEP_ON


def test_lean_left_right_and_center():
    body = fb.standing()
    rest = F.lean(body)
    lean = Lean(C.LEAN_ON, C.LEAN_OFF)
    assert lean.update(F.lean(fb.lean_body(body, 0.4)) - rest) == 1
    assert lean.update(F.lean(fb.lean_body(body, 0.25)) - rest) == 1  # hysteresis
    assert lean.update(F.lean(body) - rest) == 0
    assert lean.update(F.lean(fb.lean_body(body, -0.4)) - rest) == -1
    assert lean.update(None) == 0


def test_crouch_with_hysteresis():
    body = fb.standing()
    r = F.rest_values(body)
    crouch = Level(C.CROUCH_ON, C.CROUCH_OFF)
    drop = lambda lm: F.hip_drop(lm, r["hip_y"], r["torso_length"])  # noqa: E731
    assert not crouch.update(drop(fb.squat(body, 0.1)))
    assert crouch.update(drop(fb.squat(body, 0.3)))
    assert crouch.update(drop(fb.squat(body, 0.15)))
    assert not crouch.update(drop(body))


def test_hands_on_hips_needs_elbows_out_not_just_hanging_arms():
    body = fb.standing()
    on = Level(C.HIPS_ELBOW_SPAN_ON, C.HIPS_ELBOW_SPAN_OFF)
    score = lambda lm: F.hands_on_hips(lm, C.HIPS_WRIST_MAX)  # noqa: E731
    assert not on.update(score(body))  # relaxed arms, wrists near hips
    assert on.update(score(fb.hands_on_hips(body)))
    assert not on.update(score(fb.raise_arms(body, 0.3)))
    assert not on.update(score(body))


def test_jump_fires_once_per_arm_raise_and_respects_cooldown():
    body = fb.standing()
    jump = EdgeTrigger(C.JUMP_ON, C.JUMP_OFF, C.JUMP_COOLDOWN_S)
    up, down = F.arms_up(fb.raise_arms(body, 0.3)), F.arms_up(body)
    fired = [jump.update(v, i / FPS) for i, v in enumerate([down, up, up, up, down, up])]
    assert fired == [False, True, False, False, False, False]  # 2nd raise too soon
    assert jump.update(down, 1.0) is False
    assert jump.update(up, 1.1) is True  # rapid repeated jumps work after cooldown


def test_jump_ignores_dropouts():
    jump = EdgeTrigger(C.JUMP_ON, C.JUMP_OFF, C.JUMP_COOLDOWN_S)
    assert not any(jump.update(None, i / FPS) for i in range(10))
