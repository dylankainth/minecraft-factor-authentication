"""XOR gate v2: simplified, no step-down chains.

Every raw signal takes exactly ONE step up (with a settle hop) to reach the
NOT signals' level, then travels flat (y=2) to its merge stone. No step_down
chains, no Y_GAP, X/Z separation between lanes.

  XOR = OR(Term1, Term2)
    Term1 = NOT(NOT_A OR B)  = AND(A, NOT_B)
    Term2 = NOT(A OR NOT_B)  = AND(NOT_A, B)

  Both lanes at Y_BASE=1. NOT dusts and settled raw dusts all at y=2.
  Lane A at x=0..1, lane B at x=9..10. Merge stones S1/S2 at y=2.
  Final OR merge into lamp via repeater convergence from west and east.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1

# ================= lane A =================
SA = (0, Y, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]  # NOT_A @ (0,2,1)

dustRAW_A = rp.place_raw_tap(s, leverA, rp.SOUTH)  # (1,1,1)
rawA_step = rp.step(s, dustRAW_A, rp.SOUTH, up=True)  # (1,2,2) step landing
rawA_settle = rp._add(rawA_step, rp.SOUTH)  # (1,2,3) settle hop
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # (1,2,3) clean signal @ y=2

# ================= lane B =================
SB = (9, Y, 0)
notB = rp.place_not(s, SB, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverB = rp._add(SB, rp.EAST)  # (10,1,0)
dustB1 = notB["dust"]  # NOT_B @ (9,2,1)

dustRAW_B = rp.place_raw_tap(s, leverB, rp.SOUTH)  # (10,1,1)
rawB_step = rp.step(s, dustRAW_B, rp.SOUTH, up=True)  # (10,2,2) step landing
rawB_settle = rp._add(rawB_step, rp.SOUTH)  # (10,2,3) settle hop
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle  # (10,2,3) clean signal @ y=2

# ================= S1 = merge(NOT_A, rawB) -> Term1 =================
# NOT_A approaches S1 from the north (straight south, x=0).
# rawB approaches S1 from the east (straight west, z=20).
S1 = (0, Y + 1, 20)
rp.converge(s, S1)
rp.travel(s, dustA1, S1)  # NOT_A: (0,2,1) -> south -> (0,2,20)

# rawB: (10,2,3) -> south -> (10,2,20) -> west -> S1(0,2,20)
rawB_way = rp.travel(s, rawB, (10, Y + 1, 20), land_as="dust")
rp.travel(s, rawB_way, S1)

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (0,3,20)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0], term1_torch[1], term1_torch[2] + 1)  # (0,3,21) south of torch
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ================= S2 = merge(NOT_B, rawA) -> Term2 =================
# NOT_B approaches S2 from the north (straight south, x=15).
# rawA approaches S2 from the west (straight east, z=40).
S2 = (15, Y + 1, 40)
rp.converge(s, S2)

# NOT_B: (9,2,1) -> east -> (15,2,1) -> south -> S2(15,2,40)
notB_way1 = rp.travel(s, dustB1, (15, Y + 1, 1), land_as="dust")
rp.travel(s, notB_way1, S2)

# rawA: (1,2,3) -> south -> (1,2,40) -> east -> S2(15,2,40)
rawA_way1 = rp.travel(s, rawA, (1, Y + 1, 40), land_as="dust")
rp.travel(s, rawA_way1, S2)

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (15,3,40)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # (16,3,40) east of torch
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ================= Final: XOR = OR(Term1, Term2) -> lamp =================
LAMP = (8, Y + 2, 60)  # (8,3,60)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")

# term1_dust (1,3,20) -> south -> (1,3,60) -> east -> LAMP(8,3,60) [from west]
t1w = rp.travel(s, term1_dust, (1, Y + 2, 60), land_as="dust")
rp.travel(s, t1w, LAMP)

# term2_dust (16,3,40) -> south -> (16,3,60) -> west -> LAMP(8,3,60) [from east]
t2w = rp.travel(s, term2_dust, (16, Y + 2, 60), land_as="dust")
rp.travel(s, t2w, LAMP)

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v2 simplified, no step-down chains)")
print(f"leverA={leverA} torchA={notA['torch']} leverB={leverB} torchB={notB['torch']}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch} lamp={LAMP}")
