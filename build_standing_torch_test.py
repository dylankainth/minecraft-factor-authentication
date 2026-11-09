"""Differential test: does a STANDING torch (on top of a block) correctly
cascade power to an adjacent dust->lamp, where the WALL torch in
not_gate_test.schem reproducibly did not (dust reached power=15, lamp never
lit)? Lever is wall-mounted on the side of the torch's own support block so
toggling it causes a genuine live torch transition (needed to "unstick" the
dust, per the earlier findings), while the torch itself stands on top.

  (0,0,0) stone                          <- torch's support block
  (0,0,1) lever[face=wall,facing=south]  <- wall-mounted on north face of (0,0,0)
  (0,1,0) redstone_torch[lit=true]       <- standing on top of (0,0,0)
  (1,0,0) stone                          <- dust support
  (1,1,0) redstone_wire
  (2,0,0) stone                          <- lamp support
  (2,1,0) redstone_lamp
"""
from schem import Schematic

s = Schematic()
s.set(0, 0, 0, "minecraft:stone")
s.set(1, 0, 0, "minecraft:stone")
s.set(2, 0, 0, "minecraft:stone")
s.set(0, 0, 1, "minecraft:lever[face=wall,facing=south,powered=false]")
s.set(0, 1, 0, "minecraft:redstone_torch[lit=true]")
s.set(1, 1, 0, "minecraft:redstone_wire[power=0]")
s.set(2, 1, 0, "minecraft:redstone_lamp[lit=false]")
s.save("standing_torch_test.schem")
print("wrote standing_torch_test.schem: lever(0,0,1) -> torch(0,1,0) -> dust(1,1,0) -> lamp(2,1,0)")
