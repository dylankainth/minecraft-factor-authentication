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

const ANCHOR = new Vec3(1700, 90, 1700);
const LEVER = ANCHOR.offset(0, 1, 0);
const LAMP = ANCHOR.offset(51, 1, 0);

function dump(label, pos) {
  const b = bot.blockAt(pos);
  console.log(`[block] ${label} @ ${pos}: name=${b.name} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);

  bot.chat("//load long_chain_test.schem");
  await sleep(2500);
  bot.chat("//paste");
  await sleep(4000);

  const toggle = () => bot.activateBlock(bot.blockAt(LEVER));

  console.log("--- initial (lever off) ---");
  dump("LEVER", LEVER); dump("LAMP", LAMP);

  toggle(); await sleep(10000);
  console.log("--- after toggle 1 + 10s wait (lever ON, lamp should light) ---");
  dump("LEVER", LEVER); dump("LAMP", LAMP);

  toggle(); await sleep(10000);
  console.log("--- after toggle 2 + 10s wait (lever OFF, lamp should go dark) ---");
  dump("LEVER", LEVER); dump("LAMP", LAMP);

  toggle(); await sleep(10000);
  console.log("--- after toggle 3 + 10s wait (lever ON again, lamp should relight) ---");
  dump("LEVER", LEVER); dump("LAMP", LAMP);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
