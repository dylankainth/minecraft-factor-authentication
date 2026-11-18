// Fixed XOR gate (settle hops after every staircase step) -- build_xor_fixed_test.js
// Probe points match build_xor_fixed_test.py coords (ANCHOR + build coord).
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
    LEVER_B: ANCHOR.offset(1, 6, 0),
    TORCH_B: ANCHOR.offset(0, 7, 0),
    S1: ANCHOR.offset(0, 2, 10),
    TERM1_TORCH: ANCHOR.offset(0, 3, 10),
    S2: ANCHOR.offset(15, 2, 20),
    TERM2_TORCH: ANCHOR.offset(15, 3, 20),
    LAMP: ANCHOR.offset(0, 3, 25),
    RAWB_SETTLE: ANCHOR.offset(6, 2, 10),  // diagnostic: raw_B settle hop (not landing cell)
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

  bot.chat("//load xor_compact_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const a = () => bot.activateBlock(bot.blockAt(PTS.LEVER_A));
  const b = () => bot.activateBlock(bot.blockAt(PTS.LEVER_B));
  const WAIT = 20000;

  // Extensive warm-up: drive every input through multiple full transitions
  // before trusting any read (paste-state consistency gotcha).
  console.log("=== warm-up ===");
  for (let i = 0; i < 6; i++) {
    a(); await sleep(WAIT);
    b(); await sleep(WAIT);
  }

  console.log("=== fixed XOR gate truth table ===");

  dumpAll("A=off B=off (expect XOR=false)");

  a(); await sleep(WAIT);
  dumpAll("A=on  B=off (expect XOR=TRUE)");

  b(); await sleep(WAIT);
  dumpAll("A=on  B=on  (expect XOR=false)");

  a(); await sleep(WAIT);
  dumpAll("A=off B=on  (expect XOR=TRUE)");

  b(); await sleep(WAIT);
  dumpAll("A=off B=off back to start (expect XOR=false)");

  // repeat the two TRUE cases to confirm repeatability
  a(); await sleep(WAIT);
  dumpAll("A=on  B=off repeat (expect XOR=TRUE)");

  b(); await sleep(WAIT);
  dumpAll("A=on  B=on  repeat (expect XOR=false)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
