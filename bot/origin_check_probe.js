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

bot.once("login", async () => {
  console.log("[login] ok, default spawn pos:", bot.entity.position);
  await sleep(2000);
  console.log(`[chunk at spawn] ${bot.blockAt(bot.entity.position)}`);
  console.log(`[chunk at 320,90,320] ${bot.blockAt(new Vec3(320, 90, 320))}`);
  console.log(`[chunk at 0,64,0] ${bot.blockAt(new Vec3(0, 64, 0))}`);
  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
