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
# Two tiles were nudged by the router during placement (confirmed by
# decoding the litematic directly and finding the real lamp cluster
# offset from its nominal anchor).
placed = json.load(open(pin_targets_placed_path))
anchor_fixups = {"seg5[4]": (-1, -1), "seg1[1]": (-2, 0)}
for name, pos in sorted(placed.items()):
    dx, dy = anchor_fixups.get(name, (0, 0))
    lines.append(f"{name} {pos[0] + dx} {pos[1] + dy} {pos[2]} 0 0")

print("\n".join(lines))
