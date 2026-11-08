"""Smallest possible redstone circuit, to validate the whole pipeline
(schematic load via //load, bot flips a lever, bot reads a lamp) before
anything SHA-1-related is attempted.

Layout (y=0 floor, lever+lamp at y=1):
  (0,0,0) stone        (1,0,0) stone
  (0,1,0) lever(floor)  (1,1,0) redstone_lamp

A lever directly powers an adjacent mechanism block (lamp), same as a
button would -- no wire needed for this minimal test.
"""
from schem import Schematic

s = Schematic()
s.set(0, 0, 0, "minecraft:stone")
s.set(1, 0, 0, "minecraft:stone")
s.set(0, 1, 0, "minecraft:lever[face=floor,facing=north,powered=false]")
s.set(1, 1, 0, "minecraft:redstone_lamp[lit=false]")
s.save("lamp_test.schem")
print("wrote lamp_test.schem")
