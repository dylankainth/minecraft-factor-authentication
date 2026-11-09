"""Precise isolation: lever -> repeater (refreshes to 15) -> 5 PURE DUST
hops (decaying 15->10, no repeaters) -> lamp. Does the dust chain
correctly drop all the way to 0 when the lever turns off, or does it
stick at a decayed-but-nonzero floor (matching the exact symptom seen
in the XOR gate's raw_B staircase: power=10 regardless of input)?
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
SA = (0, 0, 0)
s.set(*SA, "minecraft:stone")
lever_pos = (SA[0], SA[1] + 1, SA[2])
s.set(*lever_pos, "minecraft:lever[face=floor,facing=north,powered=false]")
dust_pos = rp._add(lever_pos, rp.EAST)
rp.floor_under(s, dust_pos)
s.set(*dust_pos, "minecraft:redstone_wire[power=0]")

# one repeater hop (refreshes to 15)
rep_pos, after_rep = rp.extend_repeater(s, dust_pos, rp.EAST)

# 5 pure dust hops, no repeaters, each placed by hand (not step() -- same
# height, just plain dust in a row) to decay 15 -> 10
cur = after_rep
rp.floor_under(s, cur)
s.set(*cur, "minecraft:redstone_wire[power=0]")
for _ in range(4):
    cur = rp._add(cur, rp.EAST)
    rp.floor_under(s, cur)
    s.set(*cur, "minecraft:redstone_wire[power=0]")

lamp = rp._add(cur, rp.EAST)
rp.floor_under(s, lamp)
s.set(*lamp, "minecraft:redstone_lamp[lit=false]")

s.save("repeater_then_dust_test.schem")
print(f"wrote repeater_then_dust_test.schem: lever={lever_pos} rep={rep_pos} last_dust={cur} lamp={lamp}")
