# PokeSim Core

Shared Pokemon Red and Blue primitives for simulation and agent research.

The package extracts low-level functionality used by PokeSim and a separate
agent benchmark. The base install uses only Python's standard library. The
optional emulator extra supplies the Rust-backed Core emulator interface.

## Unreleased Rust integration

Version `0.2.0.dev0` uses PyBoy RS as its only production emulator. Both
applications import Core. Only Core imports the native Python package.
The working checkouts must be siblings named `pyboy-rs`, `pokesim-core`,
`pokesim`, and `pokeagent-bench`. Until releases are published, `uv` resolves
these local source overrides:

```bash
uv sync --extra dev --extra emulator
uv run pytest
uv run ruff check .
```

A source install needs Rust and Maturin. Released application installations
will use prebuilt wheels after the separate release step. The older release
commands below still install the previous PyBoy-backed version.

`Emulator` owns isolated machine operations, memory and register wrappers,
RGBA output, signed 8-bit stereo audio, hooks, and explicit cartridge export.
It has no application thread, automatic file writes, or agent policy.
`GameBoy` adds verified Red/Blue ROM selection for the benchmark. Core memory
writes and hooks are trusted host APIs. Applications decide which observations
and actions their agents can access.

Batched `tick` advances exactly the requested positive number of frames and
renders and samples its last frame. Tick one frame at a time for continuous
media. Output views are read-only and change on the next tick or state load.
Use bytes to retain a snapshot. Image encoding lazily imports Pillow. NumPy
views require the caller to install NumPy.

Raw `save` and `load` preserve format-15 compatibility. They exclude pending
controller operations and keep the caller's current pending queue. Core's
`checkpoint` and `restore_checkpoint` additionally preserve pending inputs and
frame counts and validate the ROM, settings, and exact native build. Failed
state loads leave the machine unchanged. Hooks are owned by the caller and
must be registered on a fresh machine before resuming instrumented execution.

`emulator_state` owns runtime fingerprints and known legacy import rules.
`checkpoint_audio` owns the format-specific conversion for silent legacy
checkpoints. Ordinary imports can accept PyBoy 2.7.0 format-15 saves. Exact
benchmark resumes require the recorded Rust build. New manifests identify
PyBoy RS explicitly, including the native extension and binding hashes.
Trade outputs retain an explicit source-to-output runtime migration record.

`gen1_cable.CableEndpoint` owns the verified ROM-hook transport, queues,
register parking, and hook cleanup. Applications own participants, navigation,
time budgets, persistence, and transaction adoption. This mechanism is an
explicit Gen1 virtual cable implemented with verified ROM hooks.

The optional native tests use the redistributable demo. Private gameplay and
trade checks use temporary copies and never enter package artifacts. Upstream
PyBoy is used only as a development oracle in emulator tests and the timing
harness in `tools/benchmark_emulator.py`.

## Real-time clock

MBC3 cartridges with a clock (Gold, Silver, Crystal) need clock control, which requires a PyBoy RS build with RTC support. Older builds raise `RuntimeError` from
these methods and everything else keeps working.

- `Emulator(rom, rtc_file=bytes_or_stream)` loads a PyBoy 2.7.0 `.rtc` file: ten
  bytes holding a little-endian float64 base timestamp (`timezero`), a halt byte and
  a day carry byte. Core copies the input, so the stream is never written later.
  Trailing bytes are ignored. Short input, NaN and flags above 1 raise `ValueError`.
  The argument is ignored on cartridges without a clock, like PyBoy.
- `stop(save=False, ram_file=None, rtc_file=None)` writes the ten bytes to
  `rtc_file` (replacing its contents) and the SRAM to `ram_file`. Nothing is written
  otherwise. `export_rtc()` and `import_rtc(data)` do the same on a running machine.
  Latched registers are not part of the file.
- `has_rtc`, `rtc_registers()`, `set_rtc_registers(seconds=, minutes=, hours=,
  days=, halt=, day_carry=)`, `rtc_state()` and `set_rtc_timezero(t)` give explicit
  access. Register setters move the base timestamp so the clock reads the requested
  values now. Writes made by the game keep PyBoy's upstream arithmetic.
- `lock_clock(at=None, follow_frames=False)` stops the cartridge reading the host
  clock. Time is `at` plus `advance_clock(seconds)` calls plus, when `follow_frames`
  is true, 4389/262144 seconds per completed frame. Lock before the first tick for
  reproducible runs. `unlock_clock()` continues from the frozen reading without a
  jump. `clock_locked` and `clock_now()` report the state.

Raw `save` states hold the base timestamp but not the lock. `checkpoint` on a
cartridge with a clock adds `rtc_clock`, the exact lock fields or `None`, and
`restore_checkpoint` applies it, which is what an exact resume needs. A checkpoint
without that key leaves the lock alone, and checkpoints of other cartridges are
unchanged. Execution recording and replay still reject cartridges with a live clock.

## Experimental Core acceleration

The separate `pokesim-core-native` distribution in `native/` uses PyO3 and
Maturin to decode a complete WRAM snapshot in one native call. It is optional.
The base Core package still installs without Rust or third-party dependencies.
Neither application imports the native extension directly.

From this experimental checkout, install and verify the native path with:

```bash
uv sync --extra dev --extra emulator --extra acceleration
POKESIM_CORE_DECODER=rust uv run --no-sync pytest
```

`POKESIM_CORE_DECODER=auto` is the default. It uses the native decoder when
installed and otherwise uses Python. Set it to `python` to compare with the
reference decoder or to `rust` to require the extension. Invalid modes, an
incompatible native API, and native decoder errors fail explicitly.

`pokesim_core.snapshot.read_fields(memory, move_data=None)` returns fresh
snapshot fields, including party dictionaries. It does not advance the emulator,
cache mutable state, read banked storage, or choose actions. Call it on the
emulator's owning thread between execution steps. `Memory.read_bytes(start, stop)`
returns detached bytes and avoids intermediate Python integer lists.

`Emulator.tick_read(frames, start, stop, render=True, sound=True)` is an
experimental combined advance and byte-collection API. It preserves pending
inputs, synchronous hooks, frame counts, and media refresh. Bytes are collected
after the final frame completes and are detached from later execution. Invalid
ranges fail before advancing. Older bindings fall back to separate operations.
This generic prototype does not embed game decoding in the emulator. PokeSim
does not select it automatically because its end-to-end benefit is still being
measured.

`pokesim_core.identity.pokemon_identity(trainer_id, dvs)` preserves existing
Pokémon signatures. A bounded cache stores only signatures of immutable integer
inputs. Applications retain their own matching and observation rules.

The native package needs a separate wheel when packaging a release. Local `uv`
source overrides are development conveniences and are not public dependencies.
No native package release has been published from this experiment.

## Previous published release

Python 3.11 or newer is required.

Install the published wheel directly from GitHub, without requiring Git:

```bash
pip install https://github.com/afk-sapien/pokesim-core/releases/download/v0.1.4/pokesim_core-0.1.4-py3-none-any.whl
```

For emulator support, select the optional extra:

```bash
pip install "pokesim-core[emulator] @ https://github.com/afk-sapien/pokesim-core/releases/download/v0.1.4/pokesim_core-0.1.4-py3-none-any.whl"
```

A Git source install is also supported:

```bash
pip install "pokesim-core @ git+https://github.com/afk-sapien/pokesim-core.git@v0.1.4"
```

Applications should pin the release wheel's SHA-256 from `SHA256SUMS` or pin a
full Git commit instead of following a moving branch. Releases are not published
to PyPI in v0.1.4. `pip install pokesim-core` is not the documented installation path.

## Decode without an emulator dependency

```python
from pokesim_core.gen1 import read_bag, read_party, read_progress
from pokesim_core.rom import inspect_rom

identity = inspect_rom("/path/to/pokemon-red.gb")
print(identity.game, identity.sha256, identity.verified)

# memory can be a PyBoy memory view or a synthetic bytearray in a test.
memory = bytearray(65536)
party = read_party(memory)
bag = read_bag(memory)
progress = read_progress(memory)
```

Decoders return numerical fields and read-only facts. Applications add local game
labels, user interfaces, validation, and derived state. `read_party` preserves
pending and incomplete party slots for callers to interpret. It never drops them
silently. `read_progress` does not award points or decide that the game is complete.

## Run an isolated emulator

```python
from pokesim_core.emulator import GameBoy
from pokesim_core.gen1 import read_party

with GameBoy("/path/to/pokemon-red.gb") as game:
    game.tick(1800)
    game.press("start")
    game.tick(8)
    game.release("start")
    game.tick(2)
    image_bytes = game.screenshot()
    state_bytes = game.save()
    party = read_party(game.memory)
```

Each instance uses fresh in-memory SRAM and never reads or writes save files next
to the ROM. Nothing advances until `tick` is called. There is no background loop,
autoplayer, navigation, recovery, or memory editing helper. The adapter accepts
verified English Red and Blue ROMs. Applications can narrow accepted games with
`allowed_games=("red",)`.

`GameBoy.load` restores a trusted state. The caller owns state provenance and
compatibility checks. The memory view and load method are trusted application
APIs. Do not expose them directly to an agent. This library is not a sandbox.

## Shared boundary

| Core owns | Applications own |
| --- | --- |
| ROM identification and validation | Supported-game policy and warnings |
| WRAM constants and numerical decoding | Labels, rendering, and derived app state |
| Progress flags and party/bag facts | Scoring, event confirmation, and completion rules |
| Explicit controller and frame operations | Agent tools, permissions, and budgets |
| Screenshot and state primitives | State manifests, recovery policy, and replay logs |

PokeSim retains application scheduling, adventures, trading transactions, saves,
and recovery. All machine operations use Core. The agent benchmark uses the
isolated `GameBoy` adapter through the same runtime. Both can adopt
future core releases deliberately, without changing existing experiments silently.

The library imports neither application and does not bundle a database, MCP
server, model SDK, provider key, ROM, generated game table, or game artwork.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv build
```

Tests use synthetic memory and a fake emulator. CI runs without ROMs, PyBoy,
model API keys, or paid services. Real cartridge smoke checks are performed
locally with user-supplied files and their artifacts are never committed.

See [API compatibility](docs/api.md), [release notes](CHANGELOG.md), and
[third-party notices](THIRD_PARTY_NOTICES.md).

## Read-only UI facts

Version 0.1.3 adds `pokesim_core.gen1_ui`: screen text and cursor decoding,
raw sprite positions, active battler data and banked owned-storage inspection.
These functions never advance emulation or write memory. They are not an
observation policy. Consumers must hide enemy internals, offscreen sprites and
unseen content before exposing facts to an agent. Unavailable storage banks
are marked unavailable rather than assumed empty.

## Shared controller and setup helpers

Version 0.1.4 consolidates observed name entry, restorative item use, party
switching, visible menu rows, bulk box reads and immutable decoding caches.
The apps still choose names, targets, routes and rewards. Core performs the
mechanical operations through a caller-owned controller adapter.

```python
from pokesim_core.controls import use_item, switch_pokemon
from pokesim_core.naming import enter_name

# port routes every input through your existing frame budget and action log.
use_item(port, item_id=16, party_slot=0)
switch_pokemon(port, party_slot=2)
enter_name(port, "SPARK")
```

Trusted setup tools can separately import `pokesim_core.resets` to reopen a
stationary encounter or clear a supplied event group. These are explicit memory
mutations with context checks and change receipts. They are never called by
controller helpers and must not be exposed to benchmark agents. See the
[API contracts](docs/api.md) for adapter requirements and supported operations.

## Local integration validation

The 2026-10-05 integration passed 711 Rust-package Python compatibility tests,
74 Core tests, and the benchmark suite. Real Red-to-Red cable trades passed in
both clock roles, including cartridge restart, checkpoint reload, movement,
and return-to-center checks. A cartridge export and benchmark pause/resume
checks also passed using private temporary fixtures. Blue pairings require a
separately supplied Blue ROM and fixture and are not established by this run.

The five-repeat, 4,800-frame gameplay comparison is recorded in
[the Core report](benchmarks/2026-10-05-core.json). All 90 runs matched final
hardware states and gameplay traces. Rendered runs also matched final pixels
and audio. Core throughput was within about 2% of direct Rust bindings across
these samples. With rendering and audio it delivered 39% to 64% more throughput
than compiled PyBoy. These are single-core emulator measurements, not full
agent throughput. The benchmark records hashes, not private ROM or state data.

## Experimental execution procedures

Bounded input sequences, verified input replay, complete execution checkpoints,
and opt-in native profiling are exposed through Core. See [EXECUTION.rst](EXECUTION.rst)
for API examples, ownership rules, replay limits and the profiling procedure.

## Experimental action and compatibility procedures

State-aware menu actions, intermediate replay diagnostics and the permanent
compatibility suite are described in [COMPATIBILITY.rst](COMPATIBILITY.rst).
The suite reports synthetic and private gameplay coverage separately.
