// Directly inspects the rst and start LEVER blocks themselves (not derived
// registers) via /redpiler inspect, using the same pins.txt convention
// (lever = (x+nx, y+1, z+nz)) already proven correct throughout this
// project. Confirms ground truth: is rst really off and start really on,
// as far as the compiled redpiler graph itself is concerned (not just the
// chat confirmation, which only reflects what we last told it to set).
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bot = mineflayer.createBot({ host: process.env.MC_HOST || "mchprs_fork_server", port: parseInt(process.env.MC_PORT || "25565", 10), username: "totp_levers", version: "1.20.4", auth: "offline" });
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));

const FIRST_POS = new Vec3(
  parseInt(process.argv[2] || "400", 10),
  parseInt(process.argv[3] || "8", 10),
  parseInt(process.argv[4] || "277", 10)
);
// From pins.txt: rst 39 195 222 0 1 -> lever = (x+nx, y+1, z+nz)
const RST_LEVER = [39, 196, 223];
const START_LEVER = [21, 191, 223];

async function inspectAt(bot, pos, label) {
  await bot.creative.flyTo(pos.offset(1, 0, 0));
  await bot.lookAt(pos.offset(0.5, 0.5, 0.5));
  await sleep(300);
  console.log(`[inspect] ${label} at ${pos}`);
  bot.chat("/redpiler inspect");
  await sleep(500);
}

bot.once("login", async () => {
  console.log("[login] ok -- resuming, checking lever ground truth");
  await sleep(1500);
  bot.chat("/gamemode creative");
  await sleep(500);

  await inspectAt(bot, FIRST_POS.offset(...RST_LEVER), "rst lever");
  await inspectAt(bot, FIRST_POS.offset(...START_LEVER), "start lever");

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
});
