// Torch-relight diagnostic: lever -> repeater -> stone S -> torch -> dust -> lamp.
// lamp should == NOT(lever). The OFF->ON->OFF lever transitions test whether
// the torch relights when S loses power (exactly the Term1/Term2 failure mode).
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

  // build_torch_relight_test.py coords (world = anchor + build coord, y+1):
  // lever=(1,1,0) -> world (ANCHOR.x+1, ANCHOR.y+1, ANCHOR.z)
  // torch=(6,2,1)   -> world (ANCHOR.x+6, ANCHOR.y+2, ANCHOR.z+1)
  // lamp=(8,2,1)    -> world (ANCHOR.x+8, ANCHOR.y+2, ANCHOR.z+1)
  // S=(6,1,1)       -> world (ANCHOR.x+6, ANCHOR.y+1, ANCHOR.z+1)
  const PTS = {
    LEVER: ANCHOR.offset(1, 1, 0),
    S: ANCHOR.offset(6, 1, 1),
    TORCH: ANCHOR.offset(6, 2, 1),
    LAMP: ANCHOR.offset(7, 2, 2),
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

  bot.chat("//load torch_relight_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const click = () => bot.activateBlock(bot.blockAt(PTS.LEVER));
  const WAIT = 15000;

  console.log("=== warm-up: lever off->on->off ===");
  dumpAll("start (lever off, expect lamp ON)");
  click(); await sleep(WAIT);
  dumpAll("lever ON  (expect lamp OFF)");
  click(); await sleep(WAIT);
  dumpAll("lever off again (expect lamp ON -- torch relight test)");

  click(); await sleep(WAIT);
  dumpAll("lever ON again (expect lamp OFF)");
  click(); await sleep(WAIT);
  dumpAll("lever off again (expect lamp ON)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
