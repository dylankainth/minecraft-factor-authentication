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

3. ~~The actual live in-game demo.~~ **Attempted, root-caused where it matters, then stopped — decided
   insufficient ROI to chase further; headless verification stands as the project's proof.**
   `scripts_make_server_json.py` had a real bug (fixed): it
   treated every non-`clk` pin as an input needing a lever, including the 21 *output* pins (`code[0..19]`,
   `done`), writing 55 levers instead of the correct 34 — fixed by actually checking the schematic for a
   real lever at each candidate position (same rule `crates/headless/README.md` documents: "a pin is an
   input if there is a lever at cell + (nx, 1, nz)"), not just excluding `clk` by name.

   With that fixed, `/load totp_core.litematic -c` **works**: loads a real 224x234x469 build with actual
   block updates in 7.3 seconds, `/lever <name> [on|off|toggle]` drives inputs cleanly with real chat
   confirmations ("Turned rst on", "counter[3] is already off", etc.) — a much nicer interface than the old
   `//set`+`activateBlock` dance `bot/totp_core_probe.js` used. The clock genuinely starts this time; `rst`
   and `counter[i]` were set via `/lever`, `start` turned on, and the server showed real, sustained CPU
   usage (~120%) while computing — not frozen.

   **Open issue:** live play is dramatically slower than `mchprs_headless`, even with the same
   Redpiler-compiled circuit -- it didn't finish a single code within 10 minutes, vs. headless's 10.2s for
   one code. Likely cause, not fully confirmed: `crates/core/src/plot/mod.rs`'s live tick loop sizes each
   batch to roughly a 50ms wall-clock window (based on the *previous* batch's measured per-tick cost), and
   re-does per-cycle housekeeping (player packets, world-send checks, `update_players`, `handle_commands`,
   etc.) between every batch — overhead `mchprs_headless`'s dedicated, housekeeping-free test harness simply
   doesn't have. Confirmed NOT a correctness or "frozen clock" problem — CPU was genuinely pegged the whole
   10 minutes, consistent with real (if slow) computation.

   **Resolved as a known limitation, not pursued further.** A fresh attempt (`totp_live_fresh`, after the
   machine/Docker went idle and killed an earlier 50-minute resume run silently — restarted Docker and
   relaunched from scratch) ran a full, clean 50 minutes with no crash this time: `mchprs_fork_server`
   stayed up the whole time, the bot polled `done` every ~4s throughout, and it ended with a clean
   `[result] TIMED OUT waiting for done` at t+2998s. Combined with the earlier 10-minute attempt, that's two
   full timeouts against headless's 10.2s for the identical Redpiler-compiled circuit — a ~300x gap, well
   beyond ordinary network/chunk-sync overhead. Asked the user how to proceed (resume with a much longer
   ceiling / root-cause the batching code / accept headless as sufficient and stop); chose to **stop here**.
   Headless mode already gives complete, legitimate, engine-level correctness verification (all 10 RFC
   vectors, 0 failures) regardless of whether the live path is ever sped up — see `README.md`'s Status
   section for the final writeup. The live-tick-batching bottleneck in
   `crates/core/src/plot/mod.rs` remains unconfirmed as to exact cause and is a good starting point if anyone
   picks this back up.

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
