// Directly inspects several points along the clock generator's own litematic
// region (a long repeater-delay-line loop, found via litemapy scanning the
// "clock" region of build/totp_core.litematic directly -- no netlist
// cross-referencing, so no stale-artifact risk). Samples repeatedly with
// real wall-clock gaps to see whether the oscillator is actually toggling.
// Usage: totp_check_oscillator.js <load|resume> <firstX> <firstY> <firstZ> <rounds> <gapMs>
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "totp_osc", version: "1.20.4", auth: "offline" });
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

const MODE = process.argv[2] || "load"; // "load" or "resume"
const ARG_FIRST = new Vec3(
  parseInt(process.argv[3] || "400", 10),
  parseInt(process.argv[4] || "8", 10),
  parseInt(process.argv[5] || "277", 10)
);
const ROUNDS = parseInt(process.argv[6] || "4", 10);
const GAP_MS = parseInt(process.argv[7] || "4000", 10);

// World-local offsets of a few redstone_wire cells along the oscillator loop,
// found directly from build/totp_core.litematic's "clock" region.
const WIRE_OFFSETS = [
  [121, 128, 223],
  [121, 128, 350],
  [124, 128, 467],
];
const approaches = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, -1], [1, 1, 0]];

async function inspectAt(bot, pos, label) {
  for (const a of approaches) {
    await bot.creative.flyTo(pos.offset(a[0], a[1], a[2]));
    await bot.lookAt(pos.offset(0.5, 0.5, 0.5));
    await sleep(250);
    console.log(`[inspect] ${label} approach=${a} at ${pos} t=${Date.now()}`);
    bot.chat("/redpiler inspect");
    await sleep(400);
  }
}

bot.once("login", async () => {
  console.log("[login] ok -- checking the oscillator's own wire chain");
  await sleep(1500);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps 1000000000");
  await sleep(500);

  let firstPos = ARG_FIRST;
  if (MODE === "load") {
    await bot.creative.flyTo(new Vec3(100, 70, 100));
    bot.chat("/load totp_core.litematic -c");
    const loadMsg = await waitForChatMatch(/Reloaded .* at (-?\d+), (-?\d+), (-?\d+)/, 60000);
    firstPos = new Vec3(parseInt(loadMsg[1], 10), parseInt(loadMsg[2], 10), parseInt(loadMsg[3], 10));
    console.log(`[load] first_pos = ${firstPos}`);
    await sleep(3000);
  } else {
    console.log(`[resume] using first_pos = ${firstPos}`);
  }

  for (let r = 0; r < ROUNDS; r++) {
    console.log(`[round ${r}] t=${Date.now()}`);
    for (let i = 0; i < WIRE_OFFSETS.length; i++) {
      const pos = firstPos.offset(WIRE_OFFSETS[i][0], WIRE_OFFSETS[i][1], WIRE_OFFSETS[i][2]);
      await inspectAt(bot, pos, `wire[${i}]`);
    }
    await sleep(GAP_MS);
  }

  console.log(`[first_pos_for_resume] ${firstPos.x} ${firstPos.y} ${firstPos.z}`);
  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
