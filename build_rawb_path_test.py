"""Exact replica of raw_B's real path in the XOR compact gate (lever ->
dust -> step up east -> travel east (repeaters) -> travel south
(repeaters) -> staircase down south x5 (pure dust) -> lamp), standalone,
to see if THIS EXACT combination reproduces the stuck-at-decayed-value
bug, when each sub-pattern tested alone (repeater-then-dust-decay;
pure up+down staircase) worked perfectly.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
SA = (0, 5, 0)  # matches the real script's height (SB=Y_BASE+5=6, so raw ends at y=7)
s.set(*SA, "minecraft:stone")
lever_pos = (SA[0], SA[1] + 1, SA[2])
s.set(*lever_pos, "minecraft:lever[face=floor,facing=north,powered=false]")
dust_pos = rp._add(lever_pos, rp.EAST)
rp.floor_under(s, dust_pos)
s.set(*dust_pos, "minecraft:redstone_wire[power=0]")

raw = rp.step(s, dust_pos, rp.EAST, up=True)  # mirrors rawB = step(dustRAW_B, EAST, up=True)

stage = rp.travel(s, raw, (raw[0] + 6, raw[1], raw[2]), land_as="dust")       # mirrors the east travel
stage2 = rp.travel(s, stage, (stage[0], stage[1], stage[2] + 3), land_as="dust")  # mirrors the south travel

def step_down_to(start, target_y, direction):
    cur = start
    while cur[1] > target_y:
        cur = rp.step(s, cur, direction, up=False)
    return cur

low = step_down_to(stage2, 2, rp.SOUTH)  # drop to y=2, mirrors the real script's LOW_Y target (5-level drop)

lamp = rp._add(low, rp.EAST)
rp.floor_under(s, lamp)
s.set(*lamp, "minecraft:redstone_lamp[lit=false]")

s.save("rawb_path_test.schem")
print(f"wrote rawb_path_test.schem: lever={lever_pos} raw={raw} stage={stage} stage2={stage2} low={low} lamp={lamp}")
