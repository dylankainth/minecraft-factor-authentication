# Handoff — XOR Gate Fix (2026-11-09)

## Context

This session continued stage 3 (layout + run in MCHPRS) from the blog post `docs/blog-1056-09-11-2026.md` and `CLAUDE.md`.

## Offline state (verified)

- `ref.py`, `datapath.py`, `netlist.py` all pass RFC 4226 (10 vectors) + RFC 6238 (6 vectors) + 3000/40 random cases, bit-exact. The SHA-1/HMAC/TOTP design is sound offline.
- Gate delay model: NOT=1rt, OR=0rt, AND=2rt, XOR=2rt. Ripple ~39,798 rt/code vs carry-select-8 ~31,959 rt/code. Carry-select recommended default.
- MCHPRS container running on `totp-net` at port 25565 (localhost). Bot image `totp-bot:local` built from `bot/`.

## Live verified (MCHPRS, real block reads)

- NOT gate: standing-torch inverter → dust → lamp. Truth table correct both directions.
- OR gate: two levers → repeaters → same consumer block (no shared dust). All 4 combos correct.
- AND gate: De Morgan composition of NOT+OR+NOT. All combos correct.
- Toolchain end-to-end: `schem.py` → `//load` → `//paste` → mineflayer lever clicks → `blockAt(...).getProperties()` reads.

## This session: XOR gate fix

### Root cause found

The XOR gate in `build_xor_compact_test.py` failed live because **raw lever signals took staircase steps directly into repeaters** (no settle hop). Per `build_rawb_fix_test.py` / `build_rawb_lamp_test.py`: a staircase **landing cell** can power another dust cell but **cannot reliably power a consumer** (repeater/lamp). Raw signals landed on step cells and fed repeaters directly → intermittent / stuck-on behavior.

Also confirmed: `redstone_wire.power` client reads are stale/unreliable (read `power=10` with no connections); `redstone_torch.lit` and `redstone_lamp.lit` reads are reliable.

### Fix applied

Rewrote the XOR as `build_xor_v23.py` with:
- **Settle hop after every step**: raw signal → step-up landing → plain dust settle hop → first repeater (dust-to-dust works, landing-cell-to-consumer doesn't).
- **Fully separated signal paths**: every signal path uses its own z-band; merges only at S1/S2/LAMP via `converge()` (repeaters aimed directly at consumer block — never shared dust).
- **Y-level separation**: signals at y=3 (NOT/raw), long NS legs at y=4 to avoid crossings, final OR merge at y=4.
- Logic: `XOR = OR(Term1, Term2)`, `Term1 = NOT(NOT_A OR B)`, `Term2 = NOT(A OR NOT_B)`.

### Live test results

Built `xor_compact_test.schem` with `build_xor_v23.py`, copied to `mchprs_data/schems/`, ran `xor_v23_probe.js` against live MCHPRS.

- **NOT gates work**: lever A/B toggle correctly; torch A/B invert correctly (lit=true when lever off, lit=false when lever on).
- **S1/S2/LAMP positions NULL**: could not locate S1/S2/LAMP at expected world coords. The circuit schem spans ~200 blocks in X; probe coordinates may be off. Not yet verified end-to-end truth table.
- The full XOR truth table was NOT confirmed live. S1/S2/LAMP read NULL — likely probe coordinate mapping error (schem normalized to min coords) or paste offset mismatch.

## Recommended next steps

1. **Find the actual paste coordinates**: scan around player position for redstone_lamp or stone blocks to locate S1/S2/LAMP, then fix probe coordinates in `xor_v23_probe.js` and re-run the truth table.
2. **If XOR truth table passes**: build a 1-bit full adder truth table empirically (next target per CLAUDE.md), then scale to word width.
3. **If XOR won't close**: per CLAUDE.md working rules, propose scope reduction (bit-serial datapath or lighter PRF) rather than faking a result. Switching away from SHA-1 needs user approval (breaks authenticator-app compatibility).

## Files changed this session

- `build_xor_v23.py` — new XOR build with settle hops + separated paths (compiles cleanly, 1999 segments).
- `xor_compact_test.schem` — regenerated from v23 build, copied to `mchprs_data/schems/`.
- `bot/xor_v23_probe.js` — truth-table probe (coordinates need fixing after locating S1/S2/LAMP).
- `bot/latch_probe.js`, `build_latch_test.py` — confirmed step+settle hop works reliably (step landing alone does NOT).
- `bot/torch_relight_probe.js`, `build_torch_relight_test.py` — confirmed torch relight works; failure is torch→dust→lamp turn.
- `bot/term1_fixed_probe.js`, `build_term1_fixed_test.py` — confirmed merge-stone torch relight works with settle hop.

## Docker notes

- MCHPRS: `docker run -v ./mchprs_data:/data -p 127.0.0.1:25565:25565 mchprs:local` (running, container name `mchprs`).
- Bot: `docker run --rm --network totp-net -e MC_HOST=mchprs totp-bot:local <probe.js>` (rebuild image after editing bot/*.js).
- Windows Git Bash: prefix `MSYS_NO_PATHCONV=1` for -v mounts.

## Definition of done (not yet met)

1. Redstone core outputs correct 6-digit code for RFC test key + 10 RFC 4226 counters. **Not started.**
2. Measured time per code and block count reported. **Not started.**
3. README explaining launch/load/inject/read. **Not started.**
