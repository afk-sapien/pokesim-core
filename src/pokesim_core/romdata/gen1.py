"""Read Red, Blue and Yellow game data from the cartridge.

Species are keyed by the internal index the game stores in memory (RHYDON is 1),
as in every other Gen I decoder in Core. Each species also carries its ``dex`` number.
"""
from __future__ import annotations

from ..gen1 import decode_text

RECORD = 28
INDEX_COUNT = 190
NAME_LENGTH = 10
SLOTS = 10
EVOLUTION_METHODS = {1: 'level', 2: 'item', 3: 'trade'}


def word(rom, offset):
    return rom[offset] | rom[offset + 1] << 8


def banked(base, address):
    """File offset of ``address`` in the same bank as the file offset ``base``."""
    bank = base // 0x4000
    return address if bank == 0 else bank * 0x4000 + (address - 0x4000)


def machines(raw, count):
    """TM and HM numbers (1-based, HMs follow the TMs) whose bit is set in ``raw``."""
    return [number + 1 for number in range(count) if raw[number // 8] >> (number % 8) & 1]


def base_record(rom, offset, tm_count):
    raw = rom[offset:offset + RECORD]
    return {'dex': raw[0], 'stats': list(raw[1:6]), 'types': list(raw[6:8]), 'catch_rate': raw[8],
            'base_exp': raw[9], 'start_moves': list(raw[15:19]), 'growth': raw[19],
            'tmhm': machines(raw[20:27], tm_count)}


def evos_moves(rom, offset):
    evolutions = []
    while (method := rom[offset]) != 0:
        if method == 2:
            evolutions.append({'method': 'item', 'item': rom[offset + 1], 'level': rom[offset + 2],
                               'species': rom[offset + 3]})
            offset += 4
        elif method in EVOLUTION_METHODS:
            evolutions.append({'method': EVOLUTION_METHODS[method], 'level': rom[offset + 1],
                               'species': rom[offset + 2]})
            offset += 3
        else:
            raise ValueError(f'Unknown evolution method {method} at {offset:#x}')
    offset += 1
    learnset = []
    while rom[offset] != 0:
        learnset.append([rom[offset], rom[offset + 1]])
        offset += 2
    return evolutions, learnset


def slots(rom, offset):
    return [[rom[offset + 2 * slot], rom[offset + 2 * slot + 1]] for slot in range(SLOTS)]


def encounters(rom, pointers):
    tables = {}
    for map_id in range(256):
        address = word(rom, pointers + 2 * map_id)
        if address == 0xFFFF:
            break
        offset = banked(pointers, address)
        for kind in ('grass', 'water'):
            rate = rom[offset]
            offset += 1
            if rate:
                tables[f'{kind}:{map_id}'] = {'kind': kind, 'map': map_id, 'rate': rate, 'slots': slots(rom, offset)}
                offset += 2 * SLOTS
    return tables


def parties(rom, offset, end):
    found = []
    while offset < end:
        if rom[offset] == 0xFF:
            offset += 1
            party = []
            while rom[offset] != 0:
                party.append({'level': rom[offset], 'species': rom[offset + 1]})
                offset += 2
        else:
            level = rom[offset]
            offset += 1
            party = []
            while rom[offset] != 0:
                party.append({'level': level, 'species': rom[offset]})
                offset += 1
        offset += 1
        found.append(party)
    return found


def class_spans(rom, layout):
    """(class, start, end) for each trainer class with parties.

    A class with no parties points at the next class's data. Of the classes that share a
    start, only the last one owns the parties there.
    """
    starts = [banked(layout.trainers, word(rom, layout.trainers + 2 * index))
              for index in range(layout.trainer_classes)]
    for index, start in enumerate(starts):
        if start in starts[index + 1:]:
            continue
        end = min((other for other in starts if other > start), default=layout.trainers_end)
        yield index + 1, start, end


def trainers(rom, layout):
    found = {}
    for cls, start, end in class_spans(rom, layout):
        for number, party in enumerate(parties(rom, start, end), 1):
            found[f'{cls}:{number}'] = {'class': cls, 'index': number, 'party': party}
    return found


def read(rom, layout):
    dex_order = rom[layout.dex_order:layout.dex_order + INDEX_COUNT]
    tm_count = layout.tm_count
    by_dex = {dex: base_record(rom, layout.base_stats + (dex - 1) * RECORD, tm_count)
              for dex in range(1, layout.species_count + 1)}
    if layout.mew_base_stats is not None:
        by_dex[151] = base_record(rom, layout.mew_base_stats, tm_count)
    species, evolutions, learnsets = {}, {}, {}
    for index in range(1, INDEX_COUNT + 1):
        dex = dex_order[index - 1]
        if dex == 0:
            continue
        name_at = layout.names + (index - 1) * NAME_LENGTH
        species[index] = {'name': decode_text(rom[name_at:name_at + NAME_LENGTH]), **by_dex[dex]}
        pointer = banked(layout.evos_moves, word(rom, layout.evos_moves + 2 * (index - 1)))
        evolutions[index], learnsets[index] = evos_moves(rom, pointer)
    return {
        'species': species,
        'evolutions': evolutions,
        'learnsets': learnsets,
        'tm_moves': list(rom[layout.tm_moves:layout.tm_moves + tm_count]),
        'encounters': encounters(rom, layout.wild[0][1]),
        'trainers': trainers(rom, layout),
        'starters': [rom[sites[0]] for sites in layout.starters],
    }
