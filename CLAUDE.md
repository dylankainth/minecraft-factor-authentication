# TOTP in Minecraft redstone

Handoff for a Claude Code agent with Docker access. Read this fully before acting.

## Goal

Build a working **TOTP verifier/generator in pure redstone**, and demonstrate it running in a real server. The real goal is redstone. A datapack version is an optional stepping stone, not the target.

"Working" means: for a baked-in secret and an externally supplied time counter, the redstone circuit outputs the same 6-digit code as a standard authenticator app (HMAC-SHA1, 30 s period).

## Current state (stage 1 + 2 done and verified; stage 3 toolchain proven end-to-end, dust+NOT gate circuits verified; full-core layout not yet attempted)

Files in this repo (commit them as-is):

- `ref.py`: from-scratch SHA-1, HMAC-SHA1, HOTP/TOTP. Passes the RFC 4226 vectors (10) and RFC 6238 SHA-1 vectors (6), and matches `hashlib`/`hmac` on edge-length messages and keys.
- `datapath.py`: bit-exact register-transfer model of the proposed hardware. Passes the RFC vectors and 3,000 random keys/counters against `ref.py`. Run with `python3 datapath.py` (do not use `-I`; it breaks the local import).
- `netlist.py`: gate-level model (NOT/AND/OR/XOR primitives with redstone-tick delays) of the round engine, two 32-bit adder choices (ripple, carry-select block=8), and the full 2-compression + truncate/mod core built from them. Verified bit-exact against `ref.py` on the RFC 4226 vectors (10) + 40 random keys/counters for each adder. Run with `python3 netlist.py`.
- `schem.py`: Sponge Schematic v2 writer matching MCHPRS's loader. `build_smoke_schem.py`, `build_dust_test.py`, `build_not_gate_test.py`: schematic fixtures for the verified circuits. `build_dust_chain_test.py`, `build_standing_torch_test.py`: differential tests that diagnosed the wall-torch propagation bug (see stage 3 notes) — kept because they're the evidence, not just scratch work.
- `mchprs/`: cloned from [MCHPR/MCHPRS](https://github.com/MCHPR/MCHPRS) (not committed — nested git repo, see `.gitignore`), built locally as `mchprs:local`.
- `bot/`: Node/mineflayer driver (`totp-bot:local` image) — `smoke_test.js`, `dust_probe.js`, `not_gate_probe.js` (both verified working circuits), `dust_chain_probe.js`, `standing_torch_probe.js` (the diagnostic pair).

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

**Real gotchas hit and fixed along the way (useful for anyone continuing this):**
- mineflayer's `'spawn'` event never fires against MCHPRS — it waits on an `update_health` packet MCHPRS doesn't send. Use `'login'` instead (see `bot/smoke_test.js`, `bot/dust_probe.js`).
- MCHPRS plots have **no floor by default** — a bot standing there free-falls under local gravity prediction indefinitely. Don't use `/tp` + assume it landed; use `bot.creative.flyTo(pos)` (disables local gravity, holds an exact position) before doing anything position-dependent (paste anchor, block reads).
- `//load`'s filename argument is validated against `[a-zA-Z0-9_.]+\.schem(atic)?` (substring match) — you must include the `.schem` extension in the chat command, e.g. `//load dust_test.schem`, not `//load dust_test`.
- **A pasted schematic's redstone components keep the exact blockstate you specified — MCHPRS does not recompute `lit`/`powered` from neighboring context on paste.** A torch placed without an explicit `lit=true` stays permanently unlit regardless of input until a genuine live transition occurs nearby (see next point) — `//update -p` (WorldEdit's documented recompute command) does **not** fix this either, measured directly.
- **A component's displayed power/lit state only becomes fully consistent after one real, live transition touches it — not immediately on paste, and not via `//update`.** Always drive the input through its states once before trusting a read in a freshly-pasted circuit (`not_gate_probe.js` does this: two throwaway toggles before reading the truth table).
- **Levers do NOT directly power arbitrary adjacent mechanism blocks** (lamps) — only redstone dust touching the block reliably carries power to it. An early NOT-gate attempt's one "working" lamp turned out to be lit because it was incidentally adjacent to the *lever's own cell*, not any real gate logic.
- **Wall-mounted torches (`redstone_wall_torch`) do not correctly cascade a power change past their immediate dust neighbor in this MCHPRS build — standing torches (`redstone_torch`) do.** This was the actual NOT-gate bug: a wall torch → dust → lamp chain let the dust correctly track the torch's state (power 0/15) but never lit the lamp, reproducibly, across floor-support fixes and `//update`. A differential test (lever → dust → dust → lamp, `build_dust_chain_test.py`) proved multi-hop dust propagation works fine in general; another (`build_standing_torch_test.py`) proved a standing torch in the identical position works immediately. **Use standing torches, not wall torches, for any inverter in this build.**

**What's NOT done — reported honestly rather than faked:**
- AND/OR/XOR gates, an adder, and a register have not been built as real placed structures yet — NOT is the only gate verified so far.
- **The full core (895 state bits, ~130k–280k gates per `netlist.py`) is not laid out.** This is a real placement-and-routing problem at a scale that was not attempted this session — it is a multi-session effort, not a remaining checklist item. Per the working rules, this is reported directly rather than assumed solvable from the gate-level model alone.

**Recommended path if continuing:** build one verified cell at a time, empirically (AND/OR/XOR next, then a 1-bit full adder truth table) using the now-working bot+schematic+read-back loop above, before attempting anything at word width. Each cell becomes a reusable schematic fragment once its truth table is confirmed. Only after a handful of verified primitive cells exist does a bit-sliced word-width generator become worth writing. Given the wall-torch finding, assume any new gate design needs the same "drive it through a real transition before trusting a read" treatment and prefer standing torches wherever an inverter is needed.

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
