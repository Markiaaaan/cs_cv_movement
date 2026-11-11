# cs_cv_movement

Play Counter-Strike 1.6 with your body in front of a webcam.

**Offline / LAN against bots only.** Valve Anti-Cheat and server admins can
treat injected input as cheating, so never use this on VAC-secured or public
servers. There is no auto-aim and there never will be.

## Status

The skeleton is in place: camera, pose model, HUD, calibration, kill switch,
pause, and a safe input layer. Gestures are not wired in yet.

## Setup (Windows)

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python tools\download_models.py
```

## Run

```
.venv\Scripts\python cs16_body_input.py --dry-run   # shows, sends nothing
.venv\Scripts\python cs16_body_input.py             # real input
.venv\Scripts\python tools\input_test.py            # milestone 2: does CS see us?
.venv\Scripts\python -m pytest                       # tests, no camera needed
```

1. Stand still in the neutral pose until calibration reaches 100%.
2. Press **F11** to start or pause control. Press **F12** to release
   everything and quit. Both hotkeys work while the game has focus.
3. In the preview window, press `c` to recalibrate and `q` or Esc to quit.

If CS 1.6 runs as administrator, run Python as administrator too.
Otherwise Windows silently blocks the input.

## Layout

| File | Job |
|---|---|
| `cs16_body_input.py` | main loop: capture → pose → safety → HUD |
| `body_input/config.py` | every threshold, key and sensitivity |
| `body_input/input_layer.py` | the only code that sends input; tracks held keys |
| `body_input/detectors.py` | MediaPipe Pose Landmarker (Tasks API, VIDEO mode) |
| `body_input/features.py` | body-relative units, One Euro filter, hysteresis |
| `body_input/safety.py` | person-lost watchdog, calibration, F11/F12 hotkeys |
| `body_input/hud.py` | skeleton, state, FPS, held keys |
| `tests/` | fake-landmark unit tests |
