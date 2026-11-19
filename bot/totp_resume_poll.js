const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs", port: 25565, username: "totp_bot", version: "1.20.4", auth: "offline" });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });

function waitForChatMatch(regex, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { bot.removeListener("message", handler); reject(new Error("timeout")); }, timeoutMs);
    function handler(m) {
      const s = m.toString();
      const match = s.match(regex);
      if (match) { clearTimeout(timer); bot.removeListener("message", handler); resolve(match); }
    }
    bot.on("message", handler);
  });
}
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
async function isLampLit(pos) {
  const n = await countAt(pos, "minecraft:redstone_lamp");
  return n === 0;
}

const ANCHOR = new Vec3(0, 70, 0);
const donePos = ANCHOR.offset(19, 183, 0);
const codePins = [];
for (let i = 0; i < 20; i++) codePins.push(ANCHOR.offset(114, 0, 0)); // placeholder; filled from pins.txt below

const fs = require("fs");
const path = require("path");
function loadCodePins() {
  const file = process.env.PINS_FILE || path.join(__dirname, "..", "pins.txt");
  const pins = {};
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const t = line.trim();
    if (!t) continue;
    const [name, x, y, z, nx, nz] = t.split(/\s+/);
    pins[name] = ANCHOR.offset(parseInt(x,10)+parseInt(nx,10), parseInt(y,10), parseInt(z,10)+parseInt(nz,10));
  }
  return pins;
}

bot.once("login", async () => {
  console.log("[login] resumed");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  const pins = loadCodePins();

  console.log("[poll] resuming done-lamp poll (no inputs touched)...");
  const startTime = Date.now();
  const deadline = startTime + 55 * 60 * 1000;
  let doneSeen = false;
  while (Date.now() < deadline) {
    const lit = await isLampLit(donePos);
    console.log(`[poll] done lit=${lit} (t+${Math.round((Date.now()-startTime)/1000)}s since resume)`);
    if (lit) { doneSeen = true; break; }
    await sleep(30000);
  }

  if (!doneSeen) {
    console.log("[result] TIMED OUT waiting for done (since resume)");
  } else {
    let code = 0;
    for (let i = 0; i < 20; i++) {
      const lit = await isLampLit(pins[`code[${i}]`]);
      if (lit) code |= (1 << i);
      console.log(`[bit] code[${i}]=${lit ? 1 : 0}`);
    }
    console.log(`[result] done=true code=${code} expected=755224 match=${code === 755224}`);
  }
  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
