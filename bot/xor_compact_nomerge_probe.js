// Compact XOR gate redesign -- see build_xor_compact_test.py.
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

const ANCHOR = new Vec3(3200, 90, 3200);
const PTS = {
  LEVER_A: ANCHOR.offset(1, 1, 0),
  TORCH_A: ANCHOR.offset(0, 2, 0),
  LEVER_B: ANCHOR.offset(1, 6, 0),
  TORCH_B: ANCHOR.offset(0, 7, 0),
  S1: ANCHOR.offset(0, 2, 10),
  TERM1_TORCH: ANCHOR.offset(0, 3, 10),
  S2: ANCHOR.offset(15, 2, 20),
  TERM2_TORCH: ANCHOR.offset(15, 3, 20),
};

function dump(label, pos) {
  const b = bot.blockAt(pos);
  console.log(`[block] ${label} @ ${pos}: name=${b.name} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}
function dumpAll(label) {
  console.log(`--- ${label} ---`);
  for (const [k, p] of Object.entries(PTS)) dump(k, p);
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

  bot.chat("//load xor_compact_nomerge_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const a = () => bot.activateBlock(bot.blockAt(PTS.LEVER_A));
  const b = () => bot.activateBlock(bot.blockAt(PTS.LEVER_B));
  // Chains here are ~25 hops max (vs 50-150 before); the long_chain_test
  // proved 50 hops settles in ~10s, so this should settle comfortably
  // within 10s. Still warm up every chain through a full cycle first.
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
