// Scan along x and z to find exactly where pasted blocks stop existing --
// pinpoints whether this is a plot/chunk boundary clipping the paste.
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

const ANCHOR = new Vec3(600, 70, 600);

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos] ${bot.entity.position}`);

  bot.chat(`//load xor_compact_v2.schem`);
  await sleep(1500);
  bot.chat("//paste");
  console.log("waiting 15s for paste to fully settle...");
  await sleep(15000);

  console.log("=== sanity: SA support block directly under TORCH_A, read twice 2s apart ===");
  const SA = ANCHOR.offset(1, 1, 0);
  await bot.creative.flyTo(SA.offset(0, 3, 0));
  await sleep(1000);
  console.log(`  SA first read: ${bot.blockAt(SA)?.name}`);
  await sleep(2000);
  console.log(`  SA second read (same position, no move): ${bot.blockAt(SA)?.name}`);
  await bot.creative.flyTo(SA.offset(0, 0, 0));
  await sleep(2000);
  console.log(`  SA third read (flew to it exactly, longer settle): ${bot.blockAt(SA)?.name}`);

  console.log("=== scan along x at y=71 (lever height), z=900, longer settle ===");
  for (let x = ANCHOR.x; x <= ANCHOR.x + 33; x += 2) {
    const p = new Vec3(x, ANCHOR.y + 1, ANCHOR.z);
    await bot.creative.flyTo(p.offset(0, 2, 0));
    await sleep(500);
    const b = bot.blockAt(p);
    console.log(`  x=${x} (dx=${x-ANCHOR.x}): ${b ? b.name : "NULL"}`);
  }

  console.log("=== /plot info ===");
  bot.chat("/plot info");
  await sleep(1000);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
