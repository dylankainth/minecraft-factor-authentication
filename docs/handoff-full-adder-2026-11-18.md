# Handoff — 1-bit full adder: partial progress, stopped honestly (2026-11-18)

## Context

Following up on `docs/handoff-xor-plot-fix-2026-11-18.md`, asked to move on to the 1-bit full adder (the next step in `CLAUDE.md`'s recommended path). This doc covers that attempt.

## Design (sound, unchanged from the plan)

Standard two-half-adder decomposition, using only the already-proven AND/OR primitives (never XOR itself, since that's still not live-verified):

```
HA1: P = A xor B, C1 = A and B
  P    = OR(Term1a, Term2a), Term1a = AND(A,NOT_B), Term2a = AND(NOT_A,B)
  C1   = AND(A,B)
HA2: Sum = P xor Cin, C2 = P and Cin
  Sum  = OR(Term1b, Term2b), Term1b = AND(P,NOT_Cin), Term2b = AND(NOT_P,Cin)
  C2   = AND(P,Cin)
Carry = OR(C1, C2)
```

`XOR(P,Cin)` needs both raw `P` and `NOT_P` as dust signals. Since `P` is the output of an OR-merge block (not a lever), raw `P` has to be recovered by inverting `NOT_P` a second time (double negation) — reusing only the proven "repeater output into a support, torch on top = inverted signal" mechanism, never an untested one.

## What's actually built and verified offline

`build_full_adder_test.py`, currently: 3 inputs (A, B, Cin, each with lever/support/torch/raw-tap), and **both AND terms of the first half-adder** — `Term1a = AND(A, NOT_B)` and `Term2a = AND(NOT_A, B)`. 363 blocks. Passes the offline collision checker (`place()`/`owner`) and the 2D per-height crossing checker (`add_seg`, ported from `build_xor_v23.py`) cleanly. **Not live-tested** — correctly prioritized finishing the offline design first, consistent with tonight's XOR findings that live verification is currently unreliable regardless of correctness.

Not built: the OR that combines `Term1a`/`Term2a` into `P`, `C1`, both of HA2's AND terms, `NOT_P`/`P` (the double inversion), `Sum`'s OR, `C2`, and the final `Carry` OR. Roughly 6 more merge points.

## Why stopped here

Building `Term1a` and `Term2a` required routing raw/inverted input signals around each other's existing structure — the exact same category of problem as the XOR session, just smaller in scope. Three different approaches were tried, in order:

1. **Height-layered compaction** (give every signal its own y, route via short hops) — this is what `build_xor_compact_v2.py` used. Reapplying it here produced the same kind of narrow collisions that session eventually worked through, but slower this time because there are *more* signals needing independent lanes (14+ named signals vs. XOR's 4) and the input levers are closer together, leaving less natural separation.
2. **Flat z-bands** (one dedicated z per signal, the style of the original, pre-compaction `build_xor_v23.py`, which never had a single collision bug) — reused successfully for the 3 inputs and `Term1a`, but `Term2a`'s inputs (`raw_A`, `NOT_B`) turned out to be boxed in by neighbors' already-claimed cells on 3 of their 4 sides, needing ad hoc escapes.
3. **A general-purpose router** (`route()`/`monotonic_shaft()` in the current file) — written specifically to stop hand-deriving a new escape for every single blocked signal. It works (`Term2a` was finished with it), but getting it to a working state took several rounds of a very specific failure pattern: a travel leg's floor requirement would land exactly on a cell an adjacent vertical shaft needed, fixed by separating which axis each leg/shaft uses, which then surfaced as **two different calls'** paths crossing each other (not self-collisions anymore), fixed by padding each call's horizontal travel 30 cells further out before doing its height change. Each fix solved the specific case in front of it and then uncovered a different, narrower one. `route()` as it stands now has not yet been proven to generalize to the remaining 6 merges without further iteration of the same kind.

**This is reported as a real, open gap rather than pushed through with more band-aid fixes**, per this project's working rule to report honestly rather than fake a result — and because continuing to patch increasingly specific collision cases without a principled reason to believe the *next* one won't need its own new fix is a sign the approach itself, not just this instance of it, needs reconsidering before investing more time in it.

## What would help a future session

- **`route()` likely needs a genuine redesign, not another patch.** The core tension: a vertical height-change (shaft) and a horizontal travel leg sharing an axis will self-collide; avoiding that by switching axes works until two *different* signals' legs end up sharing the axis/position instead. A real fix probably needs a shared "reserved cells" registry that every leg of every call checks against *before* committing to a path (effectively a proper pathfinder), rather than each call computing its own path in isolation and hoping padding keeps it clear of everyone else's.
- **Consider whether per-signal spatial routing is the right level of abstraction at all.** Both this session and the XOR session spent the majority of their time on 3D collision-avoidance arithmetic, not on redstone logic. A library of larger, pre-verified, pluggable "cell" schematics (e.g., a complete verified AND-gate fragment with well-defined input/output ports at fixed relative offsets, placed and connected mechanically rather than hand-routed each time) might scale better than composing primitives from scratch for every new circuit. This is speculative — not attempted this session — but worth considering before sinking more time into ad hoc routing.
- Everything else from `docs/handoff-xor-plot-fix-2026-11-18.md` still applies (plot-size limit, dust decay, the open live-read reliability bug, center-anchoring via `we_offset`).

## Definition of done (unchanged, still not met)

1. Redstone core outputs correct 6-digit code for RFC test key + 10 RFC 4226 counters. **Not started.**
2. Measured time per code and block count reported. **Not started.**
3. README explaining launch/load/inject/read. **Not started.**
