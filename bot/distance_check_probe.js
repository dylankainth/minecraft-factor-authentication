// Re-test convergence_scale_test.schem (already proven: SF at offset 3
// reads correctly) but ALSO check a padding block far from the anchor
// (offset ~150) to see if "far from paste anchor" is the real
// discriminator, independent of chunk-loading-on-read (already ruled
// out -- we fly directly adjacent every time).
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

const ANCHOR = new Vec3(810, 70, 810);

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos before paste] ${bot.entity.position}`);

  await chatAndWait("//load convergence_scale_test.schem", "loaded to your clipboard");
  await chatAndWait("//paste", "clipboard was pasted");
  await sleep(2000);

  // offsets along the padding lane at z=20 (build-local), many distances
  const checks = [3, 8, 16, 24, 32, 50, 80, 120, 160, 199];
  for (const dx of checks) {
    const p = ANCHOR.offset(dx, 1, 20);
    await bot.creative.flyTo(p.offset(0, 2, 0));
    await sleep(250);
    const b = bot.blockAt(p);
    console.log(`dx=${dx}: (${p.x},${p.y},${p.z}) = ${b ? b.name : "NULL"}`);
  }

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
