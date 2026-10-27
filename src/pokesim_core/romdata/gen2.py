"""Read Gold, Silver and Crystal game data from the cartridge.

Species are keyed by dex number, which Gen II also uses in memory. Map IDs are
``group * 256 + number``, as in :mod:`pokesim_core.gen2.tables`.
"""
from __future__ import annotations

from ..gen2.tables import decode_text
from .gen1 import banked, class_spans, machines, word

RECORD = 32
NAME_LENGTH = 10
GRASS_SLOTS = 7
WATER_SLOTS = 3
TIMES = ('morn', 'day', 'nite')
EVOLUTION_METHODS = {1: ('level', 'level'), 2: ('item', 'item'), 3: ('trade', 'item'),
                     4: ('happiness', 'time')}
ITEM = 1 << 1
MOVES = 1 << 0


def base_record(rom, offset, tm_count):
    raw = rom[offset:offset + RECORD]
    return {'stats': list(raw[1:7]), 'types': list(raw[7:9]), 'catch_rate': raw[9], 'base_exp': raw[10],
            'items': list(raw[11:13]), 'gender_ratio': raw[13], 'egg_steps': raw[15], 'growth': raw[22],
            'egg_groups': [raw[23] >> 4, raw[23] & 0x0F], 'tmhm': machines(raw[24:32], tm_count)}


def evos_moves(rom, offset):
    evolutions = []
    while (method := rom[offset]) != 0:
        if method == 5:
            evolutions.append({'method': 'stat', 'level': rom[offset + 1], 'stat': rom[offset + 2],
                               'species': rom[offset + 3]})
            offset += 4
        elif method in EVOLUTION_METHODS:
            name, field = EVOLUTION_METHODS[method]
            evolutions.append({'method': name, field: rom[offset + 1], 'species': rom[offset + 2]})
            offset += 3
        else:
            raise ValueError(f'Unknown evolution method {method} at {offset:#x}')
    offset += 1
    learnset = []
    while rom[offset] != 0:
        learnset.append([rom[offset], rom[offset + 1]])
        offset += 2
    return evolutions, learnset


def pairs(rom, offset, count):
    return [[rom[offset + 2 * slot], rom[offset + 2 * slot + 1]] for slot in range(count)]


def encounters(rom, layout):
    tables = {}
    for kind, offset in layout.wild:
        grass = kind.endswith('grass')
        while rom[offset] != 0xFF:
            map_id = rom[offset] * 256 + rom[offset + 1]
            offset += 2
            if grass:
                table = {'rates': list(rom[offset:offset + 3]),
                         'slots': {time: pairs(rom, offset + 3 + 2 * GRASS_SLOTS * n, GRASS_SLOTS)
                                   for n, time in enumerate(TIMES)}}
                offset += 3 + 2 * GRASS_SLOTS * len(TIMES)
            else:
                table = {'rate': rom[offset], 'slots': pairs(rom, offset + 1, WATER_SLOTS)}
                offset += 1 + 2 * WATER_SLOTS
            key = f'{kind}:{map_id}'
            if key in tables:
                raise ValueError(f'Two {kind} tables for map {map_id}')
            tables[key] = {'kind': kind, 'map': map_id, **table}
    return tables


def parties(rom, offset, end, version):
    found = []
    while offset < end:
        name_end = rom.index(0x50, offset)
        name = decode_text(rom[offset:name_end + 1], version)
        kind = rom[name_end + 1]
        offset = name_end + 2
        party = []
        while rom[offset] != 0xFF:
            mon = {'level': rom[offset], 'species': rom[offset + 1]}
            offset += 2
            if kind & ITEM:
                mon['item'] = rom[offset]
                offset += 1
            if kind & MOVES:
                mon['moves'] = list(rom[offset:offset + 4])
                offset += 4
            party.append(mon)
        offset += 1
        found.append({'name': name, 'type': kind, 'party': party})
    return found


def trainers(rom, layout):
    found = {}
    for cls, start, end in class_spans(rom, layout):
        for number, trainer in enumerate(parties(rom, start, end, layout.version), 1):
            found[f'{cls}:{number}'] = {'class': cls, 'index': number, **trainer}
    return found


def read(rom, layout):
    tm_count = layout.tm_count
    species, evolutions, learnsets = {}, {}, {}
    for dex in range(1, layout.species_count + 1):
        name_at = layout.names + (dex - 1) * NAME_LENGTH
        species[dex] = {'name': decode_text(rom[name_at:name_at + NAME_LENGTH], layout.version), 'dex': dex,
                        **base_record(rom, layout.base_stats + (dex - 1) * RECORD, tm_count)}
        pointer = banked(layout.evos_moves, word(rom, layout.evos_moves + 2 * (dex - 1)))
        evolutions[dex], learnsets[dex] = evos_moves(rom, pointer)
    return {
        'species': species,
        'evolutions': evolutions,
        'learnsets': learnsets,
        'tm_moves': list(rom[layout.tm_moves:layout.tm_moves + tm_count]),
        'encounters': encounters(rom, layout),
        'trainers': trainers(rom, layout),
        'starters': [rom[sites[0]] for sites in layout.starters],
    }
