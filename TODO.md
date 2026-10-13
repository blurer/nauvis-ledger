# TODO

## In Progress
- [ ] Live polling: raw RCON replies into SQLite in data/ (piece 2)

## Up Next
- [ ] Offline dump incl. flow-statistics history buffers from saves (piece 1)
- [ ] Point poller at Linux headless server (piece 3)
- [ ] Load existing saves via `--start-server` to backfill history (README method 1)

## Done
- [x] Create `data/`, uv project, `factorio-rcon-py` collector (2026-10-13)
- [x] Enable local RCON in config.ini, password in .env (2026-10-13)
- [x] Document setup in docs/rcon-setup-macos.md (2026-10-13)
- [x] Verified single-player local RCON + first snapshot on 2.0.77 (2026-10-13)
- [x] Started 60s poller; backfilled 3 unsaved reads (2026-10-13)
