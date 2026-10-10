# Changelog

## 0.7.0

### Added

- `advance_dialogue` (`AdvanceDialogue`) advances printed text on all six games and
  returns the whole conversation in `lines` and `text`. It presses A only when Core's
  text-wait check says the game waits to continue, and it stops at the first choice or
  menu (YES/NO, multiple choice, the battle menu) with `screen` and `choices`, or once the
  text box closes and the player has control again. It never answers a choice.
- `walk` (`Walk`) walks up to `tiles` tiles in one direction on all six games. A tap that
  only turns the player is followed by another. It stops early when the player cannot
  move, when a battle starts, when the map changes, or when text or a menu opens. The
  result gives `tiles_moved`, `start`, `end` and `facing`. There is no route finding.
- Every result's `shortcut` dict now has `stop_reason` and `can_continue`.
  `stop_reason` is one of `shortcuts.STOP_REASONS` (the `StopReason` enum): `completed`,
  `prompt`, `unsettled`, `refused`, `game_refused`, `no_effect`, `no_response`, `budget`,
  `stopped`, `choice`, `text_end`, `blocked`, `battle`, `map_change` or `dialogue`.
  `can_continue` says whether another command can start without inspecting the screen
  first. `Done` gained the matching `reason` field and properties.
- `shortcuts.describe(name=None, version=None)` describes every command as plain JSON
  data: its arguments as a JSON Schema object, the common options, the start
  preconditions (screens, and whether a battle is required or ruled out), the games it
  runs on and the result keys it adds. `shortcuts.result_schema()` describes the result
  dict every command returns. Which commands to offer stays the consumer's choice.

## 0.6.1

### Fixed

- `use_item` with a fishing rod waits on the overworld while the line is cast. Gen 2 closes
  the pack before "Not even a nibble!" or "Oh! A bite!" prints, so every rod used to stop with
  "returned without a confirmed effect". A cast that never prints a message still stops
  without a second cast.
- Waiting for an item's effect on the overworld no longer presses A there, where it could
  talk to someone or offer SURF.

## 0.6.0

### Added

- `change_box` (`ChangeBox`) switches the current box through Bill's PC on all six games
  and answers the save prompt.
- `learn_move` (`LearnMove`) answers a learn-a-new-move prompt on all six games: replace
  a move slot, or keep the old moves with `'keep'`. HMs and empty slots refuse.
- `delete_move` (`DeleteMove`) for the Gen 2 Move Deleter.
- A `nickname` option on every shortcut. `'no'` (the default) answers NO to a caught
  Pokemon's nickname prompt. `'caller'` stops there with `pending='nickname'`.
- `choose_move` handles a forced turn. With no PP left or a locked move, FIGHT starts
  the turn at once, and the result says `forced='struggle'` or `forced='locked'`.
- A thrown ball that catches reports `caught` in the result.

### Fixed

- Gen 2 FLY checks the Storm Badge, not the Mineral Badge.
- The Gen 2 party submenu is recognized when it scrolls, so party reorders, switches and
  field moves on a Pokemon with four field moves no longer stop with no effect.
- Gen 2 refusals for a move that can't be deleted or forgotten end the shortcut.
- A Gen 2 switch after a faint waits for the party screen under "Which PKMN?". It no
  longer presses B there and stops with "Menu did not respond".
- On Gen 2, an A press meant for text is dropped when a menu replaces the text before
  the press goes out, so it no longer opens FIGHT after a switch.
- The Gen 2 move menu is recognized while the cursor is on a disabled move, and
  `choose_move` refuses a disabled move before sending input.

## 0.5.0

### Added

- Menu shortcuts for Gold, Silver and Crystal. Every 0.4.0 action now runs on Gen 2:
  `use_item` (all kinds, with pocket switching and Berries), `choose_move`,
  `switch_pokemon` (also from the battle switch prompt), `run_away`, `reorder_party`,
  `use_field_move`, `toss_item`, `buy_item`, `sell_item`, `deposit_pokemon`,
  `withdraw_pokemon`, `release_pokemon` (still needs `allow_release=True`),
  `deposit_item` and `withdraw_item`.
- `give_item` and `take_item` (`GiveItem`, `TakeItem`) for Gen 2 held items. Replacing
  a held item needs `swap=True`.
- Gen 2 field moves WHIRLPOOL, WATERFALL, ROCKSMASH and HEADBUTT, with badge checks.
- Gen 2 item kinds and usage for every item ID, from pret pokecrystal and pokegold.
  Item names are decoded from the cartridge.
- `current_screen` names Gen 2 screens: the four pack pockets, party, item target,
  move list, quantity box, mart menu and list, the PC, Bill's PC menu and lists, the
  item PC, the battle menus, the switch prompt, YES/NO and text.

### Changed

- Gen 2 actions no longer refuse with "Not supported in Gen 2 yet".
- On Gen 2, `run` resolves menu choices itself and only calls `port.send`.
- The optional real cartridge shortcut tests release every button after loading a
  state and accept the battle switch prompt as rest.

## 0.4.0

### Added

- `pokesim_core.shortcuts`: resumable menu shortcuts for Red, Blue and Yellow. Each is a
  machine with `step(memory, ui)` that returns one button, a wait or a final `Done`, and
  never writes memory. `run(port, machine)` and `drive(machine, emulator)` are the
  blocking wrappers.
- Actions: `use_item` for every item kind, `choose_move`, `switch_pokemon`, `run_away`,
  `reorder_party`, `use_field_move` (CUT, SURF, STRENGTH, FLASH, FLY to a named town),
  `toss_item`, `buy_item`, `sell_item`, `deposit_pokemon`, `withdraw_pokemon`,
  `release_pokemon` (needs `allow_release=True`), `deposit_item` and `withdraw_item`.
- Queries: `list_items`, `list_party`, `list_moves`, `list_box` and `current_screen`.
- `ControllerPort.version` selects the game. Gen 2 actions refuse before any input.
- Optional real cartridge shortcut tests read save states and a manifest from
  `POKESIM_CORE_SHORTCUT_STATES`. None ship with Core.

### Changed

- `controls.use_item(port, item, target=None, move=None)` covers every item kind. The
  0.3 keywords `item_id` and `party_slot` still work. `controls.switch_pokemon` runs the
  new machine.

### Fixed

- Shortcuts no longer stop on a text screen after the effect. In battle, "recovered by"
  and the foe's turn are pressed through until the battle menu, the move menu, a forced
  switch or the end of the battle. If the screen never settles within the budget the
  result says `completed` and not `settled`.

## 0.3.0

Distributed as GitHub release files: the wheel `pokesim_core-0.3.0-py3-none-any.whl`,
the sdist `pokesim_core-0.3.0.tar.gz` and `SHA256SUMS.txt`. Not on PyPI.

0.2.0 was never tagged or released. 0.3.0 is the first release with the PyBoy RS
backend, so everything listed under 0.2.0 below ships for the first time here. The
`emulator` extra requires `pyboy-rs>=0.1.1,<0.2`; install the
[pyboy-rs v0.1.1](https://github.com/afk-sapien/pyboy-rs/releases/tag/v0.1.1) release wheel.

### Added

- `pokesim_core.cartridges`: a registry of the six clean English cartridges PokeSim plays
  (Red, Blue, Yellow, Gold, Silver, Crystal) with `identify`, `identify_sha1`, `identify_file`,
  `by_version`, `generation`, ZIP `unpack`, header decoding with both checksums (`read_header`),
  refusal reasons (Crystal Rev 0 and the Australian Crystal are refused) and the slot shelf.
- Yellow: `pokesim_core.yellow` with `red_layout` (a Red-layout view of raw Yellow memory),
  `read_pikachu` (happiness, mood, follow, surf and starter flags, `starter_slot`) and
  `YellowEmulator`, a Core `Emulator` whose `memory` uses Red addresses. `open_emulator(rom)`
  picks it for Yellow. `gen1.read_party`, `read_bag`, `read_progress`, `read_starters`,
  `read_trainers`, `gen1_ui.read_battler` and `read_storage` take `version=`.
  `read_starters` reports Yellow's rival evolution.
- `pokesim_core.gen1_battle_power`: PokeSim's Gen I battle power estimates (`BattlePower`,
  `calculated_stat(s)`, `stored_strength`, `stat_exp_bonus`, `dv_rating`) from the caller's
  game tables. `dvs` adds `is_perfect`, `is_shiny` and `shiny_bytes`.
- Trades and the Time Capsule: `gen1_link_metadata` gains the Yellow build,
  `gen2_link_metadata` covers Gold, Silver and Crystal, `timecapsule` converts between
  generations and checks compatibility, and `trade` verifies Gen I and Gen II trades with
  PokeSim's error messages. All pure and read-only.
- `pokesim_core.gen2`: read-only Gold, Silver and Crystal decoding moved from PokeSim with identical output. It has per-version memory maps and charmaps, party and PC boxes (DVs, shiny, held item, friendship, Pokerus, Crystal caught data), bag, pockets and PC items, Pokedex seen, caught and Unown forms, money and Johto and Kanto badges, player and map state, the game clock and RTC base, the Day Care and eggs, and roamers. The full `read_snapshot` takes consumer game tables. Core ships no game tables.
- Gen II `battle_power` and `hidden_power`, Day Care rules (`offspring`, `retrieval_cost`, `branch_parents`) and evolution-line credit (`ancestors`, `level_credit`).
- `pokesim_core.memory_snapshot.snapshot_emulator`: a per-step memory snapshot for any Core emulator class. It reads whole banks with `read_bank_bytes` (with a per-byte fallback for older `pyboy-rs`), serves unbanked Gen I reads from one WRAM copy and is invalidated by ticks, writes, loads and restores.
- `Memory.read_bank_bytes(bank, start, stop)` on the Core emulator.
- `gen2.version_of(rom_bytes)` identifies a Gen II ROM through `cartridges.identify`.
- Decoded Gen II regions are cached by their raw bytes and game tables.
- Optional cartridge tests run when `POKESIM_CORE_GEN2_ROMS` names a local ROM directory.
- `rom.require_rom` accepts any registered version named in `allowed_games`.
- The release also attaches the sdist and a `SHA256SUMS.txt`, and the notes come from this file.

### Changed

- `storage.memory_bytes` uses a snapshot window when the memory offers one. Results are unchanged.
- CI installs the released `pyboy-rs` v0.1.1 wheel (pinned by SHA-256) instead of building a commit, and requires the `bank_bytes` feature.
- The package description now covers all six games. `inspect_rom` and `KNOWN_ROM_SHA1`
  still describe only Red and Blue, as in 0.1.x.

### Compatibility

- All additions are new modules or keyword arguments with Red and Blue defaults. The
  0.1.x pure-Python surface is unchanged. `API_VERSION` stays 1.

## 0.2.0

Never tagged or released on its own. These changes first ship in 0.3.0.

### Added

- Native emulator interface: `Emulator` and `GameBoy` run on the Rust `pyboy-rs` backend. Install it with the `emulator` extra, which pins `pyboy-rs>=0.1.1,<0.2`.
- RTC support: PyBoy 2.7.0 compatible RTC file import and export, explicit clock register access and a deterministic lockable clock. Capability is detected from the `pyboy-rs` clock control flag.
- `CoreCapabilityError`, a `RuntimeError` subclass, raised when the installed backend lacks a needed capability. It does not subclass `NotImplementedError`, so existing `except NotImplementedError` handlers will not swallow it.
- Checkpoints of RTC cartridges store the clock lock in `rtc_clock` beside the state. A locked checkpoint refuses to load on a backend without the equivalent lock.

### Changed

- Checkpoint restore compares the runtime version and state format by default. The old binary sha256 comparison is available as the opt-in `exact` mode.
- Checkpoints and `retag_checkpoint` output keep `pyboy_version: "2.7.0"` when that is truthful, so PokeSim 0.4.x can still load them.
- The README test count and `API_VERSION` documentation are corrected. `press()` is documented as waiting for the tick.
- Backend change for 0.1.x users of `GameBoy` and the `emulator` extra: the backend is now `pyboy_rs`, not `PyBoy`. Code that monkeypatches a fake `pyboy` module must patch `pyboy_rs` instead. Eight tests in the 0.1.4 `test_emulator.py` do exactly this and fail by design against 0.2.0 without `pyboy-rs`.

### Fixed

- `Emulator.checkpoint()` now includes `pyboy_version: "2.7.0"` like `checkpoint_metadata()` and `retag_checkpoint()` do, so PokeSim 0.4.x accepts a Core checkpoint on rollback. The tag is still omitted for locked-clock checkpoints and any state PyBoy 2.7.0 cannot load.

- `export_rtc()` and `stop(rtc_file=)` while the clock is locked write the host-following equivalent instead of the fake locked base (which read as about +1057 days elsewhere). Requires `pyboy-rs` with `rtc_export_follows_host`.
- `restore_checkpoint` on a cartridge with a clock always applies the checkpoint's lock, and a checkpoint with no clock data releases any lock instead of keeping it.
- A checkpoint restores on a rebuilt or other-OS `pyboy-rs` wheel of the same version, as the README says. The backend rejected it before; it now checks state format and cartridge.
- Release workflow: refuses to modify a published release, actions are pinned by commit, and the wheel is attached with a `SHA256SUMS` asset whose hashes are also in the job summary.

### Removed

- The unpublished `acceleration` extra is gone from the published metadata. The native crate stays in the repository and builds from source, see the README.

### Compatibility

- The pure-Python 0.1.x surface (names, signatures and behavior outside the emulator) is unchanged and passes without `pyboy-rs` installed.
- Published 0.1.x wheels are untouched. Consumers pinned by hash to a 0.1.x wheel are unaffected.
- CI builds `pyboy-rs` from a pinned commit and runs the emulator and RTC suites. A separate job builds the native decoder.

## 0.1.4

- Consolidate bounded restorative item use and party switching through caller-owned controllers.
- Add resumable name entry and visible menu readers, keeping name and gameplay choices in consumers.
- Share cached screen glyphs and immutable bulk storage decoding without changing existing reader shapes.
- Add a separate trusted reset API for encounter and event groups, with preflight validation, context checks, change receipts and rollback on write failure.
- Keep benchmark observations, frame budgets, logs, reward timing and simulation strategy in their applications.

## 0.1.3

- Add read-only screen, sprite, battler and owned-storage readers.

## 0.1.2

- Add validated DV-total tail probabilities using all 65,536 stored DV combinations
  with derived HP. Expose inclusive and strictly better counts and probabilities
  under an explicitly uniform reference model. No gameplay policy is included.


## 0.1.1

- Correct the project name to PokeSim Core, the distribution to `pokesim-core`, and the import to `pokesim_core`.
- No changes to game decoding or emulator behavior.

## 0.1.0

- Initial shared core release, published under the incorrect project name.
