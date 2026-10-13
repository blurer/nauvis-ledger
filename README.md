# nauvis-ledger
Taking raw Factorio RCON telemetry and processing it into capacity vs supply ledgers and forecast scenarios in Python with pandas. Built with opencode and open-weights models to test their viability for this use case: hyper-focused on simple, deterministic scripts with tests that validate every figure. 

## Development

Developed with [opencode](https://opencode.ai) driven by a local [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) model on an RTX Titan via llama.cpp — `Qwen3.8-27B-Q4_K_M.gguf` with `-c 65536 --cache-type-k f16 --cache-type-v f16 -ub 1024 -ngl 99 --flash-attn on`.

## Methods of running:
- 1: Extract data from an existing run and see the usage over time (wip)
- 2: Headless server operations and real time dashboard with future state capacity scenarios (tbd)
- 3: Real time game polling showing historical data and current state with future state capacity scenarios - similar to 2 but on a local host (tbd)

## Proof of concept: live production over RCON

Read live from a fresh single-player map (`nauvis-ledger` save) on macOS, Factorio 2.0.77, via local RCON. Setup is in [docs/rcon-setup-macos.md](docs/rcon-setup-macos.md).

Lifetime production on Nauvis at **tick 22748 (6m 19s game time)**. Δ is the change since the previous read at tick 17025 (4m 44s).

This table was summarised by hand from the raw RCON reply. Δ was worked out by hand too. Both raw reads are stored in `data/snapshots.jsonl` (backfilled, marked `backfill`).

| Item | Produced | Consumed | Δ produced |
|---|---|---|---|
| iron-ore | 30 | 30 | +24 |
| iron-plate | 29 | 20 | +26 |
| coal | 20 | 12 | +3 |
| iron-gear-wheel | 4 | 4 | +4 |
| burner-mining-drill | 1 | — | new |
| burner-inserter | 1 | — | new |
| wooden-chest | 1 | — | new |
| stone-furnace | 1 | 1 | — |
| iron-chest | 1 | — | — |
| wood | — | 2 | — |
| stone | — | 5 | — |

Fluids: none yet.

```sh
uv run --env-file .env collect.py --once           # one raw snapshot -> data/snapshots.jsonl
uv run --env-file .env collect.py --once --print   # same, and print the raw JSON
uv run --env-file .env collect.py                  # poll every 60s
```

## Collecting

The main mode is the full raw dump: everything the API exposes (items, fluids, power per electric network, kills, builds, pollution, evolution, logistic networks, technologies and research queue, entity counts, platforms, players, mods), one JSON line per minute. Nothing is cleaned or aggregated.

```sh
uv run --env-file .env collect.py --dump           # full dump every 60s -> data/<map_seed>/dumps.jsonl
uv run --env-file .env collect.py --dump --once    # one full dump
uv run --env-file .env collect.py --history all    # the game's stored flow history, every window
```

Output goes to one folder per save, named by map seed (`data/<map_seed>/`). Every save of the same map shares a seed, so they share a folder.

To run the minutely dump in the background, add these to `~/.zshrc`. `ledger-start` does nothing if a collector is already running; output goes to `data/collector.log`.

```sh
alias ledger-start='pgrep -f "collect.py --dump" >/dev/null && echo "ledger already running" || { (cd ~/wrk/nauvis-ledger && nohup uv run --env-file .env python -u collect.py --dump >> data/collector.log 2>&1 &); echo "ledger started"; }'
alias ledger-stop='pkill -f "collect.py --dump" && echo "ledger stopped" || echo "ledger not running"'
```

`--history` reads the history behind the in-game production graphs. The game keeps 300 samples per window:

| Window | Sample size | Covers |
|---|---|---|
| `one_hour` | 12 s | last 1 h |
| `ten_hours` | 2 min | last 10 h |
| `fifty_hours` | 10 min | last 50 h |
| `two_hundred_fifty_hours` | 50 min | last 250 h |
| `one_thousand_hours` | 3 h 20 min | last 1000 h |

The game merges older samples into coarser ones, so past play can't be read back at finer resolution. Running the minutely dump keeps per-minute data from then on.

## Data files

- `data/<map_seed>/dumps.jsonl` — minutely full raw dumps, one JSON object per line
- `data/<map_seed>/history-<window>-<tick>.json` — flow history read at that tick: per surface, per category, per name, 300 samples (index 0 = newest)
- `data/<map_seed>/snapshots.jsonl` — the smaller snapshot format (items, fluids, power, research)
- `data/<map_seed>/dump-<tick>.json` — single dumps taken before `--dump` became a loop
- `data/collector.log` — output of `ledger-start`
- `data/snapshots.jsonl` — the research dataset: the fresh single-player save (Nauvis only, no enemies), tick-continuous within the save
- `data/big-save.jsonl` — 4 snapshots from a much larger save (10 surfaces incl. Vulcanus/Gleba/Fulgora, 182 item types on Nauvis); kept as a scale-test fixture for the analysis code

## Capacity vs supply analysis (in progress)

The goal is to turn the snapshot stream into capacity planning answers: where consumption plateaus, whether a line needs expansion, and when.

- Flatten snapshots into a long table: `tick, surface, kind (items/fluids), direction (produced/consumed), name, amount`
- Compute per-interval rates by diffing the lifetime cumulative totals between snapshots
- Plateau detection: where a consumption rate pins at or exceeds the production rate, that flow is capacity-constrained and an expansion candidate
- Timing: with a buffer level, buffer ÷ gap gives time-to-starve, i.e. the expansion deadline
- Backtest ("was I wrong"): hide the last N snapshots, predict from the rest, compare against what actually happened

