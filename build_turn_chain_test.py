"""Isolate whether a turned chain (travel + dust waypoint + travel, same
shape as NOT_A's route to S1 in the XOR gate) breaks a FALLING edge
specifically, even though a pure straight 50-hop chain (build_long_chain_test.py)
proved both directions work fine. lever -> dust -> travel east 20 ->
dust waypoint (turn) -> travel south 20 -> lamp.
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

turn = rp.travel(s, dust_pos, (dust_pos[0] + 20, dust_pos[1], dust_pos[2]), land_as="dust")
target = (turn[0], turn[1], turn[2] + 20)
rp.travel(s, turn, target)
rp.floor_under(s, target)
s.set(*target, "minecraft:redstone_lamp[lit=false]")

s.save("turn_chain_test.schem")
print(f"wrote turn_chain_test.schem: lever={lever_pos} turn={turn} lamp={target}")
