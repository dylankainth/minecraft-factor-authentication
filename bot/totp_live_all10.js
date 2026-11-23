// Runs all 10 RFC 4226 test vectors (counter 0-9) live, in one continuous
// session: one /load -c, then for each vector, pulse rst, toggle only the
// counter bits that changed since the previous vector (XOR-diff, far fewer
// commands than re-setting all 32 bits every time), wait, read done + all
// 20 code bits exactly once (no polling), record, move to the next vector.
// start is set once and left on the whole time -- rst alone forces the FSM
// back to IDLE regardless of start, and IDLE latches straight into LOAD1
// again as soon as rst releases, same as headless's own reset pattern.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const EXPECTED = [755224, 287082, 359152, 969429, 338314, 254676, 287922, 162583, 399871, 520489];
const WAIT_SECONDS = parseInt(process.argv[2] || "45", 10);

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs_fork_server",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: "totp_all10",
  version: "1.20.4",
  auth: "offline",
  checkTimeoutInterval: 120000,
});
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => { console.log("[end]", r); process.exit(0); });
bot.on("message", (m) => console.log(`[msg] ${m.toString()}`));

function waitForChatMatch(regex, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`timeout waiting for /${regex.source}/`)), timeoutMs);
    function handler(m) {
      const match = m.toString().match(regex);
      if (match) { clearTimeout(timer); bot.removeListener("message", handler); resolve(match); }
    }
    bot.on("message", handler);
  });
}
async function chatAndWait(cmd, regex, timeoutMs = 20000, attempt = 0) {
  try {
    bot.chat(cmd);
    return await waitForChatMatch(regex, timeoutMs);
  } catch (e) {
    if (attempt >= 4) throw e;
    console.log(`[retry] ${cmd} after: ${e.message}`);
    await sleep(2000);
    return chatAndWait(cmd, regex, timeoutMs, attempt + 1);
  }
}

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

async function countAt(pos, pattern, attempt = 0) {
  try {
    await bot.creative.flyTo(pos);
    await sleep(150);
    bot.chat("//pos1");
    await waitForChatMatch(/First position set/, 30000);
    bot.chat("//pos2");
    await waitForChatMatch(/Second position set/, 30000);
    bot.chat(`//count ${pattern}`);
    const m = await waitForChatMatch(/Counted (\d+) block/, 30000);
    return parseInt(m[1], 10);
  } catch (e) {
    if (attempt >= 4) throw e;
    console.log(`[retry] countAt ${pos} after: ${e.message}`);
    await sleep(2000);
    return countAt(pos, pattern, attempt + 1);
  }
}
async function isLampLit(pos) {
  return (await countAt(pos, "minecraft:redstone_lamp")) === 0;
}

bot.once("login", async () => {
  try {
  console.log("[login] ok");
  await sleep(1000);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps 1000000000");
  await sleep(500);

  await bot.creative.flyTo(new Vec3(100, 70, 100));
  bot.chat("/load totp_core.litematic -c");
  const loadMsg = await waitForChatMatch(/Reloaded .* at (-?\d+), (-?\d+), (-?\d+)/, 60000);
  const firstPos = new Vec3(parseInt(loadMsg[1], 10), parseInt(loadMsg[2], 10), parseInt(loadMsg[3], 10));
  console.log(`[load] first_pos = ${firstPos}`);
  await sleep(3000);

  const pinsRaw = loadPinsRaw();
  function outputPos(name) {
    const p = pinsRaw[name];
    return firstPos.offset(p.x + p.nx, p.y, p.z + p.nz);
  }

  await chatAndWait("/lever rst on", /rst is already on|Turned rst on/);
  await chatAndWait("/lever rst off", /rst is already off|Turned rst off/);
  await chatAndWait("/lever start on", /start is already on|Turned start on/);
  console.log("[setup] rst cycled, start on");

  const results = [];
  let prevCounter = 0;
  for (let v = 0; v < 10; v++) {
    const counter = v;
    const diff = counter ^ prevCounter;
    prevCounter = counter;

    await chatAndWait("/lever rst on", /rst is already on|Turned rst on/);
    for (let i = 0; i < 32; i++) {
      if ((diff >>> i) & 1) {
        const bitVal = (counter >>> i) & 1;
        await chatAndWait(`/lever counter[${i}] ${bitVal ? "on" : "off"}`, new RegExp(`counter\\[${i}\\] (is already (on|off)|Turned counter\\[${i}\\] (on|off))`));
      }
    }
    await chatAndWait("/lever rst off", /rst is already off|Turned rst off/);
    console.log(`[vector ${v}] counter=${counter} set, waiting ${WAIT_SECONDS}s`);
    await sleep(WAIT_SECONDS * 1000);

    const doneLit = await isLampLit(outputPos("done"));
    let code = null;
    if (doneLit) {
      code = 0;
      for (let i = 0; i < 20; i++) {
        const lit = await isLampLit(outputPos(`code[${i}]`));
        if (lit) code |= (1 << i);
      }
    }
    const match = code === EXPECTED[v];
    console.log(`[RESULT vector=${v}] counter=${counter} done=${doneLit} code=${code} expected=${EXPECTED[v]} match=${match}`);
    results.push({ v, counter, done: doneLit, code, expected: EXPECTED[v], match });
  }

  console.log("[SUMMARY]", JSON.stringify(results));
  const allMatch = results.every((r) => r.match);
  console.log(`[FINAL] all10match=${allMatch}`);

  await sleep(300);
  bot.quit();
  setTimeout(() => process.exit(0), 1500);
  } catch (e) {
    console.error("[FATAL]", e);
    try { bot.quit(); } catch {}
    setTimeout(() => process.exit(1), 1500);
  }
});
