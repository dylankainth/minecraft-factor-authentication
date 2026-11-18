"""XOR gate v11: fully separated signal paths, verified compile.

All paths use their own z-band; merges only at S1/S2/LAMP.
Settle hop after every step.

  XOR = OR(Term1, Term2)
    Term1 = NOT(NOT_A OR B)   -- S1 @ (150,2,30)
    Term2 = NOT(A OR NOT_B)   -- S2 @ (100,2,25)
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1

# ================= Lever A: NOT_A + raw_A =================
s.set(-1, Y, 0, "minecraft:stone")  # support
leverA = (0, Y, 0)
s.set(*leverA, "minecraft:lever[face=wall,facing=east,powered=false]")
torchA = (-1, Y + 1, 0)
s.set(*torchA, "minecraft:redstone_torch[lit=true]")
dustA1 = rp._add(torchA, rp.SOUTH)  # (-1,2,1) NOT_A output dust
rp.floor_under(s, dustA1)
s.set(*dustA1, "minecraft:redstone_wire[power=0]")

dustRAW_A = rp._add(leverA, rp.EAST)  # (1,1,0)
rp.floor_under(s, dustRAW_A)
s.set(*dustRAW_A, "minecraft:redstone_wire[power=0]")
rawA_step = rp.step(s, dustRAW_A, rp.EAST, up=True)  # (2,2,0)
rawA_settle = rp._add(rawA_step, rp.EAST)  # (3,2,0)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # (3,2,0)

# ================= Lever B: NOT_B + raw_B =================
s.set(-1, Y, 10, "minecraft:stone")  # support
leverB = (0, Y, 10)
s.set(*leverB, "minecraft:lever[face=wall,facing=east,powered=false]")
torchB = (-1, Y + 1, 10)
s.set(*torchB, "minecraft:redstone_torch[lit=true]")
dustB1 = (-1, Y + 1, 12)  # NOT_B output dust, south of torch
rp.floor_under(s, dustB1)
s.set(*dustB1, "minecraft:redstone_wire[power=0]")

dustRAW_B = rp._add(leverB, rp.EAST)  # (1,1,10)
rp.floor_under(s, dustRAW_B)
s.set(*dustRAW_B, "minecraft:redstone_wire[power=0]")
rawB_step = rp.step(s, dustRAW_B, rp.EAST, up=True)  # (2,2,10)
rawB_settle = rp._add(rawB_step, rp.SOUTH)  # (2,2,11)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle  # (2,2,11)

# ================= S1 = merge(NOT_A, raw_B) -> Term1 @ (150,2,30) =================
S1 = (150, Y + 1, 30)
rp.converge(s, S1)
# NOT_A: (-1,2,1) -> south to (-1,2,26) -> east to (150,2,26) -> south to S1(150,2,30)  [from north]
na1 = rp.travel(s, dustA1, (-1, Y + 1, 26), land_as="dust")
na2 = rp.travel(s, na1, (150, Y + 1, 26), land_as="dust")
rp.travel(s, na2, S1)
# rawB: (2,2,11) -> west to (0,2,11) -> south to (0,2,30) -> east to S1(150,2,30)  [from west]
rb1 = rp.travel(s, rawB, (0, Y + 1, 11), land_as="dust")
rb2 = rp.travel(s, rb1, (0, Y + 1, 30), land_as="dust")
rp.travel(s, rb2, S1)

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (150,3,30)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # east of torch
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ================= S2 = merge(raw_A, NOT_B) -> Term2 @ (100,2,25) =================
S2 = (100, Y + 1, 25)
rp.converge(s, S2)
# rawA: (3,2,0) -> east to (100,2,0) -> south to S2(100,2,25)  [from north]
ra1 = rp.travel(s, rawA, (100, Y + 1, 0), land_as="dust")
rp.travel(s, ra1, S2)
# NOT_B: (-1,2,12) -> south to (-1,2,25) -> east to S2(100,2,25)  [from west]
nb1 = rp.travel(s, dustB1, (-1, Y + 1, 25), land_as="dust")
rp.travel(s, nb1, S2)

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (100,3,25)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # east of torch
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (150,3,60) =================
LAMP = (150, Y + 2, 60)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
# term1_dust(151,3,30) -> south -> (151,3,60) -> west -> LAMP(150,3,60)  [from east]
t1w = rp.travel(s, term1_dust, (151, Y + 2, 60), land_as="dust")
rp.travel(s, t1w, LAMP)
# term2_dust(101,3,25) -> south -> (101,3,60) -> east -> LAMP(150,3,60)  [from west]
t2w = rp.travel(s, term2_dust, (101, Y + 2, 60), land_as="dust")
rp.travel(s, t2w, LAMP)

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v11 separated, no crossing paths)")
print(f"leverA={leverA} leverB={leverB}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")
