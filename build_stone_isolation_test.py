"""Isolation test: does a plain 'minecraft:stone' block (no properties)
paste and read back correctly on its own, independent of the XOR
build's complexity? If this minimal case also reads as air, it's a
clean, reportable MCHPRS/mineflayer bug, not something specific to the
XOR schematic.

Layout: lever (reference point, known-good from every prior test) at
(0,0,0)-ish, plain stone block at (2,0,0), redstone_lamp at (4,0,0).
"""
from schem import Schematic

s = Schematic()
s.set(0, 0, 0, "minecraft:lever[face=floor,facing=north,powered=false]")
s.set(1, 0, 0, "minecraft:stone")
s.set(1, 1, 0, "minecraft:stone")
s.set(2, 0, 0, "minecraft:stone")
s.set(3, 0, 0, "minecraft:redstone_lamp[lit=false]")
s.set(4, 0, 0, "minecraft:redstone_torch[lit=true]")

s.save("stone_isolation_test.schem")
print("wrote stone_isolation_test.schem")
print("LEVER=(0,0,0) STONE1=(1,0,0) STONE2=(1,1,0) STONE3=(2,0,0) LAMP=(3,0,0) TORCH=(4,0,0)")
