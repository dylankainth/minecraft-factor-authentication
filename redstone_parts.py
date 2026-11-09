"""Reusable redstone cell placement helpers, encoding every empirical
finding from CLAUDE.md so composed circuits can't silently reintroduce a
bug that's already been fixed once:

  - standing torches (not wall torches) for inversion -- wall torches
    don't cascade past their first dust neighbor in this MCHPRS build.
  - a repeater's `facing` names the direction power ENTERS from (not
    outputs to) in this stack.
  - repeaters are strictly straight-through -- these helpers only ever
    place them along one axis at a time, so a 90-degree mistake like
    the first AND-gate attempt is structurally impossible.
  - never merge two independent sources through shared dust -- there is
    no "merge dust" helper here on purpose; `converge` aims N repeaters
    directly at one consumer block instead.
  - every dust/repeater cell gets a floor block under it automatically.

Directions are unit vectors (dx,0,dz) or (0,dy,0); only horizontal
(dx,dz) directions are used for the travel axis of a wire/repeater run.
"""
from schem import Schematic

NORTH = (0, 0, -1)
SOUTH = (0, 0, 1)
EAST = (1, 0, 0)
WEST = (-1, 0, 0)
DIR_NAME = {NORTH: "north", SOUTH: "south", EAST: "east", WEST: "west"}


def _add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


def _opp(d):
    return (-d[0], -d[1], -d[2])


def floor_under(s, pos):
    s.set(pos[0], pos[1] - 1, pos[2], "minecraft:stone")


def place_not(s, support_pos, lever_dir, torch_dust_dir):
    """A standing-torch inverter: support block, wall lever on one side
    (strongly powers the support), standing torch on top (NOT output),
    one dust cell off the torch carrying the NOT signal.

    support_pos: (x,y,z) of the support block itself (needs no floor --
    plain solid blocks never need support).
    lever_dir: horizontal direction from support to the lever.
    torch_dust_dir: horizontal direction from the torch to its dust tap
    (must differ from lever_dir's cell so there's no collision -- the
    torch is one level above the lever anyway, so this is always safe).

    Returns dict: support, lever, torch, dust (all positions).
    """
    sx, sy, sz = support_pos
    s.set(sx, sy, sz, "minecraft:stone")
    lever_pos = _add(support_pos, lever_dir)
    s.set(*lever_pos, f"minecraft:lever[face=wall,facing={DIR_NAME[lever_dir]},powered=false]")
    torch_pos = (sx, sy + 1, sz)
    s.set(*torch_pos, "minecraft:redstone_torch[lit=true]")
    dust_pos = _add(torch_pos, torch_dust_dir)
    floor_under(s, dust_pos)
    s.set(*dust_pos, "minecraft:redstone_wire[power=0]")
    return {"support": support_pos, "lever": lever_pos, "torch": torch_pos, "dust": dust_pos}


def place_raw_tap(s, lever_pos, tap_dir):
    """A dust cell directly adjacent to a lever's own position, tapping
    its raw (non-inverted) power -- proven primitive (dust_test.schem):
    a lever directly powers adjacent dust at its own height.
    """
    dust_pos = _add(lever_pos, tap_dir)
    floor_under(s, dust_pos)
    s.set(*dust_pos, "minecraft:redstone_wire[power=0]")
    return dust_pos


def extend_repeater(s, dust_in_pos, travel_dir, delay=1):
    """Places one repeater immediately past a dust cell, continuing in
    travel_dir. facing = the direction INPUT comes from (= opposite of
    travel_dir), per the empirical finding in build_repeater_test.py.
    Returns (repeater_pos, output_pos) -- output_pos is the next free
    cell in travel_dir, where the signal continues or lands on a consumer.
    """
    rep_pos = _add(dust_in_pos, travel_dir)
    floor_under(s, rep_pos)
    facing = DIR_NAME[_opp(travel_dir)]
    s.set(*rep_pos, f"minecraft:repeater[facing={facing},powered=false,locked=false,delay={delay}]")
    output_pos = _add(rep_pos, travel_dir)
    return rep_pos, output_pos


def step(s, dust_pos, direction, up=True):
    """Non-inverting height change: one more dust cell, offset by
    `direction` and one level up (or down), with its own floor. Vanilla
    redstone dust auto-connects across a single-block step like this
    (the standard "redstone staircase") -- no repeater or torch needed,
    just plain dust at two different heights with nothing blocking the
    diagonal between them. Signal strength drops by 1 per hop as usual.
    Needed because different inversion-depth signals (e.g. a "raw" lever
    tap vs. a once-inverted torch tap) naturally end up at different
    heights in this library's placement scheme, and two signals must be
    at the same height to converge on one consumer block.
    """
    dy = 1 if up else -1
    new_pos = _add(_add(dust_pos, direction), (0, dy, 0))
    floor_under(s, new_pos)
    s.set(*new_pos, "minecraft:redstone_wire[power=0]")
    return new_pos


def travel(s, start_pos, target_pos, land_as=None):
    """Chains however many repeaters are needed to carry a signal in a
    straight line from a dust cell at start_pos to land exactly on
    target_pos (which must share two of the three coordinates with
    start_pos -- the travel axis is inferred). Raises if they don't
    share an axis, so a caller's geometry mistake fails immediately
    instead of silently placing something crossed-up.

    land_as="dust": place a plain dust cell (with floor) at target_pos,
    fed by the last repeater -- use this when target_pos is a turn
    waypoint (only dust is omnidirectional; a repeater can't bend) or
    any other point where the signal needs to continue as wire rather
    than power a final consumer directly.
    land_as=None (default): target_pos is left for the caller to place
    (a consumer block, a lamp, or another travel()'s start_pos after
    this leg's repeater has already landed its output there).
    """
    diffs = [target_pos[i] - start_pos[i] for i in range(3)]
    nonzero = [(i, d) for i, d in enumerate(diffs) if d != 0]
    if len(nonzero) != 1:
        raise ValueError(f"start {start_pos} -> target {target_pos} is not a straight line (diffs={diffs})")
    axis, delta = nonzero[0]
    step_dir = [0, 0, 0]
    step_dir[axis] = 1 if delta > 0 else -1
    step_dir = tuple(step_dir)
    hops = abs(delta)
    if hops < 1:
        raise ValueError(f"start {start_pos} and target {target_pos} are the same cell")
    # k repeaters chained from a dust/repeater at start_pos land their
    # final output at start_pos + (k+1)*step_dir; we want that to equal
    # target_pos = start_pos + hops*step_dir, so k = hops - 1. If hops==1
    # target is directly adjacent to start_pos already -- no repeater
    # needed at all, it'll just receive start_pos's power by adjacency.
    cur = start_pos
    out = target_pos if hops == 1 else None
    for _ in range(hops - 1):
        cur, out = extend_repeater(s, cur, step_dir)
    assert out == target_pos, f"travel({start_pos}->{target_pos}) landed at {out}, not {target_pos}"
    if land_as == "dust":
        floor_under(s, target_pos)
        s.set(*target_pos, "minecraft:redstone_wire[power=0]")
    return out


def converge(s, consumer_pos, consumer_block="minecraft:stone"):
    """Places the shared consumer block that one or more repeater outputs
    will land on directly (the proven OR-merge pattern -- never put dust
    here, always a solid block or lamp so there's no shared-dust-merge
    limitation to hit). Caller is responsible for making each
    extend_repeater's output_pos equal to consumer_pos.
    """
    s.set(*consumer_pos, consumer_block)
    return consumer_pos
