# Handoff — full TOTP core synthesized via MineRTL, simulation-verified (2026-11-19)

## What's new since `docs/handoff-minertl-pivot-2026-11-19.md`

Wrote the entire HMAC-SHA1 TOTP core as synthesizable Verilog
(`MineRTL_designs/totp_core/main.v`) — key baked in as `S_in`/`S_out` localparams (precomputed offline
from `ref.py` for the RFC test key `"12345678901234567890"`), a single FSM (`IDLE -> LOAD1 -> RUN1(x80) ->
FF1 -> LOAD2 -> RUN2(x80) -> FF2 -> TRUNC -> DONE`) running two SHA-1 compressions back to back, then
truncate + `% 1000000`. Inputs: `clk`, `rst`, `start`, `counter[31:0]`. Outputs: `code[19:0]`, `done`.
Mirrors `netlist.py`'s already-verified round/schedule/feed-forward logic exactly (same indexing for the
message schedule's sliding window, same register-boundary semantics), but written at the word level —
MineRTL's placer/router doesn't need bit-serial restructuring the way hand-routing did.

**Caught and fixed one real bug before simulating:** the first draft had the schedule-register shift
(`sched[i] <= sched[i+1]`, unconditional every round) and a `round==0` schedule-initialization block both
writing `sched` as non-blocking assignments in the same clocked process — the shift silently won every
time, so the round==0 init never took effect. Fixed by moving schedule initialization into the `LOAD1`/
`LOAD2` states (a separate clock cycle) instead of trying to special-case it inside the round loop.

**Simulation (iverilog, via oss-cad-suite, inside WSL) now passes all 10 RFC 4226 test vectors
bit-exactly** (`tb_main.v`, kept in a sibling directory `MineRTL_designs/totp_core_tb/` — MineRTL's
`synth.sh` picks up every `.v` file in the project directory, so the testbench must live outside it or it
gets synthesized as part of the design and fails on simulation-only constructs like `@(posedge clk)` inside
a task):

```
PASS counter=0 code=755224
...
PASS counter=9 code=520489
ALL RFC VECTORS PASSED
```

**Then ran the real thing through MineRTL's synth+place+route**, with artifacts on the WSL-native
filesystem per the toolchain notes, `--no-server-clock` (bakes a clock into the schematic so it runs on
plain upstream MCHPRS / vanilla+Litematica, not just the fork):

```
[macro] 0 instances; top level 6025 components, 6170 nets
[place] poisson: ... final hpwl 242797 (34.4s)
[layout] workspace 220x240x219
[wire] done (6170 nets, 0 failed) 16.3s, 316894 path cells
[hold] ... 0 left
[timing] critical path 972 ticks
Wrote litematic: ~/minertl_build/totp_core.litematic
[stats] 74.8s, 6019 cells, 6170 nets, 220x240x468, 0 failed, 0 verify
```

**0 failed nets, 0 verify errors.** This is a complete, physically laid-out, auto-routed redstone build of
the entire TOTP core — not a single gate, not a partial adder — produced in under 2 minutes of build time.
It is the first time this project has had a structurally complete core, by a wide margin past anything the
hand-routing approach reached.

## What this is NOT yet

**Not yet confirmed running in a live Minecraft/MCHPRS server.** Per this project's own working rule
("verify against a real server, don't claim from reasoning alone, don't claim a stage works from reasoning
alone"), simulation + successful synth/place/route is strong evidence but is not the same bar the earlier
NOT/OR/AND gates cleared (a real running server, real lever input, real lamp read-back). Stopping here
honestly rather than inflating the claim.

To actually run it live, still needed (none attempted yet this session):
1. **Docker Desktop was not running this session** — `docker ps` failed to connect. Needs starting before
   anything else.
2. Check whether the existing `mchprs:local` image/container from earlier stages is still present, or
   needs rebuilding.
3. **Figure out whether upstream MCHPRS's `//load` accepts `.litematic` directly**, or whether it only
   reads Sponge `.schem` (which `schem.py` writes, but that's this project's own hand-rolled writer, not
   what MineRTL emits). MineRTL's README implies plain upstream MCHPRS can load `.litematic` builds
   (distinguishing it from the fork only by `.server.json` support), but this has not been tested against
   this project's actual running `mchprs:local` container. If it can't, the alternative is Litematica in a
   normal client, which doesn't fit this project's headless-bot-driven testing approach.
4. **A new bot probe script is needed** — the existing `bot/*_probe.js` scripts drive single-bit lever/lamp
   circuits. This design needs 32 input levers (`counter[0..31]`) plus a `start` lever, and 20 output lamps
   (`code[0..19]`) plus `done` — reading/writing a 32-bit binary counter and a 20-bit binary code via real
   in-game lever flips and lamp reads, not yet written.
5. Given the measured `972`-tick critical path and roughly 162 clock edges needed per code
   (80+80+a few FSM cycles), that's **~157,000 redstone ticks per code** — at `/rtps unlimited` this is
   still a real amount of wall-clock; worth measuring once it's actually running rather than estimating
   further.

## Why stopped here rather than continuing into live verification tonight

Starting Docker Desktop, confirming/rebuilding the MCHPRS image, resolving the `.litematic`-vs-`.schem`
loader question, and writing a 52-signal (32 in + 20 out) lever/lamp probe script is a distinct chunk of
work from "get MineRTL producing a correct, routable netlist," which is the milestone this session actually
closed. Flagged to the user as the natural next session's starting point rather than rushed through.

## Definition of done — updated status

1. Redstone core outputs correct 6-digit code for RFC test key + 10 RFC 4226 counters: **logic verified in
   simulation (bit-exact, all 10 vectors) and the circuit has been physically synthesized/placed/routed
   with 0 failures; NOT YET confirmed running in a live server.**
2. Measured time per code and block count: **block count known (220x240x468 workspace, 6019 cells);
   time per code is a model estimate from `[timing] critical path 972 ticks` x ~162 cycles, NOT a live
   measurement.**
3. README for launch/load/inject/read: **not written yet — depends on resolving the live-server steps
   above first.**
