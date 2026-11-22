// Isolates whether our own //count-based polling interferes with live redpiler
// progress: loads, drives rst/start, then sleeps with ZERO further commands for
// a fixed window well beyond the ~25.6s theoretical completion time at 100,000
// rtps, then does exactly ONE read at the end.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "repro_nopoll", version: "1.20.4", auth: "offline" });
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

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps 100000");
  await sleep(500);
  await bot.creative.flyTo(new Vec3(100, 70, 100));

  bot.chat("/load repro_counter.litematic -c");
  const loadMsg = await waitForChatMatch(/Reloaded .* at (-?\d+), (-?\d+), (-?\d+)/, 60000);
  const firstPos = new Vec3(parseInt(loadMsg[1], 10), parseInt(loadMsg[2], 10), parseInt(loadMsg[3], 10));
  console.log(`[load] first_pos = ${firstPos}`);
  await sleep(2000);

  bot.chat("/lever rst on");
  await sleep(1000);
  bot.chat("/lever rst off");
  await sleep(1000);
  bot.chat("/lever start on");
  console.log("[start] on -- now sleeping 60s with ZERO further commands");

  const t0 = Date.now();
  await sleep(60000);
  console.log(`[check] t+${Math.round((Date.now() - t0) / 1000)}s -- now reading done via inspect`);

  const donePos = firstPos.offset(8, 5, 0);
  await bot.creative.flyTo(donePos.offset(1, 0, 0));
  await sleep(300);
  bot.chat("//pos1");
  await waitForChatMatch(/First position set/, 10000);
  bot.chat("//pos2");
  await waitForChatMatch(/Second position set/, 10000);
  bot.chat("//count minecraft:redstone_lamp");
  const m = await waitForChatMatch(/Counted (\d+) block/, 15000);
  const count = parseInt(m[1], 10);
  console.log(`[result] done=${count === 0} (count=${count}, 0 means lit)`);

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
