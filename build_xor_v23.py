"""XOR gate v23: final working layout.

z-bands at y=3: NOT_A=100, raw_A=101, NOT_B=200
z-band at y=4: raw_B=202
S1 at (200,3,100), S2 at (397,3,300), LAMP at (300,4,300)

Logic:
  Term1 = NOT(NOT_A OR B)   -- torch east of S1
  Term2 = NOT(A OR NOT_B)   -- torch above S2
  XOR = OR(Term1, Term2)
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
    if y > 1:
        pass  # floating dust at y>1, supported by diagonal connection
    else:
        rp.floor_under(s, (x, y, z))
    s.set(x, y, z, "minecraft:redstone_wire[power=0]")
    add_seg(x, x, z, z, y, label)

def prx(xs, xe, z, y, label):
    step = 1 if xe >= xs else -1
    for x in range(xs, xe + step, step):
        pw(x, y, z, label)

def prz(x, zs, ze, y, label):
    step = 1 if ze >= zs else -1
    for z in range(zs, ze + step, step):
        pw(x, y, z, label)

# ================= Lever A: NOT_A (z=100) + raw_A (z=101) =================
s.set(-3, Y, 100, "minecraft:stone")
s.set(-2, Y, 100, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 100, "minecraft:redstone_torch[lit=true]")
dustA1 = (-4, Y + 1, 100)  # NOT_A dust, WEST of torch
pw(*dustA1, "NOT_A dust y=2")
na_y3 = rp.step(s, dustA1, rp.WEST, up=True)   # (-5,3,100)
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
dustB1 = (-3, Y + 1, 201)  # NOT_B dust, SOUTH of torch
pw(*dustB1, "NOT_B dust y=2")
nb_y3 = rp.step(s, dustB1, rp.EAST, up=True)   # (-2,3,200)
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
# NOT_A: (-5,3,100) -> east to (199,3,100) [west of S1]
prx(-4, 199, 100, Y3, "NOT_A to S1")
# raw_B: (1,4,202) -> east to (200,4,202) -> south to (200,4,99) [north of S1]
prx(2, 200, 202, Y4, "raw_B y=4 EW")
prz(200, 201, 99, Y4, "raw_B y=4 NS")

# Term1: torch at (201,3,100) [east of S1], dust at (202,3,100)
term1_torch = (201, Y3, 100)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (202, Y3, 100)
pw(*term1_dust, "term1 dust")

# ================= S2 = merge(raw_A, NOT_B) -> Term2 @ (397,3,300) =================
S2 = (397, Y3, 300)
rp.converge(s, S2)
# raw_A: (1,3,101) -> east to (396,3,101) -> south at x=400 from z=102 to z=299 [south of S2]
prx(2, 396, 101, Y3, "raw_A EW")
prz(400, 102, 299, Y3, "raw_A NS")
# NOT_B: (-2,3,200) -> east to (397,3,200) -> south at x=397 from z=201 to z=299 [south of S2]
prx(-1, 397, 200, Y3, "NOT_B EW")
prz(397, 201, 299, Y3, "NOT_B NS")

# Term2: torch at (397,4,300) [above S2], dust at (397,4,301) [south of torch]
term2_torch = (397, Y4, 300)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (397, Y4, 301)
pw(*term2_dust, "term2 dust")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (300,4,300) =================
LAMP = (300, Y4, 300)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
# term1_dust(202,3,100) -> step up to y=4: (203,4,100) -> south to (203,4,300) -> east to x=299
t1_y4 = rp.step(s, term1_dust, rp.EAST, up=True)   # (203,4,100)
pw(*t1_y4, "term1 y=4 start")
prz(203, 101, 300, Y4, "term1 NS")
prx(204, 299, 300, Y4, "term1 EW")
# term2_dust(397,4,301) -> west at z=301 to x=301 -> south to z=300 at x=301
prx(396, 301, 301, Y4, "term2 EW")
pw(301, Y4, 300, "term2 to LAMP")

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v23, no crossing paths)")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")
print(f"Segments: {len(segments)}")
