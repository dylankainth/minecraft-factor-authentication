"""XOR gate v7o: widely spaced, no crossing signal paths.

Every signal path uses its own z-band; paths only merge at S1/S2/LAMP.
Settle hop after every step.

  XOR = OR(Term1, Term2)
    Term1 = NOT(NOT_A OR B)  = AND(A, NOT_B)
    Term2 = NOT(A OR NOT_B)  = AND(NOT_A, B)

  Y=1 lever level, Y+1=2 signal level.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1

# ================= lane A =================
SA = (0, Y, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]  # NOT_A @ (0,2,1)

dustRAW_A = rp.place_raw_tap(s, leverA, rp.EAST)  # (2,1,0)
rawA_step = rp.step(s, dustRAW_A, rp.EAST, up=True)  # (3,2,0)
rawA_settle = rp._add(rawA_step, rp.EAST)  # (4,2,0)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # (4,2,0)

# ================= lane B =================
SB = (9, Y, 0)
notB = rp.place_not(s, SB, lever_dir=rp.WEST, torch_dust_dir=rp.EAST)
leverB = rp._add(SB, rp.WEST)  # (8,1,0)
dustB1 = notB["dust"]  # NOT_B @ (10,2,0)

dustRAW_B = rp.place_raw_tap(s, leverB, rp.WEST)  # (7,1,0)
rawB_step = rp.step(s, dustRAW_B, rp.WEST, up=True)  # (6,2,0)
rawB_settle = rp._add(rawB_step, rp.NORTH)  # (6,2,-1)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle  # (6,2,-1)

# ================= S1 = merge(NOT_A, rawB) -> Term1 @ (100,2,50) =================
S1 = (100, Y + 1, 50)
rp.converge(s, S1)

# NOT_A: (0,2,1) -> south -> (0,2,50) -> east -> S1(100,2,50)  [from west]
na1 = rp.travel(s, dustA1, (0, Y + 1, 50), land_as="dust")
rp.travel(s, na1, S1)

# rawB: (6,2,-1) -> east -> (2200,2,-1) -> south -> (2200,2,50) -> west -> S1(100,2,50)
#       [arrives from east]
rb1 = rp.travel(s, rawB, (2200, Y + 1, -1), land_as="dust")
rb2 = rp.travel(s, rb1, (2200, Y + 1, 50), land_as="dust")
rp.travel(s, rb2, S1)

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (100,3,50)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0], term1_torch[1], term1_torch[2] + 1)  # (100,3,51)
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ================= S2 = merge(NOT_B, rawA) -> Term2 @ (2200,2,50) =================
S2 = (2200, Y + 1, 50)
rp.converge(s, S2)

# NOT_B: (10,2,0) -> east -> (200,2,0) -> south -> (200,2,3) -> east -> (2200,2,3)
#        -> south -> S2(2200,2,50)  [arrives from south]
nb1 = rp.travel(s, dustB1, (200, Y + 1, 0), land_as="dust")
nb2 = rp.travel(s, nb1, (200, Y + 1, 3), land_as="dust")
nb3 = rp.travel(s, nb2, (2200, Y + 1, 3), land_as="dust")
rp.travel(s, nb3, S2)

# rawA: (4,2,0) -> south -> (4,2,2) -> east -> (2200,2,2) -> south -> (2200,2,50)
#       -> west -> S2(2200,2,50)  [arrives from east]
ra1 = rp.travel(s, rawA, (4, Y + 1, 2), land_as="dust")
ra2 = rp.travel(s, ra1, (2100, Y + 1, 2), land_as="dust")
ra3 = rp.travel(s, ra2, (2100, Y + 1, 50), land_as="dust")
rp.travel(s, ra3, S2)

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (2200,3,50)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0], term2_torch[1], term2_torch[2] + 1)  # (2200,3,51)
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (400,3,80) =================
LAMP = (400, Y + 2, 80)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")

# term1_dust (100,3,51) -> south -> (100,3,80) -> east -> LAMP(400,3,80)  [from west]
t1w = rp.travel(s, term1_dust, (100, Y + 2, 80), land_as="dust")
rp.travel(s, t1w, LAMP)

# term2_dust (2200,3,51) -> south -> (2200,3,80) -> west -> LAMP(400,3,80)  [from east]
t2w = rp.travel(s, term2_dust, (2100, Y + 2, 80), land_as="dust")
rp.travel(s, t2w, LAMP)

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v7o spaced, no crossing paths)")
print(f"leverA={leverA} torchA={notA['torch']} leverB={leverB} torchB={notB['torch']}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch} lamp={LAMP}")
