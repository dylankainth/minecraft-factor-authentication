// Timed live test: load the build fresh, drive counter=0, precisely time
// how long the live circuit takes to go from `start on` to `done=true`
// (the actual redstone computation time, not verification overhead), then
// read the full binary code and all 42 seven-segment lamps using the
// proven queue-based, coordinate-specific message matching (see
// totp_read_display_clean.js's header for why that matters).
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const EXPECTED = process.argv[2] || "755224";
const COUNTER = parseInt(process.argv[3] || "0", 10);

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs_fork_server",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: `totp_timed_${Math.floor(Math.random() * 100000)}`,
  version: "1.20.4",
  auth: "offline",
  checkTimeoutInterval: 120000,
});
process.on("uncaughtException", (e) => console.error("[uncaughtException swallowed]", e.message));
process.on("unhandledRejection", (e) => console.error("[unhandledRejection swallowed]", e));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => console.log("[end]", r));

const msgQueue = [];
bot.on("message", (m) => { msgQueue.push(m.toString()); if (msgQueue.length > 300) msgQueue.shift(); });

// `matcher` is either a RegExp, or a predicate (message) => truthy match.
// Predicates are used for position confirmations: standing on a floating
// output cell with no floor beneath it, the player can settle a couple of
// blocks off the exact /tp target before flyTo's no-fall stabilization
// fully kicks in -- an exact-coordinate regex then rejects a perfectly
// valid, nearby confirmation forever. A small tolerance fixes that without
// reopening the earlier cross-lamp crosstalk bug (different lamps are tens
// of blocks apart, far outside any reasonable tolerance).
function tolerantPosMatcher(label, pos, tol = 3) {
  const re = new RegExp(`${label} set to \\((-?\\d+), (-?\\d+), (-?\\d+)\\)`);
  return (msg) => {
    const m = msg.match(re);
    if (!m) return null;
    const [x, y, z] = [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])];
    if (Math.abs(x - pos.x) <= tol && Math.abs(y - pos.y) <= tol && Math.abs(z - pos.z) <= tol) return m;
    return null;
  };
}
async function waitFor(matcher, timeoutMs) {
  const isRegex = matcher instanceof RegExp;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (let i = 0; i < msgQueue.length; i++) {
      const m = isRegex ? msgQueue[i].match(matcher) : matcher(msgQueue[i]);
      if (m) { msgQueue.splice(i, 1); return m; }
    }
    await sleep(80);
  }
  throw new Error(`timeout waiting /${isRegex ? matcher.source : "<predicate>"}/, queue=${JSON.stringify(msgQueue.slice(-5))}`);
}
async function chatAndWait(cmd, regex, timeoutMs = 20000, attempt = 0) {
  try {
    msgQueue.length = 0;
    bot.chat(cmd);
    return await waitFor(regex, timeoutMs);
  } catch (e) {
    if (attempt >= 6) throw e;
    console.log(`[retry] ${cmd}: ${e.message}`);
    await sleep(1000);
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
const pinsRaw = loadPinsRaw();
let FIRST_POS;
function outputPos(name) {
  const p = pinsRaw[name];
  const tileOffset = name.startsWith("seg") ? 1 : 0;
  return FIRST_POS.offset(p.x + p.nx + tileOffset, p.y + tileOffset, p.z + p.nz);
}

function distTo(pos) {
  return bot.entity.position.distanceTo(pos);
}
async function ensureNear(pos) {
  // flyTo's no-fall/no-clip effect only holds WHILE it's actively running --
  // skipping it as an "already close enough" optimization lets gravity
  // resume afterward, and the player free-falls off a floating output cell
  // (confirmed: landed all the way down at the build's floor, y=8, between
  // retries). So flyTo must run on every single attempt, never skipped --
  // only the expensive /tp pre-step (for closing a LONG distance, which
  // flyTo itself can hang on) is conditional.
  if (distTo(pos) >= 3) {
    bot.chat(`/tp ${pos.x} ${pos.y} ${pos.z}`);
    // Wait for the ENTITY's own position to actually update, not just a
    // fixed delay -- flyTo computing distance from a stale pre-teleport
    // position is what causes it to attempt a long simulated flight again.
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline && distTo(pos) >= 3) await sleep(150);
  }
  await Promise.race([
    bot.creative.flyTo(pos),
    sleep(4000).then(() => { throw new Error("flyTo stuck"); }),
  ]);
}
async function readLampOnce(pos, attempt) {
  if (attempt === 0) msgQueue.length = 0;
  await ensureNear(pos);
  await sleep(300);
  const firstMatch = tolerantPosMatcher("First position", pos);
  const secondMatch = tolerantPosMatcher("Second position", pos);
  if (!msgQueue.some((m) => firstMatch(m))) bot.chat("//pos1");
  await waitFor(firstMatch, 12000);
  if (!msgQueue.some((m) => secondMatch(m))) {
    await sleep(150);
    bot.chat("//pos2");
  }
  await waitFor(secondMatch, 12000);
  for (let i = msgQueue.length - 1; i >= 0; i--) {
    if (/Counted \d+ block/.test(msgQueue[i])) msgQueue.splice(i, 1);
  }
  bot.chat("//count minecraft:redstone_lamp");
  const m = await waitFor(/Counted (\d+) block/, 12000);
  return parseInt(m[1], 10) === 0;
}
async function readLamp(pos, name) {
  for (let attempt = 0; attempt < 20; attempt++) {
    try {
      return await readLampOnce(pos, attempt);
    } catch (e) {
      console.log(`[retry ${attempt}] ${name} @ ${pos}: ${e.message}`);
      await sleep(800);
    }
  }
  throw new Error(`gave up on ${name}`);
}

const DIGIT_FROM_SEG = {
  // Inverted relative to seven_seg()'s logical bits in main.v -- the
  // output driver is active-low (confirmed via mchprs_headless `expect`
  // against the real compiled circuit).
  "0000001": 0, "1001111": 1, "0010010": 2, "0000110": 3, "1001100": 4,
  "0100100": 5, "0100000": 6, "0001111": 7, "0000000": 8, "0000100": 9,
};

bot.once("login", async () => {
  console.log("[login] ok");
  await sleep(1500);
  bot.chat("/gamemode creative");
  await sleep(500);
  bot.chat("/rtps 100000");
  await sleep(500);

  const watchdog = setTimeout(() => {
    console.log("[WATCHDOG] giving up after 45 minutes");
    process.exit(2);
  }, 45 * 60 * 1000);

  try {
    bot.chat(`/tp 100 70 100`);
    await sleep(1000);

    console.log("[load] /load totp_core.litematic -c");
    const loadMsg = await chatAndWait("/load totp_core.litematic -c", /Reloaded .* at (-?\d+), (-?\d+), (-?\d+)/, 60000);
    FIRST_POS = new Vec3(parseInt(loadMsg[1], 10), parseInt(loadMsg[2], 10), parseInt(loadMsg[3], 10));
    console.log(`[load] first_pos = ${FIRST_POS}`);
    await sleep(3000);

    await chatAndWait("/lever rst on", /rst is already on|Turned rst on/);
    await chatAndWait("/lever rst off", /rst is already off|Turned rst off/);
    for (let i = 0; i < 32; i++) {
      const bitVal = (COUNTER >>> i) & 1;
      if (bitVal) {
        await chatAndWait(`/lever counter[${i}] on`, new RegExp(`counter\\[${i}\\] (is already on|Turned counter\\[${i}\\] on)`));
      }
    }
    console.log(`[setup] rst cycled, counter=${COUNTER} set`);

    // The timed measurement starts the instant `start` is confirmed on.
    await chatAndWait("/lever start on", /start is already on|Turned start on/);
    const T_START = Date.now();
    console.log(`[TIMER] start confirmed at t=0.000s -- polling for done`);

    const donePos = outputPos("done");
    let doneLit = false;
    let pollCount = 0;
    while (!doneLit) {
      pollCount++;
      doneLit = await readLamp(donePos, "done");
      const elapsed = (Date.now() - T_START) / 1000;
      console.log(`[poll ${pollCount}] t=${elapsed.toFixed(3)}s done=${doneLit}`);
      if (!doneLit) await sleep(1000);
    }
    const T_DONE = Date.now();
    const computeSeconds = (T_DONE - T_START) / 1000;
    console.log(`[TIMED RESULT] live redstone compute time: ${computeSeconds.toFixed(3)}s (from 'start on' confirmed to 'done' first read true, polled every ~1s)`);

    let code = 0;
    for (let i = 0; i < 20; i++) {
      const lit = await readLamp(outputPos(`code[${i}]`), `code[${i}]`);
      if (lit) code |= (1 << i);
      console.log(`[bit] code[${i}]=${lit ? 1 : 0}`);
    }
    console.log(`[code] code=${code} expected=${EXPECTED} match=${code === parseInt(EXPECTED, 10)}`);

    let display = "";
    for (let digit = 5; digit >= 0; digit--) {
      let segBits = "";
      for (let s = 6; s >= 0; s--) {
        const lit = await readLamp(outputPos(`seg${digit}[${s}]`), `seg${digit}[${s}]`);
        segBits += lit ? "1" : "0";
      }
      const d = DIGIT_FROM_SEG[segBits];
      console.log(`[digit] seg${digit} bits=${segBits} -> digit=${d}`);
      display += d === undefined ? "?" : String(d);
    }
    console.log(`[RESULT] display=${display} code=${code} expected=${EXPECTED} compute_time=${computeSeconds.toFixed(3)}s`);
  } catch (e) {
    console.error("[FATAL]", e.message);
  } finally {
    clearTimeout(watchdog);
    try { bot.quit(); } catch {}
    setTimeout(() => process.exit(0), 1000);
  }
});
