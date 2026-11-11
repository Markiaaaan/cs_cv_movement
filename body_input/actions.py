"""Turn an engine Output into key presses through the InputController.

Every frame we compare the wanted holds with every holdable action and
release anything not wanted. So a key is only held while its gesture is
still seen in the current frame; nothing can be left behind.
"""

HOLD_ACTIONS = ("forward", "back", "left", "right", "walk", "crouch", "fire")


class ActionMapper:
    def __init__(self, controller, keys):
        self.ctl, self.keys = controller, keys

    def apply(self, out):
        for action in HOLD_ACTIONS:
            key = self.keys[action]
            if action in out.holds:
                self.ctl.hold(key)
            else:
                self.ctl.release(key)
        for action in out.taps:
            self.ctl.tap(self.keys[action])
        dx, dy = out.move
        if dx or dy:
            self.ctl.move_mouse(dx, dy)
