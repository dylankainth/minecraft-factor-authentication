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

function dump(label, pos) {
  const b = bot.blockAt(pos);
  if (!b) { console.log(`[block] ${label} @ ${pos}: NULL`); return; }
  console.log(`[block] ${label} @ ${pos}: name=${b.name} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(3000);
  const spawn = bot.entity.position.floored();
  const ANCHOR = spawn.offset(5, 0, 5);
  const LEVER = ANCHOR.offset(0, 1, 0);
  const REP = ANCHOR.offset(2, 1, 0);
  const LAST_DUST = ANCHOR.offset(7, 1, 0);
  const LAMP = ANCHOR.offset(8, 1, 0);

  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat(`/tp ${ANCHOR.x} ${ANCHOR.y} ${ANCHOR.z}`);
  await sleep(1000);
  bot.creative.startFlying();
  for (let i = 0; i < 10; i++) {
    bot.entity.position.set(ANCHOR.x, ANCHOR.y, ANCHOR.z);
    bot.entity.velocity.set(0, 0, 0);
    await sleep(100);
  }

  bot.chat("//load repeater_then_dust_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const toggle = () => {
    const b = bot.blockAt(LEVER);
    if (!b) { console.log("[toggle] null"); return; }
    bot.activateBlock(b);
  };
  const WAIT = 4000;

  console.log("--- initial (off) ---");
  dump("LEVER", LEVER); dump("REP", REP); dump("LAST_DUST", LAST_DUST); dump("LAMP", LAMP);

  toggle(); await sleep(WAIT);
  console.log("--- toggle 1: ON ---");
  dump("LEVER", LEVER); dump("REP", REP); dump("LAST_DUST", LAST_DUST); dump("LAMP", LAMP);

  toggle(); await sleep(WAIT);
  console.log("--- toggle 2: OFF (does LAST_DUST drop to 0?) ---");
  dump("LEVER", LEVER); dump("REP", REP); dump("LAST_DUST", LAST_DUST); dump("LAMP", LAMP);

  toggle(); await sleep(WAIT);
  console.log("--- toggle 3: ON again ---");
  dump("LEVER", LEVER); dump("REP", REP); dump("LAST_DUST", LAST_DUST); dump("LAMP", LAMP);

  toggle(); await sleep(WAIT);
  console.log("--- toggle 4: OFF again ---");
  dump("LEVER", LEVER); dump("REP", REP); dump("LAST_DUST", LAST_DUST); dump("LAMP", LAMP);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
