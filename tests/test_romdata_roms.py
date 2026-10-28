"""ROM-read game data on real cartridges.

Collected only when POKESIM_CORE_ROMS (red.gb, blue.gb, yellow.gb) or POKESIM_CORE_GEN2_ROMS
(gold.gbc, silver.gbc, crystal.gbc) names a folder of ROMs. The digests cover every table
``romdata.load`` reads. Each table was checked entry by entry against the pret disassemblies
(trainer parties, wild encounters, evolutions, learnsets, base stats, TM and HM lists).
"""
import hashlib
import os
from pathlib import Path
import random

import pytest

from pokecore import randomizer, romdata
from pokecore.cartridges import read_header

DIGESTS = {
    'red': '6f1325b59eeeacb2ec8ddef1009f509d0a811e9787c8990e0c76bab38eff3fe1',
    'blue': '16cbb347027f3b8ca09fd5574e9d7f9c6f3dc85e5c32e5ce8031df01c30e2b95',
    'yellow': 'e2d47ea892e2fb8173e2ee0a004e0c9b19f3f2292872c112e7fbc694fe3bdb73',
    'gold': 'a5c68ac36e4ef0fff72ab13720d35e94f783a2a0139a88e3c9866df0c731fb0e',
    'silver': '92942d4a0c2a0d4e756b64bf0695936f17bac343b96ddba2e77ebfca749bfdb5',
    'crystal': '4cc03a36c63f8161a794dbb7d15e897fdd6f29545e89265c33fea2c2602678cb',
}
# species, encounter tables, trainers, starters
COUNTS = {
    'red': (151, 58, 391, [176, 177, 153]),
    'blue': (151, 58, 391, [176, 177, 153]),
    'yellow': (151, 63, 396, [84]),
    'gold': (251, 158, 495, [152, 155, 158]),
    'silver': (251, 158, 495, [152, 155, 158]),
    'crystal': (251, 155, 541, [152, 155, 158]),
}
FILES = {'red': 'red.gb', 'blue': 'blue.gb', 'yellow': 'yellow.gb', 'gold': 'gold.gbc', 'silver': 'silver.gbc',
         'crystal': 'crystal.gbc'}


def _rom(version):
    variable = 'POKESIM_CORE_ROMS' if version in ('red', 'blue', 'yellow') else 'POKESIM_CORE_GEN2_ROMS'
    directory = os.environ.get(variable)
    if not directory:
        pytest.skip(f'set {variable} to a folder of cartridges to run')
    path = Path(directory) / FILES[version]
    if not path.exists():
        pytest.skip(f'{FILES[version]} is not in {variable}')
    return path.read_bytes()


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_tables_match_the_checked_reading(version):
    rom = _rom(version)
    data = romdata.load(rom)
    assert data.version == version
    assert hashlib.sha256(data.canonical()).hexdigest() == DIGESTS[version]
    assert (len(data.species), len(data.encounters), len(data.trainers), data.starters) == COUNTS[version]


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_no_overrides_and_explicit_version_are_byte_identical(version):
    rom = _rom(version)
    data = romdata.load(rom)
    assert data.with_overrides({}).canonical() == data.canonical()
    assert romdata.load(rom, version=version).canonical() == data.canonical()


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_every_starter_site_agrees(version):
    rom = _rom(version)
    data = romdata.load(rom)
    for species, sites in zip(data.starters, data.starter_sites()):
        assert {rom[site] for site in sites} == {species}


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_a_modified_cartridge_reads_with_an_explicit_version(version):
    rom = bytearray(_rom(version))
    data = romdata.load(rom)
    first = data.starter_sites()[0][0]
    replacement = next(species for species in data.species if species != data.starters[0])
    rom[first] = replacement
    with pytest.raises(ValueError, match='Unknown ROM'):
        romdata.load(rom)
    modified = romdata.load(rom, version=version)
    assert modified.starters[0] == replacement
    assert modified.with_overrides({'starters': data.starters}).canonical() == data.canonical()


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_patch_without_overrides_is_byte_identical(version):
    rom = _rom(version)
    assert romdata.patch_rom(rom) == rom


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_patched_cartridge_reads_back_as_the_effective_data(version):
    rom = _rom(version)
    data = romdata.load(rom)
    species = sorted(data.species)
    shuffled = species[:]
    random.Random(version).shuffle(shuffled)
    first = next(key for key, trainer in data.trainers.items() if len(trainer['party']) > 1)
    party = [dict(mon, species=shuffled[0]) for mon in data.trainers[first]['party']]
    overrides = {'species_map': dict(zip(species, shuffled)), 'starters': shuffled[-len(data.starters):],
                 'trainers': {first: {'party': party}}}
    patched = romdata.patch_rom(rom, overrides)
    header = read_header(patched)
    assert header.header_checksum_ok and header.global_checksum_ok
    assert romdata.load(patched, version=version).canonical() == romdata.effective_data(rom, overrides).canonical()
    assert romdata.patch_rom(patched, version=version) == patched


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_every_hm_gate_names_real_tables(version):
    data = romdata.load(_rom(version))
    gates = randomizer.hm_gates(version)
    assert gates and not randomizer.missing_hm_learners(data)
    missing = {key for _, keys in gates for key in keys if key not in data.encounters}
    # Only Yellow has the Gen I water tables outside Routes 19 to 21.
    expected = {'water:17', 'water:23', 'water:24', 'water:161', 'water:162'} if version in ('red', 'blue') else set()
    assert missing == expected


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_randomized_cartridge_patches_and_reads_back(version):
    rom = _rom(version)
    data = romdata.load(rom)
    overrides = randomizer.randomize(data, 2024, randomizer.Options(trainers=True))
    assert overrides == randomizer.randomize(data, 2024, randomizer.Options(trainers=True))
    effective = data.with_overrides(overrides)
    assert not randomizer.missing_hm_learners(effective)
    patched = romdata.patch_rom(rom, overrides)
    assert romdata.load(patched, version=version).canonical() == effective.canonical()


@pytest.mark.parametrize('version', sorted(DIGESTS))
def test_shuffled_trainer_moves_are_learnable(version):
    data = romdata.load(_rom(version))
    for seed in (12345, 2024):
        effective = data.with_overrides(randomizer.randomize(data, seed, randomizer.Options(trainers=True)))
        parties = [mon for trainer in effective.trainers.values() for mon in trainer['party']]
        with_moves = [mon for mon in parties if 'moves' in mon]
        assert bool(with_moves) == (data.generation == 2)
        for mon in with_moves:
            known = {move for level, move in data.learnsets[mon['species']] if level <= mon['level']}
            assert len(mon['moves']) == 4 and set(mon['moves']) - {0} <= known, (version, seed, mon)
