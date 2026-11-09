"""Isolated reproduction of JUST the Term1 stage from build_xor_gate_test.py
(NOT_A + raw_B -> S1 -> Term1), using the exact same code path, to find
where the real circuit breaks since the turn-chain primitive in isolation
(build_turn_chain_test.py) proved completely reliable through 4 toggles.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()

SA = (0, 1, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]

SB = (0, 1, 30)
notB = rp.place_not(s, SB, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverB, dustB1 = notB["lever"], notB["dust"]
dustRAW_B = rp.place_raw_tap(s, leverB, rp.EAST)
rawB = rp.step(s, dustRAW_B, rp.EAST, up=True)

S1 = (50, 2, 50)
rp.converge(s, S1)

wpA1 = rp.travel(s, dustA1, (50, 2, 1), land_as="dust")
rp.travel(s, wpA1, S1)

wpB1 = rp.travel(s, rawB, (3, 2, 50), land_as="dust")
rp.travel(s, wpB1, S1)

term1_torch = (S1[0], S1[1] + 1, S1[2])
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")
lamp = (term1_dust[0] + 1, term1_dust[1], term1_dust[2])
rp.floor_under(s, lamp)
s.set(*lamp, "minecraft:redstone_lamp[lit=false]")

s.save("term1_isolated_test.schem")
print(f"wrote term1_isolated_test.schem: leverA={leverA} leverB={leverB} term1_torch={term1_torch} lamp={lamp}")
