// Scan a generous 3D volume around where S1/LAMP/S2 should be, after a
// confirmed paste, to see whether they're genuinely missing or just at
// an unexpected offset.
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

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos before paste] ${bot.entity.position} block_pos-ish=(${Math.floor(bot.entity.position.x)},${Math.floor(bot.entity.position.y)},${Math.floor(bot.entity.position.z)})`);

  await chatAndWait("//load xor_compact_v2.schem", "loaded to your clipboard");
  await chatAndWait("//paste", "clipboard was pasted");
  await sleep(1000);

  // fly right into the middle of the search volume so chunk/render isn't a factor
  await bot.creative.flyTo(new Vec3(618, 75, 608));
  await sleep(1000);

  console.log("=== non-air blocks in x:608-635, y:69-76, z:600-612 ===");
  let found = 0;
  for (let x = 608; x <= 635; x++) {
    for (let y = 69; y <= 76; y++) {
      for (let z = 600; z <= 612; z++) {
        const p = new Vec3(x, y, z);
        const b = bot.blockAt(p);
        if (b && b.name !== "air") {
          found++;
          console.log(`  (${x},${y},${z}): ${b.name} ${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
        }
      }
    }
  }
  console.log(`total non-air found: ${found}`);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
