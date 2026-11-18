"""Isolation test #2: same proven convergence geometry as
build_convergence_scale_test.py (which worked, SF read correctly 5/5),
but this time each branch reaching SF goes through a LONG dust run with
periodic refresh repeaters (like the real XOR's lanes), instead of a
single short hop. If SF fails here, the bug is specifically about
multi-repeater chains feeding a convergence point, not raw paste size.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()


def long_lane(label_unused, start, length, z):
    """Dust corridor along +x from start, with a repeater every 8
    blocks, ending after `length` cells. Returns the final cell."""
    x0, y0, z0 = start
    rp.floor_under(s, start)
    s.set(*start, "minecraft:redstone_wire[power=0]")
    cur = start
    since = 0
    for i in range(length):
        since += 1
        nxt = (cur[0] + 1, cur[1], cur[2])
        if since >= 8:
            rp.floor_under(s, nxt)
            s.set(*nxt, "minecraft:repeater[facing=west,powered=false,locked=false,delay=1]")
            since = 0
        else:
            rp.floor_under(s, nxt)
            s.set(*nxt, "minecraft:redstone_wire[power=0]")
        cur = nxt
    return cur


# branch A: lever -> torch -> long dust+repeater chain (20 cells) -> SF (west face)
leverA = (0, 1, 0)
s.set(*leverA, "minecraft:lever[face=wall,facing=west,powered=false]")
SA = (1, 1, 0)
s.set(*SA, "minecraft:stone")
torchA = (1, 2, 0)
s.set(*torchA, "minecraft:redstone_torch[lit=true]")
dustA0 = (2, 2, 0)
end_a = long_lane("A", dustA0, 20, 0)  # ends at (22,2,0)
# final hop into SF needs SF one east of the chain's last dust cell,
# via its own dedicated repeater
SF_X = end_a[0] + 2
SF = (SF_X, 2, 0)
repA_final = (end_a[0] + 1, 2, 0)
rp.floor_under(s, repA_final)
s.set(*repA_final, "minecraft:repeater[facing=west,powered=false,locked=false,delay=1]")

# branch B: lever -> torch -> long dust+repeater chain (20 cells) -> SF (south face)
leverB = (0, 1, 3)
s.set(*leverB, "minecraft:lever[face=wall,facing=west,powered=false]")
SB = (1, 1, 3)
s.set(*SB, "minecraft:stone")
torchB = (1, 2, 3)
s.set(*torchB, "minecraft:redstone_torch[lit=true]")
dustB0 = (2, 2, 3)
end_b = long_lane("B", dustB0, 20, 3)  # ends at (22,2,3)
# turn north at x = SF_X, then straight repeater into SF's south face
turn_x = SF_X
s.set(end_b[0], 2, 2, "minecraft:redstone_wire[power=0]")
rp.floor_under(s, (end_b[0], 2, 2))
for x in range(end_b[0] + 1, turn_x + 1):
    pos = (x, 2, 2)
    rp.floor_under(s, pos)
    s.set(*pos, "minecraft:redstone_wire[power=0]")
repB_final = (SF_X, 2, 1)
rp.floor_under(s, repB_final)
s.set(*repB_final, "minecraft:repeater[facing=south,powered=false,locked=false,delay=1]")

s.set(*SF, "minecraft:stone")

s.save("convergence_longchain_test.schem")
print("wrote convergence_longchain_test.schem")
print(f"blocks: {len(s.blocks)}")
print(f"leverA={leverA} leverB={leverB} SF={SF}")
