// Compact XOR gate redesign -- see build_xor_compact_test.py.
//
// Lessons baked in here after a long debugging detour:
//  - Large teleports (thousands of blocks) break chunk loading
//    client-side indefinitely; anchor relative to the bot's own natural
//    spawn position instead (small offset).
//  - bot.creative.flyTo() can drift indefinitely; use /tp + manual
//    position-pin (gravity disabled, position re-set for ~1s) instead.
//  - Schematic.save() normalizes to the MINIMUM coordinate across all
//    blocks, not always 0 -- build_xor_compact_test.py's lowest block is
//    at y=Y_BASE=1, so every absolute y printed by that script is one
//    higher than its actual LOCAL (and therefore pasted-relative) y.
//    Every offset below is the script's printed value minus 1 in y.
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

function dump(label, pos, pts) {
  const b = bot.blockAt(pos);
  if (!b) { console.log(`[block] ${label} @ ${pos}: NULL`); return; }
  console.log(`[block] ${label} @ ${pos}: name=${b.name} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(3000);
  const spawn = bot.entity.position.floored();
  console.log(`[spawn] ${spawn}`);
  const ANCHOR = spawn.offset(5, 0, 5);

  // RAW printed values from build_xor_compact_test.py, no shift -- the
  // earlier "-1 y shift" theory was wrong (it broke block types that
  // were already correct unshifted in an earlier run); reverted.
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
    RAWB_LOW: ANCHOR.offset(7, 2, 10),  // diagnostic: raw_B right before it enters S1
  };
  const dumpAll = (label) => {
    console.log(`--- ${label} ---`);
    for (const [k, p] of Object.entries(PTS)) dump(k, p);
  };

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
  console.log(`[pos] ${bot.entity.position}`);

  bot.chat("//load xor_compact_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const a = () => {
    const blk = bot.blockAt(PTS.LEVER_A);
    if (!blk) { console.log("[a] LEVER_A null, skipping"); return; }
    bot.activateBlock(blk);
  };
  const b = () => {
    const blk = bot.blockAt(PTS.LEVER_B);
    if (!blk) { console.log("[b] LEVER_B null, skipping"); return; }
    bot.activateBlock(blk);
  };
  const WAIT = 10000;

  console.log("=== warm-up ===");
  a(); await sleep(WAIT);
  a(); await sleep(WAIT);
  b(); await sleep(WAIT);
  b(); await sleep(WAIT);

  console.log("=== compact XOR gate truth table ===");
  dumpAll("A=off B=off (expect XOR=false)");

  a(); await sleep(WAIT);
  dumpAll("A=on B=off (expect XOR=TRUE)");

  b(); await sleep(WAIT);
  dumpAll("A=on B=on (expect XOR=false)");

  a(); await sleep(WAIT);
  dumpAll("A=off B=on (expect XOR=TRUE)");

  b(); await sleep(WAIT);
  dumpAll("A=off B=off, back to start (expect XOR=false)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
