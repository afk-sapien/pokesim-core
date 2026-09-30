# Changelog

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
