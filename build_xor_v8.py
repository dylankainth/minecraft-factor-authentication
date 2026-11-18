"""XOR gate v8: compact, verified primitives only.

XOR = OR(Term1, Term2)
  Term1 = NOT(NOT_A OR B)   -- settle hop after rawB step
  Term2 = NOT(A OR NOT_B)   -- settle hop after rawA step

Every step (height change) is followed by a plain dust settle hop before
any repeater/consumer.  Verified primitives:
  - place_not (lever->support->torch->dust): reliable live.
  - place_raw_tap (lever->dust): reliable live.
  - travel() flat chains: reliable live (long_chain_test).
  - converge() merge stone: reliable live (term1_fixed_probe).
  - step+settle hop: verified live (latch_probe).
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1

# ---- Lever A: NOT_A output dust ----
SA = (0, Y, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]   # dustA1 = NOT_A @ (0,2,1)

# raw_A tap (used by Term2): leverA -> dust -> step up -> settle hop
dustRAW_A = rp.place_raw_tap(s, leverA, rp.EAST)    # (2,1,0)
rawA_step = rp.step(s, dustRAW_A, rp.EAST, up=True) # (3,2,0) step landing
rawA_settle = rp._add(rawA_step, rp.SOUTH)          # (3,2,1) settle hop
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # (3,2,1) clean signal

# ---- Lever B: NOT_B output dust ----
SB = (0, Y, 8)
notB = rp.place_not(s, SB, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverB = rp._add(SB, rp.EAST)    # (1,1,8)
dustB1 = notB["dust"]            # NOT_B @ (0,2,9)

# raw_B tap (used by Term1): leverB -> dust -> step up -> settle hop
dustRAW_B = rp.place_raw_tap(s, leverB, rp.EAST)   # (2,1,8)
rawB_step = rp.step(s, dustRAW_B, rp.EAST, up=True) # (3,2,8) step landing
rawB_settle = rp._add(rawB_step, rp.SOUTH)         # (3,2,9) settle hop
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle  # (3,2,9) clean signal

# ---- S1 = merge(NOT_A, raw_B) -> Term1 @ (20,2,5) ----
S1 = (20, Y + 1, 5)
rp.converge(s, S1)
# NOT_A: (0,2,1) -> south -> (0,2,5) -> east -> S1(20,2,5)  [from west]
na1 = rp.travel(s, dustA1, (0, Y + 1, 5), land_as="dust")
rp.travel(s, na1, S1)
# raw_B: (3,2,9) -> south -> (3,2,5) -> west -> S1(20,2,5)? No, (3->20) is east.
# raw_B: (3,2,9) -> north -> (3,2,5) -> east -> S1(20,2,5)  [from west]
rb1 = rp.travel(s, rawB, (3, Y + 1, 5), land_as="dust")
rp.travel(s, rb1, S1)

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (20,3,5)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # east of torch
rp.floor_under(s, term1_dust)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ---- S2 = merge(raw_A, NOT_B) -> Term2 @ (20,2,15) ----
S2 = (20, Y + 1, 15)
rp.converge(s, S2)
# raw_A: (3,2,1) -> south -> (3,2,15) -> east -> S2(20,2,15)  [from west]
ra1 = rp.travel(s, rawA, (3, Y + 1, 15), land_as="dust")
rp.travel(s, ra1, S2)
# NOT_B: (0,2,9) -> south -> (0,2,15) -> east -> S2(20,2,15)  [from west]
nb1 = rp.travel(s, dustB1, (0, Y + 1, 15), land_as="dust")
rp.travel(s, nb1, S2)

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (20,3,15)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # east of torch
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ---- Final: XOR = OR(Term1, Term2) -> lamp @ (20,3,25) ----
LAMP = (20, Y + 2, 25)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
# term1_dust (21,3,5) -> south -> (21,3,25) -> east -> LAMP(40,3,25)? No, (21->40) east.
# term1_dust (21,3,5) -> south -> (21,3,25) -> east -> LAMP(40,3,25)... that's too far.
# Just go east from term1_dust: (21,3,5) -> east -> (30,3,5) -> south -> (30,3,25) -> west -> LAMP(20,3,25)
t1w = rp.travel(s, term1_dust, (30, Y + 2, 5), land_as="dust")
t1s = rp.travel(s, t1w, (30, Y + 2, 25), land_as="dust")
rp.travel(s, t1s, LAMP)  # west into LAMP
# term2_dust (21,3,15) -> south -> (21,3,25) -> east -> LAMP... collides!
# term2_dust (21,3,15) -> south -> (21,3,20) -> east -> LAMP(40,3,20)? No.
# term2_dust (21,3,15) -> east -> (30,3,15) -> south -> (30,3,25) -> west -> LAMP... collides at (30,3,25).
# Use different z: term2_dust (21,3,15) -> south -> (21,3,18) -> east -> LAMP(40,3,18)? No.
# Let me just place LAMP east of term2_dust directly: term2_dust (21,3,15) -> east -> LAMP(30,3,15)? But LAMP is at y=3... wait LAMP is at Y+2=3.
# LAMP at (30,3,15) would work! term2_dust east -> LAMP directly.
# But then term1_dust also needs to reach LAMP. term1_dust (21,3,5) -> east -> (30,3,5) -> south -> (30,3,15) -> LAMP(30,3,15)? That's the same cell as LAMP!
# Converge both at LAMP(30,3,15):
#   term1_dust -> east -> south -> LAMP
#   term2_dust -> east -> LAMP (direct)

print(f"leverA={leverA} leverB={leverB}")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v8)")
