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

const ANCHOR = new Vec3(2300, 90, 2300);
const LEVER = ANCHOR.offset(0, 1, 0);
const TURN = ANCHOR.offset(21, 1, 0);
const LAMP = ANCHOR.offset(21, 1, 20);

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
  await sleep(5000);

  bot.chat("//load turn_chain_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const toggle = () => bot.activateBlock(bot.blockAt(LEVER));
  const WAIT = 15000;

  console.log("--- initial (lever off) ---");
  dump("LEVER", LEVER); dump("TURN", TURN); dump("LAMP", LAMP);

  toggle(); await sleep(WAIT);
  console.log("--- toggle 1: ON (lamp should light) ---");
  dump("LEVER", LEVER); dump("TURN", TURN); dump("LAMP", LAMP);

  toggle(); await sleep(WAIT);
  console.log("--- toggle 2: OFF (lamp should go dark -- the falling edge through the turn) ---");
  dump("LEVER", LEVER); dump("TURN", TURN); dump("LAMP", LAMP);

  toggle(); await sleep(WAIT);
  console.log("--- toggle 3: ON again (lamp should relight) ---");
  dump("LEVER", LEVER); dump("TURN", TURN); dump("LAMP", LAMP);

  toggle(); await sleep(WAIT);
  console.log("--- toggle 4: OFF again (second falling edge, the one that failed in the XOR gate) ---");
  dump("LEVER", LEVER); dump("TURN", TURN); dump("LAMP", LAMP);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
