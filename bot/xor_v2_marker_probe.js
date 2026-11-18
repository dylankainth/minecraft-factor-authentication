// Place a distinctive marker block (diamond_block) at S1's exact
// coordinates via //set, then read it back -- isolates whether the
// "always air" bug is block-type-specific (stone/redstone_lamp) or
// position-specific.
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
const S1 = ANCHOR.offset(18, 2, 8); // (618, 72, 608)

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);

  await chatAndWait("//load xor_compact_v2.schem", "loaded to your clipboard");
  await chatAndWait("//paste", "clipboard was pasted");
  await sleep(1000);

  console.log(`=== S1 before marker, read at (${S1.x},${S1.y},${S1.z}) ===`);
  await bot.creative.flyTo(S1.offset(0, 2, 0));
  await sleep(500);
  console.log(`  S1 (expect stone): ${bot.blockAt(S1)?.name}`);

  console.log("=== flying exactly into S1's cell to set pos1/pos2 there ===");
  await bot.creative.flyTo(S1);
  await sleep(500);
  console.log(`  bot position now: ${bot.entity.position}`);
  await chatAndWait("//pos1", "First position set", 5000).catch((e) => console.log("  [pos1 wait failed]", e.message));
  await chatAndWait("//pos2", "Second position set", 5000).catch((e) => console.log("  [pos2 wait failed]", e.message));
  await chatAndWait("//set minecraft:diamond_block", "blocks have been changed", 10000).catch((e) => console.log("  [set wait failed]", e.message));
  await sleep(1000);

  await bot.creative.flyTo(S1.offset(0, 2, 0));
  await sleep(500);
  console.log(`=== S1 after //set diamond_block ===`);
  console.log(`  S1 (expect diamond_block): ${bot.blockAt(S1)?.name}`);

  // also re-check a point we KNOW works (TERM1_TORCH, one above S1) for comparison
  const T1 = S1.offset(0, 1, 0);
  console.log(`  TERM1_TORCH for comparison: ${bot.blockAt(T1)?.name}`);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
