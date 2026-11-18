// Diagnostic: scan for stone blocks at y=11, z=1 from x=144 to 220
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

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(3000);

  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  bot.chat("/tp 0 8 0");
  await sleep(1000);
  bot.creative.startFlying();
  for (let i = 0; i < 10; i++) {
    bot.entity.position.set(0, 8, 0);
    bot.entity.velocity.set(0, 0, 0);
    await sleep(100);
  }

  bot.chat("//load xor_compact_test.schem");
  await sleep(2000);
  bot.chat("//paste");
  await sleep(3000);

  // Scan for redstone_wire or stone at y=11, z=1 from x=144 to 220
  console.log("=== Scanning for redstone_wire or stone at y=11, z=1 ===");
  const found = [];
  for (let dx = 144; dx <= 220; dx++) {
    const p = new Vec3(dx, 11, 1);
    const b = bot.blockAt(p);
    if (b && b.name !== "air") {
      found.push({ pos: p, name: b.name, props: b.getProperties ? b.getProperties() : null });
    }
  }
  console.log(`Found ${found.length} non-air blocks at y=11, z=1 from x=144 to 220:`);
  for (const f of found.slice(0, 30)) {
    console.log(`  @ (${f.pos.x},${f.pos.y},${f.pos.z}): ${f.name} ${JSON.stringify(f.props)}`);
  }

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
