// Latch/reliability test: do step-landing dust cells latch power?
// Probe coords match build_latch_test.py (ANCHOR + build coord).
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

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(3000);
  const spawn = bot.entity.position.floored();
  console.log(`[spawn] ${spawn}`);
  const ANCHOR = spawn.offset(5, 0, 5);

  const PTS = {
    LEVER: ANCHOR.offset(1, 1, 1),   // build (0,1,0) -> +1 x, +1 z (schem normalization)
    LAMP1: ANCHOR.offset(6, 1, 2),   // build (5,1,1)
    LAMP2: ANCHOR.offset(7, 2, 0),   // build (6,2,-1) -> z+1 = 0
    LAMP3: ANCHOR.offset(0, 2, 7),   // build (-1,2,6) -> x+1=0, z+1=7
  };
  const dump = (label, pos) => {
    const b = bot.blockAt(pos);
    if (!b) { console.log(`[block] ${label} @ ${pos}: NULL`); return; }
    console.log(`[block] ${label} @ ${pos}: name=${b.name} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
  };
  const dumpAll = (label) => { console.log(`--- ${label} ---`); for (const [k, p] of Object.entries(PTS)) dump(k, p); };

  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  bot.chat(`/tp ${ANCHOR.x} ${ANCHOR.y} ${ANCHOR.z}`);
  await sleep(1000);
  bot.creative.startFlying();
  for (let i = 0; i < 10; i++) {
    bot.entity.position.set(ANCHOR.x, ANCHOR.y, ANCHOR.z);
    bot.entity.velocity.set(0, 0, 0);
    await sleep(100);
  }

  bot.chat("//load latch_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const click = () => bot.activateBlock(bot.blockAt(PTS.LEVER));
  const WAIT = 15000;

  // Warm-up: several full on/off cycles
  console.log("=== warm-up ===");
  for (let i = 0; i < 4; i++) {
    click(); await sleep(WAIT);
    click(); await sleep(WAIT);
  }

  dumpAll("start (lever should be off after warm-up, all lamps OFF)");

  click(); await sleep(WAIT);
  dumpAll("lever ON (all lamps ON)");

  click(); await sleep(WAIT);
  dumpAll("lever OFF (all lamps OFF -- latch test)");

  click(); await sleep(WAIT);
  dumpAll("lever ON again (all lamps ON)");

  click(); await sleep(WAIT);
  dumpAll("lever OFF again (all lamps OFF -- latch test repeat)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
