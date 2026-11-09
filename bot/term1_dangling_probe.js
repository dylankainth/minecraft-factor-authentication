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

const ANCHOR = new Vec3(2500, 90, 2500);
const PTS = {
  LEVER_A: ANCHOR.offset(1, 1, 0),
  TORCH_A: ANCHOR.offset(0, 2, 0),
  LEVER_B: ANCHOR.offset(1, 1, 30),
  TORCH_B: ANCHOR.offset(0, 2, 30),
  S1: ANCHOR.offset(50, 2, 50),
  TERM1_TORCH: ANCHOR.offset(50, 3, 50),
  LAMP: ANCHOR.offset(52, 3, 50),
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

  bot.chat("//load term1_plus_dangling_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  const a = () => bot.activateBlock(bot.blockAt(PTS.LEVER_A));
  const b = () => bot.activateBlock(bot.blockAt(PTS.LEVER_B));
  const WAIT = 20000;

  // Term1 = AND(raw_A, NOT_B) via NOT(NOT_A OR raw_B). Expected: lit
  // only when A=on, B=off.
  dumpAll("A=off B=off (expect Term1 false)");

  a(); await sleep(WAIT);
  dumpAll("A=on B=off (expect Term1 TRUE)");

  a(); await sleep(WAIT);
  dumpAll("A=off B=off again (expect Term1 false)");

  a(); await sleep(WAIT);
  dumpAll("A=on B=off again (expect Term1 TRUE -- the exact transition that failed before)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
