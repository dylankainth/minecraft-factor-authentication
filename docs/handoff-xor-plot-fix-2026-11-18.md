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

## Update (later the same night): reconnect ruled out, redpiler ruled out, a real lead found

Continued investigating after the first draft of this doc. In order:

- **Disconnect/reconnect made it worse, not better** (`bot/xor_v2_reconnect_probe.js`): a totally fresh second connection, reading moments after a confirmed paste by a first connection, read *everything* as air -- including `LEVER_A`, which every single-connection test before and after this one read correctly. Chunk-cache staleness in a persistent connection is not the cause; something about the plot/paste itself not having "settled" shortly after the writing connection disconnects is a bigger effect, if anything.
- **Polling the same persistent connection 10x over 10 seconds** (`bot/xor_v2_retry_probe.js`): S1/S2/LAMP read as air on every single attempt, perfectly stably. This is not transient flakiness that resolves with more time -- within one run, it's a deterministic result.
- **`auto_redpiler` ruled out**: `/toggleautorp` reported it as *disabled by default* (toggling it printed "...has been enabled", meaning it had been off the whole session already) and turning it on didn't change the S1/S2/LAMP result either way. MCHPRS's JIT redstone compiler is not involved.
- **A minimal isolated case (`build_stone_isolation_test.py`: one lever, three plain stone blocks, one lamp, one torch, ~6 blocks total) pastes and reads back perfectly, every single field correct.** This rules out "plain stone/redstone_lamp is unreadable" as a block-type-level bug.
- **A padded isolation case reproducing the exact proven OR-gate convergence geometry (two independent repeaters landing on one stone block) plus ~6300 blocks of inert filler (`build_convergence_scale_test.py`) also reads back perfectly, 5/5 attempts.** This rules out raw paste size/block-count alone, and rules out the convergence-of-two-repeaters pattern itself (it's the same pattern AND/OR gates already proved works).
- **A new isolated case reproducing the real XOR's actual lane style -- long dust runs (20 cells) with periodic refresh repeaters every 8 cells, feeding into a two-repeater convergence (`build_convergence_longchain_test.py`, only ~101 blocks total) failed completely** -- not just the convergence point, but `LEVER_A` itself, the simplest possible block in the file, also read as air. Retried at a different, previously-known-good anchor with the same result.
- **The most informative result: scanning a single padding lane from `build_convergence_scale_test.py`'s *working* schematic at many distances from the paste anchor** (`bot/distance_check_probe.js`) found a real pattern: **every repeater position (every 8th cell) read back correctly; most plain-dust positions in between read as air**, at distances from 3 up to 199 blocks from the anchor. One repeater position (at distance 160) also read as air, breaking a clean "dust fails, repeater succeeds" rule, so this isn't fully nailed down either -- but it's the strongest lead so far: **plain `redstone_wire` cells, specifically, are the ones that most often come back wrong**, not torches, not repeaters, not levers, not (as the isolation test proved) stone/lamp blocks in general.

**One more test, which disproved the leading theory**: rebuilt the real XOR with `line()`'s `refresh` set to 1 (a repeater at every single cell, same density as the already-existing `travel()` helper, zero plain-dust runs longer than one block) and reran the 10x polling test. **S1/S2/LAMP still read as air on all 10 attempts, identically to the `refresh=8` version.** So "too much plain dust" is not the actual trigger either -- it's specifically something about these three particular blocks (the final convergence points, each fed by two repeaters whose own inputs trace back through a long chain from the original lever), not dust density along the way. Reverted back to `refresh=8` (no worse, and fewer blocks/ticks) since the denser version bought nothing.

**Net conclusion for this session**: this is a real, reproducible MCHPRS and/or mineflayer limitation specific to blocks that are both (a) far from the paste anchor along a long routing chain and (b) the convergence target of two independent repeater inputs -- not a bug in any of this project's schematics, build scripts, or circuit logic, and not simply "too much dust" or "too large a paste" (both were independently ruled out with isolation tests that worked fine at much larger scale). The dust/repeater/torch network in the real XOR build has been directly, visually confirmed correct via block scan. The circuit is very likely correct; the read tooling cannot currently confirm it cleanly for a build this size and shape.

`redstone_parts.py` has been updated with all of the above as permanent documentation, including a strong recommendation to prefer the existing `travel()` helper (one repeater per hop, not every-8-blocks) for new work, and a warning to corroborate any single "live read says it's broken" result with a direct scan before trusting it enough to redesign a circuit.

## Two more tests, both negative

- **AND gate regression check**: reran the already-proven `and_gate_probe.js` against the live server tonight, unrelated to the XOR work, just to confirm the server/tooling baseline is still sound. **Full pass** -- `SF` (its own 2-repeater convergence stone block, 3 blocks from its paste anchor) read correctly as `stone` on every single check across the whole truth table, and `LAMP_F` correctly lit after a real transition. This reinforces that the bug is specific to large/far builds, not a general regression in the server or tooling.
- **Pre-visit-before-paste**: tried flying to S1/S2/LAMP's positions *before* issuing `//load`/`//paste` (theory: chunk sections far from wherever the player stands at paste time might not be server-side "active" yet, so the write itself could silently drop, and no amount of flying there afterward to read would fix a write that never landed). **Did not help** -- identical air-on-every-attempt result.

So the strongest honest statement this session can make: **AND/OR/NOT gates, close to their paste anchor, are rock solid. The XOR's own convergence points, far down a long routing chain, consistently fail to read back despite the underlying wiring being visibly correct in a direct scan.** Every mechanism tried to explain or fix this (distance-at-read-time, distance-at-paste-time, dust density, paste size, reconnect, redpiler) has been ruled out. The actual mechanism remains unknown.

## A promising fix that turned out to be a coincidence -- important correction

Found that `schem.py`'s `WEOffsetX/Y/Z` (always 0 before tonight) controls which *local* point in the clipboard lands on the player's position at paste time (confirmed by reading `mchprs/crates/schematic/src/lib.rs`'s `execute_paste`/`load_schematic_sponge`: `cb.offset_x = -WEOffsetX`, and the paste computes `world_offset = player_pos + WEOffset`). Since the corner-anchored XOR put S1/S2/LAMP 18-30 blocks from the paste position, setting `WEOffsetX/Y/Z` to the structure's own center (local `(16,2,10)`) roughly halves that worst-case distance for every block.

**First test of this fix: a clean pass.** `xor_v2_retry_probe.js`, rerun with the center handle, read S1/S2/LAMP correctly as `stone`/`stone`/`redstone_lamp` on all 10 attempts over 10 seconds. The full truth-table probe (`xor_compact_v2_probe.js`), updated the same way, was run next and failed again (S1/S2 air throughout, even in the very first pre-toggle read). **Re-running the exact same `xor_v2_retry_probe.js` script a second time -- same schematic, same anchor, same code, zero changes -- failed completely on every attempt**, where the first run had succeeded on every attempt.

**This is the real finding, and it supersedes the "fix" above**: the behavior is genuinely non-deterministic run-to-run, with identical inputs, not reliably explained by anchor distance, dust density, paste size, toggling, or any other variable tested tonight. The center-handle change is still worth keeping (it can only help, and costs nothing), but it is not a fix -- don't rely on it, and don't be fooled by a single successful run the way this session briefly was.

**Empirical success rate sample**: ran the identical `xor_v2_retry_probe.js` script six times total tonight (same schematic, same server, no code changes between runs). 1 succeeded (10/10 reads correct), 5 failed (10/10 reads wrong). That's roughly 1-in-6 -- "just retry until it works" is not a practical workaround at that rate; a future session would need either a real fix or a much cheaper way to detect success/failure than a full paste-and-poll cycle before retrying is worthwhile.

## Recommended next steps

1. **Stop chasing this specific bug.** Nine-plus isolation tests tonight (chunk distance, plot clipping, command races, reconnect, dust density, paste size, redpiler, pre-visit-before-paste, and the center-handle offset) have all either been ruled out or, in the center-handle case, shown to be a one-run coincidence rather than a real fix. The behavior is genuinely non-deterministic across identical runs. Further live-read debugging from here has a poor effort/information ratio.
2. **Treat the offline collision/adjacency checks as the primary correctness signal for new builds.** A schematic that passes `build_xor_compact_v2.py`'s own `check_adjacency()` and has zero `Schematic.set()` collisions is strong evidence of correctness independent of whatever's wrong with live reads. Corroborate with a direct, multi-point block scan (not a single `blockAt` call) when a live check is wanted, and expect it to sometimes need a second attempt.
3. Keep the center-handle `WEOffset` change in `schem.py`/`build_xor_compact_v2.py` going forward -- it's free and can only help, even though it didn't prove to be a reliable fix on its own.
4. Per `CLAUDE.md`'s suggested path: build a 1-bit full adder next, using `travel()` (not hand-rolled dust runs) for all routing. Budget for live verification being unreliable rather than planning around it working first try.

## Definition of done (still not met)

1. Redstone core outputs correct 6-digit code for RFC test key + 10 RFC 4226 counters. **Not started** — still at individual-gate verification stage.
2. Measured time per code and block count reported. **Not started.**
3. README explaining launch/load/inject/read. **Not started.**
