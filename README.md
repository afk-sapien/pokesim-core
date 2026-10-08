# PokeSim Core

Shared Pokemon Red, Blue, Yellow, Gold, Silver and Crystal primitives for
simulation and agent research.

The package extracts low-level functionality used by PokeSim and a separate
agent benchmark. The base install uses only Python's standard library. The
optional emulator extra supplies the Rust-backed Core emulator interface.

## Install (0.3.0)

Python 3.11 or newer is required. Core and PyBoy RS are distributed as GitHub
release files, not on PyPI. Install the PyBoy RS wheel for your platform from the
[v0.1.1 release](https://github.com/afk-sapien/pyboy-rs/releases/tag/v0.1.1), then Core:

```bash
pip install https://github.com/afk-sapien/pyboy-rs/releases/download/v0.1.1/pyboy_rs-0.1.1-cp311-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
pip install "pokesim-core[emulator] @ https://github.com/afk-sapien/pokesim-core/releases/download/v0.3.0/pokesim_core-0.3.0-py3-none-any.whl"
```

Each release has a `SHA256SUMS.txt` asset. Applications should pin the files by
SHA-256 (`url#sha256=...`) instead of following a moving branch.

## Rust emulator interface

Since `0.2.0`, Core uses PyBoy RS as its only emulator backend. Both applications
import Core and only Core imports the native Python package. The `emulator`
extra requires `pyboy-rs>=0.1.1,<0.2` and Pillow. Core 0.1.x keeps its PyBoy 2.7.0
backend and its published wheels are unchanged. The pure Python surface that 0.1.x
exposed imports and behaves the same without any emulator installed.

For development, install the released PyBoy RS wheel as above, or build it from
the `afk-sapien/pyboy-rs` repository with `maturin build --release` and install
the wheel. Do not use `maturin develop`, which installs an editable build into
the active environment. Then run the tests:

```bash
pip install -e ".[dev]" pillow numpy
pip install /path/to/pyboy_rs-0.1.1-*.whl
pytest
ruff check .
```

`Emulator` owns isolated machine operations, memory and register wrappers,
RGBA output, signed 8-bit stereo audio, hooks, and explicit cartridge export.
It has no application thread, automatic file writes, or agent policy.
`GameBoy` adds verified Red/Blue ROM selection for the benchmark. Core memory
writes and hooks are trusted host APIs. Applications decide which observations
and actions their agents can access.

`press` and `release` queue the input. It reaches the machine at the start of the
next `tick`, so a raw `save()` between `press` and `tick` does not contain the press.
`checkpoint()` stores the queue as `pending_inputs` and `restore_checkpoint` restores it.

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
checkpoints. Ordinary imports can accept PyBoy 2.7.0 format-15 saves. New
manifests identify PyBoy RS explicitly, including the version, state format and
the native extension and binding hashes. Trade outputs retain an explicit
source-to-output runtime migration record.

`restore_checkpoint(checkpoint, match="version")` compares the backend, its
version and the state format. A wheel rebuilt in CI or built for another
operating system restores earlier checkpoints of the same version. Pass
`match="exact"` to also require the identical compiled binary and binding hashes,
or `match="state_format"` to accept any version of the same backend and format.

`Emulator.checkpoint()`, `checkpoint_metadata()` and `retag_checkpoint()` keep
`pyboy_version: "2.7.0"` beside the `emulator` record. The tag is present exactly when
PyBoy 2.7.0 could load the saved state: a PyBoy 2.7.0 format-15 raw state with no clock lock
carried. A downgrade to a PokeSim release that requires the field (0.4.x) refuses
a checkpoint without it. The tag is omitted when the source lineage is not 2.7.0, when the state
format differs, and for checkpoints saved with a locked clock, which PyBoy 2.7.0 cannot
reproduce, so 0.4.x refuses those by design.

`gen1_cable.CableEndpoint` owns the verified ROM-hook transport, queues,
register parking, and hook cleanup. Applications own participants, navigation,
time budgets, persistence, and transaction adoption. This mechanism is an
explicit Gen1 virtual cable implemented with verified ROM hooks.

The optional native tests use the redistributable demo. Private gameplay and
trade checks use temporary copies and never enter package artifacts. Upstream
PyBoy is used only as a development oracle in emulator tests and the timing
harness in `tools/benchmark_emulator.py`.

## Real-time clock

MBC3 cartridges with a clock (Gold, Silver, Crystal) need clock control, which requires a PyBoy RS build with RTC support. Core detects clock control from the build's `has_rtc` flag when it
publishes one, and otherwise from the presence of the clock methods. Builds without it
raise `CoreCapabilityError` from these methods, passing `rtc_file` or `stop(rtc_file=)`, and
restoring a checkpoint saved with a locked clock. Everything else keeps working. Test
`clock_control_available` first to avoid the error. `CoreCapabilityError` subclasses
`RuntimeError` only, so a broad `except NotImplementedError` does not hide it.

- `Emulator(rom, rtc_file=bytes_or_stream)` loads a PyBoy 2.7.0 `.rtc` file: ten
  bytes holding a little-endian float64 base timestamp (`timezero`), a halt byte and
  a day carry byte. Core copies the input, so the stream is never written later.
  Trailing bytes are ignored. Short input, NaN and flags above 1 raise `ValueError`.
  The argument is ignored on cartridges without a clock, like PyBoy.
- `stop(save=False, ram_file=None, rtc_file=None)` writes the ten bytes to
  `rtc_file` (replacing its contents) and the SRAM to `ram_file`. Nothing is written
  otherwise. `export_rtc()` and `import_rtc(data)` do the same on a running machine.
  Latched registers are not part of the file. While the clock is locked, the export
  is the host-following equivalent (the file that reads as the locked clock's current
  time on the host clock), never the fake base, so a real cartridge or an unlocked
  emulator does not read about three years off. Needs `pyboy-rs` with the
  `rtc_export_follows_host` feature.
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
cartridge with a clock always adds `rtc_clock`, the exact lock fields or `None`
(also available as `clock_lock_state()`), and `restore_checkpoint` applies it, which
is what an exact resume needs. A locked checkpoint written by a different backend
version, accepted only with `match="state_format"`, is refused unless this machine
already has the identical lock applied, because the raw state cannot carry it. A
checkpoint with no clock data (no key, or `None`) releases any lock the emulator had,
without shifting the clock, whatever the emulator did before. Checkpoints of other cartridges
are unchanged. Execution recording and replay work with a locked clock and reject a live one.
Checkpoints restore on a rebuilt or repackaged `pyboy-rs` wheel of the same version: the backend
checks the state format and the cartridge, not the build; `match="exact"` is the strict mode.

## Experimental Core acceleration

The separate `pokesim-core-native` distribution in `native/` uses PyO3 and
Maturin to decode a complete WRAM snapshot in one native call. It is optional.
The base Core package still installs without Rust or third-party dependencies.
Neither application imports the native extension directly.

The decoder is not part of the `pokesim-core` metadata, because the
`pokesim-core-native` distribution is unpublished. It builds from `native/` in
this repository and Core uses it automatically when it is installed. To build and
verify it from a source checkout:

```bash
maturin build --release --manifest-path native/Cargo.toml --out dist
pip install dist/pokesim_core_native-*.whl
POKESIM_CORE_DECODER=rust pytest
```

Continuous integration builds and tests this crate in its own job.

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

The native package needs a separate wheel when packaging a release. No native
package release has been published.

## Previous published release (0.1.4)

The 0.1.x line uses PyBoy 2.7.0. Its last release is still installable:

```bash
pip install "pokesim-core[emulator] @ https://github.com/afk-sapien/pokesim-core/releases/download/v0.1.4/pokesim_core-0.1.4-py3-none-any.whl"
```

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

## Cartridges, Yellow, battle power and trades

```python
from pokesim_core import cartridges, gen1, yellow
from pokesim_core.gen1_battle_power import BattlePower
from pokesim_core import timecapsule

cartridge = cartridges.identify(rom_bytes)          # any of the six games, or None
party = gen1.read_party(memory, version=cartridge.version)
pikachu = yellow.read_pikachu(memory)               # raw Yellow memory
power = BattlePower(species, moves, matchups).battle_power(mon)
allowed = timecapsule.compatible(dex, moves, held_item)
```

Core ships no game tables. Battle power and the Time Capsule conversion take the
caller's species, move and type tables and return what PokeSim returns. See
`docs/api.md` for every name.

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

## Gold, Silver and Crystal

`pokesim_core.gen2` decodes Gen II memory read-only. It ships the per-version
memory map (`gen2.memory_map.symbols(version)`, from the pinned pret symbol
files, with Crystal's moved WRAM and the Crystal-only symbols in `CRYSTAL_ONLY`)
and the English character maps (`gen2.charmap.charmap(version)`).
`gen2.version_of(rom_bytes)` names the version through `cartridges.identify`. It ships no
species, move, item or map tables.

Table-free readers need only a version name and any memory that supports banked
reads `memory[bank, start:stop]`:

```python
from pokesim_core.gen2 import state

party = state.read_party_structs(memory, "crystal")  # DVs, shiny, held item, friendship, Pokerus, caught data
boxes = state.read_box_structs(memory, "crystal", box=0)  # one PC box, eggs included
counts, active = state.read_box_counts(memory, "crystal")
items = state.read_items(memory, "crystal")  # items, balls, key, pc and the TM/HM quantities
player = state.read_player(memory, "crystal")  # name, ID, map, position, Johto and Kanto badges, money
dex = state.read_pokedex(memory, "crystal")  # seen, caught and Unown forms
clock = state.read_clock(memory, "crystal")  # day, weekday, time of day, RTC start and DST
daycare = state.read_daycare(memory, "crystal")  # parents, egg flags, steps to egg and the egg
roamers = state.read_roamers(memory, "crystal")
```

`gen2.read_snapshot(memory, data, frame=0, *, cache=True)` returns the full
`Snapshot` PokeSim observes, with `Mon` objects, pockets, objects and screen
text. `data` is the consumer's game tables: `gen2.GameTables(raw)` builds them
from a JSON mapping, and any object with the same attributes works. Symbols and
the charmap default to Core's own. With `cache=True`, decoded regions (party,
each box, Pokedex, Day Care, screen) are reused while their bytes and `data`
are unchanged. `gen2.clear_region_cache()` drops them.

Also in `pokesim_core.gen2`:

- `battle_power(mon, data)` and `hidden_power(data, dvs)` rate a decoded Pokemon from the game tables.
- `offspring`, `retrieval_cost`, `branch_parents`, `ancestors` and `level_credit` apply the Day Care and evolution-line rules.
- `live_status(game, collection, *, data=None)` builds the shared adventure status payload.
- `ScreenText`, `has_word`, `mask_hud`, `mask_roster` and `is_roster` match whole words in screen text.
- `decode_mon`, `individual`, `calculated_stats`, `experience_at`, `experience_progress`, `dex_flags` and `decode_text` are the building blocks.

Output is identical, field for field and in `repr`, to PokeSim's `pokesim.gen2`
modules these were moved from.

## Per-step memory snapshot

```python
from pokesim_core.emulator import Emulator
from pokesim_core.memory_snapshot import snapshot_emulator

game = snapshot_emulator(Emulator)("/path/to/crystal.gbc", sound_emulated=False)
```

The returned class has the same constructor and API. Between two steps its
`memory` serves reads from a lazy copy:

- Banked WRAM and cartridge RAM reads come from one `read_bank_bytes` call per
  bank. PyBoy RS 0.1.1 serves it natively. Older bindings fall back to per-byte
  bank reads with identical values. `memory.snapshot_window(bank, address, size)`
  returns the cached bytes or None, and the Gen II readers and
  `storage.memory_bytes` use it automatically.
- Unbanked reads inside `0xC000-0xDFFF` (`memory[address]`, `memory[start:stop]`
  and `memory.read_bytes`) come from one copy of that range. The Gen I readers and
  `snapshot.read_fields` therefore use it unchanged.

Every tick, memory write, state load, checkpoint restore, input and every other
method outside `memory_snapshot.READ_ONLY` invalidates the copy. Reads made
during a call, for example from a hook, always go to the live machine. On a
Crystal save a full `gen2.read_snapshot` falls from about 0.67 ms on live memory
to about 0.13 ms with the snapshot and region cache.

`Emulator.memory.read_bank_bytes(bank, start, stop)` is also available on the
plain emulator.

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
the Core suite, and the benchmark suite. Real Red-to-Red cable trades passed in
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
