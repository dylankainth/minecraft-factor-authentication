# Next steps

Where this session left off, and what's queued up next. See `README.md` for the full story and
`docs/handoff-live-verification-2026-11-19.md` / `docs/handoff-optimization-2026-11-19.md` for the detailed
debugging trail behind each of these.

## Done since this doc was first written

1. ~~Full 10-vector `mchprs_headless` confirmation.~~ **Done.** All 10 RFC 4226 vectors pass, 0 failures,
   via Redpiler, 24.3 seconds total (~2.4s/code). See `bot/totp_headless_all10.txt` for the script.
2. ~~Try Redpiler in `mchprs_headless`.~~ **Done, and it's the real headline result.** The wire-on-wire fix
   needed to be applied to `mchprs_fork/` too (it had the identical unpatched code as `mchprs/` -- a
   separate clone of a different upstream, checked rather than assumed). With that in place: single vector
   in 10.2s (vs ~3.9 min interpreted — ~23x), all 10 vectors in 24.3s (~100x vs. the interpreted-mode
   per-vector rate). Redpiler genuinely works for this build; the bug, not fanout or circuit size, was the
   entire obstacle.

## Immediate next action

3. **The actual live in-game demo.** This is now the only thing left. The root cause (a raw `//paste` never
   schedules a tick, so a self-clocking loop never starts) and the fix (the fork's native `/load -c`, or
   `/watch`) are both understood; Redpiler is confirmed to work correctly on this exact build. Concretely:
   - Copy `totp_core.litematic` into `mchprs_fork_data/schems/`.
   - Build a real `.server.json` for it with `scripts_make_server_json.py` (written, **still untested live**)
     so `/lever <name> [on|off|toggle]` works in-game — MineRTL's own `synth.sh` only writes one when a
     build has debug probes or a server-driven clock (`builder.py`'s `if resolved_probes or clock_entry:`
     gate), neither of which this build has, hence the hand-built one.
   - `/load totp_core.litematic -c` (not `//load` + `//paste`).
   - Use the same long settle windows (2000+ ticks) the headless fix established between every `rst`/input
     change — this reflects a genuine real propagation distance in this build, not a headless-only quirk.
   - Try `/redpiler compile` once loaded, now that it's confirmed to work on this build via headless — worth
     confirming it also compiles cleanly from a proper `/load -c`, not just from `mchprs_headless`'s own
     load path, before assuming it'll behave identically live.
   - `mchprs_fork_server` is already running (port 25566, separate from the original `mchprs` on 25565,
     patched with the wire-on-wire fix and rebuilt) and `mchprs_fork:local` is built — ready to start.
   - Measure real wall-clock time for a live, player-visible code generation once this works — every timing
     number in `README.md` so far comes from headless, which has zero network/chunk-sync overhead a live
     client does carry. Don't assume the headless numbers transfer directly; measure it.

## Smaller loose ends

- `bot/shift.json` / `bot/pins.txt` currently hold the **v2 (optimized)** build's values. If testing the
  original (pre-optimization) build again for any reason, regenerate both — they are build-specific, not
  interchangeable between `main.v` revisions.
- The bit-serial datapath rewrite (README's "deliberately not attempted" optimization) is now much lower
  priority — Redpiler alone got this build to ~2.4s/code, which is fast enough that the architecture-level
  rewrite's main justification (shrinking the interpreted-mode wall-clock time) has mostly evaporated. Still
  on the table if a smaller physical footprint ever matters for its own sake.
- `mchprs_fork/` and `mchprs_fork_data/` are both gitignored (consistent with `mchprs/`, `MineRTL/`,
  `mchprs_data/`) — if either is ever re-cloned/recreated:
  - Reapply the wire-on-wire fix to `mchprs_fork/crates/redpiler/src/passes/frontend/input_search.rs`
    (identical diff to the one already applied to `mchprs/`, see README) — it does not carry over from a
    fresh clone.
  - The headless binary needs a Docker-based build, because the project's own `.cargo/config.toml` pins
    `linker = "clang"`, which this environment's WSL install didn't have by default; the Docker route
    (plain `rust:alpine`, no custom linker) sidesteps that entirely. The Dockerfile is kept at the repo root
    (`Dockerfile.mchprs_headless`, tracked — since `mchprs_fork/` is wholly gitignored, a copy *inside* it
    would never actually get committed):
    `DOCKER_BUILDKIT=1 docker build -f Dockerfile.mchprs_headless --target export -o headless_bin mchprs_fork/`
  - If a previous build's binary is still running (e.g. a long headless test in progress), exporting to the
    same `headless_bin/` directory will fail with a Windows file-lock error ("Access is denied") — export
    to a fresh directory (`headless_bin_v2`, etc.) instead of waiting, then swap once free.
- `headless_bin*/mchprs_headless` binaries are gitignored (compiled Linux/musl binaries don't belong in the
  repo) — rebuild with the command above whenever needed.
