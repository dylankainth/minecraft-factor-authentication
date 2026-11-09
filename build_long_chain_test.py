"""Isolate whether a long straight repeater chain (comparable to the
XOR gate's 47-hop raw_B->S1 leg) correctly propagates BOTH a rising and
a falling transition, or gets stuck after the first one. lever -> 50
repeaters -> lamp, straight line.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
SA = (0, 0, 0)
s.set(*SA, "minecraft:stone")
lever_pos = (SA[0], SA[1] + 1, SA[2])  # floor-mounted, directly on top
s.set(*lever_pos, "minecraft:lever[face=floor,facing=north,powered=false]")
dust_pos = rp._add(lever_pos, rp.EAST)  # same height as lever, adjacent
rp.floor_under(s, dust_pos)
s.set(*dust_pos, "minecraft:redstone_wire[power=0]")

target = (dust_pos[0] + 50, dust_pos[1], dust_pos[2])
rp.travel(s, dust_pos, target)
s.set(*target, "minecraft:redstone_lamp[lit=false]")
rp.floor_under(s, target)

s.save("long_chain_test.schem")
print(f"wrote long_chain_test.schem: lever={lever_pos} lamp={target} (50 repeaters between)")
