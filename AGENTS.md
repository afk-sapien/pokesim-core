# PokiSim Core

- Keep the base package independent of both applications and external libraries.
- PyBoy and Pillow belong to the optional emulator extra and must be imported lazily.
- Do not ship ROMs, game tables, sprites, saves, run logs, or credentials.
- Core decoders only read memory. Policies, scoring, and agent observation filters stay in consumers.
- Preserve documented field shapes unless releasing a new compatible API version.
- Use synthetic memory and fake emulator fixtures in ordinary CI.
- Run `uv run ruff check .` and `uv run pytest` before publishing.
- Do not use em dashes or semicolons in authored writing.
