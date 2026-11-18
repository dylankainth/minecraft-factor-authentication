// Single persistent connection (reconnecting made things uniformly
// worse, ruling that out). Paste, wait generously, then poll S1/S2/LAMP
// repeatedly over time to see whether reads ever stabilize -- tells us
// if this is "just needs more time" vs. genuinely lost.
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

const ANCHOR = new Vec3(600, 70, 600);
const PTS = {
  S1: ANCHOR.offset(18, 2, 8),
  S2: ANCHOR.offset(30, 1, 4),
  LAMP: ANCHOR.offset(22, 2, 9),
};

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  // Theory: auto_redpiler (MCHPRS's JIT redstone compiler, which
  // auto-activates under /rtps unlimited on complex-enough circuits) may
  // not sync internal compiled-graph node states back to the real chunk
  // data every tick -- that would exactly explain "deep merge points
  // read as air forever, but lever-adjacent IO blocks always update
  // fine" without it being a schematic or wiring bug at all.
  bot.chat("/toggleautorp");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);

  await chatAndWait("//load xor_compact_v2.schem", "loaded to your clipboard");
  await chatAndWait("//paste", "clipboard was pasted");
  console.log("paste confirmed, waiting 5s before first read...");
  await sleep(5000);

  for (let attempt = 1; attempt <= 10; attempt++) {
    console.log(`--- attempt ${attempt} (t=${5 + attempt}s after paste) ---`);
    for (const [k, p] of Object.entries(PTS)) {
      await bot.creative.flyTo(p.offset(0, 2, 0));
      await sleep(200);
      const b = bot.blockAt(p);
      console.log(`  ${k} @ (${p.x},${p.y},${p.z}): ${b ? b.name : "NULL"}`);
    }
    await sleep(1000);
  }

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
