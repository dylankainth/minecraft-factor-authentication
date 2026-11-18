// Read S1/S2/LAMP repeatedly (stable as stone/lamp with no toggling,
// per xor_v2_retry_probe.js), then toggle lever A exactly once and
// watch whether S1 flips from stone to air at that exact moment --
// pins down whether this is a redstone-simulation-triggered corruption
// bug (not a paste/read bug at all).
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "totp_bot",
  version: "1.20.4",
  auth: "offline",
});

bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });

function chatAndWait(cmd, matchSubstr, timeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    const onMsg = (m) => {
      const text = m.toString();
      if (text.includes(matchSubstr)) {
        bot.removeListener("message", onMsg);
        clearTimeout(timer);
        resolve(text);
      }
    };
    const timer = setTimeout(() => {
      bot.removeListener("message", onMsg);
      reject(new Error(`Timed out waiting for "${matchSubstr}" after "${cmd}"`));
    }, timeoutMs);
    bot.on("message", onMsg);
    bot.chat(cmd);
  });
}

const ANCHOR = new Vec3(600, 70, 600);
const HANDLE = { x: 16, y: 2, z: 10 };
const rel = (x, y, z) => ANCHOR.offset(x - HANDLE.x, y - HANDLE.y, z - HANDLE.z);
const LEVER_A = rel(0, 1, 0);
const S1 = rel(18, 2, 8);

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);

  await chatAndWait("//load xor_compact_v2.schem", "loaded to your clipboard");
  await chatAndWait("//paste", "clipboard was pasted");
  await sleep(3000);

  await bot.creative.flyTo(S1.offset(0, 2, 0));
  await sleep(300);
  console.log(`BEFORE any toggle: S1 = ${bot.blockAt(S1)?.name}`);

  console.log(">>> toggling LEVER_A now <<<");
  await bot.creative.flyTo(LEVER_A.offset(0, 2, 0));
  await sleep(300);
  bot.activateBlock(bot.blockAt(LEVER_A));

  for (let t = 0; t < 10; t++) {
    await sleep(500);
    await bot.creative.flyTo(S1.offset(0, 2, 0));
    await sleep(200);
    console.log(`  t=${(t + 1) * 0.7}s after toggle: S1 = ${bot.blockAt(S1)?.name}`);
  }

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
