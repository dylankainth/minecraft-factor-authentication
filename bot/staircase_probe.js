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

function dump(label, pos) {
  const b = bot.blockAt(pos);
  if (!b) {
    console.log(`[block] ${label} @ ${pos}: NULL (chunk not loaded)`);
    return;
  }
  console.log(`[block] ${label} @ ${pos}: name=${b.name} props=${JSON.stringify(b.getProperties ? b.getProperties() : null)}`);
}

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(3000);  // let the real spawn position settle (see origin_check2_probe.js)

  // Large jumps (thousands of blocks via flyTo or /tp, crossing many plot
  // boundaries at once) break chunk loading client-side -- confirmed via
  // origin_check2_probe.js: blockAt() stays null indefinitely after a far
  // jump, but a SMALL nearby /tp from the bot's own natural spawn works
  // immediately. Anchor relative to spawn instead of an arbitrary distant
  // coordinate.
  const spawn = bot.entity.position.floored();
  console.log(`[spawn] ${spawn}`);
  const ANCHOR = spawn.offset(5, 0, 5);
  // build_staircase_test.py's SA=(0,1,0) -- min Y across all blocks is 1,
  // not 0, so Schematic.save() normalizes with a -1 shift I forgot to
  // account for here. Lever/lamp's real LOCAL y is one less than their
  // original-script y (2 -> 1).
  const LEVER = ANCHOR.offset(0, 1, 0);
  const LAMP = ANCHOR.offset(8, 1, 0);

  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  bot.chat(`/tp ${ANCHOR.x} ${ANCHOR.y} ${ANCHOR.z}`);
  await sleep(1000);
  bot.creative.startFlying();  // disable gravity -- this is a real-terrain
  // world now (not void), so a plain /tp without this would let the bot
  // fall/settle before //paste reads its position, shifting the anchor.
  for (let i = 0; i < 10; i++) {
    bot.entity.position.set(ANCHOR.x, ANCHOR.y, ANCHOR.z);
    bot.entity.velocity.set(0, 0, 0);
    await sleep(100);
  }
  console.log(`[pos] ${bot.entity.position}`);
  console.log(`[chunk check] ${bot.blockAt(ANCHOR)}`);

  bot.chat("//load staircase_test.schem");
  await sleep(2500);
  bot.chat("//paste");
  await sleep(3000);

  const toggle = () => {
    const b = bot.blockAt(LEVER);
    if (!b) { console.log("[toggle] LEVER block is null, skipping"); return; }
    bot.activateBlock(b);
  };

  console.log("--- initial (lever off) ---");
  dump("LEVER", LEVER); dump("LAMP", LAMP);

  toggle(); await sleep(8000);
  console.log("--- toggle 1: ON (lamp should light) ---");
  dump("LEVER", LEVER); dump("LAMP", LAMP);

  toggle(); await sleep(8000);
  console.log("--- toggle 2: OFF (lamp should go dark) ---");
  dump("LEVER", LEVER); dump("LAMP", LAMP);

  toggle(); await sleep(8000);
  console.log("--- toggle 3: ON again (lamp should relight) ---");
  dump("LEVER", LEVER); dump("LAMP", LAMP);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
