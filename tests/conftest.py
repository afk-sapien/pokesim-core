import os

# Cartridge tests need local Gold, Silver or Crystal ROMs, which are never committed.
# They are collected only when POKESIM_CORE_GEN2_ROMS names a directory holding them.
collect_ignore = [] if os.environ.get('POKESIM_CORE_GEN2_ROMS') else ['test_gen2_roms.py', 'test_gen2_maps_roms.py',
                                                                   'test_gen2_hooks_roms.py', 'test_gen2_naming_roms.py']
# Save-menu exports and cable endpoints also run on Red, Blue and Yellow from POKESIM_CORE_ROMS.
if not (os.environ.get('POKESIM_CORE_GEN2_ROMS') or os.environ.get('POKESIM_CORE_ROMS')):
    collect_ignore += ['test_save_roms.py', 'test_cable_roms.py']
