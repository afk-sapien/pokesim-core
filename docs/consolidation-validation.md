# Core consolidation validation

Validated on September 30, 2026 with Core 0.1.4 and isolated local consumer adapters.

| Check | Result |
| --- | --- |
| Core synthetic tests | 67 passed |
| Core lint | Passed |
| Benchmark full regression suite | 282 passed, 2 skipped |
| Real cartridge controller cases | 15 passed |

The cartridge checks cover field and battle Full Restore, Revive, Elixer,
party selection from multiple starting menus, and the battle switch prompt.
Every completed case verifies the requested effect and an exact controller
replay. Repeating an operation ID sends no additional input. A 50-frame
cutoff stops without consuming an item. These checks use private retained
fixtures with no model calls, memory patches or live-server save changes.
No cartridge files, screenshots or private run records are included here.

Synthetic reset tests cover unloaded-room guards, battle and dialogue rejection,
unrelated-bit preservation, idempotence, merged writes, preflight errors and
rollback after an injected write failure. Existing PokeSim tests exercise
legendary, gift, fossil and trade scheduling through the shared mutation primitive.
The generic event-reset API needs caller-supplied verified event definitions.
This release does not claim every possible story event can safely be reset.

Reader tests check all 256 glyph values, unchanged public storage shapes,
immutable cache results, byte-based invalidation and scalar memory fallbacks.
The benchmark retains its observation allowlists, prompts, action budgets,
operation IDs and scoring. No reset capability is exposed to benchmark agents.
