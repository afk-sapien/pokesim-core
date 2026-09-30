# PokeSim Core

Shared Pokemon Red and Blue primitives for simulation and agent research.

The package extracts low-level functionality used by PokeSim and a separate
agent benchmark. The base install uses only Python's standard library. The
optional emulator extra supplies a controller-driven PyBoy adapter.

## Install

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

PokeSim retains its own emulator lifecycle because it manages existing adventures,
trading, saves, and recovery. It shares the decoder and ROM identity primitives.
The agent benchmark also uses the isolated `GameBoy` adapter. Both can adopt
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
