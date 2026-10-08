# Changelog

## Unreleased

### Added

- `pokesim_core.gen2`: read-only Gold, Silver and Crystal decoding moved from PokeSim with identical output. It has per-version memory maps and charmaps, party and PC boxes (DVs, shiny, held item, friendship, Pokerus, Crystal caught data), bag, pockets and PC items, Pokedex seen, caught and Unown forms, money and Johto and Kanto badges, player and map state, the game clock and RTC base, the Day Care and eggs, and roamers. The full `read_snapshot` takes consumer game tables. Core ships no game tables.
- Gen II `battle_power` and `hidden_power`, Day Care rules (`offspring`, `retrieval_cost`, `branch_parents`) and evolution-line credit (`ancestors`, `level_credit`).
- `pokesim_core.memory_snapshot.snapshot_emulator`: a per-step memory snapshot for any Core emulator class. It reads whole banks with `read_bank_bytes` (with a per-byte fallback for older `pyboy-rs`), serves unbanked Gen I reads from one WRAM copy and is invalidated by ticks, writes, loads and restores.
- `Memory.read_bank_bytes(bank, start, stop)` on the Core emulator.
- `gen2.version_of(rom_bytes)` identifies a Gen II ROM through `cartridges.identify`.
- Decoded Gen II regions are cached by their raw bytes and game tables.
- Optional cartridge tests run when `POKESIM_CORE_GEN2_ROMS` names a local ROM directory.

### Changed

- `storage.memory_bytes` uses a snapshot window when the memory offers one. Results are unchanged.
- CI builds `pyboy-rs` from a commit with `read_bank_bytes` and requires the `bank_bytes` feature.

## 0.2.0

Distributed as the GitHub release wheel `pokesim_core-0.2.0-py3-none-any.whl`, built and attached by the `Release` workflow on a `v*` tag. Not on PyPI.

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
