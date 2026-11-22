// Reconnects after the drive bot disconnected mid-wait, resumes ticking (plot
// only ticks with a player present) by just being connected, waits a bit more,
// then does exactly ONE read -- no polling loop, per the no-interference
// finding from the reproducer investigation.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "totp_resume", version: "1.20.4", auth: "offline" });
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

const FIRST_POS = new Vec3(
  parseInt(process.argv[2] || "400", 10),
  parseInt(process.argv[3] || "8", 10),
  parseInt(process.argv[4] || "277", 10)
);
const WAIT_SECONDS = parseInt(process.argv[5] || "60", 10);
const EXPECT = parseInt(process.argv[6] || "755224", 10);

bot.once("login", async () => {
  console.log("[login] ok -- resuming, no re-drive of inputs");
  await sleep(2000);
  bot.chat("/gamemode creative");

  const pinsRaw = loadPinsRaw();
  function outputPos(name) {
    const p = pinsRaw[name];
    return FIRST_POS.offset(p.x + p.nx, p.y, p.z + p.nz);
  }

  console.log(`[wait] sleeping ${WAIT_SECONDS}s with no further commands`);
  await sleep(WAIT_SECONDS * 1000);

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
    console.log(`[result] code=${code} expected=${EXPECT} match=${code === EXPECT}`);
  } else {
    console.log("[result] NOT DONE yet");
  }

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
