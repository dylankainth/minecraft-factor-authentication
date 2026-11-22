const mineflayer = require("mineflayer");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "rtps_check", version: "1.20.4", auth: "offline" });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(3000);
  bot.chat("/rtps");
  await sleep(5000);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
