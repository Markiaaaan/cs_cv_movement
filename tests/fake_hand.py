"""Fake 21-point hands, upright, palm toward the camera.

`ext` = (thumb, index, middle, ring, pinky) straight or not. s = hand size.
"""
import numpy as np

# Knuckle (MCP) x offsets for index..pinky, in hand sizes.
MCP_X = (-0.25, -0.08, 0.10, 0.30)
SIGNS = {
    "fist": (0, 0, 0, 0, 0), "palm": (1, 1, 1, 1, 1), "thumb": (1, 0, 0, 0, 0),
    "one": (0, 1, 0, 0, 0), "two": (0, 1, 1, 0, 0), "three": (0, 1, 1, 1, 0),
    "four": (0, 1, 1, 1, 1), "rock": (0, 1, 0, 0, 1),
}


def hand(x, y, ext, s=0.1):
    if isinstance(ext, str):
        ext = SIGNS[ext]
    h = np.zeros((21, 3), dtype=np.float32)
    h[0, :2] = (x, y)
    # Thumb: 1 CMC, 2 MCP, 3 IP, 4 tip.
    h[1, :2] = (x - 0.25 * s, y - 0.2 * s)
    h[2, :2] = (x - 0.35 * s, y - 0.4 * s)
    if ext[0]:
        h[3, :2], h[4, :2] = (x - 0.6 * s, y - 0.6 * s), (x - 0.85 * s, y - 0.75 * s)
    else:
        h[3, :2], h[4, :2] = (x - 0.2 * s, y - 0.55 * s), (x - 0.05 * s, y - 0.6 * s)
    for f, mx in enumerate(MCP_X):
        mcp = 5 + 4 * f
        bx = x + mx * s
        h[mcp, :2] = (bx, y - 0.85 * s)
        if ext[f + 1]:
            ys = (1.2, 1.45, 1.65)
        else:  # curled: tip comes back down toward the palm
            ys = (1.05, 0.9, 0.75)
        for k, dy in enumerate(ys):
            h[mcp + 1 + k, :2] = (bx, y - dy * s)
    return h
