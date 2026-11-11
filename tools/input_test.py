"""Milestone 2: prove that CS 1.6 sees our input.

Start this, then click into CS 1.6 within the countdown. It will:
  hold W for 1 s (you walk forward), turn the camera right then left,
  click fire once. Everything is released at the end, or on Ctrl+C.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from body_input.input_layer import DryRunBackend, InputController, SendInputBackend  # noqa: E402


def main():
    dry = "--dry-run" in sys.argv
    ctl = InputController(DryRunBackend(verbose=True) if dry else SendInputBackend())
    try:
        for n in range(5, 0, -1):
            print(f"Focus CS 1.6 now... {n}")
            time.sleep(1)
        ctl.hold("w")
        time.sleep(1.0)
        ctl.release("w")
        for _ in range(30):  # small steps look like a real mouse
            ctl.move_mouse(10, 0)
            time.sleep(0.01)
        for _ in range(30):
            ctl.move_mouse(-10, 0)
            time.sleep(0.01)
        ctl.tap("mouse_left")
        print("Done. Did the player walk, turn and shoot?")
    finally:
        ctl.release_all()


if __name__ == "__main__":
    main()
