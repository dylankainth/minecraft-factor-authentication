"""Differential test: lever -> dust -> dust -> lamp (two dust hops, lever-
sourced). The single-hop lever->dust->lamp case is already verified working
(dust_test.schem). The not-gate test's torch->dust->lamp (one hop from the
torch) reproducibly shows the dust reaching power=15 but the lamp never
lighting. This isolates whether that's specific to torch-sourced power, or
a general "power doesn't propagate past the first dust hop" limitation.
"""
from schem import Schematic

s = Schematic()
for x in range(4):
    s.set(x, 0, 0, "minecraft:stone")
s.set(0, 1, 0, "minecraft:lever[face=floor,facing=north,powered=false]")
s.set(1, 1, 0, "minecraft:redstone_wire[power=0]")
s.set(2, 1, 0, "minecraft:redstone_wire[power=0]")
s.set(3, 1, 0, "minecraft:redstone_lamp[lit=false]")
s.save("dust_chain_test.schem")
print("wrote dust_chain_test.schem: lever(0,1,0) -> dust(1,1,0) -> dust(2,1,0) -> lamp(3,1,0)")
