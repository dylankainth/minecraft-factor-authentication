# TOTP in Minecraft redstone

Handoff for a Claude Code agent with Docker access. Read this fully before acting.

## Goal

Build a working **TOTP verifier/generator in pure redstone**, and demonstrate it running in a real server. The real goal is redstone. A datapack version is an optional stepping stone, not the target.

"Working" means: for a baked-in secret and an externally supplied time counter, the redstone circuit outputs the same 6-digit code as a standard authenticator app (HMAC-SHA1, 30 s period).

## Current state (stage 1 done, verified)

Files in this repo (commit them as-is):

- `ref.py`: from-scratch SHA-1, HMAC-SHA1, HOTP/TOTP. Passes the RFC 4226 vectors (10) and RFC 6238 SHA-1 vectors (6), and matches `hashlib`/`hmac` on edge-length messages and keys.
- `datapath.py`: bit-exact register-transfer model of the proposed hardware. Passes the RFC vectors and 3,000 random keys/counters against `ref.py`. Run with `python3 datapath.py` (do not use `-I`; it breaks the local import).

Both were run and passed. Nothing below stage 1 has been built or tested.

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

## Unverified claims: check before relying on them

These came from memory or rough estimates, not measurement:

- `/tick rate` / `/tick sprint` exist in vanilla 1.20.3+ and allow up to 10,000 TPS.
- MCHPRS (redstone-focused plot server) is the intended simulator for stage 3. Check which Minecraft version it currently targets, how to load a schematic into a plot, and how to set its redstone tick rate (`/rtps` as far as I know). It does not implement vanilla datapacks/scoreboards, so it cannot run the datapack path.
- Timing estimate: about 7-20 min per code at 20 TPS with a ripple adder; about 10-120 s with a fast adder plus sprinting. **These are guesses.** Replace them with measured numbers.
- A claimed redstone SHA-256 "Bitcoin miner" and a redstone language model exist online; sourcing for the first is weak. No prior redstone/datapack TOTP implementation was found (weak evidence; niche).

## Plan

### Stage 2: gate-level design + simulation (no Minecraft needed)
1. Define a redstone-realistic primitive set (NOT/OR/AND/XOR, latch, flip-flop, delay) with per-gate tick delays.
2. Write the round engine, schedule register, control FSM, truncation and mod as a netlist. A small Python netlist simulator is fine.
3. Verify cycle-accurately against `datapath.py` (same RFC vectors and random tests). Report gate count, state bits and critical-path delay in redstone ticks for each adder choice.
4. Pick the architecture and write down the resulting real cycle time.

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
