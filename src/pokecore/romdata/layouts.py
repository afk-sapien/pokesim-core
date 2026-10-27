"""Where each table lives in each supported cartridge. Addresses only, no game data.

Banked addresses are the ``bank:address`` pairs from the pret symbol files for the
verified retail ROMs (pokered and pokeyellow, pokegold and pokesilver, pokecrystal11).
Red and Blue share every address below. Starter sites are the bytes that hold a
starter's species in Oak's or Elm's scripts. The first site of each starter is the one
that decides which Pokemon the player receives. The others repeat the same species for
the rival's pick, the picture, the cry or the name.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..rom import rom_offset

__all__ = ['LAYOUTS', 'Layout', 'layout', 'rom_offset']


@dataclass(frozen=True)
class Layout:
    version: str
    generation: int
    base_stats: int
    species_count: int
    names: int
    evos_moves: int
    tm_moves: int
    tm_count: int
    wild: tuple[tuple[str, int], ...]
    trainers: int
    trainer_classes: int
    trainers_end: int
    starters: tuple[tuple[int, ...], ...]
    # Gen I only: the dex order table and Red/Blue's separate Mew record.
    dex_order: int | None = None
    mew_base_stats: int | None = None


_RED_BLUE = dict(
    generation=1,
    base_stats=rom_offset(0x0E, 0x43DE), species_count=150, mew_base_stats=rom_offset(0x01, 0x425B),
    names=rom_offset(0x07, 0x421E), evos_moves=rom_offset(0x0E, 0x705C), dex_order=rom_offset(0x10, 0x5024),
    tm_moves=rom_offset(0x04, 0x7773), tm_count=55,
    wild=(('wild', rom_offset(0x03, 0x4EEB)),),
    trainers=rom_offset(0x0E, 0x5D3B), trainer_classes=47, trainers_end=rom_offset(0x0E, 0x652E),
    # Charmander, Squirtle, Bulbasaur: the ball's own species, then the rival's pick at the ball to its left.
    starters=((0x1D10E, 0x1D126), (0x1D11F, 0x1D104), (0x1D130, 0x1D115)),
)

_GOLD_SILVER = dict(
    generation=2,
    base_stats=rom_offset(0x14, 0x5B0B), species_count=251, names=rom_offset(0x6C, 0x4B74),
    evos_moves=rom_offset(0x10, 0x67BD), tm_moves=rom_offset(0x04, 0x5A66), tm_count=57,
    wild=(('johto_grass', rom_offset(0x0A, 0x6B35)), ('johto_water', rom_offset(0x0A, 0x7669)),
          ('kanto_grass', rom_offset(0x0A, 0x77C0)), ('kanto_water', rom_offset(0x0A, 0x7D43)),
          ('swarm_grass', rom_offset(0x0A, 0x7E1C)), ('swarm_water', rom_offset(0x0A, 0x7ED9))),
    # The last group (GruntF) has no symbol after it. Its five parties end here, before padding.
    trainers=rom_offset(0x0E, 0x593E), trainer_classes=66, trainers_end=rom_offset(0x0E, 0x7685),
    # Chikorita, Cyndaquil, Totodile: givepoke, then pokepic, cry and getmonname in the same ball script.
    starters=((0x180174, 0x180150, 0x180152, 0x180169), (0x1800F6, 0x1800D2, 0x1800D4, 0x1800EB),
              (0x180138, 0x180114, 0x180116, 0x18012D)),
)

LAYOUTS = {
    'red': Layout('red', **_RED_BLUE),
    'blue': Layout('blue', **_RED_BLUE),
    'yellow': Layout(
        'yellow', generation=1,
        base_stats=rom_offset(0x0E, 0x43DE), species_count=151,
        names=rom_offset(0x3A, 0x4000), evos_moves=rom_offset(0x0E, 0x71E5), dex_order=rom_offset(0x10, 0x50B1),
        tm_moves=rom_offset(0x04, 0x632D), tm_count=55,
        wild=(('wild', rom_offset(0x03, 0x4B95)),),
        trainers=rom_offset(0x0E, 0x5DD1), trainer_classes=47, trainers_end=rom_offset(0x0E, 0x65B2),
        # Pikachu: the gift itself, then wPlayerStarter.
        starters=((0x1CB66, 0x1CB41),),
    ),
    'gold': Layout('gold', **_GOLD_SILVER),
    'silver': Layout('silver', **_GOLD_SILVER),
    'crystal': Layout(
        'crystal', generation=2,
        base_stats=rom_offset(0x14, 0x5424), species_count=251, names=rom_offset(0x14, 0x7384),
        evos_moves=rom_offset(0x10, 0x65B1), tm_moves=rom_offset(0x04, 0x567A), tm_count=60,
        wild=(('johto_grass', rom_offset(0x0A, 0x65E9)), ('johto_water', rom_offset(0x0A, 0x711D)),
              ('kanto_grass', rom_offset(0x0A, 0x7274)), ('kanto_water', rom_offset(0x0A, 0x77F7)),
              ('swarm_grass', rom_offset(0x0A, 0x78D0)), ('swarm_water', rom_offset(0x0A, 0x792F))),
        # The last group (Mysticalman, Eusine's one party) ends here, before padding.
        trainers=rom_offset(0x0E, 0x5999), trainer_classes=67, trainers_end=rom_offset(0x0E, 0x7A67),
        starters=((0x78D21, 0x78CFD, 0x78CFF, 0x78D16), (0x78CA3, 0x78C7F, 0x78C81, 0x78C98),
                  (0x78CE5, 0x78CC1, 0x78CC3, 0x78CDA)),
    ),
}


def layout(version):
    found = LAYOUTS.get(version)
    if found is None:
        raise ValueError(f'No ROM layout for {version!r}')
    return found
