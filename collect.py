"""Poll a running Factorio game over RCON and append production snapshots to data/."""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import factorio_rcon

DATA_DIR = Path(__file__).parent / "data"

# Lifetime produced (input) / consumed (output) totals per surface; rates come from diffing snapshots.
SNAPSHOT_LUA = (
    "/sc local f=game.forces.player "
    "local out={tick=game.tick,research={name=f.current_research and f.current_research.name,"
    "progress=f.research_progress},surfaces={}} "
    "for _,s in pairs(game.surfaces) do "
    "local i=f.get_item_production_statistics(s) local fl=f.get_fluid_production_statistics(s) "
    "out.surfaces[s.name]={items={produced=i.input_counts,consumed=i.output_counts},"
    "fluids={produced=fl.input_counts,consumed=fl.output_counts}} end "
    "rcon.print(helpers.table_to_json(out))"
)


def take_snapshot(client: factorio_rcon.RCONClient) -> dict:
    raw = client.send_command(SNAPSHOT_LUA)
    if not raw:
        # The first /sc on a save is swallowed by the achievement warning; resend once.
        raw = client.send_command(SNAPSHOT_LUA)
    try:
        snapshot = json.loads(raw or "")
    except json.JSONDecodeError:
        raise RuntimeError(f"Unexpected RCON response: {raw!r}") from None
    snapshot["collected_at"] = datetime.now(timezone.utc).isoformat()
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("FACTORIO_RCON_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("FACTORIO_RCON_PORT", "27015")))
    parser.add_argument("--password", default=os.environ.get("FACTORIO_RCON_PASSWORD"))
    parser.add_argument("--interval", type=float, default=60.0, help="seconds between snapshots")
    parser.add_argument("--once", action="store_true", help="take one snapshot and exit")
    parser.add_argument("--out", type=Path, default=DATA_DIR / "snapshots.jsonl")
    parser.add_argument("--print", action="store_true", help="print each raw snapshot as it is saved")
    args = parser.parse_args()
    if not args.password:
        parser.error("set --password or FACTORIO_RCON_PASSWORD")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    client = factorio_rcon.RCONClient(args.host, args.port, args.password, timeout=10, connect_on_init=False)

    while True:
        try:
            if client.rcon_socket is None:
                client.connect()
            snapshot = take_snapshot(client)
            with args.out.open("a") as f:
                f.write(json.dumps(snapshot) + "\n")
            if args.print:
                print(json.dumps(snapshot, indent=1))
            else:
                print(f"tick={snapshot['tick']} surfaces={len(snapshot['surfaces'])} -> {args.out}")
        except factorio_rcon.RCONNetworkError as exc:
            print(f"RCON unavailable ({exc}); retrying")
            client.close()
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
