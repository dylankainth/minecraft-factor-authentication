# TOTP in Minecraft redstone

Handoff for a Claude Code agent with Docker access. Read this fully before acting.

## Goal

Build a working **TOTP verifier/generator in pure redstone**, and demonstrate it running in a real server. The real goal is redstone. A datapack version is an optional stepping stone, not the target.

"Working" means: for a baked-in secret and an externally supplied time counter, the redstone circuit outputs the same 6-digit code as a standard authenticator app (HMAC-SHA1, 30 s period).

## Current state (stage 1 done; MCHPRS/tick-rate recon done; stage 2 gate-level model done and verified)

Files in this repo (commit them as-is):

- `ref.py`: from-scratch SHA-1, HMAC-SHA1, HOTP/TOTP. Passes the RFC 4226 vectors (10) and RFC 6238 SHA-1 vectors (6), and matches `hashlib`/`hmac` on edge-length messages and keys.
- `datapath.py`: bit-exact register-transfer model of the proposed hardware. Passes the RFC vectors and 3,000 random keys/counters against `ref.py`. Run with `python3 datapath.py` (do not use `-I`; it breaks the local import).
- `netlist.py`: gate-level model (NOT/AND/OR/XOR primitives with redstone-tick delays) of the round engine, two 32-bit adder choices (ripple, carry-select block=8), and the full 2-compression + truncate/mod core built from them. Verified bit-exact against `ref.py` on the RFC 4226 vectors (10) + 40 random keys/counters for each adder. Run with `python3 netlist.py`.

All three were run and passed. Nothing below stage 2 has been built or tested.

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

### Stage 3: layout + run in a simulator
1. Write a generator that turns the netlist into a block layout (bit-sliced regular structures: adders, shift registers, XOR arrays). Emit a schematic.
2. Build MCHPRS in Docker (Rust image; `cargo build --release`) and load the schematic.
3. Drive the counter input, clock the core, read the 6-digit output. Compare to `ref.py` for the RFC vectors first, then random counters.
4. Measure actual time per code at the simulator's tick rate.

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
