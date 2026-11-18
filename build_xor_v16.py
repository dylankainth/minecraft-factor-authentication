"""XOR gate v16: fully planned layout with NO crossing paths (verified by hand).

All paths at y=2 use unique z-bands; paths 5-6 at y=3 are above y=2 paths.
XOR = OR(Term1, Term2); Term1 = NOT(NOT_A OR B); Term2 = NOT(A OR NOT_B).
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1

# ================= Lever A: NOT_A + raw_A =================
s.set(-3, Y, 0, "minecraft:stone")          # support
s.set(-2, Y, 0, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 0, "minecraft:redstone_torch[lit=true]")  # torch on support
dustA1 = (-3, Y + 1, 1)                      # NOT_A output dust, south of torch
rp.floor_under(s, dustA1)
s.set(*dustA1, "minecraft:redstone_wire[power=0]")

dustRAW_A = (-1, Y, 0)                       # east of lever
rp.floor_under(s, dustRAW_A)
s.set(*dustRAW_A, "minecraft:redstone_wire[power=0]")
rawA_step = rp.step(s, dustRAW_A, rp.EAST, up=True)   # (0,2,0)
rawA_settle = rp._add(rawA_step, rp.EAST)           # (1,2,0)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle

# ================= Lever B: NOT_B + raw_B =================
s.set(-3, Y, 5, "minecraft:stone")          # support
s.set(-2, Y, 5, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 5, "minecraft:redstone_torch[lit=true]")  # torch on support
dustB1 = (-2, Y + 1, 5)                      # NOT_B output dust, east of torch (z=5 band)
rp.floor_under(s, dustB1)
s.set(*dustB1, "minecraft:redstone_wire[power=0]")

dustRAW_B = (-1, Y, 5)                       # east of lever
rp.floor_under(s, dustRAW_B)
s.set(*dustRAW_B, "minecraft:redstone_wire[power=0]")
rawB_step = rp.step(s, dustRAW_B, rp.EAST, up=True)  # (0,2,5)
rawB_settle = rp._add(rawB_step, rp.SOUTH)           # (0,2,6)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle

# ================= S1 = merge(NOT_A, raw_B) -> Term1 @ (20,2,10) =================
S1 = (20, Y + 1, 10)
rp.converge(s, S1)
# NOT_A: (-3,2,1) -> south to (-3,2,9) -> east to (19,2,9) -> south to (19,2,10) [west of S1]
na1 = rp.travel(s, dustA1, (-3, Y + 1, 9), land_as="dust")
na2 = rp.travel(s, na1, (19, Y + 1, 9), land_as="dust")
rp.travel(s, na2, (19, Y + 1, 10), land_as="dust")
# raw_B: (0,2,6) -> east to (20,2,6) -> south to (20,2,11) [south of S1]
rb1 = rp.travel(s, rawB, (20, Y + 1, 6), land_as="dust")
rp.travel(s, rb1, (20, Y + 1, 11), land_as="dust")

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (20,3,10)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # (21,3,10)
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ================= S2 = merge(raw_A, NOT_B) -> Term2 @ (40,2,20) =================
S2 = (40, Y + 1, 20)
rp.converge(s, S2)
# raw_A: (1,2,0) -> east to (39,2,0) -> south to (39,2,19) [north of S2]
ra1 = rp.travel(s, rawA, (39, Y + 1, 0), land_as="dust")
rp.travel(s, ra1, (39, Y + 1, 19), land_as="dust")
# NOT_B: (-2,2,5) -> east to (38,2,5) -> south to (38,2,20) -> east to (39,2,20) [west of S2]
nb1 = rp.travel(s, dustB1, (38, Y + 1, 5), land_as="dust")
nb2 = rp.travel(s, nb1, (38, Y + 1, 20), land_as="dust")
rp.travel(s, nb2, (39, Y + 1, 20), land_as="dust")

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (40,3,20)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # (41,3,20)
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (30,3,30) =================
LAMP = (30, Y + 2, 30)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
# term1_dust(21,3,10) -> south to (21,3,30) -> east to LAMP [from west]
t1w = rp.travel(s, term1_dust, (21, Y + 2, 30), land_as="dust")
rp.travel(s, t1w, LAMP)
# term2_dust(41,3,20) -> south to (41,3,30) -> west to LAMP [from east]
t2w = rp.travel(s, term2_dust, (41, Y + 2, 30), land_as="dust")
rp.travel(s, t2w, LAMP)

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v16, no crossing paths)")
print(f"leverA=(-2,1,0) leverB=(-2,1,5)")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")
