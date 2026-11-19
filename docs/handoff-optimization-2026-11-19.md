# Handoff — redpiler patch + circuit optimizations (2026-11-19, continued again)

## `mchprs/` is gitignored — this patch does not survive a re-clone

`mchprs/crates/redpiler/src/passes/frontend/input_search.rs` was patched locally with
[benburk/MCHPRS PR #2](https://github.com/benburk/MCHPRS/pull/2) (not yet merged upstream), which fixes
Redpiler panicking (`Exceeded the maximum number of default inputs 255`) on redstone wire stacked directly
on top of other wire — something only a paste can produce, and exactly what this project's pastes do. The
diff:

```diff
         } else if let Block::RedstoneWire(wire) = block {
             match side {
-                BlockFace::Top => self.search_wire(start_node, pos, link_ty, distance),
-                BlockFace::Bottom => {}
+                BlockFace::Top if search_wire => {
+                    self.search_wire(start_node, pos, link_ty, distance)
+                }
+                BlockFace::Top | BlockFace::Bottom => {}
                 _ => {
```

Since `mchprs/` is gitignored (see [[project-minertl-wsl-toolchain]] and `.gitignore`), **this patch is lost
if `mchprs/` is ever re-cloned from `MCHPR/MCHPRS` upstream** — reapply it (or check whether it's landed
upstream by then) before rebuilding the `mchprs:local` image. After patching, rebuild with
`docker build -t mchprs:local mchprs/` (a Rust release build, ~9 minutes) and recreate the container (a
plain `docker restart` keeps the old binary — the container must be removed and re-run against the new
image).

## Circuit optimizations applied to `MineRTL_designs/totp_core/main.v`

See `README.md`'s "Why it was slow, and what got fixed" for the full writeup and before/after metrics table.
Summary for anyone diffing the Verilog:

1. Removed the redundant `block_mem` register — `sched[0]` already equals what it held for the first 16
   rounds (provable: `sched` is a pure rotation of the initial block words during that phase). No behavior
   change, re-verified bit-exact against all 10 RFC 4226 vectors.
2. Pipelined `e + K[round] + w` one cycle ahead into a new `ekw_reg`, cutting the round function's critical
   add chain from 4 sequential 32-bit adds (`rol5(a)+f+e+K+w`) to 2 (`rol5(a)+f+ekw_reg`).

Both changes are in the committed `main.v`; `MineRTL_designs/totp_core_tb/main.v` is kept as an identical
copy for the testbench (MineRTL's `synth.sh` picks up every `.v` file in a project directory, so the
testbench lives in a sibling directory and needs its own copy of the design — see
`docs/handoff-minertl-totp-core-2026-11-19.md`). Keep both in sync by hand if `main.v` changes again.

## Rebuilding after these changes

```
# 1. Re-simulate first
cd MineRTL_designs/totp_core_tb && iverilog -g2012 -o /tmp/tb.vvp main.v tb_main.v && vvp /tmp/tb.vvp

# 2. Re-synthesize (artifacts must be on the WSL-native filesystem, not /mnt/c -- see
#    [[project-minertl-wsl-toolchain]])
cd MineRTL && ./synth.sh ../MineRTL_designs/totp_core \
    --artifacts-dir ~/minertl_build_v2/totp_artifacts \
    --out-litematic ~/minertl_build_v2/totp_core.litematic --no-server-clock

# 3. Convert to Sponge .schem (MCHPRS doesn't read .litematic)
PYTHONPATH=. MineRTL/.venv/bin/python -c "
import scripts_litematic_to_schem as conv
conv.convert('~/minertl_build_v2/totp_core.litematic', '~/minertl_build_v2/totp_core_v2.schem', we_offset=(0,0,0))
"
# -- note the printed shift_x/y/z; bot/shift.json must be updated to match, or the
#    paste position math in totp_core_probe.js will be wrong (it was, the first time).

# 4. Re-capture pin positions (placement changes between builds, pins.txt does not
#    carry over)
MINECRAFT_V_ARTIFACTS_DIR=~/minertl_build_v2/totp_artifacts_pins \
    MineRTL/.venv/bin/python MineRTL/scripts/build_with_pins.py ~/minertl_build_v2/pins.txt \
    --netlist ~/minertl_build_v2/totp_artifacts/netlist.json.gz \
    --out-litematic ~/minertl_build_v2/totp_core_pins.litematic --no-server-clock
```

## A real gotcha hit recreating the MCHPRS container

Recreating the `mchprs` container with `docker run -v "$(pwd)/mchprs_data:/data" ...` from this project's
Bash tool (git-bash/MSYS on Windows) silently produced a broken mount — `$(pwd)` expansion combined with
MSYS's path mangling turned the bind-mount source into garbage (`...mchprs_data;C`) and the destination into
`\Program Files\Git\data`, so Docker fell back to creating an empty anonymous volume at `/data` instead of
mounting the real one. Symptom: `//load` says "the specified schematic file could not be found" even though
the file is right there in `mchprs_data/schems/` on the host. Same root cause as the `MSYS_NO_PATHCONV`
issue already documented in [[project-minertl-wsl-toolchain]], just hitting a volume mount instead of a
command argument this time — use an explicit absolute path (not `$(pwd)`) for the mount source, and verify
with `docker inspect <container> --format '{{json .Mounts}}'` that the mount actually resolved correctly
before assuming a paste failure is a real bug.

## Status

Redpiler compiles without panicking on the optimized build (confirmed: no crash, bot stayed connected,
unlike the first attempt). Whether it's actually *running* in compiled mode or silently still interpreting
is not yet confirmed — CPU stayed pegged at 100% for well over a minute after the compile command, which is
consistent with either (a) the compile step itself still running (graph construction over a
770,000-block paste is real work, separate from execution speed afterward) or (b) redpiler not actually
activating. A run is in progress; update this doc once that's resolved rather than guessing.
