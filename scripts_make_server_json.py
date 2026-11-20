"""Builds a minimal <name>.server.json for the saucefishman/MCHPRS fork's
native `/load <name>.litematic -c` and `/lever <name> [on|off|toggle]`
commands, from this project's own pins.txt (MineRTL's synth.sh doesn't write
one unless the build has debug probes or a server-driven clock -- see
MineRTL/minecraft_v/placement_engine/builder.py's `if resolved_probes or
clock_entry:` gate -- neither of which this project's builds use).

Only needs the "levers" field: {"name": ..., "pos": [x,y,z]}. A pins.txt row
is an input (gets a lever) only if the schematic actually has one at
cell+(nx,1,nz) -- per crates/headless/README.md's own rule ("A pin is an
input if there is a lever at cell + (nx, 1, nz), otherwise an output") --
NOT just "every pin that isn't clk" (output pins like code[i]/done outnumber
real inputs and must be excluded, or /lever will offer to drive outputs).
Positions are relative to the schematic's minimum corner, same frame
pins.txt itself uses.

Usage:
    python3 scripts_make_server_json.py <litematic> <pins.txt> <out.server.json>
"""
import json
import sys

import litemapy


def build(litematic_path, pins_path, out_path):
    schem = litemapy.Schematic.load(litematic_path)
    # merge all regions the same way scripts_litematic_to_schem.py does, so
    # block lookups below see the final, post-overlay state
    blocks = {}
    for region in schem.regions.values():
        rx, ry, rz = region.x, region.y, region.z
        for (lx, ly, lz) in region.block_positions():
            blocks[(rx + lx, ry + ly, rz + lz)] = region[lx, ly, lz].id

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
            lever_pos = (x + nx, y + 1, z + nz)
            if blocks.get(lever_pos) != "minecraft:lever":
                continue  # output pin, or an input whose fixture failed to place
            levers.append({"name": name, "pos": list(lever_pos)})

    data = {
        "version": 2,
        "schematic_size": [schem.width, schem.height, schem.length],
        "probes": [],
        "levers": levers,
    }
    with open(out_path, "w") as f:
        json.dump(data, f)
    print(f"wrote {out_path}: {len(levers)} levers")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])
