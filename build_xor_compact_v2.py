"""Compact XOR gate, v2: same De Morgan topology as build_xor_v23.py
(XOR = OR(Term1, Term2), Term1 = NOT(NOT_A OR raw_B), Term2 = NOT(raw_A OR NOT_B)),
but laid out in a small bounding box instead of ~400 blocks, with generous
per-lane spacing so lanes never need to run near each other.

Why this instead of iterating v23 further (see docs/handoff-xor-fix-2026-11-09.md):
  1. v23's probe never flew near S1/S2/LAMP (they're ~200-400 blocks from
     where the bot stood), so mineflayer's world model had no chunk data
     there and every read came back NULL -- the circuit may have been
     fine and untestable. Keeping everything inside ~20 blocks means one
     flyTo covers every read point.
  2. v23's only tool for crossing-avoidance was long staircases through
     unrelated territory. Here each of the 4 signals (raw_A, NOT_A,
     raw_B, NOT_B) gets its own x-OR-z corridor with several blocks of
     clearance from every other lane, so crossings don't come up at all.

An automated checker walks every placed wire cell (dust/repeater) and
flags any case where two different-labeled cells end up adjacent outside
of a declared convergence point -- catching accidental signal-bleed
before this ever touches a live server.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()

owner = {}       # (x,y,z) -> label
converge_points = set()


def place(label, x, y, z, block):
    key = (x, y, z)
    if key in owner and owner[key] != label:
        raise ValueError(f"COLLISION at {key}: {label} vs {owner[key]}")
    owner[key] = label
    s.set(x, y, z, block)


def dust(label, pos):
    rp.floor_under(s, pos)
    place(label, *pos, "minecraft:redstone_wire[power=0]")


def line(label, p_from, p_to, refresh=8):
    """Straight dust run, with a repeater dropped in every `refresh`
    cells so the signal never decays to 0 -- plain redstone dust only
    carries 15 blocks before dying out, and every lane here is longer
    than that with nothing but a single repeater at the very end. That
    turned out to be the actual bug in the first live test: every lever
    and its direct torch inverted correctly, but nothing downstream of a
    long dust run ever moved, because the signal was dead long before it
    reached S1/S2."""
    diffs = [p_to[i] - p_from[i] for i in range(3)]
    nz = [(i, d) for i, d in enumerate(diffs) if d != 0]
    assert len(nz) <= 1, f"line() needs a straight run: {p_from} -> {p_to}"
    if not nz:
        dust(label, p_from)
        return p_from
    axis, d = nz[0]
    step = 1 if d > 0 else -1
    dir_vec = [0, 0, 0]
    dir_vec[axis] = step
    dir_vec = tuple(dir_vec)
    cur = list(p_from)
    dust(label, tuple(cur))
    since_refresh = 0
    while tuple(cur) != p_to:
        since_refresh += 1
        nxt = tuple(cur[i] + dir_vec[i] for i in range(3))
        remaining = abs(p_to[axis] - nxt[axis])
        if since_refresh >= refresh and remaining >= 1:
            rp.floor_under(s, nxt)
            facing = rp.DIR_NAME[rp._opp(dir_vec)]
            place(label, *nxt, f"minecraft:repeater[facing={facing},powered=false,locked=false,delay=1]")
            since_refresh = 0
        else:
            dust(label, nxt)
        cur = list(nxt)
    return p_to


def repeater_into(label, dust_before, travel_dir, target):
    """Places one repeater between dust_before and target (the consumer
    block), reading from dust_before and outputting into target."""
    rep_pos = rp._add(dust_before, travel_dir)
    expected_target = rp._add(rep_pos, travel_dir)
    assert expected_target == target, f"repeater_into: {expected_target} != target {target}"
    rp.floor_under(s, rep_pos)
    facing = rp.DIR_NAME[rp._opp(travel_dir)]
    place(label, *rep_pos, f"minecraft:repeater[facing={facing},powered=false,locked=false,delay=1]")


def check_adjacency():
    neighbors = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    problems = []
    for pos, label in owner.items():
        if pos in converge_points:
            continue
        for d in neighbors:
            npos = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
            if npos in owner and npos not in converge_points and owner[npos] != label:
                problems.append((pos, label, npos, owner[npos]))
    return problems


# ===================== Lever A + NOT_A torch (x~0, z~0) ===================
SA = (1, 1, 0)
s.set(*SA, "minecraft:stone")
leverA = (0, 1, 0)
s.set(*leverA, "minecraft:lever[face=wall,facing=west,powered=false]")
torchA = (1, 2, 0)
s.set(*torchA, "minecraft:redstone_torch[lit=true]")

# ===================== Lever B + NOT_B torch (x~0, z~20) ==================
SB = (1, 1, 20)
s.set(*SB, "minecraft:stone")
leverB = (0, 1, 20)
s.set(*leverB, "minecraft:lever[face=wall,facing=west,powered=false]")
torchB = (1, 2, 20)
s.set(*torchB, "minecraft:redstone_torch[lit=true]")

# ===================== raw_A: z=4 lane, y=1 ================================
rawA0 = (0, 1, 1)
dust("raw_A", rawA0)
line("raw_A", rawA0, (0, 1, 4))

# ===================== NOT_A: z=0 lane, y=2 =================================
notA0 = (2, 2, 0)
dust("NOT_A", notA0)
line("NOT_A", notA0, (18, 2, 0))

# ===================== raw_B: z=16 lane, y=1 (tap at z=19) ==================
rawB0 = (0, 1, 19)
dust("raw_B", rawB0)
line("raw_B", rawB0, (0, 1, 16))
line("raw_B", (0, 1, 16), (16, 1, 16))

# ===================== NOT_B: z=20 lane, y=2 =================================
notB0 = (2, 2, 20)
dust("NOT_B", notB0)
line("NOT_B", notB0, (18, 2, 20))

# ===================== S1 = converge(NOT_A, raw_B) -> Term1 =================
# NOT_A (z=0,y=2) travels south through z=1..7 at x=18 (clear of raw_A's
# z=4 lane: raw_A's lane is y=1, this excursion is y=2, so NOT_A's floor
# (at y=1) would sit on raw_A's wire if they shared x -- raw_A's lane
# runs x=0..16, so the excursion uses x=18, outside that range).
line("NOT_A", (18, 2, 0), (18, 2, 6))
S1 = (18, 2, 8)
converge_points.add(S1)
s.set(*S1, "minecraft:stone")
repeater_into("NOT_A", (18, 2, 6), rp.SOUTH, S1)
converge_points.add((18, 2, 7))

# raw_B (z=16,y=1) travels north through z=15..10 at x=17 (one column west
# of NOT_A's excursion, clear of it; also clear of NOT_B's z=20 lane and
# of raw_A's z=4 lane since x=17 is outside raw_A's x=0..16 span).
line("raw_B", (16, 1, 16), (17, 1, 16))
line("raw_B", (17, 1, 16), (17, 1, 10))
rb_up = rp.step(s, (17, 1, 10), rp.EAST, up=True)  # -> (18,2,10)
owner[rb_up] = "raw_B"
repeater_into("raw_B", rb_up, rp.NORTH, S1)
converge_points.add((18, 2, 9))

term1_torch = (18, 3, 8)
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust0 = (19, 3, 8)
dust("Term1", term1_dust0)

# ===================== S2 = converge(raw_A, NOT_B) -> Term2 =================
# S1's neighborhood (x=17-18, z=6-10) turned out saturated enough that
# every one of S2's 4 faces collided with something if S2 sat right next
# to it. Simpler fix: put S2 out in open ground, far from that cluster,
# and give raw_A/NOT_B the extra few blocks of travel to reach it.
# raw_A's straight z=4,y=1 lane runs into NOT_A's wall at x=18 (NOT_A's
# dust itself, not just its floor, occupies x=18,z=0-7,y=2) -- one level
# of hop isn't enough clearance, so wiggle in z to gain a 2nd level before
# crossing, then mirror it coming back down.
line("raw_A", (0, 1, 4), (16, 1, 4))
ra_up1 = rp.step(s, (16, 1, 4), rp.NORTH, up=True)  # -> (16,2,3), away from NOT_A's x=18 lane
owner[ra_up1] = "raw_A"
ra_up2 = rp.step(s, ra_up1, rp.EAST, up=True)  # -> (17,3,3)
owner[ra_up2] = "raw_A"
ra_up3 = rp.step(s, ra_up2, rp.SOUTH, up=True)  # -> (17,4,4)
owner[ra_up3] = "raw_A"
line("raw_A", ra_up3, (19, 4, 4))  # clears x=18 at y=4 (NOT_A tops out at y=2)
ra_down1 = rp.step(s, (19, 4, 4), rp.EAST, up=False)  # -> (20,3,4)
owner[ra_down1] = "raw_A"
ra_down2 = rp.step(s, ra_down1, rp.EAST, up=False)  # -> (21,2,4)
owner[ra_down2] = "raw_A"
ra_down3 = rp.step(s, ra_down2, rp.EAST, up=False)  # -> (22,1,4)
owner[ra_down3] = "raw_A"
line("raw_A", ra_down3, (28, 1, 4))
S2 = (30, 1, 4)
converge_points.add(S2)
s.set(*S2, "minecraft:stone")
repeater_into("raw_A", (28, 1, 4), rp.EAST, S2)
converge_points.add((29, 1, 4))

line("NOT_B", (18, 2, 20), (30, 2, 20))
line("NOT_B", (30, 2, 20), (30, 2, 7))
nb_down = rp.step(s, (30, 2, 7), rp.NORTH, up=False)  # -> (30,1,6)
owner[nb_down] = "NOT_B"
repeater_into("NOT_B", nb_down, rp.NORTH, S2)
converge_points.add((30, 1, 5))

term2_torch = (30, 2, 4)
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
term2_dust0 = (30, 2, 3)  # north side -- open ground here, nothing adjacent
dust("Term2", term2_dust0)

problems = check_adjacency()
if problems:
    print(f"ADJACENCY PROBLEMS: {len(problems)}")
    for p in problems:
        print(" ", p)
    raise SystemExit(1)
print("No adjacency problems so far (pre-LAMP).")

# ===================== LAMP = converge(Term1, Term2) =========================
# A repeater's input/output must stay on one axis -- so each term's dust
# approaches LAMP's north or south face along a lane exactly one block
# off LAMP's own z, with the repeater as the very last straight hop.
LAMP = (22, 2, 9)

t1 = rp.step(s, term1_dust0, rp.EAST, up=False)  # -> (20,2,8)
owner[t1] = "Term1"
line("Term1", t1, (20, 2, 7))  # turn: z 8 -> 7 (one north of LAMP's lane)
line("Term1", (20, 2, 7), (22, 2, 7))

# raw_A's z=4 lane blocks every x from 0-28 at y=1, and NOT_B's lane
# occupies x=30,z=7-20 -- thread between both: east to x=32 (clear),
# south only to z=5 (short of NOT_B's z=7 start), west to x=23 (short of
# Term1's x=22 column at z=7/8), then south the rest of the way at x=23.
line("Term2", term2_dust0, (32, 2, 3))
line("Term2", (32, 2, 3), (32, 2, 2))
line("Term2", (32, 2, 2), (24, 2, 2))
line("Term2", (24, 2, 2), (24, 2, 3))
# raw_A's z=4 lane blocks every x in 22-28 at y=1 -- hop over it like
# raw_A hopped over NOT_A's wall, instead of threading around it again.
# x=24, not 23, to stay clear of Term1's own column at x=22 (adjacent at
# x=23) once both run parallel down to z=11.
t2_hop_up = rp.step(s, (24, 2, 3), rp.SOUTH, up=True)  # -> (24,3,4)
owner[t2_hop_up] = "Term2"
t2_hop_down = rp.step(s, t2_hop_up, rp.SOUTH, up=False)  # -> (24,2,5)
owner[t2_hop_down] = "Term2"
line("Term2", t2_hop_down, (24, 2, 11))
line("Term2", (24, 2, 11), (22, 2, 11))

converge_points.add(LAMP)
s.set(*LAMP, "minecraft:redstone_lamp[lit=false]")
repeater_into("Term1", (22, 2, 7), rp.SOUTH, LAMP)
converge_points.add((22, 2, 8))
repeater_into("Term2", (22, 2, 11), rp.NORTH, LAMP)
converge_points.add((22, 2, 10))

problems = check_adjacency()
if problems:
    print(f"ADJACENCY PROBLEMS: {len(problems)}")
    for p in problems:
        print(" ", p)
    raise SystemExit(1)

print("No adjacency problems.")
xs = [p[0] for p in s.blocks]
ys = [p[1] for p in s.blocks]
zs = [p[2] for p in s.blocks]
HANDLE = ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2, (min(zs) + max(zs)) // 2)
print(f"bbox x:{min(xs)}-{max(xs)} y:{min(ys)}-{max(ys)} z:{min(zs)}-{max(zs)} HANDLE(local)={HANDLE}")
s.save("xor_compact_v2.schem", we_offset=(-HANDLE[0], -HANDLE[1], -HANDLE[2]))
print("wrote xor_compact_v2.schem")
print(f"leverA={leverA} leverB={leverB}")
print(f"S1={S1} S2={S2} term1_torch={term1_torch} term2_torch={term2_torch} LAMP={LAMP}")
