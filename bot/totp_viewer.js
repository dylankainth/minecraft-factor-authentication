// Connects a separate bot (different username, so it doesn't disturb the
// running verification probe) and starts prismarine-viewer's web server so
// the build can be viewed live in a browser.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const { mineflayer: prismarineViewer } = require("prismarine-viewer");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "totp_bot_viewer",
  version: "1.20.4",
  auth: "offline",
});

bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });

const ANCHOR = new Vec3(0, 70, 0);
const VIEW_POS = ANCHOR.offset(100, 100, 100); // a spot with a good view into the build

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode spectator");
  await sleep(500);
  await bot.creative.flyTo(VIEW_POS);
  console.log(`[pos] ${bot.entity.position}`);

  const port = parseInt(process.env.VIEWER_PORT || "3007", 10);
  prismarineViewer(bot, { port, firstPerson: false, viewDistance: 8 });
  console.log(`[viewer] started on port ${port}`);
});
