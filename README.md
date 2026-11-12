# mcbody — webcam body controls for Minecraft (Java)

Lean forward/back = W/S · lean sideways = A/D · hop = jump · crouch = sneak ·
head offset = mouse look · right-hand pinch = attack · left-hand pinch = use.

    python -m venv .venv && .venv/bin/pip install -r requirements.txt
    python -m mcbody.main --dry-run     # print actions
    python -m mcbody.main               # send real input; press c to calibrate, q to quit

Models live in `models/` (hand_landmarker.task, pose_landmarker_lite.task).
Run tests with `pytest`.
