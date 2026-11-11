import pytest

from body_input.input_layer import DryRunBackend, InputController


def make():
    b = DryRunBackend()
    return InputController(b), b


def test_hold_sends_down_once_and_tracks_state():
    c, b = make()
    c.hold("w")
    c.hold("w")
    assert c.held == {"w"}
    assert b.events == [("key", "w", "down")]


def test_release_only_sends_up_for_held_keys():
    c, b = make()
    c.release("w")
    assert b.events == []
    c.hold("w")
    c.release("w")
    assert b.events[-1] == ("key", "w", "up") and not c.held


def test_release_all_releases_keys_and_buttons():
    c, b = make()
    for k in ("w", "ctrl", "mouse_left"):
        c.hold(k)
    c.release_all()
    assert not c.held
    ups = {e[1] for e in b.events if e[2] == "up"}
    assert ups == {"w", "ctrl", "mouse_left"}


def test_release_all_keeps_going_after_a_failure():
    c, b = make()
    c.hold("a")
    c.hold("w")
    real = b.key

    def flaky(name, down):
        if name == "a" and not down:
            raise OSError("boom")
        real(name, down)

    b.key = flaky
    with pytest.raises(OSError):
        c.release_all()
    assert not c.held
    assert ("key", "w", "up") in b.events


def test_tap_is_down_then_up_and_skips_held_key():
    c, b = make()
    c.tap("r")
    assert b.events == [("key", "r", "down"), ("key", "r", "up")]
    c.hold("r")
    n = len(b.events)
    c.tap("r")
    assert len(b.events) == n


def test_unknown_key_raises_and_is_not_held():
    c, _ = make()
    with pytest.raises(KeyError):
        c.hold("f13")
    assert not c.held


def test_mouse_sensitivity_and_subpixel_remainder():
    b = DryRunBackend()
    c = InputController(b, sensitivity=0.25)
    for _ in range(8):
        c.move_mouse(1, 0)  # 0.25 px each: must add up, not vanish
    total = sum(e[1] for e in b.events if e[0] == "move")
    assert total == 2


def test_zero_move_sends_nothing():
    c, b = make()
    c.move_mouse(0, 0)
    assert b.events == []
