import os

# Cartridge tests need local Gold, Silver or Crystal ROMs, which are never committed.
# They are collected only when POKESIM_CORE_GEN2_ROMS names a directory holding them.
collect_ignore = [] if os.environ.get('POKESIM_CORE_GEN2_ROMS') else ['test_gen2_roms.py']
