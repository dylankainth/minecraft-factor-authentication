"""OR gate -- history of attempts, kept because it's the actual finding:

Take 1 (lever directly adjacent to junction, T-shape): junction's own
power correctly showed OR logic (0/15) but the lamp never lit. Isolated
to "junction touching a bare lever" via build_t_junction_test.py (inert
stone 3rd neighbor: fine; unpowered lever 3rd neighbor: breaks it).

Take 2 (one dust stub between each lever and the junction, so the
junction's neighbors are dust/dust/lamp, never a bare lever): junction
STILL correctly showed OR logic (power 14) but the lamp STILL never lit.
So it isn't "levers vs stone" -- it's two independently-sourced paths
merging at a shared dust point specifically.

Take 3+4 (route each branch through a repeater before merging; had to fix
the repeater's `facing` property along the way -- it names the direction
power ENTERS from in this stack, not the direction it outputs to, see
build_repeater_test.py): both repeaters correctly showed powered=true
when their lever was on, junction correctly showed power=15 -- and the
lamp STILL never lit. So the break is a real limitation of this MCHPRS
build's dust-merge handling with 2+ distinct source-capable neighbors,
not something fixable by choosing different input component types.

Take 5 (this one, working): skip the shared dust junction entirely. Each
repeater outputs directly into the lamp from a different side -- no
dust node in between to misbehave. A lamp just needs to be adjacent to
something sufficiently powered; it doesn't compute a "merge". Each
repeater is already proven to power an adjacent lamp alone
(repeater_test.schem), so two of them on different faces of the same
lamp needs no new primitive, just no shared wire.

Layout, floor at y=0 under every used (x,z), components at y=1:
  leverA(2,0) -> repeaterA(2,1)[facing=north] -> lamp(2,2)  <- powered from north
  leverB(0,2) -> repeaterB(1,2)[facing=west]  -> lamp(2,2)  <- powered from west
"""
from schem import Schematic

s = Schematic()
for x, z in [(2, 0), (2, 1), (2, 2), (0, 2), (1, 2)]:
    s.set(x, 0, z, "minecraft:stone")
s.set(2, 1, 0, "minecraft:lever[face=floor,facing=north,powered=false]")
s.set(2, 1, 1, "minecraft:repeater[facing=north,powered=false,locked=false,delay=1]")
s.set(2, 1, 2, "minecraft:redstone_lamp[lit=false]")
s.set(0, 1, 2, "minecraft:lever[face=floor,facing=east,powered=false]")
s.set(1, 1, 2, "minecraft:repeater[facing=west,powered=false,locked=false,delay=1]")
s.save("or_gate_test.schem")
print("wrote or_gate_test.schem: leverA=(2,1,0) repA=(2,1,1) lamp=(2,1,2) repB=(1,1,2) leverB=(0,1,2)")
