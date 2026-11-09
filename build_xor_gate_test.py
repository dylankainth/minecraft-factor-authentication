"""XOR gate, built from the verified NOT/OR primitives plus the new
`step()`/`travel()` helpers in redstone_parts.py.

Identity: XOR(A,B) = OR(Term1, Term2) where
  Term1 = AND(raw_A, NOT_B) = NOT(NOT_A OR raw_B)   [De Morgan]
  Term2 = AND(NOT_A, raw_B) = NOT(raw_A OR NOT_B)   [De Morgan]
(raw_X = X itself, untouched; NOT_X = one inversion.)

Each Term needs one merge+invert stage; the AND-via-De-Morgan inputs
(NOT_A/raw_B for Term1, raw_A/NOT_B for Term2) are already directly
available, no extra inverters needed. 4 torches total: NOT_A, NOT_B
(direct from the levers) plus Term1, Term2 (the merge+invert stages).
Final OR of Term1,Term2 needs no inversion, straight repeater
convergence onto the lamp, same as the verified OR gate.

Layout strategy (reached after several collision-driven rewrites --
`Schematic.set()`'s overwrite check and `travel()`'s landing assertion
caught each one immediately, which is the whole point of having them):
every merge point (S1, S2, the lamp) sits with generous clearance on
ALL sides; its two feeders approach from two of its four cardinal
neighbors (never the same one), and whichever stage comes next (the
inverting torch's own output, or the final OR) uses one of the two
UNUSED neighbors so its own floor requirement can never land on a cell
an approach chain is already using. Raw taps (0 inversions) land one
level below NOT taps (1 inversion) in this scheme, reconciled with one
step() per raw signal before it travels.
"""
from schem import Schematic
import redstone_parts as rp

s = Schematic()

# ---- input A: NOT_A (direct) and raw_A (stepped up one level) ----
SA = (0, 1, 0)
notA = rp.place_not(s, SA, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverA, dustA1 = notA["lever"], notA["dust"]  # dustA1 = NOT_A, y=2

dustRAW_A = rp.place_raw_tap(s, leverA, rp.EAST)    # y=1 -- EAST not SOUTH: SOUTH landed directly
rawA = rp.step(s, dustRAW_A, rp.EAST, up=True)      # under NOT_A's own eastward travel row (z=1)
# and collided on the floor cell. EAST keeps raw_A at z=0, clear of it.

# ---- input B: NOT_B (direct) and raw_B (stepped up one level) ----
SB = (0, 1, 30)
notB = rp.place_not(s, SB, lever_dir=rp.EAST, torch_dust_dir=rp.SOUTH)
leverB, dustB1 = notB["lever"], notB["dust"]  # dustB1 = NOT_B, y=2

dustRAW_B = rp.place_raw_tap(s, leverB, rp.EAST)    # y=1 -- same fix as raw_A, avoid NOT_B's row (z=31)
rawB = rp.step(s, dustRAW_B, rp.EAST, up=True)      # y=2

# ==== S1 = merge(NOT_A, raw_B) -> Term1 = NOT(S1) ====
# NOT_A approaches from the WEST, raw_B from the SOUTH. Term1's own
# output then uses NORTH or EAST, both guaranteed clear.
S1 = (50, 2, 50)
rp.converge(s, S1)

wpA1 = rp.travel(s, dustA1, (50, 2, 1), land_as="dust")   # east, staying at NOT_A's own z=1
rp.travel(s, wpA1, S1)                                     # straight south into S1 -- approaches from the north

wpB1 = rp.travel(s, rawB, (3, 2, 50), land_as="dust")     # straight south, rawB is already x=3
rp.travel(s, wpB1, S1)                                     # straight east into S1 -- approaches from the west

term1_torch = (S1[0], S1[1] + 1, S1[2])
s.set(*term1_torch, "minecraft:redstone_torch[lit=true]")
term1_dust = (term1_torch[0] + 1, term1_torch[1], term1_torch[2])  # east of the torch, y=3
rp.floor_under(s, term1_dust)  # floor at (51,2,50) -- clear: approaches used north(x=50,z<50) and west(z=50,x<50)
s.set(*term1_dust, "minecraft:redstone_wire[power=0]")

# ==== S2 = merge(raw_A, NOT_B) -> Term2 = NOT(S2) ====
# raw_A approaches from the north, NOT_B from the west. Term2's output
# uses east, symmetric to Term1, at a different z so nothing crosses.
S2 = (50, 2, 90)
rp.converge(s, S2)

# raw_A approaches S2 from the EAST (not north -- a straight north column
# at S2's x would cross straight through S1 itself, since S1 sits at the
# same x between z=0 and z=90). Go east past S1's column, south to S2's
# z, then two hops west into S2.
wpA2a = rp.travel(s, rawA, (150, 2, 0), land_as="dust")  # well east of term1's output row (x=51..99 at z=50)
wpA2b = rp.travel(s, wpA2a, (150, 2, 90), land_as="dust")
rp.travel(s, wpA2b, S2)                                     # straight west into S2 -- approaches from the east

wpB2a = rp.travel(s, dustB1, (2, 2, 31), land_as="dust")   # east, staying at NOT_B's own z=31
wpB2b = rp.travel(s, wpB2a, (2, 2, 90), land_as="dust")    # straight south to S2's z, staying at x=2
rp.travel(s, wpB2b, S2)                                     # straight east into S2 from the west

term2_torch = (S2[0], S2[1] + 1, S2[2])
s.set(*term2_torch, "minecraft:redstone_torch[lit=true]")
# S2's west and east neighbors are both used (NOT_B, raw_A) -- use north
# instead (east collided: raw_A's final approach repeater sits right
# where an east-side floor would need to go).
term2_dust = (term2_torch[0], term2_torch[1], term2_torch[2] - 1)
rp.floor_under(s, term2_dust)
s.set(*term2_dust, "minecraft:redstone_wire[power=0]")

# ==== Final: XOR = OR(Term1, Term2) -> lamp ====
# term1_dust=(51,3,50): route straight east to the lamp (approaches from
# the west). term2_dust=(50,3,89): route east to the lamp's x, then
# north to the lamp's z (approaches from the south) -- different final
# neighbor than term1's, and the two paths never share a cell (term1
# stays at z=50, term2's north leg stays at x=100).
LAMP = (100, 3, 50)
rp.converge(s, LAMP, "minecraft:redstone_lamp[lit=false]")
rp.travel(s, term1_dust, LAMP)

wpL = rp.travel(s, term2_dust, (100, 3, 89), land_as="dust")
rp.travel(s, wpL, LAMP)

s.save("xor_gate_test.schem")
print("wrote xor_gate_test.schem")
print(f"leverA={leverA} leverB={leverB} lamp={LAMP}")
