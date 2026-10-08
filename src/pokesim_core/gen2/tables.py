"""Game tables the Gen II decoders read, supplied by the consumer.

Core ships no species, move, item or map tables. A consumer builds them (PokeSim
generates them from pinned pret sources) and passes them as ``data``. Decoders only
read these attributes, so any object with the same shape works:

- ``game``: 'gold', 'silver' or 'crystal'
- ``symbols``: name -> (bank, address). Defaults to Core's memory map for ``game``.
- ``charmap``: byte -> text. Defaults to Core's English charmap for ``game``.
- ``species``: id -> {'name', 'stats' (6 base stats), 'types', 'gender_ratio', 'growth',
  'egg_groups', 'evolutions'}
- ``moves``: id -> {'name', 'type', 'pp', 'power', 'accuracy', 'effect', 'constant'}
- ``items``: constant name -> id (TM01..TM50 and HM01..HM07 are read for the TM pocket)
- ``item_names``: id -> display name
- ``types``: constant name -> id, ``type_names``: id -> display name
- ``matchups``: (attack type, defending type) -> factor
- ``maps``: map id (group * 256 + number) -> {'name', 'objects'}
- ``events``: event constant -> flag index
"""
from __future__ import annotations

from .charmap import charmap as default_charmap
from .memory_map import symbols as default_symbols


def pretty(name):
    return name.replace('_', ' ').title().replace('Pokemon', 'Pokémon').replace('Pokecenter', 'Pokémon Center')


class GameTables:
    """Game tables from a JSON-shaped mapping, with the same attributes as PokeSim's GameData."""

    def __init__(self, raw):
        self.raw = raw
        self.game = raw['game']
        for name in ('species', 'moves', 'maps', 'item_attributes'):
            setattr(self, name, {int(key): value for key, value in raw.get(name, {}).items()})
        charmap = raw.get('charmap')
        self.charmap = ({int(key): value for key, value in charmap.items()} if charmap is not None
                        else dict(default_charmap(self.game)))
        for name in ('items', 'types', 'events', 'map_ids', 'collisions', 'permissions'):
            setattr(self, name, raw.get(name, {} if name != 'permissions' else []))
        symbols = raw.get('symbols')
        self.symbols = symbols if symbols is not None else dict(default_symbols(self.game))
        self.item_names = {int(key): value.title() for key, value in raw.get('item_names', {}).items()}
        for name, value in self.items.items():
            if name not in {'NO_ITEM', 'NUM_ITEMS', 'NUM_TMS', 'NUM_HMS'} and not name.startswith(('TM_', 'HM_')):
                self.item_names.setdefault(value, pretty(name))
        self.matchups = {(a, b): factor for a, b, factor in raw.get('matchups', [])}
        self.encounters = raw.get('encounters', [])
        self.fly_points = raw.get('fly_points', [])
        self.type_names = {value: pretty(name.removesuffix('_TYPE')) for name, value in self.types.items()}

    def text(self, raw):
        return ''.join(self.charmap.get(value, '') for value in bytes(raw).split(bytes([0x50]), 1)[0]).strip()


def decode_text(raw, version='crystal'):
    """Decode an English Gen II string up to its terminator, as GameTables.text does."""
    table = default_charmap(version)
    return ''.join(table.get(value, '') for value in bytes(raw).split(bytes([0x50]), 1)[0]).strip()
