"""Download the MediaPipe .task model files into models/ (skips existing ones)."""
import urllib.request
from pathlib import Path

BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "pose_landmarker_lite.task": f"{BASE}/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
    "hand_landmarker.task": f"{BASE}/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
}


def main():
    out = Path(__file__).resolve().parent.parent / "models"
    out.mkdir(exist_ok=True)
    for name, url in MODELS.items():
        path = out / name
        if path.exists():
            print(f"have {name}")
            continue
        print(f"downloading {name} ...")
        urllib.request.urlretrieve(url, path)
    print("models ready in", out)


if __name__ == "__main__":
    main()
