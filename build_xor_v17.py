"""XOR gate v17: programmatic layout with automatic collision avoidance.

Places each signal path on its own z-band, checks all path crossings,
and raises if any crossing is detected.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1

# Track all placed path segments as (x_range, z_range, y) for crossing detection
# A path segment covers x in [x1,x2], z in [z1,z2] at a given y.
segments = []  # list of ((x1,x2),(z1,z2),y,label)

def add_segment(x1, x2, z1, z2, y, label):
    """Add a path segment and check for crossings with existing segments."""
    x1, x2 = sorted([x1, x2])
    z1, z2 = sorted([z1, z2])
    for (ex1, ex2), (ez1, ez2), ey, elabel in segments:
        if ey != y:
            continue  # different y levels don't cross
        # Cross if x ranges overlap AND z ranges overlap
        if x1 <= ex2 and x2 >= ex1 and z1 <= ez2 and z2 >= ez1:
            raise ValueError(
                f"CROSSING: {label} at x[{x1},{x2}] z[{z1},{z2}] y={y} "
                f"crosses {elabel} at x[{ex1},{ex2}] z[{ez1},{ez2}] y={ey}"
            )
    segments.append(((x1, x2), (z1, z2), y, label))

def place_wire(s, x, y, z, label):
    """Place a redstone dust wire and track it."""
    rp.floor_under(s, (x, y, z))
    s.set(x, y, z, "minecraft:redstone_wire[power=0]")
    add_segment(x, x, z, z, y, label)

def place_wire_run(s, x_start, x_end, z, y, label):
    """Place a horizontal run of wires at fixed z, from x_start to x_end."""
    step = 1 if x_end >= x_start else -1
    for x in range(x_start, x_end + step, step):
        place_wire(s, x, y, z, label)
    add_segment(min(x_start, x_end), max(x_start, x_end), z, z, y, label)

def place_wire_run_z(s, x, z_start, z_end, y, label):
    """Place a vertical run of wires at fixed x, from z_start to z_end."""
    step = 1 if z_end >= z_start else -1
    for z in range(z_start, z_end + step, step):
        place_wire(s, x, y, z, label)
    add_segment(x, x, min(z_start, z_end), max(z_start, z_end), y, label)

# ================= Lever A: NOT_A + raw_A =================
# Z-bands: NOT_A=100, raw_A=102
s.set(-3, Y, 100, "minecraft:stone")       # support A
s.set(-2, Y, 100, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 100, "minecraft:redstone_torch[lit=true]")  # torch A
dustA1 = (-2, Y + 1, 100)                   # NOT_A dust, east of torch, z=100
place_wire(s, *dustA1, "NOT_A dust")

dustRAW_A = (-1, Y, 100)                    # east of lever A
rp.floor_under(s, dustRAW_A)
s.set(*dustRAW_A, "minecraft:redstone_wire[power=0]")
add_segment(-1, -1, 100, 100, Y, "raw_A dust y=1")  # y=1, different level
rawA_step = rp.step(s, dustRAW_A, rp.SOUTH, up=True)  # step south & up: (-1,2,101)
rawA_settle = rp._add(rawA_step, rp.SOUTH)           # (-1,2,102)
rp.floor_under(s, rawA_settle)
s.set(*rawA_settle, "minecraft:redstone_wire[power=0]")
rawA = rawA_settle  # (-1,2,102), z=102

# ================= Lever B: NOT_B + raw_B =================
# Z-bands: NOT_B=200, raw_B=202
s.set(-3, Y, 200, "minecraft:stone")       # support B
s.set(-2, Y, 200, "minecraft:lever[face=wall,facing=east,powered=false]")
s.set(-3, Y + 1, 200, "minecraft:redstone_torch[lit=true]")  # torch B
dustB1 = (-2, Y + 1, 200)                   # NOT_B dust, east of torch, z=200
place_wire(s, *dustB1, "NOT_B dust")

dustRAW_B = (-1, Y, 200)                    # east of lever B
rp.floor_under(s, dustRAW_B)
s.set(*dustRAW_B, "minecraft:redstone_wire[power=0]")
rawB_step = rp.step(s, dustRAW_B, rp.SOUTH, up=True)  # (-1,2,201)
rawB_settle = rp._add(rawB_step, rp.SOUTH)           # (-1,2,202)
rp.floor_under(s, rawB_settle)
s.set(*rawB_settle, "minecraft:redstone_wire[power=0]")
rawB = rawB_settle  # (-1,2,202), z=202

# ================= S1 = merge(NOT_A, raw_B) -> Term1 @ (200,2,100) =================
# NOT_A approaches from west (dust at (199,2,100) powers S1 from west)
# raw_B approaches from south (dust at (200,2,101) powers S1 from south)
S1 = (200, Y + 1, 100)
rp.converge(s, S1)  # stone at S1

# NOT_A: (-2,2,100) -> east to (199,2,100) [dust west of S1]
place_wire_run(s, -2, 199, 100, Y + 1, "NOT_A to S1")

# raw_B: (-1,2,202) -> east to (200,2,202) -> south to (200,2,101) [dust south of S1]
place_wire_run(s, -1, 200, 202, Y + 1, "raw_B EW to S1")
place_wire_run_z(s, 200, 202, 101, Y + 1, "raw_B NS to S1")

term1_torch = (S1[0], S1[1] + 1, S1[2])  # (200,3,100)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # (201,3,100)
place_wire(s, *term1_dust, "term1 dust")

# ================= S2 = merge(raw_A, NOT_B) -> Term2 @ (400,2,200) =================
# raw_A approaches from west (dust at (399,2,102) powers S2 from west)
# NOT_B approaches from south (dust at (400,2,201) powers S2 from south)
S2 = (400, Y + 1, 200)
rp.converge(s, S2)

# raw_A: (-1,2,102) -> east to (399,2,102) [dust west of S2]
place_wire_run(s, -1, 399, 102, Y + 1, "raw_A to S2")

# NOT_B: (-2,2,200) -> east to (400,2,200) -> south to (400,2,201) [dust south of S2]
place_wire_run(s, -2, 400, 200, Y + 1, "NOT_B EW to S2")
place_wire_run_z(s, 400, 200, 201, Y + 1, "NOT_B NS to S2")

term2_torch = (S2[0], S2[1] + 1, S2[2])  # (400,3,200)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust = (term2_torch[0] + 1, term2_torch[1], term2_torch[2])  # (401,3,200)
place_wire(s, *term2_dust, "term2 dust")

# ================= Final: XOR = OR(Term1, Term2) -> lamp @ (300,3,300) =================
# term1_dust(201,3,100) -> south to (201,3,300) -> east to LAMP(300,3,300)
# term2_dust(401,3,200) -> south to (401,3,300) -> west to LAMP(300,3,300)
LAMP = (300, Y + 2, 300)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")

# term1 path at y=3
place_wire_run_z(s, 201, 100, 300, Y + 2, "term1 to LAMP NS")
place_wire_run(s, 201, 300, 300, Y + 2, "term1 to LAMP EW")

# term2 path at y=3
place_wire_run_z(s, 401, 200, 300, Y + 2, "term2 to LAMP NS")
place_wire_run(s, 401, 300, 300, Y + 2, "term2 to LAMP EW")

s.save("xor_compact_test.schem")
print("wrote xor_compact_test.schem (v17, no crossing paths)")
print(f"S1={S1} term1_torch={term1_torch} S2={S2} term2_torch={term2_torch}")
print(f"term1_dust={term1_dust} term2_dust={term2_dust} LAMP={LAMP}")
print(f"Total segments: {len(segments)}")
