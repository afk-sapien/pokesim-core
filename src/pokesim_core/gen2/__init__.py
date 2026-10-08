"""Read-only Gold, Silver and Crystal decoding.

Core ships the per-version memory maps and character maps. Species, move, item and map
tables stay with the consumer and are passed in as ``data`` (a :class:`GameTables` or any
object of the same shape). The submodules ``memory_map`` and ``charmap`` hold the
per-version tables (``memory_map.symbols(version)`` and ``charmap.charmap(version)``). The table-free readers in :mod:`pokesim_core.gen2.state` need
only a version name.
"""
from .battle_power import battle_power, hidden_power
from .breeding import ancestors, branch_parents, level_credit, offspring, retrieval_cost
from .memory_map import CRYSTAL_ONLY, VERSIONS, symbols
from .ram import (BADGES, STAT_NAMES, Mon, Snapshot, calculated_stats, clear_region_cache, decode_mon, dex_flags,
                  experience_at, experience_progress, individual, read_snapshot, tile_rows)
from .screens import ScreenText, has_word, is_roster, mask_hud, mask_roster
from .state import (caught_data, decode_struct, memory_reader, pokerus, read_box_counts, read_box_structs, read_clock,
                    read_daycare, read_items, read_party_structs, read_player, read_pokedex, read_roamers)
from .status import DEFAULT_VERSION, live_status
from .tables import GameTables, decode_text, pretty

__all__ = [
    'BADGES', 'CRYSTAL_ONLY', 'DEFAULT_VERSION', 'STAT_NAMES', 'VERSIONS', 'GameTables', 'Mon', 'ScreenText',
    'Snapshot', 'ancestors', 'battle_power', 'branch_parents', 'calculated_stats', 'caught_data',
    'clear_region_cache', 'decode_mon', 'decode_struct', 'decode_text', 'dex_flags', 'experience_at',
    'experience_progress', 'has_word', 'hidden_power', 'individual', 'is_roster', 'level_credit', 'live_status',
    'mask_hud', 'mask_roster', 'memory_reader', 'offspring', 'pokerus', 'pretty', 'read_box_counts',
    'read_box_structs', 'read_clock', 'read_daycare', 'read_items', 'read_party_structs', 'read_player',
    'read_pokedex', 'read_roamers', 'read_snapshot', 'retrieval_cost', 'symbols', 'tile_rows',
]
