# API compatibility

The Python import is `pokesim_core`. The distribution and repository are
`pokesim-core`. `__version__` identifies the package release and `API_VERSION`
identifies the major data contract. It is 1 in every 0.1.x release and in 0.2.0,
and changes only for an incompatible change to documented field shapes.

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

Real-time clock control on `Emulator` is additive: the `rtc_file` argument,
`stop(..., rtc_file=)`, `has_rtc`, `export_rtc`, `import_rtc`, `rtc_registers`,
`set_rtc_registers`, `rtc_state`, `set_rtc_timezero`, `lock_clock`, `unlock_clock`,
`advance_clock`, `clock_locked`, `clock_now` and the optional `rtc_clock` checkpoint
key; a locked clock exports its host-following value and a checkpoint without
clock data releases a lock. Semantics are in the README section "Real-time clock".

## Versioning and upgrades

Consumers pin a release artifact checksum or source commit. Do not replace a
published artifact in place. Patch releases preserve documented shapes and
behavior except clearly documented corrections. A changed observation or scoring
interpretation must be reflected in the consuming benchmark's own version.

Keep recorded core versions, artifact provenance, emulator versions, and scenario
hashes with experiments. Shared code fixes are available to both applications,
but neither automatically takes an unreviewed upstream update.

## DV probability reference

`pokesim_core.dvs.dv_probabilities(dvs)` accepts HP, Attack, Defense, Speed,
Special as a list or tuple. It returns `None` for missing, malformed, or
inconsistent HP data. Valid results contain `total`, `outcomes`, `at_least`,
`better`, `at_least_probability`, and `better_probability`.

The denominator is 65,536 equally weighted combinations of the four stored DVs.
HP is derived from their low bits, never sampled independently. `at_least`
includes ties, while `better` means a strictly higher five-DV total. Perfect
DVs have inclusive probability 1/65,536 and strictly better probability zero.
These are reference probabilities, not measured cartridge encounter odds or
species encounter rates. Game RNG timing can affect observed distributions.
Consumer applications own scoring, training priorities, and replacement rules.


## Controller helpers

`controls.ControllerPort` adapts a consumer's serialized controller. The consumer
supplies `memory`, `send(button, hold, gap)`, `choose(visible_label)`,
`observe()` and `frame()`. Optional callbacks are `stopped()` and
`continue_ready()`. `item_labels` maps string item IDs to cartridge menu labels.
`send` and `choose` return false when they cannot continue. They must enforce
frame budgets and record every input. No helper bypasses these callbacks.

`observe` returns `kind`, `text`, `cursor_tile`, `selected_text` and
`visible_choices` from the consumer's visible UI classifier. `kind` uses
`overworld`, `battle_menu`, `move_menu`, `menu`, `naming`, `dialogue`,
`transition` or an unsupported state. Continue readiness must only approve
continue-only dialogue, never a choice. The default waits without confirming.
`choose` selects only the supplied visible label and must also be bounded.

- `use_item(port, item_id, party_slot)` supports status cures, potions, revives
  and Elixers. It does not choose a target, use balls, teach moves or select PP
  targets. Missing items and invalid slots produce no input. Slots are zero based.
- `switch_pokemon(port, party_slot)` switches a battler or rearranges the field
  party lead. Fainted or already active battle targets are rejected.
- Both return `outcome` and, once validated, `shortcut` metadata. `completed`
  records the observed effect, even if the controller budget expires during
  cleanup. `item_consumed` reports a verified bag decrement, not a promise of
  a particular HP change. No unconfirmed effect is repeated automatically.
- `naming.name_step(rows, cursor, name, limit=10)` returns a `ButtonAction` or
  None outside the keyboard. It reads back partial text and corrects mismatches.
- `naming.enter_name(port, name, limit=10, max_actions=256)` drives a supplied
  uppercase ASCII name from an already open naming keyboard. Use limit 7 for
  player and rival names. It does not accept nickname prompts or pick names.
- `naming.menu_button(current, target)` returns one linear menu direction or A.
- `menus.menu_options(memory, screen, kind=None)` reads visible menu rows.
  Consumer observation filtering remains required.

Menu macros have a 200-iteration ceiling in addition to the consumer's frame
budget. They do not own threads, emulator lifecycle, logging, replay or locks.
Call them only with exclusive access to the emulator. All helpers support the
verified English Red/Blue layouts, not ROM hacks or other generations.

## Cached readers

`gen1_ui.read_screen(memory, raw_text=False)` preserves the 0.1.3 default glyph
semantics. `raw_text=True` preserves the original decoder's unknown glyphs for
PokeSim. Both use immutable glyph lookup tables. `screen_rows(raw, raw_text=False)`
accepts exactly 360 tile bytes.

`storage.memory_bytes(memory, bank, start, size)` uses bulk reads with a scalar
fallback. `storage.decode_box(structs, names)` returns frozen `BoxMon` records
with zero based positions and tuple fields. Its 128-entry cache is keyed only
by complete immutable bytes. It cannot go stale after a restore, trade or box
switch. No species validity policy is applied. `read_storage` retains its
existing dictionaries and list fields, returning fresh mutable values each call.

## Trusted resets

`resets` is deliberately separate from read-only facts and controller actions.
Never register these functions as benchmark agent commands. A fixture builder
may use them before a run, then record its setup and resulting initial-state
hash. Existing benchmark runs never import or call this module.

- `Flag(base, bit)` describes one WRAM flag and validates its address.
- `update_flags(memory, [(flag, bool), ...])` is the low-level trusted primitive.
  It preserves other bits, merges updates to one byte and preflights all reads.
  Conflicting assignments fail before writes. It returns immutable `Change`
  records containing address, before and after bytes. An unchanged update
  returns an empty tuple. Failed writes trigger verified rollback attempts.
- `reset_events(memory, flags, rooms=...)` clears a caller-defined group. It
  rejects loaded target rooms, battle, visible menus, dialogue and display
  transitions. Consumers must additionally ensure scripts are idle.
- `reset_encounter(memory, event=..., visibility=..., room=...)` clears the
  encounter event and object-hide bits together through `reset_events`.

Consumers supply verified event definitions for their cartridge. Core does not
ship generated game tables or guess reset flags. Callers must verify the ROM,
stop emulation or hold its exclusive lock, and retain reward eligibility and
claim history. These helpers do not refund items, heal, rewind a save or reset
unrelated story progress. A rollback failure is attached to the original
exception and requires the caller to stop using that state.
