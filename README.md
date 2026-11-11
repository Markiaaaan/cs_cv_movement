# cs_cv_movement

Play Counter-Strike 1.6 with your body in front of a webcam.

**Offline / LAN against bots only.** Valve Anti-Cheat and server admins can
treat injected input as cheating, and a VAC ban is permanent. Never use this
on VAC-secured or public servers. There is no auto-aim and there never will be.

## Setup (Windows)

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python tools\download_models.py
```

## Run

```
.venv\Scripts\python tools\input_test.py            # 1st: does CS 1.6 see our input?
.venv\Scripts\python cs16_body_input.py --dry-run   # practise, sends nothing
.venv\Scripts\python cs16_body_input.py             # real input
.venv\Scripts\python cs16_body_input.py --no-hands  # body only, faster
.venv\Scripts\python -m pytest                       # tests, no camera needed
```

1. Stand about 2 m away so your whole body, knees included, is in the picture.
2. Stand still in a neutral pose until calibration reaches 100%. If the HUD
   says "not seen: knees", step back.
3. Press **F11** to start or pause control and **F12** to release everything
   and quit. Both hotkeys work while the game has focus.
4. In the preview window, press `c` to recalibrate and `q` or Esc to quit.

If CS 1.6 runs as administrator, run Python as administrator too.
Otherwise Windows silently blocks the input.
In CS, turn on raw mouse input (`m_rawinput 1`, if your version has it) and
tune `MOUSE_SENSITIVITY` and the `LOOK_*` settings in `body_input/config.py`.

## Gestures

| Action | Gesture | Key | Why this gesture |
|---|---|---|---|
| Walk | step in place (knee lifts) | W | natural; one knee up starts at once |
| Walk quietly | step slowly | + Shift | step speed is already measured |
| Back | step in place, hands on hips | S | lean-back is depth, hard to see with one camera |
| Strafe | lean torso left / right | A / D | big, cheap to see, works while walking |
| Crouch | squat | Ctrl | hips drop a lot; knees move together, so no fake steps |
| Jump | both arms above the head | Space | no real jumping indoors, hard to do by accident |
| Look | turn / tilt the head (joystick) | mouse | keeps both hands free; dead zone = no drift |
| Fire | right fist at chest height | left mouse | fist low at the hips does not fire |
| Weapons | left hand raised: 1, 2, 3, 4 fingers | 1-4 | finger counting is easy to remember |
| Last weapon | left hand raised: thumb only | Q | |
| Reload | left hand raised: fist | R | |
| Scope | left hand raised: open palm | right mouse | |
| Use | right hand raised: open palm | E | like pushing a door |
| Buy menu | both open palms raised, below the head, hold 0.4 s | B | rare, so a slower, deliberate pose |

Left-hand signs fire once after being held for 0.2 s. Lower the hand to do
the same sign again. Signs passing by (one → two → three while opening your
hand) do not fire.

**Head look caveat:** your eyes must stay on the screen, so the camera turns
at a speed set by how far you turn your head, not by matching angles. Small
turns give fine aim; a bigger turn spins fast.

**Left and right:** the image is mirrored, and nothing depends on MediaPipe's
left/right labels. Image position is used instead, because those labels are
easy to get backwards on a mirrored image.

## Measured

On the cloud test machine (4 CPU cores, no GPU) with a 640×480 frame:

- pose (lite): about 13 ms
- hands: about 27 ms
- both running in parallel threads: about 25 ms per frame, which is under the
  33 ms budget for 30 FPS

Your laptop will differ, so check the FPS on the HUD.

## Not tested yet (needs you, the camera, or the game)

- whether CS 1.6 accepts the SendInput scan codes (`tools/input_test.py`)
- every threshold on a real body; the tests use made-up stick figures
- hand-sign accuracy on real hands at 2 m (hands are small at that distance;
  if it is unreliable, stand closer or use `--no-hands`)
- the F11 / F12 hotkeys and the always-on-top preview window

## Layout

| File | Job |
|---|---|
| `cs16_body_input.py` | main loop: capture → detect → gestures → input, HUD |
| `body_input/config.py` | every threshold, key and sensitivity |
| `body_input/input_layer.py` | the only code that sends input; tracks held keys |
| `body_input/actions.py` | turns gesture output into holds / taps / mouse moves |
| `body_input/gestures/` | `body.py`, `look.py`, `hands.py`, `engine.py` (gesture map) |
| `body_input/features.py` | body-relative measures, One Euro filter, hysteresis |
| `body_input/detectors.py` | MediaPipe Pose and Hand Landmarker (Tasks API) |
| `body_input/safety.py` | person-lost watchdog, calibration, F11/F12 hotkeys |
| `body_input/hud.py` | skeleton, state, FPS, held keys, gestures |
| `tests/` | fake-landmark unit tests |
