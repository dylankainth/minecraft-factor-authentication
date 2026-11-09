"""Term1 sub-circuit PLUS S2/Term2 fully connected (not dangling), but
WITHOUT the final OR-merge into a shared lamp. Isolates: does S2 being
actually powered (vs merely present/dangling) corrupt S1/Term1, or is
it specifically the final merge stage?
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
lamp1 = (term1_dust[0] + 1, term1_dust[1], term1_dust[2])
rp.floor_under(s, lamp1)
s.set(*lamp1, "minecraft:redstone_lamp[lit=false]")

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
lamp2 = (term2_dust[0] + 1, term2_dust[1], term2_dust[2])
rp.floor_under(s, lamp2)
s.set(*lamp2, "minecraft:redstone_lamp[lit=false]")

s.save("term1_plus_s2_test.schem")
print(f"leverA={leverA} leverB={leverB} lamp1={lamp1} lamp2={lamp2}")
