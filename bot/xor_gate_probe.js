// XOR gate: see build_xor_gate_test.py for the full layout and the
// collision history that shaped it.
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

const ANCHOR = new Vec3(2700, 90, 2700);
const PTS = {
  LEVER_A: ANCHOR.offset(1, 1, 0),
  TORCH_A: ANCHOR.offset(0, 2, 0),
  LEVER_B: ANCHOR.offset(1, 1, 30),
  TORCH_B: ANCHOR.offset(0, 2, 30),
  S1: ANCHOR.offset(50, 2, 50),
  TERM1_TORCH: ANCHOR.offset(50, 3, 50),
  S2: ANCHOR.offset(50, 2, 90),
  TERM2_TORCH: ANCHOR.offset(50, 3, 90),
  LAMP: ANCHOR.offset(100, 3, 50),
};

function dump(label, pos) {
  const b = bot.blockAt(pos);
  console.log(`[block] ${label} @ ${pos}: name=${b.name} stateId=${b.stateId} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
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
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos] ${bot.entity.position}`);
  // Brand-new regions (never visited before) need a moment for chunks
  // to stream in -- without this, reads at this anchor have come back
  // as "air" for everything beyond ~50 blocks, a chunk-loading race,
  // not a circuit problem.
  await sleep(5000);

  // These chains run 50-150 repeaters long; at the default /rtps 10 each
  // hop costs a real tick, so a signal change can take 10+ seconds to
  // reach the far end. Speed up propagation instead of just waiting longer.
  bot.chat("/rtps unlimited");
  await sleep(500);

  bot.chat("//load xor_gate_test.schem");
  await sleep(2500);
  bot.chat("//paste");
  await sleep(4000);

  const a = () => bot.activateBlock(bot.blockAt(PTS.LEVER_A));
  const b = () => bot.activateBlock(bot.blockAt(PTS.LEVER_B));

  // build_long_chain_test.py proved a 50-repeater chain needs ~10s of
  // real wall-clock time per transition even under /rtps unlimited --
  // this gate's longest legs run ~150 repeaters, so give each toggle
  // 25s before trusting a read.
  const WAIT = 25000;

  // Warm-up: every one of NOT_A/raw_A/NOT_B/raw_B needs its OWN live
  // transition in BOTH directions before any read is trustworthy (an
  // earlier run found Term2 looking wrong simply because B was never
  // toggled at all in that probe -- NOT_B's stale contribution to S2
  // was silently stuck). Cycle A and B through a full off->on->off
  // each, independently, before touching the real truth table.
  console.log("=== warm-up: full A cycle ===");
  a(); await sleep(WAIT);
  a(); await sleep(WAIT);
  console.log("=== warm-up: full B cycle ===");
  b(); await sleep(WAIT);
  b(); await sleep(WAIT);

  console.log("=== XOR gate truth table (every chain pre-warmed) ===");
  dumpAll("A=off B=off");

  a(); await sleep(WAIT);
  dumpAll("A=on B=off (expect XOR=true)");

  b(); await sleep(WAIT);
  dumpAll("A=on B=on (expect XOR=false)");

  a(); await sleep(WAIT);
  dumpAll("A=off B=on (expect XOR=true)");

  b(); await sleep(WAIT);
  dumpAll("A=off B=off, back to start (expect XOR=false)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
