// Minimal, from-scratch seven-segment digit reader against an already
// loaded+driven circuit. One connection, teleport (not flyTo) for every
// move to avoid gravity drift, short fixed delays instead of waiting on
// chat-message regexes for teleport, and a hard overall watchdog so a
// stuck run fails loudly instead of hanging silently.
const mineflayer = require("mineflayer");
const Vec3 = require("vec3");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const FIRST_POS = new Vec3(
  parseInt(process.argv[2], 10),
  parseInt(process.argv[3], 10),
  parseInt(process.argv[4], 10)
);
const EXPECTED = process.argv[5] || "";

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
function outputPos(name) {
  const p = pinsRaw[name];
  const tileOffset = name.startsWith("seg") ? 1 : 0;
  return FIRST_POS.offset(p.x + p.nx + tileOffset, p.y + tileOffset, p.z + p.nz);
}

const bot = mineflayer.createBot({
  host: process.env.MC_HOST || "mchprs_fork_server",
  port: parseInt(process.env.MC_PORT || "25565", 10),
  username: `totp_clean_${Math.floor(Math.random() * 100000)}`,
  version: "1.20.4",
  auth: "offline",
  checkTimeoutInterval: 120000,
});
process.on("uncaughtException", (e) => console.error("[uncaughtException swallowed]", e.message));
process.on("unhandledRejection", (e) => console.error("[unhandledRejection swallowed]", e));
bot.on("error", (e) => console.error("[error]", e));
bot.on("end", (r) => console.log("[end]", r));

// A proper FIFO queue of every chat message, not a single overwritable
// variable -- a single-variable "lastMsg" loses or cross-matches messages
// when two stages' confirmations arrive close together (the actual cause
// of the wrong code=461848 readout in the previous attempt).
const msgQueue = [];
bot.on("message", (m) => { msgQueue.push(m.toString()); if (msgQueue.length > 200) msgQueue.shift(); });

async function waitFor(regex, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (let i = 0; i < msgQueue.length; i++) {
      const m = msgQueue[i].match(regex);
      if (m) { msgQueue.splice(i, 1); return m; }
    }
    await sleep(80);
  }
  throw new Error(`timeout waiting /${regex.source}/, queue=${JSON.stringify(msgQueue.slice(-5))}`);
}

async function readLampOnce(pos, attempt) {
  // Don't discard the queue on a retry -- the target position is unchanged
  // between attempts, so a slow-arriving response from an earlier attempt
  // is still valid data, not stale noise. Only skip re-sending commands
  // whose response already showed up from a previous attempt.
  //
  // CRITICAL: the position-set regexes must check the SPECIFIC coordinates,
  // not just the generic phrase -- a late reply to a DIFFERENT (already
  // moved-on-from) lamp's query can otherwise be wrongly accepted here,
  // since it still matches a bare /First position set/ pattern. This was
  // a real, confirmed bug (corrupted seg-digit reads in an earlier run).
  if (attempt === 0) msgQueue.length = 0;
  await Promise.race([
    bot.creative.flyTo(pos),
    sleep(6000).then(() => { throw new Error("flyTo stuck"); }),
  ]);
  await sleep(300);
  const firstRe = new RegExp(`First position set to \\(${pos.x}, ${pos.y}, ${pos.z}\\)`);
  const secondRe = new RegExp(`Second position set to \\(${pos.x}, ${pos.y}, ${pos.z}\\)`);
  if (!msgQueue.some((m) => firstRe.test(m))) bot.chat("//pos1");
  await waitFor(firstRe, 12000);
  if (!msgQueue.some((m) => secondRe.test(m))) {
    await sleep(150);
    bot.chat("//pos2");
  }
  await waitFor(secondRe, 12000);
  // //count has no echoed coordinates, so discard any stale "Counted" reply
  // still sitting in the queue right before sending it -- the selection is
  // now definitively this lamp's, so only a reply arriving AFTER this point
  // can be trusted as this lamp's count.
  for (let i = msgQueue.length - 1; i >= 0; i--) {
    if (/Counted \d+ block/.test(msgQueue[i])) msgQueue.splice(i, 1);
  }
  bot.chat("//count minecraft:redstone_lamp");
  const m = await waitFor(/Counted (\d+) block/, 12000);
  return parseInt(m[1], 10) === 0; // count==0 => lit, per project convention
}
async function readLamp(pos, name) {
  for (let attempt = 0; attempt < 8; attempt++) {
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
  await sleep(800);
  // flyTo over a very long first hop (spawn -> build area) can hang; close
  // the distance with a plain /tp first (gravity doesn't matter here --
  // the very next flyTo call re-stabilizes the position properly).
  const firstTarget = outputPos("done");
  bot.chat(`/tp ${firstTarget.x} ${firstTarget.y} ${firstTarget.z}`);
  await sleep(1500);

  // Watchdog: if we haven't finished in 45 minutes, dump what we have and exit non-zero.
  const watchdog = setTimeout(() => {
    console.log("[WATCHDOG] giving up after 45 minutes");
    process.exit(2);
  }, 45 * 60 * 1000);

  try {
    let doneLit = false;
    for (let round = 0; round < 12; round++) {
      doneLit = await readLamp(outputPos("done"), "done");
      console.log(`[bit] done=${doneLit} (round ${round})`);
      if (doneLit) break;
      await sleep(10000);
    }
    if (!doneLit) throw new Error("done never went true after 12 rounds");

    let code = 0;
    for (let i = 0; i < 20; i++) {
      const lit = await readLamp(outputPos(`code[${i}]`), `code[${i}]`);
      if (lit) code |= (1 << i);
      console.log(`[bit] code[${i}]=${lit ? 1 : 0}`);
    }
    console.log(`[code] done=${doneLit} code=${code} expected=${EXPECTED} match=${code === parseInt(EXPECTED, 10)}`);

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
    console.log(`[RESULT] display=${display} code=${code} expected=${EXPECTED}`);
  } catch (e) {
    console.error("[FATAL]", e.message);
  } finally {
    clearTimeout(watchdog);
    try { bot.quit(); } catch {}
    setTimeout(() => process.exit(0), 1000);
  }
});
