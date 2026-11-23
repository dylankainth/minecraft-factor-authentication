// Reads all 6 seven-segment digits (42 lamps) plus the 20 code[] bits off
// the live circuit using ONE persistent bot connection (no reconnect per
// lamp) -- same countAt/chatAndWait retry pattern as totp_live_all10.js.
// Usage: totp_read_seg_single.js <firstX> <firstY> <firstZ> <expectedCode>
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const FIRST_POS = new Vec3(
  parseInt(process.argv[2] || "400", 10),
  parseInt(process.argv[3] || "8", 10),
  parseInt(process.argv[4] || "277", 10)
);
const EXPECTED = process.argv[5] || "";

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs_fork_server",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "totp_segsingle",
  version: "1.20.4",
  auth: "offline",
  checkTimeoutInterval: 120000,
});
process.on("uncaughtException", (e) => console.error("[uncaughtException swallowed]", e.message));
process.on("unhandledRejection", (e) => console.error("[unhandledRejection swallowed]", e));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(1); });

function waitForChatMatch(regex, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      bot.removeListener("message", handler);
      reject(new Error(`timeout /${regex.source}/`));
    }, timeoutMs);
    function handler(m) {
      const match = m.toString().match(regex);
      if (match) { clearTimeout(timer); bot.removeListener("message", handler); resolve(match); }
    }
    bot.on("message", handler);
  });
}

function loadPinsRaw() {
  const fs = require("fs");
  const path = require("path");
  const file = process.env.PINS_FILE || path.join(__dirname, "pins.txt");
  const pins = {};
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const t = line.trim();
    if (!t) continue;
    const [name, x, y, z, nx, nz] = t.split(/\s+/);
    pins[name] = { x: parseInt(x, 10), y: parseInt(y, 10), z: parseInt(z, 10), nx: parseInt(nx, 10), nz: parseInt(nz, 10) };
  }
  return pins;
}
const pinsRaw = loadPinsRaw();
function outputPos(name) {
  const p = pinsRaw[name];
  // seg pins are a 3x3 lamp tile (_lamp_tile) with the anchor at the
  // lower-left corner; only the MIDDLE lamp (anchor + (1,1)) is actually
  // driven by the wire -- the rest of the tile is just decorative bulk.
  const tileOffset = name.startsWith("seg") ? 1 : 0;
  return FIRST_POS.offset(p.x + p.nx + tileOffset, p.y + tileOffset, p.z + p.nz);
}

async function countAt(pos, pattern, attempt = 0) {
  try {
    if (attempt > 0) {
      await bot.creative.flyTo(pos.offset(0, 3, 0));
      await sleep(200);
    }
    await bot.creative.flyTo(pos);
    await sleep(150);
    bot.chat("//pos1");
    await waitForChatMatch(/First position set/, 30000);
    bot.chat("//pos2");
    await waitForChatMatch(/Second position set/, 30000);
    bot.chat(`//count ${pattern}`);
    const m = await waitForChatMatch(/Counted (\d+) block/, 30000);
    return parseInt(m[1], 10);
  } catch (e) {
    if (attempt >= 10) throw e;
    console.log(`[retry] countAt ${pos} after: ${e.message}`);
    await sleep(2000);
    return countAt(pos, pattern, attempt + 1);
  }
}
async function isLampLit(pos) {
  return (await countAt(pos, "minecraft:redstone_lamp")) === 0;
}

const DIGIT_FROM_SEG = {
  "1111110": 0, "0110000": 1, "1101101": 2, "1111001": 3, "0110011": 4,
  "1011011": 5, "1011111": 6, "1110000": 7, "1111111": 8, "1111011": 9,
};

bot.once("login", async () => {
  try {
    console.log("[login] ok");
    await sleep(1000);
    bot.chat("/gamemode creative");
    await sleep(500);
    const firstTarget = outputPos("done");
    bot.chat(`/tp ${firstTarget.x} ${firstTarget.y} ${firstTarget.z}`);
    await sleep(1000);

    const doneLit = await isLampLit(outputPos("done"));
    let code = 0;
    for (let i = 0; i < 20; i++) {
      if (await isLampLit(outputPos(`code[${i}]`))) code |= (1 << i);
    }
    console.log(`[code] done=${doneLit} code=${code}`);

    let number = "";
    for (let digit = 5; digit >= 0; digit--) {
      let segBits = "";
      for (let s = 6; s >= 0; s--) {
        const lit = await isLampLit(outputPos(`seg${digit}[${s}]`));
        segBits += lit ? "1" : "0";
      }
      const d = DIGIT_FROM_SEG[segBits];
      console.log(`[digit] seg${digit} bits=${segBits} -> digit=${d}`);
      number += d === undefined ? "?" : String(d);
    }
    console.log(`[RESULT] display=${number} code=${code} expected=${EXPECTED}`);

    await sleep(300);
    bot.quit();
    setTimeout(() => process.exit(0), 1500);
  } catch (e) {
    console.error("[FATAL]", e);
    try { bot.quit(); } catch {}
    setTimeout(() => process.exit(1), 1500);
  }
});
