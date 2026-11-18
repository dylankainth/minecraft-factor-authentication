"""XOR gate v20: programmatic layout with Y-level separation.

Paths 1-3 at y=3, path 4 at y=4. All EW legs at unique z-bands.
Verified no crossings by construction.

  XOR = OR(Term1, Term2)
    Term1 = NOT(NOT_A OR B)   -- S1 @ (200,3,100)
    Term2 = NOT(A OR NOT_B)   -- S2 @ (400,3,300)
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

def pw(x, y, z, label):
    rp.floor_under(s, (x, y, z))
    s.set(x, y, z, "minecraft:redstone_wire[power=0]")
    add_seg(x, x, z, z, y, label)

def prx(xs, xe, z, y, label):
    step = 1 if xe >= xs else -1
    for x in range(xs, xe + step, step):
        pw(x, y, z, label)
    add_seg(min(xs, xe), max(xs, xe), z, z, y, label)

def prz(x, zs, ze, y, label):
    step = 1 if ze >= zs else -1
    for z in range(zs, ze + step, step):
        pw(x, y, z, label)
    add_seg(x, x, min(zs, ze), max(zs, ze), y, label)

# ================= Lever A: NOT_A (z=100) + raw_A (z=101) =================
s.set(-3, Y, 100, "minecraft:stone")
s.set(-2, Y, 100, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 100, "minecraft:redstone_torch[lit=true]")
dustA1 = (-2, Y + 1, 100)
pw(*dustA1, "NOT_A dust y=2")
na_y3 = rp.step(s, dustA1, rp.EAST, up=True)   # (-1,3,100)
pw(*na_y3, "NOT_A y=3 start")

dustRAW_A = (-1, Y, 100)
rp.floor_under(s, dustRAW_A)
s.set(*dustRAW_A, "minecraft:redstone_wire[power=0]")
rawA_step = rp.step(s, dustRAW_A, rp.EAST, up=True)   # (0,2,100)
rawA_settle = rp._add(rawA_step, rp.EAST)              # (1,2,100)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA_y3 = rp.step(s, rawA_settle, rp.SOUTH, up=True)   # (1,3,101)
pw(*rawA_y3, "raw_A y=3 start")

# ================= Lever B: NOT_B (z=200) + raw_B (z=202 at y=4) =================
s.set(-3, Y, 200, "minecraft:stone")
s.set(-2, Y, 200, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 200, "minecraft:redstone_torch[lit=true]")
dustB1 = (-2, Y + 1, 200)
pw(*dustB1, "NOT_B dust y=2")
nb_y3 = rp.step(s, dustB1, rp.EAST, up=True)   # (-1,3,200)
pw(*nb_y3, "NOT_B y=3 start")

dustRAW_B = (-1, Y, 200)
rp.floor_under(s, dustRAW_B)
s.set(*dustRAW_B, "minecraft:redstone_wire[power=0]")
rawB_step = rp.step(s, dustRAW_B, rp.EAST, up=True)   # (0,2,200)
rawB_settle = rp._add(rawB_step, rp.EAST)              # (1,2,200)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB_y3 = rp.step(s, rawB_settle, rp.SOUTH, up=True)   # (1,3,201)
rawB_y4 = rp.step(s, rawB_y3, rp.SOUTH, up=True)       # (1,4,202)
pw(*rawB_y4, "raw_B y=4 start")

# ================= S1 = merge(NOT_A, raw_B) -> Term1 @ (200,3,100) =================
S1 = (200, Y3, 100)
rp.converge(s, S1)
# NOT_A: (-1,3,100) -> east to (199,3,100) [west of S1]
prx(-1, 199, 100, Y3, "NOT_A to S1")
# raw_B: (1,4,202) -> east to (200,4,202) -> south to (200,4,100) [above S1]
prx(1, 200, 202, Y4, "raw_B y=4 EW")
prz(200, 202, 100, Y4, "raw_B y=4 NS")

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (200,4,100)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # (201,4,100)
pw(*term1_dust, "term1 dust")

# ================= S2 = merge(raw_A, NOT_B) -> Term2 @ (400,3,300) =================
S2 = (400, Y3, 300)
rp.converge(s, S2)
# raw_A: (1,3,101) -> east to (399,3,101) -> south at x=400 from z=101 to z=299 [south of S2]
prx(1, 399, 101, Y3, "raw_A EW")
prz(400, 101, 299, Y3, "raw_A NS")
# NOT_B: (-1,3,200) -> east to (399,3,200) -> south at x=399 from z=200 to z=300 [west of S2]
prx(-1, 399, 200, Y3, "NOT_B EW")
prz(399, 200, 300, Y3, "NOT_B NS")

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (400,4,300)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # (401,4,300)
pw(*term2_dust, "term2 dust")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (300,4,300) =================
LAMP = (300, Y4, 300)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
# term1_dust(201,4,100) -> south to (201,4,300) -> east to x=299 [west of LAMP]
prz(201, 100, 300, Y4, "term1 NS")
prx(201, 299, 300, Y4, "term1 EW")
# term2_dust(401,4,300) -> west to x=301 [east of LAMP]
prx(401, 301, 300, Y4, "term2 EW")

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v20, no crossing paths)")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")
print(f"Segments: {len(segments)}")
