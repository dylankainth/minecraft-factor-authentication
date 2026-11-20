// Live, in-game demo on the saucefishman/MCHPRS fork: uses the fork's native
// `/load <name>.litematic -c` (which does a real block-update pass and
// compiles redpiler immediately) instead of WorldEdit's `//load`+`//paste`
// (which never schedules a tick at all -- see README.md's root-cause
// writeup). Drives inputs via `/lever <name> [on|off|toggle]` using the
// names in totp_core.server.json, and reads outputs via the same
// //count-based trick established earlier (still needed for reads: /lever
// only addresses inputs by name, outputs still need position-based //count).
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

async function countAt(pos, pattern) {
  await bot.creative.flyTo(pos);
  await sleep(200);
  bot.chat("//pos1");
  await waitForChatMatch(/First position set/, 8000);
  bot.chat("//pos2");
  await waitForChatMatch(/Second position set/, 8000);
  bot.chat(`//count ${pattern}`);
  const m = await waitForChatMatch(/Counted (\d+) block/, 15000);
  return parseInt(m[1], 10);
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

const COUNTER = parseInt(process.argv[2] || "0", 10);
const EXPECT = parseInt(process.argv[3] || "755224", 10);

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);

  const STAND = new Vec3(100, 70, 100); // well inside plot (0,0)
  await bot.creative.flyTo(STAND);
  console.log(`[pos] ${bot.entity.position}`);

  console.log("[load] /load totp_core.litematic -c");
  bot.chat("/load totp_core.litematic -c");
  const loadMsg = await waitForChatMatch(/Reloaded .* at (-?\d+), (-?\d+), (-?\d+)/, 60000);
  const firstPos = new Vec3(parseInt(loadMsg[1], 10), parseInt(loadMsg[2], 10), parseInt(loadMsg[3], 10));
  console.log(`[load] first_pos = ${firstPos}`);

  const pinsRaw = loadPinsRaw();
  function outputPos(name) {
    const p = pinsRaw[name];
    return firstPos.offset(p.x + p.nx, p.y, p.z + p.nz);
  }

  await sleep(5000); // let redpiler compile settle

  console.log("[rst] driving via /lever");
  bot.chat("/lever rst on");
  await sleep(10000); // generous wall-clock settle -- no direct tick-count
  bot.chat("/lever rst off");                       // control live, unlike headless's "settle N"
  await sleep(10000);

  console.log(`[counter] setting counter=${COUNTER} via /lever`);
  for (let i = 0; i < 32; i++) {
    const bitVal = (COUNTER >>> i) & 1;
    bot.chat(`/lever counter[${i}] ${bitVal ? "on" : "off"}`);
    await sleep(50);
  }
  await sleep(10000);

  console.log("[start] /lever start on");
  bot.chat("/lever start on");

  console.log("[poll] waiting for done lamp...");
  const donePos = outputPos("done");
  const t0 = Date.now();
  const deadline = t0 + 50 * 60 * 1000;
  let doneSeen = false;
  while (Date.now() < deadline) {
    const lit = await isLampLit(donePos);
    console.log(`[poll] done lit=${lit} (t+${Math.round((Date.now() - t0) / 1000)}s)`);
    if (lit) { doneSeen = true; break; }
    await sleep(3000);
  }

  if (!doneSeen) {
    console.log("[result] TIMED OUT waiting for done");
  } else {
    let code = 0;
    for (let i = 0; i < 20; i++) {
      const lit = await isLampLit(outputPos(`code[${i}]`));
      if (lit) code |= (1 << i);
    }
    console.log(`[result] done=true code=${code} expected=${EXPECT} match=${code === EXPECT} total_time=${Math.round((Date.now() - t0) / 1000)}s`);
  }

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
