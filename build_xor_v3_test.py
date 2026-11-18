"""XOR gate v3: generous X/Z separation, no crossing signal paths.

Every signal path stays in its own x-column (north-south legs) or z-row
(east-west legs), so nothing crosses. Settle hop after every step.

  XOR = OR(Term1, Term2)
    Term1 = NOT(NOT_A OR B)  = AND(A, NOT_B)
    Term2 = NOT(A OR NOT_B)  = AND(NOT_A, B)

  Lane A at low z, lane B at mixed z but separated x-columns.
  S1=(50,2,25), S2=(200,2,100), LAMP=(100,3,150).
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
rawA_step = rp.step(s, dustRAW_A, rp.SOUTH, up=True)  # (2,2,1)
rawA_settle = rp._add(rawA_step, rp.SOUTH)  # (1,2,3)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # (1,2,3)

# ================= lane B =================
SB = (9, Y, 0)
notB = rp.place_not(s, SB, lever_dir=rp.EAST, torch_dust_dir=rp.EAST)
leverB = rp._add(SB, rp.EAST)  # (10,1,0)
dustB1 = notB["dust"]  # NOT_B @ (10,2,0)

dustRAW_B = rp.place_raw_tap(s, leverB, rp.SOUTH)  # (10,1,1)
rawB_step = rp.step(s, dustRAW_B, rp.SOUTH, up=True)  # (10,2,2)
rawB_settle = rp._add(rawB_step, rp.SOUTH)  # (10,2,3)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle  # (10,2,3)

# ================= S1 = merge(NOT_A, rawB) -> Term1  @ (50,2,25) =================
S1 = (50, Y + 1, 25)
rp.converge(s, S1)

# NOT_A: (0,2,1) -> east -> (50,2,1) -> south -> S1(50,2,25)  [from north]
notA_east = rp.travel(s, dustA1, (50, Y + 1, 1), land_as="dust")
rp.travel(s, notA_east, S1)

# rawB: (10,2,3) -> north -> (10,2,25) -> west -> S1(50,2,25)  [from east]
rawB_north = rp.travel(s, rawB, (10, Y + 1, 25), land_as="dust")
rp.travel(s, rawB_north, S1)

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (50,3,25)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0], term1_torch[1], term1_torch[2] + 1)  # (50,3,26) south of torch
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ================= S2 = merge(NOT_B, rawA) -> Term2  @ (200,2,100) =================
S2 = (200, Y + 1, 100)
rp.converge(s, S2)

# NOT_B: (10,2,0) -> east -> (200,2,0) -> south -> S2(200,2,100)  [from north]
notB_east = rp.travel(s, dustB1, (200, Y + 1, 0), land_as="dust")
rp.travel(s, notB_east, S2)

# rawA: (1,2,3) -> south -> (1,2,100) -> east -> S2(200,2,100)  [from west]
rawA_south = rp.travel(s, rawA, (1, Y + 1, 100), land_as="dust")
rp.travel(s, rawA_south, S2)

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (200,3,100)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0], term2_torch[1], term2_torch[2] + 1)  # (200,3,101) south of torch
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (100,3,150) =================
LAMP = (100, Y + 2, 150)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")

# term1_dust (50,3,26) -> south -> (50,3,150) -> east -> LAMP(100,3,150)  [from west]
t1w = rp.travel(s, term1_dust, (50, Y + 2, 150), land_as="dust")
rp.travel(s, t1w, LAMP)

# term2_dust (200,3,101) -> south -> (200,3,150) -> west -> LAMP(100,3,150)  [from east]
t2w = rp.travel(s, term2_dust, (200, Y + 2, 150), land_as="dust")
rp.travel(s, t2w, LAMP)

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v3 separated, no crossing paths)")
print(f"leverA={leverA} torchA={notA['torch']} leverB={leverB} torchB={notB['torch']}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch} lamp={LAMP}")
