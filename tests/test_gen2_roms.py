"""Gen II reads on real cartridges. Collected only when POKESIM_CORE_GEN2_ROMS is set.

The directory holds gold.gbc, silver.gbc and crystal.gbc, each optionally with a battery save
next to it (gold.gbc.ram). Set POKESIM_CORE_GEN2_DATA to a directory of <version>/data.json
game tables to also compare full snapshots. Missing files are reported as skips.
"""
import io
import json
import os
from pathlib import Path

import pytest

from pokesim_core import gen2
from pokesim_core.gen2 import state
from pokesim_core.memory_snapshot import snapshot_emulator

ROMS = Path(os.environ.get('POKESIM_CORE_GEN2_ROMS', '.'))
READERS = (state.read_party_structs, state.read_box_structs, state.read_box_counts, state.read_items,
           state.read_player, state.read_pokedex, state.read_clock, state.read_daycare, state.read_roamers)


def machines(version):
    pytest.importorskip('pyboy_rs')
    from pokesim_core.emulator import Emulator
    rom = ROMS / f'{version}.gbc'
    if not rom.exists():
        pytest.skip(f'{rom.name} is not in POKESIM_CORE_GEN2_ROMS')
    save = rom.with_name(rom.name + '.ram')
    raw, ram = rom.read_bytes(), save.read_bytes() if save.exists() else bytes(32768)
    return [cls(io.BytesIO(raw), ram_file=io.BytesIO(ram), sound_emulated=False)
            for cls in (snapshot_emulator(Emulator), Emulator)], save.exists()


@pytest.mark.parametrize('version', gen2.VERSIONS)
def test_snapshot_reads_match_live_reads_through_the_title_screen(version):
    (fast, live), saved = machines(version)
    tables = None
    directory = os.environ.get('POKESIM_CORE_GEN2_DATA')
    if directory:
        tables = gen2.GameTables(json.loads((Path(directory) / version / 'data.json').read_text()))
    try:
        for step in range(40):
            for machine in (fast, live):
                machine.tick(90, render=False, sound=False)
                button = 'start' if step % 3 == 0 else 'a'
                machine.press(button)
                machine.tick(6, render=False, sound=False)
                machine.release(button)
            for read in READERS:
                assert read(fast.memory, version) == read(live.memory, version), read.__name__
            if tables is not None:
                assert repr(gen2.read_snapshot(fast.memory, tables)) == repr(
                    gen2.read_snapshot(live.memory, tables, cache=False))
        if saved:
            player = state.read_player(fast.memory, version)
            assert player['name'] and len(state.read_party_structs(fast.memory, version)) >= 1
    finally:
        fast.stop()
        live.stop()
