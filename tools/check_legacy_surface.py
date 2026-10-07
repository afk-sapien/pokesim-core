"""Check that the Core 0.1.x names used by the PokeBench benchmark still import and behave.

Needs no emulator. Run it in an environment that has only pokesim-core installed.
The list is the set of imports PokeBench makes from Core, plus the GameBoy compatibility
shims that its engine relies on. Extend it when a consumer adds an import.
"""
import importlib
import inspect

SURFACE = {
    "pokesim_core": ["gen1_ui", "storage"],
    "pokesim_core.controls": ["ControllerPort", "identity", "panel", "switch_pokemon", "use_item"],
    "pokesim_core.emulator": ["GameBoy", "BUTTONS", "FPS"],
    "pokesim_core.gen1": [
        "BADGES", "W_BADGES", "W_BAG_ITEMS", "W_BATTLE_TYPE", "W_CUR_MAP", "W_DEX_OWNED", "W_ENEMY_MON",
        "W_EVENT_FLAGS", "W_IS_IN_BATTLE", "W_MONEY", "W_NUM_BAG_ITEMS", "W_PARTY_COUNT", "W_PARTY_MONS",
        "W_PARTY_NICKS", "W_PARTY_SPECIES", "W_PLAYER_NAME", "W_TRAINER_CLASS", "W_X", "W_Y", "bcd",
        "decode_text", "event_set", "flag_bits", "read_bag", "read_party", "read_progress"],
    "pokesim_core.gen1_ui": ["read_battler", "read_screen", "read_sprites", "read_storage"],
    "pokesim_core.menus": ["menu_options"],
    "pokesim_core.rom": ["inspect_rom", "require_rom", "RomInfo"],
}


def main():
    missing = []
    for module, names in SURFACE.items():
        loaded = importlib.import_module(module)
        for name in names:
            if hasattr(loaded, name):
                continue
            try:
                importlib.import_module(f"{module}.{name}")
            except ImportError:
                missing.append(f"{module}.{name}")
    if missing:
        raise SystemExit("Missing 0.1.x names: " + ", ".join(missing))
    from pokesim_core.emulator import GameBoy
    # PokeBench subclasses GameBoy and calls tick(frames, render=...), so these stay compatible.
    parameters = inspect.signature(GameBoy.tick).parameters
    assert list(parameters)[:3] == ["self", "frames", "render"], list(parameters)
    assert parameters["frames"].default == 1
    for name in ("press", "release", "screenshot", "save", "load", "close", "_pb"):
        assert hasattr(GameBoy, name), name
    import pokesim_core
    assert pokesim_core.API_VERSION == 1 and pokesim_core.__version__
    try:
        GameBoy("missing.gb")
    except ImportError as error:
        assert "emulator extra" in str(error)
    except (FileNotFoundError, ValueError):
        pass
    print("0.1.x surface ok", pokesim_core.__version__)


if __name__ == "__main__":
    main()
