"""Empirical NOT-gate (torch inverter) test.

We do NOT trust memorized torch power-propagation rules for exact adjacency --
that's exactly the kind of detail that's easy to get subtly wrong. Instead we
place ONE candidate inverter (lever -> strongly powers its own block ->
attached wall torch extinguishes) and FOUR lamps in different candidate
"powered by the torch" positions, then read back which lamps actually track
the inverted lever state when driven by the bot. That turns the gate design
into a measurement instead of a claim.

Layout (x,y,z), lever/torch column at x=0..1:
  (0,0,0) stone               <- torch attaches to its north face
  (0,0,1) redstone_wall_torch[facing=south]   <- attached to (0,0,0)
  (0,1,0) lever[face=floor]   <- on top of (0,0,0), strongly powers it

Candidate output positions (lamps), each tested independently so results
are unambiguous:
  A (1,0,1) lamp beside the torch at the same height, east of it
  B (0,0,2) lamp directly south of the torch (in the direction it points)
  C (0,1,1) lamp on top of the torch
  D (-1,0,1) lamp west of the torch
"""
from schem import Schematic

s = Schematic()
# normalize coords later (Schematic.save handles arbitrary mins)
s.set(1, 0, 0, "minecraft:stone")              # input block, x shifted +1 to keep all x>=0
s.set(1, 0, 1, "minecraft:redstone_wall_torch[facing=south,lit=true]")
s.set(1, 1, 0, "minecraft:lever[face=floor,facing=north,powered=false]")

# C (on top of torch, local (1,1,1)) dropped: measured adjacent to the
# lever's own cell too, so it lit directly from the lever regardless of the
# torch -- confounded, not a real reading of the torch's output.
s.set(2, 0, 1, "minecraft:redstone_lamp[lit=false]")  # A: east of torch
s.set(1, 0, 2, "minecraft:redstone_lamp[lit=false]")  # B: south of torch (pointed-into dir)
s.set(0, 0, 1, "minecraft:redstone_lamp[lit=false]")  # D: west of torch

s.save("not_gate_test.schem")
print("wrote not_gate_test.schem")
print("lever at (1,1,0) relative to schem origin; lamps A=(2,0,1) B=(1,0,2) C=(1,1,1) D=(0,0,1)")
