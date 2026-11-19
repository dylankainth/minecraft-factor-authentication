# Handoff — live verification debugging, root cause found (2026-11-19, continued)

## Summary

Continuing from `docs/handoff-minertl-totp-core-2026-11-19.md` (full TOTP core synthesized,
simulation-verified, 0 routing failures). This session's goal was live confirmation in MCHPRS. Hit a long
chain of real bugs, all now root-caused; a live run is in progress as this is written.

## Bugs found and fixed, in the order they were hit

1. **MineRTL emits `.litematic` (Litematica format); MCHPRS only loads Sponge `.schem`.** Wrote
   `scripts_litematic_to_schem.py` (uses `litemapy` to read the litematic, merges all regions -- later
   region's blocks win on overlap, which is correct Litematica semantics for things like a separately-added
   clock generator -- then writes via this project's existing `schem.py`).
2. **`view_distance` was 8 chunks (~128 blocks) in `mchprs_data/Config.toml`**, too small for this build's
   ~470-block span from a corner anchor. Raised to 32. (Turned out not to be the real blocker -- see #6 --
   but is still a correct fix and worth keeping.)
3. **`schem.Schematic.save()` trims to the tight bounding box of actual non-air blocks.** This build's real
   content starts at raw local x=5 (not 0), so every pasted position is offset by that trim unless the
   *player* stands at `ANCHOR + shift` instead of `ANCHOR` (shift = the trimmed bounding box's own
   min corner). `scripts_litematic_to_schem.py` now writes a `<file>.schem.shift.json` sidecar recording
   this; `totp_core_probe.js` reads it and adjusts the paste position accordingly. Pin world positions
   themselves are unaffected (`world = ANCHOR + raw_local` always, shift cancels out algebraically) --
   only the *player's paste-time standing position* needs the correction.
4. **MineRTL's `build_with_pins.py` pins are the I/O REPEATER's cell, not the lever/lamp fixture.** Per
   `MineRTL/minecraft_v/placement_engine/cosmetics.py:place_io_fixtures`: an output lamp sits at
   `(x+nx, y, z+nz)`; an input's real lever sits **one block above** that same point (a stone support at
   `(x+nx,y,z+nz)`, the lever on top of it). `totp_core_probe.js`'s `loadPins()` now applies `+1` to `y`
   for input pins only (`rst`, `start`, `counter[i]`), not for outputs.
5. **Suspected-but-ruled-out: palette size.** The build's blockstate palette has 643 distinct strings
   (mostly `redstone_wire` power/connection combinations), which crosses a few resize thresholds in
   MCHPRS's `PalettedBitBuffer` (`crates/world/src/storage.rs`). Stripped the volatile `power` property
   from `redstone_wire` in the converter (MCHPRS recomputes it on the next live transition anyway),
   cutting the palette to 140 -- the live symptom was identical before and after, so this was **not** the
   root cause. Kept the normalization anyway since it's harmless and still correct.
6. **The actual root cause: the bot's own client-side chunk cache (`bot.blockAt`) does not reliably
   reflect real world state for this build, even many minutes after a confirmed-successful paste, and even
   after flying directly to the target position first.** Proved this conclusively by bypassing
   `bot.blockAt` entirely and asking the **server** instead, via WorldEdit's `//count <pattern>` over a
   `//pos1`/`//pos2` selection: a 2.1M-cell sub-volume ("tenth" test build) reported exactly the expected
   non-air count (within rounding of the selection box), and the full 22.7M-cell build reported **exactly**
   835,116 non-air blocks -- bit-for-bit the number our converter wrote. The paste has been correct the
   entire time; only the bot's read of it was lying. (The much smaller gate-test builds from earlier
   sessions never hit this because they're tiny and close to the player.)
   - **Writes are unaffected.** `mineflayer`'s `activateBlock(block, ...)` only uses `block.position` to
     build the `block_place` interaction packet (confirmed by reading
     `node_modules/mineflayer/lib/plugins/inventory.js` inside the bot image) -- it never depends on the
     client's cached block type. So every lever toggle in every prior run almost certainly worked
     server-side, regardless of whether the client thought that position was air.
   - **Fix:** `totp_core_probe.js` now reads lamp state via `//count minecraft:redstone_lamp` at a 1-block
     selection instead of `bot.blockAt(...).getProperties().lit`. MineRTL's cosmetics.py pastes lamps with
     explicit `lit="false"`, so a count of 1 means "still default/unlit"; 0 means "in some other state"
     (trusting structurally that the position holds a lamp, which is independently confirmed by the whole-
     build block-count match). `//count`'s mask argument silently ignores bracketed property filters
     (confirmed from `crates/core/src/plot/worldedit/mod.rs`'s `WorldEditPattern::from_str` -- it parses the
     `[...]` syntax but never applies it before computing the pattern block's id), so `lit=true`/`lit=false`
     can't be selected directly in the pattern string; comparing against the known default state is the
     workaround.

## Also fixed along the way (tooling, not logic)

- **MSYS/git-bash's automatic Unix-path-to-Windows-path conversion mangles arguments passed to
  `docker.exe`, not just `wsl.exe`** -- same class of bug as already recorded in
  [[project-minertl-wsl-toolchain]], e.g. `/app/pins.txt` became `C:/Program Files/Git/app/pins.txt`. Prefix
  every `docker run` invocation with environment variables like `wsl`: `MSYS_NO_PATHCONV=1`.
- **Background bash tasks in this environment can be marked "killed" by the harness while the underlying
  `docker run` container keeps running fine.** When a background task's status flips to killed/completed
  unexpectedly but the work should still be in flight, check `docker ps` for the named container directly
  and `docker logs -f <name>` instead of trusting the wrapper task's reported status.
- **Always name bot containers explicitly** (`--name totp_probe_run`, etc.) and clean up stray ones
  (`docker ps --filter ancestor=totp-bot:local -q | xargs -r docker stop`) before a new run -- multiple
  simultaneous connections as the same username (`totp_bot`) left over from killed-but-not-removed
  containers caused at least one confusing failed run this session.

## Status as this doc is written

A live run (`totp_core_probe.js 0 755224 totp_core_corner.schem`) is in progress: paste confirmed, rst
pulsed, counter=0 set (no-op, all bits already zero), start pulsed, now polling `done` via the new
`//count`-based reader every 30s. Not yet resolved whether it reaches `done` and whether the resulting
`code` matches the expected RFC vector `755224` -- update this doc (or supersede it) once that's known
rather than claim success from the debugging alone.
