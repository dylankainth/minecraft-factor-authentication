"""Term1 sub-circuit (works perfectly in isolation, build_term1_isolated_test.py)
PLUS the full raw_A and NOT_B chains from the real XOR gate, built exactly
as in build_xor_gate_test.py but left DANGLING (not connected to any S2) --
isolates whether merely having those other two chains PRESENT (adjacent to
Term1's chains) breaks it, vs. something in how S2/Term2/the final merge
specifically wires up.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()

SA = (0, 1, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]

dustRAW_A = rp.place_raw_tap(s, leverA, rp.EAST)
rawA = rp.step(s, dustRAW_A, rp.EAST, up=True)
rp.travel(s, rawA, (150, 2, 0), land_as="dust")  # dangling, matches real gate's length

SB = (0, 1, 30)
notB = rp.place_not(s, SB, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverB, dustB1 = notB["lever"], notB["dust"]
dustRAW_B = rp.place_raw_tap(s, leverB, rp.EAST)
rawB = rp.step(s, dustRAW_B, rp.EAST, up=True)

wpB2a = rp.travel(s, dustB1, (2, 2, 31), land_as="dust")  # dangling, matches real gate's NOT_B leg
rp.travel(s, wpB2a, (2, 2, 90), land_as="dust")

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

s.save("term1_plus_dangling_test.schem")
print(f"wrote term1_plus_dangling_test.schem: leverA={leverA} leverB={leverB} term1_torch={term1_torch} lamp={lamp}")
