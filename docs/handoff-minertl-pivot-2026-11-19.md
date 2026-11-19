# Handoff — pivot to MineRTL (2026-11-19)

## What changed

An untracked, gitignored `MineRTL/` directory was found in the repo — a full Verilog-to-Minecraft-redstone
synthesizer (Yosys frontend, automatic gate placement, automatic 3D routing, MCHPRS fork integration,
`.litematic` output). It is not referenced anywhere in the rest of `CLAUDE.md`'s history; its provenance
in this working copy is unknown (not in git log, `.gitignore` already excluded it before this session touched it).

The user decided (explicitly asked, see conversation) to pivot the TOTP-in-redstone project onto MineRTL
instead of continuing to hand-route gates (`build_full_adder_test.py` / `redstone_parts.py`'s ad hoc
`route()`), which `docs/handoff-full-adder-2026-11-18.md` already flagged as not scaling: 3D collision
routing by hand was consuming nearly all session time, not redstone logic design.

**This means:** the plan in `CLAUDE.md`'s "Architecture decided so far" / "Stage 3" sections (hand-built
round engine, hand-placed AND/OR/NOT/XOR primitives, hand-routed full adder) is superseded for anything
past the primitive-gate level. The verified primitives (NOT/OR/AND gate truth tables, the live-build
gotchas: standing vs wall torches, repeater facing, no-shared-dust-junction, straight-line repeaters) are
still real empirical findings about this MCHPRS build and remain useful background, but the *path forward*
is: **write the TOTP datapath as synthesizable Verilog, let MineRTL synthesize + place + route it.**

`ref.py`, `datapath.py`, `netlist.py` (the from-scratch SHA-1/HMAC/TOTP software models, bit-exact verified
against RFC vectors) are still the correctness oracle and remain valid — a Verilog port of that same logic
is what gets handed to MineRTL, and its I/O behavior must still be checked against `ref.py`.

## Toolchain now working (this session)

MineRTL's own prerequisites (README) say macOS/Linux only, Windows needs WSL. This machine has WSL2 Ubuntu
22.04 already installed. Setup performed:

1. Ubuntu 22.04's apt `yosys` is 0.9 (from ~2019) — too old, missing flags MineRTL's synth pipeline needs
   (`flatten -noscopeinfo` errors out). **Do not `apt install yosys`.**
2. Installed a current yosys via YosysHQ's prebuilt **oss-cad-suite** instead: downloaded
   `oss-cad-suite-linux-x64-<date>.tgz` (~720MB) from
   `https://github.com/YosysHQ/oss-cad-suite-build/releases`, extracted to `~/tools/oss-cad-suite` inside
   WSL. Gives Yosys 0.71+ — confirmed working.
3. `uv` was already present at `~/.local/bin/uv` inside this WSL install (unclear if from a prior session).
4. `uv sync` inside `MineRTL/` (run from the Windows-mounted path `/mnt/c/Users/.../MineRTL`) installs fine —
   builds its Cython router extension too.
5. **DrvFs (the `/mnt/c/...` Windows-filesystem mount) cannot host named pipes** — `synth.sh` internally
   does `mkfifo build/artifacts/netlist.pipe`, which fails with "Operation not supported" if
   `--artifacts-dir` (or the default `build/`) resolves onto `/mnt/c/...`. **Fix: always pass
   `--artifacts-dir` and `--out-litematic` pointing at a path under the WSL native filesystem (e.g.
   `~/minertl_build/...`), even though the *source* Verilog/project directory can stay on `/mnt/c/...`.**
6. The repo's `synth.sh` (and other MineRTL shell scripts) have **CRLF line endings** as checked out on
   this Windows working copy, which breaks `#!/bin/bash` (`env: 'bash\r': No such file or directory`).
   Fixed once this session with `sed -i 's/\r$//'` over `MineRTL/**/*.sh` — since `MineRTL/` is gitignored,
   this fix isn't persisted by git; **repeat the `sed` fix (or reclone inside WSL directly, avoiding the
   Windows checkout/CRLF path entirely) if `MineRTL/` is ever re-fetched.**
7. **Invoking `wsl.exe` from this project's Bash tool (git-bash/MSYS on Windows) requires
   `MSYS_NO_PATHCONV=1`** (and ideally `MSYS2_ARG_CONV_EXCL="*"`) as an env prefix on the command, or MSYS's
   automatic Unix-path-to-Windows-path conversion mangles any `/bin/...`-style argument *inside* the
   command string before it reaches `wsl.exe` — symptom: `#!/bin/bash` shebang lines in heredoc-written
   scripts come out as `#!C:/Program Files/Git/bin/bash`, or plain paths get a `C:/Program Files/Git`
   prefix silently spliced in. Lost real time to this; always set it for any `wsl -d Ubuntu -- ...` call
   from this environment.

**Verified working end-to-end this session:** built MineRTL's own `examples/counter` —
`[stats] 28.0s, 10 cells, 11 nets, 37x33x44, 0 failed, 0 verify` — a clean synth+place+route+litematic-write
with zero verify failures. Toolchain is proven; the TOTP Verilog itself has not been written yet.

## Known commands (for continuing)

From the Windows side, run via the Bash tool as:
```
MSYS_NO_PATHCONV=1 wsl -d Ubuntu -- bash -lc "<command>"
```
with yosys + uv on PATH inside that command via:
```
export PATH="$HOME/tools/oss-cad-suite/bin:$HOME/.local/bin:$PATH"
```
Build command shape (from inside `MineRTL/`, project dir can stay on `/mnt/c/...`, artifacts must not):
```
./synth.sh <project-dir> --artifacts-dir ~/minertl_build/artifacts --out-litematic ~/minertl_build/result.litematic
```
Prefer writing any nontrivial script to a file via a heredoc through `bash -lc "cat > ~/foo.sh << 'EOF' ... EOF"`
rather than complex single-line quoting — nested MSYS/WSL/bash quoting is fragile (see point 7 above).

## Not yet done

- No TOTP/SHA-1 Verilog has been written. Next real step: port the round engine + adder + truncation from
  `netlist.py`'s already-verified gate-level design into synthesizable Verilog, feed it to `./synth.sh`,
  and cross-check behavior against `ref.py`/`datapath.py` (ideally via `mchprs_headless` scripted I/O, once
  that's built from the MCHPRS fork — not yet attempted).
- The MCHPRS fork MineRTL expects (`saucefishman/MCHPRS`, with `mchprs_headless` and `.server.json` support)
  is a *different* fork from the upstream `MCHPR/MCHPRS` already built in this repo's `mchprs/` /
  `mchprs:local` Docker image. Decide whether to build the fork too (needed for `mchprs_headless`
  scripted testing and in-game debug prints) or stick to upstream + manual lever-driven testing via the
  existing `bot/` mineflayer driver. Not decided yet.
- `CLAUDE.md` itself has not been updated to reflect this pivot — do that once the Verilog port is underway,
  not before (per the project's own "don't claim a stage works from reasoning alone" rule).
