"""XOR gate v4: generous spacing, no crossing signal paths.

Every signal path uses its own z-level band; paths only merge at S1/S2/LAMP
from perpendicular directions (the proven OR/converge pattern).
Settle hop after every step.

  XOR = OR(Term1, Term2)
    Term1 = NOT(NOT_A OR B)  = AND(A, NOT_B)
    Term2 = NOT(A OR NOT_B)  = AND(NOT_A, B)

  Coords (Y=1 lever level, Y+1=2 signal level):
    Lane A:  x=0..2, z=1..100   (NOT_A raw path)
    Lane B:  x=8..10, z=0..10   (NOT_B raw path)
    S1:      (50,2,10)           NOT_A from east, rawB from west
    S2:      (200,2,55)          NOT_B from south, rawA from west
    LAMP:    (125,3,80)          Term1 from west, Term2 from east
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
rawA_step = rp.step(s, dustRAW_A, rp.SOUTH, up=True)  # (2,2,1) step landing @ z=1
rawA_settle = rp._add(rawA_step, rp.SOUTH)  # (2,2,2) settle hop @ z=2
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # (2,2,2)

# ================= lane B =================
SB = (9, Y, 0)
notB = rp.place_not(s, SB, lever_dir=rp.WEST, torch_dust_dir=rp.EAST)
leverB = rp._add(SB, rp.WEST)  # (8,1,0)
dustB1 = notB["dust"]  # NOT_B @ (10,2,0)

dustRAW_B = rp.place_raw_tap(s, leverB, rp.SOUTH)  # (8,1,1)
rawB_step = rp.step(s, dustRAW_B, rp.SOUTH, up=True)  # (8,2,2)
rawB_settle = rp._add(rawB_step, rp.SOUTH)  # (8,2,3)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle  # (8,2,3)

# ================= S1 = merge(NOT_A, rawB) -> Term1 @ (50,2,10) =================
S1 = (50, Y + 1, 10)
rp.converge(s, S1)

# NOT_A: (0,2,1) -> south -> (0,2,100) -> east -> (250,2,100) -> south -> (250,2,10)
#        -> west -> S1(50,2,10)  [arrives from east]
na1 = rp.travel(s, dustA1, (0, Y + 1, 100), land_as="dust")
na2 = rp.travel(s, na1, (250, Y + 1, 100), land_as="dust")
na3 = rp.travel(s, na2, (250, Y + 1, 10), land_as="dust")
rp.travel(s, na3, S1)

# rawB: (8,2,3) -> south -> (8,2,10) -> east -> S1(50,2,10)  [arrives from west]
rb1 = rp.travel(s, rawB, (8, Y + 1, 10), land_as="dust")
rp.travel(s, rb1, S1)

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (50,3,10)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0], term1_torch[1], term1_torch[2] + 1)  # (50,3,11)
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ================= S2 = merge(NOT_B, rawA) -> Term2 @ (200,2,55) =================
S2 = (200, Y + 1, 55)
rp.converge(s, S2)

# NOT_B: (10,2,0) -> south -> (10,2,60) -> east -> (200,2,60) -> north -> S2(200,2,55)
#        [arrives from south]
nb1 = rp.travel(s, dustB1, (10, Y + 1, 60), land_as="dust")
nb2 = rp.travel(s, nb1, (200, Y + 1, 60), land_as="dust")
rp.travel(s, nb2, S2)

# rawA: (2,2,2) -> south -> (2,2,55) -> east -> S2(200,2,55)  [arrives from west]
ra1 = rp.travel(s, rawA, (2, Y + 1, 55), land_as="dust")
rp.travel(s, ra1, S2)

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (200,3,55)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0], term2_torch[1], term2_torch[2] + 1)  # (200,3,56)
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (125,3,80) =================
LAMP = (125, Y + 2, 80)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")

# term1_dust (50,3,11) -> south -> (50,3,80) -> east -> LAMP  [from west]
t1w = rp.travel(s, term1_dust, (50, Y + 2, 80), land_as="dust")
rp.travel(s, t1w, LAMP)

# term2_dust (200,3,56) -> south -> (200,3,80) -> west -> LAMP  [from east]
t2w = rp.travel(s, term2_dust, (200, Y + 2, 80), land_as="dust")
rp.travel(s, t2w, LAMP)

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v4 spaced, no crossing paths)")
print(f"leverA={leverA} torchA={notA['torch']} leverB={leverB} torchB={notB['torch']}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch} lamp={LAMP}")
