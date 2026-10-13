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
# Power is per electric network (keyed by network id), found by scanning the force's poles;
# electric stats are reversed: output_counts is generation, input_counts is consumption.
# map_seed (from surface 1, nauvis) identifies the save; snapshots go to data/<seed>/snapshots.jsonl.
SNAPSHOT_LUA = (
    "/sc local f=game.forces.player "
    "local out={tick=game.tick,map_seed=game.surfaces[1].map_gen_settings.seed,research={name=f.current_research and f.current_research.name,"
    "progress=f.research_progress},surfaces={}} "
    "for _,s in pairs(game.surfaces) do "
    "local i=f.get_item_production_statistics(s) local fl=f.get_fluid_production_statistics(s) "
    "local nets={} for _,p in pairs(s.find_entities_filtered{type='electric-pole',force=f}) do "
    "local id=p.electric_network_id and tostring(p.electric_network_id) "
    "if id and not nets[id] then local e=p.electric_network_statistics "
    "nets[id]={produced=e.output_counts,consumed=e.input_counts} end end "
    "out.surfaces[s.name]={items={produced=i.input_counts,consumed=i.output_counts},"
    "fluids={produced=fl.input_counts,consumed=fl.output_counts},power=nets} end "
    "rcon.print(helpers.table_to_json(out))"
)

# One-off raw dump of everything else the API exposes; flow stats keep the API's input/output names.
# Each section is pcall-wrapped so a failing call is recorded as {"error": ...} instead of aborting.
DUMP_LUA = "/sc " + " ".join("""
local f=game.forces.player local enemy=game.forces.enemy
local function try(fn) local ok,r=pcall(fn) if ok then return r end return {error=tostring(r)} end
local function flows(st) return {input=st.input_counts,output=st.output_counts} end
local out={tick=game.tick,map_seed=game.surfaces[1].map_gen_settings.seed,surfaces={}}
out.ticks_played=try(function() return game.ticks_played end)
out.speed=game.speed
out.mods=try(function() return script.active_mods end)
out.technologies=try(function() local t={} for n,x in pairs(f.technologies) do t[n]={researched=x.researched,level=x.level} end return t end)
out.research=try(function() local q={} for _,x in pairs(f.research_queue) do q[#q+1]=x.name end
return {current=f.current_research and f.current_research.name,progress=f.research_progress,queue=q} end)
out.entity_counts=try(function() local c={} for n in pairs(prototypes.entity) do local k=f.get_entity_count(n) if k>0 then c[n]=k end end return c end)
out.platforms=try(function() local p={} for _,x in pairs(f.platforms) do p[#p+1]={name=x.name,surface=x.surface and x.surface.name,
space_location=x.space_location and x.space_location.name,state=x.state,speed=x.speed,
hub=x.hub and x.hub.get_inventory(defines.inventory.hub_main).get_contents()} end return p end)
out.players=try(function() local p={} for _,x in pairs(game.players) do p[#p+1]={name=x.name,connected=x.connected,surface=x.surface.name,position=x.position} end return p end)
for _,s in pairs(game.surfaces) do local o={}
o.items=try(function() return flows(f.get_item_production_statistics(s)) end)
o.fluids=try(function() return flows(f.get_fluid_production_statistics(s)) end)
o.kills=try(function() return flows(f.get_kill_count_statistics(s)) end)
o.builds=try(function() return flows(f.get_entity_build_count_statistics(s)) end)
o.pollution_stats=try(function() return flows(game.get_pollution_statistics(s)) end)
o.pollution_total=try(function() return s.get_total_pollution() end)
o.evolution=try(function() return {factor=enemy.get_evolution_factor(s),by_time=enemy.get_evolution_factor_by_time(s),
by_pollution=enemy.get_evolution_factor_by_pollution(s),by_killing_spawners=enemy.get_evolution_factor_by_killing_spawners(s)} end)
o.power=try(function() local nets={} for _,p in pairs(s.find_entities_filtered{type='electric-pole',force=f}) do
local id=p.electric_network_id and tostring(p.electric_network_id)
if id and not nets[id] then nets[id]=flows(p.electric_network_statistics) end end return nets end)
o.logistic_networks=try(function() local r={} for _,n in pairs(f.logistic_networks[s.name] or {}) do
r[#r+1]={network_id=n.network_id,all_logistic_robots=n.all_logistic_robots,available_logistic_robots=n.available_logistic_robots,
all_construction_robots=n.all_construction_robots,available_construction_robots=n.available_construction_robots,
robot_limit=n.robot_limit,contents=n.get_contents()} end return r end)
out.surfaces[s.name]=o end
rcon.print(helpers.table_to_json(out))
""".split())

PRECISIONS = ["five_seconds", "one_minute", "ten_minutes", "one_hour", "ten_hours",
              "fifty_hours", "two_hundred_fifty_hours", "one_thousand_hours"]

# Per-surface flow history: every name's 300 samples (index 1 = newest) from get_flow_count with count=true.
# stop_error records why sampling stopped early for a name, if it did.
HISTORY_LUA = "/sc " + " ".join("""
local f=game.forces.player local s=game.surfaces[%s] local P=defines.flow_precision_index.%s
local function try(fn) local ok,r=pcall(fn) if ok then return r end return {error=tostring(r)} end
local function hist(st) local r={} for _,cat in pairs({'input','output'}) do local c={}
for n in pairs(st[cat..'_counts']) do local a={} for i=1,300 do
local ok,v=pcall(st.get_flow_count,{name=n,category=cat,precision_index=P,sample_index=i,count=true})
if not ok then a={samples=a,stop_error=tostring(v)} break end a[i]=v end c[n]=a end r[cat]=c end return r end
local o={}
o.items=try(function() return hist(f.get_item_production_statistics(s)) end)
o.fluids=try(function() return hist(f.get_fluid_production_statistics(s)) end)
o.kills=try(function() return hist(f.get_kill_count_statistics(s)) end)
o.builds=try(function() return hist(f.get_entity_build_count_statistics(s)) end)
o.pollution_stats=try(function() return hist(game.get_pollution_statistics(s)) end)
o.power=try(function() local nets={} for _,p in pairs(s.find_entities_filtered{type='electric-pole',force=f}) do
local id=p.electric_network_id and tostring(p.electric_network_id)
if id and not nets[id] then nets[id]=hist(p.electric_network_statistics) end end return nets end)
rcon.print(helpers.table_to_json(o))
""".split())

HEADER_LUA = (
    "/sc local n={} for _,s in pairs(game.surfaces) do n[#n+1]=s.name end "
    "rcon.print(helpers.table_to_json({tick=game.tick,map_seed=game.surfaces[1].map_gen_settings.seed,surfaces=n}))"
)


def take_snapshot(client: factorio_rcon.RCONClient, lua: str = SNAPSHOT_LUA) -> dict:
    raw = client.send_command(lua)
    if not raw:
        # The first /sc on a save is swallowed by the achievement warning; resend once.
        raw = client.send_command(lua)
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
    parser.add_argument("--out", type=Path, help="override the per-save data/<seed>/snapshots.jsonl path")
    parser.add_argument("--print", action="store_true", help="print each raw snapshot as it is saved")
    parser.add_argument("--dump", action="store_true", help="save one full raw dump to data/<seed>/dump-<tick>.json and exit")
    parser.add_argument("--history", choices=PRECISIONS + ["all"],
                        help="save the game's 300-sample flow history at this precision to "
                        "data/<seed>/history-<precision>-<tick>.json and exit")
    args = parser.parse_args()
    if not args.password:
        parser.error("set --password or FACTORIO_RCON_PASSWORD")

    client = factorio_rcon.RCONClient(args.host, args.port, args.password, timeout=60, connect_on_init=False)

    if args.history:
        precisions = PRECISIONS if args.history == "all" else [args.history]
        if args.out and len(precisions) > 1:
            parser.error("--out can't be used with --history all")
        client.connect()
        for precision in precisions:
            history = take_snapshot(client, HEADER_LUA)
            history["precision"] = precision
            history["surfaces"] = {
                name: take_snapshot(client, HISTORY_LUA % (json.dumps(name), precision))
                for name in history["surfaces"]
            }
            out = args.out or DATA_DIR / str(history["map_seed"]) / f"history-{precision}-{history['tick']}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(history))
            print(f"tick={history['tick']} {out.stat().st_size} bytes -> {out}")
        return

    if args.dump:
        client.connect()
        dump = take_snapshot(client, DUMP_LUA)
        out = args.out or DATA_DIR / str(dump["map_seed"]) / f"dump-{dump['tick']}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dump))
        print(f"tick={dump['tick']} {out.stat().st_size} bytes -> {out}")
        return

    while True:
        try:
            if client.rcon_socket is None:
                client.connect()
            snapshot = take_snapshot(client)
            out = args.out or DATA_DIR / str(snapshot["map_seed"]) / "snapshots.jsonl"
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("a") as f:
                f.write(json.dumps(snapshot) + "\n")
            if args.print:
                print(json.dumps(snapshot, indent=1))
            else:
                print(f"tick={snapshot['tick']} surfaces={len(snapshot['surfaces'])} -> {out}")
        except factorio_rcon.RCONNetworkError as exc:
            print(f"RCON unavailable ({exc}); retrying")
            client.close()
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
