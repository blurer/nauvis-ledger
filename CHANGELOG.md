# Changelog

## [Unreleased]
### Added
- `data/` directory for raw game data (contents gitignored)
- uv project (Python 3.13) with `factorio-rcon-py`
- `collect.py`: RCON poller that appends raw per-surface item/fluid totals and research state to `data/snapshots.jsonl`
- `docs/rcon-setup-macos.md`: macOS RCON setup, verification status, API notes
- `.env` (gitignored) for RCON host/port/password
- README proof-of-concept table: live production read over RCON at tick 22748
- `collect.py --print` prints each raw snapshot as it is saved
- `collect.py` also records raw electric network statistics per surface under `power`, keyed by network id
- `collect.py --dump`: one-off full raw dump (kills, builds, pollution, evolution, power, logistic networks, technologies, research queue, entity counts, platforms, players, mods) to `data/<map_seed>/dump-<tick>.json`
- `collect.py --history <precision|all>`: the game's stored 300-sample flow history (items, fluids, kills, builds, pollution, power) per surface to `data/<map_seed>/history-<precision>-<tick>.json`

### Changed
- Snapshots are written per save to `data/<map_seed>/snapshots.jsonl`; each snapshot includes `map_seed` (`--out` still overrides)

### Fixed
- Collector resends once when the first `/sc` on a save returns empty (achievement warning)
