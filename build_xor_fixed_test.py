"""XOR gate, fixed version of build_xor_compact_test.py.

Fix: every staircase step that feeds a repeater/consumer is now followed by a
plain dust settle hop. Per build_rawb_fix_test.py, a step's LANDING cell can
power another dust cell (dust-to-dust works) but cannot reliably power a
consumer (repeater/lamp). The old code let rawA/rawB (both step landings)
power the first repeater of their travel() chains directly -- intermittent.

Identity: XOR(A,B) = OR(Term1, Term2)
  Term1 = NOT(NOT_A OR B)
  Term2 = NOT(A OR NOT_B)
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()

Y_BASE = 1
Y_GAP = 5  # lane B lives this many levels above lane A

# ---- lane A ----
SA = (0, Y_BASE, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]  # dustA1 = NOT_A @ y=Y_BASE+1

dustRAW_A = rp.place_raw_tap(s, leverA, rp.SOUTH)
rawA_step = rp.step(s, dustRAW_A, rp.SOUTH, up=True)  # step landing @ y=Y_BASE+1
# settle hop: landing cell -> plain dust -> first repeater (dust-to-dust OK)
rawA_settle = rp._add(rawA_step, rp.EAST)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # clean signal continues from the settle hop

# ---- lane B, Y_GAP levels above lane A -- can never collide ----
SB = (0, Y_BASE + Y_GAP, 0)
notB = rp.place_not(s, SB, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverB, dustB1 = notB["lever"], notB["dust"]

dustRAW_B = rp.place_raw_tap(s, leverB, rp.SOUTH)
rawB_step = rp.step(s, dustRAW_B, rp.SOUTH, up=True)  # step landing @ y=Y_BASE+1+Y_GAP
rawB_settle = rp._add(rawB_step, rp.EAST)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle


def step_down_to(start, target_y, direction):
    cur = start
    while cur[1] > target_y:
        cur = rp.step(s, cur, direction, up=False)
    assert cur[1] == target_y, (cur, target_y)
    return cur


LOW_Y = Y_BASE + 1  # lane A's operating height

# ==== S1 = merge(NOT_A, B) -> Term1 ====
S1 = (0, LOW_Y, 10)
rp.converge(s, S1)
rp.travel(s, dustA1, S1)  # NOT_A approaches from the north (straight south, x=0)

rawB_stage = rp.travel(s, rawB, (7, rawB[1], 2), land_as="dust")
rawB_stage = rp.travel(s, rawB_stage, (7, rawB[1], 5), land_as="dust")
rawB_low = step_down_to(rawB_stage, LOW_Y, rp.SOUTH)
rawB_settle2 = rp._add(rawB_low, rp.WEST)
rp.floor_under(s, rawB_settle2)
s.set(*rawB_settle2, "minecraft:redstone_wire[power=0]")
rp.travel(s, rawB_settle2, S1)  # straight west into S1

term1_torch = (S1[0], S1[1] + 1, S1[2])
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0], term1_torch[1], term1_torch[2] + 1)  # south of torch
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ==== S2 = merge(A, NOT_B) -> Term2 ====
S2 = (15, LOW_Y, 20)
rawA_safe = rp.travel(s, rawA, (15, LOW_Y, 2), land_as="dust")
rp.converge(s, S2)
rp.travel(s, rawA_safe, S2)  # raw_A approaches from the north (straight south)

notB_stage = rp.travel(s, dustB1, (0, dustB1[1], 50), land_as="dust")
notB_stage = rp.travel(s, notB_stage, (10, dustB1[1], 50), land_as="dust")
notB_stage = rp.travel(s, notB_stage, (10, dustB1[1], 22), land_as="dust")
notB_low = step_down_to(notB_stage, LOW_Y, rp.EAST)  # lands at S2.x
notB_settle = rp._add(notB_low, rp.NORTH)
rp.floor_under(s, notB_settle)
s.set(*notB_settle, "minecraft:redstone_wire[power=0]")
rp.travel(s, notB_settle, S2)  # straight north into S2, from the south

term2_torch = (S2[0], S2[1] + 1, S2[2])
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # east of torch
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ==== Final: XOR = OR(Term1, Term2) -> lamp ====
LAMP = (0, LOW_Y + 1, 25)
rp.converge(s, LAMP, "minecraft:redstone_lamp[lit=false]")
rp.travel(s, term1_dust, LAMP)  # approaches from the north

wpL = rp.travel(s, term2_dust, (16, term2_dust[1], 25), land_as="dust")
rp.travel(s, wpL, LAMP)  # approaches from the east

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (fixed with settle hops)")
print(f"leverA={leverA} torchA={notA['torch']} leverB={leverB} torchB={notB['torch']}")
print(f"rawA_settle={rawA_settle} rawB_settle={rawB_settle}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch} lamp={LAMP}")
print(f"RAWB_LOW(landing)={rawB_low} RAWB_SETTLE={rawB_settle2}")
