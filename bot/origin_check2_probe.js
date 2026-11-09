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
  console.log("[login] ok");
  await sleep(3000);
  const p = bot.entity.position;
  console.log(`[pos after 3s] ${p}`);
  console.log(`[blockAt own position, floored] ${bot.blockAt(p.floored())}`);
  console.log(`[blockAt 5 below own position] ${bot.blockAt(p.floored().offset(0, -5, 0))}`);

  bot.chat("/gamemode creative");
  await sleep(500);
  // small nearby move, not a huge jump
  const near = p.floored().offset(5, 0, 5);
  bot.chat(`/tp ${near.x} ${near.y} ${near.z}`);
  await sleep(3000);
  console.log(`[pos after small tp] ${bot.entity.position}`);
  console.log(`[blockAt near tp target] ${bot.blockAt(near)}`);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
