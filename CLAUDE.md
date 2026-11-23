# TOTP in Minecraft redstone

Handoff for a Claude Code agent with Docker access. Read this fully before acting.

## Goal

Build a working **TOTP verifier/generator in pure redstone**, and demonstrate it running in a real server. The real goal is redstone. A datapack version is an optional stepping stone, not the target.

"Working" means: for a baked-in secret and an externally supplied time counter, the redstone circuit outputs the same 6-digit code as a standard authenticator app (HMAC-SHA1, 30 s period).

## Current state (2026-11-22: DONE, including the live demo -- see README.md's "TL;DR" and "Status"
sections for the full, current writeup, which supersedes everything below this line for status purposes.
Short version: pivoted to MineRTL (Verilog -> redstone synthesis, see
docs/handoff-minertl-pivot-2026-11-19.md) after the hand-routed-gate approach didn't scale past single
primitives (that approach's empirical MCHPRS findings remain valid background). The Verilog core is
bit-exact verified in simulation, synthesis (0 failed nets/0 verify errors), the real engine itself
(`mchprs_headless` + Redpiler, all 10 RFC 4226 vectors, 0 failures) -- build artifacts for this are committed
under `build/`, so a fresh clone can reproduce it without re-running synthesis, see README's "How to run
this yourself" -- and now the live, player-visible in-game demo too: a player can `/load -c` the build,
drive `rst`/`counter`/`start` via `/lever`, and watch the output lamps settle to the correct code in real
time. Getting the live path working took real engine-level debugging across two sessions (2026-11-19 and
2026-11-22) -- several real bugs found and fixed, the last and actual one being that `/load -c`'s block
placement never scheduled the tick a self-oscillating clock needs to start. See docs/next_steps.md for
remaining rough edges (none correctness-blocking) if picking this back up.)

Files in this repo (commit them as-is):

- `ref.py`: from-scratch SHA-1, HMAC-SHA1, HOTP/TOTP. Passes the RFC 4226 vectors (10) and RFC 6238 SHA-1 vectors (6), and matches `hashlib`/`hmac` on edge-length messages and keys.
- `datapath.py`: bit-exact register-transfer model of the proposed hardware. Passes the RFC vectors and 3,000 random keys/counters against `ref.py`. Run with `python3 datapath.py` (do not use `-I`; it breaks the local import).
- `netlist.py`: gate-level model (NOT/AND/OR/XOR primitives with redstone-tick delays) of the round engine, two 32-bit adder choices (ripple, carry-select block=8), and the full 2-compression + truncate/mod core built from them. Verified bit-exact against `ref.py` on the RFC 4226 vectors (10) + 40 random keys/counters for each adder. Run with `python3 netlist.py`.
- `schem.py`: Sponge Schematic v2 writer matching MCHPRS's loader. Verified-circuit fixtures: `build_smoke_schem.py`, `build_dust_test.py`, `build_not_gate_test.py`, `build_or_gate_test.py`, `build_and_gate_test.py` (each docstring has the full history of what didn't work and why, not just the final design). Diagnostic/differential tests kept as evidence, not scratch: `build_dust_chain_test.py`, `build_standing_torch_test.py` (wall-vs-standing-torch bug), `build_repeater_test.py` (repeater `facing` convention), `build_t_junction_test.py` (dust-merge limitation).
- `mchprs/`: cloned from [MCHPR/MCHPRS](https://github.com/MCHPR/MCHPRS) (not committed — nested git repo, see `.gitignore`), built locally as `mchprs:local`.
- `bot/`: Node/mineflayer driver (`totp-bot:local` image) — one probe script per schematic above, same naming (`dust_probe.js`, `not_gate_probe.js`, `or_gate_probe.js`, `and_gate_probe.js`, `dust_chain_probe.js`, `standing_torch_probe.js`, `repeater_probe.js`, `t_junction_probe.js`, plus `smoke_test.js` for the original connectivity check).

All four Python files were run and passed. See the stage 3 section below for what's verified against a real running server vs. still outstanding.

### Stage 2 results (measured from the gate-level model in `netlist.py`, not from a running build)

| adder | critical path / round (rt) | total rt/code (×201 cycles) | gate count / code |
|---|---|---|---|
| ripple-carry (32-bit) | 198 rt | 39,798 rt | ~133k (AND 48k, OR 24.6k, XOR 59k, NOT 1.3k) |
| carry-select (8-bit blocks) | 159 rt | 31,959 rt | ~281k (AND 114k, OR 57.8k, XOR 90.2k, NOT 18.8k) |

Carry-select is ~20% faster but costs ~2.1x the gates at block size 8 — a real tradeoff, not a slam-dunk win; worth trying other block sizes before committing. Carry-lookahead was **not** gate-modelled (effort tradeoff); its ~20 rt depth is a closed-form estimate only, unverified.

Gate delay convention used (textbook redstone-engineering numbers, **not yet measured against a real MCHPRS build** — treat as an assumption to revisit once something is actually placed): NOT=1 rt, OR=0 rt, AND=2 rt, XOR=2 rt. Registers reset delay to 0 at each clock edge; required clock period = worst-case combinational delay across all 80 rounds (same for both compressions since it's one synchronous core).

Converting to wall-clock using the confirmed MCHPRS fact that 2 game ticks = 1 redstone tick:

| adder | @ /rtps 10 | @ /rtps 20 | @ /rtps 100 | @ /rtps 1000 |
|---|---|---|---|---|
| ripple | 3980 s | 1990 s | 398 s | 39.8 s |
| carry-select-8 | 3196 s | 1598 s | 320 s | 32.0 s |

These are **estimates from the gate-delay model**, not measurements from a live build — real redstone wiring, repeater delay lines, and signal-strength repair will add overhead this model doesn't capture. Replace with real numbers once stage 3's layout exists in MCHPRS.

## Architecture decided so far

- **Algorithm:** HMAC-SHA1, 6 digits, 30 s step. SHA-1 chosen for compatibility with ordinary authenticator apps (Google Authenticator ignores non-SHA-1 settings). If compatibility is dropped, a lighter keyed PRF (SipHash-style ARX) would shrink the build a lot. Raise this with the user before choosing it.
- **Key baked in.** Precompute offline `S_in = compress(IV, key^ipad)` and `S_out = compress(IV, key^opad)`. The circuit then runs only **2 compressions** per code. The only variable input is the 32-bit counter.
- **Inner pass:** block = `[0, counter, 0x80000000, 0 x12, 0x240]`, start state `S_in`.
- **Outer pass:** block = `[H0..H4, 0x80000000, 0 x9, 0x2A0]`, start state `S_out`.
- **Round engine:** registers a..e (5x32) + 16x32 schedule shift register, one SHA-1 round per cycle, 80 cycles per compression, +5 cycles for the feed-forward add (reusing an adder).
- **Truncation:** 16:1 byte mux on `digest[19] & 0xF`, clear the top bit, then mod 10^6 by restoring shift-subtract (31 cycles).
- **Totals from the model:** 201 cycles per code, about 900 bits of state.
- **Clock/time:** redstone cannot know wall-clock time. The counter `floor(unix_time/30)` must be injected from outside (RCON, a plugin, or a script driving input), and the circuit computes from it. A tick-based in-world clock is not acceptable: game time scales with tick rate and drifts under lag.

## Open design axes (decide with data, not guesses)

1. **Adder design** sets the real clock. Ripple carry vs carry-lookahead vs carry-select. The round is `rol5(a)+f+e+K+w`; precomputing `e+K+w` one cycle early cuts the critical path to about 2 adds.
2. **Parallel vs bit-serial datapath.** Bit-serial uses far less space but needs about 32x the cycles (roughly 6,400). With `/tick`-style speedups this may still be fast and is much easier to lay out. Worth modelling both.
3. **Storage cell** for the 512-bit schedule register: pick whatever is smallest and reliable in the chosen simulator.
4. **Mod 10^6** alternatives to the restoring divider (the digit conversion is the least regular part).

## Recon findings (2026-11-08, confirmed via web search, not yet via a running build)

- **MCHPRS targets Minecraft 1.20.4.** Build with `cargo build --release`; binary lands at `./target/release/mchprs[.exe]`. Source: [MCHPR/MCHPRS](https://github.com/MCHPR/MCHPRS).
- **Tick rate control confirmed:** `/rtps [rtps|unlimited]` sets redstone ticks/sec per plot, default 10, fractional values supported. **2 game ticks = 1 redstone tick** in MCHPRS — fold this into cycle→seconds conversions. Source: [PR #205](https://github.com/MCHPR/MCHPRS/pull/205), [README](https://github.com/MCHPR/MCHPRS/blob/master/README.md).
- **Schematic loading confirmed:** MCHPRS ships a built-in WorldEdit clone. `//load` reads a schematic from `./schems/`, `//save` writes one, `//sel` / `/plot select` makes selections. Stage 3's generator should emit a standard `.schem` into that folder.
- **No published number for max throughput under `/rtps unlimited`** — bounded by real CPU/thread throughput, not a documented constant. Still needs an empirical measurement once something is built.
- Vanilla `/tick rate <1.0–10000.0>` and `/tick sprint` **are real**, added in 1.20.3, require permission level 3. Confirms the optional datapack-path claim; still secondary/optional per the plan.
- Docker 26.1.1 confirmed available locally.
- Timing estimate (7-20 min/code at 20 TPS ripple adder; 10-120 s fast-adder+sprint) is still a **guess**, not yet replaced by a measurement — do that once the netlist/gate-delay model (stage 2) and a build (stage 3) exist.
- A claimed redstone SHA-256 "Bitcoin miner" and a redstone language model exist online; sourcing for the first is weak. No prior redstone/datapack TOTP implementation was found (weak evidence; niche) — unchanged, not re-checked this pass.

## Plan

### Stage 2: gate-level design + simulation (no Minecraft needed) — DONE (see results above)
1. ✅ Defined NOT/OR/AND/XOR primitive set with per-gate tick delays (`netlist.py`). Latch/flip-flop/delay-line primitives not separately modelled — registers are abstracted as "delay resets to 0 at the clock edge," deferred to stage 3 layout.
2. ✅ Round engine + 5-operand add tree + truncation/mod built as a gate netlist in `netlist.py`.
3. ✅ Verified against `ref.py`/`datapath.py` (RFC vectors + 40 random vectors, both adder choices, bit-exact). Gate count and critical path reported above. Schedule register and control FSM were not modelled as separate gate-level state (the netlist drives the whole 80-round loop combinationally per cycle in software) — fine for correctness/critical-path purposes, but stage 3's actual layout still needs a real FSM/shift-register design.
4. Architecture pick: **carry-select (block=8) is the better default** — 20% faster for 2.1x the gates, and gates are cheap relative to redstone's real cost driver (footprint/wiring), not yet modelled. Revisit if stage 3 footprint estimates say otherwise. Carry-lookahead still unmodelled; worth a quick follow-up if carry-select's footprint turns out to be the bottleneck.

### Stage 3: layout + run in a simulator — toolchain proven, full core NOT built

**What's done and verified (2026-11-08), all against a real running MCHPRS container, not simulated:**

1. ✅ MCHPRS built from source in Docker (`mchprs/Dockerfile`, the project's own — `docker build -t mchprs:local mchprs/`). Rust release build took ~9 min. Image is 14.9MB (scratch-based). Container run with `-v ./mchprs_data:/data -p 127.0.0.1:25565:25565`, confirmed listening and accepting connections.
2. ✅ `schem.py`: a from-scratch Sponge Schematic v2 writer matching MCHPRS's loader (`mchprs/crates/schematic/src/lib.rs`) byte-for-byte (palette compound, varint block data in y/z/x order, `WEOffset*` metadata, `DataVersion=3700`). Round-trips correctly through `nbtlib` and loads via `//load <name>.schem` in a live server.
3. ✅ A Node/mineflayer bot (`bot/`, Dockerfile + `package.json`) drives the server headlessly — MCHPRS has no RCON/console-command path, everything is a real in-game player action (`//load`, `//paste`, lever clicks), so a protocol-level bot is required, not optional.
4. ✅ **End-to-end circuit test, fully verified**: `build_dust_test.py` generates a lever → redstone dust → lamp circuit; `bot/dust_probe.js` loads it, flips the lever, and reads back real block state via `bot.blockAt(...).getProperties()`. Measured: lever off → dust `power=0`, lamp `lit=false`; lever on → dust `power=15`, lamp `lit=true`. This confirms the full loop (generate schematic → load into a live server → drive an input → read a real output) works correctly.
5. ✅ **NOT gate, fully verified** (`build_not_gate_test.py` + `bot/not_gate_probe.js`): standing-torch inverter → dust → lamp. Measured truth table: lever OFF → torch lit, dust `power=15`, lamp `lit=true`; lever ON → torch unlit, dust `power=0`, lamp `lit=false`. Correct inversion, both directions.
6. ✅ **OR gate, fully verified** (`build_or_gate_test.py` + `bot/or_gate_probe.js`): two levers, each through its own repeater, both repeater outputs aimed directly at the same lamp from different sides — no shared dust junction. Measured truth table, all 4 combinations correct: (off,off)→unlit, (on,off)→lit, (on,on)→lit, (off,on)→lit. **This design is a direct workaround for a real MCHPRS limitation** — see below; a shared dust junction with two independently-sourced inputs does not light a downstream lamp in this build, no matter what feeds it.
7. ✅ **AND gate, fully verified** (`build_and_gate_test.py` + `bot/and_gate_probe.js`): built compositionally via De Morgan, `AND(A,B) = NOT(NOT(A) OR NOT(B))`, from the two primitives above — two standing-torch NOTs, each through its own repeater onto a shared support block (the OR, via direct convergence, no shared dust), one more standing-torch NOT on top of that, then a final repeater into the lamp. Measured truth table correct for all 3 non-trivial combinations: (on,off)→unlit, (off,on)→unlit, (on,on)→**lit**. This is the first multi-stage composed circuit built in this project and it worked once the known-good primitives were composed correctly — see the repeater-geometry gotcha below, which is what actually broke the first attempt at the final stage, not a new engine limitation.

**Real gotchas hit and fixed along the way (useful for anyone continuing this):**
- mineflayer's `'spawn'` event never fires against MCHPRS — it waits on an `update_health` packet MCHPRS doesn't send. Use `'login'` instead (see `bot/smoke_test.js`, `bot/dust_probe.js`).
- MCHPRS plots have **no floor by default** — a bot standing there free-falls under local gravity prediction indefinitely. Don't use `/tp` + assume it landed; use `bot.creative.flyTo(pos)` (disables local gravity, holds an exact position) before doing anything position-dependent (paste anchor, block reads).
- `//load`'s filename argument is validated against `[a-zA-Z0-9_.]+\.schem(atic)?` (substring match) — you must include the `.schem` extension in the chat command, e.g. `//load dust_test.schem`, not `//load dust_test`.
- **A pasted schematic's redstone components keep the exact blockstate you specified — MCHPRS does not recompute `lit`/`powered` from neighboring context on paste.** A torch placed without an explicit `lit=true` stays permanently unlit regardless of input until a genuine live transition occurs nearby (see next point) — `//update -p` (WorldEdit's documented recompute command) does **not** fix this either, measured directly.
- **A component's displayed power/lit state only becomes fully consistent after one real, live transition touches it — not immediately on paste, and not via `//update`.** Always drive the input through its states once before trusting a read in a freshly-pasted circuit (`not_gate_probe.js` does this: two throwaway toggles before reading the truth table).
- **Levers do NOT directly power arbitrary adjacent mechanism blocks** (lamps) — only redstone dust touching the block reliably carries power to it. An early NOT-gate attempt's one "working" lamp turned out to be lit because it was incidentally adjacent to the *lever's own cell*, not any real gate logic.
- **Wall-mounted torches (`redstone_wall_torch`) do not correctly cascade a power change past their immediate dust neighbor in this MCHPRS build — standing torches (`redstone_torch`) do.** This was the actual NOT-gate bug: a wall torch → dust → lamp chain let the dust correctly track the torch's state (power 0/15) but never lit the lamp, reproducibly, across floor-support fixes and `//update`. A differential test (lever → dust → dust → lamp, `build_dust_chain_test.py`) proved multi-hop dust propagation works fine in general; another (`build_standing_torch_test.py`) proved a standing torch in the identical position works immediately. **Use standing torches, not wall torches, for any inverter in this build.**
- **A `repeater`'s `facing` blockstate property names the direction power ENTERS from, not the direction it outputs to, in this stack** (opposite of the usual vanilla mental model) — `build_repeater_test.py` found a lever→dust→repeater→lamp chain only worked with the repeater's `facing` matching the *input* side. Verify empirically, don't assume, when placing any repeater via a schematic palette string.
- **A shared dust junction with two independently-sourced neighbors does not propagate power to a third (consumer) neighbor in this MCHPRS build — this is a real finding, not a geometry mistake.** Exhaustively isolated across 5 attempts (`build_or_gate_test.py`'s docstring has the full history): a T-junction with exactly ONE active source + one inert neighbor (stone, or even a dead lever) works fine; the moment a SECOND independently-drivable neighbor (a second lever, a second dust stub, or a second repeater) is added to the same junction, the junction's own power level still correctly reflects OR logic (reads 14 or 15 as expected) but the downstream lamp never lights, reproducibly, regardless of what type the two source-neighbors are. **The working fix: never let two independent sources merge through a shared dust cell. Route each source through its own repeater, and aim both repeaters' outputs directly at the same consumer (lamp, or in a composed gate, the next stage's input block) from different sides.**
- **A repeater is strictly straight-through: its input and output are on opposite faces only, never a 90° turn — this one IS a geometry mistake, not an engine quirk, but cost real debugging time because the symptom (dust/repeater correctly shows power, but the thing after it never lights) looks identical to the real engine bugs above.** The AND gate's first attempt put a torch's output repeater with its input to the north and the lamp to the east; it read `powered=true` correctly (since it genuinely was receiving input) but never lit the lamp, because a repeater simply has no path to send power out a side face. Fixed by keeping every repeater's input and output in a straight line. **When a dust/repeater correctly shows nonzero power but a downstream consumer still won't light, check straight-line geometry before assuming it's another engine limitation.**

**XOR (2026-11-18 session): logic designed and built (`build_xor_compact_v2.py`, De Morgan: `XOR = OR(Term1, Term2)`), offline-verified (zero collisions, zero signal-adjacency problems via an automated checker), a direct live block scan confirmed the real dust/repeater/torch network is wired exactly as designed — but a complete, clean live truth-table confirmation was NOT achieved.** Hit and fixed three real bugs along the way (probe never flying near distant read points; dust decaying to 0 after 15 blocks with no refresh repeater; MCHPRS's 512-block plot boundary silently dropping out-of-plot paste writes — see `docs/handoff-xor-fix-2026-11-09.md` and `docs/handoff-xor-plot-fix-2026-11-18.md`), then ran into a genuinely non-deterministic live-read bug that resisted nine-plus isolation tests and a full investigation (chunk/plot/timing/reconnect/redpiler/dust-density/paste-size/anchor-distance all ruled out or shown not to reliably help; empirical success rate ~1-in-6 across repeated identical runs). **Per the working rules, this is reported as an open gap rather than claimed as verified** — XOR's logic is very likely correct, but has not cleared the project's own "verify against a real server, don't claim from reasoning alone" bar.

**What's NOT done — reported honestly rather than faked:**
- XOR is built and almost certainly correct but not cleanly live-verified (see above). A 1-bit full adder is ~1/4 built (`build_full_adder_test.py`: both AND terms of the first half-adder, offline-verified; the OR that combines them into P, C1, the second half-adder, and the final Carry OR are not built -- see `docs/handoff-full-adder-2026-11-18.md` for why: a general-purpose spatial router was needed and kept finding new, narrower collisions as each one was fixed, suggesting the routing approach itself needs reconsidering before sinking more time into patching it). A register has not been built as a real placed structure yet. NOT, OR, and AND remain the only gates with a clean, repeatable, fully-confirmed live truth table so far.
- **The full core (895 state bits, ~130k–280k gates per `netlist.py`) is not laid out.** This is a real placement-and-routing problem at a scale that was not attempted this session — it is a multi-session effort, not a remaining checklist item. Per the working rules, this is reported directly rather than assumed solvable from the gate-level model alone.

**Recommended path if continuing:** either (a) spend a short, bounded amount of time trying to get one clean live XOR truth-table pass (the circuit is almost certainly already correct; it may just take a few retries given the ~1-in-6 observed success rate), or (b) accept offline verification (collision/adjacency checks, which `build_xor_compact_v2.py` already does automatically) as sufficient for now and move on to the 1-bit full adder, budgeting for live verification being unreliable rather than planning around it working first try. Either way, build one verified cell at a time using the now-working bot+schematic+read-back loop, before attempting anything at word width — each cell becomes a reusable schematic fragment. Given the findings above: use standing torches for inversion; verify repeater `facing` empirically rather than assuming vanilla convention, and keep every repeater's input/output in a straight line (no 90° turns); never merge two independent sources through a shared dust cell — always repeater-isolate each source into the same consumer instead; when composing multi-stage circuits, drive every input through a couple of full real transitions before trusting any read, not just once; prefer `redstone_parts.py`'s `travel()` helper over hand-rolled dust runs (it refreshes every hop, avoiding the signal-decay bug); keep every build's bounding box inside one 512-block MCHPRS plot; and anchor builds on their own center (`Schematic.save(..., we_offset=...)`) rather than a corner, which can only help the live-read reliability issue even though it isn't a confirmed fix.

### Optional: vanilla datapack path
Only if the user asks. Needs a vanilla 1.21.x server (not MCHPRS), RCON enabled, and the scoreboard-based SHA-1 emulation. Useful as a second implementation to cross-check intermediate state words.

## Docker notes

- Vanilla server: the `itzg/minecraft-server` image works (`EULA=TRUE`, enable RCON via `ENABLE_RCON=true` and set an RCON password; mount a volume for the world). Drive it with `rcon-cli` inside the container.
- MCHPRS: no assumption of an official image. Build from source in a container; keep world/plot data on a mounted volume so schematics can be dropped in.
- Keep RCON ports bound to localhost only.

## Working rules

- Verify every stage against `ref.py` with the RFC vectors before moving on. Do not claim a stage works from reasoning alone.
- Keep measured numbers and estimates clearly separate in anything you report.
- Do not hard-code a real secret anywhere; use the RFC test key `12345678901234567890` for all testing.
- If the layout step looks like it will not close in reasonable effort, report that and propose reducing scope (bit-serial datapath, lighter PRF) rather than faking a result.
- Ask the user before choosing a non-SHA-1 primitive, since that breaks authenticator-app compatibility.

## Definition of done

1. Redstone core in a running server outputs the correct 6-digit code for the RFC test key and at least the 10 RFC 4226 counters.
2. Measured time per code and block count are reported.
3. A short README explains how to launch the container, load the build, inject a counter and read the result.

**All three met (2026-11-22/23).** (1): all 10 RFC 4226 vectors confirmed on the real engine via
`mchprs_headless`, AND all 10 confirmed again live, in an actual running server, read directly off the
output lamps for every counter 0-9 (`done=true`, exact match every time -- see README's Status section
item 6 for the full table). (2): timing tables throughout README.md's Status section. (3): README's "How
to run this yourself" section.
