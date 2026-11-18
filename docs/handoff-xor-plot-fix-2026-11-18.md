# Handoff — XOR gate: plot/signal-decay bugs fixed, read-reliability bug found (2026-11-18)

## Context

Continuing stage 3 from `docs/handoff-xor-fix-2026-11-09.md`. That session built `build_xor_v23.py` (a ~400-block-wide XOR) and could not verify it live because the probe never flew near S1/S2/LAMP, so every read came back NULL (no chunk data).

This session asked "why does XOR need to be so spread out / chained" and, on the user's direction, built a **compact** version instead: same De Morgan topology (`XOR = OR(Term1, Term2)`, `Term1 = NOT(NOT_A OR raw_B)`, `Term2 = NOT(raw_A OR NOT_B)`), but in a ~33×5×21 bounding box instead of ~400 blocks.

## Files added this session

- `build_xor_compact_v2.py` — the compact XOR build. Has an automated collision checker (`place()`/`owner` dict, raises on same-cell conflicts between different signals) and an automated adjacency checker (`check_adjacency()`, flags any two different-labeled wire cells that end up face-adjacent outside a declared `converge_points` entry). Both checks run clean on the current version — **the schematic itself is proven collision- and adjacency-free**, verified offline before ever touching the server.
- `bot/xor_compact_v2_probe.js` — the truth-table probe (currently still blocked, see below).
- `bot/xor_v2_scan_probe.js`, `bot/xor_v2_neighborhood_probe.js`, `bot/xor_v2_marker_probe.js` — diagnostic probes built this session to isolate the bugs below. Kept as evidence, not scratch, per the project's working rules.

## Three real bugs found and fixed, in order

1. **Dust signal decay.** Redstone dust decays to 0 power after 15 blocks with no repeater. Every lane in the first compact attempt (`raw_A`, `NOT_A`, `raw_B`, `NOT_B`) was 20-30 blocks long with a single repeater only at the very end, right before the merge point. Nothing ever reached S1/S2 as a result — confirmed live: `TORCH_A`/`TORCH_B` (direct lever→torch, no long dust run) inverted correctly on every toggle, but `TERM1_TORCH`/`TERM2_TORCH`/`LAMP` never moved at all, in any lever state.

   **Fix**: rewrote the shared `line()` helper in `build_xor_compact_v2.py` to drop a refresh repeater in automatically every 8 cells of any straight run. Verified: schematic rebuilds clean (no collisions/adjacency problems).

2. **MCHPRS plot-boundary clipping.** Confirmed by reading MCHPRS's own source (`mchprs/crates/core/src/plot/mod.rs`): plots are `PLOT_BLOCK_WIDTH = 512` blocks (`PLOT_SCALE=5` chunks-wide, `*16`). `set_block_raw()` returns `false` silently — **no error, no message** — whenever the target position's chunk falls outside the plot the command's selection/anchor is bound to. Proved this empirically: pasting the structure anchored at `(500,70,500)` (which spans across `x=512`, a real plot boundary) showed every block past `x=512` as air, landing exactly on the tick where the server's own `"Entering plot (1,0)"` message fired.

   **Fix**: moved the paste anchor to `(600,70,600)` — comfortably inside one plot (`[512,1024)` in both x and z) with the whole ~33×21 footprint never touching a boundary.

3. **Fixed-sleep race condition on chat commands.** The probe sent `//load` then `//paste` with fixed `sleep()` delays and assumed completion. Instrumented logging showed the server's own confirmation messages (`"The schematic was loaded..."`, `"Your clipboard was pasted."`) sometimes arrived **15+ seconds after** the fixed sleep had already elapsed and the probe had started reading — meaning several earlier "the structure is entirely air" results were just reading the world before the paste had executed at all, not a real absence of blocks.

   **Fix**: added `chatAndWait(cmd, matchSubstr)` to `bot/xor_compact_v2_probe.js`, which blocks on the actual confirmation message text instead of a guessed delay.

## Unresolved: read-reliability bug, confirmed NOT a circuit/schematic problem

With all three bugs above fixed, a **direct 3D volume scan** of the live world (`bot/xor_v2_neighborhood_probe.js`, scanning a generous box around S1/S2/LAMP after a *confirmed* paste) found **every dust cell, every repeater, and Term1's torch present and correctly wired exactly where the schematic says they should be** — 48 real, correctly-typed blocks, including `TERM1_TORCH` lit and sitting exactly on top of S1's expected position.

But reads of the three specific **consumer blocks** (S1 = stone, S2 = stone, LAMP = redstone_lamp) consistently come back as `air` through `bot.blockAt`, even flying directly adjacent with long settle waits. Physically this doesn't add up — a standing torch (`TERM1_TORCH`) cannot exist without its support block (`S1`) also existing, so S1 must be real; `bot.blockAt` is misreporting it.

**Ruled out** as the cause (tested directly):
- Chunk-loading distance (fixed earlier in the session; confirmed not the issue here since we fly directly adjacent every time).
- Plot-boundary clipping (fixed; this region is nowhere near a plot edge).
- Command-completion races (fixed; using `chatAndWait` now).
- Block-type-specific bug (plain `minecraft:stone` reads fine in `build_and_gate_test.py`'s earlier, successful session; and a repeat run found `TERM1_TORCH` *also* reading as air, so it's not specific to stone/lamp).
- A `//set minecraft:diamond_block` marker test to swap S1 for an unambiguous block type didn't land conclusively — the `//set` command itself errored (`"unknown block: minecraft:diamond_block"`, likely needs the bare name `diamond_block` with no namespace prefix, untried) — but in the same run, `TERM1_TORCH` (known-present from the prior scan) *also* read as air, which independently rules out "it's about block type" regardless of whether the marker test lands.

**Current best theory**: a mineflayer client-side chunk-cache staleness issue specific to large bulk edits (3000+ block paste in one command) — i.e., the bot's local world model doesn't always get a fresh, complete update for a chunk that changed via a big worldedit-style edit, and which specific positions read stale vs. fresh varies run-to-run with no pattern found yet (not block-type, not distance, not timing-after-paste that we've tried).

**Not yet tried**: forcing a full fresh chunk load by disconnecting and reconnecting the bot (a fresh login should force the server to resend complete chunk data, bypassing whatever client-side cache is stale) instead of just flying around with the same connection. This is the next thing to try.

## Recommended next steps

1. Try the disconnect/reconnect-before-reading fix described above. If it works, the XOR truth table can finally be confirmed live, closing out the actual circuit-correctness question (which the volume scan already answered "probably yes" for, just not through a clean automated readback yet).
2. If reconnect doesn't fix it, try reading via repeated polling (e.g. 5 reads over 5 seconds, majority vote) as a workaround rather than a real fix, and flag the flakiness as a known tooling limitation going forward.
3. Once XOR is confirmed, per `CLAUDE.md`'s suggested path: build a 1-bit full adder truth table next (same compact-with-repeaters, collision/adjacency-checked methodology), then scale to word width. Each verified gate becomes a reusable schematic fragment.

## Definition of done (still not met)

1. Redstone core outputs correct 6-digit code for RFC test key + 10 RFC 4226 counters. **Not started** — still at individual-gate verification stage.
2. Measured time per code and block count reported. **Not started.**
3. README explaining launch/load/inject/read. **Not started.**
