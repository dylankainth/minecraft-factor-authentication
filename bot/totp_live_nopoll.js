// Breakthrough from the reproducer investigation: repeatedly polling via
// //pos1 + //pos2 + //count WorldEdit commands while redpiler is actively
// ticking appears to interfere with (likely resets) live progress -- the
// tiny reproducer completed in <=60s with ZERO polling, after never
// finishing within 50 minutes WHEN POLLED every few seconds. This script
// drives the real totp_core the same poll-free way: load, drive inputs,
// sleep a fixed generous window with ZERO further commands, then read
// exactly once at the end.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs_fork_server",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "totp_nopoll",
  version: "1.20.4",
  auth: "offline",
});
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));

function waitForChatMatch(regex, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`timeout waiting for /${regex.source}/`)), timeoutMs);
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

const COUNTER = parseInt(process.argv[2] || "0", 10);
const EXPECT = parseInt(process.argv[3] || "755224", 10);
const WAIT_SECONDS = parseInt(process.argv[4] || "120", 10);

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps 100000");
  await sleep(500);

  await bot.creative.flyTo(new Vec3(100, 70, 100));

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

  await sleep(3000); // let redpiler compile settle

  console.log("[rst] on");
  bot.chat("/lever rst on");
  await sleep(1000);
  console.log("[rst] off");
  bot.chat("/lever rst off");
  await sleep(1000);

  console.log(`[counter] setting counter=${COUNTER} via /lever`);
  for (let i = 0; i < 32; i++) {
    const bitVal = (COUNTER >>> i) & 1;
    if (bitVal) {
      bot.chat(`/lever counter[${i}] on`);
      await sleep(50);
    }
  }
  await sleep(1000);

  console.log("[start] on -- now sleeping with ZERO further commands");
  bot.chat("/lever start on");

  const t0 = Date.now();
  await sleep(WAIT_SECONDS * 1000);
  console.log(`[check] t+${Math.round((Date.now() - t0) / 1000)}s -- reading outputs now (single read)`);

  async function countAt(pos, pattern) {
    await bot.creative.flyTo(pos);
    await sleep(200);
    bot.chat("//pos1");
    await waitForChatMatch(/First position set/, 10000);
    bot.chat("//pos2");
    await waitForChatMatch(/Second position set/, 10000);
    bot.chat(`//count ${pattern}`);
    const m = await waitForChatMatch(/Counted (\d+) block/, 15000);
    return parseInt(m[1], 10);
  }
  async function isLampLit(pos) {
    return (await countAt(pos, "minecraft:redstone_lamp")) === 0;
  }

  const doneLit = await isLampLit(outputPos("done"));
  console.log(`[result] done=${doneLit}`);
  if (doneLit) {
    let code = 0;
    for (let i = 0; i < 20; i++) {
      const lit = await isLampLit(outputPos(`code[${i}]`));
      if (lit) code |= (1 << i);
    }
    console.log(`[result] code=${code} expected=${EXPECT} match=${code === EXPECT} total_time=${Math.round((Date.now() - t0) / 1000)}s`);
  } else {
    console.log("[result] NOT DONE after single-read window");
  }

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
