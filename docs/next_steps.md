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

   **First stop (2026-11-19 session close):** two full timeouts (10 min, then a clean 50 min, no crash) vs.
   headless's 10.2s — a ~300x gap. Decided to stop and accept headless as sufficient proof.

   **Reopened 2026-11-22 — three real bugs found and fixed, a fourth mystery found and left open.** See
   `README.md`'s Status section for the full writeup; summary here:
   1. **Fixed, kept:** live's `update()` called `redpiler.flush()` (an O(node-count) scan) after every tick
      batch instead of once before a read, like `mchprs_headless` does. Moved it to the existing
      network-send-throttled point in `crates/core/src/plot/mod.rs`.
   2. **Patched, not the real fix:** `Tps::Unlimited`'s self-reported throughput was wildly inconsistent
      (7M–140M ticks/sec, not matching its own computed ceiling). Patched a suspected zero-elapsed-time trap
      in the batch-size calc; separately found that a large *finite* `/rtps N` gives trustworthy numbers
      where `unlimited` doesn't. Neither fully explained the gap.
   3. **The real cause of "never finishes":** polling the output via WorldEdit `//count` every few seconds
      — the exact method every live-demo script in this project used — stalls live redstone progress. Proven
      with a minimal reproducer (`MineRTL_designs/repro_counter/main.v`, `bot/repro_live.js` /
      `bot/repro_nopoll.js`): never finished when polled, finished in ≤60s when read exactly once at the
      end with zero polling in between.
   4. **Resolved (narrowed, not fixed):** applying the poll-free pattern to the real `totp_core` (via
      `bot/totp_resume_fast.js` / `bot/totp_verify_inputs.js`), with correct, confirmed inputs (ruled out one
      false lead: a mid-session disconnect had left `start` never actually latched — fixed and retested) and
      confirmed high real throughput (tens of millions of ticks/sec via direct instrumentation, not the
      unreliable `/rtps` self-report), the real core *still* did not reach `done` even after far more ticks
      than headless needs for the whole computation.
   5. **Found the exact break point via `/redpiler inspect` — first attempt was wrong, corrected, now
      precise.** Used `MCHPRS_LOG=mchprs_redpiler=debug` (not `RUST_LOG` — silently does nothing) plus a
      technique for finding any internal signal's world position: cross-reference `netlist.json`'s
      `netnames` (signal name → net id) against the driving/consuming cell on that net, then look that cell
      up in `component_layout.json` for a world position (origin + the specific pin's offset).

      **Real mistake, worth remembering:** the first pass used `netlist.json`/`component_layout.json` left
      over from an earlier, *different* MineRTL synthesis run than the litematic actually deployed — MineRTL
      is not deterministic between runs on identical Verilog (confirmed: a fresh re-synth produced 5,625
      cells/5,776 nets vs. this build's 6,019/6,170 — different internal netlist, though top-level I/O pin
      *positions* happened to land in nearly the same place since their placement rule is simpler/stable).
      Caught by hashing the litematic the artifacts came from against the one actually in use — they
      didn't match. The derived internal positions from that mismatched pair gave a plausible-looking but
      unverified result (reported in README's history, since corrected, as "`start` on but its consumer
      reads off").

      **Fix and redo, if this happens again:** re-synthesize (`synth.sh`), deploy *that exact* litematic
      everywhere (`build/totp_core.litematic`, the live server's `schems/` dir — and re-touch
      `*.server.json`'s mtime, or the server warns "server.json is older than the schematic"), re-confirm
      0 failures in headless with the *existing* `bot/pins.txt` (confirms top-level I/O didn't move), then
      re-derive every internal position from the artifacts that came from that *same* synth run. Always hash
      the litematic the artifacts directory's binaries were built from against the litematic file you're
      about to inspect, before trusting any derived position.

      **The corrected, verified result:** `rst` lever `powered: false` (correct), `start` lever
      `powered: true` (correct). `state` (4 bits) reads `0001` = **`LOAD1`**, not `IDLE` — identical across
      two snapshots ~90 seconds apart, under sustained tens-of-millions-of-ticks/sec computation the whole
      time. `LOAD1`'s Verilog body (`main.v` around line 105) is unconditional: `state <= RUN1;`, no `if` —
      so being stuck there for 90+ seconds means **no clock edge has reached the FSM since the single edge
      that moved it `IDLE → LOAD1`.** The self-generated clock produces one pulse (plausibly from
      `/load -c`'s real block-placement settling) and does not keep oscillating in live play.

      **Next step, precisely scoped:** find the clock's own oscillator loop in the physical build (the
      `clk` net's `INPUT_PIN` component in `component_layout.json` gives one point on it, though direct
      raycast-inspection of that exact position failed from every angle tried — the oscillator's redstone
      loop likely needs a different point along its own path, not its abstract port marker) and watch it
      across a few real seconds to see whether it's toggling, stuck high, or stuck low. A second angle:
      compare against `mchprs_headless --run-clock`/`--probes` (a *different* code path for driving a named
      clock than this build uses, worth checking whether it even applies) or just read whether headless's
      own `settle N` ever needs more than one clock period's worth of ticks to make progress past `LOAD1` —
      if even headless's clock is a "one safe pulse during placement, nothing after" affair that just happens
      to not matter there (because `settle`'s tick loop doesn't depend on additional *real* oscillation, only
      on redpiler's `tick()` being called enough times), that would mean the oscillator was never the thing
      doing real work in headless either — worth directly confirming rather than assuming headless's success
      implies the oscillator continuously runs there.
   - A completely fresh end-to-end run (no resumes/reconnects in its history) was NOT tried and would also
     be worth ruling out, independent of the above.

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
  - Reapply the two live-tick-path fixes to `mchprs_fork/crates/core/src/plot/mod.rs` (see README's Status
    section for what/why): the deferred `redpiler.flush()` (move it out of the per-batch hot path into the
    existing `time_since_last_world_send > world_send_rate` block, alongside `world.flush_block_changes()`),
    and the `max_batch_size` zero-elapsed-time clamp (`last_nspt.max(Duration::from_nanos(1))` before
    dividing). Also doesn't carry over from a fresh clone. A temporary `[DEBUG update]` eprintln! was added
    to the same function during this investigation (calls/s, ticks_requested/s, `last_nspt`, batch sizes) —
    useful for future debugging, remove it once no longer needed.
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
- The live server's debug logging env var is `MCHPRS_LOG` (e.g. `MCHPRS_LOG=mchprs_redpiler=debug`), not
  `RUST_LOG` — the latter is silently ignored (see `mchprs_fork/src/main.rs`'s logging setup). Needed for
  `/redpiler inspect`'s output, which lands in the *server's* stdout via `tracing::debug!`, not in the
  requesting player's chat.
- The MineRTL build artifacts needed to locate internal signal positions (`netlist.json.gz`,
  `component_layout.json.gz`) aren't committed anywhere — they're only in `~/minertl_build/totp_artifacts/`
  inside WSL from when the build was last run. Re-run `synth.sh` if that's gone; the scripts in this doc's
  item 5 above expect that directory layout.
