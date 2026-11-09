"""Isolate the step() primitive itself -- specifically step(up=False),
never independently tested before being used in the (failing) compact
XOR redesign. lever -> dust -> step up x3 -> step down x3 (round trip,
back to the original height) -> lamp. If a lit lever doesn't light the
lamp here, the staircase-down mechanic itself is the bug.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
SA = (0, 1, 0)
s.set(*SA, "minecraft:stone")
lever_pos = (SA[0], SA[1] + 1, SA[2])
s.set(*lever_pos, "minecraft:lever[face=floor,facing=north,powered=false]")
dust_pos = rp._add(lever_pos, rp.EAST)
rp.floor_under(s, dust_pos)
s.set(*dust_pos, "minecraft:redstone_wire[power=0]")

cur = dust_pos
for _ in range(3):
    cur = rp.step(s, cur, rp.EAST, up=True)
print(f"after 3 up-steps: {cur}")
for _ in range(3):
    cur = rp.step(s, cur, rp.EAST, up=False)
print(f"after 3 down-steps (back to original height): {cur}")

target = (cur[0] + 1, cur[1], cur[2])
rp.floor_under(s, target)
s.set(*target, "minecraft:redstone_lamp[lit=false]")

s.save("staircase_test.schem")
print(f"wrote staircase_test.schem: lever={lever_pos} lamp={target}")
