"""Explicit emulator operations backed exclusively by PyBoy RS.

The application owns scheduling, files, budgets, and observation policy. Memory
and register writes are trusted host operations and do not belong in agent APIs.
"""
from __future__ import annotations

import io
from copy import deepcopy
import hashlib
from pathlib import Path

from .rom import require_rom

BUTTONS = ("up", "down", "left", "right", "a", "b", "start", "select")
FPS = 4_194_304 / 70_224


class ReplayDivergence(RuntimeError):
    """Replay failed at a checked interval. details contains detached diagnostics."""

    def __init__(self, details):
        self.details = deepcopy(details)
        super().__init__(f"Replay diverged at checkpoint {details['first_failed_offset']}")


class Memory:
    """Live byte and bank access. Slices return detached lists of bytes."""

    def __init__(self, owner):
        self._owner = owner

    def __getitem__(self, key):
        self._owner._ensure_open()
        return self._owner._backend.memory[key]

    def read_bytes(self, start, stop):
        """Return detached bytes from the current address-space mapping."""
        self._owner._ensure_open()
        backend = self._owner._backend.memory
        read = getattr(backend, 'read_bytes', None)
        if read is not None:
            return read(start, stop)
        import operator
        start, stop = operator.index(start), operator.index(stop)
        if not 0 <= start <= stop <= 65536:
            raise ValueError('Invalid memory range')
        return bytes(backend[start:stop]) if start != stop else b''

    def __setitem__(self, key, value):
        self._owner._ensure_open()
        self._owner._backend.memory[key] = value

    def __iter__(self):
        raise TypeError("Read an explicit memory range")


class Registers:
    """Trusted instrumentation registers, independent of the binding's types."""

    _names = frozenset(("A", "F", "B", "C", "D", "E", "HL", "SP", "PC"))

    def __init__(self, owner):
        object.__setattr__(self, "_owner", owner)

    def __getattr__(self, name):
        if name not in self._names:
            raise AttributeError(name)
        self._owner._ensure_open()
        return getattr(self._owner._backend.register_file, name)

    def __setattr__(self, name, value):
        if name not in self._names:
            raise AttributeError(name)
        self._owner._ensure_open()
        setattr(self._owner._backend.register_file, name, value)


class Screen:
    """RGBA output. Borrowed views update at the next tick or load."""

    width = 160
    height = 144

    def __init__(self, owner):
        self._owner = owner

    @property
    def raw_buffer(self):
        self._owner._ensure_open()
        return memoryview(self._owner._backend.screen.raw_buffer).toreadonly()

    @property
    def image(self):
        from PIL import Image
        return Image.frombytes("RGBA", (self.width, self.height), bytes(self.raw_buffer))

    @property
    def ndarray(self):
        import numpy as np
        return np.frombuffer(self.raw_buffer, dtype=np.uint8).reshape(self.height, self.width, 4)


class Audio:
    """Signed 8-bit interleaved stereo samples from the final ticked frame."""

    def __init__(self, owner, sample_rate):
        self._owner = owner
        self.sample_rate = sample_rate

    @property
    def raw_buffer(self):
        self._owner._ensure_open()
        return memoryview(self._owner._backend.sound.raw_buffer).toreadonly()

    @property
    def raw_buffer_head(self):
        self._owner._ensure_open()
        return self._owner._backend.sound.raw_buffer_head


class Emulator:
    """One explicitly advanced machine with isolated cartridge RAM.

    Batched tick renders and samples only its final frame. Use single-frame
    calls for continuous audio or video. No automatic file writes or pacing.
    Hooks run synchronously on the caller's thread. A hook may operate another
    machine, but may not recursively advance the same machine.
    """

    def __init__(self, rom, *, sound_emulated=True, sound_sample_rate=48000,
                 color_palette=(0xffffff, 0x999999, 0x555555, 0), ram_file=None,
                 window="null", log_level="ERROR", symbols=None):
        if window != "null":
            raise ValueError("Core emulators are headless")
        try:
            from pyboy_rs import PyBoy
        except ImportError as error:
            raise ImportError("Install pokesim-core with the emulator extra to use the Rust emulator") from error
        self._closed = False
        raw = rom.read() if hasattr(rom, "read") else Path(rom).read_bytes()
        self.rom_sha256 = hashlib.sha256(raw).hexdigest()
        self._settings = {"sample_rate": sound_sample_rate, "sound_emulated": sound_emulated,
                          "color_palette": list(color_palette)}
        self._ram = ram_file if ram_file is not None else io.BytesIO()
        self._backend = PyBoy(io.BytesIO(raw), window="null", sound_emulated=sound_emulated,
                              sound_sample_rate=sound_sample_rate, color_palette=color_palette,
                              ram_file=self._ram, log_level=log_level, symbols=symbols)
        self._backend.set_emulation_speed(0)
        self._frame_offset = -self._backend.frame_count
        self.memory = Memory(self)
        self.register_file = Registers(self)
        self.screen = Screen(self)
        self.sound = Audio(self, sound_sample_rate)
        self._pending = []
        self._recording_initial = None

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("The emulator is closed")

    @property
    def cartridge_title(self):
        self._ensure_open()
        return self._backend.cartridge_title

    @property
    def frame_count(self):
        """Completed frames on the Core timeline, including during callbacks."""
        self._ensure_open()
        return self._frame_offset + self._backend.frame_count

    @property
    def pending_inputs(self):
        return tuple(self._pending)

    def set_emulation_speed(self, speed):
        if speed != 0:
            raise ValueError("The application owns wall-clock pacing")
        self._ensure_open()

    def press(self, button):
        self._input(button, True)

    def release(self, button):
        self._input(button, False)

    def _input(self, button, pressed):
        self._ensure_open()
        if button not in BUTTONS:
            raise ValueError("Unknown controller button")
        self._pending.append((button, pressed))

    button_press = press
    button_release = release

    def tick(self, frames=1, render=True, sound=True):
        return self._advance(frames, render, sound)

    def tick_read(self, frames, start, stop, *, render=True, sound=True):
        """Advance and collect a detached range after all synchronous hooks finish."""
        import operator
        start, stop = operator.index(start), operator.index(stop)
        if not 0 <= start <= stop <= 65536:
            raise ValueError('Invalid memory range')
        return self._advance(frames, render, sound, (start, stop))

    def _flush_inputs(self):
        for button, pressed in self._pending:
            if pressed:
                self._backend.button_press(button)
            else:
                self._backend.button_release(button)
        self._pending.clear()

    def _execution_method(self, name):
        self._ensure_open()
        method = getattr(self._backend, name, None)
        if method is None:
            raise RuntimeError('This operation requires the experimental execution-enabled PyBoy RS build')
        return method

    def start_sequence(self, steps):
        if self._pending:
            raise RuntimeError('Advance pending Core inputs before starting a sequence')
        return self._execution_method('start_sequence')(steps)

    @property
    def sequence_progress(self):
        self._ensure_open()
        return deepcopy(getattr(self._backend, 'sequence_progress', None))

    def run_sequence(self, max_frames, *, render=True, sound=True, cancelled=None):
        method = self._execution_method('run_sequence')
        return method(max_frames, render=render, sound=sound, cancelled=cancelled,
                      _before_frame=self._flush_inputs)

    def cancel_sequence(self):
        return self._execution_method('cancel_sequence')()

    def start_recording(self, max_frames=100000, *, diagnostic_interval=0, diagnostic_ranges=((0xc000, 0xe000),)):
        method = self._execution_method('start_recording')
        initial = self.checkpoint()
        if diagnostic_interval or diagnostic_ranges != ((0xc000, 0xe000),):
            method(max_frames, diagnostic_interval=diagnostic_interval, diagnostic_ranges=diagnostic_ranges)
        else:
            method(max_frames)
        self._recording_initial = initial

    def stop_recording(self):
        try:
            backend = self._execution_method('stop_recording')()
        finally:
            initial, self._recording_initial = self._recording_initial, None
        return {'format': 1, 'initial': initial, 'final': self.checkpoint(), 'backend': backend}

    def replay(self, recording):
        method = self._execution_method('replay')
        if self._recording_initial is not None:
            raise RuntimeError('Stop recording before replay')
        if recording.get('format') != 1:
            raise ValueError('Unsupported Core recording')
        for name in ('initial', 'final'):
            checkpoint = recording[name]
            self._validate_checkpoint(checkpoint)
            if checkpoint.get('execution') != recording['backend'][name]:
                raise ValueError('Core and backend recording state mismatch')
        validate = getattr(self._backend, 'validate_recording', None)
        if validate is not None:
            validate(recording['backend'])
        self.restore_checkpoint(recording['initial'])
        try:
            result = method(recording['backend'])
        except RuntimeError as error:
            if hasattr(error, 'details'):
                raise ReplayDivergence(error.details) from error
            raise
        self.restore_checkpoint(recording['final'])
        return result

    def start_profiling(self):
        return self._execution_method('start_profiling')()

    def profiling_counters(self):
        return self._execution_method('profiling_counters')()

    def stop_profiling(self):
        return self._execution_method('stop_profiling')()

    def _advance(self, frames, render, sound, read_range=None):
        self._ensure_open()
        if type(frames) is not int or frames < 1:
            raise ValueError("frames must be a positive integer")
        self._flush_inputs()
        if read_range is None:
            return self._backend.tick(frames, render=render, sound=sound)
        combined = getattr(self._backend, 'tick_read', None)
        if combined is not None:
            return combined(frames, *read_range, render=render, sound=sound)
        self._backend.tick(frames, render=render, sound=sound)
        return self.memory.read_bytes(*read_range)

    def symbol_lookup(self, name):
        self._ensure_open()
        return tuple(self._backend.symbol_lookup(name))

    def hook_register(self, bank, address, callback, context):
        self._ensure_open()
        self._backend.hook_register(bank, address, callback, context)

    def hook_deregister(self, bank, address):
        self._ensure_open()
        self._backend.hook_deregister(bank, address)

    def save(self):
        self._ensure_open()
        stream = io.BytesIO()
        self._backend.save_state(stream)
        return stream.getvalue()

    def save_state(self, stream):
        stream.write(self.save())

    def load(self, state):
        """Load raw format-15 hardware state, preserving caller-queued inputs.

        Hardware states omit pending input. Use checkpoint/restore_checkpoint
        to transfer both the hardware and Core's pending input queue.
        """
        self._ensure_open()
        self._backend.load_state(io.BytesIO(state))

    def load_state(self, stream):
        self.load(stream.read())

    def checkpoint(self):
        from .emulator_state import runtime_provenance
        checkpoint = {"format": 1, "emulator": runtime_provenance(), "state": self.save(),
                      "pending_inputs": self.pending_inputs, "frames": self.frame_count,
                      "rom_sha256": self.rom_sha256, "settings": deepcopy(self._settings)}
        if hasattr(self._backend, 'execution_checkpoint'):
            checkpoint['format'] = 2
            checkpoint['execution'] = self._backend.execution_checkpoint()
        return checkpoint

    def _validate_checkpoint(self, checkpoint):
        self._ensure_open()
        from .emulator_state import validate_runtime
        validate_runtime(checkpoint, exact=True)
        if checkpoint.get("format") not in (1, 2):
            raise ValueError("Unsupported Core checkpoint")
        if checkpoint.get("rom_sha256") != self.rom_sha256 or checkpoint.get("settings") != self._settings:
            raise ValueError("Checkpoint ROM or emulator settings mismatch")
        frames = checkpoint.get("frames")
        if type(frames) is not int or frames < 0:
            raise ValueError("Invalid checkpoint frame count")
        pending = checkpoint.get("pending_inputs", ())
        for button, pressed in pending:
            if button not in BUTTONS or type(pressed) is not bool:
                raise ValueError("Invalid pending input")
        if checkpoint['format'] == 2:
            if checkpoint['state'] != checkpoint['execution']['state']:
                raise ValueError('Core and backend checkpoint state mismatch')

    def restore_checkpoint(self, checkpoint):
        checkpoint = deepcopy(checkpoint)
        self._validate_checkpoint(checkpoint)
        if self._recording_initial is not None:
            raise RuntimeError('Stop recording before restoring')
        if checkpoint['format'] == 2:
            self._execution_method('restore_execution')(checkpoint['execution'])
        else:
            self.load(checkpoint['state'])
        self._pending = list(checkpoint.get('pending_inputs', ()))
        self._frame_offset = checkpoint['frames'] - self._backend.frame_count

    def screenshot(self):
        buffer = io.BytesIO()
        self.screen.image.save(buffer, format="PNG")
        return buffer.getvalue()

    def audio_samples(self):
        return bytes(self.sound.raw_buffer[:self.sound.raw_buffer_head])

    def stop(self, save=False, ram_file=None):
        if not self._closed:
            # Persistence is explicit. Closing without a stream never writes a file.
            self._backend.stop(save=save or ram_file is not None, ram_file=ram_file)
            self._closed = True

    def close(self):
        self.stop(save=False)

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, *_):
        self.close()


class GameBoy(Emulator):
    """Verified Red/Blue adapter with isolated saves and silent hardware."""

    def __init__(self, rom: str | Path, state: bytes | None = None, *, allowed_games=("red", "blue")):
        self.rom_info = require_rom(rom, allowed_games=allowed_games)
        self.rom_sha256 = self.rom_info.sha256
        super().__init__(str(rom), sound_emulated=False, ram_file=io.BytesIO(bytes(32768)))
        try:
            if state is not None:
                self.load(state)
        except BaseException:
            self.close()
            raise


def check_runtime():
    """Exercise the installed native wheel using its public demonstration ROM."""
    rom = demo_rom().read_bytes()
    with Emulator(io.BytesIO(rom), sound_emulated=False) as game:
        game.tick(30)
        if len(game.screen.raw_buffer) != 160 * 144 * 4:
            raise RuntimeError("Invalid emulator framebuffer")


def demo_rom():
    """Path to the redistributable cartridge used by installed-runtime checks."""
    from importlib.resources import files
    return Path(str(files("pyboy_rs").joinpath("assets/default_rom.gb")))
