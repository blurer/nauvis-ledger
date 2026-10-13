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

### Fixed
- Collector resends once when the first `/sc` on a save returns empty (achievement warning)
