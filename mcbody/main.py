"""Webcam loop: MediaPipe pose + hands -> Minecraft input.

Stand facing the camera, press 'c' to calibrate a neutral pose, 'q' to quit.
Use --dry-run to print actions instead of sending input.
"""
from __future__ import annotations

import argparse
import pathlib

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

from .backend import Driver, DryRunBackend
from .controls import Baseline, Point, calibrate, compute_intent

MODELS = pathlib.Path(__file__).resolve().parent.parent / "models"


def _pts(landmarks) -> list[Point]:
    return [Point(p.x, p.y) for p in landmarks]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", default="0", help="camera index or video file")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    backend = DryRunBackend() if args.dry_run else __import__(
        "mcbody.backend", fromlist=["PynputBackend"]).PynputBackend()
    driver = Driver(backend)

    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(MODELS / "pose_landmarker_lite.task")),
        running_mode=vision.RunningMode.VIDEO))
    hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(MODELS / "hand_landmarker.task")),
        running_mode=vision.RunningMode.VIDEO, num_hands=2))

    src = int(args.camera) if args.camera.isdigit() else args.camera
    cap = cv2.VideoCapture(src)
    base: Baseline | None = None
    ts = 0
    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)  # mirror so left lean = left on screen
            image = mp.Image(image_format=mp.ImageFormat.SRGB,
                             data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            ts += 33
            pr = pose.detect_for_video(image, ts)
            hr = hands.detect_for_video(image, ts)
            key = cv2.waitKey(1) & 0xFF
            if pr.pose_landmarks:
                p = _pts(pr.pose_landmarks[0])
                if key == ord("c"):
                    base = calibrate(p)
                    print("calibrated")
                if base:
                    right = left = None
                    for lm, hd in zip(hr.hand_landmarks, hr.handedness):
                        # frame is mirrored, so MediaPipe's labels already match the user's hands
                        if hd[0].category_name == "Right":
                            right = _pts(lm)
                        else:
                            left = _pts(lm)
                    driver.apply(compute_intent(p, base, right, left))
            else:
                driver.release_all()
            cv2.putText(frame, "calibrated" if base else "press c to calibrate", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            try:
                cv2.imshow("mcbody", frame)
            except cv2.error:
                pass  # headless build
            if key == ord("q"):
                break
    finally:
        driver.release_all()
        cap.release()


if __name__ == "__main__":
    main()
