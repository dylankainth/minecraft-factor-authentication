// Reads done + all 20 code bits one at a time, reconnecting a fresh bot
// for each single read if needed, to push through the recurring ~30s
// keepalive disconnect under heavy server load. The circuit's own state is
// unaffected by reconnecting (read-only //count checks).
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// minecraft-protocol's keepalive timeout throws from inside a raw setTimeout
// callback, bypassing the bot's own 'error' event entirely -- without this,
// it crashes the whole process as an uncaught exception, defeating the
// per-read retry logic below. Swallow it and let the current readOneLamp
// attempt's own timeouts/retries handle recovery instead.
process.on("uncaughtException", (e) => {
  console.error("[uncaughtException swallowed]", e.message);
});
process.on("unhandledRejection", (e) => {
  console.error("[unhandledRejection swallowed]", e);
});

function loadPinsRaw() {
  const fs = require("fs");
  const path = require("path");
  const file = process.env.PINS_FILE || path.join(__dirname, "pins.txt");
  const pins = {};
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const t = line.trim();
    if (!t) continue;
    const [name, x, y, z, nx, nz] = t.split(/\s+/);
    pins[name] = { x: parseInt(x, 10), y: parseInt(y, 10), z: parseInt(z, 10), nx: parseInt(nx, 10), nz: parseInt(nz, 10) };
  }
  return pins;
}

const FIRST_POS = new Vec3(
  parseInt(process.argv[2] || "400", 10),
  parseInt(process.argv[3] || "8", 10),
  parseInt(process.argv[4] || "277", 10)
);
const pinsRaw = loadPinsRaw();
function outputPos(name) {
  const p = pinsRaw[name];
  return FIRST_POS.offset(p.x + p.nx, p.y, p.z + p.nz);
}

function readOneLamp(pos, attempt = 0) {
  return new Promise((resolve, reject) => {
    const bot = mineflayer.createBot({
      host: process.env.MC_HOST || "mchprs_fork_server",
      port: parseInt(process.env.MC_PORT || "25565", 10),
      username: `totp_read_${Math.floor(Math.random() * 100000)}`,
      version: "1.20.4",
      auth: "offline",
      checkTimeoutInterval: 120000, // default 30000ms keeps firing under heavy server load
    });
    let settled = false;
    const finish = (fn, val) => { if (!settled) { settled = true; try { bot.quit(); } catch {} setTimeout(() => fn(val), 200); } };

    bot.on("error", (e) => finish(reject, e));
    bot.on("end", (r) => finish(reject, new Error(`ended: ${r}`)));

    function waitForChatMatch(regex, timeoutMs) {
      return new Promise((res, rej) => {
        const timer = setTimeout(() => rej(new Error(`timeout /${regex.source}/`)), timeoutMs);
        function handler(m) {
          const match = m.toString().match(regex);
          if (match) { clearTimeout(timer); bot.removeListener("message", handler); res(match); }
        }
        bot.on("message", handler);
      });
    }

    bot.once("login", async () => {
      try {
        await sleep(1000);
        await bot.creative.flyTo(pos.offset(1, 0, 0));
        await sleep(200);
        bot.chat("//pos1");
        await waitForChatMatch(/First position set/, 15000);
        bot.chat("//pos2");
        await waitForChatMatch(/Second position set/, 15000);
        bot.chat("//count minecraft:redstone_lamp");
        const m = await waitForChatMatch(/Counted (\d+) block/, 15000);
        const count = parseInt(m[1], 10);
        finish(resolve, count === 0);
      } catch (e) {
        finish(reject, e);
      }
    });
  }).catch(async (e) => {
    if (attempt >= 4) throw e;
    await sleep(1500);
    return readOneLamp(pos, attempt + 1);
  });
}

(async () => {
  const doneLit = await readOneLamp(outputPos("done"));
  console.log(`[result] done=${doneLit}`);
  let code = 0;
  for (let i = 0; i < 20; i++) {
    const lit = await readOneLamp(outputPos(`code[${i}]`));
    if (lit) code |= (1 << i);
    console.log(`[bit] code[${i}]=${lit ? 1 : 0}`);
  }
  console.log(`[result] code=${code} expected=755224 match=${code === 755224}`);
  process.exit(0);
})();
