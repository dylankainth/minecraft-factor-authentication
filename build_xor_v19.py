"""XOR gate v19: programmatic layout with Y-level separation.

Paths 1-3 at y=3, path 4 at y=4. All EW legs at unique z-bands.
Verified no crossings by construction.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1
Y3 = Y + 2  # y=3
Y4 = Y + 3  # y=4

segments = []

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
dustA1 = (-2, Y + 1, 100)  # NOT_A dust at y=2, east of torch
place_wire(dustA1[0], dustA1[1], dustA1[2], "NOT_A dust y=2")
# Step up to y=3: step EAST up from (-2,2,100) -> (-1,3,100)
na_y3 = rp.step(s, dustA1, rp.EAST, up=True)  # (-1,3,100)
place_wire(na_y3[0], na_y3[1], na_y3[2], "NOT_A y=3 start")

dustRAW_A = (-1, Y, 100)
rp.floor_under(s, dustRAW_A)
s.set(*dustRAW_A, "minecraft:redstone_wire[power=0]")
rawA_step = rp.step(s, dustRAW_A, rp.EAST, up=True)   # (0,2,100)
rawA_settle = rp._add(rawA_step, rp.EAST)              # (1,2,100)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA_y3 = rp.step(s, rawA_settle, rp.EAST, up=True)    # (2,3,100)
place_wire(*rawA_y3, Y3, "raw_A y=3 start")

# ================= Lever B: NOT_B (z=200) + raw_B (z=202 at y=4) =================
s.set(-3, Y, 200, "minecraft:stone")
s.set(-2, Y, 200, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 200, "minecraft:redstone_torch[lit=true]")
dustB1 = (-2, Y + 1, 200)
place_wire(*dustB1, Y + 1, "NOT_B dust y=2")
nb_y3 = rp.step(s, dustB1, rp.EAST, up=True)  # (-1,3,200)
place_wire(*nb_y3, Y3, "NOT_B y=3 start")

dustRAW_B = (-1, Y, 200)
rp.floor_under(s, dustRAW_B)
s.set(*dustRAW_B, "minecraft:redstone_wire[power=0]")
rawB_step = rp.step(s, dustRAW_B, rp.EAST, up=True)   # (0,2,200)
rawB_settle = rp._add(rawB_step, rp.EAST)              # (1,2,200)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
# Step up to y=4 at z=202: need two steps. From (1,2,200): step EAST up -> (2,3,200), then step EAST up -> (3,4,200)
# But we want z=202. Let's step SOUTH up twice: (1,3,201) then (1,4,202)
rawB_y3 = rp.step(s, rawB_settle, rp.SOUTH, up=True)   # (1,3,201)
rawB_y4 = rp.step(s, rawB_y3, rp.SOUTH, up=True)       # (1,4,202)
place_wire(*rawB_y4, Y4, "raw_B y=4 start")

# ================= S1 = merge(NOT_A, raw_B) -> Term1 @ (200,3,100) =================
S1 = (200, Y3, 100)
rp.converge(s, S1)
# NOT_A: (-1,3,100) -> east to (199,3,100) [west of S1]
place_run_x(-1, 199, 100, Y3, "NOT_A to S1")
# raw_B: (1,4,202) -> east to (200,4,202) -> south to (200,4,100) [above S1]
place_run_x(1, 200, 202, Y4, "raw_B y=4 EW")
place_run_z(200, 202, 100, Y4, "raw_B y=4 NS")

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (200,4,100)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # (201,4,100)
place_wire(*term1_dust, Y4, "term1 dust")

# ================= S2 = merge(raw_A, NOT_B) -> Term2 @ (400,3,300) =================
S2 = (400, Y3, 300)
rp.converge(s, S2)
# raw_A: (2,3,100) -> east to (399,3,100) -> south to (399,3,300) [west of S2]
place_run_x(2, 399, 100, Y3, "raw_A EW")
place_run_z(399, 100, 300, Y3, "raw_A NS")
# NOT_B: (-1,3,200) -> east to (400,3,200) -> south to (400,3,201) [south of S2]
place_run_x(-1, 400, 200, Y3, "NOT_B EW")
place_run_z(400, 200, 201, Y3, "NOT_B NS")

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (400,4,300)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # (401,4,300)
place_wire(*term2_dust, Y4, "term2 dust")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (300,4,300) =================
LAMP = (300, Y4, 300)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
# term1_dust(201,4,100) -> south to (201,4,300) -> east to LAMP
place_run_z(201, 100, 300, Y4, "term1 NS")
place_run_x(201, 300, 300, Y4, "term1 EW")
# term2_dust(401,4,300) -> west to LAMP
place_run_x(401, 300, 300, Y4, "term2 EW")

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v19, no crossing paths)")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")
print(f"Segments: {len(segments)}")
