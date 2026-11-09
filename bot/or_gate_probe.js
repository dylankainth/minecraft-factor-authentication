// OR gate: lever A, lever B each directly adjacent to a shared dust
// junction, lamp adjacent to the junction. Tests all 4 input combinations.
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

const ANCHOR = new Vec3(740, 90, 740);
const PTS = {
  LEVER_A: ANCHOR.offset(2, 1, 0),
  REP_A: ANCHOR.offset(2, 1, 1),
  LAMP: ANCHOR.offset(2, 1, 2),
  REP_B: ANCHOR.offset(1, 1, 2),
  LEVER_B: ANCHOR.offset(0, 1, 2),
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

  bot.chat("//load or_gate_test.schem");
  await sleep(1500);
  bot.chat("//paste");
  await sleep(3000);

  const a = () => bot.activateBlock(bot.blockAt(PTS.LEVER_A));
  const b = () => bot.activateBlock(bot.blockAt(PTS.LEVER_B));

  console.log("=== OR gate truth table ===");
  dumpAll("A=off B=off");

  a(); await sleep(1200);
  dumpAll("A=on B=off");

  b(); await sleep(1200);
  dumpAll("A=on B=on");

  a(); await sleep(1200);
  dumpAll("A=off B=on");

  b(); await sleep(1200);
  dumpAll("A=off B=off (back to start)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
