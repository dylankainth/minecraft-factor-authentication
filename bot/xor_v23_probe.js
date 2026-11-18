// XOR gate v23 probe -- corrected coordinates
// Build (x,y,z) -> world (x+5, y+8, z-99)
// Verified: leverA at build(-2,1,100) -> world(3,9,1) ✓
//           torchA at build(-3,2,100) -> world(2,10,1) ✓
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

  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  bot.chat("/tp 0 8 0");
  await sleep(1000);
  bot.creative.startFlying();
  for (let i = 0; i < 10; i++) {
    bot.entity.position.set(0, 8, 0);
    bot.entity.velocity.set(0, 0, 0);
    await sleep(100);
  }

  bot.chat("//load xor_compact_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  // Build (x,y,z) -> world (x+5, y+8, z-99)
  const PTS = {
    LEVER_A: new Vec3(3, 9, 1),
    TORCH_A: new Vec3(2, 10, 1),
    LEVER_B: new Vec3(3, 9, 101),
    TORCH_B: new Vec3(2, 10, 101),
    S1: new Vec3(205, 11, 1),
    TERM1_TORCH: new Vec3(206, 11, 1),
    S2: new Vec3(402, 11, 200),
    TERM2_TORCH: new Vec3(402, 12, 200),
    LAMP: new Vec3(305, 12, 200),
  };
  const dump = (label, pos) => {
    const b = bot.blockAt(pos);
    if (!b) { console.log(`[block] ${label} @ ${pos}: NULL`); return; }
    console.log(`[block] ${label} @ (${pos.x},${pos.y},${pos.z}): name=${b.name} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
  };
  const dumpAll = (label) => { console.log(`--- ${label} ---`); for (const [k, p] of Object.entries(PTS)) dump(k, p); };

  const a = () => bot.activateBlock(bot.blockAt(PTS.LEVER_A));
  const b = () => bot.activateBlock(bot.blockAt(PTS.LEVER_B));
  const WAIT = 15000;

  // Warm-up
  console.log("=== warm-up ===");
  for (let i = 0; i < 4; i++) { a(); await sleep(WAIT); b(); await sleep(WAIT); }

  console.log("=== XOR gate truth table ===");
  dumpAll("A=off B=off (expect XOR=false)");

  a(); await sleep(WAIT);
  dumpAll("A=on  B=off (expect XOR=TRUE)");

  b(); await sleep(WAIT);
  dumpAll("A=on  B=on  (expect XOR=false)");

  a(); await sleep(WAIT);
  dumpAll("A=off B=on  (expect XOR=TRUE)");

  b(); await sleep(WAIT);
  dumpAll("A=off B=off back to start (expect XOR=false)");

  // Repeat TRUE cases
  a(); await sleep(WAIT);
  dumpAll("A=on  B=off repeat (expect XOR=TRUE)");

  b(); await sleep(WAIT);
  dumpAll("A=on  B=on  repeat (expect XOR=false)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
