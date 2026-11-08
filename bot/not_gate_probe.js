// Fixed version: previous probes fell continuously in the void plot (no
// floor exists by default), so the real paste anchor / lever position at
// command-execution time didn't match what we assumed from a pre-fall
// position sample. Use bot.creative.flyTo() to hold a fixed position
// (disables local gravity prediction) instead of /tp + hoping it lands.
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

const ANCHOR = new Vec3(300, 90, 300);
function lampsFor(a) {
  return {
    LEVER: a.offset(1, 1, 0),
    A_east: a.offset(2, 0, 1),
    B_south: a.offset(1, 0, 2),
    D_west: a.offset(0, 0, 1),
  };
}
function dump(label, pos) {
  const b = bot.blockAt(pos);
  console.log(`[block] ${label} @ ${pos}: name=${b.name} stateId=${b.stateId} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);

  console.log("[flyTo] moving to anchor, holding position (gravity disabled)");
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos] ${bot.entity.position}`);

  const pts = lampsFor(ANCHOR);
  bot.chat("//load not_gate_test.schem");
  await sleep(1000);
  bot.chat("//paste");
  await sleep(1500);
  console.log(`[pos after paste] ${bot.entity.position}`);  // confirm still held

  console.log("--- state BEFORE toggling lever ---");
  for (const [k, p] of Object.entries(pts)) dump(k, p);

  console.log("--- toggling lever ---");
  const leverBlock = bot.blockAt(pts.LEVER);
  bot.activateBlock(leverBlock);
  await sleep(1500);

  console.log("--- state AFTER toggling lever ---");
  for (const [k, p] of Object.entries(pts)) dump(k, p);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
