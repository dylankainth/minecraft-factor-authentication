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

// build_xor_compact_v2.py now sets WEOffset to the structure's own
// center (local (16,2,10)) -- the player's paste-time position maps to
// THAT local point, not the corner, so every PTS offset below is
// (build_local - HANDLE) instead of build_local directly.
const ANCHOR = new Vec3(600, 70, 600);
const HANDLE = { x: 16, y: 2, z: 10 };
const rel = (x, y, z) => ANCHOR.offset(x - HANDLE.x, y - HANDLE.y, z - HANDLE.z);
const PTS = {
  S1: rel(18, 2, 8),
  S2: rel(30, 1, 4),
  LAMP: rel(22, 2, 9),
};

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  // (auto_redpiler and pre-visiting-far-points-before-paste theories
  // both tested and ruled out -- see docs/handoff-xor-plot-fix-2026-11-18.md.
  // This run tests the center-handle WEOffset fix instead: ANCHOR is
  // now where the structure's CENTER lands, not its corner, roughly
  // halving the worst-case distance from paste position to S1/S2/LAMP.)
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
