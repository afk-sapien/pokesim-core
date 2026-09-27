"""Exact DV tail counts under a uniform reference model, independent of game RNG timing."""
from functools import lru_cache
from itertools import product


def hp_dv(attack, defense, speed, special):
    """Derive HP from the low bits of the four stored DVs."""
    return ((attack & 1) << 3) | ((defense & 1) << 2) | ((speed & 1) << 1) | (special & 1)


@lru_cache(maxsize=1)
def _tails():
    counts = [0] * 76
    for values in product(range(16), repeat=4):
        counts[sum(values) + hp_dv(*values)] += 1
    return tuple(sum(counts[total:]) for total in range(77))


def dv_probabilities(dvs):
    """Return inclusive and strictly better DV-total tails, or None for invalid data.

    Input order is HP, Attack, Defense, Speed, Special. HP must match the
    stored DVs. Each of the 65,536 four-DV combinations has equal weight in
    this reference model. These are not measured cartridge encounter odds.
    """
    if (not isinstance(dvs, (tuple, list)) or len(dvs) != 5
            or any(type(value) is not int or not 0 <= value <= 15 for value in dvs)
            or dvs[0] != hp_dv(*dvs[1:])):
        return None
    total = sum(dvs)
    at_least, better = _tails()[total:total + 2]
    return {'total': total, 'outcomes': 65536, 'at_least': at_least, 'better': better,
            'at_least_probability': at_least / 65536,
            'better_probability': better / 65536}
