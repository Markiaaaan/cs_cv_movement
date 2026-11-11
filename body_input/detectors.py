"""MediaPipe Pose Landmarker (Tasks API) wrapper.

mediapipe 1.2.2 has no mp.solutions, so we use mediapipe.tasks with
RunningMode.VIDEO. VIDEO mode needs a strictly growing timestamp in ms.
"""
import time

import numpy as np


class PoseDetector:
    def __init__(self, model_path, min_detection=0.5, min_tracking=0.5):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        self._mp = mp
        options = vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection,
            min_tracking_confidence=min_tracking,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._last_ts = -1
        self.last_ms = 0.0  # time spent in the model for the last frame

    def detect(self, frame_rgb, t_seconds):
        """Returns a (33, 4) array [x, y, z, visibility] or None."""
        ts = int(t_seconds * 1000)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=frame_rgb)
        start = time.perf_counter()
        result = self._landmarker.detect_for_video(image, ts)
        self.last_ms = (time.perf_counter() - start) * 1000
        if not result.pose_landmarks:
            return None
        pts = result.pose_landmarks[0]
        return np.array([[p.x, p.y, p.z, p.visibility or 0.0] for p in pts], dtype=np.float32)

    def close(self):
        self._landmarker.close()
