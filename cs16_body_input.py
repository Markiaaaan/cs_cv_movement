"""Play CS 1.6 with your body. Skeleton: camera -> pose -> safety -> HUD.

Gestures are not wired in yet (milestone 3+). What works now:
  - webcam capture, Pose Landmarker, skeleton + FPS + model time on the HUD
  - calibration (stand still in the neutral pose)
  - F11 start/pause control, F12 kill switch (Windows, works in-game)
  - release_all() on pause, on person lost > 0.3 s, on error and on exit

Keys in the preview window: c = recalibrate, q / Esc = quit.
Run with --dry-run to see what would be sent without sending anything.
"""
import argparse
import atexit
import time

import cv2

from body_input import config as C
from body_input import hud
from body_input.detectors import PoseDetector
from body_input.input_layer import DryRunBackend, InputController, SendInputBackend
from body_input.safety import Calibrator, GlobalHotkeys, PresenceWatchdog


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true", help="never send real input")
    p.add_argument("--camera", type=int, default=C.CAMERA_INDEX)
    return p.parse_args()


class App:
    def __init__(self, args):
        backend = DryRunBackend(verbose=True) if args.dry_run else SendInputBackend()
        self.dry_run = args.dry_run
        self.input = InputController(backend, C.MOUSE_SENSITIVITY)
        atexit.register(self.input.release_all)  # last line of defence

        self.active = False   # control starts paused; F11 turns it on
        self.quit = False
        self.hotkeys = GlobalHotkeys(C.KILL_SWITCH_VK, C.TOGGLE_ACTIVE_VK,
                                     self.kill, self.toggle, C.HOTKEY_POLL_S)
        self.watchdog = PresenceWatchdog(C.PERSON_LOST_RELEASE_S)
        self.calib = Calibrator(C.CALIBRATION_SECONDS, C.CALIBRATION_MAX_JITTER,
                                C.LANDMARK_MIN_VISIBILITY)
        self.pose = PoseDetector(C.POSE_MODEL_PATH, C.POSE_MIN_DETECTION_CONFIDENCE,
                                 C.POSE_MIN_TRACKING_CONFIDENCE)

        self.cap = cv2.VideoCapture(args.camera)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, C.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, C.FRAME_HEIGHT)
        if not self.cap.isOpened():
            raise RuntimeError(f"cannot open camera {args.camera}")
        self.fps = 0.0

    # Called from the hotkey thread.
    def kill(self):
        self.active = False
        self.input.release_all()
        self.quit = True

    def toggle(self):
        if not self.calib.done:
            return  # cannot start control before calibration
        self.active = not self.active
        if not self.active:
            self.input.release_all()

    def step(self, frame, t):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        lm = self.pose.detect(rgb, t)

        present = self.watchdog.update(lm is not None, t)
        if not present:
            self.input.release_all()

        if not self.calib.done:
            self.calib.update(lm, t)
        elif self.active and lm is not None:
            pass  # gesture layer goes here (milestone 3+)

        if not self.active:
            self.input.release_all()  # paused means nothing is held
        return lm

    def draw(self, frame, lm, t):
        if lm is not None:
            hud.draw_skeleton(frame, lm, C.LANDMARK_MIN_VISIBILITY)
        if not self.calib.done:
            state = f"CALIBRATING {self.calib.progress(t) * 100:.0f}% - stand still"
            color = (0, 200, 255)
        elif self.active:
            state, color = "ACTIVE (F11 pause, F12 kill)", (0, 255, 0)
        else:
            state, color = "PAUSED (F11 start)", (0, 0, 255)
        held = ", ".join(sorted(self.input.held)) or "-"
        lines = [
            (state, color),
            (f"FPS {self.fps:.1f}  pose {self.pose.last_ms:.1f} ms", (255, 255, 255)),
            (f"held: {held}", (255, 255, 255)),
        ]
        if self.calib.done:
            r = self.calib.result
            lines.append((f"shoulder w {r['shoulder_width']:.3f}  torso {r['torso_length']:.3f}",
                          (200, 200, 200)))
        if self.dry_run:
            lines.append(("DRY RUN - nothing is sent", (0, 255, 255)))
        hud.draw_text(frame, lines)
        hud.show(frame)

    def run(self):
        self.hotkeys.start()
        last = time.perf_counter()
        while not self.quit:
            ok, frame = self.cap.read()
            t = time.perf_counter()
            if not ok:
                self.input.release_all()
                continue
            if C.MIRROR:
                frame = cv2.flip(frame, 1)
            lm = self.step(frame, t)

            dt = t - last
            last = t
            if dt > 0:  # smoothed FPS so the number is readable
                self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt) if self.fps else 1.0 / dt
            self.draw(frame, lm, t)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                self.quit = True
            elif key == ord("c"):
                self.active = False
                self.input.release_all()
                self.calib.restart()

    def close(self):
        self.hotkeys.stop()
        self.input.release_all()
        self.cap.release()
        self.pose.close()
        cv2.destroyAllWindows()


def main():
    app = App(parse_args())
    try:
        app.run()
    finally:
        app.close()  # release_all() on every exit path, errors included


if __name__ == "__main__":
    main()
