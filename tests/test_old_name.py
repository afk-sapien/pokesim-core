"""The old ``pokesim_core`` name stays importable and shares module objects with ``pokecore``."""
import importlib
import subprocess
import sys

import pytest

import pokecore
import pokecore.gen1
import pokecore.gen2.state


def test_old_name_warns_and_aliases_every_module():
    code = '''
import warnings
warnings.simplefilter("error", DeprecationWarning)
try:
    import pokesim_core
except DeprecationWarning as warning:
    assert "pokecore" in str(warning)
else:
    raise AssertionError("no warning")
'''
    subprocess.run([sys.executable, '-c', code], check=True)


def test_submodules_are_the_same_objects():
    with pytest.warns(DeprecationWarning):
        old = importlib.reload(importlib.import_module('pokesim_core'))
    from pokesim_core.gen1 import read_party
    import pokesim_core.gen2.state
    assert read_party is pokecore.gen1.read_party
    assert pokesim_core.gen2.state is pokecore.gen2.state
    assert old.gen1 is pokecore.gen1 and old.__version__ == pokecore.__version__
    assert old.romdata is importlib.import_module('pokecore.romdata')
    # Each module keeps its own spec, so reload and introspection see the real name.
    assert pokecore.gen1.__spec__.name == 'pokecore.gen1'
    assert pokecore.gen2.state.__spec__.name == 'pokecore.gen2.state'


def test_missing_names_still_fail():
    import pokesim_core
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module('pokesim_core.not_a_module')
    with pytest.raises(AttributeError):
        pokesim_core.not_a_module
