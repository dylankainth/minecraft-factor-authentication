// Isolated Term1 with settle hop: Term1 = NOT(NOT_A OR B) = AND(A, NOT_B)
// Probe coords match build_term1_fixed_test.py (no schem shift, min=0).
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
    LEVER_A: ANCHOR.offset(1, 1, 0),
    TORCH_A: ANCHOR.offset(0, 2, 0),
    LEVER_B: ANCHOR.offset(1, 1, 30),
    S1: ANCHOR.offset(50, 2, 50),
    TERM1_TORCH: ANCHOR.offset(50, 3, 50),
    LAMP1: ANCHOR.offset(52, 3, 50),
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

  bot.chat("//load term1_fixed_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const a = () => bot.activateBlock(bot.blockAt(PTS.LEVER_A));
  const b = () => bot.activateBlock(bot.blockAt(PTS.LEVER_B));
  const WAIT = 20000;

  // Warm-up
  console.log("=== warm-up ===");
  for (let i = 0; i < 4; i++) { a(); await sleep(WAIT); b(); await sleep(WAIT); }

  console.log("=== Term1 = AND(A, NOT_B) truth table ===");
  // Expected lamp: ON only when A=on, B=off.
  dumpAll("A=off B=off (lamp OFF)");

  a(); await sleep(WAIT);
  dumpAll("A=on  B=off (lamp ON  -- critical: merge torch relight)");

  b(); await sleep(WAIT);
  dumpAll("A=on  B=on  (lamp OFF)");

  a(); await sleep(WAIT);
  dumpAll("A=off B=on  (lamp OFF)");

  b(); await sleep(WAIT);
  dumpAll("A=off B=off back to start (lamp OFF)");

  // repeat the critical transition
  a(); await sleep(WAIT);
  dumpAll("A=on  B=off repeat (lamp ON)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
