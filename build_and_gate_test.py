"""AND gate, built compositionally from the two verified primitives:
AND(A,B) = NOT(NOT(A) OR NOT(B))  (De Morgan)

  - NOT(A): standing-torch inverter (verified, build_not_gate_test.py).
  - NOT(B): same, parallel lane.
  - OR of NOT(A), NOT(B): each routed through its own repeater, both
    repeater outputs aimed at the SAME final support block from two
    different sides -- never merged through a shared dust cell, per the
    OR-gate finding (build_or_gate_test.py) that a shared dust junction
    with 2 independent sources doesn't propagate to a downstream
    consumer in this MCHPRS build.
  - That merged support block feeds one more standing-torch inverter,
    giving the final AND output.

New assumption being tested here (not yet verified): a repeater's output
pointed into a solid support block gives it enough power to extinguish an
attached standing torch, the same way a wall-mounted lever does. This is
standard real-redstone practice; if it doesn't hold in this build, the
truth table below will show it immediately (SF never gets powered, TF
never turns off, lamp stays lit regardless of inputs).

Layout (floor = stone at y=0 under every dust/repeater cell only --
plain solid blocks like SA/SB/SF don't need support):

  Branch A (approaches the final support from the north):
    SA(3,0,0)              torch support + lever attachment
    leverA(2,0,0)           wall lever, facing=west (attached to SA's west face)
    torchA(3,1,0)           standing torch[lit=true], on SA  -- NOT(A)
    dustA1(3,1,1)           carries NOT(A); floor (3,0,1)
    repA(3,1,2)             facing=north (reads dustA1); floor (3,0,2);
                            outputs south into SF

  Branch B (approaches the final support from the west):
    SB(0,0,3)
    leverB(0,0,2)           wall lever, facing=north (attached to SB's north face)
    torchB(0,1,3)           standing torch[lit=true], on SB  -- NOT(B)
    dustB1(1,1,3)           carries NOT(B); floor (1,0,3)
    repB(2,1,3)             facing=west (reads dustB1); floor (2,0,3);
                            outputs east into SF

  Final stage:
    SF(3,1,3)               shared support block, powered by repA (north)
                            and/or repB (west) -- OR, via direct dual-
                            repeater convergence, no shared dust
    TF(3,2,3)               standing torch[lit=true], on SF  -- final NOT
    repF(3,2,4)             facing=north (reads TF); floor (3,1,4);
                            outputs east into lampF
    lampF(4,2,4)            output lamp; floor (4,1,4)

  (First version used a plain dust cell between TF and lampF -- never
  lit regardless. Second version swapped it for a repeater but put the
  lamp EAST of repF while TF (its input) was NORTH -- a 90-degree turn,
  which doesn't work: a repeater is strictly straight-through, input and
  output on opposite faces only. That's a geometry mistake, not an
  engine quirk -- fixed by putting lampF directly SOUTH of repF,
  continuing the straight TF -> repF -> lampF line.)

Expected: lampF lit only when leverA=ON and leverB=ON.
"""
from schem import Schematic

s = Schematic()

# floor (support for dust/repeater cells only)
for x, y, z in [(3, 0, 1), (3, 0, 2), (1, 0, 3), (2, 0, 3), (3, 1, 4), (3, 1, 5)]:
    s.set(x, y, z, "minecraft:stone")

# branch A
s.set(3, 0, 0, "minecraft:stone")  # SA
s.set(2, 0, 0, "minecraft:lever[face=wall,facing=west,powered=false]")  # leverA
s.set(3, 1, 0, "minecraft:redstone_torch[lit=true]")  # torchA
s.set(3, 1, 1, "minecraft:redstone_wire[power=0]")  # dustA1
s.set(3, 1, 2, "minecraft:repeater[facing=north,powered=false,locked=false,delay=1]")  # repA

# branch B
s.set(0, 0, 3, "minecraft:stone")  # SB
s.set(0, 0, 2, "minecraft:lever[face=wall,facing=north,powered=false]")  # leverB
s.set(0, 1, 3, "minecraft:redstone_torch[lit=true]")  # torchB
s.set(1, 1, 3, "minecraft:redstone_wire[power=0]")  # dustB1
s.set(2, 1, 3, "minecraft:repeater[facing=west,powered=false,locked=false,delay=1]")  # repB

# final stage
s.set(3, 1, 3, "minecraft:stone")  # SF
s.set(3, 2, 3, "minecraft:redstone_torch[lit=true]")  # TF
s.set(3, 2, 4, "minecraft:repeater[facing=north,powered=false,locked=false,delay=1]")  # repF
s.set(3, 2, 5, "minecraft:redstone_lamp[lit=false]")  # lampF (straight south of repF)

s.save("and_gate_test.schem")
print("wrote and_gate_test.schem")
print("leverA=(2,0,0) leverB=(0,0,2) lampF=(3,2,5)")
