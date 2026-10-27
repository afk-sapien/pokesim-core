"""The old name of :mod:`pokecore`. Import ``pokecore`` instead.

``pokesim_core`` and every ``pokesim_core.<module>`` are the same module objects as their
``pokecore`` names, so state, classes and ``isinstance`` checks are shared. Importing this
name warns with ``DeprecationWarning``.
"""
import importlib
import importlib.abc
import importlib.util
import sys
import warnings

import pokecore

NEW = 'pokecore'
warnings.warn('pokesim_core is now pokecore. Import pokecore instead.', DeprecationWarning, stacklevel=2)


def _target(name):
    return NEW + name[len(__name__):]


class _Alias(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Resolves ``pokesim_core.<module>`` to the already loaded ``pokecore.<module>``."""

    def find_spec(self, name, path=None, target=None):
        if not name.startswith(__name__ + '.'):
            return None
        real = importlib.util.find_spec(_target(name))
        if real is None:
            return None
        return importlib.util.spec_from_loader(name, self, is_package=real.submodule_search_locations is not None)

    def create_module(self, spec):
        module = importlib.import_module(_target(spec.name))
        spec.loader_state = module.__spec__
        return module

    def exec_module(self, module):
        # The import system points __spec__ at the alias. Give the module its own back.
        module.__spec__ = module.__spec__.loader_state


if not any(isinstance(finder, _Alias) for finder in sys.meta_path):
    sys.meta_path.insert(0, _Alias())


def __getattr__(name):
    if hasattr(pokecore, name):
        return getattr(pokecore, name)
    try:
        return importlib.import_module(f'{NEW}.{name}')
    except ModuleNotFoundError as error:
        if error.name != f'{NEW}.{name}':
            raise
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def __dir__():
    return sorted(set(dir(pokecore)) | set(globals()))
