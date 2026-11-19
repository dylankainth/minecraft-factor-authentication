// Drives the full MineRTL-synthesized TOTP core: pulses rst, sets the
// 32-bit counter via levers, pulses start, polls the `done` lamp, then
// reads the 20 `code` lamps back as a binary number and compares against
// the expected RFC 4226 code.
//
// IMPORTANT: this build is large enough that the bot's own client-side
// chunk cache (bot.blockAt) does not reliably reflect the real world state
// at distant positions even minutes after a confirmed-successful paste --
// verified server-side via WorldEdit's //count (e.g. a 2.1M-cell sub-volume
// consistently reports the exact expected non-air count, while blockAt at
// the same positions reads stale air). So reads here go through //count
// (server-authoritative) instead of blockAt. Writes (activateBlock) are
// unaffected: mineflayer's activateBlock only uses the block's .position to
// build the interaction packet, which the server resolves itself -- it
// never depends on the client's cached block type, so lever toggles work
// even while blockAt is lying about what's there.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const fs = require("fs");
const path = require("path");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "totp_bot",
  version: "1.20.4",
  auth: "offline",
});

bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });

function waitForChatMatch(regex, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      bot.removeListener("message", handler);
      reject(new Error(`timeout waiting for /${regex.source}/`));
    }, timeoutMs);
    function handler(m) {
      const s = m.toString();
      const match = s.match(regex);
      if (match) {
        clearTimeout(timer);
        bot.removeListener("message", handler);
        resolve(match);
      }
    }
    bot.on("message", handler);
  });
}

bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));

async function countAt(pos, pattern) {
  await bot.creative.flyTo(pos);
  await sleep(300);
  bot.chat("//pos1");
  await waitForChatMatch(/First position set/, 8000);
  bot.chat("//pos2");
  await waitForChatMatch(/Second position set/, 8000);
  bot.chat(`//count ${pattern}`);
  const m = await waitForChatMatch(/Counted (\d+) block/, 15000);
  return parseInt(m[1], 10);
}

// Default pasted state is lit=false (cosmetics.py sets it explicitly), so a
// count of 1 for the bare pattern means "still default" (unlit); 0 means
// the block is in some other state (lit=true), given we trust structurally
// that this position holds a lamp.
async function isLampLit(pos) {
  const n = await countAt(pos, "minecraft:redstone_lamp");
  return n === 0;
}

// ANCHOR is the conceptual "local (0,0,0)" point: pin world positions are
// always ANCHOR + local (local coordinates as captured in pins.txt, in the
// original pre-trim region-relative frame).
const ANCHOR = new Vec3(0, 70, 0);

// schem.Schematic.save() trims to the tight bounding box of non-air blocks,
// so the player must stand at ANCHOR + shift (not ANCHOR) for the pasted
// file's own internal (already-trimmed) coordinates to land such that
// ANCHOR + local_raw still holds -- see scripts_litematic_to_schem.py.
let PASTE_POS = ANCHOR;
try {
  const shift = JSON.parse(fs.readFileSync(path.join(__dirname, "shift.json"), "utf8"));
  PASTE_POS = ANCHOR.offset(shift.shift_x, shift.shift_y, shift.shift_z);
  console.log(`[shift] applying ${JSON.stringify(shift)}, paste position ${PASTE_POS}`);
} catch (e) {
  console.log(`[shift] no shift.json found, pasting at raw anchor (${e.message})`);
}

function isInputPinName(name) {
  return name === "rst" || name === "start" || name.startsWith("counter[");
}

function loadPins() {
  // Each pins.txt row is the I/O REPEATER's cell (x,y,z) plus the outward
  // normal (nx,nz). Per cosmetics.py:place_io_fixtures: an OUTPUT lamp sits
  // at (x+nx, y, z+nz); an INPUT's actual lever sits one block ABOVE that
  // same point (a stone support is placed at (x+nx,y,z+nz), the lever on
  // top of it, face=floor) -- so inputs need +1 on y, outputs don't.
  const file = process.env.PINS_FILE || path.join(__dirname, "..", "pins.txt");
  const pins = {};
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const t = line.trim();
    if (!t) continue;
    const [name, x, y, z, nx, nz] = t.split(/\s+/);
    const fx = parseInt(x, 10) + parseInt(nx, 10);
    const fz = parseInt(z, 10) + parseInt(nz, 10);
    const fy = parseInt(y, 10) + (isInputPinName(name) ? 1 : 0);
    pins[name] = ANCHOR.offset(fx, fy, fz);
  }
  return pins;
}

const COUNTER = parseInt(process.argv[2] || "0", 10);
const EXPECT = parseInt(process.argv[3] || "755224", 10);
const SCHEM = process.argv[4] || "totp_core_corner.schem";

bot.once("login", async () => {
  console.log("[login] ok");
  const pins = loadPins();
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(PASTE_POS);
  console.log(`[pos] ${bot.entity.position}`);

  console.log(`[load] //load ${SCHEM}`);
  bot.chat(`//load ${SCHEM}`);
  await sleep(3000);
  console.log("[paste] //paste");
  bot.chat("//paste");
  await sleep(3000);

  // redpiler previously panicked ("Exceeded the maximum number of default
  // inputs 255") on wire stacked directly on wire, which only a paste can
  // produce -- fixed locally with benburk/MCHPRS PR #2 applied to our own
  // mchprs build. See README.md "Why it was slow, and what got fixed".
  console.log("[redpiler] /redpiler compile");
  bot.chat("/redpiler compile");
  await sleep(10000);

  // pulse rst to force a known IDLE state (activateBlock is position-based
  // and server-validated -- see header comment -- so this works regardless
  // of what the client's chunk cache thinks is at pins["rst"])
  console.log("[rst] pulsing reset");
  bot.activateBlock(bot.blockAt(pins["rst"]));
  await sleep(2000);
  bot.activateBlock(bot.blockAt(pins["rst"]));
  await sleep(1000);

  console.log(`[counter] setting counter=${COUNTER}`);
  for (let i = 0; i < 32; i++) {
    if ((COUNTER >>> i) & 1) {
      bot.activateBlock(bot.blockAt(pins[`counter[${i}]`]));
      await sleep(150);
    }
  }

  console.log("[start] pulsing start");
  bot.activateBlock(bot.blockAt(pins["start"]));
  await sleep(2000);

  console.log("[poll] waiting for done lamp (server-side //count checks)...");
  const deadline = Date.now() + 60 * 60 * 1000; // 60 min ceiling
  let doneSeen = false;
  while (Date.now() < deadline) {
    const lit = await isLampLit(pins["done"]);
    console.log(`[poll] done lit=${lit} (t+${Math.round((60*60*1000 - (deadline - Date.now()))/1000)}s)`);
    if (lit) { doneSeen = true; break; }
    await sleep(30000);
  }

  if (!doneSeen) {
    console.log("[result] TIMED OUT waiting for done");
  } else {
    let code = 0;
    for (let i = 0; i < 20; i++) {
      const lit = await isLampLit(pins[`code[${i}]`]);
      if (lit) code |= (1 << i);
      console.log(`[bit] code[${i}]=${lit ? 1 : 0}`);
    }
    console.log(`[result] done=true code=${code} expected=${EXPECT} match=${code === EXPECT}`);
  }

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
