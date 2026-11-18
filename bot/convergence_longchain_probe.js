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

const ANCHOR = new Vec3(600, 70, 900);
const SF = ANCHOR.offset(24, 2, 0);
const LEVER_A = ANCHOR.offset(0, 1, 0);

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(2000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps unlimited");
  await sleep(500);
  await bot.creative.flyTo(ANCHOR);
  console.log(`[pos before paste] ${bot.entity.position}`);

  await chatAndWait("//load convergence_longchain_test.schem", "loaded to your clipboard");
  await chatAndWait("//paste", "clipboard was pasted");
  await sleep(2000);

  for (let attempt = 1; attempt <= 5; attempt++) {
    await bot.creative.flyTo(SF.offset(0, 2, 0));
    await sleep(300);
    const b = bot.blockAt(SF);
    console.log(`attempt ${attempt}: SF @ (${SF.x},${SF.y},${SF.z}) = ${b ? b.name : "NULL"}`);
    await sleep(1000);
  }

  await bot.creative.flyTo(LEVER_A.offset(0, 2, 0));
  await sleep(300);
  console.log(`LEVER_A for comparison: ${bot.blockAt(LEVER_A)?.name}`);

  await sleep(500);
  bot.quit();
  setTimeout(() => process.exit(0), 2000);
});
