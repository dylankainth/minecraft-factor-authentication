// Compact XOR v2 probe. World = build-local + ANCHOR (ANCHOR is where
// //paste is executed, which happens at the bot's exact position --
// confirmed by the AND/OR-gate probes' convention).
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

// Chat command confirmations arrived 15+ seconds after a fixed sleep in
// earlier runs -- commands are queued/delayed server-side, so a fixed
// sleep after bot.chat() is not a safe "it's done" signal. Wait for the
// server's own confirmation text instead.
function chatAndWait(cmd, matchSubstr, timeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    const onMsg = (m) => {
      const text = m.toString();
      if (text.includes(matchSubstr)) {
        bot.removeListener("message", onMsg);
        clearTimeout(timer);
        resolve(text);
      }
    };
    const timer = setTimeout(() => {
      bot.removeListener("message", onMsg);
      reject(new Error(`Timed out waiting for "${matchSubstr}" after "${cmd}"`));
    }, timeoutMs);
    bot.on("message", onMsg);
    bot.chat(cmd);
  });
}

// Plot [512,1024) in x and z, confirmed empirically: a paste at anchor
// (500,70,500) had everything past world-x=512 silently dropped, lining
// up exactly with the server's own "Entering plot (1,0)" message. Keep
// well clear of any multiple of 512 in both axes.
const ANCHOR = new Vec3(600, 70, 600);
const PTS = {
  LEVER_A: ANCHOR.offset(0, 1, 0),
  LEVER_B: ANCHOR.offset(0, 1, 20),
  TORCH_A: ANCHOR.offset(1, 2, 0),
  TORCH_B: ANCHOR.offset(1, 2, 20),
  S1: ANCHOR.offset(18, 2, 8),
  TERM1_TORCH: ANCHOR.offset(18, 3, 8),
  S2: ANCHOR.offset(30, 1, 4),
  TERM2_TORCH: ANCHOR.offset(30, 2, 4),
  LAMP: ANCHOR.offset(22, 2, 9),
};

async function dump(label, pos) {
  // Fly right next to every single read point, every time -- the first
  // live run showed blocks flip from NULL/air to real content mid-run
  // with no world-state change, meaning chunk freshness near a distant
  // point can't be trusted just because we flew near it once earlier.
  await bot.creative.flyTo(pos.offset(0, 2, 0));
  await sleep(150);
  const b = bot.blockAt(pos);
  if (!b) { console.log(`[block] ${label} @ (${pos.x},${pos.y},${pos.z}): NULL`); return; }
  console.log(`[block] ${label} @ (${pos.x},${pos.y},${pos.z}): name=${b.name} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}
async function dumpAll(label) {
  console.log(`--- ${label} ---`);
  for (const [k, p] of Object.entries(PTS)) await dump(k, p);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);

  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);

  // Fly to the paste anchor itself first -- //paste pastes relative to
  // wherever the bot is standing when the command is sent.
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos] ${bot.entity.position}`);

  await chatAndWait("//load xor_compact_v2.schem", "loaded to your clipboard");
  await chatAndWait("//paste", "clipboard was pasted");
  await sleep(1000);

  // Fly a loop through the structure's footprint so mineflayer's world
  // model actually has chunk data for every read point below -- this is
  // the fix for the v23 session's NULL reads (it never moved after the
  // initial /tp, and the structure spanned ~400 blocks).
  for (const p of [ANCHOR, PTS.S1, PTS.LAMP, PTS.S2, PTS.LEVER_B]) {
    await bot.creative.flyTo(p.offset(0, 3, 0));
    await sleep(300);
  }
  await bot.creative.flyTo(ANCHOR.offset(15, 5, 10));
  await sleep(500);

  console.log("=== initial state (sanity check before toggling) ===");
  await dumpAll("A=off B=off (as pasted)");

  const toggle = async (pos) => {
    await bot.creative.flyTo(pos.offset(0, 2, 0));
    await sleep(150);
    bot.activateBlock(bot.blockAt(pos));
  };
  const a = () => toggle(PTS.LEVER_A);
  const b = () => toggle(PTS.LEVER_B);
  const WAIT = 3000;

  console.log("=== warm-up (force real transitions before trusting reads) ===");
  for (let i = 0; i < 3; i++) { await a(); await sleep(WAIT); await b(); await sleep(WAIT); }

  console.log("=== XOR gate truth table ===");
  await dumpAll("A=off B=off (expect XOR=false)");

  await a(); await sleep(WAIT);
  await dumpAll("A=on  B=off (expect XOR=TRUE)");

  await b(); await sleep(WAIT);
  await dumpAll("A=on  B=on  (expect XOR=false)");

  await a(); await sleep(WAIT);
  await dumpAll("A=off B=on  (expect XOR=TRUE)");

  await b(); await sleep(WAIT);
  await dumpAll("A=off B=off back to start (expect XOR=false)");

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
