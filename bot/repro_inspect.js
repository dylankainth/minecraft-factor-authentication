const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "repro_inspect", version: "1.20.4", auth: "offline" });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(1000);
  // first_pos passed as argv[1..3]
  const firstPos = new Vec3(parseInt(process.argv[2], 10), parseInt(process.argv[3], 10), parseInt(process.argv[4], 10));
  const donePos = firstPos.offset(8, 5, 0);
  await bot.creative.flyTo(donePos.offset(1, 0, 0));
  await bot.lookAt(donePos.offset(0.5, 0.5, 0.5));
  await sleep(500);
  for (let i = 0; i < 5; i++) {
    bot.chat("/redpiler inspect");
    await sleep(3000);
  }
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
