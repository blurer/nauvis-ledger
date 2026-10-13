# OpenCode Instructions for nauvis-ledger

## Commands

**Run the collector:**
```sh
uv run --env-file .env collect.py --dump           # full raw dump every 60s -> data/<map_seed>/dumps.jsonl
uv run --env-file .env collect.py --dump --once    # one full dump
uv run --env-file .env collect.py --history all    # stored flow history, every precision window
uv run --env-file .env collect.py --once --print   # one small snapshot, printed
ledger-start / ledger-stop                         # zsh aliases: background minutely dump (see README)
```

**Read snapshots with pandas:**
```sh
uv run read_data.py
```

## Setup prerequisites

- Factorio running locally with RCON enabled (see `docs/rcon-setup-macos.md`)
- `.env` file with `FACTORIO_RCON_HOST`, `PORT`, `PASSWORD` (gitignored)

## Python / tooling

- Uses `uv` for packaging, virtualenv, and running scripts (`.python-version = 3.13`)
- No tests, lint, or typecheck configured

## RCON quirks

- First `/sc` command on a save is swallowed (achievement warning); `collect.py` resends automatically
- Lua 2.0 API; uses `game.surfaces`, `game.forces.player`, `helpers.table_to_json`

## Architecture

- `collect.py`: RCON client that polls Factorio and appends raw JSON to `data/<map_seed>/` (full dumps, snapshots, flow history)
- `read_data.py`: pandas reader for `snapshots.jsonl`

## Environment

- `docs/rcon-setup-macos.md`: RCON configuration steps for macOS Factorio client
