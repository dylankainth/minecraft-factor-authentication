"""Minimal diagnostic: does a standing torch on top of a REPEATER-powered
stone block reliably RE-LIGHT when the stone loses power?

  lever -> (support block strongly powered) -> dust tap -> repeater chain ->
  stone S -> torch on top of S -> dust -> lamp

  lever OFF: S unpowered, torch LIT, dust on, lamp ON
  lever ON:  S powered,  torch unlit, dust off, lamp OFF
  So lamp == NOT(lever), and the OFF->ON lever transition tests torch relight.

place_not (lever directly on support) already relights reliably; this tests
whether the repeater->stone->torch path relights, which is exactly what
Term1/Term2 depend on.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()
Y = 1

# support block + wall lever (lever powers support strongly)
sup = (0, Y, 0)
s.set(*sup, "minecraft:stone")
lever = rp._add(sup, rp.EAST)
s.set(*lever, "minecraft:lever[face=wall,facing=east,powered=false]")

# dust tap adjacent to support block, taps its strong power
dust_in = rp._add(sup, rp.SOUTH)
rp.floor_under(s, dust_in)
s.set(*dust_in, "minecraft:redstone_wire[power=0]")

# repeater chain carries dust_in's power into stone S from the west
S = (6, Y, 1)
rp.converge(s, S)  # stone at S
rp.travel(s, dust_in, S)  # dust_in(0,1,1) -> east -> S(6,1,1), output into S from west

# standing torch on top of S (the inverter)
torch = (S[0], S[1] + 1, S[2])
s.set(*torch, "minecraft:redstone_torch[lit=true]")

# dust south of torch carries the inverted signal
out_dust = rp._add(torch, rp.SOUTH)
rp.floor_under(s, out_dust)
s.set(*out_dust, "minecraft:redstone_wire[power=0]")

# lamp east of the dust (proven: dust powers adjacent lamp)
lamp = rp._add(out_dust, rp.EAST)
rp.floor_under(s, lamp)
s.set(*lamp, "minecraft:redstone_lamp[lit=false]")

s.save("torch_relight_test.schem")
print("wrote torch_relight_test.schem")
print(f"lever={lever} torch={torch} out_dust={out_dust} lamp={lamp} S={S}")
