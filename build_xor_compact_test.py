"""XOR gate, compact redesign. The original (build_xor_gate_test.py) used
100-150 block detours to avoid horizontal collisions between lane A and
lane B, and showed inconsistent, hard-to-pin-down failures at that scale
across many differential tests (isolated 2-chain and 3-chain sub-circuits
worked reliably; the full 4-chain circuit with long final routing did not,
even with thorough warm-up cycling and generous settle time). Rather than
keep chasing that at scale, this rebuilds the same logic with every
distance under 25 blocks -- comparable to the AND/OR gates, which both
worked reliably on the first real attempt at that size.

Key trick: lane B lives 5 Y-levels above lane A (SB on top of SA's column
conceptually, just offset in Y) so NOTHING in lane B can ever collide or
sit adjacent to lane A regardless of X/Z footprint reuse. Lane B's two
signals (NOT_B, raw_B) step back DOWN to lane A's height only in their
final few blocks, right before each one's target merge point.

Y_BASE=1 (not 0): a raw tap sits at the same height as its lever, and
Schematic.save() normalizes the whole structure to start at y=0 by
shifting everything up by however far below 0 any block went -- a raw
tap at y=0 needs a floor at y=-1, which silently shifted the ENTIRE
schematic by one level and put every hardcoded coordinate in this file
off by one relative to the actual placed blocks (first version of this
file hit exactly that bug: every dump in-game showed the wrong block at
every position, consistently one level off). Starting at y=1 keeps
every floor requirement non-negative.

Identity (same as before): XOR(A,B) = OR(Term1, Term2)
  Term1 = NOT(NOT_A OR raw_B)
  Term2 = NOT(raw_A OR NOT_B)
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
rawA = rp.step(s, dustRAW_A, rp.SOUTH, up=True)  # raw_A @ y=Y_BASE+1

# ---- lane B, Y_GAP levels above lane A -- can never collide ----
SB = (0, Y_BASE + Y_GAP, 0)
notB = rp.place_not(s, SB, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverB, dustB1 = notB["lever"], notB["dust"]

dustRAW_B = rp.place_raw_tap(s, leverB, rp.SOUTH)
rawB = rp.step(s, dustRAW_B, rp.SOUTH, up=True)

def step_down_to(start, target_y, direction):
    cur = start
    while cur[1] > target_y:
        cur = rp.step(s, cur, direction, up=False)
    assert cur[1] == target_y, (cur, target_y)
    return cur

LOW_Y = Y_BASE + 1  # lane A's operating height (NOT_A, raw_A, S1, S2 all live here)

# ==== S1 = merge(NOT_A, raw_B) -> Term1 ====
S1 = (0, LOW_Y, 10)
rp.converge(s, S1)
rp.travel(s, dustA1, S1)  # NOT_A approaches from the north (straight south, x=0)

# raw_B -> staging point near S1 at its OWN safe height -> staircase down
# SOUTH (perpendicular to the final WEST approach, so the stair's floor
# trail never lands on the final leg's own path) -> lands exactly at
# S1's z -> short final approach from the east.
rawB_stage = rp.travel(s, rawB, (7, rawB[1], 2), land_as="dust")
rawB_stage = rp.travel(s, rawB_stage, (7, rawB[1], 5), land_as="dust")
rawB_low = step_down_to(rawB_stage, LOW_Y, rp.SOUTH)
# settle hop: a dust cell that is itself a staircase LANDING cell doesn't
# reliably power a directly-adjacent consumer block (confirmed via
# build_rawb_lamp_test.py / build_rawb_fix_test.py -- the dust's own
# power reads correctly and it CAN power another plain dust cell, but a
# lamp/torch-bearing consumer right off the landing cell itself does
# not light). Insert one plain dust hop before the final approach.
rawB_settle = rp._add(rawB_low, rp.WEST)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rp.travel(s, rawB_settle, S1)  # straight west into S1

term1_torch = (S1[0], S1[1] + 1, S1[2])
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0], term1_torch[1], term1_torch[2] + 1)  # south of torch
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ==== S2 = merge(raw_A, NOT_B) -> Term2 ====
S2 = (15, LOW_Y, 20)  # x=15: raw_A's natural column (x=1) crosses raw_B's
# approach into S1 -- move well clear of the whole S1 convergence zone first.
rawA_safe = rp.travel(s, rawA, (15, LOW_Y, 2), land_as="dust")
rp.converge(s, S2)
rp.travel(s, rawA_safe, S2)  # raw_A approaches from the north (straight south)

# NOT_B -> staging point near S2, same trick -> staircase down EAST
# (perpendicular to the final NORTH approach) ending exactly at S2's x ->
# single-hop approach from the south (no repeater needed for 1 hop, so
# no floor-trail collision risk at all for this last step).
notB_stage = rp.travel(s, dustB1, (0, dustB1[1], 50), land_as="dust")  # far clear of rawB's z=2..5 leg
notB_stage = rp.travel(s, notB_stage, (10, dustB1[1], 50), land_as="dust")
notB_stage = rp.travel(s, notB_stage, (10, dustB1[1], 22), land_as="dust")  # +1 vs before: leaves room for the settle hop below
notB_low = step_down_to(notB_stage, LOW_Y, rp.EAST)  # lands at S2.x
# settle hop (see rawB_settle above for why): one plain dust cell before
# the final approach into S2, since notB_low is itself a staircase
# landing cell and can't reliably power S2 directly.
notB_settle = rp._add(notB_low, rp.NORTH)
rp.floor_under(s, notB_settle)
s.set(*notB_settle, "minecraft:redstone_wire[power=0]")
rp.travel(s, notB_settle, S2)  # straight north into S2, from the south

term2_torch = (S2[0], S2[1] + 1, S2[2])
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # east of torch (south collided with notB_low's floor)
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ==== Final: XOR = OR(Term1, Term2) -> lamp ====
LAMP = (0, LOW_Y + 1, 25)
rp.converge(s, LAMP, "minecraft:redstone_lamp[lit=false]")
rp.travel(s, term1_dust, LAMP)  # approaches from the north

wpL = rp.travel(s, term2_dust, (16, term2_dust[1], 25), land_as="dust")
rp.travel(s, wpL, LAMP)  # approaches from the east

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem")
print(f"leverA={leverA} torchA={notA['torch']} leverB={leverB} torchB={notB['torch']}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch} lamp={LAMP}")
