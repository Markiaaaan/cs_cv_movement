import numpy as np

from body_input import config as C
from body_input import features as F
from body_input.gestures.look import HeadLook
from tests import fake_body as fb

FPS = 30


def look(**kw):
    args = dict(yaw_dead=C.LOOK_YAW_DEADZONE, pitch_dead=C.LOOK_PITCH_DEADZONE,
                yaw_speed=C.LOOK_YAW_SPEED, pitch_speed=C.LOOK_PITCH_SPEED,
                curve=C.LOOK_CURVE, max_dt=C.LOOK_MAX_DT)
    args.update(kw)
    return HeadLook(**args)


def feed(hl, body, rest, seconds, t0=0.0):
    out = []
    for i in range(int(seconds * FPS)):
        t = t0 + i / FPS
        out.append(hl.update(F.head_yaw(body) - rest[0], F.head_pitch(body) - rest[1], t))
    return np.array(out)


def rest_of(body):
    return F.head_yaw(body), F.head_pitch(body)


def test_no_drift_when_standing_still_with_noise():
    rng = np.random.default_rng(3)
    body = fb.standing()
    rest = rest_of(body)
    hl = look()
    total = np.zeros(2)
    for i in range(10 * FPS):
        n = fb.noisy(body, 0.0008, rng)
        total += hl.update(F.head_yaw(n) - rest[0], F.head_pitch(n) - rest[1], i / FPS)
    assert np.abs(total).max() == 0


def test_turn_right_moves_mouse_right_and_down_moves_down():
    body = fb.standing()
    rest = rest_of(body)
    right = feed(look(), fb.turn_head(body, yaw=0.4), rest, 1.0)
    down = feed(look(), fb.turn_head(body, pitch=0.4), rest, 1.0)
    assert right[:, 0].sum() > 0 and right[:, 1].sum() == 0
    assert down[:, 1].sum() > 0 and down[:, 0].sum() == 0


def test_bigger_turn_is_faster():
    body = fb.standing()
    rest = rest_of(body)
    small = feed(look(), fb.turn_head(body, yaw=0.2), rest, 1.0)[:, 0].sum()
    big = feed(look(), fb.turn_head(body, yaw=0.4), rest, 1.0)[:, 0].sum()
    assert big > small > 0


def test_invert_pitch():
    body = fb.standing()
    rest = rest_of(body)
    down = feed(look(invert_pitch=True), fb.turn_head(body, pitch=0.4), rest, 1.0)
    assert down[:, 1].sum() < 0


def test_dropout_sends_nothing_and_no_jump_after():
    body = fb.standing()
    rest = rest_of(body)
    hl = look()
    turned = fb.turn_head(body, yaw=0.4)
    hl.update(F.head_yaw(turned) - rest[0], 0.0, 0.0)
    assert hl.update(None, None, 0.1) == (0.0, 0.0)
    # Back after 2 s: first frame must not use the 2 s gap as dt.
    assert hl.update(F.head_yaw(turned) - rest[0], 0.0, 2.1) == (0.0, 0.0)


def test_same_turn_same_speed_at_any_distance():
    near, far = fb.standing(scale=1.2), fb.standing(scale=0.6)
    a = feed(look(), fb.turn_head(near, yaw=0.3), rest_of(near), 1.0)[:, 0].sum()
    b = feed(look(), fb.turn_head(far, yaw=0.3), rest_of(far), 1.0)[:, 0].sum()
    assert abs(a - b) / a < 0.01
