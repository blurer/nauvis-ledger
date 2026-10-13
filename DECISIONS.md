# Architecture Decisions

## ADR-001: Repo scope is raw data access only
**Date:** 2026-10-13
**Status:** Accepted

### Context
The goal is capacity vs supply and forecast analysis of Factorio production data. Cleaning and analysis scripts are hand-written by the owner.

### Decision
Tooling in this repo only gets data out of the game and stores the game's replies as-is. It does no cleaning, rate calculation or aggregation. There are three delivery targets:
1. Offline dumps from saves into `data/`
2. Live RCON polling on macOS (PoC)
3. The same poller against a 24/7 Linux headless server (later)

### Consequences
Stored data mirrors the Factorio API shape, so consumers must handle its quirks, such as empty tables and per-surface nesting.

## ADR-002: RCON via game client's local-rcon, not a headless server (PoC)
**Date:** 2026-10-13
**Status:** Accepted

### Context
On macOS with Steam, a headless `--start-server` would need a second instance to play in, and it auto-pauses when no players are connected.

### Decision
Use `local-rcon-socket` / `local-rcon-password` in `config.ini`, bound to `127.0.0.1`. Use `factorio-rcon-py` as the client because it is dependency-free and built for Factorio.

### Consequences
RCON `/sc` commands disable achievements on the save. The collector code is host-agnostic, so it can point at the headless server later.
