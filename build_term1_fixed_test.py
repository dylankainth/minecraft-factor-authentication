"""Isolated Term1 with settle hop after the rawB step.

Term1 = NOT(NOT_A OR B) = AND(A, NOT_B).
  NOT_A: lever A -> standing-torch NOT -> dust (clean signal)
  B:     lever B -> raw tap -> step -> settle hop -> repeaters -> merge stone S1
  S1:    merge stone, NOT_A and B each via own repeater (no shared dust)
  Term1: standing torch on S1 = NOT(NOT_A OR B)
  lamp:  dust east of torch

Tests whether the merge-stone torch reliably depowers/relights when one input
is a raw lever signal (via step+settle) and the other is a NOT output.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()

SA = (0, 1, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]

SB = (0, 1, 30)
leverB = (SB[0] + 1, SB[1], SB[2])
s.set(*SB, "minecraft:stone")
s.set(*leverB, "minecraft:lever[face=wall,facing=west,powered=false]")

dustRAW_B = rp.place_raw_tap(s, leverB, rp.EAST)  # (2,1,30)
rawB_step = rp.step(s, dustRAW_B, rp.EAST, up=True)  # (3,2,30) step landing
# settle hop: landing cell -> plain dust -> first repeater
rawB_settle = rp._add(rawB_step, rp.SOUTH)  # (3,2,31)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle

S1 = (50, 2, 50)
rp.converge(s, S1)
wpA1 = rp.travel(s, dustA1, (50, 2, 1), land_as="dust")
rp.travel(s, wpA1, S1)  # NOT_A approaches from north
wpB1 = rp.travel(s, rawB, (3, 2, 50), land_as="dust")
rp.travel(s, wpB1, S1)  # B approaches from west

term1_torch = (S1[0], S1[1] + 1, S1[2])
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")
lamp1 = (term1_dust[0] + 1, term1_dust[1], term1_dust[2])
rp.floor_under(s, lamp1)
s.set(*lamp1, "minecraft:redstone_lamp[lit=false]")

s.save("term1_fixed_test.schem")
print("wrote term1_fixed_test.schem")
print(f"leverA={leverA} leverB={leverB} torchA={notA['torch']}")
print(f"S1={S1} term1_torch={term1_torch} lamp1={lamp1}")
print(f"rawB_settle={rawB_settle}")
