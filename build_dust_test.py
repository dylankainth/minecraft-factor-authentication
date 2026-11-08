"""Standard lever -> redstone dust -> lamp circuit (the textbook minimal
circuit), since the direct lever/torch-adjacent-to-lamp assumption used in
the earlier smoke/NOT-gate tests was NOT empirically confirmed and the
NOT-gate test showed adjacency-without-dust does not light a lamp."""
from schem import Schematic

s = Schematic()
s.set(0, 0, 0, "minecraft:stone")
s.set(1, 0, 0, "minecraft:stone")
s.set(2, 0, 0, "minecraft:stone")
s.set(0, 1, 0, "minecraft:lever[face=floor,facing=north,powered=false]")
s.set(1, 1, 0, "minecraft:redstone_wire[power=0]")
s.set(2, 1, 0, "minecraft:redstone_lamp[lit=false]")
s.save("dust_test.schem")
print("wrote dust_test.schem: lever(0,1,0) -> dust(1,1,0) -> lamp(2,1,0)")
