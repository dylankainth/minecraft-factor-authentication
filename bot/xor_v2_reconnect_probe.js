// Theory: mineflayer's client-side chunk cache can go stale after a big
// bulk edit (3000+ block paste). Test the fix: paste with bot #1, then
// quit and reconnect with bot #2 before reading -- a fresh login forces
// the server to resend complete, fresh chunk data from scratch.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function chatAndWait(bot, cmd, matchSubstr, timeoutMs = 20000) {
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

function makeBot(username) {
  return mineflayer.createBot({
    host: process.env.MC_HOST || "mchprs",
    port: parseInt(process.env.MC_PORT || "25565", 10),
    username,
    version: "1.20.4",
    auth: "offline",
  });
}

const ANCHOR = new Vec3(600, 70, 600);
const PTS = {
  LEVER_A: ANCHOR.offset(0, 1, 0),
  TORCH_A: ANCHOR.offset(1, 2, 0),
  S1: ANCHOR.offset(18, 2, 8),
  TERM1_TORCH: ANCHOR.offset(18, 3, 8),
  S2: ANCHOR.offset(30, 1, 4),
  TERM2_TORCH: ANCHOR.offset(30, 2, 4),
  LAMP: ANCHOR.offset(22, 2, 9),
};

async function pasteWithBot1() {
  const bot = makeBot("totp_bot");
  bot.on("message", (m) => console.log(`[bot1 msg] ${m.toString()}`));
  bot.on("error", (e) => console.error("[bot1 error]", e));
  await new Promise((resolve) => bot.once("login", resolve));
  console.log("[bot1] login ok");
  await sleep(1500);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  await chatAndWait(bot, "//load xor_compact_v2.schem", "loaded to your clipboard");
  await chatAndWait(bot, "//paste", "clipboard was pasted");
  await sleep(1000);
  console.log("[bot1] paste confirmed, disconnecting");
  bot.quit();
  await sleep(2000);
}

async function readWithBot2() {
  const bot = makeBot("totp_reader");
  bot.on("message", (m) => console.log(`[bot2 msg] ${m.toString()}`));
  bot.on("error", (e) => console.error("[bot2 error]", e));
  await new Promise((resolve) => bot.once("login", resolve));
  console.log("[bot2] login ok (fresh connection)");
  await sleep(1500);
  bot.chat("/gamemode creative");
  await sleep(500);

  for (const [k, p] of Object.entries(PTS)) {
    await bot.creative.flyTo(p.offset(0, 2, 0));
    await sleep(400);
    const b = bot.blockAt(p);
    console.log(`[block] ${k} @ (${p.x},${p.y},${p.z}): ${b ? b.name : "NULL"} ${b && b.getProperties ? JSON.stringify(b.getProperties()) : ""}`);
  }

  bot.quit();
  await sleep(1000);
  process.exit(0);
}

(async () => {
  await pasteWithBot1();
  await readWithBot2();
})();
