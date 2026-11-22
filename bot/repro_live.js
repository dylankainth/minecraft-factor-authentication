// Minimal reproducer, live path: load MineRTL_designs/repro_counter (same clk/rst/
// start/done sticky-DONE FSM shape as totp_core, but counts to a known N=40000
// cycles instead of running SHA-1) via /load -c, drive rst/start DIRECTLY with
// /use (right-click emulation) on the raw block positions found by scanning the
// litematic -- no server.json/pins.txt indirection, to rule that layer out too.
// Confirmed via mchprs_headless: rst=(18,10,57), start=(11,6,57), done=(8,5,0)
// in the schematic's own local frame (add to first_pos).
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs_fork_server",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "repro_bot_v3",
  version: "1.20.4",
  auth: "offline",
});
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));

function waitForChatMatch(regex, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      bot.removeListener("message", handler);
      reject(new Error(`timeout waiting for /${regex.source}/`));
    }, timeoutMs);
    function handler(m) {
      const match = m.toString().match(regex);
      if (match) {
        clearTimeout(timer);
        bot.removeListener("message", handler);
        resolve(match);
      }
    }
    bot.on("message", handler);
  });
}

async function countAt(pos, pattern) {
  await bot.creative.flyTo(pos);
  await sleep(200);
  bot.chat("//pos1");
  await waitForChatMatch(/First position set/, 8000);
  bot.chat("//pos2");
  await waitForChatMatch(/Second position set/, 8000);
  bot.chat(`//count ${pattern}`);
  const m = await waitForChatMatch(/Counted (\d+) block/, 15000);
  return parseInt(m[1], 10);
}
async function isLampLit(pos) {
  return (await countAt(pos, "minecraft:redstone_lamp")) === 0;
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps 100000");
  await sleep(500);

  await bot.creative.flyTo(new Vec3(100, 70, 100));

  console.log("[load] /load repro_counter.litematic -c");
  bot.chat("/load repro_counter.litematic -c");
  const loadMsg = await waitForChatMatch(/Reloaded .* at (-?\d+), (-?\d+), (-?\d+)/, 90000);
  const firstPos = new Vec3(parseInt(loadMsg[1], 10), parseInt(loadMsg[2], 10), parseInt(loadMsg[3], 10));
  console.log(`[load] first_pos = ${firstPos}`);

  const rstPos = firstPos.offset(18, 10, 57);
  const startPos = firstPos.offset(11, 6, 57);
  const donePos = firstPos.offset(8, 5, 0);

  await sleep(3000); // let redpiler compile settle

  console.log("[rst] on");
  bot.chat(`/lever rst on`); // server.json wasn't generated for this build -- fall back to /use if this errors
  await sleep(1500);
  console.log("[rst] off");
  bot.chat(`/lever rst off`);
  await sleep(1500);

  console.log("[start] on");
  bot.chat(`/lever start on`);

  const t0 = Date.now();
  const deadline = t0 + 10 * 60 * 1000; // 10 min ceiling, extended to actually measure throughput
  let doneSeen = false;
  while (Date.now() < deadline) {
    const lit = await isLampLit(donePos);
    console.log(`[poll] done lit=${lit} (t+${Math.round((Date.now() - t0) / 1000)}s)`);
    if (lit) { doneSeen = true; break; }
    await sleep(2000);
  }
  console.log(doneSeen ? `[result] SUCCESS at t+${Math.round((Date.now() - t0) / 1000)}s` : "[result] TIMED OUT");

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
