"""ROM-read game data and the randomizer override layer, on small synthetic cartridges."""
import pytest

from pokesim_core import romdata
from pokesim_core.romdata import Layout, gen1, gen2


class Rom:
    """Bank 1 of a two-bank cartridge, filled front to back. Addresses equal file offsets."""

    def __init__(self):
        self.data = bytearray(0x8000)
        self.at = 0x4000

    def put(self, raw):
        offset = self.at
        self.data[offset:offset + len(raw)] = bytes(raw)
        self.at += len(raw)
        return offset

    def words(self, count):
        return self.put(bytes(2 * count))

    def set_word(self, offset, value):
        self.data[offset:offset + 2] = value.to_bytes(2, 'little')


def name(text):
    return bytes(0x80 + ord(letter) - ord('A') for letter in text) + b'\x50'


def gen1_cartridge():
    rom = Rom()
    dex_order = rom.put([1, 2] + [0] * (gen1.INDEX_COUNT - 2))
    base_stats = rom.put([1, 45, 49, 49, 45, 65, 22, 3, 45, 64] + [0] * 5 + [33, 45, 0, 0, 3, 0b101] + [0] * 6 + [0]
                         + [2, 60, 62, 63, 60, 80, 22, 3, 45, 141] + [0] * 5 + [33, 45, 73, 0, 3, 0b100] + [0] * 6 + [0])
    names = rom.put(name('ALPHA').ljust(10, b'\x50') + name('BETA').ljust(10, b'\x50'))
    evos_moves = rom.words(gen1.INDEX_COUNT)
    rom.set_word(evos_moves, rom.put([1, 16, 2, 0, 7, 73, 0]))
    rom.set_word(evos_moves + 2, rom.put([0, 22, 75, 0]))
    tm_moves = rom.put(range(1, 56))
    wild = rom.words(4)
    grass = [level for slot in range(gen1.SLOTS) for level in (3 + slot, 1 + slot % 2)]
    rom.set_word(wild, rom.put([25, *grass, 0]))
    rom.set_word(wild + 2, rom.put([0, 5, *[20, 2] * gen1.SLOTS]))
    rom.set_word(wild + 4, rom.put([10, *[9, 2] * gen1.SLOTS, 0]))
    rom.set_word(wild + 6, 0xFFFF)
    trainers = rom.words(3)
    rom.set_word(trainers, rom.put([5, 1, 2, 0, 0xFF, 7, 1, 9, 2, 0]))
    # Class 2 has no parties, so it points at class 3's data.
    shared = rom.put([10, 2, 0])
    rom.set_word(trainers + 2, shared)
    rom.set_word(trainers + 4, shared)
    trainers_end = rom.at
    starter = rom.put([1])
    found = Layout('red', 1, base_stats=base_stats, species_count=2, names=names, evos_moves=evos_moves,
                   tm_moves=tm_moves, tm_count=55, wild=(('wild', wild),), trainers=trainers, trainer_classes=3,
                   trainers_end=trainers_end, starters=((starter,),), dex_order=dex_order)
    return bytes(rom.data), found


def gen2_cartridge():
    rom = Rom()
    record = [0, 45, 49, 65, 45, 49, 65, 22, 22, 45, 64, 0, 0, 31, 100, 20, 5] + [0] * 5 + [3, 0x17, 0b11] + [0] * 7
    base_stats = rom.put(record + record)
    names = rom.put(name('ALPHA').ljust(10, b'\x50') + name('BETA').ljust(10, b'\x50'))
    evos_moves = rom.words(2)
    rom.set_word(evos_moves, rom.put([5, 20, 1, 2, 4, 1, 2, 0, 1, 33, 0]))
    rom.set_word(evos_moves + 2, rom.put([0, 0]))
    tm_moves = rom.put(range(1, 61))
    grass = rom.put([1, 2, 10, 10, 10, *[3, 1] * gen2.GRASS_SLOTS, *[4, 2] * gen2.GRASS_SLOTS,
                     *[5, 1] * gen2.GRASS_SLOTS, 0xFF])
    water = rom.put([1, 3, 6, *[20, 2] * gen2.WATER_SLOTS, 0xFF])
    trainers = rom.words(3)
    rom.set_word(trainers, rom.put([*name('AB'), 3, 8, 1, 7, 33, 0, 0, 0, 0xFF, *name('C'), 0, 9, 2, 0xFF]))
    shared = rom.put([*name('D'), 2, 30, 2, 4, 0xFF])
    rom.set_word(trainers + 2, shared)
    rom.set_word(trainers + 4, shared)
    trainers_end = rom.at
    starter = rom.put([2])
    found = Layout('gold', 2, base_stats=base_stats, species_count=2, names=names, evos_moves=evos_moves,
                   tm_moves=tm_moves, tm_count=60, wild=(('johto_grass', grass), ('johto_water', water)),
                   trainers=trainers, trainer_classes=3, trainers_end=trainers_end, starters=((starter, starter),))
    return bytes(rom.data), found


@pytest.fixture
def red(monkeypatch):
    rom, found = gen1_cartridge()
    monkeypatch.setitem(romdata.LAYOUTS, 'red', found)
    return romdata.load(rom, version='red')


@pytest.fixture
def gold(monkeypatch):
    rom, found = gen2_cartridge()
    monkeypatch.setitem(romdata.LAYOUTS, 'gold', found)
    return romdata.load(rom, version='gold')


def test_gen1_tables(red):
    assert red.generation == 1
    assert red.species[1] == {'name': 'ALPHA', 'dex': 1, 'stats': [45, 49, 49, 45, 65], 'types': [22, 3],
                              'catch_rate': 45, 'base_exp': 64, 'start_moves': [33, 45, 0, 0], 'growth': 3,
                              'tmhm': [1, 3]}
    assert red.species[2]['tmhm'] == [3]
    assert red.evolutions == {1: [{'method': 'level', 'level': 16, 'species': 2}], 2: []}
    assert red.learnsets == {1: [[7, 73]], 2: [[22, 75]]}
    assert red.tm_moves == list(range(1, 56))
    assert sorted(red.encounters) == ['grass:0', 'grass:2', 'water:1']
    assert red.encounters['grass:0']['slots'][:2] == [[3, 1], [4, 2]]
    assert red.encounters['water:1'] == {'kind': 'water', 'map': 1, 'rate': 5, 'slots': [[20, 2]] * gen1.SLOTS}
    assert red.starters == [1]


def test_gen1_trainers_skip_classes_without_parties(red):
    assert red.trainers == {
        '1:1': {'class': 1, 'index': 1, 'party': [{'level': 5, 'species': 1}, {'level': 5, 'species': 2}]},
        '1:2': {'class': 1, 'index': 2, 'party': [{'level': 7, 'species': 1}, {'level': 9, 'species': 2}]},
        '3:1': {'class': 3, 'index': 1, 'party': [{'level': 10, 'species': 2}]},
    }


def test_gen2_tables(gold):
    assert gold.generation == 2
    assert gold.species[1]['name'] == 'ALPHA'
    assert gold.species[1]['stats'] == [45, 49, 65, 45, 49, 65]
    assert gold.species[1]['egg_groups'] == [1, 7]
    assert gold.species[1]['tmhm'] == [1, 2]
    assert gold.evolutions[1] == [{'method': 'stat', 'level': 20, 'stat': 1, 'species': 2},
                                  {'method': 'happiness', 'time': 1, 'species': 2}]
    assert gold.learnsets[1] == [[1, 33]]
    grass = gold.encounters['johto_grass:258']
    assert grass['rates'] == [10, 10, 10]
    assert grass['slots']['morn'][0] == [3, 1]
    assert grass['slots']['day'][0] == [4, 2]
    assert grass['slots']['nite'][0] == [5, 1]
    assert gold.encounters['johto_water:259']['slots'] == [[20, 2]] * 3
    assert gold.trainers['1:1'] == {'class': 1, 'index': 1, 'name': 'AB', 'type': 3,
                                    'party': [{'level': 8, 'species': 1, 'item': 7, 'moves': [33, 0, 0, 0]}]}
    assert gold.trainers['1:2']['party'] == [{'level': 9, 'species': 2}]
    assert '2:1' not in gold.trainers
    assert gold.trainers['3:1']['party'] == [{'level': 30, 'species': 2, 'item': 4}]
    assert gold.starters == [2]


@pytest.mark.parametrize('game', ['red', 'gold'])
def test_no_overrides_is_byte_identical(game, request):
    data = request.getfixturevalue(game)
    assert data.with_overrides({}).canonical() == data.canonical()
    assert data.with_overrides(None).canonical() == data.canonical()


def test_species_map_rewrites_placed_pokemon_only(red):
    before = red.canonical()
    effective = red.with_overrides({'species_map': {1: 2, 2: 1}})
    assert red.canonical() == before
    assert effective.starters == [2]
    assert effective.encounters['grass:0']['slots'][:2] == [[3, 2], [4, 1]]
    assert effective.trainers['3:1']['party'] == [{'level': 10, 'species': 1}]
    assert effective.evolutions == red.evolutions
    assert effective.species == red.species


def test_species_map_covers_every_time_of_day(gold):
    effective = gold.with_overrides({'species_map': {1: 2}})
    slots = effective.encounters['johto_grass:258']['slots']
    assert {slot[1] for time in slots.values() for slot in time} == {2}


def test_encounter_swap_and_field_override(red):
    effective = red.with_overrides({'species_map': {2: 1}, 'encounters': {'grass:0': 'grass:2',
                                                                           'water:1': {'rate': 9}}})
    assert effective.encounters['grass:0'] == {'kind': 'grass', 'map': 0, 'rate': 10, 'slots': [[9, 1]] * gen1.SLOTS}
    assert effective.encounters['water:1']['rate'] == 9


def test_explicit_entries_win_over_species_map(red):
    party = [{'level': 50, 'species': 2}]
    effective = red.with_overrides({'species_map': {2: 1}, 'trainers': {'3:1': {'party': party}},
                                    'starters': [2]})
    assert effective.trainers['3:1']['party'] == party
    assert effective.starters == [2]
    assert effective.trainers['1:1']['party'][1]['species'] == 1


def test_base_data_overrides(red):
    effective = red.with_overrides({'species': {1: {'stats': [1, 2, 3, 4, 5]}}, 'learnsets': {2: [[1, 1]]},
                                    'evolutions': {1: []}, 'tm_moves': [0] * 55})
    assert effective.species[1]['stats'] == [1, 2, 3, 4, 5]
    assert effective.learnsets[2] == [[1, 1]]
    assert effective.evolutions[1] == []
    assert effective.tm_moves == [0] * 55
    assert effective.overrides['tm_moves'] == [0] * 55


@pytest.mark.parametrize('overrides, message', [
    ({'moves': {}}, 'Unknown override keys'),
    ({'species_map': {1: 99}}, 'not a species'),
    ({'species': {1: {'colour': 1}}}, 'Unknown species fields'),
    ({'tm_moves': [1]}, 'needs 55 entries'),
    ({'starters': [1, 2]}, 'needs 1 entries'),
    ({'starters': [99]}, 'not a species'),
    ({'encounters': {'grass:0': 'water:1'}}, 'Cannot swap'),
    ({'encounters': {'grass:9': {'rate': 1}}}, 'Unknown encounters key'),
    ({'encounters': {'grass:0': {'map': 3}}}, 'cannot set'),
    ({'encounters': {'grass:0': {'slots': [[5, 99]]}}}, 'not a species'),
    ({'trainers': {'2:1': {'party': []}}}, 'Unknown trainers key'),
    ({'trainers': {'1:1': {'party': [{'level': 5, 'species': 0}]}}}, 'not a species'),
])
def test_invalid_overrides(red, overrides, message):
    with pytest.raises(ValueError, match=message):
        red.with_overrides(overrides)


def test_load_needs_a_known_cartridge_or_version():
    rom, _ = gen1_cartridge()
    with pytest.raises(ValueError, match='Unknown ROM'):
        romdata.load(rom)
    with pytest.raises(ValueError, match='No ROM layout'):
        romdata.load(rom, version='green')


def test_layouts_cover_every_supported_version():
    assert sorted(romdata.LAYOUTS) == ['blue', 'crystal', 'gold', 'red', 'silver', 'yellow']
    assert romdata.rom_offset(0x0E, 0x43DE) == 0x383DE
    assert romdata.rom_offset(0, 0x0150) == 0x0150
