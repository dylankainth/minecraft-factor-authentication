"""Isolation test: the exact proven convergence geometry from
build_and_gate_test.py (two independent repeaters landing on one stone
block, SF, from different faces) -- padded out to roughly the XOR
build's total block count (~3000+) with inert, disconnected filler.

If SF still reads as stone here, the bug is specifically about
something in the real XOR schematic (not just raw paste size). If SF
reads as air here too, we've reproduced the real bug in a minimal,
reportable fixture, and it really is just "this pattern breaks once the
paste is big enough".
"""
from schem import Schematic

s = Schematic()

# floor for dust/repeater cells only (identical to build_and_gate_test.py)
for x, y, z in [(3, 0, 1), (3, 0, 2), (1, 0, 3), (2, 0, 3)]:
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

# the convergence point under test
SF = (3, 1, 3)
s.set(*SF, "minecraft:stone")

# ---- padding: ~3200 inert blocks, far away, refresh-repeatered dust
# corridors, contributing nothing logically ----
for lane in range(16):
    z = 20 + lane
    for x in range(0, 200):
        pos = (x, 1, z)
        s.set(x, 0, z, "minecraft:stone")  # floor
        if x % 8 == 0:
            s.set(*pos, "minecraft:repeater[facing=west,powered=false,locked=false,delay=1]")
        else:
            s.set(*pos, "minecraft:redstone_wire[power=0]")

s.save("convergence_scale_test.schem")
print("wrote convergence_scale_test.schem")
print(f"blocks: {len(s.blocks)}")
print("leverA=(2,0,0) leverB=(0,0,2) SF=(3,1,3)")
