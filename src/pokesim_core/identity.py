"""Stable Generation I individual signatures, independent of app policy."""
from functools import lru_cache
import hashlib
import json


@lru_cache(maxsize=4096)
def _key(trainer, dvs):
    return hashlib.sha256(json.dumps([trainer, list(dvs)]).encode()).hexdigest()[:24]


def pokemon_identity(trainer, dvs):
    """Preserve the existing signature format, caching only immutable inputs."""
    if trainer is None or len(dvs) != 5:
        return None
    values = tuple(dvs)
    if type(trainer) is int and all(type(value) is int for value in values):
        return _key(trainer, values)
    return hashlib.sha256(json.dumps([trainer, list(dvs)]).encode()).hexdigest()[:24]
