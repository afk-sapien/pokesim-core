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
