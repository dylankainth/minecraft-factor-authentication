"""Builds a minimal <name>.server.json for the saucefishman/MCHPRS fork's
native `/load <name>.litematic -c` and `/lever <name> [on|off|toggle]`
commands, from this project's own pins.txt (MineRTL's synth.sh doesn't write
one unless the build has debug probes or a server-driven clock -- see
MineRTL/minecraft_v/placement_engine/builder.py's `if resolved_probes or
clock_entry:` gate -- neither of which this project's builds use).

Only needs the "levers" field: {"name": ..., "pos": [x,y,z]} for every INPUT
pin (one whose pins.txt row has a real lever at cell+(nx,1,nz) -- per the
fork's crates/headless/README.md convention this project's own probe scripts
already use). Positions are relative to the schematic's minimum corner, same
frame pins.txt itself uses.

Usage:
    python3 scripts_make_server_json.py <pins.txt> <width> <height> <length> <out.server.json>
"""
import json
import sys


def build(pins_path, width, height, length, out_path):
    levers = []
    with open(pins_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            name, x, y, z, nx, nz = line.split()
            x, y, z, nx, nz = int(x), int(y), int(z), int(nx), int(nz)
            if name == "clk":
                continue  # no lever in a --no-server-clock build
            lever_pos = [x + nx, y + 1, z + nz]
            levers.append({"name": name, "pos": lever_pos})

    data = {
        "version": 2,
        "schematic_size": [width, height, length],
        "probes": [],
        "levers": levers,
    }
    with open(out_path, "w") as f:
        json.dump(data, f)
    print(f"wrote {out_path}: {len(levers)} levers")


if __name__ == "__main__":
    build(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
