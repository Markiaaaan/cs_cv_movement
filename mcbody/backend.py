"""Applies Intents to the OS (pynput) or just prints them (dry run)."""
from __future__ import annotations

from .controls import Intent

KEYS = {"forward": "w", "back": "s", "left": "a", "right": "d", "jump": " ", "sneak": "shift"}
BUTTONS = {"attack": "left", "use": "right"}


class DryRunBackend:
    def __init__(self) -> None:
        self.log: list[str] = []

    def key(self, name: str, down: bool) -> None:
        self.log.append(f"key {name} {'down' if down else 'up'}")

    def button(self, name: str, down: bool) -> None:
        self.log.append(f"button {name} {'down' if down else 'up'}")

    def move_mouse(self, dx: int, dy: int) -> None:
        self.log.append(f"mouse {dx},{dy}")

    def release_all(self) -> None:
        pass


class PynputBackend:
    def __init__(self) -> None:
        from pynput import keyboard, mouse  # lazy: needs a display
        self._kb, self._ms = keyboard.Controller(), mouse.Controller()
        self._keyboard, self._mouse = keyboard, mouse

    def _k(self, name: str):
        return self._keyboard.Key.shift if name == "shift" else (
            self._keyboard.Key.space if name == " " else name)

    def key(self, name: str, down: bool) -> None:
        (self._kb.press if down else self._kb.release)(self._k(name))

    def button(self, name: str, down: bool) -> None:
        b = getattr(self._mouse.Button, name)
        (self._ms.press if down else self._ms.release)(b)

    def move_mouse(self, dx: int, dy: int) -> None:
        self._ms.move(dx, dy)

    def release_all(self) -> None:
        for n in KEYS.values():
            self.key(n, False)
        for n in BUTTONS.values():
            self.button(n, False)


class Driver:
    """Edge-triggered: only sends press/release when a control changes."""

    def __init__(self, backend) -> None:
        self.backend = backend
        self._held: dict[str, bool] = {}

    def apply(self, intent: Intent) -> None:
        for attr, key in KEYS.items():
            self._edge(("k", key), getattr(intent, attr), self.backend.key, key)
        for attr, btn in BUTTONS.items():
            self._edge(("b", btn), getattr(intent, attr), self.backend.button, btn)
        dx, dy = round(intent.look_dx), round(intent.look_dy)
        if dx or dy:
            self.backend.move_mouse(dx, dy)

    def _edge(self, slot, want: bool, fn, name: str) -> None:
        if self._held.get(slot, False) != want:
            fn(name, want)
            self._held[slot] = want

    def release_all(self) -> None:
        self.backend.release_all()
        self._held.clear()
