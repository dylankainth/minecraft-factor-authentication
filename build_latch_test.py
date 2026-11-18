"""Latch/reliability test: do step-landing dust cells latch power?

Floor lever at (0,1,0), support below at (0,0,0). Three chains in separate z-bands:
  Chain 1 (baseline, no step):   lever -> dust(0,1,1) -> repeaters -> dust(4,1,1) -> lamp1(5,1,1)  [y=1,z=1]
  Chain 2 (step, no settle):     lever -> dust(1,1,0) -> step-landing(1,2,-1) -> repeaters -> dust(5,2,-1) -> lamp2(6,2,-1)  [y=2,z=-1]
  Chain 3 (step + settle hop):   lever -> dust(-1,1,0) -> step-landing(-1,2,1) -> settle(0,2,1) -> repeaters south -> dust(0,2,5) -> lamp3(0,2,6)  [y=2]

Expected: all three lamps track the lever. If lamp2/lamp3 stay on after lever
turns off, step landings latch power.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()

s.set(0, 0, 0, "minecraft:stone")  # support below lever
lever = (0, 1, 0)
s.set(*lever, "minecraft:lever[face=floor,facing=north,powered=false]")

# Chain 1: baseline, no step. y=1,z=1.
d1 = rp._add(lever, rp.SOUTH)  # (0,1,1)
rp.floor_under(s, d1)
s.set(*d1, "minecraft:redstone_wire[power=0]")
wp1 = rp.travel(s, d1, (4, 1, 1), land_as="dust")  # dust (4,1,1)
lamp1 = rp._add(wp1, rp.EAST)  # (5,1,1)
rp.floor_under(s, lamp1)
s.set(*lamp1, "minecraft:redstone_lamp[lit=false]")

# Chain 2: step up NORTH, landing feeds repeaters directly (no settle). y=2,z=-1.
d2 = rp._add(lever, rp.EAST)  # (1,1,0)
rp.floor_under(s, d2)
s.set(*d2, "minecraft:redstone_wire[power=0]")
step2 = rp.step(s, d2, rp.NORTH, up=True)  # (1,2,-1) step landing
wp2 = rp.travel(s, step2, (5, 2, -1), land_as="dust")  # dust (5,2,-1)
lamp2 = rp._add(wp2, rp.EAST)  # (6,2,-1)
rp.floor_under(s, lamp2)
s.set(*lamp2, "minecraft:redstone_lamp[lit=false]")

# Chain 3: step up SOUTH + settle hop before repeaters. y=2, travel south along x=0.
d3 = rp._add(lever, rp.WEST)  # (-1,1,0)
rp.floor_under(s, d3)
s.set(*d3, "minecraft:redstone_wire[power=0]")
step3 = rp.step(s, d3, rp.SOUTH, up=True)  # (-1,2,1) step landing
settle3 = rp._add(step3, rp.SOUTH)  # (-1,2,2) settle hop (direction of travel)
rp.floor_under(s, settle3)
s.set(*settle3, "minecraft:redstone_wire[power=0]")
wp3 = rp.travel(s, settle3, (-1, 2, 5), land_as="dust")  # dust (-1,2,5)
lamp3 = rp._add(wp3, rp.SOUTH)  # (-1,2,6)
rp.floor_under(s, lamp3)
s.set(*lamp3, "minecraft:redstone_lamp[lit=false]")

s.save("latch_test.schem")
print("wrote latch_test.schem")
print(f"lever={lever} lamp1={lamp1} lamp2={lamp2} lamp3={lamp3}")
print(f"step2={step2} step3={step3} settle3={settle3}")
