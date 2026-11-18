"""XOR gate v9: carefully planned, no crossing paths.

Layout (Y=1 lever level, Y+1=2 signal level):
  Lever A: support(-1,1,0), lever(0,1,0), torch(-1,2,0), dustA1=NOT_A at (-1,2,1)
  Lever B: support(-1,1,10), lever(0,1,10), torch(-1,2,10), dustB1=NOT_B at (-1,2,11)
  rawA: leverA->dustRAW_A(1,1,0)->step->rawA_step(2,2,0)->settle->rawA(2,2,1)
  rawB: leverB->dustRAW_B(1,1,10)->step->rawB_step(2,2,10)->settle->rawB(2,2,11)

  S1 = merge(NOT_A, raw_B) @ (20,2,20):
    NOT_A: (-1,2,1) -> east to (20,2,1) -> south to S1(20,2,20)  [from north]
    rawB:  (2,2,11) -> west to (0,2,11) -> south to (0,2,20) -> east to S1(20,2,20)  [from west]

  S2 = merge(raw_A, NOT_B) @ (60,2,40):
    rawA:  (2,2,1) -> east to (60,2,1) -> south to S2(60,2,40)  [from north]
    NOT_B: (-1,2,11) -> east to (50,2,11) -> south to (50,2,40) -> east to S2(60,2,40)  [from west]

  Term1 torch on S1, dust east of torch.
  Term2 torch on S2, dust east of torch.
  LAMP @ (60,3,45): term1_dust->south->east, term2_dust->south->west? 
    term1_dust(21,3,20)->south->(21,3,45)->east->LAMP(60,3,45) [from west]
    term2_dust(61,3,40)->south->(61,3,45)->west->LAMP(60,3,45) [from east]
    Wait term2_dust at x=61 east of S2 torch(60,3,40). ->south to (61,3,45) ->west to LAMP(60,3,45). But term1_dust->south at x=21 to z=45, then east to x=60. term2_dust->south at x=61 to z=45, then west to x=60. These are parallel south legs at different x. ✓
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1

# ---- Lever A: NOT_A ----
s.set(-1, Y, 0, "minecraft:stone")  # support
leverA = (0, Y, 0)
s.set(*leverA, "minecraft:lever[face=wall,facing=east,powered=false]")
torchA = (-1, Y + 1, 0)  # torch on support
s.set(*torchA, "minecraft:redstone_torch[lit=true]")
dustA1 = rp._add(torchA, rp.SOUTH)  # (-1,2,1) NOT_A output dust
rp.floor_under(s, dustA1)
s.set(*dustA1, "minecraft:redstone_wire[power=0]")

# raw_A tap: leverA -> east dust -> step up -> settle hop
dustRAW_A = rp._add(leverA, rp.EAST)  # (1,1,0)
rp.floor_under(s, dustRAW_A)
s.set(*dustRAW_A, "minecraft:redstone_wire[power=0]")
rawA_step = rp.step(s, dustRAW_A, rp.EAST, up=True)  # (2,2,0)
rawA_settle = rp._add(rawA_step, rp.EAST)  # (3,2,0)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # (3,2,0)

# ---- Lever B: NOT_B ----
s.set(-1, Y, 10, "minecraft:stone")  # support
leverB = (0, Y, 10)
s.set(*leverB, "minecraft:lever[face=wall,facing=east,powered=false]")
torchB = (-1, Y + 1, 10)  # torch on support
s.set(*torchB, "minecraft:redstone_torch[lit=true]")
dustB1 = rp._add(torchB, rp.NORTH)  # (-1,2,9) NOT_B output dust
rp.floor_under(s, dustB1)
s.set(*dustB1, "minecraft:redstone_wire[power=0]")

# raw_B tap: leverB -> east dust -> step up -> settle hop
dustRAW_B = rp._add(leverB, rp.EAST)  # (1,1,10)
rp.floor_under(s, dustRAW_B)
s.set(*dustRAW_B, "minecraft:redstone_wire[power=0]")
rawB_step = rp.step(s, dustRAW_B, rp.EAST, up=True)  # (2,2,10)
rawB_settle = rp._add(rawB_step, rp.SOUTH)  # (2,2,11)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle  # (2,2,11)

# ---- S1 = merge(NOT_A, raw_B) -> Term1 @ (20,2,20) ----
S1 = (20, Y + 1, 20)
rp.converge(s, S1)
# NOT_A: (-1,2,1) -> east to (20,2,1) -> south to S1(20,2,20)
na1 = rp.travel(s, dustA1, (20, Y + 1, 1), land_as="dust")
rp.travel(s, na1, S1)
# rawB: (2,2,11) -> west to (0,2,11) -> south to (0,2,20) -> east to S1
rb1 = rp.travel(s, rawB, (0, Y + 1, 11), land_as="dust")
rb2 = rp.travel(s, rb1, (0, Y + 1, 20), land_as="dust")
rp.travel(s, rb2, S1)

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (20,3,20)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # east of torch
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ---- S2 = merge(raw_A, NOT_B) -> Term2 @ (60,2,40) ----
S2 = (60, Y + 1, 40)
rp.converge(s, S2)
# rawA: (3,2,0) -> east to (60,2,0) -> south to S2(60,2,40)
ra1 = rp.travel(s, rawA, (60, Y + 1, 0), land_as="dust")
rp.travel(s, ra1, S2)
# NOT_B: (-1,2,9) -> east to (50,2,9) -> south to (50,2,40) -> east to S2(60,2,40)
nb1 = rp.travel(s, dustB1, (50, Y + 1, 9), land_as="dust")
nb2 = rp.travel(s, nb1, (50, Y + 1, 40), land_as="dust")
rp.travel(s, nb2, S2)

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (60,3,40)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # east of torch
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ---- Final: XOR = OR(Term1, Term2) -> lamp @ (60,3,45) ----
LAMP = (60, Y + 2, 45)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
# term1_dust(21,3,20) -> south -> (21,3,45) -> east -> LAMP(60,3,45)
t1w = rp.travel(s, term1_dust, (21, Y + 2, 45), land_as="dust")
rp.travel(s, t1w, LAMP)
# term2_dust(61,3,40) -> south -> (61,3,45) -> west -> LAMP(60,3,45)
t2w = rp.travel(s, term2_dust, (61, Y + 2, 45), land_as="dust")
rp.travel(s, t2w, LAMP)

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v9)")
print(f"leverA={leverA} leverB={leverB}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")
