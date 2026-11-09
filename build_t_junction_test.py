"""Round 2: plain inert stone as the 3rd neighbor worked fine (dust=15,
lamp lit). Now swap that 3rd neighbor for an UNPOWERED LEVER instead --
matching or_gate_test's real geometry (its "off" lever B) -- to see if an
inactive lever specifically, rather than any solid block, breaks the
single active lever's ability to light the lamp through the junction.
"""
from schem import Schematic

s = Schematic()
for x, z in [(1, 0), (0, 1), (1, 1), (1, 2)]:
    s.set(x, 0, z, "minecraft:stone")
s.set(1, 1, 0, "minecraft:lever[face=floor,facing=north,powered=false]")
s.set(0, 1, 1, "minecraft:lever[face=floor,facing=east,powered=false]")  # inert (off) 2nd lever
s.set(1, 1, 1, "minecraft:redstone_wire[power=0]")
s.set(1, 1, 2, "minecraft:redstone_lamp[lit=false]")
s.save("t_junction_test.schem")
print("wrote t_junction_test.schem: leverA=(1,1,0) leverB_off=(0,1,1) dust=(1,1,1) lamp=(1,1,2)")
