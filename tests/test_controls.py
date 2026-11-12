from mcbody.backend import Driver, DryRunBackend
from mcbody.controls import (INDEX_TIP, L_HIP, L_SHOULDER, MIDDLE_MCP, NOSE, R_HIP,
                             R_SHOULDER, THUMB_TIP, WRIST, Intent, Point, calibrate,
                             compute_intent)


def pose(cx=0.5, width=0.2, sh_y=0.4, hip_y=0.7, nose_dx=0.0, nose_dy=-0.5):
    p = [Point(0.5, 0.5)] * 33
    p = list(p)
    p[L_SHOULDER] = Point(cx - width / 2, sh_y)
    p[R_SHOULDER] = Point(cx + width / 2, sh_y)
    p[L_HIP] = Point(cx - width / 2, hip_y)
    p[R_HIP] = Point(cx + width / 2, hip_y)
    p[NOSE] = Point(cx + nose_dx * width, sh_y + nose_dy * width)
    return p


def hand(pinched):
    h = [Point(0, 0)] * 21
    h = list(h)
    h[WRIST], h[MIDDLE_MCP] = Point(0, 0), Point(0, 1)
    h[THUMB_TIP] = Point(0, 0.5)
    h[INDEX_TIP] = Point(0.1 if pinched else 0.8, 0.5)
    return h


BASE = calibrate(pose())


def test_neutral_is_idle():
    assert compute_intent(pose(), BASE) == Intent()


def test_lean_forward_and_back():
    assert compute_intent(pose(width=0.24), BASE).forward
    assert compute_intent(pose(width=0.16), BASE).back


def test_strafe():
    assert compute_intent(pose(cx=0.5 - 0.1), BASE).left
    assert compute_intent(pose(cx=0.5 + 0.1), BASE).right


def test_jump_and_sneak():
    assert compute_intent(pose(hip_y=0.7 - 0.08), BASE).jump
    assert compute_intent(pose(sh_y=0.4 + 0.07), BASE).sneak


def test_look_deadzone_and_direction():
    assert compute_intent(pose(nose_dx=0.05), BASE).look_dx == 0
    assert compute_intent(pose(nose_dx=0.4), BASE).look_dx > 0
    assert compute_intent(pose(nose_dx=-0.4), BASE).look_dx < 0


def test_pinch_buttons():
    i = compute_intent(pose(), BASE, right_hand=hand(True), left_hand=hand(False))
    assert i.attack and not i.use


def test_driver_is_edge_triggered():
    be = DryRunBackend()
    d = Driver(be)
    d.apply(Intent(forward=True))
    d.apply(Intent(forward=True))
    d.apply(Intent())
    assert be.log == ["key w down", "key w up"]
