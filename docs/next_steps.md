# Next steps

Where this session left off, and what's queued up next. See `README.md` for the full story and
`docs/handoff-live-verification-2026-11-19.md` / `docs/handoff-optimization-2026-11-19.md` for the detailed
debugging trail behind each of these.

## Immediate next actions (in rough priority order)

1. **Full 10-vector `mchprs_headless` confirmation.** Only counter=0 and counter=1 have actually been run so
   far (0 failures, both correct). `bot/totp_headless_all10.txt` now has the full 10-vector script with the
   same fix `bot/totp_headless_test2.txt` proved out (explicit `set`/`settle 2000`/`set` sequences, not the
   too-short `pulse NAME 10`) -- written but not yet run. At ~3.9 min/vector in interpreted mode, expect
   ~40 minutes total.
2. **Try Redpiler in `mchprs_headless`** (`--modes redpiler`, or `--modes redstone,redpiler` to run both and
   compare). This is much lower-risk than trying Redpiler live again: headless has no server to crash, and
   the wire-on-wire fix is already applied to `mchprs_fork/` (confirm this — the patch was applied to the
   separate `mchprs/` clone first; check whether `mchprs_fork/crates/redpiler/src/passes/frontend/input_search.rs`
   needs the same patch, or already has equivalent handling — it's a different upstream, don't assume).
   If Redpiler gives a real speedup here (unconfirmed, see README's "why it was slow" discussion of
   compile-time vs execution-time), this is the path to a demonstrably fast build.
3. **The actual live in-game demo**, now that the root cause (raw `//paste` never schedules a tick) and the
   fix (the fork's native `/load <name>.litematic -c`, or `/watch`) are both understood:
   - Copy `totp_core.litematic` into `mchprs_fork_data/schems/`.
   - Build a real `.server.json` for it with `scripts_make_server_json.py` (already written this session,
     untested live) so `/lever <name> [on|off|toggle]` works in-game — MineRTL's own `synth.sh` only writes
     one when a build has debug probes or a server-driven clock (`builder.py`'s `if resolved_probes or
     clock_entry:` gate), neither of which this build has, hence the need for a hand-built one.
   - `/load totp_core.litematic -c` (not `//load` + `//paste` — confirm that distinction holds for this
     fork's commands exactly as the README describes).
   - Use the same long settle windows the headless fix established: pulsing `rst` or `start` too briefly
     is not just a headless-script-timing quirk, it reflects a genuine 2000+-tick real propagation distance in
     this build -- expect the same discipline matters live.
   - `mchprs_fork_server` is already running (port 25566, separate from the original `mchprs` on 25565) and
     the `mchprs_fork:local` image is already built — this step is ready to start, just not attempted yet.

## Smaller loose ends

- `bot/shift.json` / `bot/pins.txt` currently hold the **v2 (optimized)** build's values. If testing the
  original (pre-optimization) build again for any reason, regenerate both — they are build-specific, not
  interchangeable between `main.v` revisions.
- `scripts_make_server_json.py` has not been run or tested yet this session — written but unverified.
- The bit-serial datapath rewrite (README's "deliberately not attempted" optimization) is still on the
  table if a full architecture-level speedup is ever needed, but should only be attempted with time
  budgeted for full re-verification (simulation + synthesis + headless), given its scope.
- `mchprs_fork/` and `mchprs_fork_data/` are both gitignored (consistent with `mchprs/`, `MineRTL/`,
  `mchprs_data/`) — if either is ever re-cloned/recreated, note that `mchprs_fork`'s headless binary needed
  a Docker-based build because the project's own `.cargo/config.toml` pins `linker = "clang"`, which this
  environment's WSL install didn't have by default; the Docker route (plain `rust:alpine`, no custom linker)
  sidesteps that entirely rather than requiring a system package install. The Dockerfile for this is kept
  at the repo root (`Dockerfile.mchprs_headless`, tracked -- since `mchprs_fork/` is wholly gitignored, a
  copy *inside* it would never actually get committed) rather than inside the gitignored clone:
  `DOCKER_BUILDKIT=1 docker build -f Dockerfile.mchprs_headless --target export -o headless_bin mchprs_fork/`
- `headless_bin/mchprs_headless` is the exported binary from that build, gitignored (a compiled Linux/musl
  binary doesn't belong in the repo) — rebuild it with the command above whenever `mchprs_fork/` is
  recreated.

## Open questions, not yet investigated

- Does the forked MCHPRS (`saucefishman/MCHPRS`) have the same Redpiler wire-on-wire bug as upstream, or
  does it already carry an equivalent fix? Not checked — `mchprs_fork/` was cloned fresh and never compared
  against `mchprs/`'s patched `input_search.rs` for this.
- Real measured wall-clock time for a live in-game code generation (player-visible, not headless) is still
  entirely unmeasured — every real-time figure in `README.md` so far comes from `mchprs_headless`, which has
  no network/chunk-sync overhead. A live run could plausibly be meaningfully slower for reasons unrelated to
  the redstone simulation itself (chat command round-trips, block-update packet delivery to a connected
  client) — worth measuring once step 3 above is attempted, not assumed from the headless numbers.
