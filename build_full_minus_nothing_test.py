"""Same S1/S2/Term1/Term2 as term1_plus_s2_test.schem (proven correct
individually) but with Term1 ALONE routed the long way to a lamp
(matching the real gate's term1->LAMP leg exactly, same distance) --
Term2 is left dangling, not merged in. Isolates whether a single long
final leg works, vs. specifically the 2-source merge at the lamp.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()

SA = (0, 1, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]
dustRAW_A = rp.place_raw_tap(s, leverA, rp.EAST)
rawA = rp.step(s, dustRAW_A, rp.EAST, up=True)

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

S2 = (50, 2, 90)
rp.converge(s, S2)
wpA2a = rp.travel(s, rawA, (150, 2, 0), land_as="dust")
wpA2b = rp.travel(s, wpA2a, (150, 2, 90), land_as="dust")
rp.travel(s, wpA2b, S2)
wpB2a = rp.travel(s, dustB1, (2, 2, 31), land_as="dust")
wpB2b = rp.travel(s, wpB2a, (2, 2, 90), land_as="dust")
rp.travel(s, wpB2b, S2)
term2_torch = (S2[0], S2[1] + 1, S2[2])
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0], term2_torch[1], term2_torch[2] - 1)
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

LAMP = (100, 3, 50)
rp.converge(s, LAMP, "minecraft:redstone_lamp[lit=false]")
rp.travel(s, term1_dust, LAMP)
# term2_dust intentionally left dangling (not merged into LAMP) --
# testing a single long final leg, not the 2-source merge.

s.save("full_minus_nothing_test.schem")
print(f"leverA={leverA} leverB={leverB} term1_torch={term1_torch} term2_torch={term2_torch} lamp={LAMP}")
