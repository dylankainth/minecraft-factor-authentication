"""Sanity check, round 2: a bare lever directly feeding a repeater left
repeater.powered false even after a real transition (round 1, no dust in
between). Matches the established pattern -- a lever directly powers
adjacent DUST (proven in dust_test.schem) but maybe not an adjacent
REPEATER directly. Test lever -> dust -> repeater -> lamp this time.
"""
from schem import Schematic

s = Schematic()
for x, z in [(0, 0), (0, 1), (0, 2), (0, 3)]:
    s.set(x, 0, z, "minecraft:stone")
s.set(0, 1, 0, "minecraft:lever[face=floor,facing=north,powered=false]")
s.set(0, 1, 1, "minecraft:redstone_wire[power=0]")
s.set(0, 1, 2, "minecraft:repeater[facing=north,powered=false,locked=false,delay=1]")
s.set(0, 1, 3, "minecraft:redstone_lamp[lit=false]")
s.save("repeater_test.schem")
print("wrote repeater_test.schem: lever(0,1,0) -> dust(0,1,1) -> repeater(0,1,2)[facing=south] -> lamp(0,1,3)")
