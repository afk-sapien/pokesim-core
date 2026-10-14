# Real-time clock

MBC3 cartridges with a clock (Gold, Silver, Crystal) need clock control from
pyboy-rs. Core detects it from the build's `has_rtc` flag when the build
publishes one, and otherwise from the presence of the clock methods. Without
it, these methods, passing `rtc_file` to the constructor or to `stop`, and
restoring a checkpoint saved with a locked clock raise `CoreCapabilityError`.
Everything else keeps working. Test `clock_control_available` first to avoid
the error. `CoreCapabilityError` subclasses `RuntimeError` only, so a broad
`except NotImplementedError` does not hide it.

## API

- `Emulator(rom, rtc_file=bytes_or_stream)` loads a PyBoy 2.7.0 `.rtc` file:
  ten bytes holding a little-endian float64 base timestamp (`timezero`), a halt
  byte and a day carry byte. Core copies the input, so the stream is never
  written later. Trailing bytes are ignored. Short input, NaN and flags above 1
  raise `ValueError`. The argument is ignored on cartridges without a clock,
  like PyBoy.
- `stop(save=False, ram_file=None, rtc_file=None)` writes the ten bytes to
  `rtc_file` (replacing its contents) and the SRAM to `ram_file`. Nothing is
  written otherwise. `export_rtc()` and `import_rtc(data)` do the same on a
  running machine. Latched registers are not part of the file.
- While the clock is locked, the export is the host-following equivalent (the
  file that reads as the locked clock's current time on the host clock), never
  the fake base. A real cartridge or an unlocked emulator therefore reads the
  right time. This needs pyboy-rs with the `rtc_export_follows_host` feature.
- `has_rtc`, `rtc_registers()`, `set_rtc_registers(seconds=, minutes=, hours=,
  days=, halt=, day_carry=)`, `rtc_state()` and `set_rtc_timezero(t)` give
  explicit access. Register setters move the base timestamp so the clock reads
  the requested values now.
- `lock_clock(at=None, follow_frames=False)` stops the cartridge reading the
  host clock. Time is `at`, plus `advance_clock(seconds)` calls, plus 4389/262144
  seconds per completed frame when `follow_frames` is true. Lock before the
  first tick for reproducible runs. `unlock_clock()` continues from the frozen
  reading without a jump. `clock_locked` and `clock_now()` report the state.

## Checkpoints

Raw `save` states hold the base timestamp but not the lock. `checkpoint` on a
cartridge with a clock always adds `rtc_clock`, the exact lock fields or `None`
(also available as `clock_lock_state()`), and `restore_checkpoint` applies it.
That is what an exact resume needs.

A locked checkpoint written by a different backend version, accepted only with
`match="state_format"`, is refused unless this machine already has the
identical lock applied, because the raw state cannot carry it. A checkpoint
with no clock data (no key, or `None`) releases any lock without shifting the
clock. Checkpoints of other cartridges carry no clock data. Execution recording
and replay work with a locked clock and reject a live one.
