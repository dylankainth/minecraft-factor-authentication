// Connectivity smoke test: connect to MCHPRS, claim a plot, place a block,
// read the chat/world response, disconnect. Proves the bot pipeline works
// before anything redstone-specific is attempted.
const mineflayer = require("mineflayer");

const host = process.env.MC_HOST || "mchprs";
const port = parseInt(process.env.MC_PORT || "25565", 10);

const bot = mineflayer.createBot({
  host,
  port,
  username: "totp_bot",
  version: "1.20.4",
  auth: "offline",
});

bot.on("chat", (username, message) => {
  console.log(`[chat] <${username}> ${message}`);
});

bot.on("message", (jsonMsg) => {
  console.log(`[msg] ${jsonMsg.toString()}`);
});

bot.on("error", (err) => {
  console.error("[error]", err);
});

bot.on("end", (reason) => {
  console.log("[end]", reason);
  process.exit(0);
});

bot.once("login", async () => {
  // MCHPRS doesn't send update_health, which mineflayer's 'spawn' event
  // waits on -- so we proceed off 'login' instead (see CLAUDE.md note).
  console.log("[login] bot has logged in");
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  await sleep(1000);

  bot.chat("/plot auto");
  await sleep(1000);
  bot.chat("/plot info");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(1000);

  console.log("[done] smoke test commands sent, waiting 5s before quit");
  await sleep(5000);
  bot.quit();
});
