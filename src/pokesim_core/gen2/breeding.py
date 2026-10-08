"""Day Care rules for Gen II: who can breed, what hatches and what retrieval costs.

Ported from PokeSim's pokesim/gen2/breeding.py and tracking.py. Each function reads
decoded Mon objects (or anything with the same fields) and consumer game tables.
"""
from .ram import calculated_stats, experience_at

DITTO = 132
TYROGUE = 236


def offspring(data, first, second):
    """Species the pair can produce as an egg, or an empty set when they cannot breed.

    Ditto with Ditto, eggs, the NONE egg group, a same-sex pair, no shared egg group and
    parents whose Defense and Special DVs look related all produce nothing, as in the cartridge.
    Nidoran♀ lines can produce either Nidoran.
    """
    if first.egg or second.egg or first.species == second.species == DITTO:
        return set()
    groups = [set(data.species[mon.species]['egg_groups']) for mon in (first, second)]
    if any('NONE' in group for group in groups):
        return set()
    if first.dvs[2] == second.dvs[2] and first.dvs[4] % 8 == second.dvs[4] % 8:
        return set()
    if first.species == DITTO or second.species == DITTO:
        mother = second if first.species == DITTO else first
    elif groups[0] & groups[1] and {first.gender, second.gender} == {'Male', 'Female'}:
        mother = first if first.gender == 'Female' else second
    else:
        return set()
    species = mother.species
    for _ in range(2):
        species = next((sid for sid, row in data.species.items()
                        if any(evo['species'] == species for evo in row['evolutions'])), species)
    return {29, 32} if species == 29 else {species}


def retrieval_cost(data, snapshot):
    """Money the Day Care asks to return every parent in ``snapshot.daycare`` (100 plus 100 per level gained)."""
    total = 0
    for mon in getattr(snapshot, 'daycare', ()):
        if mon:
            growth = data.species[mon.species]['growth']
            level = max(level for level in range(mon.level, 101) if experience_at(level, growth) <= mon.experience)
            total += (level - mon.level + 1) * 100
    return total


def branch_parents(data, snapshot, baby, branches):
    """Whether the snapshot's party and storage hold enough of ``baby`` to evolve into every species in ``branches``.

    Tyrogue's branch depends on Attack against Defense at the level it would evolve.
    """
    available = [mon for mon in snapshot.party + snapshot.stored if mon.species == baby]
    if baby != TYROGUE:
        return len(available) >= len(branches)
    possible = set()
    for mon in available:
        stats = calculated_stats(data.species[baby]['stats'], max(20, mon.level + 1), mon.dvs, mon.stat_exp)
        possible.add(107 if stats[1] < stats[2] else 106 if stats[1] > stats[2] else 237)
    return branches <= possible


def ancestors(data, species):
    """``species`` and every species that evolves into it, directly or not."""
    family = {species}
    while True:
        parents = {sid for sid, row in data.species.items()
                   if any(evo['species'] in family for evo in row['evolutions'])}
        if parents <= family:
            return frozenset(family)
        family.update(parents)


def level_credit(data, species):
    """The species a level-up of ``species`` counts toward: itself, or its whole line when it is final."""
    return {species} if data.species[species]['evolutions'] else ancestors(data, species)
