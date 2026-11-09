"""Follow-up to build_rawb_path_test.py: LOW correctly tracked the lever
(0/10/0/10/0 -- not stuck), clearing raw_B's staircase path itself. But
the lamp placed east of LOW never lit, even at power=10. This test
surrounds LOW with lamps on all 4 horizontal sides plus straight above,
to see which placements (if any) actually receive power -- isolating
whether it's a direction-specific adjacency quirk off the end of a
staircase, or something else.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
SA = (0, 5, 0)
s.set(*SA, "minecraft:stone")
lever_pos = (SA[0], SA[1] + 1, SA[2])
s.set(*lever_pos, "minecraft:lever[face=floor,facing=north,powered=false]")
dust_pos = rp._add(lever_pos, rp.EAST)
rp.floor_under(s, dust_pos)
s.set(*dust_pos, "minecraft:redstone_wire[power=0]")

raw = rp.step(s, dust_pos, rp.EAST, up=True)
stage = rp.travel(s, raw, (raw[0] + 6, raw[1], raw[2]), land_as="dust")
stage2 = rp.travel(s, stage, (stage[0], stage[1], stage[2] + 3), land_as="dust")

def step_down_to(start, target_y, direction):
    cur = start
    while cur[1] > target_y:
        cur = rp.step(s, cur, direction, up=False)
    return cur

low = step_down_to(stage2, 2, rp.SOUTH)

# Lamps on all 4 horizontal sides + straight up. NORTH is skipped since
# that's back toward the staircase's previous cell (would collide).
lamp_e = rp._add(low, rp.EAST)
rp.floor_under(s, lamp_e)
s.set(*lamp_e, "minecraft:redstone_lamp[lit=false]")

lamp_s = rp._add(low, rp.SOUTH)
rp.floor_under(s, lamp_s)
s.set(*lamp_s, "minecraft:redstone_lamp[lit=false]")

lamp_w = rp._add(low, rp.WEST)
rp.floor_under(s, lamp_w)
s.set(*lamp_w, "minecraft:redstone_lamp[lit=false]")

lamp_up = (low[0], low[1] + 1, low[2])
s.set(*lamp_up, "minecraft:redstone_lamp[lit=false]")

s.save("rawb_lamp_test.schem")
xs = [p[0] for p in s.blocks]; ys = [p[1] for p in s.blocks]; zs = [p[2] for p in s.blocks]
minx, miny, minz = min(xs), min(ys), min(zs)
def local(p):
    return (p[0]-minx, p[1]-miny, p[2]-minz)
print(f"lever={local(lever_pos)} low={local(low)} lamp_e={local(lamp_e)} lamp_s={local(lamp_s)} lamp_w={local(lamp_w)} lamp_up={local(lamp_up)}")
