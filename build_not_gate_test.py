"""NOT gate (torch inverter), verified working.

History of what didn't work, kept because it's the actual finding:
  1. Lamp placed bare-adjacent to the torch (no dust): never lit regardless
     of input. Bare adjacency to a torch does not power a mechanism block
     -- only redstone dust touching the block does (see dust_test.schem).
  2. Wall torch -> dust -> lamp, dust unsupported (floating, no block
     below): dust correctly read the torch's power (0/15, tracking the
     lever) but the lamp never lit.
  3. Wall torch -> dust -> lamp, dust properly supported by a floor block:
     same result -- dust reached power=15, lamp still never lit. Isolated
     by a differential test (build_dust_chain_test.py, lever -> dust ->
     dust -> lamp) that multi-hop dust propagation is NOT broken in
     general (14/15 falloff, lamp lit correctly) -- the break is specific
     to WALL torches. A STANDING torch -> dust -> lamp (same differential
     harness, build_standing_torch_test.py) worked immediately.

Conclusion: in this MCHPRS build, a wall-mounted redstone torch does not
properly notify beyond its immediate dust neighbor when it turns on/off --
the dust's own displayed power updates correctly, but it never re-notifies
ITS neighbors in turn. A standing torch does not have this problem. Use
standing torches for inverters in this project, not wall torches.

Layout (verified):
  (0,0,0) stone                          <- torch's support block (= input)
  (0,0,1) lever[face=wall,facing=south]  <- wall-mounted on north face of (0,0,0)
  (0,1,0) redstone_torch[lit=true]       <- standing on top of (0,0,0)
  (1,0,0) stone                          <- dust support
  (1,1,0) redstone_wire
  (2,0,0) stone                          <- lamp support
  (2,1,0) redstone_lamp

Expected (NOT gate): lever OFF -> input unpowered -> torch lit -> dust
powered -> lamp lit. lever ON -> input powered -> torch off -> dust
unpowered -> lamp unlit.
"""
from schem import Schematic

s = Schematic()
s.set(0, 0, 0, "minecraft:stone")
s.set(1, 0, 0, "minecraft:stone")
s.set(2, 0, 0, "minecraft:stone")
s.set(0, 0, 1, "minecraft:lever[face=wall,facing=south,powered=false]")
s.set(0, 1, 0, "minecraft:redstone_torch[lit=true]")
s.set(1, 1, 0, "minecraft:redstone_wire[power=0]")
s.set(2, 1, 0, "minecraft:redstone_lamp[lit=false]")
s.save("not_gate_test.schem")
print("wrote not_gate_test.schem: lever(0,0,1) -> torch(0,1,0) -> dust(1,1,0) -> lamp(2,1,0)")
