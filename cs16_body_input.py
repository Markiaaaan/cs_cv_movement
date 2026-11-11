"""Play CS 1.6 with your body: camera -> pose/hands -> gestures -> input.

  - calibration first (stand still in the neutral pose)
  - F11 start/pause control, F12 kill switch (Windows, works in-game)
  - release_all() on pause, on person lost > 0.3 s, on error and on exit
  - the gesture map is in body_input/gestures/engine.py

Keys in the preview window: c = recalibrate, q / Esc = quit.
Run with --dry-run to see what would be sent without sending anything.
"""
import argparse
import atexit
import time
from concurrent.futures import ThreadPoolExecutor

import cv2

from body_input import config as C
from body_input import hud
from body_input.actions import ActionMapper
from body_input.detectors import HandDetector, PoseDetector
from body_input.gestures.engine import GestureEngine
from body_input.input_layer import DryRunBackend, InputController, SendInputBackend
from body_input.safety import Calibrator, GlobalHotkeys, PresenceWatchdog


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true", help="never send real input")
    p.add_argument("--camera", type=int, default=C.CAMERA_INDEX)
    p.add_argument("--no-hands", action="store_true",
                   help="body only: faster, but no shooting or weapon switching")
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
        self.hands = None
        if C.USE_HANDS and not args.no_hands:
            self.hands = HandDetector(C.HAND_MODEL_PATH, C.HAND_MIN_DETECTION_CONFIDENCE,
                                      C.HAND_MIN_TRACKING_CONFIDENCE)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.mapper = ActionMapper(self.input, C.KEYS)
        self.engine = None   # built from the calibration result
        self.out = None      # last gesture output, for the HUD
        self.hand_pts = []

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
        # Hands run in a second thread while pose runs here. MediaPipe works
        # outside Python's GIL, so this cut 40 ms to 25 ms per frame in a test.
        fut = self.pool.submit(self.hands.detect, rgb, t) if self.hands else None
        lm = self.pose.detect(rgb, t)
        self.hand_pts = fut.result() if fut else []

        present = self.watchdog.update(lm is not None, t)

        if not self.calib.done:
            self.calib.update(lm, t)
            if self.calib.done:
                self.engine = GestureEngine(self.calib.result, C)
            self.out = None
        else:
            # Gestures run even while paused, so you can practise on the HUD.
            self.out = self.engine.update(lm, self.hand_pts, t)
            if self.active and present:
                self.mapper.apply(self.out)

        if not self.active or not present:
            self.input.release_all()  # paused or nobody there: nothing is held
        return lm

    def draw(self, frame, lm, t):
        if lm is not None:
            hud.draw_skeleton(frame, lm, C.LANDMARK_MIN_VISIBILITY)
        for h in self.hand_pts:
            hud.draw_hand(frame, h)
        if not self.calib.done:
            state = f"CALIBRATING {self.calib.progress(t) * 100:.0f}% - stand still"
            if self.calib.missing:
                state = "CALIBRATING - not seen: " + ", ".join(self.calib.missing)
            color = (0, 200, 255)
        elif self.active:
            state, color = "ACTIVE (F11 pause, F12 kill)", (0, 255, 0)
        else:
            state, color = "PAUSED (F11 start)", (0, 0, 255)
        held = ", ".join(sorted(self.input.held)) or "-"
        lines = [
            (state, color),
            (f"FPS {self.fps:.1f}  pose {self.pose.last_ms:.1f} ms"
             + (f"  hands {self.hands.last_ms:.1f} ms" if self.hands else "  (no hands)"),
             (255, 255, 255)),
            (f"held: {held}", (255, 255, 255)),
        ]
        if self.out is not None:
            lines.append(("gestures: " + (", ".join(self.out.labels) or "-"), (255, 255, 0)))
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
                self.engine = None

    def close(self):
        self.hotkeys.stop()
        self.input.release_all()
        self.cap.release()
        self.pose.close()
        self.pool.shutdown(wait=True)
        if self.hands:
            self.hands.close()
        cv2.destroyAllWindows()


def main():
    app = App(parse_args())
    try:
        app.run()
    finally:
        app.close()  # release_all() on every exit path, errors included


if __name__ == "__main__":
    main()
