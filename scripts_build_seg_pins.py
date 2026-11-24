import json
import gzip
import sys

artifacts_dir = sys.argv[1]
pin_targets_placed_path = sys.argv[2]

layout = json.load(gzip.open(f"{artifacts_dir}/component_layout.json.gz"))
by_name = {c["id"]: c for c in layout if c["type"] in ("INPUT_PIN", "OUTPUT_PIN")}

lines = []

# Inputs: pins.txt pos = INPUT_PIN origin + (0,0,1); nx,nz carried from the
# established convention (lever = pos + (nx,1,nz)).
def inp(name, nx, nz):
    o = by_name[name]["origin"]
    lines.append(f"{name} {o[0]} {o[1]} {o[2] + 1} {nx} {nz}")

inp("clk", 0, 1)
inp("rst", 0, 1)
inp("start", 0, 1)
for i in range(32):
    inp(f"counter[{i}]", 0, 1)

# Outputs not using pin_targets (done, code[i]): origin direct, nz=-2.
# Empirically verified by decoding the litematic directly: the component's
# origin is the output REPEATER, and the real lamp sits one more block
# further in -z (-1 undershoots onto the repeater itself, not the lamp).
def outp(name, nx, nz):
    o = by_name[name]["origin"]
    lines.append(f"{name} {o[0]} {o[1]} {o[2]} {nx} {nz}")

outp("done", 0, -2)
for i in range(20):
    outp(f"code[{i}]", 0, -2)

# seg0-5: stores the tile's lower-left ANCHOR position (nx=nz=0), matching
# pin_targets_placed.json directly. The tile is a 3x3 of lamps
# (_lamp_tile) and only the MIDDLE lamp (anchor + (1,1)) is actually driven
# by the wire, per the engine's own docstring -- readers (see
# bot/totp_read_seg_single.js's outputPos) apply that +1,+1 themselves.
# NOTE: an earlier version of this script applied hand-found "fixups" to
# seg5[4] and seg1[1], based on finding the nearest real lamp block to the
# nominal anchor in a decoded litematic. That methodology was WRONG and has
# been removed: a 3x3 tile has 9 clustered lamp blocks, so "nearest lamp"
# always finds *something* even when the nominal (un-adjusted) anchor is
# already correct. Confirmed via mchprs_headless's `expect` against the
# actual compiled circuit (fast, deterministic, no fixup needed) that the
# plain anchor + (1,1) formula is correct for every one of the 42 segments.
placed = json.load(open(pin_targets_placed_path))
for name, pos in sorted(placed.items()):
    lines.append(f"{name} {pos[0]} {pos[1]} {pos[2]} 0 0")

print("\n".join(lines))
