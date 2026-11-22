const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: 25565, username: "totp_bot_inspect", version: "1.20.4", auth: "offline" });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  // rst lever, computed from first_pos=(400,8,277) + pins.txt rst fixture+y+1
  const rstLever = new Vec3(400 + 39, 8 + 196, 277 + 223); // first_pos + (rst.x+nx, rst.y+1, rst.z+nz)
  await bot.creative.flyTo(rstLever.offset(1, 0, 0)); // stand nearby, look at it
  await bot.lookAt(rstLever.offset(0.5, 0.5, 0.5));
  await sleep(500);
  bot.chat("/redpiler inspect");
  await sleep(2000);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
