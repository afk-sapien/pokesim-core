"""Optional controller-driven PyBoy adapter with isolated save memory.

This is a trusted library API, not a security boundary. Applications must decide
which methods and observations they expose to an external agent.
"""
from __future__ import annotations

import io
from pathlib import Path

from .rom import require_rom

BUTTONS = ("up", "down", "left", "right", "a", "b", "start", "select")
FPS = 4_194_304 / 70_224


class GameBoy:
    """No background loop, automatic inputs, recovery, or save-file writes."""

    def __init__(self, rom: str | Path, state: bytes | None = None, *, allowed_games=("red", "blue")):
        self.rom_info = require_rom(rom, allowed_games=allowed_games)
        self.rom_sha256 = self.rom_info.sha256
        try:
            from pyboy import PyBoy
        except ImportError as error:
            raise ImportError("Install pokisim-core with the emulator extra to use GameBoy") from error
        self._closed = False
        self._pb = PyBoy(str(rom), window="null", sound_emulated=False,
                         ram_file=io.BytesIO(bytes(32768)), rtc_file=io.BytesIO())
        try:
            self._pb.set_emulation_speed(0)
            if state is not None:
                self.load(state)
        except BaseException:
            self.close()
            raise

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("The emulator is closed")

    @property
    def memory(self):
        """Return the memory view for trusted decoders. Do not expose it to agents."""
        self._ensure_open()
        return self._pb.memory

    def press(self, button: str):
        self._ensure_open()
        if button not in BUTTONS:
            raise ValueError("Unknown controller button")
        self._pb.button_press(button)

    def release(self, button: str):
        self._ensure_open()
        if button not in BUTTONS:
            raise ValueError("Unknown controller button")
        self._pb.button_release(button)

    def tick(self, frames: int = 1, *, render: bool = True):
        """Advance exactly the requested frames. Caller enforces its own budgets."""
        self._ensure_open()
        if type(frames) is not int or frames < 1:
            raise ValueError("frames must be a positive integer")
        return self._pb.tick(frames, render=render)

    def screenshot(self) -> bytes:
        self._ensure_open()
        buffer = io.BytesIO()
        self._pb.screen.image.save(buffer, format="PNG")
        return buffer.getvalue()

    def save(self) -> bytes:
        self._ensure_open()
        buffer = io.BytesIO()
        self._pb.save_state(buffer)
        return buffer.getvalue()

    def load(self, state: bytes):
        """Restore a trusted emulator state. Application manifests own compatibility checks."""
        self._ensure_open()
        self._pb.load_state(io.BytesIO(state))

    def close(self):
        if not self._closed:
            self._pb.stop(save=False)
            self._closed = True

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, *_):
        self.close()
