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

const ANCHOR = new Vec3(320, 90, 320);
const LEVER = ANCHOR.offset(0, 1, 0);
const DUST = ANCHOR.offset(1, 1, 0);
const LAMP = ANCHOR.offset(2, 1, 0);

function dump(label, pos) {
  const b = bot.blockAt(pos);
  console.log(`[block] ${label} @ ${pos}: name=${b.name} stateId=${b.stateId} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos] ${bot.entity.position}`);

  bot.chat("//load dust_test.schem");
  await sleep(1000);
  bot.chat("//paste");
  await sleep(1500);

  console.log("--- BEFORE toggling lever ---");
  dump("LEVER", LEVER); dump("DUST", DUST); dump("LAMP", LAMP);

  bot.activateBlock(bot.blockAt(LEVER));
  await sleep(1500);

  console.log("--- AFTER toggling lever ---");
  dump("LEVER", LEVER); dump("DUST", DUST); dump("LAMP", LAMP);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
