# RCON setup on macOS (PoC)

How we get raw data out of a running Factorio game on macOS (Steam install) via RCON.
Status markers: verified on this machine · pending · unverified (from research only)

## Environment

| Thing | Value |
|---|---|
| Factorio | 2.0.77 (build 84539, mac-arm64, steam) |
| Binary | `~/Library/Application Support/Steam/steamapps/common/Factorio/factorio.app/Contents/MacOS/factorio` |
| User data | `~/Library/Application Support/factorio/` (`config/`, `saves/`, `script-output/`) |
| Config | `~/Library/Application Support/factorio/config/config.ini` |
| PoC save | `saves/nauvis-ledger.zip` (fresh map) |
| Python | uv, Python 3.13, `factorio-rcon-py` 2.1.3 |

## 1. Enable RCON in the game client

No headless server needed: the normal client hosts RCON via two keys in `config.ini` under `[other]`
(described in the file as "Socket to host RCON on when launching MP server from the menu").

1. **Quit Factorio completely.** It rewrites `config.ini` on exit, so edits made while running are lost.
2. Back up: `cp config.ini config.ini.bak-nauvis-ledger`
3. Uncomment and set (they ship commented as `; local-rcon-socket=0.0.0.0:0` / `; local-rcon-password=`):
   ```ini
   local-rcon-socket=127.0.0.1:27015
   local-rcon-password=<random, e.g. openssl rand -hex 12>
   ```
    Use `127.0.0.1`, not `0.0.0.0` (don't expose the port; avoids macOS firewall prompt) and not `localhost` (reported not to work).
4. Put the same values in the repo's `.env` (gitignored):
    ```
    FACTORIO_RCON_HOST=127.0.0.1
    FACTORIO_RCON_PORT=27015
    FACTORIO_RCON_PASSWORD=<same password>
    ```

Same settings are also in-game under the hidden settings menu (Ctrl+Alt+click **Settings** → **The rest**; on Mac possibly Ctrl+Option).

Done on this machine 2026-10-13. First snapshot collected from `nauvis-ledger` save (tick 2545).

## 2. Load the game so RCON listens

- **Single player works** on 2.0.77: load the save normally and RCON listens (`game.is_multiplayer()` → `false`). Check with
  `lsof -nP -iTCP:27015 -sTCP:LISTEN`
- Fallback if it ever doesn't: **Multiplayer → Host saved game** → pick the save.

## 3. Pull data

```sh
uv run --env-file .env collect.py --once     # one snapshot
uv run --env-file .env collect.py            # every 60s (--interval to change)
```

Output: `data/snapshots.jsonl`, one raw JSON object per poll (game reply + `collected_at`). No cleaning.

Commands are Lua sent as `/sc ...` (silent-command, allowed over RCON) and answered with `rcon.print(helpers.table_to_json(...))`.

### Achievements
The first `/sc` permanently disables achievements for that save. Only point the collector at saves where that's acceptable.

Observed: the **first** `/sc` on a save returns an empty reply (the achievement warning swallows it). Every later command replies normally. `collect.py` resends once on an empty reply.

Built-in commands work without Lua: `/version` → `2.0.77`, `/time` → `38 seconds`.

## Protocol / API notes

- Source RCON over TCP (auth type 3, exec type 2). Factorio sends large replies as one packet larger than 4096 bytes; `factorio-rcon-py` reads by length prefix so it copes.
- 2.0 API (differs from 1.1, most examples online are 1.1):
  - `force.get_item_production_statistics(surface)` / `get_fluid_production_statistics(surface)` → `LuaFlowStatistics` (per surface in 2.0; 1.1 had `force.item_production_statistics`)
  - `input_counts` = produced, `output_counts` = consumed (lifetime totals)
  - `get_flow_count{name, category="input"|"output", precision_index=defines.flow_precision_index.X, sample_index=1..300}`: history buffers from `five_seconds` up to `one_thousand_hours`. Items/fluids are per minute, electric is per tick.
  - Power: `pole.electric_network_statistics` (dedupe by `electric_network_id`)
  - JSON: `helpers.table_to_json` (1.1: `game.table_to_json`)
- Docs: https://lua-api.factorio.com/2.0.77/

## Rollback

Quit Factorio, then:
`cp "config.ini.bak-nauvis-ledger" config.ini` (in `~/Library/Application Support/factorio/config/`).

## Sources

- Command line / config: https://wiki.factorio.com/Command_line_parameters, https://forums.factorio.com/viewtopic.php?p=569012
- App directory: https://wiki.factorio.com/Application_directory
- Single-player RCON fix: https://forums.factorio.com/128760, https://github.com/wube/factorio-data/blob/master/changelog.txt
- Achievements: https://wiki.factorio.com/Achievements
- LuaFlowStatistics: https://lua-api.factorio.com/2.0.77/classes/LuaFlowStatistics.html
- Client lib: https://pypi.org/project/factorio-rcon-py/
