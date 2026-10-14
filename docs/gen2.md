# Gold, Silver and Crystal

`pokesim_core.gen2` decodes Gen II memory read-only. It ships the per-version
memory map (`gen2.memory_map.symbols(version)`, from the pinned pret symbol
files, with Crystal's moved WRAM and the Crystal-only symbols in `CRYSTAL_ONLY`)
and the English character maps (`gen2.charmap.charmap(version)`).
`gen2.version_of(rom_bytes)` names the version through `cartridges.identify`. It ships no
species, move, item or map tables.

Table-free readers need only a version name and any memory that supports banked
reads `memory[bank, start:stop]`:

```python
from pokesim_core.gen2 import state

party = state.read_party_structs(memory, "crystal")  # DVs, shiny, held item, friendship, Pokerus, caught data
boxes = state.read_box_structs(memory, "crystal", box=0)  # one PC box, eggs included
counts, active = state.read_box_counts(memory, "crystal")
items = state.read_items(memory, "crystal")  # items, balls, key, pc and the TM/HM quantities
player = state.read_player(memory, "crystal")  # name, ID, map, position, Johto and Kanto badges, money
dex = state.read_pokedex(memory, "crystal")  # seen, caught and Unown forms
clock = state.read_clock(memory, "crystal")  # day, weekday, time of day, RTC start and DST
daycare = state.read_daycare(memory, "crystal")  # parents, egg flags, steps to egg and the egg
roamers = state.read_roamers(memory, "crystal")
```

`gen2.read_snapshot(memory, data, frame=0, *, cache=True)` returns the full
`Snapshot` PokeSim observes, with `Mon` objects, pockets, objects and screen
text. `data` is the consumer's game tables: `gen2.GameTables(raw)` builds them
from a JSON mapping, and any object with the same attributes works. Symbols and
the charmap default to Core's own. With `cache=True`, decoded regions (party,
each box, Pokedex, Day Care, screen) are reused while their bytes and `data`
are unchanged. `gen2.clear_region_cache()` drops them.

Also in `pokesim_core.gen2`:

- `battle_power(mon, data)` and `hidden_power(data, dvs)` rate a decoded Pokemon from the game tables.
- `offspring`, `retrieval_cost`, `branch_parents`, `ancestors` and `level_credit` apply the Day Care and evolution-line rules.
  `families`, `single_source`, `lines`, `breeding_stock`, `egg_lines`, `free_slots` and `descendants_wanted`
  find the families only the Day Care can copy and whether another hatchling is wanted.
- `live_status(game, collection, *, data=None)` builds the shared adventure status payload.
- `ScreenText`, `has_word`, `mask_hud`, `mask_roster` and `is_roster` match whole words in screen text.
  `ScreenText` and `has_word` come from the generation-neutral `pokesim_core.textmatch`, which Gen 1
  screen readers can import too.
- `decode_mon`, `individual`, `calculated_stats`, `experience_at`, `experience_progress`, `dex_flags` and `decode_text` are the building blocks.

Output is identical, field for field and in `repr`, to the PokeSim `pokesim.gen2`
modules these were moved from.

`Mon` also carries the Pokerus byte and the Crystal caught data word. `to_dict()`
reports them as `pokerus` and, on Crystal, `caught` (named through
`caught_details` and `landmark_name`), adds `power` and `accuracy` to each move
and `egg_cycles` to an egg. `Mon.to_dict(egg_view=True)` and
`Snapshot.to_dict(egg_view=True)` show an unhatched egg the way the game does,
with no Pokedex number, name or types. The default keeps the species. A
`Snapshot` has `enemy_shiny` for a wild opponent, read from the Transform backup
DVs when a wild Ditto has transformed. It is None when the symbol table has no
enemy DVs.

## Save-menu exports

`gen2.save` and `gen1_save` produce a battery save the way a console would: a private clone
of the run opens the Start menu, chooses SAVE and confirms, then a fresh emulator boots the
file, chooses Continue and checks that the party, boxes, Pokédex, badges, money, bag, names
and position match. A mismatch raises `ValueError` and nothing is returned. The live run is
never changed and nothing is written beside the ROM.

- `gen2.save.capture(emulator, data)` and `gen1_save.capture(emulator)` return a raw state,
  refused unless the trainer is walking with a party outside battle and dialogue.
- `gen2.save.export_with_clock(rom, state, data)` returns the 32 KiB save and its ten-byte
  `.rtc` file. `export` returns the save alone. `clock_archive(save, rtc, name)` zips both.
- `gen2.save.verify(rom, save, data, expected, *, rtc=None)` and `continue_save(rom, save,
  data, *, rtc=None)` boot a save. `continue_save` returns the running emulator once the
  trainer walks and leaves location checks to the caller.
- `gen2.save.checkpoint_clock(rom, state)` is the clock file a raw state reads as.
- `gen1_save.export(rom, state)` and `verify(rom, save, symbols, expected)` accept the
  verified English Red, Blue and Yellow builds (`symbols_for(rom)`). Yellow runs on
  `YellowEmulator`, so `progress(memory, symbols)` reads Red addresses on all three.
