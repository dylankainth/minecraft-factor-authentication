// Reconnects to the fork server and resumes polling the already-loaded,
// already-triggered totp_core build without touching rst/counter/start --
// the plot only ticks while a player is present, so the previous run's
// progress should still be there, just paused.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs_fork_server",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "totp_bot_live",
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

async function countAt(pos, pattern, attempt = 0) {
  try {
    await bot.creative.flyTo(pos);
    await sleep(300);
    bot.chat("//pos1");
    await waitForChatMatch(/First position set/, 10000);
    bot.chat("//pos2");
    await waitForChatMatch(/Second position set/, 10000);
    bot.chat(`//count ${pattern}`);
    const m = await waitForChatMatch(/Counted (\d+) block/, 15000);
    return parseInt(m[1], 10);
  } catch (e) {
    if (attempt >= 3) throw e;
    console.log(`[countAt] retry ${attempt + 1} after: ${e.message}`);
    await sleep(2000);
    return countAt(pos, pattern, attempt + 1);
  }
}
async function isLampLit(pos) {
  return (await countAt(pos, "minecraft:redstone_lamp")) === 0;
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

const EXPECT = parseInt(process.argv[2] || "755224", 10);
const FIRST_POS = new Vec3(
  parseInt(process.argv[3] || "400", 10),
  parseInt(process.argv[4] || "8", 10),
  parseInt(process.argv[5] || "277", 10)
);

bot.once("login", async () => {
  console.log("[login] ok (resuming, not touching inputs)");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(3000); // let the connection fully settle into the plot before anything else

  const pinsRaw = loadPinsRaw();
  function outputPos(name) {
    const p = pinsRaw[name];
    return FIRST_POS.offset(p.x + p.nx, p.y, p.z + p.nz);
  }

  console.log(`[poll] resuming at first_pos=${FIRST_POS}, waiting for done lamp...`);
  const donePos = outputPos("done");
  const t0 = Date.now();
  const deadline = t0 + 50 * 60 * 1000;
  let doneSeen = false;
  while (Date.now() < deadline) {
    const lit = await isLampLit(donePos);
    console.log(`[poll] done lit=${lit} (t+${Math.round((Date.now() - t0) / 1000)}s since resume)`);
    if (lit) { doneSeen = true; break; }
    await sleep(10000);
  }

  if (!doneSeen) {
    console.log("[result] TIMED OUT waiting for done (since resume)");
  } else {
    let code = 0;
    for (let i = 0; i < 20; i++) {
      const lit = await isLampLit(outputPos(`code[${i}]`));
      if (lit) code |= (1 << i);
    }
    console.log(`[result] done=true code=${code} expected=${EXPECT} match=${code === EXPECT}`);
  }

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
