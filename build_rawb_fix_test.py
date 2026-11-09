"""Confirm the fix for the staircase-landing-cell bug found in
build_rawb_lamp_test.py: a dust cell that is itself the landing point of
a diagonal step() doesn't reliably power horizontal (same-y) neighbors
-- only the cell directly above it. Fix: add ONE plain same-height dust
hop after the staircase lands, before connecting sideways to anything.
This mirrors raw_B's real path but with that one extra hop inserted.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
SA = (0, 5, 0)
s.set(*SA, "minecraft:stone")
lever_pos = (SA[0], SA[1] + 1, SA[2])
s.set(*lever_pos, "minecraft:lever[face=floor,facing=north,powered=false]")
dust_pos = rp._add(lever_pos, rp.EAST)
rp.floor_under(s, dust_pos)
s.set(*dust_pos, "minecraft:redstone_wire[power=0]")

raw = rp.step(s, dust_pos, rp.EAST, up=True)
stage = rp.travel(s, raw, (raw[0] + 6, raw[1], raw[2]), land_as="dust")
stage2 = rp.travel(s, stage, (stage[0], stage[1], stage[2] + 3), land_as="dust")

def step_down_to(start, target_y, direction):
    cur = start
    while cur[1] > target_y:
        cur = rp.step(s, cur, direction, up=False)
    return cur

low = step_down_to(stage2, 2, rp.SOUTH)

# THE FIX: one plain same-height dust hop east, off the staircase landing
settle = rp._add(low, rp.EAST)
rp.floor_under(s, settle)
s.set(*settle, "minecraft:redstone_wire[power=0]")

lamp = rp._add(settle, rp.EAST)
rp.floor_under(s, lamp)
s.set(*lamp, "minecraft:redstone_lamp[lit=false]")

s.save("rawb_fix_test.schem")
xs = [p[0] for p in s.blocks]; ys = [p[1] for p in s.blocks]; zs = [p[2] for p in s.blocks]
minx, miny, minz = min(xs), min(ys), min(zs)
def local(p):
    return (p[0]-minx, p[1]-miny, p[2]-minz)
print(f"lever={local(lever_pos)} low={local(low)} settle={local(settle)} lamp={local(lamp)}")
