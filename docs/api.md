# API compatibility

The Python import is `pokisim_core`. The distribution and repository are
`pokisim-core`. `__version__` identifies the package release and `API_VERSION`
identifies the major data contract, initially 1.

## ROM module

`inspect_rom(path)` returns frozen `RomInfo` fields `sha1`, `sha256`, `game`,
`name`, and `verified`. It describes unknown ROMs without accepting them.
`require_rom(path, allowed_games=...)` rejects unknown or excluded games.
SHA-1 values identify known cartridges for compatibility. SHA-256 identifies
artifacts in reproducibility manifests. No ROM file is modified.

## Generation I module

`gen1` supports the verified USA/Europe English Red and Blue layouts. It accepts
any memory object supporting integer and slice reads. It does not depend on
PyBoy, a live process, application globals, a filesystem data directory, or labels.

- `decode_text(data)` handles the original cartridge alphabet, termination,
  gender symbols, and unknown glyphs using PokeSim's established behavior.
- `bcd(data)` decodes packed BCD bytes using the original permissive behavior.
- `flag_bits(data)` returns one-based set-bit indices for Pokédex arrays.
- `event_set(flags, index)` uses zero-based event indices and validates bounds.
- `individual_data(struct)` returns moves, trainer ID, experience, DVs, and stat experience.
- `read_party(memory, move_data=None)` returns dicts matching the numerical fields
  of PokeSim's PartyMon. Optional integer-keyed move data provides base PP values.
- `read_bag(memory)` returns a tuple of item ID and quantity pairs.
- `read_progress(memory)` returns the following raw facts.

| Field | Meaning |
| --- | --- |
| `valid` | Lightweight party species/level sanity check |
| `badges` | Badge bitmask |
| `gym_flags` | Gym victory flags in badge order |
| `elite` | Named Elite Four trainer victory flags |
| `champion` | Champion rival victory flag |
| `hall_of_fame` | Cartridge Hall of Fame registration counter |
| `map_id` | Current map identifier |
| `story` | Starter, Pokédex, Silph Co., and Surf event flags |

The `valid` field is not comprehensive validation. RAM can be partly written
during transitions, and Elite Four flags can reset after a League journey.
Applications own confirmation across frames, historical tracking, unique awards,
and completion criteria. The core makes no claim that a trainer battle ending
proves victory. Core progress facts do not include hidden opponent statistics.

Party dict keys are `species`, `hp`, `max_hp`, `level`, `nick`, `status`, `types`,
`moves`, `pp`, `attack`, `defense`, `speed`, `special`, `experience`, `max_pp`,
`dvs`, `stat_exp`, and `trainer_id`. Pending counted slots remain present.
Box data uses `individual_data` but box enumeration remains application-owned.

## Emulator module

Importing the module is safe without the emulator extra. Constructing `GameBoy`
requires it. The adapter pins PyBoy 2.7.0 for save-state stability. `tick` advances
only a positive integer number of frames. `press` and `release` accept the eight
Game Boy buttons. Screenshots are native 160 by 144 PNG bytes. `save` and `load`
use opaque PyBoy state bytes. `close` is idempotent and never writes SRAM to disk.

The wrapper has no threads, wall clock, notebook, budget, or automatic actions.
Methods are not internally synchronized. The application must serialize access.
PyBoy construction reads the supplied ROM path and uses independent in-memory SRAM.

## Versioning and upgrades

Consumers pin a release artifact checksum or source commit. Do not replace a
published artifact in place. Patch releases preserve documented shapes and
behavior except clearly documented corrections. A changed observation or scoring
interpretation must be reflected in the consuming benchmark's own version.

Keep recorded core versions, artifact provenance, emulator versions, and scenario
hashes with experiments. Shared code fixes are available to both applications,
but neither automatically takes an unreviewed upstream update.
