"""Checks against real cartridges. Set POKESIM_CORE_ROMS to a folder of ROMs to run them.

CI has no ROMs, so the emulator job, which forbids skips, ignores this file.
"""
import os
from pathlib import Path

import pytest

from pokesim_core import cartridges, gen1_link_metadata, gen2_link_metadata, timecapsule as tc
from pokesim_core.cartridges import identify, unpack
from pokesim_core.rom import inspect_rom, require_rom

ROMS = os.environ.get('POKESIM_CORE_ROMS')


@pytest.mark.skipif(not ROMS, reason='set POKESIM_CORE_ROMS to a folder of cartridges to run')
def test_real_cartridges_identify_and_match_their_headers():
    seen = set()
    for path in sorted(Path(ROMS).iterdir()):
        raw = path.read_bytes()
        cartridge = identify(raw)
        if cartridge is None:
            continue
        seen.add(cartridge.version)
        assert cartridges.header_matches(raw, cartridge), path.name
        assert cartridges.refusal_reason(raw) is None and unpack(raw) == raw
        assert cartridges.identify_file(path) == cartridge
        info = require_rom(path, allowed_games=cartridges.SLOTS)
        assert info.game == cartridge.version and info.verified
        assert inspect_rom(path).verified == (cartridge.version in ('red', 'blue'))
    assert seen


@pytest.mark.skipif(not ROMS, reason='set POKESIM_CORE_ROMS to a folder of cartridges to run')
def test_real_cartridges_carry_link_code():
    for path in sorted(Path(ROMS).iterdir()):
        raw = path.read_bytes()
        cartridge = identify(raw)
        if cartridge is None:
            continue
        builds = gen1_link_metadata if cartridge.generation == 1 else gen2_link_metadata
        assert builds.verify_signatures(raw, cartridge.sha1) == [], path.name
        if cartridge.generation == 2:
            assert tc.communication_ok(raw, cartridge.version)


# Shortcuts on real cartridges -------------------------------------------------------
# POKESIM_CORE_SHORTCUT_STATES names a folder with your own save states and a
# shortcuts.json manifest, a list of entries like
#   {"rom": "red", "state": "wild-battle.state", "machine": "RunAway", "args": [], "kwargs": {},
#    "expect": "completed"}
# ``machine`` is a class from ``pokesim_core.shortcuts`` and ``rom`` is any version, Gen 1 or Gen 2.
# ``expect`` is "completed" (effect seen and the screen settled) or "refused" (the
# game or the shortcut refused, and the screen still settled). No states ship here.
STATES = os.environ.get('POKESIM_CORE_SHORTCUT_STATES')


def _shortcut_cases():
    if not (ROMS and STATES):
        return []
    import json
    manifest = Path(STATES) / 'shortcuts.json'
    return json.loads(manifest.read_text()) if manifest.is_file() else []


def _rom_for(version):
    for path in sorted(Path(ROMS).iterdir()):
        cartridge = identify(path.read_bytes())
        if cartridge is not None and cartridge.version == version:
            return path
    pytest.skip(f'no {version} cartridge in POKESIM_CORE_ROMS')


@pytest.mark.skipif(not (ROMS and STATES), reason='set POKESIM_CORE_ROMS and POKESIM_CORE_SHORTCUT_STATES to run')
@pytest.mark.parametrize('case', _shortcut_cases(), ids=lambda case: f"{case['machine']}:{case['state']}")
def test_shortcuts_finish_at_a_resting_screen_on_real_cartridges(case):
    from pokesim_core import shortcuts
    from pokesim_core.emulator import Emulator
    emulator = Emulator(str(_rom_for(case['rom'])), sound_emulated=False)
    emulator.load((Path(STATES) / case['state']).read_bytes())
    from pokesim_core.emulator import BUTTONS
    for button in BUTTONS:
        emulator.release(button)
    machine = getattr(shortcuts, case['machine'])(*case.get('args', []), version=case['rom'], **case.get('kwargs', {}))
    done = shortcuts.drive(machine, emulator)
    assert done.settled, done.outcome
    assert done.completed == (case.get('expect', 'completed') == 'completed'), done.outcome
    screen = shortcuts.current_screen(emulator.memory, case['rom'])
    assert screen in ('overworld', 'battle_menu', 'move_menu', 'party', 'mart', 'pc', 'transition',
                      'switch_prompt'), screen
