// Verified NOT gate (standing-torch inverter -> dust -> lamp). See
// build_not_gate_test.py for the full history of what didn't work and why
// (bare adjacency, wall-torch propagation limit) before landing here.
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

const ANCHOR = new Vec3(500, 90, 500);
const PTS = {
  LEVER: ANCHOR.offset(0, 0, 1),
  TORCH: ANCHOR.offset(0, 1, 0),
  DUST: ANCHOR.offset(1, 1, 0),
  LAMP: ANCHOR.offset(2, 1, 0),
};

function dump(label, pos) {
  const b = bot.blockAt(pos);
  console.log(`[block] ${label} @ ${pos}: name=${b.name} stateId=${b.stateId} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos] ${bot.entity.position}`);

  bot.chat("//load not_gate_test.schem");
  await sleep(1000);
  bot.chat("//paste");
  await sleep(1500);

  // The torch is placed already-lit by the schematic (a static placement,
  // not a live transition) -- its own displayed state is correct, but one
  // real transition is needed before downstream dust/lamp state is fully
  // consistent (see build_not_gate_test.py history). Toggle through both
  // states twice so the truth table printed at the end reflects steady
  // state, not the just-pasted transient.
  bot.activateBlock(bot.blockAt(PTS.LEVER)); // -> ON
  await sleep(1200);
  bot.activateBlock(bot.blockAt(PTS.LEVER)); // -> OFF
  await sleep(1200);

  console.log("=== NOT gate truth table ===");
  console.log("--- lever OFF (input unpowered) ---");
  for (const [k, p] of Object.entries(PTS)) dump(k, p);

  bot.activateBlock(bot.blockAt(PTS.LEVER)); // -> ON
  await sleep(1200);
  console.log("--- lever ON (input powered) ---");
  for (const [k, p] of Object.entries(PTS)) dump(k, p);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
