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

const ANCHOR = new Vec3(700, 70, 700);
const PTS = {
  LEVER: ANCHOR.offset(0, 0, 0),
  STONE1: ANCHOR.offset(1, 0, 0),
  STONE2: ANCHOR.offset(1, 1, 0),
  STONE3: ANCHOR.offset(2, 0, 0),
  LAMP: ANCHOR.offset(3, 0, 0),
  TORCH: ANCHOR.offset(4, 0, 0),
};

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos before paste] ${bot.entity.position}`);

  await chatAndWait("//load stone_isolation_test.schem", "loaded to your clipboard");
  await chatAndWait("//paste", "clipboard was pasted");
  await sleep(2000);

  for (const [k, p] of Object.entries(PTS)) {
    await bot.creative.flyTo(p.offset(0, 2, 0));
    await sleep(400);
    const b = bot.blockAt(p);
    console.log(`[block] ${k} @ (${p.x},${p.y},${p.z}): ${b ? b.name : "NULL"} ${b && b.getProperties ? JSON.stringify(b.getProperties()) : ""}`);
  }

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
