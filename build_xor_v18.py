"""XOR gate v18: programmatic layout with segment crossing detection.

Uses Y-level separation: paths 1-3 at y=3, path 4 at y=4 (long NS leg at y=4
doesn't cross y=3 paths). All EW legs at unique z-bands.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1
SEG_Y3 = Y + 2  # y=3
SEG_Y4 = Y + 3  # y=4

segments = []  # ((x1,x2),(z1,z2),y,label)

def add_seg(x1, x2, z1, z2, y, label):
    x1, x2 = sorted([x1, x2]); z1, z2 = sorted([z1, z2])
    for (ex1, ex2), (ez1, ez2), ey, el in segments:
        if ey != y:
            continue
        if x1 <= ex2 and x2 >= ex1 and z1 <= ez2 and z2 >= ez1:
            raise ValueError(f"CROSSING: {label} x[{x1},{x2}] z[{z1},{z2}] y={y} vs {el} x[{ex1},{ex2}] z[{ez1},{ez2}] y={ey}")
    segments.append(((x1, x2), (z1, z2), y, label))

def place_wire(x, y, z, label):
    rp.floor_under(s, (x, y, z))
    s.set(x, y, z, "minecraft:redstone_wire[power=0]")
    add_seg(x, x, z, z, y, label)

def place_run_x(x_start, x_end, z, y, label):
    step = 1 if x_end >= x_start else -1
    for x in range(x_start, x_end + step, step):
        place_wire(x, y, z, label)
    add_seg(min(x_start, x_end), max(x_start, x_end), z, z, y, label)

def place_run_z(x, z_start, z_end, y, label):
    step = 1 if z_end >= z_start else -1
    for z in range(z_start, z_end + step, step):
        place_wire(x, y, z, label)
    add_seg(x, x, min(z_start, z_end), max(z_start, z_end), y, label)

# ================= Lever A: NOT_A (z=100) + raw_A (z=102) =================
s.set(-3, Y, 100, "minecraft:stone")
s.set(-2, Y, 100, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 100, "minecraft:redstone_torch[lit=true]")
dustA1 = (-2, Y + 1, 100)  # NOT_A dust, east of torch
place_wire(*dustA1, SEG_Y3, "NOT_A dust")

dustRAW_A = (-1, Y, 100)
rp.floor_under(s, dustRAW_A)
s.set(*dustRAW_A, "minecraft:redstone_wire[power=0]")
rawA_step = rp.step(s, dustRAW_A, rp.EAST, up=True)   # (0,2,100)
rawA_settle = rp._add(rawA_step, rp.EAST)              # (1,2,100)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
# step up to y=3 at z=100: from (1,2,100) step EAST up -> (2,3,100)
rawA_y3 = rp.step(s, rawA_settle, rp.EAST, up=True)    # (2,3,100)
place_wire(*rawA_y3, SEG_Y3, "raw_A y=3 start")

# ================= Lever B: NOT_B (z=200) + raw_B (z=202) =================
s.set(-3, Y, 200, "minecraft:stone")
s.set(-2, Y, 200, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 200, "minecraft:redstone_torch[lit=true]")
dustB1 = (-2, Y + 1, 200)  # NOT_B dust
place_wire(*dustB1, SEG_Y3, "NOT_B dust")

dustRAW_B = (-1, Y, 200)
rp.floor_under(s, dustRAW_B)
s.set(*dustRAW_B, "minecraft:redstone_wire[power=0]")
rawB_step = rp.step(s, dustRAW_B, rp.EAST, up=True)   # (0,2,200)
rawB_settle = rp._add(rawB_step, rp.EAST)              # (1,2,200)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
# step up to y=4 at z=202: step EAST up from (1,2,200) -> (2,3,200) z=200 not 202!
# Need raw_B at z=202. Let's step SOUTH up: (1,3,201), then step SOUTH up: (1,4,202)
rawB_y3 = rp.step(s, rawB_settle, rp.SOUTH, up=True)   # (1,3,201)
rawB_y4 = rp.step(s, rawB_y3, rp.SOUTH, up=True)       # (1,4,202)
place_wire(*rawB_y4, SEG_Y4, "raw_B y=4 start")

# ================= S1 = merge(NOT_A, raw_B) -> Term1 @ (200,3,100) =================
S1 = (200, SEG_Y3, 100)
rp.converge(s, S1)  # stone at S1, y=3
# NOT_A: (-2,3,100) -> east to (199,3,100) [west of S1]
place_run_x(-2, 199, 100, SEG_Y3, "NOT_A to S1")
# raw_B: (1,4,202) -> east to (200,4,202) -> south to (200,4,100) [above S1]
place_run_x(1, 200, 202, SEG_Y4, "raw_B y=4 EW")
place_run_z(200, 202, 100, SEG_Y4, "raw_B y=4 NS")

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (200,4,100)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # (201,4,100)
place_wire(*term1_dust, SEG_Y4, "term1 dust")

# ================= S2 = merge(raw_A, NOT_B) -> Term2 @ (400,3,300) =================
S2 = (400, SEG_Y3, 300)
rp.converge(s, S2)
# raw_A: (2,3,100) -> east to (399,3,100) -> south to (399,3,300) [west of S2]
place_run_x(2, 399, 100, SEG_Y3, "raw_A EW to S2")
place_run_z(399, 100, 300, SEG_Y3, "raw_A NS to S2")
# NOT_B: (-2,3,200) -> east to (399,3,200) -> south to (399,3,300)?? No, same x as raw_A NS!
# NOT_B from south: dust at (400,3,201) powers S2 from south
place_run_x(-2, 400, 200, SEG_Y3, "NOT_B EW to S2")
place_run_z(400, 200, 201, SEG_Y3, "NOT_B NS to S2")

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (400,4,300)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # (401,4,300)
place_wire(*term2_dust, SEG_Y4, "term2 dust")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (300,4,300) =================
LAMP = (300, SEG_Y4, 300)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
# term1_dust(201,4,100) -> south to (201,4,300) -> east to LAMP(300,4,300)
place_run_z(201, 100, 300, SEG_Y4, "term1 to LAMP NS")
place_run_x(201, 300, 300, SEG_Y4, "term1 to LAMP EW")
# term2_dust(401,4,300) -> west to LAMP(300,4,300) [same z=300]
place_run_x(401, 300, 300, SEG_Y4, "term2 to LAMP EW")

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v18, no crossing paths)")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")
print(f"Segments: {len(segments)}")
